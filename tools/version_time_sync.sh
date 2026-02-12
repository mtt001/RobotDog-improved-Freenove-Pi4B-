#!/usr/bin/env bash
# =============================================================================
# File: version_time_sync.sh
# Purpose: Sync README "## Version" local-time timestamps to current local time.
# Version: v1.00 (2026-02-08 14:59)
# Revision History:
#   v1.00 (2026-02-08 14:59) - Initial tool to update README version timestamp.
# =============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <README.md> [README.md ...]" >&2
  exit 1
fi

NOW="$(date '+%Y-%m-%d %H:%M')"

for f in "$@"; do
  if [[ ! -f "$f" ]]; then
    echo "skip: not found: $f" >&2
    continue
  fi

  # Expected line style:
  # v1.4.3 (2026-02-08 14:52 local time)
  if ! grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+ \([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} local time\)$' "$f"; then
    echo "skip: version line not found or unsupported format: $f" >&2
    continue
  fi

  sed -E -i.bak \
    "s@^(v[0-9]+\.[0-9]+\.[0-9]+ \()[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}( local time\\))@\\1${NOW}\\2@" \
    "$f"
  rm -f "${f}.bak"
  echo "updated: $f -> $NOW"
done

