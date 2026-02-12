# Freenove Robot Dog - Client

## Version
v1.12.48 (2026-02-12 18:33 local time)

## Quick Start (new users)
1. Enter client environment first:
```bash
smartdog
```
2. Launch main console:
```bash
python3 mtDogMain.py
```

## Quick Start (SFU low-latency video)
1. Ensure Pi services are up (SFU + viewer + publisher + telemetry API):
```bash
ssh pi@192.168.0.32 'systemctl is-active robot-sfu.service robot-viewer.service robot-publisher.service robot-telemetry.service'
```
2. Launch client:
```bash
smartdog python3 mtDogMain.py
```

## Video Viewing (macOS + iOS Safari)
Use this order to view Pi camera video reliably:
1. Ensure Pi services are running (`smartdog.service`, `robot-sfu.service`, `robot-viewer.service`, `robot-publisher.service`, `robot-telemetry.service`).
2. Open player page in browser:
- macOS Safari/Chrome: `http://192.168.0.32:8080/webrtc_view.html`
- iOS/iPadOS Safari: `http://192.168.0.32:8080/webrtc_view.html`

Important:
- `http://192.168.0.32:8889/robotdog/whep` is a WebRTC signaling endpoint (API), not a page for direct viewing.
- `mtDogMain.py` uses SFU RTSP by default (`rtsp://192.168.0.32:8554/robotdog`), while Safari pages use WebRTC/WHEP via SFU.
- Telemetry overlay is read-only and polls `http://192.168.0.32:8090/api/telemetry` (stale/backend-down indications shown in UI).
- Viewer page now shows a visible build badge (`Build: vX | YYYY-MM-DD HH:MM`) to confirm deployed runtime version.
- Phase-3 command MVP is enabled in the viewer:
  - Session arm/disarm API: `http://192.168.0.32:8090/api/session`
  - Command API: `http://192.168.0.32:8090/api/command`
  - Motion/relax commands require ARM first; `EMERGENCY STOP` and `STOP PWM` are always allowed.
  - Low-risk actions now wired: `beep`, `led`, `cal`, `balance_on`, `balance_off` (also require ARM).
- Phase-4 multi-client session UX is enabled:
  - lock-state indicator in viewer (`owned_by_mobile` / `owned_by_other` / `available_or_unknown`)
  - handoff actions: `Request Control`, `Release Control`
  - explicit busy-owner message when command is blocked by owner arbitration (`CMD_BUSY#OWNER:<owner>`).
- Phase-5 quick diagnostics is enabled:
  - `http://192.168.0.32:8090/api/diagnostics` for service/port/session summary
  - viewer includes diagnostics mini-panel driven by diagnostics endpoint
- Low-priority UI parity scaffold is now visible in the Pi viewer:
  - motion-key layout uses `W/E/R/S/D/F/C` arrangement
  - `Tracking` + `Yolo` are now runtime toggles backed by Pi `/vision/state` (read-only state path, no actuation coupling)
  - `Face` and slider bank remain placeholders
  - wired controls include Beep/LED/Cal plus Balance/Horizon in color-viewer lab page
- D-Phase-A runtime vision state scaffold is available in Pi color-viewer:
  - `GET /vision/state` for read-only mode/target schema (`disabled/detect_only/tracking/stale`)
  - `POST /vision/state` for runtime toggle actions (`toggle_yolo`, `toggle_tracking`) during development
  - runtime server entry was renamed to `color_viewer_server.py` (replacing `Demo_IMU_server.py`) to reflect Pi production role
  - full detector worker integration now active in `color_viewer_server.py`:
    - frame ingest from Pi video socket `8001`
    - YOLO infer loop with runtime knobs (`imgsz`, `interval_n`, `conf_threshold`, `iou_threshold`)
    - live target + worker health fields published to `/vision/state`
    - browser `/color` renders target bbox overlay + class/conf label
  - current Pi runtime status:
    - OpenCV dependency is installed on Pi service runtime.
    - ONNX fallback path is wired and model export/deploy is done (`best.onnx`).
    - known blocker on this Pi image: `OpenCV 4.5.1` ONNX importer rejects current YOLO graph (`onnx_load_failed ... handleNode Add ... blob_0.size == blob_1.size`).
    - runtime now supports `tflite-multi` for comma-separated models and uses round-robin inference (`best` + `yolov8n`) with RTSP fallback when `8001` socket stream is unavailable.
    - overlay label is now model-aware for ball visibility:
      - `best*` source -> `MT_ball <conf>`
      - `yolov8n/yolo11n*` source -> `Yolo_sport ball <conf>`
    - dual-model behavior is now `best`-first with fallback:
      - infer `best` first
      - if no object is found on that infer cycle, run `yolov8n` fallback
      - active infer source is exposed in metrics as `Infer (ms) "best|yolov8n" model`
    - `Infer (ms)` is moved near the top of the `Vision/Stream Metrics` panel for no-scroll visibility during live tuning.
    - stale target overlays are now hidden in UI (`state=stale`) to avoid long linger of old boxes when object moves/occludes.
    - stream/vision fault guardrail added:
      - if video stream stalls, live pane is greyed and overlay alert is shown
      - if YOLO vision health/error is bad, overlay warning is shown with error reason
    - active-heartbeat benchmarks now show real detector metrics on Pi:
      - target: `/tmp/phaseD_benchmark_target_rrmulti_20260212_075719.json` (`det_fps_avg=0.230`, `infer_ms_avg=3027`, `stream_fps_client_p95=22.5`)
      - light: `/tmp/phaseD_benchmark_light_rrmulti_20260212_080006.json` (`det_fps_avg=0.241`, `infer_ms_avg=2789`, `stream_fps_client_p95=22.5`)
    - new reduced-latency candidate is available:
      - model: `best_256_fp16.tflite`
      - sample live run (`imgsz=256`, `N=8`, `conf=0.05`): `infer_ms_avg=1487.9`, `det_fps_avg=0.237`, `target_ratio=0.917`, class histogram dominated by `MT_ball`.
    - current blocker shifted from compatibility to performance: CPU remains saturated (`cpu_p95>97`) under dual-model Pi inference.
    - temporary safe setting remains: keep `yolo_enabled=false` outside benchmark/debug runs.
- Pi color-viewer lab (`http://192.168.0.32:8081/color`) now supports one-shot Demo trigger:
  - `POST /demo {"action":"start","demo":"helloOne"}` via color viewer `Demo` button
  - status endpoint: `GET /demo/status`
- `/color` live title now always includes resolution + FPS (for example `Live View 960x540, 30.0 fps`) using runtime fallback dimensions when browser metadata is delayed.
- `/color` `Video Resolution` selector (`1280x720/960x540/640x360`) currently updates Pi H264 fallback profile (`/video/config`); when active stream path is WebRTC, visible resolution is controlled by publisher/SFU stream settings.
- `/color` video resolution selection now persists across refresh/reboot:
  - Pi stores selected profile in `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/color_viewer/video_runtime_config.json`
  - Pi writes publisher override env to `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/color_viewer/video_publisher_profile.env`
  - on apply, Pi attempts to restart `robot-publisher.service`; if restart is blocked, setting is still saved and takes effect on next publisher restart/power cycle.
- `/color` now auto-triggers live WebRTC renegotiation right after video-profile apply, so resolution changes become visible without manual page refresh in normal cases.
- `/color` refresh reliability was hardened for Safari by disabling cache on color-viewer responses and adding post-load profile resync timers; profile dial should now reflect persisted backend value consistently after refresh.
- Pi viewer includes simple 3D IMU baseline model:
  - Safari-safe CSS cube rendering (no external 3D library)
  - orientation driven by live IMU roll/pitch/yaw telemetry
- Pi viewer now exposes 3D IMU tuning controls:
  - smoothing profile selector
  - roll/pitch/yaw axis scale inputs
  - stale/offline badge with freeze-on-stale toggle
- IMU color-model lab viewer (`Client/tools/imu_viewer/app_color.js`) now applies yaw unwrapping before smoothing to avoid visible flips when yaw crosses `+-180`.
- IMU color-model lab viewer now renders as a live-video bottom-left overlay with compact IMU text (`Pitch/Roll/Yaw`) below the model.
- IMU color-model lab viewer now includes visible build badge text and persistent orientation tuning controls:
  - invert toggles (`roll`, `pitch`, `yaw`)
  - offset inputs (`roll`, `pitch`, `yaw`, degrees)
  - reset tuning action (browser-local persistence via `localStorage`)
- IMU axis definition used in viewer diagnostics/docs:
  - `Yaw -> rotate around Z`
  - `Pitch -> rotate around X`
  - `Roll -> rotate around Y`
- If IMU telemetry pauses for over 1 second, overlay IMU text turns red and the 3D model is greyscaled until data resumes.
- For Pi-hosted runtime, viewer HTML is sourced from `Server/web/`; `Client/` keeps client-app logic.
- Path policy: if runtime hosting moves to Mac client, place/serve runtime web assets under `Client/web/`.
- For outside-home iPhone Safari planning and checks, refer to:
  - `Server/REMOTE_SAFARI_ACCESS_RUNBOOK.md`
  - `Server/phaseE_remote_precheck.sh`

## Major Changes (v1.4.0)
- Pi server `5001` now supports multiple concurrent control socket clients.
- Write commands are owner-arbitrated on server side for safety.
- Read/query telemetry can be served concurrently.
- Legacy proprietary MJPEG (`8001`) compatibility preserved on Pi side.

## Multi-Client Usage (Mac + iPhone example)
- MacBook:
  - Use `mtDogMain.py` as main operator console (control + telemetry + video).
- iPhone web viewer:
  - Use web live viewer for additional monitoring.
  - If issuing write commands from iPhone while Mac owns control, server returns `CMD_BUSY#OWNER:<ip:port>`.
  - Safety stop commands remain accepted.

## Architecture Overview
- Control + telemetry + IMU: Pi TCP `5001`
- Video default: SFU RTSP (`rtsp://<sfu>:8554/<stream>`)
- Legacy video fallback path: Pi proprietary JPEG stream on `8001`

## YOLO Vision Method (Current `mtDogMain.py`)
Dual-model YOLO is enabled by default in the current client runtime.

- Model 1: custom `best.pt` (`MT` detector)
  - path: `Client/runs/detect/train5/weights/best.pt`
  - detector init: `YOLOBallDetector(..., ball_class_id=0)`
  - runtime role: custom `mt_ball` detection
- Model 2: baseline `yolov8n.pt` (`COCO` detector)
  - path: `Client/yolov8n.pt`
  - detector init: `YOLOBallDetector(..., ball_class_id=32)`
  - runtime role: general COCO detections, with target classes:
    - `sports ball` (`cls=32`)
    - `dog` (`cls=16`)
    - `person` (`cls=0`)

How the two models are used together:
- Both models run each YOLO cycle in `vision/yolo_runtime.py` (`_run_dual_inference`).
- Runtime combines detections and selects one active target using priority:
  - ball (`mt_ball` or `sports ball`) first
  - then `dog`
  - then `person`
- Compare mode shows side-by-side outputs:
  - left: `best.pt`
  - right: `yolov8n.pt` sports-ball results
- Runtime status text includes per-model latency, counts, selected target, and refinement HSV summary.

Relevant runtime knobs (`config/mtDogConfig.py` + `mtDogMain.py` defaults):
- `YOLO_COCO_CONF_DEFAULT`
- `YOLO_MT_BALL_CONF_DEFAULT`
- `YOLO_DUAL_CAP_FPS_DEFAULT`

For full dataset, training, artifact, and quality-gate details, see:
- `Client/AI_YOLO_Datasets.md`

## YOLO Vision Method (Pi Appliance Runtime, `/color`)
Pi-side detector worker uses ONNX deployment artifacts for inference runtime:

- Trained/custom model path (source): `Client/runs/detect/train5/weights/best.pt`
- General/base model path (source): `Client/yolov8n.pt`
- Pi deployment target artifacts:
  - `best.onnx`
  - `yolov8n.onnx`

Conversion flow (same for both models):
1. Train or prepare `.pt` model on development environment.
2. Export to `.onnx` (`imgsz=320`, fixed shape recommended for Pi).
3. Deploy `.onnx` to Pi viewer runtime model folder.
4. Set `yolo_model_path` in `/vision/config` to the deployed ONNX file.

Runtime backend selection order in `color_viewer_server.py`:
1. `onnxruntime` backend (preferred when available)
2. OpenCV DNN (`onnx-dnn`) fallback
3. Ultralytics `.pt` path fallback when using `.pt` model and Torch runtime

Current Pi image behavior (2026-02-11):
- `onnxruntime` package is not available for this Pi Python environment (`pip: no matching distribution`).
- worker automatically falls back to OpenCV DNN for ONNX.
- current OpenCV `4.5.1` ONNX parser rejects the exported YOLO graph (`Add` node parse error), so detector cannot start yet.
- appliance runtime is kept safe by setting `yolo_enabled=false` until compatible backend/runtime is available.

## Boot Behavior And Recovery (Important)
- Current default deployment:
  - Pi auto-starts `smartdog.service` (control server, ports `5001/8001`).
  - Pi auto-starts `robot-sfu.service` (MediaMTX SFU host, ports `8554/8889/9997`).
  - Pi auto-starts `robot-viewer.service` (viewer page on `8080`).
  - Pi auto-starts `robot-publisher.service` (H.264 publisher to SFU path `robotdog`).
  - Pi auto-starts `robot-telemetry.service` (read-only telemetry API on `8090`).
  - Mac runs `mtDogMain.py` as control/operator client.
- You do **not** need to launch `mtDogMain.py` to start the Pi publisher; publisher is a Pi-side service now.
- Why `Ctrl:5001` can be green while video is red:
  - `5001` and SFU RTSP publish are separate pipelines.
  - Control reachability does not guarantee SFU path is currently online.
- Why telemetry may look stale:
  - In Client Mac mode (`Dog Video NOT Ready`), Dog telemetry polling is intentionally paused.
  - Switch to Dog mode after stream is ready to resume live telemetry in UI.
- Fast checks:
```bash
# On Mac: RTSP stream path health (must be 200 OK)
python3 - <<'PY'
import socket
host='192.168.0.32';port=8554;path='/robotdog'
req=(f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n').encode()
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(2);s.connect((host,port));s.sendall(req)
print((s.recv(2048).decode('utf-8','ignore').splitlines() or ['<empty>'])[0]); s.close()
PY
```
```bash
# On Pi: service status (both should be active)
systemctl is-active smartdog.service
systemctl is-active robot-sfu.service
systemctl is-active robot-viewer.service
systemctl is-active robot-publisher.service
systemctl is-active robot-telemetry.service
```

## Configuration (`config/mtDogConfig.py`)
- `VIDEO_BACKEND = "sfu_rtsp"` or `"legacy_socket"`
- `SFU_HOST`, `SFU_RTSP_PORT`, `SFU_STREAM_PATH`, `SFU_RTSP_URL`, `SFU_RTSP_TRANSPORT`
- `VIDEO_TARGET_WIDTH`, `VIDEO_TARGET_HEIGHT`, `VIDEO_TARGET_FPS`, `VIDEO_TARGET_BITRATE`
- `IMU_VIEWER_URL` (mtDogMain quick-launch URL, default Pi viewer page)
- `IMU_VIEWER_DIAG_URL` (mtDogMain IMU web reachability probe endpoint, default telemetry API)

## Detailed File Structure And Hierarchy

The hierarchy below lists project files used by the current client runtime and development workflow, with short descriptions.

### Root Client runtime files
- `Client/mtDogMain.py` - main PyQt application entry and runtime orchestration.
- `Client/mtDogLogicMixin.py` - shared robot control logic/state mixin used by main UI.
- `Client/Main.py` - legacy/alternate entry script retained for compatibility/reference.
- `Client/MT_BallTracking.py` - ball tracking prototype/legacy flow.
- `Client/Thread.py` - helper threading utilities for older code paths.
- `Client/setup.py` - package setup/install metadata.

### Models (`*.pt`)
- `Client/yolov8n.pt` - baseline COCO YOLO model.
- `Client/runs/detect/train5/weights/best.pt` - custom trained model used as MT detector.
- `Client/runs/detect/train5/weights/last.pt` - latest checkpoint from training run.

### Core configuration
- `Client/config/mtDogConfig.py` - runtime config constants (video backend, SFU, UI toggles).
- `Client/config/__init__.py` - config package init.

### Controllers (`Client/controllers/`)
- `Client/controllers/ball_tracking_controller.py` - tracking-state update and lock behavior.
- `Client/controllers/client_camera_controller.py` - local camera capture path handling.
- `Client/controllers/dog_command_controller.py` - command dispatch to robot control channel.
- `Client/controllers/frame_update_controller.py` - frame loop/update pacing for UI/render.
- `Client/controllers/pid_controller.py` - PID helper for movement/servo tuning.
- `Client/controllers/server_reconnect_controller.py` - reconnect logic for control/video sessions.
- `Client/controllers/telemetry_controller.py` - telemetry polling and state update.
- `Client/controllers/video_source_controller.py` - video source switching/backend control.

### Vision runtime (`Client/vision/`)
- `Client/vision/yolo_runtime.py` - dual-model YOLO runtime + compare/training capture flow.
- `Client/vision/ai_vision_controller.py` - GPT vision snapshot request/parse/render flow.
- `Client/vision/cv_hist_debug.py` - CV histogram debug tooling.
- `Client/vision/mask_picker.py` - mask/hue picker helpers.
- `Client/vision/legacy/mtBallDetectYOLO.py` - YOLO detector wrapper used by runtime.
- `Client/vision/legacy/mtBallDetectCV.py` - legacy CV-only ball detector.
- `Client/vision/legacy/mtBallDetectAI.py` - legacy AI detector bridge.
- `Client/vision/legacy/cv_ball_detection.py` - legacy CV detection helpers.
- `Client/vision/utils/motion_grid_builder.py` - motion-grid utility.
- `Client/vision/utils/overlay_renderer.py` - frame overlay drawing primitives.

### UI modules (`Client/ui/`)
- `Client/ui/ui_client.py` - client UI assembly helpers.
- `Client/ui/ui_event_handlers.py` - event wiring and button/toggle handlers.
- `Client/ui/control_panel_sections.py` - control panel block construction.
- `Client/ui/status_ui_controller.py` - status labels/indicators.
- `Client/ui/status_overlay_controller.py` - runtime status overlay rendering.
- `Client/ui/yolo_debug_windows.py` - YOLO debug + compare windows.
- `Client/ui/cv_debug_windows.py` - CV debug windows.
- `Client/ui/ai_hist_windows.py` - AI histogram windows.
- `Client/ui/attitude_3d_widget.py` - 3D IMU widget component.
- `Client/ui/common_widgets.py` - shared UI widgets.
- `Client/ui/ui_face.py` - face panel UI.
- `Client/ui/ui_led.py` - LED panel UI.

### Dataset and documentation
- `Client/AI_YOLO_Datasets.md` - authoritative YOLO dataset/training/quality guide.
- `Client/AI_datasets/yolo_ball_v01/README.md` - dataset-specific notes for v01.
- `Client/COPILOT_VISION_SPEC.md` - runtime vision behavior spec.
- `Client/mtDogVisionAI_YOLO_OpenCV_Hybrid.md` - hybrid vision design notes.
- `Client/mtDogVisionAI_YOLO_OpenCV_Hybrid v1,2.md` - expanded hybrid notes.

### Tools (`Client/tools/`)
- `Client/tools/yolo/yolo_labeling.py` - manual labeling helper/controller.
- `Client/tools/imu_viewer/color_viewer_server.py` - IMU/color viewer runtime server.
- `Client/tools/imu_viewer/index_color.html` - color viewer page.
- `Client/tools/imu_viewer/app_color.js` - color viewer logic + IMU/vision UI glue.
- `Client/tools/imu_viewer/live_video.js` - video embedding for IMU viewer.
- `Client/tools/realtime_webrtc/robot/pi_publish_webrtc.sh` - Pi stream publisher script.
- `Client/tools/realtime_webrtc/control/dc_authority_gateway.py` - authority gateway helper.

### Tests
- `Client/tests/test_mtdog_logic_mixin.py` - logic mixin regression tests.
- `Client/tests/test_server_reconnect_controller.py` - reconnect controller tests.
- `Client/tests/test_video_source_controller.py` - video source controller tests.

## Diagnostics
- 5001/8001 reachability:
```bash
smartdog python3 - <<'PY'
import socket
for h,p in [('192.168.0.32',5001),('192.168.0.32',8001)]:
 s=socket.socket(); s.settimeout(2)
 try:
  s.connect((h,p)); print('OK',h,p)
 except Exception as e:
  print('FAIL',h,p,e)
 s.close()
PY
```
- Client log:
```bash
tail -n 200 /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/mtDogMain.log
```

## Automated Regression Tests
Run regression checks (headless, no GUI) in the client environment:
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client
../smartdog python -m unittest discover -s tests -p 'test_*.py' -v
```

Current test scope:
- Legacy motion key mapping (`W/E/R/S/D/F/C`)
- `D` relax behavior (`CMD_RELAX` + delayed `CMD_STOP_PWM`)
- SFU no-first-frame health behavior (probe keeps video status healthy)
- Mac->Dog reconnect success flow

## Code Scale Analysis (2026-02-08)

Overall project LOC (code-like extensions in Code/): **253,382**

By extension:
- .py: 93,039
- .js: 55,742
- .ts: 12,302
- .html: 615
- .md: 22,616
- .json: 24,657
- .yml: 42,681
- .yaml: 248
- .sh: 1,482

mtDogMain-related LOC subtotal: **9,890**

Per-file LOC:
- [mtDogMain.py](mtDogMain.py): 1,875
- [mtDogLogicMixin.py](mtDogLogicMixin.py): 1,040
- [config/mtDogConfig.py](config/mtDogConfig.py): 61
- [controllers/ball_tracking_controller.py](controllers/ball_tracking_controller.py): 825
- [controllers/client_camera_controller.py](controllers/client_camera_controller.py): 291
- [controllers/dog_command_controller.py](controllers/dog_command_controller.py): 153
- [controllers/frame_update_controller.py](controllers/frame_update_controller.py): 857
- [controllers/server_reconnect_controller.py](controllers/server_reconnect_controller.py): 113
- [controllers/telemetry_controller.py](controllers/telemetry_controller.py): 73
- [controllers/video_source_controller.py](controllers/video_source_controller.py): 219
- [ui/status_ui_controller.py](ui/status_ui_controller.py): 75
- [ui/ui_event_handlers.py](ui/ui_event_handlers.py): 422
- [ui/control_panel_sections.py](ui/control_panel_sections.py): 133
- [vision/ai_vision_controller.py](vision/ai_vision_controller.py): 425
- [vision/cv_hist_debug.py](vision/cv_hist_debug.py): 135
- [vision/mask_picker.py](vision/mask_picker.py): 180
- [vision/yolo_runtime.py](vision/yolo_runtime.py): 1,883
- [vision/legacy/cv_ball_detection.py](vision/legacy/cv_ball_detection.py): 198
- [vision/utils/motion_grid_builder.py](vision/utils/motion_grid_builder.py): 170
- [vision/utils/overlay_renderer.py](vision/utils/overlay_renderer.py): 403
- [tools/yolo/yolo_labeling.py](tools/yolo/yolo_labeling.py): 359

## Additional Learning: Low Latency Video Streaming (Detailed)

This project currently has two active video-consumption paths using the same published H.264 source stream (`robotdog`).

### 1) Mac Controller Path (`mtDogMain.py`) - RTSP
- Purpose: operator-control app video path.
- Logical chain:
  - Pi camera capture -> `pi_publish_webrtc.sh` (H.264 elementary stream)
  - Publish into MediaMTX path `rtsp://<sfu-host>:8554/robotdog`
  - Mac `mtDogMain.py` opens RTSP URL and decodes frames for UI
- Protocol detail:
  - Signaling/control: RTSP (TCP control channel)
  - Media transport: configurable by client/runtime
  - Current default in this repo is RTSP client transport `tcp` for stability (`SFU_RTSP_TRANSPORT`)
- Strength:
  - simple integration with desktop control workflow
  - robust over imperfect LAN
- Tradeoff:
  - browser-native compatibility is weaker than WebRTC

### 2) Safari Viewer Path (iPhone/iPad/macOS) - WebRTC/WHEP
- Purpose: low-latency monitoring page and telemetry overlay.
- Logical chain:
  - Pi camera capture -> `pi_publish_webrtc.sh` -> MediaMTX (`/robotdog`)
  - Browser opens `http://192.168.0.32:8080/webrtc_view.html`
  - Page sends WHEP SDP offer to `http://192.168.0.32:8889/robotdog/whep`
  - MediaMTX returns SDP answer; browser receives video via WebRTC media path
- Protocol detail:
  - WHEP/HTTP is signaling only
  - media is RTP in WebRTC session (SRTP on normal secure deployment)
  - UDP is preferred for latency when network conditions allow
- Strength:
  - best fit for Safari/mobile
  - low-latency fanout via SFU relay
- Tradeoff:
  - stricter networking/ICE requirements than plain RTSP

### Important Clarification: One Source, Two Consumers
- There are not two independent camera encoders by design.
- One H.264 publish path (`robotdog`) is consumed by:
  - RTSP consumer (`mtDogMain.py`)
  - WebRTC consumers (Safari page through WHEP/WebRTC)

### Current Boot-Time Services (Pi)
- `smartdog.service`: robot control/telemetry server (`5001`, `8001`)
- `robot-publisher.service`: camera publish into SFU path (`robotdog`)
- `robot-sfu.service`: MediaMTX (`8554`, `8889`, `9997`)
- `robot-viewer.service`: static web (`8080`) from `Server/web/`
- `robot-telemetry.service`: overlay API (`8090`)

### End-to-End Verification Checklist
1. SFU path availability:
```bash
python3 - <<'PY'
import socket
host='192.168.0.32';port=8554;path='/robotdog'
req=(f'DESCRIBE rtsp://{host}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\nAccept: application/sdp\r\n\r\n').encode()
s=socket.socket(); s.settimeout(2); s.connect((host,port)); s.sendall(req)
print((s.recv(2048).decode('utf-8','ignore').splitlines() or ['<empty>'])[0]); s.close()
PY
```
2. WebRTC signaling endpoint:
```bash
curl -i -X OPTIONS http://192.168.0.32:8889/robotdog/whep | head -n 1
```
3. Viewer page + telemetry API:
```bash
curl -I http://192.168.0.32:8080/webrtc_view.html | head -n 1
curl http://192.168.0.32:8090/api/telemetry
```

### Latency Tuning Knobs (Practical)
- Publisher side:
  - `WIDTH`, `HEIGHT`, `FPS`, `BITRATE` in `robot-publisher.service` / `pi_publish_webrtc.sh`
- SFU side:
  - transport preference in `mediamtx.yml`
  - avoid transcoding (relay-only path)
- Viewer/client side:
  - keep playback path direct to Pi host
  - reduce other CPU-heavy tasks on Pi during streaming
- Troubleshooting rule:
  - control green does not imply video path healthy; validate SFU path independently

### Security Note (Current LAN Baseline)
- Current docs/config are LAN-focused baseline.
- Before WAN or untrusted LAN use, plan hardening for:
  - auth on stream/API endpoints
  - TLS/HTTPS for signaling and UI
  - TURN/STUN strategy and policy
  - access control for telemetry endpoints

## Revision History
- 2026-02-12 17:42 v1.12.48  Added Safari refresh reliability note for `/color` resolution profile: no-store response policy + delayed profile resync (`/video/config`) after page load to reduce stale default `960` UI fallback.
- 2026-02-12 17:33 v1.12.47  Added `/color` post-apply auto WebRTC renegotiation behavior note so resolution profile changes become effective without manual refresh in normal operation.
- 2026-02-12 17:26 v1.12.46  Added persisted `/color` resolution-selection behavior documentation (`video_runtime_config.json` + `video_publisher_profile.env`), including immediate apply path via `robot-publisher.service` restart and fallback-on-next-restart behavior.
- 2026-02-12 17:11 v1.12.45  Synced README version timestamp via `tools/version_time_sync.sh` after `/color` live-resolution overlay/runtime-profile documentation update.
- 2026-02-12 17:07 v1.12.45  Clarified `/color` resolution behavior: Live title now always renders `WxH` with fallback dimensions, and documented that `Video Resolution` dial currently applies to H264 fallback while active WebRTC display resolution follows publisher stream settings.
- 2026-02-12 16:09 v1.12.44  Updated `/color` low-voltage behavior visibility: added lower-left `Battery State` line (`NORMAL`/`LOW` with threshold + duration), consumed Pi debounced low-battery fields, and aligned low-battery alert/beep gating to stable server state.
- 2026-02-12 15:53 v1.12.43  Adjusted power-scope x-axis alignment to track uptime dynamically: before 60 minutes it scales `0 -> elapsed`, then transitions to 60-minute rolling window while retaining 5-minute tick labels.
- 2026-02-12 15:49 v1.12.42  Confirmed/adjusted power-scope timing source: `START` now maps to Pi power-up/boot time and `UPTIME` is strictly elapsed duration (`now - START`) from backend telemetry metadata.
- 2026-02-12 15:45 v1.12.41  Improved `/color` diagnostics readability: `Diag` now prefers LAN-reachable control endpoint instead of loopback-only display and lower-left HUD adds compact ports/function summary line (`5001/8001/8080/8081/8090/8554/8889`).
- 2026-02-12 15:42 v1.12.40  Refactored `/color` power scope to relative-time mission axis: x-axis now plots `Time Since Start` from first power sample, uses dynamic 5-minute labels, displays `START: HH:MM:SS | UPTIME: HH:MM:SS`, and defaults to a 60-minute rolling window.
- 2026-02-12 15:02 v1.12.39  Added voltage-scope power-on runtime ticker (`Power On HH:MM:SS`) sourced from Pi `/telemetry/power_history` uptime metadata for live elapsed-time visibility.
- 2026-02-12 14:51 v1.12.38  Minor `/color` UI polish: tightened battery-scope labels (`7.0V/6.4V` left-aligned with rail labels and `min` moved off `40` tick), moved hover voltage text higher, removed redundant lower-left status/proxy/model rows, merged Live Clients head+summary, added `Video Resolution` selector (`1280x720/960x540/640x360`), and ensured YOLO `imgsz` selector always displays active default.
- 2026-02-12 14:14 v1.12.37  Tuned `/color` operator HUD: merged stream transport text into lower-left status row with LIVE/STALLED pill, moved IMU mini readout into 3D overlay and added telemetry-lost red/grey fallback (`-.--`), repositioned battery scope to lower-left with mirrored 0..40min axis and explicit `7.0V`/warn lines, and enabled low-battery triple-beep guard (5s cadence).
- 2026-02-12 12:50 v1.12.36  Refined `/color` operator overlays: top-left client line now shows device+IP+FPS+heartbeat age, Live Clients summary is compact (`Live Clients : N lives (ttl Ts)`), and added translucent 25-minute battery trend chart with low-battery warning visuals.
- 2026-02-12 11:38 v1.12.35  Added `/color` `Live Clients` widget to show healthy viewer heartbeats from Pi `/viewer/summary` (device/IP/FPS/age) for real-time viewer/operator visibility.
- 2026-02-12 11:32 v1.12.34  Added `/color` viewer heartbeat identity telemetry (`/viewer/heartbeat`) to support Pi-side active-viewer summary (`/viewer/summary`) with richer browser/device hints than simple `iPhone Safari` class labels.
- 2026-02-12 11:23 v1.12.33  Added best-effort client-device label in `/color` live header (Mac/iPhone/iPad Safari class) rendered in light-yellow beside the Live View title/FPS.
- 2026-02-12 11:16 v1.12.32  Added minor-stream-warning guard for `/color`: transient RTSP worker errors now show non-blocking bottom-center warning without greying live video; only sustained/critical faults dim display.
- 2026-02-12 10:30 v1.12.31  Implemented next tracking phase (vision-only): Pi worker now keeps short-lived tracking lock/hold across brief detector misses and UI overlay marks hold source as `[trk]` for live verification.
- 2026-02-12 10:22 v1.12.30  Reduced live-UI flicker by debouncing stream-stall grey overlay on brief probe/FPS dips and stabilized static-ball visibility by adapting stale timeout to real Pi infer latency.
- 2026-02-12 10:15 v1.12.29  Removed blocking Pi-offline popup behavior in `/color`; outage/recovery now uses non-blocking in-page status/overlay only, with automatic clear after stream recovers.
- 2026-02-12 10:08 v1.12.28  Added Safari auto-recovery note: `/color` WebRTC client now re-negotiates after Pi power-cycle/disconnect states instead of remaining stuck on stale peer session.
- 2026-02-12 09:55 v1.12.27  Synced README timestamp via guard tool after `best`-priority fallback and stream/vision warning overlay documentation update.
- 2026-02-12 09:54 v1.12.27  Added `best`-first fallback policy documentation (`best` then `yolov8n`), infer-model source visibility in metrics, and UI guardrails for stalled stream / YOLO-error overlays with stale-target hide behavior.
- 2026-02-12 09:16 v1.12.26  Synced README timestamp via guard tool after ball-label UI/metrics visibility and `best_256_fp16.tflite` latency-optimization documentation update.
- 2026-02-12 09:14 v1.12.26  Added model-aware ball labels (`MT_ball`/`Yolo_sport ball`), documented `Infer (ms)` UI positioning improvement, and recorded live lower-latency `best_256_fp16.tflite` tuning result.
- 2026-02-12 08:56 v1.12.25  Synced README timestamp via guard tool after related server README viewer-port correction (`8081/color` primary lane).
- 2026-02-12 08:52 v1.12.25  Synced README timestamp via guard tool after related server README clickable `192.168.0.32` Quick Start link update.
- 2026-02-12 08:51 v1.12.25  Synced README timestamp via guard tool after related server README Safari-first Quick Start update.
- 2026-02-12 08:44 v1.12.25  Synced README timestamp via guard tool after related server README standalone WebRTC/SFU+YOLO hierarchy documentation update.
- 2026-02-12 08:04 v1.12.25  Updated Pi D-phase notes with deployed `tflite-multi` dual-model runtime (`best` + `yolov8n`), added active-heartbeat benchmark artifacts/metrics, and documented current blocker as CPU saturation rather than backend incompatibility.
- 2026-02-11 22:04 v1.12.24  Updated Pi D-phase runtime notes with TFLite-backend readiness, model fallback chain, and corrected active-heartbeat benchmark interpretation (`client_stream_fps` parsing fix); kept safety recommendation `yolo_enabled=false`.
- 2026-02-11 19:39 v1.12.23  Synced README timestamp via guard tool after related server benchmark-harness documentation update.
- 2026-02-11 19:22 v1.12.23  Synced README timestamp via guard tool after Pi appliance YOLO method documentation update.
- 2026-02-11 19:21 v1.12.23  Added Pi appliance YOLO method section: `.pt -> .onnx` conversion for both custom/general models, backend selection order (`onnxruntime` preferred), and current Pi runtime compatibility status.
- 2026-02-11 18:21 v1.12.22  Synced README timestamp via guard tool after detector-worker rollout status update.
- 2026-02-11 18:19 v1.12.22  Updated Pi detector-worker status after live validation: OpenCV installed, ONNX model deployed, and current blocker narrowed to OpenCV 4.5.1 ONNX importer incompatibility (temporary `yolo_enabled=false` rollback documented).
- 2026-02-11 17:56 v1.12.21  Synced README timestamp via guard tool after detector-worker dependency-gate documentation update.
- 2026-02-11 17:55 v1.12.21  Added detector-worker runtime dependency gate note (`opencv_or_numpy_not_available`) and clarified inference enablement requirement on Pi.
- 2026-02-11 17:53 v1.12.20  Synced README timestamp via guard tool after revision-history timestamp alignment.
- 2026-02-11 17:52 v1.12.20  Synced README timestamp via guard tool after detector-worker integration documentation update.
- 2026-02-11 17:49 v1.12.20  Documented full detector-worker integration in Pi color-viewer runtime (`8001` frame ingest + YOLO loop + `/vision/state` live target/health + bbox overlay in `/color`).
- 2026-02-11 17:38 v1.12.19  Synced README timestamp via guard tool after AI dataset detail expansion and file-hierarchy documentation update.
- 2026-02-11 17:36 v1.12.19  Added README reference to `AI_YOLO_Datasets.md` and expanded detailed file hierarchy section including all current YOLO `*.pt` model artifact paths.
- 2026-02-11 17:33 v1.12.18  Synced README timestamp via guard tool after YOLO Vision method documentation update.
- 2026-02-11 17:32 v1.12.18  Added explicit YOLO Vision method docs for current dual-model `mtDogMain.py` runtime (`best.pt` + `yolov8n.pt`) and model-role/selection flow.
- 2026-02-11 17:04 v1.12.17  Synced README timestamp via guard tool after final runtime rename refactor pass.
- 2026-02-11 17:02 v1.12.17  Synced README timestamp via guard tool after runtime rename documentation update.
- 2026-02-11 16:57 v1.12.17  Documented runtime rename to `color_viewer_server.py` and aligned color-viewer service naming notes for Pi-only operation.
- 2026-02-11 15:07 v1.12.16  Synced README timestamp via guard tool after revision-history timestamp alignment.
- 2026-02-11 15:05 v1.12.16  Synced README timestamp via guard tool after D-Phase-A vision-state documentation update.
- 2026-02-11 14:57 v1.12.16  Documented D-Phase-A runtime vision-state scaffold (`/vision/state`) and updated color-viewer status for `Yolo/Tracking` runtime toggles.
- 2026-02-11 12:23 v1.12.15  Synced README timestamp via guard tool after final pass of color-viewer action documentation updates.
- 2026-02-11 12:22 v1.12.15  Synced README timestamp via guard tool after color-viewer Demo/Horizon/Balance documentation update.
- 2026-02-11 12:20 v1.12.15  Documented color-viewer control expansion: wired `Balance/Horizon` toggles and `Demo` trigger API (`/demo`, `/demo/status`) on Pi `:8081`.
- 2026-02-11 09:45 v1.12.14  Synced README timestamp via guard tool after axis-definition documentation update.
- 2026-02-11 09:44 v1.12.14  Added explicit IMU axis-definition note (`Yaw->Z`, `Pitch->X`, `Roll->Y`) for color-view diagnostics/readability.
- 2026-02-10 19:15 v1.12.13  Synced README timestamp via guard tool after final metadata alignment.
- 2026-02-10 19:14 v1.12.13  Synced README timestamp via guard tool after revision-history consistency update.
- 2026-02-10 19:13 v1.12.13  Synced README timestamp via guard tool after color-viewer polish documentation update.
- 2026-02-10 19:10 v1.12.13  Documented color-viewer build badge and persistent IMU orientation tuning controls (invert/offset/reset).
- 2026-02-10 18:56 v1.12.12  Documented color-view overlay UX update: bottom-left 3D model embed, compact IMU line, and stale (>1s) alert styling.
- 2026-02-10 18:44 v1.12.11  Documented IMU color-viewer yaw-unwrapping behavior for smoother continuous heading visualization.
- 2026-02-10 07:40 v1.12.10  Added reference to remote Safari runbook/precheck artifacts in Server docs.
- 2026-02-10 07:33 v1.12.9  Added viewer-side `Balance` toggle wiring notes (`balance_on`/`balance_off`) with ARM/session safety.
- 2026-02-10 07:30 v1.12.8  Documented low-risk mobile action wiring (`beep`, `led`, `cal`) with ARM/session safety.
- 2026-02-10 07:27 v1.12.7  Documented Safari IMU 3D tuning controls and stale-freeze behavior in Pi viewer.
- 2026-02-10 07:11 v1.12.6  Documented simple Safari-safe 3D IMU baseline model in Pi viewer telemetry panel.
- 2026-02-09 21:31 v1.12.5  Documented mtDogMain IMU-web quick-launch/status and mobile UI-parity placeholder scaffold in Pi viewer.
- 2026-02-09 21:24 v1.12.4  Synced README timestamp via guard tool after Phase-5 failure-injection and soak-resume documentation updates.
- 2026-02-09 20:57 v1.12.3  Synced README timestamp via guard tool after Phase-5 hardening documentation updates.
- 2026-02-09 20:52 v1.12.2  Synced README timestamp via guard tool after Phase-5 runbook additions.
- 2026-02-09 19:02 v1.12.1  Synced README timestamp via guard tool after Phase-5 observability documentation update.
- 2026-02-09 18:58 v1.12.0  Added Phase-5 diagnostics endpoint usage and viewer diagnostics-panel note.
- 2026-02-09 18:52 v1.11.2  Synced README timestamp via guard tool after final Phase-4 validation updates.
- 2026-02-09 18:49 v1.11.1  Synced README timestamp via guard tool after Phase-4 documentation update.
- 2026-02-09 18:48 v1.11.0  Documented Phase-4 lock-state visibility, handoff actions, and busy-owner messaging in mobile viewer workflow.
- 2026-02-09 18:26 v1.10.1  Synced README timestamp via guard tool after Phase-3 command MVP documentation update.
- 2026-02-09 18:25 v1.10.0  Added Phase-3 mobile command MVP usage notes (`/api/session`, `/api/command`, arm + safety behavior).
- 2026-02-09 18:16 v1.9.1  Synced README timestamp via guard tool after build-badge documentation update.
- 2026-02-09 18:14 v1.9.0  Documented visible viewer build badge for runtime version/time confirmation during development.
- 2026-02-09 17:54 v1.8.1  Synced README timestamp via guard tool and confirmed educational streaming section for local + Pi sync.
- 2026-02-09 17:52 v1.8.0  Added detailed educational section on end-to-end low-latency video streaming paths (RTSP vs WebRTC/WHEP).
- 2026-02-09 17:06 v1.7.1  Synced README timestamp via guard tool after web-asset location refactor documentation.
- 2026-02-09 17:01 v1.7.0  Documented refactor: Pi-hosted viewer web assets moved to `Server/web` for clearer ownership.
- 2026-02-09 16:12 v1.6.1  Synced README timestamp via guard tool after Phase-2 updates.
- 2026-02-09 16:09 v1.6.0  Added Phase-2 telemetry overlay service checks and API endpoint guidance.
- 2026-02-09 15:26 v1.5.2  Synced README timestamp via guard tool after Phase-1 completion checks.
- 2026-02-09 15:25 v1.5.1  Synced README timestamp after Phase-1 documentation updates.
- 2026-02-09 15:15 v1.5.0  Updated default deployment to Pi-hosted SFU/viewer services and switched viewer/RTSP examples to Pi host.
- 2026-02-09 11:58 v1.4.5  Added clear macOS/iOS video-viewing runbook and explicit URL roles (player page vs WHEP API).
- 2026-02-08 15:00 v1.4.4  Added timestamp-guard workflow via `tools/version_time_sync.sh` + installed pre-commit drift check hook.
- 2026-02-08 14:52 v1.4.3  Synced README version timestamp to current local time (CST) for consistency with on-screen clock.
- 2026-02-08 12:56 v1.4.2  Clarified auto-start behavior (Pi control + publisher services), split-pipeline status interpretation, and recovery checks.
- 2026-02-08 11:29 v1.4.1  Added automated regression test command and test coverage list (`Client/tests`).
- 2026-02-08 10:06 v1.4.0  Added multi-client 5001 behavior notes and owner-arbitration usage guidance.
- 2026-02-07 20:45 v1.3.0  Added SFU backend + smartdog launcher major changes.
