#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="${SCRIPT_DIR}/aig-scanner"
OUT_DIR="${SCRIPT_DIR}/dist"

if [[ ! -f "${SKILL_DIR}/SKILL.md" ]]; then
  echo "Missing skill source: ${SKILL_DIR}/SKILL.md" >&2
  exit 1
fi

VERSION="$(awk '/^version:/ {print $2; exit}' "${SKILL_DIR}/SKILL.md")"
if [[ -z "${VERSION}" ]]; then
  echo "Unable to detect version from ${SKILL_DIR}/SKILL.md" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

mkdir -p "${TMP_DIR}/aig-scanner/scripts"
cp "${SKILL_DIR}/SKILL.md" "${TMP_DIR}/aig-scanner/SKILL.md"
cp "${SKILL_DIR}/scripts/aig_client.py" "${TMP_DIR}/aig-scanner/scripts/aig_client.py"

ARCHIVE="${OUT_DIR}/aig-scanner-${VERSION}.zip"
rm -f "${ARCHIVE}"

(
  cd "${TMP_DIR}"
  zip -r -X "${ARCHIVE}" aig-scanner >/dev/null
)

shasum -a 256 "${ARCHIVE}"
echo "Built ${ARCHIVE}"
