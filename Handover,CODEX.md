# Handover CODEX
# File: `Handover,CODEX.md`

## Version
v1.0 (2026-02-11 21:32 local time)

## Revision History
- 2026-02-11 21:32 v1.0  Initial cross-thread handover for Pi-first YOLO/WebRTC stage, including current runtime status, blockers, changed files, and immediate continuation steps.

## Should You Start A New Thread?
Yes. At ~74% context usage, start a new thread now for safer continuity and fewer context-loss errors.

## Project Intent (Current Stage)
- Pi must run in always-on appliance mode.
- P0 priority: WebRTC/SFU video + safe control path (ownership + ARM gate).
- Vision must stay decoupled from motor control loop.
- Current effort: make YOLO (`best.pt` + `yolov8n.pt`) workable in Pi runtime and measurable by benchmark harness.

## What Is Implemented
1. Pi color viewer runtime:
- Service: `robot-color-viewer.service`
- Runtime file on Pi:
  - `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/color_viewer/color_viewer_server.py`
- Latest deployed runtime version:
  - `2026.02.11-29`

2. Vision worker backends:
- Backend selection order for ONNX:
  - `onnxruntime` (preferred) -> `onnx-dnn` (OpenCV fallback)
- Ultralytics `.pt` path still supported.
- Added dual-model mode for `.pt`:
  - `yolo_model_path` accepts comma-separated models.
  - Example: `.../best.pt,.../yolov8n.pt`
  - Worker merges detections by highest confidence.

3. Benchmark harness:
- Added:
  - `/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/phaseD_benchmark_1hz.sh`
- Features:
  - 1Hz sampling
  - Tier profiles (`baseline/light/target/stress`)
  - CSV + JSON outputs
  - PASS/WARN/FAIL summary gates

## Current Blockers (Critical)
1. Pi runtime package compatibility:
- `onnxruntime` cannot be installed from current Pi package indexes (`No matching distribution found`).
- OpenCV `4.5.1` ONNX importer fails loading current YOLO graph (`Add` node parse error).

2. Result:
- Pi YOLO inference cannot run yet in this OS/runtime stack.
- Keep safe default:
  - `yolo_enabled=false`
  - `tracking_enabled=false`

## Latest Verified Runtime Status
- `robot-color-viewer.service`: active.
- `http://192.168.0.32:8081/version` => `2026.02.11-29`.
- `/vision/state` with YOLO off returns `health=idle` after short settle window.
- WebRTC endpoint readiness remains usable (`/video/status` prefers `webrtc`).

## Benchmark Results Captured On Pi
Files:
- `/tmp/phaseD_benchmark_baseline_20260211_193439.json`
- `/tmp/phaseD_benchmark_target_20260211_193620.json`

Summary:
- Baseline (30s): FAIL
  - reasons: `cpu_p95>90`, `no_client_fps_samples`
  - temp p95: `60.3C`
  - cpu p95: `92.9`
- Target (30s): FAIL
  - reasons: `cpu_p95>90`, `no_client_fps_samples`
  - temp p95: `61.8C`
  - cpu p95: `93.9`
  - vision_error_count: `30`

Important interpretation:
- These benchmark runs were headless (no active browser heartbeat), so `stream_fps_client` stayed `0`.
- FAIL is expected until run with active Safari viewer heartbeat and a compatible detector backend.

## Files Changed In This Stage (Key)
- `Client/tools/imu_viewer/color_viewer_server.py`
  - backend integration + dual-model support + version history updates.
- `Server/phaseD_benchmark_1hz.sh`
  - new script (v1.3) with 1Hz benchmark and summary.
- `NEXT_DEVELOPMENT_PROPOSAL.md`
  - updated to include A/B/C architecture-governor plan and stage verification.
- `Client/README.md`
  - added Pi YOLO method (`.pt -> .onnx`) and backend notes.
- `Server/README.md`
  - benchmark harness docs and current runtime constraints.

## Immediate Next Steps For New Thread
1. Decide runtime path to unblock Pi detector:
- Option A (recommended): migrate Pi to 64-bit newer OS/runtime where `onnxruntime`/modern stack is available.
- Option B: introduce a different inference backend compatible with current Pi image.

2. Once backend is available:
- Run detector with:
  - custom only (`best`)
  - general only (`yolov8n`)
  - dual-model (`best + yolov8n`)
- Collect real metrics:
  - `det_fps`, `infer_ms`, target stability, effect on WebRTC KPI.

3. Re-run benchmark with active viewer:
- Open Safari viewer to feed client heartbeat.
- Run:
```bash
TIER=baseline DURATION_SEC=120 WARMUP_SEC=20 ./Server/phaseD_benchmark_1hz.sh
TIER=target DURATION_SEC=120 WARMUP_SEC=20 ./Server/phaseD_benchmark_1hz.sh
```

4. Keep safety policy unchanged:
- Vision remains read-only telemetry path.
- No direct vision-to-motor coupling.

## Quick Command Snippets For New Thread
Service and version:
```bash
ssh pi@192.168.0.32 'systemctl is-active robot-color-viewer.service'
curl -fsS http://192.168.0.32:8081/version
```

Vision state/config:
```bash
curl -fsS http://192.168.0.32:8081/vision/config
curl -fsS http://192.168.0.32:8081/vision/state
```

Set safe defaults:
```bash
curl -fsS -X POST http://192.168.0.32:8081/vision/config \
  -H 'Content-Type: application/json' \
  -d '{"yolo_enabled":false,"tracking_enabled":false}'
```

Set dual-model `.pt` config (only when Ultralytics/Torch runtime is available):
```bash
curl -fsS -X POST http://192.168.0.32:8081/vision/config \
  -H 'Content-Type: application/json' \
  -d '{"yolo_model_path":"/path/to/best.pt,/path/to/yolov8n.pt","yolo_enabled":true,"tracking_enabled":false}'
```

## Notes For Continuity
- Respect AGENTS rules:
  - update header/version history on every edited `*.md/*.py/...`
  - use local timestamp minute from `date`.
- Keep Pi-server-first runtime mindset:
  - local `Code/Server` is synced backup/reference; deployment target is Pi runtime path.
