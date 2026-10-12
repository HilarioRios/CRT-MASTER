import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import authorize_youtube as auth  # noqa: E402


def test_scopes_is_force_ssl_only():
    assert auth.SCOPES == ["https://www.googleapis.com/auth/youtube.force-ssl"]


def test_get_credentials_reuses_valid_token_without_opening_browser(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    fake_creds = MagicMock(valid=True, expired=False)
    fake_creds.to_json.return_value = '{"reused": true}'
    with patch.object(auth, "TOKEN_FILE", token_file), \
         patch.object(auth.Credentials, "from_authorized_user_file", return_value=fake_creds), \
         patch.object(auth, "InstalledAppFlow") as flow_cls:
        result = auth.get_credentials()

    assert result is fake_creds
    flow_cls.from_client_secrets_file.assert_not_called()


def test_get_credentials_refreshes_expired_token_and_persists_it(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    fake_creds = MagicMock(valid=False, expired=True, refresh_token="r")
    fake_creds.to_json.return_value = '{"refreshed": true}'

    def _mark_valid(_request):
        fake_creds.valid = True

    fake_creds.refresh.side_effect = _mark_valid

    with patch.object(auth, "TOKEN_FILE", token_file), \
         patch.object(auth.Credentials, "from_authorized_user_file", return_value=fake_creds), \
         patch.object(auth, "InstalledAppFlow") as flow_cls:
        result = auth.get_credentials()

    assert result is fake_creds
    fake_creds.refresh.assert_called_once()
    flow_cls.from_client_secrets_file.assert_not_called()
    # Bug cubierto: el token refrescado debe quedar escrito en disco, no solo en memoria.
    assert token_file.read_text() == '{"refreshed": true}'


def test_get_credentials_falls_back_to_oauth_flow_when_refresh_fails(tmp_path):
    client_file = tmp_path / "client.json"
    client_file.write_text("{}")
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    broken_creds = MagicMock(valid=False, expired=True, refresh_token="r")
    broken_creds.refresh.side_effect = Exception("refresh token revoked")

    fresh_creds = MagicMock(valid=True)
    fresh_creds.to_json.return_value = '{"fresh": true}'
    fake_flow = MagicMock()
    fake_flow.run_local_server.return_value = fresh_creds

    with patch.object(auth, "CLIENT_FILE", client_file), \
         patch.object(auth, "TOKEN_FILE", token_file), \
         patch.object(auth.Credentials, "from_authorized_user_file", return_value=broken_creds), \
         patch.object(auth, "InstalledAppFlow") as flow_cls:
        flow_cls.from_client_secrets_file.return_value = fake_flow
        result = auth.get_credentials()

    broken_creds.refresh.assert_called_once()
    flow_cls.from_client_secrets_file.assert_called_once_with(str(client_file), auth.SCOPES)
    assert result is fresh_creds
    assert token_file.read_text() == '{"fresh": true}'


def test_get_credentials_falls_back_to_oauth_flow_when_token_file_is_corrupt(tmp_path):
    client_file = tmp_path / "client.json"
    client_file.write_text("{}")
    token_file = tmp_path / "token.json"
    token_file.write_text("not valid json {{{")

    fresh_creds = MagicMock(valid=True)
    fresh_creds.to_json.return_value = '{"fresh": true}'
    fake_flow = MagicMock()
    fake_flow.run_local_server.return_value = fresh_creds

    with patch.object(auth, "CLIENT_FILE", client_file), \
         patch.object(auth, "TOKEN_FILE", token_file), \
         patch.object(auth.Credentials, "from_authorized_user_file", side_effect=ValueError("bad json")), \
         patch.object(auth, "InstalledAppFlow") as flow_cls:
        flow_cls.from_client_secrets_file.return_value = fake_flow
        result = auth.get_credentials()

    flow_cls.from_client_secrets_file.assert_called_once()
    assert result is fresh_creds
    assert token_file.read_text() == '{"fresh": true}'


def test_get_credentials_raises_if_client_file_missing_when_auth_needed(tmp_path):
    missing_client_file = tmp_path / "no_such_client.json"
    missing_token_file = tmp_path / "no_such_token.json"

    with patch.object(auth, "CLIENT_FILE", missing_client_file), \
         patch.object(auth, "TOKEN_FILE", missing_token_file):
        try:
            auth.get_credentials()
            assert False, "expected FileNotFoundError"
        except FileNotFoundError:
            pass


def test_get_credentials_runs_oauth_flow_and_saves_token_when_no_valid_token(tmp_path):
    client_file = tmp_path / "client.json"
    client_file.write_text("{}")
    token_file = tmp_path / "token.json"

    fake_creds = MagicMock(valid=True)
    fake_creds.to_json.return_value = '{"fake": "token"}'
    fake_flow = MagicMock()
    fake_flow.run_local_server.return_value = fake_creds

    with patch.object(auth, "CLIENT_FILE", client_file), \
         patch.object(auth, "TOKEN_FILE", token_file), \
         patch.object(auth, "InstalledAppFlow") as flow_cls:
        flow_cls.from_client_secrets_file.return_value = fake_flow
        result = auth.get_credentials()

    flow_cls.from_client_secrets_file.assert_called_once_with(str(client_file), auth.SCOPES)
    fake_flow.run_local_server.assert_called_once_with(port=0)
    assert result is fake_creds
    assert token_file.read_text() == '{"fake": "token"}'
    assert oct(token_file.stat().st_mode)[-3:] == "600"


def test_list_my_channels_is_read_only_and_parses_items():
    fake_response = {
        "items": [
            {"id": "UC123", "snippet": {"title": "Canal de Gustavo"},
             "statistics": {"subscriberCount": "100", "videoCount": "10"}}
        ]
    }
    fake_channels_resource = MagicMock()
    fake_channels_resource.list.return_value.execute.return_value = fake_response
    fake_youtube = MagicMock()
    fake_youtube.channels.return_value = fake_channels_resource

    with patch.object(auth, "build", return_value=fake_youtube) as build_fn:
        result = auth.list_my_channels(MagicMock())

    assert result == fake_response["items"]
    fake_channels_resource.list.assert_called_once_with(
        part="snippet,contentDetails,statistics", mine=True
    )
    build_fn.assert_called_once()
    # Nunca se debe invocar ninguna operacion de escritura (insert/update/delete).
    assert not fake_youtube.channels.return_value.insert.called
    assert not fake_youtube.channels.return_value.update.called


def test_list_my_channels_returns_empty_list_when_account_has_no_channel():
    fake_channels_resource = MagicMock()
    fake_channels_resource.list.return_value.execute.return_value = {}
    fake_youtube = MagicMock()
    fake_youtube.channels.return_value = fake_channels_resource

    with patch.object(auth, "build", return_value=fake_youtube):
        result = auth.list_my_channels(MagicMock())

    assert result == []
