"""FASE 5 -- Fetch captions, cascada completa de 4 metodos en orden de
prioridad:
  1. youtube_official -- captions oficiales via YouTube Data API con OAuth
     (captions().list + captions().download). Requiere que la cuenta
     autenticada sea dueña/administradora del canal del video -- usa el
     token OAuth correspondiente al canal (ver CHANNEL_TOKEN_FILES).
  2. yt_dlp_manual -- subtitulos manuales via yt-dlp (publico, sin OAuth).
  3. yt_dlp_auto -- subtitulos automaticos via yt-dlp.
  4. whisper_local -- ver transcribe_missing.py. Si ninguno de los 3
     metodos de arriba encuentra captions, processing_status queda en
     TRANSCRIPT_PENDING para que transcribe_missing.py lo recoja.

Guarda el archivo de subtitulos crudo sin tocar bajo
data/raw/youtube/<video_id>/transcript.<lang>.vtt (RAW es inmutable --
nunca se reescribe en pasos posteriores). El formato devuelto por la API
oficial (captions().download(tfmt='vtt')) es el mismo VTT "roll-up" con
tags <c> que ya produce yt-dlp para auto-captions -- vtt_parser.py lo
parsea sin cambios, verificado empiricamente contra un video real antes de
implementar esto. Actualiza `transcripts` + `sources.processing_status` y
siempre registra `transcript_source` (metodo usado) y cuenta cuantos casos
necesitaron cada metodo (ver `results` en run_for_videos).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import yt_dlp
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw" / "youtube"
JS_RUNTIMES = {"node": {}}
PREFERRED_LANGS = ["es", "es-419", "es-ES", "es-US"]

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Descargar captions oficiales requiere el OAuth del DUEÑO del canal --
# un token cualquiera no alcanza. Mapea channel_id -> archivo de token.
CHANNEL_TOKEN_FILES = {
    "UCwMIt6Wa7WzoP2vZR1KO9PQ": "youtube_gustavo.json",         # MentoTrading (canal_01)
    "UC9jWf-KAZ9x4O7J3tM8_pWA": "youtube_gustavo_trader.json",  # Gustavom.Trader (canal_02)
}

_youtube_services_cache: dict[str, object] = {}


def get_youtube_service_for_channel(channel_id: str):
    """Construye (y cachea) un cliente de la YouTube Data API autenticado
    con el token OAuth correspondiente al dueño de ese canal. None si no
    hay token mapeado para ese channel_id (cae a yt-dlp directamente)."""
    if channel_id in _youtube_services_cache:
        return _youtube_services_cache[channel_id]

    token_name = CHANNEL_TOKEN_FILES.get(channel_id)
    if not token_name:
        return None
    token_file = ROOT / "tokens" / token_name
    if not token_file.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_file), YOUTUBE_SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
        token_file.chmod(0o600)

    service = build("youtube", "v3", credentials=creds)
    _youtube_services_cache[channel_id] = service
    return service


def fetch_official_caption(youtube, video_id: str) -> dict | None:
    """READ-ONLY sobre el video (captions().list + download, nunca
    insert/update/delete). Devuelve {'method':'youtube_official','path':...,
    'lang':...} o None si no hay track en español o la cuenta no tiene
    permiso para bajarla (video de otro canal, etc -- cae a yt-dlp)."""
    out_dir = RAW_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = youtube.captions().list(part="snippet", videoId=video_id).execute()
    except HttpError:
        return None

    tracks = [item for item in resp.get("items", []) if item["snippet"]["language"].startswith("es")]
    if not tracks:
        return None
    # Preferir track manual (no-ASR) sobre automatico si hay varios.
    tracks.sort(key=lambda t: t["snippet"]["trackKind"] == "asr")
    track = tracks[0]
    lang = track["snippet"]["language"]

    try:
        data = youtube.captions().download(id=track["id"], tfmt="vtt").execute()
    except HttpError:
        return None

    vtt_path = out_dir / f"transcript.{lang}.vtt"
    vtt_path.write_bytes(data)
    return {"method": "youtube_official", "path": str(vtt_path), "lang": lang}


def _pick_lang(available: dict) -> str | None:
    for lang in PREFERRED_LANGS:
        if lang in available:
            return lang
    # fall back to any Spanish-prefixed variant, else None
    for lang in available:
        if lang.startswith("es"):
            return lang
    return None


def fetch_one(video_id: str, video_url: str) -> dict:
    """Metodos 2-3 (yt-dlp, sin OAuth). Returns
    {'method': 'yt_dlp_manual'|'yt_dlp_auto'|None, 'path': str|None, 'lang': str|None}."""
    out_dir = RAW_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    opts = {
        "quiet": True,
        "skip_download": True,
        "simulate": True,
        "js_runtimes": JS_RUNTIMES,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    for method, source in (("yt_dlp_manual", manual), ("yt_dlp_auto", auto)):
        lang = _pick_lang(source)
        if not lang:
            continue
        dl_opts = {
            "quiet": True,
            "skip_download": True,
            "js_runtimes": JS_RUNTIMES,
            "writesubtitles": method == "yt_dlp_manual",
            "writeautomaticsub": method == "yt_dlp_auto",
            "subtitleslangs": [lang],
            "subtitlesformat": "vtt",
            "outtmpl": str(out_dir / "transcript.%(ext)s"),
        }
        for attempt in range(4):
            try:
                with yt_dlp.YoutubeDL(dl_opts) as ydl:
                    ydl.download([video_url])
                break
            except yt_dlp.utils.DownloadError as exc:
                if "429" in str(exc) and attempt < 3:
                    backoff = 15 * (attempt + 1)
                    print(f"    429 rate limited, backing off {backoff}s...", flush=True)
                    time.sleep(backoff)
                    continue
                raise

        vtt_path = out_dir / f"transcript.{lang}.vtt"
        if vtt_path.exists():
            return {"method": method, "path": str(vtt_path), "lang": lang}

    return {"method": None, "path": None, "lang": None}


def fetch_with_cascade(video_id: str, video_url: str, channel_id: str) -> dict:
    """Cascada completa: 1) youtube_official (OAuth, si hay token para ese
    canal) -> 2-3) yt-dlp manual/auto -> si nada funciona, el caller marca
    TRANSCRIPT_PENDING para method 4 (Whisper)."""
    youtube = get_youtube_service_for_channel(channel_id)
    if youtube is not None:
        result = fetch_official_caption(youtube, video_id)
        if result is not None:
            return result
    return fetch_one(video_id, video_url)


def run_for_videos(video_ids: list[str], force: bool = False) -> dict:
    init_db()
    conn = get_connection()
    results = {
        "youtube_official": 0, "yt_dlp_manual": 0, "yt_dlp_auto": 0,
        "pending": 0, "failed": 0, "already_done": 0,
    }
    try:
        for video_id in video_ids:
            row = conn.execute(
                """SELECT yv.source_id, yv.url, yv.channel_id, s.processing_status
                   FROM youtube_videos yv JOIN sources s ON s.source_id = yv.source_id
                   WHERE yv.video_id = ?""",
                (video_id,),
            ).fetchone()
            if not row:
                print(f"  !! {video_id}: not in DB, skip discovery first", flush=True)
                continue
            if not force and row["processing_status"] not in ("METADATA_READY", "TRANSCRIPT_PENDING"):
                results["already_done"] += 1
                continue
            source_id, url, channel_id = row["source_id"], row["url"], row["channel_id"]
            try:
                result = fetch_with_cascade(video_id, url, channel_id)
                time.sleep(1.5)
            except Exception as exc:  # noqa: BLE001 -- one bad video must not abort the batch
                results["failed"] += 1
                conn.execute(
                    "INSERT INTO errors (source_id, stage, message) VALUES (?, 'transcript', ?)",
                    (source_id, str(exc)),
                )
                conn.commit()
                print(f"  !! {video_id}: error {exc}", flush=True)
                continue

            if result["method"] is None:
                results["pending"] += 1
                conn.execute(
                    "UPDATE sources SET processing_status='TRANSCRIPT_PENDING' WHERE source_id=?",
                    (source_id,),
                )
                print(f"  -- {video_id}: no captions (manual or auto) -- needs Whisper", flush=True)
            else:
                results[result["method"]] += 1
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
                print(f"  ok {video_id}: {result['method']} ({result['lang']})", flush=True)
            conn.commit()
    finally:
        conn.close()
    return results


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true", help="Run only for config/pilot_selection.json videos")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if already TRANSCRIPT_READY or later")
    parser.add_argument("video_ids", nargs="*")
    args = parser.parse_args()

    if args.pilot:
        pilot = json.loads((ROOT / "config" / "pilot_selection.json").read_text())
        ids = [v["video_id"] for v in pilot["videos"]]
    else:
        ids = args.video_ids

    print(f"Fetching captions for {len(ids)} video(s)...", flush=True)
    summary = run_for_videos(ids, force=args.force)
    print(summary)
