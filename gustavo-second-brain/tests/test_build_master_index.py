import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import build_master_index as bmi  # noqa: E402


def _insert_source(conn, source_id, channel, original_url, privacy,
                    drive_raw_url=None, drive_processed_url=None):
    conn.execute(
        """INSERT INTO sources
            (source_id, source_type, original_title, original_url, channel,
             content_format, youtube_privacy_status, include_in_knowledge_base,
             drive_raw_url, drive_processed_url)
           VALUES (?, 'youtube', ?, ?, ?, 'LONG_FORM', ?, 1, ?, ?)""",
        (source_id, f"Titulo {source_id}", original_url, channel, privacy,
         drive_raw_url, drive_processed_url),
    )


def _rows(tmp_path, db_path, name="out.csv"):
    out_path = tmp_path / name
    n = bmi.build(db_path=db_path, out_path=out_path)
    with out_path.open(newline="", encoding="utf-8") as f:
        return n, list(csv.DictReader(f))


def test_public_source_keeps_its_url(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(conn, "YT_PUB", "CanalA", "https://youtube.com/watch?v=abc", "PUBLIC")
    conn.commit()
    conn.close()

    n, rows = _rows(tmp_path, db_path)

    assert n == 1
    assert rows[0]["original_url"] == "https://youtube.com/watch?v=abc"


def test_private_source_url_is_blanked_in_csv(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(conn, "YT_PRIV", "CanalA", "https://youtube.com/watch?v=secret", "PRIVATE")
    conn.commit()
    conn.close()

    n, rows = _rows(tmp_path, db_path)

    assert rows[0]["original_url"] == ""
    assert "secret" not in str(rows[0])


def test_unlisted_source_url_is_blanked_in_csv(tmp_path):
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(conn, "YT_UNL", "CanalA", "https://youtube.com/watch?v=hidden", "UNLISTED")
    conn.commit()
    conn.close()

    _, rows = _rows(tmp_path, db_path)

    assert rows[0]["original_url"] == ""


def test_unknown_privacy_source_url_is_blanked_too(tmp_path):
    """Conservative default: if privacy was never resolved, treat as non-public."""
    db_path = tmp_path / "t4.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(conn, "YT_UNK", "CanalA", "https://youtube.com/watch?v=unknown", None)
    conn.commit()
    conn.close()

    _, rows = _rows(tmp_path, db_path)

    assert rows[0]["original_url"] == ""


def test_private_source_drive_urls_are_also_blanked(tmp_path):
    db_path = tmp_path / "t5.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(
        conn, "YT_PRIV2", "CanalA", "https://youtube.com/watch?v=secret2", "PRIVATE",
        drive_raw_url="https://drive.google.com/raw-secret",
        drive_processed_url="https://drive.google.com/processed-secret",
    )
    conn.commit()
    conn.close()

    _, rows = _rows(tmp_path, db_path)

    assert rows[0]["drive_raw_url"] == ""
    assert rows[0]["drive_processed_url"] == ""


def test_this_run_never_touches_the_default_production_db_path(tmp_path):
    """Regression guard: build() must accept an explicit db_path and never
    fall back to the real production DB_PATH when one is given."""
    import db as db_module

    prod_mtime_before = (
        db_module.DB_PATH.stat().st_mtime if db_module.DB_PATH.exists() else None
    )

    db_path = tmp_path / "isolated.sqlite"
    init_db(db_path=db_path)
    _rows(tmp_path, db_path, name="isolated_out.csv")

    prod_mtime_after = (
        db_module.DB_PATH.stat().st_mtime if db_module.DB_PATH.exists() else None
    )
    assert prod_mtime_before == prod_mtime_after
