<!--
File: Documents/planHIL_DogMovement.md
Description:
  Tutorial-level phased roadmap for upgrading the Robot Dog DigitalTwin + HIL
  movement pipeline from kinematics to deterministic pseudo-physics and
  optional rigid-body co-simulation, with quantitative verification gates.
Usage:
  1) Use as the implementation and review checklist for Phases 0..7.
  2) Track pass/fail against defined metrics before promoting backend changes.
  3) Apply Go/No-Go checklist prior to rigid-body simulation migration.
Version: v1.1 (2026-03-02 09:09 CST)
Revision History:
- 2026-03-02 09:09 v1.1 - Added professional header/version metadata block to satisfy document governance rule.
- 2026-03-02 00:00 v1.0 - Initial roadmap draft with phases, decision matrix, architecture, and verification criteria.
-->

# Quadruped DigitalTwin + HIL Movement/Physics Roadmap (Phases 0–7)

## 1) Mission and Constraints

This roadmap upgrades movement realism in controlled stages while keeping your current DigitalTwin workflow stable.

### Non-negotiables
- Deterministic-first: same input log => identical pose outputs.
- Backward-compatible UI/debug contracts (no breaking existing consumers).
- Quantitative gates at every phase (timing, contact, stability, correlation).
- Promotion only through explicit Go/No-Go checks.

---

## 2) Current Pipeline Mapping (as-is)

### Core runtime
- Main movement/runtime page: `DigitalTwin/pages/freenove_robotdog_3d_render.html`
- Reference architecture/docs: `DigitalTwin/README_DigitalTwin.md`
- HIL gate semantics: `DigitalTwin/docs/HIL_Stability_Gates.md`

### Existing movement flow (today)
1. Mode/action intent (Walk/Relax/S11/Demo/Servo test)
2. Per-leg gait math + servo command generation
3. Servo-to-visual mapping for leg joints
4. Body/root update (pose + action offsets + IMU)
5. HIL checks (support/contact/clearance/margin/divergence)
6. HUD/debug export via window debug API

### Existing HIL hooks already usable
- Servo telemetry and per-channel state via debug getters
- IMU telemetry and apply toggle path
- Tick/timestamp style fields in HIL report payloads
- Contact/stability counters (anti-skate, swing-clear, penetration, margin)
- Playwright verification scripts:
  - `DigitalTwin/scripts/test_gait_walk_playwright.py`
  - `DigitalTwin/scripts/test_posture_modes_playwright.py`
  - `DigitalTwin/scripts/test_imu_feedback_playwright.py`
  - `DigitalTwin/scripts/test_mujoco_ui_gate_playwright.py`
  - `DigitalTwin/scripts/run_phase_verification.py`
  - `DigitalTwin/scripts/run_stability_sweep_playwright.py`

---

## 3) Proposed Backend-Swappable Architecture

### 3.1 Motion backend abstraction
Create one backend interface used by runtime loop:

- `computeStep(inputState, dt) -> outputState`
- outputState includes:
  - root pose
  - joint commands
  - contact states
  - diagnostics block

Backends:
1. Kinematic (existing)
2. Deterministic pseudo-physics (new)
3. Rigid-body co-sim adapter (MuJoCo/Bullet/Isaac)

### 3.2 Compatibility contract
Keep current debug API fields stable; add optional fields only.
- Existing getters must keep shape and semantics.
- New fields live under additive keys (for example physics block) so old tests still pass.
- Existing UI controls and selectors remain unchanged.

### 3.3 Where to insert new modeling
Inside existing runtime step path in `DigitalTwin/pages/freenove_robotdog_3d_render.html`:
1. After gait/servo generation
2. Before final root pose commit
3. Before HIL report finalize

That insertion point allows contact modeling + COM/support checks to influence body follow while preserving existing command generation.

---

## 4) Phase Roadmap (0..7)

## Phase 0 — Baseline Freeze + Determinism Harness
### Goal
Lock current behavior and create reproducible replay baseline.

### Implementation tasks
- Capture canonical input logs (mode switches + gait run + stop).
- Define deterministic replay seed/state reset sequence.
- Store baseline output traces (pose/joint/contact/HIL).

### Data requirements
- Input command log with timestamps
- Per-tick output snapshot (root pose + 16-servo vector + HIL counters)

### Verification gates
- Replay reproducibility: pose delta max <= 1e-6 (normalized units) for same log
- Tick jitter p99 <= 0.5 ms in fixed-step loop
- Baseline scripts pass with no new failures

### Metrics
- deterministic_replay_hash_match = true
- tick_jitter_ms_p50/p95/p99
- baseline_pass_rate

---

## Phase 1 — Canonical State and Contract Layer
### Goal
Make movement state explicit and backend-agnostic.

### Implementation tasks
- Define canonical state object: command, gait phase, joint targets, root state, contacts, IMU.
- Normalize leg indexing and frame semantics in one place.
- Add schema versioning for log rows.

### Data requirements
- Canonical leg map table
- Frame transform documentation (body/world/projection)

### Verification gates
- Schema validation pass rate = 100%
- No index mismatch warnings in 10-min run
- Existing UI/debug endpoints unchanged

### Metrics
- schema_errors = 0
- index_mismatch_count = 0
- backward_compat_tests = pass

---

## Phase 2 — Deterministic Contact + COM/Support Module
### Goal
Introduce contact/state realism without full rigid-body solver.

### Implementation tasks
- Add stance/swing contact state machine with hysteresis.
- Compute support polygon (>=3 contacts) and line fallback (2 contacts).
- Compute COM projection and stability margin each tick.
- Feed correction term into body follow solver before root pose commit.

### Data requirements
- Foot world positions per tick
- Contact confidence/state transitions
- COM projection values

### Verification gates
- Contact timing error <= 20 ms vs expected gait phase events
- Penetration violations = 0 under nominal profile
- Stability margin threshold pass rate >= 99% in 5-min walk

### Metrics
- contact_timing_error_ms_mean/p95
- margin_min, margin_p5
- anti_skate_violations, swing_clear_violations, penetration_violations

---

## Phase 3 — Pseudo-Physics Body Follow
### Goal
Make root motion physically plausible (damped, bounded, contact-aware).

### Implementation tasks
- Add spring-damper body follow in X/Z + yaw.
- Clamp acceleration/velocity by profile.
- Blend IMU compensation without destabilizing gait.

### Data requirements
- Root velocity/acceleration trace
- IMU and command trajectories

### Verification gates
- Overshoot <= 15% on step-input velocity command
- Settling time <= 600 ms for nominal profile
- No oscillation growth over 3-min continuous walk

### Metrics
- step_response_overshoot_pct
- settling_time_ms
- oscillation_energy_ratio

---

## Phase 4 — Tooling Overlays + Correlation Logging
### Goal
Make physics/correlation debugging visible and measurable.

### Implementation tasks
- Add overlays:
  - joint axes
  - COM projection
  - support polygon/line
  - foot contact markers
  - slip vectors
- Add unified correlation log row format.
- Export synchronized sim vs expected reference traces.

### Data requirements
- Overlay toggle states
- Render tick + sim tick correlation IDs

### Verification gates
- Overlay toggle latency <= 1 frame
- Log row completeness >= 99.9%
- Correlation trace time alignment error <= 10 ms

### Metrics
- overlay_frame_latency
- log_drop_rate
- trace_alignment_error_ms

---

## Phase 5 — Backend Adapter (Kinematic <-> Pseudo-Physics)
### Goal
Switch backends at runtime without breaking UI/debug/test contracts.

### Implementation tasks
- Add backend selector in internal config (not new UX surface required).
- Keep existing debug getters and add optional physics block.
- Ensure phase scripts run identically across kinematic and pseudo-physics modes.

### Data requirements
- Backend mode flag per run
- Per-backend metric snapshots

### Verification gates
- Existing Playwright suite unchanged and passing
- Metric parity checks between modes within declared tolerance bands
- No selector or endpoint regressions

### Metrics
- existing_suite_pass = true
- endpoint_contract_diff = 0
- mode_parity_delta

---

## Phase 6 — Rigid-Body Co-Sim Pilot Adapter
### Goal
Prototype external rigid-body backend behind same adapter contract.

### Implementation tasks
- Build adapter bridge (MuJoCo/Bullet/Isaac one at a time).
- Map canonical state to/from co-sim state.
- Keep deterministic replay mode where feasible (fixed stepping, seeded disturbances).

### Data requirements
- Co-sim state snapshots
- Contact impulse/normal data
- Adapter latency measurements

### Verification gates
- Adapter round-trip latency p95 <= 8 ms (local)
- State conversion error <= tolerance (joint/pose)
- Existing debug contract still valid for legacy keys

### Metrics
- adapter_latency_ms_p95
- state_mapping_error
- co_sim_step_stability

---

## Phase 7 — Promotion Readiness and Release Gates
### Goal
Decide whether to stay pseudo-physics or move to rigid-body as primary.

### Implementation tasks
- Run full matrix on nominal + stress profiles.
- Produce decision report with objective thresholds.
- Freeze chosen backend and publish rollback path.

### Data requirements
- Full regression artifacts
- Comparative scorecard (pseudo vs rigid-body)

### Verification gates
- All mandatory scripts pass
- Safety violations remain at/under acceptance limits
- Correlation metrics meet promotion criteria

### Metrics
- promotion_score
- safety_incident_count
- correlation_pass_rate

---

## 5) Decision Matrix: Pseudo-Physics vs Full Rigid-Body Co-Sim

| Condition | Stay Deterministic Pseudo-Physics | Switch to Full Rigid-Body Co-Sim |
|---|---|---|
| Current CI determinism priority | High | Medium/managed |
| Required contact realism | Moderate | High (impulses, compliance, friction cones) |
| Team iteration speed need | Very high | Medium |
| Debug complexity tolerance | Low/medium | High |
| Hardware correlation gap after Phase 4/5 | Small (<10% key metric error) | Persistent (>10-15% error) |
| Runtime budget in dev loop | Tight | Flexible |
| Need for external force/disturbance fidelity | Limited | Strong |
| Integration/maintenance overhead tolerance | Low | High |

### Practical rule
- If pseudo-physics meets safety + correlation thresholds, keep it as production default.
- Switch when correlation gap blocks hardware confidence or contact dynamics are materially wrong.

---

## 6) Verification Tooling and Correlation Log Format

### 6.1 Overlay set (must-have)
- Joint axes overlay
- COM projection marker
- Support polygon/line
- Foot contact markers (stance/swing coloring)
- Slip vector arrows
- Stability margin text/indicator

### 6.2 Correlation log row (JSONL recommended)
Required fields per tick:
- run_id
- sim_tick
- sim_time_s
- wall_time_ms
- backend_mode
- cmd_mode
- leg_index_map_version
- root_pose (x,y,z,roll,pitch,yaw)
- joint_cmd_deg[16]
- joint_state_deg[16] (if available)
- foot_world[4]
- contact_state[4]
- com_proj (x,z)
- support_geom_type (polygon|line|none)
- stability_margin
- violations (anti_skate/swing_clear/penetration/divergence)
- imu (roll,pitch,yaw,age_ms)
- checksum/hash for determinism comparison

### 6.3 Quantitative correlation criteria
- Pose correlation R >= 0.98 over trajectory windows
- Step event timing difference p95 <= 25 ms
- Margin trend correlation R >= 0.95
- Contact state agreement >= 97%

---

## 7) Go/No-Go Checklist for Promotion to Full Rigid-Body

### Go if all true
- Deterministic pseudo-physics cannot meet correlation target after Phase 5 tuning.
- Contact timing/state agreement remains below threshold (<97%).
- Hardware anomalies trace back to missing rigid-body effects (not mapping/timing bugs).
- Adapter latency budget is feasible for dev and CI.
- Team has capacity for higher maintenance complexity.

### No-Go (stay pseudo-physics) if any true
- Existing safety + correlation thresholds are already met.
- Determinism or CI stability regresses under co-sim.
- Debug/iteration speed degrades beyond accepted limits.
- Co-sim integration cost outweighs measurable fidelity benefit.

### Mandatory before either decision
- Full script suite pass on chosen backend.
- Signed artifact report with metrics, traces, and rollback plan.
- Documented operator runbook update.
