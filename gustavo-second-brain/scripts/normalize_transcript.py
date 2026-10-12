"""FASE 6 (mechanical part) -- Normalize a raw transcript into a clean,
timestamped plain-text version + machine-readable segment JSON. Does NOT
summarize, invent, or alter meaning: only cleans caption artifacts.

The semantic enrichment (resumen, conceptos, reglas, ideas clave) is NOT
done here -- that requires genuine reading/understanding and is done by
the orchestrating agent directly (see docs/ for the pilot writeup), never
by an unsupervised script, to keep the anti-hallucination guarantee
checkable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vtt_parser import parse_vtt  # noqa: E402
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "youtube"
PROCESSED_DIR = ROOT / "data" / "processed" / "youtube"


def _fmt_ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def normalize_video(video_id: str) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT yv.source_id, t.raw_file_path FROM youtube_videos yv
               JOIN transcripts t ON t.source_id = yv.source_id
               WHERE yv.video_id = ?""",
            (video_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError(f"{video_id}: no transcript row found -- run fetch_captions.py first")

    raw_path = Path(row["raw_file_path"])
    content = raw_path.read_text()
    segments = parse_vtt(content)

    out_dir = PROCESSED_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean timestamped plain text (one line per caption segment)
    lines = [f"[{_fmt_ts(s.start_sec)}]\n{s.text}\n" for s in segments]
    (out_dir / "transcript_clean.txt").write_text("\n".join(lines))

    # Machine-readable segments
    seg_json = [
        {"start_sec": round(s.start_sec, 2), "end_sec": round(s.end_sec, 2), "text": s.text}
        for s in segments
    ]
    (out_dir / "transcript_segments.json").write_text(json.dumps(seg_json, ensure_ascii=False, indent=2))

    return {
        "video_id": video_id,
        "source_id": row["source_id"],
        "segment_count": len(segments),
        "duration_sec": segments[-1].end_sec if segments else 0,
        "out_dir": str(out_dir),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("video_ids", nargs="*")
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()

    if args.pilot:
        pilot = json.loads((ROOT / "config" / "pilot_selection.json").read_text())
        ids = [v["video_id"] for v in pilot["videos"]]
    else:
        ids = args.video_ids

    init_db()
    for vid in ids:
        result = normalize_video(vid)
        print(result)
