# Plan for Cyswllt
- [x] Untrack sonar-project.properties from GitHub and add to .gitignore

## Release v1.0.8: SonarQube Cloud `python:S3776` Quality Gate Remediation (2026-11-22)
- [x] Extract `_resolve_vfs_meta_dir()`, `_is_dirty_vfs_meta_entry()`, and `_count_dirty_entries_in_dir()` in `src/cyswllt/mount_manager.py` to lower `count_pending_uploads()` Cognitive Complexity below `15` while maintaining `0` Snyk Code issues.
- [x] Verify `pytest` (`26/26`), `ruff`, and `snyk code test` (`0` issues), increment version to `1.0.8`, and verify SonarQube Cloud Quality Gate `OK`.

## Release v1.0.7: Snyk Code Path Traversal Remediation (`CS1-12`, 2026-11-21)
- [x] Create branch `fix/CS1-12-snyk-path-traversal` from `origin/main` (`7603d21`).
- [x] Harden `rclone_cache_root()`, `MountManager`, and `count_pending_uploads()` in `src/cyswllt/mount_manager.py` against `python/PT` (`CWE-23`) via `os.path.commonpath` containment, strict `remote_name` allowlist, and `followlinks=False`.
- [x] Add regression unit tests in `tests/test_mount_manager.py` and verify `pytest`, `ruff`, and `snyk code test` (`0` issues).
- [x] Auto-increment version to `1.0.7` across `src/cyswllt/version.py`, `debian/changelog`, `docs/guide/`, `sonar-project.properties`, `CHANGELOG.md`, and `Audit/security_report.md`, then open GitHub Pull Request for `CS1-12`.

## Official Linux Release v1.0.5 (2026-10-23)
- [x] Phase 1: Environment & Test Validation
  - [x] Run pytest unit & smoke test suites (19/19 passing)
  - [x] Verify GTK4 / Libadwaita bindings and rclone FUSE integration
- [x] Phase 2: Build Pipeline & Packaging Fixes
  - [x] Add `--no-bump` support to `build_release.sh` to allow deterministic builds without incrementing
  - [x] Fix launcher script argument forwarding in `debian/rules` (`"$$@"`) so CLI arguments pass properly
  - [x] Build Debian package (`cyswllt_1.0.5-1_all.deb`) using `debuild -us -uc` without elevated privileges
- [x] Phase 3: Cryptographic Integrity & Supply Chain Audit
  - [x] Generate Syft CycloneDX SBOM (`Audit/SBOM-Linux.json`, `Audit/SBOM-Linux`, `Audit/sbom.json`) per `CP-SBOM`
  - [x] Scan SBOM with Grype (0 vulnerabilities) per `CP-SecurityAudit`
  - [x] GPG detached ASCII-armored signing (`.deb.asc`) with Chuck Talk's key (`chuck@nordheim.online`, Key ID `D60BA098CDA22A20BD8BB6834E99214B22CFEE40`) per `L-DEB-Packaging`
  - [x] Export GPG public keys (`chuck_pubkey.asc`, `pubkey.asc`) per `L-Release`
  - [x] Compute SHA-512 hashes (`cyswllt_1.0.5-1_all.deb.sha512`, `checksums.sha512`, `SHA512SUMS`)
  - [x] Author comprehensive security report (`Audit/security_report.md`)
- [x] Phase 4: Distribution & Release
  - [x] Stage complete release archive in `/home/freecode/NOBuilds/Cyswllt-10-23-2026-1.0.5-1/`
  - [x] Upload signed packages, checksums, SBOM, and security reports to GitHub Release `v1.0.5`
  - [x] Commit and push changes to GitHub repository
