#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : common_widgets.py
 Author : MT & GitHub Copilot

 Description:
     UI window/widget module extracted from mtDogMain.py.

 v1.00  (2026-01-31 15:10)    : Initial UI module extraction
     • Extracted UI-only window/widgets from mtDogMain.py.
===============================================================================
"""

from PyQt5.QtWidgets import QLabel


class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.on_mouse_event = None  # (type, pos, button/buttons)

    def mousePressEvent(self, event):
        if self.on_mouse_event:
            self.on_mouse_event("press", event.pos(), event.button())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.on_mouse_event:
            # For move, we care about buttons state usually
            self.on_mouse_event("move", event.pos(), event.buttons())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.on_mouse_event:
            self.on_mouse_event("release", event.pos(), event.button())
        super().mouseReleaseEvent(event)
