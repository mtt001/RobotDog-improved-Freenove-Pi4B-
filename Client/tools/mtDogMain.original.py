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
from vision.legacy.mtBallDetectAI import AIVisionBallDetector
try:
    from vision.legacy.mtBallDetectYOLO import YOLOBallDetector
except Exception:
    YOLOBallDetector = None  # type: ignore
from controllers.dog_command_controller import COMMAND
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

from config.mtDogConfig import (
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


def _contrast_bgr_from_hsv(h: int, s: int, v: int) -> tuple[int, int, int]:
    try:
        h = int(h) % 180
        s = int(max(0, min(255, int(s))))
        v = int(max(0, min(255, int(v))))
        h_contrast = (h + 90) % 180
        s_contrast = max(160, 255 - s)
        v_contrast = max(170, 255 - v)
        hsv = np.uint8([[[h_contrast, s_contrast, v_contrast]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
        return int(bgr[0]), int(bgr[1]), int(bgr[2])
    except Exception:
        return (0, 255, 255)


def _draw_center_marker(img, cx: int, cy: int, bgr: tuple[int, int, int], *, alpha: float = 0.5):
    try:
        if img is None:
            return
        h, w = img.shape[:2]
        cx = max(0, min(w - 1, int(cx)))
        cy = max(0, min(h - 1, int(cy)))
        overlay = img.copy()
        cv2.drawMarker(
            overlay,
            (cx, cy),
            bgr,
            markerType=cv2.MARKER_CROSS,
            markerSize=10,
            thickness=1,
        )
        cv2.addWeighted(overlay, float(alpha), img, 1.0 - float(alpha), 0, img)
    except Exception:
        return


class AIVisionHistogramWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._mode_label = "GPT Vision"
        self._model_label = ""
        self._update_hz: float | None = None
        self.setWindowTitle("Object Detection Test — Histogram")
        self.resize(660, 360)
        try:
            self.setMinimumHeight(520)
            self.setMaximumHeight(520)
        except Exception:
            pass

        self.info_label = QLabel("No detection yet.")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#e6e6e6;")
        self.compare_status_line = ""

        self.hist_view = QLabel("")
        self.hist_view.setAlignment(Qt.AlignCenter)
        self.hist_view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.hist_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.contour_view = QLabel("")
        self.contour_view.setAlignment(Qt.AlignCenter)
        self.contour_view.setStyleSheet("background-color:#0b0b0b; color:#9aa6b2;")
        self.contour_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.contour_view.setScaledContents(True)

        self.method_label = QLabel("")
        self.method_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.method_label.setStyleSheet("color:#b0bac6;")
        self.method_label.setWordWrap(True)
        self.method_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.info_label)
        middle = QHBoxLayout()
        middle.addWidget(self.hist_view, stretch=2)
        middle.addWidget(self.contour_view, stretch=1)
        layout.addLayout(middle, stretch=1)
        layout.addWidget(self.method_label)
        self.setLayout(layout)

    def set_context(self, mode_label: str, model_label: str = "", update_hz: float | None = None):
        self._mode_label = str(mode_label or "").strip() or "Object Detection"
        self._model_label = str(model_label or "").strip()
        try:
            self._update_hz = None if update_hz is None else float(update_hz)
        except Exception:
            self._update_hz = None
        title = f"Histogram for Detected Object— {self._mode_label}"
        if self._model_label:
            title += f" ({self._model_label})"
        if self._update_hz is not None and self._update_hz > 0:
            title += f" @ {self._update_hz:.1f}Hz"
        try:
            self.setWindowTitle(title)
        except Exception:
            pass

    def update_histogram(self, frame_bgr, x, y, r, *, thresholds: dict | None = None, mask_combined=None, roi_rect=None):
        if frame_bgr is None:
            return
        h, w = frame_bgr.shape[:2]
        if w <= 1 or h <= 1:
            return

        x = int(max(0, min(w - 1, int(round(x)))))
        y = int(max(0, min(h - 1, int(round(y)))))

        r_draw = int(round(r)) if r is not None else 0
        if r_draw <= 0:
            r_draw = 6
        inner_ratio = 0.50
        pct_lo = 5.0
        pct_hi = 95.0
        sample_r = max(1, int(round(r_draw * inner_ratio)))
        sample_d = int(round(sample_r * 2))

        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            return

        try:
            Hc, Sc, Vc = [int(v) for v in hsv_img[y, x]]
        except Exception:
            Hc, Sc, Vc = 0, 0, 0

        diameter = int(round(2 * r_draw))

        contour_mask = None
        contour_area = 0.0
        contour_crop = None
        method_line = ""
        use_contour = False
        roi_crop_used = False
        try:
            if roi_rect is not None:
                x0, y0, x1, y1 = roi_rect
                x0 = int(max(0, min(w - 1, int(x0))))
                y0 = int(max(0, min(h - 1, int(y0))))
                x1 = int(max(0, min(w, int(x1))))
                y1 = int(max(0, min(h, int(y1))))
                if x1 > x0 and y1 > y0:
                    try:
                        contour_vis = frame_bgr.copy()
                        cv2.rectangle(contour_vis, (x0, y0), (x1, y1), (255, 255, 0), 1)
                        contour_crop = contour_vis[y0:y1, x0:x1]
                    except Exception:
                        contour_crop = frame_bgr[y0:y1, x0:x1]
                    roi_crop_used = True
            if mask_combined is not None:
                mask_src = mask_combined
                if len(mask_src.shape) == 3:
                    mask_src = cv2.cvtColor(mask_src, cv2.COLOR_BGR2GRAY)
                if mask_src.shape[:2] != (h, w):
                    mask_src = cv2.resize(mask_src, (w, h), interpolation=cv2.INTER_NEAREST)
                _, mask_bin = cv2.threshold(mask_src, 1, 255, cv2.THRESH_BINARY)
                cnts, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    cnt = max(cnts, key=cv2.contourArea)
                    contour_area = float(cv2.contourArea(cnt))
                    if contour_area > 0:
                        contour_mask = np.zeros((h, w), dtype=np.uint8)
                        cv2.drawContours(contour_mask, [cnt], -1, 255, -1)
                        method_line = f"Hist: HSV inside top-1 contour (area={int(contour_area)}px)"
                        use_contour = True
                        if not roi_crop_used:
                            contour_vis = frame_bgr.copy()
                            cv2.drawContours(contour_vis, [cnt], -1, (0, 255, 255), 1)
                            try:
                                (cx_c, cy_c), r_c = cv2.minEnclosingCircle(cnt)
                                rr_i = int(round(float(r_c)))
                                cx_i = int(round(float(cx_c)))
                                cy_i = int(round(float(cy_c)))
                                if rr_i > 3:
                                    r_in = int(max(2, round(rr_i * 0.78)))
                                    r_out = int(max(r_in + 2, round(rr_i * 1.18)))
                                    cv2.circle(contour_vis, (cx_i, cy_i), r_out, (255, 255, 0), 1)
                                    cv2.circle(contour_vis, (cx_i, cy_i), r_in, (0, 255, 0), 1)
                                    _draw_center_marker(
                                        contour_vis,
                                        cx_i,
                                        cy_i,
                                        _contrast_bgr_from_hsv(Hc, Sc, Vc),
                                        alpha=0.5,
                                    )
                            except Exception:
                                pass
                            x0, y0, ww, hh = cv2.boundingRect(cnt)
                            pad = max(6, int(round(0.1 * max(ww, hh))))
                            x1 = max(0, x0 - pad)
                            y1 = max(0, y0 - pad)
                            x2 = min(w, x0 + ww + pad)
                            y2 = min(h, y0 + hh + pad)
                            try:
                                cv2.rectangle(contour_vis, (x1, y1), (x2, y2), (255, 255, 0), 1)
                            except Exception:
                                pass
                            contour_crop = contour_vis[y1:y2, x1:x2]
        except Exception:
            pass

        if not use_contour:
            method_line = f"Hist: HSV inside inner circle (r={sample_r}px)"
            try:
                pad = max(8, int(round(0.25 * max(6, r_draw))))
                x1 = max(0, x - r_draw - pad)
                y1 = max(0, y - r_draw - pad)
                x2 = min(w, x + r_draw + pad)
                y2 = min(h, y + r_draw + pad)
                contour_vis = frame_bgr.copy()
                cv2.circle(contour_vis, (x, y), max(2, r_draw), (0, 255, 255), 1)
                cv2.circle(contour_vis, (x, y), max(2, sample_r), (0, 255, 0), 1)
                try:
                    cv2.rectangle(contour_vis, (x1, y1), (x2, y2), (255, 255, 0), 1)
                except Exception:
                    pass
                _draw_center_marker(contour_vis, x, y, _contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
                contour_crop = contour_vis[y1:y2, x1:x2]
            except Exception:
                contour_crop = None

        mask_for_hist = contour_mask
        if mask_for_hist is None:
            mask_for_hist = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(mask_for_hist, (x, y), sample_r, 255, -1)

        # Sample HSV values within the chosen histogram ROI
        pts = hsv_img[mask_for_hist > 0]
        if pts is not None and len(pts) > 0:
            h_vals = pts[:, 0].astype(np.float32)
            s_vals = pts[:, 1].astype(np.float32)
            v_vals = pts[:, 2].astype(np.float32)
            h_lo, h_hi = np.percentile(h_vals, [pct_lo, pct_hi])
            s_lo, s_hi = np.percentile(s_vals, [pct_lo, pct_hi])
            v_lo, v_hi = np.percentile(v_vals, [pct_lo, pct_hi])
            try:
                Hc = int(round(float(np.median(h_vals))))
                Sc = int(round(float(np.median(s_vals))))
                Vc = int(round(float(np.median(v_vals))))
            except Exception:
                pass
        else:
            h_lo = h_hi = s_lo = s_hi = v_lo = v_hi = 0.0

        thr_text = ""
        try:
            if isinstance(thresholds, dict) and thresholds:
                parts = []
                if "a_thr" in thresholds:
                    parts.append(f"a>={int(thresholds.get('a_thr', 0))}")
                if "s_min" in thresholds:
                    parts.append(f"S>={int(thresholds.get('s_min', 0))}")
                if "v_min" in thresholds:
                    parts.append(f"V>={int(thresholds.get('v_min', 0))}")
                if parts:
                    thr_text = " | thr:" + ",".join(parts)
        except Exception:
            thr_text = ""

        roi_label = f"Contour A{int(contour_area)}px" if use_contour else f"Inner circle r{sample_r}px"

        self.info_label.setText(
            f"{self._mode_label}"
            + (f" [{self._model_label}]" if self._model_label else "")
            + (f" @ {self._update_hz:.1f}Hz" if (self._update_hz is not None and self._update_hz > 0) else "")
            + " | "
            + roi_label + ", "
            f"HSV({Hc},{Sc},{Vc}) @ ({x},{y}) | "
            f"H[{int(round(h_lo))}-{int(round(h_hi))}] "
            f"S[{int(round(s_lo))}-{int(round(s_hi))}] "
            f"V[{int(round(v_lo))}-{int(round(v_hi))}]"
            + thr_text
        )

        try:
            legend = "Overlay: contour (yellow) + estimated circle (yellow) + half-radius circle (green) + center"
            self.method_label.setText(method_line + "\n" + legend)
        except Exception:
            pass

        hist_h = cv2.calcHist([hsv_img], [0], mask_for_hist, [180], [0, 180])
        hist_s = cv2.calcHist([hsv_img], [1], mask_for_hist, [256], [0, 256])
        hist_v = cv2.calcHist([hsv_img], [2], mask_for_hist, [256], [0, 256])

        width = 256
        band_h = 70
        gap = 10
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
                y_val = int(round(v * (band_h - 8)))
                cv2.line(
                    hist_img,
                    (x_bin, y0 + band_h - 1),
                    (x_bin, y0 + band_h - 1 - y_val),
                    color,
                    1,
                )

        def draw_marker(x_px, y0, color):
            x_px = int(max(0, min(width - 1, x_px)))
            y_base = y0 + band_h - 2
            tri = np.array(
                [
                    [x_px, y_base],
                    [max(0, x_px - 4), y_base - 6],
                    [min(width - 1, x_px + 4), y_base - 6],
                ],
                dtype=np.int32,
            )
            cv2.fillConvexPoly(hist_img, tri, color)

        def draw_thr_line(x_px, y0, color):
            x_px = int(max(0, min(width - 1, x_px)))
            y_top = y0 + 2
            y_bot = y0 + band_h - 3
            cv2.line(hist_img, (x_px, y_top), (x_px, y_bot), color, 1)
            cv2.circle(hist_img, (x_px, y_top + 1), 2, color, -1)

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

        # Draw inner-ROI percentile markers (triangles) at p5/p95
        h_lo_x = int(round((h_lo / 179.0) * (width - 1))) if 179 > 0 else 0
        h_hi_x = int(round((h_hi / 179.0) * (width - 1))) if 179 > 0 else 0
        s_lo_x = int(round((s_lo / 255.0) * (width - 1))) if 255 > 0 else 0
        s_hi_x = int(round((s_hi / 255.0) * (width - 1))) if 255 > 0 else 0
        v_lo_x = int(round((v_lo / 255.0) * (width - 1))) if 255 > 0 else 0
        v_hi_x = int(round((v_hi / 255.0) * (width - 1))) if 255 > 0 else 0

        draw_marker(h_lo_x, 0, (255, 255, 255))
        draw_marker(h_hi_x, 0, (0, 255, 255))
        draw_marker(s_lo_x, band_h + gap, (255, 255, 255))
        draw_marker(s_hi_x, band_h + gap, (0, 255, 255))
        draw_marker(v_lo_x, (band_h + gap) * 2, (255, 255, 255))
        draw_marker(v_hi_x, (band_h + gap) * 2, (0, 255, 255))

        # Optional threshold markers (e.g., CV Ball S/V minimums)
        try:
            if isinstance(thresholds, dict) and thresholds:
                if "s_min" in thresholds:
                    s_thr = float(thresholds.get("s_min", 0.0) or 0.0)
                    s_thr_x = int(round((s_thr / 255.0) * (width - 1))) if 255 > 0 else 0
                    draw_thr_line(s_thr_x, band_h + gap, (0, 165, 255))
                if "v_min" in thresholds:
                    v_thr = float(thresholds.get("v_min", 0.0) or 0.0)
                    v_thr_x = int(round((v_thr / 255.0) * (width - 1))) if 255 > 0 else 0
                    draw_thr_line(v_thr_x, (band_h + gap) * 2, (0, 165, 255))
        except Exception:
            pass

        cv2.putText(hist_img, "H", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(hist_img, "S", (6, band_h + gap + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(hist_img, "V", (6, (band_h + gap) * 2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)

        hist_rgb = cv2.cvtColor(hist_img, cv2.COLOR_BGR2RGB)
        qimg = QImage(hist_rgb.data, width, img_h, 3 * width, QImage.Format_RGB888)
        self.hist_view.setPixmap(QPixmap.fromImage(qimg))

        if contour_crop is not None and contour_crop.size > 0:
            try:
                try:
                    if contour_mask is not None and roi_rect is not None:
                        x0, y0, x1, y1 = roi_rect
                        x0 = int(max(0, min(w - 1, int(x0))))
                        y0 = int(max(0, min(h - 1, int(y0))))
                        x1 = int(max(0, min(w, int(x1))))
                        y1 = int(max(0, min(h, int(y1))))
                        if x1 > x0 and y1 > y0:
                            mask_crop = contour_mask[y0:y1, x0:x1]
                            if mask_crop is not None and mask_crop.size > 0:
                                cnts, _ = cv2.findContours(mask_crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                                if cnts:
                                    cv2.drawContours(contour_crop, cnts, -1, (0, 255, 255), 1)
                                    try:
                                        c_big = max(cnts, key=cv2.contourArea)
                                        (ccx, ccy), cr = cv2.minEnclosingCircle(c_big)
                                        ccx_i = int(round(ccx))
                                        ccy_i = int(round(ccy))
                                        cr_i = int(round(cr))
                                        if cr_i > 1:
                                            cv2.circle(contour_crop, (ccx_i, ccy_i), cr_i, (0, 255, 255), 1)
                                            cv2.circle(contour_crop, (ccx_i, ccy_i), max(1, int(round(cr_i * 0.5))), (0, 255, 0), 1)
                                        _draw_center_marker(
                                            contour_crop,
                                            ccx_i,
                                            ccy_i,
                                            _contrast_bgr_from_hsv(Hc, Sc, Vc),
                                            alpha=0.5,
                                        )
                                    except Exception:
                                        pass
                except Exception:
                    pass
                contour_rgb = cv2.cvtColor(contour_crop, cv2.COLOR_BGR2RGB)
                cqimg = QImage(
                    contour_rgb.data,
                    contour_rgb.shape[1],
                    contour_rgb.shape[0],
                    contour_rgb.strides[0],
                    QImage.Format_RGB888,
                ).copy()
                pix = QPixmap.fromImage(cqimg)
                try:
                    target_size = self.contour_view.size()
                    if target_size.width() > 0 and target_size.height() > 0:
                        pix = pix.scaled(target_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                except Exception:
                    pass
                self.contour_view.setPixmap(pix)
            except Exception:
                try:
                    self.contour_view.clear()
                except Exception:
                    pass
        else:
            try:
                self.contour_view.clear()
            except Exception:
                pass

    def clear_view(self, *, mode_label: str | None = None):
        try:
            self.hist_view.clear()
        except Exception:
            pass
        try:
            self.contour_view.clear()
        except Exception:
            pass
        try:
            self.info_label.setText("No detection yet.")
        except Exception:
            pass
        try:
            self.method_label.setText("")
        except Exception:
            pass
        if mode_label is not None:
            self.set_context(str(mode_label or "Object Detection"), "", update_hz=self._update_hz)


class CVBallDebugWindow(QWidget):
    def __init__(self, *, radial_checked: bool = False, on_radial_toggle=None):
        super().__init__()
        self.setWindowTitle("CV Ball debug")
        self.resize(760, 620)
        self._on_radial_toggle = on_radial_toggle

        self.chk_radial_gate = QCheckBox("RadialGate (CV)")
        self.chk_radial_gate.setChecked(bool(radial_checked))
        self.chk_radial_gate.setStyleSheet("color:#e6e6e6;")
        try:
            self.chk_radial_gate.toggled.connect(self._handle_radial_toggle)
        except Exception:
            pass

        self.info_label = QLabel("No detection yet.")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_label.setStyleSheet("color:#e6e6e6;")
        self.info_label.setWordWrap(True)
        self.info_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.info_label.setFixedHeight(320)

        self.view = QLabel("")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setScaledContents(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.chk_radial_gate, alignment=Qt.AlignLeft)
        layout.addWidget(self.view, stretch=1)
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def _handle_radial_toggle(self, checked: bool):
        try:
            if callable(self._on_radial_toggle):
                self._on_radial_toggle(bool(checked))
        except Exception:
            return

    def set_radial_gate_checked(self, checked: bool):
        try:
            self.chk_radial_gate.blockSignals(True)
            self.chk_radial_gate.setChecked(bool(checked))
        finally:
            try:
                self.chk_radial_gate.blockSignals(False)
            except Exception:
                pass

    def update_view(self, frame_bgr, mask, center, radius, missed_frames: int, debug_text: str = ""):
        try:
            mf = int(missed_frames)
        except Exception:
            mf = 0

        head = ""
        if center is None:
            head = f"CV Ball: none | missed:{mf}"
        else:
            try:
                cx, cy = int(center[0]), int(center[1])
            except Exception:
                cx, cy = 0, 0
            try:
                rr = int(round(float(radius or 0.0)))
            except Exception:
                rr = 0
            dpx = int(round(2 * rr)) if rr > 0 else 0
            head = f"CV Ball: ({cx},{cy}) D{dpx}px | missed:{mf}"

        if debug_text:
            text = str(debug_text)
            if "<span" in text or "<br" in text:
                try:
                    self.info_label.setTextFormat(Qt.RichText)
                except Exception:
                    pass
                if "<br" not in text:
                    text = text.replace("\n", "<br>")
                head_html = (
                    str(head)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                self.info_label.setText(head_html + "<br>" + text)
            else:
                try:
                    self.info_label.setTextFormat(Qt.PlainText)
                except Exception:
                    pass
                self.info_label.setText(head + "\n" + text)
        else:
            try:
                self.info_label.setTextFormat(Qt.PlainText)
            except Exception:
                pass
            self.info_label.setText(head)

        vis = None
        if mask is not None:
            try:
                if len(mask.shape) == 2:
                    vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                else:
                    vis = mask.copy()
            except Exception:
                vis = None

        if vis is None and frame_bgr is not None:
            try:
                vis = frame_bgr.copy()
            except Exception:
                vis = None

        if vis is None:
            return

        try:
            h, w = vis.shape[:2]
            if center is not None:
                cx, cy = int(round(float(center[0]))), int(round(float(center[1])))
                rr = int(round(float(radius or 0.0)))
                cx = max(0, min(w - 1, cx))
                cy = max(0, min(h - 1, cy))
                if rr > 0:
                    cv2.circle(vis, (cx, cy), rr, (0, 255, 255), 1)
                try:
                    if frame_bgr is not None:
                        hsv_src = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
                        Hc, Sc, Vc = [int(v) for v in hsv_src[cy, cx]]
                    else:
                        Hc, Sc, Vc = 0, 0, 0
                except Exception:
                    Hc, Sc, Vc = 0, 0, 0
                _draw_center_marker(vis, cx, cy, _contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
        except Exception:
            pass

        try:
            rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            self.view.setPixmap(QPixmap.fromImage(qimg))
        except Exception:
            return


class CVBallHistogramWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV Ball — Histograms")
        self.resize(900, 520)

        self.info_label = QLabel("Histogram panels")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#cfd6e4;")

        self.grid = QGridLayout()
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(6)

        self.panel_labels: list[QLabel] = []
        self.panel_titles: list[QLabel] = []
        for i in range(4):
            title = QLabel("Panel")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color:#b7c0ce;")
            view = QLabel("")
            view.setAlignment(Qt.AlignCenter)
            view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.panel_titles.append(title)
            self.panel_labels.append(view)

        for idx in range(4):
            r = 0 if idx < 2 else 2
            c = 0 if idx % 2 == 0 else 1
            self.grid.addWidget(self.panel_titles[idx], r, c)
            self.grid.addWidget(self.panel_labels[idx], r + 1, c)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.info_label)
        layout.addLayout(self.grid, stretch=1)
        self.setLayout(layout)

        # Rolling hist buffers (last 64 frames)
        self.picker_hist_h = deque(maxlen=64)
        self.picker_hist_s = deque(maxlen=64)
        self.picker_hist_v = deque(maxlen=64)
        self.frame_hist_h = deque(maxlen=64)
        self.frame_hist_s = deque(maxlen=64)
        self.frame_hist_v = deque(maxlen=64)
        self.picker_hist_updates = 0
        self.frame_hist_updates = 0

    def _render_hist_from_arrays(self, hist_h, hist_s, hist_v, *, thresholds: dict | None = None, label_text: str = ""):
        if hist_h is None or hist_s is None or hist_v is None:
            return None

        try:
            hist_h = np.asarray(hist_h, dtype=np.float32).flatten()
            hist_s = np.asarray(hist_s, dtype=np.float32).flatten()
            hist_v = np.asarray(hist_v, dtype=np.float32).flatten()
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
            if hist.size <= 0:
                return
            maxv = float(hist.max()) if hist.size > 0 else 1.0
            maxv = max(maxv, 1.0)
            for i in range(bins):
                v = float(hist[i]) / maxv
                x_bin = int(round(i * (width - 1) / (bins - 1)))
                y_val = int(round(v * (band_h - 6)))
                cv2.line(
                    hist_img,
                    (x_bin, y0 + band_h - 1),
                    (x_bin, y0 + band_h - 1 - y_val),
                    color,
                    1,
                )

        def draw_thr_line(x_px, y0, color):
            x_px = int(max(0, min(width - 1, x_px)))
            y_top = y0 + 2
            y_bot = y0 + band_h - 3
            cv2.line(hist_img, (x_px, y_top), (x_px, y_bot), color, 1)
            cv2.circle(hist_img, (x_px, y_top + 1), 2, color, -1)

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

        try:
            if isinstance(thresholds, dict) and thresholds:
                if "s_min" in thresholds:
                    s_thr = float(thresholds.get("s_min", 0.0) or 0.0)
                    s_thr_x = int(round((s_thr / 255.0) * (width - 1))) if 255 > 0 else 0
                    draw_thr_line(s_thr_x, band_h + gap, (0, 165, 255))
                if "v_min" in thresholds:
                    v_thr = float(thresholds.get("v_min", 0.0) or 0.0)
                    v_thr_x = int(round((v_thr / 255.0) * (width - 1))) if 255 > 0 else 0
                    draw_thr_line(v_thr_x, (band_h + gap) * 2, (0, 165, 255))
        except Exception:
            pass

        cv2.putText(hist_img, "H", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(hist_img, "S", (6, band_h + gap + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(hist_img, "V", (6, (band_h + gap) * 2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)

        if label_text:
            cv2.putText(hist_img, label_text, (90, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return hist_img

    def _render_hist(self, hsv_img, mask, *, thresholds: dict | None = None, label_text: str = ""):
        if hsv_img is None or mask is None:
            return None
        try:
            hist_h = cv2.calcHist([hsv_img], [0], mask, [180], [0, 180])
            hist_s = cv2.calcHist([hsv_img], [1], mask, [256], [0, 256])
            hist_v = cv2.calcHist([hsv_img], [2], mask, [256], [0, 256])
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

        def draw_thr_line(x_px, y0, color):
            x_px = int(max(0, min(width - 1, x_px)))
            y_top = y0 + 2
            y_bot = y0 + band_h - 3
            cv2.line(hist_img, (x_px, y_top), (x_px, y_bot), color, 1)
            cv2.circle(hist_img, (x_px, y_top + 1), 2, color, -1)

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

        try:
            if isinstance(thresholds, dict) and thresholds:
                if "s_min" in thresholds:
                    s_thr = float(thresholds.get("s_min", 0.0) or 0.0)
                    s_thr_x = int(round((s_thr / 255.0) * (width - 1))) if 255 > 0 else 0
                    draw_thr_line(s_thr_x, band_h + gap, (0, 165, 255))
                if "v_min" in thresholds:
                    v_thr = float(thresholds.get("v_min", 0.0) or 0.0)
                    v_thr_x = int(round((v_thr / 255.0) * (width - 1))) if 255 > 0 else 0
                    draw_thr_line(v_thr_x, (band_h + gap) * 2, (0, 165, 255))
        except Exception:
            pass

        cv2.putText(hist_img, "H", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(hist_img, "S", (6, band_h + gap + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(hist_img, "V", (6, (band_h + gap) * 2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)

        if label_text:
            cv2.putText(hist_img, label_text, (90, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return hist_img

    def update_panels(self, frame_bgr, picker_point, ranked_masks, *, thresholds: dict | None = None, mode_label: str = ""):
        if frame_bgr is None:
            return

        h, w = frame_bgr.shape[:2]
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            return

        # Panel 1: picker or whole frame (rolling last 64 frames)
        if picker_point is not None:
            px, py = int(picker_point[0]), int(picker_point[1])
            px = max(0, min(w - 1, px))
            py = max(0, min(h - 1, py))
            try:
                ph, ps, pv = [int(v) for v in hsv_img[py, px]]
                self.picker_hist_h.append(ph)
                self.picker_hist_s.append(ps)
                self.picker_hist_v.append(pv)
            except Exception:
                pass

            self.picker_hist_updates += 1
            title0 = f"Picker Histogram (1x1), rolling 64 frames  # {self.picker_hist_updates}"
            label0 = f"Picker @ ({px},{py})"

            if len(self.picker_hist_h) > 0:
                hist_h = np.bincount(np.asarray(self.picker_hist_h, dtype=np.uint8), minlength=180)
                hist_s = np.bincount(np.asarray(self.picker_hist_s, dtype=np.uint8), minlength=256)
                hist_v = np.bincount(np.asarray(self.picker_hist_v, dtype=np.uint8), minlength=256)
            else:
                hist_h = hist_s = hist_v = None
        else:
            try:
                fh = cv2.calcHist([hsv_img], [0], None, [180], [0, 180]).flatten()
                fs = cv2.calcHist([hsv_img], [1], None, [256], [0, 256]).flatten()
                fv = cv2.calcHist([hsv_img], [2], None, [256], [0, 256]).flatten()
                self.frame_hist_h.append(fh)
                self.frame_hist_s.append(fs)
                self.frame_hist_v.append(fv)
                self.frame_hist_updates += 1
            except Exception:
                pass

            title0 = f"Whole Frame Histogram ({w}x{h}), rolling 64 frames  # {self.frame_hist_updates}"
            label0 = "Whole Frame (rolling 64)"

            if len(self.frame_hist_h) > 0:
                hist_h = np.sum(np.asarray(self.frame_hist_h), axis=0)
                hist_s = np.sum(np.asarray(self.frame_hist_s), axis=0)
                hist_v = np.sum(np.asarray(self.frame_hist_v), axis=0)
            else:
                hist_h = hist_s = hist_v = None

        hist0 = self._render_hist_from_arrays(hist_h, hist_s, hist_v, thresholds=thresholds, label_text=label0)
        if hist0 is not None:
            rgb0 = cv2.cvtColor(hist0, cv2.COLOR_BGR2RGB)
            qimg0 = QImage(rgb0.data, rgb0.shape[1], rgb0.shape[0], rgb0.strides[0], QImage.Format_RGB888)
            self.panel_labels[0].setPixmap(QPixmap.fromImage(qimg0))
        self.panel_titles[0].setText(title0)

        # Panels 2-4: ranked contour masks
        for idx in range(3):
            pane = idx + 1
            title = f"Rank #{idx + 1} Contour"
            label = "No contour"
            mask_r = None
            try:
                if ranked_masks is not None and len(ranked_masks) > idx:
                    item = ranked_masks[idx]
                    mask_r = item.get("mask", None)
                    area = int(item.get("area", 0) or 0)
                    v_med = int(round(float(item.get("v_med", 0.0) or 0.0)))
                    label = f"A{area}px Vmed{v_med}"
            except Exception:
                mask_r = None

            if mask_r is not None and getattr(mask_r, "size", 0) > 0:
                hist_r = self._render_hist(hsv_img, mask_r, thresholds=thresholds, label_text=label)
                if hist_r is not None:
                    rgb_r = cv2.cvtColor(hist_r, cv2.COLOR_BGR2RGB)
                    qimg_r = QImage(rgb_r.data, rgb_r.shape[1], rgb_r.shape[0], rgb_r.strides[0], QImage.Format_RGB888)
                    self.panel_labels[pane].setPixmap(QPixmap.fromImage(qimg_r))
            else:
                self.panel_labels[pane].clear()

            self.panel_titles[pane].setText(title)

        try:
            self.info_label.setText(f"CV Ball Histograms — {mode_label}" if mode_label else "CV Ball Histograms")
        except Exception:
            pass


class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.on_mouse_event = None  # (type, pos, button/buttons)

    def mousePressEvent(self, event):
        if self.on_mouse_event:
            self.on_mouse_event("press", event.pos(), event.button())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.on_mouse_event:
            # For move, we care about buttons state usually
            self.on_mouse_event("move", event.pos(), event.buttons())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.on_mouse_event:
            self.on_mouse_event("release", event.pos(), event.button())
        super().mouseReleaseEvent(event)


class YoloVisionDebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yolo Vision debug")
        self.resize(760, 560)
        self.on_key_event = None  # Callback for manual labeling keys

        self.info_label = QLabel("No detection yet.")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#e6e6e6;")

        # Live YOLO controls (conf/imgsz)
        self.yolo_conf_spin = QDoubleSpinBox()
        self.yolo_conf_spin.setDecimals(3)
        self.yolo_conf_spin.setRange(0.001, 0.90)
        self.yolo_conf_spin.setSingleStep(0.005)
        self.yolo_conf_spin.setToolTip("YOLO confidence threshold (lower catches more, may add false positives)")

        self.yolo_imgsz_spin = QSpinBox()
        self.yolo_imgsz_spin.setRange(320, 1280)
        self.yolo_imgsz_spin.setSingleStep(32)
        self.yolo_imgsz_spin.setToolTip("YOLO input size (bigger can detect small objects but slower)")

        self.yolo_model_combo = QComboBox()
        self.yolo_model_combo.addItem("best.pt (default)", userData="best")
        self.yolo_model_combo.addItem("yolov8n.pt", userData="orig")
        self.yolo_model_combo.setToolTip("Select YOLO weights used for detection")

        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setCheckable(True)
        self.compare_btn.setToolTip("Toggle side-by-side YOLO compare window")
        self.compare_btn.setStyleSheet(
            """
            QPushButton { background-color:#37474f; color:#ffffff; border:none; border-radius:14px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background-color:#ffffff; color:#37474f; }
            QPushButton:checked { background-color:#26c6da; color:#0b1f22; }
            """
        )

        self.train_btn = QPushButton("Ball Trainning")
        self.train_btn.setCheckable(True)
        self.train_btn.setToolTip("Toggle YOLO Ball Training dataset capture")
        self.train_btn.setStyleSheet(
            """
            QPushButton { background-color:#6a1b9a; color:#ffffff; border:none; border-radius:14px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background-color:#ffffff; color:#6a1b9a; }
            QPushButton:checked { background-color:#00c853; color:#10221b; }
            """
        )

        self.label_btn = QPushButton("Labeling")
        self.label_btn.setCheckable(True)
        self.label_btn.setToolTip("Toggle Manual Labeling (Draw boxes, Enter to save, Space to abort)")
        self.label_btn.setStyleSheet(
            """
            QPushButton { background-color:#bf360c; color:#ffffff; border:none; border-radius:14px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background-color:#ffffff; color:#bf360c; }
            QPushButton:checked { background-color:#ff5722; color:#ffffff; }
            """
        )

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(6)
        ctrl_layout.addWidget(QLabel("conf"))
        ctrl_layout.addWidget(self.yolo_conf_spin)
        ctrl_layout.addWidget(QLabel("imgsz"))
        ctrl_layout.addWidget(self.yolo_imgsz_spin)
        ctrl_layout.addWidget(QLabel("model"))
        ctrl_layout.addWidget(self.yolo_model_combo)
        self.label_class_combo = QComboBox()
        self.label_class_combo.setToolTip("Manual labeling class")
        ctrl_layout.addWidget(QLabel("class"))
        ctrl_layout.addWidget(self.label_class_combo)
        ctrl_layout.addWidget(self.compare_btn)
        ctrl_layout.addWidget(self.train_btn)
        ctrl_layout.addWidget(self.label_btn)
        ctrl_layout.addStretch()

        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        top_layout.addWidget(self.info_label)
        top_layout.addLayout(ctrl_layout)

        # Main view + right-side full-frame histogram
        self.view = ClickableLabel("")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setScaledContents(False)  # Important for coordinate mapping

        self.full_hist_label = QLabel("")
        self.full_hist_label.setAlignment(Qt.AlignCenter)
        self.full_hist_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.full_hist_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.full_hist_label.setScaledContents(False)

        full_hist_title = QLabel("Frame HSV Histogram")
        full_hist_title.setAlignment(Qt.AlignCenter)
        full_hist_title.setStyleSheet("color:#b7c0ce; font-size:11px;")

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_layout.addWidget(full_hist_title)
        right_layout.addWidget(self.full_hist_label, stretch=1)

        # Bottom panes: hi/lo confidence images + histograms
        self.hi_img_label = QLabel("")
        self.hi_img_label.setAlignment(Qt.AlignCenter)
        self.hi_img_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.hi_img_label.setScaledContents(False)
        self.hi_img_label.setMinimumHeight(160)

        self.hi_hist_label = QLabel("")
        self.hi_hist_label.setAlignment(Qt.AlignCenter)
        self.hi_hist_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.hi_hist_label.setScaledContents(False)
        self.hi_hist_label.setMinimumHeight(160)

        self.lo_img_label = QLabel("")
        self.lo_img_label.setAlignment(Qt.AlignCenter)
        self.lo_img_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.lo_img_label.setScaledContents(False)
        self.lo_img_label.setMinimumHeight(160)

        self.lo_hist_label = QLabel("")
        self.lo_hist_label.setAlignment(Qt.AlignCenter)
        self.lo_hist_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.lo_hist_label.setScaledContents(False)
        self.lo_hist_label.setMinimumHeight(160)

        self.hi_title = QLabel("Highest Conf")
        self.hi_title.setAlignment(Qt.AlignCenter)
        self.hi_title.setStyleSheet("color:#b7c0ce; font-size:11px;")
        self.lo_title = QLabel("Lowest Conf")
        self.lo_title.setAlignment(Qt.AlignCenter)
        self.lo_title.setStyleSheet("color:#b7c0ce; font-size:11px;")

        hi_row = QHBoxLayout()
        hi_row.setContentsMargins(0, 0, 0, 0)
        hi_row.setSpacing(6)
        hi_row.addWidget(self.hi_img_label, stretch=1)
        hi_row.addWidget(self.hi_hist_label, stretch=1)

        lo_row = QHBoxLayout()
        lo_row.setContentsMargins(0, 0, 0, 0)
        lo_row.setSpacing(6)
        lo_row.addWidget(self.lo_img_label, stretch=1)
        lo_row.addWidget(self.lo_hist_label, stretch=1)

        hi_col = QVBoxLayout()
        hi_col.setContentsMargins(0, 0, 0, 0)
        hi_col.setSpacing(4)
        hi_col.addWidget(self.hi_title)
        hi_col.addLayout(hi_row)

        lo_col = QVBoxLayout()
        lo_col.setContentsMargins(0, 0, 0, 0)
        lo_col.setSpacing(4)
        lo_col.addWidget(self.lo_title)
        lo_col.addLayout(lo_row)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)
        bottom_layout.addLayout(hi_col)
        bottom_layout.addLayout(lo_col)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.addWidget(self.view, stretch=2)
        top_row.addLayout(right_layout, stretch=1)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        content_layout.addLayout(top_row, stretch=2)
        content_layout.addLayout(bottom_layout, stretch=2)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(top_layout)
        layout.addLayout(content_layout, stretch=1)
        self.setLayout(layout)

        self._controls_connected = False
        self._model_connected = False
        self._compare_connected = False
        self._label_class_connected = False

    def keyPressEvent(self, event):
        if self.on_key_event:
            self.on_key_event(event)
        super().keyPressEvent(event)

    def bind_labeling_toggle(self, on_toggle):
        try:
            self.label_btn.toggled.disconnect()
        except Exception:
            pass

    def bind_labeling_classes(self, class_names: list[str], on_change):
        try:
            self.label_class_combo.blockSignals(True)
            self.label_class_combo.clear()
            for idx, name in enumerate(class_names or []):
                label = f"{idx}:{name}"
                self.label_class_combo.addItem(label, userData=idx)
            if self.label_class_combo.count() > 0:
                self.label_class_combo.setCurrentIndex(0)
        except Exception:
            pass
        finally:
            try:
                self.label_class_combo.blockSignals(False)
            except Exception:
                pass
        if not self._label_class_connected:
            try:
                if callable(on_change):
                    try:
                        self.label_class_combo.currentIndexChanged[int].connect(on_change)
                    except Exception:
                        self.label_class_combo.currentIndexChanged.connect(on_change)
                self._label_class_connected = True
            except Exception:
                pass

    def set_labeling_class_index(self, idx: int):
        try:
            self.label_class_combo.blockSignals(True)
            if 0 <= int(idx) < self.label_class_combo.count():
                self.label_class_combo.setCurrentIndex(int(idx))
        except Exception:
            pass
        finally:
            try:
                self.label_class_combo.blockSignals(False)
            except Exception:
                pass

    def set_labeling_checked(self, checked: bool):
        try:
            self.label_btn.blockSignals(True)
            self.label_btn.setChecked(bool(checked))
        finally:
            try:
                self.label_btn.blockSignals(False)
            except Exception:
                pass

    def bind_training_toggle(self, on_toggle):
        try:
            self.train_btn.toggled.disconnect()
        except Exception:
            pass
        try:
            if callable(on_toggle):
                self.train_btn.toggled.connect(on_toggle)
        except Exception:
            pass

    def set_training_checked(self, checked: bool):
        try:
            self.train_btn.blockSignals(True)
            self.train_btn.setChecked(bool(checked))
        finally:
            try:
                self.train_btn.blockSignals(False)
            except Exception:
                pass

    def bind_model_selector(self, selected: str, on_change):
        try:
            self.yolo_model_combo.blockSignals(True)
            idx = 0
            if str(selected).lower() == "orig":
                idx = 1
            self.yolo_model_combo.setCurrentIndex(idx)
        except Exception:
            pass
        finally:
            try:
                self.yolo_model_combo.blockSignals(False)
            except Exception:
                pass
        if not self._model_connected:
            try:
                if callable(on_change):
                    try:
                        self.yolo_model_combo.currentIndexChanged[int].connect(on_change)
                    except Exception:
                        self.yolo_model_combo.currentIndexChanged.connect(on_change)
                self._model_connected = True
            except Exception:
                pass

    def bind_compare_toggle(self, on_toggle):
        try:
            self.compare_btn.toggled.disconnect()
        except Exception:
            pass
        try:
            if callable(on_toggle):
                self.compare_btn.toggled.connect(on_toggle)
        except Exception:
            pass

    def set_compare_checked(self, checked: bool):
        try:
            self.compare_btn.blockSignals(True)
            self.compare_btn.setChecked(bool(checked))
        finally:
            try:
                self.compare_btn.blockSignals(False)
            except Exception:
                pass


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
        self.cv_ball_enabled = False
        # CV Ball test-mode update rate (Hz-limited so UI stays smooth)
        # NOTE: Keep this fairly low so overlay matches what the user sees.
        self.cv_ball_interval_s = 1.0   # in seconds ,  1 Hz , ## default 0.25 Sec (4 Hz)
        # Hide CV overlay quickly when the last accepted detection is stale
        # (e.g., ball occluded between detector ticks).
        self.cv_ball_overlay_ttl_s = 0.35  # in seconds ,  0.35 Sec , Explain: hide overlay if no detection within this time 
        self._cv_ball_last_ts = 0.0
        self._cv_ball_last_mask = None
        self._cv_ball_last_hist_mask = None
        self._cv_update_count = 0
        self._cv_detect_count = 0
        self.ball_mask_window: BallMaskWindow | None = None

        # ---------- AI Vision (test module) ----------
        self.ai_vision_enabled = False
        self.ai_detector = AIVisionBallDetector()
        self.ai_detect_interval_s = 1.0
        self._ai_last_ts = 0.0
        self._ai_detections = []
        self._ai_request_sent = False
        self._ai_beep_last_ts = 0.0
        # Trial mode: one click -> one API call (no continuous polling)
        self.ai_one_shot_mode = True
        self._ai_one_shot_pending = False

        # YOLO detector (local inference) used by "Yolo Vision" mode.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.yolo_model_best_path = os.path.join(base_dir, "runs", "detect", "train5", "weights", "best.pt")
        self.yolo_model_orig_path = os.path.join(base_dir, "yolov8n.pt")
        self.yolo_model_choice = "best" if os.path.isfile(self.yolo_model_best_path) else "orig"
        self.yolo_detector_best = (
            YOLOBallDetector(model_path=self.yolo_model_best_path, ball_class_id=0) if YOLOBallDetector is not None else None
        )
        self.yolo_detector_orig = (
            YOLOBallDetector(model_path=self.yolo_model_orig_path, ball_class_id=32) if YOLOBallDetector is not None else None
        )
        self.yolo_detector = self.yolo_detector_best if self.yolo_model_choice == "best" else self.yolo_detector_orig
        self._yolo_detections = []
        self._yolo_last_error_msg = ""
        self._yolo_last_latency_s = 0.0
        self._yolo_last_hit_ts = 0.0
        self._yolo_last_hit_conf = 0.0
        self._yolo_last_hit_box = None  # (x1, y1, x2, y2, cx, cy, label, cls)
        self._yolo_last_hit_count = 0
        self._yolo_last_frame_shape = None  # (h, w)
        self._yolo_probe_last_ts = 0.0
        self._yolo_probe_interval_s = 2.0
        self._yolo_probe_conf = 0.001
        self._yolo_probe_boxes = []
        self._yolo_probe_error_msg = ""
        self._yolo_probe_latency_s = 0.0
        self._yolo_hi_conf = None
        self._yolo_lo_conf = None
        self._yolo_hi_snap = None
        self._yolo_lo_snap = None
        self._yolo_hi_center = None
        self._yolo_lo_center = None

        # YOLO compare (best vs original)
        self.yolo_compare_enabled = False
        self.yolo_compare_window: YoloCompareWindow | None = None
        self._yolo_compare_detections_best = []
        self._yolo_compare_detections_orig = []

        # YOLO Vision (ball source) - separate from GPT snapshot compare
        self.yolo_vision_enabled = False
        self.yolo_vision_interval_s = 1.0
        self._yolo_vision_last_ts = 0.0
        self._yolo_update_count = 0

        # YOLO Ball Training (dataset capture)
        self.yolo_training_enabled = False
        self.yolo_training_target = 1000
        self.yolo_training_count = 0
        self._yolo_training_dataset_label = ""
        self._yolo_training_dir = None
        self._yolo_training_next_index = 1
        self._yolo_training_conf_values = []
        self._yolo_training_easy = 0
        self._yolo_training_med = 0
        self._yolo_training_hard = 0
        self._yolo_training_recent_boxes = deque(maxlen=3)
        self._yolo_training_last_prompt_ts = 0.0
        self._yolo_training_prompt_idx = 0
        self._yolo_training_interval_default = float(self.yolo_vision_interval_s or 1.0)
        self._yolo_training_status_msg = ""
        self._yolo_training_prompt_msgs = [
            "Change ball position (edges/corners)",
            "Vary distance: close / mid / far",
            "Change lighting: bright / dim / backlight",
            "Try reflective floor / cluttered background",
            "Add partial occlusion / motion blur",
        ]
        self.yolo_train_hist_window: YoloTrainHistogramWindow | None = None

        # YOLO Manual Labeling
        self.yolo_labeling_enabled = False
        self._yolo_labeling_p1 = None       # (x, y) starting point
        self._yolo_labeling_p2 = None       # (x, y) current/end point
        self._yolo_labeling_drawing = False # Is currently dragging?
        self._yolo_labeling_class_names = ["ball", "dog_Maji", "dog_Salad"]
        self._yolo_labeling_class_id = 0    # Default to 'ball'
        self._yolo_labeling_last_frame = None
        self._yolo_labeling_msg = ""
        self._yolo_labeling_save_msg_ts = 0.0

        # Shared histogram window update rate for Object Detection Test modes
        self.test_hist_interval_s = 1.0
        self._test_hist_last_ts = 0.0
        self._test_hist_last_mode = ""
        self._test_hist_seq = 0
        self._gpt_snapshot_count = 0

        # Always-on CV histogram window
        self.cv_hist_interval_s = 0.5
        self._cv_hist_last_ts = 0.0
        self.cv_hist_window: CVBallHistogramWindow | None = None
        self._cv_ball_last_ranked_masks = []
        self._cv_ball_last_roi_rect = None
        self._cv_hist_positioned = False

        # Status message to show on the Color window (e.g. filtered/rejected)
        self._ai_status_msg = ""
        self._ai_status_ts = 0.0
        # AI post-filtering (reduce false positives)
        self.ai_score_min = 0.25
        self.ai_hsv_filter_enabled = False
        # Accept orange/red-ish hues in OpenCV HSV (0-179) - wider range
        self.ai_hue_ranges = [(0, 40), (150, 179)]
        self.ai_min_s = 25  # Lower saturation threshold
        self.ai_min_v = 25  # Lower value threshold
        self.ai_hist_window: AIVisionHistogramWindow | None = None
        self.cv_debug_window: CVBallDebugWindow | None = None
        self.yolo_debug_window: YoloVisionDebugWindow | None = None

        # Auto-calibrate HSV from AI detection (for mask-based tracking)
        self.ai_auto_hsv_enabled = True
        self.ai_auto_hsv_applied = False
        self.ai_auto_hsv_percentile_lo = 15
        self.ai_auto_hsv_percentile_hi = 85
        self.ai_auto_hsv_margin_h = 8
        self.ai_auto_hsv_margin_s = 20
        self.ai_auto_hsv_margin_v = 20
        self.ai_auto_hsv_inner_ratio = 0.6

        # Refine AI circle using HSV mask (reduce radius gap)
        self.ai_refine_enabled = True
        self.ai_refine_roi_scale = 1.2
        self.ai_refine_min_area_ratio = 0.01

        # Hover info for main color window (like Mask window)
        self.hover_xy_color = None       # (x, y) under mouse in image coords
        self.hover_hsv_color = None      # (H, S, V) at hover point

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
        self._cheer_text = str(text or "")
        self._cheer_visible = bool(visible)
        self._cheer_pending_apply = True

    def _apply_mask_cheer_if_needed(self):
        if not bool(getattr(self, "_cheer_pending_apply", False)):
            return
        try:
            if self.ball_mask_window is None:
                return
            self.ball_mask_window.set_cheer(self._cheer_text, visible=self._cheer_visible)
            self._cheer_pending_apply = False
        except Exception:
            pass

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

    def _disable_ai_vision_due_to_error(self, reason: str):
        self.ai_vision_enabled = False
        self._ai_detections = []
        self._ai_request_sent = False
        self._ai_one_shot_pending = False
        self.ai_auto_hsv_applied = False
        self._ai_last_error_msg = str(reason or "AI error").strip()
        self._ai_status_msg = ""
        self._ai_status_ts = 0.0
        self._yolo_detections = []
        self._yolo_last_error_msg = ""
        print(f"[GPT][ERR] GPT Vision stopped: {self._ai_last_error_msg}")
        # Button style → teal (OFF)
        try:
            self.btn_AIVision.setStyleSheet(
                """
                QPushButton {
                    background-color:#00a3a3;
                    color:#ffffff;
                    border:none;
                    border-radius:16px;
                    padding:4px 10px;
                    font-size:14px;
                }
                QPushButton:hover {
                    background-color:#ffffff;
                    color:#00a3a3;
                }
                """
            )
        except Exception:
            pass

    def _draw_ai_detections(self, frame_bgr, detections):
        if frame_bgr is None or not detections:
            return
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            hsv_img = None

        h, w = frame_bgr.shape[:2]
        for det in detections:
            try:
                if isinstance(det, dict):
                    x_val = det.get("x", 0)
                    y_val = det.get("y", 0)
                    r_val = det.get("r", 0)
                else:
                    x_val = getattr(det, "x", 0)
                    y_val = getattr(det, "y", 0)
                    r_val = getattr(det, "r", 0)
                x_f = float(x_val)
                y_f = float(y_val)
                r_f = float(r_val)
                if 0 < x_f <= 1.0 and 0 < y_f <= 1.0 and w > 1 and h > 1:
                    x_f *= w
                    y_f *= h
                if 0 < r_f <= 1.0 and min(w, h) > 1:
                    r_f *= min(w, h)
                x = int(round(x_f))
                y = int(round(y_f))
                r = int(round(r_f))
            except Exception:
                continue
            x = max(0, min(w - 1, x))
            y = max(0, min(h - 1, y))
            r_draw = r
            d_text = None
            if r <= 0:
                r_draw = 6
                d_text = "D?"
            r_draw = max(1, min(max(w, h), r_draw))
            if d_text is None:
                d_text = f"D{int(round(2 * r_draw))}"

            # Yellow circle + center dot
            cv2.circle(frame_bgr, (x, y), int(r_draw), (0, 255, 255), 2)
            cv2.circle(frame_bgr, (x, y), 2, (0, 255, 255), -1)
            # Histogram sampling region (smaller circle)
            sample_r = max(3, int(round(r_draw / 2)))
            cv2.circle(frame_bgr, (x, y), int(sample_r), (255, 0, 255), 1)

            H = S = V = 0
            if hsv_img is not None:
                try:
                    H, S, V = [int(v) for v in hsv_img[y, x]]
                except Exception:
                    H, S, V = 0, 0, 0

            tx = min(w - 1, x + 10)
            ty = max(15, y - 10)
            text1 = f"{d_text}px, ({x},{y})"
            text2 = f"HSV({H},{S},{V})"
            ai_hsv = None
            try:
                if isinstance(det, dict):
                    ai_hsv = det.get("hsv", None)
                else:
                    ai_hsv = getattr(det, "hsv", None)
            except Exception:
                ai_hsv = None
            if isinstance(ai_hsv, (list, tuple)) and len(ai_hsv) >= 3:
                try:
                    ah, as_, av = int(ai_hsv[0]), int(ai_hsv[1]), int(ai_hsv[2])
                    text2 = f"HSV({H},{S},{V}) AI({ah},{as_},{av})"
                except Exception:
                    pass
            try:
                score_val = det.get("score", 0.0) if isinstance(det, dict) else getattr(det, "score", 0.0)
                score_f = float(score_val)
            except Exception:
                score_f = 0.0
            latency_s = float(getattr(self.ai_detector, "last_latency_s", 0.0) or 0.0)
            text3 = f"score {int(round(score_f * 100))}"
            text4 = f"latency {latency_s:.1f}s" if latency_s > 0 else "latency --.-s"
            cv2.putText(frame_bgr, text1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, text1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            cv2.putText(frame_bgr, text2, (tx, ty + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, text2, (tx, ty + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            cv2.putText(frame_bgr, text3, (tx, ty + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, text3, (tx, ty + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            cv2.putText(frame_bgr, text4, (tx, ty + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, text4, (tx, ty + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    def _draw_yolo_detections(self, frame_bgr, detections):
        if frame_bgr is None or not detections:
            return
        h, w = frame_bgr.shape[:2]
        hsv_img = None
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            hsv_img = None
        for det in detections:
            try:
                x1 = int(round(float(getattr(det, "x1", 0))))
                y1 = int(round(float(getattr(det, "y1", 0))))
                x2 = int(round(float(getattr(det, "x2", 0))))
                y2 = int(round(float(getattr(det, "y2", 0))))
                conf = float(getattr(det, "conf", 0.0))
                label = str(getattr(det, "label", "ball") or "ball")
            except Exception:
                continue
            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))
            if x2 <= x1 or y2 <= y1:
                continue

            color = (0, 255, 0)  # green bbox for YOLO
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 1)
            txt = f"YOLO {label} {int(round(conf * 100))}%"
            ty = max(15, y1 - 6)
            tx = max(0, min(w - 1, x1 + 2))
            cv2.putText(frame_bgr, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(frame_bgr, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Center dot + coords
            cx = int(round((x1 + x2) / 2.0))
            cy = int(round((y1 + y2) / 2.0))
            cx = max(0, min(w - 1, cx))
            cy = max(0, min(h - 1, cy))
            try:
                if hsv_img is not None:
                    Hc, Sc, Vc = [int(v) for v in hsv_img[cy, cx]]
                else:
                    Hc, Sc, Vc = 0, 0, 0
            except Exception:
                Hc, Sc, Vc = 0, 0, 0
            _draw_center_marker(frame_bgr, cx, cy, _contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
            c_txt = f"({cx},{cy})"
            c_ty = min(h - 5, ty + 16)
            c_tx = max(0, min(w - 1, x1 + 2))
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    def _draw_yolo_probe_boxes(self, frame_bgr, detections):
        if frame_bgr is None or not detections:
            return
        h, w = frame_bgr.shape[:2]
        hsv_img = None
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            hsv_img = None
        for det in detections:
            try:
                x1 = int(round(float(getattr(det, "x1", 0))))
                y1 = int(round(float(getattr(det, "y1", 0))))
                x2 = int(round(float(getattr(det, "x2", 0))))
                y2 = int(round(float(getattr(det, "y2", 0))))
                conf = float(getattr(det, "conf", 0.0))
                label = str(getattr(det, "label", "cls") or "cls")
                cls_id = int(getattr(det, "cls", -1) or -1)
            except Exception:
                continue
            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))
            if x2 <= x1 or y2 <= y1:
                continue

            color = (255, 140, 0)  # orange probe bbox
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 1)
            txt = f"PROBE {label} cls{cls_id} {int(round(conf * 100))}%"
            ty = max(15, y1 - 6)
            tx = max(0, min(w - 1, x1 + 2))
            cv2.putText(frame_bgr, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            cx = int(round((x1 + x2) / 2.0))
            cy = int(round((y1 + y2) / 2.0))
            cx = max(0, min(w - 1, cx))
            cy = max(0, min(h - 1, cy))
            try:
                if hsv_img is not None:
                    Hc, Sc, Vc = [int(v) for v in hsv_img[cy, cx]]
                else:
                    Hc, Sc, Vc = 0, 0, 0
            except Exception:
                Hc, Sc, Vc = 0, 0, 0
            _draw_center_marker(frame_bgr, cx, cy, _contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
            c_txt = f"({cx},{cy})"
            c_ty = min(h - 5, ty + 16)
            c_tx = max(0, min(w - 1, x1 + 2))
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)

    def _draw_labeling_overlay(self, vis):
        if vis is None:
            return
        h, w = vis.shape[:2]
        
        # Status
        msg = str(self._yolo_labeling_msg or "")
        if msg:
            cv2.putText(vis, msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Save flash
        if time.time() - self._yolo_labeling_save_msg_ts < 2.0:
             cv2.putText(vis, "SAVED!", (w - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Box
        if self._yolo_labeling_p1 and self._yolo_labeling_p2:
            x1, y1 = self._yolo_labeling_p1
            x2, y2 = self._yolo_labeling_p2
            
            cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 255, 0), 2) # Cyan
            
            bw = abs(x2 - x1)
            bh = abs(y2 - y1)
            txt = f"{bw}x{bh}"
            cv2.putText(vis, txt, (int(min(x1, x2)), int(min(y1, y2)) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

    def _update_yolo_debug_view(self, frame_bgr):
        try:
            if self.yolo_debug_window is None or not self.yolo_debug_window.isVisible():
                return
        except Exception:
            return

        vis = None
        if frame_bgr is not None:
             # Manual Labeling Capture
            if self.yolo_labeling_enabled:
                 try:
                     self._yolo_labeling_last_frame = frame_bgr.copy()
                 except Exception:
                     pass

            try:
                vis = frame_bgr.copy()
                if getattr(vis, "size", 0) > 0 and self._yolo_detections:
                    self._draw_yolo_detections(vis, self._yolo_detections)
                elif getattr(vis, "size", 0) > 0 and self._yolo_probe_boxes:
                    self._draw_yolo_probe_boxes(vis, self._yolo_probe_boxes)
                
                if self.yolo_labeling_enabled:
                     self._draw_labeling_overlay(vis)

            except Exception:
                vis = frame_bgr

        full_hist = None
        hi_img = hi_hist = None
        lo_img = lo_hist = None
        try:
            if frame_bgr is not None and self.yolo_debug_window is not None:
                full_hist = self.yolo_debug_window._render_hsv_hist(frame_bgr, label_text="frame")
        except Exception:
            full_hist = None

        def _crop_box(src, box, pad: int = 6):
            if src is None or box is None:
                return None
            try:
                h0, w0 = src.shape[:2]
                x1 = int(round(float(getattr(box, "x1", 0.0))))
                y1 = int(round(float(getattr(box, "y1", 0.0))))
                x2 = int(round(float(getattr(box, "x2", 0.0))))
                y2 = int(round(float(getattr(box, "y2", 0.0))))
                x1 = max(0, min(w0 - 1, x1 - pad))
                y1 = max(0, min(h0 - 1, y1 - pad))
                x2 = max(0, min(w0, x2 + pad))
                y2 = max(0, min(h0, y2 + pad))
                if x2 <= x1 or y2 <= y1:
                    return None
                return src[y1:y2, x1:x2].copy()
            except Exception:
                return None

        try:
            if frame_bgr is not None and self._yolo_detections and self.yolo_debug_window is not None:
                hi_box = self._yolo_detections[0]
                lo_box = self._yolo_detections[-1]
                hi_img = _crop_box(frame_bgr, hi_box)
                lo_img = _crop_box(frame_bgr, lo_box)
                try:
                    hi_conf_now = float(getattr(hi_box, "conf", 0.0) or 0.0)
                    lo_conf_now = float(getattr(lo_box, "conf", 0.0) or 0.0)
                except Exception:
                    hi_conf_now = 0.0
                    lo_conf_now = 0.0
                if hi_img is not None and (self._yolo_hi_conf is None or hi_conf_now >= float(self._yolo_hi_conf or 0.0)):
                    self._yolo_hi_conf = hi_conf_now
                    self._yolo_hi_snap = hi_img
                    try:
                        self._yolo_hi_center = (
                            int(round(float(getattr(hi_box, "cx", 0.0)))),
                            int(round(float(getattr(hi_box, "cy", 0.0)))),
                        )
                    except Exception:
                        self._yolo_hi_center = None
                if lo_img is not None and (self._yolo_lo_conf is None or lo_conf_now <= float(self._yolo_lo_conf or 0.0)):
                    self._yolo_lo_conf = lo_conf_now
                    self._yolo_lo_snap = lo_img
                    try:
                        self._yolo_lo_center = (
                            int(round(float(getattr(lo_box, "cx", 0.0)))),
                            int(round(float(getattr(lo_box, "cy", 0.0)))),
                        )
                    except Exception:
                        self._yolo_lo_center = None
        except Exception:
            pass

        try:
            if self.yolo_debug_window is not None:
                hi_img = self._yolo_hi_snap
                lo_img = self._yolo_lo_snap
                if hi_img is not None:
                    hi_hist = self.yolo_debug_window._render_hsv_hist(hi_img, label_text="hi")
                else:
                    hi_hist = None
                if lo_img is not None:
                    lo_hist = self.yolo_debug_window._render_hsv_hist(lo_img, label_text="lo")
                else:
                    lo_hist = None
        except Exception:
            pass

        try:
            y_int = float(getattr(self, "yolo_vision_interval_s", 1.0) or 1.0)
        except Exception:
            y_int = 1.0
        y_hz = (1.0 / y_int) if y_int > 0 else 0.0
        try:
            y_n = int(getattr(self, "_yolo_update_count", 0) or 0)
        except Exception:
            y_n = 0
        det_n = len(getattr(self, "_yolo_detections", []) or [])
        err = str(getattr(self, "_yolo_last_error_msg", "") or "").strip()

        lat_s = float(getattr(self, "_yolo_last_latency_s", 0.0) or 0.0)
        lat_ms = lat_s * 1000.0 if lat_s > 0 else 0.0

        conf_th = None
        imgsz = None
        ball_cls = None
        model_path = ""
        try:
            if self.yolo_detector is not None:
                conf_th = getattr(self.yolo_detector, "conf", None)
                imgsz = getattr(self.yolo_detector, "imgsz", None)
            ball_cls = getattr(self.yolo_detector, "ball_class_id", None)
            model_path = str(getattr(self.yolo_detector, "model_path", "") or "")
        except Exception:
            pass

        h_w = self._yolo_last_frame_shape
        if vis is not None:
            try:
                h_w = (int(vis.shape[0]), int(vis.shape[1]))
            except Exception:
                pass

        last_hit_ts = float(getattr(self, "_yolo_last_hit_ts", 0.0) or 0.0)
        age_s = (time.time() - last_hit_ts) if last_hit_ts > 0 else -1.0

        def _fmt_conf_pct(conf_val: float | None) -> str:
            try:
                cv = float(conf_val or 0.0)
            except Exception:
                cv = 0.0
            pct = cv * 100.0
            if pct < 1.0:
                return f"{pct:.1f}%"
            if pct < 10.0:
                return f"{pct:.1f}%"
            return f"{pct:.0f}%"

        info_lines = []
        info_lines.append(f"YOLO Vision #{y_n} @ {y_hz:.2f}Hz | det {det_n}")
        top_conf = None
        if self._yolo_detections:
            try:
                top_conf = float(getattr(self._yolo_detections[0], "conf", 0.0) or 0.0)
            except Exception:
                top_conf = None
        det_state = "Detected" if det_n > 0 else "No detection"
        if top_conf is not None:
            info_lines.append(f"{det_state} | conf {_fmt_conf_pct(top_conf)}")
        else:
            info_lines.append(f"{det_state} | conf --%")
        if det_n == 0:
            hint = f"hint: try lower conf or larger imgsz (conf>={conf_th if conf_th is not None else '--'}, imgsz {imgsz if imgsz is not None else '--'})"
            info_lines.append(hint)
        cls_txt = f"cls {ball_cls}" if ball_cls is not None else "cls --"
        if lat_ms > 0:
            info_lines.append(
                f"latency {lat_ms:.1f}ms | conf>={conf_th if conf_th is not None else '--'} | {cls_txt} | imgsz {imgsz if imgsz is not None else '--'}"
            )
        else:
            info_lines.append(
                f"latency --.-ms | conf>={conf_th if conf_th is not None else '--'} | {cls_txt} | imgsz {imgsz if imgsz is not None else '--'}"
            )
        if h_w:
            info_lines.append(f"frame {h_w[1]}x{h_w[0]} | last hit {age_s:.2f}s ago" if age_s >= 0 else f"frame {h_w[1]}x{h_w[0]} | last hit --.-s")
        else:
            info_lines.append(f"frame --x-- | last hit {age_s:.2f}s ago" if age_s >= 0 else "frame --x-- | last hit --.-s")

        if model_path:
            info_lines.append(f"model {os.path.basename(model_path)}")
        try:
            ds_dir = str(getattr(self, "_yolo_training_dir", "") or "").strip()
            ds_label = str(getattr(self, "_yolo_training_dataset_label", "") or "").strip()
        except Exception:
            ds_dir = ""
            ds_label = ""
        if ds_dir:
            info_lines.append(f"dataset {ds_label} | {ds_dir}" if ds_label else f"dataset {ds_dir}")
        try:
            info_lines.append(
                f"ui model={str(getattr(self, 'yolo_model_choice', 'best'))} | COMPARE MODE: {'ON' if self.yolo_compare_enabled else 'OFF'}"
            )
        except Exception:
            pass
        if bool(getattr(self, "yolo_compare_enabled", False)):
            info_lines.append(">> Comparing: best.pt (Left) vs yolov8n.pt (Right)")

        top_box = None
        if det_n > 0 and self._yolo_detections:
            top_box = self._yolo_detections[0]

        if top_box is not None and det_n > 0:
            try:
                if isinstance(top_box, tuple):
                    x1, y1, x2, y2, cx, cy, label, cls_id = top_box
                    conf = float(getattr(self, "_yolo_last_hit_conf", 0.0) or 0.0)
                else:
                    x1 = float(getattr(top_box, "x1", 0.0))
                    y1 = float(getattr(top_box, "y1", 0.0))
                    x2 = float(getattr(top_box, "x2", 0.0))
                    y2 = float(getattr(top_box, "y2", 0.0))
                    cx = float(getattr(top_box, "cx", 0.0))
                    cy = float(getattr(top_box, "cy", 0.0))
                    label = str(getattr(top_box, "label", "ball") or "ball")
                    cls_id = int(getattr(top_box, "cls", -1) or -1)
                    conf = float(getattr(top_box, "conf", 0.0) or 0.0)
                bw = max(0.0, x2 - x1)
                bh = max(0.0, y2 - y1)
                info_lines.append(
                    f"top {label} cls{cls_id} {_fmt_conf_pct(conf)} | box {int(round(bw))}x{int(round(bh))} @ ({int(round(cx))},{int(round(cy))})"
                )
            except Exception:
                pass

        # Probe stats (any-class, lower conf) when no sports-ball hits
        probe_n = len(getattr(self, "_yolo_probe_boxes", []) or [])
        probe_err = str(getattr(self, "_yolo_probe_error_msg", "") or "").strip()
        probe_conf = float(getattr(self, "_yolo_probe_conf", 0.001) or 0.001)
        probe_lat_ms = float(getattr(self, "_yolo_probe_latency_s", 0.0) or 0.0) * 1000.0
        if probe_n > 0:
            info_lines.append(
                f"probe any-class det {probe_n} conf>={probe_conf} | lat {probe_lat_ms:.1f}ms"
            )
            try:
                p0 = (getattr(self, "_yolo_probe_boxes", []) or [])[0]
                plabel = str(getattr(p0, "label", "cls") or "cls")
                pcls = int(getattr(p0, "cls", -1) or -1)
                pconf = float(getattr(p0, "conf", 0.0) or 0.0)
                info_lines.append(f"probe top {plabel} cls{pcls} {int(round(pconf * 100))}%")
            except Exception:
                pass
        elif probe_err:
            info_lines.append(f"probe err: {probe_err}")

        if err:
            info_lines.append(f"err: {err}")

        info_text = "\n".join(info_lines)
        try:
            self.yolo_debug_window.update_view(
                vis,
                info_text,
                full_hist=full_hist,
                hi_img=hi_img,
                hi_hist=hi_hist,
                lo_img=lo_img,
                lo_hist=lo_hist,
            )
        except Exception:
            return

        try:
            if self.yolo_debug_window is not None and (self._yolo_hi_snap is not None or self._yolo_lo_snap is not None):
                def _median_hsv(img_bgr):
                    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
                        return 0, 0, 0
                    try:
                        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
                        pts = hsv.reshape(-1, 3)
                        if pts.size == 0:
                            return 0, 0, 0
                        med = np.median(pts, axis=0)
                        return int(round(med[0])), int(round(med[1])), int(round(med[2]))
                    except Exception:
                        return 0, 0, 0

                def _fmt_box(tag: str, conf: float | None, center, img_crop):
                    try:
                        cx, cy = center if center is not None else (0, 0)
                    except Exception:
                        cx, cy = (0, 0)
                    conf_v = float(conf or 0.0)
                    Hc, Sc, Vc = _median_hsv(img_crop)
                    return f"{tag} {_fmt_conf_pct(conf_v)}, ({cx},{cy}), ({Hc},{Sc},{Vc})"

                self.yolo_debug_window.hi_title.setText(
                    _fmt_box("Highest Conf", self._yolo_hi_conf, self._yolo_hi_center, self._yolo_hi_snap)
                )
                self.yolo_debug_window.lo_title.setText(
                    _fmt_box("Lowest Conf", self._yolo_lo_conf, self._yolo_lo_center, self._yolo_lo_snap)
                )
            elif self.yolo_debug_window is not None:
                self.yolo_debug_window.hi_title.setText("Highest Conf --%, (--,--), (--,--,--)")
                self.yolo_debug_window.lo_title.setText("Lowest Conf --%, (--,--), (--,--,--)")
        except Exception:
            pass

    def _update_yolo_compare_view(self, frame_bgr):
        try:
            if not bool(getattr(self, "yolo_compare_enabled", False)):
                return
            if self.yolo_compare_window is None or not self.yolo_compare_window.isVisible():
                return
        except Exception:
            return
        if frame_bgr is None:
            return
        try:
            left = frame_bgr.copy()
            right = frame_bgr.copy()
        except Exception:
            return
        try:
            if self._yolo_compare_detections_best:
                self._draw_yolo_detections(left, self._yolo_compare_detections_best)
        except Exception:
            pass
        try:
            if self._yolo_compare_detections_orig:
                self._draw_yolo_detections(right, self._yolo_compare_detections_orig)
        except Exception:
            pass
        try:
            self.yolo_compare_window.update_views(left, right)
        except Exception:
            pass

    def _set_ai_status(self, msg: str, *, ttl_s: float = 3.0):
        """Set a short-lived AI status message for the Color window overlay."""
        self._ai_status_msg = str(msg or "").strip()
        # store expiry time to avoid stale overlays
        try:
            self._ai_status_ts = time.time() + float(ttl_s)
        except Exception:
            self._ai_status_ts = time.time() + 3.0

    def _on_yolo_conf_changed(self, val):
        try:
            conf_v = float(val)
        except Exception:
            return
        for det in (self.yolo_detector, self.yolo_detector_best, self.yolo_detector_orig):
            if det is not None:
                try:
                    det.conf = conf_v
                except Exception:
                    pass
        print(f"[YOLO] conf -> {conf_v:.3f}")

    def _on_yolo_imgsz_changed(self, val):
        try:
            imgsz_v = int(val)
        except Exception:
            return
        for det in (self.yolo_detector, self.yolo_detector_best, self.yolo_detector_orig):
            if det is not None:
                try:
                    det.imgsz = imgsz_v
                except Exception:
                    pass
        print(f"[YOLO] imgsz -> {imgsz_v}")

    def _apply_yolo_model_choice(self):
        choice = str(getattr(self, "yolo_model_choice", "best") or "best").lower()
        if choice == "orig":
            self.yolo_detector = self.yolo_detector_orig
        else:
            self.yolo_detector = self.yolo_detector_best
        if self.yolo_debug_window is not None:
            try:
                self.yolo_debug_window.bind_model_selector(choice, self._on_yolo_model_changed)
            except Exception:
                pass
        if self.yolo_compare_window is not None:
            try:
                left_title = f"BEST ({os.path.basename(self.yolo_model_best_path)}, cls 0)"
                right_title = f"ORIGINAL ({os.path.basename(self.yolo_model_orig_path)}, cls 32)"
                self.yolo_compare_window.set_titles(left_title, right_title)
            except Exception:
                pass
        print(f"[YOLO] model -> {choice}")

    def _on_yolo_model_changed(self, idx=None):
        try:
            choice = None
            if self.yolo_debug_window is not None:
                try:
                    choice = self.yolo_debug_window.yolo_model_combo.currentData()
                except Exception:
                    choice = None
                if choice is None:
                    try:
                        idx = self.yolo_debug_window.yolo_model_combo.currentIndex()
                    except Exception:
                        idx = idx
            if isinstance(idx, str):
                if "yolo" in idx.lower():
                    choice = "orig"
                elif "best" in idx.lower():
                    choice = "best"
            if choice is None:
                choice = "orig" if int(idx or 0) == 1 else "best"
            self.yolo_model_choice = str(choice)
        except Exception:
            self.yolo_model_choice = "best"
        self._apply_yolo_model_choice()

    def _on_yolo_compare_toggle(self, checked: bool):
        if not bool(checked):
            self.yolo_compare_enabled = False
            try:
                if self.yolo_compare_window is not None:
                    self.yolo_compare_window.hide()
            except Exception:
                pass
            print("[YOLO] Compare OFF.")
            return

        self.yolo_compare_enabled = True
        self._ensure_yolo_compare_window()
        print(f"[YOLO] Compare ON  (ui model={getattr(self, 'yolo_model_choice', 'best')})")

    def _ensure_yolo_compare_window(self) -> None:
        try:
            if self.yolo_compare_window is None:
                self.yolo_compare_window = YoloCompareWindow()
            
            left_title = f"BEST ({os.path.basename(self.yolo_model_best_path)}, cls 0)"
            right_title = f"ORIGINAL ({os.path.basename(self.yolo_model_orig_path)}, cls 32)"
            self.yolo_compare_window.set_titles(left_title, right_title)

            # Ensure safe positioning (right of debug window)
            try:
                target_x, target_y = 100, 100
                if self.yolo_debug_window is not None and self.yolo_debug_window.isVisible():
                    # Place to the right
                    base_x = max(0, self.yolo_debug_window.x())
                    base_y = max(0, self.yolo_debug_window.y())
                    target_x = base_x + self.yolo_debug_window.width() + 20
                    target_y = base_y
                elif self.isVisible():
                    # Fallback relative to main window
                    base_x = max(0, self.x())
                    base_y = max(0, self.y());
                    target_x = base_x + 50
                    target_y = base_y + 50
                
                self.yolo_compare_window.move(target_x, target_y)
            except Exception:
                pass
            
            self.yolo_compare_window.show()
            self.yolo_compare_window.raise_()
            try:
                self.yolo_compare_window.activateWindow()
            except Exception:
                pass
            
        except Exception:
            pass

    def _yolo_train_next_version_dir(self) -> tuple[str, str]:
        root = os.path.join(os.path.dirname(__file__), "AI_datasets")
        os.makedirs(root, exist_ok=True)
        # Always create a new version folder to preserve existing datasets.
        for v in range(1, 100):
            label = f"yolo_ball_v{v:02d}"
            path = os.path.join(root, label)
            if not os.path.isdir(path):
                return path, label

        # All v01..v99 exist (full) -> reuse v01 (should not happen)
        label = "yolo_ball_v01"
        return os.path.join(root, label), label

    def _yolo_train_prepare_dataset(self):
        path, label = self._yolo_train_next_version_dir()
        images_dir = os.path.join(path, "images")
        labels_dir = os.path.join(path, "labels")
        meta_dir = os.path.join(path, "meta")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)
        os.makedirs(meta_dir, exist_ok=True)

        dataset_yaml = os.path.join(path, "dataset.yaml")
        if not os.path.exists(dataset_yaml):
            try:
                class_names = list(self._yolo_labeling_class_names or ["ball"])
                nc_val = len(class_names) if class_names else 1
                names_line = ", ".join(class_names) if class_names else "ball"
                with open(dataset_yaml, "w", encoding="utf-8") as f:
                    f.write("# YOLO dataset configuration\n")
                    f.write("# Root path for this dataset version (relative path).\n")
                    f.write("path: .\n\n")
                    f.write("# Image folders (relative to path).\n")
                    f.write("# Auto-labeled images are typically saved under images/ with labels/ and meta/.\n")
                    f.write("# Manual-labeled images are saved as manual_<timestamp>.jpg with matching labels.\n")
                    f.write("train: images\nval: images\n\n")
                    f.write("# Class definitions\n")
                    f.write(f"nc: {nc_val}\n")
                    f.write(f"names: [{names_line}]\n")
            except Exception:
                pass

        readme_path = os.path.join(path, "README.md")
        if not os.path.exists(readme_path):
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                version_tag = label.replace("yolo_ball_", "")
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(f"# {label}\n")
                    f.write(f"Updated: {today}\n\n")
                    f.write("YOLO Ball dataset captured via Yolo Vision.\n")
                    f.write("Auto-labeled by detector; see meta/ for confidence and difficulty.\n")
                    f.write("Manual labels (if any) are stored alongside auto labels in labels/.\n")
                    f.write("\nVersion History\n")
                    f.write(
                        f"- {version_tag} ({today}): Initial dataset folder created; preserve this dataset and create new versions in sibling folders (v02, v03, ...).\n"
                    )
                    f.write("\nData Sources\n")
                    f.write("- Auto labeling: images named `imgNNNNNN.jpg` with optional metadata in `meta/`.\n")
                    f.write("- Manual labeling: images named `manual_<timestamp>.jpg` and matching labels `manual_<timestamp>.txt`.\n")
            except Exception:
                pass

        # Determine next image index (continue to img001000)
        next_idx = 1
        try:
            max_idx = 0
            for name in os.listdir(images_dir):
                m = re.match(r"img(\d{6})\.jpg$", name)
                if m:
                    max_idx = max(max_idx, int(m.group(1)))
            next_idx = max_idx + 1
        except Exception:
            next_idx = 1

        if next_idx > int(self.yolo_training_target or 1000):
            next_idx = int(self.yolo_training_target or 1000) + 1

        self._yolo_training_dir = path
        self._yolo_training_dataset_label = label
        self._yolo_training_next_index = next_idx

    @staticmethod
    def _yolo_train_iou(a, b) -> float:
        try:
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
        except Exception:
            return 0.0
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        inter = iw * ih
        a_area = max(0.0, (ax2 - ax1) * (ay2 - ay1))
        b_area = max(0.0, (bx2 - bx1) * (by2 - by1))
        union = a_area + b_area - inter
        if union <= 0:
            return 0.0
        return inter / union

    def _yolo_train_box_sane(self, x1, y1, x2, y2, w: int, h: int) -> bool:
        bw = max(0.0, x2 - x1)
        bh = max(0.0, y2 - y1)
        if bw < 12 or bh < 12:
            return False
        if w <= 0 or h <= 0:
            return False
        ar = max(bw / bh, bh / bw) if min(bw, bh) > 0 else 999.0
        if ar > 1.6:
            return False
        if (bw * bh) > (0.40 * float(w * h)):
            return False
        return True

    def _yolo_train_update_recent(self, box) -> bool:
        self._yolo_training_recent_boxes.append(box)
        if len(self._yolo_training_recent_boxes) < 3:
            return False
        b0, b1, b2 = self._yolo_training_recent_boxes
        return (self._yolo_train_iou(b0, b1) >= 0.5) and (self._yolo_train_iou(b1, b2) >= 0.5)

    def _yolo_train_assign_difficulty(self, conf: float) -> str:
        try:
            cf = float(conf)
        except Exception:
            cf = 0.0
        if cf < 0.08:
            return "hard"
        if cf < 0.18:
            return "medium"
        return "easy"

    def _yolo_train_bucket_allowed(self, difficulty: str) -> bool:
        total = int(self.yolo_training_target or 256)
        t_easy = int(round(total * 0.30))
        t_med = int(round(total * 0.40))
        t_hard = max(0, total - t_easy - t_med)
        if difficulty == "easy":
            return self._yolo_training_easy < t_easy
        if difficulty == "hard":
            return self._yolo_training_hard < t_hard
        return self._yolo_training_med < t_med

    def _yolo_train_note_bucket(self, difficulty: str):
        if difficulty == "easy":
            self._yolo_training_easy += 1
        elif difficulty == "hard":
            self._yolo_training_hard += 1
        else:
            self._yolo_training_med += 1

    def _yolo_train_save_sample(self, frame_bgr, *, x1, y1, x2, y2, conf: float, difficulty: str):
        if self._yolo_training_dir is None:
            return
        images_dir = os.path.join(self._yolo_training_dir, "images")
        labels_dir = os.path.join(self._yolo_training_dir, "labels")
        meta_dir = os.path.join(self._yolo_training_dir, "meta")

        idx = int(self._yolo_training_next_index)
        name = f"img{idx:06d}"
        img_path = os.path.join(images_dir, f"{name}.jpg")
        label_path = os.path.join(labels_dir, f"{name}.txt")
        meta_path = os.path.join(meta_dir, f"{name}.meta.json")

        h, w = frame_bgr.shape[:2]
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        bw = max(1.0, (x2 - x1))
        bh = max(1.0, (y2 - y1))
        cx_n = max(0.0, min(1.0, cx / float(w)))
        cy_n = max(0.0, min(1.0, cy / float(h)))
        bw_n = max(0.0, min(1.0, bw / float(w)))
        bh_n = max(0.0, min(1.0, bh / float(h)))

        try:
            cv2.imwrite(img_path, frame_bgr)
        except Exception:
            return

        try:
            with open(label_path, "w", encoding="utf-8") as f:
                f.write(f"0 {cx_n:.6f} {cy_n:.6f} {bw_n:.6f} {bh_n:.6f}\n")
        except Exception:
            return

        meta = {
            "label_source": "yolo_low_conf",
            "yolo_confidence": float(conf),
            "difficulty": difficulty,
            "notes": "auto-labeled via Yolo Vision",
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception:
            pass

        self._yolo_training_next_index += 1
        self.yolo_training_count += 1
        self._yolo_training_conf_values.append(float(conf))
        self._yolo_train_note_bucket(difficulty)

    def _yolo_training_prompt(self):
        now = time.time()
        if (now - float(self._yolo_training_last_prompt_ts or 0.0)) < 4.0:
            return
        self._yolo_training_last_prompt_ts = now
        if not self._yolo_training_prompt_msgs:
            return
        self._yolo_training_prompt_idx = (self._yolo_training_prompt_idx + 1) % len(self._yolo_training_prompt_msgs)
        self._yolo_training_status_msg = self._yolo_training_prompt_msgs[self._yolo_training_prompt_idx]

    def _stop_yolo_training(self, *, reason: str = ""):
        self.yolo_training_enabled = False
        self._yolo_training_recent_boxes.clear()
        self._yolo_training_status_msg = str(reason or "")
        try:
            self.yolo_vision_interval_s = float(self._yolo_training_interval_default or 1.0)
        except Exception:
            self.yolo_vision_interval_s = 1.0
        try:
            if self.yolo_debug_window is not None:
                self.yolo_debug_window.set_training_checked(False)
        except Exception:
            pass
        try:
            if self.yolo_train_hist_window is not None:
                self.yolo_train_hist_window.hide()
        except Exception:
            pass

    def _on_yolo_training_toggle(self, checked: bool):
        if not bool(getattr(self, "yolo_vision_enabled", False)):
            self._stop_yolo_training(reason="Yolo Vision is OFF")
            return

        if not bool(checked):
            self._stop_yolo_training(reason="")
            print("[YOLO] Ball Training OFF.")
            return

        # Start training
        self.yolo_training_enabled = True
        self.yolo_training_count = 0
        self._yolo_training_conf_values = []
        self._yolo_training_easy = 0
        self._yolo_training_med = 0
        self._yolo_training_hard = 0
        self._yolo_training_recent_boxes.clear()
        self._yolo_training_status_msg = "Change ball position / lighting for variety"
        self._yolo_training_last_prompt_ts = 0.0
        self._yolo_training_prompt_idx = 0

        self._yolo_training_interval_default = float(getattr(self, "yolo_vision_interval_s", 1.0) or 1.0)
        self._yolo_train_prepare_dataset()

        try:
            if self.yolo_train_hist_window is None:
                self.yolo_train_hist_window = YoloTrainHistogramWindow()
            self.yolo_train_hist_window.show()
        except Exception:
            pass

        print(f"[YOLO] Ball Training ON -> {self._yolo_training_dataset_label}")

    def _yolo_labeling_class_label(self) -> str:
        try:
            idx = int(self._yolo_labeling_class_id)
        except Exception:
            idx = 0
        try:
            name = self._yolo_labeling_class_names[idx]
        except Exception:
            name = "class"
        return f"{idx}:{name}"

    def _on_yolo_labeling_class_changed(self, idx: int):
        try:
            idx = int(idx)
        except Exception:
            return
        if idx < 0 or idx >= len(self._yolo_labeling_class_names):
            return
        self._yolo_labeling_class_id = idx
        if self.yolo_labeling_enabled:
            self._yolo_labeling_msg = f"Draw box... Enter to save. [{self._yolo_labeling_class_label()}]"

    def _on_yolo_labeling_toggle(self, checked: bool):
        self.yolo_labeling_enabled = bool(checked)
        if self.yolo_labeling_enabled:
            print("[YOLO] Labeling Mode ON.")
            # Ensure output directory exists (reuse existing logic)
            self._yolo_train_prepare_dataset()
            self._yolo_labeling_msg = f"Draw box... Enter to save. [{self._yolo_labeling_class_label()}]"
            self._yolo_labeling_p1 = None
            self._yolo_labeling_p2 = None
            self._yolo_labeling_drawing = False
        else:
            print("[YOLO] Labeling Mode OFF.")
            self._yolo_labeling_msg = ""
            self._yolo_labeling_p1 = None
            self._yolo_labeling_p2 = None
            self._yolo_labeling_drawing = False

    def _on_labeling_mouse_event(self, etype, pos, buttons):
        if not self.yolo_labeling_enabled:
            return
        
        if self.yolo_debug_window is None:
            return
        
        view = self.yolo_debug_window.view
        pix = view.pixmap()
        if pix is None:
            return
            
        view_w, view_h = view.width(), view.height()
        px_w, px_h = pix.width(), pix.height()
        
        # Calculate offset (image is centered)
        off_x = (view_w - px_w) // 2
        off_y = (view_h - px_h) // 2
        
        # Coordinate in image space
        ix = pos.x() - off_x
        iy = pos.y() - off_y
        
        # Clamp
        ix = max(0, min(px_w - 1, ix))
        iy = max(0, min(px_h - 1, iy))
        
        if etype == "press":
            self._yolo_labeling_drawing = True
            self._yolo_labeling_p1 = (ix, iy)
            self._yolo_labeling_p2 = (ix, iy)
            self._yolo_labeling_msg = f"Drawing... [{self._yolo_labeling_class_label()}]"
        
        elif etype == "move":
            if self._yolo_labeling_drawing:
                self._yolo_labeling_p2 = (ix, iy)
        
        elif etype == "release":
            if self._yolo_labeling_drawing:
                self._yolo_labeling_p2 = (ix, iy)
                self._yolo_labeling_drawing = False
                self._yolo_labeling_msg = f"Press ENTER to save, SPACE to clear [{self._yolo_labeling_class_label()}]"

    def _on_labeling_key_event(self, event):
        if not self.yolo_labeling_enabled:
            return
        key = event.key()
        if Qt.Key_1 <= key <= Qt.Key_9:
            idx = int(key - Qt.Key_1)
            if 0 <= idx < len(self._yolo_labeling_class_names):
                self._on_yolo_labeling_class_changed(idx)
                try:
                    if self.yolo_debug_window is not None:
                        self.yolo_debug_window.set_labeling_class_index(idx)
                except Exception:
                    pass
            return
        if key == Qt.Key_Return or key == Qt.Key_Enter:
             self._save_manual_label()
        elif key == Qt.Key_Space or key == Qt.Key_Escape:
             self._yolo_labeling_p1 = None
             self._yolo_labeling_p2 = None
             self._yolo_labeling_msg = f"Cleared. [{self._yolo_labeling_class_label()}]"

    def _save_manual_label(self):
        if not self._yolo_labeling_p1 or not self._yolo_labeling_p2:
            return

        x1, y1 = self._yolo_labeling_p1
        x2, y2 = self._yolo_labeling_p2
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        
        if w < 5 or h < 5:
            self._yolo_labeling_msg = "Box too small!"
            return

        img = getattr(self, "_yolo_labeling_last_frame", None)
        if img is None:
            self._yolo_labeling_msg = "No frame captured!"
            return
            
        xmin, xmax = min(x1, x2), max(x1, x2)
        ymin, ymax = min(y1, y2), max(y1, y2)
        
        bbox = (xmin, ymin, xmax, ymax)
        
        if self._yolo_save_manual_sample(img, bbox):
            self._yolo_labeling_msg = "SAVED!"
            self._yolo_labeling_save_msg_ts = time.time()
            self._yolo_labeling_p1 = None
            self._yolo_labeling_p2 = None
        else:
            self._yolo_labeling_msg = "Save Failed!"

    def _yolo_save_manual_sample(self, img_bgr, bbox):
        if not self._yolo_training_dir:
             self._yolo_train_prepare_dataset()
        if not self._yolo_training_dir:
             return False
             
        x1, y1, x2, y2 = bbox
        h_img, w_img = img_bgr.shape[:2]
        
        # Normalize
        dw = 1.0 / w_img
        dh = 1.0 / h_img
        
        bw = (x2 - x1)
        bh = (y2 - y1)
        cx = x1 + (bw / 2.0)
        cy = y1 + (bh / 2.0)
        
        cx *= dw
        cy *= dh
        bw *= dw
        bh *= dh
        
        ts = int(time.time() * 1000)
        base = f"manual_{ts}"
        try:
            img_path = os.path.join(self._yolo_training_dir, "images", f"{base}.jpg")
            txt_path = os.path.join(self._yolo_training_dir, "labels", f"{base}.txt")
            
            cv2.imwrite(img_path, img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            with open(txt_path, "w") as f:
                f.write(f"{self._yolo_labeling_class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\\n")
            print(f"[YOLO] Manual Label Saved: {base}")
            return True
        except Exception as e:
            print(f"[YOLO] Save error: {e}")
            return False

    def _update_yolo_train_hist_window(self):
        try:
            if self.yolo_train_hist_window is None or not self.yolo_train_hist_window.isVisible():
                return
        except Exception:
            return
        try:
            self.yolo_train_hist_window.update_histogram(
                self._yolo_training_conf_values,
                easy_n=int(self._yolo_training_easy),
                med_n=int(self._yolo_training_med),
                hard_n=int(self._yolo_training_hard),
                total_target=int(self.yolo_training_target or 256),
                progress=int(self.yolo_training_count),
                dataset_label=str(self._yolo_training_dataset_label or ""),
            )
        except Exception:
            pass

    def _ai_det_to_px(self, det, w: int, h: int):
        try:
            if isinstance(det, dict):
                x_val = det.get("x", 0)
                y_val = det.get("y", 0)
                r_val = det.get("r", 0)
                score_val = det.get("score", 0.0)
            else:
                x_val = getattr(det, "x", 0)
                y_val = getattr(det, "y", 0)
                r_val = getattr(det, "r", 0)
                score_val = getattr(det, "score", 0.0)
            x_f = float(x_val)
            y_f = float(y_val)
            r_f = float(r_val)
            if 0 < x_f <= 1.0 and 0 < y_f <= 1.0 and w > 1 and h > 1:
                x_f *= w
                y_f *= h
            if 0 < r_f <= 1.0 and min(w, h) > 1:
                r_f *= min(w, h)
            x = int(round(x_f))
            y = int(round(y_f))
            r = float(r_f)
            try:
                score = float(score_val)
            except Exception:
                score = 0.0
            x = max(0, min(w - 1, x))
            y = max(0, min(h - 1, y))
            return x, y, r, score
        except Exception:
            return None

    def _refine_ai_circle(self, frame_bgr, det):
        if frame_bgr is None:
            return det
        h_img, w_img = frame_bgr.shape[:2]
        px = self._ai_det_to_px(det, w_img, h_img)
        if not px:
            return det
        x, y, r, score = px
        if r <= 4:
            return det

        roi_scale = float(getattr(self, "ai_refine_roi_scale", 1.2) or 1.2)
        r0 = int(round(r))
        pad = max(6, int(round(r0 * roi_scale)))
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w_img - 1, x + pad)
        y1 = min(h_img - 1, y + pad)
        if x1 <= x0 or y1 <= y0:
            return det

        roi = frame_bgr[y0 : y1 + 1, x0 : x1 + 1]
        try:
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        except Exception:
            return det

        t = self.ball_tracker
        lower1 = np.array([t.h1_min, t.s_min, t.v_min], np.uint8)
        upper1 = np.array([t.h1_max, t.s_max, t.v_max], np.uint8)
        mask1 = cv2.inRange(hsv, lower1, upper1)

        if t.h2_max > t.h2_min:
            lower2 = np.array([t.h2_min, t.s_min, t.v_min], np.uint8)
            upper2 = np.array([t.h2_max, t.s_max, t.v_max], np.uint8)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = mask1

        k = max(3, int(getattr(t, "kernel_size", 3) or 3))
        if k % 2 == 0:
            k += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return det

        roi_h, roi_w = mask.shape[:2]
        min_area = float(self.ai_refine_min_area_ratio) * float(roi_w * roi_h)
        cx = x - x0
        cy = y - y0
        chosen = None
        chosen_area = 0.0
        chosen_contains = False

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            contains = cv2.pointPolygonTest(cnt, (float(cx), float(cy)), False) >= 0
            if chosen is None:
                chosen = cnt
                chosen_area = area
                chosen_contains = contains
                continue
            if contains and not chosen_contains:
                chosen = cnt
                chosen_area = area
                chosen_contains = True
                continue
            if contains == chosen_contains and area > chosen_area:
                chosen = cnt
                chosen_area = area
                chosen_contains = contains

        if chosen is None:
            return det

        (xr, yr), rr = cv2.minEnclosingCircle(chosen)
        if rr <= 0:
            return det

        x_ref = x0 + float(xr)
        y_ref = y0 + float(yr)
        r_ref = float(rr)

        # Sanity clamp to avoid absurd growth
        if r_ref > r0 * 1.6:
            return det

        return {"x": x_ref, "y": y_ref, "r": r_ref, "score": score}

    def _auto_calibrate_hsv_from_ai(self, frame_bgr, det) -> bool:
        if frame_bgr is None:
            return False
        if not bool(getattr(self, "ai_auto_hsv_enabled", False)):
            return False
        if bool(getattr(self, "ai_auto_hsv_applied", False)):
            return False

        h_img, w_img = frame_bgr.shape[:2]
        px = self._ai_det_to_px(det, w_img, h_img)
        if not px:
            return False
        x, y, r, score = px
        if r <= 4:
            return False
        if score < float(getattr(self, "ai_score_min", 0.0)):
            return False

        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            return False

        inner_ratio = float(getattr(self, "ai_auto_hsv_inner_ratio", 0.6) or 0.6)
        sample_r = int(max(6, round(float(r) * inner_ratio)))
        sample_r = min(sample_r, int(min(w_img, h_img) / 2))

        mask = np.zeros((h_img, w_img), dtype=np.uint8)
        cv2.circle(mask, (x, y), sample_r, 255, -1)
        pts = hsv_img[mask > 0]
        if pts is None or len(pts) < 30:
            return False

        h_vals = pts[:, 0].astype(np.float32)
        s_vals = pts[:, 1].astype(np.float32)
        v_vals = pts[:, 2].astype(np.float32)

        # Circular mean for hue (0..179)
        angles = h_vals / 180.0 * 2.0 * np.pi
        mean_angle = np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
        if mean_angle < 0:
            mean_angle += 2.0 * np.pi
        mean_h = mean_angle / (2.0 * np.pi) * 180.0

        # Circular distance
        dist = np.abs(h_vals - mean_h)
        dist = np.minimum(dist, 180.0 - dist)
        pct_hi = float(getattr(self, "ai_auto_hsv_percentile_hi", 85) or 85)
        delta = float(np.percentile(dist, pct_hi)) + float(getattr(self, "ai_auto_hsv_margin_h", 8) or 8)
        delta = max(6.0, min(60.0, delta))

        h_low = mean_h - delta
        h_high = mean_h + delta

        if h_low < 0 or h_high > 179:
            # Wrap-around: split into two hue ranges
            h1_min = 0
            h1_max = int(round(h_high - 179)) if h_high > 179 else int(round(h_high))
            h2_min = int(round(h_low + 180)) if h_low < 0 else int(round(h_low))
            h2_max = 179
        else:
            h1_min = int(round(h_low))
            h1_max = int(round(h_high))
            h2_min = 0
            h2_max = 0

        pct_lo = float(getattr(self, "ai_auto_hsv_percentile_lo", 15) or 15)
        s_lo = float(np.percentile(s_vals, pct_lo))
        s_hi = float(np.percentile(s_vals, pct_hi))
        v_lo = float(np.percentile(v_vals, pct_lo))
        v_hi = float(np.percentile(v_vals, pct_hi))

        s_min = max(0, int(round(s_lo - float(getattr(self, "ai_auto_hsv_margin_s", 20) or 20))))
        s_max = min(255, int(round(s_hi + float(getattr(self, "ai_auto_hsv_margin_s", 20) or 20))))
        v_min = max(0, int(round(v_lo - float(getattr(self, "ai_auto_hsv_margin_v", 20) or 20))))
        v_max = min(255, int(round(v_hi + float(getattr(self, "ai_auto_hsv_margin_v", 20) or 20))))

        # Apply to tracker
        self.ball_tracker.set_hue_ranges(h1_min, h1_max, h2_min, h2_max)
        self.ball_tracker.set_sv_ranges(s_min, s_max, v_min, v_max)
        self.ball_tracker.save_default_config()

        # Update picker to ball center
        try:
            Hc, Sc, Vc = [int(v) for v in hsv_img[y, x]]
            self.ball_tracker.set_sample_point((x, y), (Hc, Sc, Vc))
        except Exception:
            pass

        # Sync mask window sliders if open
        if self.ball_mask_window is not None:
            try:
                self.ball_mask_window.apply_hsv_ranges(
                    h1_min, h1_max, h2_min, h2_max, s_min, s_max, v_min, v_max
                )
            except Exception:
                pass

        self.ai_auto_hsv_applied = True
        print(
            f"[AI] Auto HSV from AI: H1({h1_min}-{h1_max}) H2({h2_min}-{h2_max}) "
            f"S({s_min}-{s_max}) V({v_min}-{v_max})"
        )
        return True

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
        # Called by Mask window "Clear" to stop barking and hide the cheer banner.
        self._stop_barking()
        self._bark_pending_start = False
        self._set_mask_cheer("", visible=False)

        # If the OFF timer hasn't fired yet, cancel it so barking/message won't restart.
        prev = getattr(self, "_close_enough_off_timer", None)
        try:
            if prev is not None and prev.is_alive():
                prev.cancel()
        except Exception:
            pass

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
        """Update bottom-bar HTML text and Dog Video button label/color."""

        def color(ok: bool) -> str:
            return "#00ff44" if ok else "#ff4444"

        # Video port color: yellow if STALL, otherwise green/red
        if self.video_stall and self.use_dog_video:
            video_color = "#ffff00"
            video_text = f"Video:{self.video_port}(STALL)"
        else:
            video_color = "#00ff44" if self.server_video_ok else "#ff4444"
            video_text = f"Video:{self.video_port}"

        all_ok = (
            self.server_ip_ok
            and self.server_video_ok
            and self.server_control_ok
            and not (self.video_stall and self.use_dog_video)
        )

        html = (
            f"<span style='color:{color(self.server_ip_ok)}'>"
            f"IP {self.ip}</span>  |  "
            f"<span style='color:{video_color}'>{video_text}</span>  |  "
            f"<span style='color:{color(self.server_control_ok)}'>"
            f"Ctrl:{self.control_port}</span>"
        )
        self.status_detail_label.setText(html)

        if self.use_dog_video:
            btn_text = "Switch to\nClient Mac Video"
            btn_color = "#00ff44"
        else:
            if all_ok:
                btn_text = "Dog Video\nReady"
                btn_color = "#00ff44"
            else:
                btn_text = "Dog Video\nNOT Ready"
                btn_color = "#ff4444"

        self.dog_button.setText(btn_text)
        self.dog_button.setStyleSheet(
            f"font-size:16px; padding:10px; background-color:white; color:{btn_color};"
        )

    # ==================================================================
    # Dog reconnect & mode switch
    # ==================================================================
    def try_reconnect(self):
        """
        Dog Video button:
          - Dog→Mac: switch to Mac camera only.
          - Mac→Dog: probe IP/ports, then start Dog client if OK.
        """
        if self.reconnect_in_progress:
            print("[RECONNECT] Already in progress.")
            return
        self.reconnect_in_progress = True

        if self.use_dog_video:
            print("[RECONNECT] Dog→Mac.")
            self.use_dog_video = False
            self.shutdown_dog_client()
            self.server_video_ok = False
            self.server_control_ok = False
            self.video_stall = False
            self.update_status_ui()
            self.reconnect_in_progress = False
            return

        print("[RECONNECT] Mac→Dog.")
        self.last_dog_frame = None
        self.dog_last_frame_time = None
        self.dog_has_recent_frame = False
        self.video_stall = False

        # Reset FPS counters
        self.display_fps = 0.0
        self.display_frame_count = 0
        self.display_last_time = time.time()
        self.rx_fps = 0.0
        self.rx_frame_count = 0
        self.rx_last_time = time.time()

        ip_ok = self.ping_ip(self.ip)
        ctrl_ok = self.test_tcp_port(self.ip, self.control_port)

        self.server_ip_ok = ip_ok
        self.server_control_ok = ctrl_ok

        if not (ip_ok and ctrl_ok):
            print("[RECONNECT] Dog NOT ready (IP/ctrl fail).")
            self.server_video_ok = False
            self.use_dog_video = False
            self.update_status_ui()
            self.reconnect_in_progress = False
            return

        print("[RECONNECT] Dog reachable → start Dog client.")
        self.start_dog_client()
        self.use_dog_video = True
        self.server_video_ok = True
        self.video_stall = False
        self.update_status_ui()
        self.reconnect_in_progress = False
        self.schedule_dog_entry_beep()

    # ==================================================================
    # Frame update & drawing
    # ==================================================================
    def update_frame(self):
        """
        Grab and display a new frame (Dog video or Mac camera) and overlays.

        Two FPS counters:
          • RX: receive FPS (Dog frame rate).
          • UI: display FPS (Qt repaint rate).
        """
        frame = None
        new_dog_frame = False

        # ---- Count display FPS (every timer tick) ----
        self.display_frame_count += 1
        now = time.time()
        if now - self.display_last_time >= 1.0:
            self.display_fps = (
                self.display_frame_count / (now - self.display_last_time)
            )
            self.display_frame_count = 0
            self.display_last_time = now

        # Dog video
        if self.use_dog_video and self.dog_client is not None:
            with self.dog_client.image_lock:
                if isinstance(self.dog_client.image, np.ndarray):
                    current = self.dog_client.image.copy()
                    if self.last_dog_frame is None:
                        new_dog_frame = True
                    else:
                        new_dog_frame = not np.array_equal(current, self.last_dog_frame)
                    self.last_dog_frame = current
                    frame = current
                    if new_dog_frame:
                        self.dog_has_recent_frame = True
                        self.dog_last_frame_time = time.time()
                        self.video_stall = False

            if frame is None:
                now2 = time.time()
                if self.last_dog_frame is not None:
                    frame = self.last_dog_frame
                else:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(
                        frame,
                        "NO DOG VIDEO",
                        (40, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2,
                    )
                    # Debug info: show video source status
                    debug_text = f"IP:{self.ip}:{self.video_port} | Socket2:{getattr(self.dog_client, 'client_socket2', None) is not None}"
                    cv2.putText(
                        frame,
                        debug_text,
                        (40, 180),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1,
                    )
                if self.dog_last_frame_time is not None:
                    if now2 - self.dog_last_frame_time > 2.0:
                        self.video_stall = True
                self.dog_has_recent_frame = False

            # ---- Receive FPS: count only when a new Dog frame arrives ----
            if new_dog_frame:
                # Time since previous *new* frame – this is the true stream interval
                now_rx = time.time()
                if hasattr(self, "_last_rx_debug_time"):
                    dt = (now_rx - self._last_rx_debug_time) * 1000.0
                    # print(f"[RX-DEBUG] Dog new frame dt = {dt:.1f} ms")
                self._last_rx_debug_time = now_rx

                # FPS counter based on new frames
                self.rx_frame_count += 1
                if now_rx - self.rx_last_time >= 1.0:
                    self.rx_fps = self.rx_frame_count / (now_rx - self.rx_last_time)
                    self.rx_frame_count = 0
                    self.rx_last_time = now_rx

            # NEW: remember Dog frame height for head tracking
            if frame is not None:
                self.last_dog_frame_height = frame.shape[0]

        # Client-side source (Mac/Device/RTSP)
        else:
            self._retry_client_camera_if_needed()
            if self.cap is not None and self.cap.isOpened():
                ret, cam_frame = self.cap.read()
                if ret and isinstance(cam_frame, np.ndarray):
                    frame = cam_frame
                    self._client_cam_fail_count = 0
                else:
                    self._client_cam_fail_count += 1
                    self._log_client_cam("[SRC] Client source read failed.")
                    if self._client_cam_fail_count >= self._client_cam_fail_limit:
                        self._log_client_cam("[SRC] Client camera reopening after failures.")
                        try:
                            if self.cap is not None:
                                self.cap.release()
                        except Exception:
                            pass
                        self.cap = None
                        self._client_cam_opened_index = None
                        self._client_cam_next_try_ts = 0.0
                        self._client_cam_fail_count = 0
            else:
                self._log_client_cam("[SRC] Client source not opened or unavailable.")

            if frame is None:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(
                    frame,
                    "NO CLIENT SOURCE",
                    (40, 120),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            # In Mac mode we simply mirror the display FPS into rx_fps
            self.rx_fps = self.display_fps

        # Keep last BGR frame for picker clicks
        self.last_display_frame_bgr = frame.copy()  # ** for HSV picker, before any drawing or ball tracking **

        # ---- Optional ball tracking & mask window ----
        mask = None
        ball_center = None
        # IMPORTANT: autonomous tracking behavior (motion/head commands) must only run in "Ball" mode.
        # CV Ball / Yolo Vision / GPT Vision are test-only modes and must NOT move the dog.
        if self.ball_mode_enabled and frame is not None:
            #print(f"[DEBUG] Ball mode enabled: {self.ball_mode_enabled}")
            # If Yolo Vision is enabled, prefer YOLO detections for tracking.
            if self.yolo_vision_enabled and self.yolo_detector is not None:
                if not isinstance(getattr(self, "_yolo_detections", None), list):
                    self._yolo_detections = []
                now_y = time.time()
                yolo_ran = False
                if (now_y - float(getattr(self, "_yolo_vision_last_ts", 0.0) or 0.0)) >= float(
                    getattr(self, "yolo_vision_interval_s", 0.25) or 0.25
                ):
                    self._yolo_vision_last_ts = now_y
                    yolo_ran = True
                    try:
                        self._yolo_update_count = int(getattr(self, "_yolo_update_count", 0) or 0) + 1
                    except Exception:
                        self._yolo_update_count = 1
                    self._yolo_detections = []
                    self._yolo_last_error_msg = ""
                    self._yolo_last_latency_s = 0.0
                    try:
                        if frame is not None:
                            self._yolo_last_frame_shape = (int(frame.shape[0]), int(frame.shape[1]))
                    except Exception:
                        pass
                    try:
                        self._yolo_detections = self.yolo_detector.analyze(frame)
                        if getattr(self.yolo_detector, "last_error", None):
                            self._yolo_last_error_msg = str(self.yolo_detector.last_error or "").strip()
                        try:
                            self._yolo_last_latency_s = float(getattr(self.yolo_detector, "last_latency_s", 0.0) or 0.0)
                        except Exception:
                            self._yolo_last_latency_s = 0.0
                    except Exception as e:
                        self._yolo_detections = []
                        self._yolo_last_error_msg = f"YOLO exception: {e}"
                        self._yolo_last_latency_s = 0.0

                if self._yolo_detections:
                    b0 = self._yolo_detections[0]
                    try:
                        cx = int(round(float(getattr(b0, "cx", 0.0))))
                        cy = int(round(float(getattr(b0, "cy", 0.0))))
                        x1 = float(getattr(b0, "x1", 0.0))
                        y1 = float(getattr(b0, "y1", 0.0))
                        x2 = float(getattr(b0, "x2", 0.0))
                        y2 = float(getattr(b0, "y2", 0.0))
                        rr = 0.5 * max(6.0, min(abs(x2 - x1), abs(y2 - y1)))
                        if yolo_ran:
                            self._yolo_last_hit_ts = now_y
                        try:
                            self._yolo_last_hit_conf = float(getattr(b0, "conf", 0.0) or 0.0)
                        except Exception:
                            self._yolo_last_hit_conf = 0.0
                        try:
                            self._yolo_last_hit_box = (
                                x1,
                                y1,
                                x2,
                                y2,
                                float(getattr(b0, "cx", 0.0)),
                                float(getattr(b0, "cy", 0.0)),
                                str(getattr(b0, "label", "ball") or "ball"),
                                int(getattr(b0, "cls", -1) or -1),
                            )
                        except Exception:
                            self._yolo_last_hit_box = None
                        try:
                            self._yolo_last_hit_count = int(len(self._yolo_detections))
                        except Exception:
                            self._yolo_last_hit_count = 0
                    except Exception:
                        cx = cy = 0
                        rr = 0.0
                    _, frame = self.ball_tracker.apply_external_detection(
                        frame,
                        (cx, cy),
                        rr,
                        source="YOLO",
                        draw_overlay=True,
                        overlay_thickness=1,
                    )
                    try:
                        self._draw_yolo_detections(frame, self._yolo_detections)
                    except Exception:
                        pass
                    ball_center = self.ball_tracker.last_center
                    try:
                        self._ball_locked = bool(ball_center is not None and int(getattr(self.ball_tracker, "missed_frames", 0) or 0) == 0)
                        self._ball_lock_source = "YOLO" if self._ball_locked else ""
                    except Exception:
                        self._ball_locked = False
                        self._ball_lock_source = ""
                else:
                    self.ball_tracker.missed_frames += 1
                    self._ball_locked = False
                    self._ball_lock_source = ""
            else:
                # Run HSV mask ball detection + drawing on the BGR frame
                mask, frame = self.ball_tracker.process_with_mask(frame)
                #print(f"[DEBUG] After process_with_mask: last_center={self.ball_tracker.last_center} last_radius={self.ball_tracker.last_radius}")

                ball_center = self.ball_tracker.last_center
                try:
                    self._ball_locked = bool(self.ball_tracker.last_center is not None and self.ball_tracker.missed_frames == 0)
                    self._ball_lock_source = "Ball" if self._ball_locked else ""
                except Exception:
                    self._ball_locked = False
                    self._ball_lock_source = ""
        elif self.cv_ball_enabled and frame is not None:
            now_cv = time.time()
            if (now_cv - float(getattr(self, "_cv_ball_last_ts", 0.0) or 0.0)) >= float(
                getattr(self, "cv_ball_interval_s", 1.0) or 1.0
            ):
                self._cv_ball_last_ts = now_cv
                try:
                    self._cv_update_count = int(getattr(self, "_cv_update_count", 0) or 0) + 1
                except Exception:
                    self._cv_update_count = 1
                mask, frame = self.ball_tracker.process_with_cv(frame)
                try:
                    if int(getattr(self.ball_tracker, "missed_frames", 0) or 0) == 0:
                        self._cv_detect_count = int(getattr(self, "_cv_detect_count", 0) or 0) + 1
                except Exception:
                    pass
                try:
                    missed0 = int(getattr(self.ball_tracker, "missed_frames", 0) or 0)
                    self._cv_last_status = "Detected !" if missed0 == 0 else "No Ball !"
                    self._cv_last_status_ts = now_cv
                except Exception:
                    self._cv_last_status = "No Ball !"
                    self._cv_last_status_ts = now_cv
                self._cv_ball_last_mask = mask
                # Capture detector debug (thresholds + mask panes) for debug windows.
                try:
                    cv_det = getattr(self.ball_tracker, "_cv_detector", None)
                    dbg = getattr(cv_det, "last_debug", None) if cv_det is not None else None
                    if isinstance(dbg, dict):
                        self._cv_ball_last_debug_vis = dbg.get("vis", None)
                        self._cv_ball_last_debug_text = str(dbg.get("text", "") or "")
                        self._cv_ball_last_thresholds = dbg.get("thresholds", None)
                        try:
                            refine_dbg = dbg.get("refine", {}) or {}
                            x0 = refine_dbg.get("roi_x0", None)
                            y0 = refine_dbg.get("roi_y0", None)
                            x1 = refine_dbg.get("roi_x1", None)
                            y1 = refine_dbg.get("roi_y1", None)
                            if x0 is not None and y0 is not None and x1 is not None and y1 is not None:
                                self._cv_ball_last_roi_rect = (int(x0), int(y0), int(x1), int(y1))
                            else:
                                self._cv_ball_last_roi_rect = None
                        except Exception:
                            self._cv_ball_last_roi_rect = None
                        masks_dbg = dbg.get("masks", {}) or {}
                        hist_mask = masks_dbg.get("refined", None)
                        self._cv_ball_last_hist_mask = hist_mask if hist_mask is not None else mask
                        self._cv_ball_last_ranked_masks = masks_dbg.get("ranked", []) or []
                except Exception:
                    pass
                if self._cv_ball_last_hist_mask is None:
                    self._cv_ball_last_hist_mask = mask
            else:
                mask = getattr(self, "_cv_ball_last_mask", None)
                # Draw last known CV result so the overlay stays visible at UI FPS,
                # but only while detection is still "locked" (missed_frames==0).
                try:
                    c0 = getattr(self.ball_tracker, "last_center", None)
                    r0 = float(getattr(self.ball_tracker, "last_radius", 0.0) or 0.0)
                    missed0 = int(getattr(self.ball_tracker, "missed_frames", 0) or 0)
                    last_ok_ts = float(getattr(self.ball_tracker, "last_update_ts", 0.0) or 0.0)
                    ttl_s = max(
                        float(getattr(self, "cv_ball_overlay_ttl_s", 0.35) or 0.35),
                        float(getattr(self, "cv_ball_interval_s", 1.0) or 1.0) * 1.1,
                    )
                    is_fresh = (missed0 == 0) and (last_ok_ts > 0.0) and ((time.time() - last_ok_ts) <= ttl_s)
                    if is_fresh and c0 is not None and r0 > 1.0:
                        # Use raw (pre-draw) frame for HSV sampling so text doesn't perturb HSV.
                        hsv_src = self.last_display_frame_bgr if self.last_display_frame_bgr is not None else frame
                        if hasattr(self.ball_tracker, "draw_detection_overlay"):
                            self.ball_tracker.draw_detection_overlay(
                                frame,
                                source="CV",
                                hsv_source_bgr=hsv_src,
                                dashed_inner=True,
                            )
                        else:
                            cx0, cy0 = int(c0[0]), int(c0[1])
                            cv2.circle(frame, (cx0, cy0), int(round(r0)), (255, 255, 0), 2)
                            cv2.circle(frame, (cx0, cy0), 2, (255, 255, 0), -1)
                except Exception:
                    pass

            # Treat stale CV detections as "no ball" for UI perception.
            try:
                missed0 = int(getattr(self.ball_tracker, "missed_frames", 0) or 0)
                last_ok_ts = float(getattr(self.ball_tracker, "last_update_ts", 0.0) or 0.0)
                ttl_s = max(
                    float(getattr(self, "cv_ball_overlay_ttl_s", 0.35) or 0.35), 
                    float(getattr(self, "cv_ball_interval_s", 1.0) or 1.0) * 1.1,
                )
                is_fresh = (missed0 == 0) and (last_ok_ts > 0.0) and ((time.time() - last_ok_ts) <= ttl_s)
            except Exception:
                is_fresh = False
            ball_center = self.ball_tracker.last_center if is_fresh else None
            try:
                self._ball_locked = bool(ball_center is not None and int(getattr(self.ball_tracker, "missed_frames", 0) or 0) == 0)
                self._ball_lock_source = "CV" if self._ball_locked else ""
            except Exception:
                self._ball_locked = False
                self._ball_lock_source = ""

            # Shared histogram window (Object Detection Test) @ throttled rate
            try:
                src = self.last_display_frame_bgr if self.last_display_frame_bgr is not None else frame
                rr = float(getattr(self.ball_tracker, "last_radius", 0.0) or 0.0) if is_fresh else 0.0
                rank1_mask = None
                try:
                    ranked = getattr(self, "_cv_ball_last_ranked_masks", None) or []
                    if len(ranked) > 0:
                        rank1_mask = ranked[0].get("mask", None)
                except Exception:
                    rank1_mask = None
                self._maybe_update_test_hist(
                    "CV Ball",
                    src,
                    self.ball_tracker.last_center if is_fresh else None,
                    rr,
                    thresholds=getattr(self, "_cv_ball_last_thresholds", None),
                    mask_combined=rank1_mask,
                    roi_rect=getattr(self, "_cv_ball_last_roi_rect", None),
                    interval_s=float(getattr(self, "cv_ball_interval_s", 1.0) or 1.0),
                )
            except Exception:
                pass

            # CV debug window: always show thresholds + masks, even when detection is missing.
            try:
                if self.cv_debug_window is not None and self.cv_debug_window.isVisible():
                    dbg_vis = getattr(self, "_cv_ball_last_debug_vis", None)
                    vis = dbg_vis
                    txt = str(getattr(self, "_cv_ball_last_debug_text", "") or "")
                    if vis is None:
                        vis = mask
                    missed0 = int(getattr(self.ball_tracker, "missed_frames", 0) or 0)
                    use_overlay = dbg_vis is None
                    c_show = self.ball_tracker.last_center if (is_fresh and use_overlay) else None
                    r_show = float(getattr(self.ball_tracker, "last_radius", 0.0) or 0.0) if (is_fresh and use_overlay) else 0.0
                    self.cv_debug_window.update_view(
                        None,
                        vis,
                        c_show,
                        r_show,
                        missed0,
                        txt,
                    )
            except Exception:
                pass
        elif self.yolo_vision_enabled and frame is not None:
            # Yolo Vision is a test mode (no motion). Clear any stale close-enough banner.
            self._ball_close_enough = False
            now_y = time.time()
            if bool(getattr(self, "yolo_training_enabled", False)):
                try:
                    lat_s = float(getattr(self, "_yolo_last_latency_s", 0.0) or 0.0)
                except Exception:
                    lat_s = 0.0
                adaptive = max(0.25, (lat_s * 1.2) if lat_s > 0 else 0.25)
                try:
                    self.yolo_vision_interval_s = float(adaptive)
                except Exception:
                    pass
            yolo_ran = False
            if (now_y - float(getattr(self, "_yolo_vision_last_ts", 0.0) or 0.0)) >= float(
                getattr(self, "yolo_vision_interval_s", 0.25) or 0.25
            ):
                self._yolo_vision_last_ts = now_y
                yolo_ran = True
                try:
                    self._yolo_update_count = int(getattr(self, "_yolo_update_count", 0) or 0) + 1
                except Exception:
                    self._yolo_update_count = 1
                self._yolo_detections = []
                self._yolo_last_error_msg = ""
                self._yolo_last_latency_s = 0.0
                try:
                    if self.yolo_debug_window is not None and self.yolo_debug_window.isVisible():
                        ui_choice = self.yolo_debug_window.yolo_model_combo.currentData()
                        if ui_choice is None:
                            ui_choice = "best"
                        if str(ui_choice) != str(getattr(self, "yolo_model_choice", "best")):
                            self.yolo_model_choice = str(ui_choice)
                            self._apply_yolo_model_choice()
                except Exception:
                    pass
                try:
                    if frame is not None:
                        self._yolo_last_frame_shape = (int(frame.shape[0]), int(frame.shape[1]))
                except Exception:
                    pass
                if self.yolo_detector is None:
                    self._yolo_last_error_msg = "YOLO not available (install ultralytics + weights)"
                else:
                    try:
                        if bool(getattr(self, "yolo_compare_enabled", False)):
                            self._yolo_compare_detections_best = []
                            self._yolo_compare_detections_orig = []
                            best_err = ""
                            orig_err = ""
                            best_lat = 0.0
                            orig_lat = 0.0
                            if self.yolo_detector_best is not None:
                                self._yolo_compare_detections_best = self.yolo_detector_best.analyze(frame)
                                best_err = str(getattr(self.yolo_detector_best, "last_error", "") or "").strip()
                                try:
                                    best_lat = float(getattr(self.yolo_detector_best, "last_latency_s", 0.0) or 0.0)
                                except Exception:
                                    best_lat = 0.0
                            if self.yolo_detector_orig is not None:
                                self._yolo_compare_detections_orig = self.yolo_detector_orig.analyze(frame)
                                orig_err = str(getattr(self.yolo_detector_orig, "last_error", "") or "").strip()
                                try:
                                    orig_lat = float(getattr(self.yolo_detector_orig, "last_latency_s", 0.0) or 0.0)
                                except Exception:
                                    orig_lat = 0.0

                            if str(getattr(self, "yolo_model_choice", "best") or "best") == "orig":
                                self._yolo_detections = list(self._yolo_compare_detections_orig or [])
                                self._yolo_last_error_msg = orig_err
                                self._yolo_last_latency_s = orig_lat
                            else:
                                self._yolo_detections = list(self._yolo_compare_detections_best or [])
                                self._yolo_last_error_msg = best_err
                                self._yolo_last_latency_s = best_lat
                        else:
                            self._yolo_detections = self.yolo_detector.analyze(frame)
                            if getattr(self.yolo_detector, "last_error", None):
                                self._yolo_last_error_msg = str(self.yolo_detector.last_error or "").strip()
                            try:
                                self._yolo_last_latency_s = float(getattr(self.yolo_detector, "last_latency_s", 0.0) or 0.0)
                            except Exception:
                                self._yolo_last_latency_s = 0.0
                    except Exception as e:
                        self._yolo_detections = []
                        self._yolo_last_error_msg = f"YOLO exception: {e}"
                        self._yolo_last_latency_s = 0.0

                # Debug probe (any-class) when no sports-ball detections
                if (
                    yolo_ran
                    and self.yolo_detector is not None
                    and not self._yolo_detections
                ):
                    try:
                        if (now_y - float(getattr(self, "_yolo_probe_last_ts", 0.0) or 0.0)) >= float(
                            getattr(self, "_yolo_probe_interval_s", 2.0) or 2.0
                        ):
                            self._yolo_probe_last_ts = now_y
                            self._yolo_probe_boxes = []
                            self._yolo_probe_error_msg = ""
                            self._yolo_probe_latency_s = 0.0
                            probe_conf = float(getattr(self, "_yolo_probe_conf", 0.001) or 0.001)
                            self._yolo_probe_boxes = self.yolo_detector.probe(
                                frame,
                                conf=probe_conf,
                                max_det=5,
                            )
                            if getattr(self.yolo_detector, "last_probe_error", None):
                                self._yolo_probe_error_msg = str(self.yolo_detector.last_probe_error or "").strip()
                            try:
                                self._yolo_probe_latency_s = float(
                                    getattr(self.yolo_detector, "last_probe_latency_s", 0.0) or 0.0
                                )
                            except Exception:
                                self._yolo_probe_latency_s = 0.0
                    except Exception as e:
                        self._yolo_probe_boxes = []
                        self._yolo_probe_error_msg = f"probe exception: {e}"
                        self._yolo_probe_latency_s = 0.0

            # Ball Training capture (use best YOLO detection)
            if bool(getattr(self, "yolo_training_enabled", False)) and yolo_ran:
                if self._yolo_detections:
                    b0 = self._yolo_detections[0]
                    try:
                        x1 = float(getattr(b0, "x1", 0.0))
                        y1 = float(getattr(b0, "y1", 0.0))
                        x2 = float(getattr(b0, "x2", 0.0))
                        y2 = float(getattr(b0, "y2", 0.0))
                        conf = float(getattr(b0, "conf", 0.0) or 0.0)
                    except Exception:
                        x1 = y1 = x2 = y2 = 0.0
                        conf = 0.0
                    h0, w0 = frame.shape[:2]
                    if not self._yolo_train_box_sane(x1, y1, x2, y2, w0, h0):
                        self._yolo_training_recent_boxes.clear()
                        self._yolo_training_status_msg = "Train: bbox rejected (sanity)"
                    elif not (0.01 <= conf <= 0.99):
                        self._yolo_training_recent_boxes.clear()
                        self._yolo_training_status_msg = "Train: conf out of range"
                    else:
                        stable = self._yolo_train_update_recent((x1, y1, x2, y2))
                        if not stable:
                            self._yolo_training_status_msg = "Train: stabilizing (3 frames)"
                        else:
                            difficulty = self._yolo_train_assign_difficulty(conf)
                            if not self._yolo_train_bucket_allowed(difficulty):
                                self._yolo_training_status_msg = f"Train: {difficulty} bucket full"
                            else:
                                src = self.last_display_frame_bgr if self.last_display_frame_bgr is not None else frame
                                try:
                                    self._yolo_train_save_sample(
                                        src,
                                        x1=x1,
                                        y1=y1,
                                        x2=x2,
                                        y2=y2,
                                        conf=conf,
                                        difficulty=difficulty,
                                    )
                                    self._yolo_training_status_msg = "Train: saved"
                                except Exception:
                                    self._yolo_training_status_msg = "Train: save failed"
                else:
                    self._yolo_training_recent_boxes.clear()
                    self._yolo_training_status_msg = "Train: no detection"

                self._update_yolo_train_hist_window()
                self._yolo_training_prompt()
                if int(getattr(self, "yolo_training_count", 0) or 0) >= int(self.yolo_training_target or 256):
                    self._stop_yolo_training(reason="Training complete")

            # Apply best YOLO box (if any) as ball center for tracking
            if self._yolo_detections:
                b0 = self._yolo_detections[0]
                try:
                    cx = int(round(float(getattr(b0, "cx", 0.0))))
                    cy = int(round(float(getattr(b0, "cy", 0.0))))
                    x1 = float(getattr(b0, "x1", 0.0))
                    y1 = float(getattr(b0, "y1", 0.0))
                    x2 = float(getattr(b0, "x2", 0.0))
                    y2 = float(getattr(b0, "y2", 0.0))
                    rr = 0.5 * max(6.0, min(abs(x2 - x1), abs(y2 - y1)))
                    if yolo_ran:
                        self._yolo_last_hit_ts = now_y
                    try:
                        self._yolo_last_hit_conf = float(getattr(b0, "conf", 0.0) or 0.0)
                    except Exception:
                        self._yolo_last_hit_conf = 0.0
                    try:
                        self._yolo_last_hit_box = (
                            x1,
                            y1,
                            x2,
                            y2,
                            float(getattr(b0, "cx", 0.0)),
                            float(getattr(b0, "cy", 0.0)),
                            str(getattr(b0, "label", "ball") or "ball"),
                            int(getattr(b0, "cls", -1) or -1),
                        )
                    except Exception:
                        self._yolo_last_hit_box = None
                    try:
                        self._yolo_last_hit_count = int(len(self._yolo_detections))
                    except Exception:
                        self._yolo_last_hit_count = 0
                except Exception:
                    cx = cy = 0
                    rr = 0.0
                _, frame = self.ball_tracker.apply_external_detection(
                    frame,
                    (cx, cy),
                    rr,
                    source="YOLO",
                    draw_overlay=True,
                    overlay_thickness=1,
                )
                try:
                    self._draw_yolo_detections(frame, self._yolo_detections)
                except Exception:
                    pass
                ball_center = self.ball_tracker.last_center
                try:
                    self._ball_locked = bool(ball_center is not None and int(getattr(self.ball_tracker, "missed_frames", 0) or 0) == 0)
                    self._ball_lock_source = "YOLO" if self._ball_locked else ""
                except Exception:
                    self._ball_locked = False
                    self._ball_lock_source = ""
            else:
                self.ball_tracker.missed_frames += 1
                self._ball_locked = False
                self._ball_lock_source = ""

            # Shared histogram window (Object Detection Test)
            try:
                src = self.last_display_frame_bgr if self.last_display_frame_bgr is not None else frame
                rr = float(getattr(self.ball_tracker, "last_radius", 0.0) or 0.0)
                self._maybe_update_test_hist(
                    "Yolo Vision",
                    src,
                    ball_center,
                    rr,
                    interval_s=float(getattr(self, "yolo_vision_interval_s", 1.0) or 1.0),
                )
            except Exception:
                pass

            # YOLO debug window (rich status + overlay)
            try:
                self._update_yolo_debug_view(frame)
            except Exception:
                pass
            # YOLO compare window (best vs original)
            try:
                self._update_yolo_compare_view(frame)
            except Exception:
                pass
            try:
                if self.yolo_compare_enabled:
                    if self.yolo_compare_window is None:
                        self._ensure_yolo_compare_window()
                    elif not self.yolo_compare_window.isVisible():
                        self.yolo_compare_window.show()
                        self.yolo_compare_window.raise_()
            except Exception:
                pass
        else:
            self._ball_locked = False
            self._ball_lock_source = ""
            self._ball_close_enough = False

        # Common tracking behavior (AUTONOMOUS) — ONLY for "Ball" mode.
        if self.ball_mode_enabled and frame is not None:
            mode = self.ball_tracker.tracking_mode

            # If user switches to BODY mode, center head once.
            self._handle_tracking_mode_transition(mode)

            # Body tracking runs in FULL and BODY modes (independent of head tracking).
            if (
                mode in (TRACKING_MODE_FULL, TRACKING_MODE_BODY)
                and self.use_dog_video
                and self.dog_client is not None
                and getattr(self.dog_client, "tcp_flag", False)
            ):
                if ball_center is not None and self.ball_tracker.missed_frames == 0:
                    # Reset lost-search state when we reacquire a solid lock.
                    self._lost_search_state = "idle"
                    self._lost_search_sent_stop = False
                    self._lost_search_phase = "scan"
                    self._lost_search_phase_start_ts = 0.0
                    self._update_full_body_tracking(ball_center, frame.shape)
                else:
                    # Lost-ball behavior: keep searching (forward) and avoid obstacles (sonic).
                    if self.ball_tracker.missed_frames == 1:
                        if not self._lost_search_sent_stop:
                            self.send_stop_motion()
                            self._lost_search_sent_stop = True
                        self._lost_search_state = "idle"
                        self._lost_search_phase = "scan"
                        self._lost_search_phase_start_ts = 0.0
                        try:
                            self.ball_tracker.body_debug_lines = [
                                "SEARCH:hold (lost=1)",
                                f"dist:{float(getattr(self, 'distance_cm', 0.0) or 0.0):.1f}cm",
                            ]
                        except Exception:
                            pass
                    elif self.ball_tracker.missed_frames >= 2:
                        # Allow a new close-enough completion when we truly lose the ball.
                        # (Does not cancel an already-running OFF timer.)
                        self._close_enough_latched = False
                        self._update_lost_ball_search(frame.shape)

            # Head tracking (Dog video only)
            if (
                self.head_tracking_enabled
                and self.use_dog_video
                and self.dog_client is not None
                and getattr(self.dog_client, "tcp_flag", False)
                and self.last_dog_frame_height > 0
            ):
                # FULL mode: lock head at neutral for stable ranging; do not run head tracking.
                if bool(getattr(self, "full_lock_head_in_full", True)) and mode == TRACKING_MODE_FULL:
                    if not bool(getattr(self, "_full_head_sent_once", False)):
                        neutral = 90
                        try:
                            neutral = int(round(getattr(self.head_tracker.cfg, "neutral_deg", 90)))
                        except Exception:
                            pass
                        self.send_head_angle(neutral)
                        self._full_head_last_sent_ts = time.time()
                        self._full_head_sent_once = True
                else:
                    if mode == TRACKING_MODE_HEAD and ball_center is not None and self.ball_tracker.missed_frames == 0:
                        _, cy = ball_center
                        angle = self.head_tracker.update_from_ball(cy, self.last_dog_frame_height)
                        if angle is not None:
                            self.send_head_angle(int(round(angle)))
                    else:
                        if mode == TRACKING_MODE_HEAD and self.ball_tracker.missed_frames >= 2:
                            if self.ball_tracker.missed_frames == 2:
                                self.head_tracker.start_search()
                            angle = self.head_tracker.search_for_ball()
                            if angle is not None:
                                self.send_head_angle(int(round(angle)))

        # ---- GPT Vision detection (test module) ----
        if self.ai_vision_enabled and frame is not None:
            now_ai = time.time()
            # In one-shot mode, only call the API when a click has armed a request.
            if self.ai_one_shot_mode and not bool(getattr(self, "_ai_one_shot_pending", False)):
                # Still allow drawing of last detections, but do not call API.
                pass
            elif not bool(getattr(self, "_ai_request_sent", False)):
                try:
                    print("[GPT] Sending frame to vision model...")
                    src_frame = self.last_display_frame_bgr if self.last_display_frame_bgr is not None else frame
                    try:
                        h_src, w_src = src_frame.shape[:2]
                        src_tag = "last_display_frame" if self.last_display_frame_bgr is not None else "current_frame"
                        print(f"[GPT] Frame source: {src_tag} size={w_src}x{h_src}")
                    except Exception:
                        pass
                    self._ai_detections = self.ai_detector.analyze(src_frame)
                    print(
                        f"[GPT] Response: {len(self._ai_detections)} candidates"
                        + (f" (latency {self.ai_detector.last_latency_s:.2f}s)" if self.ai_detector.last_latency_s else "")
                    )
                    if self.ai_detector.last_error:
                        self._disable_ai_vision_due_to_error(self.ai_detector.last_error)
                        self._ai_last_ts = now_ai
                        self._ai_request_sent = True
                        return
                    # Inform user if AI returned no candidates
                    if not self._ai_detections:
                        self._set_ai_status("GPT Vision: no ball detected (0 candidates)")
                    else:
                        # Clear stale status on success; filtering may set a new one below.
                        self._ai_status_msg = ""
                        self._ai_status_ts = 0.0
                    raw_text = getattr(self.ai_detector, "last_raw_text", None)
                    if raw_text:
                        print("[GPT] Raw response:\n" + str(raw_text))
                    # Post-filter detections by score + HSV (to reduce false positives)
                    # Disabled in one-shot trial mode: show whatever the model returned.
                    if (not self.ai_one_shot_mode) and src_frame is not None and self._ai_detections:
                        try:
                            hsv_img = cv2.cvtColor(src_frame, cv2.COLOR_BGR2HSV)
                        except Exception:
                            hsv_img = None
                        h_ai, w_ai = src_frame.shape[:2]
                        filtered = []
                        rejected_hue = 0
                        rejected_sv = 0
                        rejected_score = 0
                        for idx, det in enumerate(self._ai_detections, start=1):
                            try:
                                if isinstance(det, dict):
                                    x_val = det.get("x", 0)
                                    y_val = det.get("y", 0)
                                    r_val = det.get("r", 0)
                                    score_val = det.get("score", 0.0)
                                else:
                                    x_val = getattr(det, "x", 0)
                                    y_val = getattr(det, "y", 0)
                                    r_val = getattr(det, "r", 0)
                                    score_val = getattr(det, "score", 0.0)
                                x_f = float(x_val)
                                y_f = float(y_val)
                                r_f = float(r_val)
                                if 0 < x_f <= 1.0 and 0 < y_f <= 1.0 and w_ai > 1 and h_ai > 1:
                                    x_f *= w_ai
                                    y_f *= h_ai
                                if 0 < r_f <= 1.0 and min(w_ai, h_ai) > 1:
                                    r_f *= min(w_ai, h_ai)
                                x = int(round(x_f))
                                y = int(round(y_f))
                                r = float(r_f)
                            except Exception:
                                continue
                            try:
                                score_f = float(score_val)
                            except Exception:
                                score_f = 0.0
                            if score_f < float(getattr(self, "ai_score_min", 0.0)):
                                rejected_score += 1
                                continue
                            if (
                                self.ai_hsv_filter_enabled
                                and hsv_img is not None
                                and 0 <= x < w_ai
                                and 0 <= y < h_ai
                            ):
                                try:
                                    H, S, V = [int(v) for v in hsv_img[y, x]]
                                except Exception:
                                    H, S, V = 0, 0, 0
                                min_s = int(getattr(self, "ai_min_s", 0))
                                min_v = int(getattr(self, "ai_min_v", 0))
                                if S < min_s or V < min_v:
                                    print(f"[GPT] Reject #{idx}@({x},{y}): HSV({H},{S},{V}) - S<{min_s} or V<{min_v}")
                                    rejected_sv += 1
                                    continue
                                ok_h = False
                                for lo, hi in getattr(self, "ai_hue_ranges", [(0, 179)]):
                                    if int(lo) <= H <= int(hi):
                                        ok_h = True
                                        break
                                if not ok_h:
                                    print(f"[GPT] Reject #{idx}@({x},{y}): HSV({H},{S},{V}) - Hue not in {self.ai_hue_ranges}")
                                    rejected_hue += 1
                                    continue
                            filtered.append(det)
                        if filtered:
                            print(f"[GPT] Filtered: {len(filtered)}/{len(self._ai_detections)} kept")
                            self._ai_status_msg = ""
                            self._ai_status_ts = 0.0
                        else:
                            print("[GPT] Filtered: 0 kept")
                            # Surface why on the Color window
                            if self.ai_hsv_filter_enabled and (rejected_hue or rejected_sv):
                                why = []
                                if rejected_hue:
                                    why.append("Hue")
                                if rejected_sv:
                                    why.append("S/V")
                                why_s = "+".join(why) if why else "HSV"
                                self._set_ai_status(f"GPT Vision: rejected by {why_s} filter (try disabling GPT HSV filter)")
                            elif rejected_score:
                                self._set_ai_status("GPT Vision: rejected by score filter")
                            else:
                                self._set_ai_status("GPT Vision: 0 kept after filtering")
                        self._ai_detections = filtered
                    # Auto-calibrate HSV ranges from the best AI detection
                    if (not self.ai_one_shot_mode) and src_frame is not None and self._ai_detections:
                        try:
                            best_det = max(
                                self._ai_detections,
                                key=lambda d: float(d.get("score", 0.0)) if isinstance(d, dict) else float(getattr(d, "score", 0.0)),
                            )
                        except Exception:
                            best_det = self._ai_detections[0]
                        self._auto_calibrate_hsv_from_ai(src_frame, best_det)
                    # Refine AI circles using HSV mask within ROI
                    if (not self.ai_one_shot_mode) and src_frame is not None and self._ai_detections and self.ai_refine_enabled:
                        refined = []
                        for det in self._ai_detections:
                            refined.append(self._refine_ai_circle(src_frame, det))
                        self._ai_detections = refined
                    # Log candidate info: diameter, center HSV, and (x,y)
                    if src_frame is not None and self._ai_detections:
                        try:
                            hsv_img = cv2.cvtColor(src_frame, cv2.COLOR_BGR2HSV)
                        except Exception:
                            hsv_img = None
                        h_ai, w_ai = src_frame.shape[:2]
                        for idx, det in enumerate(self._ai_detections, start=1):
                            try:
                                if isinstance(det, dict):
                                    x_val = det.get("x", 0)
                                    y_val = det.get("y", 0)
                                    r_val = det.get("r", 0)
                                    score_val = det.get("score", 0.0)
                                else:
                                    x_val = getattr(det, "x", 0)
                                    y_val = getattr(det, "y", 0)
                                    r_val = getattr(det, "r", 0)
                                    score_val = getattr(det, "score", 0.0)
                                x_f = float(x_val)
                                y_f = float(y_val)
                                r_f = float(r_val)
                                if 0 < x_f <= 1.0 and 0 < y_f <= 1.0 and w_ai > 1 and h_ai > 1:
                                    x_f *= w_ai
                                    y_f *= h_ai
                                if 0 < r_f <= 1.0 and min(w_ai, h_ai) > 1:
                                    r_f *= min(w_ai, h_ai)
                                x = int(round(x_f))
                                y = int(round(y_f))
                                r = float(r_f)
                                norm_xy = bool(0 < float(x_val) <= 1.0 and 0 < float(y_val) <= 1.0)
                                norm_r = bool(0 < float(r_val) <= 1.0)
                            except Exception:
                                print(f"[AI] #{idx} raw: {det}")
                                continue
                            x = max(0, min(w_ai - 1, x))
                            y = max(0, min(h_ai - 1, y))
                            d_text = "D?" if r <= 0 else f"D{int(round(2 * r))}"
                            H = S = V = 0
                            if hsv_img is not None:
                                try:
                                    H, S, V = [int(v) for v in hsv_img[y, x]]
                                except Exception:
                                    H, S, V = 0, 0, 0
                            try:
                                score_f = float(score_val)
                            except Exception:
                                score_f = 0.0
                            ai_hsv = None
                            try:
                                if isinstance(det, dict):
                                    ai_hsv = det.get("hsv", None)
                                else:
                                    ai_hsv = getattr(det, "hsv", None)
                            except Exception:
                                ai_hsv = None
                            ai_hsv_text = ""
                            if isinstance(ai_hsv, (list, tuple)) and len(ai_hsv) >= 3:
                                try:
                                    ah, as_, av = int(ai_hsv[0]), int(ai_hsv[1]), int(ai_hsv[2])
                                    ai_hsv_text = f" AIHSV({ah},{as_},{av})"
                                except Exception:
                                    ai_hsv_text = ""
                            print(
                                f"[GPT] #{idx} raw=({x_val},{y_val},{r_val}) norm(xy={norm_xy},r={norm_r}) "
                                f"-> px=({x},{y},{int(round(r))}) {d_text}px HSV({H},{S},{V}){ai_hsv_text} score:{score_f:.2f}"
                            )
                    # Update AI histogram window with best (highest-score) detection
                    if src_frame is not None and self._ai_detections:
                        try:
                            h_ai, w_ai = src_frame.shape[:2]
                        except Exception:
                            h_ai, w_ai = 0, 0
                        best_det = None
                        best_score = -1.0
                        for det in self._ai_detections:
                            try:
                                if isinstance(det, dict):
                                    x_val = det.get("x", 0)
                                    y_val = det.get("y", 0)
                                    r_val = det.get("r", 0)
                                    score_val = det.get("score", 0.0)
                                else:
                                    x_val = getattr(det, "x", 0)
                                    y_val = getattr(det, "y", 0)
                                    r_val = getattr(det, "r", 0)
                                    score_val = getattr(det, "score", 0.0)
                                x_f = float(x_val)
                                y_f = float(y_val)
                                r_f = float(r_val)
                                if 0 < x_f <= 1.0 and 0 < y_f <= 1.0 and w_ai > 1 and h_ai > 1:
                                    x_f *= w_ai
                                    y_f *= h_ai
                                if 0 < r_f <= 1.0 and min(w_ai, h_ai) > 1:
                                    r_f *= min(w_ai, h_ai)
                                score_f = float(score_val)
                            except Exception:
                                continue
                            if score_f >= best_score:
                                best_score = score_f
                                best_det = (x_f, y_f, r_f)
                        if best_det is not None:
                            # Shared histogram window used by all object detection test modes
                            try:
                                model_label = str(getattr(self.ai_detector, "model", "") or "").strip()
                            except Exception:
                                model_label = ""
                            x_b, y_b, r_b = best_det
                            self._maybe_update_test_hist(
                                "GPT Vision",
                                src_frame,
                                (x_b, y_b),
                                float(r_b or 0.0),
                                model_label=model_label,
                                interval_s=0.0,
                            )
                    if self.ai_detector.last_error:
                        self._disable_ai_vision_due_to_error(self.ai_detector.last_error)
                except Exception as e:
                    self._ai_detections = []
                    print(f"[GPT][WARN] GPT Vision failed in pipeline: {e}")
                    self._disable_ai_vision_due_to_error(str(e) or "AI Vision pipeline exception")
                self._ai_last_ts = now_ai
                self._ai_request_sent = True
                if self.ai_one_shot_mode:
                    # Disarm so we do not call API again until next click.
                    self._ai_one_shot_pending = False

            if self._ai_detections:
                # Draw on main color frame
                self._draw_ai_detections(frame, self._ai_detections)

            # Beep every 3 seconds while AI Vision mode is ON (no LED flash)
            # Disabled for one-shot trial mode to avoid annoying repeats.
            if not self.ai_one_shot_mode:
                try:
                    now_beep = time.time()
                    last_beep = float(getattr(self, "_ai_beep_last_ts", 0.0) or 0.0)
                    if (now_beep - last_beep) >= 3.0:
                        self._beep_pattern(beeps=1, on_s=0.08, off_s=0.00)
                        self._ai_beep_last_ts = now_beep
                except Exception:
                    pass

        #------- Update Mask window if open -------
        if (
            self.ball_mode_enabled
            and self.ball_mask_window is not None
            and self.ball_mask_window.isVisible()
        ):
            # Always use the original color frame for the picker/histogram
            self.ball_mask_window.update_from_frame(self.last_display_frame_bgr, mask)

        # Apply any pending cheer banner updates from background timers.
        self._apply_mask_cheer_if_needed()

        # Start barking only after OFF has been reached (scheduled by completion timer).
        if bool(getattr(self, "_bark_pending_start", False)):
            self._bark_pending_start = False
            if self._bark_should_run():
                self._start_barking()

        # If barking is active but the conditions are no longer true, stop it.
        if bool(getattr(self, "_bark_active", False)) and not self._bark_should_run():
            self._stop_barking()
            self._set_mask_cheer("", visible=False)
    
        #----------------------

        # Always-on CV histogram panels (picker/frame + top-ranked contours)
        try:
            src_hist = self.last_display_frame_bgr if self.last_display_frame_bgr is not None else frame
            self._maybe_update_cv_hist(src_hist)
        except Exception:
            pass


        # ----------------------------------
        # Convert to RGB for Qt display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape

        # ---- Deadzone guide overlays (dashed) ----
        # Body tracking: X deadzone (turn-to-center band)
        # Head tracking: Y deadband (no head motion within this band)
        def draw_dashed_vline(x: int, color, thickness: int = 1, dash: int = 10, gap: int = 6):
            x = int(max(0, min(w - 1, x)))
            y = 0
            while y < h:
                y2 = min(h - 1, y + dash)
                cv2.line(frame_rgb, (x, y), (x, y2), color, thickness)
                y += dash + gap

        def draw_dashed_hline(y: int, color, thickness: int = 1, dash: int = 10, gap: int = 6):
            y = int(max(0, min(h - 1, y)))
            x = 0
            while x < w:
                x2 = min(w - 1, x + dash)
                cv2.line(frame_rgb, (x, y), (x2, y), color, thickness)
                x += dash + gap

        # Only show overlays when ball tracking is on.
        tracking_mode = getattr(self.ball_tracker, "tracking_mode", None) if self.ball_mode_enabled else None
        if self.ball_mode_enabled and w > 0 and h > 0:
            cx = w / 2.0
            cy = h / 2.0

            # X deadzone for body tracking (in FULL/BODY modes)
            if tracking_mode in (TRACKING_MODE_FULL, TRACKING_MODE_BODY):
                try:
                    deadzone_ratio = float(getattr(self.ball_tracker, "body_deadzone_ratio", 0.18))
                except Exception:
                    deadzone_ratio = 0.18
                deadzone_ratio = max(0.05, min(0.50, deadzone_ratio))
                x_dead = max(20.0, w * deadzone_ratio)
                x1 = int(round(cx - x_dead))
                x2 = int(round(cx + x_dead))
                color_x = (0, 255, 255)  # cyan (RGB)
                draw_dashed_vline(x1, color_x, thickness=1)
                draw_dashed_vline(x2, color_x, thickness=1)

            # Y deadzone for head tracking (in FULL/HEAD modes)
            # Draw it even if head tracking is disabled, so users can see the band.
            if (
                tracking_mode in (TRACKING_MODE_FULL, TRACKING_MODE_HEAD)
                and hasattr(self, "head_tracker")
                and hasattr(self.head_tracker, "cfg")
            ):
                try:
                    deadband = float(getattr(self.head_tracker.cfg, "deadband", 0.02))
                except Exception:
                    deadband = 0.02
                deadband = max(0.0, min(0.5, deadband))
                # deadband is normalized by center_y (frame_h/2)
                y_dead = (h / 2.0) * deadband
                y1 = int(round(cy - y_dead))
                y2 = int(round(cy + y_dead))
                color_y = (255, 0, 255)  # magenta (RGB)
                draw_dashed_hline(y1, color_y, thickness=1)
                draw_dashed_hline(y2, color_y, thickness=1)

            # Center '+' marker
            x0, y0 = int(round(cx)), int(round(cy))
            plus_color = (255, 200, 0)  # amber-ish (RGB)
            plus_size = 10
            cv2.line(frame_rgb, (x0 - plus_size, y0), (x0 + plus_size, y0), plus_color, 1)
            cv2.line(frame_rgb, (x0, y0 - plus_size), (x0, y0 + plus_size), plus_color, 1)

        # Smaller font
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.4
        thickness = 1

        # IP + ports (top-left)
        cv2.putText(
            frame_rgb,
            self.ip,
            (10, 15),
            font,
            scale,
            (0, 255, 255),
            thickness,
        )
        cv2.putText(
            frame_rgb,
            f"Video {self.video_port}, Ctrl {self.control_port}",
            (10, 35),
            font,
            scale,
            (0, 255, 255),
            thickness,
        )

        # State text (centered near top)
        left_disp = int(getattr(self, "left_state_seconds", 0) or 0)
        right_disp = int(getattr(self, "right_state_seconds", 0) or 0)
        state_label = str(getattr(self, "state_name", ""))

        # Smooth display: if we know when WORKING_TIME was last received,
        # interpolate counters using inferred tick directions.
        anchor_ts = getattr(self, "_working_time_anchor_ts", None)
        anchor_left = getattr(self, "_working_time_anchor_left", None)
        anchor_right = getattr(self, "_working_time_anchor_right", None)
        if (
            isinstance(anchor_ts, (int, float))
            and anchor_ts > 0
            and isinstance(anchor_left, int)
            and isinstance(anchor_right, int)
        ):
            dt = time.time() - float(anchor_ts)
            if 0.0 <= dt <= 20.0:
                dir_left = int(getattr(self, "_working_time_left_dir", 0) or 0)
                dir_right = int(getattr(self, "_working_time_right_dir", 0) or 0)
                step = int(dt)
                left_disp = max(0, int(anchor_left) + step * dir_left)
                right_disp = max(0, int(anchor_right) + step * dir_right)

        state_text = f"{left_disp}s {state_label} {right_disp}s"
        (state_size, _) = cv2.getTextSize(state_text, font, scale, thickness)
        state_x = (w - state_size[0]) // 2
        state_y = 30
        cv2.putText(
            frame_rgb,
            state_text,
            (state_x, state_y),
            font,
            scale,
            (255, 255, 255),
            thickness,
        )

        # Telemetry overlay (top-right)
        dog_online = (
            self.dog_client is not None
            and getattr(self.dog_client, "tcp_flag", False)
            and self.server_control_ok
        )

        # GPT Vision overlay hint (top-left, under IP/ports)
        ai_err = str(getattr(self, "_ai_last_error_msg", "") or "").strip()
        if self.ai_vision_enabled:
            if bool(getattr(self, "ai_one_shot_mode", False)):
                pending = bool(getattr(self, "_ai_one_shot_pending", False))
                hint = "GPT Vision: SNAPSHOT (requesting...)" if pending else "GPT Vision: SNAPSHOT (press button again to clear)"
            else:
                hint = "GPT Vision: ON (press button again to clear)"
            cv2.putText(
                frame_rgb,
                hint,
                (10, 55),
                font,
                scale,
                (0, 255, 255),
                thickness,
            )
            # Show a short status hint when AI returns nothing or is filtered out
            try:
                ai_status = str(getattr(self, "_ai_status_msg", "") or "").strip()
                ai_until = float(getattr(self, "_ai_status_ts", 0.0) or 0.0)
            except Exception:
                ai_status = ""
                ai_until = 0.0
            if (not ai_err) and ai_status and (time.time() <= ai_until):
                cv2.putText(
                    frame_rgb,
                    ai_status,
                    (10, 75),
                    font,
                    scale,
                    (255, 255, 0),
                    thickness,
                )

            # Show GPT model name used for detections
            try:
                model_label = str(getattr(self.ai_detector, "model", "") or "").strip()
            except Exception:
                model_label = ""
            if model_label:
                cv2.putText(
                    frame_rgb,
                    f"GPT model: {model_label}",
                    (10, 95),
                    font,
                    scale,
                    (0, 255, 255),
                    thickness,
                )
            # Reference center mark '+' for AI Vision
            cx_ai = int(round(w / 2))
            cy_ai = int(round(h / 2))
            cross = 8
            cv2.line(frame_rgb, (cx_ai - cross, cy_ai), (cx_ai + cross, cy_ai), (0, 255, 255), 1)
            cv2.line(frame_rgb, (cx_ai, cy_ai - cross), (cx_ai, cy_ai + cross), (0, 255, 255), 1)
        # CV Ball / Yolo Vision hints (avoid overlapping GPT hint lines)
        y_hint = 55
        if self.ai_vision_enabled:
            y_hint = 115
        if bool(getattr(self, "cv_ball_enabled", False)):
            try:
                cv_int = float(getattr(self, "cv_ball_interval_s", 1.0) or 1.0)
            except Exception:
                cv_int = 1.0
            cv_hz = (1.0 / cv_int) if cv_int > 0 else 0.0
            try:
                cv_n = int(getattr(self, "_cv_update_count", 0) or 0)
            except Exception:
                cv_n = 0
            try:
                cv_det_n = int(getattr(self, "_cv_detect_count", 0) or 0)
            except Exception:
                cv_det_n = 0
            cv2.putText(
                frame_rgb,
                f"CV Ball: ON #{cv_n} @ {cv_hz:.1f}Hz, Detected #{cv_det_n}",
                (10, y_hint),
                font,
                scale,
                (255, 255, 0),
                thickness,
            )
            y_hint += 20
            try:
                cv_status = str(getattr(self, "_cv_last_status", "") or "").strip()
            except Exception:
                cv_status = ""
            if cv_status:
                cv_status_text = f"Status={cv_status}"
                cv_status_color = (0, 255, 0) if "Detected" in cv_status else (0, 0, 255)
                cv2.putText(
                    frame_rgb,
                    cv_status_text,
                    (10, y_hint),
                    font,
                    scale,
                    (0, 0, 0),
                    thickness + 2,
                )
                cv2.putText(
                    frame_rgb,
                    cv_status_text,
                    (10, y_hint),
                    font,
                    scale,
                    cv_status_color,
                    thickness,
                )
                y_hint += 20
        if bool(getattr(self, "yolo_vision_enabled", False)):
            yolo_err2 = str(getattr(self, "_yolo_last_error_msg", "") or "").strip()
            try:
                y_int = float(getattr(self, "yolo_vision_interval_s", 1.0) or 1.0)
            except Exception:
                y_int = 1.0
            y_hz = (1.0 / y_int) if y_int > 0 else 0.0
            try:
                y_conf = float(getattr(getattr(self, "yolo_detector", None), "conf", 0.0) or 0.0)
            except Exception:
                y_conf = 0.0
            y_conf_text = f", Conf >= {y_conf:.2f}" if y_conf > 0 else ""
            try:
                y_n = int(getattr(self, "_yolo_update_count", 0) or 0)
            except Exception:
                y_n = 0
            if yolo_err2:
                cv2.putText(
                    frame_rgb,
                    f"Yolo Vision #{y_n} @ {y_hz:.1f}Hz{y_conf_text}: {yolo_err2}",
                    (10, y_hint),
                    font,
                    scale,
                    (0, 165, 255),
                    thickness,
                )
            else:
                yolo_n2 = len(getattr(self, "_yolo_detections", []) or [])
                cv2.putText(
                    frame_rgb,
                    f"Yolo Vision: {yolo_n2} boxes #{y_n} @ {y_hz:.1f}Hz{y_conf_text}",
                    (10, y_hint),
                    font,
                    scale,
                    (0, 255, 0),
                    thickness,
                )
            y_hint += 20
            try:
                model_path = str(getattr(getattr(self, "yolo_detector", None), "model_path", "") or "")
                if model_path:
                    cv2.putText(
                        frame_rgb,
                        f"YOLO model: {os.path.basename(model_path)}",
                        (10, y_hint),
                        font,
                        scale,
                        (180, 220, 255),
                        thickness,
                    )
                    y_hint += 20
            except Exception:
                pass

        # YOLO Ball Training overlay
        if bool(getattr(self, "yolo_training_enabled", False)):
            try:
                ds_label = str(getattr(self, "_yolo_training_dataset_label", "") or "")
            except Exception:
                ds_label = ""
            try:
                cur = int(getattr(self, "yolo_training_count", 0) or 0)
            except Exception:
                cur = 0
            tgt = int(getattr(self, "yolo_training_target", 256) or 256)
            msg = f"YOLO datasets creating...  #{cur}/{tgt} {ds_label}".strip()
            cv2.putText(frame_rgb, msg, (10, y_hint), font, scale, (0, 0, 0), thickness + 2)
            cv2.putText(frame_rgb, msg, (10, y_hint), font, scale, (180, 80, 255), thickness)
            y_hint += 20
            try:
                prompt = str(getattr(self, "_yolo_training_status_msg", "") or "").strip()
            except Exception:
                prompt = ""
            if prompt:
                cv2.putText(frame_rgb, prompt, (10, y_hint), font, scale, (0, 0, 0), thickness + 2)
                cv2.putText(frame_rgb, prompt, (10, y_hint), font, scale, (255, 255, 255), thickness)
                y_hint += 20

        elif ai_err:
            cv2.putText(
                frame_rgb,
                "GPT Vision: OFF (error)",
                (10, 55),
                font,
                scale,
                (0, 0, 255),
                thickness,
            )

        # Ball tracking status overlay (Color window)
        try:
            status_y = y_hint + 10
            if bool(getattr(self, "ball_mode_enabled", False)) and bool(getattr(self, "_ball_close_enough", False)):
                msg = "Ball is Close Enough"
                cv2.putText(frame_rgb, msg, (10, status_y), font, 0.7, (0, 0, 0), 4)
                cv2.putText(frame_rgb, msg, (10, status_y), font, 0.7, (0, 255, 0), 2)
            else:
                cmd_name = str(getattr(self, "_body_cmd_name", "") or "").strip()
                if cmd_name:
                    msg = f"Move: {cmd_name}"
                    cv2.putText(frame_rgb, msg, (10, status_y), font, 0.55, (0, 0, 0), 3)
                    cv2.putText(frame_rgb, msg, (10, status_y), font, 0.55, (255, 255, 0), 1)
                elif bool(getattr(self, "_ball_locked", False)):
                    source = str(getattr(self, "_ball_lock_source", "") or "")
                    if source.upper() == "YOLO":
                        msg = "Ball Detected by Yolo"
                    elif source.upper() == "CV":
                        msg = "Ball Lock by CV"
                    elif source:
                        msg = f"Ball LOCK ({source})"
                    else:
                        msg = "Ball LOCK"
                    cv2.putText(frame_rgb, msg, (10, status_y), font, 0.55, (0, 0, 0), 3)
                    cv2.putText(frame_rgb, msg, (10, status_y), font, 0.55, (0, 255, 255), 1)
        except Exception:
            pass


        # Strong warning overlay if API access failed (show even if GPT is off)
        if ai_err:
            warn1 = "GPT VISION ERROR: API ACCESS FAILED"
            warn2 = f"Reason: {ai_err}"
            cv2.putText(frame_rgb, warn1, (10, 75), font, scale, (0, 0, 255), thickness + 1)
            cv2.putText(frame_rgb, warn1, (10, 75), font, scale, (255, 255, 255), thickness)
            cv2.putText(frame_rgb, warn2, (10, 90), font, scale, (0, 0, 255), thickness + 1)
            cv2.putText(frame_rgb, warn2, (10, 90), font, scale, (255, 255, 255), thickness)

        if dog_online and self.telemetry_valid:
            dist_text = f"{self.distance_cm:.1f}cm"
            volt_text = f"{self.battery_v:.2f}V"
        else:
            dist_text = "--.-cm"
            volt_text = "-.--V"

        rx_text = f"RX:{self.rx_fps:.1f}fps"
        ui_text = f"UI:{self.display_fps:.1f}fps"

        gap = 8
        (dist_size, _) = cv2.getTextSize(dist_text, font, scale, thickness)
        (volt_size, _) = cv2.getTextSize(volt_text, font, scale, thickness)
        (rx_size, _) = cv2.getTextSize(rx_text, font, scale, thickness)
        (ui_size, _) = cv2.getTextSize(ui_text, font, scale, thickness)

        total_width = (
            dist_size[0] + volt_size[0] + rx_size[0] + ui_size[0] + 3 * gap
        )
        start_x = w - total_width - 10
        y_top = 15
        x = start_x

        def put_text_with_outline(img, text, org, color):
            cv2.putText(
                img,
                text,
                (org[0] + 1, org[1] + 1),
                font,
                scale,
                (0, 0, 0),
                thickness + 1,
            )
            cv2.putText(
                img,
                text,
                org,
                font,
                scale,
                color,
                thickness,
            )

        # Distance: bright yellow with outline
        put_text_with_outline(frame_rgb, dist_text, (x, y_top), (0, 255, 255))
        x += dist_size[0] + gap

        # Voltage
        put_text_with_outline(frame_rgb, volt_text, (x, y_top), (0, 165, 255))
        x += volt_size[0] + gap

        # RX FPS (actual Dog frame rate)
        put_text_with_outline(frame_rgb, rx_text, (x, y_top), (255, 0, 255))
        x += rx_size[0] + gap

        # UI FPS (Qt draw rate)
        put_text_with_outline(frame_rgb, ui_text, (x, y_top), (0, 255, 0))

        # Shared picker sample point bottom-left
        if self.ball_tracker.sample_point is not None and self.last_display_frame_bgr is not None:
            sx, sy = self.ball_tracker.sample_point
            hsv_img = cv2.cvtColor(self.last_display_frame_bgr, cv2.COLOR_BGR2HSV)  # <-- ALWAYS use raw color frame
            h_img, w_img = hsv_img.shape[:2]  # <-- ADD THIS LINE           
            sx = max(0, min(w_img - 1, sx))
            sy = max(0, min(h_img - 1, sy))            
            Hs, Ss, Vs = [int(v) for v in hsv_img[sy, sx]]      # Get HSV at sample point ==> error to be fixed, out of bounds for axis 0 with size 480
            self.ball_tracker.sample_hsv = (Hs, Ss, Vs)
            
            # ... draw HUD ...
            cv2.circle(frame_rgb, (sx, sy), 2, (100, 255, 0), -1)   # small (size=2) filled circle (-1) at mouse click point
            text1 = f"HSV({Hs},{Ss},{Vs})"
            text2 = f"({sx},{sy})"
            put_text_with_outline(frame_rgb, text1, (5, h - 28), (100, 255, 0))  # left-bottom corner
            put_text_with_outline(frame_rgb, text2, (5, h - 12), (100, 255, 0))

            # Update the mask window HUD/histogram if visible, using RAW color frame
            if (
                self.ball_mode_enabled
                and self.ball_mask_window is not None
                and self.ball_mask_window.isVisible()
            ):
                if self.last_display_frame_bgr is not None:
                    _, mask2 = self.ball_tracker.compute_mask(self.last_display_frame_bgr)
                    self.ball_mask_window.update_from_frame(self.last_display_frame_bgr, mask2)

        # Ball center HSV info (NEW PATCH)
        if self.ball_mode_enabled and self.ball_tracker.last_center is not None:
            #print(f"[DEBUG] Drawing ball center overlay: last_center={self.ball_tracker.last_center}")
            bx, by = self.ball_tracker.last_center
            bx = int(bx)
            by = int(by)
            if 0 <= bx < frame_rgb.shape[1] and 0 <= by < frame_rgb.shape[0]:
                hsv_img = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                Hc, Sc, Vc = [int(v) for v in hsv_img[by, bx]]
                #print(f"[DEBUG] Drawing circle at ({bx},{by}), HSV=({Hc},{Sc},{Vc}), radius=4")
                cv2.circle(frame_rgb, (bx, by), 4, (255, 255, 0), -1)
                text_ball = f"Ball HSV({Hc},{Sc},{Vc})"
                put_text_with_outline(frame_rgb, text_ball, (bx + 8, by - 12), (255, 255, 0))

        # Hover HSV info (cursor-based) – does NOT move the picker
        if self.hover_xy_color is not None and self.hover_hsv_color is not None:
            cx, cy = self.hover_xy_color
            Hh, Sh, Vh = self.hover_hsv_color

            text1 = f"HSV({Hh},{Sh},{Vh})"
            text2 = f"({cx},{cy})"
            head_angle = getattr(self.head_tracker, "current_angle", None)
            text3 = (
                f"head {head_angle:.2f}d" if isinstance(head_angle, (int, float)) else "head --"
            )

            # Draw near the cursor, similar to mask window
            base_x = cx + 8
            base_y = max(15, cy - 12)

            # Use a bright yellow-ish color for hover
            put_text_with_outline(frame_rgb, text1, (base_x, base_y),     (255, 255, 0))
            put_text_with_outline(frame_rgb, text2, (base_x, base_y + 14), (255, 255, 0))
            put_text_with_outline(frame_rgb, text3, (base_x, base_y + 28), (255, 255, 0))

        # ----------------------------------
        # Convert to QPixmap
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        pixmap = pixmap.scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(pixmap)

        # Window title with resolution reflects Dog vs Mac mode
        src_name = "Dog Pi Camera" if self.use_dog_video else "Mac Camera"
        self.setWindowTitle(f"mtDogMain v2.40 - {src_name} {w}x{h}")

        self.update_status_ui()

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
        if (
            event.button() == Qt.LeftButton
            and self.last_display_frame_bgr is not None
        ):
            img_h, img_w, _ = self.last_display_frame_bgr.shape

            label_pos = self.video_label.mapFrom(self, event.pos())
            lx, ly = label_pos.x(), label_pos.y()
            label_w = self.video_label.width()
            label_h = self.video_label.height()
            scale = min(label_w / img_w, label_h / img_h)
            disp_w = int(img_w * scale)
            disp_h = int(img_h * scale)
            off_x = (label_w - disp_w) // 2
            off_y = (label_h - disp_h) // 2

            if off_x <= lx < off_x + disp_w and off_y <= ly < off_y + disp_h:
                ix = int((lx - off_x) / scale)
                iy = int((ly - off_y) / scale)
                ix = max(0, min(img_w - 1, ix))
                iy = max(0, min(img_h - 1, iy))

                hsv = cv2.cvtColor(self.last_display_frame_bgr, cv2.COLOR_BGR2HSV)
                H, S, V = [int(v) for v in hsv[iy, ix]]
                self.ball_tracker.set_sample_point((ix, iy), (H, S, V))

                # --- FIX: Immediately update Mask window picker HUD/histogram ---
                if (
                    self.ball_mode_enabled
                    and self.ball_mask_window is not None
                    and self.ball_mask_window.isVisible()
                    and self.last_display_frame_bgr is not None
                ):
                    _, mask = self.ball_tracker.compute_mask(self.last_display_frame_bgr)
                    self.ball_mask_window.update_from_frame(self.last_display_frame_bgr, mask)

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
        """
        Toggle ball tracking on/off.

        - When turning ON:
            * Load mtBall_Calib.json if present.
            * Show Mask window.
            * Enable head tracking.
        - When turning OFF:
            * Hide Mask window.
            * Save mtBall_Calib.json.
            * Disable head tracking (optionally return to neutral).
        """
        # Ball sources are mutually exclusive for test modes (Ball vs CV).
        if bool(getattr(self, "cv_ball_enabled", False)):
            self.cv_ball_enabled = False
            try:
                self.btn_CVBall.setStyleSheet(
                    """
                    QPushButton { background-color:#00bcd4; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00bcd4; }
                    """
                )
            except Exception:
                pass
        self.ball_mode_enabled = not self.ball_mode_enabled
        self.head_tracking_enabled = bool(self.ball_mode_enabled)
        state = "ON" if self.ball_mode_enabled else "OFF"
        print(f"[BALL] Ball tracking {state}.")

        if self.ball_mode_enabled:
            # Reset head controller to neutral on entry (optional)
            self.head_tracker.current_angle = self.head_tracker.cfg.neutral_deg

            # Load config (if exists)
            self.ball_tracker.load_default_config()

            # Create Mask window if needed
            if self.ball_mask_window is None:
                self.ball_mask_window = BallMaskWindow(self.ball_tracker)
                # Allow Mask window to stop barking by calling back into mtDogMain.
                try:
                    self.ball_tracker.on_clear_cheer = self._on_mask_clear_cheer
                except Exception:
                    pass

            # If a cheer banner is already active (e.g., completion happened before opening Mask), apply it.
            self._apply_mask_cheer_if_needed()

            # Make the mask image area initially the same size as the color view
            video_size = self.video_label.size()
            self.ball_mask_window.set_initial_view_size(
                video_size.width(), video_size.height()
            )

            # Place on the LEFT side of the color window if there is space,
            # otherwise fall back to the right side.
            mask_w = self.ball_mask_window.width()
            x_left = self.x() - mask_w - 20
            y_pos = self.y() + 40

            if x_left > 0:
                target_x = x_left
            else:
                target_x = self.x() + self.width() + 20

            self.ball_mask_window.move(target_x, y_pos)
            self.ball_mask_window.show()
            self.ball_mask_window.raise_()

            # Button style → green
            self.btn_Ball.setStyleSheet(
                """
                QPushButton {
                    background-color:#00c853;
                    color:#ffffff;
                    border:none;
                    border-radius:16px;
                    padding:4px 10px;
                    font-size:14px;
                }
                QPushButton:hover {
                    background-color:#ffffff;
                    color:#00c853;
                }
                """
            )
        else:
            # Hide window and save config
            if self.ball_mask_window is not None:
                self.ball_mask_window.hide()
            self.ball_tracker.save_default_config()

            # Stop any post-completion barking when ball mode is turned off.
            self._stop_barking()
            self._set_mask_cheer("", visible=False)
            self._bark_pending_start = False

            # Cancel any pending OFF timer (avoid starting barking after Ball mode is off).
            prev = getattr(self, "_close_enough_off_timer", None)
            try:
                if prev is not None and prev.is_alive():
                    prev.cancel()
            except Exception:
                pass

            # Optionally send head back to neutral when leaving Ball mode
            if (
                self.dog_client is not None
                and getattr(self.dog_client, "tcp_flag", False)
            ):
                self.head_tracker.current_angle = self.head_tracker.cfg.neutral_deg
                self.send_head_angle(int(round(self.head_tracker.current_angle)))

            self.head_tracking_enabled = False  # NEW

            # Button style → blue
            self.btn_Ball.setStyleSheet(
                """
                QPushButton {
                    background-color:#0066cc;
                    color:#ffffff;
                    border:none;
                    border-radius:16px;
                    padding:4px 10px;
                    font-size:14px;
                }
                QPushButton:hover {
                    background-color:#ffffff;
                    color:#0066cc;
                }
                """
            )

    # ------------------------------------------
    def _on_cv_debug_radial_gate_changed(self, checked: bool):
        """Toggle CV radial gate from CV debug window (experimental)."""
        try:
            self.ball_tracker.cv_radial_gate_enabled = bool(checked)
            self.ball_tracker._apply_cv_radial_gate()
            self.ball_tracker.save_default_config()
            state = "ON" if bool(checked) else "OFF"
            print(f"[CV] RadialGate {state} (debug window).")
        except Exception:
            return

    def handle_cv_ball_button(self):
        """Toggle basic CV ball tracking (no Mask window)."""
        # Clear stale overlays/results from other test modes
        self._clear_object_detection_state(clear_hist=True)
        # Ball sources are mutually exclusive (HSV / CV / YOLO)
        if self.ball_mode_enabled:
            self.ball_mode_enabled = False
            try:
                if self.ball_mask_window is not None:
                    self.ball_mask_window.hide()
            except Exception:
                pass
            try:
                self.btn_Ball.setStyleSheet(
                    """
                    QPushButton { background-color:#0066cc; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#0066cc; }
                    """
                )
            except Exception:
                pass

        if bool(getattr(self, "yolo_vision_enabled", False)):
            self.yolo_vision_enabled = False
            self._stop_yolo_training(reason="")
            try:
                self.btn_YoloVision.setStyleSheet(
                    """
                    QPushButton { background-color:#2e7d32; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#2e7d32; }
                    """
                )
            except Exception:
                pass

        # Turn off GPT Vision when switching to CV Ball
        if bool(getattr(self, "ai_vision_enabled", False)):
            self.ai_vision_enabled = False
            self._ai_one_shot_pending = False
            self._ai_request_sent = False
            self._ai_detections = []
            try:
                self.btn_AIVision.setStyleSheet(
                    """
                    QPushButton { background-color:#00a3a3; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00a3a3; }
                    """
                )
            except Exception:
                pass

        self.cv_ball_enabled = not bool(getattr(self, "cv_ball_enabled", False))
        # Test mode: do NOT move dog automatically (no head/body tracking)
        # But keep head tracking if Ball mode is active.
        self.head_tracking_enabled = bool(getattr(self, "ball_mode_enabled", False))
        state = "ON" if self.cv_ball_enabled else "OFF"
        print(f"[CV] CV Ball tracking {state}.")

        if self.cv_ball_enabled:
            self._cv_update_count = 0
            self._cv_detect_count = 0
            # Load config to reuse smoothing / tracking mode knobs
            try:
                self.ball_tracker.load_default_config()
            except Exception:
                pass
            # Reset head controller to neutral on entry
            try:
                self.head_tracker.current_angle = self.head_tracker.cfg.neutral_deg
            except Exception:
                pass

            # Show CV debug window near main window
            try:
                if self.cv_debug_window is None:
                    self.cv_debug_window = CVBallDebugWindow(
                        radial_checked=bool(getattr(self.ball_tracker, "cv_radial_gate_enabled", False)),
                        on_radial_toggle=self._on_cv_debug_radial_gate_changed,
                    )
                else:
                    try:
                        self.cv_debug_window.set_radial_gate_checked(
                            bool(getattr(self.ball_tracker, "cv_radial_gate_enabled", False))
                        )
                    except Exception:
                        pass
                self.cv_debug_window.move(self.x() + self.width() + 20, self.y() + 40)
                self.cv_debug_window.show()
                self.cv_debug_window.raise_()
                self._position_cv_hist_window()
            except Exception:
                pass

            # Button style → green
            try:
                self.btn_CVBall.setStyleSheet(
                    """
                    QPushButton { background-color:#00c853; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00c853; }
                    """
                )
            except Exception:
                pass
        else:
            # Save config (smoothing knobs)
            try:
                self.ball_tracker.save_default_config()
            except Exception:
                pass
            # Close detected-object histogram when CV Ball turns OFF
            try:
                if self.ai_hist_window is not None:
                    self.ai_hist_window.hide()
            except Exception:
                pass
            # Optional: return head to neutral
            if self.dog_client is not None and getattr(self.dog_client, "tcp_flag", False):
                try:
                    self.head_tracker.current_angle = self.head_tracker.cfg.neutral_deg
                    self.send_head_angle(int(round(self.head_tracker.current_angle)))
                except Exception:
                    pass
            # Hide CV debug window
            try:
                if self.cv_debug_window is not None:
                    self.cv_debug_window.hide()
            except Exception:
                pass
            # Button style → cyan
            try:
                self.btn_CVBall.setStyleSheet(
                    """
                    QPushButton { background-color:#00bcd4; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00bcd4; }
                    """
                )
            except Exception:
                pass

    # ------------------------------------------
    def handle_yolo_vision_button(self):
        """Toggle YOLO Vision ball tracking (local inference)."""
        # Clear stale overlays/results from other test modes
        self._clear_object_detection_state(clear_hist=True)
        # Ball sources are mutually exclusive (HSV / CV / YOLO)
        if self.ball_mode_enabled:
            self.ball_mode_enabled = False
            try:
                if self.ball_mask_window is not None:
                    self.ball_mask_window.hide()
            except Exception:
                pass
            try:
                self.btn_Ball.setStyleSheet(
                    """
                    QPushButton { background-color:#0066cc; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#0066cc; }
                    """
                )
            except Exception:
                pass

        if bool(getattr(self, "cv_ball_enabled", False)):
            self.cv_ball_enabled = False
            try:
                self.btn_CVBall.setStyleSheet(
                    """
                    QPushButton { background-color:#00bcd4; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00bcd4; }
                    """
                )
            except Exception:
                pass
            try:
                if self.cv_debug_window is not None:
                    self.cv_debug_window.hide()
            except Exception:
                pass
            try:
                if self.cv_hist_window is not None:
                    self.cv_hist_window.hide()
            except Exception:
                pass

        # Turn off GPT Vision when switching to Yolo Vision
        if bool(getattr(self, "ai_vision_enabled", False)):
            self.ai_vision_enabled = False
            self._ai_one_shot_pending = False
            self._ai_request_sent = False
            self._ai_detections = []
            try:
                self.btn_AIVision.setStyleSheet(
                    """
                    QPushButton { background-color:#00a3a3; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00a3a3; }
                    """
                )
            except Exception:
                pass

        self.yolo_vision_enabled = not bool(getattr(self, "yolo_vision_enabled", False))
        # Test mode: do NOT move dog automatically (no head/body tracking)
        # But keep head tracking if Ball mode is active.
        self.head_tracking_enabled = bool(getattr(self, "ball_mode_enabled", False))
        state = "ON" if self.yolo_vision_enabled else "OFF"
        print(f"[YOLO] Yolo Vision {state}.")

        if self.yolo_vision_enabled:
            self._yolo_update_count = 0
            self._yolo_detections = []
            self._yolo_last_error_msg = ""
            self._yolo_vision_last_ts = 0.0
            self._yolo_probe_last_ts = 0.0
            self._yolo_probe_boxes = []
            self._yolo_probe_error_msg = ""
            self._yolo_probe_latency_s = 0.0
            self._yolo_hi_conf = None
            self._yolo_lo_conf = None
            self._yolo_hi_snap = None
            self._yolo_lo_snap = None
            self._yolo_hi_center = None
            self._yolo_lo_center = None
            try:
                self._apply_yolo_model_choice()
            except Exception:
                pass
            # Load config to reuse smoothing / tracking mode knobs
            try:
                self.ball_tracker.load_default_config()
            except Exception:
                pass

            try:
                self.btn_YoloVision.setStyleSheet(
                    """
                    QPushButton { background-color:#00c853; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00c853; }
                    """
                )
            except Exception:
                pass

            # Show YOLO debug window near main window
            try:
                if self.yolo_debug_window is None:
                    self.yolo_debug_window = YoloVisionDebugWindow()
                
                try:
                    conf_init = float(getattr(self.yolo_detector, "conf", 0.02) or 0.02)
                except Exception:
                    conf_init = 0.02
                try:
                    imgsz_init = int(getattr(self.yolo_detector, "imgsz", 640) or 640)
                except Exception:
                    imgsz_init = 640

                # BINDING BLOCK
                try:
                    self.yolo_debug_window.bind_yolo_controls(
                        conf_init,
                        imgsz_init,
                        self._on_yolo_conf_changed,
                        self._on_yolo_imgsz_changed,
                    )
                except Exception:
                    pass

                try:
                    self.yolo_debug_window.bind_model_selector(self.yolo_model_choice, self._on_yolo_model_changed)
                except Exception:
                    pass
                
                try:
                    self.yolo_debug_window.bind_compare_toggle(self._on_yolo_compare_toggle)
                    self.yolo_debug_window.set_compare_checked(bool(getattr(self, "yolo_compare_enabled", False)))
                except Exception as e:
                    print(f"[YOLO] Error binding Compare toggle: {e}")
                
                try:
                    self.yolo_debug_window.bind_training_toggle(self._on_yolo_training_toggle)
                    self.yolo_debug_window.set_training_checked(bool(getattr(self, "yolo_training_enabled", False)))
                except Exception:
                    pass

                try:
                    self.yolo_debug_window.bind_labeling_classes(
                        list(self._yolo_labeling_class_names or []),
                        self._on_yolo_labeling_class_changed,
                    )
                    self.yolo_debug_window.set_labeling_class_index(int(self._yolo_labeling_class_id or 0))
                except Exception:
                    pass
                    
                if self.yolo_detector is None:
                    self.yolo_debug_window.yolo_conf_spin.setEnabled(False)
                    self.yolo_debug_window.yolo_imgsz_spin.setEnabled(False)
                    self.yolo_debug_window.yolo_model_combo.setEnabled(False)
                    # Keep Compare clickable for debug even if detector is missing
                    self.yolo_debug_window.compare_btn.setEnabled(True)
                else:
                    self.yolo_debug_window.yolo_conf_spin.setEnabled(True)
                    self.yolo_debug_window.yolo_imgsz_spin.setEnabled(True)
                    self.yolo_debug_window.yolo_model_combo.setEnabled(True)
                    self.yolo_debug_window.compare_btn.setEnabled(True)

                # Bind Manual Labeling
                try:
                    self.yolo_debug_window.bind_labeling_toggle(self._on_yolo_labeling_toggle)
                    self.yolo_debug_window.view.on_mouse_event = self._on_labeling_mouse_event
                    self.yolo_debug_window.on_key_event = self._on_labeling_key_event
                except Exception:
                    pass

                self.yolo_debug_window.move(self.x() + self.width() + 20, self.y() + 40)
                self.yolo_debug_window.show()
                self.yolo_debug_window.raise_()
            except Exception as e:
                print(f"[YOLO] Critical error initializing debug window: {e}")
                pass
        else:
            self._stop_yolo_training(reason="")
            self.yolo_compare_enabled = False
            self.yolo_labeling_enabled = False
            try:
                self.btn_YoloVision.setStyleSheet(
                    """
                    QPushButton { background-color:#2e7d32; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#2e7d32; }
                    """
                )
            except Exception:
                pass
            try:
                if self.yolo_compare_window is not None:
                    self.yolo_compare_window.hide()
            except Exception:
                pass
            # Close detected-object histogram when Yolo Vision turns OFF
            try:
                if self.ai_hist_window is not None:
                    self.ai_hist_window.hide()
            except Exception:
                pass
            if self.dog_client is not None and getattr(self.dog_client, "tcp_flag", False):
                try:
                    self.head_tracker.current_angle = self.head_tracker.cfg.neutral_deg
                    self.send_head_angle(int(round(self.head_tracker.current_angle)))
                except Exception:
                    pass
            # Hide YOLO debug window
            try:
                if self.yolo_debug_window is not None:
                    self.yolo_debug_window.hide()
            except Exception:
                pass
            self._yolo_probe_boxes = []
            self._yolo_probe_error_msg = ""
            self._yolo_probe_latency_s = 0.0

    # ------------------------------------------
    def handle_ai_vision_button(self):
        """GPT Vision button:

        Trial behavior (default): one click -> one API call (snapshot), no continuous polling.
        - Click when OFF: sends exactly one frame to the model and shows the result.
        - Click again: clears the snapshot.
        """
        if self.ai_one_shot_mode:
            if not self.ai_vision_enabled:
                # Turning on GPT Vision should disable other test modes to avoid mixed overlays.
                if bool(getattr(self, "cv_ball_enabled", False)):
                    self.cv_ball_enabled = False
                    try:
                        self.btn_CVBall.setStyleSheet(
                            """
                            QPushButton { background-color:#00bcd4; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                            QPushButton:hover { background-color:#ffffff; color:#00bcd4; }
                            """
                        )
                    except Exception:
                        pass
                if bool(getattr(self, "yolo_vision_enabled", False)):
                    self.yolo_vision_enabled = False
                    self._stop_yolo_training(reason="")
                    try:
                        self.btn_YoloVision.setStyleSheet(
                            """
                            QPushButton { background-color:#2e7d32; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                            QPushButton:hover { background-color:#ffffff; color:#2e7d32; }
                            """
                        )
                    except Exception:
                        pass

                # Clear stale detection overlays and histogram contents
                self._clear_object_detection_state(clear_hist=True)

                # Arm one request and show snapshot UI
                self.ai_vision_enabled = True
                self._ai_one_shot_pending = True
                self._gpt_snapshot_count = int(getattr(self, "_gpt_snapshot_count", 0) or 0) + 1
                self._ai_last_error_msg = ""
                self._ai_request_sent = False
                self._ai_detections = []
                self.ai_auto_hsv_applied = False
                self._ai_status_msg = ""
                self._ai_status_ts = 0.0
                print(f"[GPT] GPT Vision SNAPSHOT armed (one request). #{self._gpt_snapshot_count}")

                # Button style → green
                self.btn_AIVision.setStyleSheet(
                    """
                    QPushButton {
                        background-color:#00c853;
                        color:#ffffff;
                        border:none;
                        border-radius:16px;
                        padding:4px 10px;
                        font-size:14px;
                    }
                    QPushButton:hover {
                        background-color:#ffffff;
                        color:#00c853;
                    }
                    """
                )
            else:
                # Clear snapshot and turn OFF
                self.ai_vision_enabled = False
                self._ai_one_shot_pending = False
                self._ai_detections = []
                self._ai_request_sent = False
                self.ai_auto_hsv_applied = False
                self._ai_last_error_msg = ""
                self._ai_status_msg = ""
                self._ai_status_ts = 0.0
                print("[GPT] GPT Vision SNAPSHOT cleared.")

                # Button style → teal
                self.btn_AIVision.setStyleSheet(
                    """
                    QPushButton {
                        background-color:#00a3a3;
                        color:#ffffff;
                        border:none;
                        border-radius:16px;
                        padding:4px 10px;
                        font-size:14px;
                    }
                    QPushButton:hover {
                        background-color:#ffffff;
                        color:#00a3a3;
                    }
                    """
                )
            return

        # Legacy behavior: continuous polling while enabled
        self.ai_vision_enabled = not self.ai_vision_enabled
        state = "ON" if self.ai_vision_enabled else "OFF"
        print(f"[GPT] GPT Vision {state}.")

        if self.ai_vision_enabled:
            self._ai_last_error_msg = ""
            self._ai_request_sent = False
            self.ai_auto_hsv_applied = False
            # Button style → green
            self.btn_AIVision.setStyleSheet(
                """
                QPushButton {
                    background-color:#00c853;
                    color:#ffffff;
                    border:none;
                    border-radius:16px;
                    padding:4px 10px;
                    font-size:14px;
                }
                QPushButton:hover {
                    background-color:#ffffff;
                    color:#00c853;
                }
                """
            )
        else:
            self._ai_detections = []
            self._ai_request_sent = False
            self.ai_auto_hsv_applied = False
            self._ai_last_error_msg = ""
            self._ai_status_msg = ""
            self._ai_status_ts = 0.0

            # Button style → teal
            self.btn_AIVision.setStyleSheet(
                """
                QPushButton {
                    background-color:#00a3a3;
                    color:#ffffff;
                    border:none;
                    border-radius:16px;
                    padding:4px 10px;
                    font-size:14px;
                }
                QPushButton:hover {
                    background-color:#ffffff;
                    color:#00a3a3;
                }
                """
            )


    def handle_quit(self):
        """Q key / button: exit."""
        print("[SYS] Quit requested.")
        # Save calibration one more time
        self.ball_tracker.save_default_config()
        # Close auxiliary windows if open
        for win in [
            getattr(self, "ball_mask_window", None),
            getattr(self, "cv_debug_window", None),
            getattr(self, "cv_hist_window", None),
            getattr(self, "ai_hist_window", None),
            getattr(self, "yolo_debug_window", None),
            getattr(self, "yolo_compare_window", None),
            getattr(self, "yolo_train_hist_window", None),
        ]:
            if win is not None:
                try:
                    win.close()
                except Exception:
                    try:
                        win.hide()
                    except Exception:
                        pass
        try:
            self.close()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            try:
                QTimer.singleShot(50, app.quit)
            except Exception:
                try:
                    app.quit()
                except Exception:
                    pass

    def _maybe_update_test_hist(
        self,
        mode_label: str,
        src_frame_bgr,
        center_xy,
        radius_px: float,
        *,
        model_label: str = "",
        thresholds: dict | None = None,
        mask_combined=None,
        roi_rect=None,
        interval_s: float | None = None,
    ):
        if src_frame_bgr is None:
            return

        if center_xy is None:
            try:
                center_xy = getattr(self.ball_tracker, "sample_point", None)
            except Exception:
                center_xy = None
        if center_xy is None:
            try:
                h, w = src_frame_bgr.shape[:2]
                center_xy = (int(w // 2), int(h // 2))
            except Exception:
                return

        try:
            cx, cy = int(center_xy[0]), int(center_xy[1])
        except Exception:
            return

        now = time.time()
        try:
            interval_s_eff = float(self.test_hist_interval_s if interval_s is None else interval_s)
        except Exception:
            interval_s_eff = 1.0
        interval_s_eff = max(0.0, interval_s_eff)

        last_ts = float(getattr(self, "_test_hist_last_ts", 0.0) or 0.0)
        last_mode = str(getattr(self, "_test_hist_last_mode", "") or "")
        allow = (mode_label != last_mode) or (interval_s_eff <= 0.0) or ((now - last_ts) >= interval_s_eff)
        if not allow:
            return

        if self.ai_hist_window is None:
            self.ai_hist_window = AIVisionHistogramWindow()
        if not self.ai_hist_window.isVisible():
            self.ai_hist_window.show()

        hz = (1.0 / interval_s_eff) if interval_s_eff > 0 else None
        self.ai_hist_window.set_context(mode_label, model_label, update_hz=hz)
        rr = float(radius_px or 0.0)
        if rr <= 0.0:
            rr = 12.0
        self.ai_hist_window.update_histogram(
            src_frame_bgr,
            cx,
            cy,
            rr,
            thresholds=thresholds,
            mask_combined=mask_combined,
            roi_rect=roi_rect,
        )

        self._test_hist_last_ts = now
        self._test_hist_last_mode = mode_label

    def _position_cv_hist_window(self):
        if self.cv_hist_window is None:
            return
        try:
            screen = QApplication.primaryScreen()
            avail = screen.availableGeometry() if screen is not None else None
        except Exception:
            avail = None

        try:
            gap = 16
            main_x = int(self.x())
            main_y = int(self.y())
            main_w = int(self.width())
            main_h = int(self.height())

            hist_w = int(self.cv_hist_window.width())
            hist_h = int(self.cv_hist_window.height())

            if self.cv_debug_window is not None and self.cv_debug_window.isVisible():
                base_x = int(self.cv_debug_window.x())
                base_y = int(self.cv_debug_window.y())
                base_h = int(self.cv_debug_window.height())
                target_x = base_x
                target_y = base_y + base_h + gap
            else:
                target_x = main_x + main_w + gap
                target_y = main_y + max(40, main_h - hist_h)

            if avail is not None:
                max_x = max(avail.x(), avail.x() + avail.width() - hist_w)
                max_y = max(avail.y(), avail.y() + avail.height() - hist_h)
                target_x = max(avail.x(), min(target_x, max_x))
                target_y = max(avail.y(), min(target_y, max_y))

            self.cv_hist_window.move(int(target_x), int(target_y))
            self._cv_hist_positioned = True
        except Exception:
            return

    def _maybe_update_cv_hist(self, frame_bgr):
        if frame_bgr is None:
            return
        if not bool(getattr(self, "cv_ball_enabled", False)):
            try:
                if self.cv_hist_window is not None and self.cv_hist_window.isVisible():
                    self.cv_hist_window.hide()
            except Exception:
                pass
            return

        now = time.time()
        try:
            interval_s = float(getattr(self, "cv_hist_interval_s", 0.5) or 0.5)
        except Exception:
            interval_s = 0.5
        interval_s = max(0.0, interval_s)

        last_ts = float(getattr(self, "_cv_hist_last_ts", 0.0) or 0.0)
        if interval_s > 0.0 and (now - last_ts) < interval_s:
            return

        if self.cv_hist_window is None:
            self.cv_hist_window = CVBallHistogramWindow()
        if not self.cv_hist_window.isVisible():
            self.cv_hist_window.show()
            self._cv_hist_positioned = False

        if not bool(getattr(self, "_cv_hist_positioned", False)):
            self._position_cv_hist_window()

        picker = None
        try:
            picker = getattr(self.ball_tracker, "sample_point", None)
        except Exception:
            picker = None

        ranked = self._cv_ball_last_ranked_masks if bool(self.cv_ball_enabled) else []
        thresholds = getattr(self, "_cv_ball_last_thresholds", None)
        mode_label = "CV Ball ON" if bool(self.cv_ball_enabled) else "CV Ball OFF"

        self.cv_hist_window.update_panels(
            frame_bgr,
            picker,
            ranked,
            thresholds=thresholds,
            mode_label=mode_label,
        )

        self._cv_hist_last_ts = now

    def _clear_object_detection_state(self, *, clear_hist: bool = True):
        # Clear all test-mode detections/overlays so switching modes doesn't leave stale info.
        self._ai_detections = []
        self._ai_request_sent = False
        self._ai_one_shot_pending = False
        self._ai_status_msg = ""
        self._ai_status_ts = 0.0
        self._yolo_detections = []
        self._yolo_last_error_msg = ""
        self._cv_ball_last_mask = None
        self._cv_ball_last_hist_mask = None
        self._cv_ball_last_ranked_masks = []
        self._cv_detect_count = 0
        self._test_hist_last_ts = 0.0
        self._test_hist_last_mode = ""
        if clear_hist and self.ai_hist_window is not None:
            try:
                self.ai_hist_window.clear_view(mode_label="Object Detection Test")
            except Exception:
                pass


    def closeEvent(self, event):
        """Qt close: stop threads/timers and release resources."""
        print("[CLOSE] Cleaning up...")

        # Save calibration one last time
        self.ball_tracker.save_default_config()

        self.stop_server_check = True
        self.stop_cmd_thread = True

        if getattr(self, "server_check_thread", None) is not None:
            self.server_check_thread.join(timeout=1.0)

        if getattr(self, "telemetry_timer", None) is not None:
            self.telemetry_timer.stop()
        if getattr(self, "timer", None) is not None:
            self.timer.stop()

        if self.dog_client is not None:
            try:
                if hasattr(self.dog_client, "turn_off_client"):
                    self.dog_client.turn_off_client()
            except Exception as e:
                print(f"[CLOSE] Error closing dog client: {e}")

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                print(f"[CLOSE] Error releasing camera: {e}")

        event.accept()
    
    #------------------------------------
    #------------------------------------
    def mouseMoveEvent(self, event):
        """
        Mouse hover over the main video:

          • DOES NOT move the HSV picker (click-and-stay behavior).
          • Only updates hover_xy_color / hover_hsv_color so we can display
            "hover HSV (x,y)" near the cursor, similar to the Mask window.
        """
        if self.last_display_frame_bgr is not None:
            img_h, img_w, _ = self.last_display_frame_bgr.shape

            # Map Qt widget coords → video_label coords
            label_pos = self.video_label.mapFrom(self, event.pos())
            lx, ly = label_pos.x(), label_pos.y()
            label_w = self.video_label.width()
            label_h = self.video_label.height()

            scale = min(label_w / img_w, label_h / img_h)
            disp_w = int(img_w * scale)
            disp_h = int(img_h * scale)
            off_x = (label_w - disp_w) // 2
            off_y = (label_h - disp_h) // 2

            if off_x <= lx < off_x + disp_w and off_y <= ly < off_y + disp_h:
                # Inside displayed image area → map to image coords
                ix = int((lx - off_x) / scale)
                iy = int((ly - off_y) / scale)
                ix = max(0, min(img_w - 1, ix))
                iy = max(0, min(img_h - 1, iy))

                hsv = cv2.cvtColor(self.last_display_frame_bgr, cv2.COLOR_BGR2HSV)
                H, S, V = [int(v) for v in hsv[iy, ix]]

                self.hover_xy_color = (ix, iy)
                self.hover_hsv_color = (H, S, V)
            else:
                # Outside the image area
                self.hover_xy_color = None
                self.hover_hsv_color = None
        else:
            self.hover_xy_color = None
            self.hover_hsv_color = None

        super().mouseMoveEvent(event)

    #=================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = CameraWindow()
    w.show()
    sys.exit(app.exec_())
