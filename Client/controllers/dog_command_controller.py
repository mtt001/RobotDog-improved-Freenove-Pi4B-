#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : dog_command_controller.py  (originally "Command.py")
 Author : MT & GitHub Copilot

 Description:
     Dog command helpers extracted from mtDogMain.py (CameraWindow).
     Handles command logging, human-readable labels, and servo/relax helpers.

 v1.00  (2026-01-31 22:25)    : Initial dog command controller extraction
     • Move command helpers + head servo sender into controller.
 v1.01  (2026-02-02)          : Document bidirectional CMD_ATTITUDE usage
     • Clarify CMD_ATTITUDE query vs set (roll/pitch/yaw).
===============================================================================
"""

from __future__ import annotations

from datetime import datetime


class COMMAND:
    """
    Command Constants Module

    Version: 1.1.1
    Date: 2026-01-10
    Author: Freenove

    Usage Notes:
        - Each command is sent as a string over the TCP control channel (port 5001), sometimes with parameters.
        - Key bindings (W/E/R/S/D/F/C/Space/L/K) are mapped in the UI.
        - Some commands are used for telemetry/status, not direct user action.
        - For head angle: use CMD_HEAD#<angle>\n (e.g., CMD_HEAD#45\n).
        - For attitude (bidirectional):
            • Query IMU attitude: CMD_ATTITUDE\n
            • Set target attitude (if firmware supports it): CMD_ATTITUDE#<roll>#<pitch>#<yaw>\n
    """

    CMD_MOVE_STOP = "CMD_MOVE_STOP"            # Space      , Emergency stop all motion immediately
    CMD_MOVE_FORWARD = "CMD_MOVE_FORWARD"      # E          , Move dog forward
    CMD_MOVE_BACKWARD = "CMD_MOVE_BACKWARD"    # C          , Move dog backward
    CMD_MOVE_LEFT = "CMD_MOVE_LEFT"            # S          , Move dog left (strafe)
    CMD_MOVE_RIGHT = "CMD_MOVE_RIGHT"          # F          , Move dog right (strafe)
    CMD_TURN_LEFT = "CMD_TURN_LEFT"            # W          , Turn dog left (yaw)
    CMD_TURN_RIGHT = "CMD_TURN_RIGHT"          # R          , Turn dog right (yaw)
    CMD_BUZZER = "CMD_BUZZER"                  # (UI/auto)  , Activate buzzer
    CMD_LED_MOD = "CMD_LED_MOD"                # (UI/auto)  , LED mode change
    CMD_LED = "CMD_LED"                        # L          , Toggle LED
    CMD_BALANCE = "CMD_BALANCE"                # (UI/auto)  , Balance mode, toggle,
    CMD_SONIC = "CMD_SONIC"                    # (UI/auto)  , Trigger ultrasonic sensor
    CMD_HEIGHT = "CMD_HEIGHT"                  # (UI/slider), Set body height, 0-100%
    CMD_HORIZON = "CMD_HORIZON"                # (UI/auto)  , Set/level horizon, IMU-based, body pitch/roll, on/off
    CMD_HEAD = "CMD_HEAD"                      # (UI/slider), Set head servo angle (CMD_HEAD#<angle>\n)
    CMD_CALIBRATION = "CMD_CALIBRATION"        # K          , Start calibration, servo trim adjustment, toggle
    CMD_POWER = "CMD_POWER"                    # (auto)     , Query/report power/voltage status in volts
    CMD_ATTITUDE = "CMD_ATTITUDE"              # (UI/auto)  , Bidirectional: query IMU with CMD_ATTITUDE\n; set target with CMD_ATTITUDE#roll#pitch#yaw\n
    CMD_RELAX = "CMD_RELAX"                    # D          , Relax all servos (de-energize), at around 90° neutral position, still powered
    CMD_WORKING_TIME = "CMD_WORKING_TIME"      # (auto)     , Query/report working time
    CMD_STOP_PWM = "CMD_STOP_PWM"              # (auto)     , Stop all PWM outputs,power off servos to save power, better to be after RELAX

    def __init__(self):
        pass


class DogCommandController:    
    def __init__(self, host, *, write_log_func=None):
        self._host = host
        self._write_log = write_log_func

    def cmd_key_to_human(self, key_char: str | None, *, send_stop: bool = False) -> str:
        if send_stop:
            return "Stop"
        if not key_char:
            return "Idle"
        key = str(key_char).lower()
        mapping = {
            "w": "Turn-L",
            "r": "Turn-R",
            "e": "Forward",
            "c": "Backward",
            "s": "Left",
            "f": "Right",
            "d": "Relax",
        }
        return mapping.get(key, key.upper())

    def log_cmd(self, payload: str, *, tag: str = "CMD") -> None:
        host = self._host
        try:
            msg = str(payload or "").strip()
            if not msg:
                return
            ts = datetime.now().strftime("%H:%M:%S")
            entry = f"{ts} {tag}: {msg}"
            try:
                host._cmd_history.append(entry)
            except Exception:
                pass
            if self._write_log is not None:
                self._write_log(f"[{tag}] {msg}")
        except Exception:
            return

    def send_relax_only(self):
        host = self._host
        if (
            not host.use_dog_video
            or host.dog_client is None
            or not getattr(host.dog_client, "tcp_flag", False)
            or not getattr(host, "server_control_ok", False)
        ):
            return
        try:
            host._send_cmd(COMMAND.CMD_RELAX + "\n", tag="RELAX")
        except Exception as e:
            print(f"[CMD] relax failed: {e}")

    def send_stop_pwm_only(self):
        host = self._host
        if (
            not host.use_dog_video
            or host.dog_client is None
            or not getattr(host.dog_client, "tcp_flag", False)
            or not getattr(host, "server_control_ok", False)
        ):
            return
        try:
            host._send_cmd(COMMAND.CMD_STOP_PWM + "\n", tag="STOP_PWM")
        except Exception as e:
            print(f"[CMD] stop_pwm failed: {e}")

    def send_head_angle(self, angle_deg: int):
        """
        Send a head-servo angle command to the Dog Pi.
        """
        host = self._host
        if host.dog_client is None or not getattr(host.dog_client, "tcp_flag", False):
            return

        # Clamp angle to HeadTracker's safe range
        angle_deg = max(
            int(host.head_tracker.cfg.min_deg),
            min(int(host.head_tracker.cfg.max_deg), int(angle_deg))
        )

        # Use string command, not bytes
        cmd_str = f"{COMMAND.CMD_HEAD}#{angle_deg}\n"
        host._send_cmd(cmd_str, tag="HEAD")  # REMOVE .encode()
        print(f"[HEAD] CMD_HEAD → {angle_deg}° /r")     # send with /r to return to beginning of line, no line feed, minimize spawn messages
