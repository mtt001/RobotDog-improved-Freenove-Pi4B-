#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : server_reconnect_controller.py
 Author : MT & GitHub Copilot

 Description:
     Server check + reconnect controller extracted from mtDogMain.py / ui_event_handlers.py.
     Owns background server check thread and Dog/Mac reconnect flow.

 v1.00  (2026-01-31 23:15)    : Initial server/reconnect controller extraction
     • Move server check thread start/stop and try_reconnect logic into controller.
===============================================================================
"""

from __future__ import annotations

import threading
import time


class ServerReconnectController:
    def __init__(self, host):
        self._host = host

    def start_server_check_thread(self):
        host = self._host
        host.server_check_thread = threading.Thread(
            target=host.server_check_worker,
            daemon=True,
        )
        host.server_check_thread.start()

    def stop_server_check_thread(self):
        host = self._host
        host.stop_server_check = True
        if getattr(host, "server_check_thread", None) is not None:
            host.server_check_thread.join(timeout=1.0)

    def try_reconnect(self):
        """
        Dog Video button:
          - Dog→Mac: switch to Mac camera only.
          - Mac→Dog: probe IP/ports, then start Dog client if OK.
        """
        host = self._host
        if host.reconnect_in_progress:
            print("[RECONNECT] Already in progress.")
            return
        host.reconnect_in_progress = True

        if host.use_dog_video:
            print("[RECONNECT] Dog→Mac.")
            host.use_dog_video = False
            host.shutdown_dog_client()
            host.server_video_ok = False
            host.server_control_ok = False
            host.video_stall = False
            host.update_status_ui()
            host.reconnect_in_progress = False
            return

        print("[RECONNECT] Mac→Dog.")
        host.last_dog_frame = None
        host.dog_last_frame_time = None
        host.dog_has_recent_frame = False
        host.video_stall = False

        # Reset FPS counters
        host.display_fps = 0.0
        host.display_frame_count = 0
        host.display_last_time = time.time()
        host.rx_fps = 0.0
        host.rx_frame_count = 0
        host.rx_last_time = time.time()

        ip_ok = host.ping_ip(host.ip)
        ctrl_ok = host.test_tcp_port(host.ip, host.control_port)

        host.server_ip_ok = ip_ok
        host.server_control_ok = ctrl_ok

        if not (ip_ok and ctrl_ok):
            host.update_status_ui()
            host.reconnect_in_progress = False
            return

        try:
            host.start_dog_client()
            host.use_dog_video = True
            host.schedule_dog_entry_beep()
        except Exception as e:
            print(f"[RECONNECT] start_dog_client failed → MAC mode: {e}")
            host.use_dog_video = False

        host.update_status_ui()
        host.reconnect_in_progress = False
