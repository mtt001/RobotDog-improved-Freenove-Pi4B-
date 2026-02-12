# Freenove Robot Dog - Server
# File: Code/Server/README.md
> **Server-only README** — this file documents the Raspberry Pi Server code and **syncs with the Pi Server side**.

## Version
v1.16.24 (2026-02-12 17:43 local time)

## Quick Start
1. Start core server (headless fallback):
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
python3 main.py -tn
```
2. Confirm ports:
```bash
ss -lntp | egrep ':5001|:8001'
```
3. Safari-first operation (most users):
```bash
systemctl is-active smartdog.service robot-sfu.service robot-viewer.service robot-color-viewer.service robot-publisher.service robot-telemetry.service
```
- Open in Safari (iPhone/iPad/macOS): [http://192.168.0.32:8081/color](http://192.168.0.32:8081/color)
- Legacy/basic viewer page remains available at: [http://192.168.0.32:8080/webrtc_view.html](http://192.168.0.32:8080/webrtc_view.html)
- Wait for WebRTC video to show `Peer connected`.
- Press `ARM` before movement commands.
- Use hold-to-move controls (release to stop).
- Use `STOP` any time for immediate safety stop.
- Important: do not open [http://192.168.0.32:8889/robotdog/whep](http://192.168.0.32:8889/robotdog/whep) directly; it is signaling API, not player page.

## Operational Overview (WebRTC/SFU + YOLO on Pi)
This deployment is now Pi-first and can run standalone for control + streaming + browser ops.

1. Core control/video service:
- `smartdog.service` runs `Server/main.py`.
- `Server/Server.py` exposes:
  - `5001` (control + telemetry socket protocol)
  - `8001` (legacy proprietary JPEG socket stream, also used as detector ingest source)

2. Streaming fanout (SFU path):
- `robot-publisher.service` runs `pi_publish_webrtc.sh` and publishes camera H.264 to `rtsp://<pi-or-sfu-host>:8554/robotdog`.
- `robot-sfu.service` (MediaMTX) fans out to:
  - RTSP readers (e.g., desktop tooling)
  - WebRTC/WHEP readers (`/robotdog/whep`) for Safari.

3. Browser runtime:
- `robot-viewer.service` serves `Server/web/webrtc_view.html` on `:8080`.
- The page negotiates WebRTC to `:8889` and calls telemetry/command APIs on `:8090`.

4. Telemetry + safe command API:
- `robot-telemetry.service` runs `Server/telemetry_api_server.py`.
- Exposes:
  - `/api/telemetry` (overlay + health)
  - `/api/session` (arm/disarm + control-lock status)
  - `/api/command` (session-gated command path)
  - `/api/diagnostics` (service + port + session diagnostics)

5. YOLO/Tracking runtime (Pi color-viewer lane):
- `robot-color-viewer.service` runs `color_viewer_server.py` (Pi deployment source tracked from `Client/tools/imu_viewer/color_viewer_server.py`).
- Runtime endpoints on `:8081` include `/vision/state`, `/vision/config`, `/vision/metrics`.
- Runtime video profile endpoint `/video/config` now persists profile and publisher override for WebRTC resolution continuity:
  - profile store: `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/color_viewer/video_runtime_config.json`
  - publisher env override: `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/color_viewer/video_publisher_profile.env`
  - apply path: attempts `robot-publisher.service` restart; if restart is unavailable, saved profile still applies on next publisher restart/power cycle.
  - `/color` frontend now emits profile-apply event and triggers immediate WebRTC renegotiation, reducing/noing manual Safari refresh requirement after resolution change.
  - Color-viewer HTTP responses now include no-store cache headers, and frontend performs delayed profile re-sync calls after load to avoid stale Safari default-profile display.
- Detector pipeline reads stream from `8001` first, then falls back to `rtsp://<pi>:8554/robotdog`.
- Current deployed backend path supports `tflite-multi` with `best`-first then `yolov8n` fallback scheduling; KPI blocker is CPU saturation under dual-model load.

## File Structure and Hierarchy (All Operational Files)
Operational files are grouped by runtime role. `Server/` below is Pi runtime ownership; some service/template sources live under `Client/tools/*` and are deployed/synced to Pi.

```text
Code/
├── Server/                                  # Pi runtime ownership (control, APIs, web UI, ops runbooks)
│   ├── main.py                              # smartdog entrypoint
│   ├── Server.py                            # TCP services: 5001 control + 8001 video socket
│   ├── Control.py                           # command execution and motion/actuation paths
│   ├── Command.py                           # command symbols/protocol glue
│   ├── Action.py                            # demo/action helper calls used by color-viewer demo endpoint
│   ├── telemetry_api_server.py              # :8090 telemetry/session/command/diagnostics API
│   ├── smartdog.sh                          # service orchestrator/status helper for Pi
│   ├── phase1_health_check.sh               # baseline service/endpoint health check
│   ├── phase5_restart_drill.sh              # restart resilience drill
│   ├── phase5_soak_probe.sh                 # soak stability probe
│   ├── phase5_failure_injection.sh          # failure injection + recovery check
│   ├── phaseD_benchmark_1hz.sh              # 1Hz KPI benchmark for CPU/thermal/video/vision gates
│   ├── HARDENING_PREWAN_CHECKLIST.md        # pre-WAN security hardening checklist
│   ├── REMOTE_SAFARI_ACCESS_RUNBOOK.md      # outside-LAN Safari access runbook
│   ├── PHASE5_VERIFICATION_REPORT.md        # verification evidence/log summary
│   ├── Command.md                           # command protocol reference
│   ├── COMMAND_FLOW.md                      # protocol/flow reference
│   └── web/
│       ├── webrtc_view.html                 # Pi Safari viewer (WebRTC + telemetry + command UI)
│       ├── static_viewer_server.py          # static host for viewer on :8080 (+ /health)
│       └── index.html                       # helper monitor page
├── Client/
│   └── tools/
│       ├── realtime_webrtc/                 # service templates and SFU/publisher config sources
│       │   ├── robot/
│       │   │   ├── pi_publish_webrtc.sh     # publisher launcher (used by robot-publisher.service)
│       │   │   ├── pi-publisher.service     # systemd unit template
│       │   │   ├── robot-sfu.service        # MediaMTX systemd unit template
│       │   │   ├── robot-viewer.service     # viewer static-host systemd unit template
│       │   │   └── robot-telemetry.service  # telemetry API systemd unit template
│       │   └── sfu/
│       │       └── mediamtx.yml             # SFU (RTSP/WHEP/WebRTC) config source template
│       └── imu_viewer/
│           ├── color_viewer_server.py       # source tracked for Pi robot-color-viewer.service runtime
│           ├── index_color.html             # color-viewer UI served by color_viewer_server.py
│           ├── app_color.js                 # color-viewer logic (vision toggles, API wiring)
│           └── live_video.js                # shared live-video/stream helper logic
└── tools/
    ├── version_time_sync.sh                 # README timestamp synchronizer (Client/Server README pair)
    └── install_time_guard_hook.sh           # pre-commit guard installer for timestamp policy
```

## Service Model (Pi Boot)
- `smartdog.service`:
  - Owns Server `main.py` lifecycle.
  - Provides control/telemetry on `5001` and legacy video socket on `8001`.
- `robot-publisher.service`:
  - Owns H.264 publisher (`pi_publish_webrtc.sh`) for SFU path `robotdog`.
  - Publishes to RTSP `rtsp://<sfu-host>:8554/robotdog` (default mode: `rtsp`, Phase-1 default host is Pi itself).
- `robot-sfu.service`:
  - Owns MediaMTX SFU on Pi (`8554`, `8889`, `9997`).
- `robot-viewer.service`:
  - Serves static Safari viewer on Pi (`http://<pi-ip>:8080/webrtc_view.html`).
  - Source directory on Pi: `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/web/`.
  - Uses `Server/web/static_viewer_server.py` for explicit cache headers and `/health`.
- `robot-color-viewer.service`:
  - Serves enhanced Safari control/view page on Pi (`http://<pi-ip>:8081/color`).
  - Runs `Server/color_viewer/color_viewer_server.py` on Pi runtime.
  - Exposes vision runtime endpoints on `:8081` (for example `/vision/state`, `/vision/config`, `/vision/metrics`).
- `robot-telemetry.service`:
  - Serves telemetry + command MVP API:
    - `GET /api/telemetry` (overlay data)
    - `GET/POST /api/session` (arm/disarm state)
    - `POST /api/command` (mobile command actions)
    - `GET /api/diagnostics` (service/port/session quick diagnostics)
  - Supports optional bearer-token auth gate in API server (`--api-token`, default off).
- These services are independent:
  - `5001` can be healthy while SFU path is offline.
  - Client status can therefore show control green but video red.

## Video Viewing Usage (macOS + iOS Safari)
This server publishes camera video to SFU; in Phase-1 the SFU + viewer host is Pi by default.
1. On Pi, ensure services are active:
```bash
systemctl is-active smartdog.service
systemctl is-active robot-sfu.service
systemctl is-active robot-viewer.service
systemctl is-active robot-color-viewer.service
systemctl is-active robot-publisher.service
systemctl is-active robot-telemetry.service
```
2. Open in browser:
- macOS Safari/Chrome (primary control+video): `http://192.168.0.32:8081/color`
- iOS/iPadOS Safari (primary control+video): `http://192.168.0.32:8081/color`
- Optional legacy/basic viewer: `http://192.168.0.32:8080/webrtc_view.html`

Important:
- `http://192.168.0.32:8889/robotdog/whep` is signaling API endpoint only (not a direct webpage).
- `mtDogMain.py` on Mac reads RTSP from SFU (`rtsp://192.168.0.32:8554/robotdog`), while Safari pages use WebRTC/WHEP.
- Telemetry overlay API endpoint: `http://192.168.0.32:8090/api/telemetry`.
- Mobile command endpoints:
  - Session arm/disarm: `http://192.168.0.32:8090/api/session`
  - Command action: `http://192.168.0.32:8090/api/command`
  - low-risk action set now includes `beep`, `led`, `cal`, `balance_on`, `balance_off` (ARM required)
- Phase-4 session UX metadata/endpoints:
  - `GET /api/session` returns `control_lock`, `owner_hint`, `last_busy_age_ms`
  - `POST /api/session {"action":"request"}` for handoff request workflow
  - `POST /api/session {"action":"release"}` to release/disarm and send stop
- Safety behavior in Phase-3:
  - motion/relax commands require explicit ARM session
  - stop/stop-pwm are always allowed
  - motion watchdog auto-sends stop when hold stream is stale
- Phase-5 observability:
  - diagnostics endpoint: `http://192.168.0.32:8090/api/diagnostics`
  - structured JSON session/command logs from telemetry API service
  - viewer cache policy (development-safe): HTML no-store, JS/CSS short cache
- Viewer header includes visible build badge (`Build: vX | YYYY-MM-DD HH:MM`) for runtime version confirmation.
- Viewer includes low-priority UI parity scaffold:
  - motion-key arrangement aligned to `W/E/R/S/D/F/C`
  - `Tracking` + `Yolo` are now runtime Pi-state toggles (read-only vision state path)
  - placeholders remain for `Face` and attitude sliders
  - color-viewer lab now wires Balance/Horizon toggles and Demo action path on Pi `:8081`
- D-Phase-A runtime vision-state scaffold (Pi color-viewer `:8081`):
  - `GET /vision/state` (read-only state + target schema stub)
  - `POST /vision/state` (runtime toggle actions: `toggle_yolo`, `toggle_tracking`)
  - no actuation path is coupled in this stage
  - detector worker now performs real inference in runtime:
    - reads frames from Pi `8001`
    - runs YOLO with `imgsz` + `interval_n` controls
    - reports `det_fps`, `infer_ms`, `health`, `error`, and live target bbox/class/conf via `/vision/state`
  - current Pi runtime note:
    - OpenCV dependency is installed in service environment.
    - ONNX backend selection order is now:
      - `onnxruntime` (preferred), then
      - OpenCV DNN (`onnx-dnn`) fallback.
    - current Pi image cannot install `onnxruntime` wheel from pip index, so runtime falls back to OpenCV DNN.
    - runtime now includes `tflite-multi` for comma-separated model paths and round-robin per-inference scheduling (`best` + `yolov8n`) with RTSP fallback (`8001 -> 8554/robotdog`) when socket ingest is unavailable.
    - runtime now emits model-aware ball labels for operator clarity:
      - `best*` source -> `MT_ball <conf>`
      - `yolov8n/yolo11n*` source -> `Yolo_sport ball <conf>`
    - dual-model runtime policy now prioritizes custom detector:
      - run `best` first on each infer cycle
      - only if `best` returns no target, run `yolov8n` fallback on the same cycle
      - worker backend tag includes active infer model source (`...:best*` or `...:yolov8n*`) for UI visibility
    - `/color` metrics panel now places `Infer (ms)` near the top so latency stays visible without scrolling.
    - `/color` UI now hides stale targets and raises explicit visual alerts:
      - stream stall -> greyed live pane + centered stall message
      - YOLO health/error issue -> warning overlay with error reason
    - active-heartbeat benchmark now reports real dual-model detector metrics on Pi:
      - target 45 samples: `/tmp/phaseD_benchmark_target_rrmulti_20260212_075719.json` (`det_fps_avg=0.230`, `infer_ms_avg=3027`, `cpu_p95=97.3`, `stream_fps_client_p95=22.5`)
      - light 45 samples: `/tmp/phaseD_benchmark_light_rrmulti_20260212_080006.json` (`det_fps_avg=0.241`, `infer_ms_avg=2789`, `cpu_p95=97.6`, `stream_fps_client_p95=22.5`)
    - new reduced-latency model candidate deployed:
      - `best_256_fp16.tflite` (Pi path: `Server/color_viewer/models/best_256_fp16.tflite`)
      - live sample (`imgsz=256`, `N=8`, `conf=0.05`): `infer_ms_avg=1487.9`, `det_fps_avg=0.237`, `target_ratio=0.917`.
    - current blocker is now performance (CPU saturation on Pi under dual-model inference), not ONNX graph compatibility alone.

## Phase-D Benchmark Harness (1Hz)
- Script: `Server/phaseD_benchmark_1hz.sh`
- Purpose: deterministic Pi KPI sampling for architecture A/B/C gates (thermal/CPU/video/vision) with tiered vision profiles.
- Tiers:
  - `baseline`: `yolo=false`, `imgsz=320`, `N=16`
  - `light`: `yolo=true`, `imgsz=256`, `N=12`
  - `target`: `yolo=true`, `imgsz=320`, `N=8`
  - `stress`: `yolo=true`, `imgsz=416`, `N=5`
- Usage example:
```bash
TIER=baseline DURATION_SEC=120 WARMUP_SEC=20 ./phaseD_benchmark_1hz.sh
```
- Output:
  - CSV: `/tmp/phaseD_benchmark_<tier>_<timestamp>.csv`
  - Summary JSON: `/tmp/phaseD_benchmark_<tier>_<timestamp>.json`
- Current measured snapshot (2026-02-11):
  - baseline 45s with active heartbeat: PASS (`cpu_p95=76.9`, `temp_p95=65.2C`, `stream_fps_client_p95=22.5`)
  - target 30s with active heartbeat: WARN (`vision_errors_present`, `vision_error_count=30`, `stream_fps_client_p95=22.5`)
- Note:
  - benchmark gate is conservative; run with active Safari viewer heartbeat for meaningful stream-fps pass/fail evaluation.
  - parser note: `v1.4` fixed `/vision/metrics` extraction path to read nested `metrics.client_stream_fps`; older runs may show false `no_client_fps_samples`.
  - dependency gate:
    - if runtime reports `error=opencv_or_numpy_not_available`, install missing dependencies in the `robot-color-viewer.service` Python environment before enabling YOLO mode.
  - runtime service entry renamed to `color_viewer_server.py` (was `Demo_IMU_server.py`) for clearer production ownership
- Pi color-viewer demo endpoint (used by `/color` Demo button):
  - `GET /demo/status`
  - `POST /demo` with body `{"action":"start","demo":"helloOne"}` (one-shot `Server/Action.py`)
- Viewer now includes simple 3D IMU baseline visualization (Safari-safe):
  - CSS 3D cube in telemetry section
  - orientation mapped from live IMU roll/pitch/yaw with smoothing
  - zero external 3D library dependency
- IMU 3D tuning controls are now available in viewer:
  - smoothing selector (Fast/Medium/Stable)
  - axis scale tuning (roll/pitch/yaw)
  - stale/offline badge and freeze-on-stale toggle
- Web UI runtime assets are owned by `Server/web/` for Pi-hosted deployment clarity.
- Path policy: if hosting is moved back to Mac client in future, keep corresponding runtime web assets under `Client/web/`.

## Why This Matters For Client Telemetry
- Client-side live telemetry updates are tied to Dog mode polling behavior.
- If client remains in Mac mode (`Dog Video NOT Ready`), UI telemetry can appear stale even though Pi `5001` is up.

## Major Changes (v1.3.0)
- Added **multi-client concurrent control socket handlers** on TCP `5001`.
- Kept request/reply routing **per client connection** for telemetry queries.
- Added **control-owner arbitration** for write/actuation commands:
  - first writer becomes owner
  - non-owner write commands are rejected with `CMD_BUSY#OWNER:<ip:port>`
  - safety overrides (`CMD_MOVE_STOP`, `CMD_RELAX`, `CMD_STOP_PWM`) are always accepted
- Preserved proprietary MJPEG path on `8001` for original Freenove clients.

## Concurrency Model
- Port `5001`:
  - Accept loop + per-client worker thread.
  - Multiple concurrent clients can query telemetry at the same time.
  - Write commands are owner-gated for safety.
- Port `8001`:
  - Legacy proprietary JPEG stream remains unchanged.

## Command Safety Policy (5001)
- Read-only/query commands (examples):
  - `CMD_POWER`, `CMD_SONIC`, `CMD_ATTITUDE` (query form), `CMD_WORKING_TIME`
- Owner-gated write commands (examples):
  - motion commands, `CMD_HEAD`, `CMD_HEIGHT`, `CMD_HORIZON`, `CMD_ATTITUDE` (set form), LED/buzzer, calibration, balance
- Always-allowed safety commands:
  - `CMD_MOVE_STOP`, `CMD_RELAX`, `CMD_STOP_PWM`

## Compatibility Notes
- Original Freenove ecosystem remains supported:
  - Original control protocol text format on `5001` preserved.
  - Original proprietary MJPEG stream on `8001` preserved.
- SFU/WebRTC stack is independent and unaffected by this server change.

## Key Files
- For full runtime hierarchy and ownership, see:
  - `File Structure and Hierarchy (All Operational Files)` in this README.
- Most frequently touched runtime files:
  - `Server/main.py` - entry/startup
  - `Server/Server.py` - TCP server core (multi-client control + video socket)
  - `Server/Control.py` - actuation loop and command execution
  - `Server/telemetry_api_server.py` - telemetry/session/command/diagnostics API
  - `Server/web/webrtc_view.html` - Pi-hosted Safari viewer page
  - `Server/phaseD_benchmark_1hz.sh` - KPI benchmark harness for YOLO impact checks

## Diagnostics
- Show listeners:
```bash
ss -lntp | egrep ':5001|:8001'
```
- Show control clients:
```bash
ss -tnp | grep ':5001'
```
- Tail server log:
```bash
tail -n 200 /tmp/smartdog.log
```
- Show publisher service:
```bash
systemctl status robot-publisher.service --no-pager
```
- Show SFU/viewer services:
```bash
systemctl status robot-sfu.service robot-viewer.service robot-telemetry.service --no-pager
```
- Confirm RTSP path from Mac/SFU host:
```bash
ffprobe -v error -rtsp_transport tcp -show_streams -select_streams v:0 rtsp://192.168.0.32:8554/robotdog
```
- One-command Phase-1 health check:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
chmod +x phase1_health_check.sh
./phase1_health_check.sh
```
- Phase-5 restart drill:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
chmod +x phase5_restart_drill.sh
./phase5_restart_drill.sh
```
- Phase-5 soak probe (example short run):
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
chmod +x phase5_soak_probe.sh
DURATION_SEC=180 INTERVAL_SEC=5 ./phase5_soak_probe.sh
```
- Phase-5 failure injection drill:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
chmod +x phase5_failure_injection.sh
./phase5_failure_injection.sh
```
- Phase-5 verification report:
```bash
cat /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/PHASE5_VERIFICATION_REPORT.md
```
- Pre-WAN hardening checklist:
```bash
cat /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/HARDENING_PREWAN_CHECKLIST.md
```
- Remote Safari access runbook:
```bash
cat /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/REMOTE_SAFARI_ACCESS_RUNBOOK.md
```
- Remote readiness precheck:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
./phaseE_remote_precheck.sh tailscale
./phaseE_remote_precheck.sh wan
```

## Additional Learning: Low Latency Video Streaming (Detailed)

This deployment exposes two video-consumption modes from the same Pi-published H.264 stream path (`robotdog`).

### A. RTSP Path (Mac `mtDogMain.py`)
- Intended for desktop operator app.
- End-to-end:
  - Pi camera encoder -> `robot-publisher.service` (`pi_publish_webrtc.sh`)
  - publish to MediaMTX path `rtsp://192.168.0.32:8554/robotdog`
  - Mac client opens RTSP URL for decode/render
- Transport model:
  - RTSP control over TCP
  - media transport can be TCP/UDP depending on client setting
  - current client default in this repo is TCP for stability

### B. WebRTC Path (Safari viewer page)
- Intended for iPhone/iPad/macOS browser viewing.
- End-to-end:
  - Browser loads `http://192.168.0.32:8081/color` (primary) or `http://192.168.0.32:8080/webrtc_view.html` (legacy/basic)
  - JS posts SDP offer to WHEP API `http://192.168.0.32:8889/robotdog/whep`
  - MediaMTX returns answer; media flows in WebRTC session
- Transport model:
  - WHEP is signaling endpoint
  - media is RTP inside WebRTC session (UDP preferred for low latency)

### Core Point: Single Producer, Multiple Consumers
- `robot-publisher.service` is the single camera publisher.
- MediaMTX relays that stream to:
  - RTSP readers (`mtDogMain.py`)
  - WebRTC readers (`webrtc_view.html` in browsers)
- No transcoding is the baseline design goal.

### Service Responsibilities
- `robot-publisher.service`: produce camera stream to SFU path.
- `robot-sfu.service`: relay/fanout stream (RTSP + WHEP/WebRTC).
- `robot-viewer.service`: serve static web UI from `Server/web/` (`8080` lane).
- `robot-color-viewer.service`: serve enhanced color/control UI (`8081` lane).
- `robot-telemetry.service`: provide read-only JSON telemetry for overlay.

### Setup Validation By Hop
1. Publisher -> SFU path:
```bash
python3 - <<'PY'
import socket
host='192.168.0.32';port=8554;path='/robotdog'
req=(f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n').encode()
s=socket.socket(); s.settimeout(2); s.connect((host,port)); s.sendall(req)
print((s.recv(2048).decode('utf-8','ignore').splitlines() or ['<empty>'])[0]); s.close()
PY
```
2. WHEP signaling readiness:
```bash
curl -i -X OPTIONS http://192.168.0.32:8889/robotdog/whep | head -n 1
```
3. Viewer + telemetry endpoints:
```bash
curl -I http://192.168.0.32:8081/color | head -n 1
curl -I http://192.168.0.32:8080/webrtc_view.html | head -n 1
curl http://192.168.0.32:8090/api/telemetry
```

### Latency and Stability Tradeoff Notes
- Lower bitrate/resolution lowers encode/decode latency and CPU load.
- UDP media generally improves latency but can be more sensitive to loss.
- TCP media is often more stable on noisy LAN but may increase latency.
- Keep SFU relay-only (no transcoding) to preserve latency budget.

### Security Reminder (Current Baseline)
- Current operating model is LAN baseline.
- For broader deployment, add:
  - endpoint authentication
  - TLS/HTTPS
  - TURN/STUN design
  - tighter telemetry/API access control

## Revision History
- 2026-02-12 17:42 v1.16.24  Added cache-control hardening for Pi color-viewer runtime (`Cache-Control: no-store`) plus frontend delayed `/video/config` resync behavior to mitigate stale Safari resolution-profile UI after refresh.
- 2026-02-12 17:33 v1.16.23  Added `/color` runtime note: video-profile apply now triggers immediate client-side WebRTC renegotiation so new publisher resolution is reflected without manual refresh in normal conditions.
- 2026-02-12 17:26 v1.16.22  Added Pi `/video/config` persistence/apply documentation: selected profile is stored in `video_runtime_config.json`, publisher WIDTH/HEIGHT override is emitted to `video_publisher_profile.env`, and `robot-publisher.service` restart is attempted for immediate WebRTC resolution switching.
- 2026-02-12 17:11 v1.16.21  Synced README version timestamp via `tools/version_time_sync.sh` (no runtime behavior change).
- 2026-02-12 16:09 v1.16.21  Enhanced Pi low-voltage telemetry behavior: added debounced low-battery state fields (`low_battery`, `low_battery_since_ts`, `low_battery_duration_s`, policy metadata) so `/color` warnings/beep and HUD battery-state line are stable under threshold transitions.
- 2026-02-12 15:49 v1.16.20  Refined Pi `/telemetry/power_history` START/UPTIME semantics for scope accuracy: START is resolved from system power-up/boot time (`/proc/stat btime`, fallback `/proc/uptime`) and UPTIME is computed as `now - START`.
- 2026-02-12 15:45 v1.16.19  Enhanced Pi `/diag` payload for operator-facing networking clarity: added `control_display_host` (LAN-reachable host fallback when backend is loopback) and `ports_summary` string so `/color` HUD can show active endpoint and all key ports/functions.
- 2026-02-12 15:42 v1.16.18  Updated Pi `/telemetry/power_history` timeline defaults for mission-relative plotting: 60-minute rolling window and stable `history_start_ts`/`uptime_s` support to drive `/color` relative x-axis (`Time Since Start`) with dynamic minute ticks.
- 2026-02-12 15:02 v1.16.17  Extended Pi `/telemetry/power_history` payload with `uptime_s`/`history_start_ts` so `/color` voltage scope can display live elapsed runtime since power-on/service start.
- 2026-02-12 14:51 v1.16.16  Added Pi color-viewer `GET/POST /video/config` runtime endpoint for UI stream-profile dial (`1280x720`, `960x540`, `640x360`) and aligned `/color` HUD cleanup (redundant status rows removed, compact live-clients header, battery-scope label layout refinements).
- 2026-02-12 14:14 v1.16.15  Updated Pi `/color` runtime behavior: stream detail now consolidated in HUD with LIVE/STALLED pill, IMU pane supports explicit telemetry-lost mode (`IMU Attitude -- Telemetry Lost --` + grey placeholders), low-battery warning now triggers periodic triple-beep guard, and battery history window expanded to 40 minutes for oscilloscope-style left->right trend rendering.
- 2026-02-12 12:50 v1.16.14  Added Pi-side power trend telemetry (`GET /telemetry/power_history`) with boot-scoped history reset, rail/warn metadata, and low-battery status; aligned `/color` overlays to show compact live-client summary plus enhanced client identity line (device+IP+FPS+heartbeat age).
- 2026-02-12 11:38 v1.16.13  Added `/color` Live Clients UI integration note: Pi viewer now surfaces healthy active clients via `/viewer/summary` heartbeat aggregation (device/IP/FPS/age) for operator monitoring.
- 2026-02-12 11:32 v1.16.12  Added viewer-identity observability endpoints on Pi color-viewer lane: `POST /viewer/heartbeat` and `GET /viewer/summary` for active-viewer/operator summaries (IP/session + browser/device hints, viewport/screen/GPU/activity metadata).
- 2026-02-12 11:23 v1.16.11  Added `/color` live-header client-device badge (best-effort browser class) to show operator endpoint type beside Live View title without affecting Pi-first runtime path.
- 2026-02-12 11:16 v1.16.10  Updated `/color` warning policy: transient RTSP/worker read errors are treated as minor UI warnings (bottom-center banner) and no longer force grey-screen dim unless stream stall/critical condition persists.
- 2026-02-12 10:30 v1.16.9  Added tracking implementation step in Pi `/color` lane: detector miss now uses short hold/predict lock path (`source=tracking_hold`) when `tracking_enabled=true`, with no motor-control coupling.
- 2026-02-12 10:22 v1.16.8  Stabilized `/color` runtime by debouncing transient stream-stall overlays and making YOLO stale timeout adaptive to measured infer latency (prevents static `MT_ball` label on/off flicker between normal infer cycles).
- 2026-02-12 10:15 v1.16.7  Updated `/color` outage UX policy: removed modal Pi-offline popup dialog and kept non-blocking on-page stall/health overlays that auto-clear on recovery.
- 2026-02-12 10:08 v1.16.6  Documented Safari `/color` WebRTC auto-recovery fix after Pi power-cycle (disconnect/failed peer states now trigger renegotiation) and aligned detector scheduling note to `best`-first fallback.
- 2026-02-12 09:55 v1.16.5  Synced README timestamp via guard tool after `best`-priority fallback and stream/vision warning overlay documentation update.
- 2026-02-12 09:54 v1.16.5  Documented `best`-first fallback policy, infer-model source tagging in metrics, and new stream/vision fault overlays with stale-target suppression behavior.
- 2026-02-12 09:16 v1.16.4  Synced README timestamp via guard tool after model-aware ball-label behavior and `best_256_fp16.tflite` latency-optimization documentation update.
- 2026-02-12 09:14 v1.16.4  Added model-aware ball-label behavior (`MT_ball`/`Yolo_sport ball`), documented `Infer (ms)` metrics-pane positioning change, and recorded deployed `best_256_fp16.tflite` live latency-reduction result.
- 2026-02-12 08:56 v1.16.3  Synced README timestamp via guard tool after corrected Safari primary URL/port to `8081/color` and service-lane clarification updates.
- 2026-02-12 08:55 v1.16.3  Deep-validated Pi runtime viewer ports and updated Safari primary link to `http://192.168.0.32:8081/color` (kept `8080/webrtc_view.html` as legacy/basic lane).
- 2026-02-12 08:52 v1.16.2  Replaced Quick Start placeholder URLs with explicit clickable `192.168.0.32` examples for Safari users.
- 2026-02-12 08:51 v1.16.1  Synced README timestamp via guard tool after Safari-first Quick Start update for Pi-hosted streaming/control users.
- 2026-02-12 08:50 v1.16.1  Updated Quick Start with Safari-first Pi usage flow (video + control) for typical operator path.
- 2026-02-12 08:44 v1.16.0  Synced README timestamp via guard tool after standalone WebRTC/SFU+YOLO overview and full operational hierarchy documentation update.
- 2026-02-12 08:43 v1.16.0  Revised standalone Pi WebRTC/SFU+YOLO overview and added full operational file hierarchy (runtime ownership + source-template mapping for deployed services/components).
- 2026-02-12 08:04 v1.15.8  Updated Pi D-phase runtime status after deployed `tflite-multi` dual-model backend and RTSP fallback verification; added latest active-heartbeat target/light benchmark artifacts and documented CPU saturation as current blocker.
- 2026-02-11 22:04 v1.15.7  Updated D-phase runtime notes with TFLite backend readiness and fallback-chain behavior, documented benchmark parser fix (`metrics.client_stream_fps`) and refreshed active-heartbeat baseline/target measurements.
- 2026-02-11 19:39 v1.15.6  Synced README timestamp via guard tool after Phase-D benchmark-harness documentation update.
- 2026-02-11 19:38 v1.15.6  Added Phase-D 1Hz benchmark harness documentation (tier profiles, outputs, usage) and recorded latest measured baseline/target outcomes with current blocker context.
- 2026-02-11 19:22 v1.15.5  Synced README timestamp via guard tool after detector-backend documentation update.
- 2026-02-11 19:21 v1.15.5  Documented Pi detector backend order (`onnxruntime` preferred with `onnx-dnn` fallback) and current runtime constraint on this Pi image (`onnxruntime` unavailable + OpenCV 4.5.1 ONNX parser incompatibility).
- 2026-02-11 18:21 v1.15.4  Synced README timestamp via guard tool after Pi detector-worker rollout status update.
- 2026-02-11 18:19 v1.15.4  Updated Pi-side detector-worker rollout status after live validation: OpenCV installed and ONNX deployed, with runtime blocker clarified as OpenCV 4.5.1 ONNX importer incompatibility (temporary YOLO-off rollback).
- 2026-02-11 17:56 v1.15.3  Synced README timestamp via guard tool after detector-worker dependency-gate documentation update.
- 2026-02-11 17:55 v1.15.3  Added detector-worker runtime dependency gate note for Pi service environment (`opencv_or_numpy_not_available`).
- 2026-02-11 17:53 v1.15.2  Synced README timestamp via guard tool after revision-history timestamp alignment.
- 2026-02-11 17:52 v1.15.2  Synced README timestamp via guard tool after detector-worker integration documentation update.
- 2026-02-11 17:49 v1.15.2  Documented Pi color-viewer full detector-worker integration and `/vision/state` live inference/health payload fields.
- 2026-02-11 17:38 v1.15.1  Synced README timestamp via guard tool after related client README hierarchy and AI dataset reference update.
- 2026-02-11 17:33 v1.15.1  Synced README timestamp via guard tool after related client README YOLO method documentation update.
- 2026-02-11 17:04 v1.15.1  Synced README timestamp via guard tool after final runtime rename refactor pass.
- 2026-02-11 17:02 v1.15.1  Synced README timestamp via guard tool after runtime rename documentation update.
- 2026-02-11 16:57 v1.15.1  Documented runtime rename to `color_viewer_server.py` and aligned Pi color-viewer service naming notes.
- 2026-02-11 15:07 v1.15.0  Synced README timestamp via guard tool after revision-history timestamp alignment.
- 2026-02-11 15:05 v1.15.0  Synced README timestamp via guard tool after D-Phase-A vision-state documentation update.
- 2026-02-11 14:57 v1.15.0  Documented D-Phase-A runtime vision-state scaffold (`/vision/state`) and updated color-viewer control status (`Yolo/Tracking` runtime toggles, read-only coupling).
- 2026-02-11 12:23 v1.14.9  Synced README timestamp via guard tool after final pass of color-viewer action documentation updates.
- 2026-02-11 12:22 v1.14.9  Synced README timestamp via guard tool after documenting color-viewer Demo/Horizon/Balance action paths.
- 2026-02-11 12:20 v1.14.9  Documented Pi color-viewer action expansion: `Balance/Horizon` toggles and `/demo` endpoint for one-shot `Action.py` demo trigger on `:8081`.
- 2026-02-11 09:45 v1.14.8  Synced README timestamp via guard tool after related client-side axis-definition documentation update.
- 2026-02-10 19:15 v1.14.8  Synced README timestamp via guard tool after final metadata alignment.
- 2026-02-10 19:14 v1.14.8  Synced README timestamp via guard tool after revision-history consistency update.
- 2026-02-10 19:13 v1.14.8  Synced README timestamp via guard tool after related client/proposal documentation updates.
- 2026-02-10 07:40 v1.14.8  Added remote Safari access runbook and precheck script usage (`phaseE_remote_precheck.sh`).
- 2026-02-10 07:33 v1.14.7  Added documentation for wired `Balance` toggle actions (`balance_on`/`balance_off`) in mobile command path.
- 2026-02-10 07:30 v1.14.6  Documented newly wired low-risk mobile actions (`beep`, `led`, `cal`) under existing ARM/session gate.
- 2026-02-10 07:27 v1.14.5  Documented IMU 3D tuning controls and stale-freeze behavior in Safari viewer.
- 2026-02-10 07:11 v1.14.4  Documented simple Safari-safe 3D IMU model in Pi viewer (CSS cube) driven by telemetry.
- 2026-02-09 21:31 v1.14.3  Documented mobile UI-parity placeholder scaffold and mtDogMain IMU-web launch integration context.
- 2026-02-09 21:24 v1.14.2  Synced README timestamp via guard tool after Phase-5 failure-injection and soak-resume documentation updates.
- 2026-02-09 21:23 v1.14.1  Added executed failure-injection outcome note (RTSP recover 4s, WHEP recover 1s) in Phase-5 diagnostics context.
- 2026-02-09 21:20 v1.14.0  Added Phase-5 failure injection drill runbook command and tooling reference.
- 2026-02-09 20:57 v1.13.1  Synced README timestamp via guard tool after Phase-5 hardening documentation updates.
- 2026-02-09 20:56 v1.13.0  Added optional API auth-gate note (`--api-token`) and pre-WAN hardening checklist reference.
- 2026-02-09 20:52 v1.12.1  Synced README timestamp via guard tool after Phase-5 runbook additions.
- 2026-02-09 20:50 v1.12.0  Added Phase-5 restart drill, soak probe run commands, and verification report reference in diagnostics runbook.
- 2026-02-09 19:02 v1.11.1  Synced README timestamp via guard tool after Phase-5 observability documentation update.
- 2026-02-09 18:58 v1.11.0  Added Phase-5 observability/cache-control updates: diagnostics endpoint, static viewer server policy, and expanded service model notes.
- 2026-02-09 18:52 v1.10.2  Synced README timestamp via guard tool after final Phase-4 validation updates.
- 2026-02-09 18:49 v1.10.1  Synced README timestamp via guard tool after Phase-4 documentation update.
- 2026-02-09 18:48 v1.10.0  Documented Phase-4 control-lock metadata and request/release handoff workflow for multi-client session UX.
- 2026-02-09 18:26 v1.9.1  Synced README timestamp via guard tool after Phase-3 command MVP documentation update.
- 2026-02-09 18:25 v1.9.0  Documented Phase-3 command MVP endpoints (`/api/session`, `/api/command`) and safety behavior.
- 2026-02-09 18:16 v1.8.1  Synced README timestamp via guard tool after build-badge documentation update.
- 2026-02-09 18:14 v1.8.0  Documented visible on-page build badge for viewer runtime version/time confirmation.
- 2026-02-09 17:54 v1.7.1  Synced README timestamp via guard tool and confirmed educational streaming section for local + Pi sync.
- 2026-02-09 17:52 v1.7.0  Added detailed educational section on end-to-end low-latency streaming architecture and protocol flow.
- 2026-02-09 17:06 v1.6.1  Synced README timestamp via guard tool after web-asset location refactor documentation.
- 2026-02-09 17:01 v1.6.0  Moved Pi-hosted web assets to `Server/web` and documented viewer ownership/source path.
- 2026-02-09 16:12 v1.5.1  Synced README timestamp via guard tool after Phase-2 updates.
- 2026-02-09 16:09 v1.5.0  Added Phase-2 telemetry API service (`robot-telemetry.service`) and overlay endpoint usage.
- 2026-02-09 15:26 v1.4.2  Synced README timestamp via guard tool after Phase-1 completion checks.
- 2026-02-09 15:25 v1.4.1  Synced README timestamp after Phase-1 documentation updates.
- 2026-02-09 15:15 v1.4.0  Set Phase-1 default to Pi-hosted SFU + viewer services and added one-command health check usage.
- 2026-02-09 11:59 v1.3.4  Added explicit macOS/iOS video-viewing usage and URL role clarification (player page vs WHEP API).
- 2026-02-08 15:00 v1.3.3  Added timestamp-guard workflow note to align server docs with automated local-time sync/check process.
- 2026-02-08 14:52 v1.3.2  Synced README version timestamp to current local time (CST) for consistency with operator console clock.
- 2026-02-08 12:56 v1.3.1  Added Pi boot service model (`smartdog.service` + `robot-publisher.service`) and clarified control-green/video-red split behavior.
- 2026-02-08 10:05 v1.3.0  Added multi-client 5001 concurrency with owner arbitration and preserved 8001 MJPEG compatibility.
- 2026-02-06 22:07 v1.2.1  Added timestamps to revision history.
- 2026-02-06 v1.2.0  Added battery/power notes and UBEC/BEC search results.
