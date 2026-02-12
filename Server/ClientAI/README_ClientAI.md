# ClientAI Workstream README
# file: ./Code/Server/ClientAI/README_ClientAI.md

## Version
v1.0 (2026-02-12 18:30 local time)

## Revision History
- 2026-02-12 18:30 v1.0  Initialize ClientAI architecture/runbook ledger; record implemented Phase-A/B/C foundation and validation boundaries.

## Intent
Track ClientAI architecture decisions, API contract, file ownership, implementation status, and verification notes for browser-side YOLO inference with Pi-side safety authority.

## Safety Boundary
- Pi server remains authoritative for arm/disarm, watchdog stop, and command arbitration.
- Browser detections are advisory and must pass server validation.
- Invalid/stale payloads and mode mismatches are rejected server-side.

## Implemented Scope Snapshot (Current)
1. Phase A foundation:
- `GET/POST /api/clientai` mode-policy/state contract.
- `POST /api/vision/client-target` validation stub (TTL/schema/range/allowlist/rate).
- `client_ai` state visible in `/api/telemetry` and `/api/diagnostics`.

2. Phase B MVP:
- `Server/web/webrtc_view.html` adds overlay canvas and ClientAI panel.
- Browser-side ONNX Runtime Web bootstrap (`ort.min.js`) with provider probe (`webgpu` then `wasm`).
- Frame sampling + inference loop scaffold with adaptive `inferEveryN` throttle.

3. Phase C partial integration:
- Advisory target publish from browser to `POST /api/vision/client-target`.
- Session/mode-gated server acceptance; no direct control-path bypass.

## API Contract (Current)
- `GET /api/clientai`
  - returns requested/active mode, provider/model, capability state, fallback reason, counters.
- `POST /api/clientai`
  - `mode`: `client-ai|edge-ai|off`
  - `action`: `reset_auto`
  - `client_ai_capable`, `provider`, `model_id`
- `POST /api/vision/client-target`
  - required: `ts_client_ms`, `frame_id`, `model_id`, `provider`, `infer_ms`, `image_w`, `image_h`, `detections[]`
  - detection item: `label`, `conf`, `x1`, `y1`, `x2`, `y2` (normalized)

## Model Serving
- `GET /api/clientai/model-manifest`
- `GET /api/clientai/model/<name>`
- Current allowlisted ONNX names:
  - `yolov8n_cv451.onnx`
  - `best_cv451.onnx`

## File Map
- `Server/telemetry_api_server.py`: ClientAI API + validation + model-manifest/model stream.
- `Server/web/webrtc_view.html`: viewer UI, overlay render, ClientAI runtime loop.
- `Server/ClientAI/DevelopPlan_ClientAI.md`: phased roadmap + status tracker.
- `Server/ClientAI/README_ClientAI.md`: this ledger.

## Verification Notes
- Python syntax check expected: `python3 -m py_compile Server/telemetry_api_server.py`
- Runtime manual checks expected:
  - `/api/clientai`, `/api/clientai/model-manifest`, `/api/vision/client-target` response behavior
  - viewer overlay draw and mode transitions in Safari/Chrome

## Remaining Work
- Improve model-specific decoding robustness across ONNX export variants.
- Add automated schema/unit tests for validation logic.
- Wire accepted client targets into tracking-assist consumer path under explicit safety gate.
- KPI profiling and fallback thresholds per device/browser.
