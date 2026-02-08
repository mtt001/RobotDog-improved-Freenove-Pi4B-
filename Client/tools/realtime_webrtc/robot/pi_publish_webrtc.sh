#!/usr/bin/env bash
# Robot Pi WebRTC Publisher
# Version: 2026.02.07-2
# Revision History:
#   2026-02-07 - Add auto-retry loop for transient SFU/publish disconnects.
#   2026-02-07 - Initial publish script (WHIP primary, RTSP fallback).
# Usage:
#   SFU_HOST=192.168.0.198 STREAM_PATH=robotdog ./pi_publish_webrtc.sh
#   PUBLISH_MODE=rtsp SFU_HOST=192.168.0.198 ./pi_publish_webrtc.sh

set -euo pipefail

SFU_HOST="${SFU_HOST:-192.168.0.198}"
STREAM_PATH="${STREAM_PATH:-robotdog}"
WIDTH="${WIDTH:-960}"
HEIGHT="${HEIGHT:-540}"
FPS="${FPS:-30}"
BITRATE="${BITRATE:-2000000}"
PUBLISH_MODE="${PUBLISH_MODE:-whip}" # whip|rtsp
RETRY_SLEEP="${RETRY_SLEEP:-1}"

WHIP_URL="${WHIP_URL:-http://${SFU_HOST}:8889/${STREAM_PATH}/whip}"
RTSP_URL="${RTSP_URL:-rtsp://${SFU_HOST}:8554/${STREAM_PATH}}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found on Pi. Install: sudo apt-get install -y ffmpeg"
  exit 1
fi

camera_cmd=""
if command -v vcgencmd >/dev/null 2>&1; then
  if vcgencmd get_camera 2>/dev/null | grep -q "libcamera interfaces=0"; then
    if command -v raspivid >/dev/null 2>&1; then
      camera_cmd="raspivid -n -ih -t 0 -w ${WIDTH} -h ${HEIGHT} -fps ${FPS} -b ${BITRATE} -o -"
    fi
  fi
fi
if [ -z "${camera_cmd}" ] && command -v libcamera-vid >/dev/null 2>&1; then
  camera_cmd="libcamera-vid -n --codec h264 --inline --width ${WIDTH} --height ${HEIGHT} --framerate ${FPS} --timeout 0 --bitrate ${BITRATE} -o -"
fi
if [ -z "${camera_cmd}" ] && command -v rpicam-vid >/dev/null 2>&1; then
  camera_cmd="rpicam-vid -n --codec h264 --inline --width ${WIDTH} --height ${HEIGHT} --framerate ${FPS} --timeout 0 --bitrate ${BITRATE} -o -"
fi
if [ -z "${camera_cmd}" ]; then
  echo "No Pi camera capture command found (raspivid/libcamera-vid/rpicam-vid)."
  exit 1
fi

echo "[publisher] mode=${PUBLISH_MODE} host=${SFU_HOST} path=${STREAM_PATH} ${WIDTH}x${HEIGHT}@${FPS}"

run_whip() {
  # WebRTC ingest path (preferred). Requires ffmpeg with WHIP muxer support.
  bash -lc "${camera_cmd}" | ffmpeg -hide_banner -loglevel info \
    -fflags nobuffer -flags low_delay \
    -f h264 -i pipe:0 \
    -an -c:v copy \
    -f whip "${WHIP_URL}"
}

run_rtsp() {
  # Fallback ingest: RTSP publish to SFU, SFU serves WebRTC to clients.
  bash -lc "${camera_cmd}" | ffmpeg -hide_banner -loglevel info \
    -fflags nobuffer -flags low_delay \
    -f h264 -i pipe:0 \
    -an -c:v copy \
    -f rtsp -rtsp_transport tcp "${RTSP_URL}"
}

set -x
while true; do
  if [ "${PUBLISH_MODE}" = "whip" ]; then
    if run_whip; then
      exit 0
    fi
    echo "[publisher] WHIP publish failed, auto-falling back to RTSP: ${RTSP_URL}" >&2
    if run_rtsp; then
      exit 0
    fi
  else
    if run_rtsp; then
      exit 0
    fi
  fi
  echo "[publisher] publish stream ended/failed; retrying in ${RETRY_SLEEP}s ..." >&2
  sleep "${RETRY_SLEEP}"
done
