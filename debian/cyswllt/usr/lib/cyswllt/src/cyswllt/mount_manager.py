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
    Manages mounting and unmounting of the Google Drive remote.
    """
    def __init__(self, remote_name):
        self.remote_name = remote_name
        self.mount_point = os.path.expanduser("~/GoogleDrive")

    def is_mounted(self):
        """Checks if the mount point is currently mounted."""
        return os.path.ismount(self.mount_point)

    def _get_desktop_file_path(self):
        return os.path.expanduser("~/Desktop/google-drive.desktop")

    def _create_desktop_file(self):
        """Creates a .desktop file for DING to show the mount."""
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
            with open(desktop_file, "w") as f:
                f.write(content)
            os.chmod(desktop_file, 0o700) # Make executable securely
        except Exception as e:
            logging.error(f"Failed to create desktop file: {e}")

    def _remove_desktop_file(self):
        """Removes the .desktop file."""
        desktop_file = self._get_desktop_file_path()
        if os.path.exists(desktop_file):
            try:
                os.remove(desktop_file)
            except Exception as e:
                logging.error(f"Failed to remove desktop file: {e}")

    def mount(self):
        """Mounts the remote to ~/GoogleDrive."""
        if not os.path.exists(self.mount_point):
            os.makedirs(self.mount_point)

        if self.is_mounted():
            self._create_desktop_file()
            return True

        rclone_path = shutil.which("rclone")
        if not rclone_path:
            logging.error("rclone executable not found")
            return False

        try:
            # We run rclone mount in the background
            # --vfs-cache-mode writes is generally recommended for usability
            subprocess.Popen(
                [
                    rclone_path, "mount", 
                    f"{self.remote_name}:", 
                    self.mount_point,
                    "--vfs-cache-mode", "writes",
                    "--daemon" # Run as daemon so it persists
                ]
            )
            
            # Wait a bit for mount to initialize
            for _ in range(10):
                if self.is_mounted():
                    self._create_desktop_file()
                    return True
                time.sleep(0.5)
            
            return False
            
        except Exception as e:
            logging.error(f"Mount error: {e}")
            return False

    def unmount(self):
        """Unmounts the remote."""
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
            # use fusermount -u
            subprocess.run([fuser_path, "-u", self.mount_point], check=True)
            self._remove_desktop_file()
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Unmount error: {e}")
            return False
