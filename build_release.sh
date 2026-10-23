#!/bin/bash
# Cyswllt Linux Release Builder
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

NO_BUMP=0
if [ "${1:-}" = "--no-bump" ] || [ "${CYSWLLT_SKIP_INCREMENT:-0}" = "1" ]; then
    NO_BUMP=1
fi

# Auto-increment version/build number if not --no-bump (CP-ChangeComments)
if [ "$NO_BUMP" -eq 0 ]; then
    python3 "${SCRIPT_DIR}/../workflow-tools/increment_build.py" "${SCRIPT_DIR}"
fi

# Fetch ShadowAgent Ground Rules dynamically
echo "Verifying ShadowAgent configuration..."
SHADOW_AGENT_PORT="8080"
if [ -f ~/.config/shadowagent/api.port ]; then
    SHADOW_AGENT_PORT=$(cat ~/.config/shadowagent/api.port)
fi
if [ -f ~/.config/shadowagent/api.key ]; then
    API_KEY=$(cat ~/.config/shadowagent/api.key)
    curl -s -S -H "Authorization: Bearer $API_KEY" "http://localhost:${SHADOW_AGENT_PORT}/rules" > /dev/null || true
fi

# Configuration
VERSION_FILE="src/cyswllt/version.py"
# shellcheck disable=SC2034
PLAN_FILE="CyswlltPlan.md"
ARTIFACTS_DIR="artifacts"
GPG_KEY="chuck@nordheim.online"

# 1. Get current version
CURRENT_VERSION=$(awk -F '"' '/__version__/ {print $2}' "$VERSION_FILE")
echo "Current version: $CURRENT_VERSION"

# 2. Version handling
if [ "$NO_BUMP" -eq 1 ]; then
    NEW_VERSION="$CURRENT_VERSION"
    echo "Using existing version $NEW_VERSION (no bump per --no-bump)"
else
    # Increment version (Patch level)
    IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"
    MAJOR="${VERSION_PARTS[0]}"
    MINOR="${VERSION_PARTS[1]}"
    PATCH="${VERSION_PARTS[2]}"
    NEW_PATCH=$((PATCH + 1))
    NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"
    echo "New version: $NEW_VERSION"

    # 3. Update version.py
    sed -i.bak "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" "$VERSION_FILE"
    rm -f "${VERSION_FILE}.bak"

    # 4. Update Debian Changelog
    if command -v dch &> /dev/null; then
        DEBEMAIL="$GPG_KEY" DEBFULLNAME="Chuck Talk" dch -v "$NEW_VERSION-1" -D "unstable" --force-distribution "Release v$NEW_VERSION"
    else
        echo "Error: dch (devscripts) not found. Please install devscripts."
        exit 1
    fi
fi

# 5. Generate CycloneDX SBOM via Syft per CP-SBOM (CP-ChangeComments)
echo "==> Generating SBOM via Syft..."
SYFT_BIN="syft"
if ! command -v syft &> /dev/null; then
    if [ -f "${HOME}/.local/bin/syft" ]; then
        SYFT_BIN="${HOME}/.local/bin/syft"
    elif [ -f "./syft" ]; then
        SYFT_BIN="./syft"
    fi
fi
if command -v "${SYFT_BIN}" &> /dev/null; then
    mkdir -p "${SCRIPT_DIR}/Audit"
    "${SYFT_BIN}" dir:. \
        --exclude ./venv \
        --exclude ./.venv \
        --exclude ./build \
        --exclude ./dist \
        --exclude ./plan \
        --exclude ./artifacts \
        -o cyclonedx-json > "${SCRIPT_DIR}/Audit/SBOM-Linux.json"
    cp "${SCRIPT_DIR}/Audit/SBOM-Linux.json" "${SCRIPT_DIR}/Audit/SBOM-Linux"
    cp "${SCRIPT_DIR}/Audit/SBOM-Linux.json" "${SCRIPT_DIR}/Audit/sbom.json"
fi

# 6. Build Package
echo "Building package..."
rm -f ../cyswllt_*.orig.tar.gz

tar --exclude=debian --exclude=.git --exclude=artifacts --exclude=__pycache__ --exclude=venv --exclude=.venv -czf "../cyswllt_$NEW_VERSION.orig.tar.gz" .

# Build without root per CP-HumanInLoop
debuild -us -uc -i"(\.git|artifacts|__pycache__|venv|\.venv)" -I".git" -I"artifacts" -I"__pycache__" -I"venv" -I".venv"

# 7. Move Artifacts
echo "Moving artifacts..."
mkdir -p "$ARTIFACTS_DIR"
mv ../cyswllt_${NEW_VERSION}-1* "$ARTIFACTS_DIR/" || true
mv "../cyswllt_$NEW_VERSION.orig.tar.gz" "$ARTIFACTS_DIR/" || true

# 8. Sign and Hash
echo "Signing and hashing..."
# Try signing changes file if exists non-interactively
if [ -f "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_amd64.changes" ]; then
    debsign -p"gpg --batch --no-tty" -k "$GPG_KEY" "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_amd64.changes" || true
elif [ -f "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.changes" ]; then
    debsign -p"gpg --batch --no-tty" -k "$GPG_KEY" "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.changes" || true
fi

# Detached GPG signature using batch/no-tty per CP-HumanInLoop
rm -f "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.deb.asc"
if ! gpg --batch --no-tty --armor --detach-sign --yes --default-key "$GPG_KEY" "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.deb"; then
    echo "ERROR: GPG signing failed; release not built." >&2
    exit 1
fi
gpg --batch --no-tty --armor --export "$GPG_KEY" > "$ARTIFACTS_DIR/pubkey.asc"
cp "$ARTIFACTS_DIR/pubkey.asc" "$ARTIFACTS_DIR/chuck_pubkey.asc"

# Checksums
(cd "$ARTIFACTS_DIR" && sha512sum "cyswllt_${NEW_VERSION}-1_all.deb" > checksums.sha512)
(cd "$ARTIFACTS_DIR" && sha512sum "cyswllt_${NEW_VERSION}-1_all.deb" > "cyswllt_${NEW_VERSION}-1_all.deb.sha512")

# 9. Copy to NOBuilds directory per L-Release
DATE_STR=$(date +%m-%d-%Y)
NOBUILDS_DIR="${HOME}/NOBuilds/Cyswllt-${DATE_STR}-${NEW_VERSION}-1"
mkdir -p "${NOBUILDS_DIR}"

cp "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.deb" "${NOBUILDS_DIR}/"
cp "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.deb.asc" "${NOBUILDS_DIR}/"
cp "$ARTIFACTS_DIR/checksums.sha512" "${NOBUILDS_DIR}/"
cp "$ARTIFACTS_DIR/cyswllt_${NEW_VERSION}-1_all.deb.sha512" "${NOBUILDS_DIR}/"
cp "$ARTIFACTS_DIR/pubkey.asc" "${NOBUILDS_DIR}/"
cp "$ARTIFACTS_DIR/chuck_pubkey.asc" "${NOBUILDS_DIR}/"
cp "$ARTIFACTS_DIR/cyswllt_$NEW_VERSION.orig.tar.gz" "${NOBUILDS_DIR}/cyswllt_source.tar.gz" || true
cp LICENSE "${NOBUILDS_DIR}/"
cp README.md "${NOBUILDS_DIR}/"
cp docs/Cyswllt_User_Guide.pdf "${NOBUILDS_DIR}/" || true
cp docs/Cyswllt_User_Guide.pdf "${ARTIFACTS_DIR}/" || true
cp Audit/SBOM-Linux.json "${NOBUILDS_DIR}/" || true
cp Audit/SBOM-Linux "${NOBUILDS_DIR}/" || true
cp Audit/sbom.json "${NOBUILDS_DIR}/" || true
if [ -f Audit/security_report.md ]; then
    cp Audit/security_report.md "${NOBUILDS_DIR}/" || true
fi
( cd "${NOBUILDS_DIR}" && rm -f SHA512SUMS && sha512sum * > SHA512SUMS )
( cd "${ARTIFACTS_DIR}" && rm -f SHA512SUMS && sha512sum * > SHA512SUMS )

echo "Release $NEW_VERSION completed successfully!"
echo "Published to: $NOBUILDS_DIR"
