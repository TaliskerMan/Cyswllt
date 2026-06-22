# <img src="data/cyswllt.jpg" width="48" height="48" align="top"> Cyswllt

Cyswllt (Welsh for "Connect") - pronounced like "Kuh-swill-it", is a GTK application that allows you to easily mount and unmount your Google Drive on Linux locally.

## Features
-   **Google Authentication**: Securely connect to your Google Drive.
-   **One-Click Mount**: Mount and unmount your drive with a single button.
-   **Desktop Integration**: Places a drive launcher on your desktop when mounted (opens via `xdg-open`, so it works across desktop environments).
-   **Open Source**: Released under the GNU GPL v3 license.

## Installation

### Prerequisites
-   Python 3
-   GTK 4 (libadwaita recommended)
-   FUSE (libfuse2 or libfuse3)

### Running from Source
```bash
git clone https://github.com/TaliskerMan/Cyswllt.git
cd Cyswllt

# Option A — install with the entry point (recommended):
pip install .
cyswllt

# Option B — run in place without installing:
PYTHONPATH=src python3 -m cyswllt
```
> Note: `python3 src/cyswllt/main.py` does **not** work because the code uses
> absolute imports (`from cyswllt...`). Use one of the commands above.

## Security & privacy notes
Cyswllt stores your optional custom Google Client ID/Secret at
`~/.config/cyswllt/google_credentials.json` with `0600` permissions. The Google
Drive **OAuth token itself** is written by rclone to
`~/.config/rclone/rclone.conf` in plaintext (rclone's default, unencrypted). If
you want it encrypted, run `rclone config` and set a config password.

## Contributing
Contributions are welcome! Please update `CyswlltPlan.md` with your changes.
Release artifacts are published to GitHub Releases (not committed to the tree).

## License
GNU GPL v3

## Copyright
Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
