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

 v1.01  (2026-02-01)          : Improve button readability
     • Increase button size and reduce font to avoid jammed multi-line labels.
 v1.02  (2026-02-02)          : Add Space STOP button
     • Add a wide pill-shaped Space (CMD_MOVE_STOP) button under Motion controls.
 v1.03  (2026-02-02)          : Motion panel UX polish
     • Add small layout inset to prevent edge clipping.
     • Refine STOP button states (hover/pressed/focus) for better affordance.
 v1.04  (2026-02-02)          : Motion grid layout (3×3)
     • Rebuild Motion cluster as a true 3×3 grid (W/E/R, S/D/F, X/C/V).
     • Add faded reserved X/V keys for future mapping.
 v1.00  (2026-01-31 23:15)    : Initial motion grid UI extraction
     • Move movement grid UI creation into builder.
===============================================================================
"""

from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QPushButton, QFrame, QVBoxLayout, QSizePolicy, QGridLayout, QLayout
from PyQt5.QtCore import Qt


class MotionGridBuilder:
    def __init__(self, host):
        self._host = host

    def build(self, panel_layout):
        host = self._host

        move_label = QLabel("Motion (W/E/R, S/D/F, C)")
        move_label.setStyleSheet("color:#8899aa; font-size:12px;")
        panel_layout.addWidget(move_label)

        move_frame = QFrame()
        # True 3×3 grid keeps rows/columns aligned and avoids subtle macOS
        # layout drift from column-stacks + stretches.
        move_layout = QGridLayout()
        move_layout.setContentsMargins(2, 0, 2, 0)
        move_layout.setHorizontalSpacing(6)
        move_layout.setVerticalSpacing(6)
        move_layout.setAlignment(Qt.AlignHCenter)
        move_layout.setSizeConstraint(QLayout.SetMinimumSize)

        def make_round_button(text: str, tooltip: str, color: str):
            btn = QPushButton(text)
            # Slightly larger buttons + smaller font prevents multi-line text overflow
            # on macOS/HiDPI which can look like "overlapped" buttons.
            btn.setFixedSize(68, 68)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color:{color};
                    color:#ffffff;
                    border:none;
                    border-radius:34px;
                    font-size:13px;
                    padding:4px;
                }}
                QPushButton:hover {{
                    background-color:#ffffff;
                    color:{color};
                }}
                """
            )
            btn.setToolTip(tooltip)
            return btn

        def make_reserved_round_button(text: str, tooltip: str):
            btn = QPushButton(text)
            btn.setFixedSize(68, 68)
            btn.setEnabled(False)
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color:#1a2430;
                    color:#6f7f90;
                    border:1px solid #2a3848;
                    border-radius:34px;
                    font-size:16px;
                    padding:0px;
                }
                QPushButton:disabled {
                    background-color:#1a2430;
                    color:#6f7f90;
                    border:1px dashed #2a3848;
                }
                """
            )
            btn.setToolTip(tooltip)
            return btn

        host.btn_W = make_round_button("⟲\nW", "W: Turn Left", "#007bff")
        host.btn_E = make_round_button("↑\nE", "E: Move Forward", "#00aa55")
        host.btn_R = make_round_button("⟳\nR", "R: Turn Right", "#007bff")

        host.btn_S = make_round_button("←\nS", "S: Move Left", "#00aa88")
        host.btn_D = make_round_button("◎\nD", "D: Relax", "#666666")
        host.btn_F = make_round_button("→\nF", "F: Move Right", "#00aa88")

        host.btn_C = make_round_button("↓\nC", "C: Move Backward", "#00aa55")

        # Reserved keys for future mapping (no behavior).
        host.btn_X = make_reserved_round_button("X", "Reserved: X (future)")
        host.btn_V = make_reserved_round_button("V", "Reserved: V (future)")

        # Layout (3×3):
        #   W E R
        #   S D F
        #   X C V
        move_layout.addWidget(host.btn_W, 0, 0, Qt.AlignCenter)
        move_layout.addWidget(host.btn_E, 0, 1, Qt.AlignCenter)
        move_layout.addWidget(host.btn_R, 0, 2, Qt.AlignCenter)

        move_layout.addWidget(host.btn_S, 1, 0, Qt.AlignCenter)
        move_layout.addWidget(host.btn_D, 1, 1, Qt.AlignCenter)
        move_layout.addWidget(host.btn_F, 1, 2, Qt.AlignCenter)

        move_layout.addWidget(host.btn_X, 2, 0, Qt.AlignCenter)
        move_layout.addWidget(host.btn_C, 2, 1, Qt.AlignCenter)
        move_layout.addWidget(host.btn_V, 2, 2, Qt.AlignCenter)

        # Prevent vertical compression that can clip the 3rd row (X/C/V).
        btn_d = 68
        v_gap = 6
        for row in (0, 1, 2):
            move_layout.setRowMinimumHeight(row, btn_d)
        move_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        move_frame.setMinimumHeight(btn_d * 3 + v_gap * 2)
        move_frame.setLayout(move_layout)
        panel_layout.addWidget(move_frame)

        # Emergency stop (Space) — added as a motion-adjacent control.
        panel_layout.addSpacing(6)
        host.btn_SpaceStop = QPushButton("Space  STOP")
        host.btn_SpaceStop.setToolTip("Space: Immediate stop (CMD_MOVE_STOP)")
        host.btn_SpaceStop.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        host.btn_SpaceStop.setFixedHeight(44)
        host.btn_SpaceStop.setStyleSheet(
            """
            QPushButton {
                background-color:#ff3b30;
                color:#ffffff;
                border:none;
                border-radius:22px;
                padding:8px 14px;
                font-size:15px;
                font-weight:bold;
                letter-spacing:0.5px;
            }
            QPushButton:hover {
                background-color:#ff5a52;
            }
            QPushButton:pressed {
                background-color:#d92b25;
            }
            QPushButton:focus { outline:none; }
            """
        )
        panel_layout.addWidget(host.btn_SpaceStop)
