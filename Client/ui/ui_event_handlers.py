#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : ui_event_handlers.py
 Author : MT & GitHub Copilot

 Description:
     UI event handler controller extracted from mtDogMain.py (CameraWindow).
     Handles UI button events, status updates, and cleanup/quit logic.

 v1.02  (2026-02-07 20:42)    : Close pluggable Dog video source on app exit
     • Ensure external video backend resources are released in close flow.
 v1.00  (2026-01-31 20:50)    : Initial UI event handler controller extraction
     • Extract UI handlers + status updates from CameraWindow.
 v1.01  (2026-02-01)          : Remove CV/GPT Vision handlers
     • Remove CV Ball + GPT Vision handlers and references (YOLO-only test mode).
===============================================================================
"""

from __future__ import annotations

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from ui.yolo_debug_windows import YoloVisionDebugWindow


class UIEventHandlersController:
    def __init__(self, host):
        self._host = host

    def update_status_ui(self):
        return self._host.status_ui.update_status_ui()

    def try_reconnect(self):
        return self._host.server_reconnect.try_reconnect()

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
        host = self._host
        host.ball_mode_enabled = not host.ball_mode_enabled
        host.head_tracking_enabled = bool(host.ball_mode_enabled)
        state = "ON" if host.ball_mode_enabled else "OFF"
        print(f"[BALL] Ball tracking {state}.")

        if host.ball_mode_enabled:
            # Reset head controller to neutral on entry (optional)
            host.head_tracker.current_angle = host.head_tracker.cfg.neutral_deg

            # Load config (if exists)
            host.ball_tracker.load_default_config()

            host.mask_picker.show_mask_window()

            # Button style → green
            host.btn_Ball.setStyleSheet(
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

            # While Tracking is ON, ensure YOLO Vision is enabled.
            if not bool(getattr(host, "yolo_vision_enabled", False)):
                self.handle_yolo_vision_button()
        else:
            # Hide window and save config
            host.mask_picker.hide_mask_window()
            host.ball_tracker.save_default_config()

            # Stop any post-completion barking when ball mode is turned off.
            host._stop_barking()
            host._set_mask_cheer("", visible=False)
            host._bark_pending_start = False

            # Cancel any pending OFF timer (avoid starting barking after Ball mode is off).
            prev = getattr(host, "_close_enough_off_timer", None)
            try:
                if prev is not None and prev.is_alive():
                    prev.cancel()
            except Exception:
                pass

            # Optionally send head back to neutral when leaving Ball mode
            if (
                host.dog_client is not None
                and getattr(host.dog_client, "tcp_flag", False)
            ):
                host.head_tracker.current_angle = host.head_tracker.cfg.neutral_deg
                host.send_head_angle(int(round(host.head_tracker.current_angle)))

            host.head_tracking_enabled = False  # NEW

            # Button style → blue
            host.btn_Ball.setStyleSheet(
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

    def handle_yolo_vision_button(self):
        """Toggle YOLO Vision ball tracking (local inference)."""
        host = self._host
        # Clear stale overlays/results from other test modes
        host._clear_object_detection_state(clear_hist=True)
        # Ball sources are mutually exclusive (HSV / CV / YOLO)
        if host.ball_mode_enabled:
            host.ball_mode_enabled = False
            try:
                if host.ball_mask_window is not None:
                    host.ball_mask_window.hide()
            except Exception:
                pass
            try:
                host.btn_Ball.setStyleSheet(
                    """
                    QPushButton { background-color:#0066cc; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#0066cc; }
                    """
                )
            except Exception:
                pass

        host.yolo_vision_enabled = not bool(getattr(host, "yolo_vision_enabled", False))
        # Test mode: do NOT move dog automatically (no head/body tracking)
        # But keep head tracking if Ball mode is active.
        host.head_tracking_enabled = bool(getattr(host, "ball_mode_enabled", False))
        state = "ON" if host.yolo_vision_enabled else "OFF"
        print(f"[YOLO] Yolo Vision {state}.")

        if host.yolo_vision_enabled:
            host._yolo_update_count = 0
            host._yolo_detections = []
            host._yolo_last_error_msg = ""
            host._yolo_vision_last_ts = 0.0
            host._yolo_probe_last_ts = 0.0
            host._yolo_probe_boxes = []
            host._yolo_probe_error_msg = ""
            host._yolo_probe_latency_s = 0.0
            host._yolo_hi_conf = None
            host._yolo_lo_conf = None
            host._yolo_hi_snap = None
            host._yolo_lo_snap = None
            host._yolo_hi_center = None
            host._yolo_lo_center = None
            try:
                host._apply_yolo_model_choice()
            except Exception:
                pass
            # Load config to reuse smoothing / tracking mode knobs
            try:
                host.ball_tracker.load_default_config()
            except Exception:
                pass

            try:
                host.btn_YoloVision.setStyleSheet(
                    """
                    QPushButton { background-color:#00c853; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#00c853; }
                    """
                )
            except Exception:
                pass

            # Show YOLO debug window near main window
            try:
                if host.yolo_debug_window is None:
                    host.yolo_debug_window = YoloVisionDebugWindow()
                
                try:
                    conf_init = float(getattr(host.yolo_detector, "conf", 0.02) or 0.02)
                except Exception:
                    conf_init = 0.02
                try:
                    imgsz_init = int(getattr(host.yolo_detector, "imgsz", 640) or 640)
                except Exception:
                    imgsz_init = 640

                # BINDING BLOCK
                try:
                    host.yolo_debug_window.bind_yolo_controls(
                        conf_init,
                        imgsz_init,
                        host._on_yolo_conf_changed,
                        host._on_yolo_imgsz_changed,
                    )
                except Exception:
                    pass

                try:
                    host.yolo_debug_window.bind_model_selector(host.yolo_model_choice, host._on_yolo_model_changed)
                except Exception:
                    pass
                
                try:
                    host.yolo_debug_window.bind_compare_toggle(host._on_yolo_compare_toggle)
                    host.yolo_debug_window.set_compare_checked(bool(getattr(host, "yolo_compare_enabled", False)))
                except Exception as e:
                    print(f"[YOLO] Error binding Compare toggle: {e}")
                
                try:
                    host.yolo_debug_window.bind_training_toggle(host._on_yolo_training_toggle)
                    host.yolo_debug_window.set_training_checked(bool(getattr(host, "yolo_training_enabled", False)))
                except Exception:
                    pass

                try:
                    host.yolo_debug_window.bind_labeling_classes(
                        list(host._yolo_labeling_class_names or []),
                        host._on_yolo_labeling_class_changed,
                    )
                    host.yolo_debug_window.set_labeling_class_index(int(host._yolo_labeling_class_id or 0))
                except Exception:
                    pass
                    
                if host.yolo_detector is None:
                    host.yolo_debug_window.yolo_conf_spin.setEnabled(False)
                    host.yolo_debug_window.yolo_imgsz_spin.setEnabled(False)
                    host.yolo_debug_window.yolo_model_combo.setEnabled(False)
                    # Keep Compare clickable for debug even if detector is missing
                    host.yolo_debug_window.compare_btn.setEnabled(True)
                else:
                    host.yolo_debug_window.yolo_conf_spin.setEnabled(True)
                    host.yolo_debug_window.yolo_imgsz_spin.setEnabled(True)
                    host.yolo_debug_window.yolo_model_combo.setEnabled(True)
                    host.yolo_debug_window.compare_btn.setEnabled(True)

                # Bind Manual Labeling
                try:
                    host.yolo_debug_window.bind_labeling_toggle(host._on_yolo_labeling_toggle)
                    host.yolo_debug_window.view.on_mouse_event = None
                    host.yolo_debug_window.on_key_event = None
                except Exception:
                    pass

                host.yolo_debug_window.move(host.x() + host.width() + 20, host.y() + 40)
                host.yolo_debug_window.show()
                host.yolo_debug_window.raise_()
                try:
                    if host.yolo_labeling_enabled:
                        host._on_yolo_labeling_toggle(True)
                except Exception:
                    pass
            except Exception as e:
                print(f"[YOLO] Critical error initializing debug window: {e}")
                pass
        else:
            host._stop_yolo_training(reason="")
            host.yolo_compare_enabled = False
            host.yolo_labeling_enabled = False
            try:
                host.btn_YoloVision.setStyleSheet(
                    """
                    QPushButton { background-color:#2e7d32; color:#ffffff; border:none; border-radius:16px; padding:4px 10px; font-size:14px; }
                    QPushButton:hover { background-color:#ffffff; color:#2e7d32; }
                    """
                )
            except Exception:
                pass
            try:
                if host.yolo_compare_window is not None:
                    host.yolo_compare_window.hide()
            except Exception:
                pass
            # Close detected-object histogram when Yolo Vision turns OFF
            try:
                if host.ai_hist_window is not None:
                    host.ai_hist_window.hide()
            except Exception:
                pass
            if host.dog_client is not None and getattr(host.dog_client, "tcp_flag", False):
                try:
                    host.head_tracker.current_angle = host.head_tracker.cfg.neutral_deg
                    host.send_head_angle(int(round(host.head_tracker.current_angle)))
                except Exception:
                    pass
            # Hide YOLO debug window
            try:
                if host.yolo_debug_window is not None:
                    host.yolo_debug_window.hide()
            except Exception:
                pass
            try:
                if host.yolo_label_window is not None:
                    host.yolo_label_window.hide()
            except Exception:
                pass
            host._yolo_probe_boxes = []
            host._yolo_probe_error_msg = ""
            host._yolo_probe_latency_s = 0.0

    def handle_quit(self):
        """Q key / button: exit."""
        host = self._host
        print("[SYS] Quit requested.")
        # Save calibration one more time
        host.ball_tracker.save_default_config()
        # Close auxiliary windows if open
        for win in [
            getattr(host, "ball_mask_window", None),
            getattr(host, "cv_debug_window", None),
            getattr(host, "cv_hist_window", None),
            getattr(host, "ai_hist_window", None),
            getattr(host, "yolo_debug_window", None),
            getattr(host, "yolo_label_window", None),
            getattr(host, "yolo_compare_window", None),
            getattr(host, "yolo_train_hist_window", None),
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
            host.close()
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

    def clear_object_detection_state(self, *, clear_hist: bool = True):
        host = self._host
        # Clear all test-mode detections/overlays so switching modes doesn't leave stale info.
        host._ai_detections = []
        host._ai_request_sent = False
        host._ai_one_shot_pending = False
        host._ai_status_msg = ""
        host._ai_status_ts = 0.0
        host._yolo_detections = []
        host._yolo_last_error_msg = ""
        host._cv_ball_last_mask = None
        host._cv_ball_last_hist_mask = None
        host._cv_ball_last_ranked_masks = []
        host._cv_detect_count = 0
        host._test_hist_last_ts = 0.0
        host._test_hist_last_mode = ""
        if clear_hist and host.ai_hist_window is not None:
            try:
                host.ai_hist_window.clear_view(mode_label="Object Detection Test")
            except Exception:
                pass

    def close_event(self, event):
        """Qt close: stop threads/timers and release resources."""
        host = self._host
        print("[CLOSE] Cleaning up...")

        # Save calibration one last time
        host.ball_tracker.save_default_config()

        host.stop_cmd_thread = True

        host.server_reconnect.stop_server_check_thread()

        if getattr(host, "telemetry_timer", None) is not None:
            host.telemetry_timer.stop()
        if getattr(host, "timer", None) is not None:
            host.timer.stop()

        if host.dog_client is not None:
            try:
                if hasattr(host.dog_client, "turn_off_client"):
                    host.dog_client.turn_off_client()
            except Exception as e:
                print(f"[CLOSE] Error closing dog client: {e}")
        try:
            host._close_dog_video_source()
        except Exception:
            pass

        if host.cap is not None:
            try:
                host.cap.release()
            except Exception as e:
                print(f"[CLOSE] Error releasing camera: {e}")

        event.accept()
