import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection  # noqa: E402
from migrate_classification_schema import NEW_SOURCES_COLUMNS, existing_columns, migrate  # noqa: E402

# Mirrors the pre-migration `sources` table (what the real production DB
# looked like before the classification columns existed), so these tests
# exercise the actual ALTER-TABLE upgrade path instead of a fresh schema.sql
# table that already has the new columns built in.
LEGACY_SOURCES_SQL = """
CREATE TABLE sources (
    source_id           TEXT PRIMARY KEY,
    source_type         TEXT NOT NULL,
    visibility          TEXT NOT NULL DEFAULT 'PUBLIC',
    original_title       TEXT,
    original_url         TEXT,
    channel             TEXT,
    published_at         TEXT,
    transcript_source    TEXT,
    processing_version   TEXT,
    processing_status    TEXT NOT NULL DEFAULT 'DISCOVERED',
    raw_path             TEXT,
    processed_path        TEXT,
    drive_raw_url        TEXT,
    drive_processed_url  TEXT,
    content_hash         TEXT,
    error                TEXT,
    last_processed        TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _legacy_db(db_path: Path):
    conn = get_connection(db_path=db_path)
    conn.executescript(LEGACY_SOURCES_SQL)
    conn.commit()
    return conn


def test_migrate_adds_all_expected_columns(tmp_path):
    conn = _legacy_db(tmp_path / "test.sqlite")
    try:
        added = migrate(conn)
        expected_names = {name for name, _ in NEW_SOURCES_COLUMNS}
        assert set(added) == expected_names
        assert expected_names.issubset(existing_columns(conn, "sources"))
    finally:
        conn.close()


def test_migrate_is_idempotent_second_run_adds_nothing(tmp_path):
    conn = _legacy_db(tmp_path / "test2.sqlite")
    try:
        migrate(conn)
        second_run_added = migrate(conn)
        assert second_run_added == []
    finally:
        conn.close()


def test_migrate_backfills_existing_rows_with_defaults(tmp_path):
    conn = _legacy_db(tmp_path / "test3.sqlite")
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, original_url) VALUES (?, ?, ?)",
            ("YT_TEST_1", "youtube", "https://youtube.com/watch?v=test"),
        )
        conn.commit()

        migrate(conn)

        row = conn.execute(
            "SELECT content_format, include_in_knowledge_base, distribution_policy, "
            "temporal_status, potential_conflict FROM sources WHERE source_id=?",
            ("YT_TEST_1",),
        ).fetchone()
        assert row["content_format"] == "UNKNOWN"
        assert row["include_in_knowledge_base"] == 1
        assert row["distribution_policy"] == "ASK_BEFORE_SHARING"
        assert row["temporal_status"] == "UNKNOWN"
        assert row["potential_conflict"] == 0
    finally:
        conn.close()


def test_migrate_does_not_touch_the_default_production_db_path(tmp_path):
    """Regression test: migrate() must operate only on the connection it is
    given. Earlier it called init_db() with no args, which silently targeted
    the default production DB_PATH regardless of which conn was passed in."""
    import db as db_module

    prod_db_mtime_before = (
        db_module.DB_PATH.stat().st_mtime if db_module.DB_PATH.exists() else None
    )

    conn = _legacy_db(tmp_path / "test_isolated.sqlite")
    try:
        migrate(conn)
    finally:
        conn.close()

    prod_db_mtime_after = (
        db_module.DB_PATH.stat().st_mtime if db_module.DB_PATH.exists() else None
    )
    assert prod_db_mtime_before == prod_db_mtime_after


def test_new_join_tables_exist_after_migrate(tmp_path):
    conn = _legacy_db(tmp_path / "test4.sqlite")
    try:
        migrate(conn)
        tables = {
            r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"source_secondary_topics", "source_allowed_audience", "source_relations"}.issubset(tables)
    finally:
        conn.close()
