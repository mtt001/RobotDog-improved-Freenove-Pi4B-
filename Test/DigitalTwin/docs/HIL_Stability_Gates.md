<!--
File: Test/DigitalTwin/docs/HIL_Stability_Gates.md
Description:
  Pre-MuJoCo HIL stability-gate design for the Digital Twin Three.js robot dog page.
Usage:
  1) Start local server: `python3 Test/DigitalTwin/scripts/digitaltwin_dev_server.py --host 127.0.0.1 --port 8766`
  2) Verify reachability: `curl -I http://127.0.0.1:8766/Test/DigitalTwin/pages/freenove_robotdog_3d_render.html` (expect `HTTP/1.0 200 OK` or `HTTP/1.1 200 OK`).
  3) Launch UI in Safari: `open -a Safari 'http://127.0.0.1:8766/Test/DigitalTwin/pages/freenove_robotdog_3d_render.html'`
Version: v1.1 (2026-02-26 21:48)
Revision History:
- 2026-02-26 21:48 v1.1 - Updated overnight autonomous configuration: fixed-step `dt=0.01s`, diagonal Pi-style phase pairing, dynamic 2-point stance-line fallback, and CI artifact output guidance.
- 2026-02-26 21:23 v1.0 - Added deterministic loop, stability/contact gates, IMU divergence checks, and CI JSON report contract.
-->

# HIL_Stability_Gates

## Goal
Turn the Three.js Digital Twin into a pre-MuJoCo HIL validation stage that rejects physically risky gait behavior before hardware execution.

## Phase 1: Deterministic Simulation Loop
- Fixed timestep: `dt = 0.01 s`.
- Runtime uses accumulator + capped substeps per render frame.
- Record log frame fields:
  - `tSec`
  - `poseMode`
  - `dogAction` (`mode`, `posX`, `posZ`, `yawDeg`)
  - `gaitPhase` (`phaseU`, `swingGate`, `isStance` by leg)
  - `servoCommandDeg`
  - `imuTsMs`
- Replay re-applies recorded `servoCommandDeg` deterministically.

## Phase 2: Stability Gate v1 (Quasi-static)
### Assumptions
- COM proxy starts at body center (`dogRoot` world position projected to ground XZ).
- Ground is planar (`y=0`).
- Stance legs are inferred from gait phase (`swingGate < 0.20`).

### Algorithm
1. Collect stance feet world positions on XZ plane.
2. Build support polygon via convex hull.
3. Project COM to ground XZ.
4. Compute signed distance from COM projection to polygon edges.
   - Positive: inside.
   - Negative: outside.
5. Stability margin threshold gate: fail when `margin < 0.03` units.
6. For diagonal gait windows with 2 stance feet, use a dynamic fallback:
   - compute COM distance to stance line segment,
   - dynamic margin = `dynamicLineThreshold - lineDistance`,
   - fail when dynamic margin `< 0`.

### Runtime behavior
- Draw support polygon and COM marker overlay in scene.
- If unstable: mark FAIL and force action mode to `stop`.

## Phase 3: Contact Sanity Checks
- Anti-skate: if a stance foot drifts more than `0.022` units from stance lock point, flag violation.
- Swing clearance: if swing foot height is below `0.014` units above ground, flag violation.
- Ground penetration clamp: if any foot is below `y=0`, raise body globally for non-penetration and count violation.

## Phase 4: Pre-MuJoCo HIL Signal Consistency
- Expected IMU envelope from gait phase:
  - `roll_expected = 5.0 * sin(gaitT)`
  - `pitch_expected = 4.0 * sin(2*gaitT + pi/2)`
- Divergence event when max roll/pitch error exceeds `10.0 deg`.
- Event includes time, error, and likely culprit leg (highest swingGate).

## CI Report Contract
Use debug API from page:
- `window.__robotDogDebug.getHilReport()`
- `window.__robotDogDebug.getHilReportJson()`

Current report fields:
- `status`, `margin`, `marginThreshold`, `supportPolySize`, `stanceLegKeys`
- `antiSkateViolations`, `swingClearViolations`, `penetrationViolations`
- `divergenceCount`, `latestDivergence`
- `unstableCount`, `stableCount`, `simTimeSec`
- `replay` state

## Playwright Gate Expectations (Current)
- Walk mode is active.
- Existing gait channel movement checks still pass.
- HIL report is present and parseable.
- `margin >= marginThreshold`.
- `antiSkateViolations == 0`.
- `swingClearViolations == 0`.
- `penetrationViolations == 0`.
- JSON artifact written to:
  - `Test/DigitalTwin/logs/HIL_Test_Report.json`.

## Minimal Troubleshooting
1. If page is not reachable:
- Re-run server command and verify port `8766` is not used by another process.
2. If `curl -I` is not `200`:
- Confirm path includes `/Test/DigitalTwin/pages/freenove_robotdog_3d_render.html` exactly.
3. If Safari shows stale UI:
- Hard refresh and append cache buster, example:
  - `http://127.0.0.1:8766/Test/DigitalTwin/pages/freenove_robotdog_3d_render.html?ts=20260226_2123`
