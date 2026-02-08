#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : video_source_controller.py
 Author : MT & Codex

 Description:
     Video source abstraction for mtDogMain.
     Supports:
       - Legacy Pi JPEG socket frames (dog_client.image)
       - SFU RTSP pull (OpenCV/FFmpeg) for low-latency H264

 v1.00  (2026-02-07)          : Initial extraction
     • Add backend-neutral interface and SFU RTSP source.
===============================================================================
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import cv2
import numpy as np


@dataclass
class VideoFrame:
    frame: np.ndarray | None
    is_new: bool
    timestamp: float
    error: str = ""


class BaseVideoSource:
    backend = "base"

    def open(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def read(self) -> VideoFrame:
        raise NotImplementedError

    def is_ready(self) -> bool:
        return True

    def probe(self, timeout_s: float = 1.0) -> bool:
        _ = timeout_s
        return self.is_ready()


class LegacyDogSocketSource(BaseVideoSource):
    backend = "legacy_socket"

    def __init__(self, host):
        self._host = host
        self._last_frame: np.ndarray | None = None
        self._last_ts = 0.0

    def open(self) -> bool:
        return True

    def close(self) -> None:
        self._last_frame = None
        self._last_ts = 0.0

    def read(self) -> VideoFrame:
        host = self._host
        frame = None
        is_new = False
        ts = self._last_ts
        try:
            if host.dog_client is not None:
                with host.dog_client.image_lock:
                    if isinstance(host.dog_client.image, np.ndarray):
                        current = host.dog_client.image.copy()
                        is_new = self._last_frame is None or (not np.array_equal(current, self._last_frame))
                        self._last_frame = current
                        frame = current
                        if is_new:
                            ts = time.time()
                            self._last_ts = ts
        except Exception as e:
            return VideoFrame(frame=None, is_new=False, timestamp=0.0, error=str(e))
        return VideoFrame(frame=frame, is_new=is_new, timestamp=ts, error="")


class SfuRtspSource(BaseVideoSource):
    backend = "sfu_rtsp"

    def __init__(self, rtsp_url: str, *, transport: str = "tcp"):
        self.rtsp_url = str(rtsp_url or "").strip()
        self.transport = str(transport or "tcp").strip().lower()
        self.cap = None
        self.last_err = ""
        self._last_ts = 0.0
        self._last_open_try_ts = 0.0

    def _set_ffmpeg_capture_opts(self):
        opts = f"rtsp_transport;{self.transport}|fflags;nobuffer|flags;low_delay|max_delay;0|stimeout;3000000"
        prev = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS", "")
        if not prev:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = opts
        elif "rtsp_transport" not in prev:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = prev + "|" + opts

    def open(self) -> bool:
        if not self.rtsp_url:
            self.last_err = "empty RTSP URL"
            return False
        self.close()
        self._last_open_try_ts = time.time()
        self._set_ffmpeg_capture_opts()
        try:
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        except Exception as e:
            self.last_err = str(e)
            return False
        if cap is None or not cap.isOpened():
            self.last_err = f"cannot open {self.rtsp_url}"
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
            self.cap = None
            return False
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        self.cap = cap
        self.last_err = ""
        return True

    def close(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None

    def is_ready(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def probe(self, timeout_s: float = 1.0) -> bool:
        # Fast probe: TCP reachability for host:port in RTSP URL.
        try:
            parsed = urlparse(self.rtsp_url)
            host = parsed.hostname
            port = int(parsed.port or 8554)
            if not host:
                return False
            import socket

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(max(0.2, float(timeout_s)))
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            return False

    def read(self) -> VideoFrame:
        if self.cap is None or not self.cap.isOpened():
            if not self.open():
                return VideoFrame(frame=None, is_new=False, timestamp=self._last_ts, error=self.last_err)
        try:
            ok, frame = self.cap.read()
        except Exception as e:
            self.last_err = str(e)
            ok = False
            frame = None
        if ok and isinstance(frame, np.ndarray):
            ts = time.time()
            self._last_ts = ts
            self.last_err = ""
            return VideoFrame(frame=frame, is_new=True, timestamp=ts, error="")
        # Read failed: one quick reopen attempt.
        self.close()
        if self.open():
            try:
                ok2, frame2 = self.cap.read()
            except Exception as e:
                self.last_err = str(e)
                ok2 = False
                frame2 = None
            if ok2 and isinstance(frame2, np.ndarray):
                ts = time.time()
                self._last_ts = ts
                self.last_err = ""
                return VideoFrame(frame=frame2, is_new=True, timestamp=ts, error="")
        if not self.last_err:
            self.last_err = "RTSP read failed"
        return VideoFrame(frame=None, is_new=False, timestamp=self._last_ts, error=self.last_err)


class VideoSourceController:
    def __init__(self, host):
        self._host = host

    def create_source(self):
        host = self._host
        backend = str(getattr(host, "video_backend", "legacy_socket") or "legacy_socket").strip().lower()
        if backend == "sfu_rtsp":
            return SfuRtspSource(
                str(getattr(host, "sfu_rtsp_url", "") or ""),
                transport=str(getattr(host, "sfu_rtsp_transport", "tcp") or "tcp"),
            )
        return LegacyDogSocketSource(host)

