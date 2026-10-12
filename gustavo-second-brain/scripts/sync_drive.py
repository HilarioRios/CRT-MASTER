"""Sincroniza RAW/PROCESSED/METADATA de cada fuente procesada hacia el
Drive del Segundo Cerebro, usando la estructura de carpetas ya creada
(config/drive_structure.json). Disenado para escala (~345 fuentes reales y
futuras, no solo el piloto de 10):

- Idempotente: si un archivo ya tiene drive_*_file_id en SQLite y su
  md5Checksum remoto coincide con el md5 local, se saltea -- no sube de
  nuevo ni crea duplicados.
- RAW es INMUTABLE: si ya hay una copia valida en Drive, nunca se
  reemplaza. Si detecta un md5 distinto (drift), lo registra como conflicto
  en `errors` y NO sobreescribe -- requiere revision manual, nunca silenciosa.
- PROCESSED/METADATA si pueden actualizarse (mismo file_id, contenido
  nuevo) si el md5 local cambio.
- Reintentos con backoff exponencial en cada subida/actualizacion.
- Verificacion de integridad: tras cada subida/actualizacion, compara el
  md5Checksum que devuelve Drive contra el md5 local antes de dar por
  exitoso el archivo.
- Resumible: cada archivo exitoso se persiste en SQLite (tabla drive_sync)
  inmediatamente (commit por archivo, no al final del batch) -- si el
  proceso se corta a mitad de camino, la proxima corrida retoma solo lo
  que falta.
- Estructura de carpetas deterministica: usa los folder_id ya existentes
  en config/drive_structure.json, nunca crea jerarquia nueva ahi.
- Soporta archivos grandes via upload resumable (MediaFileUpload
  resumable=True -- maneja el chunking/reanudacion a nivel HTTP).
- run(source_ids=...) es una funcion Python normal ademas de CLI, para que
  un futuro trigger (n8n, u otro orquestador) pueda invocar el mismo
  sync sin pasar por argparse.

Mapeo de archivos locales -> rol en Drive (ver normalize_transcript.py):
  raw       -> data/raw/youtube/<video_id>/transcript.es.vtt
  processed -> data/processed/youtube/<video_id>/transcript_clean.txt
  metadata  -> data/processed/youtube/<video_id>/transcript_segments.json

Uso:
    .venv/bin/python scripts/sync_drive.py --pilot
    .venv/bin/python scripts/sync_drive.py <source_id> [<source_id> ...]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DRIVE_STRUCTURE_PATH = ROOT / "config" / "drive_structure.json"
PILOT_SELECTION_PATH = ROOT / "config" / "pilot_selection.json"
DRIVE_TOKEN_FILE = ROOT / os.environ["GOOGLE_DRIVE_OAUTH_TOKEN_FILE"]
# Scope completo, no drive.file -- ver authorize_drive.py para el porque
# (escribe en una carpeta preexistente referenciada por folder_id estatico,
# no por un folder que esta app creo o descubrio via listado).
SCOPES = ["https://www.googleapis.com/auth/drive"]

FILE_ROLES = {
    "raw": {
        "local": lambda video_id: ROOT / "data" / "raw" / "youtube" / video_id / "transcript.es.vtt",
        "drive_name": lambda video_id: f"{video_id}_transcript_raw.vtt",
        "subfolder": "01_RAW",
        "db_column": "drive_raw_file_id",
        "immutable": True,
    },
    "processed": {
        "local": lambda video_id: ROOT / "data" / "processed" / "youtube" / video_id / "transcript_clean.txt",
        "drive_name": lambda video_id: f"{video_id}_transcript_processed.txt",
        "subfolder": "02_PROCESSED",
        "db_column": "drive_processed_file_id",
        "immutable": False,
    },
    "metadata": {
        "local": lambda video_id: ROOT / "data" / "processed" / "youtube" / video_id / "transcript_segments.json",
        "drive_name": lambda video_id: f"{video_id}_segments.json",
        "subfolder": "03_METADATA",
        "db_column": "drive_metadata_file_id",
        "immutable": False,
    },
}

SOURCE_ID_CHANNEL_RE = re.compile(r"^YT_(CANAL_\d+)_")
# YouTube video_id puede contener guiones bajos (p.ej. "-7G__mSBIrg"), asi
# que extraerlo con rsplit("_", 1) desde la derecha es incorrecto -- hay que
# anclar en el prefijo fijo YT_CANAL_NN_ y tomar TODO lo que sigue.
SOURCE_ID_VIDEO_ID_RE = re.compile(r"^YT_CANAL_\d+_(.+)$")


def get_drive_service():
    """Requiere scripts/authorize_drive.py corrido antes (token ya en disco)."""
    if not DRIVE_TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"No hay token de Drive en {DRIVE_TOKEN_FILE}. "
            f"Corre primero: .venv/bin/python scripts/authorize_drive.py"
        )
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(DRIVE_TOKEN_FILE), SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        DRIVE_TOKEN_FILE.write_text(creds.to_json())
        DRIVE_TOKEN_FILE.chmod(0o600)
    return build("drive", "v3", credentials=creds)


def compute_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_drive_structure() -> dict:
    return json.loads(DRIVE_STRUCTURE_PATH.read_text())


def channel_key_for_source_id(source_id: str) -> str:
    """'YT_CANAL_01_abc123' -> 'canal_01'."""
    match = SOURCE_ID_CHANNEL_RE.match(source_id)
    if not match:
        raise ValueError(f"source_id con formato inesperado (no empieza con YT_CANAL_NN_): {source_id}")
    return match.group(1).lower()


def target_folder_id(structure: dict, channel_key: str, subfolder: str) -> str:
    return structure["youtube_channels"][channel_key]["subfolders"][subfolder]


def video_id_for_source_id(source_id: str) -> str:
    """'YT_CANAL_02_-7G__mSBIrg' -> '-7G__mSBIrg'. NUNCA usar
    source_id.rsplit('_', 1) -- los video_id de YouTube pueden contener
    guiones bajos, lo que corta el id a la mitad (bug real, detectado en
    el piloto: '-7G__mSBIrg' se convertia incorrectamente en 'mSBIrg')."""
    match = SOURCE_ID_VIDEO_ID_RE.match(source_id)
    if not match:
        raise ValueError(f"source_id con formato inesperado (no empieza con YT_CANAL_NN_): {source_id}")
    return match.group(1)


def retry(fn, attempts: int = 4, base_delay: float = 2.0, what: str = "operacion"):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except (HttpError, ConnectionError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt == attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            print(f"  [retry] {what} fallo (intento {attempt}/{attempts}): {exc} -- reintentando en {delay:.0f}s", flush=True)
            time.sleep(delay)
    raise last_exc


def upload_new_file(service, local_path: Path, parent_id: str, drive_name: str) -> dict:
    media = MediaFileUpload(str(local_path), resumable=True)
    return service.files().create(
        body={"name": drive_name, "parents": [parent_id]},
        media_body=media,
        fields="id,md5Checksum,size",
    ).execute()


def update_existing_file(service, file_id: str, local_path: Path) -> dict:
    media = MediaFileUpload(str(local_path), resumable=True)
    return service.files().update(
        fileId=file_id, media_body=media, fields="id,md5Checksum,size"
    ).execute()


def get_remote_file_meta(service, file_id: str) -> dict | None:
    try:
        return service.files().get(fileId=file_id, fields="id,md5Checksum,size,trashed").execute()
    except HttpError as exc:
        if exc.resp.status == 404:
            return None
        raise


def sync_one_file(conn, service, source_id: str, role: str, existing_file_id: str | None) -> dict:
    """Idempotencia + inmutabilidad de RAW + verificacion de integridad para
    UN archivo. No hace commit (el caller decide cuando persistir)."""
    spec = FILE_ROLES[role]
    video_id = video_id_for_source_id(source_id)
    local_path = spec["local"](video_id)

    if not local_path.exists():
        return {"status": "local_missing", "file_id": existing_file_id, "role": role}

    local_md5 = compute_md5(local_path)

    if existing_file_id:
        remote = get_remote_file_meta(service, existing_file_id)
        if remote and not remote.get("trashed") and remote.get("md5Checksum") == local_md5:
            return {"status": "already_synced", "file_id": existing_file_id, "role": role}

        if remote and not remote.get("trashed") and remote.get("md5Checksum") != local_md5:
            if spec["immutable"]:
                return {
                    "status": "integrity_conflict_skipped",
                    "file_id": existing_file_id,
                    "role": role,
                    "detail": f"RAW remoto (md5={remote.get('md5Checksum')}) difiere del local "
                              f"(md5={local_md5}) -- NO se sobreescribe, requiere revision manual",
                }
            updated = retry(
                lambda: update_existing_file(service, existing_file_id, local_path),
                what=f"update {role} de {source_id}",
            )
            if updated.get("md5Checksum") != local_md5:
                return {"status": "integrity_failed_after_update", "file_id": existing_file_id, "role": role}
            return {"status": "updated", "file_id": updated["id"], "role": role}
        # remote is None (trashed/deleted en Drive) -> cae a subir de nuevo abajo.

    structure = load_drive_structure()
    channel_key = channel_key_for_source_id(source_id)
    parent_id = target_folder_id(structure, channel_key, spec["subfolder"])
    drive_name = spec["drive_name"](video_id)

    uploaded = retry(
        lambda: upload_new_file(service, local_path, parent_id, drive_name),
        what=f"upload {role} de {source_id}",
    )
    if uploaded.get("md5Checksum") != local_md5:
        return {"status": "integrity_failed_after_upload", "file_id": uploaded.get("id"), "role": role}
    return {"status": "uploaded", "file_id": uploaded["id"], "role": role}


def _log_error(conn, source_id: str, message: str) -> None:
    conn.execute(
        "INSERT INTO errors (source_id, stage, message) VALUES (?, 'drive_sync', ?)",
        (source_id, message),
    )


def sync_source(conn, service, source_id: str) -> dict:
    row = conn.execute(
        "SELECT drive_raw_file_id, drive_processed_file_id, drive_metadata_file_id "
        "FROM drive_sync WHERE source_id=?",
        (source_id,),
    ).fetchone()
    existing = {
        "raw": row["drive_raw_file_id"] if row else None,
        "processed": row["drive_processed_file_id"] if row else None,
        "metadata": row["drive_metadata_file_id"] if row else None,
    }

    results = {}
    for role in ("raw", "processed", "metadata"):
        result = sync_one_file(conn, service, source_id, role, existing[role])
        results[role] = result

        if result["status"] in ("uploaded", "updated", "already_synced"):
            conn.execute(
                f"""INSERT INTO drive_sync (source_id, {FILE_ROLES[role]['db_column']}, synced_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(source_id) DO UPDATE SET
                      {FILE_ROLES[role]['db_column']}=excluded.{FILE_ROLES[role]['db_column']},
                      synced_at=excluded.synced_at""",
                (source_id, result["file_id"]),
            )
            conn.commit()
        else:
            _log_error(conn, source_id, f"drive_sync[{role}]: {result['status']} -- {result.get('detail', '')}")
            conn.commit()

    all_ok = all(r["status"] in ("uploaded", "updated", "already_synced") for r in results.values())
    if all_ok:
        conn.execute(
            "UPDATE sources SET processing_status='DRIVE_SYNCED' WHERE source_id=?", (source_id,)
        )
        conn.commit()

    return {"source_id": source_id, "all_ok": all_ok, "files": results}


def resolve_source_ids(pilot: bool, explicit_ids: list[str]) -> list[str]:
    if explicit_ids:
        return explicit_ids
    if pilot:
        selection = json.loads(PILOT_SELECTION_PATH.read_text())
        return [v["source_id"] for v in selection["videos"]]
    raise ValueError("Especifica --pilot o al menos un source_id explicito.")


def run(source_ids: list[str] | None = None, pilot: bool = False) -> list[dict]:
    """Funcion normal ademas de CLI -- invocable programaticamente (p.ej.
    por un futuro trigger de n8n) sin pasar por argparse."""
    init_db()
    service = get_drive_service()
    conn = get_connection()
    summaries = []
    try:
        ids = resolve_source_ids(pilot, source_ids or [])
        for source_id in ids:
            print(f"[{source_id}] sincronizando con Drive ...", flush=True)
            summary = sync_source(conn, service, source_id)
            summaries.append(summary)
            status_line = ", ".join(f"{role}={r['status']}" for role, r in summary["files"].items())
            print(f"[{source_id}] {status_line}", flush=True)
    finally:
        conn.close()
    return summaries


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("source_ids", nargs="*")
    args = parser.parse_args()

    results = run(source_ids=args.source_ids, pilot=args.pilot)
    ok = sum(1 for r in results if r["all_ok"])
    print(f"\n{ok}/{len(results)} fuentes sincronizadas completamente con Drive.")
