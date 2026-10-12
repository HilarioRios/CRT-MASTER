"""FASE 5 (metodo 4, ultimo recurso) -- Whisper local (faster-whisper) para
videos que no tienen captions oficiales (OAuth) ni subtitulos manuales/auto
de yt-dlp (processing_status='TRANSCRIPT_PENDING', ver fetch_captions.py).

Descarga SOLO audio (yt-dlp, bestaudio, sin video) a un archivo temporal,
transcribe localmente, escribe el resultado como un VTT estandar (un cue
por segmento, sin tags <c>) -- vtt_parser.py lo parsea sin cambios: con un
solo cue por segmento no hay cues duplicados consecutivos que colapsar, asi
que su logica de dedup simplemente no encuentra nada que fusionar y cada
segmento de Whisper queda como su propio Segment. El audio temporal se
borra despues de transcribir -- no es un artefacto RAW rastreado por el
pipeline, solo el VTT resultante lo es.

Modelo/dispositivo configurables via config/settings.yaml (whisper.model_size/
device/compute_type) -- default medio/CPU/int8, igual que el resto del
proyecto (ver README).
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import yaml
import yt_dlp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "youtube"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
JS_RUNTIMES = {"node": {}}


def load_whisper_settings() -> dict:
    settings = yaml.safe_load(SETTINGS_PATH.read_text())
    return settings.get("transcription", {}).get("whisper", {
        "model_size": "medium", "device": "cpu", "compute_type": "int8",
    })


def format_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, rem_ms = divmod(total_ms, 3_600_000)
    minutes, rem_ms = divmod(rem_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def write_whisper_vtt(segments, out_path: Path) -> None:
    lines = ["WEBVTT", ""]
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        lines.append(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}")
        lines.append(text)
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def download_audio(video_url: str, out_path_no_ext: Path) -> Path:
    """READ-ONLY respecto a YouTube (solo descarga, no modifica nada ahi).
    Descarga solo audio, nunca video."""
    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": str(out_path_no_ext) + ".%(ext)s",
        "js_runtimes": JS_RUNTIMES,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([video_url])
    candidates = list(out_path_no_ext.parent.glob(out_path_no_ext.name + ".*"))
    if not candidates:
        raise RuntimeError(f"yt-dlp no produjo audio para {video_url}")
    return candidates[0]


def transcribe_one(video_id: str, video_url: str, model) -> dict:
    """Returns {'method': 'whisper_local', 'path': str, 'lang': 'es'}."""
    with tempfile.TemporaryDirectory() as tmp:
        audio_path = download_audio(video_url, Path(tmp) / "audio")
        segments, _info = model.transcribe(str(audio_path), language="es")
        out_path = RAW_DIR / video_id / "transcript.es.vtt"
        write_whisper_vtt(segments, out_path)
    return {"method": "whisper_local", "path": str(out_path), "lang": "es"}


def run_for_videos(video_ids: list[str] | None = None, force: bool = False) -> dict:
    from faster_whisper import WhisperModel

    init_db()
    conn = get_connection()
    results = {"whisper_local": 0, "skipped_not_pending": 0, "failed": 0}
    try:
        if video_ids is None:
            rows = conn.execute(
                "SELECT yv.video_id FROM youtube_videos yv JOIN sources s ON s.source_id=yv.source_id "
                "WHERE s.processing_status='TRANSCRIPT_PENDING'"
            ).fetchall()
            video_ids = [r["video_id"] for r in rows]

        if not video_ids:
            return results

        model = None  # carga perezosa: solo si realmente hay algo que transcribir
                      # (el modelo pesa varios cientos de MB, no vale la pena
                      # cargarlo si todos los videos terminan salteados)

        for video_id in video_ids:
            row = conn.execute(
                """SELECT yv.source_id, yv.url, s.processing_status
                   FROM youtube_videos yv JOIN sources s ON s.source_id = yv.source_id
                   WHERE yv.video_id = ?""",
                (video_id,),
            ).fetchone()
            if not row:
                print(f"  !! {video_id}: not in DB, skip", flush=True)
                continue
            if not force and row["processing_status"] != "TRANSCRIPT_PENDING":
                results["skipped_not_pending"] += 1
                continue

            source_id, url = row["source_id"], row["url"]
            if model is None:
                settings = load_whisper_settings()
                print(f"Cargando modelo Whisper ({settings['model_size']}, {settings['device']}, "
                      f"{settings['compute_type']}) ...", flush=True)
                model = WhisperModel(
                    settings["model_size"], device=settings["device"], compute_type=settings["compute_type"]
                )

            print(f"  [{video_id}] transcribiendo con Whisper (puede tardar varios minutos) ...", flush=True)
            start = time.monotonic()
            try:
                result = transcribe_one(video_id, url, model)
            except Exception as exc:  # noqa: BLE001 -- un video malo no debe abortar el batch
                results["failed"] += 1
                conn.execute(
                    "INSERT INTO errors (source_id, stage, message) VALUES (?, 'transcript', ?)",
                    (source_id, f"whisper_local: {exc}"),
                )
                conn.commit()
                print(f"  !! {video_id}: error {exc}", flush=True)
                continue

            elapsed = time.monotonic() - start
            results["whisper_local"] += 1
            conn.execute(
                """INSERT INTO transcripts (source_id, method, raw_file_path, language)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(source_id) DO UPDATE SET
                     method=excluded.method, raw_file_path=excluded.raw_file_path,
                     language=excluded.language""",
                (source_id, result["method"], result["path"], result["lang"]),
            )
            conn.execute(
                """UPDATE sources SET processing_status='TRANSCRIPT_READY', transcript_source=?
                   WHERE source_id=?""",
                (result["method"], source_id),
            )
            conn.commit()
            print(f"  ok {video_id}: whisper_local ({elapsed:.0f}s)", flush=True)
    finally:
        conn.close()
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("video_ids", nargs="*")
    args = parser.parse_args()

    ids = args.video_ids or None
    summary = run_for_videos(ids, force=args.force)
    print(summary)
