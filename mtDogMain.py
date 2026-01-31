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

 v2.53  (2026-01-14)          : Body tracking motion policy update
     • Body tracking now prioritizes left/right turning to X-center the ball.
     • Forward/backward motion is blocked until the ball is X-centered within tolerance.
     • Switching from Y→X correction triggers an immediate turn command (no extra wait).
     • Body tracking defaults to forward-only (no backward) to reduce surprises from jitter.
     • Expose "Allow backward" in Mask window and persist to mtBall_Calib.json.

 v2.54  (2026-01-14)          : Body tracking derivative damping (Kd)
     • Added derivative damping (Body-Kd) to reduce overshoot when deadzone is narrow.
     • Expose Body-Kd slider in Mask window and persist to mtBall_Calib.json.

 v2.55  (2026-01-14)          : Body tracking proportional speed (Kp)
     • Added Body-Kp proportional speed control (replaces bang-bang feel by scaling turn/forward speed).
     • Body-Kp is optional (0.0 keeps fixed-speed behavior) and persisted to mtBall_Calib.json.

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
from Command import COMMAND
import threading
import time

import numpy as np
import cv2

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QSizePolicy,
    QSlider, QComboBox, QLineEdit, QCheckBox, QDoubleSpinBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QPixmap, QImage
try:
    from PyQt5.QtMultimedia import QCameraInfo
except Exception:
    QCameraInfo = None  # type: ignore
try:
    from AVFoundation import AVCaptureDevice, AVMediaTypeVideo  # type: ignore[import-not-found]
except Exception:
    AVCaptureDevice = None  # type: ignore
    AVMediaTypeVideo = None  # type: ignore

from ui.ai_hist_windows import AIVisionHistogramWindow
from ui.common_widgets import ClickableLabel
from ui.cv_debug_windows import CVBallDebugWindow, CVBallHistogramWindow
from ui.yolo_debug_windows import YoloVisionDebugWindow
from ai_vision_controller import AIVisionController
from overlay_renderer import OverlayRenderer
from cv_hist_debug import CVHistDebugController
from mask_picker import MaskPickerController
from cv_ball_detection import CVBallDetectionController
from yolo_labeling import YoloLabelingController
from yolo_runtime import YoloRuntimeController
from ui_event_handlers import UIEventHandlersController
from frame_update_controller import FrameUpdateController

from mtDogConfig import (
    DOG_DEFAULT_IP,
    DOG_VIDEO_PORT,
    DOG_CONTROL_PORT,
    LOW_VOLTAGE_THRESHOLD,
    CLIENT_CAMERA_INDEX_ORDER,
    CLIENT_CAMERA_RETRY_SEC,
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
        main_row.setContentsMargins(8, 8, 8, 8)
        main_row.setSpacing(8)
        main_row.addLayout(left_col, stretch=1)
        main_row.addLayout(right_col, stretch=1)

        self.setLayout(main_row)

    def set_titles(self, left: str, right: str):
        try:
            self.left_title.setText(str(left))
            self.right_title.setText(str(right))
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

        # Track tracking-mode transitions (e.g., to center head when switching modes)
        self._last_tracking_mode = getattr(self.ball_tracker, "tracking_mode", None)
        
        self.last_dog_frame_height = 0      # updated when Dog frame arrives
        self.body_tracking_interval = 0.6   # seconds between body tracking commands
        self.last_body_cmd_time = 0.0

        # Body tracking policy: by default, do not command backward motion.
        # (Backward can be surprising when the ball jitters above center while turning.)
        self.body_allow_backward = False

        # Body tracking hysteresis state (reduces left/right oscillation near center)
        self._body_hyst_axis = None  # 'x' | 'y' | None
        self._body_hyst_dir = 0      # -1 or +1

        # Lost-ball search + obstacle avoidance state
        self._lost_search_state = "idle"   # 'idle' | 'forward' | 'scan' | 'escape'
        self._lost_search_last_cmd_ts = 0.0
        self._lost_search_sent_stop = False
        self._lost_search_phase = "scan"   # 'scan' | 'forward'
        self._lost_search_phase_start_ts = 0.0

        # FULL mode head lock (stabilize SONIC ranging): keep head at neutral and skip head tracking.
        self.full_lock_head_in_full = True
        self._full_head_last_sent_ts = 0.0
        self._full_head_sent_once = False

        # FULL-mode close-enough completion sequence
        self._close_enough_latched = False
        self._close_enough_seq_state = "idle"  # 'idle' | 'triggered' | 'relax' | 'off'
        self._close_enough_seq_ts = 0.0
        self._close_enough_off_timer = None

        # FULL close-enough latch reset + STOP spam guard
        self._close_enough_last_stop_ts = 0.0
        self._close_enough_stop_min_interval_s = 0.8
        self._close_enough_clear_below_ratio = 0.6  # hysteresis: clear latch when diam < (w/4)*ratio
        self._close_enough_clear_hold_s = 0.6
        self._close_enough_clear_start_ts = 0.0

        # Ball tracking status (for Color window overlay)
        self._ball_close_enough = False
        self._ball_locked = False
        self._ball_lock_source = ""
        self._body_cmd_name = ""
        self._cmd_history = deque(maxlen=10)

        # Post-completion "barking" (beep + yellow flash) + Mask cheer message
        self._bark_timer = QTimer()
        self._bark_timer.timeout.connect(self._bark_tick)
        self._bark_active = False
        self._bark_pending_start = False
        self._bark_interval_ms = 2000
        self._cheer_text = ""
        self._cheer_visible = False
        self._cheer_pending_apply = False

        self.ip = ip
        self.video_port = video_port
        self.control_port = control_port

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

        # FPS measurement: display vs receive (Dog mode)
        self.display_fps = 0.0
        self.display_frame_count = 0
        self.display_last_time = time.time()

        self.rx_fps = 0.0
        self.rx_frame_count = 0
        self.rx_last_time = time.time()

        # Client camera (Mac side) preference / retry
        self._client_cam_indices = list(CLIENT_CAMERA_INDEX_ORDER)
        if not self._client_cam_indices:
            self._client_cam_indices = [0]
        self._client_cam_opened_index = None
        self._client_cam_next_try_ts = 0.0
        self._client_cam_try_pos = 0
        self._client_cam_fail_count = 0
        self._client_cam_fail_limit = 10
        self._client_cam_last_log_ts = 0.0
        self._client_cam_combo_map = []

        # Last displayed BGR frame (for HSV picker)
        self.last_display_frame_bgr = None

        # Telemetry (distance, battery, simple state text)
        self.distance_cm = 0.0
        self.battery_v = 0.0
        self.left_state_seconds = 0
        self.state_name = "Resting"
        self.right_state_seconds = 0
        # Separate textual state (e.g., RELAX / MODE) to avoid flapping the
        # work/rest overlay.
        self.dog_state_name = "Resting"

        # Low-battery tracking
        self.low_voltage_threshold = low_voltage_threshold
        self.last_low_beep_time = 0.0

        # Telemetry validity
        self.telemetry_valid = False
        self.last_telemetry_ok_time = 0.0

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

        # cv_debug_window initialized by CVHistDebugController
        self.yolo_debug_window: YoloVisionDebugWindow | None = None
        self.yolo_label_window: YoloLabelWindow | None = None

        
        # ---------- Mac camera ----------
        print("[INIT] Creating Mac camera capture...")
        # Use AVFoundation backend on macOS (required for Mac camera access)
        self.cap = None
        self._open_client_camera_initial()

        # ---------- UI ----------
        self.build_ui()
        self._refresh_client_camera_list(select_index=self._client_cam_opened_index)

        # CV histogram window: only show when CV Ball mode is enabled.

        # ---------- Frame timer ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 fps UI refresh

        # ---------- Background server check ----------
        self.server_check_thread = threading.Thread(
            target=self.server_check_worker,
            daemon=True,
        )
        self.server_check_thread.start()

        # ---------- Telemetry poll timer (Dog-mode only) ----------
        self.telemetry_timer = QTimer()
        self.telemetry_timer.timeout.connect(self.poll_telemetry)
        self.telemetry_timer.start(1000)  # 1 Hz

        # ---------- Initial probe (auto-enter Dog mode when reachable) ----------
        self._startup_initial_probe()

    # ==================================================================
    # Client camera (Mac side) helpers
    # ==================================================================
    def _log_client_cam(self, msg: str) -> None:
        last = str(getattr(self, "_client_cam_last_msg", "") or "")
        if msg == last:
            return  # Suppress duplicate success messages
        print(msg)
        self._client_cam_last_msg = msg
        self._client_cam_last_log_ts = time.time()

    def _open_client_camera_index(self, index: int, *, require_frame: bool = False):
        cap = None
        try:
            cap = cv2.VideoCapture(int(index), cv2.CAP_AVFOUNDATION)
        except Exception:
            cap = None
        if cap is None or not cap.isOpened():
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            return None
        if require_frame:
            ok = False
            for _ in range(3):
                try:
                    ret, _ = cap.read()
                except Exception:
                    ret = False
                if ret:
                    ok = True
                    break
                time.sleep(0.05)
            if not ok:
                try:
                    cap.release()
                except Exception:
                    pass
                return None
        return cap

    def _open_client_camera_best(self, preferred_index=None) -> bool:
        candidates = []
        if preferred_index is not None:
            candidates.append(int(preferred_index))
        candidates.extend([i for i in self._client_cam_indices if i not in candidates])
        for idx in candidates:
            cap = self._open_client_camera_index(idx, require_frame=True)
            if cap is not None:
                self.cap = cap
                self._client_cam_opened_index = idx
                self._client_cam_fail_count = 0
                self._log_client_cam(f"[SRC] Client camera opened (index {idx}).")
                return True
        self.cap = None
        self._client_cam_opened_index = None
        return False

    def _open_client_camera_initial(self) -> None:
        opened = False
        for idx in list(self._client_cam_indices):
            cap = self._open_client_camera_index(idx, require_frame=True)
            if cap is not None:
                self.cap = cap
                self._client_cam_opened_index = idx
                opened = True
                print(f"[INIT] Mac camera opened OK (index {idx}).")
                break
        if not opened:
            print("[INIT] ERROR: Mac camera could not be opened.")
            print("[INIT] HINT: Check System Settings > Privacy & Security > Camera")
            print("[INIT] HINT: Make sure Terminal/Python has camera permission")
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
            self.cap = None
            self._client_cam_opened_index = None
            self._client_cam_next_try_ts = time.time() + float(CLIENT_CAMERA_RETRY_SEC)

    def _iter_client_camera_indices(self):
        if not self._client_cam_indices:
            return [0]
        n = len(self._client_cam_indices)
        if self._client_cam_try_pos >= n:
            self._client_cam_try_pos = 0
        ordered = (
            self._client_cam_indices[self._client_cam_try_pos :]
            + self._client_cam_indices[: self._client_cam_try_pos]
        )
        self._client_cam_try_pos = (self._client_cam_try_pos + 1) % n
        return ordered

    def _retry_client_camera_if_needed(self) -> None:
        if self.cap is not None and self.cap.isOpened():
            return
        now = time.time()
        if now < float(self._client_cam_next_try_ts or 0.0):
            return
        for idx in self._iter_client_camera_indices():
            cap = self._open_client_camera_index(idx, require_frame=True)
            if cap is not None:
                self.cap = cap
                self._client_cam_opened_index = idx
                self._client_cam_fail_count = 0
                self._log_client_cam(f"[SRC] Client camera opened (index {idx}).")
                return
        self._client_cam_opened_index = None
        self._client_cam_next_try_ts = now + float(CLIENT_CAMERA_RETRY_SEC)

    def _get_avfoundation_device_names(self):
        if QCameraInfo is not None:
            try:
                cams = QCameraInfo.availableCameras()
                names = []
                for cam in cams or []:
                    try:
                        names.append(str(cam.description()))
                    except Exception:
                        pass
                if names:
                    return names
            except Exception:
                pass
        if AVCaptureDevice is None or AVMediaTypeVideo is None:
            return []
        try:
            devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
        except Exception:
            devices = []
        names = []
        for dev in devices or []:
            try:
                names.append(str(dev.localizedName()))
            except Exception:
                pass
        return names

    def _scan_client_camera_indices(self, max_index: int = 2):
        # Default to checking just 0, 1, 2 for speed and less log spam.
        candidates = list(dict.fromkeys(self._client_cam_indices + list(range(0, max_index + 1))))
        available = []
        for idx in candidates:
            cap = self._open_client_camera_index(idx)
            if cap is not None:
                available.append(idx)
                try:
                    cap.release()
                except Exception:
                    pass
        return available

    def _refresh_client_camera_list(self, *, select_index=None):
        if not hasattr(self, "mac_cam_combo"):
            return
        available = self._scan_client_camera_indices()
        self.mac_cam_combo.blockSignals(True)
        try:
            self.mac_cam_combo.clear()
        except Exception:
            pass
        self._client_cam_combo_map = []
        names = self._get_avfoundation_device_names()
        if names:
            try:
                self.mac_cam_combo.setToolTip("Detected devices: " + ", ".join(names))
            except Exception:
                pass
        for i, idx in enumerate(available):
            label = f"Index {idx}"
            self.mac_cam_combo.addItem(label)
            self._client_cam_combo_map.append(idx)
        if not available:
            self.mac_cam_combo.addItem("No camera")
            self._client_cam_combo_map = []
        else:
            if select_index is None:
                select_index = self._client_cam_opened_index
            if select_index in self._client_cam_combo_map:
                self.mac_cam_combo.setCurrentIndex(self._client_cam_combo_map.index(select_index))
            else:
                self.mac_cam_combo.setCurrentIndex(0)
                # Ensure a working stream is opened by default
                try:
                    first_index = self._client_cam_combo_map[0]     # type: ignore[index], list index
                except Exception:
                    first_index = None
                if first_index is not None:         # 
                    self._open_client_camera_best(preferred_index=first_index)
        self.mac_cam_combo.blockSignals(False)

    def _on_mac_camera_changed(self, combo_index: int):
        if combo_index is None or combo_index < 0:
            return
        if combo_index >= len(self._client_cam_combo_map):
            return
        target_index = self._client_cam_combo_map[combo_index]
        if target_index == self._client_cam_opened_index and self.cap is not None and self.cap.isOpened():
            return
        # Switch to Mac camera mode when user selects a client camera
        self.use_dog_video = False
        self.update_status_ui()
        # Prefer selected index first
        self._client_cam_indices = [target_index] + [i for i in self._client_cam_indices if i != target_index]
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass
        self.cap = None
        if self._open_client_camera_best(preferred_index=target_index):
            self._log_client_cam(f"[SRC] Client camera selected (index {self._client_cam_opened_index}).")
            return
        self._client_cam_opened_index = None
        self._client_cam_next_try_ts = 0.0

    # ==================================================================
    # Post-completion bark + cheer helpers
    # ==================================================================
    def _set_mask_cheer(self, text: str, *, visible: bool):
        return self.mask_picker.set_mask_cheer(text, visible=visible)

    def _apply_mask_cheer_if_needed(self):
        return self.mask_picker.apply_mask_cheer_if_needed()

    def _start_barking(self):
        if self._bark_active:
            return
        self._bark_active = True
        try:
            self._bark_timer.start(int(self._bark_interval_ms))
        except Exception:
            self._bark_active = False

    def _stop_barking(self):
        self._bark_active = False
        try:
            if self._bark_timer.isActive():
                self._bark_timer.stop()
        except Exception:
            pass

    def _bark_tick(self):
        # Auto-stop barking if the completion conditions are no longer true.
        if not self._bark_should_run():
            self._stop_barking()
            # Hide the cheer banner as well to avoid confusing state.
            self._set_mask_cheer("", visible=False)
            return

        # Only bark when in Dog mode with a control link.
        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not getattr(self, "server_control_ok", False)
        ):
            return
        # Single beep + yellow flash
        try:
            self._beep_pattern(beeps=1, on_s=0.10, off_s=0.00)
        except Exception:
            pass

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
        """Barking should only run after FULL completion reaches OFF and we still have a ball lock."""
        try:
            mode = getattr(self.ball_tracker, "tracking_mode", None)
        except Exception:
            mode = None
        try:
            missed = int(getattr(self.ball_tracker, "missed_frames", 0) or 0)
        except Exception:
            missed = 0

        return bool(
            self.ball_mode_enabled
            and self.use_dog_video
            and self.dog_client is not None
            and getattr(self.dog_client, "tcp_flag", False)
            and getattr(self, "server_control_ok", False)
            and mode == TRACKING_MODE_FULL
            and bool(getattr(self, "_close_enough_latched", False))
            and str(getattr(self, "_close_enough_seq_state", "")) == "off"
            and missed == 0
        )

    def _on_mask_clear_cheer(self):
        return self.mask_picker.on_mask_clear_cheer()
    def _startup_initial_probe(self):
        """Decide initial mode and give the window a sane startup size."""
        try:
            self.setWindowTitle("mtDogMain v2.40 - Mac Client + Dog Pi (Dog commands only)")
        except Exception:
            pass

        # Ensure the video area is not squeezed into a thin strip on startup.
        try:
            self.setMinimumSize(1200, 900)
            self.resize(1500, 1000)
        except Exception:
            pass

        # Prefer Dog mode when both control and video ports are reachable.
        try:
            ok = (
                self.ping_ip(self.ip)
                and self.test_tcp_port(self.ip, self.control_port)
                and self.test_tcp_port(self.ip, self.video_port)
            )
        except Exception:
            ok = False

        if ok:
            print("[INIT] Dog Pi reachable at startup → DOG mode.")
            self.server_ip_ok = True
            self.server_control_ok = True
            self.server_video_ok = True
            self.dog_connected = True

            try:
                self.start_dog_client()
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

        # ---- Right-side panel ----
        self.ctrl_panel = QFrame()
        self.ctrl_panel.setObjectName("ctrlPanel")
        self.ctrl_panel.setFixedWidth(230)
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
        move_label = QLabel("Motion (W/E/R, S/D/F, C)")
        move_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(move_label)

        move_frame = QFrame()
        move_layout = QHBoxLayout()
        move_layout.setContentsMargins(0, 0, 0, 0)
        move_layout.setSpacing(6)

        def make_round_button(text: str, tooltip: str, color: str):
            btn = QPushButton(text)
            # Slightly larger buttons + smaller font prevents multi-line text overflow
            # on macOS/HiDPI which can look like "overlapped" buttons.
            btn.setFixedSize(60, 60)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color:{color};
                    color:#ffffff;
                    border:none;
                    border-radius:30px;
                    font-size:14px;
                    padding:2px;
                }}
                QPushButton:hover {{
                    background-color:#ffffff;
                    color:{color};
                }}
                """
            )
            btn.setToolTip(tooltip)
            return btn

        col1 = QVBoxLayout(); col1.setSpacing(4)
        col2 = QVBoxLayout(); col2.setSpacing(4)
        col3 = QVBoxLayout(); col3.setSpacing(4)

        self.btn_W = make_round_button("⟲\nW", "W: Turn Left", "#007bff")
        self.btn_E = make_round_button("↑\nE", "E: Move Forward", "#00aa55")
        self.btn_R = make_round_button("⟳\nR", "R: Turn Right", "#007bff")

        self.btn_S = make_round_button("←\nS", "S: Move Left", "#00aa88")
        self.btn_D = make_round_button("◎\nD", "D: Relax", "#666666")
        self.btn_F = make_round_button("→\nF", "F: Move Right", "#00aa88")

        self.btn_C = make_round_button("↓\nC", "C: Move Backward", "#00aa55")

        col1.addWidget(self.btn_W)
        col1.addWidget(self.btn_S)
        col1.addStretch()

        col2.addWidget(self.btn_E)
        col2.addWidget(self.btn_D)
        col2.addWidget(self.btn_C)

        col3.addWidget(self.btn_R)
        col3.addWidget(self.btn_F)
        col3.addStretch()

        move_layout.addLayout(col1)
        move_layout.addLayout(col2)
        move_layout.addLayout(col3)
        move_frame.setLayout(move_layout)
        panel_layout.addWidget(move_frame)

        panel_layout.addSpacing(8)

        # ---- Actions ----
        act_label = QLabel("Actions")
        act_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(act_label)

        def make_pill_button(text: str, tooltip: str, bg: str):
            btn = QPushButton(text)
            btn.setMinimumHeight(32)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color:{bg};
                    color:#ffffff;
                    border:none;
                    border-radius:16px;
                    padding:4px 10px;
                    font-size:14px;
                }}
                QPushButton:hover {{
                    background-color:#ffffff;
                    color:{bg};
                }}
                """
            )
            btn.setToolTip(tooltip)
            return btn

        # Row 1: Buzzer, LED, Calibration
        actions_frame1 = QFrame()
        actions_layout1 = QHBoxLayout()
        actions_layout1.setContentsMargins(0, 0, 0, 0)
        actions_layout1.setSpacing(8)

        self.btn_Beep = make_pill_button("🔔", "B: Buzzer beep", "#ffaa00")
        self.btn_LED = make_pill_button("LED\nL", "L: LED pattern", "#ff8800")
        self.btn_Calib = make_pill_button("Cal\nK", "K: Servo calibration", "#0099cc")

        actions_layout1.addWidget(self.btn_Beep)
        actions_layout1.addWidget(self.btn_LED)
        actions_layout1.addWidget(self.btn_Calib)
        actions_frame1.setLayout(actions_layout1)
        panel_layout.addWidget(actions_frame1)

        # Row 2: Ball (autonomous tracking) + Face
        actions_frame2 = QFrame()
        actions_layout2 = QHBoxLayout()
        actions_layout2.setContentsMargins(0, 0, 0, 0)
        actions_layout2.setSpacing(8)

        self.btn_Ball = make_pill_button(
            "Ball",
            "Autonomous tracking (moves dog) + Mask window",
            "#0066cc",
        )
        self.btn_Face = make_pill_button("Face", "Face tracking (future)", "#8844cc")

        actions_layout2.addWidget(self.btn_Ball)
        actions_layout2.addWidget(self.btn_Face)
        actions_frame2.setLayout(actions_layout2)
        panel_layout.addWidget(actions_frame2)

        # ---- Object Detection Test (NO dog movement) ----
        test_label = QLabel("Object Detection Test")
        test_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(test_label)

        test_frame = QFrame()
        test_frame.setStyleSheet("background-color:#0f151d; border:1px solid #233144; border-radius:10px;")
        test_layout = QVBoxLayout()
        test_layout.setContentsMargins(8, 8, 8, 8)
        test_layout.setSpacing(8)

        self.btn_CVBall = make_pill_button("CV Ball", "CV detector test (no motion)", "#00bcd4")
        self.btn_YoloVision = make_pill_button("Yolo Vision", "YOLO detector test (no motion)", "#2e7d32")
        self.btn_AIVision = make_pill_button("GPT Vision", "GPT detector test (no motion)", "#00a3a3")

        # Make them easier to tap and read in the narrow panel
        try:
            self.btn_CVBall.setMinimumHeight(36)
            self.btn_YoloVision.setMinimumHeight(36)
            self.btn_AIVision.setMinimumHeight(36)
        except Exception:
            pass

        test_layout.addWidget(self.btn_CVBall)
        test_layout.addWidget(self.btn_YoloVision)
        test_layout.addWidget(self.btn_AIVision)
        test_frame.setLayout(test_layout)
        panel_layout.addWidget(test_frame)

        panel_layout.addSpacing(8)

        # ---- Reserved space for future features ----
        reserved_label = QLabel("Future Controls")
        reserved_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(reserved_label)

        reserved_frame = QFrame()
        reserved_frame.setFixedHeight(120)
        reserved_frame.setStyleSheet("background-color:#0f151d; border:1px dashed #233144;")
        panel_layout.addWidget(reserved_frame)

        # ---- Body / head sliders placeholders (UI only) ----
        body_label = QLabel("Body / Head (placeholders)")
        body_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(body_label)

        slider_frame = QFrame()
        slider_layout = QVBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(4)

        def make_slider_row(caption: str):
            lbl = QLabel(caption)
            lbl.setStyleSheet("color:#cccccc; font-size:11px;")
            sl = QSlider(Qt.Horizontal)
            sl.setMinimum(0)
            sl.setMaximum(100)
            sl.setValue(50)
            sl.setEnabled(False)  # placeholder only
            row = QVBoxLayout()
            row.setSpacing(2)
            row.addWidget(lbl)
            row.addWidget(sl)
            return row, sl

        row_body, self.slider_body = make_slider_row("Body tilt")
        row_head, self.slider_head_angle = make_slider_row("Head angle")
        row_height, self.slider_body_height = make_slider_row("Body height")

        slider_layout.addLayout(row_body)
        slider_layout.addLayout(row_head)
        slider_layout.addLayout(row_height)

        slider_frame.setLayout(slider_layout)
        panel_layout.addWidget(slider_frame)

        panel_layout.addStretch()

        # ---- System row ----
        sys_label = QLabel("System (D: Relax, Q: Quit)")
        sys_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(sys_label)

        sys_frame = QFrame()
        sys_layout = QHBoxLayout()
        sys_layout.setContentsMargins(0, 0, 0, 0)
        sys_layout.setSpacing(8)

        self.btn_play = make_pill_button("Play", "P: Play pose sequence", "#777777")
        self.btn_quit = make_pill_button("Quit", "Q: Quit program", "#cc3333")

        sys_layout.addWidget(self.btn_play)
        sys_layout.addWidget(self.btn_quit)
        sys_frame.setLayout(sys_layout)
        panel_layout.addWidget(sys_frame)

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
        self.mac_cam_combo.setMinimumWidth(170)
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
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.video_label, stretch=1)
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

        self.btn_Beep.clicked.connect(self.handle_beep_key)
        self.btn_LED.clicked.connect(self.handle_led_button)
        self.btn_Calib.clicked.connect(self.handle_calib_button)
        self.btn_Ball.clicked.connect(self.handle_ball_button)
        self.btn_CVBall.clicked.connect(self.handle_cv_ball_button)
        self.btn_YoloVision.clicked.connect(self.handle_yolo_vision_button)
        self.btn_Face.clicked.connect(self.handle_face_button)
        self.btn_AIVision.clicked.connect(self.handle_ai_vision_button)

        self.btn_play.clicked.connect(self.handle_play_button)
        self.btn_quit.clicked.connect(self.handle_quit)


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
        if send_stop:
            return "Stop"
        if not key_char:
            return "Idle"
        key = str(key_char).lower()
        mapping = {
            "w": "Turn-L",
            "r": "Turn-R",
            "e": "Forward",
            "c": "Backward",
            "s": "Left",
            "f": "Right",
            "d": "Relax",
        }
        return mapping.get(key, key.upper())

    def _log_cmd(self, payload: str, *, tag: str = "CMD") -> None:
        try:
            msg = str(payload or "").strip()
            if not msg:
                return
            ts = datetime.now().strftime("%H:%M:%S")
            entry = f"{ts} {tag}: {msg}"
            try:
                self._cmd_history.append(entry)
            except Exception:
                pass
            _write_log(f"[{tag}] {msg}")
        except Exception:
            return

    def _send_relax_only(self):
        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not getattr(self, "server_control_ok", False)
        ):
            return
        try:
            self._send_cmd(COMMAND.CMD_RELAX + "\n", tag="RELAX")
        except Exception as e:
            print(f"[CMD] relax failed: {e}")

    def _send_stop_pwm_only(self):
        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not getattr(self, "server_control_ok", False)
        ):
            return
        try:
            self._send_cmd(COMMAND.CMD_STOP_PWM + "\n", tag="STOP_PWM")
        except Exception as e:
            print(f"[CMD] stop_pwm failed: {e}")

    def _trigger_close_enough_sequence(self, *, ball_diameter: float | None, frame_w: float):
        """One-shot completion: double beep + double green flash, then STOP+RELAX, then OFF after 5s."""
        if self._close_enough_latched:
            return
        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not getattr(self, "server_control_ok", False)
        ):
            return

        self._close_enough_latched = True
        self._close_enough_seq_state = "triggered"
        self._close_enough_seq_ts = time.time()

        # Audible + visible cue
        try:
            self._beep_pattern(beeps=2, on_s=0.12, off_s=0.12)
            self._led_flash(flashes=2, on_s=0.18, off_s=0.18, color=(0, 255, 0))
        except Exception:
            pass

        # Immediately stop and relax
        try:
            self.send_stop_motion()
        except Exception:
            pass
        try:
            self._send_relax_only()
            self._close_enough_seq_state = "relax"
        except Exception:
            pass

        # Cancel any previous pending OFF to avoid stacking timers.
        prev = getattr(self, "_close_enough_off_timer", None)
        try:
            if prev is not None and prev.is_alive():
                prev.cancel()
        except Exception:
            pass

        def _do_off():
            self._send_stop_pwm_only()
            self._close_enough_seq_state = "off"
            self._close_enough_seq_ts = time.time()
            # After OFF, start barking and show a cheer message in Mask window.
            if self.ball_mode_enabled:
                self._bark_pending_start = True
                self._set_mask_cheer(
                    "Ball located! FULL complete → STOP, RELAX, OFF.\n"
                    "Barking: 1 beep + yellow flash every 2s. Click Clear to stop.",
                    visible=True,
                )

        self._close_enough_off_timer = threading.Timer(5.0, _do_off)
        self._close_enough_off_timer.daemon = True
        self._close_enough_off_timer.start()
        try:
            print(
                f"[FULL] Close enough -> cue+STOP+RELAX then OFF in 5s "
                f"(diam={ball_diameter if ball_diameter is not None else 'NA'} thr={frame_w/4.0:.1f})"
            )
        except Exception:
            pass

    def _handle_tracking_mode_transition(self, mode): # NEW, called from update_frame
        if mode == self._last_tracking_mode:
            return

        self._last_tracking_mode = mode

        # Reset FULL head-lock one-shot when leaving/entering FULL mode.
        try:
            if mode != TRACKING_MODE_FULL:
                self._full_head_sent_once = False
        except Exception:
            pass

        # When switching into BODY tracking, keep the head neutral (90 deg).
        if mode == TRACKING_MODE_BODY:
            try:
                self.head_tracker.reset()
                neutral = int(round(getattr(self.head_tracker.cfg, "neutral_deg", 90)))
            except Exception:
                neutral = 90

            if (
                self.use_dog_video
                and self.dog_client is not None
                and getattr(self.dog_client, "tcp_flag", False)
            ):
                self.send_head_angle(neutral)

        if mode == TRACKING_MODE_FULL:
            try:
                self._full_head_sent_once = False
            except Exception:
                pass

    # ==================================================================
    # Head servo command helper
    # ==================================================================
    def send_head_angle(self, angle_deg: int):
        """
        Send a head-servo angle command to the Dog Pi.
        """
        if self.dog_client is None or not getattr(self.dog_client, "tcp_flag", False):
            return

        # Clamp angle to HeadTracker's safe range
        angle_deg = max(
            int(self.head_tracker.cfg.min_deg),
            min(int(self.head_tracker.cfg.max_deg), int(angle_deg))
        )

        # Use string command, not bytes
        cmd_str = f"{COMMAND.CMD_HEAD}#{angle_deg}\n"
        self._send_cmd(cmd_str, tag="HEAD")  # REMOVE .encode()
        print(f"[HEAD] CMD_HEAD → {angle_deg}° /r")     # send with /r to return to beginning of line, no line feed, minimize spawn messages

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
          W/E/R/S/D/F/C → motion
          Space → stop (CMD_MOVE_STOP)
          B → beep
          L → LED
          K → calib
          P → play
          Q → quit
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

        if key in ("w", "e", "r", "s", "d", "f", "c"):
            self.send_motion_command(key)
        elif key == "b":
            self.handle_beep_key()
        elif key == "l":
            self.handle_led_button()
        elif key == "k":
            self.handle_calib_button()
        elif key == "p":
            self.handle_play_button()
        elif key == "q":
            self.handle_quit()
        elif key == "t":
            self.handle_ball_button()
        else:
            super().keyPressEvent(event)

    def _update_full_body_tracking(self, ball_center, frame_shape):
        if self.ball_tracker.tracking_mode not in (TRACKING_MODE_FULL, TRACKING_MODE_BODY):
            return
        if ball_center is None or frame_shape is None:
            return
        # Pull tuning from BallTracker (updated by mask window sliders)
        try:
            self.body_tracking_interval = float(
                getattr(self.ball_tracker, "body_tracking_interval", self.body_tracking_interval)
            )
        except Exception:
            pass
        interval = max(0.05, min(5.0, float(self.body_tracking_interval)))

        try:
            deadzone_ratio = float(getattr(self.ball_tracker, "body_deadzone_ratio", 0.18))
        except Exception:
            deadzone_ratio = 0.18
        deadzone_ratio = max(0.05, min(0.50, deadzone_ratio))

        h = frame_shape[0]
        w = frame_shape[1] if len(frame_shape) > 1 else 0
        if h == 0 or w == 0:
            return

        now = time.time()

        center_x = w / 2.0
        center_y = h / 2.0
        x_off = ball_center[0] - center_x   # positive = ball is RIGHT of center
        y_off = ball_center[1] - center_y   # positive = ball is BELOW center

        # FULL tracking: forward-approach policy based on apparent ball size.
        # Keep moving toward the ball until its diameter exceeds 1/4 of screen width.
        # (When close enough, stop forward motion even if Y offset still suggests moving.)
        full_mode = self.ball_tracker.tracking_mode == TRACKING_MODE_FULL
        ball_radius = getattr(self.ball_tracker, "last_radius", None)
        try:
            ball_diameter = float(ball_radius) * 2.0 if ball_radius is not None else None
        except Exception:
            ball_diameter = None
        thr_hi = (w / 4.0) if w > 0 else 0.0
        try:
            clear_ratio = float(getattr(self.ball_tracker, "full_close_enough_clear_below_ratio", self._close_enough_clear_below_ratio))
        except Exception:
            clear_ratio = float(getattr(self, "_close_enough_clear_below_ratio", 0.85))
        clear_ratio = max(0.20, min(0.99, clear_ratio))
        thr_lo = thr_hi * clear_ratio

        # Extra "close enough" confirmation:
        # If the ball's bottom edge reaches the bottom of the frame, consider it close enough.
        # This covers cases where the ball is still small but physically very near.
        bottom_margin_px = 2.0
        try:
            bottom_edge_reached = bool(
                full_mode
                and ball_radius is not None
                and float(ball_center[1]) + float(ball_radius) >= (float(h) - bottom_margin_px)
            )
        except Exception:
            bottom_edge_reached = False

        close_enough_by_size = bool(full_mode and ball_diameter is not None and thr_hi > 0 and ball_diameter >= thr_hi)
        close_enough_hi = bool(close_enough_by_size or bottom_edge_reached)

        # Latch auto-clear uses hysteresis on size, but also requires the ball is no longer
        # touching the bottom edge.
        close_enough_lo = bool(
            full_mode
            and ball_diameter is not None
            and thr_lo > 0
            and ball_diameter < thr_lo
            and (not bottom_edge_reached)
        )
        close_enough = close_enough_hi

        # Publish for status overlay
        try:
            latched = bool(getattr(self, "_close_enough_latched", False)) if full_mode else False
            self._ball_close_enough = bool(close_enough_hi or latched)
        except Exception:
            pass

        # FULL-mode completion sequence when close enough.
        if full_mode and close_enough_hi:
            self._trigger_close_enough_sequence(ball_diameter=ball_diameter, frame_w=float(w))

        # If we've already completed/started the close-enough sequence, do not send further motion.
        # However, auto-clear the latch (with hysteresis + hold time) once the ball is no longer close.
        if full_mode and self._close_enough_latched:
            seq = str(getattr(self, "_close_enough_seq_state", "idle"))
            can_auto_clear = seq in ("off", "idle")

            # Hysteresis-based auto-reset to resolve the "unexpected Stop" latch.
            # Only allow clearing after the completion sequence reaches OFF/IDLE.
            if can_auto_clear and close_enough_lo:
                if float(getattr(self, "_close_enough_clear_start_ts", 0.0) or 0.0) <= 0.0:
                    self._close_enough_clear_start_ts = now
                hold_s = float(getattr(self, "_close_enough_clear_hold_s", 0.6) or 0.6)
                hold_s = max(0.0, min(5.0, hold_s))
                if (now - float(self._close_enough_clear_start_ts)) >= hold_s:
                    self._close_enough_latched = False
                    self._close_enough_clear_start_ts = 0.0
                    # Resume normal tracking immediately.
                    # (Do not send STOP here; the controller below will decide.)
                else:
                    pass
            else:
                self._close_enough_clear_start_ts = 0.0

            if self._close_enough_latched:
                # While the completion sequence is still in progress, keep the robot safe by
                # occasionally re-sending STOP (rate-limited). Once OFF (stop_pwm) is reached,
                # do not send STOP anymore and show cmd:Off in the HUD.
                show_cmd = "Stop"
                if seq == "off":
                    show_cmd = "Off"
                elif seq == "relax":
                    show_cmd = "Relax"

                if seq in ("triggered", "relax"):
                    try:
                        min_dt = float(getattr(self, "_close_enough_stop_min_interval_s", 0.8) or 0.8)
                    except Exception:
                        min_dt = 0.8
                    min_dt = max(0.2, min(5.0, min_dt))
                    if (now - float(getattr(self, "_close_enough_last_stop_ts", 0.0))) >= min_dt:
                        try:
                            self.send_stop_motion()
                        except Exception:
                            pass
                        self._close_enough_last_stop_ts = now

                try:
                    t0 = float(getattr(self, "_close_enough_seq_ts", 0.0) or 0.0)
                    dt = max(0.0, time.time() - t0) if t0 > 0 else 0.0
                    lines = [
                        f"TRACK:full axis:- cmd:{show_cmd}",
                        "GOAL:close_enough → completion (latched)",
                        f"SEQ:{seq} +{dt:.1f}s  reset:diam<thr_lo for {float(getattr(self, '_close_enough_clear_hold_s', 0.6) or 0.6):.1f}s",
                    ]
                    if seq == "off":
                        lines.insert(2, "POWER:off (stop_pwm)")
                    elif seq == "relax":
                        lines.insert(2, "SERVOS:relax (waiting for off)")
                    if ball_diameter is not None:
                        lines.append(
                            f"diam:{ball_diameter:.0f} thr_hi:{thr_hi:.0f} thr_lo:{thr_lo:.0f} bottom:{int(bool(bottom_edge_reached))} close:{int(bool(close_enough_hi))}"
                        )
                    self.ball_tracker.body_debug_lines = lines
                except Exception:
                    pass
                return
            try:
                self.send_stop_motion()
            except Exception:
                pass
            try:
                seq = str(getattr(self, "_close_enough_seq_state", "idle"))
                t0 = float(getattr(self, "_close_enough_seq_ts", 0.0) or 0.0)
                dt = max(0.0, time.time() - t0) if t0 > 0 else 0.0
                lines = [
                    "TRACK:full axis:- cmd:Stop",
                    f"GOAL:close_enough → Stop, Relax, Off (5s)",
                    f"SEQ:{seq} +{dt:.1f}s",
                ]
                if ball_diameter is not None:
                    lines.append(f"diam:{ball_diameter:.0f} thr:{(w/4.0):.0f} close:1")
                self.ball_tracker.body_debug_lines = lines
            except Exception:
                pass
            return

        try:
            body_kp = float(getattr(self.ball_tracker, "body_kp", 0.0))
        except Exception:
            body_kp = 0.0
        body_kp = max(0.0, min(5.0, body_kp))

        x_ctl = x_off
        y_ctl = y_off

        def _kp_speed(error_ctl: float, dead: float, span: float) -> int | None:
            """Map error magnitude to a motion speed (2..10) using Body-Kp.

            If body_kp==0, return None to keep the existing fixed-speed behavior.
            """
            if body_kp <= 0.0:
                return None
            mag = max(0.0, abs(float(error_ctl)) - float(dead))
            if mag <= 0.0:
                return None
            frac = mag / max(1.0, float(span))
            frac = max(0.0, min(1.0, frac))
            eff = max(0.0, min(1.0, body_kp * frac))
            min_speed = 2
            max_speed = 10
            return int(round(min_speed + (max_speed - min_speed) * eff))

        # Deadzone (tunable)
        x_dead = max(20.0, w * deadzone_ratio)
        y_dead = max(20.0, h * deadzone_ratio)

        # Hysteresis: enter further out, exit further in
        x_margin = max(8.0, x_dead * 0.25)
        y_margin = max(8.0, y_dead * 0.25)
        x_enter = x_dead + x_margin
        x_exit = max(0.0, x_dead - x_margin)
        y_enter = y_dead + y_margin
        y_exit = max(0.0, y_dead - y_margin)

        # Policy: do not move forward/back unless X is centered within tolerance.
        # Use the X deadzone as the centering tolerance.
        x_centered = abs(x_off) <= x_dead

        # Policy: in body tracking, optionally disallow backward motion.
        # Prefer the BallTracker setting (tunable/persisted via mask window).
        allow_backward = bool(
            getattr(
                self.ball_tracker,
                "body_allow_backward",
                getattr(self, "body_allow_backward", False),
            )
        )

        def sign_dir(v: float) -> int:
            return -1 if v < 0 else 1

        axis = self._body_hyst_axis
        direction = int(self._body_hyst_dir)
        command = None
        speed_override = None
        send_stop = False

        axis_before = axis

        if axis == "x":
            if abs(x_ctl) < x_exit:
                axis = None
                direction = 0
                send_stop = True
            else:
                new_dir = sign_dir(x_ctl)
                if new_dir != direction and abs(x_ctl) > x_enter:
                    direction = new_dir
                command = "w" if direction < 0 else "r"
                speed_override = _kp_speed(x_ctl, x_dead, (w / 2.0) - x_dead)
        elif axis == "y":
            # If X drifts out of tolerance, immediately switch to turn-to-center.
            if not x_centered:
                axis = "x"
                direction = sign_dir(x_ctl)
                command = "w" if direction < 0 else "r"

            if full_mode:
                # FULL mode: ignore Y-offset for approach; use ball size to decide forward/stop.
                if close_enough:
                    axis = None
                    direction = 0
                    send_stop = True
                else:
                    direction = 1
                    if x_centered:
                        command = "e"  # forward toward ball
                        # Speed based on how far we are from the size threshold.
                        if ball_diameter is not None:
                            approach_err = max(0.0, (w / 4.0) - ball_diameter)
                            speed_override = _kp_speed(approach_err, 0.0, (w / 4.0))
                    else:
                        command = None
            else:
                # BODY mode: original Y-offset based forward/back behavior.
                # Forward-only Y control when backward is disabled.
                if (not allow_backward) and (y_ctl < -y_enter):
                    axis = None
                    direction = 0
                    send_stop = True
                elif abs(y_ctl) < y_exit:
                    axis = None
                    direction = 0
                    send_stop = True
                else:
                    new_dir = sign_dir(y_ctl)
                    if new_dir != direction and abs(y_ctl) > y_enter:
                        direction = new_dir
                    # Only allow forward/back when X is centered.
                    if x_centered:
                        if allow_backward:
                            command = "c" if direction < 0 else "e"
                        else:
                            command = "e" if direction > 0 else None
                    else:
                        command = None
                    if command is not None:
                        speed_override = _kp_speed(y_ctl, y_dead, (h / 2.0) - y_dead)
        else:
            # Prefer X corrections (turn) over Y (forward/back)
            # Turn whenever X is outside the deadzone tolerance.
            if not x_centered:
                axis = "x"
                direction = sign_dir(x_ctl)
                command = "w" if direction < 0 else "r"
                speed_override = _kp_speed(x_ctl, x_dead, (w / 2.0) - x_dead)
            elif full_mode:
                # FULL mode: if centered and not close enough, keep approaching.
                if x_centered and not close_enough:
                    axis = "y"
                    direction = 1
                    command = "e"
                    if ball_diameter is not None:
                        approach_err = max(0.0, (w / 4.0) - ball_diameter)
                        speed_override = _kp_speed(approach_err, 0.0, (w / 4.0))
                else:
                    axis = None
                    direction = 0
                    send_stop = True
            elif (abs(y_ctl) > y_enter) if allow_backward else (y_ctl > y_enter):
                axis = "y"
                direction = sign_dir(y_ctl)
                # Only enter Y axis if X is centered.
                if x_centered:
                    if allow_backward:
                        command = "c" if direction < 0 else "e"
                    else:
                        command = "e" if direction > 0 else None
                else:
                    axis = "x"
                    direction = sign_dir(x_ctl)
                    command = "w" if direction < 0 else "r"
                if command is not None:
                    speed_override = _kp_speed(y_ctl, y_dead, (h / 2.0) - y_dead)

        self._body_hyst_axis = axis
        self._body_hyst_dir = direction

        # ---- Debug lines for Mask window ----
        # Stored on BallTracker (shared with BallMaskWindow) so you can see live
        # body decisions without reading the terminal.
        try:
            cmd_dbg = self._cmd_key_to_human(command, send_stop=bool(send_stop))
            mode_dbg = "full" if full_mode else "body"
            lines = [
                f"TRACK:{mode_dbg} axis:{axis or '-'} cmd:{cmd_dbg}",
                f"off=({x_off:+.0f},{y_off:+.0f}) dead=({x_dead:.0f},{y_dead:.0f})",
            ]
            if full_mode:
                if ball_diameter is not None:
                    lines.append(
                        f"diam:{ball_diameter:.0f} thr_hi:{thr_hi:.0f} thr_lo:{thr_lo:.0f} close:{int(bool(close_enough_hi))}"
                    )
                else:
                    lines.append(
                        f"diam:-- thr_hi:{thr_hi:.0f} thr_lo:{thr_lo:.0f} close:{int(bool(close_enough_hi))}"
                    )
            else:
                spd_dbg = speed_override if speed_override is not None else int(getattr(self, "move_speed", 8))
                lines.append(f"kp:{body_kp:.2f} spd:{int(spd_dbg)} x_ok:{int(bool(x_centered))}")
            self.ball_tracker.body_debug_lines = lines
        except Exception:
            pass

        axis_changed = axis_before != axis

        if send_stop:
            # Stop immediately once we re-enter the inner band.
            self.send_stop_motion()
            self.last_body_cmd_time = now
            try:
                self._body_cmd_name = ""
            except Exception:
                pass
            return

        # If we just switched axes (e.g., from Y to X), allow an immediate corrective command.
        can_send = axis_changed or ((now - self.last_body_cmd_time) >= interval)

        if command and can_send:
            print(
                f"[BODY] mode={self.ball_tracker.tracking_mode} axis={axis} cmd={command} "
                f"x_off={x_off:+.0f} y_off={y_off:+.0f} "
                f"kp={body_kp:.2f} "
                f"dead=({x_dead:.0f},{y_dead:.0f})"
            )
            self.send_motion_command(command, speed_override=speed_override)
            self.last_body_cmd_time = now
            try:
                self._body_cmd_name = self._cmd_key_to_human(command)
            except Exception:
                pass
        elif can_send and not command:
            try:
                self._body_cmd_name = ""
            except Exception:
                pass

    def _update_lost_ball_search(self, frame_shape):
        """When ball is lost, search by moving forward; avoid obstacles via SONIC.

        Policy:
          - If range <= near_cm: turn-left until range > clear_cm.
          - Otherwise: move forward slowly to search.
          - If telemetry (sonic) is stale: stop for safety.
        """
        t = self.ball_tracker
        if not (getattr(t, "search_forward_enabled", True) or getattr(t, "obstacle_avoid_enabled", True)):
            return

        # If FULL-mode completion sequence is active, do not keep searching.
        if bool(getattr(self, "_close_enough_latched", False)):
            return

        now = time.time()
        interval = float(getattr(t, "body_tracking_interval", 0.6))
        interval = max(0.20, min(2.00, interval))
        if (now - float(getattr(self, "_lost_search_last_cmd_ts", 0.0))) < interval:
            return

        # Require recent telemetry for obstacle logic; otherwise stop.
        telemetry_ok = bool(getattr(self, "telemetry_valid", False)) and (
            (now - float(getattr(self, "last_telemetry_ok_time", 0.0))) <= 2.0
        )
        if not telemetry_ok:
            if self._lost_search_state != "idle" or not self._lost_search_sent_stop:
                self.send_stop_motion()
                self._lost_search_sent_stop = True
            self._lost_search_state = "idle"
            try:
                self.ball_tracker.body_debug_lines = [
                    "SEARCH:idle (telemetry stale)",
                    f"missed:{int(getattr(t, 'missed_frames', 0))}",
                ]
            except Exception:
                pass
            self._lost_search_last_cmd_ts = now
            return

        dist = float(getattr(self, "distance_cm", 9999.0) or 9999.0)
        near_cm = float(getattr(t, "obstacle_near_cm", 10.0) or 10.0)
        clear_cm = float(getattr(t, "obstacle_clear_cm", 30.0) or 30.0)
        if clear_cm < near_cm:
            clear_cm = near_cm

        search_forward_enabled = bool(getattr(t, "search_forward_enabled", True))
        obstacle_avoid_enabled = bool(getattr(t, "obstacle_avoid_enabled", True))

        # If both toggles are off, treat as feature disabled.
        if (not search_forward_enabled) and (not obstacle_avoid_enabled):
            if not self._lost_search_sent_stop:
                self.send_stop_motion()
                self._lost_search_sent_stop = True
            self._lost_search_state = "idle"
            self._lost_search_phase = "scan"
            self._lost_search_phase_start_ts = 0.0
            try:
                self.ball_tracker.body_debug_lines = [
                    "SEARCH:off",
                    f"dist:{dist:.1f}cm near:{near_cm:.0f} clear:{clear_cm:.0f}",
                    f"missed:{int(getattr(t, 'missed_frames', 0))}",
                ]
            except Exception:
                pass
            self._lost_search_last_cmd_ts = now
            return

        want_escape = obstacle_avoid_enabled and (dist <= near_cm)

        # Search policy:
        # - If forward enabled: run a simple repeating pattern: scan-left 2s, forward 1s.
        # - If forward disabled: keep scanning (turn-left) only.
        preferred_state = "pattern" if search_forward_enabled else "scan"
        state = str(getattr(self, "_lost_search_state", "idle"))
        if state == "escape":
            if dist > clear_cm:
                state = preferred_state
                self.send_stop_motion()
                self._lost_search_sent_stop = True
                # After escaping, restart the search pattern from scan.
                self._lost_search_phase = "scan"
                self._lost_search_phase_start_ts = now
        else:
            state = "escape" if want_escape else preferred_state
            if state == "escape":
                self.send_stop_motion()
                self._lost_search_sent_stop = True
                # Pause/restart pattern timing while escaping.
                self._lost_search_phase = "scan"
                self._lost_search_phase_start_ts = now

        self._lost_search_state = state

        cmd = None
        speed_override = None
        if state == "escape":
            cmd = "w"  # always turn-left for escape
            speed_override = int(getattr(t, "obstacle_turn_speed", 4) or 4)
        elif state == "pattern":
            scan_s = 2.0
            forward_s = 1.0
            if float(getattr(self, "_lost_search_phase_start_ts", 0.0)) <= 0.0:
                self._lost_search_phase_start_ts = now
                self._lost_search_phase = "scan"

            phase = str(getattr(self, "_lost_search_phase", "scan"))
            phase_elapsed = max(0.0, now - float(getattr(self, "_lost_search_phase_start_ts", now)))
            phase_dur = scan_s if phase == "scan" else forward_s
            phase_switched = False
            if phase_elapsed >= phase_dur:
                phase = "forward" if phase == "scan" else "scan"
                self._lost_search_phase = phase
                self._lost_search_phase_start_ts = now
                phase_elapsed = 0.0
                phase_dur = scan_s if phase == "scan" else forward_s
                phase_switched = True

            if phase == "forward":
                cmd = "e"
                speed_override = int(getattr(t, "search_forward_speed", 4) or 4)
            else:
                cmd = "w"
                speed_override = int(getattr(t, "obstacle_turn_speed", 4) or 4)

            # If we just switched phase, send immediately (don’t wait for the interval gate).
            if phase_switched:
                self._lost_search_last_cmd_ts = 0.0

            # Export pattern info for UI
            pattern_line = f"PATTERN:{phase} {phase_elapsed:.1f}/{phase_dur:.1f}s (scan=2.0 fwd=1.0)"
        elif state == "scan":
            cmd = "w"  # turn-left to scan for the ball
            speed_override = int(getattr(t, "obstacle_turn_speed", 4) or 4)
            pattern_line = "PATTERN:scan-only"
        else:
            cmd = None
            pattern_line = ""

        if cmd is None:
            if not self._lost_search_sent_stop:
                self.send_stop_motion()
                self._lost_search_sent_stop = True
            try:
                self.ball_tracker.body_debug_lines = [
                    f"SEARCH:{state} (disabled)",
                    f"dist:{dist:.1f}cm near:{near_cm:.0f} clear:{clear_cm:.0f}",
                    f"missed:{int(getattr(t, 'missed_frames', 0))}",
                ]
            except Exception:
                pass
            self._lost_search_last_cmd_ts = now
            return

        # Send search motion
        self._lost_search_sent_stop = False
        self.send_motion_command(cmd, speed_override=speed_override)
        self._lost_search_last_cmd_ts = now

        try:
            cmd_name = self._cmd_key_to_human(cmd)
            lines = [
                f"SEARCH:{state} cmd:{cmd_name} spd:{int(speed_override) if speed_override is not None else int(getattr(self, 'move_speed', 8))}",
                f"dist:{dist:.1f}cm near:{near_cm:.0f} clear:{clear_cm:.0f}",
                f"missed:{int(getattr(t, 'missed_frames', 0))}",
            ]
            if pattern_line:
                lines.insert(1, pattern_line)
            self.ball_tracker.body_debug_lines = lines
        except Exception:
            pass

    # ------------------------------------------
    def handle_ball_button(self):
        return self.ui_events.handle_ball_button()

    # ------------------------------------------
    def _on_cv_debug_radial_gate_changed(self, checked: bool):
        """Toggle CV radial gate from CV debug window (experimental)."""
        return self.cv_ball.on_cv_debug_radial_gate_changed(checked)

    def handle_cv_ball_button(self):
        return self.ui_events.handle_cv_ball_button()

    # ------------------------------------------
    def handle_yolo_vision_button(self):
        return self.ui_events.handle_yolo_vision_button()

    # ------------------------------------------
    def handle_ai_vision_button(self):
        return self.ui_events.handle_ai_vision_button()


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
