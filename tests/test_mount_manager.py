# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

"""Tests for MountManager: pending-upload detection and mount failure reporting.

A fake ``rclone`` script stands in for the real one, so these run without
Google Drive or FUSE.
"""

import json
import os
import stat

import pytest

from cyswllt import mount_manager
from cyswllt.mount_manager import MountManager, count_pending_uploads


def _meta(path, dirty):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"Size": 3, "Fingerprint": "", "Dirty": dirty}))


def test_count_pending_uploads_counts_only_dirty_files(tmp_path):
    meta = tmp_path / "vfsMeta" / "cyswllt_gdrive"
    _meta(meta / "a.txt", True)
    _meta(meta / "docs" / "b.txt", True)
    _meta(meta / "done.txt", False)
    (meta / "junk.txt").write_text("not json")
    assert count_pending_uploads(str(meta)) == 2


def test_count_pending_uploads_missing_folder(tmp_path):
    assert count_pending_uploads(str(tmp_path / "nope")) == 0


def test_pending_uploads_uses_rclone_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    _meta(tmp_path / "rclone" / "vfsMeta" / "cyswllt_gdrive" / "x", True)
    assert MountManager("cyswllt_gdrive").pending_uploads() == 1


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Home, mount point and rclone log inside tmp_path; fake tools on PATH."""
    monkeypatch.setenv("HOME", str(tmp_path))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    monkeypatch.setenv("PATH", str(bindir))
    monkeypatch.setattr(mount_manager, "RCLONE_LOG_FILE",
                        str(tmp_path / ".cache" / "cyswllt" / "rclone.log"))
    monkeypatch.setattr(mount_manager, "MOUNT_TIMEOUT_SECONDS", 2)
    manager = MountManager("cyswllt_gdrive")
    manager.mount_point = str(tmp_path / "GoogleDrive")
    return manager, bindir


def _tool(bindir, name, script):
    path = bindir / name
    path.write_text("#!/bin/sh\n" + script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_mount_reports_missing_fuse(isolated):
    manager, bindir = isolated
    _tool(bindir, "rclone", "exit 0\n")
    assert manager.mount() is False
    assert "FUSE isn't installed" in manager.last_mount_error


def test_mount_reports_missing_rclone(isolated):
    manager, _bindir = isolated
    assert manager.mount() is False
    assert "rclone isn't installed" in manager.last_mount_error


def test_mount_reports_rclone_error_from_its_log(isolated):
    manager, bindir = isolated
    _tool(bindir, "fusermount3", "exit 0\n")
    # Fake rclone: write an error to the --log-file it was given, then fail.
    _tool(bindir, "rclone",
          'while [ "$1" != "--log-file" ]; do shift; done\n'
          'echo "2026/10/16 ERROR : Fatal error: failed to mount FUSE fs" > "$2"\n'
          "exit 1\n")
    assert manager.mount() is False
    assert "rclone couldn't mount Google Drive" in manager.last_mount_error
    assert "failed to mount FUSE fs" in manager.last_mount_error


def test_mount_times_out_with_a_clear_message(isolated):
    manager, bindir = isolated
    _tool(bindir, "fusermount3", "exit 0\n")
    _tool(bindir, "rclone", "exit 0\n")  # "succeeds" but never mounts
    assert manager.mount() is False
    assert "wasn't mounted after 2 seconds" in manager.last_mount_error


def test_rclone_log_is_owner_only(isolated):
    manager, bindir = isolated
    _tool(bindir, "fusermount3", "exit 0\n")
    _tool(bindir, "rclone", "exit 1\n")
    manager.mount()
    mode = os.stat(mount_manager.RCLONE_LOG_FILE).st_mode & 0o777
    assert mode == 0o600
