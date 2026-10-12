import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from db import get_connection, init_db  # noqa: E402
import sync_drive as sd  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402


# --- pure helpers ------------------------------------------------------

def test_channel_key_for_source_id_extracts_canal():
    assert sd.channel_key_for_source_id("YT_CANAL_01_abc123") == "canal_01"
    assert sd.channel_key_for_source_id("YT_CANAL_02_xyz789") == "canal_02"


def test_channel_key_for_source_id_rejects_unexpected_format():
    try:
        sd.channel_key_for_source_id("NOT_A_YOUTUBE_SOURCE_ID")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_compute_md5_matches_hashlib_directly(tmp_path):
    f = tmp_path / "x.txt"
    f.write_bytes(b"contenido de prueba" * 1000)
    expected = hashlib.md5(f.read_bytes()).hexdigest()
    assert sd.compute_md5(f) == expected


def test_target_folder_id_reads_from_structure_dict():
    structure = {
        "youtube_channels": {
            "canal_01": {"subfolders": {"01_RAW": "FOLDER_RAW_1", "02_PROCESSED": "FOLDER_PROC_1"}}
        }
    }
    assert sd.target_folder_id(structure, "canal_01", "01_RAW") == "FOLDER_RAW_1"


def test_resolve_source_ids_prefers_explicit_ids():
    assert sd.resolve_source_ids(pilot=True, explicit_ids=["YT_A_1"]) == ["YT_A_1"]


def test_resolve_source_ids_raises_without_pilot_or_explicit_ids():
    try:
        sd.resolve_source_ids(pilot=False, explicit_ids=[])
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- retry ---------------------------------------------------------------

def test_retry_succeeds_after_transient_failures(monkeypatch):
    monkeypatch.setattr(sd.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    assert sd.retry(flaky, attempts=4, what="test") == "ok"
    assert calls["n"] == 3


def test_retry_raises_after_exhausting_attempts(monkeypatch):
    monkeypatch.setattr(sd.time, "sleep", lambda _: None)

    def always_fails():
        raise ConnectionError("permanent")

    try:
        sd.retry(always_fails, attempts=3, what="test")
        assert False, "expected ConnectionError"
    except ConnectionError:
        pass


def test_retry_uses_exponential_backoff(monkeypatch):
    delays = []
    monkeypatch.setattr(sd.time, "sleep", lambda d: delays.append(d))

    def always_fails():
        raise ConnectionError("x")

    try:
        sd.retry(always_fails, attempts=3, base_delay=2.0, what="test")
    except ConnectionError:
        pass
    assert delays == [2.0, 4.0]


# --- sync_one_file: idempotency / immutability / integrity branches ------

def _fake_404():
    resp = MagicMock(status=404)
    return HttpError(resp, b"not found")


def test_sync_one_file_uploads_when_no_existing_file_id(tmp_path, monkeypatch):
    video_id = "vUpload"
    local_path = tmp_path / "raw" / video_id / "transcript.es.vtt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("WEBVTT\n\ncontenido")
    monkeypatch.setitem(sd.FILE_ROLES["raw"], "local", lambda vid: local_path)

    structure = {"youtube_channels": {"canal_01": {"subfolders": {"01_RAW": "FOLDER_RAW"}}}}
    local_md5 = sd.compute_md5(local_path)

    fake_service = MagicMock()
    fake_service.files.return_value.create.return_value.execute.return_value = {
        "id": "NEWFILEID", "md5Checksum": local_md5, "size": "100"
    }

    with patch.object(sd, "load_drive_structure", return_value=structure):
        result = sd.sync_one_file(MagicMock(), fake_service, "YT_CANAL_01_vUpload", "raw", existing_file_id=None)

    assert result == {"status": "uploaded", "file_id": "NEWFILEID", "role": "raw"}
    fake_service.files.return_value.create.assert_called_once()
    assert not fake_service.files.return_value.delete.called


def test_sync_one_file_skips_when_already_synced_and_md5_matches(tmp_path, monkeypatch):
    video_id = "vSkip"
    local_path = tmp_path / "raw" / video_id / "transcript.es.vtt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("contenido identico")
    monkeypatch.setitem(sd.FILE_ROLES["raw"], "local", lambda vid: local_path)
    local_md5 = sd.compute_md5(local_path)

    fake_service = MagicMock()
    fake_service.files.return_value.get.return_value.execute.return_value = {
        "id": "EXISTING", "md5Checksum": local_md5, "trashed": False
    }

    result = sd.sync_one_file(MagicMock(), fake_service, "YT_CANAL_01_vSkip", "raw", existing_file_id="EXISTING")

    assert result == {"status": "already_synced", "file_id": "EXISTING", "role": "raw"}
    assert not fake_service.files.return_value.create.called
    assert not fake_service.files.return_value.update.called


def test_sync_one_file_raw_drift_is_never_overwritten(tmp_path, monkeypatch):
    """The core immutability guarantee: a RAW file with a different remote
    md5 must be flagged, never silently replaced."""
    video_id = "vDrift"
    local_path = tmp_path / "raw" / video_id / "transcript.es.vtt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("version local nueva")
    monkeypatch.setitem(sd.FILE_ROLES["raw"], "local", lambda vid: local_path)

    fake_service = MagicMock()
    fake_service.files.return_value.get.return_value.execute.return_value = {
        "id": "EXISTING", "md5Checksum": "md5-remoto-distinto", "trashed": False
    }

    result = sd.sync_one_file(MagicMock(), fake_service, "YT_CANAL_01_vDrift", "raw", existing_file_id="EXISTING")

    assert result["status"] == "integrity_conflict_skipped"
    assert result["file_id"] == "EXISTING"
    assert not fake_service.files.return_value.update.called
    assert not fake_service.files.return_value.create.called


def test_sync_one_file_processed_drift_updates_in_place(tmp_path, monkeypatch):
    """Non-immutable roles (processed/metadata) DO get updated in place
    (same file_id, new content) when local content changed."""
    video_id = "vUpdate"
    local_path = tmp_path / "proc" / video_id / "transcript_clean.txt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("version nueva")
    monkeypatch.setitem(sd.FILE_ROLES["processed"], "local", lambda vid: local_path)
    local_md5 = sd.compute_md5(local_path)

    fake_service = MagicMock()
    fake_service.files.return_value.get.return_value.execute.return_value = {
        "id": "EXISTING", "md5Checksum": "md5-viejo", "trashed": False
    }
    fake_service.files.return_value.update.return_value.execute.return_value = {
        "id": "EXISTING", "md5Checksum": local_md5, "size": "50"
    }

    result = sd.sync_one_file(MagicMock(), fake_service, "YT_CANAL_01_vUpdate", "processed", existing_file_id="EXISTING")

    assert result == {"status": "updated", "file_id": "EXISTING", "role": "processed"}
    fake_service.files.return_value.update.assert_called_once()


def test_sync_one_file_re_uploads_when_remote_file_was_trashed(tmp_path, monkeypatch):
    video_id = "vTrashed"
    local_path = tmp_path / "proc" / video_id / "transcript_clean.txt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("contenido")
    monkeypatch.setitem(sd.FILE_ROLES["processed"], "local", lambda vid: local_path)
    local_md5 = sd.compute_md5(local_path)

    structure = {"youtube_channels": {"canal_01": {"subfolders": {"02_PROCESSED": "FOLDER_PROC"}}}}
    fake_service = MagicMock()
    fake_service.files.return_value.get.return_value.execute.return_value = {
        "id": "OLD", "md5Checksum": "whatever", "trashed": True
    }
    fake_service.files.return_value.create.return_value.execute.return_value = {
        "id": "NEWFILE", "md5Checksum": local_md5, "size": "10"
    }

    with patch.object(sd, "load_drive_structure", return_value=structure):
        result = sd.sync_one_file(
            MagicMock(), fake_service, "YT_CANAL_01_vTrashed", "processed", existing_file_id="OLD"
        )

    assert result == {"status": "uploaded", "file_id": "NEWFILE", "role": "processed"}


def test_sync_one_file_reports_local_missing_without_calling_drive(tmp_path, monkeypatch):
    missing_path = tmp_path / "does" / "not" / "exist.vtt"
    monkeypatch.setitem(sd.FILE_ROLES["raw"], "local", lambda vid: missing_path)
    fake_service = MagicMock()

    result = sd.sync_one_file(MagicMock(), fake_service, "YT_CANAL_01_vMissing", "raw", existing_file_id=None)

    assert result == {"status": "local_missing", "file_id": None, "role": "raw"}
    assert not fake_service.files.return_value.create.called
    assert not fake_service.files.return_value.get.called


def test_sync_one_file_flags_integrity_failure_after_upload(tmp_path, monkeypatch):
    video_id = "vBadUpload"
    local_path = tmp_path / "raw" / video_id / "transcript.es.vtt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("contenido original")
    monkeypatch.setitem(sd.FILE_ROLES["raw"], "local", lambda vid: local_path)

    structure = {"youtube_channels": {"canal_01": {"subfolders": {"01_RAW": "FOLDER_RAW"}}}}
    fake_service = MagicMock()
    # Drive devuelve un md5 que NO coincide con el local -> subida corrupta/incompleta.
    fake_service.files.return_value.create.return_value.execute.return_value = {
        "id": "CORRUPT", "md5Checksum": "md5-que-no-coincide", "size": "1"
    }

    with patch.object(sd, "load_drive_structure", return_value=structure):
        result = sd.sync_one_file(
            MagicMock(), fake_service, "YT_CANAL_01_vBadUpload", "raw", existing_file_id=None
        )

    assert result["status"] == "integrity_failed_after_upload"


# --- sync_source: persistence + resumability ------------------------------

def test_sync_source_persists_each_file_immediately_and_marks_drive_synced(tmp_path, monkeypatch):
    db_path = tmp_path / "t.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, processing_status) "
            "VALUES ('YT_CANAL_01_vOK', 'youtube', 'CHUNKED')"
        )
        conn.commit()

        for role in ("raw", "processed", "metadata"):
            p = tmp_path / role / "vOK" / "f"
            p.parent.mkdir(parents=True)
            p.write_text(f"contenido {role}")
            monkeypatch.setitem(sd.FILE_ROLES[role], "local", lambda vid, p=p: p)

        fake_service = MagicMock()

        def fake_sync_one_file(conn_, service_, source_id, role, existing_file_id):
            return {"status": "uploaded", "file_id": f"FILE_{role.upper()}", "role": role}

        with patch.object(sd, "sync_one_file", side_effect=fake_sync_one_file):
            summary = sd.sync_source(conn, fake_service, "YT_CANAL_01_vOK")

        assert summary["all_ok"] is True
        row = conn.execute(
            "SELECT drive_raw_file_id, drive_processed_file_id, drive_metadata_file_id "
            "FROM drive_sync WHERE source_id='YT_CANAL_01_vOK'"
        ).fetchone()
        assert row["drive_raw_file_id"] == "FILE_RAW"
        assert row["drive_processed_file_id"] == "FILE_PROCESSED"
        assert row["drive_metadata_file_id"] == "FILE_METADATA"

        status = conn.execute(
            "SELECT processing_status FROM sources WHERE source_id='YT_CANAL_01_vOK'"
        ).fetchone()
        assert status["processing_status"] == "DRIVE_SYNCED"
    finally:
        conn.close()


def test_sync_source_does_not_mark_drive_synced_if_any_file_fails(tmp_path):
    db_path = tmp_path / "t2.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, processing_status) "
            "VALUES ('YT_CANAL_01_vPartial', 'youtube', 'CHUNKED')"
        )
        conn.commit()

        def fake_sync_one_file(conn_, service_, source_id, role, existing_file_id):
            if role == "metadata":
                return {"status": "integrity_conflict_skipped", "file_id": None, "role": role, "detail": "x"}
            return {"status": "uploaded", "file_id": f"FILE_{role.upper()}", "role": role}

        fake_service = MagicMock()
        with patch.object(sd, "sync_one_file", side_effect=fake_sync_one_file):
            summary = sd.sync_source(conn, fake_service, "YT_CANAL_01_vPartial")

        assert summary["all_ok"] is False
        status = conn.execute(
            "SELECT processing_status FROM sources WHERE source_id='YT_CANAL_01_vPartial'"
        ).fetchone()
        assert status["processing_status"] == "CHUNKED"  # unchanged, not DRIVE_SYNCED

        errors = conn.execute(
            "SELECT COUNT(*) c FROM errors WHERE source_id='YT_CANAL_01_vPartial' AND stage='drive_sync'"
        ).fetchone()
        assert errors["c"] == 1
    finally:
        conn.close()


def test_sync_source_is_resumable_skips_already_persisted_roles_on_rerun(tmp_path):
    """Regression guard for resumability: if raw/processed already have a
    drive_sync row from a prior (interrupted) run, re-running must pass
    their existing file_id through to sync_one_file instead of None."""
    db_path = tmp_path / "t3.sqlite"
    init_db(db_path=db_path)
    conn = get_connection(db_path=db_path)
    try:
        conn.execute(
            "INSERT INTO sources (source_id, source_type, processing_status) "
            "VALUES ('YT_CANAL_01_vResume', 'youtube', 'CHUNKED')"
        )
        conn.execute(
            "INSERT INTO drive_sync (source_id, drive_raw_file_id, drive_processed_file_id) "
            "VALUES ('YT_CANAL_01_vResume', 'PRIOR_RAW', 'PRIOR_PROCESSED')"
        )
        conn.commit()

        seen_existing_ids = {}

        def fake_sync_one_file(conn_, service_, source_id, role, existing_file_id):
            seen_existing_ids[role] = existing_file_id
            return {"status": "already_synced" if existing_file_id else "uploaded",
                    "file_id": existing_file_id or f"NEW_{role.upper()}", "role": role}

        fake_service = MagicMock()
        with patch.object(sd, "sync_one_file", side_effect=fake_sync_one_file):
            sd.sync_source(conn, fake_service, "YT_CANAL_01_vResume")

        assert seen_existing_ids["raw"] == "PRIOR_RAW"
        assert seen_existing_ids["processed"] == "PRIOR_PROCESSED"
        assert seen_existing_ids["metadata"] is None
    finally:
        conn.close()


# --- video_id_for_source_id: regression for the underscore-in-video_id bug -

def test_video_id_for_source_id_handles_underscores_in_video_id():
    """Regression test for a real bug found during the pilot: YouTube
    video_id can itself contain underscores (e.g. '-7G__mSBIrg'), so
    source_id.rsplit('_', 1) incorrectly truncates it to 'mSBIrg'. Must
    anchor on the fixed YT_CANAL_NN_ prefix instead."""
    assert sd.video_id_for_source_id("YT_CANAL_02_-7G__mSBIrg") == "-7G__mSBIrg"
    assert sd.video_id_for_source_id("YT_CANAL_01_abc123") == "abc123"
    assert sd.video_id_for_source_id("YT_CANAL_02_a_b_c_d") == "a_b_c_d"


def test_video_id_for_source_id_rejects_unexpected_format():
    try:
        sd.video_id_for_source_id("NOT_A_YOUTUBE_SOURCE_ID")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_sync_one_file_resolves_video_id_with_underscores_correctly(tmp_path, monkeypatch):
    """End-to-end regression: sync_one_file must find the local file for a
    video_id containing underscores, not look in the wrong directory."""
    video_id = "-7G__mSBIrg"
    local_path = tmp_path / "raw" / video_id / "transcript.es.vtt"
    local_path.parent.mkdir(parents=True)
    local_path.write_text("contenido real")
    monkeypatch.setitem(sd.FILE_ROLES["raw"], "local", lambda vid: tmp_path / "raw" / vid / "transcript.es.vtt")

    structure = {"youtube_channels": {"canal_02": {"subfolders": {"01_RAW": "FOLDER_RAW"}}}}
    local_md5 = sd.compute_md5(local_path)
    fake_service = MagicMock()
    fake_service.files.return_value.create.return_value.execute.return_value = {
        "id": "NEWFILE", "md5Checksum": local_md5, "size": "10"
    }

    with patch.object(sd, "load_drive_structure", return_value=structure):
        result = sd.sync_one_file(
            MagicMock(), fake_service, "YT_CANAL_02_-7G__mSBIrg", "raw", existing_file_id=None
        )

    assert result["status"] == "uploaded"
