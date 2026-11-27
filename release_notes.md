# Cyswllt v1.0.9 Official Linux Release

**Cyswllt** (Welsh for *"Connect"*, pronounced *Kuh-swill-it*) is a GTK4 + Libadwaita Linux desktop application that mounts and unmounts your Google Drive locally at `~/GoogleDrive` via `rclone` and `FUSE`, with background VFS write-caching, safe pending-upload disconnect protection, and optional custom Google OAuth Client ID support.

## What's Changed Since v1.0.5 (`v1.0.6` – `v1.0.9`)
- **Snyk Code Path Traversal Hardening (`CS1-12`, `CWE-23`):** Added canonical XDG Base Directory validation (`rclone_cache_root()`), `os.path.commonpath` containment, strict `remote_name` allowlisting, and symlink-safe `vfsMeta` upload inspection in `src/cyswllt/mount_manager.py`, achieving **`0` Snyk Code & Open Source issues**.
- **SonarQube Cloud Clean-Code & Security Pass (`TaliskerMan_Cyswllt`):** Resolved all 35+ SonarQube Cloud Python, JavaScript ESM (`docs/guide/build_guide.js`), Shell, and SHA-pinned GitHub Actions CI findings — including cognitive-complexity refactoring (`python:S3776`), traceback-preserving exception logging (`python:S8572`), 5 MiB rotated `0600` log sanitization, and CWE-88 OAuth credential token validation — achieving **Quality Gate `OK` (`0` Bugs, `0` Vulnerabilities, `0` Code Smells, `0` Security Hotspots)**.
- **Performance Settings Credential Lifecycle Fix (`v1.0.9`):** Restored `AuthManager.has_custom_credentials()` and `AuthManager.clear_custom_credentials()` (cleaning up both `~/.config/cyswllt/credentials.json` and custom keys in `~/.config/rclone/rclone.conf`) with full unit test coverage (`27 / 27` `pytest` passing).
- **Updated User Guide PDF & Release Pipeline (`v1.0.9`):** Aligned `README.md`, `Cyswllt_User_Guide.md`, and the branded `Cyswllt_User_Guide.pdf` (`v1.0.9`), fixed hicolor PNG icon paths in `build_guide.js` and `install.sh`, and generated path-sanitized CycloneDX SBOMs (`0` Grype/Trivy/OSV vulnerabilities).

## Package Integrity & Verification

| Asset | Description |
|---|---|
| `cyswllt_1.0.9-1_all.deb` | Debian/Ubuntu architecture-independent 64-bit desktop package |
| `cyswllt_1.0.9-1_all.deb.asc` | GPG ASCII-armored detached signature |
| `cyswllt_1.0.9-1_all.deb.sig` | GPG binary detached signature |
| `cyswllt_1.0.9-1_all.deb.sha512` / `checksums.sha512` | SHA-512 package checksum |
| `cyswllt_1.0.9-1_all.deb.sha512.asc` | Clearsigned SHA-512 package checksum |
| `cyswllt_1.0.9-1_all.deb.sha256` / `checksums.sha256` | SHA-256 package checksum |
| `pubkey.asc` / `chuck_pubkey.asc` | Maintainer GPG public key (`Chuck Talk <chuck@nordheim.online>`) |
| `cyswllt_source.tar.gz` | Corresponding GPLv3 source archive |
| `SBOM-Linux.json` / `sbom.json` | CycloneDX SBOM (Software Bill of Materials) |
| `security_report.md` | Multi-scanner security and quality audit report |
| `Cyswllt_User_Guide.pdf` | Official User Guide & manual (`v1.0.9`) |
| `SHA512SUMS` / `SHA256SUMS` | Combined release asset checksum manifests |

### Verification Instructions

```bash
# Verify SHA-512 checksum
sha512sum -c checksums.sha512

# Import Chuck Talk's release signing key and verify GPG detached signature
gpg --import chuck_pubkey.asc
gpg --verify cyswllt_1.0.9-1_all.deb.asc cyswllt_1.0.9-1_all.deb
```

### Installation

```bash
sudo apt install ./cyswllt_1.0.9-1_all.deb
```
