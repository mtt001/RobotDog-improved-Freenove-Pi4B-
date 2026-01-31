#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : ai_vision_controller.py
 Author : MT & GitHub Copilot

 Description:
     GPT/AI Vision controller extracted from mtDogMain.py (CameraWindow).
     Maintains AI detector state, filtering helpers, HSV auto-calibration,
     and test histogram updates.

 v1.00  (2026-01-31 21:40)    : Initial AI Vision controller extraction
     • Move GPT Vision helper methods + state from CameraWindow into controller.
===============================================================================
"""

from __future__ import annotations

import time

import cv2
import numpy as np

from mtBallDetectAI import AIVisionBallDetector


class AIVisionController:
    def __init__(self, host, *, hist_window_factory=None):
        self._host = host
        self._hist_window_factory = hist_window_factory

        # ---------- AI Vision (test module) ----------
        host.ai_vision_enabled = False
        host.ai_detector = AIVisionBallDetector()
        host.ai_detect_interval_s = 1.0
        host._ai_last_ts = 0.0
        host._ai_detections = []
        host._ai_request_sent = False
        host._ai_beep_last_ts = 0.0
        # Trial mode: one click -> one API call (no continuous polling)
        host.ai_one_shot_mode = True
        host._ai_one_shot_pending = False
        host._gpt_snapshot_count = 0
        host._ai_last_error_msg = ""

        # Status message to show on the Color window (e.g. filtered/rejected)
        host._ai_status_msg = ""
        host._ai_status_ts = 0.0
        # AI post-filtering (reduce false positives)
        host.ai_score_min = 0.25
        host.ai_hsv_filter_enabled = False
        # Accept orange/red-ish hues in OpenCV HSV (0-179) - wider range
        host.ai_hue_ranges = [(0, 40), (150, 179)]
        host.ai_min_s = 25  # Lower saturation threshold
        host.ai_min_v = 25  # Lower value threshold
        host.ai_hist_window = None

        # Auto-calibrate HSV from AI detection (for mask-based tracking)
        host.ai_auto_hsv_enabled = True
        host.ai_auto_hsv_applied = False
        host.ai_auto_hsv_percentile_lo = 15
        host.ai_auto_hsv_percentile_hi = 85
        host.ai_auto_hsv_margin_h = 8
        host.ai_auto_hsv_margin_s = 20
        host.ai_auto_hsv_margin_v = 20
        host.ai_auto_hsv_inner_ratio = 0.6

        # Refine AI circle using HSV mask (reduce radius gap)
        host.ai_refine_enabled = True
        host.ai_refine_roi_scale = 1.2
        host.ai_refine_min_area_ratio = 0.01

    def disable_due_to_error(self, reason: str):
        host = self._host
        host.ai_vision_enabled = False
        host._ai_detections = []
        host._ai_request_sent = False
        host._ai_one_shot_pending = False
        host.ai_auto_hsv_applied = False
        host._ai_last_error_msg = str(reason or "AI error").strip()
        host._ai_status_msg = ""
        host._ai_status_ts = 0.0
        host._yolo_detections = []
        host._yolo_last_error_msg = ""
        print(f"[GPT][ERR] GPT Vision stopped: {host._ai_last_error_msg}")
        # Button style → teal (OFF)
        try:
            host.btn_AIVision.setStyleSheet(
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

    def set_status(self, msg: str, *, ttl_s: float = 3.0):
        """Set a short-lived AI status message for the Color window overlay."""
        host = self._host
        host._ai_status_msg = str(msg or "").strip()
        # store expiry time to avoid stale overlays
        try:
            host._ai_status_ts = time.time() + float(ttl_s)
        except Exception:
            host._ai_status_ts = time.time() + 3.0

    def ai_det_to_px(self, det, w: int, h: int):
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

    def refine_ai_circle(self, frame_bgr, det):
        if frame_bgr is None:
            return det
        h_img, w_img = frame_bgr.shape[:2]
        px = self.ai_det_to_px(det, w_img, h_img)
        if not px:
            return det
        x, y, r, score = px
        if r <= 4:
            return det

        host = self._host
        roi_scale = float(getattr(host, "ai_refine_roi_scale", 1.2) or 1.2)
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

        t = host.ball_tracker
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
        min_area = float(host.ai_refine_min_area_ratio) * float(roi_w * roi_h)
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

    def auto_calibrate_hsv_from_ai(self, frame_bgr, det) -> bool:
        host = self._host
        if frame_bgr is None:
            return False
        if not bool(getattr(host, "ai_auto_hsv_enabled", False)):
            return False
        if bool(getattr(host, "ai_auto_hsv_applied", False)):
            return False

        h_img, w_img = frame_bgr.shape[:2]
        px = self.ai_det_to_px(det, w_img, h_img)
        if not px:
            return False
        x, y, r, score = px
        if r <= 4:
            return False
        if score < float(getattr(host, "ai_score_min", 0.0)):
            return False

        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            return False

        inner_ratio = float(getattr(host, "ai_auto_hsv_inner_ratio", 0.6) or 0.6)
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
        pct_hi = float(getattr(host, "ai_auto_hsv_percentile_hi", 85) or 85)
        delta = float(np.percentile(dist, pct_hi)) + float(getattr(host, "ai_auto_hsv_margin_h", 8) or 8)
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

        pct_lo = float(getattr(host, "ai_auto_hsv_percentile_lo", 15) or 15)
        s_lo = float(np.percentile(s_vals, pct_lo))
        s_hi = float(np.percentile(s_vals, pct_hi))
        v_lo = float(np.percentile(v_vals, pct_lo))
        v_hi = float(np.percentile(v_vals, pct_hi))

        s_min = max(0, int(round(s_lo - float(getattr(host, "ai_auto_hsv_margin_s", 20) or 20))))
        s_max = min(255, int(round(s_hi + float(getattr(host, "ai_auto_hsv_margin_s", 20) or 20))))
        v_min = max(0, int(round(v_lo - float(getattr(host, "ai_auto_hsv_margin_v", 20) or 20))))
        v_max = min(255, int(round(v_hi + float(getattr(host, "ai_auto_hsv_margin_v", 20) or 20))))

        # Apply to tracker
        host.ball_tracker.set_hue_ranges(h1_min, h1_max, h2_min, h2_max)
        host.ball_tracker.set_sv_ranges(s_min, s_max, v_min, v_max)
        host.ball_tracker.save_default_config()

        # Update picker to ball center
        try:
            Hc, Sc, Vc = [int(v) for v in hsv_img[y, x]]
            host.ball_tracker.set_sample_point((x, y), (Hc, Sc, Vc))
        except Exception:
            pass

        # Sync mask window sliders if open
        if host.ball_mask_window is not None:
            try:
                host.ball_mask_window.apply_hsv_ranges(
                    h1_min, h1_max, h2_min, h2_max, s_min, s_max, v_min, v_max
                )
            except Exception:
                pass

        host.ai_auto_hsv_applied = True
        print(
            f"[AI] Auto HSV from AI: H1({h1_min}-{h1_max}) H2({h2_min}-{h2_max}) "
            f"S({s_min}-{s_max}) V({v_min}-{v_max})"
        )
        return True

    def maybe_update_test_hist(
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
        host = self._host
        if src_frame_bgr is None:
            return

        if center_xy is None:
            try:
                center_xy = getattr(host.ball_tracker, "sample_point", None)
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
            interval_s_eff = float(host.test_hist_interval_s if interval_s is None else interval_s)
        except Exception:
            interval_s_eff = 1.0
        interval_s_eff = max(0.0, interval_s_eff)

        last_ts = float(getattr(host, "_test_hist_last_ts", 0.0) or 0.0)
        last_mode = str(getattr(host, "_test_hist_last_mode", "") or "")
        allow = (mode_label != last_mode) or (interval_s_eff <= 0.0) or ((now - last_ts) >= interval_s_eff)
        if not allow:
            return

        if host.ai_hist_window is None:
            if self._hist_window_factory is None:
                return
            host.ai_hist_window = self._hist_window_factory()
        if not host.ai_hist_window.isVisible():
            host.ai_hist_window.show()

        hz = (1.0 / interval_s_eff) if interval_s_eff > 0 else None
        host.ai_hist_window.set_context(mode_label, model_label, update_hz=hz)
        rr = float(radius_px or 0.0)
        if rr <= 0.0:
            rr = 12.0
        host.ai_hist_window.update_histogram(
            src_frame_bgr,
            cx,
            cy,
            rr,
            thresholds=thresholds,
            mask_combined=mask_combined,
            roi_rect=roi_rect,
        )

        host._test_hist_last_ts = now
        host._test_hist_last_mode = mode_label
