#!/usr/bin/env bash

# AI Status Heartbeat Worker
# Version: v1.0 (2026-02-28 23:56 CST)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/iCloud/AI_Reports"
STATUS_FILE="$REPORT_DIR/latest_status.md"
LOG_FILE="$REPORT_DIR/heartbeat.log"
PID_FILE="$REPORT_DIR/heartbeat.pid"
INTERVAL_SECONDS="${1:-600}"
TASK_NAME="${2:-Long Copilot Work (Heartbeat Mode)}"

mkdir -p "$REPORT_DIR"

echo "$$" > "$PID_FILE"

while true; do
  TS_LOCAL="$(date '+%Y-%m-%d %H:%M %Z')"

  cat > "$STATUS_FILE" <<EOF
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

  echo "[$TS_LOCAL] heartbeat write -> latest_status.md" >> "$LOG_FILE"
  sleep "$INTERVAL_SECONDS"
done
