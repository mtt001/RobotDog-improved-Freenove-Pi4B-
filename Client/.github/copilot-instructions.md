# Copilot Instructions — Freenove Robot Dog Client (Code/Client)

## Run / Environment (macOS)
- **Virtual Environment**: Always use `~/.venvs/freenove-client/bin/python`.
  - Use VS Code task **Run Dog Client** or alias `smartdog` (which activates venv + cds to folder).
  - *Never* use system python (`/usr/bin/python3`) or Homebrew python directly.
- **Dependencies**: 
  - `opencv-contrib-python` (headless or normal) — avoid mixing with `opencv-python`.
  - `ultralytics` for YOLO, `openai` for GPT Vision.
- **Environment Variables**:
  - `OPENAI_API_KEY`: Required for `mtBallDetectAI.py`.
  - `YOLO_MODEL_PATH`: Optional override for `mtBallDetectYOLO.py` (default: `yolov8n.pt`).

## Architecture & Code Structure
- **Entry Point**: `mtDogMain.py` (PyQt5 GUI).
  - Owns `Client` instance, camera timers, and logic mixins.
  - Never block the Qt main thread. Use `QTimer` for polling.
- **Networking**:
  - **Cmd/Telemetry**: TCP port `5001` (Text-based, line-delimited).
  - **Video Stream**: TCP port `8001` (Custom binary: 4-byte little-endian length + JPEG bytes).
- **Core Modules**:
  - `Client.py`: Socket management, video thread, keep-alive.
  - `mtDogLogicMixin.py`: "Dog mode" behavior (networking, motion) mixed into main window.
  - `mtDogBallTrack.py`: Ball tracking states, smoothing, and calibration.
- **Vision Detectors**: Mutually exclusive modes in UI.
  - `mtBallDetectCV.py`: Conventional Computer Vision (Lab a-channel).
  - `mtBallDetectYOLO.py`: On-device YOLOv8 (fast, robust).
  - `mtBallDetectAI.py`: Cloud-based GPT-4o Vision (slow, high latency, high intelligence).

## Coding Conventions
- **UI Rendering**: OpenCV (BGR) → RGB → `QImage` → `QPixmap` → `QLabel`.
- **Logging**: Short, tagged prefixes: `[PING]`, `[CAM]`, `[YOLO]`, `[AI]`.
- **Revision History Header** (Strictly Required):
  - Every file must have a standard banner.
  - Update `vX.XX` and add a changelog entry at the **TOP** of the list (descending date).
  - Format:
    ```python
    # v3.08  (2026-01-30)          : Feature Name
    #     • Brief description of changes.
    ```
- **Backups**: If user says "Backup", copy the current file to `Backup/Revisions_Backup/` with version suffix (e.g., `mtDogMain.v308.py`).

## Critical Workflows
- **Running the App**: `~/.venvs/freenove-client/bin/python mtDogMain.py`
- **YOLO Training**: See VS Code tasks (e.g., "Train YOLO v01").
- **Testing**:
  - Use `Temp/test_compare_ai_yolo_images.py` for model comparison.
  - Use `testAIVisionRepeat.py` for API stability checks.
- **Debugging**:
  - Press `T` or `F10` in main window for live video pipeline debug overlay.
  - `IP.txt` holds the target robot address.

## Specific Implementation Details
- **Video Protocol**: Do NOT change the `<I` (struct.pack) length prefix behavior. It is not standard MJPEG over HTTP.
- **Ball Source**: External detectors feed `BallTracker.apply_external_detection()` which handles smoothing/jump rejection.
- **Auto-Silence**: `mtDogMain.py` sets `OPENCV_LOG_LEVEL` to OFF to suppress noisier backend logs.
