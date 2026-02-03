#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : overlay_renderer.py
 Author : MT & GitHub Copilot

 Description:
     Overlay drawing helpers extracted from mtDogMain.py. Preserves all
     visual output for AI/YOLO overlays, probe boxes, and labeling UI.

 v1.04  (2026-02-01)          : mt_Ball label placement/color
     • Render mt_Ball label at bottom of box using distinct text color.
     • Normalize label casing to mt_Ball / Sport_Ball.
 v1.03  (2026-02-01)          : Dual-model YOLO boxes
     • Draw COCO detections (thin) + mt_ball detections (thick) and highlight active target.
 v1.02  (2026-02-01)          : YOLO label text
     • Use compact per-box label like "Ball 0.97" (instead of "YOLO ball 97%").
 v1.01  (2026-02-01)          : YOLO multi-box highlight
     • Top-confidence YOLO ROI box/text is green; remaining detections use light blue.
 v1.00  (2026-01-31 18:05)    : Initial overlay renderer extraction
     • Move overlay drawing helpers out of mtDogMain.py.
===============================================================================
"""

from __future__ import annotations

import time

import cv2
import numpy as np


class OverlayRenderer:
    @staticmethod
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

    @staticmethod
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

    def draw_ai_detections(self, frame_bgr, detections, *, ai_detector=None):
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
            latency_s = float(getattr(ai_detector, "last_latency_s", 0.0) or 0.0) if ai_detector is not None else 0.0
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

    def draw_yolo_detections(self, frame_bgr, detections):
        if frame_bgr is None or not detections:
            return
        h, w = frame_bgr.shape[:2]
        hsv_img = None
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            hsv_img = None
        # Determine "top" detection by confidence (do not assume list order).
        try:
            top_det = max(detections, key=lambda d: float(getattr(d, "conf", 0.0) or 0.0))
        except Exception:
            top_det = detections[0]

        top_color = (0, 255, 0)          # green (BGR)
        other_color = (255, 220, 140)    # light blue (BGR)

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

            # Top-confidence object highlighted in green; others use light blue.
            color = top_color if det is top_det else other_color
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 1)
            label_disp = "Ball" if "ball" in label.lower() else (label.strip().title() or "Obj")
            txt = f"{label_disp} {conf:.2f}"
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
            self._draw_center_marker(frame_bgr, cx, cy, self._contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
            c_txt = f"({cx},{cy})"
            c_ty = min(h - 5, ty + 16)
            c_tx = max(0, min(w - 1, x1 + 2))
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    def draw_yolo_dual_detections(self, frame_bgr, coco_detections, mt_detections, *, active_target=None):
        """Draw dual-model detections.

        - COCO: thin, light-blue.
        - mt_ball: thicker, high-contrast orange.
        - Active target (if provided): highlight in green.

        active_target is expected to be a dict with key 'bbox'=(x1,y1,x2,y2).
        """
        if frame_bgr is None:
            return

        h, w = frame_bgr.shape[:2]

        coco_color = (255, 220, 140)   # light blue (BGR)
        mt_color = (0, 165, 255)       # orange (BGR)
        mt_text_color = (255, 0, 255)  # magenta (BGR) to avoid Sport_Ball label collisions
        active_color = (0, 255, 0)     # green (BGR)

        active_bbox = None
        try:
            if isinstance(active_target, dict):
                active_bbox = active_target.get("bbox", None)
        except Exception:
            active_bbox = None

        def _norm_label(det_label: str, cls_id=None) -> str:
            s = str(det_label or "").strip().lower()
            if s in ("mt_ball", "mt ball", "mtball"):
                return "mt_Ball"
            if s in ("sports ball", "sport ball", "sports_ball", "sport_ball"):
                return "Sport_Ball"
            if s == "dog":
                return "Dog"
            if s == "person":
                return "Person"
            # Fallback to class id if label missing
            if not s and cls_id is not None:
                return f"cls{int(cls_id)}"
            return (det_label or "Obj").strip().replace(" ", "_").title().replace("_", "_")

        def _draw(det, *, base_color, thickness: int):
            try:
                x1 = int(round(float(getattr(det, "x1", 0.0))))
                y1 = int(round(float(getattr(det, "y1", 0.0))))
                x2 = int(round(float(getattr(det, "x2", 0.0))))
                y2 = int(round(float(getattr(det, "y2", 0.0))))
                conf = float(getattr(det, "conf", 0.0) or 0.0)
                label = str(getattr(det, "label", "") or "")
                cls_id = getattr(det, "cls", None)
            except Exception:
                return

            x1 = max(0, min(w - 1, x1))
            y1 = max(0, min(h - 1, y1))
            x2 = max(0, min(w - 1, x2))
            y2 = max(0, min(h - 1, y2))
            if x2 <= x1 or y2 <= y1:
                return

            color = base_color
            draw_th = int(thickness)
            if active_bbox is not None:
                try:
                    ax1, ay1, ax2, ay2 = [float(v) for v in active_bbox]
                    if abs(float(x1) - ax1) < 2 and abs(float(y1) - ay1) < 2 and abs(float(x2) - ax2) < 2 and abs(float(y2) - ay2) < 2:
                        color = active_color
                        draw_th = max(draw_th, 3)
                except Exception:
                    pass

            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, draw_th)

            label_disp = _norm_label(label, cls_id)
            txt = f"{label_disp} {conf:.2f}"
            tx = max(0, min(w - 1, x1 + 2))
            if label_disp == "mt_Ball" and color != active_color:
                ty = min(h - 5, y2 + 16)
                tcolor = mt_text_color
            else:
                ty = max(15, y1 - 6)
                tcolor = color
            cv2.putText(frame_bgr, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(frame_bgr, txt, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, tcolor, 1)

            # Only mark the active target center to reduce clutter.
            if color == active_color:
                cx = int(round((x1 + x2) / 2.0))
                cy = int(round((y1 + y2) / 2.0))
                cx = max(0, min(w - 1, cx))
                cy = max(0, min(h - 1, cy))
                cv2.circle(frame_bgr, (cx, cy), 2, active_color, -1)

        for det in (coco_detections or []):
            _draw(det, base_color=coco_color, thickness=1)
        for det in (mt_detections or []):
            _draw(det, base_color=mt_color, thickness=2)

    def draw_yolo_probe_boxes(self, frame_bgr, detections):
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
            self._draw_center_marker(frame_bgr, cx, cy, self._contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
            c_txt = f"({cx},{cy})"
            c_ty = min(h - 5, ty + 16)
            c_tx = max(0, min(w - 1, x1 + 2))
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, c_txt, (c_tx, c_ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)

    def draw_labeling_overlay(self, vis, label_msg: str, save_msg_ts: float, p1, p2):
        if vis is None:
            return
        h, w = vis.shape[:2]

        # Status
        msg = str(label_msg or "")
        if msg:
            cv2.putText(vis, msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Save flash
        if time.time() - float(save_msg_ts or 0.0) < 2.0:
            cv2.putText(vis, "SAVED!", (w - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Box
        if p1 and p2:
            x1, y1 = p1
            x2, y2 = p2

            cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 255, 0), 2) # Cyan

            bw = abs(x2 - x1)
            bh = abs(y2 - y1)
            txt = f"{bw}x{bh}"
            cv2.putText(vis, txt, (int(min(x1, x2)), int(min(y1, y2)) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
