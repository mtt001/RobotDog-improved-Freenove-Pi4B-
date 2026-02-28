#!/usr/bin/env bash

# Start AI Status Heartbeat
# Version: v1.0 (2026-02-28 23:56 CST)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/iCloud/AI_Reports"
PID_FILE="$REPORT_DIR/heartbeat.pid"
TASK_NAME="${1:-Long Copilot Work (Heartbeat Mode)}"
INTERVAL_SECONDS="${2:-600}"

mkdir -p "$REPORT_DIR"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Heartbeat already running (pid=$OLD_PID)."
    exit 0
  fi
  rm -f "$PID_FILE"
fi

nohup "$ROOT_DIR/tools/ai_status_heartbeat.sh" "$INTERVAL_SECONDS" "$TASK_NAME" >/dev/null 2>&1 &
NEW_PID="$!"
echo "$NEW_PID" > "$PID_FILE"

echo "Heartbeat started (pid=$NEW_PID, interval=${INTERVAL_SECONDS}s)."
