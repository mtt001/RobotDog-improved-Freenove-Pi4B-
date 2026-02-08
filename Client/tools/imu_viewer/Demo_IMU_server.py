#!/usr/bin/env python3
"""
IMU Viewer HTTP Proxy
Description:
    Serves Three.js IMU viewer pages and proxies IMU queries to the Pi control port (CMD_ATTITUDE).
Usage:
    # 0) Zero-typing launch (uses built-in DEFAULT_* config below)
    python3 Demo_IMU_server.py

    # 1) Start proxy with explicit overrides (if needed)
    python3 Demo_IMU_server.py --pi-host 192.168.0.32 --pi-port 5001 --http-port 8080 --webrtc-url http://192.168.0.198:8889/robotdog/whep

    # 2) Open pages
    #    http://127.0.0.1:8080/
    #    http://127.0.0.1:8080/simple
    #    http://127.0.0.1:8080/color

    # 3) Verify active stream method
    #    http://127.0.0.1:8080/video/status
    #    preferred=h264  => H.264 HLS path
    #    preferred=mjpeg => Proprietary MJPEG fallback path

    # Optional: tune H.264 profile
    python3 Demo_IMU_server.py --pi-host 192.168.0.32 --h264-width 1280 --h264-height 720 --h264-fps 24

    # Optional: force MJPEG-only fallback path
    python3 Demo_IMU_server.py --pi-host 192.168.0.32 --disable-h264

    # Stop proxy: Ctrl+C
Version:
    2026.02.07-14
Revision History:
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
import shutil
import socket
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
PROXY_VERSION = "2026.02.07-14"

# Default runtime configuration (used when no CLI overrides are provided).
# Goal: user can run only `python3 Demo_IMU_server.py`.
DEFAULT_PI_HOST = "192.168.0.32"
DEFAULT_PI_PORT = 5001
DEFAULT_PI_VIDEO_PORT = 8001
DEFAULT_SSH_USER = "pi"
DEFAULT_HTTP_LISTEN = "0.0.0.0"
DEFAULT_HTTP_PORT = 8080
DEFAULT_H264_WIDTH = 960
DEFAULT_H264_HEIGHT = 540
DEFAULT_H264_FPS = 20
DEFAULT_SFU_HOST = "192.168.0.198"
DEFAULT_STREAM_PATH = "robotdog"
DEFAULT_WEBRTC_URL = f"http://{DEFAULT_SFU_HOST}:8889/{DEFAULT_STREAM_PATH}/whep"


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


class TelemetryPoller(threading.Thread):
    def __init__(self, imu_client: ImuClient, interval_s: float = 1.0):
        super().__init__(daemon=True)
        self.imu_client = imu_client
        self.interval_s = max(0.3, float(interval_s))
        self.battery_v: float | None = None
        self.distance_cm: float | None = None
        self.last_ok_ts = 0.0
        self.last_err = ""
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
                self.battery_v = val
                self.last_ok_ts = time.time()
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
                self.distance_cm = val
                self.last_ok_ts = time.time()
            else:
                self.last_err = f"unexpected sonic reply: {line}"
        except Exception as e:
            self.last_err = str(e)


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


class ImuHandler(BaseHTTPRequestHandler):
    server_version = "IMUViewer/1.0"

    def _write(self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(code)
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

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if self.path == "/" or self.path == "/index.html":
            return self._serve_file(BASE_DIR / "index.html", "text/html; charset=utf-8")
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
            payload = {
                "ok": bool(imu_client.last_ok_ts),
                "ts": time.time(),
                "pi_host": imu_client.host,
                "pi_port": imu_client.port,
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
        if self.path.startswith("/telemetry"):
            telem = self.server.telemetry_poller  # type: ignore[attr-defined]
            payload = {
                "ok": bool(telem.last_ok_ts),
                "ts": time.time(),
                "battery_v": telem.battery_v,
                "distance_cm": telem.distance_cm,
                "last_ok_ts": telem.last_ok_ts,
                "last_err": telem.last_err,
            }
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
            if not cmd.endswith("\n"):
                cmd = cmd + "\n"
            try:
                self.server.imu_client.send_only(cmd)  # type: ignore[attr-defined]
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                return self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
            body = json.dumps({"ok": True}).encode("utf-8")
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
        verbose=args.verbose,
    )
    video_manager.ensure_started()

    httpd = ThreadingHTTPServer((args.listen, args.http_port), ImuHandler)
    httpd.imu_client = imu_client  # type: ignore[attr-defined]
    httpd.telemetry_poller = telemetry_poller  # type: ignore[attr-defined]
    httpd.video_manager = video_manager  # type: ignore[attr-defined]
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
        telemetry_poller.stop()
        video_manager.stop()


if __name__ == "__main__":
    main()
