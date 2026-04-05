# Freenove Robot Dog — What Can I Do Here?

## Version
v2.1 (2026-04-05 23:12 UTC)

## Revision History
- 2026-04-05 23:12 v2.1  Fix keyboard shortcut table: D = Turn Right (also schedules servo relax); remove duplicate relax row.
- 2026-04-05 23:12 v2.0  Comprehensive "What can I do here?" feature overview.
- 2025-11-12 v1.0  Initial code overview note by MT.

---

This repository contains all operational code for the improved **Freenove Robot Dog (Raspberry Pi 4B)**.
It is split into two main areas:

| Subfolder | Platform | Description |
|------------|-----------|-------------|
| [`Client/`](Client/) | macOS / Desktop | PyQt5 GUI for control, video, and vision. |
| [`Server/`](Server/) | Raspberry Pi 4B | Handles camera, servos, sensors, and telemetry. |

---

## 🤖 What Can I Do Here?

### 1. Control the Robot Dog
Drive the dog from the desktop GUI (`mtDogMain.py`) over Wi-Fi:

| Action | Keyboard | Description |
|--------|----------|-------------|
| Walk forward | `W` | Move forward at configured speed |
| Walk backward | `S` | Move backward |
| Strafe left | `Q` | Side-step left |
| Strafe right | `E` | Side-step right |
| Turn left | `A` | Rotate in place left |
| Turn right | `D` | Rotate in place right; also schedules a servo-relax sequence after 5 s |
| Emergency stop | `Space` | Immediately stop all motion (`CMD_MOVE_STOP`) |

- **Speed** is configurable from the GUI or via the config file.
- **Multi-client safety**: if more than one client connects, only the first writer becomes the *control owner*; others are rejected with `CMD_BUSY#OWNER:<ip:port>` for any motion command. Safety-stop commands (`CMD_MOVE_STOP`, `CMD_RELAX`, `CMD_STOP_PWM`) are always accepted from any client.

---

### 2. Watch Live Video
Two video backend options are selectable in [`Client/config/mtDogConfig.py`](Client/config/mtDogConfig.py):

| Backend | Setting | Description |
|---------|---------|-------------|
| **SFU / RTSP** (recommended) | `VIDEO_BACKEND = "sfu_rtsp"` | H.264 stream via MediaMTX SFU — low latency, 720p@30 fps. |
| **Legacy socket** | `VIDEO_BACKEND = "legacy_socket"` | Original Freenove JPEG stream on port `8001`. |

The SFU path supports **multiple simultaneous viewers** (Mac GUI + iPhone/iPad Safari) from a single Pi publisher.

---

### 3. Read Live Telemetry
The GUI continuously polls the Pi for:

| Sensor | Command | Description |
|--------|---------|-------------|
| Battery voltage | `CMD_POWER` | Alerts when voltage drops below `LOW_VOLTAGE_THRESHOLD` (default 6.5 V). |
| Ultrasonic distance | `CMD_SONIC` | Front obstacle range in cm. |
| IMU roll / pitch / yaw | `CMD_ATTITUDE` | 6-axis MPU-6050 orientation angles. |
| Working time / overuse | `CMD_WORKING_TIME` | Servo active/rest time tracking. |

---

### 4. Adjust Body Pose
Send real-time pose commands from sliders or keyboard shortcuts:

| Command | Description |
|---------|-------------|
| `CMD_HEIGHT` | Raise or lower body height. |
| `CMD_HORIZON` | Shift body forward or backward. |
| `CMD_ATTITUDE` | Set roll, pitch, and yaw angles. |
| `CMD_BALANCE` | Enable IMU-based automatic balance mode. |
| `CMD_HEAD` | Rotate the head servo (0–180°). |

---

### 5. Control LEDs and Buzzer

| Command | GUI shortcut | Description |
|---------|-------------|-------------|
| `CMD_LED` / `CMD_LED_MOD` | **LED** button (`L`) | Set LED mode and RGB colour. |
| `CMD_BUZZER` | **Buzzer** button (`B`) | Trigger buzzer beep. |

---

### 6. Track a Ball Autonomously
Enable **ball tracking mode** (press the **Tracking** button in the GUI):

- **Computer Vision (OpenCV)**: HSV colour thresholding with morphological cleanup, contour-based detection, EMA smoothing, and jump rejection.
- **YOLO + OpenCV hybrid**: dual-model ensemble — `yolov8n.pt` (COCO sports-ball) and a custom `best.pt` (MT ball class) running together at up to 10 FPS.
- **Three tracking modes**:
  - `HEAD` — move the head servo to follow the ball.
  - `BODY` — move the whole dog body (turn + forward/backward) to chase the ball.
  - `FULL` — combined head + body tracking until the ball is close enough.
- **Calibration**: open the **Mask window** (HSV sliders, histograms) to tune colour gates and tracking parameters. Settings auto-save to `config/mtBall_Calib.json`.

---

### 7. Run YOLO Object Detection
Press **Yolo Vision** in the GUI to toggle the detector overlay (no autonomous motion):

- Models: swap between `yolov8n.pt` (COCO 80 classes) and `best.pt` (custom MT ball) at runtime.
- Live controls: adjust confidence threshold and input size without restarting.
- **Compare mode**: side-by-side window showing both models simultaneously.
- **Dataset capture / labelling**: collect and label training images for custom YOLO fine-tuning.

---

### 8. Calibrate Servos
Press **Cal** (or `K`) to enter calibration mode:

- Adjust each of the four legs (one, two, three, four) in X/Y/Z.
- Save calibration points to `Server/point.txt` with `CMD_CALIBRATION#save`.
- Reference: [`Server/calibrateServo.md`](Server/calibrateServo.md).

---

### 9. Serve Video to iPhone / iPad
The SFU WebRTC stack in [`Client/tools/realtime_webrtc/`](Client/tools/realtime_webrtc/) enables browser playback:

1. Start MediaMTX SFU (on Mac or Pi).
2. Start the Pi publisher (`robot/pi_publish_webrtc.sh`).
3. Open `http://<sfu-host>:8080/webrtc_view.html` in Safari.

iPhone/iPad receives a low-latency H.264 WebRTC stream without needing any app installation.

---

### 10. Run Diagnostics
Quick health checks without starting the full GUI:

```bash
# Check Pi ports from Mac
smartdog python3 - <<'PY'
import socket
for h, p in [('192.168.0.32', 5001), ('192.168.0.32', 8001)]:
    s = socket.socket(); s.settimeout(2)
    try:
        s.connect((h, p)); print('OK', h, p)
    except Exception as e:
        print('FAIL', h, p, e)
    s.close()
PY

# On the Pi — show listeners
ss -lntp | egrep ':5001|:8001'

# Tail server log
tail -n 200 /tmp/smartdog.log
```

---

## 🚀 Quick Start

### On the Raspberry Pi
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
python3 main.py -tn
```

### On the Mac (Desktop Client)
```bash
smartdog                    # activate venv + cd to Client/
python3 mtDogMain.py        # launch main GUI
```

---

## 📁 Project Layout

```
.
├── Client/                 macOS desktop client
│   ├── mtDogMain.py        Main PyQt5 GUI entry point
│   ├── mtDogLogicMixin.py  Networking, telemetry, command logic
│   ├── config/             Runtime configuration (IP, ports, YOLO settings)
│   ├── controllers/        Modular controllers (video, ball, command, …)
│   ├── ui/                 UI widgets and panel builders
│   ├── vision/             YOLO, CV detection, overlay rendering
│   └── tools/              WebRTC/SFU stack, YOLO labelling utilities
├── Server/                 Raspberry Pi server
│   ├── main.py             Server entry point
│   ├── Server.py           TCP multi-client control server (port 5001)
│   ├── Control.py          Motion execution loop
│   ├── Servo.py            Servo driver
│   ├── IMU.py              MPU-6050 IMU driver
│   ├── Ultrasonic.py       HC-SR04 ultrasonic sensor
│   ├── Led.py              LED strip driver
│   ├── Buzzer.py           Buzzer driver
│   └── Command.md          Full command reference
├── NEXT_DEVELOPMENT_PROPOSAL.md   Roadmap (mobile WebRTC, YOLO on Pi, …)
└── README.md               This file — project overview
```

---

## 🛣️ What's Coming Next?
See [`NEXT_DEVELOPMENT_PROPOSAL.md`](NEXT_DEVELOPMENT_PROPOSAL.md) for the full roadmap, including:
- **Phase 1**: Always-on SFU hosting so iPhone works without the MacBook.
- **Phase 2**: Read-only telemetry overlay in the Safari mobile viewer.
- **Phase 3**: Safe mobile command MVP (STOP, RELAX, limited motion).
- **Follow-on**: Lightweight YOLO object detection + tracking on the Pi 4B itself.

---

> **Note by MT (2025-11-12):** `Client/` is the active development folder. `Client(Original)/` is the unmodified Freenove download kept for reference.
