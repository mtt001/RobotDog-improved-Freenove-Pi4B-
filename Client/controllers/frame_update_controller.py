#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : frame_update_controller.py
 Author : MT & GitHub Copilot

 Description:
     Frame update controller extracted from mtDogMain.py (CameraWindow).
     Handles per-frame capture, overlays, and detection/test-mode updates.

 v1.05  (2026-02-07 20:42)    : Add pluggable Dog video source path
     • Read Dog video from `host.video_source` when available (SFU RTSP backend).
     • Keep legacy `dog_client.image` path as fallback for compatibility.
 v1.04  (2026-02-02 20:31)    : Update IMU message pane per frame.
 v1.03  (2026-02-01)          : YOLO refine mask display
     • Feed dual-YOLO ball refinement mask into the existing mask window.
 v1.02  (2026-02-01)          : Bottom vision message pane
     • Update non-overlay vision status text each frame.
 v1.01  (2026-01-31 23:45)    : Group frame update steps
     • Split camera capture, detection, and overlay/render steps.
 v1.00  (2026-01-31 21:00)    : Initial frame update controller extraction
     • Extract update_frame logic into FrameUpdateController.
===============================================================================
"""

from __future__ import annotations

import time

import cv2
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap

from mtDogBallTrack import TRACKING_MODE_FULL, TRACKING_MODE_HEAD, TRACKING_MODE_BODY
from ui.status_overlay_controller import StatusOverlayController


class FrameUpdateController:
    def __init__(self, host):
        self._host = host
        self.status_overlay = StatusOverlayController(host)

    def update_frame(self):
        """
        Grab and display a new frame (Dog video or Mac camera) and overlays.

        Two FPS counters:
          • RX: receive FPS (Dog frame rate).
          • UI: display FPS (Qt repaint rate).
        """
        host = self._host

        frame = self._capture_frame()
        if frame is None:
            return

        # Keep last BGR frame for picker clicks
        host.last_display_frame_bgr = frame.copy()  # ** for HSV picker, before any drawing or ball tracking **

        frame, mask, abort_frame = self._run_detection_pipeline(frame)
        if abort_frame:
            return
        frame_rgb = self._apply_overlays(frame, mask)
        self._render_frame(frame_rgb)

    def _update_display_fps(self):
        host = self._host
        host.display_frame_count += 1
        now = time.time()
        if now - host.display_last_time >= 1.0:
            host.display_fps = host.display_frame_count / (now - host.display_last_time)
            host.display_frame_count = 0
            host.display_last_time = now

    def _capture_frame(self):
        host = self._host
        frame = None
        new_dog_frame = False

        self._update_display_fps()

        # Dog video (legacy socket or SFU RTSP backend)
        if host.use_dog_video and host.dog_client is not None:
            src = getattr(host, "video_source", None)
            if src is not None:
                vf = src.read()
                frame = vf.frame
                new_dog_frame = bool(vf.is_new and frame is not None)
                if new_dog_frame:
                    host.last_dog_frame = frame.copy()
                    host.dog_has_recent_frame = True
                    host.dog_last_frame_time = float(vf.timestamp or time.time())
                    host.video_stall = False
                if vf.error:
                    host.video_source_last_error = str(vf.error)
            else:
                with host.dog_client.image_lock:
                    if isinstance(host.dog_client.image, np.ndarray):
                        current = host.dog_client.image.copy()
                        if host.last_dog_frame is None:
                            new_dog_frame = True
                        else:
                            new_dog_frame = not np.array_equal(current, host.last_dog_frame)
                        host.last_dog_frame = current
                        frame = current
                        if new_dog_frame:
                            host.dog_has_recent_frame = True
                            host.dog_last_frame_time = time.time()
                            host.video_stall = False

            if frame is None:
                now2 = time.time()
                if host.last_dog_frame is not None:
                    frame = host.last_dog_frame
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
                    debug_text = f"IP:{host.ip}:{host.video_port} | Socket2:{getattr(host.dog_client, 'client_socket2', None) is not None}"
                    cv2.putText(
                        frame,
                        debug_text,
                        (40, 180),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        1,
                    )
                if host.dog_last_frame_time is not None:
                    if now2 - host.dog_last_frame_time > 2.0:
                        host.video_stall = True
                host.dog_has_recent_frame = False

                # If we're reusing the last frame for too long, RX FPS must decay to 0.
                if host.video_stall:
                    host.rx_fps = 0.0
                    host.rx_frame_count = 0
                    host.rx_last_time = now2

            # ---- Receive FPS: count only when a new Dog frame arrives ----
            if new_dog_frame:
                # Time since previous *new* frame – this is the true stream interval
                now_rx = time.time()
                if hasattr(host, "_last_rx_debug_time"):
                    dt = (now_rx - host._last_rx_debug_time) * 1000.0
                    # print(f"[RX-DEBUG] Dog new frame dt = {dt:.1f} ms")
                host._last_rx_debug_time = now_rx

                # FPS counter based on new frames
                host.rx_frame_count += 1
                if now_rx - host.rx_last_time >= 1.0:
                    host.rx_fps = host.rx_frame_count / (now_rx - host.rx_last_time)
                    host.rx_frame_count = 0
                    host.rx_last_time = now_rx
            else:
                # If we haven't seen a new frame recently, force RX FPS to 0.
                now_rx = time.time()
                if (now_rx - float(getattr(host, "rx_last_time", now_rx) or now_rx)) >= 1.0:
                    host.rx_fps = 0.0
                    host.rx_frame_count = 0
                    host.rx_last_time = now_rx

            # NEW: remember Dog frame height for head tracking
            if frame is not None:
                host.last_dog_frame_height = frame.shape[0]

        # Client-side source (Mac/Device/RTSP)
        else:
            host._retry_client_camera_if_needed()
            if host.cap is not None and host.cap.isOpened():
                ret, cam_frame = host.cap.read()
                if ret and isinstance(cam_frame, np.ndarray):
                    frame = cam_frame
                    host._client_cam_fail_count = 0
                else:
                    host._client_cam_fail_count += 1
                    host._log_client_cam("[SRC] Client source read failed.")
                    if host._client_cam_fail_count >= host._client_cam_fail_limit:
                        host._log_client_cam("[SRC] Client camera reopening after failures.")
                        try:
                            if host.cap is not None:
                                host.cap.release()
                        except Exception:
                            pass
                        host.cap = None
                        host._client_cam_opened_index = None
                        host._client_cam_next_try_ts = 0.0
                        host._client_cam_fail_count = 0
            else:
                host._log_client_cam("[SRC] Client source not opened or unavailable.")

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
            host.rx_fps = host.display_fps

        return frame

    def _run_detection_pipeline(self, frame):
        host = self._host
        mask = None
        ball_center = None
        abort_frame = False

        # IMPORTANT: autonomous tracking behavior (motion/head commands) must only run in "Ball" mode.
        # CV Ball / Yolo Vision / GPT Vision are test-only modes and must NOT move the dog.
        if host.ball_mode_enabled and frame is not None:
            # If Yolo Vision is enabled, prefer YOLO detections for tracking.
            if host.yolo_vision_enabled and host.yolo_detector is not None:
                frame, ball_center = host.yolo_runtime.run_ball_mode(frame)
            else:
                # Run HSV mask ball detection + drawing on the BGR frame
                mask, frame = host.ball_tracker.process_with_mask(frame)

                ball_center = host.ball_tracker.last_center
                try:
                    host._ball_locked = bool(host.ball_tracker.last_center is not None and host.ball_tracker.missed_frames == 0)
                    host._ball_lock_source = "Ball" if host._ball_locked else ""
                except Exception:
                    host._ball_locked = False
                    host._ball_lock_source = ""
        elif host.cv_ball_enabled and frame is not None:
            mask, frame, ball_center, _ = host.cv_ball.detect(frame)
        elif host.yolo_vision_enabled and frame is not None:
            frame, ball_center = host.yolo_runtime.run_test_mode(frame)
        else:
            host._ball_locked = False
            host._ball_lock_source = ""
            host._ball_close_enough = False

        # Common tracking behavior (AUTONOMOUS) — ONLY for "Ball" mode.
        if host.ball_mode_enabled and frame is not None:
            mode = host.ball_tracker.tracking_mode

            # If user switches to BODY mode, center head once.
            host._handle_tracking_mode_transition(mode)

            # Body tracking runs in FULL and BODY modes (independent of head tracking).
            if (
                mode in (TRACKING_MODE_FULL, TRACKING_MODE_BODY)
                and host.use_dog_video
                and host.dog_client is not None
                and getattr(host.dog_client, "tcp_flag", False)
            ):
                if ball_center is not None and host.ball_tracker.missed_frames == 0:
                    # Reset lost-search state when we reacquire a solid lock.
                    host._lost_search_state = "idle"
                    host._lost_search_sent_stop = False
                    host._lost_search_phase = "scan"
                    host._lost_search_phase_start_ts = 0.0
                    host._update_full_body_tracking(ball_center, frame.shape)
                else:
                    # Lost-ball behavior: keep searching (forward) and avoid obstacles (sonic).
                    if host.ball_tracker.missed_frames == 1:
                        if not host._lost_search_sent_stop:
                            host.send_stop_motion()
                            host._lost_search_sent_stop = True
                        host._lost_search_state = "idle"
                        host._lost_search_phase = "scan"
                        host._lost_search_phase_start_ts = 0.0
                        try:
                            host.ball_tracker.body_debug_lines = [
                                "SEARCH:hold (lost=1)",
                                f"dist:{float(getattr(host, 'distance_cm', 0.0) or 0.0):.1f}cm",
                            ]
                        except Exception:
                            pass
                    elif host.ball_tracker.missed_frames >= 2:
                        # Allow a new close-enough completion when we truly lose the ball.
                        # (Does not cancel an already-running OFF timer.)
                        host._close_enough_latched = False
                        host._update_lost_ball_search(frame.shape)

            # Head tracking (Dog video only)
            if (
                host.head_tracking_enabled
                and host.use_dog_video
                and host.dog_client is not None
                and getattr(host.dog_client, "tcp_flag", False)
                and host.last_dog_frame_height > 0
            ):
                # FULL mode: lock head at neutral for stable ranging; do not run head tracking.
                if bool(getattr(host, "full_lock_head_in_full", True)) and mode == TRACKING_MODE_FULL:
                    if not bool(getattr(host, "_full_head_sent_once", False)):
                        neutral = 90
                        try:
                            neutral = int(round(getattr(host.head_tracker.cfg, "neutral_deg", 90)))
                        except Exception:
                            pass
                        host.send_head_angle(neutral)
                        host._full_head_last_sent_ts = time.time()
                        host._full_head_sent_once = True
                else:
                    if mode == TRACKING_MODE_HEAD and ball_center is not None and host.ball_tracker.missed_frames == 0:
                        _, cy = ball_center
                        angle = host.head_tracker.update_from_ball(cy, host.last_dog_frame_height)
                        if angle is not None:
                            host.send_head_angle(int(round(angle)))
                    else:
                        if mode == TRACKING_MODE_HEAD and host.ball_tracker.missed_frames >= 2:
                            if host.ball_tracker.missed_frames == 2:
                                host.head_tracker.start_search()
                            angle = host.head_tracker.search_for_ball()
                            if angle is not None:
                                host.send_head_angle(int(round(angle)))

        if host.ai_vision_enabled and frame is not None:
            abort_frame = self._run_ai_vision_pipeline(frame)

        return frame, mask, abort_frame

    def _run_ai_vision_pipeline(self, frame) -> bool:
        host = self._host
        now_ai = time.time()
        # In one-shot mode, only call the API when a click has armed a request.
        if host.ai_one_shot_mode and not bool(getattr(host, "_ai_one_shot_pending", False)):
            # Still allow drawing of last detections, but do not call API.
            pass
        elif not bool(getattr(host, "_ai_request_sent", False)):
            try:
                print("[GPT] Sending frame to vision model...")
                src_frame = host.last_display_frame_bgr if host.last_display_frame_bgr is not None else frame
                try:
                    h_src, w_src = src_frame.shape[:2]
                    src_tag = "last_display_frame" if host.last_display_frame_bgr is not None else "current_frame"
                    print(f"[GPT] Frame source: {src_tag} size={w_src}x{h_src}")
                except Exception:
                    pass
                host._ai_detections = host.ai_detector.analyze(src_frame)
                print(
                    f"[GPT] Response: {len(host._ai_detections)} candidates"
                    + (f" (latency {host.ai_detector.last_latency_s:.2f}s)" if host.ai_detector.last_latency_s else "")
                )
                if host.ai_detector.last_error:
                    host.ai_vision.disable_due_to_error(host.ai_detector.last_error)
                    host._ai_last_ts = now_ai
                    host._ai_request_sent = True
                    return True
                # Inform user if AI returned no candidates
                if not host._ai_detections:
                    host.ai_vision.set_status("GPT Vision: no ball detected (0 candidates)")
                else:
                    # Clear stale status on success; filtering may set a new one below.
                    host._ai_status_msg = ""
                    host._ai_status_ts = 0.0
                raw_text = getattr(host.ai_detector, "last_raw_text", None)
                if raw_text:
                    print("[GPT] Raw response:\n" + str(raw_text))
                # Post-filter detections by score + HSV (to reduce false positives)
                # Disabled in one-shot trial mode: show whatever the model returned.
                if (not host.ai_one_shot_mode) and src_frame is not None and host._ai_detections:
                    try:
                        hsv_img = cv2.cvtColor(src_frame, cv2.COLOR_BGR2HSV)
                    except Exception:
                        hsv_img = None
                    h_ai, w_ai = src_frame.shape[:2]
                    filtered = []
                    rejected_hue = 0
                    rejected_sv = 0
                    rejected_score = 0
                    for idx, det in enumerate(host._ai_detections, start=1):
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
                        if score_f < float(getattr(host, "ai_score_min", 0.0)):
                            rejected_score += 1
                            continue
                        if (
                            host.ai_hsv_filter_enabled
                            and hsv_img is not None
                            and 0 <= x < w_ai
                            and 0 <= y < h_ai
                        ):
                            try:
                                H, S, V = [int(v) for v in hsv_img[y, x]]
                            except Exception:
                                H, S, V = 0, 0, 0
                            min_s = int(getattr(host, "ai_min_s", 0))
                            min_v = int(getattr(host, "ai_min_v", 0))
                            if S < min_s or V < min_v:
                                print(f"[GPT] Reject #{idx}@({x},{y}): HSV({H},{S},{V}) - S<{min_s} or V<{min_v}")
                                rejected_sv += 1
                                continue
                            ok_h = False
                            for lo, hi in getattr(host, "ai_hue_ranges", [(0, 179)]):
                                if int(lo) <= H <= int(hi):
                                    ok_h = True
                                    break
                            if not ok_h:
                                print(f"[GPT] Reject #{idx}@({x},{y}): HSV({H},{S},{V}) - Hue not in {host.ai_hue_ranges}")
                                rejected_hue += 1
                                continue
                        filtered.append(det)
                    if filtered:
                        print(f"[GPT] Filtered: {len(filtered)}/{len(host._ai_detections)} kept")
                        host._ai_status_msg = ""
                        host._ai_status_ts = 0.0
                    else:
                        print("[GPT] Filtered: 0 kept")
                        # Surface why on the Color window
                        if host.ai_hsv_filter_enabled and (rejected_hue or rejected_sv):
                            why = []
                            if rejected_hue:
                                why.append("Hue")
                            if rejected_sv:
                                why.append("S/V")
                            why_s = "+".join(why) if why else "HSV"
                            host.ai_vision.set_status(f"GPT Vision: rejected by {why_s} filter (try disabling GPT HSV filter)")
                        elif rejected_score:
                            host.ai_vision.set_status("GPT Vision: rejected by score filter")
                        else:
                            host.ai_vision.set_status("GPT Vision: 0 kept after filtering")
                    host._ai_detections = filtered
                # Auto-calibrate HSV ranges from the best AI detection
                if (not host.ai_one_shot_mode) and src_frame is not None and host._ai_detections:
                    try:
                        best_det = max(
                            host._ai_detections,
                            key=lambda d: float(d.get("score", 0.0)) if isinstance(d, dict) else float(getattr(d, "score", 0.0)),
                        )
                    except Exception:
                        best_det = host._ai_detections[0]
                    host.ai_vision.auto_calibrate_hsv_from_ai(src_frame, best_det)
                # Refine AI circles using HSV mask within ROI
                if (not host.ai_one_shot_mode) and src_frame is not None and host._ai_detections and host.ai_refine_enabled:
                    refined = []
                    for det in host._ai_detections:
                        refined.append(host.ai_vision.refine_ai_circle(src_frame, det))
                    host._ai_detections = refined
                # Log candidate info: diameter, center HSV, and (x,y)
                if src_frame is not None and host._ai_detections:
                    try:
                        hsv_img = cv2.cvtColor(src_frame, cv2.COLOR_BGR2HSV)
                    except Exception:
                        hsv_img = None
                    h_ai, w_ai = src_frame.shape[:2]
                    for idx, det in enumerate(host._ai_detections, start=1):
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
                if src_frame is not None and host._ai_detections:
                    try:
                        h_ai, w_ai = src_frame.shape[:2]
                    except Exception:
                        h_ai, w_ai = 0, 0
                    best_det = None
                    best_score = -1.0
                    for det in host._ai_detections:
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
                            model_label = str(getattr(host.ai_detector, "model", "") or "").strip()
                        except Exception:
                            model_label = ""
                        x_b, y_b, r_b = best_det
                        host.ai_vision.maybe_update_test_hist(
                            "GPT Vision",
                            src_frame,
                            (x_b, y_b),
                            float(r_b or 0.0),
                            model_label=model_label,
                            interval_s=0.0,
                        )
                if host.ai_detector.last_error:
                    host.ai_vision.disable_due_to_error(host.ai_detector.last_error)
            except Exception as e:
                host._ai_detections = []
                print(f"[GPT][WARN] GPT Vision failed in pipeline: {e}")
                host.ai_vision.disable_due_to_error(str(e) or "AI Vision pipeline exception")
            host._ai_last_ts = now_ai
            host._ai_request_sent = True
            if host.ai_one_shot_mode:
                # Disarm so we do not call API again until next click.
                host._ai_one_shot_pending = False

        if host._ai_detections:
            # Draw on main color frame
            host.overlay.draw_ai_detections(frame, host._ai_detections, ai_detector=host.ai_detector)

        # Beep every 3 seconds while AI Vision mode is ON (no LED flash)
        # Disabled for one-shot trial mode to avoid annoying repeats.
        if not host.ai_one_shot_mode:
            try:
                now_beep = time.time()
                last_beep = float(getattr(host, "_ai_beep_last_ts", 0.0) or 0.0)
                if (now_beep - last_beep) >= 3.0:
                    host._beep_pattern(beeps=1, on_s=0.08, off_s=0.00)
                    host._ai_beep_last_ts = now_beep
            except Exception:
                pass

        return False

    def _apply_overlays(self, frame, mask):
        host = self._host

        #------- Update Mask window if open -------
        try:
            if mask is None and bool(getattr(host, "yolo_vision_enabled", False)):
                mask = getattr(host, "_vision_refine_mask", None)
        except Exception:
            pass
        host.mask_picker.update_mask_window(host.last_display_frame_bgr, mask)

        # Apply any pending cheer banner updates from background timers.
        host._apply_mask_cheer_if_needed()

        # Start barking only after OFF has been reached (scheduled by completion timer).
        if bool(getattr(host, "_bark_pending_start", False)):
            host._bark_pending_start = False
            if host._bark_should_run():
                host._start_barking()

        # If barking is active but the conditions are no longer true, stop it.
        if bool(getattr(host, "_bark_active", False)) and not host._bark_should_run():
            host._stop_barking()
            host._set_mask_cheer("", visible=False)

        # Always-on CV histogram panels (picker/frame + top-ranked contours)
        try:
            src_hist = host.last_display_frame_bgr if host.last_display_frame_bgr is not None else frame
            host._maybe_update_cv_hist(src_hist)
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
        tracking_mode = getattr(host.ball_tracker, "tracking_mode", None) if host.ball_mode_enabled else None
        if host.ball_mode_enabled and w > 0 and h > 0:
            cx = w / 2.0
            cy = h / 2.0

            # X deadzone for body tracking (in FULL/BODY modes)
            if tracking_mode in (TRACKING_MODE_FULL, TRACKING_MODE_BODY):
                try:
                    deadzone_ratio = float(getattr(host.ball_tracker, "body_deadzone_ratio", 0.18))
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
                and hasattr(host, "head_tracker")
                and hasattr(host.head_tracker, "cfg")
            ):
                try:
                    deadband = float(getattr(host.head_tracker.cfg, "deadband", 0.02))
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
        try:
            ip_ok = bool(getattr(host, "server_ip_ok", False))
            ctrl_ok = bool(getattr(host, "server_control_ok", False))
            vid_ok = bool(getattr(host, "server_video_ok", False))
            stalled = bool(getattr(host, "video_stall", False))
            tcp_ok = bool(host.dog_client is not None and getattr(host.dog_client, "tcp_flag", False))
        except Exception:
            ip_ok = True
            ctrl_ok = True
            vid_ok = True
            stalled = False
            tcp_ok = True

        # NOTE: frame_rgb is RGB (not BGR)
        ip_color = (0, 255, 255) if ip_ok else (255, 0, 0)            # cyan vs red
        ports_ok = bool(ctrl_ok and vid_ok and tcp_ok and not stalled)
        ports_color = (0, 255, 255) if ports_ok else (255, 0, 0)       # cyan vs red

        cv2.putText(
            frame_rgb,
            host.ip,
            (10, 15),
            font,
            scale,
            ip_color,
            thickness,
        )
        cv2.putText(
            frame_rgb,
            f"Video {host.video_port}, Ctrl {host.control_port}",
            (10, 35),
            font,
            scale,
            ports_color,
            thickness,
        )

        # State text (centered near top)
        left_disp = int(getattr(host, "left_state_seconds", 0) or 0)
        right_disp = int(getattr(host, "right_state_seconds", 0) or 0)
        state_label = str(getattr(host, "state_name", ""))

        # Smooth display: if we know when WORKING_TIME was last received,
        # interpolate counters using inferred tick directions.
        anchor_ts = getattr(host, "_working_time_anchor_ts", None)
        anchor_left = getattr(host, "_working_time_anchor_left", None)
        anchor_right = getattr(host, "_working_time_anchor_right", None)
        if (
            isinstance(anchor_ts, (int, float))
            and anchor_ts > 0
            and isinstance(anchor_left, int)
            and isinstance(anchor_right, int)
        ):
            dt = time.time() - float(anchor_ts)
            if 0.0 <= dt <= 20.0:
                dir_left = int(getattr(host, "_working_time_left_dir", 0) or 0)
                dir_right = int(getattr(host, "_working_time_right_dir", 0) or 0)
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

        # Telemetry/status/FPS overlays
        self.status_overlay.draw(
            frame_rgb,
            frame,
            w=w,
            h=h,
            font=font,
            scale=scale,
            thickness=thickness,
            y_hint_start=55,
        )

        return frame_rgb

    def _render_frame(self, frame_rgb):
        host = self._host
        h, w, ch = frame_rgb.shape

        # Convert to QPixmap
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        pixmap = pixmap.scaled(
            host.video_label.width(),
            host.video_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        host.video_label.setPixmap(pixmap)

        # Window title with resolution reflects Dog vs Mac mode
        src_name = "Dog Pi Camera" if host.use_dog_video else "Mac Camera"
        host.setWindowTitle(f"mtDogMain v2.40 - {src_name} {w}x{h}")

        host.update_status_ui()

        # Bottom vision message pane (non-overlay status/perf)
        try:
            label = getattr(host, "vision_msg_label", None)
            if label is not None:
                txt = str(getattr(host, "_vision_status_text", "") or "")
                label.setText(txt)
        except Exception:
            pass
        try:
            imu_label = getattr(host, "imu_msg_label", None)
            if imu_label is not None:
                imu_txt = str(getattr(host, "_imu_status_text", "") or "")
                imu_label.setText(imu_txt)
        except Exception:
            pass
