title: Cyswllt
subtitle: Installation and User Guide
version: 1.0.5
platforms: Linux (GNOME and other GTK desktops)
## About Cyswllt

Cyswllt (Welsh for "connect", pronounced *kuh-SWILL-it*) mounts your Google Drive as a folder on your Linux computer. Sign in once, click **Connect**, and your Drive appears at `~/GoogleDrive`, where any application can open and save files. Click **Disconnect** to unmount it.

**What Cyswllt does**

- Signs you in to Google Drive in your browser.
- Mounts the Drive at `~/GoogleDrive` with one click, and unmounts it with another.
- Puts a "Google Drive" launcher on your Desktop while the Drive is mounted.
- Tells you why if mounting fails, and waits for your uploads to finish before disconnecting.
- Optionally uses your own Google API Client ID for better performance.

Cyswllt is a graphical front end for **rclone**, the widely used open-source cloud-storage tool, which does the actual mounting. Cyswllt is free, open-source software under the GNU General Public License v3. Source: github.com/TaliskerMan/Cyswllt.

## System requirements

| | |
|---|---|
| Operating system | Debian, Ubuntu or a derivative |
| Desktop | GTK 4 and Libadwaita (GNOME, or any desktop with those libraries) |
| Required packages | `rclone`, FUSE (`fuse3`), `rsync`, `python3-gi`, GTK 4 and Libadwaita bindings (all installed with the package) |
| Account | A Google account with Google Drive |
| Network | Internet connection |
| Disk space | Up to 10 GB for rclone's file cache |

## Installing Cyswllt

### From the release package

1. Download `cyswllt_<version>-1_all.deb`, its signature (`.asc`), `checksums.sha512` and `pubkey.asc` from the release page.
2. Check the download:

```
sha512sum -c checksums.sha512
gpg --import pubkey.asc
gpg --verify cyswllt_<version>-1_all.deb.asc cyswllt_<version>-1_all.deb
```

3. Install it (this also installs rclone and FUSE):

```
sudo apt install ./cyswllt_<version>-1_all.deb
```

4. Open **Cyswllt** from your applications menu, or run `cyswllt`.

### From source

```
git clone https://github.com/TaliskerMan/Cyswllt.git
cd Cyswllt
pip install .
cyswllt
```

Or run it without installing: `PYTHONPATH=src python3 -m cyswllt`. You'll still need `rclone` and FUSE installed.

### Uninstalling

Disconnect first, then `sudo apt remove cyswllt`. To remove your Google sign-in too, run `rclone config delete cyswllt_gdrive`, and delete `~/.config/cyswllt/` and rclone's cache if you no longer need them.

## Quick start

1. Open Cyswllt. The status reads **Sign in to Google to start**.
2. Click **Sign in with Google**. Your browser opens Google's sign-in page; choose your account and allow access. Cyswllt shows "Waiting for browser auth…" until you finish.
3. Cyswllt mounts the Drive straight after sign-in, and the status shows **Connected**. Next time, just click **Connect**.
4. Open `~/GoogleDrive` in your file manager, or double-click the **Google Drive** launcher on your Desktop.
5. When you're finished, click **Disconnect**.

## Using Cyswllt

### Main window

| Control | What it does |
|---|---|
| Sign in with Google | Starts the browser sign-in (first time only) |
| Connect | Mounts your Drive at `~/GoogleDrive` |
| Disconnect | Waits for any uploads to finish, then unmounts the Drive and removes the Desktop launcher |
| Help (?) | Short instructions |
| Menu (☰) → Performance Settings | Your own Google Client ID and Secret (see below) |
| Menu (☰) → About Cyswllt | Version, license and credits |

### Working with your files

`~/GoogleDrive` behaves like a normal folder. Open files from any application and save into it. Files are fetched from Google as you use them, and recently used files are cached on your computer (up to 10 GB) so they open quickly. Folder listings are cached for up to 72 hours, so changes made on another device can take a while to appear; disconnecting and reconnecting refreshes them.

### Uploads and disconnecting

Files you save into `~/GoogleDrive` are written to this computer first and upload to Google in the background. When you click **Disconnect**, Cyswllt checks for files that haven't finished uploading. If there are any, it shows **Finishing uploads…** with how many are left, and disconnects automatically when they're done. You can also choose:

- **Stay Connected**, to keep working.
- **Disconnect Anyway**. The remaining files stay in rclone's cache on this computer and upload the next time you connect; they aren't on Google Drive until then.

> **Note:** Shutting down or logging out while files are still uploading has the same effect as Disconnect Anyway: they upload next time you connect.

### The Desktop launcher

While the Drive is mounted, Cyswllt creates `~/Desktop/google-drive.desktop`, which opens `~/GoogleDrive` in your file manager. It's removed when you disconnect. It appears on the desktop only where desktop icons are shown (for example Ubuntu's desktop); stock GNOME doesn't show them, so open `~/GoogleDrive` from your file manager instead.

### If Connect fails

If the Drive can't be mounted, Cyswllt shows **Could not connect** with the reason, for example FUSE or rclone missing, no internet connection, or an error reported by rclone. Cyswllt waits up to 30 seconds for the mount. rclone's own messages are kept in `~/.cache/cyswllt/rclone.log`.

### If Disconnect fails

If a program still has a file open on the Drive, the normal unmount fails. Cyswllt then tries a "lazy" unmount, which detaches the folder as soon as it's no longer in use. If that also fails, it shows a message explaining why. Close any programs using files in `~/GoogleDrive` and try again.

## Performance Settings (optional)

By default, rclone signs in using its own shared Google API key, which is rate-limited because many people use it. For faster and more reliable access you can create your own Google API Client ID:

1. Follow rclone's guide, "Making your own client_id" for Google Drive, to create a Client ID and Client Secret in the Google Cloud Console.
2. In Cyswllt, open **Menu → Performance Settings**.
3. Paste the **Client ID** and **Client Secret**, and click **Save credentials**. Both are required.
4. Sign in again for the change to take effect.

**Clear credentials** removes them and returns to rclone's defaults.

## Privacy and security

- Cyswllt has no servers, analytics or telemetry. Your files travel directly between your computer and Google.
- The mount folder `~/GoogleDrive` is created readable by you only.
- Your optional Client ID and Secret are stored in `~/.config/cyswllt/google_credentials.json`, readable by you only.
- **Your Google sign-in token is stored by rclone** in `~/.config/rclone/rclone.conf`, in the section `[cyswllt_gdrive]`. By default rclone doesn't encrypt this file. To protect it, run `rclone config`, choose **Set configuration password**, and enter a password; rclone will then ask for it when Cyswllt mounts the Drive.
- Google's consent page may name **rclone**, because Cyswllt uses rclone's Google sign-in unless you add your own Client ID.

### Where things are stored

| Item | Location |
|---|---|
| Mount point | `~/GoogleDrive` |
| Desktop launcher (while mounted) | `~/Desktop/google-drive.desktop` |
| Google sign-in token | `~/.config/rclone/rclone.conf` (`[cyswllt_gdrive]`) |
| Optional Client ID/Secret | `~/.config/cyswllt/google_credentials.json` |
| File cache | rclone's cache folder (usually `~/.cache/rclone`), up to 10 GB |
| Logs | `~/.cache/cyswllt/cyswllt.log` and `~/.cache/cyswllt/rclone.log` (readable by you only) |

## Troubleshooting

**"Could not connect".** The message says why. If it mentions FUSE or rclone, install them (`sudo apt install fuse3 rclone`). If it timed out, check your internet connection and try again. More detail is in `~/.cache/cyswllt/rclone.log`.

**"Finishing uploads…" doesn't go away.** Large files take time to upload. If the count doesn't drop, check your connection; you can choose **Disconnect Anyway** and the files will upload the next time you connect.

**"Waiting for browser auth…" never finishes.** Complete the sign-in in the browser window that opened, then return to Cyswllt. If you closed the browser, restart Cyswllt and sign in again.

**Google says the request was blocked or rate-limited.** Add your own Client ID in Performance Settings.

**Files I added elsewhere don't appear.** Folder listings are cached. Disconnect and reconnect.

**Disconnect says the folder is busy.** Close programs and terminal windows using files in `~/GoogleDrive`, then try again.

**I want to sign in with a different Google account.** Disconnect, run `rclone config delete cyswllt_gdrive`, then sign in again.

## Support and license

Cyswllt is free, open-source software. Report problems or ask questions on GitHub (github.com/TaliskerMan/Cyswllt), or email **chuck@nordheim.online**.

| | |
|---|---|
| Website | nordheim.online |
| Source code | github.com/TaliskerMan/Cyswllt |
| License | GNU GPL v3 (no warranty) |
| Copyright | © 2026 Chuck Talk, Nordheim Online, LLC |
