import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import build_obsidian_vault as bov  # noqa: E402


def _insert_source(conn, source_id, video_id, channel, title, status="DRIVE_SYNCED",
                    internal_classification=None, published_year=2024):
    conn.execute(
        "INSERT OR IGNORE INTO youtube_channels (channel_id, channel_name) VALUES ('chan1', ?)",
        (channel,),
    )
    conn.execute(
        """INSERT INTO sources
            (source_id, source_type, original_title, original_url, channel,
             content_format, include_in_knowledge_base, processing_status,
             internal_classification, published_year)
           VALUES (?, 'youtube', ?, ?, ?, 'LONG_FORM', 1, ?, ?, ?)""",
        (source_id, title, f"https://youtube.com/watch?v={video_id}", channel,
         status, internal_classification, published_year),
    )
    conn.execute(
        """INSERT INTO youtube_videos (video_id, source_id, channel_id, title, url)
           VALUES (?, ?, 'chan1', ?, ?)""",
        (video_id, source_id, title, f"https://youtube.com/watch?v={video_id}"),
    )


def test_sanitize_filename_strips_invalid_chars_and_keeps_video_id():
    name = bov.sanitize_filename('¡Título con / barras y "comillas"?', "abc123")
    assert "/" not in name
    assert '"' not in name
    assert "?" not in name
    assert "(abc123)" in name


def test_sanitize_filename_different_titles_same_prefix_stay_unique():
    a = bov.sanitize_filename("X" * 200, "vid1")
    b = bov.sanitize_filename("X" * 200, "vid2")
    assert a != b


def test_synced_source_without_local_transcript_file_gets_warning_not_invented_text(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(conn, "YT_A", "vidA", "CanalA", "Un video cualquiera")
    conn.commit()
    conn.close()

    result = bov.build(vault_path=tmp_path / "vault", db_path=db_path)
    assert result["notes_written"] == 1

    notes = list((tmp_path / "vault" / "CanalA").glob("*.md"))
    assert len(notes) == 1
    content = notes[0].read_text()
    assert "Transcript no encontrado localmente" in content
    assert "```" not in content  # no se abre un bloque de codigo vacio/inventado


def test_members_only_source_gets_stub_note_no_transcript(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(
        conn, "YT_B", "vidB", "CanalA", "Clase exclusiva",
        status="PENDING_ACCESS", internal_classification="YOUTUBE_MEMBERS_ONLY_EXCLUSIVE",
        published_year=None,
    )
    conn.commit()
    conn.close()

    bov.build(vault_path=tmp_path / "vault", db_path=db_path)

    notes = list((tmp_path / "vault" / "CanalA").glob("*.md"))
    content = notes[0].read_text()
    assert "YOUTUBE_MEMBERS_ONLY_EXCLUSIVE" in content
    assert "Sin texto inventado" in content
    assert "## Transcript" not in content


def test_channel_moc_and_root_index_are_generated(tmp_path):
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    _insert_source(conn, "YT_C", "vidC", "CanalB", "Video 1")
    _insert_source(conn, "YT_D", "vidD", "CanalB", "Video 2")
    conn.commit()
    conn.close()

    vault = tmp_path / "vault"
    result = bov.build(vault_path=vault, db_path=db_path)

    assert result["channels"] == 1
    assert (vault / "CanalB.md").exists()
    assert (vault / "00_Index.md").exists()
    assert "[[CanalB]]" in (vault / "00_Index.md").read_text()


def test_this_run_never_touches_the_default_production_db_path(tmp_path):
    import db as db_module

    prod_mtime_before = (
        db_module.DB_PATH.stat().st_mtime if db_module.DB_PATH.exists() else None
    )

    db_path = tmp_path / "isolated.sqlite"
    init_db(db_path=db_path)
    bov.build(vault_path=tmp_path / "vault", db_path=db_path)

    prod_mtime_after = (
        db_module.DB_PATH.stat().st_mtime if db_module.DB_PATH.exists() else None
    )
    assert prod_mtime_before == prod_mtime_after
