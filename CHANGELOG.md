# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- **Custom Client ID now binds at sign-in:** `rclone authorize drive` receives
  the user's Client ID/Secret as positional arguments (rclone does not read the
  `RCLONE_DRIVE_*` env vars at the authorize step), and the credentials are also
  written into the remote via `config create`. Previously the headline
  "Performance Settings" feature silently did nothing during the OAuth handshake.
- **"Run from Source" actually works:** added a `pyproject.toml` console-script
  entry point (`cyswllt`) and a `__main__.py`, and corrected the README command
  (`pip install . && cyswllt`, or `PYTHONPATH=src python3 -m cyswllt`). The old
  `python3 src/cyswllt/main.py` raised `ModuleNotFoundError`.
- **Desktop launcher uses `xdg-open`** instead of hardcoded `nautilus`, so the
  mounted-drive icon opens on KDE/XFCE and other desktops.
- **Unmount failures are now visible:** a busy unmount falls back to a lazy
  unmount (`-uz`) and, if it still fails, surfaces a clear dialog instead of only
  logging.
- **Status checks no longer block the UI thread** on launch; they run on a worker
  thread and update via `GLib.idle_add`.

### Added
- pytest suite covering credential round-trips, empty-input rejection, and the
  token-extraction regex; plus a smoke-import test. CI workflow runs them.
- Documented that the rclone OAuth token at rest (`~/.config/rclone/rclone.conf`)
  is unencrypted by default, with how to enable encryption.

### Changed
- Standardized attribution on "Chuck Talk, Nordheim Online, LLC
  <chuck@nordheim.online>" across source headers, README, SECURITY.md,
  debian/copyright, and the About dialog.
- Repo hygiene: added `.gitignore`; release artifacts, `venv/`, `.DS_Store`, and
  generated Debian build outputs are no longer tracked.

## [0.1.18] - 2026-06-10
### Added
- Standardized custom App Icons generation natively.
- Integrated automated `build_release.sh` release script for debuild packaging, debsign signing, and GPG detached signature generation.
- Dynamic HELP panel dialog instructions inside UI.

### Hardened
- Switched `debsign` signature keys and copyright metadata throughout code to `chuck@nordheim.online`.
- Enforced strict `0o700` permissions on mount folders and log caches, and `0o600` on cyswllt.log file.
- Prevented desktop generation race conditions using `os.open` with `0o700` locks.
- Replaced `rclone` CLI arg passthrough for `client_secret` with environment variables to prevent process-level secret leakage.
- Switched default WebDAV client credentials to env parameters.
