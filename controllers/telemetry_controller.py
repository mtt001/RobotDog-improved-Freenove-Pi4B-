#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : telemetry_controller.py
 Author : MT & GitHub Copilot

 Description:
     Telemetry state + timer setup extracted from mtDogMain.py (CameraWindow).
     Initializes telemetry fields and runs the 1 Hz polling timer.

 v1.00  (2026-01-31 22:25)    : Initial telemetry controller extraction
     • Move telemetry state + polling timer setup into controller.
===============================================================================
"""

from __future__ import annotations

from PyQt5.QtCore import QTimer


class TelemetryController:
    def __init__(self, host, *, low_voltage_threshold: float):
        self._host = host

        # Telemetry (distance, battery, simple state text)
        host.distance_cm = 0.0
        host.battery_v = 0.0
        host.left_state_seconds = 0
        host.state_name = "Resting"
        host.right_state_seconds = 0
        # Separate textual state (e.g., RELAX / MODE) to avoid flapping the
        # work/rest overlay.
        host.dog_state_name = "Resting"

        # Low-battery tracking
        host.low_voltage_threshold = low_voltage_threshold
        host.last_low_beep_time = 0.0

        # Telemetry validity
        host.telemetry_valid = False
        host.last_telemetry_ok_time = 0.0

        host.telemetry_timer = QTimer()

    def start(self):
        host = self._host
        host.telemetry_timer.timeout.connect(host.poll_telemetry)
        host.telemetry_timer.start(1000)  # 1 Hz
