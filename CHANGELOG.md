# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.9] - 2026-11-27

### Fixed & Hardened
- **Performance Settings Credential Helpers (`src/cyswllt/auth_manager.py`):** Restored `AuthManager.has_custom_credentials()` and `AuthManager.clear_custom_credentials()` (plus automatic removal of custom `client_id` / `client_secret` keys from `rclone.conf` upon clearing) so opening **Menu → Performance Settings** or clearing saved credentials never raises `AttributeError` (`27/27` `pytest` passing).
- **Documentation & Guide Builder Alignment (`README.md`, `docs/guide/`):** Corrected the custom OAuth credentials filename from `google_credentials.json` to `credentials.json`, documented rotated `0600` logs (`~/.cache/cyswllt/cyswllt.log` and `rclone.log`), fixed the default 512×512 PNG icon path in `docs/guide/build_guide.js` and `install.sh`, and regenerated `docs/Cyswllt_User_Guide.pdf` for `v1.0.9`.
- **Standardized Linux Release Pipeline (`build_release.sh`):** Updated `build_release.sh` to generate path-sanitized CycloneDX SBOMs (`Audit/SBOM-Linux.json`, `Audit/SBOM-Linux`, `Audit/sbom.json`), non-interactive GPG detached signatures (`chuck@nordheim.online`), basename-clean SHA-512/SHA-256 checksums, and full `~/NOBuilds/Cyswllt-11-27-2026-1.0.9-1/` archiving.

## [1.0.8] - 2026-11-22

### Quality & Maintainability
- **SonarQube Cloud Quality Gate Remediation (`python:S3776`):** Extracted `_resolve_vfs_meta_dir()`, `_is_dirty_vfs_meta_entry()`, and `_count_dirty_entries_in_dir()` helpers in `src/cyswllt/mount_manager.py`, reducing `count_pending_uploads()` Cognitive Complexity from `22` to `4` while preserving canonical `rclone_cache_root()` containment (`0` Snyk Code issues, `26/26` pytest passing).

## [1.0.7] - 2026-11-21

### Security & Hardening
- **Snyk Code Path Traversal Remediation (`CS1-12`, `2 × python/PT`, `CWE-23`):** Hardened `rclone_cache_root()`, `MountManager.__init__()`, `MountManager.pending_uploads()`, and `count_pending_uploads()` in `src/cyswllt/mount_manager.py` with XDG Base Directory absolute-path validation, `..` rejection, `os.path.commonpath` containment under `$HOME` (or isolated test temp sandboxes), strict `remote_name` allowlist (`^[A-Za-z0-9_-]+$`), and `followlinks=False` symlink-safe `vfsMeta` inspection. Verified `0` open issues in `snyk code test` (`v1.1309.0`).
- **Regression Tests:** Added XDG traversal, unsafe `remote_name`, and `vfsMeta` symlink-escape tests in `tests/test_mount_manager.py`.

## [1.0.5] - 2026-10-16

### Fixed — claims vs code review & shift-left hardening (2026-10-16)
- **Mount failures are reported.** A failed mount (FUSE missing, rclone error,
  slow network) silently returned to "Ready to Connect". Cyswllt now checks for
  FUSE first, waits up to 30 seconds (was 5), stops early if rclone exits with
  an error, keeps rclone's log (`~/.cache/cyswllt/rclone.log`, owner-only) and
  shows the reason in a dialog. A failed Google sign-in is reported too.
- **Disconnect waits for uploads.** With rclone's full write cache, files copied
  into the drive upload in the background; disconnecting early left them only
  in the local cache. Disconnect now shows "Finishing uploads…" with the count
  (from rclone's cache metadata) and disconnects when they're done, with "Stay
  Connected" and "Disconnect Anyway" choices.
- **FUSE is a package dependency** (`fuse3 | fuse`); rclone's package doesn't
  pull it in, and mounting can't work without it.
- **About window icon.** It asked for an icon named `noln` that isn't
  installed, so About showed a broken image.
- **App icon.** The icon carried an image-generator watermark (✦) and was a
  175 px image installed as 256×256. It's now cleaned from the 1024 px artwork,
  rounded, and installed at 512, 256, 128, 64, 48 and 32 px.
- **Credentials file** is created owner-only (0600) from the start; it was
  briefly readable by other users before being restricted.
- **Release checksums verify.** `checksums.sha512` named the package as
  `artifacts/…`, so `sha512sum -c` failed for users; it now uses the file name.
- **Releases can't go out unsigned.** A failed GPG signature was ignored
  (`|| true`); it now stops the build.
- **SonarQube & Shift-Left Gate Compliance:** Resolved cognitive complexity
  thresholds in `main.py` and `mount_manager.py`, eliminated empty blocks,
  standardized exception logging (`S8572`), refactored `build_guide.js`
  to eliminate regex backtracking and modernize promises (`S7785`).
- The repository's desktop file no longer contains developer-machine paths.
- README: the desktop launcher needs a desktop that shows icons.

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
