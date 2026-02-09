# Next Development Proposal

## Version
v1.4 (2026-02-09 14:24 local time)

## Revision History
- 2026-02-09 14:24 v1.4  Added follow-on development target for Pi 4B minimal YOLO object detection + tracking after mobile video/server milestone.
- 2026-02-09 14:16 v1.3  Added design-for-testability feature requirements and mandatory verification gate with intervention escalation.
- 2026-02-09 13:03 v1.2  Added explicit host mapping note that `192.168.0.198` is the Client MacBook Pro M5.
- 2026-02-09 12:54 v1.1  Added quantitative acceptance criteria, API contract appendix, safety state machine, ownership lease semantics, and rollback/test hardening details.
- 2026-02-09 12:26 v1.0  Initial complete phased proposal for Pi-standalone video + iOS interactive control roadmap.

## Context
Current prototype behavior:
- Pi provides control/telemetry server (`5001`) and legacy video (`8001`).
- Pi publisher sends H.264 stream to SFU path `robotdog` via RTSP.
- SFU + web viewer host are on `192.168.0.198`.
- `mtDogMain.py` uses RTSP pull; Safari viewer uses WebRTC/WHEP.

Current issue:
- iPhone/iPad viewing depends on `192.168.0.198` being online.
- Desired direction is standalone service with clearer product path to mobile interaction.

Host mapping note (current environment):
- `192.168.0.32` = Raspberry Pi Server (robot control + publisher)
- `192.168.0.198` = Client MacBook Pro M5 (current SFU + web viewer host)

## Product Goal
Deliver a robust iPhone/iPad Safari experience that supports:
- low-latency live video
- live telemetry overlay
- selected safe robot commands

And reduce infrastructure dependency by moving toward always-on hosting.

## Scope And Principles
In scope:
- Pi-first deployment option (standalone or near-standalone)
- Safari-first web control UI
- safe command arbitration and fail-safe behavior
- phased delivery with rollback points

Out of scope for v1:
- fully replacing desktop operator workflow
- complex multi-user auth federation
- WAN internet deployment hardening (TURN/proxy/certs) beyond LAN baseline

Design principles:
- Keep video path stable and relay-only (avoid transcoding if possible).
- Keep safety decisions server-side (never trust browser-only rules).
- Ship incrementally with measurable acceptance criteria.

## Design For Testability Requirements
Every new feature/change should include testability by design:
- Deterministic interfaces:
  - keep protocol contracts explicit (`/api/telemetry`, `/api/command`, stream path, ownership semantics)
  - avoid hidden global state and implicit side effects
- Dependency injection:
  - isolate hardware/network dependencies behind interfaces for mock/fake testing
  - allow switching real Pi endpoints to stub endpoints in CI/local runs
- Observable behavior:
  - structured logs with source tags and correlation IDs for command/response tracing
  - health/status endpoints for all runtime components
- Failure-mode visibility:
  - explicit error codes and stale-data status (not silent fallback)
  - timeouts/retry counters surfaced in diagnostics
- Test layers for each feature:
  - unit tests for parsing/policy/state transitions
  - integration tests for API-to-server command path
  - runtime smoke tests for ports/stream endpoints

Verification gate for each build:
- Run the strongest test suite possible in current environment before calling work complete.
- If blocked by missing hardware/services/permissions, report:
  - what was validated
  - what remains unvalidated
  - exact user intervention required

## Target Architecture (End State)
Primary target:
1. Pi runs core control service (`smartdog.service`).
2. Pi runs publisher + SFU (MediaMTX) on Pi or another always-on host.
3. Pi (or same always-on host) serves mobile web app (`/webrtc_view.html` + API).
4. iOS Safari connects directly to always-on host for:
   - WebRTC video
   - telemetry API/WebSocket
   - command API

Transport model:
- Camera ingest: H.264 -> RTSP (or WHIP) into SFU.
- Browser playback: WHEP/WebRTC.
- Native app playback (`mtDogMain.py`): RTSP remains supported.

## Phased Delivery Plan

### Phase 0 - Baseline Freeze And Inventory
Objective:
- Freeze known-good prototype and establish reproducible baseline checks.

Deliverables:
- baseline config snapshot (IPs, ports, services)
- one-command health script output for:
  - Pi services
  - SFU endpoints
  - viewer endpoint
- documented rollback command set

Acceptance:
- Team can restore current working state in less than 10 minutes.

### Phase 1 - Infrastructure Consolidation (Always-On Hosting)
Objective:
- Remove dependency on developer MacBook power state.

Options:
1. Preferred simplicity: run SFU + web app hosting on Pi.
2. If Pi load is high: run on dedicated always-on LAN host (mini PC/NAS).

Deliverables:
- systemd service(s) for SFU and web app hosting
- updated defaults (`SFU_HOST`, viewer URLs)
- updated runbooks and `smartdog status` checks for SFU host role

Acceptance:
- iPhone playback works when MacBook is off.
- `http://<always-on-host>:8080/webrtc_view.html` and WHEP endpoint are stable after reboot.
- stream startup to first frame under 5s (p95) after service restart on LAN.
- WebRTC reconnection under 8s (p95) after brief Wi-Fi interruption.

### Phase 2 - Read-Only Mobile Telemetry Overlay
Objective:
- Add telemetry overlays to Safari viewer without control commands yet.

Telemetry v1 fields:
- battery voltage/state
- IMU roll/pitch/yaw
- ultrasonic distance
- stream status/fps indicator
- connection health timestamps

Deliverables:
- UI overlay components in viewer page
- backend API endpoint(s) or WebSocket feed
- polling/refresh strategy and stale-data indicator

Acceptance:
- overlay refresh under 1s cadence on LAN
- stale-data warnings shown when backend disconnected
- telemetry end-to-end freshness under 1200ms (p95) on LAN.

### Phase 3 - Mobile Command MVP (Safety-First)
Objective:
- Enable limited command set from iPhone/iPad.

Recommended command set v1:
- `STOP` (always allowed)
- `RELAX`
- limited directional motion (press-and-hold style)
- optional gait speed presets (bounded values)

Safety requirements:
- preserve owner arbitration on server
- enforce command rate limits and timeout auto-stop
- explicit command source labeling (mobile vs desktop)
- emergency stop always preempts ownership
- commands are ignored unless session is explicitly armed by current owner

Deliverables:
- command API in backend
- command controls in mobile UI
- server logs tagged by client/source

Acceptance:
- non-owner write command receives deterministic busy response
- emergency stop always succeeds
- motion auto-stops when command stream ends
- command-to-actuation acknowledgement under 200ms (p95) on LAN.

### Phase 4 - Multi-Client Policy And Session UX
Objective:
- Make concurrent mobile + desktop operation understandable and safe.

Deliverables:
- UI indicators for control ownership and lock state
- session handoff workflow (request/release control)
- clear messaging for `CMD_BUSY#OWNER`

Acceptance:
- users can identify who has control without reading logs
- handoff scenario tested across desktop + iOS devices
- ownership lease expiration behavior is visible and deterministic in UI.

### Phase 5 - Hardening, Observability, Release
Objective:
- Productionize for reliable daily use.

Deliverables:
- startup ordering and dependency checks (service health)
- structured logs and quick diagnostics endpoint
- cache-control strategy for mobile web assets
- soak test report (long-run stability)

Acceptance:
- 24h soak without unrecovered stream/control failure
- documented recovery steps for each known fault pattern
- per-release verification report includes executed tests + known gaps + required manual checks
- crash/restart drills pass for SFU service, API service, and Pi control service.

## Suggested Technical Changes By Area

## A. Video/SFU
- Keep relay-only path.
- Use one canonical stream path (`robotdog`) and one owner service.
- Prefer UDP for WebRTC media; keep RTSP TCP fallback where needed.

## B. Backend For Web UI
- Evolve `Demo_IMU_server.py` from demo proxy to service module, or add dedicated lightweight API service.
- Add:
  - `/api/telemetry`
  - `/api/command`
  - `/api/session` (ownership)
- Add explicit no-cache headers for HTML/JS in development and versioned assets for release.
- Freeze API schemas before UI control rollout (see contract appendix below).

## C. Pi Server Safety Layer
- Keep server-side command gating as source of truth.
- Add explicit source metadata in logs (`mobile_web`, `mtDogMain`, etc.).
- Add optional command whitelist per client type.
- Implement watchdog heartbeat timeout for motion commands (auto-stop on stale input).

## D. Configuration
- Centralize runtime host/port in one config surface.
- Avoid hardcoding mixed host IPs in multiple scripts.
- Provide one environment file for deployment profile:
  - `PI_IP`
  - `SFU_HOST`
  - `STREAM_PATH`
  - `HTTP_PORT`

## E. Documentation And Ops
- Keep `Client/README.md` and `Server/README.md` synchronized with actual deployment mode.
- Keep Pi sync rule for `Server/` enforced before closing tasks.
- Include phase-specific rollback commands in runbook sections, not only global rollback.

## Risks And Mitigations
Risk:
- Pi CPU/network bottleneck when adding SFU + web + control.
Mitigation:
- monitor CPU/mem/network; disable transcoding; lower bitrate/resolution if needed.

Risk:
- command safety regression with mobile controls.
Mitigation:
- server-side-only authorization checks; test non-owner rejection and stop override first.

Risk:
- stale cached web UI on iOS.
Mitigation:
- cache headers + version query strategy.

Risk:
- split-brain configs across machines.
Mitigation:
- single profile file and documented deployment script.

Risk:
- accidental command issuance from unauthorized browser session on LAN.
Mitigation:
- require session token + ownership lease + command arm state before motion commands.

## Definition Of Done For “Mobile v1”
- iPhone/iPad Safari can load one URL and get:
  - live video
  - live telemetry
  - stop + basic movement controls
- Works with MacBook powered off (assuming always-on host is Pi or dedicated server).
- Ownership/safety behaviors are visible and verified.
- Runbooks and diagnostics are updated and tested.

## Immediate Next Step Recommendation
Start with Phase 1 and Phase 2 first:
1. Decide hosting mode:
   - Pi-only
   - always-on external SFU host
2. Implement always-on startup and health checks.
3. Add telemetry overlay read-only before enabling commands.

This keeps safety risk low while moving quickly toward standalone mobile usability.

## Follow-On Target After Mobile Video/Server Milestone
Objective:
- Add minimal on-device object detection + tracking on Raspberry Pi 4B as a follow-on milestone after Mobile v1 is stable.

Feasibility summary (Pi 4B):
- feasible for low-resolution, small-model, single-target use cases
- not suitable for high-FPS full-scene detection on CPU-only path
- recommended operating mode: detect every N frames + tracker on intermediate frames

Scope for this follow-on:
- one camera pipeline
- limited class set (or single target type)
- tracking output for telemetry/assist logic first, autonomous motion later

Non-goals for first vision milestone:
- 15-30 FPS dense detection
- large multi-class model deployment
- direct motor actuation from raw detector output without safety policy layer

Proposed phases:
1. Vision Phase A (Read-only analytics):
   - run lightweight detector (`yolo-nano`/tiny-equivalent) at 320-416 input
   - publish target bbox/score/fps as telemetry only
   - no robot motion control coupling
2. Vision Phase B (Tracked target assist):
   - add tracker (e.g., SORT/ByteTrack class) to smooth low-FPS detector output
   - maintain target ID and confidence decay policy
   - expose target lock status in mobile UI
3. Vision Phase C (Safety-gated control integration):
   - optional closed-loop assist commands only through existing ownership/safety gate
   - enforce max speed, timeout auto-stop, and immediate operator override

Acceptance targets (initial Pi 4B CPU-only baseline):
- end-to-end detector+tracker pipeline stable for 30 minutes without crash
- achieved vision update rate documented (target baseline: 1-6 FPS depending on model)
- target-loss behavior is deterministic (confidence timeout then clear lock)
- CPU/memory budget recorded under concurrent server workloads

Decision gate before implementation:
- proceed on Pi CPU-only path if achieved FPS and thermal stability meet mission need
- otherwise offload inference (always-on LAN host) or add accelerator (USB TPU/NPU class)

## API Contract Appendix (v1 Draft)

### `/api/telemetry` (GET)
Response `200`:
```json
{
  "ts": 1739076840.231,
  "battery": {"voltage": 7.82, "state": "normal"},
  "imu": {"roll": -1.2, "pitch": 0.4, "yaw": 124.7},
  "ultrasonic_cm": 48.5,
  "stream": {"status": "live", "fps": 29.7},
  "source_health": {"pi_link": "ok", "age_ms": 320}
}
```
Errors:
- `503 TELEMETRY_STALE` when upstream data age exceeds stale threshold.

### `/api/session` (GET/POST/DELETE)
- `GET`: current ownership snapshot.
- `POST`: request ownership lease.
- `DELETE`: release ownership.

Response `GET 200`:
```json
{
  "owner_id": "mobile:iphone14:abc123",
  "owner_type": "mobile_web",
  "lease_ttl_ms": 10000,
  "expires_in_ms": 7421,
  "armed": false
}
```

Response `POST 200`:
```json
{
  "status": "granted",
  "owner_id": "mobile:iphone14:abc123",
  "lease_ttl_ms": 10000
}
```

Response `POST 409`:
```json
{
  "error": "CMD_BUSY#OWNER",
  "owner_id": "desktop:mtdogmain:workstation01"
}
```

### `/api/command` (POST)
Request:
```json
{
  "session_id": "mobile:iphone14:abc123",
  "seq": 1027,
  "cmd": "MOVE_FWD",
  "hold": true,
  "speed": 0.35,
  "ts": 1739076841.119
}
```

Response `200`:
```json
{
  "accepted": true,
  "applied_cmd": "MOVE_FWD",
  "auto_stop_ms": 300
}
```

Errors:
- `401 UNAUTHORIZED_SESSION`
- `409 CMD_BUSY#OWNER`
- `422 INVALID_COMMAND`
- `423 NOT_ARMED`

## Safety State Machine (Server Authoritative)

States:
- `IDLE`: no active owner, robot not moving.
- `OWNED`: owner lease granted, command channel open, not moving.
- `MOVING`: valid hold command stream active.
- `STALE_INPUT`: lease exists but command heartbeat timed out; auto-stop issued.
- `E_STOP`: emergency stop latched; movement blocked until explicit clear.

Transitions:
- `IDLE -> OWNED`: `/api/session POST` granted.
- `OWNED -> MOVING`: valid armed motion command received.
- `MOVING -> STALE_INPUT`: heartbeat gap exceeds timeout (e.g., 300ms).
- `STALE_INPUT -> OWNED`: valid command stream resumes.
- `* -> E_STOP`: emergency stop command or safety fault.
- `E_STOP -> IDLE`: explicit reset + safety checks pass.
- `OWNED -> IDLE`: lease released or lease expires.

Required timers:
- ownership lease TTL: 10s (renew every 3s).
- command heartbeat timeout: 300ms.
- telemetry stale threshold: 1500ms.

## Ownership And Lease Semantics

- Ownership is a lease, not a permanent lock.
- Only lease owner can issue non-emergency commands.
- `STOP` is always accepted from any client source.
- iOS background/tab suspension is treated as heartbeat loss; server auto-stops and keeps or expires lease by TTL.
- UI must display: owner, lease countdown, armed/disarmed state, and last safety event.

## Test Matrix And Fault Injection (Minimum)

- Owner conflict: desktop owns, mobile issues movement command -> expect `409 CMD_BUSY#OWNER`.
- Emergency override: non-owner sends `STOP` during owner motion -> motion halts immediately.
- Network jitter/loss: introduce packet loss and verify auto-stop plus recovery.
- Service restart: restart SFU and API service separately; verify reconnect within targets.
- Pi reboot: verify services come back in correct order and health checks pass.
- iOS backgrounding: lock screen or switch app while moving; verify heartbeat timeout auto-stop.
- Cache validation: deploy new web assets and verify iOS serves updated bundle/version.
