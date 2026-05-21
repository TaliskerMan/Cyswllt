# Copyright (C) 2026 Chuck Talk <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

import subprocess
import json
import logging
import shutil
import os
import re

# Path where the user's custom Google API credentials are stored.
_CREDENTIALS_FILE = os.path.expanduser("~/.config/cyswllt/google_credentials.json")


class AuthManager:
    """
    Manages authentication with Google Drive via rclone.

    Optionally uses a user-supplied Google OAuth Client ID and Secret to
    bypass rclone's shared, heavily rate-limited credentials.  When custom
    credentials are present they are passed to both ``rclone authorize`` and
    ``rclone config create`` so the resulting remote is fully associated with
    the private Client ID.
    """
    REMOTE_NAME = "cyswllt_gdrive"

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Custom credential helpers
    # ------------------------------------------------------------------

    def get_custom_credentials(self):
        """
        Returns the stored custom Client ID and Secret as a dict
        ``{"client_id": "...", "client_secret": "..."}`` or ``None`` if
        no credentials have been saved yet.
        """
        if not os.path.exists(_CREDENTIALS_FILE):
            return None
        try:
            with open(_CREDENTIALS_FILE, "r") as f:
                data = json.load(f)
            if data.get("client_id") and data.get("client_secret"):
                return data
        except Exception as e:
            logging.error(f"Failed to read credentials file: {e}")
        return None

    def save_custom_credentials(self, client_id: str, client_secret: str) -> bool:
        """
        Persists the user's custom Google OAuth credentials to disk.

        Returns ``True`` on success, ``False`` on failure.
        """
        client_id = client_id.strip()
        client_secret = client_secret.strip()
        if not client_id or not client_secret:
            logging.error("save_custom_credentials: client_id and client_secret must not be empty")
            return False
        try:
            os.makedirs(os.path.dirname(_CREDENTIALS_FILE), exist_ok=True)
            with open(_CREDENTIALS_FILE, "w") as f:
                json.dump({"client_id": client_id, "client_secret": client_secret}, f)
            os.chmod(_CREDENTIALS_FILE, 0o600)  # owner read/write only
            logging.info("Custom Google credentials saved.")
            return True
        except Exception as e:
            logging.error(f"Failed to save credentials: {e}")
            return False

    def clear_custom_credentials(self) -> bool:
        """
        Removes any stored custom Google OAuth credentials.

        Returns ``True`` on success (or if the file did not exist).
        """
        if not os.path.exists(_CREDENTIALS_FILE):
            return True
        try:
            os.remove(_CREDENTIALS_FILE)
            logging.info("Custom Google credentials cleared.")
            return True
        except Exception as e:
            logging.error(f"Failed to clear credentials: {e}")
            return False

    def has_custom_credentials(self) -> bool:
        """Returns ``True`` if valid custom credentials are on disk."""
        return self.get_custom_credentials() is not None

    # ------------------------------------------------------------------
    # rclone helpers
    # ------------------------------------------------------------------

    def is_rclone_installed(self):
        """Checks if rclone is installed/available in PATH."""
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            return False
        try:
            subprocess.run(
                [rclone_path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def is_authenticated(self):
        """Checks if the remote is already configured."""
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            return False
        try:
            result = subprocess.run(
                [rclone_path, "listremotes"],
                capture_output=True,
                text=True,
                check=True,
            )
            return f"{self.REMOTE_NAME}:" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def start_authentication(self):
        """
        Starts the OAuth authentication flow via ``rclone authorize``.

        If custom credentials are stored they are injected into the
        ``rclone authorize`` call so that Google uses the private Client ID
        rather than rclone's shared one.  The resulting token is then used
        to create (or overwrite) the rclone remote, also tagged with the
        custom Client ID/Secret when available.

        This is a blocking call — run it from a background thread.
        """
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            logging.error("Rclone not found in PATH")
            return False

        creds = self.get_custom_credentials()
        if creds:
            logging.info(
                "Using custom Google Client ID for authentication "
                "(bypasses rclone shared rate limits)."
            )
        else:
            logging.info(
                "No custom Google Client ID found — using rclone's default "
                "shared credentials.  Consider adding your own Client ID in "
                "Settings → Performance for faster connections."
            )

        try:
            logging.info("Starting authorization...")

            # Build the authorize command.  When custom credentials are
            # available we pass them via --client-id / --client-secret so
            # that the resulting token is bound to the private application.
            authorize_cmd = [rclone_path, "authorize", "drive"]
            if creds:
                authorize_cmd += [
                    "--client-id", creds["client_id"],
                    "--client-secret", creds["client_secret"],
                ]

            result = subprocess.run(
                authorize_cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            output = result.stdout.strip()

            # rclone prints the JSON token somewhere in stdout — extract it.
            match = re.search(r'(\{.*\})', output, re.DOTALL)
            if not match:
                try:
                    json.loads(output)
                    token_json = output
                except json.JSONDecodeError:
                    raise Exception("Could not find token JSON in rclone authorize output")
            else:
                token_json = match.group(0)

            # Validate the token is parseable JSON before proceeding.
            json.loads(token_json)

            logging.info(f"Token received.  Configuring remote '{self.REMOTE_NAME}'...")

            # Build the config create command.  Mirror the Client ID/Secret
            # into the remote config so every future rclone call uses them.
            config_cmd = [
                rclone_path, "config", "create",
                self.REMOTE_NAME, "drive",
                f"token={token_json}",
                "config_is_local=false",
            ]
            if creds:
                config_cmd += [
                    f"client_id={creds['client_id']}",
                    f"client_secret={creds['client_secret']}",
                ]

            subprocess.run(config_cmd, check=True, capture_output=True)
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"Rclone error: {e}")
            if e.stderr:
                logging.error(f"Stderr: {e.stderr}")
            return False
        except Exception as e:
            logging.error(f"Auth error: {e}")
            return False

    def delete_remote(self):
        """Removes the remote configuration."""
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            return False
        try:
            subprocess.run(
                [rclone_path, "config", "delete", self.REMOTE_NAME],
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
