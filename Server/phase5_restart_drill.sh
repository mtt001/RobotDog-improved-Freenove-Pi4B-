#!/usr/bin/env bash
# =============================================================================
# Freenove Robot Dog (Server side)
# phase5_restart_drill.sh - restart/recovery drill for key services
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v1.1 (2026-02-09 20:47)
# Author    : pi (admin) + Codex
# -----------------------------------------------------------------------------
# Revision History:
# - 2026-02-09 20:47 v1.1  Add RTSP DESCRIBE retry window after restarts to account for publisher path warm-up.
# - 2026-02-09 20:43 v1.0  Initial Phase-5 restart drill for smartdog/SFU/viewer/publisher/telemetry.
# =============================================================================

set -euo pipefail

PI_IP="${PI_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
STREAM_PATH="${STREAM_PATH:-robotdog}"
TIMEOUT_SEC="${TIMEOUT_SEC:-20}"

SERVICES=(
  "smartdog.service"
  "robot-sfu.service"
  "robot-publisher.service"
  "robot-telemetry.service"
  "robot-viewer.service"
)

ts_ms() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

wait_active() {
  local svc="$1"
  local start now
  start="$(ts_ms)"
  while true; do
    if systemctl is-active --quiet "$svc"; then
      now="$(ts_ms)"
      echo $((now - start))
      return 0
    fi
    now="$(ts_ms)"
    if [ $(((now - start) / 1000)) -ge "$TIMEOUT_SEC" ]; then
      return 1
    fi
    sleep 0.3
  done
}

check_http() {
  local name="$1" url="$2" expect="${3:-200}" method="${4:-GET}"
  local code
  code="$(curl -sS -m 3 -X "$method" -o /dev/null -w '%{http_code}' "$url" || true)"
  if [ "$code" = "$expect" ]; then
    echo "ok http:${name} code=${code}"
    return 0
  fi
  echo "fail http:${name} code=${code:-n/a} expect=${expect}"
  return 1
}

check_rtsp_once() {
  local host="$1" path="$2"
  python3 - "$host" "$path" <<'PY'
import socket, sys
host = sys.argv[1]
path = "/" + sys.argv[2].strip().lstrip("/")
req = (f"DESCRIBE rtsp://{host}:8554{path} RTSP/1.0\r\n"
       "CSeq: 1\r\n"
       "Accept: application/sdp\r\n\r\n").encode()
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect((host, 8554))
    s.sendall(req)
    line = (s.recv(2048).decode("utf-8", "ignore").splitlines() or [""])[0]
    if "200" in line:
        print("ok rtsp:DESCRIBE", line)
        raise SystemExit(0)
    print("fail rtsp:DESCRIBE", line)
    raise SystemExit(1)
except Exception as e:
    print("fail rtsp:DESCRIBE", e)
    raise SystemExit(1)
finally:
    try:
        s.close()
    except Exception:
        pass
PY
}

check_rtsp_with_retry() {
  local host="$1" path="$2" timeout="${3:-15}"
  local start now
  start="$(date +%s)"
  while true; do
    if check_rtsp_once "$host" "$path"; then
      return 0
    fi
    now="$(date +%s)"
    if [ $((now - start)) -ge "$timeout" ]; then
      echo "fail rtsp:DESCRIBE retry_timeout=${timeout}s"
      return 1
    fi
    sleep 1
  done
}

echo "== Phase-5 Restart Drill =="
echo "PI_IP=${PI_IP} STREAM_PATH=${STREAM_PATH} TIMEOUT_SEC=${TIMEOUT_SEC}"

for svc in "${SERVICES[@]}"; do
  echo
  echo "-- Restart ${svc}"
  sudo systemctl restart "$svc"
  if ms="$(wait_active "$svc")"; then
    echo "ok service:${svc} active_after_ms=${ms}"
  else
    echo "fail service:${svc} did_not_become_active_within=${TIMEOUT_SEC}s"
    exit 1
  fi
done

echo
echo "-- Endpoint checks after restart drill"
check_http "viewer" "http://${PI_IP}:8080/webrtc_view.html" "200"
check_http "viewer-health" "http://${PI_IP}:8080/health" "200"
check_http "whep-options" "http://${PI_IP}:8889/${STREAM_PATH}/whep" "204" "OPTIONS"
check_http "telemetry" "http://${PI_IP}:8090/api/telemetry" "200"
check_http "session" "http://${PI_IP}:8090/api/session" "200"
check_http "diagnostics" "http://${PI_IP}:8090/api/diagnostics" "200"
check_rtsp_with_retry "${PI_IP}" "${STREAM_PATH}" 18

echo
echo "== Restart drill completed =="
