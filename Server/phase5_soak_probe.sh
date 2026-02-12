#!/usr/bin/env bash
# =============================================================================
# Freenove Robot Dog (Server side)
# phase5_soak_probe.sh - short soak probe for service/endpoint continuity
# Location  : /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
# Version   : v1.0 (2026-02-09 20:43)
# Author    : pi (admin) + Codex
# -----------------------------------------------------------------------------
# Revision History:
# - 2026-02-09 20:43 v1.0  Initial soak probe loop for Phase-5 pre-soak validation.
# =============================================================================

set -euo pipefail

PI_IP="${PI_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
DURATION_SEC="${DURATION_SEC:-300}"
INTERVAL_SEC="${INTERVAL_SEC:-5}"
STREAM_PATH="${STREAM_PATH:-robotdog}"

end_ts=$(( $(date +%s) + DURATION_SEC ))
round=0
fails=0

echo "== Phase-5 Soak Probe =="
echo "PI_IP=${PI_IP} DURATION_SEC=${DURATION_SEC} INTERVAL_SEC=${INTERVAL_SEC}"

check_code() {
  local url="$1" expect="$2" method="${3:-GET}"
  local code
  code="$(curl -sS -m 3 -X "$method" -o /dev/null -w '%{http_code}' "$url" || true)"
  [ "$code" = "$expect" ]
}

while [ "$(date +%s)" -lt "$end_ts" ]; do
  round=$((round + 1))
  ts="$(date '+%H:%M:%S')"
  ok=1

  systemctl is-active --quiet smartdog.service || ok=0
  systemctl is-active --quiet robot-sfu.service || ok=0
  systemctl is-active --quiet robot-publisher.service || ok=0
  systemctl is-active --quiet robot-viewer.service || ok=0
  systemctl is-active --quiet robot-telemetry.service || ok=0

  check_code "http://${PI_IP}:8080/webrtc_view.html" "200" || ok=0
  check_code "http://${PI_IP}:8080/health" "200" || ok=0
  check_code "http://${PI_IP}:8889/${STREAM_PATH}/whep" "204" "OPTIONS" || ok=0
  check_code "http://${PI_IP}:8090/api/telemetry" "200" || ok=0
  check_code "http://${PI_IP}:8090/api/session" "200" || ok=0
  check_code "http://${PI_IP}:8090/api/diagnostics" "200" || ok=0

  if [ "$ok" -eq 1 ]; then
    echo "[$ts] round=${round} ok"
  else
    fails=$((fails + 1))
    echo "[$ts] round=${round} fail"
  fi

  sleep "$INTERVAL_SEC"
done

echo "== Soak Probe Summary =="
echo "rounds=${round} fails=${fails}"
if [ "$fails" -eq 0 ]; then
  echo "result=pass"
else
  echo "result=degraded"
fi
