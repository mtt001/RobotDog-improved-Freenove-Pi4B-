#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : cv_hist_debug.py
 Author : MT & GitHub Copilot

 Description:
     CV histogram + debug window controller extracted from mtDogMain.py.
     Preserves CV debug and histogram window behavior.

 v1.00  (2026-01-31 18:40)    : Initial CV hist/debug controller extraction
     • Move CV histogram + debug window update logic out of mtDogMain.py.
===============================================================================
"""

from __future__ import annotations

import time

from ui.cv_debug_windows import CVBallHistogramWindow, CVBallDebugWindow


class CVHistDebugController:
    def __init__(self, host):
        self._host = host

        # Always-on CV histogram window
        self._host.cv_hist_interval_s = 0.5
        self._host._cv_hist_last_ts = 0.0
        self._host.cv_hist_window: CVBallHistogramWindow | None = None
        self._host._cv_ball_last_ranked_masks = []
        self._host._cv_ball_last_roi_rect = None
        self._host._cv_hist_positioned = False
        self._host.cv_debug_window: CVBallDebugWindow | None = None

    def position_cv_hist_window(self):
        host = self._host
        if host.cv_hist_window is None:
            return
        try:
            target_x = int(host.x() + host.width() + 20)
            target_y = int(host.y() + 40)
            hist_w = int(host.cv_hist_window.width())
            hist_h = int(host.cv_hist_window.height())
            if host.cv_debug_window is not None and host.cv_debug_window.isVisible():
                base_x = int(host.cv_debug_window.x())
                base_y = int(host.cv_debug_window.y())
                base_h = int(host.cv_debug_window.height())
                target_x = base_x
                target_y = base_y + base_h + 10
            # Keep within screen bounds if possible
            try:
                screen = host.screen()
                if screen is not None:
                    geo = screen.availableGeometry()
                    if (target_x + hist_w) > geo.right():
                        target_x = max(0, geo.right() - hist_w)
                    if (target_y + hist_h) > geo.bottom():
                        target_y = max(0, geo.bottom() - hist_h)
            except Exception:
                pass
            host.cv_hist_window.move(int(target_x), int(target_y))
            host._cv_hist_positioned = True
        except Exception:
            pass

    def maybe_update_cv_hist(self, frame_bgr):
        host = self._host
        if frame_bgr is None:
            return
        if not bool(getattr(host, "cv_ball_enabled", False)):
            try:
                if host.cv_hist_window is not None and host.cv_hist_window.isVisible():
                    host.cv_hist_window.hide()
            except Exception:
                pass
            return

        interval_s = float(getattr(host, "cv_hist_interval_s", 0.5) or 0.5)
        last_ts = float(getattr(host, "_cv_hist_last_ts", 0.0) or 0.0)
        now = time.time()
        if (now - last_ts) < interval_s:
            return

        if host.cv_hist_window is None:
            host.cv_hist_window = CVBallHistogramWindow()
        if not host.cv_hist_window.isVisible():
            host.cv_hist_window.show()
            host._cv_hist_positioned = False

        if not bool(getattr(host, "_cv_hist_positioned", False)):
            self.position_cv_hist_window()

        ranked = host._cv_ball_last_ranked_masks if bool(host.cv_ball_enabled) else []
        thresholds = getattr(host, "_cv_ball_last_thresholds", None)
        mode_label = "CV Ball ON" if bool(host.cv_ball_enabled) else "CV Ball OFF"
        try:
            host.cv_hist_window.update_panels(
                frame_bgr,
                getattr(host.ball_tracker, "sample_point", None),
                ranked,
                thresholds=thresholds,
                mode_label=mode_label,
            )
        except Exception:
            pass
        host._cv_hist_last_ts = now

    def update_cv_debug_window(self, mask, *, is_fresh: bool):
        host = self._host
        try:
            if host.cv_debug_window is not None and host.cv_debug_window.isVisible():
                dbg_vis = getattr(host, "_cv_ball_last_debug_vis", None)
                vis = dbg_vis
                txt = str(getattr(host, "_cv_ball_last_debug_text", "") or "")
                if vis is None:
                    vis = mask
                missed0 = int(getattr(host.ball_tracker, "missed_frames", 0) or 0)
                use_overlay = dbg_vis is None
                c_show = host.ball_tracker.last_center if (is_fresh and use_overlay) else None
                r_show = float(getattr(host.ball_tracker, "last_radius", 0.0) or 0.0) if (is_fresh and use_overlay) else 0.0
                host.cv_debug_window.update_view(
                    None,
                    vis,
                    c_show,
                    r_show,
                    missed0,
                    txt,
                )
        except Exception:
            pass
