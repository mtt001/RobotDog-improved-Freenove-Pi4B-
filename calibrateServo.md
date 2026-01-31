# Servo Calibration Manual - calibrateServo.py  for calibration in Server... provided by copilot AI code

**Version:** 2.0.0  
**Date:** 2025-12-26  
**Author:** Freenove / Documentation Team

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start Guide](#quick-start-guide)
3. [Coordinate System](#coordinate-system)
4. [User Interface Guide](#user-interface-guide)
5. [Calibration Workflow](#calibration-workflow)
6. [Code Structure](#code-structure)
7. [Method Reference](#method-reference)
8. [Integration with Control System](#integration-with-control-system)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)

---

## Overview

### What is calibrateServo.py?

`calibrateServo.py` is an **interactive coordinate-based calibration tool** for the Freenove Robot Dog. 
Unlike traditional servo calibration that adjusts individual servo angles, this tool follows the **Freenove method** by adjusting leg positions using 3D cartesian coordinates (x, y, z).

### Why Coordinate-Based Calibration?

**Traditional Method (Angle-Based):**
- Adjust 12 individual servos (3 per leg × 4 legs)
- Difficult to visualize final leg position
- Hard to ensure symmetry between legs
- Requires understanding of servo mapping

**Freenove Method (Coordinate-Based):**
- Adjust 4 leg positions (one coordinate set per leg)
- Direct control of foot position in 3D space
- Easy to ensure left/right, front/rear symmetry
- Automatic conversion to servo angles using inverse kinematics

### Key Features

✅ **Loads existing calibration** from `point.txt`  
✅ **Real-time preview** of coordinate changes  
✅ **Fine & coarse adjustments** (±1mm or ±5mm)  
✅ **Saves to point.txt** (standard Freenove format)  
✅ **Audio/visual feedback** (beeps and LED)  
✅ **Reset to defaults** command  
✅ **Interactive console interface**

---

## Quick Start Guide

### Prerequisites

- Robot dog assembled with all 12 servos connected
- Raspberry Pi with Python 3
- Sudo privileges (for GPIO access to buzzer/LED)

### Basic Usage

**1. Start calibration with current settings:**
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
sudo python3 calibrateServo.py
```

**2. Reset to default neutral position:**
```bash
sudo python3 calibrateServo.py reset
```

### First-Time Calibration Steps

1. **Run the calibration tool:**
   ```bash
   sudo python3 calibrateServo.py
   ```

2. **Robot will automatically move to calibration posture** based on current `point.txt` (or defaults)

3. **Select a leg to calibrate** (options 1-4)

4. **Adjust coordinates** using interactive commands:
   - `y-` to lower leg if it's too high
   - `y+` to raise leg if it's too low
   - `x+` to move leg forward
   - `z+` to shift leg left
   - `apply` to preview changes

5. **Save calibration** (option 6)

6. **Exit** (option 9)

---

## Coordinate System

### Axis Definitions

```
        ↑ Y (Up/Down)
        │
        │         Positive Y = Up (raises leg)
        │         Negative Y = Down (lowers leg)
        │
        └─────────→ X (Forward/Backward)
       ╱
      ╱            Positive X = Forward
     ╱             Negative X = Backward
    ↙ Z (Left/Right)
                   Positive Z = Left
                   Negative Z = Right
```

### Coordinate Ranges

| Axis | Range | Default | Description |
|------|-------|---------|-------------|
| **X** | -50 to 50 mm | 0 mm | Forward(+) / Backward(-) position |
| **Y** | 70 to 120 mm | 99 mm | Leg height (up is positive) |
| **Z** | -30 to 30 mm | ±10 mm | Lateral offset (left/right) |

### Default Neutral Position

The default calibration position (before any adjustments):

| Leg # | Position | X | Y | Z | Notes |
|-------|----------|---|---|---|-------|
| **0** | Front-Left | 0 | 99 | 10 | Z=+10 (shifted left) |
| **1** | Front-Right | 0 | 99 | 10 | Z=+10 (shifted left) |
| **2** | Rear-Left | 0 | 99 | -10 | Z=-10 (shifted right) |
| **3** | Rear-Right | 0 | 99 | -10 | Z=-10 (shifted right) |

**Why Z offsets?**  
The Z values (±10mm) compensate for the leg mounting geometry and ensure the feet are positioned correctly under the body center.

---

## User Interface Guide

### Main Menu

```
📋 CALIBRATION MENU:
   1. Adjust Leg 0 (Front-Left) coordinates
   2. Adjust Leg 1 (Front-Right) coordinates
   3. Adjust Leg 2 (Rear-Left) coordinates
   4. Adjust Leg 3 (Rear-Right) coordinates
   5. Reset to default neutral position
   6. Save calibration to point.txt
   7. Show current calibration values
   8. Apply and preview current calibration
   9. Exit (release servos)

Select option (1-9): 
```

### Coordinate Adjustment Interface

When you select a leg (options 1-4), you enter the adjustment interface:

```
🎯 Adjusting Leg 0 (Front-Left)
   Current: X=0, Y=99, Z=10

   Commands:
     x+/x- : Adjust X coordinate (±1mm)
     y+/y- : Adjust Y coordinate (±1mm)
     z+/z- : Adjust Z coordinate (±1mm)
     X+/X- : Adjust X coordinate (±5mm)
     Y+/Y- : Adjust Y coordinate (±5mm)
     Z+/Z- : Adjust Z coordinate (±5mm)
     set   : Set exact values
     apply : Apply changes to servos
     q     : Return to main menu

   [Front-Left] X=  0 Y= 99 Z= 10 > 
```

### Command Reference

| Command | Action | Example |
|---------|--------|---------|
| `x+` | Increase X by 1mm | Move leg forward slightly |
| `x-` | Decrease X by 1mm | Move leg backward slightly |
| `y+` | Increase Y by 1mm | Raise leg by 1mm |
| `y-` | Decrease Y by 1mm | Lower leg by 1mm |
| `z+` | Increase Z by 1mm | Shift leg left by 1mm |
| `z-` | Decrease Z by 1mm | Shift leg right by 1mm |
| `X+` | Increase X by 5mm | Move leg forward significantly |
| `X-` | Decrease X by 5mm | Move leg backward significantly |
| `Y+` | Increase Y by 5mm | Raise leg significantly |
| `Y-` | Decrease Y by 5mm | Lower leg significantly |
| `Z+` | Increase Z by 5mm | Shift leg left significantly |
| `Z-` | Decrease Z by 5mm | Shift leg right significantly |
| `set` | Set exact X, Y, Z values | Manually enter coordinates |
| `apply` | Apply changes to servos | Preview the adjustment |
| `q` | Return to main menu | Exit adjustment mode |

### Feedback Indicators

**Audio Feedback (Buzzer):**
- **1 short beep:** Coordinate adjusted
- **2 beeps:** Exact values set or reset completed
- **3 beeps:** Calibration saved successfully

**Visual Feedback (LED):**
- **1 blue flash:** Applying calibration
- **2 blue flashes:** Calibration saved

---

## Calibration Workflow

### Step-by-Step Calibration Process

#### **Step 1: Prepare the Robot**

1. Place robot on a flat, level surface
2. Ensure all 12 servos are properly connected
3. Power on the robot
4. Connect via SSH or use directly on Raspberry Pi

#### **Step 2: Start Calibration Tool**

```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
sudo python3 calibrateServo.py
```

**On startup, you'll see:**
```
======================================================================
    Freenove Robot Dog - Coordinate Calibration (v2.0.0)
======================================================================

📐 COORDINATE SYSTEM:
   X-axis: Forward(+) / Backward(-), range: -50 to 50 mm
   Y-axis: Up(+) / Down(-), range: 70 to 120 mm  
   Z-axis: Left(+) / Right(-), range: -30 to 30 mm

🦿 LEG NUMBERING:
   0: Front-Left   1: Front-Right
   2: Rear-Left    3: Rear-Right

⚙️  Initializing and applying current calibration...
✓ Loaded calibration from point.txt
✓ Robot set to calibration posture
```

#### **Step 3: Assess Current Position**

**Select option 7** to view current calibration:
```
📊 CURRENT CALIBRATION:
   ============================================================
   Leg 0 (Front-Left ): X=  0, Y= 99, Z= 10
   Leg 1 (Front-Right): X= -1, Y= 88, Z= 21
   Leg 2 (Rear-Left  ): X=  2, Y= 95, Z= 11
   Leg 3 (Rear-Right ): X=  9, Y= 79, Z=-12
   ============================================================
```

**Observe the robot:**
- Are all legs at the same height? (Y values should be similar)
- Are legs tilting forward/backward? (check X values)
- Are legs too wide or too narrow? (check Z values)

#### **Step 4: Calibrate Each Leg**

**Example: Calibrating Front-Left leg (Leg 0)**

1. **Select option 1** from main menu

2. **Lower the leg if it's too high:**
   ```
   [Front-Left] X=  0 Y= 99 Z= 10 > y-
   [Front-Left] X=  0 Y= 98 Z= 10 > y-
   [Front-Left] X=  0 Y= 97 Z= 10 > apply
   ```
   
3. **Observe the robot** - did the leg reach the desired height?

4. **Continue adjusting:**
   ```
   [Front-Left] X=  0 Y= 97 Z= 10 > Y-    (lower by 5mm)
   [Front-Left] X=  0 Y= 92 Z= 10 > apply
   ```

5. **Fine-tune the position:**
   ```
   [Front-Left] X=  0 Y= 92 Z= 10 > y+
   [Front-Left] X=  0 Y= 93 Z= 10 > apply
   ```

6. **Return to menu:**
   ```
   [Front-Left] X=  0 Y= 93 Z= 10 > q
   ```

#### **Step 5: Repeat for Other Legs**

- **Leg 1 (Front-Right):** Option 2
- **Leg 2 (Rear-Left):** Option 3
- **Leg 3 (Rear-Right):** Option 4

**Pro tip:** Try to keep **Y values** (height) consistent across all legs for a level stance.

#### **Step 6: Save Calibration**

1. **Select option 6** from main menu
2. Confirmation message appears:
   ```
   ✅ Calibration saved to point.txt
   ```
3. Audio/visual feedback confirms save

#### **Step 7: Test Calibration**

1. **Exit calibration tool** (option 9)
2. **Run the main robot program:**
   ```bash
   sudo python3 main.py
   ```
3. **Test movements** (forward, backward, turn)
4. **If adjustments needed:** Re-run calibration tool

---

## Code Structure

### File Organization

```
calibrateServo.py
├── Imports (Servo, Buzzer, Led, Command)
├── ServoCalibrator class
│   ├── __init__()              # Initialize hardware and load calibration
│   ├── Helper methods          # Buzzer, LED, signal handlers
│   ├── File I/O methods        # Load/save point.txt
│   ├── Kinematics methods      # coordinateToAngle()
│   ├── Application methods     # apply_calibration()
│   ├── UI methods              # print_banner(), print_menu()
│   ├── Interactive methods     # adjust_leg_coordinates()
│   └── run()                   # Main loop
└── main()                      # Entry point with CLI argument handling
```

### Class: ServoCalibrator

**Purpose:** Manages the entire calibration process, from loading existing calibration to saving new values.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `self.servo` | Servo | Hardware interface to PCA9685 PWM driver |
| `self.buzzer` | Buzzer | Audio feedback device |
| `self.led` | Led | Visual feedback device (WS281x RGB LED) |
| `self.default_point` | list[list[int]] | Default neutral position coordinates |
| `self.calibration_point` | list[list[int]] | Current calibration coordinates (4 legs × XYZ) |
| `self.current_leg` | int | Currently selected leg for adjustment (0-3) |

#### Data Structure: calibration_point

```python
self.calibration_point = [
    [x0, y0, z0],   # Leg 0 (Front-Left)
    [x1, y1, z1],   # Leg 1 (Front-Right)
    [x2, y2, z2],   # Leg 2 (Rear-Left)
    [x3, y3, z3]    # Leg 3 (Rear-Right)
]
```

**Example:**
```python
[
    [0, 99, 10],    # Front-Left at X=0, Y=99, Z=10
    [-1, 88, 21],   # Front-Right offset
    [2, 95, 11],    # Rear-Left offset
    [9, 79, -12]    # Rear-Right offset
]
```

---

## Method Reference

### Initialization Methods

#### `__init__(self)`

**Purpose:** Initialize the calibrator, load hardware interfaces, and load existing calibration.

**Process:**
1. Initialize Servo, Buzzer, LED objects
2. Set default neutral position
3. Call `load_calibration()` to read point.txt
4. Register SIGINT handler for graceful shutdown

**Code Flow:**
```python
ServoCalibrator()
  → Servo()           # Initialize PCA9685 PWM driver
  → Buzzer()          # Initialize buzzer (GPIO)
  → Led()             # Initialize WS281x LED
  → load_calibration() # Load point.txt or use defaults
  → signal.signal()   # Register Ctrl+C handler
```

---

### File I/O Methods

#### `load_calibration(self) -> list[list[int]]`

**Purpose:** Load calibration coordinates from `point.txt`.

**File Format (point.txt):**
```
0	99	10	
-1	88	21	
2	95	11	
9	79	-12	
```
- Tab-separated values (`\t`)
- 4 lines (one per leg)
- 3 columns per line (X, Y, Z)

**Return Value:**
- Success: List of 4 coordinate sets `[[x0,y0,z0], [x1,y1,z1], ...]`
- Failure: Default neutral position `[[0,99,10], [0,99,10], [0,99,-10], [0,99,-10]]`

**Error Handling:**
- File not found → Use defaults
- Invalid format → Use defaults
- Parse error → Use defaults

**Code Example:**
```python
def load_calibration(self):
    try:
        if os.path.exists('point.txt'):
            with open('point.txt', 'r') as f:
                lines = f.readlines()
                calibration = []
                for line in lines:
                    values = line.strip().split('\t')
                    if len(values) >= 3:
                        calibration.append([int(values[0]), int(values[1]), int(values[2])])
                if len(calibration) == 4:
                    print("✓ Loaded calibration from point.txt")
                    return calibration
    except Exception as e:
        print(f"⚠️  Could not load point.txt: {e}")
    
    print("✓ Using default neutral position")
    return [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
```

#### `save_calibration(self) -> bool`

**Purpose:** Save current calibration coordinates to `point.txt`.

**Process:**
1. Open `point.txt` in write mode
2. Write 4 lines (one per leg)
3. Each line: `X\tY\tZ\t\n`
4. Emit audio/visual feedback on success

**Return Value:**
- `True` on success
- `False` on error

**Code Example:**
```python
def save_calibration(self):
    try:
        with open('point.txt', 'w') as f:
            for i in range(4):
                f.write(f"{self.calibration_point[i][0]}\t")
                f.write(f"{self.calibration_point[i][1]}\t")
                f.write(f"{self.calibration_point[i][2]}\t\n")
        print("\n✅ Calibration saved to point.txt")
        self._beep(count=3)
        self._flash_led(count=2)
        return True
    except Exception as e:
        print(f"\n❌ Failed to save calibration: {e}")
        return False
```

---

### Kinematics Methods

#### `coordinateToAngle(self, x, y, z, l1=23, l2=55, l3=55) -> tuple[int, int, int]`

**Purpose:** Convert cartesian foot position (x, y, z) to joint angles (a, b, c) using inverse kinematics.

**Parameters:**
- `x` (float): X coordinate (mm)
- `y` (float): Y coordinate (mm)
- `z` (float): Z coordinate (mm)
- `l1` (float): Hip link length (default 23mm)
- `l2` (float): Upper leg length (default 55mm)
- `l3` (float): Lower leg length (default 55mm)

**Returns:**
- `(a, b, c)` tuple of integers (degrees)
  - `a`: Hip angle (lateral rotation)
  - `b`: Shoulder angle
  - `c`: Knee angle

**Mathematical Model:**

```
        Body
         │
         │ (Hip - l1=23mm)
         ●────a (hip angle)
        ╱│
       ╱ │
   l2 ╱  │ b (shoulder angle)
     ╱   ●
    ╱   ╱│
   ╱   ╱ │
  ●   ╱  │ c (knee angle)
  │  ╱   │
  │ ╱ l3 │
  │╱     │
  ●──────┘
 Foot (x,y,z)
```

**Algorithm Steps:**

1. **Calculate hip angle (a):**
   ```python
   a = π/2 - atan2(z, y)
   ```
   This determines lateral leg rotation.

2. **Project into 2D plane:**
   ```python
   x_4 = l1 * sin(a)
   x_5 = l1 * cos(a)
   l23 = sqrt((z - x_5)² + (y - x_4)² + (x - 0)²)
   ```

3. **Calculate shoulder angle (b) using law of cosines:**
   ```python
   w = (x - 0) / l23
   v = (l2² + l23² - l3²) / (2 * l2 * l23)
   b = asin(w) - acos(v)
   ```

4. **Calculate knee angle (c) using law of cosines:**
   ```python
   c = π - acos((l2² + l3² - l23²) / (2 * l3 * l2))
   ```

5. **Convert radians to degrees and round**

**Code Implementation:**
```python
def coordinateToAngle(self, x, y, z, l1=23, l2=55, l3=55):
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

---

### Application Methods

#### `apply_calibration(self)`

**Purpose:** Convert current calibration coordinates to servo angles and apply to hardware.

**Process:**

1. **Initialize angle storage:**
   ```python
   angle = [[90, 0, 0], [90, 0, 0], [90, 0, 0], [90, 0, 0]]
   ```

2. **Convert all 4 legs from XYZ → ABC:**
   ```python
   for i in range(4):
       angle[i][0], angle[i][1], angle[i][2] = self.coordinateToAngle(
           self.calibration_point[i][0],
           self.calibration_point[i][1],
           self.calibration_point[i][2]
       )
   ```

3. **Apply servo-specific transformations:**

   **Front legs (0, 1):**
   ```python
   angle[i][0] = angle[i][0]           # Hip: direct
   angle[i][1] = 90 - angle[i][1]      # Shoulder: inverted
   angle[i][2] = angle[i][2]           # Knee: direct
   ```

   **Rear legs (2, 3):**
   ```python
   angle[i+2][0] = angle[i+2][0]           # Hip: direct
   angle[i+2][1] = 90 + angle[i+2][1]      # Shoulder: offset + value
   angle[i+2][2] = 180 - angle[i+2][2]     # Knee: mirrored
   ```

4. **Clamp angles to valid range (0-180°):**
   ```python
   angle[i][j] = max(0, min(180, angle[i][j]))
   ```

5. **Send to servos:**
   ```python
   # Front legs
   self.servo.setServoAngle(4+i*3, angle[i][0])  # Hip
   self.servo.setServoAngle(3+i*3, angle[i][1])  # Shoulder
   self.servo.setServoAngle(2+i*3, angle[i][2])  # Knee
   
   # Rear legs
   self.servo.setServoAngle(8+i*3, angle[i+2][0])  # Hip
   self.servo.setServoAngle(9+i*3, angle[i+2][1])  # Shoulder
   self.servo.setServoAngle(10+i*3, angle[i+2][2]) # Knee
   ```

**Servo Channel Mapping:**

| Leg | Position | Hip Servo | Shoulder Servo | Knee Servo |
|-----|----------|-----------|----------------|------------|
| 0 | Front-Left | 4 | 3 | 2 |
| 1 | Front-Right | 7 | 6 | 5 |
| 2 | Rear-Left | 8 | 9 | 10 |
| 3 | Rear-Right | 11 | 12 | 13 |

---

### Interactive Methods

#### `adjust_leg_coordinates(self, leg: int)`

**Purpose:** Provide interactive console interface for adjusting a single leg's coordinates.

**Parameters:**
- `leg` (int): Leg number (0-3)

**Commands Handled:**

| Command | Delta | Axis | Code |
|---------|-------|------|------|
| `x+` | +1mm | X | `self.calibration_point[leg][0] += 1` |
| `x-` | -1mm | X | `self.calibration_point[leg][0] -= 1` |
| `y+` | +1mm | Y | `self.calibration_point[leg][1] += 1` |
| `y-` | -1mm | Y | `self.calibration_point[leg][1] -= 1` |
| `z+` | +1mm | Z | `self.calibration_point[leg][2] += 1` |
| `z-` | -1mm | Z | `self.calibration_point[leg][2] -= 1` |
| `X+` | +5mm | X | `self.calibration_point[leg][0] += 5` |
| `X-` | -5mm | X | `self.calibration_point[leg][0] -= 5` |
| `Y+` | +5mm | Y | `self.calibration_point[leg][1] += 5` |
| `Y-` | -5mm | Y | `self.calibration_point[leg][1] -= 5` |
| `Z+` | +5mm | Z | `self.calibration_point[leg][2] += 5` |
| `Z-` | -5mm | Z | `self.calibration_point[leg][2] -= 5` |
| `set` | Manual | XYZ | Prompt for exact values |
| `apply` | - | - | Call `apply_calibration()` |
| `q` | - | - | Return to main menu |

**Validation:**
- X range: -50 to 50 mm
- Y range: 70 to 120 mm
- Z range: -30 to 30 mm

**Example Session:**
```
🎯 Adjusting Leg 0 (Front-Left)
   Current: X=0, Y=99, Z=10

   [Front-Left] X=  0 Y= 99 Z= 10 > y-
   [Front-Left] X=  0 Y= 98 Z= 10 > y-
   [Front-Left] X=  0 Y= 97 Z= 10 > Y-
   [Front-Left] X=  0 Y= 92 Z= 10 > apply
   📍 Applying calibration to servos...
   ✓ Applied
   [Front-Left] X=  0 Y= 92 Z= 10 > q
```

---

### UI Methods

#### `print_banner(self)`

Displays startup banner with coordinate system reference.

#### `print_current_calibration(self)`

Displays formatted table of current calibration values for all 4 legs.

#### `print_menu(self) -> str`

Returns the main menu text with 9 options.

---

### Main Loop

#### `run(self)`

**Purpose:** Main interactive loop for the calibration tool.

**Process:**

1. **Print banner**
2. **Apply current calibration** (set robot to posture)
3. **Enter menu loop:**
   - Display menu
   - Get user input (1-9)
   - Execute corresponding method
   - Repeat until option 9 (exit)
4. **On exit:** Release servos (disable PWM)

**Menu Option Mapping:**

| Option | Method | Description |
|--------|--------|-------------|
| 1 | `adjust_leg_coordinates(0)` | Adjust Front-Left |
| 2 | `adjust_leg_coordinates(1)` | Adjust Front-Right |
| 3 | `adjust_leg_coordinates(2)` | Adjust Rear-Left |
| 4 | `adjust_leg_coordinates(3)` | Adjust Rear-Right |
| 5 | `reset_to_default()` | Reset to neutral position |
| 6 | `save_calibration()` | Save to point.txt |
| 7 | `print_current_calibration()` | Show current values |
| 8 | `apply_calibration()` | Apply and preview |
| 9 | Exit | Release servos and quit |

---

## Integration with Control System

### How Control.py Uses point.txt

When the robot runs (`main.py` → `Control.py`), the calibration data is loaded and applied automatically:

#### **Control.py Initialization:**

```python
class Control:
    def __init__(self):
        # ... other initialization ...
        
        # Default neutral positions
        self.point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        
        # Load calibration from point.txt
        self.calibration_point = self.readFromTxt('point')
        
        # Calculate angle offsets
        self.calibration()
```

#### **Calibration Offset Calculation:**

```python
def calibration(self):
    # Step 1: Convert calibration points to angles
    for i in range(4):
        self.calibration_angle[i] = self.coordinateToAngle(
            self.calibration_point[i][0],
            self.calibration_point[i][1],
            self.calibration_point[i][2]
        )
    
    # Step 2: Convert default points to angles
    for i in range(4):
        self.angle[i] = self.coordinateToAngle(
            self.point[i][0],
            self.point[i][1],
            self.point[i][2]
        )
    
    # Step 3: Calculate offsets
    for i in range(4):
        self.calibration_angle[i] = self.calibration_angle[i] - self.angle[i]
```

#### **Runtime Application:**

Every time the robot moves (`Control.run()`), the calibration offsets are applied:

```python
def run(self):
    # Convert current leg positions to angles
    for i in range(4):
        self.angle[i] = self.coordinateToAngle(
            self.point[i][0],
            self.point[i][1],
            self.point[i][2]
        )
    
    # Apply calibration offsets
    for i in range(4):
        self.angle[i] += self.calibration_angle[i]
    
    # Send to servos
    # ...
```

### Data Flow Diagram

```
calibrateServo.py                    Control.py
─────────────────                    ──────────
                                     
User adjusts                         main.py starts
coordinates                          ↓
↓                                    Control.__init__()
apply_calibration()                  ↓
(preview)                            readFromTxt('point')
↓                                    ↓
save_calibration()  ───────────────> point.txt
                                     ↓
                                     calibration()
                                     (calculate offsets)
                                     ↓
                                     run()
                                     (apply offsets during motion)
```

---

## Troubleshooting

### Common Issues

#### **Issue 1: "Permission denied" error**

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/dev/i2c-1'
```

**Cause:** Script needs sudo privileges to access I2C (servos) and GPIO (buzzer/LED).

**Solution:**
```bash
sudo python3 calibrateServo.py
```

---

#### **Issue 2: Robot legs don't move**

**Symptom:** Coordinates change but servos don't respond.

**Possible Causes:**
1. **Servos not powered** - Check battery voltage
2. **I2C connection** - Check PCA9685 wiring
3. **Coordinate out of range** - Kinematics can't solve

**Solutions:**
1. Check battery: `cat /sys/class/power_supply/BAT0/voltage_now`
2. Test I2C: `i2cdetect -y 1` (should show 0x40)
3. Use smaller coordinate adjustments
4. Reset to defaults: `sudo python3 calibrateServo.py reset`

---

#### **Issue 3: point.txt not saving**

**Symptom:** Changes saved but disappear after restart.

**Possible Causes:**
1. **Wrong directory** - Running from different location
2. **Read-only filesystem** - SD card mounted read-only
3. **Insufficient permissions** - File owned by root

**Solutions:**
1. Check current directory: `pwd`
2. Verify writable: `touch test.txt && rm test.txt`
3. Check file permissions: `ls -l point.txt`

---

#### **Issue 4: Leg positions inconsistent**

**Symptom:** Calibration looks good but robot tilts during walking.

**Cause:** Calibration offsets only apply at neutral position; motion algorithms may need tuning.

**Solution:**
1. Ensure all Y values (height) are similar
2. Test with `python3 testServo.py calib` to verify neutral position
3. Recalibrate with robot on level surface
4. Check for mechanical issues (loose servos, worn gears)

---

#### **Issue 5: Servo reaches mechanical limit**

**Symptom:** Servo buzzes or won't move further; angle clamping to 0° or 180°.

**Cause:** Coordinate position requires servo angle outside 0-180° range.

**Solution:**
1. Reduce the coordinate value (especially Y)
2. Use `set` command to enter more moderate values
3. Check default ranges in code documentation
4. May need to adjust leg link lengths in code if hardware differs

---

### Debug Mode

To add debug output, modify `apply_calibration()` to print calculated angles:

```python
def apply_calibration(self):
    angle = [[90, 0, 0], [90, 0, 0], [90, 0, 0], [90, 0, 0]]
    
    for i in range(4):
        angle[i][0], angle[i][1], angle[i][2] = self.coordinateToAngle(
            self.calibration_point[i][0],
            self.calibration_point[i][1],
            self.calibration_point[i][2]
        )
        print(f"DEBUG Leg {i}: XYZ={self.calibration_point[i]} → ABC={angle[i]}")
    
    # ... rest of method ...
```

---

## Advanced Usage

### Batch Calibration from Script

Create a Python script to set specific calibration values:

```python
#!/usr/bin/env python3
from calibrateServo import ServoCalibrator

# Create calibrator
cal = ServoCalibrator()

# Set custom calibration
cal.calibration_point = [
    [0, 95, 10],    # Front-Left: lowered by 4mm
    [0, 95, 10],    # Front-Right: lowered by 4mm
    [0, 95, -10],   # Rear-Left: lowered by 4mm
    [0, 95, -10]    # Rear-Right: lowered by 4mm
]

# Apply and save
cal.apply_calibration()
cal.save_calibration()
```

### Automated Calibration Routine

Create a test pattern that cycles through positions:

```python
#!/usr/bin/env python3
import time
from calibrateServo import ServoCalibrator

cal = ServoCalibrator()

# Test pattern: raise and lower all legs
for y in range(95, 105, 2):  # Y from 95 to 105 in steps of 2
    print(f"Testing Y={y}")
    for i in range(4):
        cal.calibration_point[i][1] = y
    cal.apply_calibration()
    time.sleep(2)
```

### Export/Import Calibration

**Export to JSON:**
```python
import json

cal = ServoCalibrator()
with open('calibration_backup.json', 'w') as f:
    json.dump(cal.calibration_point, f, indent=2)
```

**Import from JSON:**
```python
import json

cal = ServoCalibrator()
with open('calibration_backup.json', 'r') as f:
    cal.calibration_point = json.load(f)
cal.save_calibration()
```

---

## Appendix

### File Format Specification: point.txt

**Format:** Tab-separated values (TSV)  
**Encoding:** UTF-8 or ASCII  
**Line Ending:** Unix (LF) or Windows (CRLF)

**Structure:**
```
<X0><TAB><Y0><TAB><Z0><TAB><LF>
<X1><TAB><Y1><TAB><Z1><TAB><LF>
<X2><TAB><Y2><TAB><Z2><TAB><LF>
<X3><TAB><Y3><TAB><Z3><TAB><LF>
```

**Example:**
```
0	99	10	
-1	88	21	
2	95	11	
9	79	-12	
```

**Constraints:**
- Exactly 4 lines
- Each line: 3 integer values
- Values separated by tab character (`\t`)
- Optional trailing tab and newline

---

### Related Documentation

- [calibration_Explain.md](calibration_Explain.md) - How calibration affects servo motion
- [testServo.py](testServo.py) - Servo testing utility with `calib` command
- [Control.py](Control.py) - Main motion control system
- [Servo.py](Servo.py) - Low-level servo interface

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12-26 | Complete rewrite for coordinate-based calibration |
| 1.0.0 | 2025-12-25 | Initial angle-based calibration |

---

**End of Manual**
