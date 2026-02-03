#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mtDogBallTrack.py

Ball colour tracking, HSV calibration, mask visualisation,
AND Head Tracking logic for the Freenove Robot Dog Client (Mac mode).

Features
--------
- remove circular dependency by merging HeadTracker into this file
- HSV-based ball mask with optional second hue segment.
- Circularity-aware contour selection (prefers large, round blobs).
- Temporal smoothing (EMA) + jump rejection for stable lock.
- Shared HSV picker (click-to-sample) between colour and mask views.
- Ball center trace with time-based fading.
- Head Tracking (P-controller) logic integrated.
- Calibration window with:
    * Live mask view
    * Linked HSV picker readout
    * Sliders for H1/H2/S/V and morphology kernel size
    * Sliders for EMA smoothing + min circularity threshold
    * Slider for Head Tracking Kp gain
    * Rolling histograms for H, S, V with peak / SD / slider markers.
- JSON-based persistence (mtBall_Calib.json).

Revision History
----------------
- v2.8.4: 2026-01-28
          Allow external detection overlays to set circle thickness (used by YOLO).
- v2.8.3: 2026-01-28
          Add optional suppression of external detection overlay (for YOLO-only bbox tests).
- v2.8.2: 2026-01-21
          Added CV RadialGate toggle with persistence in mtBall_Calib.json.
- v2.8.0: 2026-01-14
          Added Body-Kp/Body-Kd sliders (proportional + derivative shaping) for smoother body tracking and persisted them to mtBall_Calib.json.
          Added Head-Deadzone slider (head deadband) and persisted it.
          Renamed Deadzone label to Body-Deadzone and added Allow backward toggle.
- v2.8.1: 2026-01-19
          Moved the center-info overlay text above the ROI circle for a clearer view of the ball ROI.
- v2.7.1: 2025-12-10 Added optical flow overlay to mask visualization for better motion tracking.
- v2.7.0: 2025-12-06
          Merged HeadTracker logic into this file to resolve circular dependencies and attribute errors.
          Added Kp slider to Mask Window for tuning head tracking gain.
          Fixed Mask Window HUD to correctly display HSV values from the color frame picker.
          Ensured Kp value is saved/loaded from JSON config.
- v2.6.0: Added rolling histograms for H/S/V in calibration window.
          Added circularity and EMA smoothing sliders.
- v2.5.0: Initial implementation of shared HSV picker and mask visualization.

Author
------
MT (User) & GitHub Copilot
Version: 2.8.0 - 2026-01-14
"""

import math
import time
import cv2
import json
import os
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QFrame,
    QPushButton,
    QVBoxLayout,
    QGridLayout,
    QSlider,
    QHBoxLayout,
    QSizePolicy,
    QComboBox,
    QCheckBox,
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

try:
    from vision.legacy.mtBallDetectCV import CVBallDetector
except Exception:
    CVBallDetector = None  # type: ignore


# Tracking modes
# Tracking modes are stored/compared as lowercase canonical values.
TRACKING_MODE_FULL = "full"   # head + body
TRACKING_MODE_HEAD = "head"   # head only
TRACKING_MODE_BODY = "body"   # body only

# ==============================================================================
# HEAD TRACKER CLASSES
# ==============================================================================

@dataclass
class HeadConfig:
    neutral_deg: float = 90.0
    min_deg: float = 40.0
    max_deg: float = 140.0
    kp: float = 0.5  # Incremental gain: deg per normalized error per update (was 4.0 for absolute mode)
    deadband: float = 0.02  # Reduced from 0.08 to 0.02 for fine tracking (2% of frame height)
    max_step_deg: float = 3.0  # Max angle change per update (velocity limit)
    min_cmd_interval: float = 0.15  # Increased from 0.10 to 0.15 seconds for stability

class HeadTracker:
    """
    Calculates the desired head servo angle based on the ball's vertical position.
    Uses a simple P-controller with deadband and clamping.
    """
    def __init__(self):
        self.cfg = HeadConfig()
        self.current_angle = self.cfg.neutral_deg
        self.last_cmd_time = 0.0
        self.last_err_norm = 0.0
        self.search_mode = False
        self.search_blocked = False
        self.search_targets = []
        self.search_index = 0
        self.search_state = "idle"

    def update_from_ball(self, ball_cy: Optional[int], frame_h: int) -> Optional[float]:
        """
        Calculate new head angle based on ball Y position.
        Returns None if no update needed (no ball, deadband, or too soon).
        """
        if ball_cy is None or frame_h == 0:
            return None

        now = time.time()
        if now - self.last_cmd_time < self.cfg.min_cmd_interval:
            return None

        # Normalize vertical error into [-1, +1]
        # center_y is target.
        # If ball is below center (y > center), we need to look DOWN (increase angle).
        # If ball is above center (y < center), we need to look UP (decrease angle).
        # Standard image coords: y=0 at top.
        # Servo: 90=center, <90=up, >90=down (usually).
        
        center_y = frame_h / 2.0    # 400x300 frame → center_y=150
        # Error = (ball - center) / center
        # ball below center (larger y) -> error > 0 -> command increases angle (tilt down)
        # ball above center (smaller y) -> error < 0 -> command decreases angle (tilt up)
        err_norm = (ball_cy - center_y) / center_y      # positive = ball below center

        # Deadband — suppress jitter
        if abs(err_norm) < self.cfg.deadband:
            return None

        # P CONTROLLER: Incremental/velocity control
        # Calculate angle adjustment (delta) from current position, not absolute target
        # ball below center (err_norm > 0) → need to tilt up (decrease angle)
        # Servo convention: larger angle = tilt down, smaller = tilt up
        delta_angle = -(self.cfg.kp * err_norm)
        
        # Limit rate of change (velocity limit)
        delta_angle = max(-self.cfg.max_step_deg, min(self.cfg.max_step_deg, delta_angle))
        
        # Apply incremental change to current angle
        target = self.current_angle + delta_angle

        # Clamp to safe servo range
        target = max(self.cfg.min_deg, min(self.cfg.max_deg, target))

        # Update state
        self.current_angle = target
        self.last_cmd_time = now
        self.last_err_norm = err_norm
        self.search_mode = False
        self.search_blocked = False
        self.search_targets = []
        self.search_index = 0
        self.search_state = "tracking"
        return self.current_angle

    def reset(self):
        self.current_angle = self.cfg.neutral_deg
        self.last_err_norm = 0.0
        self.search_mode = False
        self.search_blocked = False
        self.search_targets = []
        self.search_index = 0
        self.search_state = "idle"

    def start_search(self):
        if self.search_blocked:
            return
        direction = math.copysign(1.0, self.last_err_norm) if abs(self.last_err_norm) > 1e-3 else 1.0
        first = self.cfg.max_deg if direction > 0 else self.cfg.min_deg
        second = self.cfg.min_deg if direction > 0 else self.cfg.max_deg
        self.search_targets = [first, second]
        self.search_index = 0
        self.search_mode = True
        self.search_state = "searching"

    def search_for_ball(self) -> Optional[float]:
        now = time.time()
        if now - self.last_cmd_time < self.cfg.min_cmd_interval:
            return None
        if self.search_blocked:
            return self._move_to_neutral()
        if not self.search_mode:
            return None
        if self.search_index >= len(self.search_targets):
            self.search_mode = False
            self.search_blocked = True
            return self._move_to_neutral()
        target = self.search_targets[self.search_index]
        angle = self._move_toward(target)
        if abs(self.current_angle - target) < 0.1:
            self.search_index += 1
            if self.search_index >= len(self.search_targets):
                self.search_mode = False
                self.search_blocked = True
                return self._move_to_neutral()
        return angle

    def _move_toward(self, target: float) -> Optional[float]:
        delta = target - self.current_angle
        if abs(delta) < 0.1:
            self.current_angle = target
            self.last_cmd_time = time.time()
            return self.current_angle
        step = math.copysign(min(abs(delta), self.cfg.max_step_deg), delta)
        self.current_angle += step
        self.last_cmd_time = time.time()
        return self.current_angle

    def _move_to_neutral(self) -> Optional[float]:
        if abs(self.current_angle - self.cfg.neutral_deg) < 0.1:
            self.current_angle = self.cfg.neutral_deg
            self.search_state = "idle"
            self.search_blocked = True
            return None
        angle = self._move_toward(self.cfg.neutral_deg)
        if abs(self.current_angle - self.cfg.neutral_deg) < 0.1:
            self.current_angle = self.cfg.neutral_deg
            self.search_state = "idle"
            self.search_blocked = True
            return None
        return angle


# ==============================================================================
# BALL TRACKER CLASS
# ==============================================================================

class BallTracker:
    """
    Holds HSV threshold config and shared state for ball detection
    + global sample point for HSV picker.
    + Owns the HeadTracker instance.
    """

    def __init__(self):
        # Default orange-ish ball
        self.h1_min = 0
        self.h1_max = 20
        self.h2_min = 0
        self.h2_max = 0
        self.s_min = 120
        self.s_max = 255
        self.v_min = 80
        self.v_max = 255
        self.kernel_size = 3  # morphology kernel (odd)

        # Detection info (instant and smoothed)
        self.last_center = None      # (x, y) – smoothed center used by UI / head
        self.last_hsv = None         # (H, S, V) at smoothed center
        self.last_radius = None      # radius used for drawing

        # Smoothing / noise-filter state
        self.filtered_center = None  # internal EMA center
        self.smooth_alpha = 0.35     # 0.0 = no smoothing, 1.0 = follow raw center
        self.max_jump_ratio = 0.35   # ignore jumps > 35% of min(frame_w, frame_h)

        # Stability counters for smart reacquire
        self.last_update_ts = 0.0     # timestamp of last accepted detection
        self.missed_frames = 0        # consecutive frames without acceptance
        self.reacquire_timeout = 0.6  # seconds without update → allow bigger jumps
        self.reacquire_area_ratio = 0.02  # if blob area > 2% of frame, allow reacquire

        # Trace of recent centers (for visual trail)
        # Each entry: ( (x, y), timestamp_seconds )
        self.trace_points = deque(maxlen=60)
        self.trace_max_age = 3.0  # seconds

        # Shared picker point across windows
        self.sample_point = None  # (x, y) in image coords
        self.sample_hsv = None    # (H, S, V)

        self.picker_point = None      # (x, y) in image coordinates
        self.picker_hsv = None        # (H, S, V) at picker_point

        # --- Head Tracker Instance ---
        self.head_tracker = HeadTracker()
        # Default mode requested: Full tracking
        self.tracking_mode = TRACKING_MODE_FULL

        # Body tracking tuning (used by mtDogMain)
        self.body_tracking_interval = 0.6   # seconds between motion commands
        self.body_deadzone_ratio = 0.18     # fraction of frame size used as deadzone
        self.body_allow_backward = False    # forward-only by default
        self.body_kp = 0.0                  # proportional speed scaling (0.0 disables)

        # Lost-ball search + obstacle avoidance (used by mtDogMain)
        self.search_forward_enabled = True
        self.obstacle_avoid_enabled = True
        self.obstacle_near_cm = 10.0
        self.obstacle_clear_cm = 30.0
        self.search_forward_speed = 4
        self.obstacle_turn_speed = 4

        # CV detector gating controls (default OFF for stability)
        self.cv_radial_gate_enabled = False

        # Config path
        self.config_path = os.path.join(
            os.path.dirname(__file__), "config", "mtBall_Calib.json"
        )

        # Optional CV detector (basic, non-ML)
        self._cv_detector = CVBallDetector() if CVBallDetector is not None else None
        self._apply_cv_radial_gate()

    def _apply_cv_radial_gate(self):
        """Apply radial gate setting to the CV detector (if available)."""
        try:
            if self._cv_detector is None:
                return
            if hasattr(self._cv_detector, "set_radial_gate_enabled"):
                self._cv_detector.set_radial_gate_enabled(bool(self.cv_radial_gate_enabled))
            else:
                if bool(self.cv_radial_gate_enabled):
                    self._cv_detector.min_radial_score = float(getattr(self._cv_detector, "min_radial_score", 0.55))
                    self._cv_detector.min_radial_coverage = float(getattr(self._cv_detector, "min_radial_coverage", 0.15))
                else:
                    self._cv_detector.min_radial_score = 0.0
                    self._cv_detector.min_radial_coverage = 0.0
        except Exception:
            return

    # ------------------------------------------------------------------
    # Config I/O  (mtBall_Calib.json)
    # ------------------------------------------------------------------
    def load_default_config(self):
        """Load HSV + filter config from the default JSON path."""
        self.load_config(self.config_path)

    def save_default_config(self):
        """Save HSV + filter config to the default JSON path."""
        self.save_config(self.config_path)

    def load_config(self, path: str):
        """Load HSV + filter config from JSON (backward compatible)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"[BALL] Config not found, using defaults: {path}")
            return
        except Exception as e:
            print(f"[BALL] Error reading config {path}: {e}")
            return

        hsv = data.get("hsv", {})

        # Old names: H_low/H_high → H1 segment
        self.h1_min = int(hsv.get("H1_low", hsv.get("H_low", self.h1_min)))
        self.h1_max = int(hsv.get("H1_high", hsv.get("H_high", self.h1_max)))
        self.h2_min = int(hsv.get("H2_low", self.h2_min))
        self.h2_max = int(hsv.get("H2_high", self.h2_max))

        self.s_min = int(hsv.get("S_low", self.s_min))
        self.s_max = int(hsv.get("S_high", self.s_max))
        self.v_min = int(hsv.get("V_low", self.v_min))
        self.v_max = int(hsv.get("V_high", self.v_max))

        filt = data.get("filter", {})
        self.kernel_size = int(filt.get("kernel_size", self.kernel_size))
        self.smooth_alpha = float(filt.get("smooth_alpha", self.smooth_alpha))
        self.max_jump_ratio = float(filt.get("max_jump_ratio", self.max_jump_ratio))
        
        # --- Load P gain for head tracker ---
        kp_val = float(filt.get("kp", self.head_tracker.cfg.kp))
        self.head_tracker.cfg.kp = kp_val

        # Head tracking deadband (normalized fraction of half-frame height)
        try:
            deadband_val = float(filt.get("deadband", self.head_tracker.cfg.deadband))
            self.head_tracker.cfg.deadband = max(0.0, min(0.50, deadband_val))
        except Exception:
            pass

        tracking = data.get("tracking", {})
        saved_mode = str(tracking.get("mode", self.tracking_mode)).lower()
        if saved_mode in (TRACKING_MODE_FULL, TRACKING_MODE_HEAD, TRACKING_MODE_BODY):
            self.tracking_mode = saved_mode

        # Body tracking tuning (optional; backward compatible)
        try:
            interval = float(tracking.get("body_interval", self.body_tracking_interval))
            self.body_tracking_interval = max(0.05, min(5.0, interval))
        except Exception:
            pass

        try:
            ratio = float(tracking.get("deadzone_ratio", self.body_deadzone_ratio))
            self.body_deadzone_ratio = max(0.05, min(0.50, ratio))
        except Exception:
            pass

        try:
            self.body_allow_backward = bool(
                tracking.get("body_allow_backward", self.body_allow_backward)
            )
        except Exception:
            pass

        # Body tracking proportional speed scaling (optional)
        try:
            kp = float(tracking.get("body_kp", self.body_kp))
            self.body_kp = max(0.0, min(5.0, kp))
        except Exception:
            pass

        # Lost-ball search + obstacle avoidance (optional; backward compatible)
        try:
            self.search_forward_enabled = bool(
                tracking.get("search_forward_enabled", self.search_forward_enabled)
            )
        except Exception:
            pass

        try:
            self.obstacle_avoid_enabled = bool(
                tracking.get("obstacle_avoid_enabled", self.obstacle_avoid_enabled)
            )
        except Exception:
            pass

        try:
            near = float(tracking.get("obstacle_near_cm", self.obstacle_near_cm))
            self.obstacle_near_cm = max(1.0, min(200.0, near))
        except Exception:
            pass

        try:
            clear = float(tracking.get("obstacle_clear_cm", self.obstacle_clear_cm))
            self.obstacle_clear_cm = max(1.0, min(300.0, clear))
        except Exception:
            pass

        if self.obstacle_clear_cm < self.obstacle_near_cm:
            self.obstacle_clear_cm = float(self.obstacle_near_cm)

        try:
            spd = int(tracking.get("search_forward_speed", self.search_forward_speed))
            self.search_forward_speed = max(2, min(10, spd))
        except Exception:
            pass

        try:
            spd = int(tracking.get("obstacle_turn_speed", self.obstacle_turn_speed))
            self.obstacle_turn_speed = max(2, min(10, spd))
        except Exception:
            pass

        cv_cfg = data.get("cv", {})
        try:
            self.cv_radial_gate_enabled = bool(
                cv_cfg.get("radial_gate", self.cv_radial_gate_enabled)
            )
        except Exception:
            pass
        self._apply_cv_radial_gate()

        self._clamp_all()
        print(f"[BALL] Config loaded from {path}: {self.to_dict()}")

    def save_config(self, path: str):
        """Save HSV + filter config into JSON."""
        data = self.to_dict()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[BALL] Error saving config {path}: {e}")

    def to_dict(self):
        return {
            "hsv": {
                "H1_low": self.h1_min,
                "H1_high": self.h1_max,
                "H2_low": self.h2_min,
                "H2_high": self.h2_max,
                "S_low": self.s_min,
                "S_high": self.s_max,
                "V_low": self.v_min,
                "V_high": self.v_max,
            },
            "filter": {
                "kernel_size": self.kernel_size,
                "smooth_alpha": self.smooth_alpha,
                "max_jump_ratio": self.max_jump_ratio,
                "kp": self.head_tracker.cfg.kp,
                "deadband": self.head_tracker.cfg.deadband,
            },
            "tracking": {
                "mode": self.tracking_mode,
                "body_interval": self.body_tracking_interval,
                "deadzone_ratio": self.body_deadzone_ratio,
                "body_allow_backward": self.body_allow_backward,
                "body_kp": self.body_kp,
                "search_forward_enabled": self.search_forward_enabled,
                "obstacle_avoid_enabled": self.obstacle_avoid_enabled,
                "obstacle_near_cm": self.obstacle_near_cm,
                "obstacle_clear_cm": self.obstacle_clear_cm,
                "search_forward_speed": self.search_forward_speed,
                "obstacle_turn_speed": self.obstacle_turn_speed,
            },
            "cv": {
                "radial_gate": bool(self.cv_radial_gate_enabled),
            },
        }

    def _clamp_all(self):
        # Hue
        self.h1_min = max(0, min(179, self.h1_min))
        self.h1_max = max(0, min(179, self.h1_max))
        self.h2_min = max(0, min(179, self.h2_min))
        self.h2_max = max(0, min(179, self.h2_max))
        # Saturation / Value
        self.s_min = max(0, min(255, self.s_min))
        self.s_max = max(0, min(255, self.s_max))
        self.v_min = max(0, min(255, self.v_min))
        self.v_max = max(0, min(255, self.v_max))
        # Kernel (odd)
        self.kernel_size = max(1, min(15, int(self.kernel_size)))
        if self.kernel_size % 2 == 0:
            self.kernel_size += 1

    # ------------------------------------------------------------------
    # Range setters
    # ------------------------------------------------------------------
    def set_hue_ranges(self, h1_min, h1_max, h2_min=0, h2_max=0):
        self.h1_min, self.h1_max = int(h1_min), int(h1_max)
        self.h2_min, self.h2_max = int(h2_min), int(h2_max)
        self._clamp_all()

    def set_sv_ranges(self, s_min, s_max, v_min, v_max):
        self.s_min, self.s_max = int(s_min), int(s_max)
        self.v_min, self.v_max = int(v_min), int(v_max)
        self._clamp_all()

    def set_kernel_size(self, k):
        self.kernel_size = int(k)
        self._clamp_all()

    def set_tracking_mode(self, mode: str):
        candidate = str(mode).lower()
        if candidate in (TRACKING_MODE_FULL, TRACKING_MODE_HEAD, TRACKING_MODE_BODY):
            self.tracking_mode = candidate

    # ------------------------------------------------------------------
    # Shared picker point  (click-and-stay for both windows)
    # ------------------------------------------------------------------
    def set_sample_point(self, point, hsv):
        """
        point: (x, y) image coords
        hsv  : (H, S, V)
        """
        # Single source of truth for the picker
        self.sample_point = point
        self.sample_hsv = hsv

        # Keep legacy names in sync (anything that still uses picker_*)
        self.picker_point = point
        self.picker_hsv = hsv

    def set_picker(self, point, hsv):
        """
        Backward-compatible alias.
        Anything still calling set_picker() will update the same state.
        """
        self.set_sample_point(point, hsv)

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------
    def compute_mask(self, frame_bgr):
        if frame_bgr is None:
            return None, None

        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

        lower1 = np.array([self.h1_min, self.s_min, self.v_min], np.uint8)
        upper1 = np.array([self.h1_max, self.s_max, self.v_max], np.uint8)
        mask1 = cv2.inRange(hsv, lower1, upper1)

        if self.h2_max > self.h2_min:
            lower2 = np.array([self.h2_min, self.s_min, self.v_min], np.uint8)
            upper2 = np.array([self.h2_max, self.s_max, self.v_max], np.uint8)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = mask1

        k = self.kernel_size
        kernel = np.ones((k, k), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        return hsv, mask

    # ------------------------------------------------------------------
    def process_with_mask(self, frame_bgr):
        """
        Detect ball, apply temporal smoothing + jump rejection,
        draw overlay and return (mask, annotated_frame).
        """
        # Reset per-frame outputs (retain previous center to avoid flicker)
        # Keep last_center so UI continues to show previous lock when a frame is rejected.
        self.last_hsv = None
        self.last_radius = None

        if frame_bgr is None:
            return None, frame_bgr

        hsv, mask = self.compute_mask(frame_bgr)        # 
        if mask is None:
            return None, frame_bgr

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            # No ball this frame → keep previous center, mark as a miss
            self.missed_frames += 1
                # print(f"[BallTracker] No contours found (missed_frames={self.missed_frames})\r", end='') # noisy
            return mask, frame_bgr

        # --- choose best contour: MAX AREA STRATEGY ---
        h, w = hsv.shape[:2]
        min_area = 0.0004 * (w * h)      # ignore very tiny blobs (noise)
        
        chosen_cnt = None
        max_area = 0.0
        
            # print(f"[BallTracker] Frame {w}×{h}, min_area={min_area:.1f}, found {len(contours)} contour(s)")

        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
                # print(f"  Contour {i}: area={area:.1f}, {'REJECTED (too small)' if area < min_area else 'OK'}")
            if area < min_area:
                continue
            
            # Simple Max Area logic: if this blob is bigger, take it
            if area > max_area:
                max_area = area
                chosen_cnt = cnt
                    # print(f"    → SELECTED (new max_area={max_area:.1f})")
        
        if chosen_cnt is None:
            self.missed_frames += 1
                # print(f"[BallTracker] No valid contour ≥ min_area (missed_frames={self.missed_frames})")
            return mask, frame_bgr
        
            # print(f"[BallTracker] FINAL SELECTION: contour with area={max_area:.1f}")
        
        # --- got chosen contour ---
        (cx_f, cy_f), radius = cv2.minEnclosingCircle(chosen_cnt)
        raw_center = (int(cx_f), int(cy_f))

        # --- jump rejection with smart reacquire ---
        if self.filtered_center is not None:
            dx = raw_center[0] - self.filtered_center[0]
            dy = raw_center[1] - self.filtered_center[1]
            dist2 = dx * dx + dy * dy
            max_jump = self.max_jump_ratio * min(w, h)
            now_ts = time.time()
            allow_reacquire = (
                self.missed_frames >= 2 or
                (now_ts - self.last_update_ts) > self.reacquire_timeout or
                (max_area >= self.reacquire_area_ratio * (w * h))
            )
            if dist2 > max_jump * max_jump and not allow_reacquire:
                print(
                    f"[BallTracker] Jump rejected: dist={math.sqrt(dist2):.1f} > {max_jump:.1f}"
                    f" (missed={self.missed_frames}, area={max_area:.0f})"
                )
                self.missed_frames += 1
                # Large instantaneous jump → ignore this frame, keep previous center
                return mask, frame_bgr

        # --- exponential smoothing of center (EMA) ---
        if self.filtered_center is None:
            fx, fy = raw_center
        else:
            fx = int(
                self.smooth_alpha * raw_center[0]
                + (1.0 - self.smooth_alpha) * self.filtered_center[0]
            )
            fy = int(
                self.smooth_alpha * raw_center[1]
                + (1.0 - self.smooth_alpha) * self.filtered_center[1]
            )
        self.filtered_center = (fx, fy)
        self.last_center = self.filtered_center
        self.last_radius = radius
        self.missed_frames = 0
        self.last_update_ts = time.time()

        # HSV at smoothed center
        cx = max(0, min(w - 1, fx))
        cy = max(0, min(h - 1, fy))
        H, S, V = [int(v) for v in hsv[cy, cx]]
        self.last_hsv = (H, S, V)

        # Update trace history (age-based)
        now_t = time.time()
        self.trace_points.append((self.last_center, now_t))

        # --- draw on color frame ---
        cv2.circle(frame_bgr, self.last_center, int(radius), (0, 255, 100), 2)
        cv2.circle(frame_bgr, self.last_center, 4, (0, 0, 255), -1)

        pts = [p for (p, t) in self.trace_points if now_t - t <= self.trace_max_age]
        self.trace_points = deque(
            [(p, t) for (p, t) in self.trace_points if now_t - t <= self.trace_max_age],
            maxlen=self.trace_points.maxlen,
        )

        # draw connected translucent trace
        for i, p in enumerate(pts):
            cv2.circle(frame_bgr, p, 2, (0, 255, 255), -1)
            if i > 0:
                cv2.line(frame_bgr, pts[i - 1], p, (0, 255, 255), 1)

        text1 = f"HSV({H},{S},{V})"
        text2 = f"({self.last_center[0]},{self.last_center[1]})"
        tx = max(5, self.last_center[0] - 40)
        ty = max(20, self.last_center[1] - int(radius) - 10)

        # simple outline for readability
        for dy in (-1, 1):
            for dx in (-1, 1):
                # Draw outlined HSV and center text
                for dy in (-1, 1):
                    for dx in (-1, 1):
                        cv2.putText(frame_bgr, text1, (tx + dx, ty + dy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)
                        cv2.putText(frame_bgr, text2, (tx + dx, ty + dy + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)

                cv2.putText(frame_bgr, text1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 100), 1)
                cv2.putText(frame_bgr, text2, (tx, ty + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 100), 1)
        # ---------------------------------------------------------
        # Draw shared picker dot and HSV, using sample_point (click-and-stay)
        if self.sample_point:
            x, y = self.sample_point
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            h_img, w_img = hsv_img.shape[:2]
            x = max(0, min(w_img - 1, x))
            y = max(0, min(h_img - 1, y))
            Hs, Ss, Vs = [int(v) for v in hsv_img[y, x]]
            self.sample_hsv = (Hs, Ss, Vs)

            # Red dot at the picked pixel
            cv2.circle(frame_bgr, (x, y), 4, (0, 0, 255), -1)

        return mask, frame_bgr

    # ------------------------------------------------------------------
    def apply_external_detection(
        self,
        frame_bgr,
        raw_center,
        radius,
        *,
        source: str = "EXT",
        draw_overlay: bool = True,
        overlay_thickness: int | None = None,
    ):
        """Apply smoothing/jump-rejection using an externally-provided detection.

        raw_center: (x,y) in pixels, or None if no detection this frame.
        radius    : float radius in pixels, may be None/0.

        Updates:
          - last_center / last_radius / last_hsv
          - missed_frames / last_update_ts
          - trace_points
        """
        self.last_hsv = None
        self.last_radius = None

        if frame_bgr is None:
            return None, frame_bgr

        h, w = frame_bgr.shape[:2]

        if raw_center is None:
            self.missed_frames += 1
            return None, frame_bgr

        try:
            rx, ry = int(raw_center[0]), int(raw_center[1])
        except Exception:
            self.missed_frames += 1
            return None, frame_bgr

        rx = max(0, min(w - 1, rx))
        ry = max(0, min(h - 1, ry))
        raw_center_i = (rx, ry)

        try:
            r_f = float(radius) if radius is not None else 0.0
        except Exception:
            r_f = 0.0
        if r_f <= 0:
            r_f = 6.0

        # Estimate an area proxy for reacquire rules.
        est_area = float(np.pi * r_f * r_f)

        # --- jump rejection with smart reacquire ---
        if self.filtered_center is not None:
            dx = raw_center_i[0] - int(self.filtered_center[0])
            dy = raw_center_i[1] - int(self.filtered_center[1])
            dist2 = dx * dx + dy * dy
            max_jump = self.max_jump_ratio * min(w, h)
            now_ts = time.time()
            allow_reacquire = (
                self.missed_frames >= 2
                or (now_ts - self.last_update_ts) > self.reacquire_timeout
                or (est_area >= self.reacquire_area_ratio * (w * h))
            )
            if dist2 > max_jump * max_jump and not allow_reacquire:
                self.missed_frames += 1
                return None, frame_bgr

        # --- exponential smoothing of center (EMA) ---
        if self.filtered_center is None:
            fx, fy = raw_center_i
        else:
            fx = int(
                self.smooth_alpha * raw_center_i[0]
                + (1.0 - self.smooth_alpha) * int(self.filtered_center[0])
            )
            fy = int(
                self.smooth_alpha * raw_center_i[1]
                + (1.0 - self.smooth_alpha) * int(self.filtered_center[1])
            )

        self.filtered_center = (fx, fy)
        self.last_center = self.filtered_center
        self.last_radius = float(r_f)
        self.missed_frames = 0
        self.last_update_ts = time.time()

        # HSV at smoothed center (for HUD/debug)
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            cx = max(0, min(w - 1, int(fx)))
            cy = max(0, min(h - 1, int(fy)))
            H, S, V = [int(v) for v in hsv_img[cy, cx]]
            self.last_hsv = (H, S, V)
        except Exception:
            self.last_hsv = None

        # Trace
        now_t = time.time()
        self.trace_points.append((self.last_center, now_t))
        self.trace_points = deque(
            [(p, t) for (p, t) in self.trace_points if now_t - t <= self.trace_max_age],
            maxlen=self.trace_points.maxlen,
        )

        # Draw overlay every time we accept an external detection.
        if bool(draw_overlay):
            self.draw_detection_overlay(
                frame_bgr,
                source=source,
                hsv_source_bgr=frame_bgr,
                thickness=overlay_thickness,
            )

        return None, frame_bgr

    # ------------------------------------------------------------------
    def draw_detection_overlay(
        self,
        frame_bgr,
        *,
        source: str = "EXT",
        hsv_source_bgr=None,
        inner_ratio: float = 0.75,
        dashed_inner: bool = True,
        thickness: int | None = None,
    ):
        """Draw detection overlays using the *current* last_center/last_radius.

        This is used to keep the overlay stable at UI FPS even when detection is
        throttled (e.g., CV Ball @ 1Hz).
        """
        if frame_bgr is None or self.last_center is None or self.last_radius is None:
            return

        try:
            h, w = frame_bgr.shape[:2]
        except Exception:
            return

        color = (255, 255, 0) if str(source).upper().startswith("CV") else (0, 255, 0)
        inner_color = (0, 165, 255)  # orange-ish (BGR)

        rr = int(round(float(self.last_radius or 0.0)))
        rr = max(2, rr)
        inner_ratio = float(inner_ratio)
        inner_ratio = max(0.10, min(0.95, inner_ratio))
        inner_r = int(round(rr * inner_ratio))
        inner_r = max(1, min(rr - 1, inner_r)) if rr > 1 else 1

        cx, cy = int(self.last_center[0]), int(self.last_center[1])
        cx = max(0, min(w - 1, cx))
        cy = max(0, min(h - 1, cy))

        def draw_dashed_circle(img, center, radius, col, thickness=2, dash_deg=14, gap_deg=10):
            try:
                if radius <= 1:
                    return
                step = max(4, int(dash_deg + gap_deg))
                ang = 0
                while ang < 360:
                    a0 = ang
                    a1 = min(360, ang + int(dash_deg))
                    cv2.ellipse(img, center, (radius, radius), 0, a0, a1, col, thickness)
                    ang += step
            except Exception:
                pass

        use_th = int(thickness) if thickness is not None else 2
        use_th = max(1, use_th)

        # Outer ROI circle (solid)
        cv2.circle(frame_bgr, (cx, cy), rr, color, use_th)
        # Inner sampling circle (0.75x radius)
        if dashed_inner:
            draw_dashed_circle(frame_bgr, (cx, cy), inner_r, inner_color, thickness=use_th)
        else:
            cv2.circle(frame_bgr, (cx, cy), inner_r, inner_color, use_th)
        cv2.circle(frame_bgr, (cx, cy), 3, color, -1)

        # Ensure HSV is available (prefer raw frame without overlays)
        if self.last_hsv is None:
            try:
                src = hsv_source_bgr if hsv_source_bgr is not None else frame_bgr
                hsv_img = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
                H, S, V = [int(v) for v in hsv_img[cy, cx]]
                self.last_hsv = (H, S, V)
            except Exception:
                self.last_hsv = None

        dpx = int(round(2 * rr))
        text1 = f"({cx},{cy}), D{dpx}px"
        if self.last_hsv is not None:
            H, S, V = self.last_hsv
            text2 = f"HSV({H},{S},{V})"
        else:
            text2 = "HSV(?, ?, ?)"

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.45
        thick = 1
        (w1, h1), _ = cv2.getTextSize(text1, font, scale, thick)
        (w2, h2), _ = cv2.getTextSize(text2, font, scale, thick)
        block_w = max(w1, w2)
        line_gap = 6
        block_h = h1 + line_gap + h2
        tx = int(cx - block_w / 2)
        tx = max(5, min(w - block_w - 5, tx))

        # Prefer placing the label ABOVE the ROI circle so the ROI stays clear.
        # If we're too close to the top edge, fall back to BELOW the circle.
        pad = 10
        y_top_above = int(cy - rr - pad - block_h)
        y_top_below = int(cy + rr + pad)
        if y_top_above >= 2:
            y_top = y_top_above
        else:
            y_top = y_top_below

        # Clamp within frame bounds (allow a small top margin for outlines)
        y_top = max(2, min(h - block_h - 2, y_top))
        ty = int(y_top + h1)  # baseline for line 1

        def put_outline(t, x, y):
            cv2.putText(frame_bgr, t, (x + 1, y + 1), font, scale, (0, 0, 0), 3)
            cv2.putText(frame_bgr, t, (x, y), font, scale, color, 1)

        put_outline(text1, tx, ty)
        put_outline(text2, tx, ty + line_gap + h2)

    # ------------------------------------------------------------------
    def process_with_cv(self, frame_bgr):
        """Detect ball using the basic CV detector (Lab redness + refinement)."""
        if self._cv_detector is None:
            # Detector not available
            self.missed_frames += 1
            return None, frame_bgr

        self._apply_cv_radial_gate()

        det, mask = self._cv_detector.analyze(frame_bgr)
        if det is None:
            self.missed_frames += 1
            return mask, frame_bgr

        raw_center = (int(round(det.x)), int(round(det.y)))
        radius = float(det.r)
        _, frame_bgr = self.apply_external_detection(frame_bgr, raw_center, radius, source="CV")
        return mask, frame_bgr


# ==============================================================================
# BALL MASK WINDOW CLASS
# ==============================================================================

class BallMaskWindow(QWidget):
    """
    Separate window showing thresholded MASK with:
      • Ball lock circle and HSV.
      • Shared sample point dot + HSV in bottom-left.
      • Sliders for H1/H2/S/V + kernel_size + EMA smoothing + min_circularity.
      • Rolling histograms for H/S/V.

    Frames are pushed in from mtDogMain via update_from_frame().
    """
    PICK_COLOR = (0, 0, 255)   # red

    def __init__(self, tracker: BallTracker):
        super().__init__()
        self.tracker = tracker

        self.setWindowTitle("Ball Mask & HSV Calibration")
        self.resize(700, 540)

        self.mask_label = QLabel("Mask")
        self.mask_label.setAlignment(Qt.AlignCenter)
        self.mask_label.setStyleSheet("background-color:#101010;")
        self.mask_label.setMouseTracking(True)
        self.setMouseTracking(True)

        # Allow the mask image to grow/shrink with the window
        self.mask_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mask_label.setMinimumSize(320, 240)
        self.resize(320 + 80, 240 + 220)

        self.last_bgr = None
        self.last_mask = None
        self.prev_gray = None   # for optical flow

        layout = QVBoxLayout()

        # Cheer banner (e.g., after FULL completion)
        self.cheer_frame = QFrame()
        self.cheer_frame.setStyleSheet(
            "background-color:#3a3300; border:1px solid #d6c200; border-radius:6px;"
        )
        cheer_layout = QHBoxLayout(self.cheer_frame)
        cheer_layout.setContentsMargins(10, 6, 10, 6)
        cheer_layout.setSpacing(8)

        self.cheer_label = QLabel("")
        self.cheer_label.setStyleSheet("color:#ffffff; font-size:12px; font-weight:600;")
        self.cheer_label.setWordWrap(True)

        self.cheer_clear_btn = QPushButton("Clear")
        self.cheer_clear_btn.setFixedWidth(70)
        self.cheer_clear_btn.setStyleSheet(
            "QPushButton{background:#d6c200;color:#000;border:none;border-radius:10px;padding:4px 10px;}"
            "QPushButton:hover{background:#fff3a0;}"
        )
        self.cheer_clear_btn.clicked.connect(self._on_clear_cheer_clicked)

        cheer_layout.addWidget(self.cheer_label, stretch=1)
        cheer_layout.addWidget(self.cheer_clear_btn)
        self.cheer_frame.setVisible(False)
        layout.addWidget(self.cheer_frame)

        layout.addWidget(self.mask_label, stretch=1)

        # Rolling HSV history (for histograms)
        self.hist_H = deque(maxlen=128) # Hue, queue for histogram
        self.hist_S = deque(maxlen=128) # Saturation, queue for histogram
        self.hist_V = deque(maxlen=128) # Value, queue for histogram

        # Small histogram views for H / S / V
        self.hist_label_H = QLabel("Hue (H)")
        self.hist_label_S = QLabel("Saturation (S)")
        self.hist_label_V = QLabel("Value (V)")

        # Live hover info (cursor HSV)  
        self.hover_xy = None
        self.hover_hsv = None

        for lab in (self.hist_label_H, self.hist_label_S, self.hist_label_V):
            lab.setMinimumHeight(80)
            lab.setStyleSheet(
                "background-color:#000000; color:#ffffff; font-size:10px;"
            )
            lab.setAlignment(Qt.AlignCenter)

        hist_layout = QHBoxLayout()
        hist_layout.setContentsMargins(4, 2, 4, 2)
        hist_layout.setSpacing(4)
        hist_layout.addWidget(self.hist_label_H)
        hist_layout.addWidget(self.hist_label_S)
        hist_layout.addWidget(self.hist_label_V)
        layout.addLayout(hist_layout)

        grid = QGridLayout()
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setSpacing(6)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)
        grid.setColumnMinimumWidth(1, 180)
        grid.setColumnMinimumWidth(3, 180)

        def make_slider(row, col, name, minimum, maximum, value, color_hex):
            lbl = QLabel(f"{name}:{value}")
            lbl.setStyleSheet("color:#ffffff; font-size:11px;")
            lbl.setFixedWidth(70)
            s = QSlider(Qt.Horizontal)
            s.setMinimum(minimum)
            s.setMaximum(maximum)
            s.setValue(value)
            s.setTickInterval(max(1, (maximum - minimum) // 10))
            s.setSingleStep(1)
            s.setStyleSheet(
                f"""
                QSlider::groove:horizontal {{
                    height: 6px;
                    background: #202020;
                    border: 1px solid #333333;
                    border-radius: 3px;
                }}
                QSlider::handle:horizontal {{
                    background: {color_hex};
                    border: 1px solid #d0d0d0;
                    width: 14px; height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {color_hex};
                    border: 1px solid #404040;
                    height: 6px;
                    border-radius: 3px;
                }}
                QSlider::add-page:horizontal {{
                    background: #202020;
                    border: 1px solid #404040;
                    height: 6px;
                    border-radius: 3px;
                }}
                """
            )
            grid.addWidget(lbl, row, col * 2)
            grid.addWidget(s, row, col * 2 + 1)
            return s, lbl

        def style_slider(slider: QSlider, color_hex: str = "#3daee9"):
            slider.setStyleSheet(
                f"""
                QSlider::groove:horizontal {{
                    height: 6px;
                    background: #202020;
                    border: 1px solid #333333;
                    border-radius: 3px;
                }}
                QSlider::handle:horizontal {{
                    background: {color_hex};
                    border: 1px solid #d0d0d0;
                    width: 14px; height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {color_hex};
                    border: 1px solid #404040;
                    height: 6px;
                    border-radius: 3px;
                }}
                QSlider::add-page:horizontal {{
                    background: #202020;
                    border: 1px solid #404040;
                    height: 6px;
                    border-radius: 3px;
                }}
                """
            )

        t = tracker
        # Hue Range 1 (low=orange, high=white to match histogram triangles)

        self.s_H1_low, self.lbl_H1_low = make_slider(0, 0, "H1 low", 0, 179, t.h1_min, "#ffb347")
        self.s_H1_high, self.lbl_H1_high = make_slider(0, 1, "H1 high", 0, 179, t.h1_max, "#ffffff")
        # Hue Range 2 (wrap-around: low=magenta, high=cyan for secondary hue segment)
        self.s_H2_low, self.lbl_H2_low = make_slider(1, 0, "H2 low", 0, 179, t.h2_min, "#ff00ff")
        self.s_H2_high, self.lbl_H2_high = make_slider(1, 1, "H2 high", 0, 179, t.h2_max, "#00ffff")
        # Saturation
        self.s_S_low, self.lbl_S_low = make_slider(2, 0, "S low", 0, 255, t.s_min, "#ffb347")
        self.s_S_high, self.lbl_S_high = make_slider(2, 1, "S high", 0, 255, t.s_max, "#ffffff")
        # Value
        self.s_V_low, self.lbl_V_low = make_slider(3, 0, "V low", 0, 255, t.v_min, "#ffb347")
        self.s_V_high, self.lbl_V_high = make_slider(3, 1, "V high", 0, 255, t.v_max, "#ffffff")

        # Morphology kernel slider with min/max labels
        row_kernel = 4
        kernel_label = QLabel(f"Kernel:{t.kernel_size}")
        kernel_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(kernel_label, row_kernel, 0)

        self.s_kernel = QSlider(Qt.Horizontal)
        self.s_kernel.setMinimum(1)
        self.s_kernel.setMaximum(15)
        self.s_kernel.setValue(t.kernel_size)
        self.s_kernel.setTickInterval(2)
        self.s_kernel.setSingleStep(2)
        style_slider(self.s_kernel)
        self.lbl_kernel = kernel_label

        ker_row_layout = QHBoxLayout()
        self.lbl_kernel_min = QLabel("1")
        self.lbl_kernel_min.setStyleSheet("color:#aaaaaa; font-size:10px;")
        self.lbl_kernel_max = QLabel("15")
        self.lbl_kernel_max.setStyleSheet("color:#aaaaaa; font-size:10px;")
        ker_row_layout.addWidget(self.lbl_kernel_min)
        ker_row_layout.addWidget(self.s_kernel)
        ker_row_layout.addWidget(self.lbl_kernel_max)
        grid.addLayout(ker_row_layout, row_kernel, 1, 1, 1)

        # EMA smoothing slider with min/max labels
        row_ema = 5
        ema_label = QLabel(f"EMA:{self.tracker.smooth_alpha:.2f}")
        ema_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(ema_label, row_ema, 0)

        self.slider_ema = QSlider(Qt.Horizontal)
        self.slider_ema.setRange(5, 90)  # 0.05 – 0.90
        self.slider_ema.setValue(int(self.tracker.smooth_alpha * 100))
        style_slider(self.slider_ema)

        self.lbl_ema = ema_label

        ema_row_layout = QHBoxLayout()
        self.lbl_ema_min = QLabel("0.05")
        self.lbl_ema_min.setStyleSheet("color:#aaaaaa; font-size:10px;")
        self.lbl_ema_max = QLabel("0.90")
        self.lbl_ema_max.setStyleSheet("color:#aaaaaa; font-size:10px;")
        ema_row_layout.addWidget(self.lbl_ema_min)
        ema_row_layout.addWidget(self.slider_ema)
        ema_row_layout.addWidget(self.lbl_ema_max)
        grid.addLayout(ema_row_layout, row_ema, 1, 1, 1)

        #-- kp slider for Dog Head movement control --#
        row_kp = 6
        kp_label = QLabel(f"Kp-Head:{self.tracker.head_tracker.cfg.kp:.1f}")
        kp_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(kp_label, row_kp, 0)

        self.slider_kp = QSlider(Qt.Horizontal) # Kp slider
        self.slider_kp.setRange(1, 50)  # Kp from 1 to 50
        self.slider_kp.setValue(int(self.tracker.head_tracker.cfg.kp))  # initial value from tracker config
        style_slider(self.slider_kp)

        self.lbl_kp = kp_label

        kp_row_layout = QHBoxLayout()
        self.lbl_kp_min = QLabel("1")   # minimum label=1
        self.lbl_kp_min.setStyleSheet("color:#aaaaaa; font-size:10px;")  # gray color, font size 10px
        self.lbl_kp_max = QLabel("50")  # maximum label=50
        self.lbl_kp_max.setStyleSheet("color:#aaaaaa; font-size:10px;")  # gray color, font size 10px
        kp_row_layout.addWidget(self.lbl_kp_min)    # add min label to layout
        kp_row_layout.addWidget(self.slider_kp)     # add slider to layout
        kp_row_layout.addWidget(self.lbl_kp_max)    # add max label to layout
        grid.addLayout(kp_row_layout, row_kp, 1, 1, 1)

        # --- CV radial gate toggle ---------------------------------
        row_cv_gate = 7
        cv_gate_label = QLabel("CV RadialGate")
        cv_gate_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(cv_gate_label, row_cv_gate, 0)

        self.chk_cv_radial_gate = QCheckBox("RadialGate (CV)")
        self.chk_cv_radial_gate.setChecked(bool(getattr(t, "cv_radial_gate_enabled", False)))
        self.chk_cv_radial_gate.setStyleSheet("color:#ffffff;")
        grid.addWidget(self.chk_cv_radial_gate, row_cv_gate, 1)

        # --- head tracking deadzone (deadband) -----------------------
        row_head_dead = 8
        head_dead_label = QLabel(f"Head-Deadzone:{self.tracker.head_tracker.cfg.deadband:.2f}")
        head_dead_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(head_dead_label, row_head_dead, 0)

        self.slider_head_deadzone = QSlider(Qt.Horizontal)
        # deadband range: 0.00 – 0.20 (in steps of 0.01)
        self.slider_head_deadzone.setRange(0, 20)
        self.slider_head_deadzone.setValue(int(round(self.tracker.head_tracker.cfg.deadband * 100)))
        style_slider(self.slider_head_deadzone)
        self.lbl_head_deadzone = head_dead_label

        head_dead_row_layout = QHBoxLayout()
        self.lbl_head_deadzone_min = QLabel("0.00")
        self.lbl_head_deadzone_min.setStyleSheet("color:#aaaaaa; font-size:10px;")
        self.lbl_head_deadzone_max = QLabel("0.20")
        self.lbl_head_deadzone_max.setStyleSheet("color:#aaaaaa; font-size:10px;")
        head_dead_row_layout.addWidget(self.lbl_head_deadzone_min)
        head_dead_row_layout.addWidget(self.slider_head_deadzone)
        head_dead_row_layout.addWidget(self.lbl_head_deadzone_max)
        grid.addLayout(head_dead_row_layout, row_head_dead, 1, 1, 1)

        # --- tracking mode selector ---------------------------------
        row_mode = 9
        mode_label = QLabel("Tracking mode")
        mode_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(mode_label, row_mode, 0)

        self.combo_tracking_mode = QComboBox()
        self.combo_tracking_mode.addItems(["Full tracking", "Head Tracking", "Body Tracking"])
        self.combo_tracking_mode.setStyleSheet(
            "color:#ffffff; background-color:#202020; border:1px solid #444444; border-radius:6px;"
        )
        self.combo_tracking_mode.setMinimumHeight(26)
        if self.tracker.tracking_mode == TRACKING_MODE_HEAD:
            default_index = 1
        elif self.tracker.tracking_mode == TRACKING_MODE_BODY:
            default_index = 2
        else:
            default_index = 0
        self.combo_tracking_mode.setCurrentIndex(default_index)
        grid.addWidget(self.combo_tracking_mode, row_mode, 1)

        # --- body tracking tuning sliders ----------------------------
        row_body_intv = 10
        body_intv_label = QLabel(f"Body intv:{t.body_tracking_interval:.2f}s")
        body_intv_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(body_intv_label, row_body_intv, 0)

        self.slider_body_interval = QSlider(Qt.Horizontal)
        self.slider_body_interval.setRange(10, 200)  # 0.10 – 2.00 sec
        self.slider_body_interval.setValue(int(round(t.body_tracking_interval * 100)))
        style_slider(self.slider_body_interval)
        self.lbl_body_interval = body_intv_label

        body_intv_row_layout = QHBoxLayout()
        self.lbl_body_interval_min = QLabel("0.10")
        self.lbl_body_interval_min.setStyleSheet("color:#aaaaaa; font-size:10px;")
        self.lbl_body_interval_max = QLabel("2.00")
        self.lbl_body_interval_max.setStyleSheet("color:#aaaaaa; font-size:10px;")
        body_intv_row_layout.addWidget(self.lbl_body_interval_min)
        body_intv_row_layout.addWidget(self.slider_body_interval)
        body_intv_row_layout.addWidget(self.lbl_body_interval_max)
        grid.addLayout(body_intv_row_layout, row_body_intv, 1, 1, 1)

        row_deadzone = 11
        deadzone_label = QLabel(f"Body-Deadzone:{t.body_deadzone_ratio:.2f}")
        deadzone_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(deadzone_label, row_deadzone, 0)

        self.slider_body_deadzone = QSlider(Qt.Horizontal)
        self.slider_body_deadzone.setRange(5, 40)  # 0.05 – 0.40
        self.slider_body_deadzone.setValue(int(round(t.body_deadzone_ratio * 100)))
        style_slider(self.slider_body_deadzone)
        self.lbl_body_deadzone = deadzone_label

        deadzone_row_layout = QHBoxLayout()
        self.lbl_body_deadzone_min = QLabel("0.05")
        self.lbl_body_deadzone_min.setStyleSheet("color:#aaaaaa; font-size:10px;")
        self.lbl_body_deadzone_max = QLabel("0.40")
        self.lbl_body_deadzone_max.setStyleSheet("color:#aaaaaa; font-size:10px;")
        deadzone_row_layout.addWidget(self.lbl_body_deadzone_min)
        deadzone_row_layout.addWidget(self.slider_body_deadzone)
        deadzone_row_layout.addWidget(self.lbl_body_deadzone_max)
        grid.addLayout(deadzone_row_layout, row_deadzone, 1, 1, 1)

        # --- body tracking proportional (Kp) -------------------------
        row_body_kp = 12
        body_kp_label = QLabel(f"Kp-Body:{getattr(t, 'body_kp', 0.0):.2f}")
        body_kp_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(body_kp_label, row_body_kp, 0)

        self.slider_body_kp = QSlider(Qt.Horizontal)
        self.slider_body_kp.setRange(0, 300)  # 0.00 – 3.00
        self.slider_body_kp.setValue(int(round(float(getattr(t, 'body_kp', 0.0)) * 100)))
        style_slider(self.slider_body_kp)
        self.lbl_body_kp = body_kp_label

        body_kp_row_layout = QHBoxLayout()
        self.lbl_body_kp_min = QLabel("0.00")
        self.lbl_body_kp_min.setStyleSheet("color:#aaaaaa; font-size:10px;")
        self.lbl_body_kp_max = QLabel("3.00")
        self.lbl_body_kp_max.setStyleSheet("color:#aaaaaa; font-size:10px;")
        body_kp_row_layout.addWidget(self.lbl_body_kp_min)
        body_kp_row_layout.addWidget(self.slider_body_kp)
        body_kp_row_layout.addWidget(self.lbl_body_kp_max)
        grid.addLayout(body_kp_row_layout, row_body_kp, 1, 1, 1)

        # --- body tracking policy toggle -----------------------------
        row_body_policy = 13
        body_policy_label = QLabel("Body backward")
        body_policy_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(body_policy_label, row_body_policy, 0)

        self.chk_body_allow_backward = QCheckBox("Allow backward")
        self.chk_body_allow_backward.setChecked(bool(getattr(t, "body_allow_backward", False)))
        self.chk_body_allow_backward.setStyleSheet("color:#ffffff;")
        grid.addWidget(self.chk_body_allow_backward, row_body_policy, 1)

        # --- lost-ball search + obstacle avoidance toggles ------------
        row_search = 14
        search_label = QLabel("Lost ball")
        search_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(search_label, row_search, 0)

        self.chk_search_forward = QCheckBox("Search forward (off = turn-left scan)")
        self.chk_search_forward.setChecked(bool(getattr(t, "search_forward_enabled", True)))
        self.chk_search_forward.setStyleSheet("color:#ffffff;")
        grid.addWidget(self.chk_search_forward, row_search, 1)

        row_obstacle = 15
        obstacle_label = QLabel("Obstacle")
        obstacle_label.setStyleSheet("color:#ffffff; font-size:11px;")
        grid.addWidget(obstacle_label, row_obstacle, 0)

        self.chk_obstacle_avoid = QCheckBox("Avoid (<=10cm turn-left)")
        self.chk_obstacle_avoid.setChecked(bool(getattr(t, "obstacle_avoid_enabled", True)))
        self.chk_obstacle_avoid.setStyleSheet("color:#ffffff;")
        grid.addWidget(self.chk_obstacle_avoid, row_obstacle, 1)

        # connect sliders
        for s in (
            self.s_H1_low,
            self.s_H1_high,
            self.s_H2_low,
            self.s_H2_high,
            self.s_S_low,
            self.s_S_high,
            self.s_V_low,
            self.s_V_high,
        ):
            s.valueChanged.connect(self._sliders_changed)

        self.s_kernel.valueChanged.connect(self._on_kernel_changed)
        self.slider_ema.valueChanged.connect(self._on_ema_changed)
        self.slider_kp.valueChanged.connect(self._on_kp_changed)
        self.slider_head_deadzone.valueChanged.connect(self._on_head_deadzone_changed)
        self.slider_body_interval.valueChanged.connect(self._on_body_interval_changed)
        self.slider_body_deadzone.valueChanged.connect(self._on_body_deadzone_changed)
        self.slider_body_kp.valueChanged.connect(self._on_body_kp_changed)
        self.chk_cv_radial_gate.toggled.connect(self._on_cv_radial_gate_changed)
        self.chk_body_allow_backward.toggled.connect(self._on_body_allow_backward_changed)
        self.chk_search_forward.toggled.connect(self._on_search_forward_changed)
        self.chk_obstacle_avoid.toggled.connect(self._on_obstacle_avoid_changed)
        self.combo_tracking_mode.currentIndexChanged.connect(
            self._on_tracking_mode_changed
        )

        layout.addLayout(grid)
        self.setLayout(layout)
        self.setStyleSheet("background-color:#181818; color:#ffffff;")  # dark bg 

    # ------------------------------------------------------------------
    def set_cheer(self, text: str | None, *, visible: bool | None = None):
        """Show/hide a cheer banner at the top of the Mask window."""
        if text is None:
            text = ""
        try:
            self.cheer_label.setText(str(text))
        except Exception:
            self.cheer_label.setText("")
        if visible is None:
            visible = bool(text)
        self.cheer_frame.setVisible(bool(visible))

    def _on_clear_cheer_clicked(self):
        """Clear cheer banner and notify owner (mtDogMain) to stop barking."""
        self.set_cheer("", visible=False)
        cb = getattr(self.tracker, "on_clear_cheer", None)
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def closeEvent(self, event):
        # Treat closing the mask window as "clear" so barking doesn't run forever.
        try:
            self._on_clear_cheer_clicked()
        except Exception:
            pass
        super().closeEvent(event)

    # ------------------------------------------------------------------
    def set_initial_view_size(self, width, height):
        """
        Called from mtDogMain to make the mask image area match
        the current color video display size on first show.
        """
        self.mask_label.setMinimumSize(width, height)
        self.resize(width + 80, height + 280)

    # ------------------------------------------------------------------
    def apply_hsv_ranges(
        self,
        h1_min: int,
        h1_max: int,
        h2_min: int,
        h2_max: int,
        s_min: int,
        s_max: int,
        v_min: int,
        v_max: int,
    ):
        """Programmatically set HSV ranges and refresh sliders/labels."""
        sliders = (
            self.s_H1_low,
            self.s_H1_high,
            self.s_H2_low,
            self.s_H2_high,
            self.s_S_low,
            self.s_S_high,
            self.s_V_low,
            self.s_V_high,
        )
        try:
            for s in sliders:
                s.blockSignals(True)
            self.s_H1_low.setValue(int(h1_min))
            self.s_H1_high.setValue(int(h1_max))
            self.s_H2_low.setValue(int(h2_min))
            self.s_H2_high.setValue(int(h2_max))
            self.s_S_low.setValue(int(s_min))
            self.s_S_high.setValue(int(s_max))
            self.s_V_low.setValue(int(v_min))
            self.s_V_high.setValue(int(v_max))
        finally:
            for s in sliders:
                s.blockSignals(False)

        # Sync tracker, labels, and mask once
        self._sliders_changed(0)

    # ------------------------------------------------------------------
    def _sliders_changed(self, _value):
        """Sync tracker ranges from dual sliders, update labels, autosave."""
        # Enforce high >= low for each pair
        if self.s_H1_high.value() < self.s_H1_low.value():
            self.s_H1_high.setValue(self.s_H1_low.value())
        if self.s_H2_high.value() < self.s_H2_low.value():
            self.s_H2_high.setValue(self.s_H2_low.value())
        if self.s_S_high.value() < self.s_S_low.value():
            self.s_S_high.setValue(self.s_S_low.value())
        if self.s_V_high.value() < self.s_V_low.value():
            self.s_V_high.setValue(self.s_V_low.value())

        t = self.tracker
        t.set_hue_ranges(
            self.s_H1_low.value(),
            self.s_H1_high.value(),
            self.s_H2_low.value(),
            self.s_H2_high.value(),
        )
        t.set_sv_ranges(
            self.s_S_low.value(),
            self.s_S_high.value(),
            self.s_V_low.value(),
            self.s_V_high.value(),
        )

        # Update labels
        self.lbl_H1_low.setText(f"H1L:{t.h1_min}")
        self.lbl_H1_high.setText(f"H1H:{t.h1_max}")
        self.lbl_H2_low.setText(f"H2L:{t.h2_min}")
        self.lbl_H2_high.setText(f"H2H:{t.h2_max}")
        self.lbl_S_low.setText(f"SL:{t.s_min}")
        self.lbl_S_high.setText(f"SH:{t.s_max}")
        self.lbl_V_low.setText(f"VL:{t.v_min}")
        self.lbl_V_high.setText(f"VH:{t.v_max}")
        self.lbl_kernel.setText(f"Kernel:{t.kernel_size}")

        # Autosave config
        t.save_default_config()

        if self.last_bgr is not None:
            _, mask = t.compute_mask(self.last_bgr)
            self.update_from_frame(self.last_bgr, mask)

    def _on_kernel_changed(self, value):
        t = self.tracker
        t.set_kernel_size(value)
        self.lbl_kernel.setText(f"Kernel:{t.kernel_size}")
        t.save_default_config()
        if self.last_bgr is not None:
            _, mask = t.compute_mask(self.last_bgr)
            self.update_from_frame(self.last_bgr, mask)

    # ------------------------------------------------------------------
    def update_from_frame(self, frame, mask):
        # Save the current frame for picker use
        self.current_frame = frame.copy()

        if frame is None or mask is None:
            return

        # keep originals for resizing & picker
        self.last_bgr = frame.copy()
        self.last_mask = mask.copy()

        h, w = self.last_mask.shape[:2]

        center_y = h // 2
        center_x = w // 2

        # Composite: overlay mask on color frame for display, with transparency
        alpha = 0.8  # mask opacity, 0.0 = color only, 1.0 = mask only
        color_bgr = self.last_bgr.copy()
        mask_bgr = cv2.cvtColor(self.last_mask, cv2.COLOR_GRAY2BGR)
        # Make mask white where mask > 0
        mask_bgr[np.where(self.last_mask > 0)] = (255, 255, 255)
        mask_color = cv2.addWeighted(color_bgr, 1 - alpha, mask_bgr, alpha, 0)  # blended image, mask over color, with transparency

        # ---- Guide overlays (deadzone + center '+') ----
        def draw_dashed_vline(x: int, color_bgr, thickness: int = 1, dash: int = 10, gap: int = 6):
            x = int(max(0, min(w - 1, x)))
            y = 0
            while y < h:
                y2 = min(h - 1, y + dash)
                cv2.line(mask_color, (x, y), (x, y2), color_bgr, thickness)
                y += dash + gap

        def draw_dashed_hline(y: int, color_bgr, thickness: int = 1, dash: int = 10, gap: int = 6):
            y = int(max(0, min(h - 1, y)))
            x = 0
            while x < w:
                x2 = min(w - 1, x + dash)
                cv2.line(mask_color, (x, y), (x2, y), color_bgr, thickness)
                x += dash + gap

        def draw_center_plus(color_bgr=(0, 200, 255), size: int = 10, thickness: int = 1):
            x0, y0 = int(center_x), int(center_y)
            cv2.line(mask_color, (x0 - size, y0), (x0 + size, y0), color_bgr, thickness)
            cv2.line(mask_color, (x0, y0 - size), (x0, y0 + size), color_bgr, thickness)

        # X deadzone (body tracking): center_x ± x_dead
        try:
            deadzone_ratio = float(getattr(self.tracker, "body_deadzone_ratio", 0.18))
        except Exception:
            deadzone_ratio = 0.18
        deadzone_ratio = max(0.05, min(0.50, deadzone_ratio))
        x_dead = max(20.0, w * deadzone_ratio)
        x1 = int(round(center_x - x_dead))
        x2 = int(round(center_x + x_dead))
        draw_dashed_vline(x1, (255, 255, 0))  # cyan (BGR)
        draw_dashed_vline(x2, (255, 255, 0))

        # Y deadzone (head tracking deadband): center_y ± y_dead
        try:
            deadband = float(getattr(self.tracker.head_tracker.cfg, "deadband", 0.02))
        except Exception:
            deadband = 0.02
        deadband = max(0.0, min(0.5, deadband))
        y_dead = (h / 2.0) * deadband
        y1 = int(round(center_y - y_dead))
        y2 = int(round(center_y + y_dead))
        draw_dashed_hline(y1, (255, 0, 255))  # magenta (BGR)
        draw_dashed_hline(y2, (255, 0, 255))

        # Center '+' marker
        draw_center_plus()

        # update window title with resolution
        self.setWindowTitle(f"Ball Mask & HSV Calibration {w}x{h}")

        # --- locked ball circle + HSV (using smoothed center & radius) ---
        if self.tracker.last_center is not None:
            cx, cy = self.tracker.last_center
            radius = int(self.tracker.last_radius or 12)
            cv2.circle(mask_color, (cx, cy), radius, (0, 255, 100), 2)
            # DEBUG: Draw a RED hexagon to mark selected center clearly
            pts = np.array([
                (cx + int(radius*0.866), cy - int(radius*0.5)),
                (cx + int(radius*0.866), cy + int(radius*0.5)),
                (cx, cy + radius),
                (cx - int(radius*0.866), cy + int(radius*0.5)),
                (cx - int(radius*0.866), cy - int(radius*0.5)),
                (cx, cy - radius),
            ], np.int32)
            cv2.polylines(mask_color, [pts], True, (0, 0, 255), 2)  # Red hexagon
            cv2.circle(mask_color, (cx, cy), 3, (0, 0, 255), -1)  # Red center dot

            if self.tracker.last_hsv is not None:
                H, S, V = self.tracker.last_hsv
                text1 = f"HSV({H},{S},{V})"
                text2 = f"({cx},{cy})"
                tx = max(5, cx - 40)
                ty = max(20, cy - 20)
                cv2.putText(
                    mask_color,
                    text1,
                    (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 100),
                    1,
                )
                cv2.putText(
                    mask_color,
                    text2,
                    (tx, ty + 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 100),
                    1,
                )

        else:
            # DEBUG: No center detected
            cv2.putText(
                mask_color,
                "[NO BALL DETECTED]",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )

        # --- draw trace of recent centers ---
        if self.tracker.trace_points:
            now_t = time.time()
            pts = [
                p for (p, t) in self.tracker.trace_points
                if now_t - t <= self.tracker.trace_max_age
            ]
            for i, p in enumerate(pts):
                cv2.circle(mask_color, p, 2, (0, 255, 255), -1)
                if i > 0:
                    cv2.line(mask_color, pts[i - 1], p, (0, 255, 255), 1)

 
        # --- sample-point marker + HUD in bottom-left (picker, click-and-stay) --- *** HSV HUD        
        if self.tracker.sample_point is not None and self.tracker.sample_hsv is not None:
            sx, sy = self.tracker.sample_point
            Hs, Ss, Vs = self.tracker.sample_hsv  # <--- always use the shared value

            # Draw only the picker dot, not HSV text near it
            cv2.circle(mask_color, (sx, sy), 6, self.PICK_COLOR, 2)
            cv2.circle(mask_color, (sx, sy), 2, self.PICK_COLOR, -1)

            # HUD at bottom left (always matches color window)
            text1 = f"HSV({Hs},{Ss},{Vs})"
            text2 = f"({sx},{sy})"
            cv2.putText(
                mask_color,
                text1,
                (5, h - 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                self.PICK_COLOR,
                1,
            )
            cv2.putText(
                mask_color,
                text2,
                (5, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                self.PICK_COLOR,
                1,
            )

        # --- Hover mouse info (cursor HSV, sticks to mouse pointer) --- *** HSV HUD
        if self.hover_xy is not None and self.hover_hsv is not None:
            cx, cy = self.hover_xy
            Hh, Sh, Vh = self.hover_hsv

            text1 = f"HSV({Hh},{Sh},{Vh})"
            text2 = f"({cx},{cy})"

            # Draw near the cursor with a smaller font
            base_x = cx + 8
            base_y = max(15, cy - 12)
            cv2.putText(
                mask_color,
                text1,
                (base_x, base_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 255),  # yellow for hover
                1,
            )
            cv2.putText(
                mask_color,
                text2,
                (base_x, base_y + 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 255),
                1,
            )

        # --- update rolling HSV history (for histograms) ---
        source_hsv = self.tracker.sample_hsv or self.tracker.last_hsv
        if source_hsv is not None:
            Hs, Ss, Vs = source_hsv
            self.hist_H.append(max(0, min(179, Hs)))   # Hue is 0..179
            self.hist_S.append(max(0, min(255, Ss)))
            self.hist_V.append(max(0, min(255, Vs)))
            self._update_histograms()


        # ===== HEAD TRACKING COMPASS OVERLAY (Bottom-Right Corner) =====
        if self.tracker.last_center is not None:
            current_angle = self.tracker.head_tracker.current_angle
            neutral_angle = self.tracker.head_tracker.cfg.neutral_deg
            min_deg = self.tracker.head_tracker.cfg.min_deg
            max_deg = self.tracker.head_tracker.cfg.max_deg

            # Compute ball-driven target angle (incremental control)
            cy = self.tracker.last_center[1]
            center_y = h / 2.0 if h else 0.0
            err_norm = (cy - center_y) / center_y if center_y else 0.0
            # For display: show what the next delta would be
            delta_cmd = -(self.tracker.head_tracker.cfg.kp * err_norm)
            delta_cmd = max(-self.tracker.head_tracker.cfg.max_step_deg, 
                           min(self.tracker.head_tracker.cfg.max_step_deg, delta_cmd))
            ball_angle = current_angle + delta_cmd
            ball_angle = max(min_deg, min(max_deg, ball_angle))
            pixel_error = cy - center_y

            # Calculate angle offset from neutral (positive = down, negative = up)
            angle_offset = current_angle - neutral_angle
            
            # Professional vector compass in bottom-right corner
            corner_pad = 50 # padding from corner
            #compass_cx = w - corner_pad # x position, width (w=400) minus padding
            #compass_cy = h - corner_pad # y position, height (h=300) minus padding
            compass_cx = w - corner_pad # x position, width (w=400) minus padding  (right corner)
            compass_cy = 20 + corner_pad # y position, height (h=300) minus padding (top right corner)
            compass_radius = 30  # radius of compass circle
            
            # Draw outer circle (compass background)
            cv2.circle(mask_color, (compass_cx, compass_cy), compass_radius, (100, 100, 100), 2)    # gray border
            cv2.circle(mask_color, (compass_cx, compass_cy), compass_radius - 2, (40, 40, 40), -1)  # dark fill
            
            # Draw center dot
            cv2.circle(mask_color, (compass_cx, compass_cy), 3, (0, 255, 255), -1)  # yellow center dot
            
            # Draw cardinal direction lines (up/down/center)
            # Up (blue, neutral position)
            cv2.line(mask_color, (compass_cx, compass_cy), (compass_cx, compass_cy - compass_radius), (200, 100, 0), 2) # blue-ish
            # Down (red)
            cv2.line(mask_color, (compass_cx, compass_cy), (compass_cx, compass_cy + compass_radius), (0, 50, 200), 2) # light red
            
            # Draw movement vector arrow based on angle offset
            # Convert angle to pixel position (scale: 90 deg = radius for wider range visibility)
            arrow_length = int((angle_offset / 3.0) * (compass_radius - 8))  # Scale expanded: 10deg = radius
            arrow_length = max(-compass_radius + 5, min(compass_radius - 5, arrow_length))
            
            arrow_end_y = compass_cy + arrow_length
            
            # Main arrow (green for tracking active)
            cv2.arrowedLine(
                mask_color,
                (compass_cx, compass_cy),
                (compass_cx, arrow_end_y),
                (0, 255, 0),  # Green
                thickness=3,
                tipLength=0.3
            )
            
            # Angle text above compass
            head_text =  f"Head Angle : {current_angle:.2f} deg"
            angle_text = f"Ball Angle : {ball_angle:.2f} deg"
            offset_text = f"  Offset   : {angle_offset:+.2f} deg"
            
            # Draw head angle and offset text above the compass (compact, with comments)
            cv2.putText(
                mask_color, head_text, (compass_cx - 70, compass_cy - compass_radius - 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 255), 1
            )
            cv2.putText(
                mask_color, angle_text, (compass_cx - 70, compass_cy - compass_radius - 15 ),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1
            )  # Head angle (yellow) vertical offset in deg, font size 0.3, thickness 1
            cv2.putText(
                mask_color, offset_text, (compass_cx - 70, compass_cy - compass_radius -4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1
            )  # Offset from neutral (green)  Horizontal offset in deg, font size 0.3, thickness 1

            # Extra debug: show pixel error and normalized error
            pix_err_x = int(round(cx - center_x))
            pix_err_y = int(round(cy - center_y))
            norm_err_x = (cx - center_x) / center_x if center_x else 0.0
            norm_err_y = (cy - center_y) / center_y if center_y else 0.0

            dbg_text2 = f"Pix Err ({pix_err_x:+d}, {pix_err_y:+d})"
            dbg_text3 = f"Norm :({norm_err_x:+.3f}, {norm_err_y:+.3f})"
            cv2.putText(
                mask_color,
                dbg_text2,
                (compass_cx - 100, compass_cy + compass_radius + 28),    # below compass, first line
                cv2.FONT_HERSHEY_SIMPLEX,
                0.33,
                (0, 200, 255),
                1,
            )
            cv2.putText(
                mask_color,
                dbg_text3,
                (compass_cx - 100, compass_cy + compass_radius + 40),    # below compass, second line
                cv2.FONT_HERSHEY_SIMPLEX,
                0.33,
                (0, 200, 255),
                1,
            )
            if self.tracker.missed_frames == 0:
                lock_text = "Lock: Strong"
                lock_color = (0, 255, 0)
            elif self.tracker.missed_frames < 2:
                lock_text = "Lock: Weak"
                lock_color = (0, 200, 255)
            else:
                if self.tracker.head_tracker.search_state == "searching":
                    lock_text = "Searching..."
                    lock_color = (0, 200, 255)
                else:
                    lock_text = "Idle"
                    lock_color = (255, 100, 0)
            lock_y = compass_cy + compass_radius + 6
            cv2.putText(
                mask_color,
                lock_text,
                (compass_cx - 20, lock_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                lock_color,
                1,
            )
            
            # Direction indicator label below compass
            if angle_offset > 0.2:    # threshold to avoid jitter
                direction = "v DOWN"
                color = (0, 100, 255) # light red
            elif angle_offset < -0.2:    # threshold to avoid jitter
                direction = "^ UP"
                color = (255, 100, 0) # light blue   
            else:
                direction = "*Center"
                color = (0, 255, 255)
            
            # Draw direction label below compass
            cv2.putText(
                mask_color,
                direction,  # direction label based on angle offset,  DOWN/UP/Center
                (compass_cx - 20, lock_y + 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.30,
                color,
                1
            )

        # --- push mask_color to QLabel ---
        # ---- On-screen debug from body tracking (set by mtDogMain) ----
        dbg_lines = getattr(self.tracker, "body_debug_lines", None)
        if dbg_lines:
            y0 = 18
            for i, line in enumerate(list(dbg_lines)[:4]):
                y = y0 + i * 14
                # Outline for contrast
                for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    cv2.putText(
                        mask_color,
                        str(line),
                        (8 + dx, y + dy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.38,
                        (0, 0, 0),
                        2,
                    )
                cv2.putText(
                    mask_color,
                    str(line),
                    (8, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,
                    (0, 255, 255),
                    1,
                )

        mask_rgb = cv2.cvtColor(mask_color, cv2.COLOR_BGR2RGB)
        qimg = QImage(mask_rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        pix = pix.scaled(
            self.mask_label.width(),
            self.mask_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.mask_label.setPixmap(pix)

        # --- optical flow overlay ---
        # self._draw_optical_flow(self.last_bgr, mask_color)  #  pass color frame for optical flow

    # ------------------------------------------------------------------
    def _update_histograms(self):
        """
        Render rolling histograms for H, S, V into three labels.
        Each histogram uses the last 256 samples.
        We also draw:
            • channel title (Hue / Saturation / Value)
            • peak bin index
            • standard deviation
            • slider low / high as little triangles.
        """
        # ----- render_hist() -------------------------------------------------------------
        def render_hist(data, label, channel, low_val, high_val, extra_ranges=None):
            if not data or label.width() <= 0 or label.height() <= 0:
                return

            values = np.array(list(data), dtype=np.float32)

            # Raw histogram in 0..255 bins (Hue really uses 0..179)
            hist = np.bincount(values.astype(np.uint8), minlength=256).astype(np.float32)
            if hist.max() > 0:
                hist /= hist.max()

            h_img = 80
            w_img = 256
            img = np.zeros((h_img, w_img, 3), dtype=np.uint8)

            # Channel-specific settings
            if channel == "H":
                bar_color = (0, 255, 0)     # green
                title = "Hue"
                max_val = 179.0             # OpenCV Hue: 0..179
            elif channel == "S":
                bar_color = (255, 0, 0)     # blue-ish (BGR)
                title = "Saturation"
                max_val = 255.0
            else:
                bar_color = (0, 255, 255)   # yellow
                title = "Value"
                max_val = 255.0

            # Draw histogram bars, with a special x→bin mapping for Hue
            for x in range(w_img):
                if channel == "H":
                    # Map canvas x (0..w_img-1) → hue bin (0..179)
                    src_bin = int(round(x / (w_img - 1) * 179.0))
                else:
                    src_bin = x

                src_bin = max(0, min(255, src_bin))
                v = hist[src_bin]
                if v <= 0:
                    continue

                y0 = h_img - 1
                y1 = int(h_img * (1.0 - v))
                img[y1:y0, x, :] = bar_color

            # stats
            std = float(values.std())
            peak_bin = int(np.argmax(hist))

            # Slider value → x-position mapping
            if channel == "H":
                def val_to_x(v):
                    v = max(0.0, min(max_val, float(v)))     # 0..179
                    return int(round(v / max_val * (w_img - 1)))
            else:
                def val_to_x(v):
                    v = max(0.0, min(max_val, float(v)))     # 0..255
                    return int(round(v / max_val * (w_img - 1)))

            # triangles for low/high ranges
            tri_specs = []

            # main low / high markers
            tri_specs.append((val_to_x(low_val), (0, 180, 255)))     # orange-ish
            tri_specs.append((val_to_x(high_val), (255, 255, 255)))  # white

            # optional extra ranges (e.g. H2L/H2H)
            if extra_ranges:
                for v, color in extra_ranges:
                    tri_specs.append((val_to_x(v), color))

            # draw triangles
            for x_pos, color in tri_specs:
                for dy in range(0, 6):
                    xs = x_pos - dy
                    xe = x_pos + dy
                    y = h_img - 1 - dy
                    if 0 <= y < h_img:
                        xs = max(0, xs)
                        xe = min(w_img - 1, xe)
                        img[y, xs : xe + 1] = color

            # overlay text: title + peak + std dev
            text_title = f"{title}"
            text_stats = f"pk:{peak_bin}  SD:{std:.1f}"

            cv2.putText(
                img,
                text_title,
                (4, 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
            )
            cv2.putText(
                img,
                text_stats,
                (4, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (200, 200, 200),
                1,
            )

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            qimg = QImage(img_rgb.data, w_img, h_img, 3 * w_img, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg)
            pix = pix.scaled(
                label.width(),
                label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            label.setPixmap(pix)
        # ------------------------------------------------------------------    

        # current slider values
        H1L = self.tracker.h1_min
        H1H = self.tracker.h1_max
        H2L = self.tracker.h2_min
        H2H = self.tracker.h2_max
        S_L = self.tracker.s_min
        S_H = self.tracker.s_max
        V_L = self.tracker.v_min
        V_H = self.tracker.v_max

        # Hue histogram with both H1 and H2 range markers
        extra_hue_ranges = [
            (H2L, (255, 0, 255)),   # magenta for H2 low
            (H2H, (0, 255, 255)),   # cyan for H2 high
        ]
        render_hist(self.hist_H, self.hist_label_H, "H", H1L, H1H, extra_hue_ranges)
        render_hist(self.hist_S, self.hist_label_S, "S", S_L, S_H, None)
        render_hist(self.hist_V, self.hist_label_V, "V", V_L, V_H, None)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _update_sample_from_pos(self, global_pos):
        """Map a position in this widget to image coords and update tracker sample."""
        if self.last_bgr is None or self.last_mask is None:
            return

        h, w = self.last_mask.shape[:2]

        # Map from widget coords -> label coords
        label_pos = self.mask_label.mapFrom(self, global_pos)
        lx, ly = label_pos.x(), label_pos.y()
        label_w = self.mask_label.width()
        label_h = self.mask_label.height()

        scale = min(label_w / w, label_h / h)
        disp_w = int(w * scale)
        disp_h = int(h * scale)
        off_x = (label_w - disp_w) // 2
        off_y = (label_h - disp_h) // 2

        # Click outside the displayed image → ignore
        if not (off_x <= lx < off_x + disp_w and off_y <= ly < off_y + disp_h):
            return

        # Map back to image pixel
        ix = int((lx - off_x) / scale)
        iy = int((ly - off_y) / scale)
        ix = max(0, min(w - 1, ix))
        iy = max(0, min(h - 1, iy))

        hsv = cv2.cvtColor(self.last_bgr, cv2.COLOR_BGR2HSV)
        H, S, V = [int(v) for v in hsv[iy, ix]]
        self.tracker.set_sample_point((ix, iy), (H, S, V))

        # Immediate redraw so picker HUD + histogram update
        self.update_from_frame(self.last_bgr, self.last_mask)

    def mouseMoveEvent(self, event):
        self._update_hover_from_event(event)        # Hover HSV update, but no pick, just hover with mouse move, without click
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Pick sample point when clicking in Mask window."""
        if event.button() == Qt.LeftButton:
            self._update_sample_from_pos(event.pos())
        super().mousePressEvent(event)   
    
    # ------------------------------------------------------------------
    def _update_hover_from_event(self, event):          # Hover HSV under mouse cursor 
        """Map a position in this widget to image coords and update hover_xy, hover_hsv.""" 
        if self.last_bgr is None:
            self.hover_xy = None
            self.hover_hsv = None
            return

        h, w = self.last_bgr.shape[:2]

        # Map Qt widget → mask_label coords
        label_pos = self.mask_label.mapFrom(self, event.pos())
        lx, ly = label_pos.x(), label_pos.y()
        Lw = self.mask_label.width()
        Lh = self.mask_label.height()

        scale = min(Lw / w, Lh / h)
        disp_w = int(w * scale)
        disp_h = int(h * scale)
        off_x = (Lw - disp_w) // 2
        off_y = (Lh - disp_h) // 2

        if not (off_x <= lx < off_x + disp_w and off_y <= ly < off_y + disp_h):
            self.hover_xy = None
            self.hover_hsv = None
            return

        ix = int((lx - off_x) / scale)
        iy = int((ly - off_y) / scale)
        ix = max(0, min(w - 1, ix))
        iy = max(0, min(h - 1, iy))

        hsv = cv2.cvtColor(self.last_bgr, cv2.COLOR_BGR2HSV)
        H, S, V = [int(v) for v in hsv[iy, ix]]

        self.hover_xy = (ix, iy)
        self.hover_hsv = (H, S, V)

    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        """
        When the user resizes the Mask window, rescale the last frame
        to the new label size (same behavior as color window).
        """
        super().resizeEvent(event)
        if self.last_bgr is not None and self.last_mask is not None:
            self.update_from_frame(self.last_bgr, self.last_mask)

    # ------------------------------------------------------------------
    def _on_ema_changed(self, value):
        """Slider callback for EMA smoothing."""
        # map slider [5..90] to alpha [0.05..0.90]
        alpha = max(0.05, min(0.90, value / 100.0))
        self.tracker.smooth_alpha = alpha
        self.lbl_ema.setText(f"EMA:{alpha:.2f}")
        self.tracker.save_default_config()

    def _on_kp_changed(self, value):
        """Slider callback for head Kp."""
        kp = max(1.0, min(50.0, float(value)))
        self.tracker.head_tracker.cfg.kp = kp
        self.lbl_kp.setText(f"Kp-Head:{kp:.1f}")
        self.tracker.save_default_config()  # save config after changing Kp

    def _on_head_deadzone_changed(self, value):
        """Slider callback for head tracking deadzone (deadband)."""
        deadband = max(0.0, min(0.20, float(value) / 100.0))
        self.tracker.head_tracker.cfg.deadband = deadband
        self.lbl_head_deadzone.setText(f"Head-Deadzone:{deadband:.2f}")
        self.tracker.save_default_config()
        if self.last_bgr is not None and self.last_mask is not None:
            self.update_from_frame(self.last_bgr, self.last_mask)

    def _on_tracking_mode_changed(self, index):
        """Update tracking mode selection and persist it."""
        if index == 1:
            mode = TRACKING_MODE_HEAD
        elif index == 2:
            mode = TRACKING_MODE_BODY
        else:
            mode = TRACKING_MODE_FULL
        self.tracker.set_tracking_mode(mode)
        self.tracker.save_default_config()

    def _on_body_interval_changed(self, value):
        """Slider callback for body tracking command interval."""
        interval = max(0.10, min(2.00, float(value) / 100.0))
        self.tracker.body_tracking_interval = interval
        self.lbl_body_interval.setText(f"Body intv:{interval:.2f}s")
        self.tracker.save_default_config()

    def _on_body_deadzone_changed(self, value):
        """Slider callback for body tracking deadzone ratio."""
        ratio = max(0.05, min(0.40, float(value) / 100.0))
        self.tracker.body_deadzone_ratio = ratio
        self.lbl_body_deadzone.setText(f"Body-Deadzone:{ratio:.2f}")
        self.tracker.save_default_config()

    def _on_body_kp_changed(self, value):
        """Slider callback for body tracking proportional speed scaling (Kp)."""
        kp = max(0.0, min(3.0, float(value) / 100.0))
        self.tracker.body_kp = kp
        self.lbl_body_kp.setText(f"Kp-Body:{kp:.2f}")
        self.tracker.save_default_config()

    def _on_body_allow_backward_changed(self, checked: bool):
        """Checkbox callback for allowing backward motion in body tracking."""
        self.tracker.body_allow_backward = bool(checked)
        self.tracker.save_default_config()

    def _on_cv_radial_gate_changed(self, checked: bool):
        """Checkbox callback for CV radial gate enable/disable."""
        self.tracker.cv_radial_gate_enabled = bool(checked)
        try:
            self.tracker._apply_cv_radial_gate()
        except Exception:
            pass
        self.tracker.save_default_config()

    def _on_search_forward_changed(self, checked: bool):
        """Checkbox callback for searching forward when the ball is lost."""
        self.tracker.search_forward_enabled = bool(checked)
        self.tracker.save_default_config()

    def _on_obstacle_avoid_changed(self, checked: bool):
        """Checkbox callback for obstacle avoidance while searching."""
        self.tracker.obstacle_avoid_enabled = bool(checked)
        self.tracker.save_default_config()

    def _draw_optical_flow(self, bgr_frame, mask_canvas):
        """Compute dense Farneback optical flow and overlay sparse arrows on mask_canvas."""
        gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
        if self.prev_gray is None:
            self.prev_gray = gray
            return
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        step = 16  # arrow grid step
        h, w = gray.shape
        for y in range(step//2, h, step):
            for x in range(step//2, w, step):
                fx, fy = flow[y, x]
                end_pt = (int(x + fx), int(y + fy))
                cv2.arrowedLine(mask_canvas, (x, y), end_pt, (0, 200, 255), 1, tipLength=0.3)
        self.prev_gray = gray


# === end of file ===
