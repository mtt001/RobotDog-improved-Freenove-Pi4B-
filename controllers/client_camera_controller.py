#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : client_camera_controller.py
 Author : MT & GitHub Copilot

 Description:
     Client (Mac) camera controller extracted from mtDogMain.py (CameraWindow).
     Handles camera selection, retry logic, and UI combo population.

 v1.00  (2026-01-31 22:05)    : Initial client camera controller extraction
     • Move client camera helpers + state into controller.
===============================================================================
"""

from __future__ import annotations

import time

import cv2

try:
    from PyQt5.QtMultimedia import QCameraInfo
except Exception:
    QCameraInfo = None  # type: ignore
try:
    from AVFoundation import AVCaptureDevice, AVMediaTypeVideo  # type: ignore[import-not-found]
except Exception:
    AVCaptureDevice = None  # type: ignore
    AVMediaTypeVideo = None  # type: ignore

from config.mtDogConfig import CLIENT_CAMERA_INDEX_ORDER, CLIENT_CAMERA_RETRY_SEC


class ClientCameraController:
    def __init__(self, host):
        self._host = host

        # Client camera (Mac side) preference / retry
        host._client_cam_indices = list(CLIENT_CAMERA_INDEX_ORDER)
        if not host._client_cam_indices:
            host._client_cam_indices = [0]
        host._client_cam_opened_index = None
        host._client_cam_next_try_ts = 0.0
        host._client_cam_try_pos = 0
        host._client_cam_fail_count = 0
        host._client_cam_fail_limit = 10
        host._client_cam_last_log_ts = 0.0
        host._client_cam_combo_map = []
        host._client_cam_last_msg = ""

    def log_client_cam(self, msg: str) -> None:
        host = self._host
        last = str(getattr(host, "_client_cam_last_msg", "") or "")
        if msg == last:
            return  # Suppress duplicate success messages
        print(msg)
        host._client_cam_last_msg = msg
        host._client_cam_last_log_ts = time.time()

    def open_client_camera_index(self, index: int, *, require_frame: bool = False):
        cap = None
        try:
            cap = cv2.VideoCapture(int(index), cv2.CAP_AVFOUNDATION)
        except Exception:
            cap = None
        if cap is None or not cap.isOpened():
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            return None
        if require_frame:
            ok = False
            for _ in range(3):
                try:
                    ret, _ = cap.read()
                except Exception:
                    ret = False
                if ret:
                    ok = True
                    break
                time.sleep(0.05)
            if not ok:
                try:
                    cap.release()
                except Exception:
                    pass
                return None
        return cap

    def open_client_camera_best(self, preferred_index=None) -> bool:
        host = self._host
        candidates = []
        if preferred_index is not None:
            candidates.append(int(preferred_index))
        candidates.extend([i for i in host._client_cam_indices if i not in candidates])
        for idx in candidates:
            cap = self.open_client_camera_index(idx, require_frame=True)
            if cap is not None:
                host.cap = cap
                host._client_cam_opened_index = idx
                host._client_cam_fail_count = 0
                self.log_client_cam(f"[SRC] Client camera opened (index {idx}).")
                return True
        host.cap = None
        host._client_cam_opened_index = None
        return False

    def open_client_camera_initial(self) -> None:
        host = self._host
        opened = False
        for idx in list(host._client_cam_indices):
            cap = self.open_client_camera_index(idx, require_frame=True)
            if cap is not None:
                host.cap = cap
                host._client_cam_opened_index = idx
                opened = True
                print(f"[INIT] Mac camera opened OK (index {idx}).")
                break
        if not opened:
            print("[INIT] ERROR: Mac camera could not be opened.")
            print("[INIT] HINT: Check System Settings > Privacy & Security > Camera")
            print("[INIT] HINT: Make sure Terminal/Python has camera permission")
            if host.cap is not None:
                try:
                    host.cap.release()
                except Exception:
                    pass
            host.cap = None
            host._client_cam_opened_index = None
            host._client_cam_next_try_ts = time.time() + float(CLIENT_CAMERA_RETRY_SEC)

    def iter_client_camera_indices(self):
        host = self._host
        if not host._client_cam_indices:
            return [0]
        n = len(host._client_cam_indices)
        if host._client_cam_try_pos >= n:
            host._client_cam_try_pos = 0
        ordered = (
            host._client_cam_indices[host._client_cam_try_pos :]
            + host._client_cam_indices[: host._client_cam_try_pos]
        )
        host._client_cam_try_pos = (host._client_cam_try_pos + 1) % n
        return ordered

    def retry_client_camera_if_needed(self) -> None:
        host = self._host
        if host.cap is not None and host.cap.isOpened():
            return
        now = time.time()
        if now < float(host._client_cam_next_try_ts or 0.0):
            return
        for idx in self.iter_client_camera_indices():
            cap = self.open_client_camera_index(idx, require_frame=True)
            if cap is not None:
                host.cap = cap
                host._client_cam_opened_index = idx
                host._client_cam_fail_count = 0
                self.log_client_cam(f"[SRC] Client camera opened (index {idx}).")
                return
        host._client_cam_opened_index = None
        host._client_cam_next_try_ts = now + float(CLIENT_CAMERA_RETRY_SEC)

    def _get_avfoundation_device_names(self):
        if QCameraInfo is not None:
            try:
                cams = QCameraInfo.availableCameras()
                names = []
                for cam in cams or []:
                    try:
                        names.append(str(cam.description()))
                    except Exception:
                        pass
                if names:
                    return names
            except Exception:
                pass
        if AVCaptureDevice is None or AVMediaTypeVideo is None:
            return []
        try:
            devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
        except Exception:
            devices = []
        names = []
        for dev in devices or []:
            try:
                names.append(str(dev.localizedName()))
            except Exception:
                pass
        return names

    def _scan_client_camera_indices(self, max_index: int = 2):
        host = self._host
        # Default to checking just 0, 1, 2 for speed and less log spam.
        candidates = list(dict.fromkeys(host._client_cam_indices + list(range(0, max_index + 1))))
        available = []
        for idx in candidates:
            cap = self.open_client_camera_index(idx)
            if cap is not None:
                available.append(idx)
                try:
                    cap.release()
                except Exception:
                    pass
        return available

    def refresh_client_camera_list(self, *, select_index=None):
        host = self._host
        if not hasattr(host, "mac_cam_combo"):
            return
        available = self._scan_client_camera_indices()
        host.mac_cam_combo.blockSignals(True)
        try:
            host.mac_cam_combo.clear()
        except Exception:
            pass
        host._client_cam_combo_map = []
        names = self._get_avfoundation_device_names()
        if names:
            try:
                host.mac_cam_combo.setToolTip("Detected devices: " + ", ".join(names))
            except Exception:
                pass
        for idx in available:
            label = f"Index {idx}"
            host.mac_cam_combo.addItem(label)
            host._client_cam_combo_map.append(idx)
        if not available:
            host.mac_cam_combo.addItem("No camera")
            host._client_cam_combo_map = []
        else:
            if select_index is None:
                select_index = host._client_cam_opened_index
            if select_index in host._client_cam_combo_map:
                host.mac_cam_combo.setCurrentIndex(host._client_cam_combo_map.index(select_index))
            else:
                host.mac_cam_combo.setCurrentIndex(0)
                # Ensure a working stream is opened by default
                try:
                    first_index = host._client_cam_combo_map[0]     # type: ignore[index], list index
                except Exception:
                    first_index = None
                if first_index is not None:
                    self.open_client_camera_best(preferred_index=first_index)
        host.mac_cam_combo.blockSignals(False)

    def on_mac_camera_changed(self, combo_index: int):
        host = self._host
        if combo_index is None or combo_index < 0:
            return
        if combo_index >= len(host._client_cam_combo_map):
            return
        target_index = host._client_cam_combo_map[combo_index]
        if target_index == host._client_cam_opened_index and host.cap is not None and host.cap.isOpened():
            return
        # Switch to Mac camera mode when user selects a client camera
        host.use_dog_video = False
        host.update_status_ui()
        # Prefer selected index first
        host._client_cam_indices = [target_index] + [i for i in host._client_cam_indices if i != target_index]
        try:
            if host.cap is not None:
                host.cap.release()
        except Exception:
            pass
        host.cap = None
        if self.open_client_camera_best(preferred_index=target_index):
            self.log_client_cam(f"[SRC] Client camera selected (index {host._client_cam_opened_index}).")
            return
        host._client_cam_opened_index = None
        host._client_cam_next_try_ts = 0.0
