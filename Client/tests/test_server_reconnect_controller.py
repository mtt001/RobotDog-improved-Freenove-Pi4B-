#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : test_server_reconnect_controller.py
 Author : Codex

 Description:
     Headless unit tests for reconnect flow behavior.

 v1.00  (2026-02-08 11:27)    : Initial reconnect regression tests
     • Verify Mac->Dog reconnect enters Dog mode when IP/CTRL/video probe are healthy.
===============================================================================
"""

from __future__ import annotations

import unittest

from controllers.server_reconnect_controller import ServerReconnectController


class _Host:
    def __init__(self):
        self.reconnect_in_progress = False
        self.use_dog_video = False

        self.last_dog_frame = None
        self.dog_last_frame_time = None
        self.dog_has_recent_frame = False
        self.video_stall = False

        self.display_fps = 1.0
        self.display_frame_count = 10
        self.display_last_time = 0.0
        self.rx_fps = 1.0
        self.rx_frame_count = 10
        self.rx_last_time = 0.0

        self.ip = "192.168.0.32"
        self.control_port = 5001

        self.server_ip_ok = False
        self.server_control_ok = False
        self.server_video_ok = False

        self.started = False
        self.beeped = False

    def ping_ip(self, _ip):
        return True

    def test_tcp_port(self, _ip, _port):
        return True

    def _probe_selected_video_path(self):
        return True

    def start_dog_client(self):
        self.started = True

    def _init_dog_video_source(self):
        return True

    def schedule_dog_entry_beep(self):
        self.beeped = True

    def _close_dog_video_source(self):
        return None

    def shutdown_dog_client(self):
        return None

    def update_status_ui(self):
        return None


class TestServerReconnectController(unittest.TestCase):
    def test_mac_to_dog_reconnect_success(self):
        host = _Host()
        ctl = ServerReconnectController(host)
        ctl.try_reconnect()

        self.assertTrue(host.started)
        self.assertTrue(host.use_dog_video)
        self.assertTrue(host.beeped)
        self.assertTrue(host.server_ip_ok)
        self.assertTrue(host.server_control_ok)
        self.assertTrue(host.server_video_ok)
        self.assertFalse(host.reconnect_in_progress)


if __name__ == "__main__":
    unittest.main(verbosity=2)
