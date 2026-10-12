"""One-shot migration: adds the classification/governance columns (see
database/schema.sql) to an existing `sources` table, and creates the new
join tables (source_secondary_topics, source_allowed_audience,
source_relations) if missing.

Idempotent and safe to re-run: checks `pragma table_info('sources')` before
adding each column, so it never raises "duplicate column name". This is
deliberately a separate script from schema.sql -- schema.sql's CREATE TABLE
IF NOT EXISTS statements are no-ops against an already-created `sources`
table, so a fresh install gets the new columns from schema.sql, while an
existing database (like this project's) needs this ALTER-based migration.

Adding a column with a constant DEFAULT backfills every existing row with
that default value -- this is the "migrate the 732 records" step; actual
per-row classification happens separately in classify_videos.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import SCHEMA_PATH, get_connection  # noqa: E402

# (column_name, full column definition to use in ALTER TABLE ... ADD COLUMN)
NEW_SOURCES_COLUMNS = [
    ("content_format", "TEXT NOT NULL DEFAULT 'UNKNOWN'"),
    ("youtube_privacy_status", "TEXT"),
    ("include_in_knowledge_base", "INTEGER NOT NULL DEFAULT 1"),
    ("primary_content_type", "TEXT"),
    ("distribution_policy", "TEXT NOT NULL DEFAULT 'ASK_BEFORE_SHARING'"),
    ("internal_classification", "TEXT"),
    ("published_year", "INTEGER"),
    ("temporal_status", "TEXT NOT NULL DEFAULT 'UNKNOWN'"),
    ("potential_conflict", "INTEGER NOT NULL DEFAULT 0"),
    ("source_authority_type", "TEXT"),
    ("derived_from_source_id", "TEXT REFERENCES sources(source_id)"),
    ("possible_parent_video_id", "TEXT"),
    ("parent_match_confidence", "REAL"),
]


def existing_columns(conn, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def migrate(conn) -> list[str]:
    """Returns the list of column names actually added (empty if already migrated).
    Operates entirely on the given `conn` -- never opens a second connection
    to the default production DB path, so this is safe to call against a
    test or alternate database."""
    # ALTER the missing sources columns first: schema.sql's CREATE INDEX
    # statements reference content_format/include_in_knowledge_base, and
    # would fail against a pre-migration table where those don't exist yet.
    current = existing_columns(conn, "sources")
    added = []
    for name, definition in NEW_SOURCES_COLUMNS:
        if name in current:
            continue
        conn.execute(f"ALTER TABLE sources ADD COLUMN {name} {definition}")
        added.append(name)

    # Now safe to run schema.sql: creates source_secondary_topics /
    # source_allowed_audience / source_relations and the new indexes if
    # missing -- all idempotent (CREATE ... IF NOT EXISTS).
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    return added


def run() -> list[str]:
    conn = get_connection()
    try:
        return migrate(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    added_columns = run()
    if added_columns:
        print(f"Migracion aplicada. Columnas agregadas a sources: {', '.join(added_columns)}")
    else:
        print("Ya estaba migrado -- ninguna columna nueva que agregar.")
