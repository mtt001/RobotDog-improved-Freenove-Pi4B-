#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : yolo_runtime.py
 Author : MT & GitHub Copilot

 Description:
     YOLO runtime controller extracted from mtDogMain.py (CameraWindow).
     Maintains YOLO detector setup, compare/probe logic, runtime updates,
     training capture, and debug/compare view rendering.

 v1.00  (2026-01-31 20:30)    : Initial YOLO runtime controller extraction
     • Extract YOLO runtime pipeline from CameraWindow into controller.
===============================================================================
"""

from __future__ import annotations

import json
import os
import time
from collections import deque

import cv2
import numpy as np

try:
    from vision.legacy.mtBallDetectYOLO import YOLOBallDetector
except Exception:
    YOLOBallDetector = None  # type: ignore


class YoloRuntimeController:
    def __init__(self, host, *, compare_window_factory=None, train_hist_window_factory=None):
        self._host = host
        self._compare_window_factory = compare_window_factory
        self._train_hist_window_factory = train_hist_window_factory

        # YOLO detector (local inference) used by "Yolo Vision" mode.
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        host.yolo_model_best_path = os.path.join(project_root, "runs", "detect", "train5", "weights", "best.pt")
        host.yolo_model_orig_path = os.path.join(project_root, "yolov8n.pt")
        host.yolo_model_choice = "best" if os.path.isfile(host.yolo_model_best_path) else "orig"
        host.yolo_detector_best = (
            YOLOBallDetector(model_path=host.yolo_model_best_path, ball_class_id=0) if YOLOBallDetector is not None else None
        )
        host.yolo_detector_orig = (
            YOLOBallDetector(model_path=host.yolo_model_orig_path, ball_class_id=32) if YOLOBallDetector is not None else None
        )
        host.yolo_detector = host.yolo_detector_best if host.yolo_model_choice == "best" else host.yolo_detector_orig
        host._yolo_detections = []
        host._yolo_last_error_msg = ""
        host._yolo_last_latency_s = 0.0
        host._yolo_last_hit_ts = 0.0
        host._yolo_last_hit_conf = 0.0
        host._yolo_last_hit_box = None  # (x1, y1, x2, y2, cx, cy, label, cls)
        host._yolo_last_hit_count = 0
        host._yolo_last_frame_shape = None  # (h, w)
        host._yolo_probe_last_ts = 0.0
        host._yolo_probe_interval_s = 2.0
        host._yolo_probe_conf = 0.001
        host._yolo_probe_boxes = []
        host._yolo_probe_error_msg = ""
        host._yolo_probe_latency_s = 0.0
        host._yolo_hi_conf = None
        host._yolo_lo_conf = None
        host._yolo_hi_snap = None
        host._yolo_lo_snap = None
        host._yolo_hi_center = None
        host._yolo_lo_center = None

        # YOLO compare (best vs original)
        host.yolo_compare_enabled = False
        host.yolo_compare_window = None
        host._yolo_compare_detections_best = []
        host._yolo_compare_detections_orig = []

        # YOLO Vision (ball source) - separate from GPT snapshot compare
        host.yolo_vision_enabled = False
        host.yolo_vision_interval_s = 1.0
        host._yolo_vision_last_ts = 0.0
        host._yolo_update_count = 0

        # YOLO Ball Training (dataset capture)
        host.yolo_training_enabled = False
        host.yolo_training_target = 1000
        host.yolo_training_count = 0
        host._yolo_training_dataset_label = ""
        host._yolo_training_dir = None
        host._yolo_training_next_index = 1
        host._yolo_training_conf_values = []
        host._yolo_training_easy = 0
        host._yolo_training_med = 0
        host._yolo_training_hard = 0
        host._yolo_training_recent_boxes = deque(maxlen=3)
        host._yolo_training_last_prompt_ts = 0.0
        host._yolo_training_prompt_idx = 0
        host._yolo_training_interval_default = float(host.yolo_vision_interval_s or 1.0)
        host._yolo_training_status_msg = ""
        host._yolo_training_prompt_msgs = [
            "Change ball position (edges/corners)",
            "Vary distance: close / mid / far",
            "Change lighting: bright / dim / backlight",
            "Try reflective floor / cluttered background",
            "Add partial occlusion / motion blur",
        ]
        host.yolo_train_hist_window = None

    def update_debug_view(self, frame_bgr):
        host = self._host
        try:
            if host.yolo_debug_window is None or not host.yolo_debug_window.isVisible():
                return
        except Exception:
            return

        vis = None
        if frame_bgr is not None:
             # Manual Labeling Capture
            if host.yolo_labeling_enabled:
                 try:
                     host._yolo_labeling_last_frame = frame_bgr.copy()
                 except Exception:
                     pass

            try:
                vis = frame_bgr.copy()
                if getattr(vis, "size", 0) > 0 and host._yolo_detections:
                    host.overlay.draw_yolo_detections(vis, host._yolo_detections)
                elif getattr(vis, "size", 0) > 0 and host._yolo_probe_boxes:
                    host.overlay.draw_yolo_probe_boxes(vis, host._yolo_probe_boxes)
                
                if host.yolo_labeling_enabled:
                     host.overlay.draw_labeling_overlay(
                         vis,
                         host._yolo_labeling_msg,
                         host._yolo_labeling_save_msg_ts,
                         host._yolo_labeling_p1,
                         host._yolo_labeling_p2,
                     )

            except Exception:
                vis = frame_bgr

        full_hist = None
        hi_img = hi_hist = None
        lo_img = lo_hist = None
        try:
            if frame_bgr is not None and host.yolo_debug_window is not None:
                full_hist = host.yolo_debug_window._render_hsv_hist(frame_bgr, label_text="frame")
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
            if frame_bgr is not None and host._yolo_detections and host.yolo_debug_window is not None:
                hi_box = host._yolo_detections[0]
                lo_box = host._yolo_detections[-1]
                hi_img = _crop_box(frame_bgr, hi_box)
                lo_img = _crop_box(frame_bgr, lo_box)
                try:
                    hi_conf_now = float(getattr(hi_box, "conf", 0.0) or 0.0)
                    lo_conf_now = float(getattr(lo_box, "conf", 0.0) or 0.0)
                except Exception:
                    hi_conf_now = 0.0
                    lo_conf_now = 0.0
                if hi_img is not None and (host._yolo_hi_conf is None or hi_conf_now >= float(host._yolo_hi_conf or 0.0)):
                    host._yolo_hi_conf = hi_conf_now
                    host._yolo_hi_snap = hi_img
                    try:
                        host._yolo_hi_center = (
                            int(round(float(getattr(hi_box, "cx", 0.0)))),
                            int(round(float(getattr(hi_box, "cy", 0.0)))),
                        )
                    except Exception:
                        host._yolo_hi_center = None
                if lo_img is not None and (host._yolo_lo_conf is None or lo_conf_now <= float(host._yolo_lo_conf or 0.0)):
                    host._yolo_lo_conf = lo_conf_now
                    host._yolo_lo_snap = lo_img
                    try:
                        host._yolo_lo_center = (
                            int(round(float(getattr(lo_box, "cx", 0.0)))),
                            int(round(float(getattr(lo_box, "cy", 0.0)))),
                        )
                    except Exception:
                        host._yolo_lo_center = None
        except Exception:
            pass

        try:
            if host.yolo_debug_window is not None:
                hi_img = host._yolo_hi_snap
                lo_img = host._yolo_lo_snap
                if hi_img is not None:
                    hi_hist = host.yolo_debug_window._render_hsv_hist(hi_img, label_text="hi")
                else:
                    hi_hist = None
                if lo_img is not None:
                    lo_hist = host.yolo_debug_window._render_hsv_hist(lo_img, label_text="lo")
                else:
                    lo_hist = None
        except Exception:
            pass

        try:
            y_int = float(getattr(host, "yolo_vision_interval_s", 1.0) or 1.0)
        except Exception:
            y_int = 1.0
        y_hz = (1.0 / y_int) if y_int > 0 else 0.0
        try:
            y_n = int(getattr(host, "_yolo_update_count", 0) or 0)
        except Exception:
            y_n = 0
        det_n = len(getattr(host, "_yolo_detections", []) or [])
        err = str(getattr(host, "_yolo_last_error_msg", "") or "").strip()

        lat_s = float(getattr(host, "_yolo_last_latency_s", 0.0) or 0.0)
        lat_ms = lat_s * 1000.0 if lat_s > 0 else 0.0

        conf_th = None
        imgsz = None
        ball_cls = None
        model_path = ""
        try:
            if host.yolo_detector is not None:
                conf_th = getattr(host.yolo_detector, "conf", None)
                imgsz = getattr(host.yolo_detector, "imgsz", None)
            ball_cls = getattr(host.yolo_detector, "ball_class_id", None)
            model_path = str(getattr(host.yolo_detector, "model_path", "") or "")
        except Exception:
            pass

        h_w = host._yolo_last_frame_shape
        if vis is not None:
            try:
                h_w = (int(vis.shape[0]), int(vis.shape[1]))
            except Exception:
                pass

        last_hit_ts = float(getattr(host, "_yolo_last_hit_ts", 0.0) or 0.0)
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
        if host._yolo_detections:
            try:
                top_conf = float(getattr(host._yolo_detections[0], "conf", 0.0) or 0.0)
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
            ds_dir = str(getattr(host, "_yolo_training_dir", "") or "").strip()
            ds_label = str(getattr(host, "_yolo_training_dataset_label", "") or "").strip()
        except Exception:
            ds_dir = ""
            ds_label = ""
        if ds_dir:
            info_lines.append(f"dataset {ds_label} | {ds_dir}" if ds_label else f"dataset {ds_dir}")
        try:
            info_lines.append(
                f"ui model={str(getattr(host, 'yolo_model_choice', 'best'))} | COMPARE MODE: {'ON' if host.yolo_compare_enabled else 'OFF'}"
            )
        except Exception:
            pass
        if bool(getattr(host, "yolo_compare_enabled", False)):
            info_lines.append(">> Comparing: best.pt (Left) vs yolov8n.pt (Right)")

        top_box = None
        if det_n > 0 and host._yolo_detections:
            top_box = host._yolo_detections[0]

        if top_box is not None and det_n > 0:
            try:
                if isinstance(top_box, tuple):
                    x1, y1, x2, y2, cx, cy, label, cls_id = top_box
                    conf = float(getattr(host, "_yolo_last_hit_conf", 0.0) or 0.0)
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
        probe_n = len(getattr(host, "_yolo_probe_boxes", []) or [])
        probe_err = str(getattr(host, "_yolo_probe_error_msg", "") or "").strip()
        probe_conf = float(getattr(host, "_yolo_probe_conf", 0.001) or 0.001)
        probe_lat_ms = float(getattr(host, "_yolo_probe_latency_s", 0.0) or 0.0) * 1000.0
        if probe_n > 0:
            info_lines.append(
                f"probe any-class det {probe_n} conf>={probe_conf} | lat {probe_lat_ms:.1f}ms"
            )
            try:
                p0 = (getattr(host, "_yolo_probe_boxes", []) or [])[0]
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
            host.yolo_debug_window.update_view(
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
            if host.yolo_labeling_enabled and host.yolo_label_window is not None and host.yolo_label_window.isVisible():
                label_vis = None
                if vis is not None:
                    try:
                        label_vis = vis.copy()
                    except Exception:
                        label_vis = None
                if label_vis is None:
                    try:
                        if host._yolo_labeling_last_frame is not None:
                            label_vis = host._yolo_labeling_last_frame.copy()
                            host.overlay.draw_labeling_overlay(
                                label_vis,
                                host._yolo_labeling_msg,
                                host._yolo_labeling_save_msg_ts,
                                host._yolo_labeling_p1,
                                host._yolo_labeling_p2,
                            )
                    except Exception:
                        label_vis = None
                try:
                    ds_dir = str(getattr(host, "_yolo_training_dir", "") or "").strip()
                    ds_label = str(getattr(host, "_yolo_training_dataset_label", "") or "").strip()
                except Exception:
                    ds_dir = ""
                    ds_label = ""
                msg = str(getattr(host, "_yolo_labeling_msg", "") or "").strip()
                class_label = host._yolo_labeling_class_label()
                info = f"{msg}  |  Class {class_label}" if msg else f"Class {class_label}"
                if ds_dir:
                    info = f"{info}  |  {ds_label}  {ds_dir}" if ds_label else f"{info}  |  {ds_dir}"
                host.yolo_label_window.update_view(label_vis, info, host._yolo_label_help_text())
        except Exception:
            pass

        try:
            if host.yolo_debug_window is not None and (host._yolo_hi_snap is not None or host._yolo_lo_snap is not None):
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

                host.yolo_debug_window.hi_title.setText(
                    _fmt_box("Highest Conf", host._yolo_hi_conf, host._yolo_hi_center, host._yolo_hi_snap)
                )
                host.yolo_debug_window.lo_title.setText(
                    _fmt_box("Lowest Conf", host._yolo_lo_conf, host._yolo_lo_center, host._yolo_lo_snap)
                )
            elif host.yolo_debug_window is not None:
                host.yolo_debug_window.hi_title.setText("Highest Conf --%, (--,--), (--,--,--)")
                host.yolo_debug_window.lo_title.setText("Lowest Conf --%, (--,--), (--,--,--)")
        except Exception:
            pass

    def update_compare_view(self, frame_bgr):
        host = self._host
        try:
            if not bool(getattr(host, "yolo_compare_enabled", False)):
                return
            if host.yolo_compare_window is None or not host.yolo_compare_window.isVisible():
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
            if host._yolo_compare_detections_best:
                host.overlay.draw_yolo_detections(left, host._yolo_compare_detections_best)
        except Exception:
            pass
        try:
            if host._yolo_compare_detections_orig:
                host.overlay.draw_yolo_detections(right, host._yolo_compare_detections_orig)
        except Exception:
            pass
        try:
            host.yolo_compare_window.update_views(left, right)
        except Exception:
            pass

    def on_yolo_conf_changed(self, val):
        host = self._host
        try:
            conf_v = float(val)
        except Exception:
            return
        for det in (host.yolo_detector, host.yolo_detector_best, host.yolo_detector_orig):
            if det is not None:
                try:
                    det.conf = conf_v
                except Exception:
                    pass
        print(f"[YOLO] conf -> {conf_v:.3f}")

    def on_yolo_imgsz_changed(self, val):
        host = self._host
        try:
            imgsz_v = int(val)
        except Exception:
            return
        for det in (host.yolo_detector, host.yolo_detector_best, host.yolo_detector_orig):
            if det is not None:
                try:
                    det.imgsz = imgsz_v
                except Exception:
                    pass
        print(f"[YOLO] imgsz -> {imgsz_v}")

    def apply_yolo_model_choice(self):
        host = self._host
        choice = str(getattr(host, "yolo_model_choice", "best") or "best").lower()
        if choice == "orig":
            host.yolo_detector = host.yolo_detector_orig
        else:
            host.yolo_detector = host.yolo_detector_best
        if host.yolo_debug_window is not None:
            try:
                host.yolo_debug_window.bind_model_selector(choice, host._on_yolo_model_changed)
            except Exception:
                pass
        if host.yolo_compare_window is not None:
            try:
                left_title = f"BEST ({os.path.basename(host.yolo_model_best_path)}, cls 0)"
                right_title = f"ORIGINAL ({os.path.basename(host.yolo_model_orig_path)}, cls 32)"
                host.yolo_compare_window.set_titles(left_title, right_title)
            except Exception:
                pass
        print(f"[YOLO] model -> {choice}")

    def on_yolo_model_changed(self, idx=None):
        host = self._host
        try:
            choice = None
            if host.yolo_debug_window is not None:
                try:
                    choice = host.yolo_debug_window.yolo_model_combo.currentData()
                except Exception:
                    choice = None
                if choice is None:
                    try:
                        idx = host.yolo_debug_window.yolo_model_combo.currentIndex()
                    except Exception:
                        idx = idx
            if isinstance(idx, str):
                if "yolo" in idx.lower():
                    choice = "orig"
                elif "best" in idx.lower():
                    choice = "best"
            if choice is None:
                choice = "orig" if int(idx or 0) == 1 else "best"
            host.yolo_model_choice = str(choice)
        except Exception:
            host.yolo_model_choice = "best"
        self.apply_yolo_model_choice()

    def on_yolo_compare_toggle(self, checked: bool):
        host = self._host
        if bool(checked) and bool(getattr(host, "yolo_labeling_enabled", False)):
            try:
                if host.yolo_debug_window is not None:
                    host.yolo_debug_window.set_compare_checked(False)
                    host.yolo_debug_window.set_compare_status(True, "Compare disabled while Labeling")
            except Exception:
                pass
            print("[YOLO] Compare blocked (Labeling Mode ON).")
            return
        if not bool(checked):
            host.yolo_compare_enabled = False
            try:
                if host.yolo_compare_window is not None:
                    host.yolo_compare_window.hide()
            except Exception:
                pass
            print("[YOLO] Compare OFF.")
            return

        host.yolo_compare_enabled = True
        self.ensure_yolo_compare_window()
        print(f"[YOLO] Compare ON  (ui model={getattr(host, 'yolo_model_choice', 'best')})")

    def ensure_yolo_compare_window(self) -> None:
        host = self._host
        try:
            if host.yolo_compare_window is None:
                if callable(self._compare_window_factory):
                    host.yolo_compare_window = self._compare_window_factory()
                else:
                    return
            
            left_title = f"BEST ({os.path.basename(host.yolo_model_best_path)}, cls 0)"
            right_title = f"ORIGINAL ({os.path.basename(host.yolo_model_orig_path)}, cls 32)"
            host.yolo_compare_window.set_titles(left_title, right_title)

            # Ensure safe positioning (right of debug window)
            try:
                target_x, target_y = 100, 100
                if host.yolo_debug_window is not None and host.yolo_debug_window.isVisible():
                    # Place to the right
                    base_x = max(0, host.yolo_debug_window.x())
                    base_y = max(0, host.yolo_debug_window.y())
                    target_x = base_x + host.yolo_debug_window.width() + 20
                    target_y = base_y
                elif host.isVisible():
                    # Fallback relative to main window
                    base_x = max(0, host.x())
                    base_y = max(0, host.y());
                    target_x = base_x + 50
                    target_y = base_y + 50
                
                host.yolo_compare_window.move(target_x, target_y)
            except Exception:
                pass
            
            host.yolo_compare_window.show()
            host.yolo_compare_window.raise_()
            try:
                host.yolo_compare_window.activateWindow()
            except Exception:
                pass
            
        except Exception:
            pass

    def yolo_train_next_version_dir(self) -> tuple[str, str]:
        return self._host.yolo_labeling.yolo_train_next_version_dir()

    def yolo_train_prepare_dataset(self):
        return self._host.yolo_labeling.yolo_train_prepare_dataset()

    @staticmethod
    def yolo_train_iou(a, b) -> float:
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

    def yolo_train_box_sane(self, x1, y1, x2, y2, w: int, h: int) -> bool:
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

    def yolo_train_update_recent(self, box) -> bool:
        host = self._host
        host._yolo_training_recent_boxes.append(box)
        if len(host._yolo_training_recent_boxes) < 3:
            return False
        b0, b1, b2 = host._yolo_training_recent_boxes
        return (self.yolo_train_iou(b0, b1) >= 0.5) and (self.yolo_train_iou(b1, b2) >= 0.5)

    def yolo_train_assign_difficulty(self, conf: float) -> str:
        try:
            cf = float(conf)
        except Exception:
            cf = 0.0
        if cf < 0.08:
            return "hard"
        if cf < 0.18:
            return "medium"
        return "easy"

    def yolo_train_bucket_allowed(self, difficulty: str) -> bool:
        host = self._host
        total = int(host.yolo_training_target or 256)
        t_easy = int(round(total * 0.30))
        t_med = int(round(total * 0.40))
        t_hard = max(0, total - t_easy - t_med)
        if difficulty == "easy":
            return host._yolo_training_easy < t_easy
        if difficulty == "hard":
            return host._yolo_training_hard < t_hard
        return host._yolo_training_med < t_med

    def yolo_train_note_bucket(self, difficulty: str):
        host = self._host
        if difficulty == "easy":
            host._yolo_training_easy += 1
        elif difficulty == "hard":
            host._yolo_training_hard += 1
        else:
            host._yolo_training_med += 1

    def yolo_train_save_sample(self, frame_bgr, *, x1, y1, x2, y2, conf: float, difficulty: str):
        host = self._host
        if host._yolo_training_dir is None:
            return
        images_dir = os.path.join(host._yolo_training_dir, "images")
        labels_dir = os.path.join(host._yolo_training_dir, "labels")
        meta_dir = os.path.join(host._yolo_training_dir, "meta")

        idx = int(host._yolo_training_next_index)
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

        host._yolo_training_next_index += 1
        host.yolo_training_count += 1
        host._yolo_training_conf_values.append(float(conf))
        self.yolo_train_note_bucket(difficulty)

    def yolo_training_prompt(self):
        host = self._host
        now = time.time()
        if (now - float(host._yolo_training_last_prompt_ts or 0.0)) < 4.0:
            return
        host._yolo_training_last_prompt_ts = now
        if not host._yolo_training_prompt_msgs:
            return
        host._yolo_training_prompt_idx = (host._yolo_training_prompt_idx + 1) % len(host._yolo_training_prompt_msgs)
        host._yolo_training_status_msg = host._yolo_training_prompt_msgs[host._yolo_training_prompt_idx]

    def stop_yolo_training(self, *, reason: str = ""):
        host = self._host
        host.yolo_training_enabled = False
        host._yolo_training_recent_boxes.clear()
        host._yolo_training_status_msg = str(reason or "")
        try:
            host.yolo_vision_interval_s = float(host._yolo_training_interval_default or 1.0)
        except Exception:
            host.yolo_vision_interval_s = 1.0
        try:
            if host.yolo_debug_window is not None:
                host.yolo_debug_window.set_training_checked(False)
        except Exception:
            pass
        try:
            if host.yolo_train_hist_window is not None:
                host.yolo_train_hist_window.hide()
        except Exception:
            pass

    def on_yolo_training_toggle(self, checked: bool):
        host = self._host
        if not bool(getattr(host, "yolo_vision_enabled", False)):
            self.stop_yolo_training(reason="Yolo Vision is OFF")
            return

        if not bool(checked):
            self.stop_yolo_training(reason="")
            print("[YOLO] Ball Training OFF.")
            return

        # Start training
        host.yolo_training_enabled = True
        host.yolo_training_count = 0
        host._yolo_training_conf_values = []
        host._yolo_training_easy = 0
        host._yolo_training_med = 0
        host._yolo_training_hard = 0
        host._yolo_training_recent_boxes.clear()
        host._yolo_training_status_msg = "Change ball position / lighting for variety"
        host._yolo_training_last_prompt_ts = 0.0
        host._yolo_training_prompt_idx = 0

        host._yolo_training_interval_default = float(getattr(host, "yolo_vision_interval_s", 1.0) or 1.0)
        self.yolo_train_prepare_dataset()

        try:
            if host.yolo_train_hist_window is None:
                if callable(self._train_hist_window_factory):
                    host.yolo_train_hist_window = self._train_hist_window_factory()
            if host.yolo_train_hist_window is not None:
                host.yolo_train_hist_window.show()
        except Exception:
            pass

        print(f"[YOLO] Ball Training ON -> {host._yolo_training_dataset_label}")

    def update_yolo_train_hist_window(self):
        host = self._host
        try:
            if host.yolo_train_hist_window is None or not host.yolo_train_hist_window.isVisible():
                return
        except Exception:
            return
        try:
            host.yolo_train_hist_window.update_histogram(
                host._yolo_training_conf_values,
                easy_n=int(host._yolo_training_easy),
                med_n=int(host._yolo_training_med),
                hard_n=int(host._yolo_training_hard),
                total_target=int(host.yolo_training_target or 256),
                progress=int(host.yolo_training_count),
                dataset_label=str(host._yolo_training_dataset_label or ""),
            )
        except Exception:
            pass

    def run_ball_mode(self, frame_bgr):
        host = self._host
        if not isinstance(getattr(host, "_yolo_detections", None), list):
            host._yolo_detections = []
        now_y = time.time()
        yolo_ran = False
        if (now_y - float(getattr(host, "_yolo_vision_last_ts", 0.0) or 0.0)) >= float(
            getattr(host, "yolo_vision_interval_s", 0.25) or 0.25
        ):
            host._yolo_vision_last_ts = now_y
            yolo_ran = True
            try:
                host._yolo_update_count = int(getattr(host, "_yolo_update_count", 0) or 0) + 1
            except Exception:
                host._yolo_update_count = 1
            host._yolo_detections = []
            host._yolo_last_error_msg = ""
            host._yolo_last_latency_s = 0.0
            try:
                if frame_bgr is not None:
                    host._yolo_last_frame_shape = (int(frame_bgr.shape[0]), int(frame_bgr.shape[1]))
            except Exception:
                pass
            try:
                host._yolo_detections = host.yolo_detector.analyze(frame_bgr)
                if getattr(host.yolo_detector, "last_error", None):
                    host._yolo_last_error_msg = str(host.yolo_detector.last_error or "").strip()
                try:
                    host._yolo_last_latency_s = float(getattr(host.yolo_detector, "last_latency_s", 0.0) or 0.0)
                except Exception:
                    host._yolo_last_latency_s = 0.0
            except Exception as e:
                host._yolo_detections = []
                host._yolo_last_error_msg = f"YOLO exception: {e}"
                host._yolo_last_latency_s = 0.0

        ball_center = None
        if host._yolo_detections:
            b0 = host._yolo_detections[0]
            try:
                cx = int(round(float(getattr(b0, "cx", 0.0))))
                cy = int(round(float(getattr(b0, "cy", 0.0))))
                x1 = float(getattr(b0, "x1", 0.0))
                y1 = float(getattr(b0, "y1", 0.0))
                x2 = float(getattr(b0, "x2", 0.0))
                y2 = float(getattr(b0, "y2", 0.0))
                rr = 0.5 * max(6.0, min(abs(x2 - x1), abs(y2 - y1)))
                if yolo_ran:
                    host._yolo_last_hit_ts = now_y
                try:
                    host._yolo_last_hit_conf = float(getattr(b0, "conf", 0.0) or 0.0)
                except Exception:
                    host._yolo_last_hit_conf = 0.0
                try:
                    host._yolo_last_hit_box = (
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
                    host._yolo_last_hit_box = None
                try:
                    host._yolo_last_hit_count = int(len(host._yolo_detections))
                except Exception:
                    host._yolo_last_hit_count = 0
            except Exception:
                cx = cy = 0
                rr = 0.0
            _, frame_bgr = host.ball_tracker.apply_external_detection(
                frame_bgr,
                (cx, cy),
                rr,
                source="YOLO",
                draw_overlay=True,
                overlay_thickness=1,
            )
            try:
                host.overlay.draw_yolo_detections(frame_bgr, host._yolo_detections)
            except Exception:
                pass
            ball_center = host.ball_tracker.last_center
            try:
                host._ball_locked = bool(ball_center is not None and int(getattr(host.ball_tracker, "missed_frames", 0) or 0) == 0)
                host._ball_lock_source = "YOLO" if host._ball_locked else ""
            except Exception:
                host._ball_locked = False
                host._ball_lock_source = ""
        else:
            host.ball_tracker.missed_frames += 1
            host._ball_locked = False
            host._ball_lock_source = ""

        return frame_bgr, ball_center

    def run_test_mode(self, frame_bgr):
        host = self._host
        # Yolo Vision is a test mode (no motion). Clear any stale close-enough banner.
        host._ball_close_enough = False
        now_y = time.time()
        if bool(getattr(host, "yolo_training_enabled", False)):
            try:
                lat_s = float(getattr(host, "_yolo_last_latency_s", 0.0) or 0.0)
            except Exception:
                lat_s = 0.0
            adaptive = max(0.25, (lat_s * 1.2) if lat_s > 0 else 0.25)
            try:
                host.yolo_vision_interval_s = float(adaptive)
            except Exception:
                pass
        yolo_ran = False
        if (now_y - float(getattr(host, "_yolo_vision_last_ts", 0.0) or 0.0)) >= float(
            getattr(host, "yolo_vision_interval_s", 0.25) or 0.25
        ):
            host._yolo_vision_last_ts = now_y
            yolo_ran = True
            try:
                host._yolo_update_count = int(getattr(host, "_yolo_update_count", 0) or 0) + 1
            except Exception:
                host._yolo_update_count = 1
            host._yolo_detections = []
            host._yolo_last_error_msg = ""
            host._yolo_last_latency_s = 0.0
            try:
                if host.yolo_debug_window is not None and host.yolo_debug_window.isVisible():
                    ui_choice = host.yolo_debug_window.yolo_model_combo.currentData()
                    if ui_choice is None:
                        ui_choice = "best"
                    if str(ui_choice) != str(getattr(host, "yolo_model_choice", "best")):
                        host.yolo_model_choice = str(ui_choice)
                        self.apply_yolo_model_choice()
            except Exception:
                pass
            try:
                if frame_bgr is not None:
                    host._yolo_last_frame_shape = (int(frame_bgr.shape[0]), int(frame_bgr.shape[1]))
            except Exception:
                pass
            if host.yolo_detector is None:
                host._yolo_last_error_msg = "YOLO not available (install ultralytics + weights)"
            else:
                try:
                    if bool(getattr(host, "yolo_compare_enabled", False)):
                        host._yolo_compare_detections_best = []
                        host._yolo_compare_detections_orig = []
                        best_err = ""
                        orig_err = ""
                        best_lat = 0.0
                        orig_lat = 0.0
                        if host.yolo_detector_best is not None:
                            host._yolo_compare_detections_best = host.yolo_detector_best.analyze(frame_bgr)
                            best_err = str(getattr(host.yolo_detector_best, "last_error", "") or "").strip()
                            try:
                                best_lat = float(getattr(host.yolo_detector_best, "last_latency_s", 0.0) or 0.0)
                            except Exception:
                                best_lat = 0.0
                        if host.yolo_detector_orig is not None:
                            host._yolo_compare_detections_orig = host.yolo_detector_orig.analyze(frame_bgr)
                            orig_err = str(getattr(host.yolo_detector_orig, "last_error", "") or "").strip()
                            try:
                                orig_lat = float(getattr(host.yolo_detector_orig, "last_latency_s", 0.0) or 0.0)
                            except Exception:
                                orig_lat = 0.0

                        if str(getattr(host, "yolo_model_choice", "best") or "best") == "orig":
                            host._yolo_detections = list(host._yolo_compare_detections_orig or [])
                            host._yolo_last_error_msg = orig_err
                            host._yolo_last_latency_s = orig_lat
                        else:
                            host._yolo_detections = list(host._yolo_compare_detections_best or [])
                            host._yolo_last_error_msg = best_err
                            host._yolo_last_latency_s = best_lat
                    else:
                        host._yolo_detections = host.yolo_detector.analyze(frame_bgr)
                        if getattr(host.yolo_detector, "last_error", None):
                            host._yolo_last_error_msg = str(host.yolo_detector.last_error or "").strip()
                        try:
                            host._yolo_last_latency_s = float(getattr(host.yolo_detector, "last_latency_s", 0.0) or 0.0)
                        except Exception:
                            host._yolo_last_latency_s = 0.0
                except Exception as e:
                    host._yolo_detections = []
                    host._yolo_last_error_msg = f"YOLO exception: {e}"
                    host._yolo_last_latency_s = 0.0

            # Debug probe (any-class) when no sports-ball detections
            if (
                yolo_ran
                and host.yolo_detector is not None
                and not host._yolo_detections
            ):
                try:
                    if (now_y - float(getattr(host, "_yolo_probe_last_ts", 0.0) or 0.0)) >= float(
                        getattr(host, "_yolo_probe_interval_s", 2.0) or 2.0
                    ):
                        host._yolo_probe_last_ts = now_y
                        host._yolo_probe_boxes = []
                        host._yolo_probe_error_msg = ""
                        host._yolo_probe_latency_s = 0.0
                        probe_conf = float(getattr(host, "_yolo_probe_conf", 0.001) or 0.001)
                        host._yolo_probe_boxes = host.yolo_detector.probe(
                            frame_bgr,
                            conf=probe_conf,
                            max_det=5,
                        )
                        if getattr(host.yolo_detector, "last_probe_error", None):
                            host._yolo_probe_error_msg = str(host.yolo_detector.last_probe_error or "").strip()
                        try:
                            host._yolo_probe_latency_s = float(
                                getattr(host.yolo_detector, "last_probe_latency_s", 0.0) or 0.0
                            )
                        except Exception:
                            host._yolo_probe_latency_s = 0.0
                except Exception as e:
                    host._yolo_probe_boxes = []
                    host._yolo_probe_error_msg = f"probe exception: {e}"
                    host._yolo_probe_latency_s = 0.0

        # Ball Training capture (use best YOLO detection)
        if bool(getattr(host, "yolo_training_enabled", False)) and yolo_ran:
            if host._yolo_detections:
                b0 = host._yolo_detections[0]
                try:
                    x1 = float(getattr(b0, "x1", 0.0))
                    y1 = float(getattr(b0, "y1", 0.0))
                    x2 = float(getattr(b0, "x2", 0.0))
                    y2 = float(getattr(b0, "y2", 0.0))
                    conf = float(getattr(b0, "conf", 0.0) or 0.0)
                except Exception:
                    x1 = y1 = x2 = y2 = 0.0
                    conf = 0.0
                h0, w0 = frame_bgr.shape[:2]
                if not self.yolo_train_box_sane(x1, y1, x2, y2, w0, h0):
                    host._yolo_training_recent_boxes.clear()
                    host._yolo_training_status_msg = "Train: bbox rejected (sanity)"
                elif not (0.01 <= conf <= 0.99):
                    host._yolo_training_recent_boxes.clear()
                    host._yolo_training_status_msg = "Train: conf out of range"
                else:
                    stable = self.yolo_train_update_recent((x1, y1, x2, y2))
                    if not stable:
                        host._yolo_training_status_msg = "Train: stabilizing (3 frames)"
                    else:
                        difficulty = self.yolo_train_assign_difficulty(conf)
                        if not self.yolo_train_bucket_allowed(difficulty):
                            host._yolo_training_status_msg = f"Train: {difficulty} bucket full"
                        else:
                            src = host.last_display_frame_bgr if host.last_display_frame_bgr is not None else frame_bgr
                            try:
                                self.yolo_train_save_sample(
                                    src,
                                    x1=x1,
                                    y1=y1,
                                    x2=x2,
                                    y2=y2,
                                    conf=conf,
                                    difficulty=difficulty,
                                )
                                host._yolo_training_status_msg = "Train: saved"
                            except Exception:
                                host._yolo_training_status_msg = "Train: save failed"
            else:
                host._yolo_training_recent_boxes.clear()
                host._yolo_training_status_msg = "Train: no detection"

            self.update_yolo_train_hist_window()
            self.yolo_training_prompt()
            if int(getattr(host, "yolo_training_count", 0) or 0) >= int(host.yolo_training_target or 256):
                self.stop_yolo_training(reason="Training complete")

        ball_center = None
        # Apply best YOLO box (if any) as ball center for tracking
        if host._yolo_detections:
            b0 = host._yolo_detections[0]
            try:
                cx = int(round(float(getattr(b0, "cx", 0.0))))
                cy = int(round(float(getattr(b0, "cy", 0.0))))
                x1 = float(getattr(b0, "x1", 0.0))
                y1 = float(getattr(b0, "y1", 0.0))
                x2 = float(getattr(b0, "x2", 0.0))
                y2 = float(getattr(b0, "y2", 0.0))
                rr = 0.5 * max(6.0, min(abs(x2 - x1), abs(y2 - y1)))
                if yolo_ran:
                    host._yolo_last_hit_ts = now_y
                try:
                    host._yolo_last_hit_conf = float(getattr(b0, "conf", 0.0) or 0.0)
                except Exception:
                    host._yolo_last_hit_conf = 0.0
                try:
                    host._yolo_last_hit_box = (
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
                    host._yolo_last_hit_box = None
                try:
                    host._yolo_last_hit_count = int(len(host._yolo_detections))
                except Exception:
                    host._yolo_last_hit_count = 0
            except Exception:
                cx = cy = 0
                rr = 0.0
            _, frame_bgr = host.ball_tracker.apply_external_detection(
                frame_bgr,
                (cx, cy),
                rr,
                source="YOLO",
                draw_overlay=True,
                overlay_thickness=1,
            )
            try:
                host.overlay.draw_yolo_detections(frame_bgr, host._yolo_detections)
            except Exception:
                pass
            ball_center = host.ball_tracker.last_center
            try:
                host._ball_locked = bool(ball_center is not None and int(getattr(host.ball_tracker, "missed_frames", 0) or 0) == 0)
                host._ball_lock_source = "YOLO" if host._ball_locked else ""
            except Exception:
                host._ball_locked = False
                host._ball_lock_source = ""
        else:
            host.ball_tracker.missed_frames += 1
            host._ball_locked = False
            host._ball_lock_source = ""

        # Shared histogram window (Object Detection Test)
        try:
            src = host.last_display_frame_bgr if host.last_display_frame_bgr is not None else frame_bgr
            rr = float(getattr(host.ball_tracker, "last_radius", 0.0) or 0.0)
            host.ai_vision.maybe_update_test_hist(
                "Yolo Vision",
                src,
                ball_center,
                rr,
                interval_s=float(getattr(host, "yolo_vision_interval_s", 1.0) or 1.0),
            )
        except Exception:
            pass

        # YOLO debug window (rich status + overlay)
        try:
            self.update_debug_view(frame_bgr)
        except Exception:
            pass
        # YOLO compare window (best vs original)
        try:
            self.update_compare_view(frame_bgr)
        except Exception:
            pass
        try:
            if host.yolo_compare_enabled:
                if host.yolo_compare_window is None:
                    self.ensure_yolo_compare_window()
                elif not host.yolo_compare_window.isVisible():
                    host.yolo_compare_window.show()
                    host.yolo_compare_window.raise_()
        except Exception:
            pass

        return frame_bgr, ball_center
