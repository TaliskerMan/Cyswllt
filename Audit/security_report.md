# Cyswllt Security Audit & Quality Scan Report

**Application:** Cyswllt v1.0.9 (`1.0.9-1`)  
**Date:** November 27, 2026  
**Tools:** Snyk CLI (`v1.1309.0`), SonarQube Cloud (`TaliskerMan_Cyswllt`), Syft, Grype, Trivy, OSV-Scanner, ShellCheck, Ruff, Pytest  
**Auditor:** Antigravity AI / ShadowAgent Shift-Left Compliance Engine  
**Repository:** `TaliskerMan/Cyswllt`  
**Target Platform:** Linux (`all` architecture DEB on `amd64`)

---

## 1. Executive Summary

A multi-scanner security audit and quality gate verification was conducted on **Cyswllt v1.0.9 (`1.0.9-1`)** per the Nordheim Online development standards (`~/sarules`).

| Gate / Audit Layer | Tool | Result | Details |
|---|---|---|---|
| **Snyk Code (SAST) & Open Source** | `snyk` (`v1.1309.0`, `TaliskerMan`) | ✅ PASS | `0` Snyk Code issues (`CS1-12` `2 × python/PT` `CWE-23` remediated), `0` Open Source vulnerabilities |
| **SonarQube Cloud Quality Gate** | `TaliskerMan_Cyswllt` (`main`) | ✅ PASS | `OK` (`0` Bugs, `0` Vulnerabilities, `0` Security Hotspots, `0` Code Smells; `A/A/A/A` ratings) |
| **Unit & Smoke Tests** | `pytest` + `ruff` | ✅ PASS | `27 / 27` tests passed (OAuth token extraction, CWE-88 credential validation, custom credential save/check/clear, XDG traversal & symlink guards, FUSE mount/unmount lifecycle); `0` Ruff errors |
| **Shell Static Analysis** | `shellcheck` | ✅ PASS | `0` warnings across `build_release.sh`, `build_test.sh`, and `install.sh` |
| **Secret Detection** | `trivy` | ✅ PASS | `0` hardcoded secrets detected |
| **SBOM & Supply Chain** | `syft` + `grype` + `osv-scanner` | ✅ PASS | Path-sanitized CycloneDX JSON SBOM (`Audit/SBOM-Linux.json`); `0` host paths, `0` vulnerabilities |

---

## 2. Security Safeguards & Integrity Protections
- **Canonical XDG & `vfsMeta` Containment (`CS1-12`):** `rclone_cache_root()` and `count_pending_uploads()` enforce `os.path.commonpath` containment, strict `remote_name` allowlisting (`^[A-Za-z0-9_-]+$`), and symlink exclusion (`followlinks=False`, `os.path.islink` checks).
- **Credential & Log Isolation (`CP-Logging`):** Custom Google OAuth credentials (`~/.config/cyswllt/credentials.json`) and `~/.config/rclone/rclone.conf` are written via `os.open(..., 0o600)` inside `0o700` directories; custom credentials pass via environment variables (`RCLONE_DRIVE_CLIENT_ID` / `RCLONE_DRIVE_CLIENT_SECRET`) rather than CLI arguments, and diagnostic logs (`~/.cache/cyswllt/cyswllt.log` and `rclone.log`) use `0o600` permissions with 5 MiB rotation and CR/LF control-character sanitization.
- **Subprocess Safety:** All `rclone` and `fusermount` / `fusermount3` calls use fixed list-form `argv` vectors with `CWE-88` leading-hyphen validation on user-entered OAuth tokens.
- **GPG Detached Signing (`L-DEB-Packaging`, `L-Release`):** `cyswllt_1.0.9-1_all.deb` is signed with maintainer key `Chuck Talk <chuck@nordheim.online>` (`D60BA098CDA22A20BD8BB6834E99214B22CFEE40`), accompanied by SHA-512/SHA-256 checksums, `chuck_pubkey.asc`, `cyswllt_source.tar.gz`, `Cyswllt_User_Guide.pdf`, and CycloneDX SBOMs in `~/NOBuilds/Cyswllt-11-27-2026-1.0.9-1/`.
