#!/bin/bash
set -euo pipefail

echo "Installing Cyswllt dependencies..."

# Check for root/sudo if needed for apt, though we prefer user to run with sudo or we invoke sudo
if [[ "$EUID" -ne 0 ]]; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "Updating apt repositories and installing system packages (rclone, fuse3, GTK4, Libadwaita)..."
$SUDO apt-get update
$SUDO apt-get install -y \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    rclone \
    fuse3 \
    libfuse2

# Ensure user_allow_other is enabled in /etc/fuse.conf if needed (optional, good practice)
if [[ -f /etc/fuse.conf ]]; then
    if ! grep -q "^user_allow_other" /etc/fuse.conf; then
        echo "Enabling user_allow_other in /etc/fuse.conf..."
        echo "user_allow_other" | $SUDO tee -a /etc/fuse.conf >/dev/null
    fi
fi

echo "Installing Cyswllt Python package..."
# Install in user space to avoid messing with system python, or system-wide if preferred.
# Using --break-system-packages on newer Debian/Ubuntu if installing globally/user without venv,
# but pip install --user . is standard for simple desktop apps if not packaging as .deb yet.
pip3 install --user . --break-system-packages || pip3 install --user .

echo "Installing Desktop Entry and Icons..."
mkdir -p ~/.local/share/applications
cp data/com.taliskerman.cyswllt.desktop ~/.local/share/applications/

mkdir -p ~/.local/share/icons/hicolor/scalable/apps
cp data/icons/hicolor/scalable/apps/com.taliskerman.cyswllt.svg ~/.local/share/icons/hicolor/scalable/apps/

# Update desktop database
update-desktop-database ~/.local/share/applications || true
gtk-update-icon-cache ~/.local/share/icons/hicolor -f -t || true

echo ""
echo "Installation complete!"
echo "Make sure ~/.local/bin is in your PATH."
echo "You can now launch 'Cyswllt' from your application menu or by running 'cyswllt' in the terminal."
