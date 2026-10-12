import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_captions as fc  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402


def _http_error(status: int):
    resp = MagicMock(status=status)
    return HttpError(resp, b"error")


# --- get_youtube_service_for_channel ---------------------------------------

def test_get_youtube_service_returns_none_for_unmapped_channel():
    fc._youtube_services_cache.clear()
    assert fc.get_youtube_service_for_channel("UC_UNKNOWN_CHANNEL") is None


def test_get_youtube_service_returns_none_if_token_file_missing(tmp_path, monkeypatch):
    fc._youtube_services_cache.clear()
    monkeypatch.setattr(fc, "ROOT", tmp_path)  # no tokens/ dir under here
    assert fc.get_youtube_service_for_channel("UCwMIt6Wa7WzoP2vZR1KO9PQ") is None


def test_get_youtube_service_caches_per_channel(tmp_path, monkeypatch):
    fc._youtube_services_cache.clear()
    token_dir = tmp_path / "tokens"
    token_dir.mkdir()
    (token_dir / "youtube_gustavo.json").write_text('{"fake": "token"}')
    monkeypatch.setattr(fc, "ROOT", tmp_path)

    fake_creds = MagicMock(valid=True)
    fake_service = MagicMock()
    with patch.object(fc.Credentials, "from_authorized_user_file", return_value=fake_creds), \
         patch.object(fc, "build", return_value=fake_service) as build_mock:
        s1 = fc.get_youtube_service_for_channel("UCwMIt6Wa7WzoP2vZR1KO9PQ")
        s2 = fc.get_youtube_service_for_channel("UCwMIt6Wa7WzoP2vZR1KO9PQ")

    assert s1 is fake_service
    assert s2 is fake_service
    build_mock.assert_called_once()  # segunda llamada usa el cache, no reconstruye


# --- fetch_official_caption --------------------------------------------------

def test_fetch_official_caption_returns_none_when_no_spanish_track(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "RAW_DIR", tmp_path)
    fake_youtube = MagicMock()
    fake_youtube.captions.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "capId", "snippet": {"language": "en", "trackKind": "asr"}}]
    }
    assert fc.fetch_official_caption(fake_youtube, "vid1") is None


def test_fetch_official_caption_prefers_manual_over_asr_track(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "RAW_DIR", tmp_path)
    fake_youtube = MagicMock()
    fake_youtube.captions.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "asrId", "snippet": {"language": "es", "trackKind": "asr"}},
            {"id": "manualId", "snippet": {"language": "es", "trackKind": "standard"}},
        ]
    }
    fake_youtube.captions.return_value.download.return_value.execute.return_value = b"WEBVTT\n\ncontenido"

    result = fc.fetch_official_caption(fake_youtube, "vid2")

    fake_youtube.captions.return_value.download.assert_called_once_with(id="manualId", tfmt="vtt")
    assert result["method"] == "youtube_official"
    assert result["lang"] == "es"
    assert Path(result["path"]).read_bytes() == b"WEBVTT\n\ncontenido"


def test_fetch_official_caption_writes_raw_file_under_video_id_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "RAW_DIR", tmp_path)
    fake_youtube = MagicMock()
    fake_youtube.captions.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "capId", "snippet": {"language": "es-419", "trackKind": "asr"}}]
    }
    fake_youtube.captions.return_value.download.return_value.execute.return_value = b"WEBVTT\n\nx"

    result = fc.fetch_official_caption(fake_youtube, "vid3")

    expected_path = tmp_path / "vid3" / "transcript.es-419.vtt"
    assert Path(result["path"]) == expected_path
    assert expected_path.exists()


def test_fetch_official_caption_returns_none_on_list_http_error(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "RAW_DIR", tmp_path)
    fake_youtube = MagicMock()
    fake_youtube.captions.return_value.list.return_value.execute.side_effect = _http_error(403)
    assert fc.fetch_official_caption(fake_youtube, "vid4") is None


def test_fetch_official_caption_returns_none_on_download_http_error(tmp_path, monkeypatch):
    monkeypatch.setattr(fc, "RAW_DIR", tmp_path)
    fake_youtube = MagicMock()
    fake_youtube.captions.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "capId", "snippet": {"language": "es", "trackKind": "standard"}}]
    }
    fake_youtube.captions.return_value.download.return_value.execute.side_effect = _http_error(403)
    assert fc.fetch_official_caption(fake_youtube, "vid5") is None


# --- fetch_with_cascade: priority order --------------------------------------

def test_cascade_uses_official_caption_when_available_and_skips_ytdlp():
    with patch.object(fc, "get_youtube_service_for_channel", return_value=MagicMock()) as get_svc, \
         patch.object(fc, "fetch_official_caption", return_value={"method": "youtube_official", "path": "p", "lang": "es"}) as official, \
         patch.object(fc, "fetch_one") as ytdlp_fallback:
        result = fc.fetch_with_cascade("vid", "http://x", "UCwMIt6Wa7WzoP2vZR1KO9PQ")

    get_svc.assert_called_once_with("UCwMIt6Wa7WzoP2vZR1KO9PQ")
    official.assert_called_once()
    assert not ytdlp_fallback.called
    assert result["method"] == "youtube_official"


def test_cascade_falls_back_to_ytdlp_when_no_official_caption():
    with patch.object(fc, "get_youtube_service_for_channel", return_value=MagicMock()), \
         patch.object(fc, "fetch_official_caption", return_value=None), \
         patch.object(fc, "fetch_one", return_value={"method": "yt_dlp_auto", "path": "p", "lang": "es"}) as ytdlp_fallback:
        result = fc.fetch_with_cascade("vid", "http://x", "UCwMIt6Wa7WzoP2vZR1KO9PQ")

    ytdlp_fallback.assert_called_once_with("vid", "http://x")
    assert result["method"] == "yt_dlp_auto"


def test_cascade_falls_back_to_ytdlp_when_no_oauth_service_for_channel():
    with patch.object(fc, "get_youtube_service_for_channel", return_value=None), \
         patch.object(fc, "fetch_official_caption") as official, \
         patch.object(fc, "fetch_one", return_value={"method": "yt_dlp_manual", "path": "p", "lang": "es"}) as ytdlp_fallback:
        result = fc.fetch_with_cascade("vid", "http://x", "UC_UNKNOWN")

    assert not official.called
    ytdlp_fallback.assert_called_once()
    assert result["method"] == "yt_dlp_manual"
