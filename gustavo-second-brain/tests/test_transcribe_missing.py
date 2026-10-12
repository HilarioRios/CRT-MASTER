import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import transcribe_missing as tm  # noqa: E402
import vtt_parser  # noqa: E402


def test_format_timestamp_formats_hours_minutes_seconds_millis():
    assert tm.format_timestamp(0) == "00:00:00.000"
    assert tm.format_timestamp(3661.5) == "01:01:01.500"
    assert tm.format_timestamp(7384.25) == "02:03:04.250"


class _FakeSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


def test_write_whisper_vtt_produces_valid_vtt_header(tmp_path):
    out = tmp_path / "out.vtt"
    tm.write_whisper_vtt([_FakeSegment(0, 2, "hola mundo")], out)
    content = out.read_text()
    assert content.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:02.000" in content
    assert "hola mundo" in content


def test_write_whisper_vtt_skips_empty_segments(tmp_path):
    out = tmp_path / "out2.vtt"
    tm.write_whisper_vtt(
        [_FakeSegment(0, 1, "  "), _FakeSegment(1, 2, "contenido real")], out
    )
    content = out.read_text()
    assert content.count("-->") == 1
    assert "contenido real" in content


def test_write_whisper_vtt_output_is_parseable_by_vtt_parser(tmp_path):
    """The whole point of plain single-cue-per-segment VTT: vtt_parser.py's
    roll-up dedup logic must not accidentally merge or drop real segments."""
    out = tmp_path / "out3.vtt"
    tm.write_whisper_vtt(
        [_FakeSegment(0, 2, "primera frase"), _FakeSegment(2, 5, "segunda frase distinta")],
        out,
    )
    segments = vtt_parser.parse_vtt(out.read_text())
    assert len(segments) == 2
    assert segments[0].text == "primera frase"
    assert segments[1].text == "segunda frase distinta"
    assert segments[1].start_sec == 2.0


# --- run_for_videos orchestration (faster_whisper mocked) -------------------

def test_run_for_videos_skips_sources_not_pending_unless_forced(tmp_path, monkeypatch):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    conn.execute(
        "INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES ('UC_X','Canal','u')"
    )
    conn.execute(
        "INSERT INTO sources (source_id, source_type, processing_status) "
        "VALUES ('YT_X_v1', 'youtube', 'METADATA_READY')"
    )
    conn.execute(
        "INSERT INTO youtube_videos (video_id, source_id, channel_id, url) "
        "VALUES ('v1', 'YT_X_v1', 'UC_X', 'http://x')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(tm, "get_connection", lambda: get_connection(db_path=db_path))
    monkeypatch.setattr(tm, "init_db", lambda: init_db(db_path=db_path))

    fake_model_cls = MagicMock()
    with patch.dict(sys.modules, {"faster_whisper": MagicMock(WhisperModel=fake_model_cls)}):
        results = tm.run_for_videos(["v1"], force=False)

    assert results["skipped_not_pending"] == 1
    assert results["whisper_local"] == 0
    fake_model_cls.assert_not_called()  # no deberia ni cargar el modelo si no hay nada que hacer...


def test_run_for_videos_transcribes_pending_video_and_updates_db(tmp_path, monkeypatch):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    conn.execute(
        "INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES ('UC_X','Canal','u')"
    )
    conn.execute(
        "INSERT INTO sources (source_id, source_type, processing_status) "
        "VALUES ('YT_X_v2', 'youtube', 'TRANSCRIPT_PENDING')"
    )
    conn.execute(
        "INSERT INTO youtube_videos (video_id, source_id, channel_id, url) "
        "VALUES ('v2', 'YT_X_v2', 'UC_X', 'http://x')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(tm, "get_connection", lambda: get_connection(db_path=db_path))
    monkeypatch.setattr(tm, "init_db", lambda: init_db(db_path=db_path))

    fake_result = {"method": "whisper_local", "path": "/fake/path.vtt", "lang": "es"}
    with patch.object(tm, "transcribe_one", return_value=fake_result) as transcribe_mock, \
         patch.object(tm, "load_whisper_settings", return_value={"model_size": "tiny", "device": "cpu", "compute_type": "int8"}):
        fake_model_cls = MagicMock()
        with patch.dict(sys.modules, {"faster_whisper": MagicMock(WhisperModel=fake_model_cls)}):
            results = tm.run_for_videos(["v2"], force=False)

    assert results["whisper_local"] == 1
    transcribe_mock.assert_called_once()

    conn2 = get_connection(db_path=db_path)
    row = conn2.execute(
        "SELECT processing_status, transcript_source FROM sources WHERE source_id='YT_X_v2'"
    ).fetchone()
    assert row["processing_status"] == "TRANSCRIPT_READY"
    assert row["transcript_source"] == "whisper_local"
    transcript_row = conn2.execute(
        "SELECT method, raw_file_path FROM transcripts WHERE source_id='YT_X_v2'"
    ).fetchone()
    assert transcript_row["method"] == "whisper_local"
    conn2.close()


def test_run_for_videos_logs_error_and_continues_on_failure(tmp_path, monkeypatch):
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    conn.execute(
        "INSERT INTO youtube_channels (channel_id, channel_name, channel_url) VALUES ('UC_X','Canal','u')"
    )
    conn.execute(
        "INSERT INTO sources (source_id, source_type, processing_status) "
        "VALUES ('YT_X_v3', 'youtube', 'TRANSCRIPT_PENDING')"
    )
    conn.execute(
        "INSERT INTO youtube_videos (video_id, source_id, channel_id, url) "
        "VALUES ('v3', 'YT_X_v3', 'UC_X', 'http://x')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(tm, "get_connection", lambda: get_connection(db_path=db_path))
    monkeypatch.setattr(tm, "init_db", lambda: init_db(db_path=db_path))

    with patch.object(tm, "transcribe_one", side_effect=RuntimeError("boom")), \
         patch.object(tm, "load_whisper_settings", return_value={"model_size": "tiny", "device": "cpu", "compute_type": "int8"}):
        fake_model_cls = MagicMock()
        with patch.dict(sys.modules, {"faster_whisper": MagicMock(WhisperModel=fake_model_cls)}):
            results = tm.run_for_videos(["v3"], force=False)

    assert results["failed"] == 1
    conn2 = get_connection(db_path=db_path)
    err = conn2.execute(
        "SELECT COUNT(*) c FROM errors WHERE source_id='YT_X_v3' AND stage='transcript'"
    ).fetchone()
    assert err["c"] == 1
    # El status no debe quedar erroneamente en TRANSCRIPT_READY tras un fallo.
    status = conn2.execute("SELECT processing_status FROM sources WHERE source_id='YT_X_v3'").fetchone()
    assert status["processing_status"] == "TRANSCRIPT_PENDING"
    conn2.close()
