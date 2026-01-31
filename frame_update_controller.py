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

class FrameUpdateController:
    def __init__(self, host):
        self._host = host

    def update_frame(self):
        """
        Grab and display a new frame (Dog video or Mac camera) and overlays.

        Two FPS counters:
          • RX: receive FPS (Dog frame rate).
          • UI: display FPS (Qt repaint rate).
        """
        host = self._host
        frame = None
        new_dog_frame = False

        # ---- Count display FPS (every timer tick) ----
        host.display_frame_count += 1
        now = time.time()
        if now - host.display_last_time >= 1.0:
            host.display_fps = (
                host.display_frame_count / (now - host.display_last_time)
            )
            host.display_frame_count = 0
            host.display_last_time = now

        # Dog video
        if host.use_dog_video and host.dog_client is not None:
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

        # Keep last BGR frame for picker clicks
        host.last_display_frame_bgr = frame.copy()  # ** for HSV picker, before any drawing or ball tracking **

        # ---- Optional ball tracking & mask window ----
        mask = None
        ball_center = None
        # IMPORTANT: autonomous tracking behavior (motion/head commands) must only run in "Ball" mode.
        # CV Ball / Yolo Vision / GPT Vision are test-only modes and must NOT move the dog.
        if host.ball_mode_enabled and frame is not None:
            #print(f"[DEBUG] Ball mode enabled: {host.ball_mode_enabled}")
            # If Yolo Vision is enabled, prefer YOLO detections for tracking.
            if host.yolo_vision_enabled and host.yolo_detector is not None:
                frame, ball_center = host.yolo_runtime.run_ball_mode(frame)
            else:
                # Run HSV mask ball detection + drawing on the BGR frame
                mask, frame = host.ball_tracker.process_with_mask(frame)
                #print(f"[DEBUG] After process_with_mask: last_center={host.ball_tracker.last_center} last_radius={host.ball_tracker.last_radius}")

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

        # ---- GPT Vision detection (test module) ----
        if host.ai_vision_enabled and frame is not None:
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
                        return
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

        #------- Update Mask window if open -------
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
    
        #----------------------

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
        cv2.putText(
            frame_rgb,
            host.ip,
            (10, 15),
            font,
            scale,
            (0, 255, 255),
            thickness,
        )
        cv2.putText(
            frame_rgb,
            f"Video {host.video_port}, Ctrl {host.control_port}",
            (10, 35),
            font,
            scale,
            (0, 255, 255),
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

        # Telemetry overlay (top-right)
        dog_online = (
            host.dog_client is not None
            and getattr(host.dog_client, "tcp_flag", False)
            and host.server_control_ok
        )

        # GPT Vision overlay hint (top-left, under IP/ports)
        ai_err = str(getattr(host, "_ai_last_error_msg", "") or "").strip()
        if host.ai_vision_enabled:
            if bool(getattr(host, "ai_one_shot_mode", False)):
                pending = bool(getattr(host, "_ai_one_shot_pending", False))
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
                ai_status = str(getattr(host, "_ai_status_msg", "") or "").strip()
                ai_until = float(getattr(host, "_ai_status_ts", 0.0) or 0.0)
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
                model_label = str(getattr(host.ai_detector, "model", "") or "").strip()
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
        if host.ai_vision_enabled:
            y_hint = 115
        if bool(getattr(host, "cv_ball_enabled", False)):
            try:
                cv_int = float(getattr(host, "cv_ball_interval_s", 1.0) or 1.0)
            except Exception:
                cv_int = 1.0
            cv_hz = (1.0 / cv_int) if cv_int > 0 else 0.0
            try:
                cv_n = int(getattr(host, "_cv_update_count", 0) or 0)
            except Exception:
                cv_n = 0
            try:
                cv_det_n = int(getattr(host, "_cv_detect_count", 0) or 0)
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
                cv_status = str(getattr(host, "_cv_last_status", "") or "").strip()
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
        if bool(getattr(host, "yolo_vision_enabled", False)):
            yolo_err2 = str(getattr(host, "_yolo_last_error_msg", "") or "").strip()
            try:
                y_int = float(getattr(host, "yolo_vision_interval_s", 1.0) or 1.0)
            except Exception:
                y_int = 1.0
            y_hz = (1.0 / y_int) if y_int > 0 else 0.0
            try:
                y_conf = float(getattr(getattr(host, "yolo_detector", None), "conf", 0.0) or 0.0)
            except Exception:
                y_conf = 0.0
            y_conf_text = f", Conf >= {y_conf:.2f}" if y_conf > 0 else ""
            try:
                y_n = int(getattr(host, "_yolo_update_count", 0) or 0)
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
                yolo_n2 = len(getattr(host, "_yolo_detections", []) or [])
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
                model_path = str(getattr(getattr(host, "yolo_detector", None), "model_path", "") or "")
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
        if bool(getattr(host, "yolo_training_enabled", False)):
            try:
                ds_label = str(getattr(host, "_yolo_training_dataset_label", "") or "")
            except Exception:
                ds_label = ""
            try:
                cur = int(getattr(host, "yolo_training_count", 0) or 0)
            except Exception:
                cur = 0
            tgt = int(getattr(host, "yolo_training_target", 256) or 256)
            msg = f"YOLO datasets creating...  #{cur}/{tgt} {ds_label}".strip()
            cv2.putText(frame_rgb, msg, (10, y_hint), font, scale, (0, 0, 0), thickness + 2)
            cv2.putText(frame_rgb, msg, (10, y_hint), font, scale, (180, 80, 255), thickness)
            y_hint += 20
            try:
                prompt = str(getattr(host, "_yolo_training_status_msg", "") or "").strip()
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
            if bool(getattr(host, "ball_mode_enabled", False)) and bool(getattr(host, "_ball_close_enough", False)):
                msg = "Ball is Close Enough"
                cv2.putText(frame_rgb, msg, (10, status_y), font, 0.7, (0, 0, 0), 4)
                cv2.putText(frame_rgb, msg, (10, status_y), font, 0.7, (0, 255, 0), 2)
            else:
                cmd_name = str(getattr(host, "_body_cmd_name", "") or "").strip()
                if cmd_name:
                    msg = f"Move: {cmd_name}"
                    cv2.putText(frame_rgb, msg, (10, status_y), font, 0.55, (0, 0, 0), 3)
                    cv2.putText(frame_rgb, msg, (10, status_y), font, 0.55, (255, 255, 0), 1)
                elif bool(getattr(host, "_ball_locked", False)):
                    source = str(getattr(host, "_ball_lock_source", "") or "")
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

        if dog_online and host.telemetry_valid:
            dist_text = f"{host.distance_cm:.1f}cm"
            volt_text = f"{host.battery_v:.2f}V"
        else:
            dist_text = "--.-cm"
            volt_text = "-.--V"

        rx_text = f"RX:{host.rx_fps:.1f}fps"
        ui_text = f"UI:{host.display_fps:.1f}fps"

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
        if host.ball_tracker.sample_point is not None and host.last_display_frame_bgr is not None:
            sx, sy = host.ball_tracker.sample_point
            hsv_img = cv2.cvtColor(host.last_display_frame_bgr, cv2.COLOR_BGR2HSV)  # <-- ALWAYS use raw color frame
            h_img, w_img = hsv_img.shape[:2]  # <-- ADD THIS LINE           
            sx = max(0, min(w_img - 1, sx))
            sy = max(0, min(h_img - 1, sy))            
            Hs, Ss, Vs = [int(v) for v in hsv_img[sy, sx]]      # Get HSV at sample point ==> error to be fixed, out of bounds for axis 0 with size 480
            host.ball_tracker.sample_hsv = (Hs, Ss, Vs)
            
            # ... draw HUD ...
            cv2.circle(frame_rgb, (sx, sy), 2, (100, 255, 0), -1)   # small (size=2) filled circle (-1) at mouse click point
            text1 = f"HSV({Hs},{Ss},{Vs})"
            text2 = f"({sx},{sy})"
            put_text_with_outline(frame_rgb, text1, (5, h - 28), (100, 255, 0))  # left-bottom corner
            put_text_with_outline(frame_rgb, text2, (5, h - 12), (100, 255, 0))

            # Update the mask window HUD/histogram if visible, using RAW color frame
            if host.last_display_frame_bgr is not None:
                _, mask2 = host.ball_tracker.compute_mask(host.last_display_frame_bgr)
                host.mask_picker.update_mask_window(host.last_display_frame_bgr, mask2)

        # Ball center HSV info (NEW PATCH)
        if host.ball_mode_enabled and host.ball_tracker.last_center is not None:
            #print(f"[DEBUG] Drawing ball center overlay: last_center={host.ball_tracker.last_center}")
            bx, by = host.ball_tracker.last_center
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
        if host.hover_xy_color is not None and host.hover_hsv_color is not None:
            cx, cy = host.hover_xy_color
            Hh, Sh, Vh = host.hover_hsv_color

            text1 = f"HSV({Hh},{Sh},{Vh})"
            text2 = f"({cx},{cy})"
            head_angle = getattr(host.head_tracker, "current_angle", None)
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
