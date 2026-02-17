#!/bin/bash
set -e

# Configuration
VERSION_FILE="src/cyswllt/version.py"
PLAN_FILE="CyswlltPlan.md"
ARTIFACTS_DIR="artifacts"
GPG_KEY="cwtalk1@gmail.com"

# 1. Get current version
CURRENT_VERSION=$(grep -oP '__version__ = "\K[^"]+' "$VERSION_FILE")
echo "Current version: $CURRENT_VERSION"

# 2. Increment version (Patch level)
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
echo "New version: $NEW_VERSION"

# 3. Update version.py
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" "$VERSION_FILE"

# 4. Update Debian Changelog
# Check if dch is available
if command -v dch &> /dev/null; then
    # -v version, -D distribution, --force-distribution to force it
    # Use standard "Release <version>" message
    DEBEMAIL="$GPG_KEY" DEBFULLNAME="Chuck Talk" dch -v "$NEW_VERSION-1" -D "unstable" --force-distribution "Release v$NEW_VERSION"
else
    echo "Error: dch (devscripts) not found. Please install devscripts."
    exit 1
fi

# 5. Update CyswlltPlan.md
echo "" >> "$PLAN_FILE"
echo "## Release $NEW_VERSION ($(date +%Y-%m-%d))" >> "$PLAN_FILE"
echo "- Bumped version to $NEW_VERSION" >> "$PLAN_FILE"
echo "- Built and signed DEB package" >> "$PLAN_FILE"

# 6. Build Package
echo "Building package..."
# We need to create the orig tarball again for the new version
# The directory name needs to be cyswllt-0.1.1 for dpkg-source if strictly following, 
# but usually it handles it if we provide the orig setup correctly.
# Let's clean up old builds first
rm -f ../cyswllt_*.orig.tar.gz

tar --exclude=debian --exclude=.git --exclude=artifacts --exclude=__pycache__ -czf "../cyswllt_$NEW_VERSION.orig.tar.gz" .

# Build
# -i: Ignore files matching regex (for diff)
# -I: Ignore files (for tar)
# We ignore .git, artifacts, and __pycache__ to prevent them from being part of the diff/tar
debuild -us -uc -i"(\.git|artifacts|__pycache__)" -I".git" -I"artifacts" -I"__pycache__"

# 7. Move Artifacts
echo "Moving artifacts..."
mkdir -p "$ARTIFACTS_DIR"
mv ../cyswllt_${NEW_VERSION}-1* "$ARTIFACTS_DIR/" || true
mv "../cyswllt_$NEW_VERSION.orig.tar.gz" "$ARTIFACTS_DIR/" || true

# 8. Sign and Hash
echo "Signing and hashing..."
# debsign might be interactive if gpg requires passphrase. 
# We assume the user has gpg agent set up or will enter it.
debsign -k "$GPG_KEY" "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_amd64.changes"
sha512sum "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.deb" > "$ARTIFACTS_DIR/checksums.sha512"

# 9. Git Operations (SKIPPED FOR TEST BUILD)
# echo "Committing and tagging..."
# git add .
# git commit -m "Release v$NEW_VERSION"
# git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
# git push origin HEAD --tags

echo "Test Build $NEW_VERSION completed successfully!"
