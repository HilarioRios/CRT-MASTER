"""Enumera las pestañas /shorts y /streams de cada canal via yt-dlp
(extraccion flat, metadata-only -- NO descarga video ni audio) para obtener
los video_id que YOUTUBE MISMO presenta en esas secciones. Esta es evidencia
mas fuerte que la heuristica de duracion/hashtag (ver classify_videos.py) y
tiene prioridad sobre ella.

Guarda el resultado en video_tab_membership (video_id, tab_type, channel_id)
-- no toca sources/youtube_videos directamente; classify_videos.py es quien
lee esta tabla y la aplica a la clasificacion final.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402
from discover_videos import flat_list, load_channels  # noqa: E402

TAB_TYPES = ("shorts", "streams")


def tab_url(handle: str, tab_type: str) -> str:
    """handle es '@AlgunHandle'. Se construye la URL del tab directamente
    desde el handle -- channel_page en channels.json NO es fiable para esto
    (p.ej. canal_02 lo guarda sin segmento final: 'youtube.com/@Handle', sin
    '/featured' ni '/videos', lo que rompería un rsplit del ultimo segmento)."""
    return f"https://www.youtube.com/{handle}/{tab_type}"


def list_tab_video_ids(handle: str, tab_type: str) -> list[str]:
    """READ-ONLY, metadata-only (yt-dlp extract_flat). No descarga nada."""
    url = tab_url(handle, tab_type)
    info = flat_list(url)
    return [e["id"] for e in info.get("entries", []) if e and e.get("id")]


def store_tab_membership(conn, video_ids: list[str], tab_type: str, channel_id: str) -> int:
    conn.executemany(
        """INSERT INTO video_tab_membership (video_id, tab_type, channel_id)
           VALUES (?, ?, ?)
           ON CONFLICT(video_id, tab_type) DO UPDATE SET
             channel_id=excluded.channel_id, discovered_at=datetime('now')""",
        [(vid, tab_type, channel_id) for vid in video_ids],
    )
    return len(video_ids)


def run() -> dict:
    init_db()
    conn = get_connection()
    summary: dict[str, dict[str, int]] = {}
    try:
        for ch in load_channels():
            key, handle = ch["key"], ch["handle"]
            summary[key] = {}
            for tab_type in TAB_TYPES:
                print(f"[{key}] listando /{tab_type} via yt-dlp ...", flush=True)
                video_ids = list_tab_video_ids(handle, tab_type)
                # channel_id: resuelto por discovery previo (ver youtube_channels);
                # si aun no existe el canal en DB, se guarda igual con NULL-safe fallback.
                row = conn.execute(
                    "SELECT channel_id FROM youtube_channels WHERE channel_url LIKE ?",
                    (f"%{ch['handle']}%",),
                ).fetchone()
                channel_id = row["channel_id"] if row else ""
                n = store_tab_membership(conn, video_ids, tab_type, channel_id)
                conn.commit()
                summary[key][tab_type] = n
                print(f"[{key}] /{tab_type}: {n} video_id encontrados", flush=True)
    finally:
        conn.close()
    return summary


if __name__ == "__main__":
    result = run()
    for key, counts in result.items():
        print(f"{key}: {counts}")
