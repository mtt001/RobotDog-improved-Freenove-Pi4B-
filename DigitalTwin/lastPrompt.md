<!--
File: DigitalTwin/lastPrompt.md
Version: v1.0 (2026-02-28 19:32)
Revision History:
- 2026-02-28 19:32 v1.0 - Restored safeguarded prompt spec for dedicated 2D sagittal gait debug panel.
-->

We are implementing a dedicated 2D Sagittal Gait Debug Panel.

Important constraints:

1. This panel must NOT depend on Three.js camera or scene transforms.
2. It must render strictly in Dog body frame (FLU).
3. Use Dog coordinate:
   +X = forward (horizontal axis)
   +Z = up (vertical axis)
   +Y = ignored (camera looking along +Y).
4. Assume HAA = fixed at 90° so leg motion is purely in X-Z plane.

Goal:

Render FR leg (S11=HAA, S12=HFE, S13=KFE) as a 2D linkage:

- Draw hip pivot at origin (0,0).
- Draw HFE link length L1.
- Draw KFE link length L2.
- Compute forward kinematics using firmware math.
- Render foot position in X-Z plane.

Do NOT use scene axes.
Do NOT map to Three.js world axes.
Do NOT rotate the model.

Use raw firmware angles and math directly.

Add:

- Real-time angle display (deg)
- Joint markers
- Foot trace trail
- Toggle to isolate single leg

The visual must match firmware IK math exactly.