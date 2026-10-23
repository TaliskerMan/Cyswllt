# Plan for Cyswllt
- [x] Untrack sonar-project.properties from GitHub and add to .gitignore

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
