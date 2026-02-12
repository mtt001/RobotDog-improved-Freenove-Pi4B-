#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Phase 5 Telemetry + Command API
 File   : telemetry_api_server.py
 Author : pi (admin) + Codex

 Exposes telemetry and multi-client-aware command endpoints for mobile Safari viewer:
 - /api/telemetry (JSON)
 - /api/session (JSON; arm/disarm command session)
 - /api/command (JSON; command MVP)
 - /api/diagnostics (JSON; service health + quick checks)
 - /health (JSON)
 - Optional API auth via bearer token (disabled by default)

Version
v1.9 (2026-02-10 07:33)

Revision History
v1.9 (2026-02-10 07:33) : Add mobile `balance_on` / `balance_off` actions (ARM required).
v1.8 (2026-02-10 07:27) : Add low-risk mobile command actions (`beep`, `led`, `cal`) under existing arm/session policy.
v1.7 (2026-02-09 20:54) : Add optional bearer-token auth gate for /api/* endpoints (off by default) and expose auth_enabled in diagnostics.
v1.6 (2026-02-09 18:55) : Add diagnostics endpoint and structured JSON logs for session/command/health events.
v1.5 (2026-02-09 18:43) : Add Phase-4 session UX metadata (lock state/owner hint), request/release workflow, and explicit busy-owner context.
v1.4 (2026-02-09 18:28) : Normalize loopback client IP for session keys and clear per-client rate state on disarm.
v1.3 (2026-02-09 18:21) : Add Phase-3 session arm + command API with rate-limit and motion watchdog auto-stop.
v1.2 (2026-02-09 16:13) : Add explicit version section in header block for repo compliance checks.
v1.1 (2026-02-09 16:09) : Make command reply parsing resilient by matching expected prefixes across buffered lines.
v1.0 (2026-02-09 16:04) : Initial telemetry API service for Phase-2 read-only overlay.
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from subprocess import DEVNULL, check_output
from urllib.parse import urlparse


def log_event(level: str, event: str, **fields):
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=True), flush=True)


class ControlClient:
    def __init__(self, host: str, port: int, timeout: float = 1.2):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.recv_buf = b""
        self.lock = threading.Lock()

    def _connect(self):
        self._close()
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        self.sock = s

    def _close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.recv_buf = b""

    def _recv_line(self) -> str:
        if self.sock is None:
            raise RuntimeError("not connected")
        data = self.recv_buf
        self.recv_buf = b""
        deadline = time.time() + self.timeout
        while time.time() < deadline and b"\n" not in data:
            chunk = self.sock.recv(1024)
            if not chunk:
                break
            data += chunk
        if b"\n" not in data:
            raise RuntimeError("no complete line")
        line_raw, remain = data.split(b"\n", 1)
        self.recv_buf = remain
        return line_raw.decode("utf-8", errors="ignore").strip()

    def exchange(self, cmd: str, expect_prefix: str | None = None, max_lines: int = 6) -> str:
        with self.lock:
            try:
                if self.sock is None:
                    self._connect()
                self.sock.sendall(cmd.encode("utf-8"))
                if expect_prefix is None:
                    return self._recv_line()
                last_line = ""
                for _ in range(max_lines):
                    line = self._recv_line()
                    last_line = line
                    if line.startswith(expect_prefix):
                        return line
                raise RuntimeError(f"unexpected reply sequence: {last_line}")
            except Exception:
                self._close()
                raise

    def send_no_reply(self, cmd: str) -> str:
        with self.lock:
            try:
                if self.sock is None:
                    self._connect()
                self.sock.sendall(cmd.encode("utf-8"))
                return self._try_recv_line(0.08)
            except Exception:
                self._close()
                raise

    def _try_recv_line(self, timeout_sec: float) -> str:
        if self.sock is None:
            return ""

        if b"\n" in self.recv_buf:
            line_raw, remain = self.recv_buf.split(b"\n", 1)
            self.recv_buf = remain
            return line_raw.decode("utf-8", errors="ignore").strip()

        prev_timeout = self.sock.gettimeout()
        try:
            self.sock.settimeout(timeout_sec)
            chunk = self.sock.recv(1024)
            if not chunk:
                return ""
            data = self.recv_buf + chunk
            if b"\n" not in data:
                self.recv_buf = data
                return ""
            line_raw, remain = data.split(b"\n", 1)
            self.recv_buf = remain
            return line_raw.decode("utf-8", errors="ignore").strip()
        except socket.timeout:
            return ""
        finally:
            try:
                self.sock.settimeout(prev_timeout if prev_timeout is not None else self.timeout)
            except Exception:
                pass


def parse_power(line: str):
    if not line.startswith("CMD_POWER#"):
        return None
    try:
        return float(line.split("#", 1)[1])
    except Exception:
        return None


def parse_sonic(line: str):
    if not line.startswith("CMD_SONIC#"):
        return None
    try:
        return float(line.split("#", 1)[1])
    except Exception:
        return None


def parse_attitude(line: str):
    if not line.startswith("CMD_ATTITUDE"):
        return None
    vals = {}
    for seg in line.split("#")[1:]:
        if ":" not in seg:
            continue
        k, v = seg.split(":", 1)
        k = k.strip().lower()
        try:
            vals[k] = float(v)
        except Exception:
            pass
    if all(k in vals for k in ("roll", "pitch", "yaw")):
        return vals
    return None


def service_active(name: str) -> bool:
    try:
        out = check_output(["systemctl", "is-active", name], stderr=DEVNULL, text=True, timeout=1.5).strip()
        return out == "active"
    except Exception:
        return False


def tcp_connect_ok(host: str, port: int, timeout: float = 1.0) -> bool:
    s = None
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        return True
    except Exception:
        return False
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


def rtsp_describe_ok(host: str, path: str) -> bool:
    req = (
        f"DESCRIBE rtsp://{host}:8554/{path} RTSP/1.0\r\n"
        "CSeq: 1\r\n"
        "Accept: application/sdp\r\n\r\n"
    ).encode("utf-8")
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((host, 8554))
        s.sendall(req)
        head = (s.recv(1024).decode("utf-8", "ignore").splitlines() or [""])[0]
        return "200" in head
    except Exception:
        return False
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


class TelemetryState:
    def __init__(self, control_host: str, control_port: int, stream_path: str):
        self.client = ControlClient(control_host, control_port)
        self.stream_path = stream_path
        self.lock = threading.Lock()
        self.payload = {
            "ts": time.time(),
            "battery": {"voltage": None, "state": "unknown"},
            "imu": {"roll": None, "pitch": None, "yaw": None},
            "ultrasonic_cm": None,
            "stream": {
                "status": "unknown",
                "fps": None,
                "publisher_active": False,
                "sfu_active": False,
                "rtsp_describe_ok": False,
            },
            "source_health": {
                "pi_control_link": "init",
                "age_ms": None,
                "last_ok_ts": None,
                "last_error": "",
            },
        }
        self.last_ok_ts = 0.0
        self.last_error = ""

    def _battery_state(self, v):
        if v is None:
            return "unknown"
        if v < 6.4:
            return "low"
        if v < 7.2:
            return "medium"
        return "normal"

    def poll_once(self):
        battery_v = None
        sonic = None
        attitude = None
        err = ""
        try:
            power_line = self.client.exchange("CMD_POWER\n", expect_prefix="CMD_POWER#")
            battery_v = parse_power(power_line)

            sonic_line = self.client.exchange("CMD_SONIC\n", expect_prefix="CMD_SONIC#")
            sonic = parse_sonic(sonic_line)

            att_line = self.client.exchange("CMD_ATTITUDE\n", expect_prefix="CMD_ATTITUDE")
            attitude = parse_attitude(att_line)

            if battery_v is None or sonic is None or attitude is None:
                raise RuntimeError("unexpected telemetry format")

            self.last_ok_ts = time.time()
            self.last_error = ""
        except Exception as e:
            err = str(e)
            self.last_error = err

        publisher_active = service_active("robot-publisher.service")
        sfu_active = service_active("robot-sfu.service")
        rtsp_ok = rtsp_describe_ok("127.0.0.1", self.stream_path)
        if publisher_active and sfu_active and rtsp_ok:
            stream_state = "live"
        elif sfu_active:
            stream_state = "degraded"
        else:
            stream_state = "down"

        now = time.time()
        age_ms = None
        if self.last_ok_ts > 0:
            age_ms = int((now - self.last_ok_ts) * 1000)

        with self.lock:
            if battery_v is not None:
                self.payload["battery"]["voltage"] = round(battery_v, 2)
                self.payload["battery"]["state"] = self._battery_state(battery_v)
            if sonic is not None:
                self.payload["ultrasonic_cm"] = round(sonic, 2)
            if attitude is not None:
                self.payload["imu"] = {
                    "roll": round(attitude["roll"], 2),
                    "pitch": round(attitude["pitch"], 2),
                    "yaw": round(attitude["yaw"], 2),
                }

            self.payload["stream"] = {
                "status": stream_state,
                "fps": None,
                "publisher_active": publisher_active,
                "sfu_active": sfu_active,
                "rtsp_describe_ok": rtsp_ok,
            }
            self.payload["source_health"] = {
                "pi_control_link": "ok" if err == "" else "degraded",
                "age_ms": age_ms,
                "last_ok_ts": self.last_ok_ts if self.last_ok_ts > 0 else None,
                "last_error": self.last_error,
            }
            self.payload["ts"] = now

    def get_payload(self):
        with self.lock:
            return json.loads(json.dumps(self.payload))


class PollThread(threading.Thread):
    def __init__(self, state: TelemetryState, interval: float):
        super().__init__(daemon=True)
        self.state = state
        self.interval = max(0.4, interval)
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            self.state.poll_once()
            self.stop_event.wait(self.interval)


class CommandState:
    ACTION_MAP = {
        "stop": ("CMD_MOVE_STOP\n", False),
        "relax": ("CMD_RELAX\n", True),
        "stop_pwm": ("CMD_STOP_PWM\n", False),
        "forward": ("CMD_MOVE_FORWARD#35\n", True),
        "backward": ("CMD_MOVE_BACKWARD#35\n", True),
        "left": ("CMD_MOVE_LEFT#35\n", True),
        "right": ("CMD_MOVE_RIGHT#35\n", True),
        "turn_left": ("CMD_TURN_LEFT#30\n", True),
        "turn_right": ("CMD_TURN_RIGHT#30\n", True),
        "beep": ("__SEQ_BEEP__", True),
        "led": ("__SEQ_LED__", True),
        "cal": ("CMD_CALIBRATION\n", True),
        "balance_on": ("CMD_BALANCE#1\n", True),
        "balance_off": ("CMD_BALANCE#0\n", True),
    }

    def __init__(self, client: ControlClient, arm_ttl_sec: float = 20.0, motion_timeout_sec: float = 0.9):
        self.client = client
        self.arm_ttl_sec = max(5.0, arm_ttl_sec)
        self.motion_timeout_sec = max(0.4, motion_timeout_sec)
        self.rate_limit_sec = 0.12
        self.lock = threading.Lock()
        self.armed_until_by_ip = {}
        self.last_cmd_ts_by_ip = {}
        self.last_control_ok_ts_by_ip = {}
        self.last_busy_owner_by_ip = {}
        self.last_busy_ts_by_ip = {}
        self.active_motion_ip = None
        self.active_motion_ts = 0.0
        self.stop_event = threading.Event()
        self.watchdog = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog.start()

    def _now(self):
        return time.time()

    def _gc(self, now_ts: float):
        stale = [k for k, v in self.armed_until_by_ip.items() if v <= now_ts]
        for k in stale:
            self.armed_until_by_ip.pop(k, None)

    def _lock_snapshot(self, client_ip: str, now_ts: float):
        busy_ts = float(self.last_busy_ts_by_ip.get(client_ip, 0.0))
        busy_owner = self.last_busy_owner_by_ip.get(client_ip, "")
        own_ok_ts = float(self.last_control_ok_ts_by_ip.get(client_ip, 0.0))
        busy_recent = (now_ts - busy_ts) <= 8.0 if busy_ts > 0 else False
        own_recent = (now_ts - own_ok_ts) <= 8.0 if own_ok_ts > 0 else False

        if busy_recent and busy_owner:
            lock = "owned_by_other"
        elif own_recent:
            lock = "owned_by_mobile"
        else:
            lock = "available_or_unknown"

        out = {
            "control_lock": lock,
            "owner_hint": busy_owner if busy_recent and busy_owner else "",
            "last_busy_age_ms": int((now_ts - busy_ts) * 1000) if busy_ts > 0 else None,
        }
        return out

    def session_status(self, client_ip: str):
        now_ts = self._now()
        with self.lock:
            self._gc(now_ts)
            until = self.armed_until_by_ip.get(client_ip, 0.0)
            ttl_ms = int(max(0.0, until - now_ts) * 1000)
            out = {"armed": ttl_ms > 0, "arm_ttl_ms": ttl_ms}
            out.update(self._lock_snapshot(client_ip, now_ts))
            return out

    def set_armed(self, client_ip: str, armed: bool):
        now_ts = self._now()
        with self.lock:
            if armed:
                self.armed_until_by_ip[client_ip] = now_ts + self.arm_ttl_sec
            else:
                self.armed_until_by_ip.pop(client_ip, None)
                self.last_cmd_ts_by_ip.pop(client_ip, None)
            until = self.armed_until_by_ip.get(client_ip, 0.0)
            ttl_ms = int(max(0.0, until - now_ts) * 1000)
            st = {"armed": ttl_ms > 0, "arm_ttl_ms": ttl_ms}
            st.update(self._lock_snapshot(client_ip, now_ts))
        return st

    def request_control(self, client_ip: str):
        st = self.set_armed(client_ip, True)
        st["workflow"] = "request"
        st["next_step"] = "If lock is owned_by_other, ask current owner to release then retry movement."
        return st

    def release_control(self, client_ip: str):
        self._send_control("CMD_MOVE_STOP\n")
        st = self.set_armed(client_ip, False)
        st["workflow"] = "release"
        st["next_step"] = "Session disarmed and stop sent."
        return st

    def snapshot(self):
        now_ts = self._now()
        with self.lock:
            self._gc(now_ts)
            active_sessions = sum(1 for _, until in self.armed_until_by_ip.items() if until > now_ts)
            return {
                "active_sessions": active_sessions,
                "active_motion_ip": self.active_motion_ip,
                "rate_limit_sec": self.rate_limit_sec,
                "arm_ttl_sec": self.arm_ttl_sec,
                "motion_timeout_sec": self.motion_timeout_sec,
            }

    def _is_armed(self, client_ip: str, now_ts: float):
        until = self.armed_until_by_ip.get(client_ip, 0.0)
        return until > now_ts

    def _rate_limit_ok(self, client_ip: str, now_ts: float):
        prev = self.last_cmd_ts_by_ip.get(client_ip, 0.0)
        if (now_ts - prev) < self.rate_limit_sec:
            return False, int((self.rate_limit_sec - (now_ts - prev)) * 1000)
        self.last_cmd_ts_by_ip[client_ip] = now_ts
        return True, 0

    def _set_motion_active(self, client_ip: str):
        self.active_motion_ip = client_ip
        self.active_motion_ts = self._now()

    def _clear_motion(self):
        self.active_motion_ip = None
        self.active_motion_ts = 0.0

    def _send_control(self, wire_cmd: str):
        try:
            reply = self.client.send_no_reply(wire_cmd)
            if reply.startswith("CMD_BUSY#OWNER:"):
                return {"ok": False, "error": "busy", "detail": reply}
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": "control_unreachable", "detail": str(e)}

    def _send_sequence(self, commands, sleep_sec: float = 0.0):
        for idx, cmd in enumerate(commands):
            rs = self._send_control(cmd)
            if not rs.get("ok"):
                return rs
            if sleep_sec > 0.0 and idx < (len(commands) - 1):
                time.sleep(sleep_sec)
        return {"ok": True}

    def execute(self, client_ip: str, action: str):
        now_ts = self._now()
        action = (action or "").strip().lower()
        spec = self.ACTION_MAP.get(action)
        if spec is None:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "unsupported_action"}

        wire_cmd, requires_arm = spec
        with self.lock:
            self._gc(now_ts)
            if requires_arm and not self._is_armed(client_ip, now_ts):
                return HTTPStatus.FORBIDDEN, {
                    "ok": False,
                    "error": "session_not_armed",
                    "hint": "POST /api/session with {\"armed\":true} first",
                }
            if action not in {"stop", "stop_pwm", "relax"}:
                ok_rate, wait_ms = self._rate_limit_ok(client_ip, now_ts)
                if not ok_rate:
                    return HTTPStatus.TOO_MANY_REQUESTS, {
                        "ok": False,
                        "error": "rate_limited",
                        "retry_after_ms": wait_ms,
                    }

            if action in {"forward", "backward", "left", "right", "turn_left", "turn_right"}:
                self._set_motion_active(client_ip)
            if action in {"stop", "stop_pwm", "relax"}:
                self._clear_motion()

        if wire_cmd == "__SEQ_BEEP__":
            rs = self._send_sequence(["CMD_BUZZER#1\n", "CMD_BUZZER#0\n"], sleep_sec=0.12)
        elif wire_cmd == "__SEQ_LED__":
            rs = self._send_sequence(
                ["CMD_LED_MOD#1\n", "CMD_LED#255#0#255#0\n", "CMD_LED_MOD#0\n"],
                sleep_sec=0.16,
            )
        else:
            rs = self._send_control(wire_cmd)
        status = HTTPStatus.OK if rs.get("ok") else HTTPStatus.CONFLICT
        now_ts2 = self._now()
        payload = {
            "ok": rs.get("ok", False),
            "action": action,
            "ts": now_ts,
            "client_ip": client_ip,
        }
        if not rs.get("ok"):
            payload["error"] = rs.get("error")
            payload["detail"] = rs.get("detail")
            if payload["error"] == "busy":
                owner = ""
                detail = payload.get("detail", "")
                if "CMD_BUSY#OWNER:" in detail:
                    owner = detail.split("CMD_BUSY#OWNER:", 1)[1].strip()
                with self.lock:
                    self.last_busy_owner_by_ip[client_ip] = owner
                    self.last_busy_ts_by_ip[client_ip] = now_ts2
                payload["owner_hint"] = owner
        else:
            if action in {"forward", "backward", "left", "right", "turn_left", "turn_right"}:
                with self.lock:
                    self.last_control_ok_ts_by_ip[client_ip] = now_ts2
                    self.last_busy_owner_by_ip.pop(client_ip, None)
                    self.last_busy_ts_by_ip.pop(client_ip, None)
        payload.update(self.session_status(client_ip))
        return status, payload

    def _watchdog_loop(self):
        while not self.stop_event.is_set():
            time.sleep(0.1)
            should_stop = False
            with self.lock:
                if self.active_motion_ip is not None and (self._now() - self.active_motion_ts) > self.motion_timeout_sec:
                    should_stop = True
                    self._clear_motion()
            if should_stop:
                self._send_control("CMD_MOVE_STOP\n")


class Handler(BaseHTTPRequestHandler):
    state = None
    command_state = None
    stream_path = "robotdog"
    api_token = ""

    def _set_headers(self, code=200, content_type="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "").strip()
        if fwd:
            ip = fwd.split(",")[0].strip()
        else:
            ip = self.client_address[0]
        if ip in {"::1", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1"}:
            return "127.0.0.1"
        return ip

    def _read_json_body(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        raw = self.rfile.read(n) if n > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def _auth_ok(self):
        token = (Handler.api_token or "").strip()
        if token == "":
            return True
        hdr = self.headers.get("Authorization", "")
        if not hdr.startswith("Bearer "):
            return False
        got = hdr.split("Bearer ", 1)[1].strip()
        return got == token

    def _reject_unauthorized(self):
        self._set_headers(HTTPStatus.UNAUTHORIZED)
        self.wfile.write(json.dumps({"ok": False, "error": "unauthorized"}).encode("utf-8"))

    def do_OPTIONS(self):
        self._set_headers(HTTPStatus.NO_CONTENT)

    def do_GET(self):
        if self.path == "/health":
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps({"ok": True, "ts": time.time(), "version": "v1.7"}).encode("utf-8"))
            return

        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/") and not self._auth_ok():
            self._reject_unauthorized()
            return
        if parsed.path.startswith("/api/telemetry"):
            payload = Handler.state.get_payload()
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        if parsed.path == "/api/session":
            ip = self._client_ip()
            sess = Handler.command_state.session_status(ip)
            payload = {"ok": True, "client_ip": ip, "ts": time.time(), **sess}
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        if parsed.path == "/api/diagnostics":
            ip = self._client_ip()
            payload = self._diagnostics_payload(ip)
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        self._set_headers(HTTPStatus.NOT_FOUND)
        self.wfile.write(json.dumps({"error": "not_found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/") and not self._auth_ok():
            self._reject_unauthorized()
            return
        ip = self._client_ip()
        body = self._read_json_body()
        if body is None:
            self._set_headers(HTTPStatus.BAD_REQUEST)
            self.wfile.write(json.dumps({"ok": False, "error": "invalid_json"}).encode("utf-8"))
            return

        if parsed.path == "/api/session":
            action = str(body.get("action", "")).strip().lower()
            if action == "request":
                sess = Handler.command_state.request_control(ip)
            elif action == "release":
                sess = Handler.command_state.release_control(ip)
            else:
                armed = bool(body.get("armed", False))
                sess = Handler.command_state.set_armed(ip, armed)
            payload = {"ok": True, "client_ip": ip, "ts": time.time(), **sess}
            log_event("info", "session_update", client_ip=ip, action=(action or "set_armed"), armed=payload.get("armed"), lock=payload.get("control_lock"), owner_hint=payload.get("owner_hint", ""))
            self._set_headers(HTTPStatus.OK)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        if parsed.path == "/api/command":
            action = str(body.get("action", "")).strip().lower()
            code, payload = Handler.command_state.execute(ip, action)
            log_event("info" if payload.get("ok") else "warn", "command", client_ip=ip, action=action, ok=payload.get("ok"), error=payload.get("error", ""), owner_hint=payload.get("owner_hint", ""))
            self._set_headers(code)
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        self._set_headers(HTTPStatus.NOT_FOUND)
        self.wfile.write(json.dumps({"error": "not_found"}).encode("utf-8"))

    def log_message(self, fmt, *args):
        return

    def _diagnostics_payload(self, client_ip: str):
        now_ts = time.time()
        services = {
            "smartdog.service": service_active("smartdog.service"),
            "robot-sfu.service": service_active("robot-sfu.service"),
            "robot-publisher.service": service_active("robot-publisher.service"),
            "robot-viewer.service": service_active("robot-viewer.service"),
            "robot-telemetry.service": service_active("robot-telemetry.service"),
        }
        ports = {}
        for p in (5001, 8001, 8080, 8090, 8554, 8889):
            ports[str(p)] = tcp_connect_ok("127.0.0.1", p, timeout=0.8)

        session = Handler.command_state.session_status(client_ip)
        payload = {
            "ok": True,
            "ts": now_ts,
            "version": "v1.7",
            "client_ip": client_ip,
            "auth_enabled": (Handler.api_token or "") != "",
            "services": services,
            "ports": ports,
            "stream_rtsp_describe_ok": rtsp_describe_ok("127.0.0.1", Handler.stream_path),
            "session": session,
            "command_state": Handler.command_state.snapshot(),
        }
        return payload


def main():
    p = argparse.ArgumentParser(description="Robot Dog telemetry + command API")
    p.add_argument("--listen", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8090)
    p.add_argument("--control-host", default="127.0.0.1")
    p.add_argument("--control-port", type=int, default=5001)
    p.add_argument("--stream-path", default="robotdog")
    p.add_argument("--poll-interval", type=float, default=0.8)
    p.add_argument("--arm-ttl", type=float, default=20.0)
    p.add_argument("--motion-timeout", type=float, default=0.9)
    p.add_argument("--api-token", default="")
    args = p.parse_args()

    state = TelemetryState(args.control_host, args.control_port, args.stream_path)
    Handler.state = state
    Handler.stream_path = args.stream_path
    Handler.api_token = (args.api_token or "").strip()
    Handler.command_state = CommandState(
        client=state.client,
        arm_ttl_sec=args.arm_ttl,
        motion_timeout_sec=args.motion_timeout,
    )

    poller = PollThread(state, args.poll_interval)
    poller.start()

    server = ThreadingHTTPServer((args.listen, args.port), Handler)
    print(f"[telemetry-api] serving on {args.listen}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
