# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC.
# Released under the GNU GPL v3 license.

"""Unit tests for AuthManager token extraction and credential validation."""

import configparser
import os
import subprocess
from unittest.mock import MagicMock, patch

from cyswllt.auth_manager import AuthManager, is_valid_oauth_credential


class TestExtractTokenJson:
    def test_pure_json(self):
        raw = '{"access_token":"abc","token_type":"Bearer","expiry":"2026-01-01T00:00:00Z"}'
        assert AuthManager.extract_token_json(raw) == raw

    def test_json_wrapped_in_rclone_banner(self):
        banner = (
            "Paste the following into your remote machine --->\n"
            '{"access_token":"xyz","refresh_token":"ref"}\n'
            "<---End paste\n"
        )
        assert (
            AuthManager.extract_token_json(banner)
            == '{"access_token":"xyz","refresh_token":"ref"}'
        )

    def test_multiline_pretty_json_in_banner(self):
        banner = 'Header line\n{\n  "access_token": "tok",\n  "expiry": "soon"\n}\nFooter'
        extracted = AuthManager.extract_token_json(banner)
        assert extracted is not None
        assert '"access_token": "tok"' in extracted

    def test_no_json_returns_none(self):
        assert AuthManager.extract_token_json("nothing useful here") is None

    def test_empty_output_returns_none(self):
        assert AuthManager.extract_token_json("") is None
        assert AuthManager.extract_token_json("   \n  ") is None

    def test_malformed_braces_returns_none(self):
        assert AuthManager.extract_token_json("{not: valid json}") is None


class TestCredentialValidationAndAuthFlow:
    def test_is_valid_oauth_credential_accepts_valid_tokens(self):
        assert is_valid_oauth_credential("123456-abcdef.apps.googleusercontent.com")
        assert is_valid_oauth_credential("GOCSPX-abcDEF_1234567890")

    def test_is_valid_oauth_credential_rejects_flag_injection_and_bad_inputs(self):
        assert not is_valid_oauth_credential("--config=/tmp/evil.conf")
        assert not is_valid_oauth_credential("-v")
        assert not is_valid_oauth_credential("")
        assert not is_valid_oauth_credential("   ")
        assert not is_valid_oauth_credential(None)
        assert not is_valid_oauth_credential("bad space")
        assert not is_valid_oauth_credential("bad\nnewline")

    def test_save_and_get_custom_credentials(self, tmp_path):
        mgr = AuthManager()
        with patch.object(mgr, "get_config_dir", return_value=str(tmp_path)):
            assert mgr.save_custom_credentials(
                "123456-abc.apps.googleusercontent.com",
                "GOCSPX-secret_value_123",
            )
            creds = mgr.get_custom_credentials()
            assert creds == {
                "client_id": "123456-abc.apps.googleusercontent.com",
                "client_secret": "GOCSPX-secret_value_123",
            }

            # Reject leading hyphen (CWE-88 argument injection attempt)
            assert not mgr.save_custom_credentials("--evil-flag", "GOCSPX-secret_value_123")

    def test_has_and_clear_custom_credentials(self, tmp_path):
        mgr = AuthManager()
        conf_dir = tmp_path / "cyswllt"
        conf_dir.mkdir()
        rclone_conf = tmp_path / "rclone.conf"
        with (
            patch.object(mgr, "get_config_dir", return_value=str(conf_dir)),
            patch.object(mgr, "get_rclone_config_file", return_value=str(rclone_conf)),
        ):
            assert mgr.has_custom_credentials() is False
            assert mgr.save_custom_credentials(
                "123456-abc.apps.googleusercontent.com",
                "GOCSPX-secret_value_123",
            )
            mgr._persist_remote_credentials(mgr.get_custom_credentials())
            assert mgr.has_custom_credentials() is True

            assert mgr.clear_custom_credentials() is True
            assert mgr.has_custom_credentials() is False
            assert mgr.get_custom_credentials() is None
            parser = configparser.RawConfigParser()
            parser.read(rclone_conf, encoding="utf-8")
            assert not parser.has_option(AuthManager.REMOTE_NAME, "client_id")
            assert not parser.has_option(AuthManager.REMOTE_NAME, "client_secret")

    def test_start_authentication_uses_env_and_persists_rclone_conf(self, tmp_path):
        mgr = AuthManager()
        conf_dir = tmp_path / "cyswllt"
        conf_dir.mkdir()
        rclone_conf = tmp_path / "rclone.conf"

        with (
            patch.object(mgr, "get_rclone_path", return_value="/usr/bin/rclone"),
            patch.object(mgr, "get_config_dir", return_value=str(conf_dir)),
            patch.object(mgr, "get_rclone_config_file", return_value=str(rclone_conf)),
            patch("cyswllt.auth_manager.subprocess.run") as mock_run,
        ):
            mgr.save_custom_credentials(
                "123456-abc.apps.googleusercontent.com",
                "GOCSPX-secret_value_123",
            )
            auth_proc = MagicMock(
                stdout='{"access_token":"tok123","token_type":"Bearer"}',
                stderr="",
            )
            cfg_proc = MagicMock(stdout="", stderr="")
            mock_run.side_effect = [auth_proc, cfg_proc]

            assert mgr.start_authentication() is True
            assert mock_run.call_count == 2

            # Verify client_id and client_secret were NOT passed in CLI argv
            auth_call_args = mock_run.call_args_list[0]
            assert auth_call_args.args[0] == ["/usr/bin/rclone", "authorize", "drive"]
            assert (
                auth_call_args.kwargs["env"]["RCLONE_DRIVE_CLIENT_ID"]
                == "123456-abc.apps.googleusercontent.com"
            )
            assert (
                auth_call_args.kwargs["env"]["RCLONE_DRIVE_CLIENT_SECRET"]
                == "GOCSPX-secret_value_123"
            )

            # Verify persisted to rclone.conf with 0600 permissions
            assert rclone_conf.exists()
            assert (os.stat(rclone_conf).st_mode & 0o777) == 0o600
            parser = configparser.RawConfigParser()
            parser.read(rclone_conf, encoding="utf-8")
            assert (
                parser.get(AuthManager.REMOTE_NAME, "client_id")
                == "123456-abc.apps.googleusercontent.com"
            )
            assert (
                parser.get(AuthManager.REMOTE_NAME, "client_secret")
                == "GOCSPX-secret_value_123"
            )

    def test_start_authentication_handles_called_process_error(self):
        mgr = AuthManager()
        with (
            patch.object(mgr, "get_rclone_path", return_value="/usr/bin/rclone"),
            patch.object(mgr, "get_custom_credentials", return_value=None),
            patch(
                "cyswllt.auth_manager.subprocess.run",
                side_effect=subprocess.CalledProcessError(
                    1, ["/usr/bin/rclone"], stderr="oauth failed"
                ),
            ),
        ):
            assert mgr.start_authentication() is False
