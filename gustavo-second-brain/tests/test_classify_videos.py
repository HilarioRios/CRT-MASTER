import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import classify_videos as clf  # noqa: E402


# --- content_format -------------------------------------------------------

def test_live_flag_wins_over_everything_else():
    assert clf.detect_content_format(45, "cualquier titulo #shorts", None, is_live=True) == "LIVE"


def test_duration_over_3min_is_long_form_even_with_shorts_hashtag():
    # YouTube Shorts cap at 3 minutes (180s); anything longer cannot be a Short
    # even if mistakenly hashtagged -- treat the tag as noise, not signal.
    assert clf.detect_content_format(200, "mira esto #shorts", None, is_live=False) == "LONG_FORM"


def test_short_duration_with_shorts_hashtag_in_title_is_short():
    assert clf.detect_content_format(45, "Tip rapido #shorts", None, is_live=False) == "SHORT"


def test_short_duration_with_shorts_hashtag_in_description_is_short():
    assert clf.detect_content_format(45, "Tip rapido", "mas contenido #Shorts aqui", is_live=False) == "SHORT"


def test_short_duration_without_hashtag_is_unknown_not_short():
    """Explicit requirement: duration alone must never produce a false-positive SHORT."""
    assert clf.detect_content_format(45, "Clase completa de hoy", None, is_live=False) == "UNKNOWN"


def test_duration_between_1_and_3_min_without_hashtag_is_unknown_not_long_form():
    """Explicit requirement: absence of #shorts must never be used as
    positive evidence for LONG_FORM either -- it's absence of evidence."""
    assert clf.detect_content_format(120, "Analisis rapido", None, is_live=False) == "UNKNOWN"


def test_missing_duration_is_unknown():
    assert clf.detect_content_format(None, "titulo cualquiera", None, is_live=False) == "UNKNOWN"


def test_hashtag_matching_is_case_insensitive():
    assert clf.detect_content_format(30, "TIP #SHORTS", None, is_live=False) == "SHORT"


# --- /shorts and /streams tab evidence (highest priority) ------------------

def test_shorts_tab_membership_wins_over_long_duration():
    """/shorts tab evidence outranks everything, including a duration that
    looks inconsistent with being a Short -- the discrepancy gets logged in
    the report, not silently used to override the tab's own evidence."""
    assert clf.detect_content_format(
        600, "Titulo cualquiera", None, is_live=False, is_short_tab=True
    ) == "SHORT"


def test_shorts_tab_membership_wins_with_no_hashtag_and_no_duration():
    assert clf.detect_content_format(
        None, "Titulo cualquiera", None, is_live=False, is_short_tab=True
    ) == "SHORT"


def test_shorts_tab_membership_wins_over_live_flag():
    """A video can't really be both, but if both signals somehow fire,
    the explicit /shorts tab membership (more concrete, directly observed)
    takes priority over the is_live signal."""
    assert clf.detect_content_format(
        45, "t", None, is_live=True, is_short_tab=True
    ) == "SHORT"


def test_shorts_tab_membership_wins_over_streams_tab_membership_too():
    """Same conflict, but both signals coming from tab evidence (is_short_tab
    AND is_live_tab both True) rather than one tab + one API flag -- the
    code checks is_short_tab first and returns before is_live_tab is ever
    consulted, so SHORT must still win."""
    assert clf.detect_content_format(
        45, "t", None, is_live=False, is_short_tab=True, is_live_tab=True
    ) == "SHORT"


def test_streams_tab_membership_marks_live():
    assert clf.detect_content_format(
        3600, "Sesion en vivo", None, is_live=False, is_live_tab=True
    ) == "LIVE"


def test_streams_tab_membership_wins_over_shorts_hashtag():
    assert clf.detect_content_format(
        45, "clip del vivo #shorts", None, is_live=False, is_live_tab=True
    ) == "LIVE"


def test_no_tab_evidence_falls_back_to_heuristic():
    assert clf.detect_content_format(
        45, "Tip #shorts", None, is_live=False, is_short_tab=False, is_live_tab=False
    ) == "SHORT"


# --- privacy_to_distribution ----------------------------------------------

def test_public_privacy_maps_to_shareable_with_no_internal_classification():
    assert clf.privacy_to_distribution("PUBLIC") == ("SHAREABLE", None)


def test_private_privacy_maps_to_ask_before_sharing_and_unclassified():
    assert clf.privacy_to_distribution("PRIVATE") == ("ASK_BEFORE_SHARING", "PRIVATE_UNCLASSIFIED")


def test_unlisted_privacy_maps_to_ask_before_sharing_and_unclassified():
    assert clf.privacy_to_distribution("UNLISTED") == ("ASK_BEFORE_SHARING", "PRIVATE_UNCLASSIFIED")


def test_unknown_privacy_maps_to_ask_before_sharing_without_guessing_classification():
    assert clf.privacy_to_distribution(None) == ("ASK_BEFORE_SHARING", None)


# --- audience_for_privacy ---------------------------------------------------

def test_public_privacy_allows_all_audiences():
    assert clf.audience_for_privacy("PUBLIC") == ["PUBLIC", "STUDENT", "VIP_STUDENT", "TEAM"]


def test_private_or_unlisted_privacy_restricts_to_team_only():
    assert clf.audience_for_privacy("PRIVATE") == ["TEAM"]
    assert clf.audience_for_privacy("UNLISTED") == ["TEAM"]


def test_unknown_privacy_restricts_to_team_only_as_safe_default():
    assert clf.audience_for_privacy(None) == ["TEAM"]


# --- compute_published_year ------------------------------------------------

def test_compute_published_year_from_iso_date():
    assert clf.compute_published_year("2024-03-15") == 2024


def test_compute_published_year_handles_none():
    assert clf.compute_published_year(None) is None


def test_compute_published_year_handles_empty_string():
    assert clf.compute_published_year("") is None


def test_compute_published_year_handles_garbage():
    assert clf.compute_published_year("not-a-date") is None


# --- authority_type_for ------------------------------------------------------

def test_live_gets_live_stream_authority():
    assert clf.authority_type_for("LIVE", "PUBLIC") == "LIVE_STREAM"


def test_short_gets_no_authority_type():
    """Shorts get no semantic classification at all -- see
    classify_short_as_inventory_only. Even calling this helper directly for
    SHORT must never assign one."""
    assert clf.authority_type_for("SHORT", "PUBLIC") is None


def test_public_long_form_gets_long_form_youtube_authority():
    assert clf.authority_type_for("LONG_FORM", "PUBLIC") == "LONG_FORM_YOUTUBE"


def test_private_long_form_has_no_authority_guess():
    """Can't tell VIP_CLASS from MENTORSHIP_CLASS from OTHER without more evidence."""
    assert clf.authority_type_for("LONG_FORM", "PRIVATE") is None


def test_unknown_format_has_no_authority_guess():
    assert clf.authority_type_for("UNKNOWN", "PUBLIC") is None


# --- fetch_extra_metadata (READ-ONLY API wrapper) ---------------------------

def test_fetch_extra_metadata_extracts_privacy_and_live_flag():
    fake_resp = {
        "items": [
            {
                "id": "v1",
                "status": {"privacyStatus": "public"},
            },
            {
                "id": "v2",
                "status": {"privacyStatus": "private"},
                "liveStreamingDetails": {"actualStartTime": "2024-01-01T00:00:00Z"},
            },
        ]
    }
    fake_videos = MagicMock()
    fake_videos.list.return_value.execute.return_value = fake_resp
    fake_youtube = MagicMock()
    fake_youtube.videos.return_value = fake_videos

    result = clf.fetch_extra_metadata(fake_youtube, ["v1", "v2"])

    assert result["v1"] == {"privacy": "PUBLIC", "is_live": False}
    assert result["v2"] == {"privacy": "PRIVATE", "is_live": True}
    # Solo lectura: nunca insert/update/delete.
    assert not fake_videos.insert.called
    assert not fake_videos.update.called


def test_fetch_extra_metadata_missing_video_is_absent_from_result():
    fake_videos = MagicMock()
    fake_videos.list.return_value.execute.return_value = {"items": []}
    fake_youtube = MagicMock()
    fake_youtube.videos.return_value = fake_videos

    result = clf.fetch_extra_metadata(fake_youtube, ["deleted_id"])
    assert "deleted_id" not in result


# --- fetch_tab_membership ---------------------------------------------------

def test_fetch_tab_membership_groups_tab_types_per_video(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.executemany(
            "INSERT INTO video_tab_membership (video_id, tab_type, channel_id) VALUES (?, ?, ?)",
            [("v1", "shorts", "UC_X"), ("v2", "streams", "UC_X"), ("v3", "shorts", "UC_X"),
             ("v3", "streams", "UC_X")],
        )
        conn.commit()

        result = clf.fetch_tab_membership(conn)

        assert result == {
            "v1": {"shorts"},
            "v2": {"streams"},
            "v3": {"shorts", "streams"},
        }
    finally:
        conn.close()


def test_fetch_tab_membership_empty_table_returns_empty_dict(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        assert clf.fetch_tab_membership(conn) == {}
    finally:
        conn.close()


# --- classify_all (integration: real temp DB + mocked YouTube client) ------

def _seed_video(conn, video_id, source_id, title, description, duration_sec, published_at):
    conn.execute(
        """INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES (?, ?, ?)
           ON CONFLICT(channel_id) DO NOTHING""",
        ("UC_TEST", "Canal Test", "https://youtube.com/@test"),
    )
    conn.execute(
        """INSERT INTO sources (source_id, source_type, original_title, channel, published_at)
           VALUES (?, 'youtube', ?, 'Canal Test', ?)
           ON CONFLICT(source_id) DO NOTHING""",
        (source_id, title, published_at),
    )
    conn.execute(
        """INSERT INTO youtube_videos
            (video_id, source_id, channel_id, title, url, published_at, duration_sec, description)
           VALUES (?, ?, 'UC_TEST', ?, ?, ?, ?, ?)""",
        (video_id, source_id, title, f"https://youtube.com/watch?v={video_id}",
         published_at, duration_sec, description),
    )


def test_classify_all_writes_content_format_privacy_and_audience_to_db(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_video(conn, "vLong", "YT_T_vLong", "Clase completa", None, 600, "2024-05-01")
        _seed_video(conn, "vShort", "YT_T_vShort", "Tip rapido #shorts", None, 30, "2024-05-02")
        conn.commit()

        fake_videos = MagicMock()
        fake_videos.list.return_value.execute.return_value = {
            "items": [
                {"id": "vLong", "status": {"privacyStatus": "public"}},
                {"id": "vShort", "status": {"privacyStatus": "private"}},
            ]
        }
        fake_youtube = MagicMock()
        fake_youtube.videos.return_value = fake_videos

        classified = clf.classify_all(conn, fake_youtube)
        assert classified == 2

        long_row = conn.execute(
            "SELECT content_format, youtube_privacy_status, include_in_knowledge_base, "
            "distribution_policy, internal_classification, published_year, source_authority_type "
            "FROM sources WHERE source_id='YT_T_vLong'"
        ).fetchone()
        assert long_row["content_format"] == "LONG_FORM"
        assert long_row["youtube_privacy_status"] == "PUBLIC"
        assert long_row["include_in_knowledge_base"] == 1
        assert long_row["distribution_policy"] == "SHAREABLE"
        assert long_row["internal_classification"] is None
        assert long_row["published_year"] == 2024
        assert long_row["source_authority_type"] == "LONG_FORM_YOUTUBE"

        short_row = conn.execute(
            "SELECT content_format, youtube_privacy_status, include_in_knowledge_base, "
            "internal_classification, source_authority_type, primary_content_type "
            "FROM sources WHERE source_id='YT_T_vShort'"
        ).fetchone()
        assert short_row["content_format"] == "SHORT"
        assert short_row["youtube_privacy_status"] == "PRIVATE"
        assert short_row["include_in_knowledge_base"] == 0
        # Inventory-only: no semantic/governance classification for Shorts.
        assert short_row["internal_classification"] is None
        assert short_row["source_authority_type"] is None
        assert short_row["primary_content_type"] is None

        long_audience = {
            r["audience"] for r in conn.execute(
                "SELECT audience FROM source_allowed_audience WHERE source_id='YT_T_vLong'"
            ).fetchall()
        }
        assert long_audience == {"PUBLIC", "STUDENT", "VIP_STUDENT", "TEAM"}

        short_audience = conn.execute(
            "SELECT audience FROM source_allowed_audience WHERE source_id='YT_T_vShort'"
        ).fetchall()
        assert short_audience == []  # Shorts get no audience assignment at all

        # Solo lectura contra la API: nunca insert/update/delete.
        assert not fake_videos.insert.called
        assert not fake_videos.update.called
    finally:
        conn.close()


def test_classify_all_reclassifying_twice_does_not_duplicate_audience_rows(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_video(conn, "vPub", "YT_T_vPub", "Clase completa", None, 600, "2024-05-01")
        conn.commit()

        fake_videos = MagicMock()
        fake_videos.list.return_value.execute.return_value = {
            "items": [{"id": "vPub", "status": {"privacyStatus": "public"}}]
        }
        fake_youtube = MagicMock()
        fake_youtube.videos.return_value = fake_videos

        clf.classify_all(conn, fake_youtube)
        clf.classify_all(conn, fake_youtube)  # re-run (idempotent)

        rows = conn.execute(
            "SELECT audience FROM source_allowed_audience WHERE source_id='YT_T_vPub'"
        ).fetchall()
        assert len(rows) == 4  # PUBLIC/STUDENT/VIP_STUDENT/TEAM, not 8
    finally:
        conn.close()


def test_classify_all_missing_api_metadata_defaults_to_safe_unknown_privacy(tmp_path):
    """If the API call doesn't return a video_id (e.g. rate-limited batch
    response), classification must fall back to the unknown-privacy safe
    defaults, not crash or silently assume PUBLIC."""
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_video(conn, "vMissing", "YT_T_vMissing", "Clase completa", None, 600, "2024-05-01")
        conn.commit()

        fake_videos = MagicMock()
        fake_videos.list.return_value.execute.return_value = {"items": []}
        fake_youtube = MagicMock()
        fake_youtube.videos.return_value = fake_videos

        clf.classify_all(conn, fake_youtube)

        row = conn.execute(
            "SELECT youtube_privacy_status, distribution_policy, internal_classification "
            "FROM sources WHERE source_id='YT_T_vMissing'"
        ).fetchone()
        assert row["youtube_privacy_status"] is None
        assert row["distribution_policy"] == "ASK_BEFORE_SHARING"
        assert row["internal_classification"] is None

        audience = {
            r["audience"] for r in conn.execute(
                "SELECT audience FROM source_allowed_audience WHERE source_id='YT_T_vMissing'"
            ).fetchall()
        }
        assert audience == {"TEAM"}
    finally:
        conn.close()


def test_classify_all_shorts_tab_membership_overrides_long_duration(tmp_path):
    """A video confirmed by the /shorts tab must classify as SHORT even
    though its stored duration_sec looks like a regular long video -- tab
    evidence outranks the duration/hashtag heuristic."""
    db_path = tmp_path / "t4.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_video(conn, "vTabShort", "YT_T_vTabShort", "Titulo sin pista alguna",
                    None, 600, "2024-05-01")
        conn.execute(
            "INSERT INTO video_tab_membership (video_id, tab_type, channel_id) VALUES (?, 'shorts', 'UC_TEST')",
            ("vTabShort",),
        )
        conn.commit()

        fake_videos = MagicMock()
        fake_videos.list.return_value.execute.return_value = {
            "items": [{"id": "vTabShort", "status": {"privacyStatus": "public"}}]
        }
        fake_youtube = MagicMock()
        fake_youtube.videos.return_value = fake_videos

        clf.classify_all(conn, fake_youtube)

        row = conn.execute(
            "SELECT content_format, include_in_knowledge_base FROM sources WHERE source_id='YT_T_vTabShort'"
        ).fetchone()
        assert row["content_format"] == "SHORT"
        assert row["include_in_knowledge_base"] == 0
    finally:
        conn.close()


def test_classify_all_streams_tab_membership_marks_live(tmp_path):
    db_path = tmp_path / "t5.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_video(conn, "vTabLive", "YT_T_vTabLive", "Sesion de hoy",
                    None, 5400, "2024-05-01")
        conn.execute(
            "INSERT INTO video_tab_membership (video_id, tab_type, channel_id) VALUES (?, 'streams', 'UC_TEST')",
            ("vTabLive",),
        )
        conn.commit()

        fake_videos = MagicMock()
        fake_videos.list.return_value.execute.return_value = {
            "items": [{"id": "vTabLive", "status": {"privacyStatus": "public"}}]
        }
        fake_youtube = MagicMock()
        fake_youtube.videos.return_value = fake_videos

        clf.classify_all(conn, fake_youtube)

        row = conn.execute(
            "SELECT content_format, source_authority_type FROM sources WHERE source_id='YT_T_vTabLive'"
        ).fetchone()
        assert row["content_format"] == "LIVE"
        assert row["source_authority_type"] == "LIVE_STREAM"
    finally:
        conn.close()


def test_classify_all_no_tab_evidence_falls_back_to_unknown_not_long_form(tmp_path):
    """Regression guard for the rule change: a 90s video with no #shorts tag
    and no tab evidence must land in UNKNOWN now, not LONG_FORM."""
    db_path = tmp_path / "t6.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_video(conn, "vAmbiguous", "YT_T_vAmbiguous", "Analisis del dia",
                    None, 90, "2024-05-01")
        conn.commit()

        fake_videos = MagicMock()
        fake_videos.list.return_value.execute.return_value = {
            "items": [{"id": "vAmbiguous", "status": {"privacyStatus": "public"}}]
        }
        fake_youtube = MagicMock()
        fake_youtube.videos.return_value = fake_videos

        clf.classify_all(conn, fake_youtube)

        row = conn.execute(
            "SELECT content_format, include_in_knowledge_base FROM sources WHERE source_id='YT_T_vAmbiguous'"
        ).fetchone()
        assert row["content_format"] == "UNKNOWN"
        assert row["include_in_knowledge_base"] == 1  # only confirmed SHORT excludes
    finally:
        conn.close()


def test_classify_short_as_inventory_only_sets_minimal_fields(tmp_path):
    db_path = tmp_path / "t7.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, channel) VALUES ('YT_X', 'youtube', 'CanalX')"
        )
        conn.commit()

        clf.classify_short_as_inventory_only(conn, "YT_X", "PUBLIC", 2024)
        conn.commit()

        row = conn.execute(
            "SELECT content_format, youtube_privacy_status, include_in_knowledge_base, "
            "published_year, source_authority_type, primary_content_type, internal_classification, "
            "derived_from_source_id, possible_parent_video_id, parent_match_confidence "
            "FROM sources WHERE source_id='YT_X'"
        ).fetchone()
        assert row["content_format"] == "SHORT"
        assert row["youtube_privacy_status"] == "PUBLIC"
        assert row["include_in_knowledge_base"] == 0
        assert row["published_year"] == 2024
        assert row["source_authority_type"] is None
        assert row["primary_content_type"] is None
        assert row["internal_classification"] is None
        # Nunca auto-poblados en esta fase (ver schema.sql / migrate_classification_schema.py).
        assert row["derived_from_source_id"] is None
        assert row["possible_parent_video_id"] is None
        assert row["parent_match_confidence"] is None
    finally:
        conn.close()


def test_classify_short_as_inventory_only_wipes_stale_prior_semantic_classification(tmp_path):
    """A video previously classified as LONG_FORM (with full semantic
    fields) that later gets reclassified as SHORT (new tab evidence
    arrives) must have its old classification wiped, not left stale."""
    db_path = tmp_path / "t8.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            """INSERT INTO sources
                (source_id, source_type, channel, content_format, source_authority_type,
                 primary_content_type, internal_classification, include_in_knowledge_base,
                 distribution_policy, temporal_status, potential_conflict)
               VALUES ('YT_Y', 'youtube', 'CanalX', 'LONG_FORM', 'LONG_FORM_YOUTUBE',
                       'STRATEGY_EDUCATION', 'SOME_PRIOR_VALUE', 1,
                       'SHAREABLE', 'CURRENT', 1)"""
        )
        conn.execute(
            "INSERT INTO source_allowed_audience (source_id, audience) VALUES ('YT_Y', 'PUBLIC')"
        )
        conn.commit()

        clf.classify_short_as_inventory_only(conn, "YT_Y", "PUBLIC", 2024)
        conn.commit()

        row = conn.execute(
            "SELECT content_format, source_authority_type, primary_content_type, "
            "internal_classification, include_in_knowledge_base, distribution_policy, "
            "temporal_status, potential_conflict "
            "FROM sources WHERE source_id='YT_Y'"
        ).fetchone()
        assert row["content_format"] == "SHORT"
        assert row["source_authority_type"] is None
        assert row["primary_content_type"] is None
        assert row["internal_classification"] is None
        assert row["include_in_knowledge_base"] == 0
        # Regression: un SHORT nunca debe quedar con distribution_policy='SHAREABLE'
        # (u otro valor) heredado de una clasificacion previa como contenido
        # regular -- debe resetearse al default neutral, no quedar pegado.
        assert row["distribution_policy"] == "ASK_BEFORE_SHARING"
        assert row["temporal_status"] == "UNKNOWN"
        assert row["potential_conflict"] == 0

        audience = conn.execute(
            "SELECT audience FROM source_allowed_audience WHERE source_id='YT_Y'"
        ).fetchall()
        assert audience == []
    finally:
        conn.close()
