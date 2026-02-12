#!/usr/bin/env bash
# =============================================================================
# Freenove Robot Dog (Server side)
# phase1_health_check.sh - one-command health check for Phase-1 always-on hosting
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v1.2 (2026-02-09 18:55)
# Author    : pi (admin) + Codex
# -----------------------------------------------------------------------------
# Revision History:
# - 2026-02-09 18:55 v1.2  Add telemetry/session/diagnostics endpoint checks for Phase-5 observability coverage.
# - 2026-02-09 15:15 v1.1  Use OPTIONS for WHEP endpoint probe to avoid false-negative GET status.
# - 2026-02-09 15:15 v1.0  Initial Phase-1 health checker for smartdog/SFU/viewer/publisher endpoints.
# =============================================================================

set -euo pipefail

PI_IP="${PI_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
STREAM_PATH="${STREAM_PATH:-robotdog}"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red() { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

check_service() {
  local svc="$1"
  local active
  active="$(systemctl is-active "$svc" 2>/dev/null || true)"
  if [ "$active" = "active" ]; then
    green "service:$svc active"
  else
    red "service:$svc $active"
  fi
}

check_http_code() {
  local name="$1" url="$2" expect="$3" method="${4:-GET}"
  local code
  code="$(curl -sS -m 3 -X "$method" -o /dev/null -w '%{http_code}' "$url" || true)"
  if [ "$code" = "$expect" ]; then
    green "http:$name ${code} (${url})"
  else
    red "http:$name ${code:-n/a} (${url}) expected ${expect}"
  fi
}

check_rtsp_describe() {
  local host="$1" path="$2"
  local line
  line="$(python3 - "$host" "$path" <<'PY'
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
    print((s.recv(2048).decode("utf-8", "ignore").splitlines() or [""])[0])
except Exception as e:
    print(f"FAIL: {e}")
finally:
    try:
        s.close()
    except Exception:
        pass
PY
)"
  if printf "%s" "$line" | grep -q "200"; then
    green "rtsp:DESCRIBE $line"
  else
    red "rtsp:DESCRIBE ${line:-n/a}"
  fi
}

echo "== Phase-1 Health Check =="
echo "PI_IP=${PI_IP:-n/a} STREAM_PATH=${STREAM_PATH}"
echo

check_service smartdog.service
check_service robot-sfu.service
check_service robot-viewer.service
check_service robot-publisher.service
check_service robot-telemetry.service

echo
check_http_code "viewer" "http://${PI_IP}:8080/webrtc_view.html" "200"
check_http_code "whep-options" "http://${PI_IP}:8889/${STREAM_PATH}/whep" "204" "OPTIONS"
check_http_code "telemetry-api" "http://${PI_IP}:8090/api/telemetry" "200"
check_http_code "session-api" "http://${PI_IP}:8090/api/session" "200"
check_http_code "diagnostics-api" "http://${PI_IP}:8090/api/diagnostics" "200"
check_rtsp_describe "${PI_IP}" "${STREAM_PATH}"

echo
yellow "Tip: run 'sudo journalctl -u robot-sfu.service -u robot-publisher.service -n 80 --no-pager' on failure."
