#!/bin/bash

# Configuration
APP_NAME="Cyswllt"
APP_PKG="com.taliskerman.cyswllt"
INSTALL_DIR="$HOME/.local/lib/cyswllt"
BIN_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "Installing $APP_NAME..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"

# Copy source
echo "Copying source code..."
rsync -av --exclude 'artifacts' --exclude '.git' --exclude '__pycache__' ./ "$INSTALL_DIR/"

# Install Icon
echo "Installing icon..."
cp "$INSTALL_DIR/data/icons/cyswllt.png" "$ICON_DIR/$APP_PKG.png"

# Update Desktop File
echo "Configuring desktop entry..."
DESKTOP_FILE="$INSTALL_DIR/data/$APP_PKG.desktop"

# Fix paths in desktop file
sed -i "s|Exec=.*|Exec=python3 $INSTALL_DIR/src/cyswllt/main.py|" "$DESKTOP_FILE"
sed -i "s|Icon=.*|Icon=$APP_PKG|" "$DESKTOP_FILE"

# Install Desktop File
cp "$DESKTOP_FILE" "$DESKTOP_DIR/"

# Make source executable just in case
chmod +x "$INSTALL_DIR/src/cyswllt/main.py"

# Update icon cache (if possible)
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" || true
fi

echo "$APP_NAME installed successfully!"
echo "You can now launch it from your application menu."
