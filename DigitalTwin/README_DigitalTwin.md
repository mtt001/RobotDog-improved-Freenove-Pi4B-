<!--
File: DigitalTwin/README_DigitalTwin.md
Version: v1.75 (2026-02-28 13:21)
Revision History: moved to the end of this file.
-->

# README_DigitalTwin

## Handoff Relay
- Detailed operator relay package: `handoff_TaskList.md`

## Quick Start (Launch Page First)

For a new user, use this exact sequence:

1. Start local host service:
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code
python3 DigitalTwin/scripts/digitaltwin_dev_server.py --host 127.0.0.1 --port 8766 --pi-host 192.168.0.32 --notify
```

2. Verify the page is reachable (`HTTP 200` expected):
```bash
curl -I http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html
```

3. Open the page in Safari:
```bash
open -a Safari 'http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html'
```

4. If Safari is already open and not focused:
```bash
osascript -e 'tell application "Safari" to activate'
```

Troubleshooting (basic):
- If step 2 is not `HTTP 200`, restart step 1 and try again.
- Do not use `file://...` path for normal operation; use the `http://127.0.0.1:8766/...` URL above.

## HIL Stability Gates (Pre-MuJoCo)
1. Read algorithm/threshold design:
```bash
cat DigitalTwin/docs/HIL_Stability_Gates.md
```
2. Run gait + HIL gate test:
```bash
python3 DigitalTwin/scripts/test_gait_walk_playwright.py --headless
```
Expected artifact:
- `DigitalTwin/logs/HIL_Test_Report.json`
3. Open page in Safari for visual support-polygon/COM overlay:
```bash
open -a Safari 'http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html'
```
4. Basic troubleshooting:
- If Playwright fails on HIL margin, confirm dog is in `Walk` mode and not in replay state.
- If penetration violations appear, refresh page and rerun with default camera/controls.

## Goal
Create a local **Digital Twin** for the Pi Server Robot Dog at a **professional-grade engineering standard** comparable to MuJoCo and ROS 2 simulation workflows, so it can:
- Prioritize a MuJoCo-style operator UI (clean viewport, deterministic controls, and measurable simulation feedback) as the primary development interface.
- Emulate servo/joint movement accurately.
- Develop and test posture and gait behavior safely before hardware runs.
- Integrate IMU feedback (roll/pitch/yaw) into the 3D pose pipeline.
- Enforce reproducible validation, interface contracts, and kinematic correctness suitable for long-term robotics development.
- Stay aligned with Freenove tutorial references and real hardware constraints.

## Camera Mode Architecture Upgrade (v2.00)
- Date: 2026-02-27 20:48 CST
- Removed 2D projection dependency from regression-critical verification path; servo behavior gates now rely on 3D command/isolation checks.
- Enforced and re-verified 3D servo hierarchy behavior via Playwright (`S11/S12/S13` isolation + range checks).
- Added camera mode manager hooks (`FOLLOW` default, `FREE` optional) through runtime debug API.
- Hotfix refinement (2026-02-27 20:48 CST):
  - Corrected servo rig axis mapping so S12/S13 visual movement matches actual 3D leg hinge geometry.
  - Added FOLLOW/HORIZON wheel-distance adjust behavior to restore practical zoom/model-size control in follow camera mode.
  - Re-ran full phased regression (`pass=7`, `fail=0`) and refreshed UI evidence screenshots.
- COM visibility refinement (2026-02-28 07:50 CST):
  - Torso shell (`body`/`bodyTop`) is now semi-transparent so the body COM marker can be inspected through the torso.
  - Added higher-visibility COM core marker (cyan shell + pink core) for easier center-of-mass inspection in 3D view.
- Added world invariance runtime audit:
  - Grid and ground transforms are continuously checked against startup baselines.
  - Duplicate robot-root detection is enforced (`robotCount == 1`).
  - Runtime emits `worldInvariant=true/false` diagnostics and halts action on violation.
- Regression status:
  - `python3 DigitalTwin/scripts/run_phase_verification.py --headless` => PASS (`pass=7`, `fail=0`).
- Extension artifacts:
  - `iCloud/AI_Reports/ext1_servo_isolation.json`
  - `iCloud/AI_Reports/ext2_camera_stability.md`
  - `iCloud/AI_Reports/ext3_world_invariance.json`
  - `iCloud/AI_Reports/ext4_performance.json`
  - `iCloud/AI_Reports/ext5_fk_ik_consistency.json`
  - `iCloud/AI_Reports/ext6_com_debug.png`
  - `iCloud/AI_Reports/ext7_structure_hardening.md`
  - `iCloud/AI_Reports/ext8_camera_modes.md`
  - `iCloud/AI_Reports/final_autonomous_cycle.md`

## Coordinate Systems Tutorial (Interactive 3D)

An interactive 3D tutorial page visualizes the three coordinate systems used
throughout the Digital Twin and explains how they map to each other.

### The Three Frames

| Frame | +X | +Y | +Z | Where used |
|---|---|---|---|---|
| **Dog FLU** (body-fixed) | Forward | Left | **Up** | Body arrows on 3D model |
| **Three.js Scene** (internal) | Forward | **Up** | Right | `getWorldPosition()` returns |
| **Pi Firmware IK** (math vars) | Stride | Height | Lateral | `Control.py forWard()` |

### Key Mapping (Dog ↔ Scene)

```
Dog X (Forward) = Scene x (Forward)
Dog Y (Left)    = Scene −z
Dog Z (Up)      = Scene y (Up)     ← this is why gait panel label was wrong!
```

### Side-View Projection Plane

When the camera looks along Dog +Y (from the right side), the visible plane
is **Dog X-Z** (X horizontal, Z vertical). In Scene coordinates this corresponds
to **Scene x-y**. The Gait Debug panel should therefore label its axes as
**X horizontal, Z vertical** (dog frame), not "X, Y" (scene frame).

### Launch the Tutorial

```bash
# 1. Start local server (if not already running):
python3 -m http.server 8877

# 2. Verify reachable (expect HTTP 200):
curl -I http://127.0.0.1:8877/DigitalTwin/pages/tutorial_coordinate_systems.html

# 3. Open in Safari:
open -a Safari 'http://127.0.0.1:8877/DigitalTwin/pages/tutorial_coordinate_systems.html'
```

The tutorial page provides:
- Orbitable 3D view with all three coordinate frames rendered as labeled arrows.
- Dashed mapping lines connecting physically identical directions across frames.
- A semi-transparent green projection plane showing the side-view Dog X-Z cut.
- A camera-eye arrow demonstrating the "looking along Dog +Y" viewpoint.
- A Pi Firmware IK ellipse showing the internal math variable plane.
- WRONG vs CORRECT label comparison banners.
- Buttons to isolate each frame, jump to side-view camera, or reset.

File: [`DigitalTwin/pages/tutorial_coordinate_systems.html`](pages/tutorial_coordinate_systems.html)

---

### UI Priority (MuJoCo-Style)
- UI parity is a top-level priority for all phases.
- Any phase is considered complete only when UI behavior and telemetry remain clear, deterministic, and regression-tested.
- New kinematics/runtime features must be visible and controllable from the primary UI path before phase sign-off.

## Goal Deployment Plan (All Phases to Implement)
Execute all phases in sequence; do not skip phase exit gates.

1. **Phase A — Baseline Foundation (UI-First)**
  - Implement scene graph, coordinate frames (FLU/ENU), and neutral pose with MuJoCo-style operator-facing panel layout.
  - Deliverable: stable 3D model with axis overlays, deterministic startup, and usable primary UI controls.
  - Exit gate: frame checks PASS and no parent-child transform leakage.

2. **Phase B — Command Runtime Integration**
  - Implement servo command ingest (`S11/S12/S13`), mapping, and optional smoothing.
  - Deliverable: repeatable joint response for identical command streams.
  - Exit gate: replay determinism confirmed and command mapping traceable.

3. **Phase C — Kinematics Core (FK + IK)**
  - Implement FK debug outputs and IK solver with limits/clamping behavior.
  - Deliverable: target-to-joint solve path and FK/IK round-trip validation.
  - Exit gate: round-trip error within tolerance and unreachable target handling is explicit.

4. **Phase D — Sensor/Body Coupling**
  - Integrate IMU roll/pitch/yaw into body pose while preserving frame semantics.
  - Deliverable: synchronized body orientation with consistent leg kinematics.
  - Exit gate: posture sweeps maintain correct axis orientation and PASS diagnostics.

5. **Phase E — Regression and Reliability**
  - Run smoke/posture/gait/imu test suites and persist artifacts to logs.
  - Deliverable: repeatable validation evidence for each build.
  - Exit gate: all automated checks pass in clean local runs.

6. **Phase F — Module Hardening and Reuse**
  - Refactor into reusable modules (`Leg3DOF`, `IKSolver`, `CoordinateDebug`) without behavior drift.
  - Deliverable: maintainable architecture ready for ClientAI/ROS-style integration.
  - Exit gate: regression outputs unchanged after refactor.

7. **Phase G — Deployment Readiness**
  - Freeze interfaces, document contracts, and validate operator workflow end-to-end.
  - Deliverable: professional local Digital Twin package suitable for continuous development.
  - Exit gate: onboarding + engineering docs are complete and implementation checks remain green.

## Scope and Source Inputs
- Robot platform: Freenove Robot Dog Kit for Raspberry Pi.
- Servo model baseline: `Emax ES08MA II`.
- Reference tutorial:
  - `resources/freenove_refs/Freenove Robot Dog,Tutorial.pdf`
- Specs/dimensions template:
  - `resources/specs/robot_specs_template.json`

## File Hierarchy and Related Files

### Core Hierarchy (DigitalTwin)
```text
DigitalTwin/
├─ README_DigitalTwin.md                    # Main engineering/runtime guide
├─ handoff_TaskList.md                      # Operator/agent relay plan and pending tasks
├─ pages/
│  └─ freenove_robotdog_3d_render.html      # Main local Digital Twin UI page
├─ scripts/
│  ├─ run_phase_verification.py             # A→G phase orchestrator and status summary
│  ├─ smoke_servo_sweep_playwright.py       # Servo sweep smoke verification
│  ├─ test_posture_modes_playwright.py      # Posture/mode transition verification
│  ├─ test_gait_walk_playwright.py          # Walk gait dynamic verification
│  ├─ test_imu_feedback_playwright.py       # IMU/pose and frame-pass verification
│  ├─ test_mujoco_ui_gate_playwright.py     # MuJoCo-style UI priority gate
│  ├─ test_servo_axis_direction_playwright.py # S11/S12/S13 direction/isolation checks
│  ├─ p1_calibration_update.py              # Sync P1 calibration values to JSON/CSV
│  ├─ p2_sim_estimate_and_update.py         # Simulated P2 estimate + update flow
│  └─ digitaltwin_dev_server.py             # Resilient local host/watchdog launcher
├─ resources/
│  ├─ specs/
│  │  ├─ robot_specs_template.json          # Canonical machine-readable robot parameters
│  │  └─ measurement_log_template.csv       # Measurement/provenance tracking log
│  └─ freenove_refs/
│     └─ Freenove Robot Dog,Tutorial.pdf    # Hardware/tutorial reference
└─ docs/
   └─ MEASUREMENT_BENCH_SHEET.md            # Printable measurement worksheet
```

### Related Files and Descriptions (Quick Index)
| File | Role | When to Update |
|---|---|---|
| `README_DigitalTwin.md` | Human-readable architecture, methods, workflow, revision history | Any behavior/workflow/method change |
| `handoff_TaskList.md` | Agent relay status, pending tasks, execution SOP | End of each work stage / operator handoff |
| `resources/specs/robot_specs_template.json` | Source-of-truth numeric parameters and provenance | Any measured/assumed value change |
| `resources/specs/measurement_log_template.csv` | Measurement log with source/confidence/owner | Every calibration or assumption update |
| `scripts/run_phase_verification.py` | Primary gate runner for phase PASS/FAIL | When phase flow, checks, or orchestration change |
| `pages/freenove_robotdog_3d_render.html` | Main UI runtime and 3D rendering behavior | Any UI/render/control behavior change |

Sync rule:
- Keep `README_DigitalTwin.md` + `robot_specs_template.json` + `measurement_log_template.csv` synchronized as one update set.

## Hardware and Physical Arrangement (Critical, Do Not Omit)

This section is mandatory for faithful Digital Twin emulation and must remain in the README.

### Physical Layer (Real Robot)
- Raspberry Pi 4B
- Freenove HAT (`PCA9685`, 16-channel PWM)
- 13x `Emax ES08MA II` servos
- `MPU6050` IMU
- WebRTC video stream path
- WebSocket telemetry path

### Physical Servo Topology Used by This Workspace
- Modeled active servo channels: `S2..S13` and `S15` (13 total channels).
- Leg-to-channel grouping:
  - `FL`: `S2, S3, S4`
  - `FR`: `S11, S12, S13`
  - `RL`: `S5, S6, S7`
  - `RR`: `S8, S9, S10`
- Additional body/head channel used in twin runtime: `S15`.

### Physical Joint Arrangement and Axis Semantics
- Per leg chain (proximal -> distal): hip roll -> hip pitch -> knee pitch.
- Baseline axis semantics (FR reference):
  - `S11`: hip roll around `+X`
  - `S12`: hip pitch around `+Y`
  - `S13`: knee pitch around local `+Y`
- Positive rotation follows right-hand rule.
- Neutral command baseline remains 90° unless explicit offset/sign mapping overrides it.

### Body Frame Convention (Right-Handed)
- `+X = Forward`
- `+Y = Left`
- `+Z = Up`

### S11 / S12 / S13 Movement Semantics (FR Reference)

| Servo | Joint Type | Axis | Positive Effect |
|---|---|---|---|
| S11 | Hip Roll | +X | Leg moves outward (lateral roll) |
| S12 | Hip Pitch | +Y | Leg swings forward |
| S13 | Knee Pitch | +Y (local) | Knee bends |

### Planar Leg Model (Pitch-Knee Subchain)

```
Hip joint (S12)
  |
  |  L1 (thigh)
  o  Knee joint (S13)
  |
  |  L2 (shank)
  o  Foot
```

Parameters:
- `L1` = thigh length
- `L2` = shank length
- `θ1` = hip pitch (`S12`)
- `θ2` = knee pitch (`S13`)

Forward Kinematics (planar, 2D leg):
- `x = L1*cos(θ1) + L2*cos(θ1 + θ2)`
- `z = L1*sin(θ1) + L2*sin(θ1 + θ2)`

Implementation strategy (best practice):
- Use Three.js hierarchical `Object3D` chain for articulated transforms.
- Apply local joint rotations at each articulation node.
- For rendering transforms, avoid manual world-space trig reconstruction.
- Use explicit FK equations above for debug validation, tolerances, and regression checks.

### Assembly Detail Collection Plan (Kinetics + Physics Fidelity)

Collect and freeze the following physical details before physics-grade tuning:

1. Link geometry and mass properties
- Thigh/shank/hip bracket lengths (`L1`, `L2`, offsets).
- Link masses and estimated COM positions (or measured approximations).
- Principal dimensions affecting inertia assumptions.

2. Joint mechanical constraints
- Hard stop angles (min/max) per servo after assembly.
- Backlash/deadband estimates for each joint.
- Neutral (90° command) real-world pose offset per joint.

3. Servo/electrical behavior impacting motion
- Effective max speed under load (deg/s).
- Command-to-motion latency and update interval.
- Saturation behavior near angle extremes.

4. Contact and support assumptions
- Foot contact points and effective sole geometry.
- Ground condition used for tests (friction proxy assumption).
- Any compliance/flex in links or mounts.

5. Sensor alignment
- IMU mounting orientation relative to body frame (FLU alignment matrix).
- Static bias notes for roll/pitch/yaw baseline.

6. Verification artifacts to store
- Calibration photos per leg and joint zero pose.
- Mapping table: `channel -> joint -> axis -> sign -> offset`.
- Timestamped measurements saved under `DigitalTwin/resources/specs/`.

Collection output requirements:
- Update `resources/specs/robot_specs_template.json` with measured values.
- Update README mapping tables when any physical arrangement differs.
- Re-run `run_phase_verification.py` after each mapping/constraint update.

### AI/Copilot Measurement Feedback Loop (Required in Plan)

To polish the model against real hardware, AI/Copilot must actively request user-provided measurements at each phase gate.

Required behavior:
- At the end of every implementation phase, Copilot asks for missing real-world numbers before marking the phase complete.
- If values are unknown, Copilot requests temporary estimates and tags them as `ASSUMED` until measured.
- Any new measurement must be written back to specs/mapping tables and reflected in revision history.

Mandatory measurement request checklist (Copilot -> User):
1. Link geometry: `L1`, `L2`, hip offsets, foot reference offsets.
2. Joint constraints: min/max hard-stop angles for `S11`, `S12`, `S13`.
3. Zero/calibration offsets: real neutral angle deviation from command 90°.
4. Dynamic behavior: measured servo speed under load (deg/s), delay/latency.
5. IMU alignment: mounting orientation relative to FLU body frame.
6. Contact assumptions: foot contact point and floor condition used for tests.

Suggested Copilot prompt template:
- "Please provide latest measured values for `L1`, `L2`, `S11/S12/S13` limits, neutral offsets, and IMU mounting orientation. If unknown, reply with `ASSUMED` values and confidence level."

Phase-close rule:
- A phase is only `measurement-complete` after user feedback is received (or explicitly marked `ASSUMED`) and synced to `resources/specs/robot_specs_template.json`.

### Measurement Input Form (Fill Per Phase)

Use this table during each phase review. Keep one filled copy per phase in project notes/logs.

| Phase | Parameter | Value | Unit | Source (`MEASURED`/`ASSUMED`) | Confidence (0-100) | Date | Owner | Notes |
|---|---|---|---|---|---:|---|---|---|
| A | `L1` thigh length | 55 | mm | MEASURED | 80 | 2026-02-26 | user | Confirmed directly on robot |
| A | `L2` shank length | 55 | mm | ASSUMED | 70 | 2026-02-26 | copilot | Estimated from assembly drawing scale using confirmed L1 |
| A | Hip offset (body->S11 pivot) | 70 (x), 37.5 (y), 0 (z) | mm | MIXED | 75 | 2026-02-26 | user+copilot | x/y derived from measured FR-RR=140 and FR-FL=75 pivot spans |
| B | `S11` min / max hard-stop | 65 / 180 | deg | MEASURED | 80 | 2026-02-26 | user | Verified safe sweep |
| B | `S12` min / max hard-stop | 0 / 180 | deg | MEASURED | 85 | 2026-02-26 | user | Verified no issue through full range |
| B | `S13` min / max hard-stop | 0 / 180 | deg | MEASURED | 85 | 2026-02-26 | user | Verified no issue through full range |
| C | Neutral offset from 90° (`S11`) | 0 | deg | ASSUMED | 65 | 2026-02-26 | Copilot(provisional) | Provisional assumption frozen per user instruction; replace after calibration support run |
| C | Neutral offset from 90° (`S12`) | 0 | deg | ASSUMED | 65 | 2026-02-26 | Copilot(provisional) | Provisional assumption frozen per user instruction; replace after calibration support run |
| C | Neutral offset from 90° (`S13`) | 0 | deg | ASSUMED | 65 | 2026-02-26 | Copilot(provisional) | Provisional assumption frozen per user instruction; replace after calibration support run |
| D | IMU mounting orientation (FLU relation) | Identity (FLU-aligned) | matrix/euler | ASSUMED | 45 | 2026-02-26 | Copilot(provisional) | Provisional assumption; confirm MPU6050 board orientation physically |
| D | IMU static bias (roll/pitch/yaw) | 0 / 0 / 0 | deg | ASSUMED | 45 | 2026-02-26 | Copilot(provisional) | Provisional assumption; collect static bias on flat surface |
| E | Servo speed under load (`S11/S12/S13`) | 300 | deg/s | ASSUMED | 35 | 2026-02-26 | Copilot(init) | Derived startup value for smooth simulation |
| E | Command-to-motion latency | 35 | ms | ASSUMED | 35 | 2026-02-26 | Copilot(init) | Refine using telemetry timestamp comparison |
| F | Backlash/deadband estimate (`S11/S12/S13`) | 2.0 | deg | ASSUMED | 30 | 2026-02-26 | Copilot(init) | Measure with small-step reversals |
| G | Foot contact point / sole geometry | Point contact, centered at foot tip | text/mm | ASSUMED | 30 | 2026-02-26 | Copilot(init) | Replace with measured contact polygon |
| G | Floor condition used for validation | Flat hard floor, medium friction | text | ASSUMED | 50 | 2026-02-26 | Copilot(init) | Match tutorial recommendation |

Initial baseline note:
- These values are intentionally conservative bootstrap estimates to get simulation running.
- Use failures/drift in `run_phase_verification.py` as triggers to replace ASSUMED values with measured values.

### Top 5 Measurement Priority (Best Improvement per Hour)

1. Leg link lengths and hip offsets (`L1`, `L2`, hip pivot offsets)
- Impact: highest effect on FK/IK trajectory correctness and foot placement error.
- Quick method: caliper measurement on assembled robot, repeat 3 times and average.

2. Per-joint hard-stop limits (`S11`, `S12`, `S13` min/max)
- Impact: prevents unrealistic poses and hardware-risk commands.
- Quick method: manual sweep in calibration/support mode, record first contact point before mechanical stop.

3. Neutral zero offsets from 90° (`S11`, `S12`, `S13`)
- Impact: removes posture bias and straight-walk drift.
- Quick method: set command 90°, place on flat reference, record angular deviation for each joint.

4. IMU mounting orientation and static bias
- Impact: directly affects body-pose correctness (roll/pitch/yaw coupling).
- Quick method: robot fixed on level surface, collect 10-20 s IMU data and compute mean bias.

5. Servo dynamic response (speed under load + command latency)
- Impact: improves motion realism, phase timing, and response matching.
- Quick method: run sweep test with timestamp logs, estimate deg/s and command-to-motion delay.

Apply-after-measurement rule:
- Update `resources/specs/robot_specs_template.json` immediately after each item is measured.
- Re-run `run_phase_verification.py --headless` after each update.
- If gait/posture drift decreases, keep value; otherwise roll back and re-measure.

### First Measurement Session Checklist (30 Minutes, Items #1 + #2)

Printable version:
- `DigitalTwin/docs/MEASUREMENT_BENCH_SHEET.md`

Objective:
- Replace highest-impact assumed values first: geometry (`L1`, `L2`, hip offsets) and joint hard-stop limits (`S11`, `S12`, `S13`).

Prep (3 minutes):
1. Tools: caliper/ruler, marker tape, notebook/phone camera.
2. Robot state: power on, place on flat hard table, run servo neutral so joints are near 90°.
3. Open files ready for updates:
  - `DigitalTwin/resources/specs/robot_specs_template.json`
  - this README measurement form.

Block A — Geometry (`L1`, `L2`, hip offsets) (12 minutes):
1. Measure `L1` (hip-pitch axis center to knee-pitch axis center), 3 repeats.
2. Measure `L2` (knee-pitch axis center to foot reference point), 3 repeats.
3. Measure hip pivot offsets relative to body reference (`x`, `y`, `z`) for FR leg.
4. Compute average for each measurement.
5. Record each value with source=`MEASURED`, confidence, and photo reference.

Block B — Joint hard-stop limits (`S11/S12/S13`) (12 minutes):
1. For each joint, slowly sweep in positive direction until first mechanical resistance.
2. Record max safe angle before hard-stop (leave small safety margin).
3. Sweep in negative direction and record min safe angle.
4. Repeat once to confirm consistency.
5. Record min/max per joint as MEASURED.

Closeout (3 minutes):
1. Update `robot_specs_template.json` with new averages and limits.
2. Re-run quick verification:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase B
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase C
```
3. If result degrades, compare to previous values and re-check measurements with largest variance.

Form completion rules:
- `Source=ASSUMED` requires a follow-up measurement task in `Notes`.
- Any changed value must be synced to `resources/specs/robot_specs_template.json`.
- Keep phase status as `open` until all critical rows for that phase are filled.

### Digital Twin Layer (Browser) Module Arrangement
- Planned module grouping (architecture source-of-truth for implementation):
  - `/core/` -> `SceneManager.js`, `CoordinateSystem.js`, `RobotModel.js`, `ServoModel.js`
  - `/robot/` -> `Body.js`, `Leg_FL.js`, `Leg_FR.js`, `Leg_RL.js`, `Leg_RR.js`
  - `/control/` -> `TelemetryBridge.js`, `IK_Solver.js`, `JointLimit.js`, `SafetyFilter.js`
  - `/debug/` -> `AxisHelperExtended.js`, `FrameVisualizer.js`, `LatencyMonitor.js`

### Physical Fidelity Guardrails
- Do not change channel-to-leg mapping without updating both:
  - runtime mapping code, and
  - this README section.
- Do not change axis sign/offset conventions without regression re-verification.
- If hardware wiring differs from this baseline, record the exact delta in the revision history and update mapping tables before merging.

## Full Coverage of `plan_WebPage_DigitalTwin` (Extended Technical Mapping)

This section ensures all plan sections are explicitly covered and implementation-ready.

1. Executive Objective (Plan §1)
- Fully covered by Goal + UI Priority + Goal Deployment Plan.
- Extended target: deterministic UI+kinematics verification gates, MuJoCo-style operator flow, ROS-aligned frame semantics.

2. System Architecture Overview (Plan §2)
- Runtime split is explicitly enforced:
  - `core`: scene graph, coordinate transforms, model lifecycle.
  - `robot`: body + 4 leg articulation nodes with strict parent-child boundaries.
  - `control`: telemetry ingest, IK, joint-limit filtering, safety checks.
  - `debug`: frame validator, overlays, telemetry diagnostics, latency visibility.
- Contract rule: rendering and IK logic remain decoupled; data crosses modules only through typed runtime payloads.

3. Kinematic Model (Plan §3)
- 13-servo topology and per-leg 3DOF chain are covered with explicit transform-chain constraints.
- Technical constraint: joint updates are local-frame operations only; no global-frame direct rotation mutation.

4. Servo Modeling (Plan §4)
- Servo state model is covered via command mapping + smoothing policy.
- Extended model requirements:
  - `current_deg`, `target_deg`, `max_velocity_deg_per_sec`, `joint_limit_[min,max]`.
  - Discrete update form: `angle_next = angle_now + clamp(target-angle_now, ±(vmax*dt))`.
  - Clamping and saturation state must be externally observable in UI/debug output.

5. ROS 2 Alignment (Plan §5)
- REP-103 style right-handed semantics are covered by FLU body and ENU world checks.
- Extended acceptance: `X × Y = Z` must remain PASS under mode changes and camera operations.

6. MuJoCo-Level Structural Equivalence (Plan §6)
- Covered by UI priority gate and structural hierarchy constraints.
- Extended equivalence points: rigid-link chain, revolute joints, joint limits, local/world transforms, deterministic propagation, and future URDF-friendly abstraction.

7. WebRTC Telemetry Integration (Plan §7)
- Covered by runtime interfaces + telemetry checks; phase plan enforces live ingest validation.
- Extended pipeline contract:
  1) receive packet,
  2) schema/units validation,
  3) `deg -> rad` conversion,
  4) limit/safety filtering,
  5) interpolation (optional),
  6) latency accounting + on-screen status.

8. Inverse Kinematics (Plan §8)
- Covered by IK requirements and Stage 5 implementation flow.
- Extended requirement: explicit unreachable-state output (`clamped`/`unreachable`) with no silent fallback.

9. Safety Layer (Plan §9)
- Covered by Numerical and Safety Constraints + acceptance criteria.
- Extended controls: joint-limit hard stop, velocity bound, optional acceleration bound, and hyperextension prevention behavior.

10. 2D Lightweight Debug Mode (Plan §10)
- Covered by roadmap and build order as fast fallback path.
- Extended requirement: must reuse shared kinematic core so 2D/3D outputs are numerically comparable.

11. Validation Stages (Plan §11)
- Covered by subsystem matrix + phase runner + MuJoCo UI gate.
- Extended stage mapping:
  - static pose, servo sweep, telemetry mirror, IMU orientation, and closed-loop behavior checks.
  - standardized execution via `scripts/run_phase_verification.py` with per-phase PASS/FAIL outputs.

12. Development Roadmap (Plan §12)
- Covered by Goal Deployment Plan (A-G), Ground-Up stages (0-8), and recommended build order.
- Extended readiness rule: phase sign-off requires UI launch + endpoint reachability + automated gate pass.

## Plan-to-Implementation Traceability Matrix

| Plan Section | README Coverage | Verification Script / Gate |
|---|---|---|
| §1 Executive Objective | Goal, UI Priority, Goal Deployment Plan | `test_mujoco_ui_gate_playwright.py`, `run_phase_verification.py` (Phase A/G) |
| §2 System Architecture Overview | Full Coverage mapping §2, Recommended Engineering Layers | `run_phase_verification.py` (Phase F syntax + Phase E regression bundle) |
| §3 Kinematic Model | Kinematic Model, Frame and Transform Chain, Joint Definition | `test_posture_modes_playwright.py`, `test_gait_walk_playwright.py` |
| §4 Servo Modeling (Emax) | Servo Command Mapping Contract, Numerical/Safety Constraints | `smoke_servo_sweep_playwright.py`, `test_mujoco_ui_gate_playwright.py` |
| §5 ROS 2 Alignment | Coordinate Convention, Debug Requirements, Frame checks | `test_imu_feedback_playwright.py`, `test_mujoco_ui_gate_playwright.py` |
| §6 MuJoCo Structural Equivalence | UI Priority, MuJoCo-Style UI Acceptance Checklist | `test_mujoco_ui_gate_playwright.py` |
| §7 WebRTC Telemetry Integration | Runtime Data Interfaces, telemetry pipeline mapping | `test_imu_feedback_playwright.py`, `run_phase_verification.py` (Phase D) |
| §8 Inverse Kinematics | IK Requirements, Stage 5 integration guide | `test_posture_modes_playwright.py`, `test_gait_walk_playwright.py` |
| §9 Safety Layer | Numerical and Safety Constraints, acceptance criteria | `test_mujoco_ui_gate_playwright.py` (visible failure states), `smoke_servo_sweep_playwright.py` |
| §10 2D Lightweight Debug Mode | Phase Roadmap + Recommended Build Order + Stage roadmap | `run_phase_verification.py` process gate (phase sign-off discipline) |
| §11 Validation Stages | Subsystem Test Matrix, MuJoCo UI gate, phase automation | `run_phase_verification.py` (A→G full run) |
| §12 Development Roadmap | Goal Deployment Plan, Ground-Up stages 0–8, checklists | `run_phase_verification.py` + manual Safari verification path |

Audit use:
- Treat each row as complete only when the mapped script exits `0` and phase summary is PASS.
- For release readiness, require `run_phase_verification.py --headless` summary `pass: 7` and `fail: 0`.

## Integrated 3DOF Emulation Plan

### Target Capabilities
- Full 3D engineering model with coordinate/axis debug.
- WebRTC/live digital-twin angle injection.
- Inverse kinematics (IK) solver path.
- Exportable module architecture for ClientAI integration.
- Lightweight 2D debug mode for fast math verification.
- ROS-aligned coordinate conventions.

### Coordinate Convention (Source of Truth)
- Body frame: right-handed FLU (`+X forward`, `+Y left`, `+Z up`).
- World frame: right-handed ENU.
- Keep the same convention across all runtime modes.

### Kinematic Model (Per-Leg 3DOF)
- Model type: serial chain with three revolute joints per leg.
- Joint order: `q1 = hip_roll (S11)`, `q2 = hip_pitch (S12)`, `q3 = knee_pitch (S13)`.
- Link lengths:
  - `L1`: hip lateral offset to pitch plane
  - `L2`: upper leg (thigh)
  - `L3`: lower leg (shank)
- Required source of dimensions: `resources/specs/robot_specs_template.json`.
- Neutral command baseline: 90° servo command (mapped to model zero or configured offset).

### Frame and Transform Chain
- Canonical transform chain (FR leg):
  - `T_world_hip * R_x(q1) * T_hip_to_pitch * R_y(q2) * T_thigh * R_y(q3) * T_shank`
- Rotation direction must follow right-hand rule around each joint local axis.
- Each joint only rotates descendants (strict parent-child isolation).

### Forward Kinematics (FK) Requirements
- Given `{q1, q2, q3}`, compute foot position `p_foot = (x, y, z)` in body frame.
- Planar reduced form for pitch/knee plane:
  - `x_p = L2*cos(q2) + L3*cos(q2+q3)`
  - `z_p = L2*sin(q2) + L3*sin(q2+q3)`
- Hip roll projection to full 3D must preserve FLU sign conventions.
- Runtime must expose current FK foot position in debug output.

### Inverse Kinematics (IK) Requirements
- Input: target foot point `(x, y, z)` in body frame.
- Step 1: solve `q1` from lateral projection (hip roll plane alignment).
- Step 2: reduce to 2D pitch-knee plane (`r` distance to hip-pitch origin).
- Step 3: law-of-cosines for knee:
  - `cos(q3) = (r^2 - L2^2 - L3^2) / (2*L2*L3)` (clamped to `[-1, 1]`).
- Step 4: solve hip pitch:
  - `q2 = atan2(z_p, x_p) - atan2(L3*sin(q3), L2 + L3*cos(q3))`.
- Step 5: enforce joint limits and report saturation state.

### Servo Command Mapping Contract
- Model angles (rad) and servo commands (deg) must be explicitly mapped by:
  - `servo_deg = offset_deg + sign * rad2deg(q_joint)`.
- Mapping table and signs must be documented per channel in implementation code.
- Mandatory FR mapping baseline used in this workspace:
  - `S11 -> hip_roll`, `S12 -> hip_pitch`, `S13 -> knee_pitch`.

### Runtime Data Interfaces
- Live servo packet (minimum contract):
```json
{
  "S11": 12.5,
  "S12": -20.3,
  "S13": 44.0,
  "timestamp": 12345678
}
```
- IMU packet (minimum contract):
```json
{
  "roll": 1.2,
  "pitch": -3.4,
  "yaw": 178.9,
  "timestamp": 12345679
}
```
- All angle units must be explicitly stated at API boundaries (`deg` vs `rad`).

### Numerical and Safety Constraints
- Joint limit enforcement required before render/apply.
- IK unreachable targets must return deterministic status (`clamped` or `unreachable`) rather than silent failure.
- Angle update smoothing must be optional and bounded to avoid unstable lag.
- Default update behavior must be deterministic for headless test runs.

### Joint Definition (FR Leg Baseline)
- `S11`: hip roll, axis `+X`, vector `(1, 0, 0)`.
- `S12`: hip pitch, axis `+Y`, vector `(0, 1, 0)`.
- `S13`: knee pitch, axis `+Y` (thigh-local frame).
- Positive rotation follows right-hand rule.

### Phase Roadmap
1. **Phase 1: 3D Engineering Foundation**
  - Build hierarchical scene graph (`RobotRoot -> BodyFrame -> Leg -> S11 -> S12 -> S13`).
  - Add visible local/world axes and verify right-hand-rule behavior.
2. **Phase 2: WebRTC Digital Twin Runtime**
  - Receive live servo commands (JSON), convert `deg -> rad`, apply to joints.
  - Add optional interpolation and latency instrumentation.
3. **Phase 3: IK Solver Layer**
  - Input target foot `(x, y, z)`.
  - Compute hip yaw from lateral displacement.
  - Reduce to planar problem and solve hip/knee with law-of-cosines.
  - Enforce joint limits before apply.
4. **Phase 4: Lightweight 2D Debug Mode**
  - Canvas-only leg visualization (thigh/shank, angles, trajectory).
  - Use as fast fallback without WebGL dependency.
5. **Phase 5: Exportable Module Refactor**
  - Planned module split:
    - `modules/Leg3DOF.js`
    - `modules/IKSolver.js`
    - `modules/CoordinateDebug.js`

### Debug Requirements
- Display world frame axes and local joint axes.
- Show foot world coordinates.
- Provide visibility toggles for coordinate overlays.
- Keep console-level verification outputs for CI/smoke tests.

### Engineering Acceptance Criteria
- Coordinate validation:
  - Frame check displays PASS for right-hand-rule and FLU/ENU conventions.
- Kinematic correctness:
  - FK output changes consistently with signed joint commands.
  - IK solution reproduces target pose within defined tolerance (recommendation: <= 5 mm in test geometry).
- Command mapping:
  - Channel-to-joint mapping is traceable and consistent across visual mode and tests.
- Regression checks:
  - `test_mujoco_ui_gate_playwright.py` passes.
  - `smoke_servo_sweep_playwright.py` passes.
  - `test_posture_modes_playwright.py` passes.
  - `test_gait_walk_playwright.py` passes.
  - `test_imu_feedback_playwright.py` passes.

### MuJoCo-Style UI Acceptance Checklist (Priority Gate)
Use this as the mandatory PASS/FAIL gate before phase sign-off.

- Viewport and camera controls:
  - Orbit, pan, and zoom are smooth and deterministic under repeated input.
  - Body frame and world frame remain visually consistent after camera reset.
- Joint control panel behavior:
  - Slider/input changes update the expected joint only (no sibling leakage).
  - UI value and rendered joint state remain synchronized with no stale display.
- Telemetry and diagnostics:
  - Live pose/angles/foot-position text updates every frame cycle.
  - `Frame PASS` status is visible and remains stable during posture/gait transitions.
- Runtime mode switching:
  - Manual, posture, gait, and IMU-driven states switch without UI freeze or desync.
  - Current mode label always matches active control authority.
- Determinism and replay:
  - Running the same command sequence twice yields equivalent sampled UI telemetry.
  - No non-deterministic joint jump on startup or mode change.
- Failure visibility:
  - Invalid IK target or out-of-range command surfaces explicit UI status (`clamped`/`unreachable`).
  - Error states are visible without opening browser developer tools.
- Regression coupling:
  - UI text/selectors required by Playwright tests are stable across updates.
  - All four baseline scripts pass after UI changes.

### Recommended Build Order
1. 3D engineering skeleton.
2. Axis/coordinate debug verification.
3. Live angle injection path.
4. IK integration.
5. Module export refactor.
6. 2D fallback implementation.

## Recommended Engineering Layers
1. Kinematic Layer
- Define per-leg 3DOF chain (`hip_roll`, `hip_pitch`, `knee_pitch`).
- Keep neutral pose at 90 deg command unless channel override exists.
- Preserve known mapping semantics (e.g., FR: S11/S12/S13).

2. Motion Layer
- Posture modes: Relax 90, Stand, Tilt tests.
- Gait modes: walk cycle with phase offsets.
- Servo test mode: single/multi-channel sweep with speed control.

3. Sensor Layer
- IMU stream normalization to twin convention:
  - world: ENU
  - body: FLU
- Apply roll/pitch/yaw to digital body frame with clear axis notes.

4. Validation Layer
- Automated smoke tests (Playwright).
- Visual checks in Safari/local page.
- Per-servo axis-direction verification and range checks.

## Subsystem Test Matrix
- `scripts/run_phase_verification.py`
  - Runs phased verification end-to-end with maximum automation: checks HTTP reachability, launches real UI in Safari before each phase, runs mapped checks, and prints PASS/FAIL status after every phase.
- `scripts/test_mujoco_ui_gate_playwright.py`
  - Verifies MuJoCo-style UI priority gate: required UI selectors, telemetry/frame stability after viewport interaction, mode-switch determinism, and visible error-state status.
- `scripts/smoke_servo_sweep_playwright.py`
  - Verifies smooth servo stepping and status behavior.
- `scripts/test_posture_modes_playwright.py`
  - Verifies Walk/RELAX/S11 mode transitions and S11-only swing isolation.
- `scripts/test_gait_walk_playwright.py`
  - Verifies Walk full-leg dynamics: roll (`S11,S8,S7,S4`) and pitch/knee channels move with non-zero ranges.
- `scripts/test_imu_feedback_playwright.py`
  - Verifies frame PASS and numeric `Pose ENU XYZ | FLU RPY` feedback text.
- `scripts/line_messaging_api.py`
  - Sends status notifications using LINE Messaging API (`push`/`broadcast`) and supports token validation.
- `scripts/p1_calibration_update.py`
  - Syncs P1 calibration values (neutral offsets + IMU mount/bias) to JSON+CSV in one command and can run phase C/D live verification.
- `scripts/test_servo_axis_direction_playwright.py`
  - Verifies isolated channel movement and start-direction monotonicity for S11/S12/S13 in Servo Test mode.
- `scripts/p2_sim_estimate_and_update.py`
  - Estimates servo speed/latency/backlash from DigitalTwin simulation, updates JSON+CSV with `SIMULATED` provenance, and can run Phase E verification.

## Beginner Workflow Tutorial
1. Prepare environment
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code
python3 -c "import playwright; print('playwright ok')"
```
If needed:
```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

2. Fill real hardware specs
- Open `resources/specs/robot_specs_template.json`.
- Enter measured dimensions from hardware/tutorial.
- Keep units in millimeters and angles in degrees.

3. Run Digital Twin checks
```bash
python3 DigitalTwin/scripts/smoke_servo_sweep_playwright.py --headless
python3 DigitalTwin/scripts/test_posture_modes_playwright.py --headless
python3 DigitalTwin/scripts/test_gait_walk_playwright.py --headless
python3 DigitalTwin/scripts/test_imu_feedback_playwright.py --headless
python3 DigitalTwin/scripts/test_mujoco_ui_gate_playwright.py --headless
```

4. Run maximum-automation phased verification (recommended)
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless
```
- This launches the real UI in Safari before each phase and prints phase-by-phase status.
- Use one phase only when debugging:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase C
```

5. Optional: send LINE status message
```bash
cp DigitalTwin/resources/line_messaging.env.example /tmp/line_messaging.env

# Fill token + recipient in /tmp/line_messaging.env, then:
python3 DigitalTwin/scripts/line_messaging_api.py --env-file /tmp/line_messaging.env --validate-only
python3 DigitalTwin/scripts/line_messaging_api.py --env-file /tmp/line_messaging.env --text "DigitalTwin checks PASS"
```

6. Optional: apply P1 calibration update and verify C/D in one step
```bash
python3 DigitalTwin/scripts/p1_calibration_update.py \
  --neutral-s11 0 --neutral-s12 0 --neutral-s13 0 \
  --neutral-source ASSUMED --neutral-confidence 65 \
  --imu-mount-roll 0 --imu-mount-pitch 0 --imu-mount-yaw 0 \
  --imu-bias-roll 0 --imu-bias-pitch 0 --imu-bias-yaw 0 \
  --imu-source ASSUMED --imu-confidence 45 \
  --apply --verify --headless
```

7. Optional: apply P2 simulated dynamics update and verify E
```bash
python3 DigitalTwin/scripts/p2_sim_estimate_and_update.py --headless --apply --verify
```

8. Launch resilient local page host with watchdog (recommended)
```bash
python3 DigitalTwin/scripts/digitaltwin_dev_server.py --host 127.0.0.1 --port 8766 --pi-host 192.168.0.32 --notify
```

9. Open visual page for manual confirmation
```bash
open -a Safari http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html
```

10. Record evidence
- Save terminal output and screenshots to `logs/`.
- Include tested channels/modes and threshold checks.

## Ground-Up Implementation Guide (Beginner -> Engineering)

This section is the **practical build manual** for implementing the Digital Twin from zero.
If you are new to robotics simulation, follow each stage in order and do not skip validation gates.

### Stage 0: Project Setup and Mental Model

Objective:
- Understand what the twin is expected to do before writing math or rendering code.

What to prepare:
- A browser that can run ES modules.
- Python + Playwright test tooling.
- The canonical workspace paths:
  - `DigitalTwin/pages/`
  - `DigitalTwin/scripts/`
  - `DigitalTwin/resources/specs/`

Deliverable:
- You can open the page and run all four baseline test scripts.

Validation gate:
- All scripts execute (pass/fail allowed initially), and no path-not-found errors occur.

---

### Stage 1: Define Mechanical Parameters Before Coding

Objective:
- Freeze naming and dimensions so code and math share the same assumptions.

Tasks:
1. Fill `resources/specs/robot_specs_template.json` with measured dimensions.
2. Confirm channel-to-joint mapping for each leg.
3. Confirm sign conventions (`+` direction for each joint).

Beginner note:
- Most simulation bugs are not math mistakes; they are **wrong axis/sign/offset assumptions**.

Deliverable:
- A completed spec file with link lengths and mapping values.

Validation gate:
- Team can answer: “For `S11`, positive command rotates around which axis and in what direction?”

---

### Stage 2: Build Scene Graph Skeleton (No IK Yet)

Objective:
- Create a correct parent-child transform hierarchy.

Tasks:
1. Build nodes: body -> leg root -> `S11` -> `S12` -> `S13` -> foot marker.
2. Attach visual axis helpers at body and each joint.
3. Add a static neutral pose (all at 90° command equivalent).

Deliverable:
- 3D model renders with visible axes and stable neutral pose.

Validation gate:
- Rotating `S11` only should not directly rotate siblings; only descendants move.

---

### Stage 3: Servo Command Injection Path

Objective:
- Make the twin respond to external angle commands.

Tasks:
1. Implement JSON command ingest (`S11/S12/S13/timestamp`).
2. Convert degrees to radians.
3. Apply mapping formula (`offset + sign * angle`).
4. Add optional interpolation/smoothing.

Deliverable:
- Given command packets, joint motion is deterministic and traceable.

Validation gate:
- Replaying the same command sequence twice produces identical sampled outputs.

---

### Stage 4: Forward Kinematics Debug Outputs

Objective:
- Verify geometry and transform logic through computed foot position.

Tasks:
1. Compute foot position from current joint angles.
2. Display the position in UI/debug output.
3. Compare observed trajectory against expected motion shape.

Deliverable:
- Live `p_foot(x,y,z)` debug output tied to joint movement.

Validation gate:
- Small angle changes produce smooth and physically plausible foot movement.

---

### Stage 5: Inverse Kinematics Solver Integration

Objective:
- Compute joint angles from a target foot coordinate.

Tasks:
1. Implement target validation (reachable workspace check).
2. Solve `q1` from lateral component.
3. Solve planar `q2/q3` using law-of-cosines.
4. Enforce joint limits and emit saturation status.
5. Feed solved angles back to command path.

Deliverable:
- Setting foot target updates joints automatically.

Validation gate:
- For known test targets, IK->FK round-trip error stays within tolerance.

---

### Stage 6: Sensor Fusion and Body Pose Coupling

Objective:
- Integrate IMU orientation and keep frame semantics correct.

Tasks:
1. Ingest roll/pitch/yaw stream.
2. Apply pose to body frame (not to world frame axes).
3. Keep ENU/FLU mapping explicit in code comments and UI.

Deliverable:
- Body orientation tracks IMU while leg kinematics remain consistent.

Validation gate:
- `frameCheck` stays PASS and no axis inversion appears during pose sweeps.

---

### Stage 7: Regression Test Hardening

Objective:
- Convert manual checks into repeatable automation.

Tasks:
1. Keep smoke + posture + gait + imu scripts up-to-date with current UI.
2. Add pass/fail thresholds for ranges, text patterns, and mode states.
3. Store run logs in `logs/` with timestamped files.

Deliverable:
- One-command regression confidence for every major change.

Validation gate:
- All four scripts pass on clean state.

---

### Stage 8: Module Refactor for Reuse

Objective:
- Separate rendering, kinematics, and integration logic.

Target split:
- `Leg3DOF.js`: joint graph + FK path.
- `IKSolver.js`: inverse solver + limits.
- `CoordinateDebug.js`: axes/labels/diagnostics.

Deliverable:
- Clean interfaces, lower coupling, easier testing.

Validation gate:
- Refactor does not change regression outputs.

## Practical Troubleshooting Flow

When behavior is wrong, debug in this order:
1. **Frame mismatch**: verify ENU/FLU and right-hand-rule assumptions.
2. **Mapping mismatch**: verify servo channel, sign, and offset.
3. **Geometry mismatch**: verify `L1/L2/L3` and link anchor positions.
4. **Solver mismatch**: verify IK clamping and angle branch selection.
5. **UI/runtime mismatch**: verify displayed mode equals applied mode.

Rule of thumb:
- If the model “looks mirrored,” suspect axis/sign mapping first.
- If the model “moves but misses target,” suspect dimensions or IK branch.

## Minimum Engineering Checklist (Before Merge)

- Specs file is filled and reviewed.
- Channel mapping table is explicitly documented.
- FK debug output is visible and stable.
- IK handles unreachable targets gracefully.
- Frame check remains PASS under posture changes.
- All Playwright regression scripts pass.
- MuJoCo-style UI priority gate script passes (`test_mujoco_ui_gate_playwright.py`).
- README and code comments use the same coordinate vocabulary.

## Next Development Tasks
- Geometry binding queue (active):
  1) Keep body/hip/leg lengths tied to measured spec values (`180/110/85`, `L1/L2=55`, `hip offsets 70/37.5`) and verify visual alignment.
  2) Continue CAD-proportion polish for head/neck/tail and servo shell placement against side-view references.
  3) Add spec-driven geometry debug HUD (`mm` + scene-unit derived values) for fast operator checks.
  4) Re-run Phase C/E gates after each geometry batch and keep log snapshots for handoff.
- Replace `SIMULATED` P2 values with real hardware measurements (speed, latency, backlash) and re-verify phase E.
- Add IMU playback test data and expected orientation snapshots.
- Add one summary exporter that compiles all phase logs into a single report file.


## Revision History
- 2026-02-28 12:33 v1.74 - Relocated folder from `Code/Test/DigitalTwin/` to `Code/DigitalTwin/`; updated all internal/external path references, Python parent-index logic, and URL strings across ~36 files.
- 2026-02-28 11:57 v1.73 - Added GAIT debug HAA assembly visualization with highlighted white top-right rotating shaft and HAA tooltip helper; re-verified full phase regression PASS (`pass=7`, `fail=0`).

## Older Revision History
- 2026-02-28 11:23 v1.71 - Added GAIT debug servo annotations (`HFE`/`KFE`) and mouse-hover tooltip helper so each yellow servo marker reports leg/joint context directly in-panel.
- 2026-02-28 11:23 v1.70 - Refined GAIT debug servo/link relationship: servo glyph shafts are centered in their bodies, servo bodies are offset to the inner side of thigh/shank links, and link plates are rendered translucent for clearer side-view mounting interpretation.
- 2026-02-28 11:21 v1.69 - Updated GAIT debug leg geometry to Freenove-like side-view link profile (upper/lower links now render as plate-style shapes with broad joint ends and narrower mid-sections) for clearer visual match to reference side view.
- 2026-02-28 11:04 v1.68 - Updated GAIT debug servo markers for visibility tuning: servo rectangles are now 2x larger and use high-contrast yellow/dark styling for clearer leg-joint inspection.
- 2026-02-28 11:00 v1.67 - Enhanced GAIT debug side panel glyph clarity: added explicit joint circles plus small servo-rectangle markers aligned with upper/lower link orientation, and kept panel axis labeling in dog-frame `X/Z`.
- 2026-02-28 10:47 v1.66 - Updated GAIT debug panel projection semantics to dog-frame local `X/Z` (instead of world-projected axes) so side-view debug geometry remains correct during body yaw rotation; relabeled panel axis text accordingly.
- 2026-02-28 07:50 v1.65 - Added transparent torso COM-inspection rendering and enhanced body COM marker visibility (core marker) in the Digital Twin page.
- 2026-02-27 20:48 v1.64 - Applied runtime hotfix pass for user-reported issues: corrected servo rig axis mapping (`S12/S13`), restored FOLLOW zoom-size adjustment via wheel follow-distance control, refreshed UI screenshots, and reconfirmed full regression clean (`pass=7 fail=0`).
- 2026-02-27 20:18 v1.63 - Completed post-success extension cycle: added camera/servo module extraction (`CameraManager.js`, `ServoHierarchy.js`), advanced camera mode coverage (`FPV/HORIZON/TOPDOWN`), updated extension artifacts (`ext1-ext8`), and reconfirmed full regression clean (`pass=7 fail=0`).
- 2026-02-27 19:58 v1.62 - Added v2.00 camera-mode/world-invariance upgrade section, recorded clean full regression (`pass=7 fail=0`), and linked autonomous extension audit artifacts under `iCloud/AI_Reports`.
- 2026-02-26 19:07 v1.59 - Fixed UI overlap in render page by switching left-side panels to dynamic stack layout (HUD -> mode controls -> Servo Test), plus viewport-safe servo-dock height handling.
- 2026-02-26 19:01 v1.58 - Added top-level new-user `Quick Start (Launch Page First)` section with explicit host/verify/open steps and basic troubleshooting.
- 2026-02-26 13:40 v1.57 - Added `Apply IMU` checkbox with default OFF so IMU telemetry can be monitored without rotating the model; this aligns operator expectation that pitch=0 should appear level unless IMU application is enabled.
- 2026-02-26 18:22 v1.56 - Added explicit `File Hierarchy and Related Files` section with structure tree, key file roles, and update-sync guidance for faster agent/operator onboarding.
- 2026-02-26 13:40 v1.55 - Added gait timing correction record: reduced stance ratio and increased lateral continuous-wave contribution to avoid rear-leg low-motion windows and improve whole-cycle walk consistency.
- 2026-02-26 13:40 v1.54 - Added follow-up gait calibration note: increased lateral/cadence slightly after deep retune to ensure roll-channel movement margins remain above validation thresholds without reintroducing crab-like motion.
- 2026-02-26 13:40 v1.53 - Deep gait-correction update: raised stance ratio, reduced cadence/lateral coupling, and softened stance vertical compliance to reduce crab-like/jerky walk artifacts while keeping axis validation behavior.
- 2026-02-26 13:20 v1.52 - Added resilient local-host recovery workflow for parallel-agent contention: introduced `digitaltwin_dev_server.py` watchdog host (`127.0.0.1:8766`) with IMU proxy plus local recovery endpoint, and documented the new HTTP launch path for manual Safari validation.
- 2026-02-26 13:20 v1.51 - Added note for default-ON Servo Test operator flow: top button now keeps panel ON for stable per-servo verification (avoids accidental disable during test setup).
- 2026-02-26 13:20 v1.50 - Updated Servo Test UX defaults and readability: panel starts ON by default and channel labels now use stacked name/angle layout with increased spacing to prevent overlap.
- 2026-02-26 13:07 v1.49 - Fixed `Geom Bind` HUD initialization order to prevent early DOM reference during script startup; frame/pose runtime checks are restored.
- 2026-02-26 13:07 v1.48 - Added live HUD geometry-binding readout (`Geom Bind`) so operators can confirm the active measured mm baseline directly on the render page.
- 2026-02-26 13:07 v1.47 - Added active geometry-binding queue and recorded measured-spec proportion binding for body/leg/hip geometry updates in the DigitalTwin 3D model.
- 2026-02-26 12:55 v1.46 - Logged walk-cadence increase for verification robustness so all roll channels are exercised within standard gait-test sample windows.
- 2026-02-26 12:55 v1.45 - Recorded IK lateral-excursion increase for walk-mode verification so commanded roll channels produce measurable range in gait tests.
- 2026-02-26 12:55 v1.44 - Added full-cycle lateral gait modulation note (`latWave`) to keep hip-roll channels active during verification windows and avoid swing-only roll dead zones.
- 2026-02-26 12:55 v1.43 - Logged gait-regression recovery tuning: raised roll/lateral dynamics after automated walk test to keep roll-channel motion above validation threshold while preserving 4-beat walk sequencing.
- 2026-02-26 12:55 v1.42 - Updated gait-improvement record: walk mode now uses a 4-beat phase sequence (`FR->RR->FL->RL`) plus light stance-height compliance for less rigid/trot-like visual behavior.
- 2026-02-26 12:47 v1.41 - Documented live Servo Test angle labels (`Sx (deg)` readout for each channel, unsupported channels show `--`) and additional gait softening pass for smoother walk verification.
- 2026-02-26 12:25 v1.40 - Updated Servo Test selector layout to fixed row grouping for operator checks: `S2,S3,S4,S11,S12,S13` and `S5,S6,S7,S8,S9,S10`.
- 2026-02-26 12:19 v1.39 - Rebalanced gait tuning after validation: slightly increased lateral/roll dynamics to recover full roll-channel movement while keeping improved smoothness.
- 2026-02-26 21:23 v1.60 - Added pre-MuJoCo HIL stability gate coverage: deterministic fixed-step runtime, support-polygon/COM margin workflow references, contact sanity checks, IMU divergence report hooks, and beginner-safe usage steps for the new gate document.
- 2026-02-26 21:48 v1.61 - Added overnight HIL upgrade record for deterministic `dt=0.01` stepping, diagonal gait parity, enhanced stability/contact/IMU gates, and CI artifact output (`HIL_Test_Report.json`) documentation.
- 2026-02-26 12:19 v1.38 - Performed another walk-gait refinement pass (stride/cadence/roll/lateral coupling and turn bias tuning) plus subtle body bob in walk mode for improved natural motion.
- 2026-02-26 11:46 v1.37 - Fixed Servo Test neutral-angle mapping so 90deg per-channel visualization matches Relax neutral posture baseline, specifically correcting knee-channel behavior (S13/S10 at 90deg).
- 2026-02-26 11:46 v1.36 - Added Dog Controls `Demo` button and local runner sequence aligned to `Server/Action.py` demo order with per-step cue emulation and auto stop/relax completion behavior.
- 2026-02-26 11:46 v1.35 - Prioritized walk-gait stabilization with smoother stance/swing continuity and reduced lateral coupling to address weird gait artifacts.
- 2026-02-26 11:41 v1.34 - Added follow-camera behavior for Dog Controls translation actions so the viewport tracks dog position and avoids walking out of frame during local simulation.
- 2026-02-26 11:33 v1.34 - Added Dog Controls emulation panel in DigitalTwin page and mapped action buttons to local motion/yaw simulation states (turn, forward/backward, left/right, relax/stop, beep/LED indicators).
- 2026-02-26 11:29 v1.33 - Updated walk-gait method to stance/swing phase trajectory with reduced lateral-roll coupling for improved local DigitalTwin gait naturalness and stability.
- 2026-02-26 11:21 v1.32 - Documented IMU telemetry overlay behavior in the Digital Twin viewport and clarified that live roll/pitch/yaw now drive body quaternion orientation in the main 3D scene.
- 2026-02-26 11:14 v1.31 - Added P2 simulation-estimation workflow (`p2_sim_estimate_and_update.py`), updated tutorial steps, and marked next tasks toward replacing SIMULATED values with measured hardware data.
- 2026-02-26 10:54 v1.30 - Added `test_servo_axis_direction_playwright.py` to subsystem matrix for per-servo direction/isolation compliance checks.
- 2026-02-26 10:50 v1.29 - Added `p1_calibration_update.py` to subsystem matrix and workflow (single-command JSON/CSV sync + phase C/D live verification).
- 2026-02-26 10:34 v1.28 - Added direct handoff relay section pointing to `handoff_TaskList.md` and aligned version metadata for operator continuity.
- 2026-02-28 11:51 v1.72 - Added Coordinate Systems Tutorial section with 3-frame mapping table, side-view projection explanation, launch steps, and link to interactive 3D tutorial page (`tutorial_coordinate_systems.html`).
- 2026-02-26 10:29 v1.27 - Applied provisional assumed values for Phase C/D (neutral offsets and IMU mount/bias), synced JSON/CSV/README, and advanced to next-step validation workflow.
- 2026-02-26 10:12 v1.26 - Synced live measurement updates: set S12/S13 limits to measured 0/180, refreshed measurement table with latest measured/derived values, and aligned current baseline entries.
- 2026-02-26 10:04 v1.25 - Added LINE Messaging API sender workflow (`line_messaging_api.py`) and env-template usage in beginner tutorial.
- 2026-02-26 09:32 v1.24 - Added printable bench-sheet reference for first measurement session and linked to `DigitalTwin/docs/MEASUREMENT_BENCH_SHEET.md`.
- 2026-02-26 09:31 v1.23 - Added concrete 30-minute first measurement session checklist focused on top-priority geometry and hard-stop limit capture, including immediate post-measurement verification commands.
- 2026-02-26 09:30 v1.22 - Updated gait validation semantics to full 3-DOF walk dynamics (roll channels no longer fixed at 90deg).
- 2026-02-26 09:29 v1.21 - Added a prioritized Top-5 measurement order (impact-first) with quick acquisition methods to accelerate replacement of ASSUMED values.
- 2026-02-26 09:16 v1.20 - Filled initial ASSUMED baseline numbers for the measurement form and set explicit bootstrap tuning policy for replacing values with measured data after verification failures.
- 2026-02-26 09:13 v1.19 - Added a structured phase-by-phase measurement input form (value/unit/source/confidence/owner) and completion rules for Copilot-driven real-world feedback collection.
- 2026-02-26 09:12 v1.18 - Added mandatory AI/Copilot measurement-feedback loop to the plan, requiring user-provided real-world numbers (or explicit ASSUMED values) at each phase gate to polish model fidelity.
- 2026-02-26 09:10 v1.17 - Added organized assembly-detail collection plan for kinetics/physics fidelity, explicit body-frame convention, S11/S12/S13 movement table, planar leg model, and forward-kinematics equations.
- 2026-02-26 09:04 v1.16 - Restored and expanded critical hardware/physical arrangement details (physical layer inventory, 13-servo topology, leg/channel grouping, joint-axis semantics, and module architecture inventory) to preserve Digital Twin fidelity requirements.
- 2026-02-26 08:57 v1.15 - Added audit-ready Plan-to-Implementation Traceability Matrix mapping all 12 plan sections to concrete README coverage and executable verification gates.
- 2026-02-26 08:55 v1.14 - Added explicit 12-section full coverage mapping for `plan_WebPage_DigitalTwin` with extended technical contracts, architecture boundaries, servo-state model, telemetry pipeline, and verification-stage alignment.
- 2026-02-26 08:50 v1.13 - Added maximum-automation phase verification workflow documentation using `run_phase_verification.py`, including per-phase status reporting with real Safari UI launch.
- 2026-02-26 08:50 v1.12 - Added executable MuJoCo-style UI priority gate integration to the test flow and documented the new Playwright command and pass requirement.
- 2026-02-26 08:48 v1.11 - Added a concrete MuJoCo-style UI acceptance checklist with explicit PASS/FAIL gates for controls, telemetry, mode switching, determinism, and regression sign-off.
- 2026-02-26 08:47 v1.10 - Prioritized MuJoCo-style UI in the project goal and made phase execution explicitly UI-first for implementation sign-off.
- 2026-02-26 08:46 v1.9 - Moved Revision History from the top header block to this end-of-file section.
- 2026-02-26 08:46 v1.8 - Added a goal-aligned all-phases deployment plan with execution order, deliverables, and exit gates for implementation.
- 2026-02-26 08:45 v1.7 - Elevated the project goal to a professional-grade local Digital Twin target, explicitly aligned to MuJoCo/ROS 2-level engineering quality and verification discipline.
- 2026-02-26 08:43 v1.6 - Expanded this README into a beginner-friendly, engineering-level ground-up implementation guide with staged build milestones, coding order, validation gates, and troubleshooting workflow.
- 2026-02-26 08:42 v1.5 - Added detailed engineering specification sections (kinematic model, FK/IK equations, interface contracts, constraints, and validation acceptance criteria) to make this README implementation-complete.
- 2026-02-26 08:38 v1.4 - Merged WebPage 3DOF leg-emulation plan into this README (phase roadmap, IK/module strategy, debug requirements, and build order) for single-source DigitalTwin implementation guidance.
- 2026-02-26 08:33 v1.3 - Finalized folder reorganization to a single workspace `Code/DigitalTwin`; updated command and page paths accordingly.
- 2026-02-26 10:08 v1.2 - Updated Digital Twin workspace paths to `test/WebAnimation` and switched local Safari page path to `DigitalTwin/pages/freenove_robotdog_3d_render.html`.
- 2026-02-26 08:21 v1.1 - Added subsystem test matrix and command examples for posture, gait, and IMU verification scripts.
- 2026-02-26 08:13 v1.0 - Added Digital Twin architecture/tutorial for local Pi Robot Dog emulation including Freenove refs, Emax ES08MA II specs template, posture/gait/IMU verification flow.
