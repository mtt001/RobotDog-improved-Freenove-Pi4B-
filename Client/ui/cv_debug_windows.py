#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : cv_debug_windows.py
 Author : MT & GitHub Copilot

 Description:
     UI window/widget module extracted from mtDogMain.py.

 v1.00  (2026-01-31 15:10)    : Initial UI module extraction
     • Extracted UI-only window/widgets from mtDogMain.py.
===============================================================================
"""

from collections import deque

import cv2
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QSizePolicy,
    QWidget,
)


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


class CVBallDebugWindow(QWidget):
    def __init__(self, *, radial_checked: bool = False, on_radial_toggle=None):
        super().__init__()
        self.setWindowTitle("CV Ball debug")
        self.resize(760, 620)
        self._on_radial_toggle = on_radial_toggle

        self.chk_radial_gate = QCheckBox("RadialGate (CV)")
        self.chk_radial_gate.setChecked(bool(radial_checked))
        self.chk_radial_gate.setStyleSheet("color:#e6e6e6;")
        try:
            self.chk_radial_gate.toggled.connect(self._handle_radial_toggle)
        except Exception:
            pass

        self.info_label = QLabel("No detection yet.")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_label.setStyleSheet("color:#e6e6e6;")
        self.info_label.setWordWrap(True)
        self.info_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.info_label.setFixedHeight(320)

        self.view = QLabel("")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setScaledContents(True)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.chk_radial_gate, alignment=Qt.AlignLeft)
        layout.addWidget(self.view, stretch=1)
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def _handle_radial_toggle(self, checked: bool):
        try:
            if callable(self._on_radial_toggle):
                self._on_radial_toggle(bool(checked))
        except Exception:
            return

    def set_radial_gate_checked(self, checked: bool):
        try:
            self.chk_radial_gate.blockSignals(True)
            self.chk_radial_gate.setChecked(bool(checked))
        finally:
            try:
                self.chk_radial_gate.blockSignals(False)
            except Exception:
                pass

    def update_view(self, frame_bgr, mask, center, radius, missed_frames: int, debug_text: str = ""):
        try:
            mf = int(missed_frames)
        except Exception:
            mf = 0

        head = ""
        if center is None:
            head = f"CV Ball: none | missed:{mf}"
        else:
            try:
                cx, cy = int(center[0]), int(center[1])
            except Exception:
                cx, cy = 0, 0
            try:
                rr = int(round(float(radius or 0.0)))
            except Exception:
                rr = 0
            dpx = int(round(2 * rr)) if rr > 0 else 0
            head = f"CV Ball: ({cx},{cy}) D{dpx}px | missed:{mf}"

        if debug_text:
            text = str(debug_text)
            if "<span" in text or "<br" in text:
                try:
                    self.info_label.setTextFormat(Qt.RichText)
                except Exception:
                    pass
                if "<br" not in text:
                    text = text.replace("\n", "<br>")
                head_html = (
                    str(head)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                self.info_label.setText(head_html + "<br>" + text)
            else:
                try:
                    self.info_label.setTextFormat(Qt.PlainText)
                except Exception:
                    pass
                self.info_label.setText(head + "\n" + text)
        else:
            try:
                self.info_label.setTextFormat(Qt.PlainText)
            except Exception:
                pass
            self.info_label.setText(head)

        vis = None
        if mask is not None:
            try:
                if len(mask.shape) == 2:
                    vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                else:
                    vis = mask.copy()
            except Exception:
                vis = None

        if vis is None and frame_bgr is not None:
            try:
                vis = frame_bgr.copy()
            except Exception:
                vis = None

        if vis is None:
            return

        try:
            h, w = vis.shape[:2]
            if center is not None:
                cx, cy = int(round(float(center[0]))), int(round(float(center[1])))
                rr = int(round(float(radius or 0.0)))
                cx = max(0, min(w - 1, cx))
                cy = max(0, min(h - 1, cy))
                if rr > 0:
                    cv2.circle(vis, (cx, cy), rr, (0, 255, 255), 1)
                try:
                    if frame_bgr is not None:
                        hsv_src = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
                        Hc, Sc, Vc = [int(v) for v in hsv_src[cy, cx]]
                    else:
                        Hc, Sc, Vc = 0, 0, 0
                except Exception:
                    Hc, Sc, Vc = 0, 0, 0
                _draw_center_marker(vis, cx, cy, _contrast_bgr_from_hsv(Hc, Sc, Vc), alpha=0.5)
        except Exception:
            pass

        try:
            rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            self.view.setPixmap(QPixmap.fromImage(qimg))
        except Exception:
            return


class CVBallHistogramWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV Ball — Histograms")
        self.resize(900, 520)

        self.info_label = QLabel("Histogram panels")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#cfd6e4;")

        self.grid = QGridLayout()
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(6)

        self.panel_labels: list[QLabel] = []
        self.panel_titles: list[QLabel] = []
        for i in range(4):
            title = QLabel("Panel")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color:#b7c0ce;")
            view = QLabel("")
            view.setAlignment(Qt.AlignCenter)
            view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.panel_titles.append(title)
            self.panel_labels.append(view)

        for idx in range(4):
            r = 0 if idx < 2 else 2
            c = 0 if idx % 2 == 0 else 1
            self.grid.addWidget(self.panel_titles[idx], r, c)
            self.grid.addWidget(self.panel_labels[idx], r + 1, c)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.info_label)
        layout.addLayout(self.grid, stretch=1)
        self.setLayout(layout)

        # Rolling hist buffers (last 64 frames)
        self.picker_hist_h = deque(maxlen=64)
        self.picker_hist_s = deque(maxlen=64)
        self.picker_hist_v = deque(maxlen=64)
        self.frame_hist_h = deque(maxlen=64)
        self.frame_hist_s = deque(maxlen=64)
        self.frame_hist_v = deque(maxlen=64)
        self.picker_hist_updates = 0
        self.frame_hist_updates = 0

    def _render_hist_from_arrays(self, hist_h, hist_s, hist_v, *, thresholds: dict | None = None, label_text: str = ""):
        if hist_h is None or hist_s is None or hist_v is None:
            return None

        try:
            hist_h = np.asarray(hist_h, dtype=np.float32).flatten()
            hist_s = np.asarray(hist_s, dtype=np.float32).flatten()
            hist_v = np.asarray(hist_v, dtype=np.float32).flatten()
        except Exception:
            return None

        width = 256
        band_h = 60
        gap = 8
        img_h = band_h * 3 + gap * 2
        hist_img = np.zeros((img_h, width, 3), dtype=np.uint8)

        def draw_hist(hist, color, y0, bins):
            if hist is None:
                return
            if hist.size <= 0:
                return
            maxv = float(hist.max()) if hist.size > 0 else 1.0
            maxv = max(maxv, 1.0)
            for i in range(bins):
                v = float(hist[i]) / maxv
                x_bin = int(round(i * (width - 1) / (bins - 1)))
                y_val = int(round(v * (band_h - 6)))
                cv2.line(
                    hist_img,
                    (x_bin, y0 + band_h - 1),
                    (x_bin, y0 + band_h - 1 - y_val),
                    color,
                    1,
                )

        def draw_thr_line(x_px, y0, color):
            x_px = int(max(0, min(width - 1, x_px)))
            y_top = y0 + 2
            y_bot = y0 + band_h - 3
            cv2.line(hist_img, (x_px, y_top), (x_px, y_bot), color, 1)
            cv2.circle(hist_img, (x_px, y_top + 1), 2, color, -1)

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

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

        if label_text:
            cv2.putText(hist_img, label_text, (90, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return hist_img

    def _render_hist(self, hsv_img, mask, *, thresholds: dict | None = None, label_text: str = ""):
        if hsv_img is None or mask is None:
            return None
        try:
            hist_h = cv2.calcHist([hsv_img], [0], mask, [180], [0, 180])
            hist_s = cv2.calcHist([hsv_img], [1], mask, [256], [0, 256])
            hist_v = cv2.calcHist([hsv_img], [2], mask, [256], [0, 256])
        except Exception:
            return None

        width = 256
        band_h = 60
        gap = 8
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
                y_val = int(round(v * (band_h - 6)))
                cv2.line(
                    hist_img,
                    (x_bin, y0 + band_h - 1),
                    (x_bin, y0 + band_h - 1 - y_val),
                    color,
                    1,
                )

        def draw_thr_line(x_px, y0, color):
            x_px = int(max(0, min(width - 1, x_px)))
            y_top = y0 + 2
            y_bot = y0 + band_h - 3
            cv2.line(hist_img, (x_px, y_top), (x_px, y_bot), color, 1)
            cv2.circle(hist_img, (x_px, y_top + 1), 2, color, -1)

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

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

        if label_text:
            cv2.putText(hist_img, label_text, (90, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return hist_img

    def update_panels(self, frame_bgr, picker_point, ranked_masks, *, thresholds: dict | None = None, mode_label: str = ""):
        if frame_bgr is None:
            return

        h, w = frame_bgr.shape[:2]
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        except Exception:
            return

        # Panel 1: picker or whole frame (rolling last 64 frames)
        if picker_point is not None:
            px, py = int(picker_point[0]), int(picker_point[1])
            px = max(0, min(w - 1, px))
            py = max(0, min(h - 1, py))
            try:
                ph, ps, pv = [int(v) for v in hsv_img[py, px]]
                self.picker_hist_h.append(ph)
                self.picker_hist_s.append(ps)
                self.picker_hist_v.append(pv)
            except Exception:
                pass

            self.picker_hist_updates += 1
            title0 = f"Picker Histogram (1x1), rolling 64 frames  # {self.picker_hist_updates}"
            label0 = f"Picker @ ({px},{py})"

            if len(self.picker_hist_h) > 0:
                hist_h = np.bincount(np.asarray(self.picker_hist_h, dtype=np.uint8), minlength=180)
                hist_s = np.bincount(np.asarray(self.picker_hist_s, dtype=np.uint8), minlength=256)
                hist_v = np.bincount(np.asarray(self.picker_hist_v, dtype=np.uint8), minlength=256)
            else:
                hist_h = hist_s = hist_v = None
        else:
            try:
                fh = cv2.calcHist([hsv_img], [0], None, [180], [0, 180]).flatten()
                fs = cv2.calcHist([hsv_img], [1], None, [256], [0, 256]).flatten()
                fv = cv2.calcHist([hsv_img], [2], None, [256], [0, 256]).flatten()
                self.frame_hist_h.append(fh)
                self.frame_hist_s.append(fs)
                self.frame_hist_v.append(fv)
                self.frame_hist_updates += 1
            except Exception:
                pass

            title0 = f"Whole Frame Histogram ({w}x{h}), rolling 64 frames  # {self.frame_hist_updates}"
            label0 = "Whole Frame (rolling 64)"

            if len(self.frame_hist_h) > 0:
                hist_h = np.sum(np.asarray(self.frame_hist_h), axis=0)
                hist_s = np.sum(np.asarray(self.frame_hist_s), axis=0)
                hist_v = np.sum(np.asarray(self.frame_hist_v), axis=0)
            else:
                hist_h = hist_s = hist_v = None

        hist0 = self._render_hist_from_arrays(hist_h, hist_s, hist_v, thresholds=thresholds, label_text=label0)
        if hist0 is not None:
            rgb0 = cv2.cvtColor(hist0, cv2.COLOR_BGR2RGB)
            qimg0 = QImage(rgb0.data, rgb0.shape[1], rgb0.shape[0], rgb0.strides[0], QImage.Format_RGB888)
            self.panel_labels[0].setPixmap(QPixmap.fromImage(qimg0))
        self.panel_titles[0].setText(title0)

        # Panels 2-4: ranked contour masks
        for idx in range(3):
            pane = idx + 1
            title = f"Rank #{idx + 1} Contour"
            label = "No contour"
            mask_r = None
            try:
                if ranked_masks is not None and len(ranked_masks) > idx:
                    item = ranked_masks[idx]
                    mask_r = item.get("mask", None)
                    area = int(item.get("area", 0) or 0)
                    v_med = int(round(float(item.get("v_med", 0.0) or 0.0)))
                    label = f"A{area}px Vmed{v_med}"
            except Exception:
                mask_r = None

            if mask_r is not None and getattr(mask_r, "size", 0) > 0:
                hist_r = self._render_hist(hsv_img, mask_r, thresholds=thresholds, label_text=label)
                if hist_r is not None:
                    rgb_r = cv2.cvtColor(hist_r, cv2.COLOR_BGR2RGB)
                    qimg_r = QImage(rgb_r.data, rgb_r.shape[1], rgb_r.shape[0], rgb_r.strides[0], QImage.Format_RGB888)
                    self.panel_labels[pane].setPixmap(QPixmap.fromImage(qimg_r))
            else:
                self.panel_labels[pane].clear()

            self.panel_titles[pane].setText(title)

        try:
            self.info_label.setText(f"CV Ball Histograms — {mode_label}" if mode_label else "CV Ball Histograms")
        except Exception:
            pass
