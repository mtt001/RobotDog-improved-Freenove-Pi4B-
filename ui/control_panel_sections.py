#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : control_panel_sections.py
 Author : MT & GitHub Copilot

 Description:
     Control panel UI section builder extracted from mtDogMain.py (CameraWindow).
     Builds Actions, Object Detection Test, and System control sections.

 v1.00  (2026-01-31 23:45)    : Initial control panel section extraction
     • Move actions/test/system UI section creation into builder.
===============================================================================
"""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout


class ControlPanelSectionsBuilder:
    def __init__(self, host):
        self._host = host

    def build_actions(self, panel_layout):
        host = self._host

        act_label = QLabel("Actions")
        act_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(act_label)

        # Row 1: Buzzer, LED, Calibration
        actions_frame1 = QFrame()
        actions_layout1 = QHBoxLayout()
        actions_layout1.setContentsMargins(0, 0, 0, 0)
        actions_layout1.setSpacing(8)

        host.btn_Beep = self._make_pill_button("🔔", "B: Buzzer beep", "#ffaa00")
        host.btn_LED = self._make_pill_button("LED\nL", "L: LED pattern", "#ff8800")
        host.btn_Calib = self._make_pill_button("Cal\nK", "K: Servo calibration", "#0099cc")

        actions_layout1.addWidget(host.btn_Beep)
        actions_layout1.addWidget(host.btn_LED)
        actions_layout1.addWidget(host.btn_Calib)
        actions_frame1.setLayout(actions_layout1)
        panel_layout.addWidget(actions_frame1)

        # Row 2: Ball (autonomous tracking) + Face
        actions_frame2 = QFrame()
        actions_layout2 = QHBoxLayout()
        actions_layout2.setContentsMargins(0, 0, 0, 0)
        actions_layout2.setSpacing(8)

        host.btn_Ball = self._make_pill_button(
            "Ball",
            "Autonomous tracking (moves dog) + Mask window",
            "#0066cc",
        )
        host.btn_Face = self._make_pill_button("Face", "Face tracking (future)", "#8844cc")

        actions_layout2.addWidget(host.btn_Ball)
        actions_layout2.addWidget(host.btn_Face)
        actions_frame2.setLayout(actions_layout2)
        panel_layout.addWidget(actions_frame2)

    def build_test(self, panel_layout):
        host = self._host

        test_label = QLabel("Object Detection Test")
        test_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(test_label)

        test_frame = QFrame()
        test_frame.setStyleSheet("background-color:#0f151d; border:1px solid #233144; border-radius:10px;")
        test_layout = QVBoxLayout()
        test_layout.setContentsMargins(8, 8, 8, 8)
        test_layout.setSpacing(8)

        host.btn_CVBall = self._make_pill_button("CV Ball", "CV detector test (no motion)", "#00bcd4")
        host.btn_YoloVision = self._make_pill_button("Yolo Vision", "YOLO detector test (no motion)", "#2e7d32")
        host.btn_AIVision = self._make_pill_button("GPT Vision", "GPT detector test (no motion)", "#00a3a3")

        # Make them easier to tap and read in the narrow panel
        try:
            host.btn_CVBall.setMinimumHeight(36)
            host.btn_YoloVision.setMinimumHeight(36)
            host.btn_AIVision.setMinimumHeight(36)
        except Exception:
            pass

        test_layout.addWidget(host.btn_CVBall)
        test_layout.addWidget(host.btn_YoloVision)
        test_layout.addWidget(host.btn_AIVision)
        test_frame.setLayout(test_layout)
        panel_layout.addWidget(test_frame)

    def build_system(self, panel_layout):
        host = self._host

        sys_label = QLabel("System (D: Relax, Q: Quit)")
        sys_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(sys_label)

        sys_frame = QFrame()
        sys_layout = QHBoxLayout()
        sys_layout.setContentsMargins(0, 0, 0, 0)
        sys_layout.setSpacing(8)

        host.btn_play = self._make_pill_button("Play", "P: Play pose sequence", "#777777")
        host.btn_quit = self._make_pill_button("Quit", "Q: Quit program", "#cc3333")

        sys_layout.addWidget(host.btn_play)
        sys_layout.addWidget(host.btn_quit)
        sys_frame.setLayout(sys_layout)
        panel_layout.addWidget(sys_frame)

    @staticmethod
    def _make_pill_button(text: str, tooltip: str, bg: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(32)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color:{bg};
                color:#ffffff;
                border:none;
                border-radius:16px;
                padding:4px 10px;
                font-size:14px;
            }}
            QPushButton:hover {{
                background-color:#ffffff;
                color:{bg};
            }}
            """
        )
        btn.setToolTip(tooltip)
        return btn
