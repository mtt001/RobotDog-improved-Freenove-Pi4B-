# Handoff Note — mtDogMain.py Refactor Status (2026-01-31)
Last updated: 2026-01-31 23:50:00 CST

## Goal
Reduce `mtDogMain.py` to under 2000 lines via extraction-only refactors while preserving behavior and visuals.

## Rules followed
- No logic changes, no UI layout changes, no detection changes.
- All new files have professional headers with version + history entries.

## Completed extractions
### 1) UI classes → `ui/`
- `ui/common_widgets.py` → `ClickableLabel`
- `ui/ai_hist_windows.py` → `AIVisionHistogramWindow`
- `ui/cv_debug_windows.py` → `CVBallDebugWindow`, `CVBallHistogramWindow`
- `ui/yolo_debug_windows.py` → `YoloVisionDebugWindow`
- `ui/__init__.py`

### 2) YOLO labeling → `yolo_labeling.py`
- `YoloLabelingController` owns labeling state, dataset versioning, save logic, input handlers.
- CameraWindow delegates:
  - `_on_yolo_labeling_toggle`, `_on_labeling_mouse_event`, `_on_labeling_key_event`
  - `_save_manual_label`, `_yolo_save_manual_sample`
  - `_yolo_train_prepare_dataset`, `_yolo_train_next_version_dir`
  - `_yolo_label_help_text`, `_yolo_labeling_class_label`, `_on_yolo_labeling_class_changed`

### 3) CV detection pipeline → `cv_ball_detection.py`
- `CVBallDetectionController.detect(frame)` handles CV Ball timing, counters, debug capture, overlay gating.
- Delegated from `update_frame`: `mask, frame, ball_center, _ = self.cv_ball.detect(frame)`
- `_on_cv_debug_radial_gate_changed` delegates to controller.

### 4) CV histogram + debug → `cv_hist_debug.py`
- `CVHistDebugController` handles histogram + CV debug window updates.
- CameraWindow delegates `_position_cv_hist_window`, `_maybe_update_cv_hist`.
- CV debug window updates triggered from CV controller via `host.cv_hist_debug.update_cv_debug_window(...)`.

### 5) Overlays → `overlay_renderer.py`
- `OverlayRenderer` handles AI/YOLO boxes, probe boxes, labeling overlays, HSV contrast, center marker.
- CameraWindow uses `self.overlay` for all drawing.

### 6) Mask window + HSV picker → `mask_picker.py`
- `MaskPickerController` handles cheer banner, mask window show/hide/update, mouse press/hover for HSV picker.
- CameraWindow delegates:
  - `_set_mask_cheer`, `_apply_mask_cheer_if_needed`, `_on_mask_clear_cheer`
  - `mousePressEvent`, `mouseMoveEvent`
  - `handle_ball_button` show/hide
  - `update_frame` mask window updates

### 7) YOLO runtime pipeline → `yolo_runtime.py` (2026-01-31 20:30:35 CST)
- `YoloRuntimeController` handles YOLO detector setup, compare/probe, training capture, and debug/compare updates.
- CameraWindow delegates:
  - `_update_yolo_debug_view`, `_update_yolo_compare_view`
  - `_on_yolo_conf_changed`, `_on_yolo_imgsz_changed`
  - `_apply_yolo_model_choice`, `_on_yolo_model_changed`
  - `_on_yolo_compare_toggle`, `_ensure_yolo_compare_window`
  - `_yolo_train_*` helpers, `_stop_yolo_training`, `_on_yolo_training_toggle`
  - `update_frame` YOLO run paths (ball mode + test mode)

### 8) UI event handlers → `ui_event_handlers.py` (2026-01-31 20:41:00 CST)
- `UIEventHandlersController` handles UI button events, status updates, and cleanup/quit logic.
- CameraWindow delegates:
  - `update_status_ui`, `try_reconnect`
  - `handle_ball_button`, `handle_cv_ball_button`, `handle_yolo_vision_button`, `handle_ai_vision_button`, `handle_quit`
  - `_clear_object_detection_state`, `closeEvent`

### 9) Frame update loop → `frame_update_controller.py` (2026-01-31 21:22:03 CST)
- `FrameUpdateController` handles per-frame capture, overlays, and test-mode updates.
- CameraWindow delegates:
  - `update_frame` (thin wrapper)

### 10) AI Vision helpers → `ai_vision_controller.py` (2026-01-31 21:40:00 CST)
- `AIVisionController` owns GPT Vision state, filter helpers, HSV auto-calibration, and test histogram updates.
- CameraWindow delegates:
  - AI state initialization via controller
  - AI helper methods used by frame update pipeline

### 11) Client camera helpers → `client_camera_controller.py` (2026-01-31 22:05:00 CST)
- `ClientCameraController` owns Mac camera selection, retry logic, and combo refresh.
- CameraWindow delegates:
  - `_log_client_cam`, `_retry_client_camera_if_needed`, `_refresh_client_camera_list`, `_on_mac_camera_changed`
  - Mac camera initial open during startup

### 12) Telemetry loop/state → `telemetry_controller.py` (2026-01-31 22:25:00 CST)
- `TelemetryController` owns telemetry fields and the 1 Hz polling timer.
- CameraWindow delegates:
  - Telemetry state initialization + timer setup

### 13) Dog command helpers → `dog_command_controller.py` (2026-01-31 22:25:00 CST)
- `DogCommandController` owns command logging, human-readable labels, and relax/stop/head helpers.
- CameraWindow delegates:
  - `_cmd_key_to_human`, `_log_cmd`, `_send_relax_only`, `_send_stop_pwm_only`, `send_head_angle`

### 14) Ball tracking helpers → `ball_tracking_controller.py` (2026-01-31 22:25:00 CST)
- `BallTrackingController` owns tracking transitions, full/body tracking, lost-ball search, and close-enough/bark logic.
- CameraWindow delegates:
  - `_handle_tracking_mode_transition`, `_update_full_body_tracking`, `_update_lost_ball_search`
  - `_trigger_close_enough_sequence`, `_start_barking`, `_stop_barking`, `_bark_should_run`

### 15) Status UI → `status_ui_controller.py` (2026-01-31 22:55:00 CST)
- `StatusUIController` owns bottom bar HTML string and Dog Video button label/color.
- UIEventHandlers delegates:
  - `update_status_ui`

### 16) Server check + reconnect → `server_reconnect_controller.py` (2026-01-31 23:15:00 CST)
- `ServerReconnectController` owns background server check thread and reconnect flow.
- UIEventHandlers delegates:
  - `try_reconnect`
  - server check thread stop on close
- CameraWindow delegates:
  - server check thread start on init

### 17) Motion grid UI → `motion_grid_builder.py` (2026-01-31 23:15:00 CST)
- `MotionGridBuilder` builds movement label + round button grid.
- CameraWindow delegates:
  - movement grid layout in `build_ui`

### 18) Status overlay/HUD → `status_overlay_controller.py` (2026-01-31 23:20:00 CST)
- `StatusOverlayController` owns FPS/telemetry + AI/CV/YOLO hint overlay assembly.
- FrameUpdateController delegates:
  - overlay draw for status/HUD text
### 19) Control panel sections → `ui/control_panel_sections.py` (2026-01-31 23:45:00 CST)
- `ControlPanelSectionsBuilder` builds Actions/Test/System control groups.
- CameraWindow delegates:
  - actions/test/system UI section creation in `build_ui`
### 20) Frame update grouping → `frame_update_controller.py` (2026-01-31 23:45:00 CST)
- `FrameUpdateController` groups update steps into capture/detection/overlays helpers.

## Current wiring in CameraWindow.__init__
- `self.yolo_labeling = YoloLabelingController(self, label_window_factory=YoloLabelWindow)`
- `self.ai_vision = AIVisionController(self, hist_window_factory=AIVisionHistogramWindow)`
- `self.client_camera = ClientCameraController(self)`
- `self.telemetry = TelemetryController(self, low_voltage_threshold=LOW_VOLTAGE_THRESHOLD)`
- `self.dog_commands = DogCommandController(self, write_log_func=_write_log)`
- `self.ball_tracking = BallTrackingController(self)`
- `self.status_ui = StatusUIController(self)`
- `self.server_reconnect = ServerReconnectController(self)`
- `self.cv_ball = CVBallDetectionController(self)`
- `self.cv_hist_debug = CVHistDebugController(self)`
- `self.overlay = OverlayRenderer()`
- `self.mask_picker = MaskPickerController(self)`

## mtDogMain.py header revision entries
- v3.17: mask/picker controller extraction
- v3.16: CV hist/debug controller extraction
- v3.15: overlay renderer extraction
- v3.14: CV detection controller extraction
- v3.13: YOLO labeling controller extraction
- v3.18: YOLO runtime controller extraction
- v3.19: UI event handler controller extraction
- v3.20: Frame update controller extraction

## Current file size
- `mtDogMain.py`: ~1492 lines
- `yolo_runtime.py`: ~1225 lines
- `ui_event_handlers.py`: ~856 lines
- `frame_update_controller.py`: ~1098 lines

## Next suggested extractions
- (none; actions/test/system + frame update grouping completed on 2026-01-31)

## Notes
- No tests run.
