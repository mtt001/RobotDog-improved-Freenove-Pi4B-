#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : ai_hist_windows.py
 Author : MT & GitHub Copilot

 Description:
     UI window/widget module extracted from mtDogMain.py.

 v1.00  (2026-01-31 15:10)    : Initial UI module extraction
     • Extracted UI-only window/widgets from mtDogMain.py.
===============================================================================
"""

import cv2
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy, QWidget


def _contrast_bgr_from_hsv(h: int, s: int, v: int) -> tuple[int, int, int]:
    try:
        h = int(max(0, min(179, int(h))))
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
