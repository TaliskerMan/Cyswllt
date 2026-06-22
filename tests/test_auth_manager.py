# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

"""Unit tests for the credential handling and token extraction in AuthManager.

These cover the logic most worth protecting in a tool that handles OAuth tokens,
without touching the real ~/.config or invoking rclone.
"""

import json
import pytest

from cyswllt import auth_manager
from cyswllt.auth_manager import AuthManager


@pytest.fixture
def temp_credentials(tmp_path, monkeypatch):
    """Point the module's credentials file at a temp location."""
    cred_file = tmp_path / "google_credentials.json"
    monkeypatch.setattr(auth_manager, "_CREDENTIALS_FILE", str(cred_file))
    return cred_file


def test_save_get_has_clear_round_trip(temp_credentials):
    am = AuthManager()
    assert am.has_custom_credentials() is False
    assert am.get_custom_credentials() is None

    assert am.save_custom_credentials("id-123", "secret-xyz") is True
    assert temp_credentials.exists()
    # Saved with owner-only permissions.
    assert (temp_credentials.stat().st_mode & 0o777) == 0o600

    creds = am.get_custom_credentials()
    assert creds == {"client_id": "id-123", "client_secret": "secret-xyz"}
    assert am.has_custom_credentials() is True

    assert am.clear_custom_credentials() is True
    assert am.has_custom_credentials() is False
    # Clearing an already-absent file is success, not error.
    assert am.clear_custom_credentials() is True


def test_save_rejects_empty_or_whitespace_input(temp_credentials):
    am = AuthManager()
    assert am.save_custom_credentials("", "secret") is False
    assert am.save_custom_credentials("id", "   ") is False
    assert am.save_custom_credentials("   ", "   ") is False
    assert not temp_credentials.exists()


def test_save_strips_surrounding_whitespace(temp_credentials):
    am = AuthManager()
    assert am.save_custom_credentials("  id-1  ", "\tsecret-1\n") is True
    assert am.get_custom_credentials() == {
        "client_id": "id-1",
        "client_secret": "secret-1",
    }


def test_get_returns_none_on_corrupt_file(temp_credentials):
    temp_credentials.write_text("not json {{{")
    assert AuthManager().get_custom_credentials() is None


class TestExtractTokenJson:
    def test_extracts_json_embedded_in_human_text(self):
        output = (
            "If your browser doesn't open automatically go to ...\n"
            "Paste the following into your remote machine --->\n"
            '{"access_token":"ya29.abc","token_type":"Bearer","expiry":"2026-01-01"}\n'
            "<---End paste\n"
        )
        token = AuthManager.extract_token_json(output)
        assert json.loads(token)["access_token"] == "ya29.abc"

    def test_accepts_bare_json(self):
        out = '{"access_token":"t","token_type":"Bearer"}'
        assert json.loads(AuthManager.extract_token_json(out))["token_type"] == "Bearer"

    def test_raises_on_no_json(self):
        with pytest.raises(ValueError):
            AuthManager.extract_token_json("Failed: could not authorize, try again")

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            AuthManager.extract_token_json("")
