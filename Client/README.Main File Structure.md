===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File    : README.Main File Structure.md
 Author  : MT & GitHub Copilot

 Description:
     Architecture and runtime flow overview for mtDogMain.py and refactored
     controller modules (UI, vision, tracking, telemetry, networking).

 v1.00  (2026-02-01)          : Refactor-aware documentation update
     • Document refactored controllers, boundaries, and execution flow.
===============================================================================

## File Structure of mtDogMain.py and related code (.py)

Primary entry point

- Main GUI runtime: [mtDogMain.py](mtDogMain.py)
    - `CameraWindow` (main application window, `QWidget` + `DogLogicMixin`)
    - `YoloLabelWindow`, `YoloCompareWindow`, `YoloTrainHistogramWindow` (auxiliary UI windows)

Core runtime boundaries (file-linked, class/module boundaries)

- Main window + composition root: [mtDogMain.py](mtDogMain.py)
    - owns UI widgets, timers, and controller wiring
    - owns the main per-frame loop via `FrameUpdateController`
- Network/motion logic mixin: [mtDogLogicMixin.py](mtDogLogicMixin.py)
    - `DogLogicMixin` (dog networking, telemetry parsing, command send helpers)
- Socket client + video stream: [Client.py](Client.py)
    - `Client` (control + video sockets, frame buffer + locks)
- Per-frame update pipeline: [frame_update_controller.py](frame_update_controller.py)
    - `FrameUpdateController` (frame capture, detection dispatch, overlay render, Qt paint)
- Ball tracking logic & close-enough sequence: [ball_tracking_controller.py](ball_tracking_controller.py)
    - `BallTrackingController` (tracking policy + bark/cheer sequence)
- Telemetry timer/state: [telemetry_controller.py](telemetry_controller.py)
    - `TelemetryController` (1 Hz poll timer + state)
- Command labeling/logging helpers: [dog_command_controller.py](dog_command_controller.py)
    - `DogCommandController` (command history + servo helpers)
- CV ball detection (test-only): [cv_ball_detection.py](cv_ball_detection.py)
    - `CVBallDetectionController` (HSV mask + contour pipeline)
- CV hist/debug windows: [cv_hist_debug.py](cv_hist_debug.py)
    - `CVHistDebugController` (CV debug + histogram windows)
- Mask/HSV picker window: [mask_picker.py](mask_picker.py)
    - `MaskPickerController` (mask window + picker interaction)
- AI Vision (GPT) runtime: [ai_vision_controller.py](ai_vision_controller.py)
    - `AIVisionController` (API polling, filtering, HSV auto-calibration)
- YOLO runtime + training: [yolo_runtime.py](yolo_runtime.py)
    - `YoloRuntimeController` (runtime inference + compare/train + debug views)
- YOLO manual labeling: [yolo_labeling.py](yolo_labeling.py)
    - `YoloLabelingController` (manual capture + labeling state)
- UI event handlers: [ui_event_handlers.py](ui_event_handlers.py)
    - `UIEventHandlersController` (button handlers, mode toggles, quit flow)
- Status bar + overlay assembly: [status_ui_controller.py](status_ui_controller.py), [status_overlay_controller.py](status_overlay_controller.py)
    - `StatusUIController`, `StatusOverlayController`
- Server reconnect + health checks: [server_reconnect_controller.py](server_reconnect_controller.py)
    - `ServerReconnectController` (background ping/reconnect loop)
- Client camera selection: [client_camera_controller.py](client_camera_controller.py)
    - `ClientCameraController` (Mac camera discovery + retry)
- UI builders: [motion_grid_builder.py](motion_grid_builder.py), [ui/control_panel_sections.py](ui/control_panel_sections.py)
    - `MotionGridBuilder`, `ControlPanelSectionsBuilder`
- Overlay drawing helpers: [overlay_renderer.py](overlay_renderer.py)
    - `OverlayRenderer` (all frame overlays)

Detector backends (called by controllers)

- GPT Vision detector: [mtBallDetectAI.py](mtBallDetectAI.py)
    - `AIVisionBallDetector`
- YOLO detector wrapper: [mtBallDetectYOLO.py](mtBallDetectYOLO.py)
    - `YOLOBallDetector`
- CV mask/hist logic: [mtBallDetectCV.py](mtBallDetectCV.py)
    - CV-only helpers used by CV pipeline

UI widgets (Qt windows and shared widgets)

- Common widgets: [ui/common_widgets.py](ui/common_widgets.py)
- AI hist windows: [ui/ai_hist_windows.py](ui/ai_hist_windows.py)
- CV debug windows: [ui/cv_debug_windows.py](ui/cv_debug_windows.py)
- YOLO debug windows: [ui/yolo_debug_windows.py](ui/yolo_debug_windows.py)

Execution order (startup → steady state)

1) Application starts at [mtDogMain.py](mtDogMain.py)
     - Qt `QApplication` created, then `CameraWindow` instantiated.
2) `CameraWindow.__init__` wires core components
     - Initializes `BallTracker`/`HeadTracker` from [mtDogBallTrack.py](mtDogBallTrack.py).
     - Creates controllers: `FrameUpdateController`, `TelemetryController`, `BallTrackingController`, `YoloRuntimeController`, `AIVisionController`, `CVBallDetectionController`, and UI/controller helpers.
     - Builds UI via `MotionGridBuilder` + `ControlPanelSectionsBuilder`.
3) Camera + networking startup
     - Client camera opened by `ClientCameraController`.
     - Dog server check thread started by `ServerReconnectController`.
4) Timers begin
     - Frame timer ticks into `FrameUpdateController.update_frame` (~33 FPS).
     - Telemetry timer ticks into `poll_telemetry` (1 Hz).
5) Steady state loop
     - Frame capture → detection dispatch (Ball/CV/YOLO/AI) → overlay render → Qt paint.
     - User input handlers toggle modes and send commands via `DogLogicMixin` + `DogCommandController`.

High-level flow diagram (file-linked, class/module boundaries)

[mtDogMain.py](mtDogMain.py) `CameraWindow`
    → [client_camera_controller.py](client_camera_controller.py) `ClientCameraController`
    → [frame_update_controller.py](frame_update_controller.py) `FrameUpdateController`
            → [cv_ball_detection.py](cv_ball_detection.py) `CVBallDetectionController`
            → [yolo_runtime.py](yolo_runtime.py) `YoloRuntimeController`
            → [ai_vision_controller.py](ai_vision_controller.py) `AIVisionController`
            → [ball_tracking_controller.py](ball_tracking_controller.py) `BallTrackingController`
            → [overlay_renderer.py](overlay_renderer.py) `OverlayRenderer`
            → [status_overlay_controller.py](status_overlay_controller.py) `StatusOverlayController`
    → [ui_event_handlers.py](ui_event_handlers.py) `UIEventHandlersController`
    → [telemetry_controller.py](telemetry_controller.py) `TelemetryController`
    → [server_reconnect_controller.py](server_reconnect_controller.py) `ServerReconnectController`
    → [dog_command_controller.py](dog_command_controller.py) `DogCommandController`
    → [mtDogLogicMixin.py](mtDogLogicMixin.py) `DogLogicMixin`
            → [Client.py](Client.py) `Client`

If you want deeper per-class notes, tell me which module to expand.