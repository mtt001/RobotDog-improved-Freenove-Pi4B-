#!/usr/bin/env bash
# =============================================================================
# File: install_time_guard_hook.sh
# Purpose: Install pre-commit hook that checks README local-time recency.
# Version: v1.00 (2026-02-08 14:59)
# Revision History:
#   v1.00 (2026-02-08 14:59) - Initial installer for timestamp guard hook.
# =============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_SRC="${ROOT_DIR}/.githooks/pre-commit"
HOOK_DST="${ROOT_DIR}/.git/hooks/pre-commit"

if [[ ! -f "${HOOK_SRC}" ]]; then
  echo "hook source missing: ${HOOK_SRC}" >&2
  exit 1
fi
if [[ ! -d "${ROOT_DIR}/.git/hooks" ]]; then
  echo "not a git repo root (missing .git/hooks): ${ROOT_DIR}" >&2
  exit 1
fi

cp "${HOOK_SRC}" "${HOOK_DST}"
chmod +x "${HOOK_DST}"
echo "installed: ${HOOK_DST}"
echo "tip: run ./tools/version_time_sync.sh Client/README.md Server/README.md before commit"

