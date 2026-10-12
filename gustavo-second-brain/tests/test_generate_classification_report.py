import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
from generate_classification_report import build_report  # noqa: E402


def _insert_source(conn, source_id, channel, content_format, privacy, include_kb,
                    internal_classification=None, published_year=None,
                    video_id=None, channel_id="UC_TEST", duration_sec=600):
    conn.execute(
        """INSERT INTO sources
            (source_id, source_type, original_title, channel, content_format,
             youtube_privacy_status, include_in_knowledge_base, internal_classification,
             published_year)
           VALUES (?, 'youtube', ?, ?, ?, ?, ?, ?, ?)""",
        (source_id, f"Titulo {source_id}", channel, content_format, privacy,
         include_kb, internal_classification, published_year),
    )
    if video_id:
        conn.execute(
            """INSERT INTO youtube_channels (channel_id, channel_name, channel_url)
               VALUES (?, ?, ?) ON CONFLICT(channel_id) DO NOTHING""",
            (channel_id, channel, f"https://youtube.com/{channel_id}"),
        )
        conn.execute(
            """INSERT INTO youtube_videos (video_id, source_id, channel_id, duration_sec)
               VALUES (?, ?, ?, ?)""",
            (video_id, source_id, channel_id, duration_sec),
        )


def test_report_includes_discovery_reconciliation_section(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        report = build_report(conn)
        assert "## DISCOVERY_RECONCILIATION" in report
        assert "COUNT(DISTINCT video_id)" in report
    finally:
        conn.close()


def test_report_counts_total_and_per_channel_with_privacy_breakdown(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "LONG_FORM", "PUBLIC", 1,
                        published_year=2023, video_id="v1")
        _insert_source(conn, "YT_A_2", "CanalA", "SHORT", "PUBLIC", 0,
                        published_year=2024, video_id="v2")
        _insert_source(conn, "YT_A_3", "CanalA", "LONG_FORM", "PRIVATE", 1,
                        published_year=2024, video_id="v3")
        _insert_source(conn, "YT_B_1", "CanalB", "UNKNOWN", "PUBLIC", 1,
                        published_year=2024, video_id="v4", channel_id="UC_B")
        conn.commit()

        report = build_report(conn)

        assert "TOTAL CANONICO DE VIDEOS UNICOS: 4" in report
        assert "| CanalA | 3 | 2 | 0 | 1 |" in report
        assert "| CanalB | 1 | 1 | 0 | 0 |" in report
    finally:
        conn.close()


def test_report_breaks_down_knowledge_base_by_reason(tmp_path):
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "LONG_FORM", "PUBLIC", 1, video_id="v1")
        _insert_source(conn, "YT_A_2", "CanalA", "SHORT", "PUBLIC", 0, video_id="v2")
        _insert_source(conn, "YT_A_3", "CanalA", "UNKNOWN", "PUBLIC", 1, video_id="v3")
        conn.commit()

        report = build_report(conn)

        assert "Incluidos (include_in_knowledge_base=true): 2" in report
        assert "Excluidos por SHORT confirmado: 1" in report
        assert "Excluidos por otra razon: 0" in report
        assert "Pendientes (content_format=UNKNOWN" in report
    finally:
        conn.close()


def test_report_counts_manual_review_for_unknown_format(tmp_path):
    db_path = tmp_path / "t4.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "UNKNOWN", "PUBLIC", 1, video_id="v1")
        _insert_source(conn, "YT_A_2", "CanalA", "LONG_FORM", "PUBLIC", 1, video_id="v2")
        conn.commit()

        report = build_report(conn)

        assert "UNKNOWN, privacy desconocida" in report
        assert ": 1" in report.split("Revision manual requerida")[1].split("\n")[1]
    finally:
        conn.close()


def test_report_lists_private_sources_without_exposing_url(tmp_path):
    db_path = tmp_path / "t5.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            """INSERT INTO sources
                (source_id, source_type, original_title, original_url, channel,
                 content_format, youtube_privacy_status, include_in_knowledge_base,
                 internal_classification)
               VALUES (?, 'youtube', ?, ?, ?, ?, ?, ?, ?)""",
            ("YT_A_PRIV", "Clase VIP", "https://youtube.com/watch?v=secret123",
             "CanalA", "LONG_FORM", "PRIVATE", 1, "PRIVATE_UNCLASSIFIED"),
        )
        conn.commit()

        report = build_report(conn)

        assert "YT_A_PRIV" in report
        assert "PRIVATE" in report
        # La URL privada no debe filtrarse al reporte.
        assert "secret123" not in report
    finally:
        conn.close()


def test_report_includes_chronological_distribution_by_year(tmp_path):
    db_path = tmp_path / "t6.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "LONG_FORM", "PUBLIC", 1,
                        published_year=2022, video_id="v1")
        _insert_source(conn, "YT_A_2", "CanalA", "LONG_FORM", "PUBLIC", 1,
                        published_year=2022, video_id="v2")
        _insert_source(conn, "YT_A_3", "CanalA", "LONG_FORM", "PUBLIC", 1,
                        published_year=2024, video_id="v3")
        conn.commit()

        report = build_report(conn)

        assert "2022: 2" in report
        assert "2024: 1" in report
    finally:
        conn.close()


def test_report_shows_shorts_confirmed_by_tab_vs_heuristic_only(tmp_path):
    db_path = tmp_path / "t7.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "SHORT", "PUBLIC", 0, video_id="vTab")
        _insert_source(conn, "YT_A_2", "CanalA", "SHORT", "PUBLIC", 0, video_id="vHeuristic")
        conn.execute(
            "INSERT INTO video_tab_membership (video_id, tab_type, channel_id) VALUES ('vTab', 'shorts', 'UC_TEST')"
        )
        conn.commit()

        report = build_report(conn)

        assert "SHORT confirmados por pestaña /shorts" in report
        assert "pestaña /shorts (yt-dlp, evidencia fuerte): 1" in report
        assert "solo por heuristica" in report
    finally:
        conn.close()


def test_report_shows_live_confirmed_by_tab_vs_api_only(tmp_path):
    db_path = tmp_path / "t8.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "LIVE", "PUBLIC", 1, video_id="vLiveTab")
        _insert_source(conn, "YT_A_2", "CanalA", "LIVE", "PUBLIC", 1, video_id="vLiveApi")
        conn.execute(
            "INSERT INTO video_tab_membership (video_id, tab_type, channel_id) "
            "VALUES ('vLiveTab', 'streams', 'UC_TEST')"
        )
        conn.commit()

        report = build_report(conn)

        assert "pestaña /streams (yt-dlp): 1" in report
        assert "solo por la API (liveStreamingDetails" in report
    finally:
        conn.close()


def test_report_flags_duration_discrepancy_for_tab_shorts_over_180s(tmp_path):
    db_path = tmp_path / "t9.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "SHORT", "PUBLIC", 0,
                        video_id="vLong", duration_sec=300)
        conn.execute(
            "INSERT INTO video_tab_membership (video_id, tab_type, channel_id) VALUES ('vLong', 'shorts', 'UC_TEST')"
        )
        conn.commit()

        report = build_report(conn)

        assert "Discrepancias: video_id en /shorts con duration_sec>180s almacenado" in report
        assert report.count("tratada como no confiable aqui): 1") == 1
    finally:
        conn.close()


def test_report_shows_shorts_summary_and_confirms_zero_in_kb(tmp_path):
    db_path = tmp_path / "t10.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "SHORT", "PUBLIC", 0, video_id="v1")
        _insert_source(conn, "YT_A_2", "CanalA", "SHORT", "PUBLIC", 0, video_id="v2")
        _insert_source(conn, "YT_A_3", "CanalA", "LONG_FORM", "PUBLIC", 1, video_id="v3")
        conn.commit()

        report = build_report(conn)

        assert "SHORTS CONFIRMADOS: 2" in report
        assert "EXCLUIDOS DEL KNOWLEDGE BASE: 2" in report
        assert "SHORTS_IN_KNOWLEDGE_BASE = 0" in report
    finally:
        conn.close()


def test_report_flags_short_leaked_into_knowledge_base_if_it_ever_happens(tmp_path):
    """Regression guard: if a data bug ever let a SHORT keep
    include_in_knowledge_base=1, the report must surface it, not hide it."""
    db_path = tmp_path / "t11.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "SHORT", "PUBLIC", 1, video_id="v1")  # bug scenario
        conn.commit()

        report = build_report(conn)

        assert "SHORTS_IN_KNOWLEDGE_BASE = 1" in report
    finally:
        conn.close()


def test_report_computes_candidate_universe_excluding_shorts(tmp_path):
    db_path = tmp_path / "t12.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _insert_source(conn, "YT_A_1", "CanalA", "SHORT", "PUBLIC", 0, video_id="v1")
        _insert_source(conn, "YT_A_2", "CanalA", "LONG_FORM", "PUBLIC", 1, video_id="v2")
        _insert_source(conn, "YT_A_3", "CanalA", "LIVE", "PUBLIC", 1, video_id="v3")
        _insert_source(conn, "YT_A_4", "CanalA", "UNKNOWN", "PRIVATE", 1, video_id="v4")
        conn.commit()

        report = build_report(conn)

        assert "- TOTAL = 4" in report
        assert "- menos SHORTS = 1" in report
        assert "**CANDIDATOS = 3**" in report
        assert "videos largos (LONG_FORM): 1" in report
        assert "lives (LIVE): 1" in report
        assert "unknown (UNKNOWN): 1" in report
        assert "- private: 1" in report
        # Los SHORT nunca deben contarse en el desglose del universo candidato.
        candidate_section = report.split("Universo candidato")[1].split("## Knowledge base")[0]
        assert "SHORT" not in candidate_section.replace("SHORTS", "")
    finally:
        conn.close()
