#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : mask_picker.py
 Author : MT & GitHub Copilot

 Description:
     Mask window + HSV picker controller extracted from mtDogMain.py.
     Preserves picker behavior, hover HSV tracking, and mask window updates.

 v1.00  (2026-01-31 19:20)    : Initial mask/picker controller extraction
     • Move mask window + HSV picker handling out of mtDogMain.py.
===============================================================================
"""

from __future__ import annotations

import cv2

from PyQt5.QtCore import Qt

from mtDogBallTrack import BallMaskWindow


class MaskPickerController:
    def __init__(self, host):
        self._host = host
        self._host.ball_mask_window: BallMaskWindow | None = None
        self._host._cheer_text = ""
        self._host._cheer_visible = False
        self._host._cheer_pending_apply = False
        self._host.hover_xy_color = None
        self._host.hover_hsv_color = None

    def set_mask_cheer(self, text: str, *, visible: bool):
        self._host._cheer_text = str(text or "")
        self._host._cheer_visible = bool(visible)
        self._host._cheer_pending_apply = True

    def apply_mask_cheer_if_needed(self):
        if not bool(getattr(self._host, "_cheer_pending_apply", False)):
            return
        try:
            if self._host.ball_mask_window is None:
                return
            self._host.ball_mask_window.set_cheer(self._host._cheer_text, visible=self._host._cheer_visible)
            self._host._cheer_pending_apply = False
        except Exception:
            pass

    def on_mask_clear_cheer(self):
        # Called by Mask window "Clear" to stop barking and hide the cheer banner.
        self.set_mask_cheer("", visible=False)

    def show_mask_window(self):
        host = self._host
        if host.ball_mask_window is None:
            host.ball_mask_window = BallMaskWindow(host.ball_tracker)
            # Allow Mask window to stop barking by calling back into mtDogMain.
            try:
                host.ball_tracker.on_clear_cheer = host._on_mask_clear_cheer
            except Exception:
                pass

        # If a cheer banner is already active (e.g., completion happened before opening Mask), apply it.
        self.apply_mask_cheer_if_needed()

        # Make the mask image area initially the same size as the color view
        video_size = host.video_label.size()
        host.ball_mask_window.set_initial_view_size(
            video_size.width(), video_size.height()
        )

        # Place on the LEFT side of the color window if there is space,
        # otherwise fall back to the right side.
        mask_w = host.ball_mask_window.width()
        x_left = host.x() - mask_w - 20
        y_pos = host.y() + 40

        if x_left > 0:
            target_x = x_left
        else:
            target_x = host.x() + host.width() + 20

        host.ball_mask_window.move(target_x, y_pos)
        host.ball_mask_window.show()
        host.ball_mask_window.raise_()

    def hide_mask_window(self):
        if self._host.ball_mask_window is not None:
            self._host.ball_mask_window.hide()

    def update_mask_window(self, frame_bgr, mask):
        host = self._host
        if (
            host.ball_mode_enabled
            and host.ball_mask_window is not None
            and host.ball_mask_window.isVisible()
        ):
            # Always use the original color frame for the picker/histogram
            host.ball_mask_window.update_from_frame(frame_bgr, mask)

    def handle_mouse_press(self, event):
        host = self._host
        if (
            event.button() == Qt.LeftButton
            and host.last_display_frame_bgr is not None
        ):
            img_h, img_w, _ = host.last_display_frame_bgr.shape

            label_pos = host.video_label.mapFrom(host, event.pos())
            lx, ly = label_pos.x(), label_pos.y()
            label_w = host.video_label.width()
            label_h = host.video_label.height()
            scale = min(label_w / img_w, label_h / img_h)
            disp_w = int(img_w * scale)
            disp_h = int(img_h * scale)
            off_x = (label_w - disp_w) // 2
            off_y = (label_h - disp_h) // 2

            if off_x <= lx < off_x + disp_w and off_y <= ly < off_y + disp_h:
                ix = int((lx - off_x) / scale)
                iy = int((ly - off_y) / scale)
                ix = max(0, min(img_w - 1, ix))
                iy = max(0, min(img_h - 1, iy))

                hsv = cv2.cvtColor(host.last_display_frame_bgr, cv2.COLOR_BGR2HSV)
                H, S, V = [int(v) for v in hsv[iy, ix]]
                host.ball_tracker.set_sample_point((ix, iy), (H, S, V))

                # --- FIX: Immediately update Mask window picker HUD/histogram ---
                if (
                    host.ball_mode_enabled
                    and host.ball_mask_window is not None
                    and host.ball_mask_window.isVisible()
                    and host.last_display_frame_bgr is not None
                ):
                    _, mask = host.ball_tracker.compute_mask(host.last_display_frame_bgr)
                    host.ball_mask_window.update_from_frame(host.last_display_frame_bgr, mask)

    def handle_mouse_move(self, event):
        host = self._host
        if host.last_display_frame_bgr is not None:
            img_h, img_w, _ = host.last_display_frame_bgr.shape

            # Map Qt widget coords → video_label coords
            label_pos = host.video_label.mapFrom(host, event.pos())
            lx, ly = label_pos.x(), label_pos.y()
            label_w = host.video_label.width()
            label_h = host.video_label.height()

            scale = min(label_w / img_w, label_h / img_h)
            disp_w = int(img_w * scale)
            disp_h = int(img_h * scale)
            off_x = (label_w - disp_w) // 2
            off_y = (label_h - disp_h) // 2

            if off_x <= lx < off_x + disp_w and off_y <= ly < off_y + disp_h:
                # Inside displayed image area → map to image coords
                ix = int((lx - off_x) / scale)
                iy = int((ly - off_y) / scale)
                ix = max(0, min(img_w - 1, ix))
                iy = max(0, min(img_h - 1, iy))

                hsv = cv2.cvtColor(host.last_display_frame_bgr, cv2.COLOR_BGR2HSV)
                H, S, V = [int(v) for v in hsv[iy, ix]]

                host.hover_xy_color = (ix, iy)
                host.hover_hsv_color = (H, S, V)
            else:
                # Outside the image area
                host.hover_xy_color = None
                host.hover_hsv_color = None
        else:
            host.hover_xy_color = None
            host.hover_hsv_color = None
