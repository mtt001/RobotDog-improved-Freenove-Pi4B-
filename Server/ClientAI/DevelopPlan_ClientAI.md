# ClientAI Development Plan
# file: ./Code/Server/ClientAI/DevelopPlan_ClientAI.md

## Version
v1.4 (2026-02-12 18:30 local time)

## Document Intent
Define the implementation plan for ClientAI (browser YOLO inference) while keeping current Edge AI mode as user-selectable fallback. This file is the working execution plan for all ClientAI development under `Code/Server/ClientAI/`.

## Context
Current system already provides:
- Pi-side control/safety authority and command arbitration.
- WebRTC viewer path served from server-side web assets.
- Existing Edge AI mode and YOLO/tracking controls in current runtime.

New goal:
- Shift YOLO object detection inference to client browser for capable devices (Mac/iPad/iPhone) to reduce Pi CPU pressure, while preserving Pi-side authority for safety and actuation.

## Objective
1. Introduce ClientAI inference path using ONNX Runtime Web.
2. Offload compute-heavy object-detection inference from Pi to capable browser clients (Mac/iPad/iPhone), with Pi primarily serving web assets, video, and APIs.
3. Keep Pi server as deterministic I/O and safety appliance with authoritative command gating, even when inference is client-side.
4. Ensure browser detections are treated as advisory inputs that must pass server-side validation before any tracking/control consumption.
5. Default to ClientAI mode on capable client devices, with explicit manual override and automatic fallback to Edge AI.
6. Keep development artifacts organized under `Code/Server/ClientAI/`, with changelog discipline and README traceability.

## Scope
In scope:
- Browser inference runtime integration with live WebRTC frames.
- Detection result overlay and telemetry metrics in web UI.
- Client-to-server target publishing contract for tracking-assist use.
- Mode switching policy (`client-ai`, `edge-ai`, `off`) and fallback behavior.
- Cross-device performance validation (Safari iOS/macOS, Chrome desktop).
- Pi-side validation and protection path for client target payloads (freshness/schema/range/allowlist/rate-limit).
- Pi-side safety continuity: ownership, arm/disarm, watchdog, emergency-stop precedence remain server-authoritative.
- Pi-side fallback orchestration when client inference is unavailable/unstable/slow.

Out of scope for this phase:
- Fully autonomous motion based only on browser detections.
- WAN hardening changes unrelated to ClientAI execution.
- Replacing existing Edge AI implementation.
- Removing Pi-side safety and command arbitration responsibilities.

## Architecture Principles
1. Pi server remains authoritative for:
   - arm/disarm state
   - command safety limits
   - watchdog and stop behavior
   - ownership arbitration
2. Browser is an inference compute worker, not a safety authority.
3. Any browser-reported target is advisory until server-side validation passes freshness/range checks.
4. Fallback must be deterministic and observable (clear status + reason code).

## Target Runtime Architecture
### Client (Web)
- Inference engine: ONNX Runtime Web.
- Execution providers:
  - first choice: `webgpu` (if available/stable)
  - fallback: `wasm` (baseline compatibility)
- Input source: decoded video frames from current viewer pipeline.
- Output:
  - overlay rendering (boxes/labels/confidence)
  - structured target payload to server endpoint
  - local inference metrics (`infer_ms`, model_id, dropped_frames)

### Server (Pi)
- Maintains mode and policy state.
- Accepts client target payload only if:
  - session is armed as required
  - payload freshness within TTL window
  - payload schema and range validation pass
- Uses target data only in existing safe tracking pipeline (no bypass of safety gates).
- Exposes status/diagnostics for active inference source and fallback reason.

## Device Selection And Mode Policy
Default policy:
- If user agent is Mac/iPad/iPhone and browser capability check passes, default to `client-ai`.
- If capability check fails, use `edge-ai` (or `off` based on operator setting).

Mandatory controls:
- Manual mode selector always visible: `client-ai | edge-ai | off`.
- Manual selection has higher precedence than auto-detection until session reset/reconnect.
- Explicit status banner with:
  - active mode
  - active model
  - provider (`webgpu`/`wasm`)
  - fallback reason (if any)

## ClientAI-Server Contract (Proposed v1)
Endpoint concept:
- `POST /vision/client-target` (or websocket message channel equivalent)

Required payload fields:
- `ts_client_ms`
- `frame_id`
- `model_id`
- `provider`
- `infer_ms`
- `image_w`, `image_h`
- `detections[]` with:
  - `label`
  - `conf`
  - `x1`, `y1`, `x2`, `y2` (normalized 0..1)

Server validation:
- Reject stale payload (`now_ms - ts_client_ms > ttl_ms`)
- Reject malformed/overflow values
- Reject unsupported labels/classes (allowlist)
- Rate-limit accepted updates per client session

## Performance Policy And KPI Gates
Primary user experience target:
- Keep WebRTC viewing smooth first; inference is secondary.

Initial KPI targets (LAN baseline):
- Live stream:
  - `stream_fps_client_p95 >= 20`
  - no sustained stall > 2s
- Client inference:
  - iPhone/iPad Safari: `infer_ms_p95 <= 180`
  - Mac Safari/Chrome: `infer_ms_p95 <= 120`
  - detection cadence >= 3 Hz effective for tracked class
- Server protection:
  - no regression in command latency/safety watchdog behavior

Adaptive degrade policy:
1. Increase frame interval `N`.
2. Reduce model input size (example: 320 -> 256).
3. Switch provider `webgpu -> wasm` if unstable.
4. Fallback to `edge-ai` or `off` with visible reason.

## Phased Delivery Plan
### Phase A - Foundation And Contract
Status: Done (2026-02-12 18:30 local time)

Deliverables:
- `Server/ClientAI/README_ClientAI.md` (design + runbook + file map)
- client-target schema spec and server validation stub
- mode state contract in server status API

Acceptance:
- schema test vectors pass
- mode state visible in runtime status endpoint
Progress note (2026-02-12 18:30): mode/state APIs and client-target validation stub are implemented in `Server/telemetry_api_server.py`; ClientAI status is visible in telemetry and diagnostics payloads.

### Phase B - Browser Inference MVP (Read-Only Overlay)
Status: Done (2026-02-12 18:30 local time)

Deliverables:
- ONNX Runtime Web loader + model init logic
- frame sampling and inference loop
- overlay rendering with confidence labels
- runtime metrics panel fields for ClientAI

Acceptance:
- overlay and metrics visible on Safari + Chrome
- no control-path changes required for operation
Progress note (2026-02-12 18:30): `Server/web/webrtc_view.html` now includes ONNX Runtime Web bootstrap, frame sampling/inference loop scaffold, and overlay canvas render path.

### Phase C - Controlled Target Publish Integration
Status: On-going (2026-02-12 18:30 local time)

Deliverables:
- target publish channel from browser to server
- server freshness/validation/rate-limit enforcement
- tracking-assist path consumes validated target payload

Acceptance:
- invalid/stale payloads are rejected and logged
- valid payloads influence tracking only when safety state allows
Progress note (2026-02-12 18:30): advisory target publish to `/api/vision/client-target` is wired from browser; validation/rate/TTL enforcement is implemented server-side, but downstream tracking-assist consumer integration is still pending.

### Phase D - Hardening And Fallback
Status: On-going (2026-02-12 18:30 local time; queued after Phase C completion)

Deliverables:
- auto capability check + default mode policy
- adaptive degrade ladder implementation
- fallback reason codes + operator-facing status

Acceptance:
- deterministic fallback on error/perf drop
- one-switch rollback to current Edge AI behavior

### Phase E - Verification, Runbook, and Pi Sync Gate
Status: On-going (2026-02-12 18:30 local time; final verification gate)

Deliverables:
- verification report with KPI table by device/browser
- rollback checklist
- synchronized documentation updates under `Server/`

Acceptance:
- pass criteria met or explicit exception log approved
- Pi-side `Server/` source-of-truth sync and version-line verification completed before close

## Files And Documentation Rules For This Workstream
1. All new ClientAI artifacts live under `Code/Server/ClientAI/`.
2. Any changed file must include header/version history update with timestamp.
3. Maintain `Server/ClientAI/README_ClientAI.md` as change ledger:
   - architecture decisions
   - file-by-file purpose
   - test and validation notes
4. If server behavior/workflow/config changes, update `Server/README.md` in same task.

## Risks And Mitigations
Risk: Safari WebGPU variability across iOS versions.
- Mitigation: strict capability probe + wasm fallback + perf gate.

Risk: Browser detections introduce unsafe direct control assumptions.
- Mitigation: server-side validation + advisory-only target semantics.

Risk: Thermal/performance instability on mobile devices.
- Mitigation: adaptive interval/input-size policy and explicit operator controls.

Risk: State drift between local mirror and Pi source-of-truth `Server/`.
- Mitigation: mandatory sync + Pi-side header/version verification before completion.

## Rollback Plan
Immediate rollback path:
1. Force mode to `edge-ai` or `off` in runtime config.
2. Disable client target ingestion endpoint.
3. Keep existing WebRTC/telemetry/control paths unchanged.

Rollback acceptance:
- robot control safety behavior unchanged from pre-ClientAI baseline.
- viewer remains operational with no ClientAI dependency.

## Open Decisions Requiring Discussion
1. Should client detections be allowed to influence autonomous command generation, or only tracking-assist hints?
2. What exact UX thresholds do you require for iPhone Safari (`fps`, max overlay delay, reconnect time)?
3. Do you want a single model family only, or dual model policy (`best` primary + fallback model)?
4. Should auto mode selection persist per device/session, and where should preference be stored?
5. Which endpoint shape is preferred for target publishing (`POST` polling vs `WebSocket`)?

=========================================================================
=========================================================================

## Revision History
- 2026-02-12 18:30 v1.4  Updated phase execution status after implementation progress: Phase-A Done, Phase-B Done, Phase-C On-going with advisory publish + server validation completed and tracking-consumer integration pending.
- 2026-02-12 18:24 v1.3  Moved revision-history section to end of file to keep plan overview clean at document start.
- 2026-02-12 18:22 v1.2  Refactored core clarification into Objective/Scope: Pi offloads heavy AI inference to browser clients, while Pi remains authoritative for safety validation, command gating, and fallback orchestration.
- 2026-02-12 18:08 v1.1  Updated phased execution tracker with timestamped status per phase (Done/On-going) for active development visibility.
- 2026-02-12 17:57 v1.0  Rebuilt draft into a full execution proposal for browser-side YOLO inference with Pi-server deterministic safety boundary, phased delivery, KPI gates, rollback, and open decisions.
