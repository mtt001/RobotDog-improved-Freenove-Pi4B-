# IMU Viewer (WebRTC-First) Runbook

README Version: `2026.02.07-15`  
Last Updated: `2026-02-07 18:59:09 CST`

This document is the operational guide for `Demo_IMU_server.py` and the Live View stack (Pi publisher + MediaMTX SFU + browser viewer).

## Quick Usage (Start Here)

### A) One command (recommended)
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/imu_viewer
./start_live_view.sh
```

What this does:
- Starts SFU (`mediamtx`) on Mac (`192.168.0.198`)
- Syncs and starts Pi publisher (`robotdog` path)
- Starts proxy (`Demo_IMU_server.py`) in WebRTC-first mode
- Opens browser at `http://127.0.0.1:8080/simple`

### B) Verify immediately
```bash
curl -s http://127.0.0.1:8080/video/status
```
Expected key fields:
- `"webrtc": {"ready": true, ...}`
- `"preferred": "webrtc"`

### C) Open pages
- `http://127.0.0.1:8080/`
- `http://127.0.0.1:8080/simple`
- `http://127.0.0.1:8080/color`

## What This Tool Does

`Demo_IMU_server.py`:
- Proxies IMU + telemetry commands to Pi control server (`5001`)
- Serves web UI assets (`/`, `/simple`, `/color`, JS, assets)
- Exposes stream status endpoint (`/video/status`)
- Uses WebRTC/SFU as preferred path when `--webrtc-url` is set
- Falls back to MJPEG bridge (`/video.mjpeg`) when WebRTC is unavailable

## Current Default Runtime Configuration

Source of truth: `Demo_IMU_server.py` `DEFAULT_*` constants.

- Pi host: `192.168.0.32`
- Pi control port: `5001`
- Pi video port (MJPEG): `8001`
- HTTP bind: `0.0.0.0:8080`
- Default SFU host: `192.168.0.198`
- Stream path: `robotdog`
- Default WebRTC URL: `http://192.168.0.198:8889/robotdog/whep`

Important behavior:
- When WebRTC URL is configured, local H264 pull is auto-disabled by default to avoid Pi camera contention (`ENOSPC`).
- You can override with `--enable-h264-fallback`.

## Requirements

### Raspberry Pi
- Pi reachable on LAN (example `192.168.0.32`)
- Robot server running (`main.py` / `smartdog.service`)
- Control port `5001` open
- Camera available and not monopolized by unrelated processes

### Mac (viewer/proxy/SFU host)
- `python3`
- `ssh`
- `ffmpeg`
- `mediamtx` binary (`/opt/homebrew/opt/mediamtx/bin/mediamtx` by default)

## Operational Modes

### Mode 1: Full stack auto-launch (recommended)
Use `start_live_view.sh`.

### Mode 2: Manual launch
1. Start SFU
```bash
/opt/homebrew/opt/mediamtx/bin/mediamtx /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/realtime_webrtc/sfu/mediamtx.yml
```
2. Start Pi publisher (example 1280x720)
```bash
ssh pi@192.168.0.32 'cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/realtime_webrtc/robot && nohup env SFU_HOST=192.168.0.198 STREAM_PATH=robotdog PUBLISH_MODE=rtsp WIDTH=1280 HEIGHT=720 FPS=30 BITRATE=3500000 ./pi_publish_webrtc.sh >/tmp/pi_publish_webrtc.log 2>&1 < /dev/null &'
```
3. Start proxy
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/imu_viewer
python3 Demo_IMU_server.py
```

## Resolution and FPS Control

Primary stream caps are set by Pi publisher environment values:
- `WIDTH`
- `HEIGHT`
- `FPS`
- `BITRATE`

Examples:
- 960x540: `WIDTH=960 HEIGHT=540 FPS=30 BITRATE=2000000`
- 1280x720: `WIDTH=1280 HEIGHT=720 FPS=30 BITRATE=3500000`
- 1920x1080: `WIDTH=1920 HEIGHT=1080 FPS=30 BITRATE=6000000`

Live title shows actual browser-received dimensions/FPS, for example:
- `Live View 1280x720, 11.8 fps`

## Key Endpoints

- `GET /imu` IMU JSON (`roll/pitch/yaw`)
- `GET /telemetry` battery/range
- `GET /diag` proxy-to-Pi connectivity status
- `GET /video/status` active stream readiness and preference
- `GET /video.mjpeg` MJPEG stream fallback
- `POST /cmd` robot command passthrough (`{"cmd":"CMD_*"}`)

## Health Checks

### Local checks (Mac)
```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
lsof -nP -iTCP:8889 -sTCP:LISTEN
lsof -nP -iTCP:8554 -sTCP:LISTEN
curl -s http://127.0.0.1:8080/diag
curl -s http://127.0.0.1:8080/video/status
curl -i -X OPTIONS http://192.168.0.198:8889/robotdog/whep
```

### Pi checks
```bash
ssh pi@192.168.0.32 'pgrep -af "main.py|raspivid|libcamera-vid|rpicam-vid|ffmpeg|pi_publish_webrtc"'
ssh pi@192.168.0.32 'tail -n 120 /tmp/pi_publish_webrtc.log'
```

### SFU checks
```bash
tail -n 120 /tmp/mediamtx.log
```
Look for:
- `is publishing to path 'robotdog'`
- `stream is available and online`

## Troubleshooting Matrix

Symptom: `Stream: Proprietary MJPEG` appears
- Cause: WebRTC endpoint unavailable or no stream on SFU path
- Check: `/video/status` `webrtc.error`
- Fix: restart SFU and Pi publisher, then retry

Symptom: Browser popup says `Pi Server not reachable`
- Cause: proxy not reachable on `8080` or Pi control connection dropped
- Check: `curl http://127.0.0.1:8080/diag`
- Fix: restart proxy, confirm Pi `5001`

Symptom: `ENOSPC` in Pi publisher log
- Cause: camera contention (multiple camera holders)
- Fix: kill stale `raspivid/libcamera-vid/rpicam-vid/ffmpeg`, relaunch single publisher

Symptom: `Connection refused` to `:8554` or `:8889`
- Cause: SFU process not running on Mac
- Fix: restart `mediamtx`; verify listeners with `lsof`

Symptom: stream starts then drops (`Broken pipe`)
- Cause: transient network disconnect or SFU restart
- Fix: keep publisher auto-retry enabled (default in current script), verify SFU uptime

## Recovery Runbook

Use this when state is inconsistent:
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/imu_viewer
./start_live_view.sh
curl -s http://127.0.0.1:8080/video/status
```

If still failing, collect and inspect:
```bash
tail -n 120 /tmp/mediamtx.log
tail -n 120 /tmp/imu_proxy.log
ssh pi@192.168.0.32 'tail -n 120 /tmp/pi_publish_webrtc.log'
```

## Files and Roles

- `Demo_IMU_server.py`: HTTP proxy + IMU bridge + stream status API
- `live_video.js`: browser-side stream selector (WebRTC/H264/MJPEG)
- `start_live_view.sh`: one-command orchestrator
- `../realtime_webrtc/sfu/mediamtx.yml`: SFU config
- `../realtime_webrtc/robot/pi_publish_webrtc.sh`: Pi publisher

## Notes

- A `204` on `OPTIONS /robotdog/whep` means endpoint exists, not necessarily that stream is currently online.
- `video/status -> webrtc.ready=true` plus SFU path online is the practical condition for live WebRTC playback.
- Browser tab may need hard reload (`Cmd+Shift+R`) after stack restarts.
