"""FASE 7 -- Chunking. Groups consecutive transcript segments into
semantic chunks of ~60-120 seconds (config/settings.yaml), with a small
overlap so context isn't lost at boundaries. Purely mechanical: never
alters the text, just groups it.

Writes to:
 - database `chunks` table (+ chunks_fts index)
 - data/chunks/youtube/<video_id>.json (machine-readable, for inspection
   and for sync_drive.py later)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed" / "youtube"
CHUNKS_DIR = ROOT / "data" / "chunks" / "youtube"
SETTINGS = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())

TARGET_MIN = SETTINGS["chunking"]["target_seconds_min"]
TARGET_MAX = SETTINGS["chunking"]["target_seconds_max"]
OVERLAP = SETTINGS["chunking"]["overlap_seconds"]


def load_segments(video_id: str) -> list[dict]:
    path = PROCESSED_DIR / video_id / "transcript_segments.json"
    return json.loads(path.read_text())


def build_chunks(segments: list[dict], video_id: str) -> list[dict]:
    if not segments:
        return []

    chunks = []
    i = 0
    n = len(segments)
    chunk_index = 0

    while i < n:
        start_sec = segments[i]["start_sec"]
        texts = []
        j = i
        end_sec = start_sec
        while j < n:
            seg = segments[j]
            texts.append(seg["text"])
            end_sec = seg["end_sec"]
            duration = end_sec - start_sec
            j += 1
            if duration >= TARGET_MIN and (duration >= TARGET_MAX or j >= n):
                break
            if duration >= TARGET_MAX:
                break

        chunk_index += 1
        chunks.append({
            "chunk_id": f"YT_{video_id}_{chunk_index:03d}",
            "video_id": video_id,
            "start_sec": round(start_sec, 2),
            "end_sec": round(end_sec, 2),
            "text": " ".join(texts).strip(),
        })

        if j >= n:
            break

        # start next chunk `OVERLAP` seconds before this one ended, by
        # walking back from j until we cross that boundary (avoids
        # cutting a chunk off mid-sentence at the same instant every time)
        overlap_target = end_sec - OVERLAP
        k = j - 1
        while k > i and segments[k]["start_sec"] > overlap_target:
            k -= 1
        i = max(k, i + 1)  # always make progress

    return chunks


def run_for_video(video_id: str, source_id: str, title: str, channel: str, url: str) -> int:
    segments = load_segments(video_id)
    chunks = build_chunks(segments, video_id)

    out_dir = CHUNKS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    enriched = []
    for c in chunks:
        deep_link = f"{url}&t={int(c['start_sec'])}s"
        enriched.append({
            **c,
            "source_id": source_id,
            "title": title,
            "channel": channel,
            "topics": [],
            "source_url": url,
            "deep_link": deep_link,
        })
    (out_dir / f"{video_id}.json").write_text(json.dumps(enriched, ensure_ascii=False, indent=2))

    conn = get_connection()
    try:
        conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
        for c in enriched:
            conn.execute(
                """INSERT INTO chunks (chunk_id, source_id, start_sec, end_sec, topic, text, source_url, deep_link)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["chunk_id"], source_id, c["start_sec"], c["end_sec"], None, c["text"], url, deep_link),
            )
        conn.execute("UPDATE sources SET processing_status='CHUNKED' WHERE source_id=?", (source_id,))
        conn.commit()
    finally:
        conn.close()

    return len(enriched)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("video_ids", nargs="*")
    args = parser.parse_args()

    init_db()
    conn = get_connection()
    try:
        if args.pilot:
            pilot = json.loads((ROOT / "config" / "pilot_selection.json").read_text())
            ids = [v["video_id"] for v in pilot["videos"]]
        else:
            ids = args.video_ids

        for video_id in ids:
            row = conn.execute(
                """SELECT yv.source_id, yv.title, s.channel, yv.url
                   FROM youtube_videos yv JOIN sources s ON s.source_id = yv.source_id
                   WHERE yv.video_id = ?""",
                (video_id,),
            ).fetchone()
            if not row:
                print(f"  !! {video_id}: not found in DB")
                continue
            count = run_for_video(video_id, row["source_id"], row["title"], row["channel"], row["url"])
            print(f"{video_id}: {count} chunks")
    finally:
        conn.close()
