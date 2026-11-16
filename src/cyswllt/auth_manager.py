# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC.
# Released under the GNU GPL v3 license.

import configparser
import json
import logging
import os
import re
import shutil
import stat
import subprocess


_CREDENTIAL_TOKEN_RE = re.compile(r"^[A-Za-z0-9._~+/=-]{4,256}$")


def is_valid_oauth_credential(value: object) -> bool:
    """Validate that an OAuth client_id or client_secret is a safe token string.

    Rejects empty values, non-strings, leading hyphens (CWE-88 option injection),
    whitespace, and control characters.
    """
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped or stripped.startswith("-"):
        return False
    return bool(_CREDENTIAL_TOKEN_RE.fullmatch(stripped))


class AuthManager:
    """Manages rclone authentication and Google Drive remote configuration.

    Handles locating the rclone binary, storing custom OAuth credentials,
    running the interactive browser-based OAuth flow, and creating the
    named rclone remote used by MountManager.
    """

    REMOTE_NAME = "cyswllt_gdrive"

    def __init__(self):
        """Initialize the AuthManager with no cached rclone path."""
        self._rclone_path = None

    def get_rclone_path(self) -> str | None:
        """Locate the rclone binary, caching the result after the first lookup.

        Checks the system PATH first via shutil.which, then falls back to common
        installation locations (/usr/bin, /usr/local/bin, /snap/bin).

        Returns:
            The absolute path to the rclone executable, or None if not found.
        """
        if self._rclone_path:
            return self._rclone_path

        # Check standard locations and PATH
        path = shutil.which("rclone")
        if path:
            self._rclone_path = path
            return path

        common_paths = ["/usr/bin/rclone", "/usr/local/bin/rclone", "/snap/bin/rclone"]
        for candidate in common_paths:
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                self._rclone_path = candidate
                return candidate

        return None

    def get_config_dir(self) -> str:
        """Return the path to the Cyswllt configuration directory, creating it if needed.

        The directory is created at ~/.config/cyswllt with 0700 permissions so that
        stored OAuth credentials are only readable by the owning user.

        Returns:
            The absolute path to ~/.config/cyswllt.
        """
        config_dir = os.path.expanduser("~/.config/cyswllt")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, mode=0o700, exist_ok=True)
        return config_dir

    def get_credentials_file(self) -> str:
        """Return the path to the custom OAuth credentials JSON file.

        Returns:
            The absolute path to ~/.config/cyswllt/credentials.json.
        """
        return os.path.join(self.get_config_dir(), "credentials.json")

    def get_rclone_config_file(self) -> str:
        """Return the user's rclone.conf path under ~/.config/rclone."""
        rclone_dir = os.path.expanduser("~/.config/rclone")
        if not os.path.exists(rclone_dir):
            os.makedirs(rclone_dir, mode=0o700, exist_ok=True)
        return os.path.join(rclone_dir, "rclone.conf")

    def save_custom_credentials(self, client_id: str, client_secret: str) -> bool:
        """Persist custom Google OAuth client credentials to disk.

        Writes the credentials as JSON to ~/.config/cyswllt/credentials.json with
        0600 permissions (user read/write only) to protect the client secret.

        Args:
            client_id: The Google OAuth 2.0 Client ID.
            client_secret: The Google OAuth 2.0 Client Secret.

        Returns:
            True if the credentials were saved successfully, False on invalid input or I/O error.
        """
        clean_id = client_id.strip() if isinstance(client_id, str) else ""
        clean_secret = client_secret.strip() if isinstance(client_secret, str) else ""
        if not is_valid_oauth_credential(clean_id) or not is_valid_oauth_credential(clean_secret):
            logging.error("Rejected invalid OAuth credential format.")
            return False

        try:
            creds = {
                "client_id": clean_id,
                "client_secret": clean_secret,
            }
            path = self.get_credentials_file()

            # Write with restrictive permissions (600)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = stat.S_IRUSR | stat.S_IWUSR
            with open(path, "w", opener=lambda p, f: os.open(p, flags, mode)) as file:
                json.dump(creds, file)
            return True
        except Exception as error:
            logging.error(f"Error saving credentials: {error}")
            return False

    def get_custom_credentials(self) -> dict[str, str] | None:
        """Load custom Google OAuth client credentials from disk if present.

        Returns:
            A dict containing 'client_id' and 'client_secret' if both are set and
            valid in the credentials file, or None if the file does not exist,
            is incomplete, or cannot be read.
        """
        path = self.get_credentials_file()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
                if not isinstance(data, dict):
                    return None
                client_id = data.get("client_id")
                client_secret = data.get("client_secret")
                if is_valid_oauth_credential(client_id) and is_valid_oauth_credential(
                    client_secret
                ):
                    return {
                        "client_id": client_id.strip(),
                        "client_secret": client_secret.strip(),
                    }
        except Exception as error:
            logging.error(f"Error loading credentials: {error}")
        return None

    def _persist_remote_credentials(self, creds: dict[str, str]) -> None:
        """Persist validated client_id and client_secret into rclone.conf."""
        client_id = creds.get("client_id", "")
        client_secret = creds.get("client_secret", "")
        if not is_valid_oauth_credential(client_id) or not is_valid_oauth_credential(client_secret):
            return

        conf_path = self.get_rclone_config_file()
        parser = configparser.RawConfigParser()
        if os.path.exists(conf_path):
            parser.read(conf_path, encoding="utf-8")
        if not parser.has_section(self.REMOTE_NAME):
            parser.add_section(self.REMOTE_NAME)
        parser.set(self.REMOTE_NAME, "client_id", client_id)
        parser.set(self.REMOTE_NAME, "client_secret", client_secret)

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = stat.S_IRUSR | stat.S_IWUSR
        with open(
            conf_path,
            "w",
            encoding="utf-8",
            opener=lambda p, f: os.open(p, flags, mode),
        ) as conf_file:
            parser.write(conf_file)

    def is_authenticated(self) -> bool:
        """Check whether the Google Drive rclone remote is already configured.

        Runs ``rclone listremotes`` and checks for ``cyswllt_gdrive:`` in the output.

        Returns:
            True if the remote exists in rclone's configuration, False otherwise.
        """
        rclone_path = self.get_rclone_path()
        if not rclone_path:
            return False

        try:
            result = subprocess.run(
                [rclone_path, "listremotes"], capture_output=True, text=True, check=True
            )
            return f"{self.REMOTE_NAME}:" in result.stdout
        except Exception as error:
            logging.error(f"Error checking authentication: {error}")
            return False

    @staticmethod
    def extract_token_json(output: str) -> str | None:
        """Extract the OAuth token JSON object from ``rclone authorize`` stdout.

        rclone surrounds the JSON token with human-readable instructions; this
        method locates the ``{...}`` block (or accepts output that is already
        pure JSON) and validates that it parses as JSON.

        Args:
            output: Raw stdout captured from ``rclone authorize``.

        Returns:
            The validated JSON string, or None if no valid JSON object was found.
        """
        trimmed = output.strip()
        match = re.search(r"(\{.*\})", trimmed, re.DOTALL)
        candidate = match.group(1) if match else trimmed
        try:
            json.loads(candidate)
            return candidate
        except ValueError:
            return None

    def start_authentication(self) -> bool:
        """Run the interactive rclone OAuth flow and create the Google Drive remote.

        Launches ``rclone authorize drive`` (which opens the user's browser for
        Google sign-in), extracts the resulting OAuth token from stdout, and
        registers the ``cyswllt_gdrive`` remote via ``rclone config create``.
        If custom OAuth credentials have been saved, they are supplied via
        environment variables during authorization and persisted to rclone.conf.

        Returns:
            True if authorization and remote creation succeeded, False otherwise.
        """
        rclone_path = self.get_rclone_path()
        if not rclone_path:
            logging.error("Rclone binary not found.")
            return False

        try:
            logging.info("Starting rclone authorize flow...")
            env = os.environ.copy()
            if "PATH" in env:
                env["PATH"] = f"/usr/bin:/bin:{env['PATH']}"
            else:
                env["PATH"] = "/usr/bin:/bin"

            creds = self.get_custom_credentials()
            if creds:
                logging.info("Using custom Client ID for authorization.")
                env["RCLONE_DRIVE_CLIENT_ID"] = creds["client_id"]
                env["RCLONE_DRIVE_CLIENT_SECRET"] = creds["client_secret"]

            authorize_cmd = [rclone_path, "authorize", "drive"]
            result = subprocess.run(
                authorize_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

            output = result.stdout
            token_json = self.extract_token_json(output)
            if token_json is None:
                logging.error("Could not find valid token JSON in rclone output.")
                logging.debug(f"Output was: {output}")
                return False

            logging.info(f"Configuring remote {self.REMOTE_NAME}...")
            config_cmd = [
                rclone_path,
                "config",
                "create",
                self.REMOTE_NAME,
                "drive",
                f"token={token_json}",
                "config_is_local=false",
            ]
            subprocess.run(config_cmd, capture_output=True, text=True, check=True, env=env)

            if creds:
                self._persist_remote_credentials(creds)

            logging.info("Authentication successful.")
            return True

        except subprocess.CalledProcessError as error:
            stderr_msg = (error.stderr or "").strip()
            logging.exception("Rclone error during authentication (stderr=%s)", stderr_msg)
            return False
        except Exception:
            logging.exception("Unexpected error during authentication")
            return False
