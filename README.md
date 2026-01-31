# Freenove Robot Dog Client - Architecture & Development Guide

```
╔══════════════════════════════════════════════════════════════════════════╗
║                 FREENOVE ROBOT DOG - CLIENT APPLICATION                  ║
║                     Desktop Control & Video Streaming                    ║
╚══════════════════════════════════════════════════════════════════════════╝

Project      : Freenove Robot Dog Kit for Raspberry Pi - Client Software
Version      : 1.21 (Main.py), 1.16 (Client.py)
Platform     : macOS / Linux / Windows
Language     : Python 3.7+
Framework    : PyQt5, OpenCV, NumPy
Setup        : Virtual Environment (~/.venvs/freenove-client) + smartdog alias

Authors      : MT & GitHub Copilot
Created      : 2024-10-15 (Original Freenove codebase)
Revised      : 2025-11-17 (Current architecture documentation)
Updated      : 2025-12-28 (Virtual environment & smartdog setup documentation)
Maintainers  : MT (Lead Developer), GitHub Copilot (AI Assistant)

Repository   : /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/
License      : See main project LICENSE file
Contact      : [Project repository issues]

Purpose      : This README documents the client-side architecture, threading
               model, communication protocols, development guidelines, and
               setup instructions for the Freenove Robot Dog desktop application.

Last Updated : 2025-12-28 17:00 PST
Status       : Production (v1.20) - Actively Maintained
Setup Status : ✅ Virtual environment configured with smartdog alias
```

---

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
  - [Network Topology](#network-topology)
  - [Communication Protocols](#communication-protocols)
- [File Hierarchy](#file-hierarchy)
- [Key Components](#key-components)
  - [Main.py (v1.20)](#mainpy-v120)
  - [Client.py (v1.15)](#clientpy-v115)
- [Feature Modules](#feature-modules)
  - [1. Face Recognition Module](#1-face-recognition-module)
  - [2. Ball Tracking Module](#2-ball-tracking-module)
  - [3. LED Control Module](#3-led-control-module)
  - [4. Servo Calibration Module](#4-servo-calibration-module)
- [Common Workflows](#common-workflows)
- [Revision History](#revision-history)
- [Threading Model](#threading-model)
- [Video Pipeline](#video-pipeline)
- [Telemetry System](#telemetry-system)
- [Development Guidelines](#development-guidelines)
- [Error Codes Reference](#error-codes-reference)
- [Troubleshooting](#troubleshooting)
- [Related Files](#related-files)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**Application**: Desktop PyQt5 client for controlling the Freenove Robot Dog  
**Platform**: macOS / Linux / Windows  
**Language**: Python 3.7+  
**Current Version**: Main.py v1.20, Client.py v1.15

This client provides:
- Real-time video streaming (MJPEG over TCP, 15-30 FPS)
- Bidirectional command/telemetry channel (text protocol)
- Robot motion control (WASD keys + GUI buttons)
- Sensor monitoring (ultrasonic distance, battery voltage, IMU)
- Feature modules (face recognition, ball tracking, LED control, servo calibration)
- In-app debug viewer for video pipeline diagnostics (press T or F10)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.7+ with virtual environment (already configured)
# Dependencies: PyQt5, opencv-python, numpy (installed in venv)

# macOS users: Qt5 may be needed
brew install qt@5
export PATH="/usr/local/opt/qt@5/bin:$PATH"
```

### Virtual Environment Setup

The project uses a dedicated Python virtual environment located at `~/.venvs/freenove-client`.

#### Activate venv (recommended way)

From **any directory**, type:
```bash
smartdog
```

This alias will:
- ✅ Activate the `freenove-client` virtual environment
- 📂 Navigate to the Client directory
- 🐚 Start a new interactive shell with venv active
- 📍 Prompt shows `((freenove-client))` when active

#### Deactivate venv

```bash
# Exit the venv shell
exit
# or use Ctrl+D
```

#### Manual activation (alternative method)

If `smartdog` doesn't work, use manual activation:
```bash
source ~/.venvs/freenove-client/bin/activate
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client
```

### How the `smartdog` Alias Works

The `smartdog` command runs `~/launch_smartdog.sh`:
```bash
#!/bin/bash
source ~/.venvs/freenove-client/bin/activate
cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client
echo "✅ Freenove client venv activated"
echo "📂 Working directory: $(pwd)"
exec $SHELL
```

**Key mechanics:**
- `source` activates venv in the current shell environment
- `exec $SHELL` replaces the script with a new shell, preserving venv activation
- Works from any directory in your system

### First-Time Setup

1. **Activate Environment**:
   ```bash
   smartdog
   ```

2. **Configure Robot IP**:
   - Default IP: `192.168.1.100`
   - Edit `IP.txt` or enter IP in the GUI dialog

3. **Launch Client**:
   ```bash
   python mtDogMain.py
   # or for original version:
   python Main.py
   ```

4. **Connect to Robot**:
   - Enter robot IP address (e.g., `192.168.1.150`)
   - Click **Connect** button
   - Video should auto-start within 1-2 seconds
   - Battery voltage indicator appears in top-right corner

### Keyboard Controls

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| `W` | Forward | `A` | Turn Left |
| `S` | Backward | `D` | Turn Right |
| `Q` | Step Left | `E` | Step Right |
| `Space` | Stop | `R` | Relax (sit) |
| `T` / `F10` | Open Debug Window | `Esc` | Close Dialogs |

### Debug Mode

Enable detailed logging for troubleshooting:

```python
# In Main.py (lines ~90-95), set:
self.debug_ui_enabled = True   # Show GUI debug prints
self.debug_rx_enabled = True   # Show network debug prints
```

Console output example:
```
[DEBUG][GUI] refresh_image: FPS=28.3, latency=35ms
[DEBUG][RX] Power#8.15#
[DEBUG][RX] Sonic#42.7#
```

---

## 🏗️ System Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Client (Main.py)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Qt Main Thread (GUI)                                  │ │
│  │    - Event loop, painting, user input                  │ │
│  │    - QTimer callbacks (refresh_image, power, sonic)    │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │                                        │
│  ┌──────────────────▼──────────────┐  ┌──────────────────┐  │
│  │  Video Receive Thread           │  │ Instruction Thread│  │
│  │  (Client.receiving_video)       │  │ (receive_instr.)  │  │
│  │   - Port 8001                   │  │  - Port 5001      │  │
│  │   - Decodes JPEG frames         │  │  - Text protocol  │  │
│  │   - Writes to Client.image      │  │  - Parses commands│  │
│  └─────────────────────────────────┘  └──────────────────┘  │
│                     │                           │            │
│                     └───────────┬───────────────┘            │
│                                 ▼                            │
│                      Shared State (Client.py)               │
│                      - image (numpy BGR)                    │
│                      - image_lock (threading.Lock)          │
│                      - video_flag (bool)                    │
│                      - video_last_frame_ts (float)          │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 │ TCP/IP
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 Raspberry Pi Robot Dog (Server)             │
│  ┌────────────────┐              ┌────────────────────────┐ │
│  │  Video Server  │              │  Command Server        │ │
│  │  Port 8001     │◄────────────►│  Port 5001             │ │
│  │  (MJPEG stream)│              │  (Text protocol)       │ │
│  └────────────────┘              └────────────────────────┘ │
│         │                                   │               │
│         ▼                                   ▼               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     Robot Control Layer (Servo, IMU, Sensors)       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Communication Protocols

#### Port 5001: Command/Telemetry (Text-based)

```
Direction: Bidirectional
Format:    CMD_NAME#param1#param2#...\n

Examples (Client → Robot):
  CMD_MOVE_FORWARD#8\n          → Move forward at speed 8
  CMD_HEAD#90\n                 → Set head servo to 90°
  CMD_SONIC\n                   → Request distance reading
  CMD_FACE_DETECT\n             → Enable face tracking
  CMD_BALL_TRACK\n              → Enable ball tracking
  CMD_LED#255#128#0\n           → Set LED RGB color

Examples (Robot → Client):
  Power#8.12#\n                 → Battery voltage
  Sonic#45.3#\n                 → Distance in cm
  WorkingTime#1234#\n           → Uptime in seconds
  FaceDetect#1#120#80#\n        → Face found at (x,y)
```

#### Port 8001: Video Stream (Binary)

```
Direction: Robot → Client (unidirectional)
Format:    <4-byte length><JPEG data><4-byte length><JPEG data>...

Frame Structure:
  [0:4]   uint32_t (little-endian) = JPEG payload size
  [4:N]   JPEG compressed image data
  
Example:
  b'\x42\x1f\x00\x00'  → Frame size = 7,986 bytes
  b'\xff\xd8\xff...'   → JPEG starts with FF D8 FF
```

---

## 📁 File Hierarchy

```
Client/
├── Main.py                    # Main GUI window (v1.20)
│   ├── MyWindow               # Main application window
│   ├── faceWindow             # Face recognition UI
│   ├── calibrationWindow      # Servo calibration UI
│   └── ledWindow              # LED control UI
│
├── Client.py                  # Network client & shared state (v1.15)
│   ├── Client                 # Core client class
│   │   ├── receiving_video()  # Video receive thread (port 8001)
│   │   ├── send_data()        # Command sender (port 5001)
│   │   ├── turn_on_client()   # Connection manager
│   │   └── turn_off_client()  # Cleanup
│   └── cmd                    # Command constants (CMD_MOVE_*, etc.)
│
├── testVideoStream.py         # Debug viewer (standalone + embedded)
│   ├── DebugStreamWindow      # In-app diagnostic window
│   └── draw_top_bar()         # Overlay rendering (FPS, battery, etc.)
│
├── Calibration.py             # Servo offset manager
│   └── Ui_calibration         # PyQt5 designer output
│
├── ui_client.py               # Main window UI layout
├── ui_led.py                  # LED window UI layout
├── ui_face.py                 # Face window UI layout
│
└── Picture/                   # Asset files
    ├── dog_client.png         # Startup splash screen
    └── logo_Mini.png          # Application icon
```

---

## 🔑 Key Components

### Main.py (v1.20)

**Purpose**: PyQt5 GUI application  
**Key Responsibilities**:
- User interface rendering and event handling
- Video frame display pipeline (QLabel painting)
- Keyboard/mouse input processing
- Timer-based refresh loops (video, telemetry, debug)
- Window management (main, debug, calibration, LED, face)

**Critical Methods**:

| Method | Purpose | Timing |
|--------|---------|--------|
| `refresh_image()` | Consumes frames from `Client.image`, draws overlays, updates QLabel | Every 33ms (≈30 FPS) |
| `receive_instruction()` | Listens on port 5001 for telemetry (battery, distance) | Runs in thread until disconnect |
| `_overlay_refresh_if_stalled()` | Redraws status bar when no new frames arrive | Every 500ms |
| `connect()` | Initiates TCP connections, starts threads, validates success | User-triggered |
| `closeEvent()` | Graceful shutdown: stops threads, closes sockets | Window close |

**State Variables**:

```python
self.client.image          # Latest BGR frame (numpy array)
self.client.image_lock     # Protects image reads/writes
self.client.video_flag     # False = new frame ready; True = consumed
self._last_frame_bgr       # Cached frame for stall handling
self.tele_batt_v           # Battery voltage (float)
self.tele_dist_cm          # Ultrasonic distance (float)
self._fps                  # Smoothed display framerate
```

---

### Client.py (v1.15)

**Purpose**: Network layer and shared state  
**Key Responsibilities**:
- Manages TCP sockets (port 5001 command, 8001 video)
- Decodes MJPEG stream into numpy BGR frames
- Thread-safe frame buffer (`image` + `image_lock`)
- Command transmission with retry logic
- Connection state tracking (`tcp_flag`, `connection`)

**Critical Methods**:

| Method | Purpose | Thread Safety |
|--------|---------|---------------|
| `receiving_video(ip)` | Receives binary stream, decodes JPEG, writes to `self.image` | Acquires `image_lock` |
| `send_data(data)` | Transmits command to robot via port 5001 | Thread-safe (socket handles locking) |
| `turn_on_client(ip)` | Creates sockets, sets timeouts | Called from main thread |
| `turn_off_client()` | Closes sockets, releases resources | Called from main thread |

**Shared State Contract**:

```python
# Producer (receiving_video thread):
with self.image_lock:
    self.image = frame.copy()  # BGR numpy array
    self.video_flag = False    # Signal new frame
    self.video_last_frame_ts = time.time()

# Consumer (Main.py refresh_image):
with self.client.image_lock:
    if isinstance(self.client.image, np.ndarray):
        base = self.client.image.copy()
        self.client.video_flag = True  # Mark as consumed
```

**CRITICAL RULES**:
1. **Never use `struct.pack('L')`** → Always use `'<I'` (4-byte little-endian)
2. **Never block Qt main thread** → All socket I/O happens in worker threads
3. **Always copy frames under lock** → Avoid race conditions with in-place operations

---

## 🎨 Feature Modules

### 1. Face Recognition Module

**File**: `Main.py` → `faceWindow` class  
**UI Designer**: `ui_face.py` → `Ui_Face`

**Purpose**: Capture, store, and recognize human faces for personalized robot interactions.

**Key Features**:
- **Face Capture**: Takes photo snapshots from video stream
- **Face Storage**: Saves face images with user-defined labels
- **Face Detection**: Real-time face detection with bounding boxes
- **Face Recognition**: Identifies saved faces and displays names

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  faceWindow (QMainWindow)                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  UI Elements:                                     │  │
│  │  - Video preview (QLabel)                         │  │
│  │  - Face name input (QLineEdit)                    │  │
│  │  - Capture button → facePhoto()                   │  │
│  │  - Save button → saveFacePhoto()                  │  │
│  │  - Detect button → faceDetection()                │  │
│  │  - Face list (QListWidget)                        │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Face Processing (OpenCV)                         │  │
│  │  - Haar Cascade classifier                        │  │
│  │  - Face detection (detectMultiScale)              │  │
│  │  - Face alignment and cropping                    │  │
│  │  - Feature extraction (optional LBPH/DNN)         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Storage Layer                                          │
│  - Saved faces: /FaceDetect/faces/<name>.jpg            │
│  - Face database: faces.pkl (pickled dictionary)        │
│  - Format: {name: encoded_features}                     │
└─────────────────────────────────────────────────────────┘
```

**Command Protocol**:

```python
# Enable face detection on robot
self.client.send_data("CMD_FACE_DETECT\n")

# Robot response when face found:
# "FaceDetect#1#x_center#y_center#width#height#\n"
# Example: "FaceDetect#1#160#120#80#100#\n"
```

**Methods**:

| Method | Purpose | Trigger |
|--------|---------|---------|
| `facePhoto()` | Captures current frame from video stream | Button click |
| `saveFacePhoto()` | Saves captured face with user-provided name | Button click |
| `faceDetection()` | Toggles real-time face detection on robot | Button click |
| `readFace()` | Loads saved faces from disk into UI list | Window open |

**Workflow Example**:

```
User Action                     System Response
─────────────────────────────────────────────────────────
1. Click "Capture"      →      Freeze frame, show in preview
2. Enter name "Alice"   →      Enable "Save" button
3. Click "Save"         →      Write alice.jpg to disk
4. Click "Detect"       →      Send CMD_FACE_DETECT to robot
5. Robot sees Alice     →      "FaceDetect#1#..." received
                        →      Draw green box + "Alice" label on video
```

**Configuration**:

```python
# In Main.py, faceWindow class:
FACE_STORAGE_DIR = "FaceDetect/faces/"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
MIN_FACE_SIZE = (30, 30)  # Minimum detection size
DETECTION_SCALE = 1.1     # Cascade scale factor
MIN_NEIGHBORS = 5         # Detection sensitivity
```

---

### 2. Ball Tracking Module

**File**: `Main.py` → `MyWindow.chase_ball_and_find_face()`  
**Button**: `Button_Ball_And_Face` (toggles between Ball/Face modes)

**Purpose**: Autonomous ball tracking using color-based computer vision (HSV filtering).

**Key Features**:
- **Color Detection**: Detects balls by HSV color range (default: red/orange)
- **Centroid Tracking**: Calculates ball center coordinates
- **Autonomous Following**: Robot moves toward ball automatically
- **Distance Control**: Stops when ball is within threshold distance

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  Robot (Server-side Processing)                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Video Frame Capture (OpenCV)                  │  │
│  │     - Capture BGR frame from camera               │  │
│  │     - Convert BGR → HSV color space               │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  2. HSV Color Filtering                           │  │
│  │     - Define HSV range for ball color             │  │
│  │     - cv2.inRange() → binary mask                 │  │
│  │     - Morphological ops (erode/dilate)            │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  3. Contour Detection                             │  │
│  │     - cv2.findContours() on mask                  │  │
│  │     - Filter by area (min threshold)              │  │
│  │     - Find largest contour (main ball)            │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  4. Centroid & Distance Calculation               │  │
│  │     - cv2.moments() → center (cx, cy)             │  │
│  │     - Estimate distance from contour area         │  │
│  │     - Send telemetry: "Ball#cx#cy#area#\n"        │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  5. Motor Control (PID-like)                      │  │
│  │     - Error_x = cx - frame_center_x               │  │
│  │     - if Error_x > threshold: turn_right()        │  │
│  │     - if Error_x < -threshold: turn_left()        │  │
│  │     - if area < min_area: move_forward()          │  │
│  │     - if area > max_area: stop()                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Client (Main.py)                                       │
│  - Receives annotated video (ball outlined)             │
│  - Displays tracking status on overlay                  │
│  - Toggle: Button text cycles "Ball" → "Face" → "Off"  │
└─────────────────────────────────────────────────────────┘
```

**Command Protocol**:

```python
# Toggle ball tracking
def chase_ball_and_find_face(self):
    text = self.Button_Ball_And_Face.text()
    if text == 'Ball':
        self.client.send_data("CMD_BALL_TRACK#1\n")  # Enable
        self.Button_Ball_And_Face.setText('Face')
    elif text == 'Face':
        self.client.send_data("CMD_FACE_DETECT#1\n")  # Switch to face
        self.Button_Ball_And_Face.setText('Off')
    else:
        self.client.send_data("CMD_TRACK_OFF\n")     # Disable all
        self.Button_Ball_And_Face.setText('Ball')
```

**HSV Color Tuning** (server-side configuration):

```python
# Default: Red/Orange ball
BALL_COLOR_HSV_LOWER = np.array([0, 120, 70])    # (Hue, Sat, Val)
BALL_COLOR_HSV_UPPER = np.array([10, 255, 255])

# Alternative: Green ball
# LOWER = np.array([40, 50, 50])
# UPPER = np.array([80, 255, 255])

# Morphological kernel for noise reduction
KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
```

**Performance Characteristics**:

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| Detection FPS | 15-25 | Limited by Pi camera throughput |
| Min ball size | 20x20 px | Adjustable via `MIN_CONTOUR_AREA` |
| Max tracking distance | ~2 meters | Depends on ball size and lighting |
| Turn response time | ~200ms | Limited by servo update rate |

---

### 3. LED Control Module

**File**: `Main.py` → `ledWindow` class  
**UI Designer**: `ui_led.py` → `Ui_led`

**Purpose**: Real-time RGB LED color control with multiple animation modes.

**Key Features**:
- **Color Picker**: Qt color dialog with live preview
- **RGB/HSL Modes**: Dual color space input (sliders + text fields)
- **Animation Modes**: Static, breathing, rainbow, chase effects
- **Brightness Control**: 0-100% dimming via dial widget

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  ledWindow (QMainWindow)                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  UI Components:                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Color Preview (QLabel with paintEvent)      │  │  │
│  │  │  - Shows current color as filled circle     │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Mode Selection (QComboBox)                  │  │  │
│  │  │  - Static                                   │  │  │
│  │  │  - Breathing (fade in/out)                  │  │  │
│  │  │  - Rainbow (HSV hue rotation)               │  │  │
│  │  │  - Chase (sequential LED activation)        │  │  │
│  │  │  - Strobe (rapid on/off)                    │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ RGB Sliders (0-255) / Text Inputs           │  │  │
│  │  │  - Red   [████████░░] (180)  ┌──────┐       │  │  │
│  │  │  - Green [████░░░░░░] (90)   │ 180  │       │  │  │
│  │  │  - Blue  [██████████] (255)  └──────┘       │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ HSL Sliders / Text Inputs                   │  │  │
│  │  │  - Hue (0-360°)                             │  │  │
│  │  │  - Saturation (0-100%)                      │  │  │
│  │  │  - Lightness (0-100%)                       │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Brightness Dial (QDial)                     │  │  │
│  │  │       ╱ ‾ ╲                                 │  │  │
│  │  │      │  75% │   [Apply] [Turn Off]          │  │  │
│  │  │       ╲ _ ╱                                 │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Color Space Conversion (Internal Logic)               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  RGB ←→ HSL Conversion                            │  │
│  │  - rgb01_to_hsl(): RGB[0,1] → HSL[0-360, 0-1, 0-1]│  │
│  │  - hsl_to_rgb01(): HSL → RGB[0,1]                │  │
│  │  - rgb255_to_rgb01(): Scale 0-255 → 0-1          │  │
│  │  - rgb01_to_rgb255(): Scale 0-1 → 0-255          │  │
│  │  - rgb255_to_rgbhex(): RGB → "#FF8000"           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Command Transmission                                   │
│  - Static:    "CMD_LED#mode#R#G#B#\n"                   │
│  - Breathing: "CMD_LED#breath#R#G#B#speed#\n"           │
│  - Rainbow:   "CMD_LED#rainbow#speed#\n"                │
│  - Off:       "CMD_LED#off#\n"                          │
└─────────────────────────────────────────────────────────┘
```

**Methods**:

| Method | Purpose | Trigger |
|--------|---------|---------|
| `mode1Color()` | Opens Qt color picker dialog | "Pick Color" button |
| `onCurrentColorChanged(color)` | Live preview during color selection | Color dialog drag |
| `changeRGBText()` | Updates HSL when RGB text changed | Text field edit |
| `changeHSLText()` | Updates RGB when HSL text changed | Text field edit |
| `dialValueChanged()` | Applies brightness scaling to current color | Dial rotation |
| `ledMode(index)` | Switches animation mode (static/breath/rainbow) | ComboBox change |
| `turnOff()` | Sends LED off command | "Turn Off" button |

**Command Protocol**:

```python
# Static color (RGB 180, 90, 255 at 75% brightness)
brightness_factor = 0.75
r, g, b = int(180 * brightness_factor), int(90 * brightness_factor), int(255 * brightness_factor)
self.client.send_data(f"CMD_LED#static#{r}#{g}#{b}#\n")

# Breathing mode (red, speed=5)
self.client.send_data("CMD_LED#breath#255#0#0#5#\n")

# Rainbow mode (speed=10)
self.client.send_data("CMD_LED#rainbow#10#\n")

# Turn off
self.client.send_data("CMD_LED#off#\n")
```

**Color Space Formulas** (implemented in `ledWindow`):

```python
# RGB to HSL
def rgb01_to_hsl(rgb: np.array) -> np.array:
    """
    Input: RGB in [0, 1]
    Output: HSL where H in [0, 360], S in [0, 1], L in [0, 1]
    """
    import colorsys
    h, l, s = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
    return np.array([h * 360, s, l])

# HSL to RGB
def hsl_to_rgb01(hsl: np.array) -> np.array:
    """
    Input: HSL where H in [0, 360], S in [0, 1], L in [0, 1]
    Output: RGB in [0, 1]
    """
    import colorsys
    r, g, b = colorsys.hls_to_rgb(hsl[0] / 360, hsl[2], hsl[1])
    return np.array([r, g, b])
```

**Widget Implementation Example**:

```python
# In ledWindow.__init__():
self.colorDialog = ColorDialog(self)
self.colorDialog.currentColorChanged.connect(self.onCurrentColorChanged)
self.colorDialog.setOption(QColorDialog.ShowAlphaChannel, False)
self.colorDialog.setOption(QColorDialog.NoButtons, True)

# Custom color dialog with circular preview
class ColorDialog(QColorDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_color = QColor(255, 255, 255)
    
    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(self.current_color))
        painter.drawEllipse(10, 10, 50, 50)  # Color preview circle
```

**Server-side LED Driver** (pseudocode):

```python
# In Robot Server code:
def handle_led_command(cmd_parts):
    mode = cmd_parts[1]
    
    if mode == "static":
        r, g, b = int(cmd_parts[2]), int(cmd_parts[3]), int(cmd_parts[4])
        neopixel.fill((r, g, b))
        neopixel.show()
    
    elif mode == "breath":
        r, g, b, speed = int(cmd_parts[2]), int(cmd_parts[3]), int(cmd_parts[4]), int(cmd_parts[5])
        start_breathing_animation(r, g, b, speed)
    
    elif mode == "rainbow":
        speed = int(cmd_parts[2])
        start_rainbow_animation(speed)
    
    elif mode == "off":
        neopixel.fill((0, 0, 0))
        neopixel.show()
```

---

### 4. Servo Calibration Module

**File**: `Calibration.py` → `calibrationWindow` class  
**UI Designer**: `Calibration.py` → `Ui_calibration`

**Purpose**: Fine-tune servo offsets for all 12 leg servos to correct assembly tolerances.

**Key Features**:
- **Per-Leg Calibration**: Adjust all 3 joints (coxa, femur, tibia) for each leg
- **Live Preview**: See servo movements in real-time during adjustment
- **Persistent Storage**: Save/load calibration to `Deviation.txt`
- **Reset Function**: Restore factory default positions

**Servo Layout**:

```
        Front
    ┌─────────────┐
    │  LF      RF │   LF = Left Front   (Servos 0,1,2)
    │   ●      ●  │   RF = Right Front  (Servos 3,4,5)
    │             │   LB = Left Back    (Servos 6,7,8)
    │  LB      RB │   RB = Right Back   (Servos 9,10,11)
    │   ●      ●  │
    └─────────────┘
         Back

Servo Mapping:
  Leg LF: Servo 0 (coxa), 1 (femur), 2 (tibia)
  Leg RF: Servo 3 (coxa), 4 (femur), 5 (tibia)
  Leg LB: Servo 6 (coxa), 7 (femur), 8 (tibia)
  Leg RB: Servo 9 (coxa), 10 (femur), 11 (tibia)
```

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  calibrationWindow (QMainWindow)                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  UI Grid Layout (4 legs × 3 joints)              │  │
│  │  ┌──────────────┬──────────────┬──────────────┐  │  │
│  │  │   Servo 0    │   Servo 1    │   Servo 2    │  │  │
│  │  │  (LF Coxa)   │ (LF Femur)   │ (LF Tibia)   │  │  │
│  │  │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │  │  │
│  │  │ │  [+] [-] │ │ │  [+] [-] │ │ │  [+] [-] │ │  │  │
│  │  │ │ Offset:5 │ │ │ Offset:2 │ │ │ Offset:-3│ │  │  │
│  │  │ └──────────┘ │ └──────────┘ │ └──────────┘ │  │  │
│  │  └──────────────┴──────────────┴──────────────┘  │  │
│  │  (Repeated for RF, LB, RB legs...)               │  │
│  │                                                   │  │
│  │  [Save Calibration]  [Load Calibration]          │  │
│  │  [Reset to Defaults] [Test All Servos]           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Calibration Data Structure                             │
│  deviation = {                                          │
│      'LF_0': 5,    # Left Front, Servo 0 offset         │
│      'LF_1': -2,   # Left Front, Servo 1 offset         │
│      'LF_2': 3,    # Left Front, Servo 2 offset         │
│      'RF_0': 0,    # Right Front, Servo 0 offset        │
│      ...                                                │
│      'RB_2': -1    # Right Back, Servo 2 offset         │
│  }                                                      │
│  Stored in: Deviation.txt (plain text, one per line)    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Command Transmission                                   │
│  "CMD_SERVO#servo_id#angle#\n"                          │
│  Example: "CMD_SERVO#0#95#\n"  → Servo 0 to 95° (90+5)  │
└─────────────────────────────────────────────────────────┘
```

**Methods**:

| Method | Purpose | Trigger |
|--------|---------|---------|
| `X1()`, `X2()` | Increment/decrement X-axis servo offset | +/- button |
| `Y1()`, `Y2()` | Increment/decrement Y-axis servo offset | +/- button |
| `Z1()`, `Z2()` | Increment/decrement Z-axis servo offset | +/- button |
| `save()` | Writes all offsets to `Deviation.txt` | "Save" button |
| `get_point()` | Loads offsets from `Deviation.txt` | Window init |
| `set_point(data)` | Sends servo commands with offsets applied | Any adjustment |
| `leg_point(leg)` | Returns calibration dict for specific leg | Internal helper |

**Calibration Workflow**:

```
Initial Setup
   │
   ▼
┌────────────────────────────────────┐
│ 1. Power on robot, stand position │
│    All servos at 90° (neutral)    │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 2. Visually inspect leg alignment │
│    - Legs should be vertical      │
│    - Feet flat on ground          │
│    - Body level                   │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 3. Adjust each misaligned servo   │
│    - Click [+] to increase angle  │
│    - Click [-] to decrease angle  │
│    - Range: typically -10 to +10  │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 4. Click "Save Calibration"       │
│    Writes: Deviation.txt          │
│    Format: LF_0#5#                │
│           LF_1#-2#                │
│           ...                     │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 5. Test walking gait              │
│    - Use WASD keys to move        │
│    - Verify smooth motion         │
│    - Repeat calibration if needed │
└────────────────────────────────────┘
```

**File Format** (`Deviation.txt`):

```
LF_0#5#
LF_1#-2#
LF_2#3#
RF_0#0#
RF_1#1#
RF_2#-1#
LB_0#2#
LB_1#0#
LB_2#-4#
RB_0#-3#
RB_1#2#
RB_2#1#
```

**Code Example**:

```python
# In calibrationWindow:
def X1(self):
    """Increment X-axis (coxa) servo offset"""
    self.X += 1  # Increase offset
    self.set_point(f"CMD_SERVO#0#{90 + self.X}#\n")  # Send to robot
    self.label_X.setText(str(self.X))  # Update UI

def save(self):
    """Save all calibration data to file"""
    data = []
    for leg in ['LF', 'RF', 'LB', 'RB']:
        points = self.leg_point(leg)  # Get current offsets
        for i in range(3):
            data.append(f"{leg}_{i}#{points[i]}#\n")
    self.Save_to_txt(data, 'Deviation.txt')
    QMessageBox.information(self, "Success", "Calibration saved!")
```

---

## 🔄 Common Workflows

### Workflow 1: First Connection & Calibration

```
┌──────────────────────────────────────────────┐
│ Step 1: Power on Robot                       │
│   • Battery voltage ≥ 7.5V                   │
│   • Wait 30 seconds for boot                 │
│   • LED should blink (server ready)          │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Find Robot IP Address               │
│   Method A: Check router DHCP table          │
│   Method B: nmap scan                        │
│     $ sudo nmap -sn 192.168.1.0/24           │
│   Method C: Connect monitor to Pi            │
│     $ hostname -I                            │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Launch Client & Connect             │
│   • Run: python Main.py                      │
│   • Enter IP, click "Connect"                │
│   • Verify: Video displays, battery shows    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Servo Calibration (if needed)       │
│   • Click "Stand" button                     │
│   • Open: Menu → Calibration                 │
│   • Adjust offsets until robot stands level │
│   • Click "Save Calibration"                 │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Test Movement                       │
│   • Press W/A/S/D keys                       │
│   • Verify smooth gait                       │
│   • Check battery doesn't drop rapidly       │
└──────────────────────────────────────────────┘
```

---

### Workflow 2: Face Recognition Setup

```
┌──────────────────────────────────────────────┐
│ Step 1: Open Face Recognition Window        │
│   Menu: Features → Face Recognition          │
│   (Or click "Face" button in main window)    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Capture Training Images             │
│   • Position subject 1-2 meters from robot   │
│   • Good lighting (avoid harsh shadows)      │
│   • Subject faces camera directly            │
│   • Click "Capture" button                   │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Label and Save                      │
│   • Enter name in text field (e.g., "Alice") │
│   • Click "Save" button                      │
│   • Repeat 3-5 times with different angles:  │
│     - Front view                             │
│     - 30° left/right                         │
│     - Slight up/down tilt                    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Enable Real-time Detection          │
│   • Click "Detect" button                    │
│   • Robot starts face tracking               │
│   • Green box + name appears when recognized │
│   • Red box if face unknown                  │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Test & Refine                       │
│   • Move subject to different distances      │
│   • Test in different lighting conditions    │
│   • Add more training images if needed       │
└──────────────────────────────────────────────┘
```

---

### Workflow 3: Ball Tracking Mode

```
┌──────────────────────────────────────────────┐
│ Step 1: Prepare Ball                        │
│   • Use solid-color ball (red/orange best)   │
│   • Size: 5-10 cm diameter                   │
│   • Avoid shiny/reflective surfaces          │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Enable Ball Tracking                │
│   • Click "Ball/Face" button                 │
│   • Button text changes to "Face"            │
│   • Robot enters autonomous tracking mode    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Position Ball                       │
│   • Place ball 1-2 meters in front           │
│   • In well-lit area                         │
│   • Robot should turn toward ball            │
│   • Blue circle drawn around detected ball   │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Observe Behavior                    │
│   • Robot follows ball movements             │
│   • Stops when ball within 30cm              │
│   • Loses tracking if ball moves too fast    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Adjust HSV (if needed)              │
│   • If detection fails:                      │
│     - Edit Server/vision_config.py           │
│     - Adjust HSV_LOWER/UPPER values          │
│     - Restart robot server                   │
└──────────────────────────────────────────────┘
```

---

### Workflow 4: LED Customization

```
┌──────────────────────────────────────────────┐
│ Step 1: Open LED Control Window             │
│   Menu: Features → LED Control               │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Choose Color Method                 │
│   Method A: Color Picker                     │
│     • Click "Pick Color" button              │
│     • Drag to select hue                     │
│     • Adjust saturation/brightness           │
│   Method B: RGB Sliders                      │
│     • Red: 0-255                             │
│     • Green: 0-255                           │
│     • Blue: 0-255                            │
│   Method C: HSL Text Input                   │
│     • Hue: 0-360°                            │
│     • Saturation: 0-100%                     │
│     • Lightness: 0-100%                      │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Select Animation Mode               │
│   • Static: Solid color                      │
│   • Breathing: Fade in/out (specify speed)   │
│   • Rainbow: HSV color cycle                 │
│   • Chase: Sequential LED activation         │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Adjust Brightness                   │
│   • Rotate dial (0-100%)                     │
│   • Preview updates in real-time             │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Apply & Save                        │
│   • Click "Apply" to send to robot           │
│   • LED color changes immediately            │
│   • Settings persist until power cycle       │
└──────────────────────────────────────────────┘
```

---

## 📜 Revision History

### Main.py Evolution

| Version | Date | Changes |
|---------|------|---------|
| v1.20 | 2025-11-15 | Added visible "DebugWin" button above "Close Video" for UX improvement |
| v1.19 | 2025-11-13 | Integrated `DebugStreamWindow` (press T/F10 to open), enriched documentation |
| v1.18 | 2025-11-13 | Shrank status bar overlay, added optional GUI heartbeat for diagnostics |
| v1.17 | 2025-11-12 | Fixed QImage stride bug (`rgb.strides[0]`), continuous placeholder updates |
| v1.16 | 2025-11-12 | Auto-start video after connect, draw status on placeholder frames |
| v1.15 | 2025-11-12 | iOS-style status bar overlay, safer connect flow with timeout validation |
| v1.00 | Initial | Port from original Freenove codebase (now archived as `Main_Freenove.py`) |

### Client.py Evolution

| Version | Date | Changes |
|---------|------|---------|
| v1.15 | 2025-11-13 | Added `video_last_frame_ts` for FPS calculation, improved frame metadata |
| v1.14 | 2025-11-12 | Fixed struct format (`'<I'` enforcement), added `frames_produced` counter |
| v1.13 | 2025-11-11 | Thread-safe flag checks, added connection timeout handling |
| v1.12 | 2025-11-10 | Refactored `turn_off_client()` to prevent socket leaks |
| v1.00 | Initial | Original implementation (basic TCP client) |

---

## 🧵 Threading Model

### Thread Lifecycle

```
Application Start
       │
       ▼
┌──────────────┐
│ Qt Main Loop │ (Primary thread - never blocks)
└──────┬───────┘
       │
       │ User clicks "Connect"
       ▼
┌────────────────────────────────────────┐
│  connect() method                      │
│  1. Creates sockets (non-blocking)     │
│  2. Spawns threads:                    │
│     - video_thread                     │
│     - instruction_thread               │
│  3. Starts timers:                     │
│     - refresh_image (33ms)             │
│     - power (1000ms)                   │
│     - sonic (1000ms)                   │
│     - overlay_timer (500ms)            │
└────────────────────────────────────────┘
       │
       ▼
┌─────────────────────┬──────────────────────┐
│  video_thread       │ instruction_thread   │
│  (Client.py)        │ (Main.py)            │
│  - Recv binary      │ - Recv text lines    │
│  - Decode JPEG      │ - Parse telemetry    │
│  - Update image     │ - Update UI state    │
│  - Loop until       │ - Loop until         │
│    tcp_flag=False   │   tcp_flag=False     │
└─────────────────────┴──────────────────────┘
       │                       │
       │ User clicks "Disconnect"
       ▼                       ▼
┌──────────────────────────────────────────┐
│  closeEvent() / disconnect               │
│  1. Sets tcp_flag = False                │
│  2. Calls stop_thread() [⚠️ deprecated]  │
│  3. Closes sockets                       │
│  4. Stops all timers                     │
└──────────────────────────────────────────┘
```

### Thread Safety Checklist

✅ **Safe Operations**:
- Reading `Client.image` under `image_lock`
- Calling `send_data()` from any thread
- Modifying Qt widgets via `QTimer.singleShot(0, lambda: ...)`

❌ **Unsafe Operations**:
- Directly modifying `Client.image` without lock
- Calling `stop_thread()` (uses deprecated `PyThreadState_SetAsyncExc`)
- Blocking Qt main thread with `time.sleep()` or `socket.recv()`

---

## 🎥 Video Pipeline

### Frame Flow (Producer-Consumer Pattern)

```
Robot (Port 8001)
      │
      │ Binary stream: <len><JPEG><len><JPEG>...
      ▼
┌──────────────────────────────────────────────┐
│ Client.receiving_video() [Producer Thread]   │
│ 1. Read 4 bytes → frame_length               │
│ 2. Read frame_length bytes → jpeg_data       │
│ 3. cv2.imdecode(jpeg_data) → BGR numpy array │
│ 4. Acquire image_lock                        │
│ 5. self.image = frame.copy()                 │
│ 6. self.video_flag = False (new frame ready) │
│ 7. Release image_lock                        │
└──────────────────────────────────────────────┘
      │
      │ Every 33ms
      ▼
┌──────────────────────────────────────────────┐
│ MyWindow.refresh_image() [Consumer/Qt Thread]│
│ 1. Acquire image_lock                        │
│ 2. if isinstance(image, np.ndarray):         │
│ 3.   base = image.copy()                     │
│ 4.   video_flag = True (mark consumed)       │
│ 5. Release image_lock                        │
│ 6. Draw overlays on base (NOT on shared buf) │
│ 7. Convert BGR → RGB                         │
│ 8. Create QImage with .copy() (memory safety)│
│ 9. setPixmap() to QLabel                     │
└──────────────────────────────────────────────┘
      │
      ▼
   Display
```

### Overlay Rendering

**Layers** (drawn in order):
1. **Base frame** (BGR from camera)
2. **Top bar** (semi-transparent black, 30px height):
   - Left: IP:Port, elapsed time, robot state
   - Center: Distance (XX.Xcm)
   - Right: Battery (X.XXV), FPS
3. **Stall badge** (if no new frames >2s):
   - Red rectangle with "Stalled X.Xs" text

**Implementation** (`testVideoStream.draw_top_bar`):

```python
def draw_top_bar(frame, fps, battery_v, distance_cm, state_text, state_since):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0,0), (w, 30), (0,0,0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    # Left: IP/state
    elapsed = int(time.time() - state_since)
    cv2.putText(frame, f"{state_text} {elapsed}s", (5, 20), ...)
    
    # Center: Distance
    if distance_cm:
        cv2.putText(frame, f"{distance_cm:.1f}cm", (w//2-30, 20), ...)
    
    # Right: Battery/FPS
    if battery_v:
        cv2.putText(frame, f"{battery_v:.2f}V", (w-100, 20), ...)
    cv2.putText(frame, f"{fps:.1f}fps", (w-50, 20), ...)
```

---

## 📡 Telemetry System

### Battery Monitoring

**Flow**:

```
Main.py (timer_power)
   │ Every 1000ms
   ▼
power() → send_data("CMD_POWER\n")
   │
   ▼
Robot processes command
   │
   ▼
Robot sends "Power#8.12#\n" on port 5001
   │
   ▼
receive_instruction() receives line
   │
   ▼
_handle_server_line() parses:
   - Extracts float from "Power#8.12#"
   - Sets self.tele_batt_v = 8.12
   - Calculates percentage: (8.12 - 7.0) / 1.4 * 100
   - Updates progress_Power via QTimer.singleShot()
```

**Battery Voltage Mapping**:

| Voltage | Percentage | Status |
|---------|------------|--------|
| 8.40V   | 100%       | Full charge |
| 7.70V   | 50%        | Normal |
| 7.00V   | 0%         | Critical (shutdown) |

### Distance Sensing

**Flow**:

```
Main.py (timer_sonic)
   │ Every 1000ms (when enabled)
   ▼
getSonicData() → send_data("CMD_SONIC\n")
   │
   ▼
Robot measures ultrasonic distance
   │
   ▼
Robot sends "Sonic#45.3#\n"
   │
   ▼
_handle_server_line() parses:
   - Extracts float from "Sonic#45.3#"
   - Sets self.tele_dist_cm = 45.3
   - Overlay shows "45.3cm" in next refresh_image()
```

---

## 🛠️ Development Guidelines

### Before Making Changes

1. **Create backup**: `cp Main.py Main_backup_$(date +%Y%m%d).py`
2. **Check revision history**: Verify you're modifying the latest version
3. **Read threading contract**: Ensure no Qt main thread blocking
4. **Test video pipeline**: Run with `debug_ui_enabled = True`

### Adding New Features

**Example: Add gyroscope telemetry**

1. **Server-side** (Robot Pi):

```python
# In server code, add periodic transmission:
gyro_data = read_gyroscope()  # Returns (x, y, z)
client_socket.send(f"Gyro#{gyro_data[0]}#{gyro_data[1]}#{gyro_data[2<!-- filepath: /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/README.md -->
# Freenove Robot Dog Client - Architecture & Development Guide

```
╔══════════════════════════════════════════════════════════════════════════╗
║                 FREENOVE ROBOT DOG - CLIENT APPLICATION                  ║
║                     Desktop Control & Video Streaming                    ║
╚══════════════════════════════════════════════════════════════════════════╝

Project      : Freenove Robot Dog Kit for Raspberry Pi - Client Software
Version      : 1.20 (Main.py), 1.15 (Client.py)
Platform     : macOS / Linux / Windows
Language     : Python 3.7+
Framework    : PyQt5, OpenCV, NumPy

Authors      : MT & GitHub Copilot
Created      : 2024-10-15 (Original Freenove codebase)
Revised      : 2025-11-17 (Current architecture documentation)
Maintainers  : MT (Lead Developer), GitHub Copilot (AI Assistant)

Repository   : /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/
License      : See main project LICENSE file
Contact      : [Project repository issues]

Purpose      : This README documents the client-side architecture, threading
               model, communication protocols, and development guidelines for
               the Freenove Robot Dog desktop control application.

Last Updated : 2025-11-17 15:45 PST
Status       : Production (v1.20) - Actively Maintained
```

---

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
  - [Network Topology](#network-topology)
  - [Communication Protocols](#communication-protocols)
- [File Hierarchy](#file-hierarchy)
- [Key Components](#key-components)
  - [Main.py (v1.20)](#mainpy-v120)
  - [Client.py (v1.15)](#clientpy-v115)
- [Feature Modules](#feature-modules)
  - [1. Face Recognition Module](#1-face-recognition-module)
  - [2. Ball Tracking Module](#2-ball-tracking-module)
  - [3. LED Control Module](#3-led-control-module)
  - [4. Servo Calibration Module](#4-servo-calibration-module)
- [Common Workflows](#common-workflows)
- [Revision History](#revision-history)
- [Threading Model](#threading-model)
- [Video Pipeline](#video-pipeline)
- [Telemetry System](#telemetry-system)
- [Development Guidelines](#development-guidelines)
- [Error Codes Reference](#error-codes-reference)
- [Troubleshooting](#troubleshooting)
- [Related Files](#related-files)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**Application**: Desktop PyQt5 client for controlling the Freenove Robot Dog  
**Platform**: macOS / Linux / Windows  
**Language**: Python 3.7+  
**Current Version**: Main.py v1.20, Client.py v1.15

This client provides:
- Real-time video streaming (MJPEG over TCP, 15-30 FPS)
- Bidirectional command/telemetry channel (text protocol)
- Robot motion control (WASD keys + GUI buttons)
- Sensor monitoring (ultrasonic distance, battery voltage, IMU)
- Feature modules (face recognition, ball tracking, LED control, servo calibration)
- In-app debug viewer for video pipeline diagnostics (press T or F10)

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python dependencies
pip install PyQt5 opencv-python numpy

# macOS users may need:
brew install qt@5
export PATH="/usr/local/opt/qt@5/bin:$PATH"
```

### First-Time Setup

1. **Configure Robot IP**:
   - Default IP: `192.168.1.100`
   - Edit `IP.txt` or enter IP in GUI

2. **Launch Client**:
   ```bash
   cd /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client
   python Main.py
   ```

3. **Connect to Robot**:
   - Enter robot IP address (e.g., `192.168.1.150`)
   - Click **Connect** button
   - Video should auto-start within 1-2 seconds
   - Battery indicator appears in top-right

### Keyboard Controls

| Key | Action | Key | Action |
|-----|--------|-----|--------|
| `W` | Forward | `A` | Turn Left |
| `S` | Backward | `D` | Turn Right |
| `Q` | Step Left | `E` | Step Right |
| `Space` | Stop | `R` | Relax (sit) |
| `T` / `F10` | Open Debug Window | `Esc` | Close Dialogs |

### Debug Mode

Enable detailed logging for troubleshooting:

```python
# In Main.py (lines ~90-95), set:
self.debug_ui_enabled = True   # Show GUI debug prints
self.debug_rx_enabled = True   # Show network debug prints
```

Console output example:
```
[DEBUG][GUI] refresh_image: FPS=28.3, latency=35ms
[DEBUG][RX] Power#8.15#
[DEBUG][RX] Sonic#42.7#
```

---

## 🏗️ System Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Client (Main.py)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Qt Main Thread (GUI)                                  │ │
│  │    - Event loop, painting, user input                  │ │
│  │    - QTimer callbacks (refresh_image, power, sonic)    │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │                                        │
│  ┌──────────────────▼──────────────┐  ┌──────────────────┐  │
│  │  Video Receive Thread           │  │ Instruction Thread│  │
│  │  (Client.receiving_video)       │  │ (receive_instr.)  │  │
│  │   - Port 8001                   │  │  - Port 5001      │  │
│  │   - Decodes JPEG frames         │  │  - Text protocol  │  │
│  │   - Writes to Client.image      │  │  - Parses commands│  │
│  └─────────────────────────────────┘  └──────────────────┘  │
│                     │                           │            │
│                     └───────────┬───────────────┘            │
│                                 ▼                            │
│                      Shared State (Client.py)               │
│                      - image (numpy BGR)                    │
│                      - image_lock (threading.Lock)          │
│                      - video_flag (bool)                    │
│                      - video_last_frame_ts (float)          │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 │ TCP/IP
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                 Raspberry Pi Robot Dog (Server)             │
│  ┌────────────────┐              ┌────────────────────────┐ │
│  │  Video Server  │              │  Command Server        │ │
│  │  Port 8001     │◄────────────►│  Port 5001             │ │
│  │  (MJPEG stream)│              │  (Text protocol)       │ │
│  └────────────────┘              └────────────────────────┘ │
│         │                                   │               │
│         ▼                                   ▼               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     Robot Control Layer (Servo, IMU, Sensors)       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Communication Protocols

#### Port 5001: Command/Telemetry (Text-based)

```
Direction: Bidirectional
Format:    CMD_NAME#param1#param2#...\n

Examples (Client → Robot):
  CMD_MOVE_FORWARD#8\n          → Move forward at speed 8
  CMD_HEAD#90\n                 → Set head servo to 90°
  CMD_SONIC\n                   → Request distance reading
  CMD_FACE_DETECT\n             → Enable face tracking
  CMD_BALL_TRACK\n              → Enable ball tracking
  CMD_LED#255#128#0\n           → Set LED RGB color

Examples (Robot → Client):
  Power#8.12#\n                 → Battery voltage
  Sonic#45.3#\n                 → Distance in cm
  WorkingTime#1234#\n           → Uptime in seconds
  FaceDetect#1#120#80#\n        → Face found at (x,y)
```

#### Port 8001: Video Stream (Binary)

```
Direction: Robot → Client (unidirectional)
Format:    <4-byte length><JPEG data><4-byte length><JPEG data>...

Frame Structure:
  [0:4]   uint32_t (little-endian) = JPEG payload size
  [4:N]   JPEG compressed image data
  
Example:
  b'\x42\x1f\x00\x00'  → Frame size = 7,986 bytes
  b'\xff\xd8\xff...'   → JPEG starts with FF D8 FF
```

---

## 📁 File Hierarchy

```
Client/
├── Main.py                    # Main GUI window (v1.20)
│   ├── MyWindow               # Main application window
│   ├── faceWindow             # Face recognition UI
│   ├── calibrationWindow      # Servo calibration UI
│   └── ledWindow              # LED control UI
│
├── Client.py                  # Network client & shared state (v1.15)
│   ├── Client                 # Core client class
│   │   ├── receiving_video()  # Video receive thread (port 8001)
│   │   ├── send_data()        # Command sender (port 5001)
│   │   ├── turn_on_client()   # Connection manager
│   │   └── turn_off_client()  # Cleanup
│   └── cmd                    # Command constants (CMD_MOVE_*, etc.)
│
├── testVideoStream.py         # Debug viewer (standalone + embedded)
│   ├── DebugStreamWindow      # In-app diagnostic window
│   └── draw_top_bar()         # Overlay rendering (FPS, battery, etc.)
│
├── Calibration.py             # Servo offset manager
│   └── Ui_calibration         # PyQt5 designer output
│
├── ui_client.py               # Main window UI layout
├── ui_led.py                  # LED window UI layout
├── ui_face.py                 # Face window UI layout
│
└── Picture/                   # Asset files
    ├── dog_client.png         # Startup splash screen
    └── logo_Mini.png          # Application icon
```

---

## 🔑 Key Components

### Main.py (v1.20)

**Purpose**: PyQt5 GUI application  
**Key Responsibilities**:
- User interface rendering and event handling
- Video frame display pipeline (QLabel painting)
- Keyboard/mouse input processing
- Timer-based refresh loops (video, telemetry, debug)
- Window management (main, debug, calibration, LED, face)

**Critical Methods**:

| Method | Purpose | Timing |
|--------|---------|--------|
| `refresh_image()` | Consumes frames from `Client.image`, draws overlays, updates QLabel | Every 33ms (≈30 FPS) |
| `receive_instruction()` | Listens on port 5001 for telemetry (battery, distance) | Runs in thread until disconnect |
| `_overlay_refresh_if_stalled()` | Redraws status bar when no new frames arrive | Every 500ms |
| `connect()` | Initiates TCP connections, starts threads, validates success | User-triggered |
| `closeEvent()` | Graceful shutdown: stops threads, closes sockets | Window close |

**State Variables**:

```python
self.client.image          # Latest BGR frame (numpy array)
self.client.image_lock     # Protects image reads/writes
self.client.video_flag     # False = new frame ready; True = consumed
self._last_frame_bgr       # Cached frame for stall handling
self.tele_batt_v           # Battery voltage (float)
self.tele_dist_cm          # Ultrasonic distance (float)
self._fps                  # Smoothed display framerate
```

---

### Client.py (v1.15)

**Purpose**: Network layer and shared state  
**Key Responsibilities**:
- Manages TCP sockets (port 5001 command, 8001 video)
- Decodes MJPEG stream into numpy BGR frames
- Thread-safe frame buffer (`image` + `image_lock`)
- Command transmission with retry logic
- Connection state tracking (`tcp_flag`, `connection`)

**Critical Methods**:

| Method | Purpose | Thread Safety |
|--------|---------|---------------|
| `receiving_video(ip)` | Receives binary stream, decodes JPEG, writes to `self.image` | Acquires `image_lock` |
| `send_data(data)` | Transmits command to robot via port 5001 | Thread-safe (socket handles locking) |
| `turn_on_client(ip)` | Creates sockets, sets timeouts | Called from main thread |
| `turn_off_client()` | Closes sockets, releases resources | Called from main thread |

**Shared State Contract**:

```python
# Producer (receiving_video thread):
with self.image_lock:
    self.image = frame.copy()  # BGR numpy array
    self.video_flag = False    # Signal new frame
    self.video_last_frame_ts = time.time()

# Consumer (Main.py refresh_image):
with self.client.image_lock:
    if isinstance(self.client.image, np.ndarray):
        base = self.client.image.copy()
        self.client.video_flag = True  # Mark as consumed
```

**CRITICAL RULES**:
1. **Never use `struct.pack('L')`** → Always use `'<I'` (4-byte little-endian)
2. **Never block Qt main thread** → All socket I/O happens in worker threads
3. **Always copy frames under lock** → Avoid race conditions with in-place operations

---

## 🎨 Feature Modules

### 1. Face Recognition Module

**File**: `Main.py` → `faceWindow` class  
**UI Designer**: `ui_face.py` → `Ui_Face`

**Purpose**: Capture, store, and recognize human faces for personalized robot interactions.

**Key Features**:
- **Face Capture**: Takes photo snapshots from video stream
- **Face Storage**: Saves face images with user-defined labels
- **Face Detection**: Real-time face detection with bounding boxes
- **Face Recognition**: Identifies saved faces and displays names

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  faceWindow (QMainWindow)                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  UI Elements:                                     │  │
│  │  - Video preview (QLabel)                         │  │
│  │  - Face name input (QLineEdit)                    │  │
│  │  - Capture button → facePhoto()                   │  │
│  │  - Save button → saveFacePhoto()                  │  │
│  │  - Detect button → faceDetection()                │  │
│  │  - Face list (QListWidget)                        │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Face Processing (OpenCV)                         │  │
│  │  - Haar Cascade classifier                        │  │
│  │  - Face detection (detectMultiScale)              │  │
│  │  - Face alignment and cropping                    │  │
│  │  - Feature extraction (optional LBPH/DNN)         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Storage Layer                                          │
│  - Saved faces: /FaceDetect/faces/<name>.jpg            │
│  - Face database: faces.pkl (pickled dictionary)        │
│  - Format: {name: encoded_features}                     │
└─────────────────────────────────────────────────────────┘
```

**Command Protocol**:

```python
# Enable face detection on robot
self.client.send_data("CMD_FACE_DETECT\n")

# Robot response when face found:
# "FaceDetect#1#x_center#y_center#width#height#\n"
# Example: "FaceDetect#1#160#120#80#100#\n"
```

**Methods**:

| Method | Purpose | Trigger |
|--------|---------|---------|
| `facePhoto()` | Captures current frame from video stream | Button click |
| `saveFacePhoto()` | Saves captured face with user-provided name | Button click |
| `faceDetection()` | Toggles real-time face detection on robot | Button click |
| `readFace()` | Loads saved faces from disk into UI list | Window open |

**Workflow Example**:

```
User Action                     System Response
─────────────────────────────────────────────────────────
1. Click "Capture"      →      Freeze frame, show in preview
2. Enter name "Alice"   →      Enable "Save" button
3. Click "Save"         →      Write alice.jpg to disk
4. Click "Detect"       →      Send CMD_FACE_DETECT to robot
5. Robot sees Alice     →      "FaceDetect#1#..." received
                        →      Draw green box + "Alice" label on video
```

**Configuration**:

```python
# In Main.py, faceWindow class:
FACE_STORAGE_DIR = "FaceDetect/faces/"
CASCADE_FILE = "haarcascade_frontalface_default.xml"
MIN_FACE_SIZE = (30, 30)  # Minimum detection size
DETECTION_SCALE = 1.1     # Cascade scale factor
MIN_NEIGHBORS = 5         # Detection sensitivity
```

---

### 2. Ball Tracking Module

**File**: `Main.py` → `MyWindow.chase_ball_and_find_face()`  
**Button**: `Button_Ball_And_Face` (toggles between Ball/Face modes)

**Purpose**: Autonomous ball tracking using color-based computer vision (HSV filtering).

**Key Features**:
- **Color Detection**: Detects balls by HSV color range (default: red/orange)
- **Centroid Tracking**: Calculates ball center coordinates
- **Autonomous Following**: Robot moves toward ball automatically
- **Distance Control**: Stops when ball is within threshold distance

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  Robot (Server-side Processing)                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Video Frame Capture (OpenCV)                  │  │
│  │     - Capture BGR frame from camera               │  │
│  │     - Convert BGR → HSV color space               │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  2. HSV Color Filtering                           │  │
│  │     - Define HSV range for ball color             │  │
│  │     - cv2.inRange() → binary mask                 │  │
│  │     - Morphological ops (erode/dilate)            │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  3. Contour Detection                             │  │
│  │     - cv2.findContours() on mask                  │  │
│  │     - Filter by area (min threshold)              │  │
│  │     - Find largest contour (main ball)            │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  4. Centroid & Distance Calculation               │  │
│  │     - cv2.moments() → center (cx, cy)             │  │
│  │     - Estimate distance from contour area         │  │
│  │     - Send telemetry: "Ball#cx#cy#area#\n"        │  │
│  └────────────────┬──────────────────────────────────┘  │
│                   ▼                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  5. Motor Control (PID-like)                      │  │
│  │     - Error_x = cx - frame_center_x               │  │
│  │     - if Error_x > threshold: turn_right()        │  │
│  │     - if Error_x < -threshold: turn_left()        │  │
│  │     - if area < min_area: move_forward()          │  │
│  │     - if area > max_area: stop()                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Client (Main.py)                                       │
│  - Receives annotated video (ball outlined)             │
│  - Displays tracking status on overlay                  │
│  - Toggle: Button text cycles "Ball" → "Face" → "Off"  │
└─────────────────────────────────────────────────────────┘
```

**Command Protocol**:

```python
# Toggle ball tracking
def chase_ball_and_find_face(self):
    text = self.Button_Ball_And_Face.text()
    if text == 'Ball':
        self.client.send_data("CMD_BALL_TRACK#1\n")  # Enable
        self.Button_Ball_And_Face.setText('Face')
    elif text == 'Face':
        self.client.send_data("CMD_FACE_DETECT#1\n")  # Switch to face
        self.Button_Ball_And_Face.setText('Off')
    else:
        self.client.send_data("CMD_TRACK_OFF\n")     # Disable all
        self.Button_Ball_And_Face.setText('Ball')
```

**HSV Color Tuning** (server-side configuration):

```python
# Default: Red/Orange ball
BALL_COLOR_HSV_LOWER = np.array([0, 120, 70])    # (Hue, Sat, Val)
BALL_COLOR_HSV_UPPER = np.array([10, 255, 255])

# Alternative: Green ball
# LOWER = np.array([40, 50, 50])
# UPPER = np.array([80, 255, 255])

# Morphological kernel for noise reduction
KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
```

**Performance Characteristics**:

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| Detection FPS | 15-25 | Limited by Pi camera throughput |
| Min ball size | 20x20 px | Adjustable via `MIN_CONTOUR_AREA` |
| Max tracking distance | ~2 meters | Depends on ball size and lighting |
| Turn response time | ~200ms | Limited by servo update rate |

---

### 3. LED Control Module

**File**: `Main.py` → `ledWindow` class  
**UI Designer**: `ui_led.py` → `Ui_led`

**Purpose**: Real-time RGB LED color control with multiple animation modes.

**Key Features**:
- **Color Picker**: Qt color dialog with live preview
- **RGB/HSL Modes**: Dual color space input (sliders + text fields)
- **Animation Modes**: Static, breathing, rainbow, chase effects
- **Brightness Control**: 0-100% dimming via dial widget

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  ledWindow (QMainWindow)                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  UI Components:                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Color Preview (QLabel with paintEvent)      │  │  │
│  │  │  - Shows current color as filled circle     │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Mode Selection (QComboBox)                  │  │  │
│  │  │  - Static                                   │  │  │
│  │  │  - Breathing (fade in/out)                  │  │  │
│  │  │  - Rainbow (HSV hue rotation)               │  │  │
│  │  │  - Chase (sequential LED activation)        │  │  │
│  │  │  - Strobe (rapid on/off)                    │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ RGB Sliders (0-255) / Text Inputs           │  │  │
│  │  │  - Red   [████████░░] (180)  ┌──────┐       │  │  │
│  │  │  - Green [████░░░░░░] (90)   │ 180  │       │  │  │
│  │  │  - Blue  [██████████] (255)  └──────┘       │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ HSL Sliders / Text Inputs                   │  │  │
│  │  │  - Hue (0-360°)                             │  │  │
│  │  │  - Saturation (0-100%)                      │  │  │
│  │  │  - Lightness (0-100%)                       │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ Brightness Dial (QDial)                     │  │  │
│  │  │       ╱ ‾ ╲                                 │  │  │
│  │  │      │  75% │   [Apply] [Turn Off]          │  │  │
│  │  │       ╲ _ ╱                                 │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Color Space Conversion (Internal Logic)               │
│  ┌───────────────────────────────────────────────────┐  │
│  │  RGB ←→ HSL Conversion                            │  │
│  │  - rgb01_to_hsl(): RGB[0,1] → HSL[0-360, 0-1, 0-1]│  │
│  │  - hsl_to_rgb01(): HSL → RGB[0,1]                │  │
│  │  - rgb255_to_rgb01(): Scale 0-255 → 0-1          │  │
│  │  - rgb01_to_rgb255(): Scale 0-1 → 0-255          │  │
│  │  - rgb255_to_rgbhex(): RGB → "#FF8000"           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Command Transmission                                   │
│  - Static:    "CMD_LED#mode#R#G#B#\n"                   │
│  - Breathing: "CMD_LED#breath#R#G#B#speed#\n"           │
│  - Rainbow:   "CMD_LED#rainbow#speed#\n"                │
│  - Off:       "CMD_LED#off#\n"                          │
└─────────────────────────────────────────────────────────┘
```

**Methods**:

| Method | Purpose | Trigger |
|--------|---------|---------|
| `mode1Color()` | Opens Qt color picker dialog | "Pick Color" button |
| `onCurrentColorChanged(color)` | Live preview during color selection | Color dialog drag |
| `changeRGBText()` | Updates HSL when RGB text changed | Text field edit |
| `changeHSLText()` | Updates RGB when HSL text changed | Text field edit |
| `dialValueChanged()` | Applies brightness scaling to current color | Dial rotation |
| `ledMode(index)` | Switches animation mode (static/breath/rainbow) | ComboBox change |
| `turnOff()` | Sends LED off command | "Turn Off" button |

**Command Protocol**:

```python
# Static color (RGB 180, 90, 255 at 75% brightness)
brightness_factor = 0.75
r, g, b = int(180 * brightness_factor), int(90 * brightness_factor), int(255 * brightness_factor)
self.client.send_data(f"CMD_LED#static#{r}#{g}#{b}#\n")

# Breathing mode (red, speed=5)
self.client.send_data("CMD_LED#breath#255#0#0#5#\n")

# Rainbow mode (speed=10)
self.client.send_data("CMD_LED#rainbow#10#\n")

# Turn off
self.client.send_data("CMD_LED#off#\n")
```

**Color Space Formulas** (implemented in `ledWindow`):

```python
# RGB to HSL
def rgb01_to_hsl(rgb: np.array) -> np.array:
    """
    Input: RGB in [0, 1]
    Output: HSL where H in [0, 360], S in [0, 1], L in [0, 1]
    """
    import colorsys
    h, l, s = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
    return np.array([h * 360, s, l])

# HSL to RGB
def hsl_to_rgb01(hsl: np.array) -> np.array:
    """
    Input: HSL where H in [0, 360], S in [0, 1], L in [0, 1]
    Output: RGB in [0, 1]
    """
    import colorsys
    r, g, b = colorsys.hls_to_rgb(hsl[0] / 360, hsl[2], hsl[1])
    return np.array([r, g, b])
```

**Widget Implementation Example**:

```python
# In ledWindow.__init__():
self.colorDialog = ColorDialog(self)
self.colorDialog.currentColorChanged.connect(self.onCurrentColorChanged)
self.colorDialog.setOption(QColorDialog.ShowAlphaChannel, False)
self.colorDialog.setOption(QColorDialog.NoButtons, True)

# Custom color dialog with circular preview
class ColorDialog(QColorDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_color = QColor(255, 255, 255)
    
    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(self.current_color))
        painter.drawEllipse(10, 10, 50, 50)  # Color preview circle
```

**Server-side LED Driver** (pseudocode):

```python
# In Robot Server code:
def handle_led_command(cmd_parts):
    mode = cmd_parts[1]
    
    if mode == "static":
        r, g, b = int(cmd_parts[2]), int(cmd_parts[3]), int(cmd_parts[4])
        neopixel.fill((r, g, b))
        neopixel.show()
    
    elif mode == "breath":
        r, g, b, speed = int(cmd_parts[2]), int(cmd_parts[3]), int(cmd_parts[4]), int(cmd_parts[5])
        start_breathing_animation(r, g, b, speed)
    
    elif mode == "rainbow":
        speed = int(cmd_parts[2])
        start_rainbow_animation(speed)
    
    elif mode == "off":
        neopixel.fill((0, 0, 0))
        neopixel.show()
```

---

### 4. Servo Calibration Module

**File**: `Calibration.py` → `calibrationWindow` class  
**UI Designer**: `Calibration.py` → `Ui_calibration`

**Purpose**: Fine-tune servo offsets for all 12 leg servos to correct assembly tolerances.

**Key Features**:
- **Per-Leg Calibration**: Adjust all 3 joints (coxa, femur, tibia) for each leg
- **Live Preview**: See servo movements in real-time during adjustment
- **Persistent Storage**: Save/load calibration to `Deviation.txt`
- **Reset Function**: Restore factory default positions

**Servo Layout**:

```
        Front
    ┌─────────────┐
    │  LF      RF │   LF = Left Front   (Servos 0,1,2)
    │   ●      ●  │   RF = Right Front  (Servos 3,4,5)
    │             │   LB = Left Back    (Servos 6,7,8)
    │  LB      RB │   RB = Right Back   (Servos 9,10,11)
    │   ●      ●  │
    └─────────────┘
         Back

Servo Mapping:
  Leg LF: Servo 0 (coxa), 1 (femur), 2 (tibia)
  Leg RF: Servo 3 (coxa), 4 (femur), 5 (tibia)
  Leg LB: Servo 6 (coxa), 7 (femur), 8 (tibia)
  Leg RB: Servo 9 (coxa), 10 (femur), 11 (tibia)
```

**Architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  calibrationWindow (QMainWindow)                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  UI Grid Layout (4 legs × 3 joints)              │  │
│  │  ┌──────────────┬──────────────┬──────────────┐  │  │
│  │  │   Servo 0    │   Servo 1    │   Servo 2    │  │  │
│  │  │  (LF Coxa)   │ (LF Femur)   │ (LF Tibia)   │  │  │
│  │  │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │  │  │
│  │  │ │  [+] [-] │ │ │  [+] [-] │ │ │  [+] [-] │ │  │  │
│  │  │ │ Offset:5 │ │ │ Offset:2 │ │ │ Offset:-3│ │  │  │
│  │  │ └──────────┘ │ └──────────┘ │ └──────────┘ │  │  │
│  │  └──────────────┴──────────────┴──────────────┘  │  │
│  │  (Repeated for RF, LB, RB legs...)               │  │
│  │                                                   │  │
│  │  [Save Calibration]  [Load Calibration]          │  │
│  │  [Reset to Defaults] [Test All Servos]           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Calibration Data Structure                             │
│  deviation = {                                          │
│      'LF_0': 5,    # Left Front, Servo 0 offset         │
│      'LF_1': -2,   # Left Front, Servo 1 offset         │
│      'LF_2': 3,    # Left Front, Servo 2 offset         │
│      'RF_0': 0,    # Right Front, Servo 0 offset        │
│      ...                                                │
│      'RB_2': -1    # Right Back, Servo 2 offset         │
│  }                                                      │
│  Stored in: Deviation.txt (plain text, one per line)    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Command Transmission                                   │
│  "CMD_SERVO#servo_id#angle#\n"                          │
│  Example: "CMD_SERVO#0#95#\n"  → Servo 0 to 95° (90+5)  │
└─────────────────────────────────────────────────────────┘
```

**Methods**:

| Method | Purpose | Trigger |
|--------|---------|---------|
| `X1()`, `X2()` | Increment/decrement X-axis servo offset | +/- button |
| `Y1()`, `Y2()` | Increment/decrement Y-axis servo offset | +/- button |
| `Z1()`, `Z2()` | Increment/decrement Z-axis servo offset | +/- button |
| `save()` | Writes all offsets to `Deviation.txt` | "Save" button |
| `get_point()` | Loads offsets from `Deviation.txt` | Window init |
| `set_point(data)` | Sends servo commands with offsets applied | Any adjustment |
| `leg_point(leg)` | Returns calibration dict for specific leg | Internal helper |

**Calibration Workflow**:

```
Initial Setup
   │
   ▼
┌────────────────────────────────────┐
│ 1. Power on robot, stand position │
│    All servos at 90° (neutral)    │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 2. Visually inspect leg alignment │
│    - Legs should be vertical      │
│    - Feet flat on ground          │
│    - Body level                   │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 3. Adjust each misaligned servo   │
│    - Click [+] to increase angle  │
│    - Click [-] to decrease angle  │
│    - Range: typically -10 to +10  │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 4. Click "Save Calibration"       │
│    Writes: Deviation.txt          │
│    Format: LF_0#5#                │
│           LF_1#-2#                │
│           ...                     │
└───────────┬────────────────────────┘
            │
            ▼
┌────────────────────────────────────┐
│ 5. Test walking gait              │
│    - Use WASD keys to move        │
│    - Verify smooth motion         │
│    - Repeat calibration if needed │
└────────────────────────────────────┘
```

**File Format** (`Deviation.txt`):

```
LF_0#5#
LF_1#-2#
LF_2#3#
RF_0#0#
RF_1#1#
RF_2#-1#
LB_0#2#
LB_1#0#
LB_2#-4#
RB_0#-3#
RB_1#2#
RB_2#1#
```

**Code Example**:

```python
# In calibrationWindow:
def X1(self):
    """Increment X-axis (coxa) servo offset"""
    self.X += 1  # Increase offset
    self.set_point(f"CMD_SERVO#0#{90 + self.X}#\n")  # Send to robot
    self.label_X.setText(str(self.X))  # Update UI

def save(self):
    """Save all calibration data to file"""
    data = []
    for leg in ['LF', 'RF', 'LB', 'RB']:
        points = self.leg_point(leg)  # Get current offsets
        for i in range(3):
            data.append(f"{leg}_{i}#{points[i]}#\n")
    self.Save_to_txt(data, 'Deviation.txt')
    QMessageBox.information(self, "Success", "Calibration saved!")
```

---

## 🔄 Common Workflows

### Workflow 1: First Connection & Calibration

```
┌──────────────────────────────────────────────┐
│ Step 1: Power on Robot                       │
│   • Battery voltage ≥ 7.5V                   │
│   • Wait 30 seconds for boot                 │
│   • LED should blink (server ready)          │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Find Robot IP Address               │
│   Method A: Check router DHCP table          │
│   Method B: nmap scan                        │
│     $ sudo nmap -sn 192.168.1.0/24           │
│   Method C: Connect monitor to Pi            │
│     $ hostname -I                            │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Launch Client & Connect             │
│   • Run: python Main.py                      │
│   • Enter IP, click "Connect"                │
│   • Verify: Video displays, battery shows    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Servo Calibration (if needed)       │
│   • Click "Stand" button                     │
│   • Open: Menu → Calibration                 │
│   • Adjust offsets until robot stands level │
│   • Click "Save Calibration"                 │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Test Movement                       │
│   • Press W/A/S/D keys                       │
│   • Verify smooth gait                       │
│   • Check battery doesn't drop rapidly       │
└──────────────────────────────────────────────┘
```

---

### Workflow 2: Face Recognition Setup

```
┌──────────────────────────────────────────────┐
│ Step 1: Open Face Recognition Window        │
│   Menu: Features → Face Recognition          │
│   (Or click "Face" button in main window)    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Capture Training Images             │
│   • Position subject 1-2 meters from robot   │
│   • Good lighting (avoid harsh shadows)      │
│   • Subject faces camera directly            │
│   • Click "Capture" button                   │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Label and Save                      │
│   • Enter name in text field (e.g., "Alice") │
│   • Click "Save" button                      │
│   • Repeat 3-5 times with different angles:  │
│     - Front view                             │
│     - 30° left/right                         │
│     - Slight up/down tilt                    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Enable Real-time Detection          │
│   • Click "Detect" button                    │
│   • Robot starts face tracking               │
│   • Green box + name appears when recognized │
│   • Red box if face unknown                  │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Test & Refine                       │
│   • Move subject to different distances      │
│   • Test in different lighting conditions    │
│   • Add more training images if needed       │
└──────────────────────────────────────────────┘
```

---

### Workflow 3: Ball Tracking Mode

```
┌──────────────────────────────────────────────┐
│ Step 1: Prepare Ball                        │
│   • Use solid-color ball (red/orange best)   │
│   • Size: 5-10 cm diameter                   │
│   • Avoid shiny/reflective surfaces          │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Enable Ball Tracking                │
│   • Click "Ball/Face" button                 │
│   • Button text changes to "Face"            │
│   • Robot enters autonomous tracking mode    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Position Ball                       │
│   • Place ball 1-2 meters in front           │
│   • In well-lit area                         │
│   • Robot should turn toward ball            │
│   • Blue circle drawn around detected ball   │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Observe Behavior                    │
│   • Robot follows ball movements             │
│   • Stops when ball within 30cm              │
│   • Loses tracking if ball moves too fast    │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Adjust HSV (if needed)              │
│   • If detection fails:                      │
│     - Edit Server/vision_config.py           │
│     - Adjust HSV_LOWER/UPPER values          │
│     - Restart robot server                   │
└──────────────────────────────────────────────┘
```

---

### Workflow 4: LED Customization

```
┌──────────────────────────────────────────────┐
│ Step 1: Open LED Control Window             │
│   Menu: Features → LED Control               │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 2: Choose Color Method                 │
│   Method A: Color Picker                     │
│     • Click "Pick Color" button              │
│     • Drag to select hue                     │
│     • Adjust saturation/brightness           │
│   Method B: RGB Sliders                      │
│     • Red: 0-255                             │
│     • Green: 0-255                           │
│     • Blue: 0-255                            │
│   Method C: HSL Text Input                   │
│     • Hue: 0-360°                            │
│     • Saturation: 0-100%                     │
│     • Lightness: 0-100%                      │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 3: Select Animation Mode               │
│   • Static: Solid color                      │
│   • Breathing: Fade in/out (specify speed)   │
│   • Rainbow: HSV color cycle                 │
│   • Chase: Sequential LED activation         │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 4: Adjust Brightness                   │
│   • Rotate dial (0-100%)                     │
│   • Preview updates in real-time             │
└───────────────┬──────────────────────────────┘
                ▼
┌──────────────────────────────────────────────┐
│ Step 5: Apply & Save                        │
│   • Click "Apply" to send to robot           │
│   • LED color changes immediately            │
│   • Settings persist until power cycle       │
└──────────────────────────────────────────────┘
```

---

## 📜 Revision History

### Main.py Evolution

| Version | Date | Changes |
|---------|------|---------|
| v1.20 | 2025-11-15 | Added visible "DebugWin" button above "Close Video" for UX improvement |
| v1.19 | 2025-11-13 | Integrated `DebugStreamWindow` (press T/F10 to open), enriched documentation |
| v1.18 | 2025-11-13 | Shrank status bar overlay, added optional GUI heartbeat for diagnostics |
| v1.17 | 2025-11-12 | Fixed QImage stride bug (`rgb.strides[0]`), continuous placeholder updates |
| v1.16 | 2025-11-12 | Auto-start video after connect, draw status on placeholder frames |
| v1.15 | 2025-11-12 | iOS-style status bar overlay, safer connect flow with timeout validation |
| v1.00 | Initial | Port from original Freenove codebase (now archived as `Main_Freenove.py`) |

### Client.py Evolution

| Version | Date | Changes |
|---------|------|---------|
| v1.15 | 2025-11-13 | Added `video_last_frame_ts` for FPS calculation, improved frame metadata |
| v1.14 | 2025-11-12 | Fixed struct format (`'<I'` enforcement), added `frames_produced` counter |
| v1.13 | 2025-11-11 | Thread-safe flag checks, added connection timeout handling |
| v1.12 | 2025-11-10 | Refactored `turn_off_client()` to prevent socket leaks |
| v1.00 | Initial | Original implementation (basic TCP client) |

---

## 🧵 Threading Model

### Thread Lifecycle

```
Application Start
       │
       ▼
┌──────────────┐
│ Qt Main Loop │ (Primary thread - never blocks)
└──────┬───────┘
       │
       │ User clicks "Connect"
       ▼
┌────────────────────────────────────────┐
│  connect() method                      │
│  1. Creates sockets (non-blocking)     │
│  2. Spawns threads:                    │
│     - video_thread                     │
│     - instruction_thread               │
│  3. Starts timers:                     │
│     - refresh_image (33ms)             │
│     - power (1000ms)                   │
│     - sonic (1000ms)                   │
│     - overlay_timer (500ms)            │
└────────────────────────────────────────┘
       │
       ▼
┌─────────────────────┬──────────────────────┐
│  video_thread       │ instruction_thread   │
│  (Client.py)        │ (Main.py)            │
│  - Recv binary      │ - Recv text lines    │
│  - Decode JPEG      │ - Parse telemetry    │
│  - Update image     │ - Update UI state    │
│  - Loop until       │ - Loop until         │
│    tcp_flag=False   │   tcp_flag=False     │
└─────────────────────┴──────────────────────┘
       │                       │
       │ User clicks "Disconnect"
       ▼                       ▼
┌──────────────────────────────────────────┐
│  closeEvent() / disconnect               │
│  1. Sets tcp_flag = False                │
│  2. Calls stop_thread() [⚠️ deprecated]  │
│  3. Closes sockets                       │
│  4. Stops all timers                     │
└──────────────────────────────────────────┘
```

### Thread Safety Checklist

✅ **Safe Operations**:
- Reading `Client.image` under `image_lock`
- Calling `send_data()` from any thread
- Modifying Qt widgets via `QTimer.singleShot(0, lambda: ...)`

❌ **Unsafe Operations**:
- Directly modifying `Client.image` without lock
- Calling `stop_thread()` (uses deprecated `PyThreadState_SetAsyncExc`)
- Blocking Qt main thread with `time.sleep()` or `socket.recv()`

---

## 🎥 Video Pipeline

### Frame Flow (Producer-Consumer Pattern)

```
Robot (Port 8001)
      │
      │ Binary stream: <len><JPEG><len><JPEG>...
      ▼
┌──────────────────────────────────────────────┐
│ Client.receiving_video() [Producer Thread]   │
│ 1. Read 4 bytes → frame_length               │
│ 2. Read frame_length bytes → jpeg_data       │
│ 3. cv2.imdecode(jpeg_data) → BGR numpy array │
│ 4. Acquire image_lock                        │
│ 5. self.image = frame.copy()                 │
│ 6. self.video_flag = False (new frame ready) │
│ 7. Release image_lock                        │
└──────────────────────────────────────────────┘
      │
      │ Every 33ms
      ▼
┌──────────────────────────────────────────────┐
│ MyWindow.refresh_image() [Consumer/Qt Thread]│
│ 1. Acquire image_lock                        │
│ 2. if isinstance(image, np.ndarray):         │
│ 3.   base = image.copy()                     │
│ 4.   video_flag = True (mark consumed)       │
│ 5. Release image_lock                        │
│ 6. Draw overlays on base (NOT on shared buf) │
│ 7. Convert BGR → RGB                         │
│ 8. Create QImage with .copy() (memory safety)│
│ 9. setPixmap() to QLabel                     │
└──────────────────────────────────────────────┘
      │
      ▼
   Display
```

### Overlay Rendering

**Layers** (drawn in order):
1. **Base frame** (BGR from camera)
2. **Top bar** (semi-transparent black, 30px height):
   - Left: IP:Port, elapsed time, robot state
   - Center: Distance (XX.Xcm)
   - Right: Battery (X.XXV), FPS
3. **Stall badge** (if no new frames >2s):
   - Red rectangle with "Stalled X.Xs" text

**Implementation** (`testVideoStream.draw_top_bar`):

```python
def draw_top_bar(frame, fps, battery_v, distance_cm, state_text, state_since):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0,0), (w, 30), (0,0,0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    # Left: IP/state
    elapsed = int(time.time() - state_since)
    cv2.putText(frame, f"{state_text} {elapsed}s", (5, 20), ...)
    
    # Center: Distance
    if distance_cm:
        cv2.putText(frame, f"{distance_cm:.1f}cm", (w//2-30, 20), ...)
    
    # Right: Battery/FPS
    if battery_v:
        cv2.putText(frame, f"{battery_v:.2f}V", (w-100, 20), ...)
    cv2.putText(frame, f"{fps:.1f}fps", (w-50, 20), ...)
```

---

## 📡 Telemetry System

### Battery Monitoring

**Flow**:

```
Main.py (timer_power)
   │ Every 1000ms
   ▼
power() → send_data("CMD_POWER\n")
   │
   ▼
Robot processes command
   │
   ▼
Robot sends "Power#8.12#\n" on port 5001
   │
   ▼
receive_instruction() receives line
   │
   ▼
_handle_server_line() parses:
   - Extracts float from "Power#8.12#"
   - Sets self.tele_batt_v = 8.12
   - Calculates percentage: (8.12 - 7.0) / 1.4 * 100
   - Updates progress_Power via QTimer.singleShot()
```

**Battery Voltage Mapping**:

| Voltage | Percentage | Status |
|---------|------------|--------|
| 8.40V   | 100%       | Full charge |
| 7.70V   | 50%        | Normal |
| 7.00V   | 0%         | Critical (shutdown) |

### Distance Sensing

**Flow**:

```
Main.py (timer_sonic)
   │ Every 1000ms (when enabled)
   ▼
getSonicData() → send_data("CMD_SONIC\n")
   │
   ▼
Robot measures ultrasonic distance
   │
   ▼
Robot sends "Sonic#45.3#\n"
   │
   ▼
_handle_server_line() parses:
   - Extracts float from "Sonic#45.3#"
   - Sets self.tele_dist_cm = 45.3
   - Overlay shows "45.3cm" in next refresh_image()
```

---
## 🛠️ Development Guidelines

### Before Making Changes
- Create backup: `cp Main.py Main_backup_$(date +%Y%m%d).py`
- Check revision history: verify you modify the latest version.
- Read threading contract: never block the Qt main thread.
- Test video pipeline: run with `debug_ui_enabled = True`.

### Adding New Features

Example: Add gyroscope telemetry

1) Server-side (Robot Pi):
```python
# Send gyroscope telemetry periodically (server-side)
gyro_x, gyro_y, gyro_z = read_gyroscope()  # Returns floats
client_socket.send(f"Gyro#{gyro_x}#{gyro_y}#{gyro_z}#\n".encode("utf-8"))
```

2) Client-side (Main.py):
```python
# In MyWindow.__init__():
self.tele_gyro_xyz = None

# In _handle_server_line():
if "GYRO" in tag:
    if len(parts) >= 4:
        try:
            gx, gy, gz = float(parts[1]), float(parts[2]), float(parts[3])
            self.tele_gyro_xyz = (gx, gy, gz)
        except ValueError:
            pass
    return
```

3) Display overlay (optional, e.g., in testVideoStream.draw_top_bar):
```python
if gyro_xyz:
    gx, gy, gz = gyro_xyz
    cv2.putText(frame, f"Gyro {gx:.1f},{gy:.1f},{gz:.1f}",
                (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
```

### Performance Tuning

Video Stream Optimization
```python
# Client-side (Main.py)
TIMER_INTERVAL_MS = 33       # ~30 FPS. Use 50ms for lower CPU, 16ms for higher FPS.
OVERLAY_TIMER_MS = 500       # Update overlay every 0.5s

# Server-side (Pi)
JPEG_QUALITY = 75            # 50-95 (lower = faster, lower quality)
RESOLUTION = (640, 480)      # Use (320, 240) for higher FPS on slower networks
FPS_TARGET = 25
```

Network Optimization
```python
# Client.py
SOCKET_TIMEOUT = 2.0         # Seconds
RECV_BUFFER_SIZE = 65536     # Increase for high-res streams (e.g., 131072)
```

```bash
# Raspberry Pi sysctls (optional)
sudo sysctl -w net.ipv4.tcp_window_scaling=1
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
```

Memory Management
```python
# In refresh_image(), always work on a copy
with self.client.image_lock:
    if isinstance(self.client.image, np.ndarray):
        base = self.client.image.copy()
        self.client.video_flag = True

# Periodic GC (optional)
if hasattr(self.client, 'frames_displayed') and self.client.frames_displayed % 1000 == 0:
    import gc; gc.collect()
```

CPU Usage Optimization
```python
# Avoid heavy per-frame allocations; reuse buffers when possible
# Keep overlay drawing simple (small fonts, minimal blending)
```

Battery Life Optimization
```python
def enter_low_power_mode(self):
    # Slow down telemetry
    if hasattr(self, 'timer_power'):
        self.timer_power.setInterval(5000)
    if hasattr(self, 'timer_sonic'):
        self.timer_sonic.stop()
    # Dim LEDs
    self.client.send_data("CMD_LED#static#10#10#10#\n")
```

---

## ⚠️ Error Codes Reference

Connection Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| E001 | Connect Failed | Robot unreachable | Check IP, ping robot, verify WiFi and power |
| E002 | Port 5001 refused | Command server down | Restart server on Pi |
| E003 | Port 8001 refused | Video server down | Check camera, restart video service |
| E004 | Connection timeout | High latency/packet loss | Move closer to router; increase timeouts |

Video Stream Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| V001 | JPEG decode failed | Corrupt frame | Lower JPEG quality; check WiFi |
| V002 | Frame size mismatch | struct format mismatch | Ensure both ends use '<I' little-endian |
| V003 | Video stalled >5s | Producer died | Check server logs; restart video |
| V004 | FPS <5 | CPU/network bottleneck | Lower resolution; increase timer interval |
| V005 | QImage creation failed | Invalid dims/stride | Validate frame shape and stride |

Hardware Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| H001 | Battery <7.0V | Low battery | Charge immediately |
| H002 | Servo timeout | Wiring/power issue | Check servo wiring, supply |
| H003 | IMU read failed | I2C error | Re-seat IMU; i2cdetect -y 1 |
| H004 | Camera not found | /dev/video0 missing | Enable camera; reboot; test raspistill |
| H005 | Ultrasonic timeout | Sensor not responding | Check TRIG/ECHO pins; test script |

Debug Commands
```bash
# Connectivity
ping <robot_ip>
traceroute <robot_ip>

# Open ports
nmap -p 5001,8001 <robot_ip>

# Live traffic
sudo tcpdump -i wlan0 host <robot_ip> and '(port 5001 or port 8001)'
```

---

## 🐛 Troubleshooting

Video not displaying
- Symptoms: Black screen or only placeholder.
- Checks:
  - Confirm server: ports 5001/8001 listening on Pi.
  - Confirm frames arrive: Client.receiving_video prints frame sizes.
  - Ensure image_lock usage around shared buffers.
  - Call self.Video.update() after setPixmap if needed.

Connection timeout
- Verify robot IP (router DHCP, nmap, or hostname -I on Pi).
- Check firewall on macOS (System Settings → Network → Firewall).
- Try increasing Client.py socket timeouts.

Frame rate drops
- Lower resolution or JPEG quality on server.
- Increase timer interval to 50ms in Main.py.
- Close CPU-heavy tasks on Pi; check WiFi quality.

Battery drains quickly
- Disable LED animations or use dim static color.
- Reduce telemetry frequency; stop ultrasonic polling when idle.

---

## 📚 Related Files
- Server code (Pi): ./Server/
- Hardware drivers: Servo, IMU, ultrasonic, camera modules
- Archived reference: Main_Freenove.py

---

## 🤝 Contributing
- Keep UI responsive; no blocking calls in Qt thread.
- Update file headers and Revision History when changing behavior.
- Include sanity checks for new telemetry parsers.
- Document new commands in Communication Protocols section.

Pull Request checklist
- Tested connect/disconnect and graceful shutdown.
- Verified video pipeline works 5+ minutes without leaks.
- Checked telemetry parsing with simulated lines and edge cases.
- Updated README Feature Modules/Revision History if applicable.

---

## 📄 License
See the project’s LICENSE file.

---

╔══════════════════════════════════════════════════════════════════════════╗
║                          END OF DOCUMENTATION                            ║
╚══════════════════════════════════════════════════════════════════════════╝

Document Version  : 1.1  
Last Updated      : 2025-11-17 15:45 PST  
Maintained By     : MT (Lead Developer), GitHub Copilot (AI Assistant)  
Repository        : /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/  
Status            : Production - Actively Maintained
