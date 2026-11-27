#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Author: Chuck Talk, <chuck@nordheim.online>
# Project: Cyswllt
# Purpose: Automated Linux DEB build, GPG detached sign, SHA-512/256 hash,
#          CycloneDX SBOM, Grype/Trivy pre-flight, and NOBuilds staging script.
# Updated: 2026-11-27 (CP-ChangeComments: standardized v1.0.9 CycloneDX SBOM,
#          non-interactive GPG signing, basename checksums, and NOBuilds archive)
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
cd "${SCRIPT_DIR}"

readonly PACKAGE_NAME="cyswllt"
readonly APP_TITLE="Cyswllt"
readonly GPG_EMAIL="chuck@nordheim.online"
readonly BUILD_DIR="artifacts"
readonly AUDIT_DIR="Audit"
readonly PRIMARY_SBOM="${AUDIT_DIR}/SBOM-Linux.json"
readonly SEPARATOR="=================================================="

NO_BUMP=0
for arg in "$@"; do
    case "${arg}" in
        --no-bump)
            NO_BUMP=1
            ;;
        *)
            echo "ERROR: Unknown option: ${arg}" >&2
            exit 1
            ;;
    esac
done
readonly NO_BUMP

if [[ "${NO_BUMP}" -eq 0 ]]; then
    INCREMENT_SCRIPT="${SCRIPT_DIR}/../workflow-tools/increment_build.py"
    if [[ -f "${INCREMENT_SCRIPT}" ]]; then
        echo "==> Incrementing build version..."
        python3 "${INCREMENT_SCRIPT}" .
    fi
fi

VERSION="$(grep -oP '(?<=^__version__ = ")[^"]+' src/cyswllt/version.py)"
readonly VERSION
readonly DEB_VERSION="${VERSION}-1"

echo "${SEPARATOR}"
echo "☁️  Building ${APP_TITLE} v${VERSION} (${DEB_VERSION})"
echo "${SEPARATOR}"

mkdir -p "${AUDIT_DIR}" "${BUILD_DIR}"
find "${BUILD_DIR}" -mindepth 1 -maxdepth 1 ! -name '.keep' ! -name 'chuck_pubkey.asc' -exec rm -rf -- {} + 2>/dev/null || true

resolve_tool() {
    local tool_name="$1"
    if command -v "${tool_name}" >/dev/null 2>&1; then
        command -v "${tool_name}"
        return 0
    fi
    if [[ -x "${HOME}/.local/bin/${tool_name}" ]]; then
        echo "${HOME}/.local/bin/${tool_name}"
        return 0
    fi
    echo "ERROR: Required tool '${tool_name}' is not installed." >&2
    exit 1
}

TRIVY_BIN="$(resolve_tool trivy)"
SYFT_BIN="$(resolve_tool syft)"
GRYPE_BIN="$(resolve_tool grype)"
readonly TRIVY_BIN SYFT_BIN GRYPE_BIN

echo "[1/6] Scanning repository for exposed secrets..."
"${TRIVY_BIN}" fs --scanners secret --exit-code 1 .

echo "[2/6] Generating CycloneDX SBOM via Syft and scanning with Grype..."
"${SYFT_BIN}" scan dir:. \
    --source-name "${PACKAGE_NAME}" \
    --source-version "${VERSION}" \
    --exclude './.git/**' \
    --exclude './.venv/**' \
    --exclude './venv/**' \
    --exclude './build/**' \
    --exclude './dist/**' \
    --exclude './debian/cyswllt/**' \
    --exclude './artifacts/**' \
    --exclude './Audit/**' \
    --exclude './*.deb' \
    --exclude './*.tar.gz' \
    -o "cyclonedx-json=${PRIMARY_SBOM}"
sed -i "s|${SCRIPT_DIR}/\?||g" "${PRIMARY_SBOM}"
cp "${PRIMARY_SBOM}" "${AUDIT_DIR}/SBOM-Linux"
cp "${PRIMARY_SBOM}" "${AUDIT_DIR}/sbom.json"
"${GRYPE_BIN}" "sbom:${PRIMARY_SBOM}" --fail-on high

echo "[3/6] Running automated test suite..."
PYTEST_BIN="pytest"
if [[ -x ".venv/bin/pytest" ]]; then
    PYTEST_BIN=".venv/bin/pytest"
elif [[ -x "${HOME}/antigrav/Shine/.venv/bin/pytest" ]]; then
    PYTEST_BIN="${HOME}/antigrav/Shine/.venv/bin/pytest"
fi
PYTHONPATH="${SCRIPT_DIR}/src:/usr/lib/python3/dist-packages" "${PYTEST_BIN}" tests

echo "[4/6] Building Debian package..."
TOP_VERSION="$(head -n 1 debian/changelog | sed -E 's/.*\(([^)]+)\).*/\1/')"
if [[ "${TOP_VERSION}" != "${DEB_VERSION}" ]]; then
    echo "ERROR: debian/changelog (${TOP_VERSION}) does not match version.py (${DEB_VERSION})." >&2
    exit 1
fi

rm -rf -- build dist ./*.egg-info src/*.egg-info debian/cyswllt
rm -f -- ../"${PACKAGE_NAME}_${VERSION}"* ../"${PACKAGE_NAME}_${DEB_VERSION}"*
dpkg-buildpackage -us -uc -b

mv -- ../"${PACKAGE_NAME}_${DEB_VERSION}"*.deb "${BUILD_DIR}/"
mv -- ../"${PACKAGE_NAME}_${DEB_VERSION}"*.changes "${BUILD_DIR}/" 2>/dev/null || true
mv -- ../"${PACKAGE_NAME}_${DEB_VERSION}"*.buildinfo "${BUILD_DIR}/" 2>/dev/null || true

readonly DEB_BASENAME="${PACKAGE_NAME}_${DEB_VERSION}_all.deb"
readonly DEB_FILE="${BUILD_DIR}/${DEB_BASENAME}"

echo "[5/6] Generating GPG detached signatures and SHA-512/SHA-256 checksums..."
gpg --batch --yes --armor --pinentry-mode loopback --detach-sign --default-key "${GPG_EMAIL}" "${DEB_FILE}"
gpg --batch --yes --pinentry-mode loopback --detach-sign --output "${DEB_FILE}.sig" --default-key "${GPG_EMAIL}" "${DEB_FILE}"
gpg --batch --yes --armor --export "${GPG_EMAIL}" > "${BUILD_DIR}/pubkey.asc"
cp "${BUILD_DIR}/pubkey.asc" "${BUILD_DIR}/chuck_pubkey.asc"

(
    cd "${BUILD_DIR}"
    sha512sum -- "${DEB_BASENAME}" > "${DEB_BASENAME}.sha512"
    sha256sum -- "${DEB_BASENAME}" > "${DEB_BASENAME}.sha256"
    cp "${DEB_BASENAME}.sha512" checksums.sha512
    cp "${DEB_BASENAME}.sha256" checksums.sha256
)
gpg --batch --yes --clearsign --pinentry-mode loopback --default-key "${GPG_EMAIL}" "${DEB_FILE}.sha512"

echo "[6/6] Staging release archive to NOBuilds..."
DATE_STR="$(date +%m-%d-%Y)"
readonly DATE_STR
readonly NOBUILDS_DIR="${HOME}/NOBuilds/${APP_TITLE}-${DATE_STR}-${DEB_VERSION}"
mkdir -p "${NOBUILDS_DIR}"

tar --exclude=debian/cyswllt --exclude=debian/.debhelper --exclude=.git \
    --exclude=artifacts --exclude=Audit --exclude=__pycache__ --exclude=build \
    --exclude=dist --exclude=./venv --exclude=./.venv --exclude='*.tar.gz' \
    --exclude=.pytest_cache --exclude=.ruff_cache --exclude=.scannerwork \
    --exclude=.sonarlint --exclude='**/node_modules' --exclude=.DS_Store \
    -czf "${NOBUILDS_DIR}/${PACKAGE_NAME}_source.tar.gz" .
cp "${NOBUILDS_DIR}/${PACKAGE_NAME}_source.tar.gz" "${BUILD_DIR}/"

for asset in \
    "${DEB_FILE}" \
    "${DEB_FILE}.asc" \
    "${DEB_FILE}.sig" \
    "${DEB_FILE}.sha512" \
    "${DEB_FILE}.sha512.asc" \
    "${DEB_FILE}.sha256" \
    "${BUILD_DIR}/checksums.sha512" \
    "${BUILD_DIR}/checksums.sha256" \
    "${BUILD_DIR}/pubkey.asc" \
    "${BUILD_DIR}/chuck_pubkey.asc" \
    LICENSE README.md PLAN.md release_notes.md \
    "${PRIMARY_SBOM}" "${AUDIT_DIR}/SBOM-Linux" "${AUDIT_DIR}/sbom.json"; do
    cp "${asset}" "${NOBUILDS_DIR}/"
done

if [[ -f "${AUDIT_DIR}/security_report.md" ]]; then
    cp "${AUDIT_DIR}/security_report.md" "${BUILD_DIR}/"
    cp "${AUDIT_DIR}/security_report.md" "${NOBUILDS_DIR}/"
fi

if [[ -f "docs/Cyswllt_User_Guide.pdf" ]]; then
    cp "docs/Cyswllt_User_Guide.pdf" "${BUILD_DIR}/"
    cp "docs/Cyswllt_User_Guide.pdf" "${NOBUILDS_DIR}/"
fi

for target_dir in "${BUILD_DIR}" "${NOBUILDS_DIR}"; do
    (
        cd "${target_dir}"
        rm -f -- SHA512SUMS SHA256SUMS
        sha512sum -- ./* > SHA512SUMS 2>/dev/null || true
        sha256sum -- ./* > SHA256SUMS 2>/dev/null || true
    )
done

echo "${SEPARATOR}"
echo "✅ ${APP_TITLE} v${VERSION} Release Build Complete!"
echo "Package: ${DEB_FILE}"
echo "Archive: ${NOBUILDS_DIR}"
