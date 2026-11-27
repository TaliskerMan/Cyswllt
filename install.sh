#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Author: Chuck Talk, <chuck@nordheim.online>
# Project: Cyswllt
# Purpose: Local user-space dependency and hicolor icon installer.
# Updated: 2026-11-27 (CP-ChangeComments: install PNG hicolor icon suite instead of nonexistent scalable SVG)
###############################################################################

readonly ICON_NAME="com.taliskerman.cyswllt"
readonly LOCAL_SHARE="${HOME}/.local/share"
readonly APPS_DIR="${LOCAL_SHARE}/applications"
readonly HICOLOR_DIR="${LOCAL_SHARE}/icons/hicolor"

echo "Installing Cyswllt dependencies..."

if [[ "${EUID}" -ne 0 ]]; then
    SUDO="sudo"
else
    SUDO=""
fi

echo "Updating apt repositories and installing system packages (rclone, fuse3, GTK4, Libadwaita)..."
${SUDO} apt-get update
${SUDO} apt-get install -y \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    rclone \
    fuse3

if [[ -f /etc/fuse.conf ]] && ! grep -q "^user_allow_other" /etc/fuse.conf; then
    echo "Enabling user_allow_other in /etc/fuse.conf..."
    echo "user_allow_other" | ${SUDO} tee -a /etc/fuse.conf >/dev/null
fi

echo "Installing Cyswllt Python package in user space..."
pip3 install --user .

echo "Installing Desktop Entry and Icons..."
mkdir -p "${APPS_DIR}"
cp "data/${ICON_NAME}.desktop" "${APPS_DIR}/"

for size in 32x32 48x48 64x64 128x128 256x256 512x512; do
    mkdir -p "${HICOLOR_DIR}/${size}/apps"
    cp "data/icons/hicolor/${size}/apps/${ICON_NAME}.png" "${HICOLOR_DIR}/${size}/apps/"
done

update-desktop-database "${APPS_DIR}" || true
gtk-update-icon-cache "${HICOLOR_DIR}" -f -t || true

echo ""
echo "Installation complete!"
echo "Make sure ~/.local/bin is in your PATH."
echo "You can now launch 'Cyswllt' from your application menu or by running 'cyswllt' in the terminal."
