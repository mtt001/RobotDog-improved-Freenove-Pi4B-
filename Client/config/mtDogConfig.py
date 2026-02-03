#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : mtDogConfig.py
 Author : MT & Copilot ChatGPT

 Shared configuration values for the mt* Mac client modules.

 Revision History
 v1.01 (2026-01-30)          : Client camera preference
	 • Add client camera index order and retry interval.
 v1.02 (2026-02-01)          : YOLO dual-model defaults
	 • Add default confidence thresholds and dual-model FPS cap.
===============================================================================
"""

# Default Dog Pi network settings
DOG_DEFAULT_IP      = "192.168.0.32"
DOG_VIDEO_PORT      = 8001
DOG_CONTROL_PORT    = 5001

# Typical low-battery threshold for 2S LiPo (can be overridden at runtime)
LOW_VOLTAGE_THRESHOLD = 6.5   # 7.8V to test warning Beep and LED flash. Default low battery voltage is 6.5V

# Client camera preference (Mac side when Dog server not ready)
# Index order is tried in sequence until a working camera is found.
# Common macOS setup: built-in camera is index 0, Continuity/iPhone is index 1.
# If your iPhone is index 0, move 0 behind 1 (e.g., [1, 0, 2, 3]).
CLIENT_CAMERA_INDEX_ORDER = [0, 1, 2, 3]
CLIENT_CAMERA_RETRY_SEC = 2.0

# YOLO defaults (dual-model ensemble)
# - COCO model: yolov8n.pt (sports ball id=32, dog id=16, person id=0)
# - MT model: best.pt (single class mt_ball id=0)
YOLO_COCO_CONF_DEFAULT = 0.10
YOLO_MT_BALL_CONF_DEFAULT = 0.10

# Cap inference rate to protect UI responsiveness (0/None disables capping)
YOLO_DUAL_CAP_FPS_DEFAULT = 10.0
