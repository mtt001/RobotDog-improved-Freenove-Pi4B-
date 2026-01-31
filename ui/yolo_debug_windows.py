#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : yolo_debug_windows.py
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
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.common_widgets import ClickableLabel


class YoloVisionDebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yolo Vision debug")
        self.resize(760, 560)
        self.on_key_event = None  # Callback for manual labeling keys

        self.info_label = QLabel("No detection yet.")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color:#e6e6e6;")
        self.compare_status_line = ""

        # Live YOLO controls (conf/imgsz)
        self.yolo_conf_spin = QDoubleSpinBox()
        self.yolo_conf_spin.setDecimals(3)
        self.yolo_conf_spin.setRange(0.001, 0.90)
        self.yolo_conf_spin.setSingleStep(0.005)
        self.yolo_conf_spin.setToolTip("YOLO confidence threshold (lower catches more, may add false positives)")

        self.yolo_imgsz_spin = QSpinBox()
        self.yolo_imgsz_spin.setRange(320, 1280)
        self.yolo_imgsz_spin.setSingleStep(32)
        self.yolo_imgsz_spin.setToolTip("YOLO input size (bigger can detect small objects but slower)")

        self.yolo_model_combo = QComboBox()
        self.yolo_model_combo.addItem("best.pt (default)", userData="best")
        self.yolo_model_combo.addItem("yolov8n.pt", userData="orig")
        self.yolo_model_combo.setToolTip("Select YOLO weights used for detection")

        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setCheckable(True)
        self.compare_btn.setToolTip("Toggle side-by-side YOLO compare window")
        self.compare_btn.setStyleSheet(
            """
            QPushButton { background-color:#37474f; color:#ffffff; border:none; border-radius:14px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background-color:#ffffff; color:#37474f; }
            QPushButton:checked { background-color:#26c6da; color:#0b1f22; }
            """
        )

        self.train_btn = QPushButton("Ball Trainning")
        self.train_btn.setCheckable(True)
        self.train_btn.setToolTip("Toggle YOLO Ball Training dataset capture")
        self.train_btn.setStyleSheet(
            """
            QPushButton { background-color:#6a1b9a; color:#ffffff; border:none; border-radius:14px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background-color:#ffffff; color:#6a1b9a; }
            QPushButton:checked { background-color:#00c853; color:#10221b; }
            """
        )

        self.label_btn = QPushButton("Labeling")
        self.label_btn.setCheckable(True)
        self.label_btn.setToolTip("Toggle Manual Labeling (Draw boxes, Enter to save, Space to abort)")
        self.label_btn.setStyleSheet(
            """
            QPushButton { background-color:#bf360c; color:#ffffff; border:none; border-radius:14px; padding:4px 10px; font-size:12px; }
            QPushButton:hover { background-color:#ffffff; color:#bf360c; }
            QPushButton:checked { background-color:#ff5722; color:#ffffff; }
            """
        )

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(6)
        ctrl_layout.addWidget(QLabel("conf"))
        ctrl_layout.addWidget(self.yolo_conf_spin)
        ctrl_layout.addWidget(QLabel("imgsz"))
        ctrl_layout.addWidget(self.yolo_imgsz_spin)
        ctrl_layout.addWidget(QLabel("model"))
        ctrl_layout.addWidget(self.yolo_model_combo)
        self.label_class_combo = QComboBox()
        self.label_class_combo.setToolTip("Manual labeling class")
        ctrl_layout.addWidget(QLabel("class"))
        ctrl_layout.addWidget(self.label_class_combo)
        ctrl_layout.addWidget(self.compare_btn)
        ctrl_layout.addWidget(self.train_btn)
        ctrl_layout.addWidget(self.label_btn)
        ctrl_layout.addStretch()

        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        top_layout.addWidget(self.info_label)
        top_layout.addLayout(ctrl_layout)

        # Main view + right-side full-frame histogram
        self.view = ClickableLabel("")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.setScaledContents(False)  # Important for coordinate mapping

        self.full_hist_label = QLabel("")
        self.full_hist_label.setAlignment(Qt.AlignCenter)
        self.full_hist_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.full_hist_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.full_hist_label.setScaledContents(False)

        full_hist_title = QLabel("Frame HSV Histogram")
        full_hist_title.setAlignment(Qt.AlignCenter)
        full_hist_title.setStyleSheet("color:#b7c0ce; font-size:11px;")

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_layout.addWidget(full_hist_title)
        right_layout.addWidget(self.full_hist_label, stretch=1)

        # Bottom panes: hi/lo confidence images + histograms
        self.hi_img_label = QLabel("")
        self.hi_img_label.setAlignment(Qt.AlignCenter)
        self.hi_img_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.hi_img_label.setScaledContents(False)
        self.hi_img_label.setMinimumHeight(160)

        self.hi_hist_label = QLabel("")
        self.hi_hist_label.setAlignment(Qt.AlignCenter)
        self.hi_hist_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.hi_hist_label.setScaledContents(False)
        self.hi_hist_label.setMinimumHeight(160)

        self.lo_img_label = QLabel("")
        self.lo_img_label.setAlignment(Qt.AlignCenter)
        self.lo_img_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.lo_img_label.setScaledContents(False)
        self.lo_img_label.setMinimumHeight(160)

        self.lo_hist_label = QLabel("")
        self.lo_hist_label.setAlignment(Qt.AlignCenter)
        self.lo_hist_label.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.lo_hist_label.setScaledContents(False)
        self.lo_hist_label.setMinimumHeight(160)

        self.hi_title = QLabel("Highest Conf")
        self.hi_title.setAlignment(Qt.AlignCenter)
        self.hi_title.setStyleSheet("color:#b7c0ce; font-size:11px;")
        self.lo_title = QLabel("Lowest Conf")
        self.lo_title.setAlignment(Qt.AlignCenter)
        self.lo_title.setStyleSheet("color:#b7c0ce; font-size:11px;")

        hi_row = QHBoxLayout()
        hi_row.setContentsMargins(0, 0, 0, 0)
        hi_row.setSpacing(6)
        hi_row.addWidget(self.hi_img_label, stretch=1)
        hi_row.addWidget(self.hi_hist_label, stretch=1)

        lo_row = QHBoxLayout()
        lo_row.setContentsMargins(0, 0, 0, 0)
        lo_row.setSpacing(6)
        lo_row.addWidget(self.lo_img_label, stretch=1)
        lo_row.addWidget(self.lo_hist_label, stretch=1)

        hi_col = QVBoxLayout()
        hi_col.setContentsMargins(0, 0, 0, 0)
        hi_col.setSpacing(4)
        hi_col.addWidget(self.hi_title)
        hi_col.addLayout(hi_row)

        lo_col = QVBoxLayout()
        lo_col.setContentsMargins(0, 0, 0, 0)
        lo_col.setSpacing(4)
        lo_col.addWidget(self.lo_title)
        lo_col.addLayout(lo_row)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)
        bottom_layout.addLayout(hi_col)
        bottom_layout.addLayout(lo_col)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.addWidget(self.view, stretch=2)
        top_row.addLayout(right_layout, stretch=1)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        content_layout.addLayout(top_row, stretch=2)
        content_layout.addLayout(bottom_layout, stretch=2)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(top_layout)
        layout.addLayout(content_layout, stretch=1)
        self.setLayout(layout)

        self._controls_connected = False
        self._model_connected = False
        self._compare_connected = False
        self._label_class_connected = False

    def keyPressEvent(self, event):
        if self.on_key_event:
            self.on_key_event(event)
        super().keyPressEvent(event)

    def bind_labeling_toggle(self, on_toggle):
        try:
            self.label_btn.toggled.disconnect()
        except Exception:
            pass

    def bind_labeling_classes(self, class_names: list[str], on_change):
        try:
            self.label_class_combo.blockSignals(True)
            self.label_class_combo.clear()
            for idx, name in enumerate(class_names or []):
                label = f"{idx}:{name}"
                self.label_class_combo.addItem(label, userData=idx)
            if self.label_class_combo.count() > 0:
                self.label_class_combo.setCurrentIndex(0)
        except Exception:
            pass
        finally:
            try:
                self.label_class_combo.blockSignals(False)
            except Exception:
                pass
        if not self._label_class_connected:
            try:
                if callable(on_change):
                    try:
                        self.label_class_combo.currentIndexChanged[int].connect(on_change)
                    except Exception:
                        self.label_class_combo.currentIndexChanged.connect(on_change)
                self._label_class_connected = True
            except Exception:
                pass

    def set_labeling_class_index(self, idx: int):
        try:
            self.label_class_combo.blockSignals(True)
            if 0 <= int(idx) < self.label_class_combo.count():
                self.label_class_combo.setCurrentIndex(int(idx))
        except Exception:
            pass
        finally:
            try:
                self.label_class_combo.blockSignals(False)
            except Exception:
                pass

    def set_labeling_checked(self, checked: bool):
        try:
            self.label_btn.blockSignals(True)
            self.label_btn.setChecked(bool(checked))
        finally:
            try:
                self.label_btn.blockSignals(False)
            except Exception:
                pass

    def bind_training_toggle(self, on_toggle):
        try:
            self.train_btn.toggled.disconnect()
        except Exception:
            pass
        try:
            if callable(on_toggle):
                self.train_btn.toggled.connect(on_toggle)
        except Exception:
            pass

    def set_training_checked(self, checked: bool):
        try:
            self.train_btn.blockSignals(True)
            self.train_btn.setChecked(bool(checked))
        finally:
            try:
                self.train_btn.blockSignals(False)
            except Exception:
                pass

    def bind_model_selector(self, selected: str, on_change):
        try:
            self.yolo_model_combo.blockSignals(True)
            idx = 0
            if str(selected).lower() == "orig":
                idx = 1
            self.yolo_model_combo.setCurrentIndex(idx)
        except Exception:
            pass
        finally:
            try:
                self.yolo_model_combo.blockSignals(False)
            except Exception:
                pass
        if not self._model_connected:
            try:
                if callable(on_change):
                    try:
                        self.yolo_model_combo.currentIndexChanged[int].connect(on_change)
                    except Exception:
                        self.yolo_model_combo.currentIndexChanged.connect(on_change)
                self._model_connected = True
            except Exception:
                pass

    def bind_compare_toggle(self, on_toggle):
        try:
            self.compare_btn.toggled.disconnect()
        except Exception:
            pass
        try:
            if callable(on_toggle):
                self.compare_btn.toggled.connect(on_toggle)
        except Exception:
            pass

    def set_compare_checked(self, checked: bool):
        try:
            self.compare_btn.blockSignals(True)
            self.compare_btn.setChecked(bool(checked))
        finally:
            try:
                self.compare_btn.blockSignals(False)
            except Exception:
                pass

    def _set_pixmap(self, label: QLabel, img_bgr):
        if label is None:
            return
        if img_bgr is None:
            label.clear()
            return
        try:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            qimg = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            try:
                target = label.size()
                if target.width() > 0 and target.height() > 0:
                    pix = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                pass
            label.setPixmap(pix)
        except Exception:
            label.clear()

    def _render_hsv_hist(self, frame_bgr, *, label_text: str = ""):
        if frame_bgr is None:
            return None
        try:
            hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            hist_h = cv2.calcHist([hsv_img], [0], None, [180], [0, 180])
            hist_s = cv2.calcHist([hsv_img], [1], None, [256], [0, 256])
            hist_v = cv2.calcHist([hsv_img], [2], None, [256], [0, 256])
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

        draw_hist(hist_h, (0, 0, 255), 0, 180)
        draw_hist(hist_s, (0, 255, 0), band_h + gap, 256)
        draw_hist(hist_v, (255, 0, 0), (band_h + gap) * 2, 256)

        cv2.putText(hist_img, "H", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        cv2.putText(hist_img, "S", (6, band_h + gap + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(hist_img, "V", (6, (band_h + gap) * 2 + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 0), 1)
        if label_text:
            cv2.putText(hist_img, label_text, (90, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        return hist_img

    def update_view(
        self,
        vis_bgr,
        info_text: str,
        *,
        full_hist=None,
        hi_img=None,
        hi_hist=None,
        lo_img=None,
        lo_hist=None,
    ):
        text = str(info_text or "")
        if self.compare_status_line:
            text = f"{self.compare_status_line}\n{text}" if text else self.compare_status_line
        self.info_label.setText(text)
        self._set_pixmap(self.view, vis_bgr)
        self._set_pixmap(self.full_hist_label, full_hist)
        self._set_pixmap(self.hi_img_label, hi_img)
        self._set_pixmap(self.hi_hist_label, hi_hist)
        self._set_pixmap(self.lo_img_label, lo_img)
        self._set_pixmap(self.lo_hist_label, lo_hist)

    def set_compare_status(self, enabled: bool, message: str = ""):
        if enabled:
            self.compare_status_line = str(message or "")
        else:
            self.compare_status_line = ""
        if self.compare_status_line:
            self.info_label.setText(self.compare_status_line)
