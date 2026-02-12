#!/usr/bin/env bash
# =============================================================================
# Freenove Robot Dog (Server side)
# phase5_failure_injection.sh - targeted failure injection drills
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v1.0 (2026-02-09 21:20)
# Author    : pi (admin) + Codex
# -----------------------------------------------------------------------------
# Revision History:
# - 2026-02-09 21:20 v1.0  Initial Phase-5 failure drills for publisher/SFU interruption and recovery verification.
# =============================================================================

set -euo pipefail

PI_IP="${PI_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
STREAM_PATH="${STREAM_PATH:-robotdog}"
HOLD_SEC="${HOLD_SEC:-5}"
RECOVER_TIMEOUT="${RECOVER_TIMEOUT:-20}"

check_http_code() {
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

check_rtsp_200() {
  python3 - "$PI_IP" "$STREAM_PATH" <<'PY'
import socket,sys
host=sys.argv[1]
path="/" + sys.argv[2].strip().lstrip("/")
req=(f"DESCRIBE rtsp://{host}:8554{path} RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n").encode()
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect((host,8554))
    s.sendall(req)
    head=(s.recv(1024).decode("utf-8","ignore").splitlines() or [""])[0]
    print(head)
    raise SystemExit(0 if "200" in head else 1)
except Exception:
    raise SystemExit(1)
finally:
    try: s.close()
    except Exception: pass
PY
}

wait_recover_rtsp() {
  local t=0
  while [ "$t" -lt "$RECOVER_TIMEOUT" ]; do
    if check_rtsp_200 >/dev/null 2>&1; then
      echo "ok recover:rtsp sec=${t}"
      return 0
    fi
    sleep 1
    t=$((t+1))
  done
  echo "fail recover:rtsp timeout=${RECOVER_TIMEOUT}s"
  return 1
}

wait_recover_whep() {
  local t=0
  while [ "$t" -lt "$RECOVER_TIMEOUT" ]; do
    if check_http_code "whep-options" "http://${PI_IP}:8889/${STREAM_PATH}/whep" "204" "OPTIONS" >/dev/null 2>&1; then
      echo "ok recover:whep sec=${t}"
      return 0
    fi
    sleep 1
    t=$((t+1))
  done
  echo "fail recover:whep timeout=${RECOVER_TIMEOUT}s"
  return 1
}

echo "== Phase-5 Failure Injection =="
echo "PI_IP=${PI_IP} STREAM_PATH=${STREAM_PATH} HOLD_SEC=${HOLD_SEC} RECOVER_TIMEOUT=${RECOVER_TIMEOUT}"

echo
echo "-- Baseline checks"
check_http_code "viewer" "http://${PI_IP}:8080/webrtc_view.html" "200"
check_http_code "telemetry" "http://${PI_IP}:8090/api/telemetry" "200"
check_http_code "whep-options" "http://${PI_IP}:8889/${STREAM_PATH}/whep" "204" "OPTIONS"
check_rtsp_200 >/dev/null
echo "ok baseline:rtsp"

echo
echo "-- Drill A: publisher interruption"
sudo systemctl stop robot-publisher.service
sleep "$HOLD_SEC"
if check_rtsp_200 >/dev/null 2>&1; then
  echo "warn drillA:rtsp still available while publisher stopped"
else
  echo "ok drillA:rtsp interrupted"
fi
sudo systemctl start robot-publisher.service
wait_recover_rtsp

echo
echo "-- Drill B: SFU interruption"
sudo systemctl stop robot-sfu.service
sleep "$HOLD_SEC"
if check_http_code "whep-options-down" "http://${PI_IP}:8889/${STREAM_PATH}/whep" "204" "OPTIONS" >/dev/null 2>&1; then
  echo "warn drillB:whep still reachable while SFU stopped"
else
  echo "ok drillB:whep interrupted"
fi
sudo systemctl start robot-sfu.service
wait_recover_whep

echo
echo "-- Post checks"
check_http_code "viewer" "http://${PI_IP}:8080/webrtc_view.html" "200"
check_http_code "telemetry" "http://${PI_IP}:8090/api/telemetry" "200"
check_http_code "diagnostics" "http://${PI_IP}:8090/api/diagnostics" "200"
check_rtsp_200 >/dev/null
echo "ok post:rtsp"

echo
echo "== Failure injection completed =="
