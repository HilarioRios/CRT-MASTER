import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import discover_shorts_live_tabs as tabs  # noqa: E402


def test_tab_url_builds_from_handle_directly():
    assert tabs.tab_url("@MentoTradingClub", "shorts") == "https://www.youtube.com/@MentoTradingClub/shorts"
    assert tabs.tab_url("@Gustavom.Trader", "streams") == "https://www.youtube.com/@Gustavom.Trader/streams"


def test_list_tab_video_ids_extracts_ids_from_flat_entries():
    fake_info = {
        "entries": [
            {"id": "a1", "title": "x"},
            {"id": "a2", "title": "y"},
            None,  # yt-dlp can yield None entries for unresolved items
            {"title": "sin id"},  # malformed entry, no 'id' key
        ]
    }
    with patch.object(tabs, "flat_list", return_value=fake_info) as flat_list_mock:
        result = tabs.list_tab_video_ids("@Handle", "shorts")

    assert result == ["a1", "a2"]
    flat_list_mock.assert_called_once_with("https://www.youtube.com/@Handle/shorts")


def test_list_tab_video_ids_handles_no_entries():
    with patch.object(tabs, "flat_list", return_value={}):
        assert tabs.list_tab_video_ids("@Handle", "streams") == []


def test_store_tab_membership_inserts_rows(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        n = tabs.store_tab_membership(conn, ["v1", "v2", "v3"], "shorts", "UC_X")
        conn.commit()
        assert n == 3
        rows = conn.execute(
            "SELECT video_id, tab_type, channel_id FROM video_tab_membership ORDER BY video_id"
        ).fetchall()
        assert [dict(r) for r in rows] == [
            {"video_id": "v1", "tab_type": "shorts", "channel_id": "UC_X"},
            {"video_id": "v2", "tab_type": "shorts", "channel_id": "UC_X"},
            {"video_id": "v3", "tab_type": "shorts", "channel_id": "UC_X"},
        ]
    finally:
        conn.close()


def test_store_tab_membership_is_idempotent_on_rerun(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        tabs.store_tab_membership(conn, ["v1"], "shorts", "UC_X")
        conn.commit()
        tabs.store_tab_membership(conn, ["v1"], "shorts", "UC_X")
        conn.commit()
        rows = conn.execute("SELECT COUNT(*) c FROM video_tab_membership").fetchone()
        assert rows["c"] == 1
    finally:
        conn.close()


def test_a_video_can_appear_in_both_shorts_and_streams_tab_types_as_distinct_rows(tmp_path):
    """shorts and streams are different tab_type values -- the composite PK
    (video_id, tab_type) must allow the same video_id under two tab_types
    without clobbering each other (even if that combination is atypical)."""
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        tabs.store_tab_membership(conn, ["v1"], "shorts", "UC_X")
        tabs.store_tab_membership(conn, ["v1"], "streams", "UC_X")
        conn.commit()
        rows = conn.execute(
            "SELECT tab_type FROM video_tab_membership WHERE video_id='v1' ORDER BY tab_type"
        ).fetchall()
        assert [r["tab_type"] for r in rows] == ["shorts", "streams"]
    finally:
        conn.close()
