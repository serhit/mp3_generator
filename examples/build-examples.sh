#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CLI="${PROJECT_DIR}/.venv/bin/telc-audio"
COVER="${SCRIPT_DIR}/cover-small.jpg"

if [[ ! -x "${CLI}" ]]; then
  printf 'Missing CLI: %s\n' "${CLI}" >&2
  printf 'Create .venv and run: .venv/bin/pip install -e .\n' >&2
  exit 1
fi

if ! command -v lame >/dev/null 2>&1; then
  printf 'lame must be installed and available on PATH.\n' >&2
  exit 1
fi

"${CLI}" build \
  "${SCRIPT_DIR}/01_Geburtstag/01_Geburtstag.md" \
  --cover "${COVER}"

"${CLI}" build \
  "${SCRIPT_DIR}/05_Touristeninformation/05_Touristeninformation.md" \
  --cover "${COVER}"

printf 'Generated both example MP3 files.\n'

