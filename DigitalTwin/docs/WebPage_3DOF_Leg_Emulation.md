# WebPage_3DOF_Leg_Emulation

**Author:** Mengta Tsai + ChatGPT\
**Created:** 2026-02-26 05:51:45 (Asia/Taipei)\
**Version:** v1.0

------------------------------------------------------------------------

# 🎯 Project Goal

Build a professional-grade browser-based 3DOF robot leg emulator that
supports:

-   ✅ Full 3D engineering model (axes + coordinate debug)
-   ✅ WebRTC-integrated live digital twin
-   ✅ Inverse kinematics (IK) solver
-   ✅ Exportable module for ClientAI integration
-   ✅ 2D lightweight debug mode
-   ✅ ROS-compliant coordinate system

Body Frame (Right-Handed): +X = Forward\
+Y = Left\
+Z = Up

------------------------------------------------------------------------

# 🏗 Phase 1 --- 3D Engineering Model (Foundation)

## Objectives

-   Hierarchical joint structure
-   Visible local coordinate axes
-   Clear separation of world vs body frame
-   Correct right-hand-rule rotation behavior

## Joint Definition (Front Right Leg Example)

S11 --- Hip Roll\
- Axis: +X\
- Vector: (1,0,0)\
- Positive rotation follows right-hand rule

S12 --- Hip Pitch\
- Axis: +Y\
- Vector: (0,1,0)

S13 --- Knee Pitch\
- Axis: +Y (local thigh frame)

## Three.js Structure

RobotRoot\
└── BodyFrame\
└── Leg_FR\
└── S11\
└── S12\
└── S13

Each joint rotates its child only.

------------------------------------------------------------------------

# 🎥 Phase 2 --- WebRTC Digital Twin

## Objectives

-   Receive servo angles from Pi Server
-   Apply real-time joint updates
-   Display inference + telemetry overlay

## Data Format Example

``` json
{
  "S11": 12.5,
  "S12": -20.3,
  "S13": 44.0,
  "timestamp": 12345678
}
```

## Implementation Steps

1.  WebSocket channel from Pi
2.  Convert degrees → radians
3.  Apply rotation to each joint
4.  Smooth interpolation (optional)
5.  Add latency measurement

------------------------------------------------------------------------

# 🤖 Phase 3 --- Inverse Kinematics (IK)

## Goal

Given foot target (x,y,z), compute:

-   S11 angle
-   S12 angle
-   S13 angle

## Simplified IK Plan (Planar Projection)

1.  Compute hip yaw from Y displacement\
2.  Reduce to 2D plane\
3.  Use law of cosines for knee angle\
4.  Compute hip pitch\
5.  Apply joint limits

------------------------------------------------------------------------

# 🪶 Phase 4 --- Lightweight 2D Debug Mode

Purpose:

-   Fast math validation
-   No WebGL dependency
-   Canvas-based visualization

Features:

-   Draw thigh + shank
-   Show joint angles
-   Plot foot trajectory

------------------------------------------------------------------------

# 📦 Phase 5 --- Exportable Module

Structure:

/modules/Leg3DOF.js\
/modules/IKSolver.js\
/modules/CoordinateDebug.js

Expose API:

``` javascript
Leg.updateAngles({
  S11: deg,
  S12: deg,
  S13: deg
})

Leg.solveIK({
  x: targetX,
  y: targetY,
  z: targetZ
})
```

------------------------------------------------------------------------

# 🔍 Debug Requirements

-   Display world frame axes
-   Display local joint axes
-   Show foot world coordinates
-   Toggle coordinate visibility

------------------------------------------------------------------------

# 🧠 Development Strategy for Codex

Codex must:

1.  Implement hierarchical scene graph only (no manual trig FK)
2.  Add axis helper per joint
3.  Verify right-hand-rule behavior
4.  Add JSON-driven update function
5.  Implement IK math separately
6.  Add joint limit safety check
7.  Provide console verification output

------------------------------------------------------------------------

# 🏁 Final Architecture

Mode 1: Engineering Debug\
Mode 2: WebRTC Digital Twin\
Mode 3: IK Control\
Mode 4: 2D Lightweight

Single shared coordinate convention across all modes.

------------------------------------------------------------------------

# 🚀 Recommended Build Order

1️⃣ 3D engineering skeleton\
2️⃣ Axis debug\
3️⃣ WebSocket live angle injection\
4️⃣ IK solver integration\
5️⃣ Module export refactor\
6️⃣ 2D fallback mode

------------------------------------------------------------------------

End of document.
