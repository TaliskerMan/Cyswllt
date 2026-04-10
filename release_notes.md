# Cyswllt Release 0.1.12

This official release contains minor branding updates, URL mapping fixes, and essential security/compliance improvements aligned with the latest ShadowAgent policies.

## ✨ Updates & Branding
* **Nordheim Online Logo**: The native About Window (`Adw.AboutWindow`) now strictly tracks and dynamically renders the `noln` branding logo directly from the system icon path.
* **White Halo Artefacts Fixed**: Utilized localized fuzz-matting to completely strip out anti-aliasing white pixels around the logo edges for perfect native-theme transparency compliance.
* **URL Routing**: Updated the canonical target URL string to strictly bind to `https://nordheim.online`.
* **Copyright**: Formalized the ownership structural declaration string.

## 📦 Artifacts
Deployed fully according to **ShadowAgent** offline compliance rules:
* Standardized `.deb` compilation archive bounds.
* `sha512sum` hashing metrics attached natively (`checksums.sha512`).
* Detached locally authenticated GPG chain signatures provided natively via the standard Debian `.changes` and `.dsc` structure format.
