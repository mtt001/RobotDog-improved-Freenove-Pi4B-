#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : mtDogConfig.py
 Author : MT & Copilot ChatGPT

 Shared configuration values for the mt* Mac client modules.

Revision History
v1.07 (2026-02-09 21:31)    : Add IMU web viewer defaults for mtDogMain quick-launch
	 • Add `IMU_VIEWER_URL` (default Pi-hosted `/webrtc_view.html`) with env override.
	 • Add `IMU_VIEWER_DIAG_URL` (default Pi telemetry API) for reachability checks.
v1.06 (2026-02-09 15:15)    : Move SFU default host to Pi for Phase-1 always-on deployment
	 • Set `SFU_HOST` default to 192.168.0.32 so RTSP/WebRTC paths stay available when Mac is offline.
v1.05 (2026-02-08 12:18)    : Restore SFU host default and add env override
	 • Decouple SFU host from DOG_DEFAULT_IP (control host), default back to 192.168.0.198.
	 • Allow runtime override with environment variable `SFU_HOST`.
v1.04 (2026-02-08 10:18)    : Fix SFU host IP mismatch
	 • Use DOG_DEFAULT_IP for SFU_HOST to ensure video stream matches command IP.
v1.03 (2026-02-07)          : SFU low-latency video backend defaults
	 • Add selectable video backend and SFU stream profile settings for mtDogMain.
 v1.02 (2026-02-01)          : YOLO dual-model defaults
	 • Add default confidence thresholds and dual-model FPS cap.
 v1.01 (2026-01-30)          : Client camera preference
	 • Add client camera index order and retry interval.
===============================================================================
"""

import os

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

# Main video backend selection for mtDogMain:
# - "legacy_socket": Pi direct JPEG socket on DOG_VIDEO_PORT (original path).
# - "sfu_rtsp": pull H264 stream from SFU RTSP path (lower latency + higher resolution).
VIDEO_BACKEND = "sfu_rtsp"

# SFU defaults for low-latency H264 ingest/playback pipeline.
# Control channel host (Pi) and SFU host can be different machines.
SFU_HOST = os.getenv("SFU_HOST", "192.168.0.32")	# Phase-1 default: Pi hosts SFU for always-on operation; allow override with env var.
SFU_RTSP_PORT = 8554
SFU_STREAM_PATH = "robotdog"
SFU_RTSP_TRANSPORT = "tcp"  # OpenCV/FFmpeg generally stable with TCP over LAN.
SFU_RTSP_URL = f"rtsp://{SFU_HOST}:{SFU_RTSP_PORT}/{SFU_STREAM_PATH}" 
	# RTSP is typically more efficient for video streaming than raw TCP sockets, 
	# especially for H264-encoded frames. OpenCV can directly read from RTSP URLs, 
	# which simplifies the client implementation and can reduce latency 
	# compared to receiving JPEG frames over a socket and decoding them manually.

# Preferred source profile (publisher side target; UI/diagnostics reference).
VIDEO_TARGET_WIDTH = 1280
VIDEO_TARGET_HEIGHT = 720
VIDEO_TARGET_FPS = 30
VIDEO_TARGET_BITRATE = 3500000

# Pi-hosted web IMU viewer defaults (used by mtDogMain quick-launch/status).
IMU_VIEWER_URL = os.getenv("IMU_VIEWER_URL", f"http://{DOG_DEFAULT_IP}:8080/webrtc_view.html")
IMU_VIEWER_DIAG_URL = os.getenv("IMU_VIEWER_DIAG_URL", f"http://{DOG_DEFAULT_IP}:8090/api/telemetry")
