#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : motion_grid_builder.py
 Author : MT & GitHub Copilot

 Description:
     Motion grid UI builder extracted from mtDogMain.py (CameraWindow).
     Builds the movement label, round buttons, and grid layout.

 v1.00  (2026-01-31 23:15)    : Initial motion grid UI extraction
     • Move movement grid UI creation into builder.
===============================================================================
"""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout


class MotionGridBuilder:
    def __init__(self, host):
        self._host = host

    def build(self, panel_layout):
        host = self._host

        move_label = QLabel("Motion (W/E/R, S/D/F, C)")
        move_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(move_label)

        move_frame = QFrame()
        move_layout = QHBoxLayout()
        move_layout.setContentsMargins(0, 0, 0, 0)
        move_layout.setSpacing(6)

        def make_round_button(text: str, tooltip: str, color: str):
            btn = QPushButton(text)
            # Slightly larger buttons + smaller font prevents multi-line text overflow
            # on macOS/HiDPI which can look like "overlapped" buttons.
            btn.setFixedSize(60, 60)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color:{color};
                    color:#ffffff;
                    border:none;
                    border-radius:30px;
                    font-size:14px;
                    padding:2px;
                }}
                QPushButton:hover {{
                    background-color:#ffffff;
                    color:{color};
                }}
                """
            )
            btn.setToolTip(tooltip)
            return btn

        col1 = QVBoxLayout(); col1.setSpacing(4)
        col2 = QVBoxLayout(); col2.setSpacing(4)
        col3 = QVBoxLayout(); col3.setSpacing(4)

        host.btn_W = make_round_button("⟲\nW", "W: Turn Left", "#007bff")
        host.btn_E = make_round_button("↑\nE", "E: Move Forward", "#00aa55")
        host.btn_R = make_round_button("⟳\nR", "R: Turn Right", "#007bff")

        host.btn_S = make_round_button("←\nS", "S: Move Left", "#00aa88")
        host.btn_D = make_round_button("◎\nD", "D: Relax", "#666666")
        host.btn_F = make_round_button("→\nF", "F: Move Right", "#00aa88")

        host.btn_C = make_round_button("↓\nC", "C: Move Backward", "#00aa55")

        col1.addWidget(host.btn_W)
        col1.addWidget(host.btn_S)
        col1.addStretch()

        col2.addWidget(host.btn_E)
        col2.addWidget(host.btn_D)
        col2.addWidget(host.btn_C)

        col3.addWidget(host.btn_R)
        col3.addWidget(host.btn_F)
        col3.addStretch()

        move_layout.addLayout(col1)
        move_layout.addLayout(col2)
        move_layout.addLayout(col3)
        move_frame.setLayout(move_layout)
        panel_layout.addWidget(move_frame)
