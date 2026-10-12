"""FASE 21/21 -- Importacion completa por lotes del catalogo real
(include_in_knowledge_base=1 -- excluye SHORTS permanentemente, sin
excepcion). Reusa cada paso ya construido y probado como funciones
importadas -- NO reimplementa nada, NO usa subprocess:
  - fetch_captions.fetch_with_cascade (metodos 1-3: OAuth, yt-dlp manual/auto)
  - transcribe_missing.transcribe_one (metodo 4: Whisper, ultimo recurso)
  - normalize_transcript.normalize_video
  - chunk_content.run_for_video
  - build_search_index.rebuild_index (una vez por lote -- indice incremental,
    nunca se espera al final)
  - sync_drive.sync_source (create/update de archivos propios, checksum,
    reintentos, RAW inmutable -- ver su propio docstring)
  - build_master_index.build (una vez por lote)

Resumible por diseño: select_pending_batch() SIEMPRE calcula "pendientes"
via SQL (include_in_knowledge_base=1 AND processing_status NOT IN
('DRIVE_SYNCED', 'FAILED')) -- nunca una lista fija. Si el proceso se
corta a mitad de un lote, la proxima corrida retoma exactamente donde
quedo: cada fuente ya avanzo a su processing_status real en SQLite, y
process_source() reanuda desde ahi (no reprocesa pasos ya completados).

IMPORTANTE -- por que FAILED se excluye de la seleccion normal: si se
incluyera, una fuente que falla en el lote 1 volveria a aparecer en TODOS
los lotes siguientes (mientras su status siga sin ser DRIVE_SYNCED),
consumiendo cuota/tiempo repetidamente en vez de las "max 2 reintentos"
pedidas. Por eso FAILED se procesa UNICAMENTE en run_retry_pass(), una vez
terminada la primera pasada, con un tope real de reintentos contado via la
tabla `errors` (stage='pipeline').

Seguridad (IMMUTABILITY_GUARD): este script no agrega ningun llamado nuevo
a YouTube ni a Drive -- solo reutiliza fetch_with_cascade/transcribe_one
(solo lectura sobre YouTube) y sync_source (create/update sobre archivos
propios en el Drive destino, nunca delete, nunca sobre el Drive original).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402
from fetch_captions import fetch_with_cascade  # noqa: E402
from transcribe_missing import transcribe_one, load_whisper_settings  # noqa: E402
from normalize_transcript import normalize_video  # noqa: E402
from chunk_content import run_for_video  # noqa: E402
from build_search_index import rebuild_index  # noqa: E402
from sync_drive import sync_source, get_drive_service  # noqa: E402
from build_master_index import build as build_master_index  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

BATCH_SIZE = 25
MAX_RETRIES = 2
FAILURE_RATE_STOP_THRESHOLD = 0.10

# Rank de cada processing_status en la cadena de pasos -- usado para saber
# por donde reanudar una fuente sin repetir pasos ya hechos.
STEP_RANK = {
    "DISCOVERED": 0, "METADATA_READY": 0, "TRANSCRIPT_PENDING": 0,
    "TRANSCRIPT_READY": 1, "PROCESSED": 2, "CHUNKED": 3, "INDEXED": 3,
    "DRIVE_SYNCED": 4, "FAILED": 0,
}

_whisper_model = None  # cache: un solo modelo cargado para toda la corrida


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        settings = load_whisper_settings()
        print(f"Cargando modelo Whisper ({settings['model_size']}, {settings['device']}, "
              f"{settings['compute_type']}) ...", flush=True)
        _whisper_model = WhisperModel(
            settings["model_size"], device=settings["device"], compute_type=settings["compute_type"]
        )
    return _whisper_model


def select_pending_batch(conn, limit: int = BATCH_SIZE, include_failed: bool = False) -> list[dict]:
    """SIEMPRE calculado via SQL en el momento, nunca una lista fija (ver
    docstring del modulo). include_failed=True es solo para run_retry_pass."""
    # PENDING_ACCESS = contenido de membresia paga de YouTube (internal_classification=
    # YOUTUBE_MEMBERS_ONLY_EXCLUSIVE), sin acceso via OAuth de propietario tampoco. Se
    # excluye de ambos modos (no solo del normal): reintentarlo en cada corrida del
    # retry pass quemaria cuota de la API sin ninguna posibilidad real de exito hasta
    # que se resuelva el acceso manualmente.
    excluded = "('DRIVE_SYNCED', 'PENDING_ACCESS')" if include_failed else "('DRIVE_SYNCED', 'FAILED', 'PENDING_ACCESS')"
    rows = conn.execute(
        f"""SELECT s.source_id, yv.video_id, yv.channel_id, s.channel, s.original_title,
                   s.original_url, s.processing_status
            FROM sources s JOIN youtube_videos yv ON yv.source_id = s.source_id
            WHERE s.include_in_knowledge_base = 1 AND s.processing_status NOT IN {excluded}
            ORDER BY s.source_id
            LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def select_all_failed(conn) -> list[dict]:
    """TODAS las fuentes FAILED, sin LIMIT. Usado unicamente por
    run_retry_pass -- NUNCA uses select_pending_batch(limit=N,
    include_failed=True) dentro de un loop de reintentos: con LIMIT fijo y
    ORDER BY source_id deterministico, si las primeras N (alfabeticamente)
    siguen fallando, la consulta devuelve SIEMPRE el mismo bloque y las
    fuentes FAILED que quedan despues de la posicion N nunca se llegan a
    intentar (bug real encontrado en la primera corrida de importacion
    completa: 6 de 345 fuentes quedaron sin ningun intento de reintento,
    con updated_at congelado en la fecha del discovery original)."""
    rows = conn.execute(
        """SELECT s.source_id, yv.video_id, yv.channel_id, s.channel, s.original_title,
                  s.original_url, s.processing_status
           FROM sources s JOIN youtube_videos yv ON yv.source_id = s.source_id
           WHERE s.include_in_knowledge_base = 1 AND s.processing_status = 'FAILED'
           ORDER BY s.source_id"""
    ).fetchall()
    return [dict(r) for r in rows]


def attempt_count(conn, source_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) c FROM errors WHERE source_id=? AND stage='pipeline'", (source_id,)
    ).fetchone()["c"]


def process_source(conn, drive_service, source: dict) -> tuple[bool, dict]:
    """Avanza UNA fuente desde su processing_status actual hasta
    DRIVE_SYNCED, reanudando desde el paso que corresponda. Nunca levanta
    una excepcion hacia el caller -- cualquier fallo se registra en
    `errors` (stage='pipeline'), la fuente queda FAILED, y se devuelve
    (False, info) para que el batch siga con la siguiente."""
    source_id = source["source_id"]
    video_id = source["video_id"]
    status = source["processing_status"]
    info: dict = {"transcript_source": None, "chunks": 0}

    try:
        if STEP_RANK[status] < 1:
            result = fetch_with_cascade(video_id, source["original_url"], source["channel_id"])
            if result["method"] is None:
                model = get_whisper_model()
                result = transcribe_one(video_id, source["original_url"], model)
            conn.execute(
                """INSERT INTO transcripts (source_id, method, raw_file_path, language)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(source_id) DO UPDATE SET
                     method=excluded.method, raw_file_path=excluded.raw_file_path,
                     language=excluded.language""",
                (source_id, result["method"], result["path"], result["lang"]),
            )
            conn.execute(
                "UPDATE sources SET processing_status='TRANSCRIPT_READY', transcript_source=? WHERE source_id=?",
                (result["method"], source_id),
            )
            conn.commit()
            info["transcript_source"] = result["method"]
            status = "TRANSCRIPT_READY"

        if STEP_RANK[status] < 2:
            normalize_video(video_id)
            conn.execute("UPDATE sources SET processing_status='PROCESSED' WHERE source_id=?", (source_id,))
            conn.commit()
            status = "PROCESSED"

        if STEP_RANK[status] < 3:
            n_chunks = run_for_video(
                video_id, source_id, source["original_title"], source["channel"], source["original_url"]
            )
            info["chunks"] = n_chunks
            status = "CHUNKED"  # run_for_video ya lo persiste en DB

        if STEP_RANK[status] < 4:
            drive_summary = sync_source(conn, drive_service, source_id)
            if not drive_summary["all_ok"]:
                failed_roles = {r: v["status"] for r, v in drive_summary["files"].items()
                                 if v["status"] not in ("uploaded", "updated", "already_synced")}
                raise RuntimeError(f"drive_sync incompleto: {failed_roles}")
            status = "DRIVE_SYNCED"

        return True, info
    except Exception as exc:  # noqa: BLE001 -- una fuente mala no debe frenar el lote
        conn.execute(
            "INSERT INTO errors (source_id, stage, message) VALUES (?, 'pipeline', ?)",
            (source_id, str(exc)),
        )
        conn.execute("UPDATE sources SET processing_status='FAILED' WHERE source_id=?", (source_id,))
        conn.commit()
        info["error"] = str(exc)
        return False, info


def run_batch(conn, drive_service, sources: list[dict], batch_num: int) -> dict:
    start = time.monotonic()
    summary = {
        "batch_num": batch_num, "processed": 0, "succeeded": 0, "failed": 0,
        "youtube_official": 0, "yt_dlp_manual": 0, "yt_dlp_auto": 0, "whisper_local": 0,
        "chunks": 0, "sources": [],
    }
    for source in sources:
        ok, info = process_source(conn, drive_service, source)
        summary["processed"] += 1
        summary["sources"].append({"source_id": source["source_id"], "ok": ok, **info})
        if ok:
            summary["succeeded"] += 1
            summary["chunks"] += info.get("chunks", 0)
            method = info.get("transcript_source")
            if method in summary:
                summary[method] += 1
        else:
            summary["failed"] += 1
        print(f"  [{source['source_id']}] {'OK' if ok else 'FAILED'} "
              f"{info.get('transcript_source') or info.get('error', '')}", flush=True)

    rebuild_index()  # indice incremental -- nunca se espera al final
    build_master_index()
    summary["elapsed_sec"] = time.monotonic() - start
    summary["failure_rate"] = summary["failed"] / summary["processed"] if summary["processed"] else 0.0
    return summary


def write_batch_report(summary: dict) -> Path:
    n = summary["batch_num"]
    path = ROOT / f"BATCH_REPORT_{n}.md"
    lines = [
        f"# BATCH_REPORT_{n}", "",
        f"- Procesados: {summary['processed']}",
        f"- Exitosos: {summary['succeeded']}",
        f"- Fallidos: {summary['failed']} (tasa: {summary['failure_rate']*100:.1f}%)",
        f"- Captions oficiales (OAuth): {summary['youtube_official']}",
        f"- yt-dlp manual: {summary['yt_dlp_manual']}",
        f"- yt-dlp auto: {summary['yt_dlp_auto']}",
        f"- Whisper local: {summary['whisper_local']}",
        f"- Chunks generados: {summary['chunks']}",
        f"- Tiempo del lote: {summary['elapsed_sec']:.1f}s",
        "",
        "## Detalle por fuente",
    ]
    for s in summary["sources"]:
        status = "OK" if s["ok"] else "FAILED"
        extra = s.get("transcript_source") or s.get("error", "")
        lines.append(f"- {s['source_id']}: {status} ({extra})")
    path.write_text("\n".join(lines) + "\n")
    return path


def run_retry_pass(conn, drive_service, max_retries: int = MAX_RETRIES) -> dict:
    """Reintenta las fuentes FAILED, hasta max_retries veces cada una
    (contado via `errors` stage='pipeline'). Las que agoten los reintentos
    quedan FAILED para revision manual -- nunca bloquean a las demas."""
    summary = {"retried": 0, "recovered": 0, "still_failed": 0}
    while True:
        candidates = [
            s for s in select_all_failed(conn)
            if attempt_count(conn, s["source_id"]) <= max_retries
        ]
        if not candidates:
            break
        for source in candidates:
            summary["retried"] += 1
            ok, _info = process_source(conn, drive_service, source)
            if ok:
                summary["recovered"] += 1
            print(f"  [retry] [{source['source_id']}] {'recuperado' if ok else 'sigue fallando'}", flush=True)
    summary["still_failed"] = conn.execute(
        "SELECT COUNT(*) c FROM sources WHERE include_in_knowledge_base=1 AND processing_status='FAILED'"
    ).fetchone()["c"]
    rebuild_index()
    build_master_index()
    return summary


def run_import() -> dict:
    init_db()
    conn = get_connection()
    drive_service = get_drive_service()
    batch_reports = []
    try:
        batch_num = 0
        while True:
            batch_sources = select_pending_batch(conn)
            if not batch_sources:
                break
            batch_num += 1
            print(f"\n=== Lote {batch_num} ({len(batch_sources)} fuentes) ===", flush=True)
            summary = run_batch(conn, drive_service, batch_sources, batch_num)
            write_batch_report(summary)
            batch_reports.append(summary)
            if summary["failure_rate"] > FAILURE_RATE_STOP_THRESHOLD:
                print(f"DETENIDO: tasa de fallo {summary['failure_rate']*100:.1f}% > 10% en lote {batch_num}", flush=True)
                return {"batch_reports": batch_reports, "stopped_early": True, "reason": "failure_rate"}

        print("\n=== Primera pasada completa. Iniciando retry_failed (max 2 por fuente) ===", flush=True)
        retry_summary = run_retry_pass(conn, drive_service)
        return {"batch_reports": batch_reports, "retry_summary": retry_summary, "stopped_early": False}
    finally:
        conn.close()


if __name__ == "__main__":
    result = run_import()
    print("\n=== IMPORTACION COMPLETA ===")
    print(result.get("retry_summary"))
