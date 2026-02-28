#!/usr/bin/env bash

# Stop AI Status Heartbeat
# Version: v1.0 (2026-02-28 23:56 CST)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/iCloud/AI_Reports"
PID_FILE="$REPORT_DIR/heartbeat.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No heartbeat pid file found."
  exit 0
fi

PID="$(cat "$PID_FILE" || true)"
if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID" || true
  sleep 0.2
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" || true
  fi
  echo "Heartbeat stopped (pid=$PID)."
else
  echo "Heartbeat process not running; cleaning stale pid file."
fi

rm -f "$PID_FILE"
