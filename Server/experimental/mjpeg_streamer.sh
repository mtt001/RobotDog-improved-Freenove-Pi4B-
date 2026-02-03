# TEST script
# This to test the MJPEG video streaming with Raspberry Pi 4B Setup (server side)
# Prepare once  , suggested by ChatGPT  10/24, 2025

#!/usr/bin/env bash
set -euo pipefail

# mjpg-streamer expects its plugins in this dir
export LD_LIBRARY_PATH=/usr/local/lib/mjpg-streamer

# --- pick ONE input ---
# For CSI camera (flat cable) – recommended:
INPUT='input_raspicam.so -x 640 -y 480 -fps 20 -q 80'
# For USB/UVC webcam (if you ever use one):
# INPUT='input_uvc.so -d /dev/video0 -r 640x480 -f 20'

# Start HTTP server on :8080
exec /usr/local/bin/mjpg_streamer \
  -i "$INPUT" \
  -o "output_http.so -p 8080 -w /usr/local/www"

