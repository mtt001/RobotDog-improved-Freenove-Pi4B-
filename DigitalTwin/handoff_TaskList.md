<!--
File: DigitalTwin/handoff_TaskList.md
Version: v1.8 (2026-02-28 13:21)
Revision History: moved to the end of this file.
-->

# handoff_TaskList

## Purpose
- This file is the operator relay package for DigitalTwin work continuity.
- Any new agent/copilot should be able to resume from this file without scanning prior chat history.

## Stage Wrap-Up (Current)

### Stage Label
- DigitalTwin calibration-and-verification stage (A-D stabilized with mixed measured+assumed baseline).

### Stage Status
- Closed for current cycle with documented assumptions.
- P0 regression lock refreshed: Phase E PASS and full A->G PASS captured at 2026-02-26 10:39 CST.
- Safe to continue into assumption replacement workflow (P1 neutral offsets + IMU).
- P1 tooling improved: new one-command updater `scripts/p1_calibration_update.py` verified with live C/D checks.
- Axis compliance tooling added: `scripts/test_servo_axis_direction_playwright.py` integrated into phase C/E; phase runner hardened with transient retry for Playwright connection races.
- P2 simulation-estimation completed: `scripts/p2_sim_estimate_and_update.py` applied (`SIMULATED` source) and verified with Phase E PASS.
- Geometry-proportion polish is now active with measured-spec binding on core body/leg/hip dimensions.

### Active Away-Time Queue
1. Measurement-bound geometry refinement
- Keep these bindings active in model geometry:
  - body `180/110/85` mm
  - leg links `L1/L2=55/55` mm
  - hip offsets `70/37.5` mm
- Re-verify silhouette against side/top references after each geometry adjustment.

2. CAD-style detail polish
- Tune head/neck/tail and servo-shell placement spacing to reduce visual mismatch with real hardware.
- Preserve verified S11/S12/S13 semantics and axis behavior.

3. Verification gate after each batch
- Run `--only-phase C` and `--only-phase E` for each major geometry update.
- Record outputs to timestamped logs under `DigitalTwin/logs/`.

### Completed in This Stage
1. Measurement baseline synchronization
- Synced measured limits: `S11=65..180`, `S12=0..180`, `S13=0..180`.
- Synced provisional assumptions for current continuation:
  - Neutral offsets (`S11/S12/S13`): `0 deg` (`ASSUMED`, confidence 65).
  - IMU mount/bias (`roll/pitch/yaw`): `0/0/0 deg` (`ASSUMED`, confidence 45).

2. Documentation + traceability updates
- Updated stage measurement table and provenance tracking in:
  - `DigitalTwin/README_DigitalTwin.md` (now v1.27).
  - `DigitalTwin/resources/specs/robot_specs_template.json`.
  - `DigitalTwin/resources/specs/measurement_log_template.csv`.

3. Verification evidence collected
- Phase B PASS (command runtime sweep).
- Phase C PASS (kinematics posture/gait checks).
- Phase D PASS (IMU/pose coupling checks).
- All runs reported HTTP 200 page reachability and Safari launch PASS.
- Fresh P0 lock evidence (2026-02-26 10:39 CST):
  - `DigitalTwin/logs/phaseE_2026-02-26_1039.log` (Phase E PASS)
  - `DigitalTwin/logs/fullAtoG_2026-02-26_1039.log` (pass: 7, fail: 0)
4. Calibration automation added and validated
- Added `DigitalTwin/scripts/p1_calibration_update.py`.
- Verified dry-run preview and apply+verify flow with current baseline values.
- Live verification result through updater: Phase C PASS and Phase D PASS.
5. Axis-direction and phase reliability hardening
- Added `DigitalTwin/scripts/test_servo_axis_direction_playwright.py` (S11/S12/S13 isolation + direction checks).
- Integrated axis-direction test into `run_phase_verification.py` phase C and E bundles.
- Added transient retry in `run_phase_verification.py` for intermittent `ERR_CONNECTION_REFUSED`.
- Verified with:
  - `DigitalTwin/logs/phaseC_2026-02-26_1054_axis.log` (PASS)
  - `DigitalTwin/logs/phaseE_2026-02-26_1057_retryfix.log` (PASS)
6. P2 dynamics/backlash simulation pipeline executed
- Added `DigitalTwin/scripts/p2_sim_estimate_and_update.py`.
- Applied simulated estimates into JSON+CSV (source=`SIMULATED`):
  - speed under load: ~`2.28 deg/s`
  - command-to-motion latency: ~`554.67 ms`
  - backlash estimates: S11 `11.53`, S12 `36.79`, S13 `5.12` deg
- Verification logs:
  - `DigitalTwin/logs/p2sim_2026-02-26_1111.log` (apply + verify PASS)
  - `DigitalTwin/logs/fullAtoG_2026-02-26_1111_after_p2.log` (pass: 7, fail: 0)

## Fast Resume (5 Minutes)

1. Open these files first:
- `DigitalTwin/README_DigitalTwin.md`
- `DigitalTwin/resources/specs/robot_specs_template.json`
- `DigitalTwin/resources/specs/measurement_log_template.csv`
- `DigitalTwin/handoff_TaskList.md`

2. Confirm current baseline by running:
```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase E
```

3. If PASS, proceed to P1 measurements (neutral offsets and IMU).

4. After each measurement update, sync the triad (JSON + CSV + README) in the same timestamp block.

## Source-of-Truth and Scope Guardrails

- This handoff is for `DigitalTwin` workflow only.
- Local source of truth for this stage:
  - `DigitalTwin/README_DigitalTwin.md`
  - `DigitalTwin/resources/specs/robot_specs_template.json`
  - `DigitalTwin/resources/specs/measurement_log_template.csv`
- Do not treat assumptions as measured values.
- Every markdown/json/csv edit must include version/provenance consistency updates.

## Current Baseline Snapshot

### Measurement State
- `MEASURED`: `L1`, hip offsets (`x`,`y` derived from measured spans), `S11/S12/S13` safe ranges.
- `ASSUMED`: `L2`, neutral offsets, IMU mount/bias, dynamic response, backlash, contact model.

### Known Good Verification Window
- Last known successful focused phases:
  - Phase B PASS
  - Phase C PASS
  - Phase D PASS
- Last assumption lock:
  - Neutral offsets = `0/0/0 deg` (ASSUMED, confidence 65)
  - IMU mount/bias = `0/0/0 deg` (ASSUMED, confidence 45)

### Confidence Hotspots (Need Upgrade First)
1. IMU mount/bias assumptions (confidence 45)
2. Neutral offsets assumptions (confidence 65)
3. Servo dynamics assumptions (confidence 35)
4. Backlash assumptions (confidence 30)
5. Contact model assumptions (confidence 30)

## Pending Task List (Prioritized)

### P0 — Keep Regression Green While Replacing Assumptions
1. Run Phase E regression bundle with current assumptions.
- Goal: lock a known-good reference before further measurement replacement.
- Command:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase E
```
- Exit criteria: phase summary `PASS`.

2. Run full A→G check once after P0.1 if time allows.
- Command:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless
```
- Exit criteria: summary `pass: 7`, `fail: 0`.

Definition of done for P0:
- Commands execute without crash.
- All required phases PASS.
- Any failure has reproducible notes and rollback point.

### P1 — Replace Highest-Impact Assumptions with Measurements
1. Neutral offsets measurement (`S11/S12/S13` from 90°)
- Why: strongest impact on posture drift and gait symmetry.
- Update targets:
  - `DigitalTwin/resources/specs/robot_specs_template.json`
  - `DigitalTwin/resources/specs/measurement_log_template.csv`
  - `DigitalTwin/README_DigitalTwin.md`
- Verification after update:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase C
```

2. IMU mounting orientation + static bias capture
- Why: directly affects body-pose correctness in phase D.
- Verification after update:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase D
```

Definition of done for P1:
- Neutral offsets and IMU values converted from ASSUMED to MEASURED in JSON+CSV+README.
- C and D phases PASS after updates.
- Confidence values updated to measured confidence.

### P2 — Dynamics Realism Tuning
1. Measure servo speed under load (`S11/S12/S13`, deg/s).
2. Measure command-to-motion latency (ms).
3. Measure backlash/deadband (`S11/S12/S13`, deg).
- Verification after each item:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase E
```

Definition of done for P2:
- Speed/latency/backlash rows converted to MEASURED (or explicit ASSUMED if user confirms).
- E phase PASS retained after each update.

### P3 — Contact Model and Validation Context
1. Replace point-contact assumption with measured/declared contact geometry.
2. Record floor type/friction context used for validation runs.
- Verification:
```bash
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase G
```

Definition of done for P3:
- Contact geometry and floor condition documented in all three artifacts.
- G phase PASS with no new regressions.

## Implementation Relay SOP (Mandatory)

1. Capture timestamp first.
2. Apply minimal edits.
3. Sync triad artifacts together:
- README measurement table
- JSON machine-readable values
- CSV log rows
4. Run smallest relevant phase check.
5. If PASS, optionally broaden to full A→G.
6. Append revision/history delta before handoff.

## Failure Handling and Rollback

If any phase fails after a measurement update:
1. Revert only the last changed parameter set.
2. Re-run the same phase to confirm recovery.
3. Mark the parameter as `ASSUMED` with lower confidence and note why.
4. Request refined user measurement with narrower method.

## Risk Register (Current)

1. Neutral offsets not measured yet
- Risk: posture bias, straight-walk drift.
- Mitigation: prioritize P1.1 and rerun Phase C.

2. IMU orientation and bias still assumed
- Risk: incorrect body pose and axis coupling.
- Mitigation: prioritize P1.2 and rerun Phase D.

3. Dynamics values still assumed
- Risk: unrealistic smoothness and timing mismatch.
- Mitigation: execute P2 with measured speed/latency/backlash.

4. Contact model still assumed
- Risk: unreliable high-level gait interpretation.
- Mitigation: execute P3 and rerun Phase G.

## Exact Pending Inputs Needed From User

1. Neutral offsets from 90 for S11, S12, S13, with confidence.
2. IMU mount orientation relative to FLU.
3. IMU static bias roll/pitch/yaw on flat table.
4. Servo speed under load and command latency.
5. Backlash/deadband for S11, S12, S13.
6. Foot contact geometry and floor condition.

## Operator Prompt Templates

Use this to request measurements consistently:
- Please provide measured values for [parameter list].
- If unknown, provide ASSUMED values and confidence (0-100).
- Format: parameter=value unit, source=MEASURED/ASSUMED, confidence=?, notes=?

Use this to report completion consistently:
- Updated files: README/JSON/CSV.
- Changed parameters: [list].
- Verification: phase [X] PASS/FAIL.
- Next pending inputs: [list].

## Execution Plan (Next Session)

### Step 1 (10-15 min): Stabilize Evidence
- Re-run Phase E and save output log.
- Optional full A→G run for release-style confidence.

### Step 2 (15-25 min): Neutral + IMU measurement batch
- Capture neutral offsets for FR first, then mirror check on remaining legs.
- Capture IMU orientation + static bias on flat surface.

### Step 3 (10 min): Sync + verify
- Sync JSON/CSV/README in one pass with one timestamp block.
- Run targeted C + D verification.

### Step 4 (15-30 min): Dynamics batch
- Capture speed/latency/backlash assumptions replacement.
- Run targeted E verification.

### Step 5 (5-10 min): Finalize handoff delta
- Add revision entries and summarize measured-vs-assumed delta.

## Ready-to-Use Command Block

```bash
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase E
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase C
python3 DigitalTwin/scripts/run_phase_verification.py --headless --only-phase D
python3 DigitalTwin/scripts/run_phase_verification.py --headless
```

## Evidence Capture Checklist

- Save terminal output for each phase run.
- Save at least one screenshot for UI-visible changes.
- Record all changed parameters and confidence before/after.
- Keep one-line rationale per changed assumption.

## Open Items Requiring User Inputs
1. Neutral offsets from 90° (`S11/S12/S13`) measured values + confidence.
2. IMU board mounting orientation relative to FLU + confidence.
3. IMU static bias roll/pitch/yaw on flat reference + confidence.
4. Replace SIMULATED servo speed under load and command latency with measured hardware values.
5. Replace SIMULATED backlash/deadband estimates with measured hardware values per joint.
6. Foot contact geometry and floor condition used for acceptance runs.

## Handoff Notes for Next Operator
- Treat `README_DigitalTwin.md` measurement table and JSON/CSV as a locked triad: update all three together.
- After each measurement replacement, run the smallest relevant phase first (C/D/E), then broaden.
- Keep all assumptions explicitly labeled `ASSUMED` until measured values are provided.
- Prefer one-parameter-at-a-time updates when debugging regressions.
- Do not run broad refactors while measurement baseline is still evolving.


## Revision History
- 2026-02-26 13:07 v1.7 - Added active away-time queue for measured-geometry binding and CAD-style proportion polish with mandatory C/E verification gates.
- 2026-02-26 11:14 v1.6 - Added P2 simulation-estimation completion, applied-value summary, fresh full A->G PASS evidence, and clarified remaining items requiring real hardware replacement.

## Older Revision History
- 2026-02-26 10:57 v1.5 - Added axis-direction compliance integration and phase-runner retry hardening with fresh PASS evidence logs.
- 2026-02-26 10:50 v1.4 - Added P1 calibration updater tooling status (`p1_calibration_update.py`) with verified apply+C/D live-check outcome.
- 2026-02-26 10:42 v1.3 - Added fresh P0 regression lock evidence (Phase E PASS + full A->G PASS) with exact log paths and updated stage status for next operator.
- 2026-02-26 10:36 v1.2 - Relocated handoff file into `DigitalTwin/` and updated file metadata for same-folder README relay usage.
- 2026-02-26 10:34 v1.1 - Expanded into full relay playbook with fast-resume workflow, SOP, risk register, failure handling, DoD gates, and operator prompt/report templates.
- 2026-02-26 10:32 v1.0 - Created stage wrap-up handoff task list with completed evidence, prioritized pending tasks, and an execution plan for next measurement/verification cycle.
