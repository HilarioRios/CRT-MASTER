"""FASE 3 (API) -- Discovery via la YouTube Data API v3 oficial (YOUTUBE_API_KEY),
en vez de yt-dlp (ver discover_videos.py). Resuelve el channel_id real de cada
canal desde su @handle, enumera TODOS los videos de su uploads playlist, y
guarda metadata completa en SQLite. Idempotente: un video_id ya conocido se
salta (mismo esquema y ON CONFLICT DO NOTHING que discover_videos.py).

Solo hace llamadas READ-ONLY (channels().list, playlistItems().list,
videos().list). NO descarga transcripts, NO corre Whisper, NO genera
embeddings.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402
from discover_videos import (  # noqa: E402
    already_discovered,
    load_channels,
    summary_from_db,
    upsert_channel,
    write_report,
)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DURATION_RE = re.compile(
    r"P(?:\d+Y)?(?:\d+M)?(?:\d+D)?T?(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?"
)


def parse_iso8601_duration(value: str | None) -> int:
    """Convierte una duracion ISO 8601 (ej. 'PT1H2M10S') a segundos. Devuelve
    0 si viene vacia o no matchea (p.ej. streams en vivo sin duracion fija)."""
    if not value:
        return 0
    match = DURATION_RE.fullmatch(value)
    if not match:
        return 0
    h = int(match.group("h") or 0)
    m = int(match.group("m") or 0)
    s = int(match.group("s") or 0)
    return h * 3600 + m * 60 + s


def chunked(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def resolve_channel(youtube, handle: str) -> dict:
    """READ-ONLY. Resuelve channel_id + uploads playlist id a partir del @handle."""
    resp = youtube.channels().list(
        part="snippet,contentDetails,statistics", forHandle=handle
    ).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"No se pudo resolver el canal para el handle {handle}")
    item = items[0]
    return {
        "channel_id": item["id"],
        "channel_name": item["snippet"]["title"],
        "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "video_count_reported": int(item.get("statistics", {}).get("videoCount", 0)),
    }


def list_all_uploaded_video_ids(youtube, uploads_playlist_id: str) -> list[str]:
    """READ-ONLY. Pagina playlistItems().list hasta agotar nextPageToken."""
    video_ids: list[str] = []
    page_token = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in resp.get("items", []):
            vid = item.get("contentDetails", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def fetch_videos_metadata(youtube, video_ids: list[str]) -> dict[str, dict]:
    """READ-ONLY. Trae metadata completa en lotes de 50. Un video_id ausente
    en la respuesta esta borrado o es completamente privado."""
    metadata: dict[str, dict] = {}
    for batch in chunked(video_ids, 50):
        if not batch:
            continue
        resp = youtube.videos().list(
            part="snippet,contentDetails,status", id=",".join(batch)
        ).execute()
        for item in resp.get("items", []):
            metadata[item["id"]] = item
    return metadata


def _thumbnail_url(snippet: dict) -> str | None:
    thumbs = snippet.get("thumbnails", {})
    best = thumbs.get("maxres") or thumbs.get("high") or thumbs.get("default") or {}
    return best.get("url")


def run(limit_per_channel: int | None = None) -> dict:
    api_key = os.environ["YOUTUBE_API_KEY"]
    youtube = build("youtube", "v3", developerKey=api_key)

    init_db()
    conn = get_connection()
    summary = {}
    try:
        for ch in load_channels():
            key, handle = ch["key"], ch["handle"]
            print(f"[{key}] resolviendo {handle} via YouTube Data API ...", flush=True)
            info = resolve_channel(youtube, handle)
            upsert_channel(conn, info["channel_id"], info["channel_name"], ch["channel_page"])
            conn.execute(
                "UPDATE youtube_channels SET uploads_playlist_id=? WHERE channel_id=?",
                (info["uploads_playlist_id"], info["channel_id"]),
            )
            conn.commit()
            print(
                f"  channel_id={info['channel_id']} "
                f"videoCount(reportado por API)={info['video_count_reported']}",
                flush=True,
            )

            video_ids = list_all_uploaded_video_ids(youtube, info["uploads_playlist_id"])
            if limit_per_channel:
                video_ids = video_ids[:limit_per_channel]

            already_known = {vid for vid in video_ids if already_discovered(conn, vid)}
            to_fetch = [vid for vid in video_ids if vid not in already_known]
            metadata = fetch_videos_metadata(youtube, to_fetch)

            new_count = unavailable_count = 0
            for vid in to_fetch:
                meta = metadata.get(vid)
                source_id = f"YT_{key.upper()}_{vid}"
                video_url = f"https://www.youtube.com/watch?v={vid}"

                if meta is None:
                    conn.execute(
                        """INSERT INTO sources
                            (source_id, source_type, visibility, original_url, channel, processing_status)
                           VALUES (?, 'youtube', 'PUBLIC', ?, ?, 'FAILED')
                           ON CONFLICT(source_id) DO NOTHING""",
                        (source_id, video_url, info["channel_name"]),
                    )
                    conn.execute(
                        """INSERT INTO youtube_videos (video_id, source_id, channel_id, url, availability)
                           VALUES (?, ?, ?, ?, 'unavailable')
                           ON CONFLICT(video_id) DO NOTHING""",
                        (vid, source_id, info["channel_id"], video_url),
                    )
                    conn.execute(
                        "INSERT INTO errors (source_id, stage, message) VALUES (?, 'discovery_api', ?)",
                        (source_id, "En uploads playlist pero ausente en videos().list (borrado/privado)"),
                    )
                    unavailable_count += 1
                    conn.commit()
                    continue

                snippet = meta.get("snippet", {})
                content = meta.get("contentDetails", {})
                title = snippet.get("title")
                description = snippet.get("description")
                published_at = (snippet.get("publishedAt") or "")[:10] or None
                duration_sec = parse_iso8601_duration(content.get("duration"))
                thumbnail = _thumbnail_url(snippet)

                conn.execute(
                    """INSERT INTO sources
                        (source_id, source_type, visibility, original_title, original_url,
                         channel, published_at, processing_status)
                       VALUES (?, 'youtube', 'PUBLIC', ?, ?, ?, ?, 'METADATA_READY')
                       ON CONFLICT(source_id) DO NOTHING""",
                    (source_id, title, video_url, info["channel_name"], published_at),
                )
                conn.execute(
                    """INSERT INTO youtube_videos
                        (video_id, source_id, channel_id, title, url, published_at,
                         duration_sec, description, thumbnail_url, availability)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')
                       ON CONFLICT(video_id) DO NOTHING""",
                    (vid, source_id, info["channel_id"], title, video_url, published_at,
                     duration_sec, description, thumbnail),
                )
                conn.commit()
                new_count += 1

            summary[key] = {
                "channel_name": info["channel_name"],
                "channel_id": info["channel_id"],
                "found": len(video_ids),
                "new": new_count,
                "already_known": len(already_known),
                "unavailable": unavailable_count,
                "members_only": 0,
                "failed": 0,
            }
            print(f"[{key}] done: {summary[key]}", flush=True)
    finally:
        conn.close()

    write_report(summary)
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-per-channel", type=int, default=None)
    args = parser.parse_args()
    run(limit_per_channel=args.limit_per_channel)
