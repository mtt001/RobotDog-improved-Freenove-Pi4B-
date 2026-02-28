# plan_WebPage_DigitalTwin

Author: Mengta Tsai + ChatGPT\
Created: 2026-02-26 08:22:40 (Asia/Taipei)\
Version: v2.0\
Description: Professional-grade browser-based Digital Twin architecture
to fully emulate the Pi Server Robot Dog (13x Emax ES08MA II servos)
aligned with ROS 2 and MuJoCo modeling principles.

------------------------------------------------------------------------

# 1. Executive Objective

Develop a browser-based Digital Twin capable of:

-   Full 13-servo emulation (Emax ES08MA II)
-   Real-time WebRTC telemetry synchronization
-   ROS 2 coordinate compliance (REP-103)
-   MuJoCo-level kinematic fidelity (hierarchical articulated body)
-   Deterministic joint modeling
-   Joint limits and safety constraints
-   Inverse kinematics (per leg)
-   Physics-ready abstraction layer (future dynamics support)

Body Frame (Right-Handed): +X = Forward +Y = Left +Z = Up

------------------------------------------------------------------------

# 2. System Architecture Overview

## Physical Layer (Real Robot)

-   Raspberry Pi 4B
-   Freenove HAT (PCA9685 16-ch PWM)
-   13x Emax ES08MA II
-   MPU6050 IMU
-   WebRTC video stream
-   WebSocket telemetry channel

## Digital Twin Layer (Browser)

Modules:

/core/ SceneManager.js CoordinateSystem.js RobotModel.js ServoModel.js

/robot/ Body.js Leg_FL.js Leg_FR.js Leg_RL.js Leg_RR.js

/control/ TelemetryBridge.js IK_Solver.js JointLimit.js SafetyFilter.js

/debug/ AxisHelperExtended.js FrameVisualizer.js LatencyMonitor.js

------------------------------------------------------------------------

# 3. Kinematic Model

RobotRoot └── BodyFrame ├── Leg_FL (S2,S3,S4) ├── Leg_FR (S11,S12,S13)
├── Leg_RL (S5,S6,S7) └── Leg_RR (S8,S9,S10)

Each leg:

HipRoll (axis +X) └── HipPitch (axis +Y) └── KneePitch (axis +Y local)

No manual forward kinematics. Use scene graph transform propagation.

------------------------------------------------------------------------

# 4. Servo Modeling -- Emax ES08MA II

ServoModel parameters:

-   current_angle_deg
-   target_angle_deg
-   max_velocity_deg_per_sec
-   joint_limit_min/max

Simulated response:

angle += clamp((target - angle), max_velocity \* dt)

------------------------------------------------------------------------

# 5. ROS 2 Alignment

REP-103 compliant coordinate convention.

World Frame: Z up X forward Y left

All joint axes explicitly defined as unit vectors. Right-hand rule
strictly enforced.

------------------------------------------------------------------------

# 6. MuJoCo-Level Structural Equivalence

Digital twin mimics:

-   Rigid links
-   Revolute joints
-   Joint limits
-   Local and world transforms
-   Hierarchical propagation

Future-ready for URDF export compatibility.

------------------------------------------------------------------------

# 7. WebRTC Telemetry Integration

Example JSON:

{ "servo": { "S11": 12.4, "S12": -18.2, "S13": 43.9 }, "imu": { "roll":
2.1, "pitch": -1.3, "yaw": 15.4 }, "timestamp": 12345678 }

Processing Pipeline:

1.  Receive JSON
2.  Validate schema
3.  Convert deg → rad
4.  Apply joint rotation
5.  Interpolate if required
6.  Update latency metrics

------------------------------------------------------------------------

# 8. Inverse Kinematics (Per Leg)

Given foot (x,y,z):

1.  Compute hip roll from Y offset
2.  Transform to sagittal plane
3.  Use law of cosines for knee
4.  Compute hip pitch
5.  Enforce joint limits

IK solver separated from rendering logic.

------------------------------------------------------------------------

# 9. Safety Layer

-   Joint limit enforcement
-   Velocity limit
-   Optional acceleration constraint
-   Prevent hyperextension

------------------------------------------------------------------------

# 10. 2D Lightweight Debug Mode

Canvas-only rendering Shared kinematic core Used for fast math
validation

------------------------------------------------------------------------

# 11. Validation Stages

1.  Static pose validation
2.  Servo sweep comparison
3.  Live telemetry mirror test
4.  IMU orientation verification
5.  Closed-loop foot position test

------------------------------------------------------------------------

# 12. Development Roadmap

1.  Define coordinate root transform
2.  Build 13-servo hierarchy
3.  Add axis visualizers
4.  Implement servo abstraction
5.  Integrate telemetry bridge
6.  Implement IK solver
7.  Add safety layer
8.  Modular refactor

------------------------------------------------------------------------

End of Document
