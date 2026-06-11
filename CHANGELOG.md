# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
