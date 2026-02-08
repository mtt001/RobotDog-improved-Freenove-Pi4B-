#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : status_ui_controller.py
 Author : MT & GitHub Copilot

 Description:
     Status/HUD controller extracted from ui_event_handlers.py (CameraWindow).
     Builds the bottom-bar HTML string and Dog Video button state.

 v1.01  (2026-02-07 20:42)    : Show SFU stream label in video status line
     • Status now displays `Video:SFU/<path>` when SFU backend is active.
 v1.00  (2026-01-31 22:55)    : Initial status UI controller extraction
     • Move bottom-bar status string + button color/label logic into controller.
===============================================================================
"""

from __future__ import annotations


class StatusUIController:
    def __init__(self, host):
        self._host = host

    def update_status_ui(self):
        """Update bottom-bar HTML text and Dog Video button label/color."""
        host = self._host

        def color(ok: bool) -> str:
            return "#00ff44" if ok else "#ff4444"

        # Video port color: yellow if STALL, otherwise green/red
        backend = str(getattr(host, "video_backend", "legacy_socket") or "legacy_socket")
        video_label = f"Video:{host.video_port}" if backend != "sfu_rtsp" else f"Video:SFU/{getattr(host, 'sfu_stream_path', 'robotdog')}"

        if host.video_stall and host.use_dog_video:
            video_color = "#ffff00"
            video_text = f"{video_label}(STALL)"
        else:
            video_color = "#00ff44" if host.server_video_ok else "#ff4444"
            video_text = video_label

        all_ok = (
            host.server_ip_ok
            and host.server_video_ok
            and host.server_control_ok
            and not (host.video_stall and host.use_dog_video)
        )

        html = (
            f"<span style='color:{color(host.server_ip_ok)}'>"
            f"IP {host.ip}</span>  |  "
            f"<span style='color:{video_color}'>{video_text}</span>  |  "
            f"<span style='color:{color(host.server_control_ok)}'>"
            f"Ctrl:{host.control_port}</span>"
        )
        host.status_detail_label.setText(html)

        if host.use_dog_video:
            btn_text = "Switch to\nClient Mac Video"
            btn_color = "#00ff44"
        else:
            if all_ok:
                btn_text = "Dog Video\nReady"
                btn_color = "#00ff44"
            else:
                btn_text = "Dog Video\nNOT Ready"
                btn_color = "#ff4444"

        host.dog_button.setText(btn_text)
        host.dog_button.setStyleSheet(
            f"font-size:16px; padding:10px; background-color:white; color:{btn_color};"
        )
