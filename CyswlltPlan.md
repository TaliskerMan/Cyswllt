# Cyswllt Plan

## Work Done
-   Initialized project structure.
-   Created `LICENSE` (GPLv3) and `README.md`.
-   Generated application icon.
-   Selected `rclone` as the backend for Google Drive mounting.

## Completed Work
-   [x] Implement basic GTK4 + Libadwaita window (`main.py`, `window.py`).
-   [x] Implement `AuthManager` to handle `rclone config` for Google Drive.
-   [x] Implement `MountManager` to handle `rclone mount`.
-   [x] Add "Connect" / "Disconnect" UI logic.
-   [x] Create `.desktop` file for DING integration.
-   [x] Verify end-to-end functionality.
-   [x] Fix `GLib-GIO-CRITICAL` launch error.
-   [x] Fix Icon resolution issues (About dialog, AppGrid).
-   [x] Add "Help" documentation to UI.

## Future Work
-   [ ] Publish source to GitHub.
-   [ ] Create public release.
-   [ ] Add more detailed error handling for rclone failures.

## Security Hardening
-   [x] Rectify Permission vulnerabilities and subprocess execution flaws (File permissions tightened, subprocess lists verified).
-   [x] Implement application-wide structured execution logging to `~/.cache/cyswllt/cyswllt.log` with strict `0o600` permissions.
-   [x] Reassign copyright metadata and emails throughout all source code and UI interfaces to `chuck@nordheim.online`.
-   [x] Remediate automated repository packaging builds by switching `debsign` keys to `chuck@nordheim.online`, injecting detached GPG artifact generation (`.asc`), and publishing the pubkey.

## Release History

### Release 0.1.15 (Pending)
-   **Security**: Comprehensive security audit and hardening (file permissions tightened, logs secured).

## Release History

### Release 0.1.9 (2026-02-16)
-   **Documentation**: Added application icon to README.md.
-   **Release**: Automated build, sign, and hash process for GitHub release.
-   **GitHub**: Enabled Discussions and updated repository description.

### Release 0.1.8 (2026-02-16)
-   **New Feature**: Added "Help" button with usage instructions.
-   **Fix**: Added `StartupNotify=true` to desktop file to fix launch tracking in GNOME/Wayland.

### Release 0.1.7 (2026-02-16)
-   **Fix**: Resized application icon to 256x256 to match install directory requirements.
-   **Fix**: Added `postinst` script to force icon cache update (`gtk-update-icon-cache`).
-   **Fix**: Improved icon resolution in `main.py` by adding local path to `Gtk.IconTheme`.

### Release 0.1.6 (2026-02-16)
-   **Fix**: Resolved `GLib-GIO-CRITICAL` error by implementing `HANDLES_COMMAND_LINE` in `Gtk.Application`.
-   **Fix**: Fixed `NameError` (missing Gdk import) and markup errors in About dialog.

### Release 0.1.5 (2026-02-16)
-   Bumped version to 0.1.5
-   Built and signed DEB package

### Release 0.1.4 (2026-02-16)
-   Bumped version to 0.1.4
-   Built and signed DEB package

### Release 0.1.3 (2026-02-16)
-   Bumped version to 0.1.3
-   Built and signed DEB package

### Release 0.1.2 (2026-02-16)
-   Bumped version to 0.1.2
-   Built and signed DEB package

### Release 0.1.1 (2026-02-16)
-   Bumped version to 0.1.1
-   Built and signed DEB package
