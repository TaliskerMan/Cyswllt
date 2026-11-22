# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

# How long to wait for rclone to finish mounting. A first mount can take
# well over 5 seconds while rclone contacts Google Drive.
MOUNT_TIMEOUT_SECONDS = 30

# rclone's own log for the mount, read back to explain a failed mount.
RCLONE_LOG_FILE = os.path.expanduser("~/.cache/cyswllt/rclone.log")

# Conservative allowlist for configured rclone remote identifiers.
_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _allowed_cache_roots() -> tuple[str, str]:
    """Return canonical allowed roots (`$HOME` and system temp dir for test sandboxes)."""
    return (
        os.path.realpath(os.path.expanduser("~")),
        os.path.realpath(tempfile.gettempdir()),
    )


def rclone_cache_root() -> str:
    """Resolve rclone's cache folder (`$XDG_CACHE_HOME/rclone` or `~/.cache/rclone`) safely.

    Change Comment (2026-11-21, CS1-12 / Snyk python/PT CWE-23 / CP-ChangeComments):
    Enforced XDG Base Directory absolute-path validation, `..` segment rejection,
    and canonical `os.path.commonpath` containment under `$HOME` (or temp root in tests).
    """
    home_root, temp_root = _allowed_cache_roots()
    fallback_base = os.path.realpath(os.path.join(home_root, ".cache"))

    raw_value = os.environ.get("XDG_CACHE_HOME", "")
    chosen_base = fallback_base
    if (
        raw_value
        and "\x00" not in raw_value
        and os.path.isabs(raw_value)
        and ".." not in Path(raw_value).parts
    ):
        candidate_base = os.path.realpath(raw_value)
        for allowed_root in (home_root, temp_root):
            if os.path.commonpath([allowed_root, candidate_base]) == allowed_root:
                chosen_base = candidate_base
                break

    cache_real = os.path.realpath(os.path.join(chosen_base, "rclone"))
    if (
        os.path.commonpath([chosen_base, cache_real]) != chosen_base
        or not cache_real.startswith(chosen_base + os.sep)
    ):
        cache_real = os.path.realpath(os.path.join(fallback_base, "rclone"))
    return cache_real


def count_pending_uploads(meta_dir: str) -> int:
    """
    Counts files in an rclone VFS metadata folder that are still waiting to be
    uploaded (``"Dirty": true``). rclone writes one small JSON file per cached
    file under ``vfsMeta/<remote>/`` and clears the flag once the upload has
    finished; this layout exists since rclone 1.53.

    Args:
        meta_dir (str): The ``vfsMeta/<remote>`` folder.

    Returns:
        int: Number of files not yet uploaded (0 if the folder doesn't exist).
    """
    if not meta_dir or "\x00" in meta_dir:
        return 0

    meta_real = os.path.realpath(meta_dir)
    cache_root = os.path.realpath(rclone_cache_root())
    if os.path.commonpath([cache_root, meta_real]) != cache_root:
        return 0

    if not os.path.isdir(meta_real):
        return 0

    pending = 0
    for root, _dirs, files in os.walk(meta_real, followlinks=False):
        root_real = os.path.realpath(root)
        if os.path.commonpath([meta_real, root_real]) != meta_real:
            continue
        for name in files:
            candidate = os.path.join(root_real, name)
            if os.path.islink(candidate):
                continue
            entry_real = os.path.realpath(candidate)
            if (
                not entry_real.startswith(meta_real + os.sep)
                or os.path.commonpath([meta_real, entry_real]) != meta_real
            ):
                continue
            try:
                with open(entry_real, "r", encoding="utf-8") as handle:
                    if json.load(handle).get("Dirty") is True:
                        pending += 1
            except (OSError, ValueError, AttributeError):
                continue  # unreadable or not rclone metadata: ignore
    return pending


class MountManager:
    """
    Manages mounting and unmounting operations for Google Drive storage remotes via rclone.
    """
    def __init__(self, remote_name):
        """
        Initializes the MountManager instance.

        Args:
            remote_name (str): The name of the configured rclone remote (e.g. cyswllt_gdrive).
        """
        if not remote_name or not _REMOTE_NAME_RE.match(remote_name):
            raise ValueError(f"Invalid rclone remote name: {remote_name!r}")
        self.remote_name = remote_name
        self.mount_point = os.path.expanduser("~/GoogleDrive")
        # Human-readable reasons the last mount/unmount failed, for the UI.
        self.last_mount_error = None
        self.last_unmount_error = None

    def pending_uploads(self):
        """
        Number of files copied into the drive that rclone hasn't uploaded yet.

        With ``--vfs-cache-mode full`` writes land in a local cache and upload
        in the background; disconnecting early leaves them in the cache until
        the next connect.
        """
        cache_root = rclone_cache_root()
        meta_real = os.path.realpath(
            os.path.join(cache_root, "vfsMeta", self.remote_name)
        )
        if not meta_real.startswith(cache_root + os.sep):
            return 0
        return count_pending_uploads(meta_real)

    @staticmethod
    def fuse_available():
        """True if a FUSE mount helper (fusermount3 or fusermount) is installed."""
        return bool(shutil.which("fusermount3") or shutil.which("fusermount"))

    @staticmethod
    def _rclone_log_tail(max_lines=6):
        """Last error-looking lines of rclone's log, for error messages."""
        try:
            with open(RCLONE_LOG_FILE, "r", errors="replace") as handle:
                lines = [ln.strip() for ln in handle.readlines() if ln.strip()]
        except OSError:
            return ""
        errors = [ln for ln in lines if "ERROR" in ln or "CRITICAL" in ln
                  or "Fatal" in ln or "fatal" in ln]
        return "\n".join((errors or lines)[-max_lines:])

    def is_mounted(self):
        """
        Checks if the Google Drive remote is currently mounted.

        Returns:
            bool: True if the mount point directory is active, False otherwise.
        """
        return os.path.ismount(self.mount_point)

    def _get_desktop_file_path(self):
        """
        Resolves the file path where the Desktop launcher (.desktop) is located.

        Returns:
            str: Absolute path to the launcher file.
        """
        return os.path.expanduser("~/Desktop/google-drive.desktop")

    def _create_desktop_file(self):
        """
        Creates a local Desktop entry file to allow file managers to access the mounted Drive.
        """
        desktop_file = self._get_desktop_file_path()
        content = f"""[Desktop Entry]
Type=Application
Name=Google Drive
Comment=Mounted Google Drive
Icon=drive-harddisk
Exec=xdg-open "{self.mount_point}"
Terminal=false
Categories=FileManager;
"""
        try:
            # Secure file creation with tight permissions to prevent hijacking
            mode = 0o700
            with open(desktop_file, "w", opener=lambda path, flags: os.open(path, flags, mode)) as f:
                f.write(content)
        except Exception:
            logging.exception("Failed to create desktop file")

    def _remove_desktop_file(self):
        """
        Deletes the local Desktop entry file when Drive unmounts.
        """
        desktop_file = self._get_desktop_file_path()
        if os.path.exists(desktop_file):
            try:
                os.remove(desktop_file)
            except Exception:
                logging.exception("Failed to remove desktop file")

    def mount(self):
        """
        Mounts the remote to the mount point with VFS caching.

        Starts ``rclone mount --daemon`` and waits up to MOUNT_TIMEOUT_SECONDS
        for the mount to appear, stopping early if rclone exits with an error.
        On failure, ``last_mount_error`` explains why (using rclone's log).

        Returns:
            bool: True if mounting succeeded, False on error or timeout.
        """
        self.last_mount_error = None

        if not os.path.exists(self.mount_point):
            os.makedirs(self.mount_point, mode=0o700)

        if self.is_mounted():
            self._create_desktop_file()
            return True

        rclone_path = shutil.which("rclone")
        if not rclone_path:
            self.last_mount_error = (
                "rclone isn't installed. Install it with: sudo apt install rclone"
            )
            logging.error(self.last_mount_error)
            return False

        if not self.fuse_available():
            self.last_mount_error = (
                "FUSE isn't installed, so Google Drive can't be mounted. "
                "Install it with: sudo apt install fuse3"
            )
            logging.error(self.last_mount_error)
            return False

        try:
            # Performance-optimised rclone mount flags:
            #
            # --vfs-cache-mode full
            #   Cache both reads and writes locally. After the first access,
            #   files and directories behave much like a local disk. Writes
            #   upload in the background (see pending_uploads()).
            #
            # --dir-cache-time 72h
            #   Cache directory listings for 72 hours so repeated folder
            #   visits are instant without re-querying Google Drive.
            #
            # --vfs-read-chunk-size 128M
            #   Download data in large 128 MB chunks, significantly speeding
            #   up transfers of large files.
            #
            # --vfs-cache-max-size 10G
            #   Cap the local VFS cache at 10 GB to avoid filling the disk.
            #
            # --daemon
            #   Detach and run as a background daemon so the mount persists
            #   after Cyswllt's process exits.
            #
            # --log-file / --log-level NOTICE
            #   Keep rclone's own messages so a failed mount can be explained.
            from .auth_manager import AuthManager
            auth = AuthManager()
            creds = auth.get_custom_credentials()
            env = os.environ.copy()
            if creds:
                env["RCLONE_DRIVE_CLIENT_ID"] = creds["client_id"]
                env["RCLONE_DRIVE_CLIENT_SECRET"] = creds["client_secret"]

            os.makedirs(os.path.dirname(RCLONE_LOG_FILE), mode=0o700,
                        exist_ok=True)
            # Start each mount with a fresh log so old errors aren't reported.
            with open(RCLONE_LOG_FILE, "w", opener=lambda path, flags:
                      os.open(path, flags, 0o600)) as log_init:
                log_init.write("")
            # rclone's start-up output (e.g. a bad option) goes to a file, not
            # a pipe: with --daemon a background child could hold a pipe open
            # and block the read.
            startup_err_path = RCLONE_LOG_FILE + ".startup"
            startup_err = open(startup_err_path, "w", opener=lambda path, flags:
                               os.open(path, flags, 0o600))

            process = subprocess.Popen(
                [
                    rclone_path, "mount",
                    f"{self.remote_name}:",
                    self.mount_point,
                    "--cache-dir", rclone_cache_root(),
                    "--vfs-cache-mode", "full",
                    "--dir-cache-time", "72h",
                    "--vfs-read-chunk-size", "128M",
                    "--vfs-cache-max-size", "10G",
                    "--log-file", RCLONE_LOG_FILE,
                    "--log-level", "NOTICE",
                    "--daemon"
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=startup_err,
            )
            startup_err.close()  # the child has its own copy

            return self._wait_for_mount(process, startup_err_path)

        except Exception as error:
            self.last_mount_error = f"Mount error: {error}"
            logging.error(self.last_mount_error)
            return False

    def _read_startup_err(self, startup_err_path: str) -> str:
        try:
            with open(startup_err_path, "r", errors="replace") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    def _wait_for_mount(self, process, startup_err_path: str) -> bool:
        deadline = time.monotonic() + MOUNT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self.is_mounted():
                self._create_desktop_file()
                return True
            code = process.poll()
            if code not in (None, 0):
                startup = self._read_startup_err(startup_err_path)
                detail = self._rclone_log_tail() or startup[-1500:]
                self.last_mount_error = (
                    "rclone couldn't mount Google Drive."
                    + (f"\n\n{detail}" if detail else "")
                )
                logging.error(self.last_mount_error)
                return False
            time.sleep(0.5)

        detail = self._rclone_log_tail()
        self.last_mount_error = (
            f"Google Drive wasn't mounted after {MOUNT_TIMEOUT_SECONDS} "
            "seconds. Check your internet connection and try again."
            + (f"\n\n{detail}" if detail else "")
        )
        logging.error(self.last_mount_error)
        return False

    def unmount(self):
        """
        Unmounts the remote Google Drive filesystem.

        Calls fusermount or fusermount3 depending on availability, then cleans up
        the Desktop entry launcher.

        Returns:
            bool: True if unmounting succeeded, False on error.
        """
        self.last_unmount_error = None

        if not self.is_mounted():
            self._remove_desktop_file()
            return True

        fuser_path = shutil.which("fusermount") or shutil.which("fusermount3")
        if not fuser_path:
            self.last_unmount_error = "fusermount executable not found."
            logging.error(self.last_unmount_error)
            return False

        try:
            subprocess.run([fuser_path, "-u", self.mount_point],
                           check=True, capture_output=True, text=True)
            self._remove_desktop_file()
            return True
        except subprocess.CalledProcessError as error:
            # A normal unmount usually fails because files are still open.
            # Fall back to a lazy unmount (-uz), which detaches the filesystem
            # and cleans up once the open handles are released.
            logging.warning(
                "Normal unmount failed (%s); attempting lazy unmount (-uz).",
                (error.stderr or "").strip() or error,
            )
            try:
                subprocess.run([fuser_path, "-uz", self.mount_point],
                               check=True, capture_output=True, text=True)
                self._remove_desktop_file()
                return True
            except subprocess.CalledProcessError as error_secondary:
                detail = ((error_secondary.stderr or error.stderr or "").strip())
                self.last_unmount_error = (
                    "Could not unmount Google Drive — files may still be open. "
                    + (detail or "Close any apps using the drive and try again.")
                )
                logging.error(self.last_unmount_error)
                return False
