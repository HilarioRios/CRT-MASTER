import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import discover_videos_api as api  # noqa: E402


def test_parse_iso8601_duration_hours_minutes_seconds():
    assert api.parse_iso8601_duration("PT1H2M10S") == 3730


def test_parse_iso8601_duration_minutes_only():
    assert api.parse_iso8601_duration("PT45M") == 2700


def test_parse_iso8601_duration_seconds_only():
    assert api.parse_iso8601_duration("PT30S") == 30


def test_parse_iso8601_duration_empty_or_none_is_zero():
    assert api.parse_iso8601_duration("") == 0
    assert api.parse_iso8601_duration(None) == 0


def test_chunked_splits_into_fixed_size_groups():
    assert api.chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunked_empty_list_returns_empty():
    assert api.chunked([], 50) == []


def test_resolve_channel_extracts_id_name_and_uploads_playlist():
    fake_resp = {
        "items": [{
            "id": "UCwMIt6Wa7WzoP2vZR1KO9PQ",
            "snippet": {"title": "MentoTrading"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UUwMIt6Wa7WzoP2vZR1KO9PQ"}},
            "statistics": {"videoCount": "130"},
        }]
    }
    fake_channels = MagicMock()
    fake_channels.list.return_value.execute.return_value = fake_resp
    fake_youtube = MagicMock()
    fake_youtube.channels.return_value = fake_channels

    result = api.resolve_channel(fake_youtube, "@MentoTradingClub")

    fake_channels.list.assert_called_once_with(
        part="snippet,contentDetails,statistics", forHandle="@MentoTradingClub"
    )
    assert result == {
        "channel_id": "UCwMIt6Wa7WzoP2vZR1KO9PQ",
        "channel_name": "MentoTrading",
        "uploads_playlist_id": "UUwMIt6Wa7WzoP2vZR1KO9PQ",
        "video_count_reported": 130,
    }
    # Solo lectura: nunca se debe invocar insert/update/delete sobre canales.
    assert not fake_channels.insert.called
    assert not fake_channels.update.called


def test_resolve_channel_raises_if_handle_not_found():
    fake_channels = MagicMock()
    fake_channels.list.return_value.execute.return_value = {"items": []}
    fake_youtube = MagicMock()
    fake_youtube.channels.return_value = fake_channels

    try:
        api.resolve_channel(fake_youtube, "@no-existe")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_list_all_uploaded_video_ids_paginates_until_no_next_token():
    fake_playlist_items = MagicMock()
    fake_playlist_items.list.return_value.execute.side_effect = [
        {
            "items": [{"contentDetails": {"videoId": "v1"}}, {"contentDetails": {"videoId": "v2"}}],
            "nextPageToken": "PAGE2",
        },
        {
            "items": [{"contentDetails": {"videoId": "v3"}}],
        },
    ]
    fake_youtube = MagicMock()
    fake_youtube.playlistItems.return_value = fake_playlist_items

    result = api.list_all_uploaded_video_ids(fake_youtube, "UUxyz")

    assert result == ["v1", "v2", "v3"]
    assert fake_playlist_items.list.call_count == 2
    first_call_kwargs = fake_playlist_items.list.call_args_list[0].kwargs
    assert first_call_kwargs["playlistId"] == "UUxyz"
    assert first_call_kwargs["maxResults"] == 50
    second_call_kwargs = fake_playlist_items.list.call_args_list[1].kwargs
    assert second_call_kwargs["pageToken"] == "PAGE2"


def test_fetch_videos_metadata_batches_in_groups_of_50_and_keys_by_id():
    ids = [f"v{i}" for i in range(60)]
    fake_videos = MagicMock()
    fake_videos.list.return_value.execute.side_effect = [
        {"items": [{"id": vid, "snippet": {"title": vid}} for vid in ids[:50]]},
        {"items": [{"id": vid, "snippet": {"title": vid}} for vid in ids[50:]]},
    ]
    fake_youtube = MagicMock()
    fake_youtube.videos.return_value = fake_videos

    result = api.fetch_videos_metadata(fake_youtube, ids)

    assert fake_videos.list.call_count == 2
    assert set(result.keys()) == set(ids)
    assert result["v0"]["snippet"]["title"] == "v0"
    # Solo lectura: nunca se debe invocar insert/update/delete sobre videos.
    assert not fake_videos.insert.called


def test_fetch_videos_metadata_missing_id_means_absent_from_result():
    fake_videos = MagicMock()
    fake_videos.list.return_value.execute.return_value = {"items": [{"id": "v1", "snippet": {}}]}
    fake_youtube = MagicMock()
    fake_youtube.videos.return_value = fake_videos

    result = api.fetch_videos_metadata(fake_youtube, ["v1", "v2_deleted"])

    assert "v1" in result
    assert "v2_deleted" not in result
