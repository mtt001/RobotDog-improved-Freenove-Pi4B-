#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : test_mtdog_logic_mixin.py
 Author : Codex

 Description:
     Headless unit tests for DogLogicMixin behavior (no Qt required).

 v1.00  (2026-02-08 11:27)    : Initial bug-fix regression tests
     • Verify legacy W/E/R/S/D/F/C motion key mapping.
     • Verify SFU no-first-frame path keeps video status healthy when probe succeeds.
===============================================================================
"""

from __future__ import annotations

import threading
import unittest
from unittest import mock

from mtDogLogicMixin import DogLogicMixin
from controllers.dog_command_controller import COMMAND as CMD


class _DummyClient:
    def __init__(self):
        self.tcp_flag = True


class _Host(DogLogicMixin):
    def __init__(self):
        self.use_dog_video = True
        self.dog_client = _DummyClient()
        self.server_control_ok = True
        self._sent: list[str] = []
        self.move_speed = 8

        self.server_ip_ok = False
        self.server_video_ok = False
        self.video_stall = False
        self.dog_connected = False

        self.external_video_stream = True
        self.dog_last_frame_time = 0.0
        self.ip = "192.168.0.32"

    def _send_cmd(self, payload: str, tag: str = "CMD") -> bool:
        _ = tag
        self._sent.append(payload)
        return True

    def ping_ip(self, ip: str) -> bool:
        _ = ip
        return True

    def _probe_selected_video_path(self) -> bool:
        return True


class TestDogLogicMixin(unittest.TestCase):
    def test_motion_key_mapping_legacy_layout(self):
        host = _Host()
        expected = {
            "w": CMD.CMD_TURN_LEFT,
            "e": CMD.CMD_MOVE_FORWARD,
            "r": CMD.CMD_TURN_RIGHT,
            "s": CMD.CMD_MOVE_LEFT,
            "d": CMD.CMD_RELAX,
            "f": CMD.CMD_MOVE_RIGHT,
            "c": CMD.CMD_MOVE_BACKWARD,
        }
        for k, cmd in expected.items():
            self.assertEqual(host.motion_key_to_command(k), cmd)

    def test_send_motion_command_uses_legacy_mapping(self):
        host = _Host()
        host.send_motion_command("e")
        self.assertIn(f"{CMD.CMD_MOVE_FORWARD}#8\n", host._sent)

    def test_relax_sends_cmd_relax_and_schedules_stop_pwm(self):
        host = _Host()

        class _FakeTimer:
            def __init__(self, delay, fn):
                self.delay = delay
                self.fn = fn
                self.daemon = False
            def start(self):
                # Keep deterministic test timing: do not auto-fire callback here.
                return None
            def is_alive(self):
                return False
            def cancel(self):
                return None

        with mock.patch.object(threading, "Timer", _FakeTimer):
            host.send_motion_command("d")

        self.assertIn(f"{CMD.CMD_RELAX}\n", host._sent)
        self.assertTrue(hasattr(host, "_stop_pwm_timer"))

    def test_sfu_no_first_frame_uses_probe_status(self):
        host = _Host()
        host.periodic_server_check()

        self.assertTrue(host.server_ip_ok)
        self.assertTrue(host.server_control_ok)
        self.assertTrue(host.server_video_ok)
        self.assertFalse(host.video_stall)
        self.assertTrue(host.dog_connected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
