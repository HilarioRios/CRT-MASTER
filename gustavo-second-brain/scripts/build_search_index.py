"""FASE 17 -- Build the SQLite FTS5 full-text index.

Rebuilds chunks_search from the `chunks` table. The indexed copy of the text
has known ASR jargon mistranscriptions corrected (config/term_corrections.json)
so that searching for the real term (e.g. "bias") finds chunks where
YouTube's auto-caption misheard it (e.g. "vallas", "bías"). The verbatim
chunks.text is never modified -- citations/display always show what was
actually captioned.

Semantic (embedding) search is a separate, additive step (not yet built
for the pilot -- FTS5 alone is enough to validate the quality-gate
questions; see PILOT_REPORT.md).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_connection, init_db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORRECTIONS_PATH = ROOT / "config" / "term_corrections.json"


def load_corrections() -> list[tuple[re.Pattern, str]]:
    data = json.loads(CORRECTIONS_PATH.read_text())
    patterns = []
    for entry in data["corrections"]:
        pattern = re.compile(rf"\b{re.escape(entry['wrong'])}\b", re.IGNORECASE)
        patterns.append((pattern, entry["right"]))
    return patterns


def apply_corrections(text: str, patterns: list[tuple[re.Pattern, str]]) -> str:
    for pattern, right in patterns:
        text = pattern.sub(right, text)
    return text


def rebuild_index() -> int:
    init_db()
    patterns = load_corrections()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM chunks_search")
        rows = conn.execute("SELECT chunk_id, text FROM chunks").fetchall()
        for row in rows:
            corrected = apply_corrections(row["text"], patterns)
            conn.execute(
                "INSERT INTO chunks_search (chunk_id, text) VALUES (?, ?)",
                (row["chunk_id"], corrected),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    n = rebuild_index()
    print(f"Indexed {n} chunks into chunks_search (with term corrections applied).")
