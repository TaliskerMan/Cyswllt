# Copyright (C) 2026 Chuck Talk <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

import subprocess
import shutil
import logging
import os
import time

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
        self.remote_name = remote_name
        self.mount_point = os.path.expanduser("~/GoogleDrive")

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
Exec=nautilus "{self.mount_point}"
Terminal=false
Categories=FileManager;
"""
        try:
            # Secure file creation with tight permissions to prevent hijacking
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            mode = 0o700
            with open(desktop_file, "w", opener=lambda path, flags: os.open(path, flags, mode)) as f:
                f.write(content)
        except Exception as e:
            logging.error(f"Failed to create desktop file: {e}")

    def _remove_desktop_file(self):
        """
        Deletes the local Desktop entry file when Drive unmounts.
        """
        desktop_file = self._get_desktop_file_path()
        if os.path.exists(desktop_file):
            try:
                os.remove(desktop_file)
            except Exception as e:
                logging.error(f"Failed to remove desktop file: {e}")

    def mount(self):
        """
        Mounts the remote to the mount point with VFS caching.

        Spawns rclone in a daemon thread. Wait loops for up to 5 seconds to verify
        that mounting succeeded before adding the Desktop entry launcher.

        Returns:
            bool: True if mounting succeeded, False on error or timeout.
        """
        if not os.path.exists(self.mount_point):
            os.makedirs(self.mount_point, mode=0o700)

        if self.is_mounted():
            self._create_desktop_file()
            return True

        rclone_path = shutil.which("rclone")
        if not rclone_path:
            logging.error("rclone executable not found")
            return False

        try:
            # Performance-optimised rclone mount flags:
            #
            # --vfs-cache-mode full
            #   Cache both reads and writes locally. After the first access,
            #   files and directories behave much like a local disk.
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
            from .auth_manager import AuthManager
            auth = AuthManager()
            creds = auth.get_custom_credentials()
            env = os.environ.copy()
            if creds:
                env["RCLONE_DRIVE_CLIENT_ID"] = creds["client_id"]
                env["RCLONE_DRIVE_CLIENT_SECRET"] = creds["client_secret"]

            subprocess.Popen(
                [
                    rclone_path, "mount",
                    f"{self.remote_name}:",
                    self.mount_point,
                    "--vfs-cache-mode", "full",
                    "--dir-cache-time", "72h",
                    "--vfs-read-chunk-size", "128M",
                    "--vfs-cache-max-size", "10G",
                    "--daemon"
                ],
                env=env
            )

            # Wait up to 5 seconds for the mount to initialise
            for _ in range(10):
                if self.is_mounted():
                    self._create_desktop_file()
                    return True
                time.sleep(0.5)

            logging.error("Mount timed out — rclone daemon did not mount in time")
            return False

        except Exception as e:
            logging.error(f"Mount error: {e}")
            return False

    def unmount(self):
        """
        Unmounts the remote Google Drive filesystem.

        Calls fusermount or fusermount3 depending on availability, then cleans up
        the Desktop entry launcher.

        Returns:
            bool: True if unmounting succeeded, False on error.
        """
        if not self.is_mounted():
            self._remove_desktop_file()
            return True

        fuser_path = shutil.which("fusermount")
        if not fuser_path:
            fuser_path = shutil.which("fusermount3")

        if not fuser_path:
            logging.error("fusermount executable not found")
            return False

        try:
            subprocess.run([fuser_path, "-u", self.mount_point], check=True)
            self._remove_desktop_file()
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Unmount error: {e}")
            return False
