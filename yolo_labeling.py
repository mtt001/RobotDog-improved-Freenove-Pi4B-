#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : yolo_labeling.py
 Author : MT & GitHub Copilot

 Description:
     YOLO manual labeling controller extracted from mtDogMain.py (CameraWindow).
     Maintains labeling state, input handlers, dataset path/version resolution,
     and manual label saving logic.

 v1.00  (2026-01-31 16:55)    : Initial labeling controller extraction
     • Extract YOLO manual labeling state + handlers from CameraWindow.
===============================================================================
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime

import cv2

from PyQt5.QtCore import Qt


class YoloLabelingController:
    def __init__(self, host, *, label_window_factory=None):
        self._host = host
        self._label_window_factory = label_window_factory

        # YOLO Manual Labeling
        self._host.yolo_labeling_enabled = False
        self._host._yolo_labeling_p1 = None       # (x, y) starting point
        self._host._yolo_labeling_p2 = None       # (x, y) current/end point
        self._host._yolo_labeling_drawing = False # Is currently dragging?
        self._host._yolo_labeling_class_names = ["ball", "dog_Maji", "dog_Salad"]
        self._host._yolo_labeling_class_id = 0    # Default to 'ball'
        self._host._yolo_labeling_last_frame = None
        self._host._yolo_labeling_msg = ""
        self._host._yolo_labeling_save_msg_ts = 0.0

    def yolo_train_next_version_dir(self) -> tuple[str, str]:
        root = os.path.join(os.path.dirname(__file__), "AI_datasets")
        os.makedirs(root, exist_ok=True)
        # Always create a new version folder to preserve existing datasets.
        for v in range(1, 100):
            label = f"yolo_ball_v{v:02d}"
            path = os.path.join(root, label)
            if not os.path.isdir(path):
                return path, label

        # All v01..v99 exist (full) -> reuse v01 (should not happen)
        label = "yolo_ball_v01"
        return os.path.join(root, label), label

    def yolo_train_prepare_dataset(self):
        path, label = self.yolo_train_next_version_dir()
        images_dir = os.path.join(path, "images")
        labels_dir = os.path.join(path, "labels")
        meta_dir = os.path.join(path, "meta")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)
        os.makedirs(meta_dir, exist_ok=True)

        dataset_yaml = os.path.join(path, "dataset.yaml")
        if not os.path.exists(dataset_yaml):
            try:
                class_names = list(self._host._yolo_labeling_class_names or ["ball"])
                nc_val = len(class_names) if class_names else 1
                names_line = ", ".join(class_names) if class_names else "ball"
                with open(dataset_yaml, "w", encoding="utf-8") as f:
                    f.write("# YOLO dataset configuration\n")
                    f.write("# Root path for this dataset version (relative path).\n")
                    f.write("path: .\n\n")
                    f.write("# Image folders (relative to path).\n")
                    f.write("# Auto-labeled images are typically saved under images/ with labels/ and meta/.\n")
                    f.write("# Manual-labeled images are saved as manual_<timestamp>.jpg with matching labels.\n")
                    f.write("train: images\nval: images\n\n")
                    f.write("# Class definitions\n")
                    f.write(f"nc: {nc_val}\n")
                    f.write(f"names: [{names_line}]\n")
            except Exception:
                pass

        readme_path = os.path.join(path, "README.md")
        if not os.path.exists(readme_path):
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                version_tag = label.replace("yolo_ball_", "")
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(f"# {label}\n")
                    f.write(f"Updated: {today}\n\n")
                    f.write("YOLO Ball dataset captured via Yolo Vision.\n")
                    f.write("Auto-labeled by detector; see meta/ for confidence and difficulty.\n")
                    f.write("Manual labels (if any) are stored alongside auto labels in labels/.\n")
                    f.write("\nVersion History\n")
                    f.write(
                        f"- {version_tag} ({today}): Initial dataset folder created; preserve this dataset and create new versions in sibling folders (v02, v03, ...).\n"
                    )
                    f.write("\nData Sources\n")
                    f.write("- Auto labeling: images named `imgNNNNNN.jpg` with optional metadata in `meta/`.\n")
                    f.write("- Manual labeling: images named `manual_<timestamp>.jpg` and matching labels `manual_<timestamp>.txt`.\n")
            except Exception:
                pass

        # Determine next image index (continue to img001000)
        next_idx = 1
        try:
            max_idx = 0
            for name in os.listdir(images_dir):
                m = re.match(r"img(\d{6})\.jpg$", name)
                if m:
                    max_idx = max(max_idx, int(m.group(1)))
            next_idx = max_idx + 1
        except Exception:
            next_idx = 1

        if next_idx > int(self._host.yolo_training_target or 1000):
            next_idx = int(self._host.yolo_training_target or 1000) + 1

        self._host._yolo_training_dir = path
        self._host._yolo_training_dataset_label = label
        self._host._yolo_training_next_index = next_idx

    def yolo_labeling_class_label(self) -> str:
        try:
            idx = int(self._host._yolo_labeling_class_id)
        except Exception:
            idx = 0
        try:
            name = self._host._yolo_labeling_class_names[idx]
        except Exception:
            name = "class"
        return f"{idx}:{name}"

    def on_yolo_labeling_class_changed(self, idx: int):
        try:
            idx = int(idx)
        except Exception:
            return
        if idx < 0 or idx >= len(self._host._yolo_labeling_class_names):
            return
        self._host._yolo_labeling_class_id = idx
        if self._host.yolo_labeling_enabled:
            self._host._yolo_labeling_msg = f"Draw box... Enter to save. [{self.yolo_labeling_class_label()}]"

    def on_yolo_labeling_toggle(self, checked: bool):
        self._host.yolo_labeling_enabled = bool(checked)
        if self._host.yolo_labeling_enabled:
            print("[YOLO] Labeling Mode ON.")
            if bool(getattr(self._host, "yolo_compare_enabled", False)):
                self._host.yolo_compare_enabled = False
                print("[YOLO] Compare OFF (disabled during Labeling).")
                try:
                    if self._host.yolo_compare_window is not None:
                        self._host.yolo_compare_window.hide()
                except Exception:
                    pass
                try:
                    if self._host.yolo_debug_window is not None:
                        self._host.yolo_debug_window.set_compare_checked(False)
                except Exception:
                    pass
            try:
                if self._host.yolo_debug_window is not None:
                    self._host.yolo_debug_window.set_compare_status(True, "Labeling ON — Compare OFF")
            except Exception:
                pass
            # Ensure output directory exists (reuse existing logic)
            self.yolo_train_prepare_dataset()
            self._host._yolo_labeling_msg = f"Draw box... Enter to save. [{self.yolo_labeling_class_label()}]"
            self._host._yolo_labeling_p1 = None
            self._host._yolo_labeling_p2 = None
            self._host._yolo_labeling_drawing = False
            try:
                if self._host.yolo_label_window is None and callable(self._label_window_factory):
                    self._host.yolo_label_window = self._label_window_factory()
                if self._host.yolo_label_window is not None:
                    self._host.yolo_label_window.on_key_event = self._host._on_labeling_key_event
                    self._host.yolo_label_window.view.on_mouse_event = self._host._on_labeling_mouse_event
                    if self._host.yolo_debug_window is not None and self._host.yolo_debug_window.isVisible():
                        base_x = max(0, self._host.yolo_debug_window.x())
                        base_y = max(0, self._host.yolo_debug_window.y())
                        target_x = base_x + self._host.yolo_debug_window.width() + 20
                        target_y = base_y
                        self._host.yolo_label_window.move(target_x, target_y)
                    else:
                        self._host.yolo_label_window.move(self._host.x() + self._host.width() + 20, self._host.y() + 40)
                    self._host.yolo_label_window.show()
                    self._host.yolo_label_window.raise_()
                    self._host.yolo_label_window.activateWindow()
            except Exception:
                pass
        else:
            print("[YOLO] Labeling Mode OFF.")
            self._host._yolo_labeling_msg = ""
            self._host._yolo_labeling_p1 = None
            self._host._yolo_labeling_p2 = None
            self._host._yolo_labeling_drawing = False
            try:
                if self._host.yolo_debug_window is not None:
                    self._host.yolo_debug_window.set_compare_status(False, "")
            except Exception:
                pass
            try:
                if self._host.yolo_label_window is not None:
                    self._host.yolo_label_window.hide()
            except Exception:
                pass

    def on_labeling_mouse_event(self, etype, pos, buttons):
        if not self._host.yolo_labeling_enabled:
            return

        view = None
        if self._host.yolo_label_window is not None and self._host.yolo_label_window.isVisible():
            view = self._host.yolo_label_window.view
        elif self._host.yolo_debug_window is not None:
            view = self._host.yolo_debug_window.view
        if view is None:
            return
        pix = view.pixmap()
        if pix is None:
            return

        view_w, view_h = view.width(), view.height()
        px_w, px_h = pix.width(), pix.height()

        # Calculate offset (image is centered)
        off_x = (view_w - px_w) // 2
        off_y = (view_h - px_h) // 2

        # Coordinate in image space
        ix = pos.x() - off_x
        iy = pos.y() - off_y

        # Clamp
        ix = max(0, min(px_w - 1, ix))
        iy = max(0, min(px_h - 1, iy))

        if etype == "press":
            self._host._yolo_labeling_drawing = True
            self._host._yolo_labeling_p1 = (ix, iy)
            self._host._yolo_labeling_p2 = (ix, iy)
            self._host._yolo_labeling_msg = f"Drawing... [{self.yolo_labeling_class_label()}]"

        elif etype == "move":
            if self._host._yolo_labeling_drawing:
                self._host._yolo_labeling_p2 = (ix, iy)

        elif etype == "release":
            if self._host._yolo_labeling_drawing:
                self._host._yolo_labeling_p2 = (ix, iy)
                self._host._yolo_labeling_drawing = False
                self._host._yolo_labeling_msg = f"Press ENTER to save, SPACE to clear [{self.yolo_labeling_class_label()}]"

    def on_labeling_key_event(self, event):
        if not self._host.yolo_labeling_enabled:
            return
        key = event.key()
        if Qt.Key_1 <= key <= Qt.Key_9:
            idx = int(key - Qt.Key_1)
            if 0 <= idx < len(self._host._yolo_labeling_class_names):
                self.on_yolo_labeling_class_changed(idx)
                try:
                    if self._host.yolo_debug_window is not None:
                        self._host.yolo_debug_window.set_labeling_class_index(idx)
                except Exception:
                    pass
            return
        if key == Qt.Key_Return or key == Qt.Key_Enter:
             self.save_manual_label()
        elif key == Qt.Key_Space or key == Qt.Key_Escape:
             self._host._yolo_labeling_p1 = None
             self._host._yolo_labeling_p2 = None
             self._host._yolo_labeling_msg = f"Cleared. [{self.yolo_labeling_class_label()}]"

    def save_manual_label(self):
        if not self._host._yolo_labeling_p1 or not self._host._yolo_labeling_p2:
            return

        x1, y1 = self._host._yolo_labeling_p1
        x2, y2 = self._host._yolo_labeling_p2
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        if w < 5 or h < 5:
            self._host._yolo_labeling_msg = "Box too small!"
            return

        img = getattr(self._host, "_yolo_labeling_last_frame", None)
        if img is None:
            self._host._yolo_labeling_msg = "No frame captured!"
            return

        xmin, xmax = min(x1, x2), max(x1, x2)
        ymin, ymax = min(y1, y2), max(y1, y2)

        bbox = (xmin, ymin, xmax, ymax)

        if self.yolo_save_manual_sample(img, bbox):
            self._host._yolo_labeling_msg = "SAVED!"
            self._host._yolo_labeling_save_msg_ts = time.time()
            self._host._yolo_labeling_p1 = None
            self._host._yolo_labeling_p2 = None
        else:
            self._host._yolo_labeling_msg = "Save Failed!"

    def yolo_save_manual_sample(self, img_bgr, bbox):
        if not self._host._yolo_training_dir:
             self.yolo_train_prepare_dataset()
        if not self._host._yolo_training_dir:
             return False

        x1, y1, x2, y2 = bbox
        h_img, w_img = img_bgr.shape[:2]

        # Normalize
        dw = 1.0 / w_img
        dh = 1.0 / h_img

        bw = (x2 - x1)
        bh = (y2 - y1)
        cx = x1 + (bw / 2.0)
        cy = y1 + (bh / 2.0)

        cx *= dw
        cy *= dh
        bw *= dw
        bh *= dh

        ts = int(time.time() * 1000)
        base = f"manual_{ts}"
        try:
            img_path = os.path.join(self._host._yolo_training_dir, "images", f"{base}.jpg")
            txt_path = os.path.join(self._host._yolo_training_dir, "labels", f"{base}.txt")

            cv2.imwrite(img_path, img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            with open(txt_path, "w") as f:
                f.write(f"{self._host._yolo_labeling_class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\\n")
            print(f"[YOLO] Manual Label Saved: {base}")
            return True
        except Exception as e:
            print(f"[YOLO] Save error: {e}")
            return False

    def yolo_label_help_text(self) -> str:
        return (
            "Use this window to label (not the main camera view).\n"
            "Steps: Click-drag to draw a box around the object.\n"
            "Keys: ENTER to save, SPACE/ESC to clear.\n"
            "Class: Press 1-9 or use the class dropdown in Yolo Debug."
        )
