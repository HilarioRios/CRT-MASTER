import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import init_db, get_connection  # noqa: E402

EXPECTED_TABLES = {
    "sources",
    "youtube_channels",
    "youtube_videos",
    "transcripts",
    "chunks",
    "processing_runs",
    "errors",
    "drive_sync",
}


def test_init_db_creates_expected_tables(tmp_path):
    db_path = tmp_path / "test.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {r["name"] for r in rows}
        assert EXPECTED_TABLES.issubset(table_names)
    finally:
        conn.close()


def test_sources_insert_and_default_status(tmp_path):
    db_path = tmp_path / "test2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, original_url) VALUES (?, ?, ?)",
            ("YT_TEST_1", "youtube", "https://youtube.com/watch?v=test"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT processing_status, visibility FROM sources WHERE source_id = ?",
            ("YT_TEST_1",),
        ).fetchone()
        assert row["processing_status"] == "DISCOVERED"
        assert row["visibility"] == "PUBLIC"
    finally:
        conn.close()
