# mtDog.md

## Overview

This document provides an in-depth explanation of the ball tracking and calibration system for the Freenove Robot Dog Client (Mac mode), focusing on the code in `mtDogMain.py` and `mtDogBallTrack.py`. It covers architecture, class responsibilities, HSV picker logic, mask calibration, and user interaction.

---

## 1. Architecture & Main Components

### 1.1. CameraWindow (`mtDogMain.py`)
- **Role:** Main application window, handles UI, video, ball tracking, and user interaction.
- **Key Members:**
  - `BallTracker` instance: Handles all HSV thresholding, mask computation, and picker state.
  - `BallMaskWindow` instance: Separate calibration/mask window.
  - `HeadTracker` instance: For head servo tracking.
  - Networking and telemetry via `DogLogicMixin`.

### 1.2. BallTracker (`mtDogBallTrack.py`)
- **Role:** Core logic for ball detection, HSV thresholding, smoothing, and picker state.
- **Key Features:**
  - HSV thresholding with two hue segments.
  - Contour selection based on area and circularity.
  - Exponential smoothing and jump rejection for stable tracking.
  - Shared HSV picker (click-and-stay) for both color and mask windows.
  - Rolling trace of detected ball centers.
  - JSON-based config persistence.

### 1.3. BallMaskWindow (`mtDogBallTrack.py`)
- **Role:** Calibration window for mask visualization and HSV tuning.
- **Key Features:**
  - Displays thresholded mask with overlays.
  - Shows shared picker dot and HSV info.
  - Provides sliders for HSV, kernel size, smoothing, and circularity.
  - Rolling histograms for H, S, V channels.
  - Handles mouse clicks for picker selection.

---

## 2. HSV Picker Logic

### 2.1. Unified Picker State
- **Variables:**  
  - `sample_point` / `picker_point`: (x, y) image coordinates of the selected pixel.
  - `sample_hsv` / `picker_hsv`: (H, S, V) value at the picker point.
- **Synchronization:**  
  - Both color and mask windows use the same picker state.
  - Picker is updated only on mouse click (not on mouse move).
  - Picker dot and HSV info are drawn in both windows.

### 2.2. Picker Behavior
- **Click-and-stay:**  
  - Mouse click in either window sets the picker.
  - Picker remains until another click.
  - Sliders can be adjusted independently.
  - Histogram and overlays are based on the stationary picker.

### 2.3. Picker Implementation
- **Setting the Picker:**
  - `set_sample_point(point, hsv)` and `set_picker(point, hsv)` (alias) update the picker state.
- **Drawing the Picker:**
  - Red dot and HSV info are drawn at the picker location in both windows.
  - Info is shown at the bottom-left in both color and mask windows.

---

## 3. Ball Detection & Mask Processing

### 3.1. Mask Computation
- **Method:** `compute_mask(frame_bgr)`
  - Converts frame to HSV.
  - Applies two hue ranges (if configured).
  - Morphological operations (erode, dilate) for noise reduction.

### 3.2. Ball Detection
- **Method:** `process_with_mask(frame_bgr)`
  - Finds contours in the mask.
  - Selects the best contour based on area and circularity.
  - Applies jump rejection and exponential smoothing.
  - Updates trace history for visual trail.
  - Draws overlays: ball circle, center, trace, and HSV info.

---

## 4. BallMaskWindow: Calibration & Visualization

### 4.1. UI Elements
- **Mask Display:** Shows the thresholded mask with overlays.
- **Sliders:** For H1/H2/S/V, kernel size, EMA smoothing, and min circularity.
- **Histograms:** Rolling histograms for H, S, V channels.
- **HUD:** Shows picker HSV and (x, y) at the bottom-left.

### 4.2. Mouse Interaction
- **Click:** Sets the picker point using `_update_sample_from_pos()`.
- **Move:** Does not update the picker (click-to-hold behavior).

### 4.3. Histogram Rendering
- **Method:** `_update_histograms()`
  - Renders histograms for H, S, V.
  - Shows peak, standard deviation, and slider markers.

---

## 5. Synchronization & Data Flow

### 5.1. Frame Update Flow
1. `CameraWindow.update_frame()` (main window)
    - Gets latest frame.
    - Calls `BallTracker.process_with_mask()`.
    - Draws overlays (including picker).
    - Calls `BallMaskWindow.update_from_frame(frame, mask)`.

2. `BallMaskWindow.update_from_frame()`
    - Updates mask display.
    - Draws overlays and picker info.
    - Updates histograms.

### 5.2. Picker Update Flow
- Mouse click in either window:
    - Calls `set_sample_point()` in `BallTracker`.
    - Both windows reflect the new picker state and update overlays/histograms.

---

## 6. Error Handling & Robustness

- **Index Clamping:**  
  - All (x, y) accesses are clamped to image bounds to prevent `IndexError`.
- **Frame Availability:**  
  - All frame-dependent operations check for `None` before proceeding.

---

## 7. Example: Picker Update in Mask Window

```python
def mousePressEvent(self, event):
    if event.button() == Qt.LeftButton:
        self._update_sample_from_pos(event.pos())
    super().mousePressEvent(event)

def _update_sample_from_pos(self, global_pos):
    # Map widget coordinates to image pixel
    # Clamp to image bounds
    # Update tracker sample point and HSV
    self.tracker.set_sample_point((ix, iy), (H, S, V))
    self.update_from_frame(self.last_bgr, self.last_mask)
```

---

## 8. Summary Table

| Component         | Role                                 | Key Methods / Features                    |
|-------------------|--------------------------------------|-------------------------------------------|
| CameraWindow      | Main UI, video, user events          | update_frame, mousePressEvent, etc.       |
| BallTracker       | Ball detection, HSV picker, smoothing| set_sample_point, process_with_mask, etc. |
| BallMaskWindow    | Mask view, calibration, histograms   | update_from_frame, _update_histograms     |

---

## 9. References

- [OpenCV Documentation](https://docs.opencv.org/)
- [PyQt5 Documentation](https://doc.qt.io/qtforpython/)
- [Freenove Robot Dog Kit](https://www.freenove.com/)

---

## 10. Call Hierarchy: Major Methods and Flow

This section details the call hierarchy and flow between the main classes and methods, showing how user actions and frame updates propagate through the system.

---

### 10.1. Application Startup

- `if __name__ == "__main__":`
    - `app = QApplication(sys.argv)`
    - `w = CameraWindow()`
        - `CameraWindow.__init__()`
            - Initializes BallTracker, BallMaskWindow, HeadTracker, etc.
            - Calls `build_ui()`
    - `w.show()`
    - `sys.exit(app.exec_())`

---

### 10.2. Frame Update Cycle

- `QTimer` or similar triggers:
    - `CameraWindow.update_frame()`
        - Grabs latest video frame.
        - Calls `BallTracker.process_with_mask(frame_bgr)`
            - Converts frame to HSV.
            - Computes mask via `compute_mask()`.
            - Finds ball contour, applies smoothing, updates trace.
        - Draws overlays (ball, picker, info) on color window.
        - Calls `BallMaskWindow.update_from_frame(frame, mask)`
            - Updates mask display.
            - Draws overlays (ball, picker, info) on mask window.
            - Calls `_update_histograms()` to refresh H/S/V histograms.

---

### 10.3. HSV Picker Update (User Click)

#### In Color Window:
- User clicks on video:
    - `CameraWindow.mousePressEvent(event)`
        - Maps click to image coordinates.
        - Gets HSV at (x, y).
        - Calls `BallTracker.set_picker((x, y), (H, S, V))`
            - Updates shared picker state.
        - Triggers redraw in both windows on next frame update.

#### In Mask Window:
- User clicks on mask:
    - `BallMaskWindow.mousePressEvent(event)`
        - Calls `_update_sample_from_pos(event.pos())`
            - Maps widget coordinates to image pixel.
            - Clamps to image bounds.
            - Gets HSV at (x, y).
            - Calls `BallTracker.set_picker((x, y), (H, S, V))`
        - Triggers redraw in both windows on next frame update.

---

### 10.4. Slider Adjustment (Mask Window)

- User moves a slider:
    - `BallMaskWindow._sliders_changed(value)`
        - Updates BallTracker HSV/kernel/circularity/EMA parameters.
        - Calls `BallTracker._clamp_all()` to ensure valid ranges.
        - Triggers mask and histogram update.

---

### 10.5. Ball Tracking Toggle

- User presses Ball button:
    - `CameraWindow.handle_ball_button()`
        - Toggles ball tracking state.
        - Opens or closes `BallMaskWindow`.

---

### 10.6. Head Tracking

- Ball position is updated:
    - `CameraWindow.update_frame()` (after ball detected)
        - If head tracking enabled, calls `send_head_angle(angle_deg)`
            - Sends command to robot dog to move head servo.

---

### 10.7. Networking and Telemetry

- Periodic status check:
    - `DogLogicMixin.periodic_server_check()`
        - Checks IP, ports, and connection status.
        - Updates status flags for UI.

- Telemetry polling:
    - `DogLogicMixin.poll_telemetry()`
        - Receives and parses telemetry data from robot dog.

---

### 10.8. Error Handling

- All frame and mask accesses are guarded by `None` checks.
- All pixel accesses are clamped to valid image bounds.

---

### 10.9. Summary Diagram

```text
[User Click/Timer]
      |
      v
CameraWindow.mousePressEvent() / update_frame()
      |
      +--> BallTracker.set_picker() / process_with_mask()
      |         |
      |         +--> BallMaskWindow.update_from_frame()
      |                   |
      |                   +--> BallMaskWindow._update_histograms()
      |
      +--> CameraWindow.send_head_angle() (if tracking)
      |
      +--> DogLogicMixin.periodic_server_check() (background)
```

---
## 11. Threading: Details of All Threads

This section explains the use of threads in the system, focusing on background operations that run outside the main Qt UI thread. Threading is essential for keeping the UI responsive while handling networking, telemetry, and command processing.

---

### 11.1. Main Qt UI Thread

- **Role:**  
  Handles all user interface operations, video display, user input, and direct interaction with PyQt widgets.
- **Key Methods Running Here:**  
  - `CameraWindow.update_frame()`
  - All event handlers (`mousePressEvent`, `keyPressEvent`, etc.)
  - All drawing and UI updates

---

### 11.2. DogLogicMixin Threads

The `DogLogicMixin` class (mixed into `CameraWindow`) manages several background threads for networking and robot communication.

#### a) Server Check Worker Thread

- **Purpose:**  
  Periodically checks the status of the robot dog server (IP, ports, connection health).
- **Method:**  
  - `DogLogicMixin.server_check_worker()`
- **Typical Flow:**  
  - Runs in a loop (e.g., every few seconds).
  - Calls `periodic_server_check()` to:
    - Ping the robot dog IP.
    - Test TCP ports for video and control.
    - Update connection status flags.
  - Posts results back to the main thread (often via signals/slots or thread-safe variables).

#### b) Telemetry Polling Thread

- **Purpose:**  
  Continuously polls telemetry data from the robot dog (battery, sensors, etc.).
- **Method:**  
  - `DogLogicMixin.poll_telemetry()`
- **Typical Flow:**  
  - Runs in a loop.
  - Receives telemetry packets from the robot dog.
  - Parses and updates telemetry state.
  - Posts updates to the main thread for UI display.

#### c) Command Receiver Worker Thread

- **Purpose:**  
  Listens for and processes incoming command responses or asynchronous messages from the robot dog.
- **Method:**  
  - `DogLogicMixin.command_receiver_worker()`
- **Typical Flow:**  
  - Runs in a loop.
  - Waits for command responses or status messages.
  - Calls `handle_cmd_line(line)` to parse and act on messages.

---

### 11.3. Thread Safety and UI Updates

- **UI Updates:**  
  All UI updates must occur in the main Qt thread. Background threads should use thread-safe mechanisms (such as Qt signals/slots or thread-safe queues) to communicate with the UI.
- **Shared State:**  
  Shared variables (e.g., telemetry data, connection status) should be protected or updated in a thread-safe manner to avoid race conditions.

---

### 11.4. Example Thread Startup (Pseudocode)

```python
# In DogLogicMixin or CameraWindow.__init__():
self.server_check_thread = threading.Thread(target=self.server_check_worker, daemon=True)
self.server_check_thread.start()

self.telemetry_thread = threading.Thread(target=self.poll_telemetry, daemon=True)
self.telemetry_thread.start()

self.command_receiver_thread = threading.Thread(target=self.command_receiver_worker, daemon=True)
self.command_receiver_thread.start()
```

---

### 11.5. Summary Table

| Thread Name              | Method                        | Purpose                                   |
|------------------------- |------------------------------|-------------------------------------------|
| Main Qt UI Thread        | (main event loop)             | UI, video, user input, drawing            |
| Server Check Worker      | `server_check_worker()`       | Periodic network/server health check      |
| Telemetry Polling Thread | `poll_telemetry()`            | Continuous telemetry data polling         |
| Command Receiver Thread  | `command_receiver_worker()`   | Handles incoming robot command responses  |

---

## 12. Video Receiving and Display Pipeline

This section details how video frames are received from the robot dog (or local camera), processed for ball tracking, and displayed in the UI.

---

### 12.1. Video Receiving

- **Source:**  
  - The video stream can come from the robot dog over the network (via the Dog client) or from a local camera (e.g., Mac webcam using OpenCV's `cv2.VideoCapture`).

- **Acquisition:**  
  - In `CameraWindow.update_frame()`:
    - If using the robot dog: frames are received via the Dog client (network socket).
    - If using the local camera: frames are grabbed using `cv2.VideoCapture.read()`.

- **Format:**  
  - Frames are typically in BGR format (as used by OpenCV).

---

### 12.2. Frame Processing and Ball Tracking

#### a) Frame Acquisition

- `CameraWindow.update_frame()` is called periodically (e.g., by a `QTimer`).
- It retrieves the latest frame from the video source.

#### b) Ball Tracking Pipeline

- The frame is passed to `BallTracker.process_with_mask(frame_bgr)`:
    1. **Color Conversion:**  
       - The frame is converted from BGR to HSV color space using `cv2.cvtColor`.
    2. **Mask Computation:**  
       - `BallTracker.compute_mask(frame_bgr)` applies HSV thresholding:
         - Two hue ranges (for colors that wrap around the hue circle, e.g., red).
         - Saturation and value thresholds.
         - Morphological operations (erode/dilate) to clean up the mask.
    3. **Contour Detection:**  
       - Finds contours in the binary mask using `cv2.findContours`.
       - Selects the largest, most circular contour as the ball candidate.
    4. **Ball Center and Radius:**  
       - Computes the center and radius of the detected ball using `cv2.minEnclosingCircle`.
    5. **Smoothing and Jump Rejection:**  
       - Applies exponential moving average (EMA) to smooth the detected position.
       - Rejects sudden jumps to avoid false positives.
    6. **Trace History:**  
       - Maintains a deque of recent ball positions for drawing a fading trace.
    7. **Picker Dot and HSV Info:**  
       - Draws a red dot at the picker location.
       - Displays HSV and (x, y) info at the bottom-left.
    8. **Overlay Drawing:**  
       - Draws the detected ball, center, and trace on the frame.

#### c) Mask Window Update

- The processed mask and frame are sent to `BallMaskWindow.update_from_frame(frame, mask)`:
    - Updates the mask display.
    - Draws overlays (ball, picker, info).
    - Updates histograms for H, S, V channels.

---

### 12.3. Display in UI

- **Color Window (Main):**
  - The processed frame (with overlays) is converted to a `QImage` and displayed in a `QLabel` or similar widget.
- **Mask Window (Calibration):**
  - The mask (with overlays) is similarly converted and displayed.
  - Picker dot and HSV info are synchronized with the main window.

---

### 12.4. Summary Flow

```text
[Video Source] --> [CameraWindow.update_frame()]
      |
      v
[BallTracker.process_with_mask()]
      |
      +--> [HSV conversion, mask, contour, ball detection, overlays]
      |
      +--> [BallMaskWindow.update_from_frame()]
                |
                +--> [Mask display, overlays, histograms]
      |
      v
[Display in Color Window and Mask Window]
```

---

### 12.5. Key Methods

| Method                                 | Purpose                                      |
|-----------------------------------------|----------------------------------------------|
| `CameraWindow.update_frame()`           | Grabs frame, triggers processing and display |
| `BallTracker.process_with_mask()`       | Full ball tracking pipeline                  |
| `BallTracker.compute_mask()`            | HSV thresholding and mask creation           |
| `BallMaskWindow.update_from_frame()`    | Updates mask/calibration window              |

---

**In summary:**  
Video frames are acquired, processed for ball detection and tracking, and displayed with overlays in both the main and calibration windows. The pipeline ensures real-time feedback for both robot control and HSV calibration.

**Note:**  
All long-running or blocking operations (networking, telemetry, command processing) are run in background threads to keep the UI responsive. Only the main thread should update the UI directly.

---
**This call hierarchy should help you trace the flow of data and control through the major components of the system. For more details, refer to the source code or request a specific method walkthrough.**