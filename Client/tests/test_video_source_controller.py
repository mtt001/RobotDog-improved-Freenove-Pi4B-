#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : test_video_source_controller.py
 Author : Codex

 Description:
     Unit tests for SFU RTSP probe behavior in video_source_controller.

 v1.00  (2026-02-08 12:31)    : Initial SFU RTSP probe regression tests
     • Require probe=False on RTSP 404 responses.
     • Require probe=True on RTSP 200 responses.
===============================================================================
"""

from __future__ import annotations

import unittest
from unittest import mock

from controllers.video_source_controller import SfuRtspSource


class _FakeSocket:
    def __init__(self, response: bytes):
        self._response = response

    def settimeout(self, _timeout):
        return None

    def connect(self, _addr):
        return None

    def sendall(self, _payload):
        return None

    def recv(self, _n):
        return self._response

    def close(self):
        return None


class TestSfuRtspProbe(unittest.TestCase):
    def test_probe_false_when_describe_404(self):
        src = SfuRtspSource("rtsp://192.168.0.198:8554/robotdog")
        fake = _FakeSocket(b"RTSP/1.0 404 Not Found\r\nCSeq: 1\r\n\r\n")
        with mock.patch("controllers.video_source_controller.socket.socket", return_value=fake):
            ok = src.probe(timeout_s=0.5)
        self.assertFalse(ok)
        self.assertIn("404", src.last_err)

    def test_probe_true_when_describe_200(self):
        src = SfuRtspSource("rtsp://192.168.0.198:8554/robotdog")
        src.last_err = "previous error"
        fake = _FakeSocket(b"RTSP/1.0 200 OK\r\nCSeq: 1\r\n\r\n")
        with mock.patch("controllers.video_source_controller.socket.socket", return_value=fake):
            ok = src.probe(timeout_s=0.5)
        self.assertTrue(ok)
        self.assertEqual(src.last_err, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
