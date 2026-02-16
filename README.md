# Cyswllt

Cyswllt (Welsh for "Connect") is a GTK application that allows you to easily mount and unmount your Google Drive on Linux locally.

## Features
-   **Google Authentication**: Securely connect to your Google Drive.
-   **One-Click Mount**: Mount and unmount your drive with a single button.
-   **Desktop Integration**: Automatically places a drive icon on your GNOME Desktop (DING compliant) when mounted.
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
python3 src/cyswllt/main.py
```

## Contributing
Contributions are welcome! Please ensure all builds start and end in the `artifacts` directory and update `CyswlltPlan.md` with your changes.

## License
GNU GPL v3
