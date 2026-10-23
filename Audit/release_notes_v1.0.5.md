# Cyswllt v1.0.5 Official Release

Official Linux release of **Cyswllt** (Linux Cloud Storage Mounter & Manager).

This release has undergone rigorous quality-gate validation and multi-scanner security auditing prior to production release, achieving full pass status across test suites, Grype vulnerability scans, and Syft CycloneDX SBOM analysis.

## Highlights & Enhancements
- **Official Linux Release Pipeline**: Clean Debian package (`cyswllt_1.0.5-1_all.deb`), GPG detached ASCII-armored signing (`cyswllt_1.0.5-1_all.deb.asc`) with maintainer key `Chuck Talk <chuck@nordheim.online>`, SHA-512 checksum verification, and NOBuilds distribution archive.
- **Robust Mount Error Reporting**: Added preemptive FUSE availability checks, extended mount detection timeout to 30 seconds with early exit on rclone process termination, and surfaced detailed actionable error dialogs backed by clean rclone logs (`~/.cache/cyswllt/rclone.log`, `0600`).
- **Graceful Upload Handling on Disconnect**: Checked rclone VFS metadata (`vfsMeta/<remote>`) dirty flags to identify files pending background upload prior to unmount. Provided interactive "Stay Connected" and "Disconnect Anyway" actions.
- **Lazy Unmount Fallback**: Implemented graceful fallback to `fusermount3 -uz` when files or terminal handles keep mount points busy.
- **FUSE Package Dependency**: Explicitly added `fuse3 | fuse` as a package dependency to ensure seamless installation across Debian/Ubuntu derivatives.
- **Launcher CLI Passthrough**: Fixed launcher script argument forwarding (`"$@"`) to ensure CLI flags pass cleanly to the core application.
- **Desktop Launcher & UI Polish**: Corrected desktop launcher generation using `xdg-open` and clean application icons across all standard hicolor dimensions (32x32 to 512x512).
- **User Guide Verification**: Verified all claims in `docs/guide/Cyswllt_User_Guide.md` and compiled `docs/Cyswllt_User_Guide.pdf` against the active codebase.

## Security & Supply Chain Verification
- **Unit & Smoke Tests (`pytest`)**: 19/19 tests passed cleanly
- **Grype**: 0 vulnerabilities detected in CycloneDX SBOM
- **Permissions**: Strict `0600` permissions on authentication and cache files

## Artifacts & Checksums
- `cyswllt_1.0.5-1_all.deb` (Official Debian release package)
- `cyswllt_1.0.5-1_all.deb.asc` (Detached GPG signature by Chuck Talk `chuck@nordheim.online`)
- `cyswllt_1.0.5-1_all.deb.sha512` (SHA-512 checksum)
- `checksums.sha512` / `SHA512SUMS` (Multi-file checksum manifest)
- `chuck_pubkey.asc` / `pubkey.asc` (Public GPG key for detached signature verification)
- `SBOM-Linux.json` (CycloneDX Software Bill of Materials for Linux)
- `Cyswllt_User_Guide.pdf` (User documentation)
- `cyswllt_source.tar.gz` (Source code archive)
- `security_report.md` (Full security and vulnerability audit report)
