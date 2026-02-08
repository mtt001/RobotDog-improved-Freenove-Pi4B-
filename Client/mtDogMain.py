#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Silence OpenCV startup warnings on macOS (AVFoundation)
import os
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : mtDogMain.py
 Author : MT & GitHub Copilot
 Usage  :
     1) Configure video backend in `config/mtDogConfig.py`:
        - `VIDEO_BACKEND = "sfu_rtsp"` (recommended low latency)
        - `VIDEO_BACKEND = "legacy_socket"` (original Pi 8001 JPEG stream)
     2) Run: `python3 mtDogMain.py`

 v3.34  (2026-02-08 10:45)    : Restore WASD+QE motion keys
     • Reverted experimental motion keys to standard W/S (fwd/back), A/D (turns), Q/E (strafe).
     • Fixed command blocking when video backend is not "dog" (allow blind control).
 v3.33  (2026-02-07 19:40)    : Add SFU low-latency video backend (RTSP pull)
     • New selectable backend: legacy Pi socket or SFU RTSP (`config/mtDogConfig.py`).
     • Dog mode can use command channel on 5001 with video from SFU (no direct Pi camera pull).
     • Startup/reconnect probes selected backend and displays SFU path in status bar.
 v3.32  (2026-02-02 20:31)    : Add bottom IMU message box beside vision status pane.
 v3.31  (2026-02-02)          : Increase startup window height
     • Start with a taller window so Motion controls never overlap on launch.
 v3.30  (2026-02-02)          : Dog Controls panel layout + Space STOP button
     • Fix right panel motion-button clipping via minimum-width layout constraint.
     • Add a pill-shaped Space (CMD_MOVE_STOP) emergency stop button under Motion.
     • UI tip: Press Space / Space STOP anytime for immediate stop. # Height scale factor (tune as needed).
            STARTUP_H_SCALE = 1.2
            min_w, min_h = 1200, 900     w, h = 1500, 1000
 v3.27  (2026-02-01)          : Vision compare + message pane UX
     • Make bottom vision message pane taller.
     • Add Total Detect Count line to YOLO Compare window.
 v3.29  (2026-02-02)          : Vision pane rich text
     • Allow colored, multi-line status text in the bottom vision pane.
 v3.28  (2026-02-01)          : Simplify test UI + camera labels
     • Remove CV Ball + GPT Vision buttons and handlers.
     • Widen camera selector to show device names.

 v3.17  (2026-01-31 19:35)    : Extract mask/picker controller
     • Move mask window + HSV picker handling into mask_picker.py.
     • Delegate mouse/cheer/mask window logic from CameraWindow.
 v3.18  (2026-01-31 20:30)    : Extract YOLO runtime controller
     • Move YOLO runtime pipeline into yolo_runtime.py.
     • Delegate YOLO runtime helpers from CameraWindow.
 v3.19  (2026-01-31 20:50)    : Extract UI event handler controller
     • Move UI button handlers + status updates into ui_event_handlers.py.
 v3.20  (2026-01-31 21:00)    : Extract frame update controller
     • Move update_frame into frame_update_controller.py.
 v3.21  (2026-01-31 21:40)    : Extract AI Vision controller
     • Move GPT Vision helpers + histogram update into ai_vision_controller.py.
 v3.22  (2026-01-31 22:25)    : Extract tracking + telemetry + command helpers
     • Move ball tracking helpers into ball_tracking_controller.py.
     • Move telemetry timer/state into telemetry_controller.py.
     • Move command helpers into dog_command_controller.py.
 v3.23  (2026-01-31 22:55)    : Extract status UI controller
     • Move bottom bar status string + button style into status_ui_controller.py.
 v3.24  (2026-01-31 23:20)    : Extract server/reconnect + UI + overlay helpers
     • Move server check/reconnect flow into server_reconnect_controller.py.
     • Move motion grid UI builder into motion_grid_builder.py.
     • Move status overlay assembly into status_overlay_controller.py.
 v3.25  (2026-01-31 23:45)    : Extract control panel section builder
     • Move actions/test/system UI sections into control_panel_sections.py.
 v3.26  (2026-02-01)          : Add bottom vision message pane
     • Add a non-overlay message pane widget under the video for YOLO status/perf.
 v3.16  (2026-01-31 18:55)    : Extract CV hist/debug controller
     • Move CV histogram + debug window updates into cv_hist_debug.py.
     • Delegate CV hist/debug calls from CameraWindow and CV controller.
 v3.15  (2026-01-31 18:20)    : Extract overlay renderer
     • Move overlay/drawing helpers into overlay_renderer.py.
     • Delegate overlay drawing from CameraWindow.
 v3.14  (2026-01-31 17:40)    : Extract CV Ball detection controller
     • Move CV-only detection pipeline into cv_ball_detection.py.
     • Delegate CV detection calls from CameraWindow.
 v3.13  (2026-01-31 17:05)    : Extract YOLO labeling controller
     • Move YOLO manual labeling state/handlers into yolo_labeling.py.
     • Delegate labeling-related methods from CameraWindow.
 v3.12  (2026-01-31 14:30)    : Labeling window + compare lockout
     • Manual labeling now uses a dedicated labeling window with help text.
     • Labeling disables Compare mode and shows status in debug + CLI.
 v3.11  (2026-01-31 13:55)    : Dataset versioning metadata + debug path
     • New dataset README includes Updated date + Version History.
     • YOLO debug window shows dataset path/label when available.
 v3.10  (2026-01-31)          : Manual labeling class selection
     • Add class selector for manual labeling and propagate to dataset.yaml template.
 v3.09  (2026-01-31)          : Dataset versioning + README/dataset templates
     • Always create a new YOLO dataset version folder (preserve existing data).
     • Add manual-label notes in dataset README and dataset.yaml templates.
 v3.08  (2026-01-30)          : Silence Startup Logs
     • Suppress repetitive Client Camera success messages and OpenCV warnings.
 v3.07  (2026-01-30)          : AVFoundation optional import hint
     • Silence editor import warning for macOS-only AVFoundation dependency.
 v3.07  (2026-01-30)          : Compare button debug
     • Add local Compare click/toggle logging + status line in YOLO debug window.
 v3.06  (2026-01-30)          : Ensure streaming client camera
     • Validate client camera by reading a frame; fallback to next index if needed.
 v3.05  (2026-01-30)          : Camera list index labeling
     • List client cameras by index and show device names in tooltip.
 v3.04  (2026-01-30)          : Quit closes all windows
     • Ensure Quit button closes auxiliary windows and exits the app.
 v3.03  (2026-01-30)          : Mac camera selection UI
     • List available client cameras and allow selection when in Mac mode.
 v3.02  (2026-01-30)          : Client camera fallback + retry
     • Prefer Mac camera index order with retry when Dog server is offline.
     • Avoid stuck "NO CLIENT SOURCE" and reduce accidental iPhone camera usage.
 v3.01  (2026-01-29)          : Fix YOLO model switch/compare UI
     • Ensure model selection switches active detector and overlay label.
     • Position compare window near YOLO debug window.
 v3.00  (2026-01-29)          : YOLO model select + compare view
     • Add model selector (best.pt vs yolov8n.pt) in YOLO debug window.
     • Add Compare toggle with side-by-side YOLO outputs.
     • Overlay active YOLO model on main camera view.
 v2.99  (2026-01-29)          : YOLO Training no conf range gate
     • Remove confidence range restriction during Ball Training capture.
 v2.98  (2026-01-29)          : YOLO Ball Training capture
     • Add Ball Trainning toggle, dataset capture, and confidence distribution window.
     • Live overlay prompts and 30/40/30 difficulty mix status.
 v2.97  (2026-01-28)          : Allow YOLO in Ball mode
     • Keep Yolo Vision enabled when Ball mode is toggled on.
     • Preserve head tracking if Ball mode is active.
 v2.96  (2026-01-28)          : Ball mode prefers YOLO detection
     • In Ball tracking mode, use YOLO detections when Yolo Vision is enabled.
 v2.95  (2026-01-28)          : YOLO overlay in color window
     • Always draw YOLO circle overlay during Yolo Vision detections.
     • Suppress "Close Enough" banner outside Ball mode.
 v2.94  (2026-01-28)          : YOLO circle line thickness
     • Use 1px circle line in Yolo Vision when overlay is drawn.
 v2.93  (2026-01-28)          : YOLO circle overlay in ball mode
     • Draw YOLO-based tracking circle when Ball tracking mode is enabled.
 v2.92  (2026-01-28)          : YOLO debug draws probe boxes
     • Draw any-class probe boxes on the YOLO debug view when no ball is detected.
 v2.91  (2026-01-28)          : YOLO no-detect debug hint
     • Show a brief hint line when no detections are returned.
 v2.90  (2026-01-28)          : YOLO debug labels + center mark styling
     • Show hi/lo conf labels with center HSV and side-by-side panes.
     • Add boundary box in detected-object preview; all shapes 1px.
     • Use translucent high-contrast center markers.
 v2.89  (2026-01-28)          : Yolo debug layout + object hist fallback
     • Hide CV debug/hist windows during Yolo Vision test mode.
     • Enable detected-object histogram fallback using inner-circle ROI.
     • Fix YOLO debug pane sizing and preserve image aspect ratios.
 v2.88  (2026-01-28)          : Yolo debug UI panes + controls
     • Move YOLO conf/imgsz controls into debug window; add HSV hist panes.
 v2.87  (2026-01-28)          : Live YOLO conf/imgsz UI controls
     • Added live controls to adjust YOLO confidence and input size at runtime.
 v2.86  (2026-01-28)          : Fix YOLO debug model_path indentation
     • Align model_path assignment to prevent unexpected indentation error.
 v2.85  (2026-01-28)          : YOLO debug probe (any-class) + extra stats
     • Probe any-class detections when no sports-ball hit and show top class/conf.
 v2.84  (2026-01-28)          : Yolo Vision shows bbox only
     • Suppress tracker circle overlay during Yolo Vision test mode.
 v2.83  (2026-01-28)          : YOLO debug window expanded stats
     • Show YOLO latency, thresholds, last-hit age, and top-box details.
 v2.82  (2026-01-24)          : Overlay legend for detected-object preview
     • Show a short legend describing contour/circle overlays.
 v2.81  (2026-01-24)          : Contour-only hist + overlay marks
     • Show contour/center overlays in detected-object preview and clear when no contour.
 v2.80  (2026-01-24)          : Fix hist window sizing + contour ROI crop
     • Keep detected-object histogram window height fixed to CV hist panel height.
     • Crop contour preview from CV refine ROI (yellow box) without masking.
 v2.79  (2026-01-24)          : Fix object hist ROI + CV hist debug counters
     • Object histogram uses contour ROI medians and zoomed contour crop.
     • CV 4-panel histogram shows update counters for picker/whole-frame.
 v2.81  (2026-01-28)          : Clarify Ball Lock source (CV vs YOLO)
 v2.80  (2026-01-24)          : Remove ring band from Detected Object overlay
 v2.79  (2026-01-24)          : Show ring band on Detected Object overlay
 v2.78  (2026-01-24)          : Arrange CV histogram window placement
     • Position the 4-panel CV histogram window below the CV debug window (or to the right).
 v2.77  (2026-01-24)          : Force CV histogram window show on startup
     • Ensure the 4-panel CV histogram window is created and shown after UI build.
 v2.76  (2026-01-24)          : Fix detected-object hist + keep CV panels alive
     • Detected-object histogram now uses rank-1 contour mask (even if rejected).
     • CV 4-panel histogram uses current frame fallback when last_display_frame is missing.
 v2.75  (2026-01-24)          : Rolling picker/frame histograms (64 frames)
     • Picker/whole-frame histograms now roll over the last 64 frames.
     • Panel header reflects rolling window when picker is pinned/unpinned.
 v2.73  (2026-01-24)          : Always-on CV histogram panels
     • Picker/frame histogram shown even when CV Ball is off.
     • Added top-3 ranked contour histograms in CV Ball mode.
 v2.72  (2026-01-24)          : CV histogram always visible
     • Histogram window stays open in CV Ball mode even without detection.
     • Fallback to frame center when sample point is unavailable.
 v2.71  (2026-01-23)          : CV histogram uses refined top contour
     • Prefer refined-candidate contour mask for histogram sampling.
     • Keep raw combined mask for CV debug window display.
 v2.70  (2026-01-23)          : CV debug rich-text candidate list
     • Allow colored accept/reject lines in CV Ball debug info panel.
 v2.69  (2026-01-23)          : Histogram uses top-1 contour + UI panes
     • Histogram samples pixels inside the largest blob contour when available.
     • Add contour side pane + bottom method message; remove inner-ROI thumbnail.
 v2.68  (2026-01-23)          : CV overlay TTL scales with interval
     • Prevent CV Ball overlay/status from toggling off between slow detector ticks.
 v2.67  (2026-01-22)          : CV debug window size + info space
     • Enlarged CV debug window and info panel to avoid debug text truncation.
 v2.66  (2026-01-22)          : Full-mode head neutral once
     • Send CMD_HEAD neutral once on entering FULL tracking (no 1s spam).
 v2.65  (2026-01-22)          : Close-enough stop guard + overlay cleanup
     • Suppress extra CMD_MOVE_STOP after FULL completion (Relax/Off).
     • Show Close Enough status while completion is latched.
     • Remove command-feed overlay from Color window.
 v2.64  (2026-01-22)          : Command feed overlay + logging + close-enough threshold (w/4)
     • Show recent server commands and motion status on the Color window.
     • Log terminal messages + commands to mtDogMain.log.
     • Adjust FULL-mode close-enough diameter to w/4 (clear logic unchanged).
 v2.63  (2026-01-21)          : CV RadialGate toggle in CV debug window
     • Add RadialGate (CV) checkbox to CV Ball debug window for quick experiments.
 v2.62  (2026-01-21)          : CV Ball status line in color window
     • Show Detected!/No Ball! in green/red beneath CV Ball hint.
 v2.61  (2026-01-20)          : CV debug layout + HSV gate display
     • CV Ball debug window now keeps masks on top with info text pinned at bottom.
     • HSV gate mask is shown in the CV debug mosaic.
 v2.60  (2026-01-20)          : CV debug UX improvements
     • Larger CV debug window (1.5x) for easier inspection.
     • Overlay includes CV detection success count.
 v2.59  (2026-01-20)          : CV Ball faster UI perception
     • Faster CV update rate + short overlay TTL so occlusion clears quickly.

 v2.58  (2026-01-20)          : CV Ball stale overlay fix
     • Do not draw last-known CV circle when detection is currently missing.

 v2.57  (2026-01-20)          : Histogram window inner-ROI markers
     • Percentile triangle markers now reflect inner-circle ROI only (p5/p95).
     • Threshold markers use vertical lines to reduce visual confusion.

 v2.56  (2026-01-17)          : AI Vision histogram window + HSV filter toggle
     • Disabled AI HSV filter by default for multi-color ball support.
     • Added AI histogram window with H/S/V histograms from half-radius ROI.
     • Histogram window persists even after AI Vision is turned off.

 v2.55  (2026-01-14)          : Body tracking proportional speed (Kp)
     • Added Body-Kp proportional speed control (replaces bang-bang feel by scaling turn/forward speed).
     • Body-Kp is optional (0.0 keeps fixed-speed behavior) and persisted to mtBall_Calib.json.

 v2.54  (2026-01-14)          : Body tracking derivative damping (Kd)
     • Added derivative damping (Body-Kd) to reduce overshoot when deadzone is narrow.
     • Expose Body-Kd slider in Mask window and persist to mtBall_Calib.json.

 v2.53  (2026-01-14)          : Body tracking motion policy update
     • Body tracking now prioritizes left/right turning to X-center the ball.
     • Forward/backward motion is blocked until the ball is X-centered within tolerance.
     • Switching from Y→X correction triggers an immediate turn command (no extra wait).
     • Body tracking defaults to forward-only (no backward) to reduce surprises from jitter.
     • Expose "Allow backward" in Mask window and persist to mtBall_Calib.json.

 v2.50  (2025-12-05)          : Stable release
    • Fix head servo control commands,  refer Main.py for correct command format.
    . Shared HSV picker (click-and-stay) for color and mask windows.
    • Picker HUD always updates correctly, even when ball is locked.
    • No HSV info shown near picker location, only at bottom-left.
    • Mask window HUD always matches color window HSV info.
    • Robust error handling for out-of-bounds picker coordinates.
    • Head tracking integration.
    • Ball tracking, mask calibration, and rolling HSV histograms.
    • UI and telemetry improvements.
===============================================================================

 v2.42  (2025-12-04)          : click and stay HSV sample point, Hover HSV\n(x,y) with mouse
    • Left-click in either video or mask window to set sample point.
    • Sample point remains until another left-click.
    • Hover mouse in either window to show HSV\n(x,y) at bottom-left.  
    . Click = move picker + update histograms
    . Move mouse = only hover HUD, no change to picker / histograms 
    . Bugs to be fixed: while ball locked, the HSV hud does not update correctly. and ball center HSV shown in Color window is not correct.
 v2.41  (2025-12-02)          : Head tracking integration fix
 v2.40  (2025-12-02)
   • Uses:
       - mtDogConfig.py       : shared config ...
       - mtDogLogicMixin.py   : Dog logic (network, telemetry, commands)
       - mtDogBallTrack.py    : BallTracker + BallMaskWindow
   • Ball button:
       - Toggles ball tracking on main video.
       - Opens/closes Mask window with HSV sliders.
       - Loads / saves mtBall_Calib.json (autosave on slider change).
   • FPS overlay:
       - RX:xx.xfps  → receive rate from Dog
       - UI:yy.yfps  → Qt drawing rate
   • HSV picker:
       - Shared sample point (left-click in either window).
       - Dot + HSV(x,y) at bottom-left in both windows.
   • Mask window:
       - Title includes resolution (e.g. 400x300).
       - Size adjusted to resolution, visually similar to color window.

    Get OpenAI API key named "RobotDogFreenove"from: https://platform.openai.com/account/api-keys
    Set it in your shell environment variable OPENAI_API_KEY.
        export OPENAI_API_KEY="YOUR_API_KEY_HERE"
        see ChatGPT API Key.txt for the key setup instructions.
        
===============================================================================
"""

import sys
import platform
import builtins
import os
import json
import re
from datetime import datetime
from collections import deque


def _fatal_env_error(message: str) -> "None":
    print("\n[FATAL] " + message)
    print(f"        sys.executable = {sys.executable}")
    print(f"        python = {sys.version.split()[0]} ({platform.machine()})")
    print("\n        Use the project venv/task instead:")
    print("          ~/.venvs/freenove-client/bin/python mtDogMain.py")
    print("\n        (VS Code task: 'Run Dog Client')\n")
    raise SystemExit(2)


if sys.version_info < (3, 9):
    _fatal_env_error("Python 3.9+ is required.")

try:
    import numpy as _np  # noqa: F401
    import cv2  # noqa: F401
except Exception as e:
    _fatal_env_error(
        "OpenCV/NumPy failed to import. This is usually caused by running the wrong interpreter "
        "or an architecture-mismatched NumPy wheel (x86_64 vs arm64) in user site-packages.\n"
        f"        Import error: {e}"
    )

from mtDogBallTrack import (
    BallTracker,
    BallMaskWindow,
    HeadTracker,
    HeadConfig,
    TRACKING_MODE_FULL,
    TRACKING_MODE_HEAD,
    TRACKING_MODE_BODY,
)  # <--- CHANGED: Import from merged file
import threading
import time

import numpy as np
import cv2

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QSizePolicy,
    QSlider, QComboBox, QLineEdit, QCheckBox, QDoubleSpinBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, QEvent, QRect, QPoint
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont

from ui.ai_hist_windows import AIVisionHistogramWindow
from ui.common_widgets import ClickableLabel
from ui.control_panel_sections import ControlPanelSectionsBuilder
from ui.cv_debug_windows import CVBallDebugWindow, CVBallHistogramWindow
from ui.yolo_debug_windows import YoloVisionDebugWindow
from controllers.ball_tracking_controller import BallTrackingController
from controllers.client_camera_controller import ClientCameraController
from controllers.dog_command_controller import DogCommandController, COMMAND as CMD
from controllers.frame_update_controller import FrameUpdateController
from controllers.server_reconnect_controller import ServerReconnectController
from controllers.telemetry_controller import TelemetryController
from controllers.video_source_controller import VideoSourceController
from ui.status_ui_controller import StatusUIController
from ui.ui_event_handlers import UIEventHandlersController
from vision.ai_vision_controller import AIVisionController
from vision.cv_hist_debug import CVHistDebugController
from vision.mask_picker import MaskPickerController
from vision.yolo_runtime import YoloRuntimeController
from vision.legacy.cv_ball_detection import CVBallDetectionController
from vision.utils.motion_grid_builder import MotionGridBuilder
from vision.utils.overlay_renderer import OverlayRenderer
from tools.yolo.yolo_labeling import YoloLabelingController

from config.mtDogConfig import (
    DOG_DEFAULT_IP,
    DOG_VIDEO_PORT,
    DOG_CONTROL_PORT,
    LOW_VOLTAGE_THRESHOLD,
    YOLO_COCO_CONF_DEFAULT,
    YOLO_MT_BALL_CONF_DEFAULT,
    YOLO_DUAL_CAP_FPS_DEFAULT,
    VIDEO_BACKEND,
    SFU_RTSP_URL,
    SFU_RTSP_TRANSPORT,
    SFU_STREAM_PATH,
    VIDEO_TARGET_WIDTH,
    VIDEO_TARGET_HEIGHT,
    VIDEO_TARGET_FPS,
)
from mtDogLogicMixin import DogLogicMixin

# ---------------------------------------------------------------------------
# Logging (terminal messages + commands)
# ---------------------------------------------------------------------------
_LOG_PATH = os.path.join(os.path.dirname(__file__), "mtDogMain.log")
_LOG_LOCK = threading.Lock()
_ORIG_PRINT = builtins.print
_PRINT_HOOKED = False


def _write_log(message: str) -> None:
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{ts}] {message}"
        with _LOG_LOCK:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        return


def _install_print_logger() -> None:
    global _PRINT_HOOKED
    if _PRINT_HOOKED:
        return

    try:
        with _LOG_LOCK:
            with open(_LOG_PATH, "w", encoding="utf-8") as f:
                f.write("")
    except Exception:
        pass

    def _print_with_log(*args, **kwargs):
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        try:
            msg = sep.join(str(a) for a in args)
        except Exception:
            msg = "<print:unformattable>"
        if msg:
            _write_log(msg)
        return _ORIG_PRINT(*args, **kwargs)

    builtins.print = _print_with_log  # type: ignore
    _PRINT_HOOKED = True


_install_print_logger()
# ---------------------------------------------------------------------------
# Head servo configuration (Dog Pi side)
# ---------------------------------------------------------------------------
HEAD_SERVO_ID = 8  # TODO: set this to your actual head-servo ID on the Dog



class YoloLabelWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO Manual Labeling")
        self.resize(760, 560)
        self.on_key_event = None  # Callback for manual labeling keys

        self.info_label = QLabel("Manual labeling ready.")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#e6e6e6; font-size:12px;")

        self.help_label = QLabel("")
        self.help_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.help_label.setStyleSheet("color:#9fb0c3; font-size:11px;")
        self.help_label.setWordWrap(True)

        self.view = ClickableLabel("")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setScaledContents(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.info_label)
        layout.addWidget(self.help_label)
        layout.addWidget(self.view, stretch=1)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, event):
        if self.on_key_event:
            self.on_key_event(event)
        super().keyPressEvent(event)

    def _set_pixmap(self, label: QLabel, img_bgr):
        if label is None:
            return
        if img_bgr is None:
            label.clear()
            return
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            try:
                target = label.size()
                if target.width() > 0 and target.height() > 0:
                    pix = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pass
            label.setPixmap(pix)
        except Exception:
            label.clear()

    def update_view(self, img_bgr, info_text: str, help_text: str):
        try:
            self.info_label.setText(str(info_text or ""))
            self.help_label.setText(str(help_text or ""))
        except Exception:
            pass
        self._set_pixmap(self.view, img_bgr)


class YoloCompareWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO Compare")
        self.resize(820, 420)

        self.left_title = QLabel("BEST (best.pt)")
        self.left_title.setAlignment(Qt.AlignCenter)
        self.left_title.setStyleSheet("color:#b7c0ce; font-size:11px;")

        self.right_title = QLabel("ORIGINAL (yolov8n.pt)")
        self.right_title.setAlignment(Qt.AlignCenter)
        self.right_title.setStyleSheet("color:#b7c0ce; font-size:11px;")

        self.left_view = QLabel("")
        self.left_view.setAlignment(Qt.AlignCenter)
        self.left_view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.left_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.left_view.setScaledContents(False)

        self.right_view = QLabel("")
        self.right_view.setAlignment(Qt.AlignCenter)
        self.right_view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.right_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.right_view.setScaledContents(False)

        self.total_label = QLabel("Total Detect Count: 0 (100.0%)")
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setStyleSheet("color:#7f8a99; font-size:11px;")

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(4)
        left_col.addWidget(self.left_title)
        left_col.addWidget(self.left_view, stretch=1)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(4)
        right_col.addWidget(self.right_title)
        right_col.addWidget(self.right_view, stretch=1)

        main_row = QHBoxLayout()
        main_row.setContentsMargins(8, 8, 8, 0)
        main_row.setSpacing(8)
        main_row.addLayout(left_col, stretch=1)
        main_row.addLayout(right_col, stretch=1)

        main_col = QVBoxLayout()
        main_col.setContentsMargins(0, 0, 0, 8)
        main_col.setSpacing(6)
        main_col.addLayout(main_row, stretch=1)
        main_col.addWidget(self.total_label)

        self.setLayout(main_col)

    def set_titles(self, left: str, right: str):
        try:
            self.left_title.setText(str(left))
            self.right_title.setText(str(right))
        except Exception:
            pass

    def set_total_text(self, text: str):
        try:
            self.total_label.setText(str(text or ""))
        except Exception:
            pass

    def _set_pixmap(self, label: QLabel, img_bgr):
        if label is None:
            return
        if img_bgr is None:
            label.clear()
            return
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            try:
                target = label.size()
                if target.width() > 0 and target.height() > 0:
                    pix = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pass
            label.setPixmap(pix)
        except Exception:
            label.clear()

    def update_views(self, left_bgr, right_bgr):
        self._set_pixmap(self.left_view, left_bgr)
        self._set_pixmap(self.right_view, right_bgr)


class YoloTrainHistogramWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO Ball Training — Confidence Distribution")
        self.resize(520, 240)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#e6e6e6; font-size:11px;")

        self.view = QLabel("")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setScaledContents(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.info_label)
        layout.addWidget(self.view, stretch=1)
        self.setLayout(layout)

    def update_histogram(
        self,
        conf_values,
        *,
        easy_n: int = 0,
        med_n: int = 0,
        hard_n: int = 0,
        target_easy: float = 0.30,
        target_med: float = 0.40,
        target_hard: float = 0.30,
        total_target: int = 256,
        progress: int = 0,
        dataset_label: str = "",
    ):
        total = max(1, int(easy_n + med_n + hard_n))
        easy_pct = 100.0 * float(easy_n) / float(total)
        med_pct = 100.0 * float(med_n) / float(total)
        hard_pct = 100.0 * float(hard_n) / float(total)

        header = (
            f"{dataset_label}  #{int(progress)}/{int(total_target)}  "
            f"Easy {easy_pct:.0f}%/{int(round(target_easy*100))}%  "
            f"Med {med_pct:.0f}%/{int(round(target_med*100))}%  "
            f"Hard {hard_pct:.0f}%/{int(round(target_hard*100))}%"
        ).strip()
        try:
            self.info_label.setText(header)
        except Exception:
            pass

        w = 480
        h = 160
        img = np.zeros((h, w, 3), dtype=np.uint8)

        # Histogram bins 0.01–1.00
        bins = np.linspace(0.01, 1.0, 21)
        vals = np.asarray(conf_values or [], dtype=np.float32)
        vals = vals[(vals >= 0.01) & (vals <= 1.0)]
        hist = np.zeros((20,), dtype=np.float32)
        if vals.size > 0:
            hist, _ = np.histogram(vals, bins=bins)

        maxv = float(hist.max()) if hist.size > 0 else 1.0
        maxv = max(maxv, 1.0)
        bar_w = int(w / 20)

        # Axes
        cv2.rectangle(img, (0, 0), (w - 1, h - 1), (60, 60, 60), 1)
        for i in range(20):
            x0 = i * bar_w
            x1 = x0 + bar_w - 2
            v = float(hist[i]) / maxv
            y1 = h - 8
            y0 = int(round(y1 - v * (h - 20)))
            cv2.rectangle(img, (x0 + 1, y0), (x1, y1), (0, 200, 255), -1)

        # Min/Max labels
        cv2.putText(img, "0.01", (4, h - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        cv2.putText(img, "1.00", (w - 40, h - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
        self.view.setPixmap(QPixmap.fromImage(qimg))

    def bind_yolo_controls(self, conf_value: float, imgsz_value: int, on_conf, on_imgsz):
        try:
            self.yolo_conf_spin.blockSignals(True)
            self.yolo_imgsz_spin.blockSignals(True)
            self.yolo_conf_spin.setValue(float(conf_value))
            self.yolo_imgsz_spin.setValue(int(imgsz_value))
        except Exception:
            pass
        finally:
            try:
                self.yolo_conf_spin.blockSignals(False)
                self.yolo_imgsz_spin.blockSignals(False)
            except Exception:
                pass

        if not self._controls_connected:
            try:
                self.yolo_conf_spin.valueChanged.connect(on_conf)
                self.yolo_imgsz_spin.valueChanged.connect(on_imgsz)
                self._controls_connected = True
            except Exception:
                pass

    def _set_pixmap(self, label: QLabel, img_bgr):
        if label is None:
            return
        if img_bgr is None:
            label.clear()
            return
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            try:
                target = label.size()
                if target.width() > 0 and target.height() > 0:
                    pix = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pass
            label.setPixmap(pix)
        except Exception:
            label.clear()

    def _render_hsv_hist(self, frame_bgr, *, label_text: str = ""):
        if frame_bgr is None:
            return None
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv_img], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv_img], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv_img], [2], None, [256], [0, 256])
        except Exception:
            return None

        width = 256
        band_h = 60
        gap = 8
        img_h = band_h * 3 + gap * 2
        hist_img = np.zeros((img_h, width, 3), dtype=np.uint8)

        def draw_hist(hist, color, y0, bins):
            if hist is None:
                return
            hist = hist.flatten()
            maxv = float(hist.max()) if hist.size > 0 else 1.0
            maxv = max(maxv, 1.0)
            for i in range(bins):
                v = hist[i] / maxv
                x_bin = int(round(i * (width - 1) / (bins - 1)))
                y_val = int(round(v * (band_h - 6)))
                cv2.line(
                    hist_img,
                    (x_bin, y0 + band_h - 1),
                    (x_bin, y0 + band_h - 1 - y_val),
                    color,
                    1,
                )

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

        cv2.putText(hist_img, "H", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(hist_img, "S", (6, band_h + gap + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(hist_img, "V", (6, (band_h + gap) * 2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)
        if label_text:
            cv2.putText(hist_img, label_text, (90, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return hist_img

    def update_view(
        self,
        vis_bgr,
        info_text: str,
        *,
        full_hist=None,
        hi_img=None,
        hi_hist=None,
        lo_img=None,
        lo_hist=None,
    ):
        text = str(info_text or "")
        if self.compare_status_line:
            text = f"{self.compare_status_line}\n{text}" if text else self.compare_status_line
        self.info_label.setText(text)
        self._set_pixmap(self.view, vis_bgr)
        self._set_pixmap(self.full_hist_label, full_hist)
        self._set_pixmap(self.hi_img_label, hi_img)
        self._set_pixmap(self.hi_hist_label, hi_hist)
        self._set_pixmap(self.lo_img_label, lo_img)
        self._set_pixmap(self.lo_hist_label, lo_hist)

    def set_compare_status(self, enabled: bool, message: str = ""):
        if enabled:
            self.compare_status_line = str(message or "")
        else:
            self.compare_status_line = ""
        if self.compare_status_line:
            self.info_label.setText(self.compare_status_line)

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

class AttitudeWidget(QWidget):
    def __init__(self, *, range_deg: int = 20, parent=None):
        super().__init__(parent)
        self._range = max(1, int(range_deg))
        self._pitch = 0.0
        self._yaw = 0.0
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_values(self, pitch: float, yaw: float):
        self._pitch = max(-self._range, min(self._range, float(pitch)))
        self._yaw = max(-self._range, min(self._range, float(yaw)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        bg = QColor("#0f151d")
        border = QColor("#2a3645")
        grid = QColor("#2da8ff")
        text = QColor("#9fb0c3")
        dot = QColor("#f5f7fb")

        painter.fillRect(self.rect(), bg)

        rect = self.rect().adjusted(8, 8, -8, -8)
        side = min(rect.width(), rect.height())
        square = QRect(
            rect.center().x() - side // 2,
            rect.center().y() - side // 2,
            side,
            side,
        )

        painter.setPen(QPen(border, 1))
        painter.drawRect(square)

        center = square.center()
        painter.setPen(QPen(grid, 1))
        painter.drawLine(center.x(), square.top(), center.x(), square.bottom())
        painter.drawLine(square.left(), center.y(), square.right(), center.y())

        painter.setPen(QPen(text, 1))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            QRect(square.left(), center.y() - 10, square.width(), 20),
            Qt.AlignCenter,
            "(0,0)",
        )

        radius = max(3, int(round(side * 0.03)))
        span = (side / 2) - radius - 2
        x = center.x() + int(round((self._yaw / self._range) * span))
        y = center.y() - int(round((self._pitch / self._range) * span))

        painter.setPen(QPen(QColor("#0b1117"), 1))
        painter.setBrush(dot)
        painter.drawEllipse(QPoint(x, y), radius, radius)

class CameraWindow(QWidget, DogLogicMixin):
    def __init__(
        self,
        ip: str = DOG_DEFAULT_IP,
        video_port: int = DOG_VIDEO_PORT,
        control_port: int = DOG_CONTROL_PORT,
        low_voltage_threshold: float = LOW_VOLTAGE_THRESHOLD,
    ):
        super().__init__()  # QWidget init, super()is DogLogicMixin. __init__()

        # ---------- Ball & Head Tracking ----------
        # Initialize BallTracker early because it now owns the HeadTracker
        self.ball_tracker = BallTracker()
        
        # Use the HeadTracker instance inside BallTracker so the Kp slider works
        self.head_tracker = self.ball_tracker.head_tracker 
        self.head_tracking_enabled = False  # toggled with Ball button
        self.ball_tracking = BallTrackingController(self)

        self.ip = ip
        self.video_port = video_port
        self.control_port = control_port
        self.video_backend = str(VIDEO_BACKEND).strip().lower()
        self.sfu_rtsp_url = str(SFU_RTSP_URL).strip()
        self.sfu_rtsp_transport = str(SFU_RTSP_TRANSPORT).strip().lower()
        self.sfu_stream_path = str(SFU_STREAM_PATH).strip()
        self.video_target_width = int(VIDEO_TARGET_WIDTH)
        self.video_target_height = int(VIDEO_TARGET_HEIGHT)
        self.video_target_fps = int(VIDEO_TARGET_FPS)
        # In SFU mode we only need command channel from dog_client; camera is pulled from SFU RTSP.
        self.external_video_stream = self.video_backend == "sfu_rtsp"

        # Status flags for bottom bar
        self.server_ip_ok = False
        self.server_video_ok = False
        self.server_control_ok = False
        self.dog_connected = False

        # False = Mac camera, True = Dog camera
        self.use_dog_video = False

        # Dog video tracking
        self.dog_has_recent_frame = False
        self.last_dog_frame = None
        self.dog_last_frame_time = None
        self.video_stall = False

        # Freenove client + threads (Dog mode)
        self.dog_client = None
        self.video_thread = None
        self.cmd_thread = None
        self.stop_cmd_thread = False
        self.video_source_controller = VideoSourceController(self)
        self.video_source = None
        self.video_source_last_error = ""

        # FPS measurement: display vs receive (Dog mode)
        self.display_fps = 0.0
        self.display_frame_count = 0
        self.display_last_time = time.time()

        self.rx_fps = 0.0
        self.rx_frame_count = 0
        self.rx_last_time = time.time()

        # Client camera (Mac side) controller
        self.client_camera = ClientCameraController(self)

        # Last displayed BGR frame (for HSV picker)
        self.last_display_frame_bgr = None

        # Telemetry controller
        self.telemetry = TelemetryController(self, low_voltage_threshold=low_voltage_threshold)

        # Reconnect debounce & background loop control
        self.reconnect_in_progress = False
        self.stop_server_check = False

        # ---------- Ball tracking ----------
        # self.ball_tracker = BallTracker()  <--- REMOVED (already initialized above)
        self.ball_mode_enabled = False
        self.cv_ball = CVBallDetectionController(self)

        # ---------- AI Vision (test module) ----------
        self.ai_vision = AIVisionController(self, hist_window_factory=AIVisionHistogramWindow)

        # YOLO runtime (local inference) used by "Yolo Vision" mode.
        self.yolo_runtime = YoloRuntimeController(
            self,
            compare_window_factory=YoloCompareWindow,
            train_hist_window_factory=YoloTrainHistogramWindow,
        )

        # Dual-model YOLO (keep COCO yolov8n.pt untouched + mt_ball best.pt)
        self.yolo_dual_enabled = True
        self.yolo_coco_conf = float(YOLO_COCO_CONF_DEFAULT)
        self.yolo_mt_ball_conf = float(YOLO_MT_BALL_CONF_DEFAULT)
        self.yolo_dual_cap_fps = float(YOLO_DUAL_CAP_FPS_DEFAULT)

        # YOLO Manual Labeling controller
        self.yolo_labeling = YoloLabelingController(self, label_window_factory=YoloLabelWindow)
        self.overlay = OverlayRenderer()

        # Shared histogram window update rate for Object Detection Test modes
        self.test_hist_interval_s = 1.0
        self._test_hist_last_ts = 0.0
        self._test_hist_last_mode = ""
        self._test_hist_seq = 0

        # CV histogram + debug controller
        self.cv_hist_debug = CVHistDebugController(self)
        self.mask_picker = MaskPickerController(self)
        self.ui_events = UIEventHandlersController(self)
        self.frame_updater = FrameUpdateController(self)
        self._cmd_history = deque(maxlen=10)
        self.dog_commands = DogCommandController(self, write_log_func=_write_log)
        self.status_ui = StatusUIController(self)
        self.server_reconnect = ServerReconnectController(self)

        # cv_debug_window initialized by CVHistDebugController
        self.yolo_debug_window: YoloVisionDebugWindow | None = None
        self.yolo_label_window: YoloLabelWindow | None = None

        # Attitude/pose control state
        self._sliders_ready = False
        self._balance_enabled = False
        self._horizon_enabled = False

        
        # ---------- Mac camera ----------
        print("[INIT] Creating Mac camera capture...")
        # Use AVFoundation backend on macOS (required for Mac camera access)
        self.cap = None
        self._open_client_camera_initial()

        # ---------- UI ----------
        self.build_ui()
        self._refresh_client_camera_list(select_index=self._client_cam_opened_index)

        # Default: enable YOLO Vision on launch.
        try:
            self.ui_events.handle_yolo_vision_button()
        except Exception:
            pass

        # CV histogram window: only show when CV Ball mode is enabled.

        # ---------- Frame timer ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 fps UI refresh

        # ---------- Background server check ----------
        self.server_reconnect.start_server_check_thread()

        # ---------- Telemetry poll timer (Dog-mode only) ----------
        self.telemetry.start()

        # ---------- Initial probe (auto-enter Dog mode when reachable) ----------
        self._startup_initial_probe()

    # ==================================================================
    # Client camera (Mac side) helpers
    # ==================================================================
    def _log_client_cam(self, msg: str) -> None:
        return self.client_camera.log_client_cam(msg)

    def _open_client_camera_initial(self) -> None:
        return self.client_camera.open_client_camera_initial()

    def _retry_client_camera_if_needed(self) -> None:
        return self.client_camera.retry_client_camera_if_needed()

    def _refresh_client_camera_list(self, *, select_index=None):
        return self.client_camera.refresh_client_camera_list(select_index=select_index)

    def _on_mac_camera_changed(self, combo_index: int):
        return self.client_camera.on_mac_camera_changed(combo_index)

    # ==================================================================
    # Post-completion bark + cheer helpers
    # ==================================================================
    def _set_mask_cheer(self, text: str, *, visible: bool):
        return self.mask_picker.set_mask_cheer(text, visible=visible)

    def _apply_mask_cheer_if_needed(self):
        return self.mask_picker.apply_mask_cheer_if_needed()

    def _start_barking(self):
        return self.ball_tracking.start_barking()

    def _stop_barking(self):
        return self.ball_tracking.stop_barking()

    def _bark_tick(self):
        return self.ball_tracking.bark_tick()

    def _yolo_label_help_text(self) -> str:
        return self.yolo_labeling.yolo_label_help_text()

    def _update_yolo_debug_view(self, frame_bgr):
        return self.yolo_runtime.update_debug_view(frame_bgr)

    def _update_yolo_compare_view(self, frame_bgr):
        return self.yolo_runtime.update_compare_view(frame_bgr)

    def _on_yolo_conf_changed(self, val):
        return self.yolo_runtime.on_yolo_conf_changed(val)

    def _on_yolo_imgsz_changed(self, val):
        return self.yolo_runtime.on_yolo_imgsz_changed(val)

    def _apply_yolo_model_choice(self):
        return self.yolo_runtime.apply_yolo_model_choice()

    def _on_yolo_model_changed(self, idx=None):
        return self.yolo_runtime.on_yolo_model_changed(idx)

    def _on_yolo_compare_toggle(self, checked: bool):
        return self.yolo_runtime.on_yolo_compare_toggle(checked)

    def _ensure_yolo_compare_window(self) -> None:
        return self.yolo_runtime.ensure_yolo_compare_window()

    def _yolo_train_next_version_dir(self) -> tuple[str, str]:
        return self.yolo_runtime.yolo_train_next_version_dir()

    def _yolo_train_prepare_dataset(self):
        return self.yolo_runtime.yolo_train_prepare_dataset()

    def _yolo_train_iou(a, b) -> float:
        return YoloRuntimeController.yolo_train_iou(a, b)

    def _yolo_train_box_sane(self, x1, y1, x2, y2, w: int, h: int) -> bool:
        return self.yolo_runtime.yolo_train_box_sane(x1, y1, x2, y2, w, h)

    def _yolo_train_update_recent(self, box) -> bool:
        return self.yolo_runtime.yolo_train_update_recent(box)

    def _yolo_train_assign_difficulty(self, conf: float) -> str:
        return self.yolo_runtime.yolo_train_assign_difficulty(conf)

    def _yolo_train_bucket_allowed(self, difficulty: str) -> bool:
        return self.yolo_runtime.yolo_train_bucket_allowed(difficulty)

    def _yolo_train_note_bucket(self, difficulty: str):
        return self.yolo_runtime.yolo_train_note_bucket(difficulty)

    def _yolo_train_save_sample(self, frame_bgr, *, x1, y1, x2, y2, conf: float, difficulty: str):
        return self.yolo_runtime.yolo_train_save_sample(
            frame_bgr,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            conf=conf,
            difficulty=difficulty,
        )

    def _yolo_training_prompt(self):
        return self.yolo_runtime.yolo_training_prompt()

    def _stop_yolo_training(self, *, reason: str = ""):
        return self.yolo_runtime.stop_yolo_training(reason=reason)

    def _on_yolo_training_toggle(self, checked: bool):
        return self.yolo_runtime.on_yolo_training_toggle(checked)

    def _yolo_labeling_class_label(self) -> str:
        return self.yolo_labeling.yolo_labeling_class_label()

    def _on_yolo_labeling_class_changed(self, idx: int):
        return self.yolo_labeling.on_yolo_labeling_class_changed(idx)

    def _on_yolo_labeling_toggle(self, checked: bool):
        return self.yolo_labeling.on_yolo_labeling_toggle(checked)

    def _on_labeling_mouse_event(self, etype, pos, buttons):
        return self.yolo_labeling.on_labeling_mouse_event(etype, pos, buttons)

    def _on_labeling_key_event(self, event):
        return self.yolo_labeling.on_labeling_key_event(event)

    def _save_manual_label(self):
        return self.yolo_labeling.save_manual_label()

    def _yolo_save_manual_sample(self, img_bgr, bbox):
        return self.yolo_labeling.yolo_save_manual_sample(img_bgr, bbox)

    def _update_yolo_train_hist_window(self):
        return self.yolo_runtime.update_yolo_train_hist_window()

    def _bark_should_run(self) -> bool:
        return self.ball_tracking.bark_should_run()

    def _on_mask_clear_cheer(self):
        return self.mask_picker.on_mask_clear_cheer()
    def _startup_initial_probe(self):
        """Decide initial mode and give the window a sane startup size."""
        try:
            self.setWindowTitle("mtDogMain v3.33 - Mac Client + Dog Pi + SFU low-latency video")
        except Exception:
            pass

        # Ensure the video area is not squeezed into a thin strip on startup.
        try:
            # Height scale factor (tune as needed).
            STARTUP_H_SCALE = 1.2
            min_w, min_h = 1200, 900
            w, h = 1500, 1000

            self.setMinimumSize(min_w, int(round(min_h * STARTUP_H_SCALE)))
            self.resize(w, int(round(h * STARTUP_H_SCALE)))
        except Exception:
            pass

        # Prefer Dog mode when control is reachable and selected video backend is ready.
        try:
            ip_ok = self.ping_ip(self.ip)
            ctrl_ok = self.test_tcp_port(self.ip, self.control_port)
            video_ok = self._probe_selected_video_path()
            ok = ip_ok and ctrl_ok and video_ok
            self.server_ip_ok = bool(ip_ok)
            self.server_control_ok = bool(ctrl_ok)
            self.server_video_ok = bool(video_ok)
        except Exception:
            ok = False

        if ok:
            print("[INIT] Dog Pi reachable at startup → DOG mode.")
            self.dog_connected = True

            try:
                self.start_dog_client()
                if not self._init_dog_video_source():
                    raise RuntimeError(f"video source init failed ({self.video_backend})")
                self.use_dog_video = True
                self.schedule_dog_entry_beep()
            except Exception as e:
                print(f"[INIT] start_dog_client failed → MAC mode: {e}")
                self.use_dog_video = False
        else:
            print("[INIT] Dog Pi NOT ready at startup → MAC mode.")
            self.use_dog_video = False

        try:
            self.update_status_ui()
        except Exception:
            pass

    def _probe_selected_video_path(self) -> bool:
        backend = str(getattr(self, "video_backend", "legacy_socket") or "legacy_socket").strip().lower()
        if backend == "sfu_rtsp":
            src = self.video_source_controller.create_source()
            return bool(src.probe(timeout_s=1.0))
        return self.test_tcp_port(self.ip, self.video_port)

    def _init_dog_video_source(self) -> bool:
        try:
            self._close_dog_video_source()
        except Exception:
            pass
        src = self.video_source_controller.create_source()
        self.video_source = src
        ok = bool(src.open())
        if not ok:
            self.video_source_last_error = getattr(src, "last_err", "") or "video source open failed"
            print(f"[VIDEO] Backend={self.video_backend} open failed: {self.video_source_last_error}")
        else:
            self.video_source_last_error = ""
            print(f"[VIDEO] Backend={self.video_backend} ready.")
        return ok

    def _close_dog_video_source(self):
        src = getattr(self, "video_source", None)
        if src is None:
            return
        try:
            src.close()
        except Exception:
            pass
        self.video_source = None

    # ==================================================================
    # UI BUILDING
    # ==================================================================
    def build_ui(self):
        # ---- Main video ----
        self.video_label = QLabel("No Video")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color:#202020;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMouseTracking(True)
        self.setMouseTracking(True)

        # ---- Vision message pane (non-overlay, under video) ----
        self.vision_msg_label = QLabel("")
        self.vision_msg_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.vision_msg_label.setTextFormat(Qt.RichText)
        self.vision_msg_label.setWordWrap(True)
        self.vision_msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.vision_msg_label.setStyleSheet(
            "background-color:#0f151d; color:#cfd6df; font-size:12px; padding:6px;"
        )
        self.vision_msg_label.setFixedHeight(120)

        self.imu_msg_label = QLabel("")
        self.imu_msg_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.imu_msg_label.setTextFormat(Qt.RichText)
        self.imu_msg_label.setWordWrap(True)
        self.imu_msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.imu_msg_label.setStyleSheet(
            "background-color:#0f151d; color:#cfd6df; font-size:12px; padding:6px; border:1px solid #233144;"
        )
        self.imu_msg_label.setFixedHeight(120)
        self.imu_msg_label.setFixedWidth(260)

        # ---- Right-side panel ----
        self.ctrl_panel = QFrame()
        self.ctrl_panel.setObjectName("ctrlPanel")
        # IMPORTANT: use layout constraints (min width) instead of a too-small fixed
        # width that can clip the right-most motion buttons on macOS/HiDPI.
        self.ctrl_panel.setMinimumWidth(260)
        self.ctrl_panel.setStyleSheet(
            """
            QFrame#ctrlPanel {
                background-color:#111820;
                border-left:1px solid #303840;
            }
            QPushButton {
                border-radius:16px;
                padding:6px;
                font-size:14px;
            }
            QPushButton:focus { outline:none; }
            """
        )

        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(14)

        title = QLabel("Dog Controls")
        title.setStyleSheet("color:#ffffff; font-size:14px; font-weight:bold;")
        panel_layout.addWidget(title)
        panel_layout.addSpacing(4)

        # ---- Movement grid ----
        MotionGridBuilder(self).build(panel_layout)

        panel_layout.addSpacing(8)

        section_builder = ControlPanelSectionsBuilder(self)
        section_builder.build_actions(panel_layout)
        section_builder.build_test(panel_layout)

        panel_layout.addSpacing(8)

        # ---- Balance / Horizon toggles ----
        stability_label = QLabel("Stability Modes")
        stability_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(stability_label)

        stability_frame = QFrame()
        stability_frame.setStyleSheet(
            "background-color:#0f151d; border:1px solid #233144; border-radius:10px;"
        )
        stability_layout = QHBoxLayout()
        stability_layout.setContentsMargins(8, 8, 8, 8)
        stability_layout.setSpacing(8)

        self.btn_balance = QPushButton("Balance\nOFF")
        self.btn_balance.setCheckable(True)
        self.btn_balance.setMinimumHeight(42)
        self.btn_balance.setToolTip("CMD_BALANCE toggle")

        self.btn_horizon = QPushButton("Horizon\nOFF")
        self.btn_horizon.setCheckable(True)
        self.btn_horizon.setMinimumHeight(42)
        self.btn_horizon.setToolTip("CMD_HORIZON enable/disable")

        stability_layout.addWidget(self.btn_balance)
        stability_layout.addWidget(self.btn_horizon)
        stability_frame.setLayout(stability_layout)
        panel_layout.addWidget(stability_frame)

        self._apply_toggle_style(self.btn_balance, False, on_color="#00c853", off_color="#1a2430")
        self._apply_toggle_style(self.btn_horizon, False, on_color="#f6c343", off_color="#1a2430")

        # ---- Attitude + sliders ----
        attitude_label = QLabel("Attitude Angle")
        attitude_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(attitude_label)

        attitude_frame = QFrame()
        attitude_frame.setStyleSheet(
            "background-color:#0f151d; border:1px solid #233144; border-radius:10px;"
        )
        attitude_layout = QVBoxLayout()
        attitude_layout.setContentsMargins(8, 8, 8, 8)
        attitude_layout.setSpacing(8)

        attitude_grid = QHBoxLayout()
        attitude_grid.setContentsMargins(0, 0, 0, 0)
        attitude_grid.setSpacing(6)

        pitch_col = QVBoxLayout()
        pitch_col.setContentsMargins(0, 0, 0, 0)
        pitch_col.setSpacing(2)
        pitch_label_width = 48
        self.label_pitch_top = QLabel("+20\n(Pitch)")
        self.label_pitch_mid = QLabel("0")
        self.label_pitch_bottom = QLabel("-20")
        for lbl in (self.label_pitch_top, self.label_pitch_mid, self.label_pitch_bottom):
            lbl.setStyleSheet("color:#9fb0c3; font-size:10px;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl.setFixedWidth(pitch_label_width)
        pitch_col.addWidget(self.label_pitch_top)
        pitch_col.addStretch()
        pitch_col.addWidget(self.label_pitch_mid)
        pitch_col.addStretch()
        pitch_col.addWidget(self.label_pitch_bottom)

        self.attitude_widget = AttitudeWidget(range_deg=20)

        attitude_grid.addLayout(pitch_col)
        attitude_grid.addWidget(self.attitude_widget)

        attitude_layout.addLayout(attitude_grid)

        yaw_row = QHBoxLayout()
        yaw_row.setContentsMargins(pitch_label_width, 0, 0, 0)
        yaw_row.setSpacing(6)
        self.label_yaw_left = QLabel("-20")
        self.label_yaw_mid = QLabel("0")
        self.label_yaw_right = QLabel("+20")
        self.label_yaw_axis = QLabel("(Yaw)")
        for lbl in (self.label_yaw_left, self.label_yaw_mid, self.label_yaw_right, self.label_yaw_axis):
            lbl.setStyleSheet("color:#9fb0c3; font-size:10px;")
            lbl.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        yaw_row.addWidget(self.label_yaw_left)
        yaw_row.addStretch()
        yaw_row.addWidget(self.label_yaw_mid)
        yaw_row.addStretch()
        yaw_row.addWidget(self.label_yaw_right)
        yaw_row.addWidget(self.label_yaw_axis)
        attitude_layout.addLayout(yaw_row)

        slider_frame = QFrame()
        slider_frame.setStyleSheet(
            "QLabel { color:#cfd6df; font-size:11px; }"
            "QSlider::groove:horizontal { height:6px; border-radius:3px; background:#1b2530; }"
            "QSlider::sub-page:horizontal { height:6px; border-radius:3px; background:#2da8ff; }"
            "QSlider::add-page:horizontal { height:6px; border-radius:3px; background:#1b2530; }"
            "QSlider::handle:horizontal { width:12px; margin:-4px 0; border-radius:6px; background:#f0f4f8; border:1px solid #3a4655; }"
        )
        slider_layout = QVBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(6)

        def build_slider_row(
            title: str,
            *,
            min_val: int,
            max_val: int,
            value: int,
            slider_attr: str,
            value_attr: str,
            tooltip: str,
        ):
            row = QHBoxLayout()
            row.setSpacing(6)
            value_label = QLabel(str(value))
            value_label.setFixedWidth(28)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(value)
            slider.setToolTip(tooltip)
            title_label = QLabel(title)
            title_label.setFixedWidth(64)
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(value_label)
            row.addWidget(slider, stretch=1)
            row.addWidget(title_label)
            setattr(self, slider_attr, slider)
            setattr(self, value_attr, value_label)
            return row

        slider_layout.addLayout(
            build_slider_row(
                "Roll",
                min_val=-20,
                max_val=20,
                value=0,
                slider_attr="slider_roll",
                value_attr="label_roll_value",
                tooltip="CMD_ATTITUDE roll",
            )
        )
        slider_layout.addLayout(
            build_slider_row(
                "Pitch",
                min_val=-20,
                max_val=20,
                value=0,
                slider_attr="slider_pitch",
                value_attr="label_pitch_value",
                tooltip="CMD_ATTITUDE pitch",
            )
        )
        slider_layout.addLayout(
            build_slider_row(
                "Yaw",
                min_val=-20,
                max_val=20,
                value=0,
                slider_attr="slider_yaw",
                value_attr="label_yaw_value",
                tooltip="CMD_ATTITUDE yaw",
            )
        )
        slider_layout.addLayout(
            build_slider_row(
                "Horizon",
                min_val=-20,
                max_val=20,
                value=0,
                slider_attr="slider_horizon",
                value_attr="label_horizon_value",
                tooltip="CMD_HORIZON trim",
            )
        )
        slider_layout.addLayout(
            build_slider_row(
                "Height",
                min_val=-20,
                max_val=20,
                value=0,
                slider_attr="slider_height",
                value_attr="label_height_value",
                tooltip="CMD_HEIGHT",
            )
        )
        head_min = int(getattr(self.head_tracker.cfg, "min_deg", 40))
        head_max = int(getattr(self.head_tracker.cfg, "max_deg", 140))
        head_neutral = int(getattr(self.head_tracker.cfg, "neutral_deg", 90))
        slider_layout.addLayout(
            build_slider_row(
                "Head",
                min_val=head_min,
                max_val=head_max,
                value=head_neutral,
                slider_attr="slider_head",
                value_attr="label_head_value",
                tooltip="CMD_HEAD angle",
            )
        )

        slider_frame.setLayout(slider_layout)
        attitude_layout.addWidget(slider_frame)

        attitude_frame.setLayout(attitude_layout)
        panel_layout.addWidget(attitude_frame)

        panel_layout.addStretch()

        section_builder.build_system(panel_layout)

        self.ctrl_panel.setLayout(panel_layout)

        # ---- Bottom bar ----
        self.dog_button = QPushButton("Dog Video\nReconnect")
        self.dog_button.setStyleSheet(
            "font-size:16px; padding:10px; background-color:white; color:red;"
        )
        self.dog_button.clicked.connect(self.try_reconnect)

        self.status_detail_label = QLabel()
        self.status_detail_label.setTextFormat(Qt.RichText)
        self.status_detail_label.setStyleSheet("font-size:16px;")

        self.mac_cam_label = QLabel("Mac Camera:")
        self.mac_cam_label.setStyleSheet("color:#cfd6df; font-size:12px;")
        self.mac_cam_combo = QComboBox()
        self.mac_cam_combo.setMinimumWidth(240)
        self.mac_cam_combo.currentIndexChanged.connect(self._on_mac_camera_changed)

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(self.dog_button)
        bottom_bar.addWidget(self.status_detail_label)
        bottom_bar.addSpacing(8)
        bottom_bar.addWidget(self.mac_cam_label)
        bottom_bar.addWidget(self.mac_cam_combo)
        bottom_bar.addStretch()

        self.bottom_frame = QFrame()
        self.bottom_frame.setObjectName("bottomFrame")
        self.bottom_frame.setLayout(bottom_bar)
        self.bottom_frame.setFixedHeight(70)
        self.bottom_frame.setStyleSheet(
            "QFrame#bottomFrame { background-color:#001a3d; }"
        )

        # ---- Combine ----
        video_frame = QFrame()
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(6)
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)
        info_row.addWidget(self.vision_msg_label, stretch=1)
        info_row.addWidget(self.imu_msg_label, stretch=0)

        video_layout.addWidget(self.video_label, stretch=1)
        video_layout.addLayout(info_row, stretch=0)
        video_frame.setLayout(video_layout)

        center_layout = QHBoxLayout()
        center_layout.addWidget(video_frame, stretch=1)
        center_layout.addWidget(self.ctrl_panel, stretch=0)

        main_layout = QVBoxLayout()
        main_layout.addLayout(center_layout, stretch=1)
        main_layout.addWidget(self.bottom_frame, stretch=0)
        self.setLayout(main_layout)

        # ---- Wire buttons to handlers ----
        # Motion: original behavior (single click sends one command).
        self.btn_W.clicked.connect(lambda: self.send_motion_command("w"))
        self.btn_E.clicked.connect(lambda: self.send_motion_command("e"))
        self.btn_R.clicked.connect(lambda: self.send_motion_command("r"))
        self.btn_S.clicked.connect(lambda: self.send_motion_command("s"))
        self.btn_D.clicked.connect(lambda: self.send_motion_command("d"))
        self.btn_F.clicked.connect(lambda: self.send_motion_command("f"))
        self.btn_C.clicked.connect(lambda: self.send_motion_command("c"))
        self.btn_SpaceStop.clicked.connect(self.send_stop_motion)

        self.btn_Beep.clicked.connect(self.handle_beep_key)
        self.btn_LED.clicked.connect(self.handle_led_button)
        self.btn_Calib.clicked.connect(self.handle_calib_button)
        self.btn_Ball.clicked.connect(self.handle_ball_button)
        self.btn_YoloVision.clicked.connect(self.handle_yolo_vision_button)
        self.btn_Face.clicked.connect(self.handle_face_button)

        self.btn_play.clicked.connect(self.handle_play_button)
        self.btn_quit.clicked.connect(self.handle_quit)

        self.btn_balance.toggled.connect(self.handle_balance_toggle)
        self.btn_horizon.toggled.connect(self.handle_horizon_toggle)

        self.slider_roll.valueChanged.connect(self._on_attitude_slider_changed)
        self.slider_pitch.valueChanged.connect(self._on_attitude_slider_changed)
        self.slider_yaw.valueChanged.connect(self._on_attitude_slider_changed)
        self.slider_horizon.valueChanged.connect(self._on_horizon_slider_changed)
        self.slider_height.valueChanged.connect(self._on_height_slider_changed)
        self.slider_head.valueChanged.connect(self._on_head_slider_changed)

        self.slider_horizon.setEnabled(False)
        self._on_attitude_slider_changed()
        self._on_horizon_slider_changed()
        self._on_height_slider_changed()
        self._on_head_slider_changed()

        QTimer.singleShot(250, self._enable_pose_controls)

    def _enable_pose_controls(self):
        self._sliders_ready = True

    def _apply_toggle_style(self, btn: QPushButton, active: bool, *, on_color: str, off_color: str):
        bg = on_color if active else off_color
        fg = "#0b1117" if active else "#cfd6df"
        border = on_color if active else "#2a3340"
        hover_bg = "#ffffff" if active else "#1b2530"
        hover_fg = on_color if active else "#ffffff"
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color:{bg};
                color:{fg};
                border:1px solid {border};
                border-radius:14px;
                padding:6px 10px;
                font-size:12px;
                letter-spacing:0.3px;
            }}
            QPushButton:hover {{
                background-color:{hover_bg};
                color:{hover_fg};
            }}
            """
        )

    def handle_balance_toggle(self, checked: bool):
        self._balance_enabled = bool(checked)
        self.btn_balance.setText(f"Balance\n{'ON' if checked else 'OFF'}")
        self._apply_toggle_style(self.btn_balance, checked, on_color="#00c853", off_color="#1a2430")
        payload = f"{CMD.CMD_BALANCE}#{1 if checked else 0}\n"
        self._send_cmd(payload, tag="BAL")

    def handle_horizon_toggle(self, checked: bool):
        self._horizon_enabled = bool(checked)
        self.btn_horizon.setText(f"Horizon\n{'ON' if checked else 'OFF'}")
        self._apply_toggle_style(self.btn_horizon, checked, on_color="#f6c343", off_color="#1a2430")
        self.slider_horizon.setEnabled(bool(checked))
        if not checked:
            payload = f"{CMD.CMD_HORIZON}#0\n"
            self._send_cmd(payload, tag="HZN")
            return
        self._on_horizon_slider_changed()

    def _on_attitude_slider_changed(self):
        roll = int(self.slider_roll.value())
        pitch = int(self.slider_pitch.value())
        yaw = int(self.slider_yaw.value())
        self.label_roll_value.setText(str(roll))
        self.label_pitch_value.setText(str(pitch))
        self.label_yaw_value.setText(str(yaw))
        self.attitude_widget.set_values(pitch=pitch, yaw=yaw)
        if not self._sliders_ready:
            return
        payload = f"{CMD.CMD_ATTITUDE}#{roll}#{pitch}#{yaw}\n"
        self._send_cmd(payload, tag="ATT")

    def _on_horizon_slider_changed(self):
        value = int(self.slider_horizon.value())
        self.label_horizon_value.setText(str(value))
        if not self._sliders_ready or not self._horizon_enabled:
            return
        payload = f"{CMD.CMD_HORIZON}#{value}\n"
        self._send_cmd(payload, tag="HZN")

    def _on_height_slider_changed(self):
        value = int(self.slider_height.value())
        self.label_height_value.setText(str(value))
        if not self._sliders_ready:
            return
        payload = f"{CMD.CMD_HEIGHT}#{value}\n"
        self._send_cmd(payload, tag="HEIGHT")

    def _on_head_slider_changed(self):
        value = int(self.slider_head.value())
        self.label_head_value.setText(str(value))
        try:
            self.head_tracker.current_angle = float(value)
        except Exception:
            pass
        if not self._sliders_ready:
            return
        self.send_head_angle(value)


    # ==================================================================
    # Status UI
    # ==================================================================
    def update_status_ui(self):
        return self.ui_events.update_status_ui()

    # ==================================================================
    # Dog reconnect & mode switch
    # ==================================================================
    def try_reconnect(self):
        return self.ui_events.try_reconnect()

    # ==================================================================
    # Frame update & drawing
    # ==================================================================
    def update_frame(self):
        return self.frame_updater.update_frame()

    def _cmd_key_to_human(self, key_char: str | None, *, send_stop: bool = False) -> str:
        return self.dog_commands.cmd_key_to_human(key_char, send_stop=send_stop)

    def _log_cmd(self, payload: str, *, tag: str = "CMD") -> None:
        return self.dog_commands.log_cmd(payload, tag=tag)

    def _send_relax_only(self):
        return self.dog_commands.send_relax_only()

    def _send_stop_pwm_only(self):
        return self.dog_commands.send_stop_pwm_only()

    def _trigger_close_enough_sequence(self, *, ball_diameter: float | None, frame_w: float):
        return self.ball_tracking.trigger_close_enough_sequence(ball_diameter=ball_diameter, frame_w=frame_w)

    def _handle_tracking_mode_transition(self, mode): # NEW, called from update_frame
        return self.ball_tracking.handle_tracking_mode_transition(mode)

    # ==================================================================
    # Head servo command helper
    # ==================================================================
    def send_head_angle(self, angle_deg: int):
        return self.dog_commands.send_head_angle(angle_deg)

    # ==================================================================
    # Events & helpers
    # ==================================================================
    def mousePressEvent(self, event):   # for the color video window
        """
        Left-click on the video picks a shared sample point for HSV picker.
        """
        self.mask_picker.handle_mouse_press(event)
        super().mousePressEvent(event)

    # ------------------------------------------
    def keyPressEvent(self, event):
        """
        Keyboard:
          WASD+QE → motion std (W=fwd, S=back, A=turnL, D=turnR, Q=strafeL, E=strafeR)
          Space → stop (CMD_MOVE_STOP)
          B → beep
          L → LED
          K → calib
          P → play
          Q → quit (if Ctrl+Q, but here Q is motion strafe! Need to resolve conflict)
          T → toggle ball tracking (same as Ball button)
        """
        # Space sometimes comes through as a keycode with blank text on some platforms,
        # so handle it via keycode first.
        if event.key() == Qt.Key_Space:
            self.send_stop_motion()
            return

        text = event.text()
        if not text:
            return
        key = text.lower()

        # Resolve Q conflict: check modifiers or just use Q for motion?
        # Standard Main.py used Q for strafe and did not have 'Q' for quit (it was Esc or close button).
        # send_motion_command handles 'q'.
        # handle_quit is mapped to Key_Q in some contexts?
        # Let's map 'q' to motion. If user wants to quit, they can use window close or Cmd+Q.

        if key in ("w", "a", "s", "d", "q", "e"):
            self.send_motion_command(key)
        elif key == "b":
            self.handle_beep_key()
        elif key == "l":
            self.handle_led_button()
        elif key == "k":
            self.handle_calib_button()
        elif key == "p":
            self.handle_play_button()
        elif key == "t":
            self.handle_ball_button()
        else:
            super().keyPressEvent(event)

    def _update_full_body_tracking(self, ball_center, frame_shape):
        return self.ball_tracking.update_full_body_tracking(ball_center, frame_shape)

    def _update_lost_ball_search(self, frame_shape):
        return self.ball_tracking.update_lost_ball_search(frame_shape)

    # ------------------------------------------
    def handle_ball_button(self):
        return self.ui_events.handle_ball_button()

    # ------------------------------------------
    def _on_cv_debug_radial_gate_changed(self, checked: bool):
        """Toggle CV radial gate from CV debug window (experimental)."""
        return self.cv_ball.on_cv_debug_radial_gate_changed(checked)

    # ------------------------------------------
    def handle_yolo_vision_button(self):
        return self.ui_events.handle_yolo_vision_button()


    def handle_quit(self):
        return self.ui_events.handle_quit()

    def _position_cv_hist_window(self):
        return self.cv_hist_debug.position_cv_hist_window()

    def _maybe_update_cv_hist(self, frame_bgr):
        return self.cv_hist_debug.maybe_update_cv_hist(frame_bgr)

    def _clear_object_detection_state(self, *, clear_hist: bool = True):
        return self.ui_events.clear_object_detection_state(clear_hist=clear_hist)


    def closeEvent(self, event):
        return self.ui_events.close_event(event)
    
    #------------------------------------
    def mouseMoveEvent(self, event):
        """
        Mouse hover over the main video:

          • DOES NOT move the HSV picker (click-and-stay behavior).
          • Only updates hover_xy_color / hover_hsv_color so we can display
            "hover HSV (x,y)" near the cursor, similar to the Mask window.
        """
        self.mask_picker.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    #=================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CameraWindow()
    w.show()
    sys.exit(app.exec_())
