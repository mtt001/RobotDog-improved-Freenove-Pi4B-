#!/usr/bin/env python3
"""
IMU Viewer HTTP Proxy
Description:
    Serves Three.js IMU viewer pages and proxies IMU queries to the Pi control port (CMD_ATTITUDE).
Version:
    2026.02.07-2
Revision History:
    2026-02-07 13:39 - Added live telemetry polling for power/range via /telemetry.
    2026-02-07 13:46 - Added line-safe socket buffering and filtered telemetry replies.
"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROXY_VERSION = "2026.02.07-2"


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
        if self.path == "/" or self.path == "/index.html":
            return self._serve_file(BASE_DIR / "index.html", "text/html; charset=utf-8")
        if self.path == "/simple" or self.path == "/index_simple.html":
            return self._serve_file(BASE_DIR / "index_simple.html", "text/html; charset=utf-8")
        if self.path == "/color" or self.path == "/index_color.html":
            return self._serve_file(BASE_DIR / "index_color.html", "text/html; charset=utf-8")
        if self.path == "/app.js":
            return self._serve_file(BASE_DIR / "app.js", "application/javascript; charset=utf-8")
        if self.path == "/app_simple.js":
            return self._serve_file(BASE_DIR / "app_simple.js", "application/javascript; charset=utf-8")
        if self.path == "/app_color.js":
            return self._serve_file(BASE_DIR / "app_color.js", "application/javascript; charset=utf-8")
        if self.path.startswith("/assets/") or self.path.startswith("/vendor/"):
            rel = self.path.lstrip("/")
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
        if self.path.startswith("/imu"):
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
    parser.add_argument("--pi-host", default="192.168.0.32", help="Pi IP/hostname (control port)")
    parser.add_argument("--pi-port", type=int, default=5001, help="Pi control port")
    parser.add_argument("--listen", default="0.0.0.0", help="HTTP listen address")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP listen port")
    parser.add_argument("--timeout", type=float, default=1.0, help="Pi TCP timeout seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    imu_client = ImuClient(args.pi_host, args.pi_port, timeout=args.timeout, verbose=args.verbose)
    telemetry_poller = TelemetryPoller(imu_client, interval_s=1.0)
    telemetry_poller.start()

    httpd = ThreadingHTTPServer((args.listen, args.http_port), ImuHandler)
    httpd.imu_client = imu_client  # type: ignore[attr-defined]
    httpd.telemetry_poller = telemetry_poller  # type: ignore[attr-defined]
    httpd.verbose = args.verbose  # type: ignore[attr-defined]

    print(f"IMU viewer running at http://{args.listen}:{args.http_port}")
    print(f"Proxying IMU from {args.pi_host}:{args.pi_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        telemetry_poller.stop()


if __name__ == "__main__":
    main()
