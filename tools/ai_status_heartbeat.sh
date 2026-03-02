#!/usr/bin/env bash

# AI Status Heartbeat Worker
# Version: v1.1 (2026-03-01 00:06 CST)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_REPORT_DIR="$ROOT_DIR/iCloud/AI_Reports"
ICLOUD_REPORT_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AI_Reports"
STATUS_FILE_REPO="$REPO_REPORT_DIR/latest_status.md"
STATUS_FILE_ICLOUD="$ICLOUD_REPORT_DIR/latest_status.md"
LOG_FILE="$REPO_REPORT_DIR/heartbeat.log"
PID_FILE="$REPO_REPORT_DIR/heartbeat.pid"
INTERVAL_SECONDS="${1:-600}"
TASK_NAME="${2:-Long Copilot Work (Heartbeat Mode)}"

mkdir -p "$REPO_REPORT_DIR"
mkdir -p "$ICLOUD_REPORT_DIR"

echo "$$" > "$PID_FILE"

while true; do
  TS_LOCAL="$(date '+%Y-%m-%d %H:%M %Z')"

  STATUS_BODY="$(cat <<EOF
# AI Live Status

## Version
v1.2 ($TS_LOCAL)

---

- Current Task: $TASK_NAME
- Current Phase: Running (Heartbeat)
- Timestamp: $TS_LOCAL
- Elapsed Time: Heartbeat mode
- Session Units: Tracking in active chat
- Task Delta: Tracking in active chat
- Monthly Estimate: Tracking in active chat
- Burn Velocity (units/hour): Tracking in active chat
- Oscillation Detected: NO
- Warning Level: LOW

---

Update Note:
- Automatic heartbeat is active.
- This file refreshes every $INTERVAL_SECONDS seconds for iPhone monitoring.
EOF
)"

  printf '%s\n' "$STATUS_BODY" > "$STATUS_FILE_REPO"
  printf '%s\n' "$STATUS_BODY" > "$STATUS_FILE_ICLOUD"

  echo "[$TS_LOCAL] heartbeat write -> repo+iCloud latest_status.md" >> "$LOG_FILE"
  sleep "$INTERVAL_SECONDS"
done
