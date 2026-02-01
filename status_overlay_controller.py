#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : status_overlay_controller.py
 Author : MT & GitHub Copilot

 Description:
     Status/FPS/HUD overlay controller extracted from frame_update_controller.py.
     Draws AI/CV/YOLO hints, telemetry, FPS, and HSV overlays on the main frame.

 v1.00  (2026-01-31 23:20)    : Initial status overlay controller extraction
     • Move overlay assembly into controller.
===============================================================================
"""

from __future__ import annotations

import os
import time

import cv2


class StatusOverlayController:
    def __init__(self, host):
        self._host = host

    def draw(self, frame_rgb, frame_bgr, *, w: int, h: int, font, scale: float, thickness: int, y_hint_start: int):
        host = self._host

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
        y_hint = y_hint_start
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
                hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
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
