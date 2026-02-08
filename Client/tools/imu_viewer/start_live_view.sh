#!/usr/bin/env bash
# One-command launcher for IMU live view stack:
# - Starts MediaMTX SFU on Mac
# - Starts Pi publisher (RTSP ingest to SFU)
# - Starts Demo_IMU_server.py proxy (WebRTC-first)
# - Opens browser page
#
# Usage:
#   ./start_live_view.sh
# Optional env overrides:
#   PI=192.168.0.32 SFU=192.168.0.198 HTTP_PORT=8080 PAGE=simple ./start_live_view.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMU_DIR="$ROOT_DIR/imu_viewer"
SFU_CFG="$ROOT_DIR/realtime_webrtc/sfu/mediamtx.yml"
PI_PUB_DIR="/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/realtime_webrtc/robot"
LOCAL_PI_PUB_SCRIPT="$ROOT_DIR/realtime_webrtc/robot/pi_publish_webrtc.sh"

PI="${PI:-192.168.0.32}"
SFU="${SFU:-192.168.0.198}"
STREAM_PATH="${STREAM_PATH:-robotdog}"
HTTP_PORT="${HTTP_PORT:-8080}"
PAGE="${PAGE:-simple}" # simple|color|index
PUB_WIDTH="${PUB_WIDTH:-1280}"
PUB_HEIGHT="${PUB_HEIGHT:-720}"
PUB_FPS="${PUB_FPS:-30}"
PUB_BITRATE="${PUB_BITRATE:-3500000}"

MTX_BIN="${MTX_BIN:-/opt/homebrew/opt/mediamtx/bin/mediamtx}"
PROXY_LOG="${PROXY_LOG:-/tmp/imu_proxy.log}"
MTX_LOG="${MTX_LOG:-/tmp/mediamtx.log}"

if [[ ! -x "$MTX_BIN" ]]; then
  echo "ERROR: mediamtx binary not found: $MTX_BIN" >&2
  exit 1
fi

case "$PAGE" in
  simple) VIEW_PATH="/simple" ;;
  color) VIEW_PATH="/color" ;;
  index) VIEW_PATH="/" ;;
  *) echo "ERROR: PAGE must be simple|color|index" >&2; exit 1 ;;
esac

echo "[1/5] Starting SFU (MediaMTX)"
pkill -f "$MTX_BIN" >/dev/null 2>&1 || true
nohup "$MTX_BIN" "$SFU_CFG" >"$MTX_LOG" 2>&1 < /dev/null &
sleep 1

echo "[2/5] Verifying SFU WHEP endpoint"
if ! curl -sS -m 3 -i -X OPTIONS "http://${SFU}:8889/${STREAM_PATH}/whep" | grep -q "204 No Content"; then
  echo "ERROR: SFU WHEP endpoint not ready: http://${SFU}:8889/${STREAM_PATH}/whep" >&2
  tail -n 60 "$MTX_LOG" || true
  exit 1
fi

echo "[3/5] Starting Pi publisher (RTSP ingest)"
# Sync latest publisher script to Pi so runtime behavior matches local fixes.
scp -o ConnectTimeout=8 -o BatchMode=yes "$LOCAL_PI_PUB_SCRIPT" "pi@${PI}:${PI_PUB_DIR}/pi_publish_webrtc.sh" >/dev/null
ssh -o ConnectTimeout=8 -o BatchMode=yes "pi@${PI}" "chmod +x ${PI_PUB_DIR}/pi_publish_webrtc.sh" >/dev/null
# Use -f so SSH does not block waiting on remote background jobs.
ssh -f -o ConnectTimeout=8 -o BatchMode=yes "pi@${PI}" \
  "bash -lc 'cd ${PI_PUB_DIR} && nohup env SFU_HOST=${SFU} STREAM_PATH=${STREAM_PATH} PUBLISH_MODE=rtsp WIDTH=${PUB_WIDTH} HEIGHT=${PUB_HEIGHT} FPS=${PUB_FPS} BITRATE=${PUB_BITRATE} ./pi_publish_webrtc.sh >/tmp/pi_publish_webrtc.log 2>&1 < /dev/null &'" \
  >/dev/null

# Confirm SFU actually sees the stream online before continuing.
stream_online=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if grep -Eiq "path ${STREAM_PATH}.*online|is publishing to path '${STREAM_PATH}'" "$MTX_LOG" 2>/dev/null; then
    stream_online=1
    break
  fi
  sleep 1
done
if [[ "$stream_online" -ne 1 ]]; then
  echo "WARN: publisher started but SFU has not reported path '${STREAM_PATH}' online yet." >&2
  echo "      Check Pi log: ssh pi@${PI} 'tail -n 120 /tmp/pi_publish_webrtc.log'" >&2
fi

echo "[4/5] Starting IMU proxy (WebRTC-first)"
pkill -f "Demo_IMU_server.py" >/dev/null 2>&1 || true
pkill -f "imu_proxy_supervisor_loop" >/dev/null 2>&1 || true
cd "$IMU_DIR"
nohup bash -lc "
  # imu_proxy_supervisor_loop
  while true; do
    python3 -u Demo_IMU_server.py \
      --pi-host '$PI' \
      --http-port '$HTTP_PORT' \
      --webrtc-url 'http://${SFU}:8889/${STREAM_PATH}/whep' \
      >>'$PROXY_LOG' 2>&1
    echo \"[supervisor] proxy exited, restarting in 1s\" >>'$PROXY_LOG'
    sleep 1
  done
" >/dev/null 2>&1 < /dev/null &

# Wait until proxy responds or fail fast with logs.
proxy_ok=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS -m 2 "http://127.0.0.1:${HTTP_PORT}/diag" >/dev/null 2>&1; then
    proxy_ok=1
    break
  fi
  sleep 1
done
if [[ "$proxy_ok" -ne 1 ]]; then
  echo "ERROR: proxy did not come up on :${HTTP_PORT}" >&2
  tail -n 120 "$PROXY_LOG" || true
  exit 1
fi

STATUS_JSON="$(curl -sS -m 4 "http://127.0.0.1:${HTTP_PORT}/video/status" || true)"
echo "[5/5] Proxy video status:"
echo "$STATUS_JSON"

echo "Opening browser: http://127.0.0.1:${HTTP_PORT}${VIEW_PATH}"
open "http://127.0.0.1:${HTTP_PORT}${VIEW_PATH}"

if echo "$STATUS_JSON" | grep -q '"preferred": "webrtc"'; then
  echo "OK: WebRTC preferred."
else
  echo "WARN: Not on WebRTC yet. Check:"
  echo "  - Mac SFU log: $MTX_LOG"
  echo "  - Pi publisher log: ssh pi@${PI} 'tail -n 120 /tmp/pi_publish_webrtc.log'"
  echo "  - Proxy log: $PROXY_LOG"
fi
