#!/bin/bash
set -euo pipefail

# Ensure execution from repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Increment Build Version (Rule_017)
INCREMENT_SCRIPT="${SCRIPT_DIR}/../workflow-tools/increment_build.py"
if [[ -f "$INCREMENT_SCRIPT" ]]; then
    echo "=== Incrementing Build Version (Rule_017) ==="
    python3 "$INCREMENT_SCRIPT" .
fi

# --- Pre-Flight Security & Quality Gate (Rules 003, 004, 005, 006) ---
echo "=== Running Pre-Flight Security & Quality Scans ==="
mkdir -p Audit
if ! command -v trivy >/dev/null 2>&1; then
    echo "Error: trivy is required (Rule 004). Install trivy." >&2
    exit 1
fi
if ! command -v syft >/dev/null 2>&1 || ! command -v grype >/dev/null 2>&1; then
    echo "Error: syft and grype are required (Rule 003). Install syft and grype." >&2
    exit 1
fi

echo "[1/3] Scanning for exposed secrets..."
trivy fs --scanners secret --exit-code 1 .
echo "[2/3] Generating SBOM and scanning dependencies..."
OS_NAME="$(uname -s)"
if [[ "$OS_NAME" == "Darwin" ]]; then
    SBOM_SUFFIX="macOS"
else
    SBOM_SUFFIX="$OS_NAME"
fi
syft . \
    --source-name "Cyswllt" \
    --exclude "./Audit/**" \
    --exclude "./.git/**" \
    --exclude "./artifacts/**" \
    -o spdx-json="Audit/SBOM-${SBOM_SUFFIX}.json" \
    -o syft-table="Audit/SBOM-${SBOM_SUFFIX}"
grype "sbom:Audit/SBOM-${SBOM_SUFFIX}.json" --fail-on high
echo "[3/3] Running automated test suite..."
PYTHONPATH=src pytest
echo "=== Pre-Flight Gate Passed ==="

# Extract current version from src/cyswllt/version.py
VERSION=$(grep "__version__" src/cyswllt/version.py | cut -d '"' -f 2)
# Use a timestamp to ensure unique test build versions
TIMESTAMP=$(date +%Y%m%d%H%M)
TEST_VERSION="${VERSION}~test${TIMESTAMP}"

echo "Building Test Package for Cyswllt v${TEST_VERSION}..."

# 1. Update Debian Changelog (Temporary for test build)
export DEBFULLNAME="Chuck Talk"
export DEBEMAIL="chuck@nordheim.online"

if ! command -v dch &> /dev/null; then
    echo "Error: dch (devscripts) not found. Please install devscripts." >&2
    exit 1
fi

# Backup original changelog
cp debian/changelog debian/changelog.bak

# Cleanup function to restore changelog on exit
cleanup() {
    if [[ -f debian/changelog.bak ]]; then
        echo "Restoring original debian/changelog..."
        mv debian/changelog.bak debian/changelog
    fi
}
trap cleanup EXIT

dch -v "${TEST_VERSION}-1" -D unstable "Automated test build"

# 2. Build Unsigned Binary Package
echo "Running dpkg-buildpackage (unsigned binary only)..."
dpkg-buildpackage -b -us -uc

# 3. Move Artifacts
mkdir -p artifacts/test
mv "../cyswllt_${TEST_VERSION}-1_"*.deb artifacts/test/
mv "../cyswllt_${TEST_VERSION}-1_"*.changes artifacts/test/ 2>/dev/null || true
mv "../cyswllt_${TEST_VERSION}-1_"*.buildinfo artifacts/test/ 2>/dev/null || true

echo ""
echo "=== Test Build Complete ==="
echo "Test package available in ./artifacts/test/:"
ls -lh artifacts/test/*.deb
echo ""
echo "To install:"
echo "sudo apt install ./artifacts/test/cyswllt_${TEST_VERSION}-1_all.deb"
