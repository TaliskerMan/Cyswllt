#!/bin/bash
set -euo pipefail

# Ensure execution from repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Pre-Flight Security & Quality Gate (Rules 003, 004, 005, 006, 007) ---
echo "=== Running Pre-Flight Security & Quality Scans ==="
mkdir -p Audit
if [[ -f "$HOME/.env" ]]; then
    # shellcheck disable=SC1091
    set -a && source "$HOME/.env" && set +a
fi

# 1. Dependency Updates
echo "[1/7] Updating local dependencies..."
if [[ -f "pyproject.toml" ]]; then
    pip install --upgrade pip
fi

# 2. Secret Scanning
if ! command -v trivy >/dev/null 2>&1; then
    echo "Error: trivy is required (Rule 004). Install trivy." >&2
    exit 1
fi
if ! command -v syft >/dev/null 2>&1 || ! command -v grype >/dev/null 2>&1; then
    echo "Error: syft and grype are required (Rule 003). Install syft and grype." >&2
    exit 1
fi

echo "[2/7] Scanning for exposed secrets..."
trivy fs --scanners secret --exit-code 1 .

# 3. SAST (SonarCloud / Snyk Code)
echo "[3/7] Running SAST scans..."
if command -v snyk >/dev/null 2>&1; then
    snyk code test || true
fi

# 4. Vulnerability Scan
echo "[4/7] Running filesystem vulnerability scan..."
trivy fs --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed .

# 5. SBOM Generation & Scan
echo "[5/7] Generating and scanning SBOM..."
OS_NAME="$(uname -s)"
if [[ "$OS_NAME" == "Darwin" ]]; then
    SBOM_SUFFIX="macOS"
else
    SBOM_SUFFIX="$OS_NAME"
fi
syft . \
    --source-name "Cyswllt" \
    --source-version "${VERSION:-1.0.6}" \
    --exclude "./Audit/**" \
    --exclude "./.git/**" \
    --exclude "./artifacts/**" \
    -o spdx-json="Audit/SBOM-${SBOM_SUFFIX}.json" \
    -o syft-table="Audit/SBOM-${SBOM_SUFFIX}"
# shellcheck disable=SC2016
python3 -c '
import pathlib, re, sys
p = pathlib.Path(sys.argv[1])
if p.exists():
    raw = p.read_text(encoding="utf-8")
    cleaned = re.sub(r"/(?:Users|home)/[^/\"\\]+", "$HOME", raw)
    p.write_text(cleaned, encoding="utf-8")
' "Audit/SBOM-${SBOM_SUFFIX}.json"
grype "sbom:Audit/SBOM-${SBOM_SUFFIX}.json" --fail-on high

# 6. Automated Unit Testing
echo "[6/7] Running automated test suite..."
PYTHONPATH=src pytest

echo "=== Pre-Flight Gate Passed ==="

# 7. Increment Build Version (Rule_017)
INCREMENT_SCRIPT="${SCRIPT_DIR}/../workflow-tools/increment_build.py"
if [[ -f "$INCREMENT_SCRIPT" ]]; then
    echo "=== Incrementing Build Version (Rule_017) ==="
    python3 "$INCREMENT_SCRIPT" .
fi

# Extract current version from src/cyswllt/version.py
VERSION=$(grep "__version__" src/cyswllt/version.py | cut -d '"' -f 2)
echo "Building Release for Cyswllt v${VERSION}..."

# 1. Update Debian Changelog
echo "Updating debian/changelog..."
export DEBFULLNAME="Chuck Talk"
export DEBEMAIL="chuck@nordheim.online"

if ! command -v dch &> /dev/null; then
    echo "Error: dch (devscripts) not found. Please install devscripts." >&2
    exit 1
fi

# Check if this version is already the top entry in changelog
TOP_VERSION=$(head -n 1 debian/changelog | sed -E 's/.*\(([^)]+)\).*/\1/')
DEB_VERSION="${VERSION}-1"

if [[ "$TOP_VERSION" == "$DEB_VERSION" ]]; then
    echo "Changelog already at version ${DEB_VERSION}. Updating timestamp..."
    dch -r ""
else
    echo "Adding new changelog entry for ${DEB_VERSION}..."
    dch -v "${DEB_VERSION}" -D unstable "Release v${VERSION}"
fi

# 2. Clean previous build artifacts
echo "Cleaning up previous builds..."
rm -rf build/ dist/ ./*.egg-info debian/cyswllt/
rm -f "../cyswllt_${VERSION}"* "../cyswllt_${DEB_VERSION}"*
mkdir -p artifacts
rm -rf artifacts/*

# 3. Build Unsigned Package (Binary + Source)
echo "Running dpkg-buildpackage (unsigned)..."
dpkg-buildpackage -us -uc

# 4. Move Artifacts
echo "Moving artifacts to ./artifacts/..."
mv "../cyswllt_${DEB_VERSION}"* artifacts/ 2>/dev/null || true
mv "../cyswllt_${VERSION}"* artifacts/ 2>/dev/null || true

cd artifacts

# 5. Sign Artifacts
echo ""
echo "=== Signing Phase ==="
echo "Signing artifacts for Chuck Talk <chuck@nordheim.online>..."

# Identify files to sign
CHANGES_FILE="cyswllt_${DEB_VERSION}_amd64.changes"
if [[ ! -f "$CHANGES_FILE" ]]; then
    # Fallback to wildcard if arch is different (e.g., all or arm64)
    CHANGES_FILES=(cyswllt_"${DEB_VERSION}"_*.changes)
    CHANGES_FILE="${CHANGES_FILES[0]}"
fi

DEB_FILES=(cyswllt_"${DEB_VERSION}"_*.deb)
DEB_FILE="${DEB_FILES[0]}"

if [[ -f "$CHANGES_FILE" ]]; then
    echo "Signing .dsc and .changes with debsign..."
    debsign -k"chuck@nordheim.online" "$CHANGES_FILE"
else
    echo "Warning: .changes file not found! Cannot run debsign." >&2
fi

if [[ -f "$DEB_FILE" ]]; then
    echo "Creating detached armored signature for ${DEB_FILE}..."
    gpg --local-user "chuck@nordheim.online" --armor --detach-sig --output "${DEB_FILE}.asc" "${DEB_FILE}"
fi

# 6. Generate Checksums
echo ""
echo "=== Generating Checksums ==="
sha256sum -- ./* > SHA256SUMS
sha512sum -- ./* > SHA512SUMS
# Backwards-compat filenames for scripts/docs expecting lowercase
cp SHA256SUMS checksums.sha256
cp SHA512SUMS checksums.sha512

echo "Signing Checksums..."
gpg --local-user "chuck@nordheim.online" --clearsign --output SHA256SUMS.asc SHA256SUMS
gpg --local-user "chuck@nordheim.online" --clearsign --output SHA512SUMS.asc SHA512SUMS

# 7. Export Public Key
echo "Exporting public key..."
gpg --armor --export "chuck@nordheim.online" > pubkey.asc

echo ""
echo "=== Release Build Complete ==="
echo "Artifacts in ./artifacts/:"
ls -lh
