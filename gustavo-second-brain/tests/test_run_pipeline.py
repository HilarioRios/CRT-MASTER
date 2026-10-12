import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import run_pipeline as rp  # noqa: E402


def _seed_source(conn, source_id, status, video_id=None, channel="CanalA", channel_id="UC_X"):
    video_id = video_id or source_id.rsplit("_", 1)[-1]
    conn.execute(
        "INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES (?, ?, ?) "
        "ON CONFLICT(channel_id) DO NOTHING",
        (channel_id, channel, f"https://youtube.com/{channel_id}"),
    )
    conn.execute(
        """INSERT INTO sources
            (source_id, source_type, original_title, original_url, channel,
             include_in_knowledge_base, content_format, processing_status)
           VALUES (?, 'youtube', ?, ?, ?, 1, 'LONG_FORM', ?)""",
        (source_id, f"Titulo {source_id}", f"https://youtube.com/watch?v={video_id}", channel, status),
    )
    conn.execute(
        "INSERT INTO youtube_videos (video_id, source_id, channel_id, url) VALUES (?, ?, ?, ?)",
        (video_id, source_id, channel_id, f"https://youtube.com/watch?v={video_id}"),
    )


# --- select_pending_batch ----------------------------------------------

def test_select_pending_batch_excludes_drive_synced_and_failed_by_default(tmp_path):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        _seed_source(conn, "YT_A_v2", "DRIVE_SYNCED")
        _seed_source(conn, "YT_A_v3", "FAILED")
        conn.commit()

        batch = rp.select_pending_batch(conn)

        ids = {s["source_id"] for s in batch}
        assert ids == {"YT_A_v1"}
    finally:
        conn.close()


def test_select_pending_batch_include_failed_true_includes_failed_not_drive_synced(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        _seed_source(conn, "YT_A_v2", "DRIVE_SYNCED")
        _seed_source(conn, "YT_A_v3", "FAILED")
        conn.commit()

        batch = rp.select_pending_batch(conn, include_failed=True)

        ids = {s["source_id"] for s in batch}
        assert ids == {"YT_A_v1", "YT_A_v3"}
    finally:
        conn.close()


def test_select_pending_batch_excludes_shorts_implicitly_via_include_in_kb(tmp_path):
    """SHORTS always have include_in_knowledge_base=0 (see classify_videos.py)
    -- the batch query must never pick them up, permanently."""
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        conn.execute(
            "INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES ('UC_Y','C','u')"
        )
        conn.execute(
            """INSERT INTO sources (source_id, source_type, include_in_knowledge_base,
                content_format, processing_status) VALUES ('YT_A_short', 'youtube', 0, 'SHORT', 'METADATA_READY')"""
        )
        conn.execute(
            "INSERT INTO youtube_videos (video_id, source_id, channel_id, url) VALUES ('short1','YT_A_short','UC_Y','u')"
        )
        conn.commit()

        batch = rp.select_pending_batch(conn)

        ids = {s["source_id"] for s in batch}
        assert "YT_A_short" not in ids
    finally:
        conn.close()


def test_select_pending_batch_respects_limit(tmp_path):
    db_path = tmp_path / "t4.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        for i in range(5):
            _seed_source(conn, f"YT_A_v{i}", "METADATA_READY")
        conn.commit()

        batch = rp.select_pending_batch(conn, limit=3)
        assert len(batch) == 3
    finally:
        conn.close()


# --- attempt_count -------------------------------------------------------

def test_attempt_count_counts_pipeline_stage_errors_only(tmp_path):
    db_path = tmp_path / "t5.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute("INSERT INTO errors (source_id, stage, message) VALUES ('YT_A_v1', 'pipeline', 'x')")
        conn.execute("INSERT INTO errors (source_id, stage, message) VALUES ('YT_A_v1', 'pipeline', 'y')")
        conn.execute("INSERT INTO errors (source_id, stage, message) VALUES ('YT_A_v1', 'discovery', 'z')")
        conn.commit()
        assert rp.attempt_count(conn, "YT_A_v1") == 2
    finally:
        conn.close()


# --- process_source: resumability (the core correctness property) -------

def test_process_source_from_metadata_ready_runs_full_pipeline(tmp_path):
    db_path = tmp_path / "t6.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        conn.commit()
        source = dict(conn.execute("SELECT * FROM sources WHERE source_id='YT_A_v1'").fetchone())
        source.update({"video_id": "v1", "channel_id": "UC_X"})

        with patch.object(rp, "fetch_with_cascade", return_value={"method": "youtube_official", "path": "p", "lang": "es"}) as fetch_mock, \
             patch.object(rp, "normalize_video", return_value={}) as norm_mock, \
             patch.object(rp, "run_for_video", return_value=5) as chunk_mock, \
             patch.object(rp, "sync_source", return_value={"all_ok": True, "files": {}}) as sync_mock:
            ok, info = rp.process_source(conn, MagicMock(), source)

        assert ok is True
        assert info["transcript_source"] == "youtube_official"
        assert info["chunks"] == 5
        fetch_mock.assert_called_once()
        norm_mock.assert_called_once()
        chunk_mock.assert_called_once()
        sync_mock.assert_called_once()
        # DRIVE_SYNCED es escrito por el propio sync_source() en produccion
        # (ya cubierto por tests/test_sync_drive.py) -- aqui esta mockeado,
        # asi que no reproduce ese efecto secundario; lo que importa en
        # este test es que process_source LLEGA a invocarlo con exito.
    finally:
        conn.close()


def test_process_source_resumes_from_chunked_skips_earlier_steps(tmp_path):
    """Regression guard: a source already at CHUNKED must NOT re-fetch,
    re-normalize, or re-chunk -- only run Drive sync."""
    db_path = tmp_path / "t7.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "CHUNKED")
        conn.commit()
        source = dict(conn.execute("SELECT * FROM sources WHERE source_id='YT_A_v1'").fetchone())
        source.update({"video_id": "v1", "channel_id": "UC_X"})

        with patch.object(rp, "fetch_with_cascade") as fetch_mock, \
             patch.object(rp, "normalize_video") as norm_mock, \
             patch.object(rp, "run_for_video") as chunk_mock, \
             patch.object(rp, "sync_source", return_value={"all_ok": True, "files": {}}) as sync_mock:
            ok, info = rp.process_source(conn, MagicMock(), source)

        assert ok is True
        assert not fetch_mock.called
        assert not norm_mock.called
        assert not chunk_mock.called
        sync_mock.assert_called_once()
    finally:
        conn.close()


def test_process_source_resumes_from_transcript_ready_skips_fetch(tmp_path):
    db_path = tmp_path / "t8.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "TRANSCRIPT_READY")
        conn.commit()
        source = dict(conn.execute("SELECT * FROM sources WHERE source_id='YT_A_v1'").fetchone())
        source.update({"video_id": "v1", "channel_id": "UC_X"})

        with patch.object(rp, "fetch_with_cascade") as fetch_mock, \
             patch.object(rp, "normalize_video", return_value={}) as norm_mock, \
             patch.object(rp, "run_for_video", return_value=2) as chunk_mock, \
             patch.object(rp, "sync_source", return_value={"all_ok": True, "files": {}}):
            ok, info = rp.process_source(conn, MagicMock(), source)

        assert ok is True
        assert not fetch_mock.called
        norm_mock.assert_called_once()
        chunk_mock.assert_called_once()
    finally:
        conn.close()


def test_process_source_falls_back_to_whisper_when_cascade_returns_none(tmp_path):
    db_path = tmp_path / "t9.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        conn.commit()
        source = dict(conn.execute("SELECT * FROM sources WHERE source_id='YT_A_v1'").fetchone())
        source.update({"video_id": "v1", "channel_id": "UC_X"})

        with patch.object(rp, "fetch_with_cascade", return_value={"method": None, "path": None, "lang": None}), \
             patch.object(rp, "get_whisper_model", return_value=MagicMock()) as model_mock, \
             patch.object(rp, "transcribe_one", return_value={"method": "whisper_local", "path": "p", "lang": "es"}) as whisper_mock, \
             patch.object(rp, "normalize_video", return_value={}), \
             patch.object(rp, "run_for_video", return_value=1), \
             patch.object(rp, "sync_source", return_value={"all_ok": True, "files": {}}):
            ok, info = rp.process_source(conn, MagicMock(), source)

        assert ok is True
        assert info["transcript_source"] == "whisper_local"
        model_mock.assert_called_once()
        whisper_mock.assert_called_once()
    finally:
        conn.close()


def test_process_source_logs_error_and_marks_failed_on_exception(tmp_path):
    db_path = tmp_path / "t10.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        conn.commit()
        source = dict(conn.execute("SELECT * FROM sources WHERE source_id='YT_A_v1'").fetchone())
        source.update({"video_id": "v1", "channel_id": "UC_X"})

        with patch.object(rp, "fetch_with_cascade", side_effect=RuntimeError("boom")):
            ok, info = rp.process_source(conn, MagicMock(), source)

        assert ok is False
        assert "boom" in info["error"]
        row = conn.execute("SELECT processing_status FROM sources WHERE source_id='YT_A_v1'").fetchone()
        assert row["processing_status"] == "FAILED"
        err = conn.execute("SELECT COUNT(*) c FROM errors WHERE source_id='YT_A_v1' AND stage='pipeline'").fetchone()
        assert err["c"] == 1
    finally:
        conn.close()


def test_process_source_drive_sync_incomplete_marks_failed_not_silently_ok(tmp_path):
    db_path = tmp_path / "t11.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "CHUNKED")
        conn.commit()
        source = dict(conn.execute("SELECT * FROM sources WHERE source_id='YT_A_v1'").fetchone())
        source.update({"video_id": "v1", "channel_id": "UC_X"})

        with patch.object(rp, "sync_source", return_value={
            "all_ok": False, "files": {"raw": {"status": "integrity_conflict_skipped"}}
        }):
            ok, info = rp.process_source(conn, MagicMock(), source)

        assert ok is False
        row = conn.execute("SELECT processing_status FROM sources WHERE source_id='YT_A_v1'").fetchone()
        assert row["processing_status"] == "FAILED"
    finally:
        conn.close()


# --- run_batch -------------------------------------------------------------

def test_run_batch_aggregates_counts_and_rebuilds_index_once(tmp_path):
    db_path = tmp_path / "t12.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "METADATA_READY")
        _seed_source(conn, "YT_A_v2", "METADATA_READY")
        conn.commit()
        sources = rp.select_pending_batch(conn)

        def fake_process(conn_, service_, source):
            return True, {"transcript_source": "youtube_official", "chunks": 3}

        with patch.object(rp, "process_source", side_effect=fake_process), \
             patch.object(rp, "rebuild_index", return_value=0) as rebuild_mock, \
             patch.object(rp, "build_master_index") as master_mock:
            summary = rp.run_batch(conn, MagicMock(), sources, batch_num=1)

        assert summary["processed"] == 2
        assert summary["succeeded"] == 2
        assert summary["failed"] == 0
        assert summary["youtube_official"] == 2
        assert summary["chunks"] == 6
        assert summary["failure_rate"] == 0.0
        rebuild_mock.assert_called_once()
        master_mock.assert_called_once()
    finally:
        conn.close()


def test_run_batch_computes_failure_rate(tmp_path):
    db_path = tmp_path / "t13.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        for i in range(10):
            _seed_source(conn, f"YT_A_v{i}", "METADATA_READY")
        conn.commit()
        sources = rp.select_pending_batch(conn)

        call_count = {"n": 0}

        def fake_process(conn_, service_, source):
            call_count["n"] += 1
            ok = call_count["n"] > 2  # first 2 fail
            return ok, ({"transcript_source": "youtube_official", "chunks": 1} if ok else {"error": "x"})

        with patch.object(rp, "process_source", side_effect=fake_process), \
             patch.object(rp, "rebuild_index", return_value=0), \
             patch.object(rp, "build_master_index"):
            summary = rp.run_batch(conn, MagicMock(), sources, batch_num=1)

        assert summary["failed"] == 2
        assert summary["failure_rate"] == 0.2
    finally:
        conn.close()


# --- run_retry_pass: respects the max-retries cap ---------------------

def test_run_retry_pass_stops_after_max_retries_per_source(tmp_path):
    db_path = tmp_path / "t14.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "FAILED")
        conn.commit()

        call_count = {"n": 0}

        def always_fails(conn_, service_, source):
            call_count["n"] += 1
            conn.execute(
                "INSERT INTO errors (source_id, stage, message) VALUES (?, 'pipeline', 'still broken')",
                (source["source_id"],),
            )
            conn.commit()
            return False, {"error": "still broken"}

        with patch.object(rp, "process_source", side_effect=always_fails), \
             patch.object(rp, "rebuild_index", return_value=0), \
             patch.object(rp, "build_master_index"):
            summary = rp.run_retry_pass(conn, MagicMock(), max_retries=2)

        # max_retries=2 -> se reintenta mientras attempt_count <= 2 ANTES del intento;
        # no debe convertirse en un loop infinito ni superar unos pocos intentos.
        assert call_count["n"] <= 3
        assert summary["still_failed"] == 1
    finally:
        conn.close()


def test_run_retry_pass_recovers_source_that_succeeds_on_retry(tmp_path):
    db_path = tmp_path / "t15.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        _seed_source(conn, "YT_A_v1", "FAILED")
        conn.commit()

        def succeeds(conn_, service_, source):
            conn.execute("UPDATE sources SET processing_status='DRIVE_SYNCED' WHERE source_id=?", (source["source_id"],))
            conn.commit()
            return True, {"transcript_source": "yt_dlp_auto", "chunks": 2}

        with patch.object(rp, "process_source", side_effect=succeeds), \
             patch.object(rp, "rebuild_index", return_value=0), \
             patch.object(rp, "build_master_index"):
            summary = rp.run_retry_pass(conn, MagicMock(), max_retries=2)

        assert summary["recovered"] == 1
        assert summary["still_failed"] == 0
    finally:
        conn.close()


# --- write_batch_report ------------------------------------------------

def test_write_batch_report_writes_expected_file(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "ROOT", tmp_path)
    summary = {
        "batch_num": 7, "processed": 2, "succeeded": 2, "failed": 0,
        "youtube_official": 2, "yt_dlp_manual": 0, "yt_dlp_auto": 0, "whisper_local": 0,
        "chunks": 10, "elapsed_sec": 12.3, "failure_rate": 0.0,
        "sources": [{"source_id": "YT_A_v1", "ok": True, "transcript_source": "youtube_official"}],
    }

    path = rp.write_batch_report(summary)

    assert path == tmp_path / "BATCH_REPORT_7.md"
    content = path.read_text()
    assert "BATCH_REPORT_7" in content
    assert "Procesados: 2" in content
    assert "Captions oficiales (OAuth): 2" in content
    assert "YT_A_v1: OK" in content


def test_select_all_failed_returns_every_failed_source_no_limit(tmp_path):
    db_path = tmp_path / "t16.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        for i in range(30):  # mas que BATCH_SIZE (25)
            _seed_source(conn, f"YT_A_v{i:02d}", "FAILED")
        conn.commit()

        result = rp.select_all_failed(conn)

        assert len(result) == 30
    finally:
        conn.close()


def test_run_retry_pass_attempts_every_failed_source_even_beyond_batch_size(tmp_path):
    """Regression test for the real bug found in the first full import run:
    with >25 FAILED sources, calling select_pending_batch(limit=25,
    include_failed=True) inside the retry loop always returns the same
    deterministic first-25-by-source_id slice while they keep failing,
    so sources past position 25 never get attempted at all. Must use
    select_all_failed() instead."""
    db_path = tmp_path / "t17.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        for i in range(30):
            _seed_source(conn, f"YT_A_v{i:02d}", "FAILED")
        conn.commit()

        attempted_ids = set()

        def record_and_fail(conn_, service_, source):
            attempted_ids.add(source["source_id"])
            conn.execute(
                "INSERT INTO errors (source_id, stage, message) VALUES (?, 'pipeline', 'still broken')",
                (source["source_id"],),
            )
            conn.commit()
            return False, {"error": "still broken"}

        with patch.object(rp, "process_source", side_effect=record_and_fail), \
             patch.object(rp, "rebuild_index", return_value=0), \
             patch.object(rp, "build_master_index"):
            rp.run_retry_pass(conn, MagicMock(), max_retries=2)

        assert len(attempted_ids) == 30  # las 30, no solo las primeras 25
    finally:
        conn.close()
