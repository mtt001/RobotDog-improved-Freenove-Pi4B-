<!--
File: Documents md/Baseline_Gait_Comparison.md
Description:
  Phase-0 baseline comparison between Pi Server gait source (`Server/Control.py`) and the pre-upgrade Digital Twin forced 4-beat gait model.
Usage:
  1) Open this file to review baseline assumptions before HIL tuning.
  2) Compare with overnight status file for post-upgrade deltas.
Version: v1.0 (2026-02-26 21:48)
Revision History:
- 2026-02-26 21:48 v1.0 - Added baseline phase/timing/step/orientation comparison for autonomous overnight HIL upgrade.
-->

# Baseline Gait Comparison

## Scope
- Pi source: `Server/Control.py` (`forWard`, `changeCoordinates`, `run`).
- Twin baseline source: pre-upgrade `freenove_robotdog_3d_render.html` v1.90 forced 4-beat phase map.

## Baseline Capture Method
- Static source audit from code constants/functions.
- Deterministic command-range sampling via Playwright debug API for pre-upgrade behavior.

## Baseline A: Pi Server `forWard`
- Gait generator: cosine/sine trajectory in loop `i=90..450 step speed`.
- Commanded stride amplitude:
  - `X1/X2 = 12*cos(.)` => nominal step length about `24` coordinate units.
- Vertical motion:
  - `Y = 6*sin(.) + height`, then clamped not above `height`.
- Phase relation:
  - Two leg groups 180 degrees apart (`X2/Y2` uses `i+180`).
- Expected behavior:
  - Pairwise alternating leg groups, controller-calibrated mapping in `run()`.

## Baseline B: Twin v1.90 forced 4-beat model
- Phase map:
  - FR `0`, RR `pi/2`, FL `pi`, RL `3pi/2`.
- Stance ratio:
  - `0.72` (from `TUTORIAL_IK.stanceRatio`).
- Cadence:
  - `2.15` (from `TUTORIAL_IK.cadence`).
- Nominal stride:
  - `2 * 6.9 = 13.8` IK units (`strideX`).
- Body orientation traces:
  - Walk bob only: `0.010*sin(2*gaitT)` on body Y.
  - No intrinsic yaw for walk-in-place unless Dog Action turn commands active.

## Joint/Phase Baseline Summary
| Metric | Pi `Control.py` | Twin v1.90 forced 4-beat |
|---|---|---|
| Joint group order | 2-group alternation | 4-beat FR->RR->FL->RL |
| Pairing | 180-degree pair split | 90-degree staggered sequence |
| Stance/Swing timing | sinusoidal with Y clamp | explicit stance/swing gate with `stanceRatio=0.72` |
| Step length basis | `~24` coord units | `~13.8` IK stride units |
| Orientation trace | hardware + IMU dependent | bob-only (unless action/IMU applied) |

## Baseline Risk Notes
- Twin v1.90 phase order did not match requested Pi-style diagonal pairing target.
- Quasi-static support checks were likely to flag forced 4-beat windows with low margin depending on stance inference threshold.
