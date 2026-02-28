# Digital Twin Camera Mode & 3D Servo Upgrade Plan
# File: DigitalTwin/README_DigitalTwin_CameraUpgrade_v2.00.md
Version: v2.09 Date: 2026-02-28 11:59 (CST) Author: MT & ChatGPT

------------------------------------------------------------------------

## 1. Objective

Upgrade the Digital Twin architecture to:

1.  Replace 2D servo projection panels with true 3D hierarchical servo
    visualization.
2.  Support two camera modes:
    -   Mode A: FREE (independent camera)
    -   Mode B: FOLLOW (camera follows robot; default)
3.  Ensure world-frame invariance and ROS-aligned coordinate
    consistency.
4.  Prepare system for future MuJoCo / physics integration.

------------------------------------------------------------------------

## 2. World and Frame Contract (Locked)

World frame (right-handed):

+X = Forward\
+Y = Left\
+Z = Up

Rules:

-   World frame never moves.
-   Grid remains fixed in world frame.
-   Robot motion updates its model transform.
-   Camera movement updates only the view transform.
-   No axis remapping or 2D projection allowed.

------------------------------------------------------------------------

## 3. Servo 3D Hierarchy (FR Leg Reference)

Required structure:

RobotRoot └── BodyFrame └── Leg_FR └── S11_group (Hip Roll, axis +X) └──
S12_group (Hip Pitch, axis +Y) └── S13_group (Knee Pitch, axis +Y local)
└── Foot

Each servo rotates only its own group. No sibling leakage.

Axis definitions (FR):

-   S11: rotate around +X (hip abduction/adduction)
-   S12: rotate around +Y (hip flexion/extension)
-   S13: rotate around local +Y (knee flexion)

Positive rotation follows right-hand rule.

------------------------------------------------------------------------

## 4. 3D Servo Debug Requirements

1.  Remove all 2D projection math.
2.  Add THREE.AxesHelper to:
    -   Body frame
    -   S11_group
    -   S12_group
    -   S13_group
3.  Show live joint angle (deg + rad) overlay.
4.  Display FK foot position (x, y, z).

Acceptance criteria:

-   Rotating S11 affects only descendants.
-   FK changes smoothly with joint input.
-   Frame check remains PASS.

------------------------------------------------------------------------

## 5. Camera Mode Architecture

### Mode A --- FREE

-   OrbitControls enabled.
-   Camera independent of robot.
-   Robot may walk out of frame.
-   Used for debugging.

### Mode B --- FOLLOW (Default)

-   Camera tracks robot position.
-   Smooth interpolation required.
-   Grid remains fixed in world.
-   Robot centered during walking.

FOLLOW logic (conceptual):

targetPosition = robot.position + offset
camera.position.lerp(targetPosition, alpha)
camera.lookAt(robot.position)

Recommended default offset (side view example):

offset = (0, -0.5, 0.3)

------------------------------------------------------------------------

## 6. Camera Stability Options

Two variants supported:

1.  Stabilized Horizon (Recommended for gait review)
    -   Camera inherits robot translation.
    -   Camera does NOT inherit roll/pitch.
    -   Camera.up remains (0,0,1).
2.  Rigid FPV Mode
    -   Camera is child of robot.
    -   Inherits full rotation.
    -   Used for immersive view.

------------------------------------------------------------------------

## 7. Development Order (Strict)

Step 1 --- Remove 2D projection code. Step 2 --- Build correct 3D servo
hierarchy. Step 3 --- Add axis helpers and verify rotation isolation.
Step 4 --- Add servoCamera rendering same scene. Step 5 --- Implement
Camera Mode Manager. Step 6 --- Implement FOLLOW mode (default). Step 7
--- Re-test gait walking under FOLLOW mode.

Do not skip order.

------------------------------------------------------------------------

## 8. Codex Implementation Prompt

Use this exact instruction:

------------------------------------------------------------------------

Refactor Digital Twin for 3D Servo + Camera Modes

Phase 1 --- Remove 2D Projection - Delete all 2D (x,y) math projection
logic. - Ensure only ONE robot instance exists in scene.

Phase 2 --- Implement 3D Hierarchy - RobotRoot -\> Body -\> Leg_FR -\>
S11 -\> S12 -\> S13. - S11 rotates around +X. - S12 rotates around +Y. -
S13 rotates around local +Y. - Add THREE.AxesHelper at body and each
joint.

Phase 3 --- Multi Camera Support - Keep mainCamera with OrbitControls. -
Add cameraMode variable: "FOLLOW" or "FREE". - Default = FOLLOW.

FOLLOW behavior: - camera.position = robot.position + offset
(smoothed). - camera.lookAt(robot.position). - Grid must remain fixed in
world frame.

FREE behavior: - OrbitControls enabled. - Camera independent of robot.

Do NOT: - Move world/grid to simulate motion. - Rotate robot to fake
view. - Create duplicate robot instances.

Goal: When robot walks forward (+X), robot world position updates,
camera follows smoothly, ground grid appears moving, servo hierarchy
remains correct.

------------------------------------------------------------------------

------------------------------------------------------------------------

## 9. Expected Result

After implementation:

-   Servo view is true 3D.
-   HAA (S11), HFE (S12), KFE (S13) all visible.
-   No axis confusion.
-   Gait review stable in FOLLOW mode.
-   World invariance preserved.
-   Ready for MuJoCo alignment.

------------------------------------------------------------------------
## 10. Execution Status (2026-02-28 07:50 CST)

Completed baseline gates:
- Full regression command passed clean:
  - `python3 DigitalTwin/scripts/run_phase_verification.py --headless`
  - Summary: `pass=7`, `fail=0`.

Implemented/verified:
- Resolved merge conflicts in DigitalTwin page/test scripts.
- Servo Test runtime restored (`THREE.Clock` initialization fix).
- Walk roll-channel observability restored (mild lateral modulation).
- Camera manager hooks added for `FOLLOW/FREE` (debug API control).
- World invariance runtime audit added (`worldInvariant=true/false` diagnostics).

Extension artifacts written:
- `iCloud/AI_Reports/ext1_servo_isolation.json`
- `iCloud/AI_Reports/ext2_camera_stability.md`
- `iCloud/AI_Reports/ext3_world_invariance.json`
- `iCloud/AI_Reports/ext4_performance.json`
- `iCloud/AI_Reports/ext5_fk_ik_consistency.json`
- `iCloud/AI_Reports/ext6_com_debug.png`
- `iCloud/AI_Reports/phase3_follow_mode.png`

Current extension status:
- EXT-1 Servo isolation: PASS (`ext1_servo_isolation.json`, all cases isolated within tolerance).
- EXT-2 Camera stress: PASS (`ext2_camera_stability.md`).
- EXT-3 World invariance: PASS (`worldInvariant=true` across sampled walk run).
- EXT-4 Performance: PASS by simulation-frame baseline (`simulation_fps_avg ~100`, `goal_gt_55fps=true` in `ext4_performance.json`).
- EXT-5 FK/IK consistency: PASS (50/50, max error `~1.24e-11`).
- EXT-6 Physics prep marker: PASS (`ext6_com_debug.png`).
- EXT-7 Code structure hardening: PASS (extracted `CameraManager.js` and `ServoHierarchy.js`, added single-scene guard).
- EXT-8 Advanced camera modes: PASS (`FOLLOW/FREE/FPV/HORIZON/TOPDOWN` mode-switch audit in `ext8_camera_modes.md`).

Hotfix cycle (user-reported runtime issues):
- Fixed servo leg mismatch with visible 3D rig:
  - `DigitalTwin/pages/ServoHierarchy.js` now applies S12/S13 hinge rotation on the rig-consistent local hinge axis (`rotation.z`) while keeping S11 on `rotation.x`.
- Fixed FOLLOW-mode model size adjustability:
  - `DigitalTwin/pages/CameraManager.js` + page wheel handler now support FOLLOW/HORIZON distance adjustment (wheel zoom behavior) without breaking world-frame invariance.
- Re-verified after hotfix:
  - `python3 DigitalTwin/scripts/test_servo_axis_direction_playwright.py --page http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html --headless` => PASS.
  - `python3 DigitalTwin/scripts/run_phase_verification.py --headless` => PASS (`pass=7`, `fail=0`).
  - `python3 DigitalTwin/scripts/ext1_servo_isolation_playwright.py --page http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html --headless` => PASS.
- Updated visual evidence:
  - `iCloud/AI_Reports/phase2_servo3d.png`
  - `iCloud/AI_Reports/phase3_follow_mode.png`
  - `iCloud/AI_Reports/hotfix_ui_verify.png`
  - `iCloud/AI_Reports/hotfix_ui_verify_zoomed.png`

COM visibility refinement (2026-02-28 07:50 CST):
- Added transparent torso shell rendering for COM inspection (`body`/`bodyTop` opacity enabled).
- Enhanced COM marking with a high-contrast core marker at body COM position.
- Runtime UI verification captured:
  - `iCloud/AI_Reports/hotfix_com_transparent_torso.png`

GAIT debug tooltip refinement (2026-02-28 11:33 CST):
- Servo markers now include clear `HFE` / `KFE` labels with higher-contrast text rendering.
- Tooltip helper is active on yellow servo markers in GAIT debug view, with larger hover tolerance and marker highlight.
- Added deterministic debug inspection hook:
  - `window.__robotDogDebug.getGaitDebugState()`
- Fixed follow-up regression (2026-02-28 11:40 CST):
  - Restored non-blocking control interactions by switching tooltip hover tracking to global mouse sampling and setting GAIT canvas to non-interactive pointer hit-testing.
  - Verified no Servo Test click interception.
- Real UI verification:
  - URL launched and refreshed in Safari:
    - `http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html?ts=1772192460`
  - `HTTP 200` reachability confirmed.
  - Screenshot evidence:
    - `iCloud/AI_Reports/hotfix_gait_debug_hfe_kfe_tooltip_hover_v242.png`
  - Regression spot-check:
    - `python3 DigitalTwin/scripts/test_mujoco_ui_gate_playwright.py --headless --page http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html?ts=1772192460` => PASS.
    - `python3 DigitalTwin/scripts/run_phase_verification.py --headless` => PASS (`pass=7`, `fail=0`).

Leg profile/proportion refinement (2026-02-28 11:50 CST):
- GAIT debug side-view leg glyphs now use non-identical profiles:
  - Upper leg: narrow-waist plate profile.
  - Lower leg: bracket/foot profile with toe extension.
- Normalized panel proportion updated to Freenove-like non-equal lengths:
  - `L1 upper > L2 lower` (visual ratio applied in normalized rendering).
- UI verification (Safari + screenshot):
  - URL: `http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html?ts=1772192760`
  - Evidence: `iCloud/AI_Reports/hotfix_leg_shape_ratio_v243.png`
- Regression verification:
  - `python3 DigitalTwin/scripts/run_phase_verification.py --headless` => PASS (`pass=7`, `fail=0`).

HAA assembly refinement (2026-02-28 11:57 CST):
- Added explicit HAA servo-side assembly structure near hip in GAIT debug side view.
- Highlighted the top-right rotating shaft with bright white shaft geometry (matching tutorial emphasis).
- Added tooltip target support for HAA shaft hover (`leg + HAA` context).
- UI verification (Safari + screenshot):
  - URL: `http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html?ts=1772193180`
  - Evidence: `iCloud/AI_Reports/hotfix_haa_shaft_v244.png`
- Regression verification:
  - `python3 DigitalTwin/scripts/run_phase_verification.py --headless` => PASS (`pass=7`, `fail=0`).

Joint-role visualization refinement (2026-02-28 11:59 CST):
- Clarified role mapping directly in the GAIT panel:
  - `HAA` label anchored to top white rotating shaft.
  - `HFE` label anchored to hip joint axis.
  - `KFE` label anchored to knee joint axis.
- Updated tooltip logic to target axis points (`HAA/HFE/KFE`) rather than servo-body label positions.
- UI verification (Safari + screenshot):
  - URL: `http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html?ts=1772193540`
  - Evidence: `iCloud/AI_Reports/hotfix_joint_roles_haa_hfe_kfe_v245.png`
- Regression verification:
  - `python3 DigitalTwin/scripts/run_phase_verification.py --headless` => PASS (`pass=7`, `fail=0`).

------------------------------------------------------------------------
========================================================================
prompt to Codex for implementation:  date: 2026-02-27 07:35 (Taipei Time)
AUTONOMOUS DIGITAL TWIN UPGRADE TASK
Mode: Self-Execution + Self-Verification + Status Reporting

Objective:
Upgrade Digital Twin to:
1) True 3D Servo Hierarchy (S11/S12/S13)
2) Camera Mode Manager (FOLLOW default, FREE optional)
3) Remove ALL 2D projection logic
4) Preserve world-frame invariance
5) Self-verify using UI + Playwright
6) Update progress report in iCloud/AI_Reports
7) Update README progress section

You must operate independently and verify behavior in real UI.

------------------------------------------------------------
PHASE 0 — Safety & Baseline Snapshot
------------------------------------------------------------

1. Create backup branch or local snapshot.
2. Save initial status file:
   iCloud/AI_Reports/latest_status.md
   Include:
   - Timestamp
   - Current Git hash (if available)
   - Phase = START
   - Summary of intended changes

------------------------------------------------------------
PHASE 1 — Remove 2D Projection
------------------------------------------------------------

Tasks:
- Search for any code performing:
    manual (x,y) projection
    world X/Y remapping
    2D canvas math for servo leg
- Remove or disable all 2D projection logic.
- Confirm only ONE robot instance exists in scene graph.

Verification:
- Launch dev server:
    python3 DigitalTwin/scripts/digitaltwin_dev_server.py --host 127.0.0.1 --port 8766
- Open Safari UI.
- Ensure page loads without JS error.
- Confirm no missing references.

If UI fails → fix before proceeding.

Update report:
- Phase = 1_COMPLETE
- List files changed.

------------------------------------------------------------
PHASE 2 — Implement 3D Servo Hierarchy
------------------------------------------------------------

Implement strict hierarchy:

RobotRoot
 └── BodyFrame
       └── Leg_FR
             └── S11_group (axis +X)
                   └── S12_group (axis +Y)
                         └── S13_group (axis +Y local)
                               └── Foot

Rules:
- S11 rotates around +X.
- S12 rotates around +Y.
- S13 rotates around local +Y.
- Add THREE.AxesHelper to:
    Body
    S11
    S12
    S13

Verification:
- Launch UI.
- In Servo Test mode:
    Move S11 → only lateral roll observed.
    Move S12 → forward/back swing.
    Move S13 → knee bend only.
- Confirm no sibling leakage.

Run:
    python3 DigitalTwin/scripts/test_servo_axis_direction_playwright.py --headless

If fail → fix axis or hierarchy.

Update:
- Phase = 2_COMPLETE
- Screenshot saved to:
    iCloud/AI_Reports/phase2_servo3d.png

------------------------------------------------------------
PHASE 3 — Multi Camera Architecture
------------------------------------------------------------

Add:

cameraMode = "FOLLOW" (default)
Supported modes:
- FOLLOW
- FREE

FREE:
- Enable OrbitControls.

FOLLOW:
- camera.position = robot.position + offset
- Smooth with lerp (alpha ~0.1)
- camera.lookAt(robot.position)
- Grid remains fixed in world.

IMPORTANT:
- Do NOT move world/grid.
- Do NOT rotate robot to fake camera.
- Do NOT create duplicate robot object.

Verification:
1) In WALK mode:
    Robot moves in +X.
    Camera tracks smoothly.
    Grid appears moving.
2) Switch to FREE:
    Orbit works normally.
3) Switch back to FOLLOW:
    Robot recenters.

Run:
    python3 DigitalTwin/scripts/test_gait_walk_playwright.py --headless
    python3 DigitalTwin/scripts/test_mujoco_ui_gate_playwright.py --headless

If fail → adjust follow logic.

Update:
- Phase = 3_COMPLETE
- Save:
    iCloud/AI_Reports/phase3_follow_mode.png

------------------------------------------------------------
PHASE 4 — Regression Gate
------------------------------------------------------------

Run full suite:

python3 DigitalTwin/scripts/run_phase_verification.py --headless

Require:
PASS count = all phases
FAIL count = 0

If fail:
- Diagnose
- Fix
- Re-run

Do not proceed unless clean.

------------------------------------------------------------
PHASE 5 — Update Documentation
------------------------------------------------------------

1. Append section in:
   README_DigitalTwin.md

Section title:
   "Camera Mode Architecture Upgrade (v2.00)"

Include:
- Removal of 2D projection
- 3D servo hierarchy
- Camera Mode A/B
- World invariance guarantee
- Date + summary

2. Update revision history entry.

------------------------------------------------------------
PHASE 6 — Final Status Report
------------------------------------------------------------

Write:
iCloud/AI_Reports/latest_status.md

Include:
- Timestamp
- Completed Phases
- Tests PASS/FAIL
- Files modified
- Remaining TODO (if any)
- Confidence level (0–100%)

Also create:
iCloud/AI_Reports/latest_status.json

Format:
{
  "timestamp": "...",
  "phase_completed": 3,
  "tests_pass": true,
  "world_invariance": true,
  "servo3d": true,
  "camera_follow": true
}

------------------------------------------------------------
FAIL-SAFE RULES
------------------------------------------------------------

STOP immediately if:
- Multiple robot instances detected.
- World frame altered.
- Grid position changed relative to world origin.
- Joint axis mismatch detected.
- FK foot position unstable.

Log error and write to:
iCloud/AI_Reports/latest_status.md

------------------------------------------------------------
SUCCESS CONDITION
------------------------------------------------------------

Success =

- Servo view fully 3D
- S11/S12/S13 correct axes
- FOLLOW mode stable
- FREE mode stable
- All Playwright tests pass
- README updated
- iCloud report written

Only declare SUCCESS after full regression PASS.

------------------------------------------------------------

Work autonomously.
Verify with real UI.
Fix errors iteratively.
Update reports after each phase.
Do not skip verification.
================================================================
POST-SUCCESS EXTENSION TASKS
Execute only if all prior phases PASS and regression = clean.

------------------------------------------------------------
EXT-1 — Servo Stress Test & Isolation Validation
------------------------------------------------------------

1. Create automated servo sweep test:
   - Sweep S11 only while others fixed.
   - Sweep S12 only.
   - Sweep S13 only.
   - Then sweep combinations (S11+S12, S12+S13).
2. Detect any unintended sibling movement.
3. Log max deviation of unintended axes.

If cross-axis leakage detected > tolerance:
  Fix hierarchy and re-test.

Save:
iCloud/AI_Reports/ext1_servo_isolation.json

------------------------------------------------------------
EXT-2 — Camera Stability & Follow Stress Test
------------------------------------------------------------

1. Run walk gait at:
   - Normal speed
   - 2x speed
   - 0.5x speed
2. Measure:
   - Camera jitter (position delta variance)
   - Frame consistency
   - Grid stability
3. Ensure FOLLOW mode never detaches from robot.
4. Ensure FREE mode restores correctly.

Save:
iCloud/AI_Reports/ext2_camera_stability.md

------------------------------------------------------------
EXT-3 — World Invariance Audit
------------------------------------------------------------

Implement runtime check:

- Confirm world origin remains constant.
- Confirm grid transform never changes.
- Confirm only robot model matrix changes during walking.

Add console diagnostic:
   worldInvariant = true/false

If false → log and halt.

------------------------------------------------------------
EXT-4 — Performance & Frame Timing Audit
------------------------------------------------------------

Measure:
- FPS average
- Frame time variance
- CPU spike during walk

Log to:
iCloud/AI_Reports/ext4_performance.json

Goal:
Stable > 55 FPS (local baseline).

------------------------------------------------------------
EXT-5 — FK/IK Numerical Consistency Check
------------------------------------------------------------

For 50 random reachable foot targets:

1. Solve IK.
2. Recompute FK.
3. Measure error norm.

If error > tolerance:
  Log case.
  Attempt branch correction.

Save:
iCloud/AI_Reports/ext5_fk_ik_consistency.json

------------------------------------------------------------
EXT-6 — Future Physics Preparation
------------------------------------------------------------

1. Insert placeholder physics hooks:
   - Robot mass
   - Link mass
   - COM estimation
2. Compute static COM location.
3. Render COM marker sphere.

Save:
iCloud/AI_Reports/ext6_com_debug.png

------------------------------------------------------------
EXT-7 — Code Structure Hardening
------------------------------------------------------------

Refactor if safe:

- Extract CameraManager.js
- Extract ServoHierarchy.js
- Ensure no global variable leakage.
- Enforce single scene instance pattern.

Run full regression again.

------------------------------------------------------------
EXT-8 — Advanced Camera Modes (Optional)
------------------------------------------------------------

If time allows:

Add:
- FPV rigid attach mode
- Stabilized horizon follow mode
- Top-down tactical mode

Ensure mode switching never breaks world invariance.

------------------------------------------------------------
FINAL RULE
------------------------------------------------------------

Do NOT modify world frame convention.
Do NOT move grid to fake motion.
Do NOT duplicate robot object.

All changes must pass:
run_phase_verification.py --headless

If all extension tasks pass,
write summary to:
iCloud/AI_Reports/final_autonomous_cycle.md


================================================================
End of Document
