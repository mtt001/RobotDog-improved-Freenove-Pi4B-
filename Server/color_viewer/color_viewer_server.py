#!/usr/bin/env python3
"""
IMU Viewer HTTP Proxy
Description:
    Serves Three.js IMU viewer pages and proxies IMU queries to the Pi control port (CMD_ATTITUDE).
Usage:
    # 0) Zero-typing launch (uses built-in DEFAULT_* config below)
    python3 color_viewer_server.py

    # 1) Start proxy with explicit overrides (if needed)
    python3 color_viewer_server.py --pi-host 192.168.0.32 --pi-port 5001 --http-port 8080 --webrtc-url http://192.168.0.198:8889/robotdog/whep

    # 2) Open pages
    #    http://127.0.0.1:8080/
    #    http://127.0.0.1:8080/simple
    #    http://127.0.0.1:8080/color

    # 3) Verify active stream method
    #    http://127.0.0.1:8080/video/status
    #    preferred=h264  => H.264 HLS path
    #    preferred=mjpeg => Proprietary MJPEG fallback path

    # Optional: tune H.264 profile
    python3 color_viewer_server.py --pi-host 192.168.0.32 --h264-width 1280 --h264-height 720 --h264-fps 24

    # Optional: force MJPEG-only fallback path
    python3 color_viewer_server.py --pi-host 192.168.0.32 --disable-h264

    # Stop proxy: Ctrl+C
Version:
    2026.02.12-53
Revision History:
    2026-02-12 17:42 - Added no-store cache headers for color-viewer HTTP responses to prevent stale Safari JS/UI state after refresh and ensure `/video/config` profile reflects latest persisted backend value.
    2026-02-12 17:23 - Added persistent video-profile runtime config (`video_runtime_config.json`) and publisher apply bridge: `/video/config` now writes `video_publisher_profile.env`, attempts `robot-publisher.service` restart, and keeps selected resolution across refresh/reboot.
    2026-02-12 16:09 - Added debounced low-battery state machine to telemetry (`low_battery`, `low_battery_since_ts`, `low_battery_duration_s`, policy metadata) so web UI behavior under 6.4V is explicit and stable.
    2026-02-12 15:49 - Hardened START/UPTIME semantics for power scope: START now resolves to Pi power-up/boot timestamp (`/proc/stat btime` with `/proc/uptime` fallback), and UPTIME is always computed as `now - START`.
    2026-02-12 15:45 - Improved `/diag` operator clarity: when control backend uses loopback (`127.0.0.1`), publish LAN-reachable display host and include compact runtime ports/function summary for HUD visibility.
    2026-02-12 15:42 - Refactored power-history timeline for relative mission time: default window increased to 60 minutes (rolling view) with larger in-memory ring buffer and stable start/uptime metadata for oscilloscope-style `time since start` plotting.
    2026-02-12 15:02 - Added battery-history uptime metadata (`uptime_s`, `history_start_ts`) to `/telemetry/power_history` so voltage scope can render a live power-on runtime ticker.
    2026-02-12 14:51 - Added runtime video profile config API (`GET/POST /video/config`) for `/color` UI dial (`1280x720`/`960x540`/`640x360`), applying H264 fallback capture width/height changes without restarting the whole proxy service.
    2026-02-12 14:14 - Expanded battery trend history window to 40 minutes for oscilloscope-style left->right time rendering (0..40min) while keeping boot-scoped in-memory reset behavior.
    2026-02-12 12:50 - Added Pi-side power history telemetry (`GET /telemetry/power_history`) with in-memory boot-scoped ring buffer, battery warning threshold metadata, and low-battery status flags for live overlay trend visualization.
    2026-02-12 11:35 - Bumped runtime `PROXY_VERSION` to match viewer-identity endpoint rollout so `/version` reflects active build and deployment verification is unambiguous.
    2026-02-12 11:32 - Added viewer identity registry for `/color`: new `POST /viewer/heartbeat` and `GET /viewer/summary` endpoints aggregate active viewers (IP/session, device/browser hints, viewport/screen/GPU, activity age) for operator/viewer audit summaries.
    2026-02-12 10:30 - Added Pi-side vision-only tracking lock/hold path (no motor coupling): when tracking is enabled and detector misses briefly, publish short-lived predicted/held target (`source=tracking_hold`) to reduce label flicker.
    2026-02-12 10:22 - Reduced target flicker by making vision stale-threshold adaptive to real infer latency (`stale_after_ms = max(4000, infer_ms*3+800)`), preventing normal Pi inference cadence from toggling `state=stale` between valid detections.
    2026-02-12 09:51 - Switched dual TFLite policy to `best`-first fallback (`best` infer first, run `yolov8n` only when no target) and included active infer-model tag in worker backend field (`...:best`/`...:yolov8n`) so UI can show the real model source for current `infer_ms`.
    2026-02-12 09:09 - Added model-aware target labeling for live overlay readability: detections from `best` sources are emitted as `MT_ball`, detections from `yolov8n/yolo11n` sources as `Yolo_sport ball`, preserving confidence display on UI (`<label> <conf>`).
    2026-02-12 08:34 - Added detector worker hot-reload trigger when `yolo_model_path` changes at runtime; active socket/RTSP loops now break/reload model deterministically so profile switches apply without manual YOLO toggle/restart.
    2026-02-12 08:25 - Improved TFLite/ONNX box decoding for normalized outputs (`0..1`) by auto-scaling `cx/cy/w/h` to model input size before frame-space conversion, fixing tiny corner-locked bbox artifacts on Pi exported YOLO models.
    2026-02-12 08:23 - Fixed TFLite fixed-shape inference mismatch by auto-deriving model input size from interpreter input tensor metadata (per model/spec), preventing `imgsz` runtime config from forcing invalid tensor shapes for `*_320_fp16.tflite`.
    2026-02-12 07:50 - Added Pi `tflite-multi` round-robin backend for comma-separated model paths (e.g. `best.pt,yolov8n.pt`), including per-model `.tflite` candidate resolution and active-model runtime labeling to reduce dual-model CPU pressure while keeping both models live.
    2026-02-12 07:42 - Hardened RTSP detector fallback with consecutive-read-failure auto-reopen to reduce persistent `rtsp_read_failed` stalls during long-running Pi inference.
    2026-02-12 07:38 - Added detector frame-source fallback (`8001` socket -> RTSP `8554/robotdog`) so vision inference can continue when legacy JPEG stream is unavailable/closed.
    2026-02-11 22:00 - Fixed detector worker fallback crash (`NameError: model_path`) so failed model attempts now report cleanly instead of terminating the vision thread.
    2026-02-11 21:52 - Added TFLite detector backend (`tflite-runtime`/`tensorflow.lite`) with model-path fallback candidates (`.onnx`, `_cv451.onnx`, `.tflite`) for Pi-first runtime recovery when Ultralytics/ONNXRuntime is unavailable.
    2026-02-11 21:27 - Added dual-model Ultralytics inference mode: `yolo_model_path` now accepts comma-separated paths (e.g. `best.pt,yolov8n.pt`) and worker merges detections by confidence.
    2026-02-11 19:17 - Integrated ONNX Runtime backend for `.onnx` models with automatic backend preference (`onnxruntime` -> `onnx-dnn`), preserving existing Ultralytics `.pt` path as fallback.
    2026-02-11 18:03 - Completed detector backend integration: fixed model path resolver and added working ONNX/OpenCV-DNN fallback path in vision worker when Ultralytics/Torch is unavailable on Pi.
    2026-02-11 18:00 - Added OpenCV-DNN ONNX fallback backend for Pi inference when Ultralytics/Torch is unavailable; supports YOLOv8 ONNX parsing + NMS in detector worker.
    2026-02-11 17:20 - Implemented Pi-side vision detector worker: pulls frames from `8001`, runs YOLO every `interval_n`, and publishes live target/health metrics into `/vision/state`.
    2026-02-11 16:57 - Renamed runtime service entry from `Demo_IMU_server.py` to `color_viewer_server.py` to match Pi-hosted production role and reduce demo/prod confusion.
    2026-02-11 14:57 - Added `/vision/state` API and runtime `yolo_enabled`/`tracking_enabled` toggles with read-only target schema stub for D-Phase-A integration.
    2026-02-11 14:55 - Switched auto-degrade loop to conservative mode: only increase YOLO interval `N` when stream FPS drops below target; no automatic decrease.
    2026-02-11 14:40 - Added `/vision/metrics` runtime heartbeat + KPI evaluator; auto-throttles YOLO interval `N` against configurable min-stream-FPS target when auto-degrade is enabled.
    2026-02-11 14:40 - Added runtime vision tuning API (`GET/POST /vision/config`) with validated knobs (`imgsz`, `interval_n`, `min_stream_fps`, `auto_degrade`) and persisted config for Pi service use.
    2026-02-11 12:57 - Auto-stop active Demo mode when `/cmd` receives stop-class safety commands (`CMD_RELAX`, `CMD_MOVE_STOP`, `CMD_STOP_PWM`).
    2026-02-11 12:17 - Fixed default `Action.py` path resolution across both local prototype (`Client/tools/imu_viewer`) and Pi deployment (`Server/color_viewer`).
    2026-02-11 12:13 - Added `/demo` API with process manager for one-shot `Server/Action.py` demos (start/stop/status) used by color UI Demo button.
    2026-02-11 10:14 - Set default SFU host to Pi (`192.168.0.32`) so `/color` prototype uses current Pi WebRTC/SFU path by default.
    2026-02-08 15:43 - Added explicit /webrtc_view.html route to serve Safari WHEP viewer from realtime_webrtc monitor folder.
    2026-02-07 17:58 - Auto-disable local H264 pull when WebRTC URL is configured (unless explicitly re-enabled).
    2026-02-07 17:38 - Added DEFAULT_* runtime config so plain launch auto-uses PI/SFU settings.
    2026-02-07 17:28 - Added copy-paste short alias usage for WebRTC-first startup.
    2026-02-07 17:07 - Startup log now reports effective video preference order including WebRTC URL.
    2026-02-07 17:04 - WebRTC readiness now probes WHEP endpoint via HTTP OPTIONS.
    2026-02-07 16:38 - Added WebRTC/SFU-first status path (with HLS/MJPEG fallback order).
    2026-02-07 16:24 - Switched H264->HLS ffmpeg path to robust re-encode pipeline for legacy Pi stream stability.
    2026-02-07 16:20 - Tightened HLS readiness check to reject ended/zero-duration playlists.
    2026-02-07 16:16 - Auto-select Pi H264 source command: use raspivid on legacy stack, libcamera-vid otherwise.
    2026-02-07 15:16 - Kept MJPEG disconnect errors from polluting H264 status error field.
    2026-02-07 15:14 - Added MJPEG FPS reporting and top-left telemetry FPS overlay support.
    2026-02-07 15:01 - Expanded header Usage with complete start/open/verify/stop steps.
    2026-02-07 14:56 - Added header Usage section with H.264 and MJPEG run examples.
    2026-02-07 14:52 - Added explicit stream method metadata for Live View overlay labeling.
    2026-02-07 14:46 - Added H264(HLS)-preferred video pipeline with automatic MJPEG fallback.
    2026-02-07 13:39 - Added live telemetry polling for power/range via /telemetry.
    2026-02-07 13:46 - Added line-safe socket buffering and filtered telemetry replies.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import socket
import struct
import subprocess
import threading
import time
import math
import uuid
import urllib.error
import urllib.request
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:
    cv2 = None
    np = None

try:
    from ultralytics import YOLO  # type: ignore
except Exception:
    YOLO = None

try:
    import onnxruntime as ort  # type: ignore
except Exception:
    ort = None

try:
    import tflite_runtime.interpreter as tflite  # type: ignore
except Exception:
    try:
        from tensorflow import lite as tflite  # type: ignore
    except Exception:
        tflite = None

BASE_DIR = Path(__file__).resolve().parent
PROXY_VERSION = "2026.02.12-53"
WEBRTC_VIEW_FILE = BASE_DIR.parent / "realtime_webrtc" / "monitor" / "webrtc_view.html"

# Default runtime configuration (used when no CLI overrides are provided).
# Goal: user can run only `python3 color_viewer_server.py`.
DEFAULT_PI_HOST = "192.168.0.32"
DEFAULT_PI_PORT = 5001
DEFAULT_PI_VIDEO_PORT = 8001
DEFAULT_SSH_USER = "pi"
DEFAULT_HTTP_LISTEN = "0.0.0.0"
DEFAULT_HTTP_PORT = 8080
DEFAULT_H264_WIDTH = 960
DEFAULT_H264_HEIGHT = 540
DEFAULT_H264_FPS = 20
DEFAULT_SFU_HOST = "192.168.0.32"
DEFAULT_STREAM_PATH = "robotdog"
DEFAULT_WEBRTC_URL = f"http://{DEFAULT_SFU_HOST}:8889/{DEFAULT_STREAM_PATH}/whep"
DEFAULT_VISION_CONFIG_FILE = BASE_DIR / "vision_runtime_config.json"
DEFAULT_VIDEO_CONFIG_FILE = BASE_DIR / "video_runtime_config.json"
DEFAULT_PUBLISHER_PROFILE_ENV_FILE = BASE_DIR / "video_publisher_profile.env"
DEFAULT_PUBLISHER_SERVICE = os.getenv("ROBOT_PUBLISHER_SERVICE", "robot-publisher.service")
VIDEO_PROFILE_MAP: dict[str, tuple[int, int]] = {
    "1280x720": (1280, 720),
    "960x540": (960, 540),
    "640x360": (640, 360),
}
BATTERY_RAIL_MIN_V = 5.5
BATTERY_RAIL_MAX_V = 8.5
BATTERY_REF_V = 7.0
BATTERY_WARN_V = float(os.getenv("ROBOT_LOW_BATT_WARN_V", "6.4") or 6.4)
BATTERY_HISTORY_WINDOW_MIN = 60.0
LOW_BATT_ASSERT_SAMPLES = 2
LOW_BATT_CLEAR_SAMPLES = 2


def _resolve_default_yolo_model() -> str:
    candidates = [
        BASE_DIR.parent.parent / "runs" / "detect" / "train5" / "weights" / "best.onnx",
        BASE_DIR.parent.parent / "runs" / "detect" / "train5" / "weights" / "best_cv451.onnx",
        BASE_DIR.parent.parent / "runs" / "detect" / "train5" / "weights" / "best.pt",
        BASE_DIR.parent.parent / "yolov8n.onnx",
        BASE_DIR.parent.parent / "yolov8n_cv451.onnx",
        BASE_DIR.parent.parent / "yolov8n.pt",
        BASE_DIR.parent.parent / "yolov8n.tflite",
        BASE_DIR.parent.parent / "runs" / "detect" / "train5" / "weights" / "best.tflite",
        BASE_DIR.parent.parent / "yolo11n.onnx",
        BASE_DIR.parent.parent / "yolo11n.pt",
        BASE_DIR / "models" / "best.onnx",
        BASE_DIR / "models" / "best_cv451.onnx",
        BASE_DIR / "models" / "best.pt",
        BASE_DIR / "models" / "yolov8n_cv451.onnx",
        BASE_DIR / "models" / "yolov8n.tflite",
        BASE_DIR / "models" / "best.tflite",
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return str(candidates[0])


def _resolve_default_action_script() -> Path:
    candidates = [
        BASE_DIR.parent / "Action.py",  # Pi deployment: /Code/Server/color_viewer -> /Code/Server/Action.py
        BASE_DIR.parents[2] / "Server" / "Action.py",  # Local prototype: /Code/Client/tools/imu_viewer -> /Code/Server/Action.py
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


DEFAULT_ACTION_SCRIPT = _resolve_default_action_script()


def _now_iso():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


class ImuClient:
    def __init__(self, host: str, port: int, timeout: float = 1.0, verbose: bool = False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verbose = verbose
        self._lock = threading.Lock()
        self._sock: socket.socket | None = None
        self._recv_buf = b""
        self.last_ok_ts = 0.0
        self.last_err = ""

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] {msg}")

    def _connect(self):
        self._close()
        self._log(f"Connecting to IMU server {self.host}:{self.port}")
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        self._sock = s

    def _close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._recv_buf = b""

    def _recv_line(self, max_bytes: int = 2048) -> str:
        if self._sock is None:
            raise RuntimeError("socket not connected")
        data = self._recv_buf
        self._recv_buf = b""
        deadline = time.time() + self.timeout
        while time.time() < deadline and len(data) < max_bytes:
            if b"\n" in data:
                break
            chunk = self._sock.recv(1024)
            if not chunk:
                break
            data += chunk
        if not data or b"\n" not in data:
            raise RuntimeError("no data received")
        line_raw, remainder = data.split(b"\n", 1)
        self._recv_buf = remainder
        line = line_raw.decode("utf-8", errors="ignore").strip()
        return line

    @staticmethod
    def _parse_attitude(line: str) -> dict | None:
        if not line.startswith("CMD_ATTITUDE"):
            return None
        parts = line.split("#")
        out = {}
        for p in parts[1:]:
            if ":" not in p:
                continue
            k, v = p.split(":", 1)
            k = k.strip().lower()
            try:
                out[k] = float(v)
            except ValueError:
                continue
        if not {"roll", "pitch", "yaw"}.issubset(out.keys()):
            return None
        return out

    def exchange(self, cmd: str) -> str:
        with self._lock:
            try:
                if self._sock is None:
                    self._connect()
                self._sock.sendall(cmd.encode("utf-8"))
                return self._recv_line()
            except Exception:
                self._close()
                raise

    def send_only(self, cmd: str) -> None:
        with self._lock:
            try:
                if self._sock is None:
                    self._connect()
                self._sock.sendall(cmd.encode("utf-8"))
            except Exception:
                self._close()
                raise

    def exchange_expected(self, cmd: str, accept_fn, max_lines: int = 5) -> str:
        with self._lock:
            try:
                if self._sock is None:
                    self._connect()
                self._sock.sendall(cmd.encode("utf-8"))
                last_line = ""
                for _ in range(max_lines):
                    line = self._recv_line()
                    last_line = line
                    if accept_fn(line):
                        return line
                raise RuntimeError(f"unexpected reply: {last_line}")
            except Exception:
                self._close()
                raise

    def query(self) -> dict | None:
        try:
            line = self.exchange_expected(
                "CMD_ATTITUDE\n",
                lambda ln: "ATTITUDE" in ln.upper(),
            )
            parsed = self._parse_attitude(line)
            if not parsed:
                raise RuntimeError(f"unexpected reply: {line}")
            self.last_ok_ts = time.time()
            self.last_err = ""
            return parsed
        except Exception as e:
            self.last_err = str(e)
            self._log(f"IMU query failed: {e}")
            return None


def _first_float(text: str) -> float | None:
    for token in text.replace("#", " ").replace(":", " ").split():
        try:
            return float(token)
        except ValueError:
            continue
    return None


def _parse_power(line: str) -> float | None:
    upper = line.upper()
    if any(k in upper for k in ("POWER", "BAT", "VOLT")):
        return _first_float(line)
    return None


def _parse_distance(line: str) -> float | None:
    upper = line.upper()
    if any(k in upper for k in ("SONIC", "DIST", "RANGE", "ULTRASONIC")):
        return _first_float(line)
    return None


def _system_power_up_ts() -> float:
    # Prefer kernel boot timestamp (power-up proxy) from /proc/stat.
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("btime "):
                    val = float(line.split()[1])
                    if val > 0:
                        return val
    except Exception:
        pass
    # Fallback: now - uptime from /proc/uptime.
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            up = float((f.read().strip().split() or ["0"])[0])
            if up >= 0:
                return max(0.0, time.time() - up)
    except Exception:
        pass
    return 0.0


class TelemetryPoller(threading.Thread):
    def __init__(self, imu_client: ImuClient, interval_s: float = 1.0):
        super().__init__(daemon=True)
        self.imu_client = imu_client
        self.interval_s = max(0.3, float(interval_s))
        self.battery_v: float | None = None
        self.distance_cm: float | None = None
        self.last_ok_ts = 0.0
        self.last_err = ""
        self._lock = threading.Lock()
        self._history = deque(maxlen=5000)
        self._history_start_ts = _system_power_up_ts()
        self._low_batt_active = False
        self._low_batt_since_ts = 0.0
        self._low_batt_streak = 0
        self._recover_streak = 0
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            self._poll_once()
            end = time.time() + self.interval_s
            while time.time() < end:
                if self._stop_event.is_set():
                    return
                time.sleep(0.05)

    def _poll_once(self):
        try:
            line = self.imu_client.exchange_expected(
                "CMD_POWER\n",
                lambda ln: any(k in ln.upper() for k in ("POWER", "BAT", "VOLT")),
            )
            val = _parse_power(line)
            if val is not None:
                now_ts = time.time()
                with self._lock:
                    self.battery_v = val
                    self.last_ok_ts = now_ts
                    if self._history_start_ts <= 0:
                        self._history_start_ts = now_ts
                    raw_low = float(val) <= float(BATTERY_WARN_V)
                    if raw_low:
                        self._low_batt_streak += 1
                        self._recover_streak = 0
                    else:
                        self._recover_streak += 1
                        self._low_batt_streak = 0
                    if (not self._low_batt_active) and self._low_batt_streak >= LOW_BATT_ASSERT_SAMPLES:
                        self._low_batt_active = True
                        self._low_batt_since_ts = now_ts
                    elif self._low_batt_active and self._recover_streak >= LOW_BATT_CLEAR_SAMPLES:
                        self._low_batt_active = False
                        self._low_batt_since_ts = 0.0
                    self._history.append((now_ts, float(val)))
            else:
                self.last_err = f"unexpected power reply: {line}"
        except Exception as e:
            self.last_err = str(e)

        try:
            line = self.imu_client.exchange_expected(
                "CMD_SONIC\n",
                lambda ln: any(k in ln.upper() for k in ("SONIC", "DIST", "RANGE", "ULTRASONIC")),
            )
            val = _parse_distance(line)
            if val is not None:
                with self._lock:
                    self.distance_cm = val
                    self.last_ok_ts = time.time()
            else:
                self.last_err = f"unexpected sonic reply: {line}"
        except Exception as e:
            self.last_err = str(e)

    def snapshot(self) -> dict:
        with self._lock:
            batt = self.battery_v
            now_ts = time.time()
            raw_low = bool(batt is not None and batt <= BATTERY_WARN_V)
            low_since = float(self._low_batt_since_ts or 0.0)
            low_duration = max(0.0, now_ts - low_since) if (self._low_batt_active and low_since > 0) else 0.0
            return {
                "ok": bool(self.last_ok_ts),
                "ts": now_ts,
                "battery_v": batt,
                "distance_cm": self.distance_cm,
                "last_ok_ts": self.last_ok_ts,
                "last_err": self.last_err,
                "battery_warn_v": BATTERY_WARN_V,
                "low_battery_raw": raw_low,
                "low_battery": bool(self._low_batt_active),
                "low_battery_since_ts": low_since,
                "low_battery_duration_s": low_duration,
                "low_battery_policy": f"assert>={LOW_BATT_ASSERT_SAMPLES} clear>={LOW_BATT_CLEAR_SAMPLES}",
            }

    def snapshot_power_history(self) -> dict:
        now_ts = time.time()
        cutoff = now_ts - (BATTERY_HISTORY_WINDOW_MIN * 60.0)
        with self._lock:
            pts = []
            for ts, v in list(self._history):
                if ts < cutoff:
                    continue
                pts.append({"ts": ts, "battery_v": round(float(v), 3)})
            batt = self.battery_v
            start_ts = float(self._history_start_ts or 0.0)
            uptime_s = max(0.0, now_ts - start_ts) if start_ts > 0 else 0.0
            raw_low = bool(batt is not None and batt <= BATTERY_WARN_V)
            low_since = float(self._low_batt_since_ts or 0.0)
            low_duration = max(0.0, now_ts - low_since) if (self._low_batt_active and low_since > 0) else 0.0
            return {
                "ok": bool(self.last_ok_ts),
                "ts": now_ts,
                "window_min": BATTERY_HISTORY_WINDOW_MIN,
                "history_start_ts": start_ts,
                "uptime_s": uptime_s,
                "rail_min_v": BATTERY_RAIL_MIN_V,
                "rail_max_v": BATTERY_RAIL_MAX_V,
                "ref_v": BATTERY_REF_V,
                "warn_v": BATTERY_WARN_V,
                "low_battery_raw": raw_low,
                "low_battery": bool(self._low_batt_active),
                "low_battery_since_ts": low_since,
                "low_battery_duration_s": low_duration,
                "low_battery_policy": f"assert>={LOW_BATT_ASSERT_SAMPLES} clear>={LOW_BATT_CLEAR_SAMPLES}",
                "current_battery_v": batt,
                "points": pts,
            }


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("socket closed")
        data.extend(chunk)
    return bytes(data)


def _read_frame_len(sock: socket.socket) -> int:
    hdr = _recv_exact(sock, 4)
    ln = struct.unpack("<I", hdr)[0]
    if not (0 < ln <= 5_000_000):
        raise ValueError(f"invalid frame length {ln}")
    return ln


class VideoManager:
    def __init__(
        self,
        pi_host: str,
        pi_video_port: int = 8001,
        ssh_user: str = "pi",
        h264_enable: bool = True,
        h264_width: int = 960,
        h264_height: int = 540,
        h264_fps: int = 20,
        webrtc_url: str = "",
        video_config_file: Path = DEFAULT_VIDEO_CONFIG_FILE,
        publisher_profile_env_file: Path = DEFAULT_PUBLISHER_PROFILE_ENV_FILE,
        publisher_service_name: str = DEFAULT_PUBLISHER_SERVICE,
        verbose: bool = False,
    ):
        self.pi_host = pi_host
        self.pi_video_port = pi_video_port
        self.ssh_user = ssh_user
        ffmpeg_ok = bool(shutil.which("ffmpeg"))
        ssh_ok = bool(shutil.which("ssh"))
        self.h264_enable = bool(h264_enable and ffmpeg_ok and ssh_ok)
        self.h264_width = max(320, int(h264_width))
        self.h264_height = max(240, int(h264_height))
        self.h264_fps = max(5, int(h264_fps))
        self.webrtc_url = str(webrtc_url or "").strip()
        self.verbose = verbose
        self.hls_dir = BASE_DIR / ".hls"
        self.hls_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._ssh_proc: subprocess.Popen | None = None
        self._ffmpeg_proc: subprocess.Popen | None = None
        if not h264_enable:
            self.last_err = "disabled by --disable-h264"
        elif not ffmpeg_ok or not ssh_ok:
            self.last_err = "missing ffmpeg or ssh on proxy host"
        else:
            self.last_err = ""
        self.last_ok_ts = 0.0
        self.mjpeg_fps = 0.0
        self.mjpeg_last_frame_ts = 0.0
        self.webrtc_last_ok_ts = 0.0
        self.webrtc_last_err = ""
        self.video_profile = self._infer_video_profile()
        self.video_config_file = Path(video_config_file)
        self.publisher_profile_env_file = Path(publisher_profile_env_file)
        self.publisher_service_name = str(publisher_service_name or "").strip()
        self.publisher_last_apply = {
            "restart_attempted": False,
            "restart_ok": False,
            "restart_cmd": "",
            "restart_error": "",
            "env_file": str(self.publisher_profile_env_file),
        }
        self._load_video_config_from_disk()
        self._write_publisher_profile_env()

    def _infer_video_profile(self) -> str:
        for key, (w, h) in VIDEO_PROFILE_MAP.items():
            if int(self.h264_width) == int(w) and int(self.h264_height) == int(h):
                return key
        return f"{int(self.h264_width)}x{int(self.h264_height)}"

    def _load_video_config_from_disk(self):
        try:
            if not self.video_config_file.exists():
                return
            raw = json.loads(self.video_config_file.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            profile = str(raw.get("profile", "") or "").strip()
            if profile in VIDEO_PROFILE_MAP:
                w, h = VIDEO_PROFILE_MAP[profile]
                self.h264_width = int(w)
                self.h264_height = int(h)
                self.video_profile = profile
                return
            width = int(raw.get("width", self.h264_width) or self.h264_width)
            height = int(raw.get("height", self.h264_height) or self.h264_height)
            self.h264_width = max(320, width)
            self.h264_height = max(240, height)
            self.video_profile = self._infer_video_profile()
        except Exception as e:
            self._log(f"video-config load failed: {e}")

    def _save_video_config_to_disk(self):
        try:
            payload = {
                "profile": self.video_profile,
                "width": int(self.h264_width),
                "height": int(self.h264_height),
                "updated_ts": time.time(),
            }
            self.video_config_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as e:
            self._log(f"video-config save failed: {e}")

    def _write_publisher_profile_env(self):
        try:
            lines = [
                "# Auto-generated by color_viewer_server.py (/video/config)",
                f"# Updated: {_now_iso()}",
                f"WIDTH={int(self.h264_width)}",
                f"HEIGHT={int(self.h264_height)}",
                "",
            ]
            self.publisher_profile_env_file.write_text("\n".join(lines), encoding="utf-8")
        except Exception as e:
            self._log(f"publisher profile env save failed: {e}")

    def _restart_publisher_service(self) -> dict:
        out = {
            "restart_attempted": False,
            "restart_ok": False,
            "restart_cmd": "",
            "restart_error": "",
        }
        svc = str(self.publisher_service_name or "").strip()
        if not svc:
            out["restart_error"] = "publisher service not configured"
            return out
        cmds = [
            ["systemctl", "restart", svc],
            ["sudo", "-n", "systemctl", "restart", svc],
        ]
        for cmd in cmds:
            out["restart_attempted"] = True
            out["restart_cmd"] = " ".join(cmd)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8.0, check=False)
                if proc.returncode == 0:
                    out["restart_ok"] = True
                    out["restart_error"] = ""
                    return out
                err = (proc.stderr or proc.stdout or "").strip()
                out["restart_error"] = err or f"exit {proc.returncode}"
            except Exception as e:
                out["restart_error"] = str(e)
        return out

    def _apply_video_profile_to_publisher(self, *, restart_requested: bool) -> dict:
        self._write_publisher_profile_env()
        out = {
            "env_file": str(self.publisher_profile_env_file),
            "restart_attempted": False,
            "restart_ok": False,
            "restart_cmd": "",
            "restart_error": "",
            "publisher_service": self.publisher_service_name,
        }
        if restart_requested:
            out.update(self._restart_publisher_service())
        self.publisher_last_apply = dict(out)
        return out

    def get_video_config(self) -> dict:
        return {
            "profile": self.video_profile,
            "width": int(self.h264_width),
            "height": int(self.h264_height),
            "fps": int(self.h264_fps),
            "persist_file": str(self.video_config_file),
            "publisher_service": self.publisher_service_name,
            "publisher_env_file": str(self.publisher_profile_env_file),
            "publisher_apply": dict(self.publisher_last_apply),
            "profiles": [
                {"id": key, "width": int(val[0]), "height": int(val[1])}
                for key, val in VIDEO_PROFILE_MAP.items()
            ],
        }

    def update_video_config(self, payload: dict) -> dict:
        profile = str((payload or {}).get("profile", "") or "").strip()
        if not profile:
            return self.get_video_config()
        if profile not in VIDEO_PROFILE_MAP:
            raise ValueError(f"unsupported profile '{profile}'")
        width, height = VIDEO_PROFILE_MAP[profile]
        changed = (int(width) != int(self.h264_width)) or (int(height) != int(self.h264_height)) or (profile != self.video_profile)
        self.h264_width = int(width)
        self.h264_height = int(height)
        self.video_profile = profile
        self._save_video_config_to_disk()
        apply_out = self._apply_video_profile_to_publisher(restart_requested=changed)
        if changed and self.h264_enable:
            with self._lock:
                self._kill_procs()
        cfg = self.get_video_config()
        cfg["publisher_apply"] = apply_out
        return cfg

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] {msg}")

    def ensure_started(self):
        if not self.h264_enable:
            return
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._stop.clear()
                self._worker = threading.Thread(target=self._run, daemon=True)
                self._worker.start()

    def stop(self):
        self._stop.set()
        with self._lock:
            self._kill_procs()

    def _kill_procs(self):
        for p in (self._ffmpeg_proc, self._ssh_proc):
            if p is None:
                continue
            try:
                p.terminate()
            except Exception:
                pass
        for p in (self._ffmpeg_proc, self._ssh_proc):
            if p is None:
                continue
            try:
                p.wait(timeout=1.5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        self._ffmpeg_proc = None
        self._ssh_proc = None

    def _cleanup_hls(self):
        for p in self.hls_dir.glob("stream*"):
            try:
                p.unlink()
            except Exception:
                pass

    def _run(self):
        while not self._stop.is_set():
            self._cleanup_hls()
            ssh_cmd = [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=4",
                f"{self.ssh_user}@{self.pi_host}",
                (
                    "bash -lc '"
                    "CAM=\"\"; "
                    "if command -v vcgencmd >/dev/null 2>&1; then "
                    "  if vcgencmd get_camera 2>/dev/null | grep -q \"libcamera interfaces=0\"; then CAM=legacy; fi; "
                    "fi; "
                    "if [ \"$CAM\" = legacy ] && command -v raspivid >/dev/null 2>&1; then "
                    f"  exec raspivid -n -ih -t 0 -w {self.h264_width} -h {self.h264_height} -fps {self.h264_fps} -o -; "
                    "elif command -v libcamera-vid >/dev/null 2>&1; then "
                    f"  exec libcamera-vid -n --codec h264 --inline --width {self.h264_width} --height {self.h264_height} --framerate {self.h264_fps} --timeout 0 -o -; "
                    "elif command -v rpicam-vid >/dev/null 2>&1; then "
                    f"  exec rpicam-vid -n --codec h264 --inline --width {self.h264_width} --height {self.h264_height} --framerate {self.h264_fps} --timeout 0 -o -; "
                    "else "
                    "  echo \"No camera H264 command found\" >&2; exit 127; "
                    "fi'"
                ),
            ]
            m3u8 = str(self.hls_dir / "stream.m3u8")
            ffmpeg_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "h264",
                "-framerate",
                str(self.h264_fps),
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-tune",
                "zerolatency",
                "-pix_fmt",
                "yuv420p",
                "-g",
                str(max(10, self.h264_fps * 2)),
                "-sc_threshold",
                "0",
                "-f",
                "hls",
                "-hls_time",
                "1",
                "-hls_list_size",
                "6",
                "-hls_flags",
                "delete_segments+append_list+independent_segments",
                m3u8,
            ]
            self._log(f"Starting H264 pipeline: {' '.join(ssh_cmd)} | {' '.join(ffmpeg_cmd)}")
            try:
                with self._lock:
                    self._ssh_proc = subprocess.Popen(
                        ssh_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self._ffmpeg_proc = subprocess.Popen(
                        ffmpeg_cmd,
                        stdin=self._ssh_proc.stdout,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )
                    if self._ssh_proc.stdout:
                        self._ssh_proc.stdout.close()
                while not self._stop.is_set():
                    time.sleep(0.5)
                    with self._lock:
                        ssh_rc = self._ssh_proc.poll() if self._ssh_proc else 1
                        ff_rc = self._ffmpeg_proc.poll() if self._ffmpeg_proc else 1
                    if ssh_rc is not None or ff_rc is not None:
                        break
                    if self.hls_ready():
                        self.last_ok_ts = time.time()
                        self.last_err = ""
            except Exception as e:
                self.last_err = str(e)
                self._log(f"H264 pipeline error: {e}")
            finally:
                err_msg = ""
                with self._lock:
                    if self._ssh_proc and self._ssh_proc.stderr:
                        try:
                            err_msg += self._ssh_proc.stderr.read().decode("utf-8", errors="ignore")[-400:]
                        except Exception:
                            pass
                    if self._ffmpeg_proc and self._ffmpeg_proc.stderr:
                        try:
                            err_msg += self._ffmpeg_proc.stderr.read().decode("utf-8", errors="ignore")[-400:]
                        except Exception:
                            pass
                    self._kill_procs()
                if err_msg.strip():
                    self.last_err = err_msg.strip()
            if not self._stop.is_set():
                time.sleep(1.0)

    def hls_ready(self) -> bool:
        m3u8 = self.hls_dir / "stream.m3u8"
        if not m3u8.exists():
            return False
        try:
            age = time.time() - m3u8.stat().st_mtime
            text = m3u8.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False
        if age >= 5.0:
            return False
        if "#EXT-X-ENDLIST" in text:
            return False
        if "#EXTINF:0.000000" in text:
            return False
        if ".ts" not in text:
            return False
        return True

    def status(self) -> dict:
        ready = self.hls_ready() if self.h264_enable else False
        self.ensure_started()
        webrtc_ready = self._check_webrtc_ready() if self.webrtc_url else False
        preferred = "webrtc" if webrtc_ready else ("h264" if ready else "mjpeg")
        return {
            "webrtc": {
                "enabled": bool(self.webrtc_url),
                "ready": webrtc_ready,
                "url": self.webrtc_url,
                "method": "WebRTC",
                "protocol": "RTP/UDP via SFU",
                "error": self.webrtc_last_err,
                "last_ok_ts": self.webrtc_last_ok_ts,
            },
            "h264": {
                "enabled": self.h264_enable,
                "ready": ready,
                "url": "/hls/stream.m3u8",
                "method": "H.264",
                "protocol": "HLS (MPEG-TS segments)",
                "error": self.last_err,
                "last_ok_ts": self.last_ok_ts,
                "width": self.h264_width,
                "height": self.h264_height,
                "fps": self.h264_fps,
                "profile": self.video_profile,
            },
            "mjpeg": {
                "enabled": True,
                "url": "/video.mjpeg",
                "method": "Proprietary MJPEG",
                "protocol": "Length-prefixed JPEG over raw TCP bridge",
                "pi_video_port": self.pi_video_port,
                "fps": self.mjpeg_fps,
                "last_frame_ts": self.mjpeg_last_frame_ts,
            },
            "preferred": preferred,
        }

    def _check_webrtc_ready(self) -> bool:
        url = self.webrtc_url
        if not url:
            return False
        try:
            req = urllib.request.Request(url, method="OPTIONS")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                _ = resp.status
            self.webrtc_last_ok_ts = time.time()
            self.webrtc_last_err = ""
            return True
        except urllib.error.HTTPError as e:
            # 204/405 are acceptable signals that endpoint exists.
            if e.code in (204, 405):
                self.webrtc_last_ok_ts = time.time()
                self.webrtc_last_err = ""
                return True
            self.webrtc_last_err = str(e)
            return False
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            self.webrtc_last_err = str(e)
            return False


class DemoManager:
    def __init__(self, action_script: Path, verbose: bool = False):
        self.action_script = Path(action_script)
        self.verbose = verbose
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._last_demo = ""
        self._last_err = ""
        self._last_start_ts = 0.0
        self._last_exit_code: int | None = None

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] demo: {msg}")

    def _refresh_state(self):
        if self._proc is None:
            return
        rc = self._proc.poll()
        if rc is None:
            return
        self._last_exit_code = rc
        self._proc = None

    def status(self) -> dict:
        with self._lock:
            self._refresh_state()
            running = self._proc is not None
            return {
                "ok": True,
                "running": running,
                "pid": self._proc.pid if self._proc else None,
                "demo": self._last_demo,
                "last_start_ts": self._last_start_ts,
                "last_exit_code": self._last_exit_code,
                "last_err": self._last_err,
                "action_script": str(self.action_script),
            }

    def start(self, demo_name: str = "helloOne") -> tuple[bool, str]:
        with self._lock:
            self._refresh_state()
            if self._proc is not None:
                return False, "demo already running"
            if not self.action_script.exists():
                return False, f"action script not found: {self.action_script}"
            demo = (demo_name or "helloOne").strip()
            cmd = ["python3", str(self.action_script), "--once", "--demo", demo]
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.action_script.parent),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=os.environ.copy(),
                )
                self._last_demo = demo
                self._last_err = ""
                self._last_start_ts = time.time()
                self._last_exit_code = None
                self._log(f"started demo '{demo}' pid={self._proc.pid}")
                return True, ""
            except Exception as e:
                self._last_err = str(e)
                self._proc = None
                return False, str(e)

    def stop(self) -> tuple[bool, str]:
        with self._lock:
            self._refresh_state()
            if self._proc is None:
                return True, "not running"
            proc = self._proc
            try:
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=5.0)
                self._last_exit_code = proc.returncode
                self._proc = None
                self._log(f"stopped demo pid={proc.pid} rc={proc.returncode}")
                return True, ""
            except Exception as e:
                self._last_err = str(e)
                try:
                    proc.kill()
                except Exception:
                    pass
                self._proc = None
                return False, str(e)


class VisionConfigManager:
    DEFAULTS = {
        "imgsz": 320,
        "interval_n": 5,
        "min_stream_fps": 20.0,
        "auto_degrade": True,
        "yolo_enabled": False,
        "tracking_enabled": False,
        "conf_threshold": 0.15,
        "iou_threshold": 0.45,
        "yolo_model_path": _resolve_default_yolo_model(),
        "target_width": 960,
        "target_height": 540,
    }

    def __init__(self, config_file: Path, verbose: bool = False):
        self.config_file = Path(config_file)
        self.verbose = verbose
        self._lock = threading.Lock()
        self._config = dict(self.DEFAULTS)
        self._load_from_disk()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] vision-config: {msg}")

    @staticmethod
    def _to_bool(v) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on", "y")
        return False

    @classmethod
    def _sanitize(cls, payload: dict, base: dict | None = None) -> dict:
        cfg = dict(cls.DEFAULTS if base is None else base)
        if "imgsz" in payload:
            try:
                imgsz = int(payload["imgsz"])
            except Exception:
                imgsz = cfg["imgsz"]
            if imgsz < 160:
                imgsz = 160
            if imgsz > 640:
                imgsz = 640
            imgsz = int(round(imgsz / 32.0) * 32)
            cfg["imgsz"] = imgsz
        if "interval_n" in payload:
            try:
                interval_n = int(payload["interval_n"])
            except Exception:
                interval_n = cfg["interval_n"]
            cfg["interval_n"] = max(1, min(30, interval_n))
        if "min_stream_fps" in payload:
            try:
                min_fps = float(payload["min_stream_fps"])
            except Exception:
                min_fps = cfg["min_stream_fps"]
            cfg["min_stream_fps"] = max(5.0, min(60.0, min_fps))
        if "auto_degrade" in payload:
            cfg["auto_degrade"] = cls._to_bool(payload["auto_degrade"])
        if "yolo_enabled" in payload:
            cfg["yolo_enabled"] = cls._to_bool(payload["yolo_enabled"])
        if "tracking_enabled" in payload:
            cfg["tracking_enabled"] = cls._to_bool(payload["tracking_enabled"])
        if "conf_threshold" in payload:
            try:
                conf = float(payload["conf_threshold"])
            except Exception:
                conf = float(cfg.get("conf_threshold", 0.15))
            cfg["conf_threshold"] = max(0.01, min(0.95, conf))
        if "iou_threshold" in payload:
            try:
                iou = float(payload["iou_threshold"])
            except Exception:
                iou = float(cfg.get("iou_threshold", 0.45))
            cfg["iou_threshold"] = max(0.1, min(0.95, iou))
        if "yolo_model_path" in payload:
            model_path = str(payload["yolo_model_path"] or "").strip()
            if model_path:
                cfg["yolo_model_path"] = model_path
        return cfg

    def _load_from_disk(self):
        try:
            if self.config_file.exists():
                raw = json.loads(self.config_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._config = self._sanitize(raw, self._config)
                    self._log(f"loaded {self.config_file}")
        except Exception as e:
            self._log(f"load failed: {e}")

    def _save_to_disk(self):
        try:
            self.config_file.write_text(json.dumps(self._config, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as e:
            self._log(f"save failed: {e}")

    def get(self) -> dict:
        with self._lock:
            return dict(self._config)

    def update(self, payload: dict) -> dict:
        with self._lock:
            self._config = self._sanitize(payload or {}, self._config)
            self._save_to_disk()
            return dict(self._config)


class VisionMetricsManager:
    def __init__(self, *, verbose: bool = False):
        self.verbose = verbose
        self._lock = threading.Lock()
        self.client_stream_fps = 0.0
        self.client_stream_mode = ""
        self.last_client_ts = 0.0
        self.last_throttle_action = "hold"
        self.last_throttle_ts = 0.0
        self.throttle_count = 0
        self._last_adjust_ts = 0.0

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] vision-metrics: {msg}")

    def ingest(self, payload: dict, cfg_mgr: VisionConfigManager) -> dict:
        now = time.time()
        with self._lock:
            try:
                fps = float(payload.get("stream_fps", 0.0) or 0.0)
            except Exception:
                fps = 0.0
            mode = str(payload.get("stream_mode", "") or "").strip()
            self.client_stream_fps = max(0.0, fps)
            self.client_stream_mode = mode
            self.last_client_ts = now

            cfg = cfg_mgr.get()
            min_fps = float(cfg.get("min_stream_fps", 20.0) or 20.0)
            interval_n = int(cfg.get("interval_n", 5) or 5)
            auto_degrade = bool(cfg.get("auto_degrade", True))
            action = "hold"
            new_interval = interval_n

            # Throttle updates with cooldown to prevent noisy oscillation.
            cooldown_s = 8.0
            can_adjust = (now - self._last_adjust_ts) >= cooldown_s
            if auto_degrade and can_adjust and self.client_stream_fps > 0:
                if self.client_stream_fps < min_fps and interval_n < 30:
                    new_interval = interval_n + 1
                    action = f"increase_n->{new_interval}"
                else:
                    # Conservative policy: prioritize stream stability over YOLO aggressiveness.
                    # Automatic relaxation (decrease N) is intentionally disabled.
                    action = "hold_conservative"

            if new_interval != interval_n:
                cfg = cfg_mgr.update({"interval_n": new_interval})
                self._last_adjust_ts = now
                self.last_throttle_action = action
                self.last_throttle_ts = now
                self.throttle_count += 1
                self._log(f"auto-adjust {action} (fps={self.client_stream_fps:.1f}, min={min_fps:.1f})")

            return dict(cfg)

    def snapshot(self, cfg_mgr: VisionConfigManager, video_mgr: VideoManager) -> dict:
        now = time.time()
        cfg = cfg_mgr.get()
        try:
            vstat = video_mgr.status()
        except Exception:
            vstat = {"preferred": "unknown", "mjpeg": {"fps": 0.0}}
        with self._lock:
            min_fps = float(cfg.get("min_stream_fps", 20.0) or 20.0)
            kpi_status = "unknown"
            if self.client_stream_fps > 0:
                if self.client_stream_fps >= min_fps:
                    kpi_status = "PASS"
                elif self.client_stream_fps >= (min_fps - 2.0):
                    kpi_status = "WARN"
                else:
                    kpi_status = "FAIL"
            return {
                "client_stream_fps": self.client_stream_fps,
                "client_stream_mode": self.client_stream_mode,
                "client_metric_age_s": (now - self.last_client_ts) if self.last_client_ts else None,
                "min_stream_fps": min_fps,
                "kpi_status": kpi_status,
                "imgsz": int(cfg.get("imgsz", 320) or 320),
                "interval_n": int(cfg.get("interval_n", 5) or 5),
                "auto_degrade": bool(cfg.get("auto_degrade", True)),
                "yolo_enabled": bool(cfg.get("yolo_enabled", False)),
                "tracking_enabled": bool(cfg.get("tracking_enabled", False)),
                "last_throttle_action": self.last_throttle_action,
                "last_throttle_ts": self.last_throttle_ts,
                "throttle_count": self.throttle_count,
                "server_preferred_stream": vstat.get("preferred"),
                "server_mjpeg_fps": ((vstat.get("mjpeg") or {}).get("fps")),
            }


class VisionStateManager:
    def __init__(self, *, verbose: bool = False):
        self.verbose = verbose
        self._lock = threading.Lock()
        self.target = None
        self.note = "no_target"
        self.last_update_ts = 0.0
        self.det_fps = 0.0
        self.track_fps = 0.0
        self.infer_ms = 0.0
        self.last_error = ""
        self.health = "idle"
        self.model_path = ""
        self.model_backend = ""
        self.worker_last_ts = 0.0

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] vision-state: {msg}")

    def update_target(self, payload: dict):
        with self._lock:
            if bool(payload.get("clear_target", False)):
                self.target = None
                self.note = "cleared"
                self.last_update_ts = time.time()
                self._log("target cleared")
                return
            tgt = payload.get("target")
            if isinstance(tgt, dict):
                bbox = tgt.get("bbox", [0, 0, 0, 0])
                if not isinstance(bbox, list):
                    bbox = [0, 0, 0, 0]
                self.target = {
                    "id": str(tgt.get("id", "t0")),
                    "class": str(tgt.get("class", "unknown")),
                    "conf": float(tgt.get("conf", 0.0) or 0.0),
                    "bbox": list(bbox)[:4],
                    "age_ms": int(tgt.get("age_ms", 0) or 0),
                    "is_locked": bool(tgt.get("is_locked", False)),
                    "is_stale": bool(tgt.get("is_stale", False)),
                    "source": str(tgt.get("source", "detector")),
                    "miss_count": int(tgt.get("miss_count", 0) or 0),
                }
                self.note = str(payload.get("note", "target_update"))
                self.last_update_ts = time.time()
                self._log("target updated")

    def update_worker_stats(
        self,
        *,
        det_fps: float | None = None,
        track_fps: float | None = None,
        infer_ms: float | None = None,
        health: str | None = None,
        error: str | None = None,
        model_path: str | None = None,
        model_backend: str | None = None,
    ):
        with self._lock:
            if det_fps is not None:
                self.det_fps = max(0.0, float(det_fps))
            if track_fps is not None:
                self.track_fps = max(0.0, float(track_fps))
            if infer_ms is not None:
                self.infer_ms = max(0.0, float(infer_ms))
            if health is not None:
                self.health = str(health)
            if error is not None:
                self.last_error = str(error)
            if model_path is not None:
                self.model_path = str(model_path)
            if model_backend is not None:
                self.model_backend = str(model_backend)
            self.worker_last_ts = time.time()

    def snapshot(self, cfg_mgr: VisionConfigManager) -> dict:
        cfg = cfg_mgr.get()
        now = time.time()
        with self._lock:
            yolo_enabled = bool(cfg.get("yolo_enabled", False))
            tracking_enabled = bool(cfg.get("tracking_enabled", False)) and yolo_enabled
            target = self.target if isinstance(self.target, dict) else None
            target_age_ms = int((now - self.last_update_ts) * 1000) if self.last_update_ts else None
            infer_stale_ms = int(max(4000.0, (self.infer_ms * 3.0) + 800.0))
            stale = bool(yolo_enabled and target_age_ms is not None and target_age_ms > infer_stale_ms)
            state = "disabled"
            if yolo_enabled and not tracking_enabled:
                state = "detect_only"
            if yolo_enabled and tracking_enabled:
                state = "tracking"
            if yolo_enabled and target is None:
                state = "no_target"
            if yolo_enabled and stale:
                state = "stale"
            return {
                "yolo_enabled": yolo_enabled,
                "tracking_enabled": tracking_enabled,
                "state": state,
                "target_count": 1 if target else 0,
                "targets": [target] if target else [],
                "target_age_ms": target_age_ms,
                "stale_after_ms": infer_stale_ms,
                "stale": stale,
                "note": self.note,
                "last_update_ts": self.last_update_ts,
                "det_fps": self.det_fps,
                "track_fps": self.track_fps,
                "infer_ms": self.infer_ms,
                "health": self.health,
                "error": self.last_error,
                "model_path": self.model_path,
                "model_backend": self.model_backend,
                "worker_age_s": (now - self.worker_last_ts) if self.worker_last_ts else None,
            }


class VisionDetectorWorker(threading.Thread):
    def __init__(
        self,
        *,
        cfg_mgr: VisionConfigManager,
        state_mgr: VisionStateManager,
        pi_host: str,
        pi_video_port: int,
        verbose: bool = False,
    ):
        super().__init__(daemon=True)
        self.cfg_mgr = cfg_mgr
        self.state_mgr = state_mgr
        self.pi_host = pi_host
        self.pi_video_port = pi_video_port
        self.verbose = verbose
        self._stop_event = threading.Event()
        self._model = None
        self._models = []
        self._dnn_net = None
        self._ort_session = None
        self._tflite_interpreter = None
        self._tflite_input_detail = None
        self._tflite_output_details = []
        self._tflite_models = []
        self._tflite_rr_index = 0
        self._model_path = ""
        self._requested_model_path = ""
        self._backend = ""
        self._det_count = 0
        self._det_t0 = time.time()
        self._frame_count = 0
        self._frame_t0 = time.time()
        self._last_yolo_enabled = False
        self._rtsp_url = f"rtsp://{self.pi_host}:8554/{DEFAULT_STREAM_PATH}"
        self._track_last_target = None
        self._track_last_ts = 0.0
        self._track_vx = 0.0
        self._track_vy = 0.0
        self._track_miss_count = 0

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] vision-worker: {msg}")

    def stop(self):
        self._stop_event.set()

    def _tracking_reset(self) -> None:
        self._track_last_target = None
        self._track_last_ts = 0.0
        self._track_vx = 0.0
        self._track_vy = 0.0
        self._track_miss_count = 0

    @staticmethod
    def _bbox_center(bbox) -> tuple[float, float]:
        x = float(bbox[0] or 0.0)
        y = float(bbox[1] or 0.0)
        w = float(bbox[2] or 0.0)
        h = float(bbox[3] or 0.0)
        return (x + (w * 0.5), y + (h * 0.5))

    def _tracking_update_from_detection(self, target: dict, now_ts: float) -> None:
        if not isinstance(target, dict):
            return
        bbox = list(target.get("bbox", [0, 0, 0, 0]))[:4]
        prev = self._track_last_target
        prev_ts = self._track_last_ts
        if isinstance(prev, dict) and prev_ts > 0.0:
            dt = max(1e-3, now_ts - prev_ts)
            cx, cy = self._bbox_center(bbox)
            pcx, pcy = self._bbox_center(prev.get("bbox", [0, 0, 0, 0]))
            self._track_vx = (cx - pcx) / dt
            self._track_vy = (cy - pcy) / dt
        self._track_last_target = dict(target)
        self._track_last_ts = now_ts
        self._track_miss_count = 0

    def _tracking_hold_target(self, now_ts: float, infer_ms: float) -> dict | None:
        if not isinstance(self._track_last_target, dict) or self._track_last_ts <= 0.0:
            return None
        age_ms = (now_ts - self._track_last_ts) * 1000.0
        hold_ms = max(2200.0, infer_ms * 2.5 + 500.0)
        if age_ms > hold_ms or self._track_miss_count >= 3:
            return None
        prev = self._track_last_target
        bbox = list(prev.get("bbox", [0, 0, 0, 0]))[:4]
        dt = max(0.0, now_ts - self._track_last_ts)
        x = float(bbox[0]) + self._track_vx * dt
        y = float(bbox[1]) + self._track_vy * dt
        w = max(0.02, min(1.0, float(bbox[2])))
        h = max(0.02, min(1.0, float(bbox[3])))
        x = max(0.0, min(1.0 - w, x))
        y = max(0.0, min(1.0 - h, y))
        conf = max(0.2, float(prev.get("conf", 0.0)) * 0.88)
        self._track_miss_count += 1
        held = {
            "id": str(prev.get("id", "t0")),
            "class": str(prev.get("class", "MT_ball")),
            "conf": conf,
            "bbox": [x, y, w, h],
            "age_ms": int(age_ms),
            "is_locked": True,
            "is_stale": False,
            "source": "tracking_hold",
            "miss_count": int(self._track_miss_count),
        }
        self._track_last_target = dict(held)
        self._track_last_ts = now_ts
        return held

    def _load_model(self, model_path: str):
        if self._requested_model_path == model_path and (
            self._model is not None
            or self._models
            or self._dnn_net is not None
            or self._ort_session is not None
            or self._tflite_interpreter is not None
            or self._tflite_models
        ):
            return True
        model_paths = [s.strip() for s in str(model_path or "").replace(";", ",").split(",") if s.strip()]
        if not model_paths:
            self._model = None
            self._models = []
            self._dnn_net = None
            self._ort_session = None
            self._tflite_interpreter = None
            self._tflite_input_detail = None
            self._tflite_output_details = []
            self._tflite_models = []
            self._tflite_rr_index = 0
            self._model_path = ""
            self._requested_model_path = ""
            self._backend = ""
            self.state_mgr.update_worker_stats(
                health="degraded",
                error="model_not_set",
                model_path=model_path,
                model_backend="",
            )
            return False
        # Multi-model path is supported for Ultralytics backend only.
        if len(model_paths) > 1 and YOLO is not None:
            loaded = []
            missing = []
            for mp in model_paths:
                p = Path(mp)
                if not p.exists():
                    missing.append(mp)
                    continue
                try:
                    loaded.append(YOLO(str(p)))
                except Exception:
                    missing.append(mp)
            if loaded:
                self._model = loaded[0]
                self._models = loaded
                self._dnn_net = None
                self._ort_session = None
                self._model_path = ",".join(model_paths)
                self._backend = "ultralytics-multi" if len(loaded) > 1 else "ultralytics"
                err = ""
                if missing:
                    err = f"partial_model_load_missing:{'|'.join(missing)}"
                self.state_mgr.update_worker_stats(
                    health="ok",
                    error=err,
                    model_path=self._model_path,
                    model_backend=self._backend,
                )
                self._log(f"loaded {len(loaded)} ultralytics model(s): {self._model_path}")
                return True
        if len(model_paths) > 1 and tflite is not None:
            loaded_specs = []
            missing = []
            for raw_mp in model_paths:
                selected = None
                for candidate in self._expand_candidates(raw_mp):
                    if candidate.suffix.lower() != ".tflite" or not candidate.exists():
                        continue
                    spec = self._build_tflite_spec(candidate)
                    if spec is not None:
                        selected = spec
                        break
                if selected is None:
                    missing.append(raw_mp)
                else:
                    loaded_specs.append(selected)
            if loaded_specs:
                self._model = None
                self._models = []
                self._dnn_net = None
                self._ort_session = None
                self._tflite_interpreter = None
                self._tflite_input_detail = None
                self._tflite_output_details = []
                self._tflite_models = loaded_specs
                self._tflite_rr_index = 0
                self._model_path = ",".join([str(spec["path"]) for spec in loaded_specs])
                self._requested_model_path = model_path
                self._backend = "tflite-multi" if len(loaded_specs) > 1 else "tflite"
                err = ""
                if missing:
                    err = f"partial_model_load_missing:{'|'.join(missing)}"
                self.state_mgr.update_worker_stats(
                    health="ok",
                    error=err,
                    model_path=self._model_path,
                    model_backend=self._backend,
                )
                self._log(f"loaded {len(loaded_specs)} tflite model(s): {self._model_path}")
                return True

        expanded_candidates = []
        for raw_path in model_paths:
            expanded_candidates.extend(self._expand_candidates(raw_path))

        any_found = False
        last_err = "model_not_found"
        for p in expanded_candidates:
            if not p.exists():
                continue
            any_found = True
            if self._load_single_model(p):
                return True
            last_err = self.state_mgr.snapshot(self.cfg_mgr).get("error", "model_load_failed")

        if not any_found:
            last_err = f"model_not_found:{'|'.join(str(p) for p in expanded_candidates)}"
        self._model = None
        self._models = []
        self._dnn_net = None
        self._ort_session = None
        self._tflite_interpreter = None
        self._tflite_input_detail = None
        self._tflite_output_details = []
        self._tflite_models = []
        self._tflite_rr_index = 0
        self._model_path = ""
        self._requested_model_path = ""
        self._backend = ""
        self.state_mgr.update_worker_stats(
            health="degraded",
            error=last_err,
            model_path=",".join(str(p) for p in expanded_candidates),
            model_backend="",
        )
        return False

    def _expand_candidates(self, raw_path: str):
        p = Path(raw_path)
        candidates = [p]
        if p.suffix.lower() == ".pt":
            candidates.append(p.with_suffix(".onnx"))
            candidates.append(p.with_name(f"{p.stem}_cv451.onnx"))
            candidates.append(p.with_suffix(".tflite"))
            candidates.append(p.with_name(f"{p.stem}_int8.tflite"))
            candidates.append(p.with_name(f"{p.stem}_fp16.tflite"))
            candidates.append(p.with_name(f"{p.stem}_320_fp16.tflite"))
            try:
                for extra in sorted(p.parent.glob(f"{p.stem}*.tflite")):
                    candidates.append(extra)
            except Exception:
                pass
        deduped = []
        seen = set()
        for c in candidates:
            key = str(c)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)
        return deduped

    def _build_tflite_spec(self, p: Path):
        if tflite is None:
            return None
        try:
            interpreter = tflite.Interpreter(model_path=str(p), num_threads=2)
            interpreter.allocate_tensors()
            in_details = interpreter.get_input_details()
            out_details = interpreter.get_output_details()
            if not in_details or not out_details:
                raise RuntimeError("tflite_missing_io_details")
            return {
                "path": str(p),
                "interpreter": interpreter,
                "input_detail": in_details[0],
                "output_details": out_details,
            }
        except Exception:
            return None

    def _load_single_model(self, p: Path) -> bool:
        if p.suffix.lower() == ".onnx":
            if ort is not None:
                try:
                    sess_opts = ort.SessionOptions()
                    sess_opts.log_severity_level = 3
                    self._ort_session = ort.InferenceSession(str(p), sess_options=sess_opts, providers=["CPUExecutionProvider"])
                    self._dnn_net = None
                    self._model = None
                    self._models = []
                    self._tflite_interpreter = None
                    self._tflite_input_detail = None
                    self._tflite_output_details = []
                    self._tflite_models = []
                    self._tflite_rr_index = 0
                    self._model_path = str(p)
                    self._requested_model_path = str(p)
                    self._backend = "onnxruntime"
                    self.state_mgr.update_worker_stats(
                        health="ok",
                        error="",
                        model_path=self._model_path,
                        model_backend=self._backend,
                    )
                    self._log(f"loaded ONNX model via onnxruntime {self._model_path}")
                    return True
                except Exception as e:
                    self._ort_session = None
                    self.state_mgr.update_worker_stats(
                        health="degraded",
                        error=f"onnxruntime_load_failed:{e}",
                        model_path=str(p),
                        model_backend="onnxruntime",
                    )
            if cv2 is None:
                self.state_mgr.update_worker_stats(
                    health="degraded",
                    error="opencv_not_available_for_onnx",
                    model_path=str(p),
                    model_backend="onnx-dnn",
                )
                return False
            try:
                self._dnn_net = cv2.dnn.readNetFromONNX(str(p))
                self._ort_session = None
                self._model = None
                self._models = []
                self._tflite_interpreter = None
                self._tflite_input_detail = None
                self._tflite_output_details = []
                self._tflite_models = []
                self._tflite_rr_index = 0
                self._model_path = str(p)
                self._requested_model_path = str(p)
                self._backend = "onnx-dnn"
                self.state_mgr.update_worker_stats(
                    health="ok",
                    error="",
                    model_path=self._model_path,
                    model_backend=self._backend,
                )
                self._log(f"loaded ONNX model via opencv-dnn {self._model_path}")
                return True
            except Exception as e:
                self._dnn_net = None
                self._ort_session = None
                self._models = []
                self._model_path = ""
                self._requested_model_path = ""
                self._backend = ""
                self.state_mgr.update_worker_stats(
                    health="error",
                    error=f"onnx_load_failed:{e}",
                    model_path=str(p),
                    model_backend="onnx-dnn",
                )
                return False
        if p.suffix.lower() == ".tflite":
            if tflite is None:
                self.state_mgr.update_worker_stats(
                    health="degraded",
                    error="tflite_runtime_not_available",
                    model_path=str(p),
                    model_backend="tflite",
                )
                return False
            try:
                spec = self._build_tflite_spec(p)
                if spec is None:
                    raise RuntimeError("tflite_model_init_failed")
                self._tflite_interpreter = spec["interpreter"]
                self._tflite_input_detail = spec["input_detail"]
                self._tflite_output_details = spec["output_details"]
                self._tflite_models = []
                self._tflite_rr_index = 0
                self._model = None
                self._models = []
                self._dnn_net = None
                self._ort_session = None
                self._model_path = str(p)
                self._requested_model_path = str(p)
                self._backend = "tflite"
                self.state_mgr.update_worker_stats(
                    health="ok",
                    error="",
                    model_path=self._model_path,
                    model_backend=self._backend,
                )
                self._log(f"loaded TFLite model {self._model_path}")
                return True
            except Exception as e:
                self._tflite_interpreter = None
                self._tflite_input_detail = None
                self._tflite_output_details = []
                self._tflite_models = []
                self._tflite_rr_index = 0
                self.state_mgr.update_worker_stats(
                    health="error",
                    error=f"tflite_load_failed:{e}",
                    model_path=str(p),
                    model_backend="tflite",
                )
                return False

        if YOLO is None:
            self.state_mgr.update_worker_stats(
                health="degraded",
                error="ultralytics_not_available",
                model_path=str(p),
                model_backend="ultralytics",
            )
            return False
        try:
            self._model = YOLO(str(p))
            self._models = [self._model]
            self._dnn_net = None
            self._ort_session = None
            self._tflite_interpreter = None
            self._tflite_input_detail = None
            self._tflite_output_details = []
            self._tflite_models = []
            self._tflite_rr_index = 0
            self._model_path = str(p)
            self._requested_model_path = str(p)
            self._backend = "ultralytics"
            self.state_mgr.update_worker_stats(
                health="ok",
                error="",
                model_path=self._model_path,
                model_backend=self._backend,
            )
            self._log(f"loaded model {self._model_path}")
            return True
        except Exception as e:
            self._model = None
            self._models = []
            self._dnn_net = None
            self._ort_session = None
            self._tflite_interpreter = None
            self._tflite_input_detail = None
            self._tflite_output_details = []
            self._tflite_models = []
            self._tflite_rr_index = 0
            self._model_path = ""
            self._requested_model_path = ""
            self._backend = ""
            self.state_mgr.update_worker_stats(
                health="error",
                error=f"model_load_failed:{e}",
                model_path=str(p),
                model_backend="ultralytics",
            )
            return False

    def _infer_tflite_target(
        self,
        frame,
        *,
        imgsz: int,
        conf_threshold: float,
        iou_threshold: float,
        interpreter=None,
        input_detail=None,
        output_details=None,
    ) -> dict | None:
        interp = interpreter if interpreter is not None else self._tflite_interpreter
        in_detail = input_detail if input_detail is not None else self._tflite_input_detail
        out_details = output_details if output_details is not None else self._tflite_output_details
        if interp is None or in_detail is None or cv2 is None or np is None:
            return None
        frame_h, frame_w = frame.shape[:2]
        model_imgsz = imgsz
        try:
            shape = [int(v) for v in (in_detail.get("shape", []) or [])]
        except Exception:
            shape = []
        if len(shape) == 4:
            if shape[1] == 3 and shape[2] > 0 and shape[3] > 0:
                model_imgsz = int(shape[2])
            elif shape[3] == 3 and shape[1] > 0 and shape[2] > 0:
                model_imgsz = int(shape[1])
        if model_imgsz < 32:
            model_imgsz = imgsz
        resized = cv2.resize(frame, (model_imgsz, model_imgsz), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        inp = rgb.astype(np.float32) / 255.0
        shape = in_detail.get("shape", [])
        if len(shape) == 4 and int(shape[1]) == 3 and int(shape[-1]) != 3:
            inp = np.transpose(inp, (2, 0, 1))
        inp = np.expand_dims(inp, axis=0)

        dtype = in_detail.get("dtype", np.float32)
        qparams = in_detail.get("quantization", (0.0, 0))
        if dtype in (np.uint8, np.int8):
            scale = float(qparams[0] or 0.0)
            zero = float(qparams[1] or 0.0)
            if scale > 0:
                inp = (inp / scale + zero).astype(dtype)
            else:
                inp = inp.astype(dtype)
        else:
            inp = inp.astype(dtype)

        interp.set_tensor(in_detail["index"], inp)
        interp.invoke()
        outputs = []
        for od in out_details:
            out = interp.get_tensor(od["index"])
            od_dtype = od.get("dtype")
            od_q = od.get("quantization", (0.0, 0))
            if od_dtype in (np.uint8, np.int8):
                scale = float(od_q[0] or 0.0)
                zero = float(od_q[1] or 0.0)
                out = out.astype(np.float32)
                if scale > 0:
                    out = (out - zero) * scale
            outputs.append(out)
        if not outputs:
            return None
        primary = max(outputs, key=lambda a: int(np.prod(np.array(a).shape)))
        return self._parse_onnx_output(
            primary,
            frame_w=frame_w,
            frame_h=frame_h,
            imgsz=model_imgsz,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
        )

    def _read_jpeg_frame(self, sock: socket.socket) -> bytes:
        ln = _read_frame_len(sock)
        jpg = _recv_exact(sock, ln)
        if len(jpg) < 2 or jpg[0] != 0xFF or jpg[1] != 0xD8:
            raise ValueError("invalid_jpeg_header")
        return jpg

    def _decode_frame(self, jpg: bytes):
        if cv2 is None or np is None:
            return None
        arr = np.frombuffer(jpg, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame

    def _pick_best_target(self, result, frame_w: int, frame_h: int) -> dict | None:
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return None
        best = None
        best_conf = -1.0
        try:
            names = result.names if hasattr(result, "names") else {}
        except Exception:
            names = {}
        for i in range(len(boxes)):
            try:
                conf = float(boxes.conf[i].item())
                cls_id = int(boxes.cls[i].item())
                xyxy = boxes.xyxy[i].tolist()
            except Exception:
                continue
            if conf > best_conf:
                best_conf = conf
                x1, y1, x2, y2 = xyxy
                x1 = max(0.0, min(float(frame_w - 1), float(x1)))
                x2 = max(0.0, min(float(frame_w - 1), float(x2)))
                y1 = max(0.0, min(float(frame_h - 1), float(y1)))
                y2 = max(0.0, min(float(frame_h - 1), float(y2)))
                w = max(1.0, x2 - x1)
                h = max(1.0, y2 - y1)
                best = {
                    "id": "t0",
                    "class": str(names.get(cls_id, cls_id)),
                    "conf": conf,
                    "bbox": [x1 / frame_w, y1 / frame_h, w / frame_w, h / frame_h],
                    "age_ms": 0,
                    "is_locked": True,
                    "is_stale": False,
                }
        return best

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x >= 0:
            z = math.exp(-x)
            return 1.0 / (1.0 + z)
        z = math.exp(x)
        return z / (1.0 + z)

    def _infer_onnx_target(
        self,
        frame,
        *,
        imgsz: int,
        conf_threshold: float,
        iou_threshold: float,
    ) -> dict | None:
        if self._dnn_net is None or cv2 is None:
            return None
        frame_h, frame_w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0 / 255.0, (imgsz, imgsz), swapRB=True, crop=False)
        self._dnn_net.setInput(blob)
        raw = self._dnn_net.forward()
        return self._parse_onnx_output(raw, frame_w=frame_w, frame_h=frame_h, imgsz=imgsz, conf_threshold=conf_threshold, iou_threshold=iou_threshold)

    def _infer_onnxruntime_target(
        self,
        frame,
        *,
        imgsz: int,
        conf_threshold: float,
        iou_threshold: float,
    ) -> dict | None:
        if self._ort_session is None or np is None or cv2 is None:
            return None
        frame_h, frame_w = frame.shape[:2]
        resized = cv2.resize(frame, (imgsz, imgsz), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        inp = rgb.astype(np.float32) / 255.0
        inp = np.transpose(inp, (2, 0, 1))
        inp = np.expand_dims(inp, axis=0)
        input_name = self._ort_session.get_inputs()[0].name
        raw = self._ort_session.run(None, {input_name: inp})
        return self._parse_onnx_output(raw, frame_w=frame_w, frame_h=frame_h, imgsz=imgsz, conf_threshold=conf_threshold, iou_threshold=iou_threshold)

    def _parse_onnx_output(
        self,
        raw,
        *,
        frame_w: int,
        frame_h: int,
        imgsz: int,
        conf_threshold: float,
        iou_threshold: float,
    ) -> dict | None:
        if isinstance(raw, (list, tuple)):
            if not raw:
                return None
            raw = raw[0]
        arr = np.array(raw)
        if arr.ndim == 3:
            arr = arr[0]
        if arr.ndim != 2:
            return None
        # YOLOv8 ONNX commonly outputs [84, N] or [N, 84].
        if arr.shape[0] < arr.shape[1]:
            arr = arr.T
        rows = arr.shape[0]
        cols = arr.shape[1]
        if cols < 5:
            return None
        boxes = []
        scores = []
        class_ids = []
        x_scale = float(frame_w) / float(imgsz)
        y_scale = float(frame_h) / float(imgsz)
        for i in range(rows):
            row = arr[i]
            cx, cy, w, h = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            # Some exported heads emit normalized XYWH (0..1), others emit model-space pixels.
            # Detect normalized form and map into model input-space for consistent downstream scaling.
            if max(abs(cx), abs(cy), abs(w), abs(h)) <= 2.5:
                cx *= float(imgsz)
                cy *= float(imgsz)
                w *= float(imgsz)
                h *= float(imgsz)
            if cols >= 85:
                obj = float(row[4])
                cls_scores = row[5:]
                cls_id = int(np.argmax(cls_scores))
                cls_conf = float(cls_scores[cls_id])
                score = obj * cls_conf
            elif cols == 5:
                cls_id = 0
                raw_conf = float(row[4])
                score = raw_conf if 0.0 <= raw_conf <= 1.0 else self._sigmoid(raw_conf)
            else:
                cls_scores = row[4:]
                cls_id = int(np.argmax(cls_scores))
                raw_conf = float(cls_scores[cls_id])
                score = raw_conf if 0.0 <= raw_conf <= 1.0 else self._sigmoid(raw_conf)
            if score < conf_threshold:
                continue
            bw = max(1.0, w * x_scale)
            bh = max(1.0, h * y_scale)
            x1 = (cx - (w / 2.0)) * x_scale
            y1 = (cy - (h / 2.0)) * y_scale
            x1 = max(0.0, min(float(frame_w - 1), x1))
            y1 = max(0.0, min(float(frame_h - 1), y1))
            bw = max(1.0, min(float(frame_w) - x1, bw))
            bh = max(1.0, min(float(frame_h) - y1, bh))
            boxes.append([int(round(x1)), int(round(y1)), int(round(bw)), int(round(bh))])
            scores.append(float(score))
            class_ids.append(cls_id)
        if not boxes:
            return None
        idxs = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)
        if idxs is None or len(idxs) == 0:
            return None
        if hasattr(idxs, "flatten"):
            idx_list = [int(v) for v in idxs.flatten().tolist()]
        else:
            idx_list = [int(v[0]) if isinstance(v, (list, tuple)) else int(v) for v in idxs]
        best_i = max(idx_list, key=lambda ii: scores[ii])
        x1, y1, bw, bh = boxes[best_i]
        return {
            "id": "t0",
            "class": str(class_ids[best_i]),
            "conf": float(scores[best_i]),
            "bbox": [x1 / frame_w, y1 / frame_h, bw / frame_w, bh / frame_h],
            "age_ms": 0,
            "is_locked": True,
            "is_stale": False,
        }

    def _process_frame(self, frame, *, cfg: dict, backend_label: str) -> None:
        interval_n = int(cfg.get("interval_n", 5) or 5)
        imgsz = int(cfg.get("imgsz", 320) or 320)
        conf = float(cfg.get("conf_threshold", 0.15) or 0.15)
        iou = float(cfg.get("iou_threshold", 0.45) or 0.45)
        tracking_enabled = bool(cfg.get("tracking_enabled", False))

        self._frame_count += 1
        f_elapsed = max(1e-6, time.time() - self._frame_t0)
        frame_fps = self._frame_count / f_elapsed
        self.state_mgr.update_worker_stats(
            track_fps=frame_fps,
            health="ok",
            error="",
            model_backend=backend_label,
        )
        if self._frame_count % max(1, interval_n) != 0:
            return

        t0 = time.time()
        target = None
        run_backend_label = backend_label
        try:
            if self._backend == "onnxruntime":
                target = self._infer_onnxruntime_target(
                    frame,
                    imgsz=imgsz,
                    conf_threshold=conf,
                    iou_threshold=iou,
                )
            elif self._backend == "onnx-dnn":
                target = self._infer_onnx_target(
                    frame,
                    imgsz=imgsz,
                    conf_threshold=conf,
                    iou_threshold=iou,
                )
            elif self._backend in ("tflite", "tflite-multi"):
                run_backend_label = backend_label
                if self._backend == "tflite-multi" and self._tflite_models:
                    specs = list(self._tflite_models)
                    primary = []
                    fallback = []
                    for spec in specs:
                        name = Path(str(spec.get("path", ""))).name.lower()
                        if "best" in name:
                            primary.append(spec)
                        else:
                            fallback.append(spec)
                    ordered = primary + fallback if primary else specs
                    chosen = ordered[0]
                    run_backend_label = f"{backend_label}:{Path(str(chosen.get('path', 'unknown'))).name}"
                    target = self._infer_tflite_target(
                        frame,
                        imgsz=imgsz,
                        conf_threshold=conf,
                        iou_threshold=iou,
                        interpreter=chosen.get("interpreter"),
                        input_detail=chosen.get("input_detail"),
                        output_details=chosen.get("output_details"),
                    )
                    if target is None and len(ordered) > 1:
                        fb = ordered[1]
                        run_backend_label = f"{backend_label}:{Path(str(fb.get('path', 'unknown'))).name}"
                        target = self._infer_tflite_target(
                            frame,
                            imgsz=imgsz,
                            conf_threshold=conf,
                            iou_threshold=iou,
                            interpreter=fb.get("interpreter"),
                            input_detail=fb.get("input_detail"),
                            output_details=fb.get("output_details"),
                        )
                else:
                    target = self._infer_tflite_target(
                        frame,
                        imgsz=imgsz,
                        conf_threshold=conf,
                        iou_threshold=iou,
                    )
            else:
                models = self._models if self._models else ([self._model] if self._model is not None else [])
                frame_h, frame_w = frame.shape[:2]
                best = None
                for m in models:
                    results = m.predict(frame, imgsz=imgsz, conf=conf, iou=iou, verbose=False, device="cpu")
                    if not results or len(results) == 0:
                        continue
                    cand = self._pick_best_target(results[0], frame_w, frame_h)
                    if cand is None:
                        continue
                    if best is None or float(cand.get("conf", 0.0)) > float(best.get("conf", 0.0)):
                        best = cand
                target = best
        except Exception as e:
            self.state_mgr.update_worker_stats(
                health="error",
                error=f"infer_failed:{e}",
                model_backend=run_backend_label,
            )
            return

        if target:
            hint = f"{run_backend_label}|{self._model_path}".lower()
            if "best" in hint:
                target["class"] = "MT_ball"
            elif "yolov8n" in hint or "yolo11n" in hint:
                target["class"] = "Yolo_sport ball"
            target["source"] = "detector"
            target["miss_count"] = 0

        infer_ms = (time.time() - t0) * 1000.0
        now_ts = time.time()
        if target and tracking_enabled:
            target["is_locked"] = True
            self._tracking_update_from_detection(target, now_ts)
        elif not target and tracking_enabled:
            target = self._tracking_hold_target(now_ts, infer_ms)
        elif not tracking_enabled:
            self._tracking_reset()
        self._det_count += 1
        d_elapsed = max(1e-6, time.time() - self._det_t0)
        det_fps = self._det_count / d_elapsed
        if target:
            note = "detector_live"
            if str(target.get("source", "")) == "tracking_hold":
                note = "tracking_hold"
            elif tracking_enabled:
                note = "tracking_lock"
            self.state_mgr.update_target({"target": target, "note": note})
        self.state_mgr.update_worker_stats(
            det_fps=det_fps,
            infer_ms=infer_ms,
            health="ok",
            error="",
            model_path=self._model_path,
            model_backend=run_backend_label,
        )

    def run(self):
        if cv2 is None or np is None:
            self.state_mgr.update_worker_stats(
                health="degraded",
                error="opencv_or_numpy_not_available",
                model_backend="",
            )
            return
        while not self._stop_event.is_set():
            cfg = self.cfg_mgr.get()
            yolo_enabled = bool(cfg.get("yolo_enabled", False))
            if not yolo_enabled:
                if self._last_yolo_enabled:
                    self.state_mgr.update_target({"clear_target": True, "note": "worker_yolo_disabled"})
                self._tracking_reset()
                self.state_mgr.update_worker_stats(
                    health="idle",
                    error="",
                    det_fps=0.0,
                    track_fps=0.0,
                    model_backend=self._backend,
                )
                self._last_yolo_enabled = False
                time.sleep(0.25)
                continue
            self._last_yolo_enabled = True
            model_path = str(cfg.get("yolo_model_path", "") or "")
            if not self._load_model(model_path):
                time.sleep(1.0)
                continue
            reload_required = False
            use_rtsp_fallback = False
            try:
                sock = socket.create_connection((self.pi_host, self.pi_video_port), timeout=3.0)
                sock.settimeout(3.0)
            except Exception as e:
                self.state_mgr.update_worker_stats(
                    health="degraded",
                    error=f"video_connect_failed:{e}",
                    model_backend=self._backend,
                )
                use_rtsp_fallback = True
            try:
                if not use_rtsp_fallback:
                    while not self._stop_event.is_set():
                        cfg = self.cfg_mgr.get()
                        if not bool(cfg.get("yolo_enabled", False)):
                            break
                        live_model_path = str(cfg.get("yolo_model_path", "") or "")
                        if live_model_path != self._requested_model_path:
                            reload_required = True
                            break
                        jpg = self._read_jpeg_frame(sock)
                        frame = self._decode_frame(jpg)
                        if frame is None:
                            self.state_mgr.update_worker_stats(
                                health="error",
                                error="frame_decode_failed",
                                model_backend=self._backend,
                            )
                            continue
                        self._process_frame(frame, cfg=cfg, backend_label=self._backend)
            except Exception as e:
                use_rtsp_fallback = True
                self.state_mgr.update_worker_stats(
                    health="degraded",
                    error=f"worker_stream_error:{e}",
                    model_backend=self._backend,
                )
            finally:
                try:
                    sock.close()
                except Exception:
                    pass
            if reload_required:
                time.sleep(0.05)
                continue
            if use_rtsp_fallback and not self._stop_event.is_set():
                rtsp_backend = f"{self._backend}+rtsp"
                cap = None
                fail_count = 0
                try:
                    while not self._stop_event.is_set():
                        cfg = self.cfg_mgr.get()
                        if not bool(cfg.get("yolo_enabled", False)):
                            break
                        live_model_path = str(cfg.get("yolo_model_path", "") or "")
                        if live_model_path != self._requested_model_path:
                            reload_required = True
                            break
                        if cap is None or not cap.isOpened():
                            cap = cv2.VideoCapture(self._rtsp_url)
                            try:
                                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            except Exception:
                                pass
                            if not cap.isOpened():
                                self.state_mgr.update_worker_stats(
                                    health="degraded",
                                    error=f"rtsp_open_failed:{self._rtsp_url}",
                                    model_backend=rtsp_backend,
                                )
                                time.sleep(0.5)
                                continue
                            fail_count = 0
                        ok, frame = cap.read()
                        if not ok or frame is None:
                            fail_count += 1
                            if fail_count >= 3:
                                self.state_mgr.update_worker_stats(
                                    health="degraded",
                                    error="rtsp_read_failed",
                                    model_backend=rtsp_backend,
                                )
                            if fail_count >= 12:
                                try:
                                    cap.release()
                                except Exception:
                                    pass
                                cap = None
                                fail_count = 0
                            time.sleep(0.05)
                            continue
                        fail_count = 0
                        self._process_frame(frame, cfg=cfg, backend_label=rtsp_backend)
                except Exception as e:
                    self.state_mgr.update_worker_stats(
                        health="degraded",
                        error=f"rtsp_worker_error:{e}",
                        model_backend=rtsp_backend,
                    )
                finally:
                    try:
                        cap.release()
                    except Exception:
                        pass
            if reload_required:
                time.sleep(0.05)
                continue
            time.sleep(0.3)


class ViewerPresenceManager:
    def __init__(self, *, ttl_s: float = 25.0, verbose: bool = False):
        self.ttl_s = max(10.0, float(ttl_s))
        self.verbose = verbose
        self._lock = threading.Lock()
        self._viewers = {}

    def _log(self, msg: str):
        if self.verbose:
            print(f"[{_now_iso()}] viewer-presence: {msg}")

    def _prune_locked(self, now_ts: float) -> None:
        stale_ids = [
            vid
            for vid, rec in self._viewers.items()
            if (now_ts - float(rec.get("last_seen_ts", 0.0))) > self.ttl_s
        ]
        for vid in stale_ids:
            self._viewers.pop(vid, None)

    @staticmethod
    def _safe_str(v, limit: int = 200) -> str:
        s = str(v or "").strip()
        return s[:limit]

    def ingest(self, *, client_ip: str, user_agent: str, payload: dict) -> dict:
        now_ts = time.time()
        with self._lock:
            self._prune_locked(now_ts)
            viewer_id = self._safe_str(payload.get("viewer_id"), 80)
            if not viewer_id:
                viewer_id = f"anon-{uuid.uuid4().hex[:10]}"
            rec = self._viewers.get(viewer_id) or {
                "viewer_id": viewer_id,
                "first_seen_ts": now_ts,
            }
            hints = payload.get("hints", {})
            if not isinstance(hints, dict):
                hints = {}
            rec.update(
                {
                    "viewer_id": viewer_id,
                    "client_ip": self._safe_str(client_ip, 64),
                    "device_label": self._safe_str(payload.get("device_label"), 120),
                    "user_agent": self._safe_str(payload.get("user_agent") or user_agent, 420),
                    "platform": self._safe_str(payload.get("platform"), 120),
                    "language": self._safe_str(payload.get("language"), 40),
                    "timezone": self._safe_str(payload.get("timezone"), 80),
                    "page_path": self._safe_str(payload.get("page_path"), 80),
                    "stream_mode": self._safe_str(payload.get("stream_mode"), 60),
                    "fps": float(payload.get("fps", 0.0) or 0.0),
                    "is_visible": bool(payload.get("is_visible", True)),
                    "active_recent_ms": int(payload.get("active_recent_ms", 0) or 0),
                    "screen_w": int(payload.get("screen_w", 0) or 0),
                    "screen_h": int(payload.get("screen_h", 0) or 0),
                    "viewport_w": int(payload.get("viewport_w", 0) or 0),
                    "viewport_h": int(payload.get("viewport_h", 0) or 0),
                    "dpr": float(payload.get("dpr", 1.0) or 1.0),
                    "gpu_renderer": self._safe_str(payload.get("gpu_renderer"), 180),
                    "ua_platform": self._safe_str(hints.get("platform"), 80),
                    "ua_platform_version": self._safe_str(hints.get("platformVersion"), 80),
                    "ua_model": self._safe_str(hints.get("model"), 80),
                    "ua_arch": self._safe_str(hints.get("architecture"), 40),
                    "ua_bitness": self._safe_str(hints.get("bitness"), 40),
                    "ua_full_version": self._safe_str(hints.get("uaFullVersion"), 80),
                    "last_seen_ts": now_ts,
                }
            )
            self._viewers[viewer_id] = rec
            return {
                "viewer_id": viewer_id,
                "client_ip": rec.get("client_ip", ""),
                "device_label": rec.get("device_label", ""),
                "last_seen_ts": now_ts,
            }

    def snapshot(self) -> dict:
        now_ts = time.time()
        with self._lock:
            self._prune_locked(now_ts)
            rows = sorted(
                self._viewers.values(),
                key=lambda r: float(r.get("last_seen_ts", 0.0)),
                reverse=True,
            )
            device_counts = {}
            for r in rows:
                k = str(r.get("device_label", "unknown") or "unknown")
                device_counts[k] = int(device_counts.get(k, 0)) + 1
            viewers = []
            for r in rows:
                viewers.append(
                    {
                        "viewer_id": r.get("viewer_id"),
                        "client_ip": r.get("client_ip"),
                        "device_label": r.get("device_label"),
                        "ua_model": r.get("ua_model"),
                        "ua_platform": r.get("ua_platform"),
                        "page_path": r.get("page_path"),
                        "stream_mode": r.get("stream_mode"),
                        "fps": r.get("fps"),
                        "is_visible": r.get("is_visible"),
                        "active_recent_ms": r.get("active_recent_ms"),
                        "gpu_renderer": r.get("gpu_renderer"),
                        "screen": {
                            "w": r.get("screen_w"),
                            "h": r.get("screen_h"),
                            "viewport_w": r.get("viewport_w"),
                            "viewport_h": r.get("viewport_h"),
                            "dpr": r.get("dpr"),
                        },
                        "age_s": round(max(0.0, now_ts - float(r.get("last_seen_ts", now_ts))), 2),
                        "first_seen_ts": r.get("first_seen_ts"),
                        "last_seen_ts": r.get("last_seen_ts"),
                    }
                )
            return {
                "active_count": len(viewers),
                "ttl_s": self.ttl_s,
                "device_counts": device_counts,
                "viewers": viewers,
            }


class ImuHandler(BaseHTTPRequestHandler):
    server_version = "IMUViewer/1.0"

    def _write(self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self._write(HTTPStatus.NOT_FOUND, b"Not found")
            return
        body = path.read_bytes()
        self._write(HTTPStatus.OK, body, content_type)

    def _client_ip(self) -> str:
        xff = str(self.headers.get("X-Forwarded-For", "") or "").strip()
        if xff:
            return xff.split(",", 1)[0].strip()
        return str(self.client_address[0] or "")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if self.path == "/" or self.path == "/index.html":
            return self._serve_file(BASE_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/webrtc_view.html" or path == "/webrtc":
            return self._serve_file(WEBRTC_VIEW_FILE, "text/html; charset=utf-8")
        if path == "/simple" or path == "/index_simple.html":
            return self._serve_file(BASE_DIR / "index_simple.html", "text/html; charset=utf-8")
        if path == "/color" or path == "/index_color.html":
            return self._serve_file(BASE_DIR / "index_color.html", "text/html; charset=utf-8")
        if path == "/app.js":
            return self._serve_file(BASE_DIR / "app.js", "application/javascript; charset=utf-8")
        if path == "/app_simple.js":
            return self._serve_file(BASE_DIR / "app_simple.js", "application/javascript; charset=utf-8")
        if path == "/app_color.js":
            return self._serve_file(BASE_DIR / "app_color.js", "application/javascript; charset=utf-8")
        if path == "/live_video.js":
            return self._serve_file(BASE_DIR / "live_video.js", "application/javascript; charset=utf-8")
        if path.startswith("/assets/") or path.startswith("/vendor/"):
            rel = path.lstrip("/")
            safe = (BASE_DIR / rel).resolve()
            if not safe.is_file() or not str(safe).startswith(str(BASE_DIR)):
                return self._write(HTTPStatus.NOT_FOUND, b"Not found")
            ext = safe.suffix.lower()
            content_types = {
                ".obj": "text/plain; charset=utf-8",
                ".mtl": "text/plain; charset=utf-8",
                ".txt": "text/plain; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
            }
            return self._serve_file(safe, content_types.get(ext, "application/octet-stream"))
        if path.startswith("/hls/"):
            rel = path[len("/hls/") :]
            safe = (self.server.video_manager.hls_dir / rel).resolve()  # type: ignore[attr-defined]
            base = self.server.video_manager.hls_dir.resolve()  # type: ignore[attr-defined]
            if not safe.is_file() or not str(safe).startswith(str(base)):
                return self._write(HTTPStatus.NOT_FOUND, b"Not found")
            ext = safe.suffix.lower()
            content_type = "application/vnd.apple.mpegurl"
            if ext == ".ts":
                content_type = "video/mp2t"
            return self._serve_file(safe, f"{content_type}; charset=utf-8")
        if path == "/video/status":
            payload = self.server.video_manager.status()  # type: ignore[attr-defined]
            payload["ts"] = time.time()
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if path == "/video/config":
            payload = {"ok": True, "ts": time.time(), "config": self.server.video_manager.get_video_config()}  # type: ignore[attr-defined]
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if path == "/video.mjpeg":
            return self._stream_mjpeg()
        if path.startswith("/imu"):
            imu = self.server.imu_client.query()  # type: ignore[attr-defined]
            payload = {
                "ok": imu is not None,
                "ts": time.time(),
                "roll": (imu or {}).get("roll"),
                "pitch": (imu or {}).get("pitch"),
                "yaw": (imu or {}).get("yaw"),
                "error": self.server.imu_client.last_err,  # type: ignore[attr-defined]
                "last_ok_ts": self.server.imu_client.last_ok_ts,  # type: ignore[attr-defined]
            }
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/diag"):
            imu_client = self.server.imu_client  # type: ignore[attr-defined]
            vm = self.server.video_manager  # type: ignore[attr-defined]
            request_host = str(self.headers.get("Host", "") or "").strip().split(":", 1)[0].strip()
            webrtc_host = ""
            webrtc_port = 8889
            try:
                parsed_whep = urlparse(str(vm.webrtc_url or ""))
                webrtc_host = str(parsed_whep.hostname or "")
                if parsed_whep.port:
                    webrtc_port = int(parsed_whep.port)
            except Exception:
                webrtc_host = ""
                webrtc_port = 8889
            display_host = str(imu_client.host or "")
            if display_host in ("127.0.0.1", "localhost", "::1", "0.0.0.0", ""):
                if request_host and request_host not in ("127.0.0.1", "localhost", "::1"):
                    display_host = request_host
                elif webrtc_host:
                    display_host = webrtc_host
                else:
                    display_host = imu_client.host
            viewer_port = int(os.getenv("ROBOT_VIEWER_STATIC_PORT", "8080") or 8080)
            telemetry_port = int(os.getenv("ROBOT_TELEMETRY_PORT", "8090") or 8090)
            ports_summary = (
                f"5001 ctrl+IMU | 8001 MJPEG | {viewer_port} WebRTC page | "
                f"{self.server.server_port} color UI | {telemetry_port} telemetry | "
                f"8554 RTSP | {webrtc_port} WHEP"
            )
            payload = {
                "ok": bool(imu_client.last_ok_ts),
                "ts": time.time(),
                "pi_host": imu_client.host,
                "pi_port": imu_client.port,
                "control_display_host": display_host,
                "control_display_port": imu_client.port,
                "ports_summary": ports_summary,
                "last_ok_ts": imu_client.last_ok_ts,
                "last_err": imu_client.last_err,
            }
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/version"):
            payload = {
                "version": PROXY_VERSION,
                "ts": time.time(),
            }
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/telemetry/power_history"):
            telem = self.server.telemetry_poller  # type: ignore[attr-defined]
            payload = telem.snapshot_power_history()
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/telemetry"):
            telem = self.server.telemetry_poller  # type: ignore[attr-defined]
            payload = telem.snapshot()
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/viewer/summary"):
            mgr = self.server.viewer_presence_manager  # type: ignore[attr-defined]
            payload = {"ok": True, "ts": time.time(), "summary": mgr.snapshot()}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/vision/config"):
            cfg = self.server.vision_config_manager.get()  # type: ignore[attr-defined]
            payload = {"ok": True, "ts": time.time(), "config": cfg}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/vision/metrics"):
            metrics = self.server.vision_metrics_manager.snapshot(  # type: ignore[attr-defined]
                self.server.vision_config_manager,  # type: ignore[attr-defined]
                self.server.video_manager,  # type: ignore[attr-defined]
            )
            payload = {"ok": True, "ts": time.time(), "metrics": metrics}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/vision/state"):
            state = self.server.vision_state_manager.snapshot(self.server.vision_config_manager)  # type: ignore[attr-defined]
            payload = {"ok": True, "ts": time.time(), "state": state}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/demo/status"):
            payload = self.server.demo_manager.status()  # type: ignore[attr-defined]
            payload["ts"] = time.time()
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")

        self._write(HTTPStatus.NOT_FOUND, b"Not found")

    def _stream_mjpeg(self):
        vm = self.server.video_manager  # type: ignore[attr-defined]
        boundary = "frame"
        self.send_response(HTTPStatus.OK)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary}")
        self.end_headers()

        s: socket.socket | None = None
        frame_count = 0
        fps_t0 = time.time()
        try:
            s = socket.create_connection((vm.pi_host, vm.pi_video_port), timeout=4.0)
            s.settimeout(8.0)
            while True:
                ln = _read_frame_len(s)
                jpg = _recv_exact(s, ln)
                if len(jpg) < 2 or jpg[0] != 0xFF or jpg[1] != 0xD8:
                    continue
                frame_count += 1
                now = time.time()
                vm.mjpeg_last_frame_ts = now
                elapsed = now - fps_t0
                if elapsed >= 1.0:
                    vm.mjpeg_fps = frame_count / elapsed
                    frame_count = 0
                    fps_t0 = now
                part = (
                    f"--{boundary}\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpg)}\r\n\r\n"
                ).encode("ascii")
                self.wfile.write(part)
                self.wfile.write(jpg)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            vm.mjpeg_fps = 0.0
            return
        except Exception as e:
            vm.mjpeg_fps = 0.0
            return
        finally:
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass

    def do_POST(self):
        if self.path.startswith("/viewer/heartbeat"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            if not isinstance(data, dict):
                data = {}
            mgr = self.server.viewer_presence_manager  # type: ignore[attr-defined]
            ack = mgr.ingest(
                client_ip=self._client_ip(),
                user_agent=str(self.headers.get("User-Agent", "") or ""),
                payload=data,
            )
            payload = {"ok": True, "ts": time.time(), "ack": ack}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/vision/state"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            action = str(data.get("action", "") or "").strip().lower()
            updates = {}
            if action == "toggle_yolo":
                cfg0 = self.server.vision_config_manager.get()  # type: ignore[attr-defined]
                yolo_now = bool(cfg0.get("yolo_enabled", False))
                next_yolo = not yolo_now
                updates["yolo_enabled"] = next_yolo
                if not next_yolo:
                    updates["tracking_enabled"] = False
                    self.server.vision_state_manager.update_target({"clear_target": True, "note": "yolo_off"})  # type: ignore[attr-defined]
            elif action == "toggle_tracking":
                cfg0 = self.server.vision_config_manager.get()  # type: ignore[attr-defined]
                tracking_now = bool(cfg0.get("tracking_enabled", False))
                updates["tracking_enabled"] = not tracking_now
                if not bool(cfg0.get("yolo_enabled", False)):
                    updates["yolo_enabled"] = True
            elif action == "target_update":
                self.server.vision_state_manager.update_target(data)  # type: ignore[attr-defined]
            elif action == "clear_target":
                self.server.vision_state_manager.update_target({"clear_target": True, "note": "api_clear"})  # type: ignore[attr-defined]
            if updates:
                self.server.vision_config_manager.update(updates)  # type: ignore[attr-defined]
            state = self.server.vision_state_manager.snapshot(self.server.vision_config_manager)  # type: ignore[attr-defined]
            payload = {"ok": True, "ts": time.time(), "state": state}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/vision/metrics"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            self.server.vision_metrics_manager.ingest(data, self.server.vision_config_manager)  # type: ignore[attr-defined]
            metrics = self.server.vision_metrics_manager.snapshot(  # type: ignore[attr-defined]
                self.server.vision_config_manager,  # type: ignore[attr-defined]
                self.server.video_manager,  # type: ignore[attr-defined]
            )
            payload = {"ok": True, "ts": time.time(), "metrics": metrics}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/vision/config"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            try:
                cfg = self.server.vision_config_manager.update(data)  # type: ignore[attr-defined]
                payload = {"ok": True, "ts": time.time(), "config": cfg}
            except Exception as e:
                payload = {"ok": False, "ts": time.time(), "error": str(e)}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/video/config"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            try:
                cfg = self.server.video_manager.update_video_config(data)  # type: ignore[attr-defined]
                payload = {"ok": True, "ts": time.time(), "config": cfg}
            except Exception as e:
                payload = {"ok": False, "ts": time.time(), "error": str(e)}
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/cmd"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            cmd = str(data.get("cmd", "") or data.get("payload", "") or "").strip()
            if not cmd.startswith("CMD_"):
                return self._write(HTTPStatus.BAD_REQUEST, b"invalid cmd")
            # Safety policy: stop/relax class commands immediately terminate active demo mode.
            cmd_upper = cmd.upper()
            if cmd_upper.startswith("CMD_RELAX") or cmd_upper.startswith("CMD_MOVE_STOP") or cmd_upper.startswith("CMD_STOP_PWM"):
                self.server.demo_manager.stop()  # type: ignore[attr-defined]
            if not cmd.endswith("\n"):
                cmd = cmd + "\n"
            try:
                self.server.imu_client.send_only(cmd)  # type: ignore[attr-defined]
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
            body = json.dumps({"ok": True}).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        if self.path.startswith("/demo"):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except Exception:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                data = {}
            action = str(data.get("action", "status")).strip().lower()
            demo_name = str(data.get("demo", "helloOne")).strip() or "helloOne"
            mgr = self.server.demo_manager  # type: ignore[attr-defined]
            if action == "start":
                ok, err = mgr.start(demo_name)
                payload = mgr.status()
                payload.update({"ok": ok, "error": err})
                body = json.dumps(payload).encode("utf-8")
                return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
            if action == "stop":
                ok, err = mgr.stop()
                payload = mgr.status()
                payload.update({"ok": ok, "error": err})
                body = json.dumps(payload).encode("utf-8")
                return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
            payload = mgr.status()
            payload.update({"ok": True, "error": ""})
            body = json.dumps(payload).encode("utf-8")
            return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
        self._write(HTTPStatus.NOT_FOUND, b"Not found")

    def log_message(self, fmt, *args):
        # Silence default HTTP logs; enable with --verbose.
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description="IMU viewer HTTP proxy")
    parser.add_argument("--pi-host", default=DEFAULT_PI_HOST, help=f"Pi IP/hostname (default: {DEFAULT_PI_HOST})")
    parser.add_argument("--pi-port", type=int, default=DEFAULT_PI_PORT, help=f"Pi control port (default: {DEFAULT_PI_PORT})")
    parser.add_argument(
        "--pi-video-port",
        type=int,
        default=DEFAULT_PI_VIDEO_PORT,
        help=f"Pi video port (MJPEG TCP, default: {DEFAULT_PI_VIDEO_PORT})",
    )
    parser.add_argument("--ssh-user", default=DEFAULT_SSH_USER, help=f"SSH username for Pi H264 pull (default: {DEFAULT_SSH_USER})")
    parser.add_argument("--disable-h264", action="store_true", help="Disable H264 HLS path")
    parser.add_argument(
        "--enable-h264-fallback",
        action="store_true",
        help="When --webrtc-url is set, keep H264 pull fallback enabled (may contend for Pi camera)",
    )
    parser.add_argument("--h264-width", type=int, default=DEFAULT_H264_WIDTH, help=f"H264 width for libcamera-vid (default: {DEFAULT_H264_WIDTH})")
    parser.add_argument(
        "--h264-height",
        type=int,
        default=DEFAULT_H264_HEIGHT,
        help=f"H264 height for libcamera-vid (default: {DEFAULT_H264_HEIGHT})",
    )
    parser.add_argument("--h264-fps", type=int, default=DEFAULT_H264_FPS, help=f"H264 FPS for libcamera-vid (default: {DEFAULT_H264_FPS})")
    parser.add_argument(
        "--webrtc-url",
        default=DEFAULT_WEBRTC_URL,
        help=f"SFU WebRTC player URL (default: {DEFAULT_WEBRTC_URL})",
    )
    parser.add_argument(
        "--video-config-file",
        default=str(DEFAULT_VIDEO_CONFIG_FILE),
        help=f"Persisted /video/config file path (default: {DEFAULT_VIDEO_CONFIG_FILE})",
    )
    parser.add_argument(
        "--publisher-profile-env-file",
        default=str(DEFAULT_PUBLISHER_PROFILE_ENV_FILE),
        help=f"Publisher width/height env override file (default: {DEFAULT_PUBLISHER_PROFILE_ENV_FILE})",
    )
    parser.add_argument(
        "--publisher-service",
        default=DEFAULT_PUBLISHER_SERVICE,
        help=f"Publisher service name to restart after /video/config apply (default: {DEFAULT_PUBLISHER_SERVICE})",
    )
    parser.add_argument(
        "--action-script",
        default=str(DEFAULT_ACTION_SCRIPT),
        help=f"Server Action.py path for one-shot demo trigger (default: {DEFAULT_ACTION_SCRIPT})",
    )
    parser.add_argument("--listen", default=DEFAULT_HTTP_LISTEN, help=f"HTTP listen address (default: {DEFAULT_HTTP_LISTEN})")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT, help=f"HTTP listen port (default: {DEFAULT_HTTP_PORT})")
    parser.add_argument("--timeout", type=float, default=1.0, help="Pi TCP timeout seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    imu_client = ImuClient(args.pi_host, args.pi_port, timeout=args.timeout, verbose=args.verbose)
    telemetry_poller = TelemetryPoller(imu_client, interval_s=1.0)
    telemetry_poller.start()
    h264_enable = not args.disable_h264
    # WebRTC-first mode should not also grab the camera via SSH/H264 pull by default.
    # Keeping H264 enabled can cause ENOSPC camera contention against the Pi WebRTC publisher.
    if args.webrtc_url and not args.enable_h264_fallback:
        h264_enable = False
        if args.verbose:
            print("WebRTC URL configured; auto-disabling H264 pull (use --enable-h264-fallback to override).")

    video_manager = VideoManager(
        pi_host=args.pi_host,
        pi_video_port=args.pi_video_port,
        ssh_user=args.ssh_user,
        h264_enable=h264_enable,
        h264_width=args.h264_width,
        h264_height=args.h264_height,
        h264_fps=args.h264_fps,
        webrtc_url=args.webrtc_url,
        video_config_file=Path(args.video_config_file),
        publisher_profile_env_file=Path(args.publisher_profile_env_file),
        publisher_service_name=str(args.publisher_service),
        verbose=args.verbose,
    )
    video_manager.ensure_started()
    demo_manager = DemoManager(Path(args.action_script), verbose=args.verbose)
    vision_config_manager = VisionConfigManager(DEFAULT_VISION_CONFIG_FILE, verbose=args.verbose)
    vision_metrics_manager = VisionMetricsManager(verbose=args.verbose)
    vision_state_manager = VisionStateManager(verbose=args.verbose)
    viewer_presence_manager = ViewerPresenceManager(verbose=args.verbose)
    vision_worker = VisionDetectorWorker(
        cfg_mgr=vision_config_manager,
        state_mgr=vision_state_manager,
        pi_host=args.pi_host,
        pi_video_port=args.pi_video_port,
        verbose=args.verbose,
    )
    vision_worker.start()

    httpd = ThreadingHTTPServer((args.listen, args.http_port), ImuHandler)
    httpd.imu_client = imu_client  # type: ignore[attr-defined]
    httpd.telemetry_poller = telemetry_poller  # type: ignore[attr-defined]
    httpd.video_manager = video_manager  # type: ignore[attr-defined]
    httpd.demo_manager = demo_manager  # type: ignore[attr-defined]
    httpd.vision_config_manager = vision_config_manager  # type: ignore[attr-defined]
    httpd.vision_metrics_manager = vision_metrics_manager  # type: ignore[attr-defined]
    httpd.vision_state_manager = vision_state_manager  # type: ignore[attr-defined]
    httpd.viewer_presence_manager = viewer_presence_manager  # type: ignore[attr-defined]
    httpd.verbose = args.verbose  # type: ignore[attr-defined]

    print(f"IMU viewer running at http://{args.listen}:{args.http_port}")
    print(f"Proxying IMU from {args.pi_host}:{args.pi_port}")
    if args.webrtc_url:
        print(
            "Video pipeline: WebRTC(SFU) preferred "
            f"({args.webrtc_url}), H264 fallback={'off' if args.disable_h264 else 'on'}, "
            f"MJPEG fallback from {args.pi_host}:{args.pi_video_port}"
        )
    else:
        print(f"Video pipeline: H264 preferred, MJPEG fallback from {args.pi_host}:{args.pi_video_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        vision_worker.stop()
        try:
            vision_worker.join(timeout=1.0)
        except Exception:
            pass
        telemetry_poller.stop()
        video_manager.stop()


if __name__ == "__main__":
    main()
