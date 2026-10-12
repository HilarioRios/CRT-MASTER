import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import authorize_youtube_remote as remote  # noqa: E402


def test_scopes_is_force_ssl_only():
    assert remote.SCOPES == ["https://www.googleapis.com/auth/youtube.force-ssl"]


def test_callback_path_matches_configured_redirect_uri():
    assert remote.CALLBACK_PATH == "/oauth2/callback"


def test_build_flow_raises_if_client_file_missing(tmp_path):
    missing = tmp_path / "no_such_client.json"
    with patch.object(remote, "CLIENT_FILE", missing):
        try:
            remote.build_flow()
            assert False, "expected FileNotFoundError"
        except FileNotFoundError:
            pass


def test_build_flow_uses_client_file_scopes_and_redirect_uri(tmp_path):
    client_file = tmp_path / "web_client.json"
    client_file.write_text("{}")
    fake_flow = MagicMock()

    with patch.object(remote, "CLIENT_FILE", client_file), \
         patch.object(remote.Flow, "from_client_secrets_file", return_value=fake_flow) as from_file:
        result = remote.build_flow()

    assert result is fake_flow
    from_file.assert_called_once_with(
        str(client_file), scopes=remote.SCOPES, redirect_uri=remote.REDIRECT_URI
    )


def test_get_authorization_url_requests_offline_access_and_consent():
    fake_flow = MagicMock()
    fake_flow.authorization_url.return_value = ("https://accounts.google.com/auth?x=1", "state123")

    url, state = remote.get_authorization_url(fake_flow)

    assert url == "https://accounts.google.com/auth?x=1"
    assert state == "state123"
    fake_flow.authorization_url.assert_called_once_with(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )


def test_match_callback_returns_none_for_unrelated_path():
    assert remote.match_callback("/favicon.ico") is None


def test_match_callback_extracts_code_and_state():
    result = remote.match_callback("/oauth2/callback?code=abc123&state=xyz")
    assert result == {"code": "abc123", "state": "xyz", "error": None}


def test_match_callback_extracts_error():
    result = remote.match_callback("/oauth2/callback?error=access_denied&state=xyz")
    assert result == {"code": None, "state": "xyz", "error": "access_denied"}


def test_accept_callback_rejects_mismatched_state():
    result = {"code": "abc", "state": "WRONG", "error": None}
    assert remote.accept_callback(result, expected_state="expected-state") is False


def test_accept_callback_accepts_matching_state():
    result = {"code": "abc", "state": "expected-state", "error": None}
    assert remote.accept_callback(result, expected_state="expected-state") is True


def test_accept_callback_rejects_missing_state():
    result = {"code": "abc", "state": None, "error": None}
    assert remote.accept_callback(result, expected_state="expected-state") is False


def test_list_my_channels_is_reused_from_authorize_youtube():
    import authorize_youtube as local_auth
    assert remote.list_my_channels is local_auth.list_my_channels


def test_main_writes_to_given_token_file_without_touching_the_default_one(tmp_path):
    default_token_file = tmp_path / "youtube_gustavo.json"
    default_token_file.write_text('{"existing": "do-not-touch"}')
    extra_token_file = tmp_path / "youtube_gustavo_trader.json"

    fake_flow = MagicMock()
    fake_flow.authorization_url.return_value = ("https://accounts.google.com/auth", "state1")
    fake_creds = MagicMock()
    fake_creds.to_json.return_value = '{"new": "token"}'
    fake_flow.credentials = fake_creds

    fake_channels_resp = {"items": []}

    with patch.object(remote, "TOKEN_FILE", default_token_file), \
         patch.object(remote, "build_flow", return_value=fake_flow), \
         patch.object(remote, "wait_for_callback", return_value="auth-code"), \
         patch.object(remote, "list_my_channels", return_value=[]):
        remote.main(token_file=extra_token_file)

    assert extra_token_file.read_text() == '{"new": "token"}'
    # El token ya existente para la otra cuenta no debe modificarse.
    assert default_token_file.read_text() == '{"existing": "do-not-touch"}'
    fake_flow.fetch_token.assert_called_once_with(code="auth-code")
