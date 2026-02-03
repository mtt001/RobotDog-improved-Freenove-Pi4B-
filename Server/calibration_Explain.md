# Robot Dog Servo Calibration System

**Version:** 1.0.0  
**Date:** 2025-12-26  
**Author:** System Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Calibration Data Structure](#calibration-data-structure)
3. [System Architecture](#system-architecture)
4. [Calibration Workflow](#calibration-workflow)
5. [Mathematical Details](#mathematical-details)
6. [Practical Example: Move Forward](#practical-example-move-forward)
7. [Servo Mapping](#servo-mapping)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Servo Calibration?

The Freenove Robot Dog uses 12 servo motors (3 per leg × 4 legs) to control movement. Due to manufacturing tolerances, assembly variations, and mechanical wear, each servo may not respond identically to the same angle command. **Calibration** compensates for these hardware inconsistencies by applying individual offset corrections to each servo.

### Why Calibration is Critical

**Without calibration:**
- Legs reach different heights when commanded to the same position
- Robot tilts or leans to one side during walking
- Uneven gait causes instability and stumbling
- Coordinated movements appear jerky or asymmetric

**With calibration:**
- All four legs move in perfect synchronization
- Robot maintains level posture during motion
- Smooth, natural walking gait
- Precise positioning for complex movements

---

## Calibration Data Structure

### File: `point.txt`

The calibration data is stored in a simple tab-separated text file:

```text
0	99	10	
-1	88	21	
2	95	11	
9	79	-12	
```

### Data Format

Each line represents one leg's calibration point in 3D cartesian space:

| Line | Leg Position    | X (mm) | Y (mm) | Z (mm) | Description |
|------|-----------------|--------|--------|--------|-------------|
| 0    | Front-Left      | 0      | 99     | 10     | Hip, shoulder, knee offset point |
| 1    | Front-Right     | -1     | 88     | 21     | Hip, shoulder, knee offset point |
| 2    | Rear-Left       | 2      | 95     | 11     | Hip, shoulder, knee offset point |
| 3    | Rear-Right      | 9      | 79     | -12    | Hip, shoulder, knee offset point |

**Coordinate System:**
- **X-axis**: Forward/backward (positive = forward)
- **Y-axis**: Up/down (positive = up from body)
- **Z-axis**: Left/right (positive = left, negative = right)

### Reference Position

The default neutral position (before calibration) is:
```python
self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
#             Front-L      Front-R       Rear-L        Rear-R
```

**The calibration points in `point.txt` represent deviations from this neutral position.**

---

## System Architecture

### Module Interaction

```
┌─────────────────┐
│   Command.py    │ ← User/network commands
│  (CMD_MOVE_*)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Control.py    │ ← Main controller (THIS MODULE)
│                 │
│ • Load point.txt│
│ • Calculate     │
│   calibration   │
│ • Apply offsets │
│ • Motion logic  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Servo.py     │ ← Hardware abstraction
│  (PCA9685 PWM)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  12 Physical    │
│  Servo Motors   │
└─────────────────┘
```

---

## Calibration Workflow

### Phase 1: Initialization (Control.__init__)

**File:** `Control.py`, Lines 28-52

```python
def __init__(self):
    self.imu = IMU()
    self.servo = Servo()
    self.pid = Incremental_PID(0.5, 0.0, 0.0025)
    
    # Default neutral positions
    self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
    
    # Load calibration data from point.txt
    self.calibration_point = self.readFromTxt('point')  # ← Load file
    
    # Storage for computed angle offsets
    self.angle = [[90,0,0], [90,0,0], [90,0,0], [90,0,0]]
    self.calibration_angle = [[0,0,0], [0,0,0], [0,0,0], [0,0,0]]
    
    # Calculate calibration angle offsets
    self.calibration()  # ← Compute offsets
    self.relax(True)     # Set robot to relax position
```

### Phase 2: Load Calibration Data

**File:** `Control.py`, Lines 54-66

```python
def readFromTxt(self, filename):
    """Read tab-separated calibration data from file."""
    file1 = open(filename + ".txt", "r")
    list_row = file1.readlines()
    list_source = []
    
    for i in range(len(list_row)):
        column_list = list_row[i].strip().split("\t")  # Split by tab
        list_source.append(column_list)
    
    # Convert strings to integers
    for i in range(len(list_source)):
        for j in range(len(list_source[i])):
            list_source[i][j] = int(list_source[i][j])
    
    file1.close()
    return list_source
```

**Result:**
```python
self.calibration_point = [
    [0, 99, 10],    # Leg 0
    [-1, 88, 21],   # Leg 1
    [2, 95, 11],    # Leg 2
    [9, 79, -12]    # Leg 3
]
```

### Phase 3: Calculate Angle Offsets

**File:** `Control.py`, Lines 102-115

```python
def calibration(self):
    """Convert XYZ calibration points to angle offsets."""
    
    # Step 1: Convert calibration points (XYZ) → angles (ABC)
    for i in range(4):
        self.calibration_angle[i][0], \
        self.calibration_angle[i][1], \
        self.calibration_angle[i][2] = self.coordinateToAngle(
            self.calibration_point[i][0],
            self.calibration_point[i][1],
            self.calibration_point[i][2]
        )
    
    # Step 2: Convert default neutral points (XYZ) → angles (ABC)
    for i in range(4):
        self.angle[i][0], \
        self.angle[i][1], \
        self.angle[i][2] = self.coordinateToAngle(
            self.point[i][0],
            self.point[i][1],
            self.point[i][2]
        )
    
    # Step 3: Calculate difference (offset) = calibration - default
    for i in range(4):
        self.calibration_angle[i][0] = self.calibration_angle[i][0] - self.angle[i][0]
        self.calibration_angle[i][1] = self.calibration_angle[i][1] - self.angle[i][1]
        self.calibration_angle[i][2] = self.calibration_angle[i][2] - self.angle[i][2]
```

**Example Calculation:**

For **Leg 0** with calibration point `[0, 99, 10]`:

1. **Convert to angles** (using inverse kinematics):
   ```
   coordinateToAngle(0, 99, 10) → (87°, 50°, 80°)
   ```

2. **Default neutral position** `[0, 99, 10]`:
   ```
   coordinateToAngle(0, 99, 10) → (90°, 45°, 90°)
   ```

3. **Calculate offset**:
   ```python
   calibration_angle[0] = [87° - 90°, 50° - 45°, 80° - 90°]
                        = [-3°, 5°, -10°]
   ```

For **Leg 1** with calibration point `[-1, 88, 21]`:
```
coordinateToAngle(-1, 88, 21) → (92°, 42°, 88°)
coordinateToAngle(0, 99, 10)  → (90°, 45°, 90°)
Offset: [2°, -3°, -2°]
```

**Final calibration_angle array:**
```python
self.calibration_angle = [
    [-3,  5, -10],   # Leg 0 offsets (degrees)
    [ 2, -3,  -2],   # Leg 1 offsets
    [ 1,  2,  -5],   # Leg 2 offsets (example)
    [ 4, -1,   3]    # Leg 3 offsets (example)
]
```

### Phase 4: Apply Calibration During Motion

**File:** `Control.py`, Lines 116-137

Every time `run()` is called (hundreds of times during walking), calibration offsets are applied:

```python
def run(self):
    """Convert leg positions to servo angles and apply calibration."""
    
    if self.checkPoint():  # Verify coordinates are within valid range
        try:
            # Convert current leg positions (XYZ) → joint angles (ABC)
            for i in range(4):
                self.angle[i][0], \
                self.angle[i][1], \
                self.angle[i][2] = self.coordinateToAngle(
                    self.point[i][0],
                    self.point[i][1],
                    self.point[i][2]
                )
            
            # Apply calibration offsets and servo-specific transformations
            for i in range(2):
                # Front legs (0, 1)
                self.angle[i][0] = self.restriction(
                    self.angle[i][0] + self.calibration_angle[i][0], 0, 180
                )
                self.angle[i][1] = self.restriction(
                    90 - (self.angle[i][1] + self.calibration_angle[i][1]), 0, 180
                )
                self.angle[i][2] = self.restriction(
                    self.angle[i][2] + self.calibration_angle[i][2], 0, 180
                )
                
                # Rear legs (2, 3)
                self.angle[i+2][0] = self.restriction(
                    self.angle[i+2][0] + self.calibration_angle[i+2][0], 0, 180
                )
                self.angle[i+2][1] = self.restriction(
                    90 + self.angle[i+2][1] + self.calibration_angle[i+2][1], 0, 180
                )
                self.angle[i+2][2] = self.restriction(
                    180 - (self.angle[i+2][2] + self.calibration_angle[i+2][2]), 0, 180
                )
            
            # Send calibrated angles to physical servos
            for i in range(2):
                self.servo.setServoAngle(4+i*3, self.angle[i][0])      # Hip
                self.servo.setServoAngle(3+i*3, self.angle[i][1])      # Shoulder
                self.servo.setServoAngle(2+i*3, self.angle[i][2])      # Knee
                self.servo.setServoAngle(8+i*3, self.angle[i+2][0])    # Hip
                self.servo.setServoAngle(9+i*3, self.angle[i+2][1])    # Shoulder
                self.servo.setServoAngle(10+i*3, self.angle[i+2][2])   # Knee
                
        except Exception as e:
            pass
    else:
        print("This coordinate point is out of the active range")
```

---

## Mathematical Details

### Inverse Kinematics: coordinateToAngle()

**File:** `Control.py`, Lines 75-88

Converts cartesian coordinates (x, y, z) to joint angles (a, b, c):

```python
def coordinateToAngle(self, x, y, z, l1=23, l2=55, l3=55):
    """
    Inverse kinematics for 3-DOF leg.
    
    Args:
        x, y, z: Target foot position (mm)
        l1: Hip link length (23mm)
        l2: Upper leg length (55mm)
        l3: Lower leg length (55mm)
    
    Returns:
        (a, b, c): Joint angles in degrees
            a: Hip angle (lateral)
            b: Shoulder angle
            c: Knee angle
    """
    # Hip angle (lateral rotation)
    a = math.pi/2 - math.atan2(z, y)
    
    # Project leg into 2D plane
    x_3 = 0
    x_4 = l1 * math.sin(a)
    x_5 = l1 * math.cos(a)
    
    # Distance from hip to foot in 2D
    l23 = math.sqrt((z - x_5)**2 + (y - x_4)**2 + (x - x_3)**2)
    
    # Shoulder angle using law of cosines
    w = (x - x_3) / l23
    v = (l2*l2 + l23*l23 - l3*l3) / (2 * l2 * l23)
    b = math.asin(round(w, 2)) - math.acos(round(v, 2))
    
    # Knee angle
    c = math.pi - math.acos(round((l2**2 + l3**2 - l23**2) / (2 * l3 * l2), 2))
    
    # Convert radians to degrees
    a = round(math.degrees(a))
    b = round(math.degrees(b))
    c = round(math.degrees(c))
    
    return a, b, c
```

**Leg Geometry:**
```
        Body
         │
         │ (Hip - l1=23mm)
         ●────a
        ╱│
       ╱ │
   l2 ╱  │ b (Shoulder)
     ╱   ●
    ╱   ╱│
   ╱   ╱ │
  ●   ╱  │ c (Knee)
  │  ╱   │
  │ ╱ l3 │
  │╱     │
  ●──────┘
 Foot (x,y,z)
```

### Angle Transformations

Due to different mounting orientations, front and rear legs use different formulas:

#### Front Legs (Legs 0, 1):
```python
angle_a = uncalibrated_a + calibration_offset_a
angle_b = 90 - (uncalibrated_b + calibration_offset_b)
angle_c = uncalibrated_c + calibration_offset_c
```

#### Rear Legs (Legs 2, 3):
```python
angle_a = uncalibrated_a + calibration_offset_a
angle_b = 90 + uncalibrated_b + calibration_offset_b
angle_c = 180 - (uncalibrated_c + calibration_offset_c)
```

These transformations account for:
- **Servo mounting direction** (front vs rear servos face opposite directions)
- **Mechanical zero position** (90° for shoulders, 180° mirroring for knees)
- **Coordinate frame transformations** (body frame to leg frame)

---

## Practical Example: Move Forward

### Command Flow

```
USER COMMAND: "Move Forward" at speed 8
         ↓
    Control.condition() receives CMD_MOVE_FORWARD
         ↓
    Control.forWard() generates gait trajectory
         ↓
    Loop 45 times (90° to 450° in 8° steps)
```

### Frame-by-Frame Breakdown

**Iteration 1: i=90°**

1. **Calculate foot positions**:
   ```python
   X1 = 12 * cos(90°) = 0 mm
   Y1 = 6 * sin(90°) + 99 = 105 mm
   X2 = 12 * cos(270°) = 0 mm
   Y2 = 6 * sin(270°) + 99 = 93 mm (clamped to 99)
   ```

2. **Update leg coordinates**:
   ```python
   self.point[0] = [10, 105, 10]   # Front-left
   self.point[1] = [10, 99, 10]    # Front-right
   self.point[2] = [10, 105, -10]  # Rear-left
   self.point[3] = [10, 99, -10]   # Rear-right
   ```

3. **Convert to joint angles** (uncalibrated):
   ```python
   coordinateToAngle(10, 105, 10) → (91°, 46°, 89°)  # Leg 0
   coordinateToAngle(10, 99, 10)  → (90°, 45°, 90°)  # Leg 1
   coordinateToAngle(10, 105, -10) → (89°, 46°, 89°) # Leg 2
   coordinateToAngle(10, 99, -10)  → (90°, 45°, 90°) # Leg 3
   ```

4. **Apply calibration offsets**:
   ```python
   # Leg 0: [-3°, 5°, -10°]
   Calibrated: (91-3, 90-(46+5), 89-10) = (88°, 39°, 79°)
   
   # Leg 1: [2°, -3°, -2°]
   Calibrated: (90+2, 90-(45-3), 90-2) = (92°, 48°, 88°)
   
   # Leg 2: [1°, 2°, -5°]
   Calibrated: (89+1, 90+(46+2), 180-(89-5)) = (90°, 138°, 96°)
   
   # Leg 3: [4°, -1°, 3°]
   Calibrated: (90+4, 90+(45-1), 180-(90+3)) = (94°, 134°, 87°)
   ```

5. **Command servos**:
   ```python
   Servo 4 → 88°   (Leg 0 hip)
   Servo 3 → 39°   (Leg 0 shoulder)
   Servo 2 → 79°   (Leg 0 knee)
   Servo 7 → 92°   (Leg 1 hip)
   Servo 6 → 48°   (Leg 1 shoulder)
   Servo 5 → 88°   (Leg 1 knee)
   ... (rear legs)
   ```

**Iteration 2: i=98°**

1. **New foot positions**:
   ```python
   X1 = 12 * cos(98°) = -1.67 mm
   Y1 = 6 * sin(98°) + 99 = 104.9 mm
   ```

2. **Same calibration offsets applied** (offsets never change)

3. Servos move smoothly to new positions

**...continues for 45 iterations...**

### Gait Pattern

```
Front Legs:  ●───────○        ○───────●
            Lift    Swing    Plant   Drag

Rear Legs:   ○───────●        ●───────○
            Plant   Drag     Lift    Swing

Timeline:    0°      90°      180°    270°    360°
```

The circular trajectory creates natural alternating gait:
- **0°-180°**: Front legs swing forward, rear legs push
- **180°-360°**: Front legs push, rear legs swing forward

---

## Servo Mapping

### Physical Servo Channels

| Servo | Leg Position   | Joint    | Function |
|-------|----------------|----------|----------|
| 2     | Front-Left     | Knee     | Extend/flex lower leg |
| 3     | Front-Left     | Shoulder | Raise/lower leg |
| 4     | Front-Left     | Hip      | Rotate leg laterally |
| 5     | Front-Right    | Knee     | Extend/flex lower leg |
| 6     | Front-Right    | Shoulder | Raise/lower leg |
| 7     | Front-Right    | Hip      | Rotate leg laterally |
| 8     | Rear-Left      | Hip      | Rotate leg laterally |
| 9     | Rear-Left      | Shoulder | Raise/lower leg |
| 10    | Rear-Left      | Knee     | Extend/flex lower leg |
| 11    | Rear-Right     | Hip      | Rotate leg laterally |
| 12    | Rear-Right     | Shoulder | Raise/lower leg |
| 13    | Rear-Right     | Knee     | Extend/flex lower leg |

### Servo to Leg Mapping in Code

```python
# Code from Control.run(), lines 131-137
for i in range(2):
    # Front legs (i=0 → Leg 0, i=1 → Leg 1)
    self.servo.setServoAngle(4+i*3, self.angle[i][0])      # Servo 4, 7 (Hip)
    self.servo.setServoAngle(3+i*3, self.angle[i][1])      # Servo 3, 6 (Shoulder)
    self.servo.setServoAngle(2+i*3, self.angle[i][2])      # Servo 2, 5 (Knee)
    
    # Rear legs (i=0 → Leg 2, i=1 → Leg 3)
    self.servo.setServoAngle(8+i*3, self.angle[i+2][0])    # Servo 8, 11 (Hip)
    self.servo.setServoAngle(9+i*3, self.angle[i+2][1])    # Servo 9, 12 (Shoulder)
    self.servo.setServoAngle(10+i*3, self.angle[i+2][2])   # Servo 10, 13 (Knee)
```

---

## Troubleshooting

### Symptom: Robot tilts to one side

**Cause:** Calibration offsets incorrect for one or more legs

**Solution:**
1. Use `CMD_CALIBRATION` command to adjust individual leg positions
2. Save updated calibration with `CMD_CALIBRATION save`
3. Restart robot to reload `point.txt`

### Symptom: One leg doesn't move properly

**Possible causes:**
1. **Servo mechanical failure** - Check servo physically
2. **Servo channel wrong** - Verify servo mapping
3. **Calibration offset too large** - Reset `point.txt` to neutral values

### Symptom: Jerky motion during walking

**Cause:** Calibration offsets causing servo angle clamping (0-180° limits)

**Solution:**
1. Check if `self.restriction()` is clamping angles to 0° or 180°
2. Reduce calibration offset magnitudes in `point.txt`
3. Verify leg coordinate calculations aren't exceeding mechanical limits

### How to Recalibrate

**Method 1: Manual Calibration (using calibrateServo.py)**
```bash
python3 calibrateServo.py
# Use interactive mode to adjust each servo
# Save to JSON profile
```

**Method 2: Network Calibration (using Server.py)**
```python
# Send calibration command via network
CMD_CALIBRATION one X Y Z    # Adjust leg 0
CMD_CALIBRATION two X Y Z    # Adjust leg 1
CMD_CALIBRATION three X Y Z  # Adjust leg 2
CMD_CALIBRATION four X Y Z   # Adjust leg 3
CMD_CALIBRATION save         # Write to point.txt
```

**Method 3: Direct Edit**
```bash
nano point.txt
# Edit coordinates manually
# Restart robot
```

### Calibration Best Practices

1. **Start with neutral values**:
   ```text
   0	99	10
   0	99	10
   0	99	-10
   0	99	-10
   ```

2. **Adjust one leg at a time** - Easier to isolate issues

3. **Small increments** - Change by ±1-2mm per iteration

4. **Test after each change** - Run forward/backward to verify

5. **Document changes** - Keep notes on what values work best

---

## Related Files

| File | Purpose |
|------|---------|
| `Control.py` | Main controller, applies calibration |
| `point.txt` | Calibration data storage |
| `Servo.py` | Hardware abstraction, PWM control |
| `calibrateServo.py` | Interactive calibration tool |
| `Action.py` | Pre-programmed movement sequences |
| `Command.py` | Command definitions |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-26 | Initial documentation - comprehensive calibration system explanation |

---

**End of Document**
