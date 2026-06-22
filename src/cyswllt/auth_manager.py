# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
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
        """
        Initializes the AuthManager instance.
        """
        pass

    # ------------------------------------------------------------------
    # Custom credential helpers
    # ------------------------------------------------------------------

    def get_custom_credentials(self):
        """
        Returns the stored custom Client ID and Secret as a dict.

        Returns:
            dict: Custom credentials dictionary `{"client_id": "...", "client_secret": "..."}`,
                  or `None` if credentials file doesn't exist or is invalid.
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

        Args:
            client_id (str): The Google Cloud Client ID string.
            client_secret (str): The Google Cloud Client Secret string.

        Returns:
            bool: True on success, False on failure. Saves configuration to
                  ~/.config/cyswllt/google_credentials.json with strict 0o600 permissions.
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
        Removes any stored custom Google OAuth credentials from disk.

        Returns:
            bool: True on success or if the file was already absent, False on error.
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
        """
        Checks if valid custom credentials exist on disk.

        Returns:
            bool: True if Client ID and Secret exist, False otherwise.
        """
        return self.get_custom_credentials() is not None

    # ------------------------------------------------------------------
    # rclone helpers
    # ------------------------------------------------------------------

    def is_rclone_installed(self):
        """
        Checks if rclone is installed and available in the system PATH.

        Returns:
            bool: True if installed and responds to version query, False otherwise.
        """
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
        """
        Checks if the custom Cyswllt remote is already configured in rclone.

        Returns:
            bool: True if the remote cyswllt_gdrive is configured, False otherwise.
        """
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

    @staticmethod
    def extract_token_json(output: str) -> str:
        """
        Extracts the OAuth token JSON object from rclone authorize stdout.

        rclone surrounds the token with human-readable text, so we pull the first
        ``{...}`` block; if none is found we treat the whole output as the
        candidate. The candidate is validated as JSON before being returned.

        Args:
            output (str): Raw stdout from ``rclone authorize``.

        Returns:
            str: The token JSON string.

        Raises:
            ValueError: If no valid JSON token can be extracted.
        """
        text = (output or "").strip()
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        candidate = match.group(0) if match else text
        # Raises json.JSONDecodeError (a ValueError subclass) on malformed input.
        json.loads(candidate)
        return candidate

    def start_authentication(self):
        """
        Starts the Google Drive OAuth flow using rclone authorize.

        Launches the authentication web page. If custom credentials exist, they
        are injected. Once the token is returned, configures the cyswllt_gdrive remote.
        This is a blocking call and must be executed in a worker thread.

        Returns:
            bool: True if authentication succeeded and remote was created, False otherwise.
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

            # Build the authorize command.  rclone's `authorize` subcommand takes
            # the client id/secret as POSITIONAL arguments
            # (`rclone authorize drive <client_id> <client_secret>`); it does not
            # read the RCLONE_DRIVE_* backend env vars at this step.  Passing them
            # positionally is what actually binds the user's private Client ID at
            # sign-in, so they avoid the shared rate limits during the OAuth
            # handshake.  We also keep the env vars set for any downstream calls.
            authorize_cmd = [rclone_path, "authorize", "drive"]
            env = os.environ.copy()
            if creds:
                authorize_cmd += [creds["client_id"], creds["client_secret"]]
                env["RCLONE_DRIVE_CLIENT_ID"] = creds["client_id"]
                env["RCLONE_DRIVE_CLIENT_SECRET"] = creds["client_secret"]

            result = subprocess.run(
                authorize_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

            # rclone prints the JSON token somewhere in stdout — extract + validate it.
            token_json = self.extract_token_json(result.stdout)

            logging.info(f"Token received.  Configuring remote '{self.REMOTE_NAME}'...")

            # Build the config create command.  Write the Client ID/Secret
            # directly into the remote config (not just via env) so every future
            # rclone call against this remote uses the private credentials.
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

            subprocess.run(config_cmd, check=True, capture_output=True, env=env)
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
        """
        Deletes the configured cyswllt_gdrive remote from the rclone configuration.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
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
