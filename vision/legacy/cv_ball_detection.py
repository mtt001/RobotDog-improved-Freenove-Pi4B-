#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : cv_ball_detection.py
 Author : MT & GitHub Copilot

 Description:
     CV-only ball detection controller extracted from mtDogMain.py (CameraWindow).
     Maintains CV detection state, timing, debug capture, and overlay gating.

 v1.00  (2026-01-31 17:25)    : Initial CV detection controller extraction
     • Extract OpenCV CV Ball detection pipeline from CameraWindow.
===============================================================================
"""

from __future__ import annotations

import time

import cv2


class CVBallDetectionController:
    def __init__(self, host):
        self._host = host

        self._host.cv_ball_enabled = False
        # CV Ball test-mode update rate (Hz-limited so UI stays smooth)
        self._host.cv_ball_interval_s = 1.0   # in seconds ,  1 Hz , ## default 0.25 Sec (4 Hz)
        # Hide CV overlay quickly when the last accepted detection is stale
        self._host.cv_ball_overlay_ttl_s = 0.35  # in seconds ,  0.35 Sec , Explain: hide overlay if no detection within this time
        self._host._cv_ball_last_ts = 0.0
        self._host._cv_ball_last_mask = None
        self._host._cv_ball_last_hist_mask = None
        self._host._cv_update_count = 0
        self._host._cv_detect_count = 0
        self._host._cv_last_status = ""
        self._host._cv_last_status_ts = 0.0
        self._host._cv_ball_last_debug_vis = None
        self._host._cv_ball_last_debug_text = ""
        self._host._cv_ball_last_thresholds = None
        self._host._cv_ball_last_ranked_masks = []
        self._host._cv_ball_last_roi_rect = None

    def on_cv_debug_radial_gate_changed(self, checked: bool):
        """Toggle CV radial gate from CV debug window (experimental)."""
        try:
            self._host.ball_tracker.cv_radial_gate_enabled = bool(checked)
            self._host.ball_tracker._apply_cv_radial_gate()
            self._host.ball_tracker.save_default_config()
            state = "ON" if bool(checked) else "OFF"
            print(f"[CV] RadialGate {state} (debug window).")
        except Exception:
            pass

    def detect(self, frame_bgr):
        host = self._host
        if frame_bgr is None:
            return None, frame_bgr, None, False

        mask = None
        ball_center = None
        is_fresh = False

        now_cv = time.time()
        if (now_cv - float(getattr(host, "_cv_ball_last_ts", 0.0) or 0.0)) >= float(
            getattr(host, "cv_ball_interval_s", 1.0) or 1.0
        ):
            host._cv_ball_last_ts = now_cv
            try:
                host._cv_update_count = int(getattr(host, "_cv_update_count", 0) or 0) + 1
            except Exception:
                host._cv_update_count = 1
            mask, frame_bgr = host.ball_tracker.process_with_cv(frame_bgr)
            try:
                if int(getattr(host.ball_tracker, "missed_frames", 0) or 0) == 0:
                    host._cv_detect_count = int(getattr(host, "_cv_detect_count", 0) or 0) + 1
            except Exception:
                pass
            try:
                missed0 = int(getattr(host.ball_tracker, "missed_frames", 0) or 0)
                host._cv_last_status = "Detected !" if missed0 == 0 else "No Ball !"
                host._cv_last_status_ts = now_cv
            except Exception:
                host._cv_last_status = "No Ball !"
                host._cv_last_status_ts = now_cv
            host._cv_ball_last_mask = mask
            # Capture detector debug (thresholds + mask panes) for debug windows.
            try:
                cv_det = getattr(host.ball_tracker, "_cv_detector", None)
                dbg = getattr(cv_det, "last_debug", None) if cv_det is not None else None
                if isinstance(dbg, dict):
                    host._cv_ball_last_debug_vis = dbg.get("vis", None)
                    host._cv_ball_last_debug_text = str(dbg.get("text", "") or "")
                    host._cv_ball_last_thresholds = dbg.get("thresholds", None)
                    try:
                        refine_dbg = dbg.get("refine", {}) or {}
                        x0 = refine_dbg.get("roi_x0", None)
                        y0 = refine_dbg.get("roi_y0", None)
                        x1 = refine_dbg.get("roi_x1", None)
                        y1 = refine_dbg.get("roi_y1", None)
                        if x0 is not None and y0 is not None and x1 is not None and y1 is not None:
                            host._cv_ball_last_roi_rect = (int(x0), int(y0), int(x1), int(y1))
                        else:
                            host._cv_ball_last_roi_rect = None
                    except Exception:
                        host._cv_ball_last_roi_rect = None
                    masks_dbg = dbg.get("masks", {}) or {}
                    hist_mask = masks_dbg.get("refined", None)
                    host._cv_ball_last_hist_mask = hist_mask if hist_mask is not None else mask
                    host._cv_ball_last_ranked_masks = masks_dbg.get("ranked", []) or []
            except Exception:
                pass
            if host._cv_ball_last_hist_mask is None:
                host._cv_ball_last_hist_mask = mask
        else:
            mask = getattr(host, "_cv_ball_last_mask", None)
            # Draw last known CV result so the overlay stays visible at UI FPS,
            # but only while detection is still "locked" (missed_frames==0).
            try:
                c0 = getattr(host.ball_tracker, "last_center", None)
                r0 = float(getattr(host.ball_tracker, "last_radius", 0.0) or 0.0)
                missed0 = int(getattr(host.ball_tracker, "missed_frames", 0) or 0)
                last_ok_ts = float(getattr(host.ball_tracker, "last_update_ts", 0.0) or 0.0)
                ttl_s = max(
                    float(getattr(host, "cv_ball_overlay_ttl_s", 0.35) or 0.35),
                    float(getattr(host, "cv_ball_interval_s", 1.0) or 1.0) * 1.1,
                )
                is_fresh = (missed0 == 0) and (last_ok_ts > 0.0) and ((time.time() - last_ok_ts) <= ttl_s)
                if is_fresh and c0 is not None and r0 > 1.0:
                    # Use raw (pre-draw) frame for HSV sampling so text doesn't perturb HSV.
                    hsv_src = host.last_display_frame_bgr if host.last_display_frame_bgr is not None else frame_bgr
                    if hasattr(host.ball_tracker, "draw_detection_overlay"):
                        host.ball_tracker.draw_detection_overlay(
                            frame_bgr,
                            source="CV",
                            hsv_source_bgr=hsv_src,
                            dashed_inner=True,
                        )
                    else:
                        cx0, cy0 = int(c0[0]), int(c0[1])
                        cv2.circle(frame_bgr, (cx0, cy0), int(round(r0)), (255, 255, 0), 2)
                        cv2.circle(frame_bgr, (cx0, cy0), 2, (255, 255, 0), -1)
            except Exception:
                pass

        # Treat stale CV detections as "no ball" for UI perception.
        try:
            missed0 = int(getattr(host.ball_tracker, "missed_frames", 0) or 0)
            last_ok_ts = float(getattr(host.ball_tracker, "last_update_ts", 0.0) or 0.0)
            ttl_s = max(
                float(getattr(host, "cv_ball_overlay_ttl_s", 0.35) or 0.35),
                float(getattr(host, "cv_ball_interval_s", 1.0) or 1.0) * 1.1,
            )
            is_fresh = (missed0 == 0) and (last_ok_ts > 0.0) and ((time.time() - last_ok_ts) <= ttl_s)
        except Exception:
            is_fresh = False
        ball_center = host.ball_tracker.last_center if is_fresh else None
        try:
            host._ball_locked = bool(ball_center is not None and int(getattr(host.ball_tracker, "missed_frames", 0) or 0) == 0)
            host._ball_lock_source = "CV" if host._ball_locked else ""
        except Exception:
            host._ball_locked = False
            host._ball_lock_source = ""

        # Shared histogram window (Object Detection Test) @ throttled rate
        try:
            src = host.last_display_frame_bgr if host.last_display_frame_bgr is not None else frame_bgr
            rr = float(getattr(host.ball_tracker, "last_radius", 0.0) or 0.0) if is_fresh else 0.0
            rank1_mask = None
            try:
                ranked = getattr(host, "_cv_ball_last_ranked_masks", None) or []
                if len(ranked) > 0:
                    rank1_mask = ranked[0].get("mask", None)
            except Exception:
                rank1_mask = None
            host.ai_vision.maybe_update_test_hist(
                "CV Ball",
                src,
                host.ball_tracker.last_center if is_fresh else None,
                rr,
                thresholds=getattr(host, "_cv_ball_last_thresholds", None),
                mask_combined=rank1_mask,
                roi_rect=getattr(host, "_cv_ball_last_roi_rect", None),
                interval_s=float(getattr(host, "cv_ball_interval_s", 1.0) or 1.0),
            )
        except Exception:
            pass

        try:
            if getattr(host, "cv_hist_debug", None) is not None:
                host.cv_hist_debug.update_cv_debug_window(mask, is_fresh=is_fresh)
        except Exception:
            pass

        return mask, frame_bgr, ball_center, is_fresh
