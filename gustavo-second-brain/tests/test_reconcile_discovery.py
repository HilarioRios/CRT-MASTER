import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
from reconcile_discovery import build_section, reconcile  # noqa: E402


def _seed(conn, video_id, source_id, channel_id, channel_name, availability):
    conn.execute(
        """INSERT INTO youtube_channels (channel_id, channel_name, channel_url)
           VALUES (?, ?, ?) ON CONFLICT(channel_id) DO NOTHING""",
        (channel_id, channel_name, f"https://youtube.com/{channel_id}"),
    )
    conn.execute(
        "INSERT INTO sources (source_id, source_type, channel) VALUES (?, 'youtube', ?)",
        (source_id, channel_name),
    )
    conn.execute(
        """INSERT INTO youtube_videos (video_id, source_id, channel_id, availability)
           VALUES (?, ?, ?, ?)""",
        (video_id, source_id, channel_id, availability),
    )


def test_reconcile_counts_distinct_videos_and_per_channel(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed(conn, "v1", "YT_A_v1", "UC_A", "CanalA", "available")
        _seed(conn, "v2", "YT_A_v2", "UC_A", "CanalA", "members_only")
        _seed(conn, "v3", "YT_B_v3", "UC_B", "CanalB", "public")
        conn.commit()

        result = reconcile(conn)

        assert result["total_distinct"] == 3
        by_channel = {r["channel_name"]: r["c"] for r in result["by_channel"]}
        assert by_channel == {"CanalA": 2, "CanalB": 1}
    finally:
        conn.close()


def test_reconcile_reports_zero_duplicates_and_zero_orphans_on_clean_data(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed(conn, "v1", "YT_A_v1", "UC_A", "CanalA", "available")
        conn.commit()

        result = reconcile(conn)

        assert result["duplicates"] == 0
        assert result["orphan_sources"] == 0
        assert result["orphan_videos"] == 0
    finally:
        conn.close()


def test_reconcile_detects_orphan_source_without_youtube_video_row(tmp_path):
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, channel) VALUES ('YT_ORPHAN', 'youtube', 'CanalA')"
        )
        conn.commit()

        result = reconcile(conn)

        assert result["orphan_sources"] == 1
    finally:
        conn.close()


def test_reconcile_breaks_down_by_availability_per_channel(tmp_path):
    db_path = tmp_path / "t4.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed(conn, "v1", "YT_A_v1", "UC_A", "CanalA", "available")
        _seed(conn, "v2", "YT_A_v2", "UC_A", "CanalA", "members_only")
        _seed(conn, "v3", "YT_A_v3", "UC_A", "CanalA", "members_only")
        conn.commit()

        result = reconcile(conn)

        availability_counts = {
            (r["channel_name"], r["availability"]): r["c"] for r in result["by_availability"]
        }
        assert availability_counts[("CanalA", "members_only")] == 2
        assert availability_counts[("CanalA", "available")] == 1
    finally:
        conn.close()


# --- build_section: narrative must be derived from live query results, ----
# --- not hardcoded prose (regression guard against staleness) -------------

def test_build_section_computes_gated_total_from_live_data_not_hardcoded(tmp_path):
    db_path = tmp_path / "t5.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed(conn, "v1", "YT_A_v1", "UC_A", "CanalA", "available")
        _seed(conn, "v2", "YT_A_v2", "UC_A", "CanalA", "members_only")
        _seed(conn, "v3", "YT_A_v3", "UC_A", "CanalA", "members_only")
        _seed(conn, "v4", "YT_A_v4", "UC_A", "CanalA", "members_only")
        conn.commit()

        section = build_section(conn)

        # 4 total, 3 gated (members_only) -> api_visible_total = 1.
        assert "COUNT(DISTINCT video_id) real en SQLite: 4" in section
        assert "**3** video(s) en esa situacion" in section
        assert "**1**, mientras que el total real en SQLite" in section
        assert "**4**." in section
        # No numero de un escenario distinto debe colarse (p.ej. de una corrida anterior real).
        assert "762" not in section
        assert "732" not in section
    finally:
        conn.close()


def test_build_section_handles_no_gated_content_case(tmp_path):
    db_path = tmp_path / "t6.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed(conn, "v1", "YT_A_v1", "UC_A", "CanalA", "available")
        _seed(conn, "v2", "YT_A_v2", "UC_A", "CanalA", "public")
        conn.commit()

        section = build_section(conn)

        assert "no hay actualmente ningun video con" in section
        assert "deberian" in section
        assert "coincidir (2)" in section
    finally:
        conn.close()


def test_build_section_canonical_total_always_matches_live_count(tmp_path):
    """The 'canonical figure' claim must always equal the live-computed
    total_distinct, by construction -- never a number left over from a
    previous run or a different dataset."""
    db_path = tmp_path / "t7.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        for i in range(5):
            _seed(conn, f"v{i}", f"YT_A_v{i}", "UC_A", "CanalA", "available")
        conn.commit()

        section = build_section(conn)
        r = reconcile(conn)

        assert f"**{r['total_distinct']} es la cifra canonica**" in section
        assert r["total_distinct"] == 5
    finally:
        conn.close()
