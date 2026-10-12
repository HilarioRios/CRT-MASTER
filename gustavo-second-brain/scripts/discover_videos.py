"""FASE 3 -- Discovery. Finds every video on both channels and stores metadata
in SQLite. Does NOT download video/audio/transcripts. Safe to re-run: videos
already at METADATA_READY are skipped (idempotent).

Uses yt-dlp instead of the YouTube Data API because no YOUTUBE_API_KEY is
configured yet (see .env.example). If YOUTUBE_API_KEY is later set, this
script still works unchanged -- it doesn't require the API.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import yt_dlp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHANNELS_PATH = ROOT / "config" / "channels.json"
REPORT_PATH = ROOT / "DISCOVERY_REPORT.md"


def load_channels() -> list[dict]:
    return json.loads(CHANNELS_PATH.read_text())["channels"]


JS_RUNTIMES = {"node": {}}  # node v22+ is already installed; avoids the deno dependency


def flat_list(channel_url: str, limit: int | None = None) -> dict:
    opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "skip_download": True,
        "js_runtimes": JS_RUNTIMES,
    }
    if limit:
        opts["playlistend"] = limit
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(channel_url, download=False)


def fetch_full_metadata(video_url: str) -> tuple[dict | None, str | None]:
    """Returns (metadata, None) on success, or (None, reason) on failure.
    reason is 'members_only' (paid channel membership required), or
    'unavailable' for anything else (deleted/private/geo-blocked/etc)."""
    opts = {"quiet": True, "skip_download": True, "simulate": True, "js_runtimes": JS_RUNTIMES}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(video_url, download=False), None
    except yt_dlp.utils.DownloadError as exc:
        reason = "members_only" if "channel's members" in str(exc) else "unavailable"
        return None, reason


def upsert_channel(conn, channel_id: str, name: str, url: str) -> None:
    conn.execute(
        """INSERT INTO youtube_channels (channel_id, channel_name, channel_url, last_synced_at)
           VALUES (?, ?, ?, datetime('now'))
           ON CONFLICT(channel_id) DO UPDATE SET
             channel_name=excluded.channel_name, last_synced_at=excluded.last_synced_at""",
        (channel_id, name, url),
    )


def already_discovered(conn, video_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM youtube_videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    return row is not None


def run(full_metadata: bool = True, sleep_between: float = 0.3, limit_per_channel: int | None = None) -> dict:
    init_db()
    conn = get_connection()
    summary = {}
    try:
        for ch in load_channels():
            key, url = ch["key"], ch["url"]
            print(f"[{key}] listing uploads from {url} ...", flush=True)
            info = flat_list(url, limit=limit_per_channel)
            channel_id = info.get("channel_id") or info.get("id")
            channel_name = info.get("channel") or info.get("title") or ch.get("name")
            upsert_channel(conn, channel_id, channel_name, url)
            conn.commit()

            entries = [e for e in info.get("entries", []) if e and e.get("id")]
            seen_ids = set()
            new_count = 0
            skipped_count = 0
            unavailable_count = 0
            members_only_count = 0
            failed_count = 0

            for e in entries:
                video_id = e["id"]
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)

                if already_discovered(conn, video_id):
                    skipped_count += 1
                    continue

                try:
                    video_url = e.get("url") or f"https://www.youtube.com/watch?v={video_id}"
                    title = e.get("title")
                    duration = e.get("duration")
                    thumbnail = None
                    if e.get("thumbnails"):
                        thumbnail = e["thumbnails"][-1].get("url")
                    published_at = None
                    description = None
                    availability = "available"

                    if full_metadata:
                        meta, fail_reason = fetch_full_metadata(video_url)
                        time.sleep(sleep_between)
                        if meta is None:
                            availability = fail_reason or "unavailable"
                            if availability == "members_only":
                                members_only_count += 1
                            else:
                                unavailable_count += 1
                        else:
                            title = meta.get("title", title)
                            duration = meta.get("duration", duration)
                            description = meta.get("description")
                            upload_date = meta.get("upload_date")  # YYYYMMDD
                            if upload_date:
                                published_at = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
                            availability = meta.get("availability") or "available"
                            thumbnail = meta.get("thumbnail", thumbnail)

                    source_id = f"YT_{key.upper()}_{video_id}"
                    gated = availability in ("members_only", "unavailable")
                    source_status = "FAILED" if gated else "METADATA_READY"
                    conn.execute(
                        """INSERT INTO sources
                            (source_id, source_type, visibility, original_title, original_url,
                             channel, published_at, processing_status)
                           VALUES (?, 'youtube', 'PUBLIC', ?, ?, ?, ?, ?)
                           ON CONFLICT(source_id) DO NOTHING""",
                        (source_id, title, video_url, channel_name, published_at, source_status),
                    )
                    conn.execute(
                        """INSERT INTO youtube_videos
                            (video_id, source_id, channel_id, title, url, published_at,
                             duration_sec, description, thumbnail_url, availability)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(video_id) DO NOTHING""",
                        (video_id, source_id, channel_id, title, video_url, published_at,
                         duration, description, thumbnail, availability),
                    )
                    if gated:
                        conn.execute(
                            "INSERT INTO errors (source_id, stage, message) VALUES (?, 'discovery', ?)",
                            (source_id, "Requires paid YouTube channel membership"
                                if availability == "members_only"
                                else "Video unavailable (private/deleted/geo-blocked)"),
                        )
                    conn.commit()
                    new_count += 1
                    if new_count % 25 == 0:
                        print(f"  ... {new_count} new videos discovered so far", flush=True)
                except Exception as exc:  # noqa: BLE001 -- one bad video must never abort discovery
                    conn.rollback()
                    failed_count += 1
                    conn.execute(
                        "INSERT INTO errors (source_id, stage, message) VALUES (?, 'discovery', ?)",
                        (f"YT_{key.upper()}_{video_id}", str(exc)),
                    )
                    conn.commit()
                    print(f"  !! error on {video_id}: {exc}", flush=True)

            summary[key] = {
                "channel_name": channel_name,
                "channel_id": channel_id,
                "found": len(seen_ids),
                "new": new_count,
                "already_known": skipped_count,
                "unavailable": unavailable_count,
                "members_only": members_only_count,
                "failed": failed_count,
            }
            print(f"[{key}] done: {summary[key]}", flush=True)
    finally:
        conn.close()

    write_report(summary)
    return summary


def retry_unavailable(sleep_between: float = 1.0) -> dict:
    """Re-attempt metadata fetch for videos marked 'unavailable' or
    'members_only'. Generic 'unavailable' marks can be transient (rate
    limiting during a bulk run); 'members_only' won't resolve without
    membership credentials but costs nothing to recheck occasionally."""
    init_db()
    conn = get_connection()
    retried = fixed = still_unavailable = 0
    try:
        rows = conn.execute(
            "SELECT video_id, source_id, url FROM youtube_videos WHERE availability IN ('unavailable', 'members_only')"
        ).fetchall()
        for row in rows:
            retried += 1
            meta, fail_reason = fetch_full_metadata(row["url"])
            time.sleep(sleep_between)
            if meta is None:
                conn.execute(
                    "UPDATE youtube_videos SET availability=? WHERE video_id=?",
                    (fail_reason or "unavailable", row["video_id"]),
                )
                conn.commit()
                still_unavailable += 1
                continue
            upload_date = meta.get("upload_date")
            published_at = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}" if upload_date else None
            conn.execute(
                """UPDATE youtube_videos SET title=?, duration_sec=?, description=?,
                   published_at=?, thumbnail_url=?, availability=? WHERE video_id=?""",
                (meta.get("title"), meta.get("duration"), meta.get("description"),
                 published_at, meta.get("thumbnail"), meta.get("availability") or "public",
                 row["video_id"]),
            )
            conn.execute(
                "UPDATE sources SET published_at=?, processing_status='METADATA_READY' WHERE source_id=?",
                (published_at, row["source_id"]),
            )
            conn.commit()
            fixed += 1
        print(f"retry_unavailable: {retried} reintentados, {fixed} recuperados, {still_unavailable} siguen sin disponibilidad", flush=True)
    finally:
        conn.close()
    return {"retried": retried, "fixed": fixed, "still_unavailable": still_unavailable}


def summary_from_db() -> dict:
    """Rebuild the per-channel summary dict (for the report) from current DB state."""
    conn = get_connection()
    summary = {}
    try:
        for ch in load_channels():
            key = ch["key"]
            row = conn.execute(
                """SELECT yc.channel_name AS channel_name,
                          COUNT(*) AS found,
                          SUM(CASE WHEN yv.availability='unavailable' THEN 1 ELSE 0 END) AS unavailable,
                          SUM(CASE WHEN yv.availability='members_only' THEN 1 ELSE 0 END) AS members_only
                   FROM youtube_videos yv
                   JOIN youtube_channels yc ON yc.channel_id = yv.channel_id
                   WHERE yv.source_id LIKE ?""",
                (f"YT_{key.upper()}_%",),
            ).fetchone()
            if row and row["found"]:
                summary[key] = {
                    "channel_name": row["channel_name"],
                    "found": row["found"],
                    "new": 0,
                    "already_known": row["found"],
                    "unavailable": row["unavailable"] or 0,
                    "members_only": row["members_only"] or 0,
                    "failed": 0,
                }
    finally:
        conn.close()
    return summary


def write_report(summary: dict) -> None:
    total_found = sum(s["found"] for s in summary.values())
    total_new = sum(s["new"] for s in summary.values())
    total_unavailable = sum(s["unavailable"] for s in summary.values())
    total_members_only = sum(s.get("members_only", 0) for s in summary.values())

    conn = get_connection()
    try:
        dup_row = conn.execute(
            "SELECT COUNT(*) - COUNT(DISTINCT video_id) AS dups FROM youtube_videos"
        ).fetchone()
        duplicates = dup_row["dups"] if dup_row else 0
        ready_row = conn.execute(
            "SELECT COUNT(*) AS c FROM sources WHERE processing_status != 'FAILED'"
        ).fetchone()
        total_ready = ready_row["c"]
    finally:
        conn.close()

    lines = ["# DISCOVERY_REPORT", ""]
    for key, s in summary.items():
        lines.append(f"## {s['channel_name']} ({key})")
        lines.append(f"- Videos encontrados: {s['found']}")
        lines.append(f"- Nuevos esta corrida: {s['new']}")
        lines.append(f"- Ya conocidos (idempotente, no reprocesados): {s['already_known']}")
        lines.append(f"- No disponibles (privado/borrado/geo-bloqueado): {s['unavailable']}")
        lines.append(f"- Solo para miembros del canal (requiere membresía paga, no accesible vía API/yt-dlp): {s.get('members_only', 0)}")
        lines.append(f"- Errores (en tabla `errors`, reintentables): {s.get('failed', 0)}")
        lines.append("")
    lines.append(f"**TOTAL encontrados: {total_found}**")
    lines.append("")
    lines.append(f"Duplicados (mismo video_id en más de un registro): {duplicates}")
    lines.append(f"No disponibles/privados: {total_unavailable}")
    lines.append(f"Solo-miembros (excluidos del pipeline automático): {total_members_only}")
    lines.append(f"Listos para procesar: {total_ready}")
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"\nDISCOVERY_REPORT.md escrito en {REPORT_PATH}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-per-channel", type=int, default=None)
    parser.add_argument("--no-full-metadata", action="store_true")
    parser.add_argument("--retry-unavailable", action="store_true",
                         help="Re-attempt metadata fetch for videos marked unavailable, then regenerate the report")
    args = parser.parse_args()
    if args.retry_unavailable:
        retry_unavailable()
        write_report(summary_from_db())
    else:
        run(full_metadata=not args.no_full_metadata, limit_per_channel=args.limit_per_channel)
