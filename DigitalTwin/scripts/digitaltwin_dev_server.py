#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/digitaltwin_dev_server.py
Version: v1.2 (2026-02-28 12:33)
Revision History:
- 2026-02-28 12:33 v1.2 - Relocated to `Code/DigitalTwin/scripts/`; updated DEFAULT_PAGE_REL and parents[] index for new folder depth.
- 2026-02-26 13:20 v1.1 - Fixed default `--code-root` discovery to repository `Code/` root so watchdog serves canonical page path (`/DigitalTwin/pages/...`) without requiring explicit override.
- 2026-02-26 13:20 v1.0 - Added local DigitalTwin dev watchdog server with static page hosting, IMU proxy endpoints, and staged auto-recovery trigger endpoint to tolerate parallel-agent runtime contention.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
DEFAULT_PI_HOST = "192.168.0.32"
DEFAULT_PAGE_REL = "DigitalTwin/pages/freenove_robotdog_3d_render.html"
DEFAULT_WATCH_INTERVAL_SEC = 1.5
DEFAULT_RECOVERY_COOLDOWN_SEC = 90
DEFAULT_IMU_HOLD_SEC = 2.0


def _now_iso() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _json_get(url: str, timeout: float = 1.8) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError("json response is not object")
    return payload


def _json_post(url: str, payload: dict[str, Any], timeout: float = 4.0) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        code = int(resp.getcode() or 0)
    parsed = json.loads(raw) if raw.strip() else {}
    if not isinstance(parsed, dict):
        parsed = {"raw": raw}
    return code, parsed


def _as_float(v: Any) -> float | None:
    try:
        n = float(v)
    except Exception:
        return None
    return n if (n == n and abs(n) < 1e9) else None


def _extract_rpy(payload: dict[str, Any]) -> tuple[float, float, float] | None:
    candidates = [payload]
    for key in ("imu", "data", "telemetry", "pose"):
        sub = payload.get(key)
        if isinstance(sub, dict):
            candidates.append(sub)
    for src in candidates:
        roll = _as_float(src.get("roll", src.get("roll_deg", src.get("r"))))
        pitch = _as_float(src.get("pitch", src.get("pitch_deg", src.get("p"))))
        yaw = _as_float(src.get("yaw", src.get("yaw_deg", src.get("y"))))
        if roll is None or pitch is None or yaw is None:
            continue
        return roll, pitch, yaw
    return None


def _url_alive(url: str, timeout: float = 1.2) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = int(resp.getcode() or 0)
            return 200 <= code < 500
    except Exception:
        return False


def _notify_macos(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    title_safe = title.replace('"', "'")
    msg_safe = message.replace('"', "'")
    cmd = [
        "osascript",
        "-e",
        f'display notification "{msg_safe}" with title "{title_safe}"',
    ]
    try:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


class DigitalTwinDevServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass,
        *,
        code_root: Path,
        pi_host: str,
        recovery_cooldown_sec: int,
        allow_ssh_recover: bool,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.code_root = Path(code_root).resolve()
        self.pi_host = str(pi_host).strip()
        self.recovery_cooldown_sec = int(max(15, recovery_cooldown_sec))
        self.allow_ssh_recover = bool(allow_ssh_recover)
        self.start_ts = time.time()
        self._lock = threading.Lock()

        self.imu_upstreams = [
            f"http://{self.pi_host}:8081/imu",
            f"http://{self.pi_host}:8090/imu",
            "http://127.0.0.1:8081/imu",
            "http://127.0.0.1:8090/imu",
        ]
        self.recover_upstreams = [
            f"http://{self.pi_host}:8081/video/recover",
            "http://127.0.0.1:8081/video/recover",
        ]

        self.last_imu_payload: dict[str, Any] | None = None
        self.last_imu_ts = 0.0
        self.last_imu_error = ""
        self.imu_success_count = 0
        self.imu_fail_count = 0
        self.imu_hold_count = 0

        self.recover_inflight = False
        self.last_recover_ts = 0.0
        self.recover_count = 0
        self.recover_fail_count = 0
        self.last_recover_result: dict[str, Any] = {}

    def _hold_imu(self, now_ts: float, reason: str) -> dict[str, Any] | None:
        with self._lock:
            if not self.last_imu_payload or self.last_imu_ts <= 0:
                return None
            if (now_ts - self.last_imu_ts) > DEFAULT_IMU_HOLD_SEC:
                return None
            self.imu_hold_count += 1
            self.last_imu_error = reason
            out = dict(self.last_imu_payload)
        out["quality"] = "local_hold"
        out["fresh"] = False
        out["error"] = reason
        out["sample_age_ms"] = int(max(0.0, (now_ts - self.last_imu_ts) * 1000.0))
        return out

    def fetch_imu(self) -> tuple[bool, dict[str, Any]]:
        now_ts = time.time()
        errors: list[str] = []
        for endpoint in self.imu_upstreams:
            try:
                payload = _json_get(endpoint, timeout=1.6)
                rpy = _extract_rpy(payload)
                if rpy is None:
                    errors.append(f"{endpoint}: missing_rpy")
                    continue
                roll, pitch, yaw = rpy
                out = {
                    "roll": roll,
                    "pitch": pitch,
                    "yaw": yaw,
                    "quality": str(payload.get("quality") or "ok"),
                    "fresh": bool(payload.get("fresh", True)),
                    "source": str(payload.get("source") or payload.get("provider") or endpoint),
                    "endpoint": endpoint,
                    "error": "",
                }
                with self._lock:
                    self.last_imu_payload = dict(out)
                    self.last_imu_ts = now_ts
                    self.last_imu_error = ""
                    self.imu_success_count += 1
                    out["sample_age_ms"] = 0
                    out["imu_success_count"] = self.imu_success_count
                    out["imu_fail_count"] = self.imu_fail_count
                    out["imu_hold_count"] = self.imu_hold_count
                return True, out
            except Exception as exc:
                errors.append(f"{endpoint}: {exc}")
        reason = "; ".join(errors[-3:]) if errors else "imu_fetch_failed"
        with self._lock:
            self.imu_fail_count += 1
            self.last_imu_error = reason
        held = self._hold_imu(now_ts, reason)
        if held is not None:
            with self._lock:
                held["imu_success_count"] = self.imu_success_count
                held["imu_fail_count"] = self.imu_fail_count
                held["imu_hold_count"] = self.imu_hold_count
            return True, held
        return False, {
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "quality": "error",
            "fresh": False,
            "source": "none",
            "endpoint": "",
            "error": reason,
            "sample_age_ms": None,
            "imu_success_count": self.imu_success_count,
            "imu_fail_count": self.imu_fail_count,
            "imu_hold_count": self.imu_hold_count,
        }

    def trigger_recover(self, *, reason: str, client: str, auto: bool) -> dict[str, Any]:
        now_ts = time.time()
        with self._lock:
            cooldown_left = int(max(0, (self.recovery_cooldown_sec - (now_ts - self.last_recover_ts)) * 1000.0))
            if self.recover_inflight:
                return {
                    "ok": False,
                    "accepted": False,
                    "in_progress": True,
                    "cooldown_ms": cooldown_left,
                    "error": "recover_in_progress",
                    "last": dict(self.last_recover_result),
                }
            if cooldown_left > 0:
                return {
                    "ok": False,
                    "accepted": False,
                    "in_progress": False,
                    "cooldown_ms": cooldown_left,
                    "error": "recover_cooldown",
                    "last": dict(self.last_recover_result),
                }
            self.recover_inflight = True
            self.last_recover_ts = now_ts
            self.recover_count += 1

        attempt_id = f"dtrec-{int(now_ts)}-{self.recover_count}"
        result = {
            "ok": False,
            "accepted": False,
            "attempt_id": attempt_id,
            "cooldown_ms": self.recovery_cooldown_sec * 1000,
            "auto": bool(auto),
            "reason": str(reason or ""),
            "client": str(client or ""),
            "steps": [],
            "error": "",
        }

        try:
            req_payload = {
                "mode": "full_stack",
                "reason": f"digitaltwin:{reason}"[:180],
                "client": client or "digitaltwin",
                "confirm": True,
            }
            for endpoint in self.recover_upstreams:
                step = {"endpoint": endpoint, "ok": False, "status": 0, "error": ""}
                try:
                    status, body = _json_post(endpoint, req_payload, timeout=5.0)
                    step["status"] = status
                    step["body"] = body
                    step["ok"] = bool(body.get("ok") or body.get("accepted"))
                    result["steps"].append(step)
                    if step["ok"]:
                        result["ok"] = True
                        result["accepted"] = True
                        result["recover"] = body
                        break
                except Exception as exc:
                    step["error"] = str(exc)
                    result["steps"].append(step)

            if not result["ok"] and self.allow_ssh_recover:
                ssh_cmd = [
                    "ssh",
                    f"pi@{self.pi_host}",
                    "sudo systemctl restart robot-publisher.service robot-sfu.service robot-color-viewer.service",
                ]
                step = {"endpoint": "ssh:systemctl", "ok": False, "status": 0, "error": ""}
                try:
                    proc = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=12, check=False)
                    step["status"] = int(proc.returncode)
                    step["stdout"] = (proc.stdout or "").strip()
                    step["error"] = (proc.stderr or "").strip()
                    step["ok"] = proc.returncode == 0
                except Exception as exc:
                    step["error"] = str(exc)
                result["steps"].append(step)
                if step["ok"]:
                    result["ok"] = True
                    result["accepted"] = True

            if not result["ok"]:
                result["error"] = "recover_attempt_failed"
                with self._lock:
                    self.recover_fail_count += 1
            return result
        finally:
            with self._lock:
                self.recover_inflight = False
                self.last_recover_result = dict(result)

    def health_snapshot(self) -> dict[str, Any]:
        now_ts = time.time()
        with self._lock:
            imu_age_ms = int(max(0.0, (now_ts - self.last_imu_ts) * 1000.0)) if self.last_imu_ts > 0 else None
            out = {
                "ok": True,
                "ts": now_ts,
                "uptime_s": round(max(0.0, now_ts - self.start_ts), 2),
                "code_root": str(self.code_root),
                "pi_host": self.pi_host,
                "imu_upstreams": list(self.imu_upstreams),
                "last_imu_age_ms": imu_age_ms,
                "last_imu_error": self.last_imu_error,
                "imu_success_count": self.imu_success_count,
                "imu_fail_count": self.imu_fail_count,
                "imu_hold_count": self.imu_hold_count,
                "recover_inflight": self.recover_inflight,
                "recover_count": self.recover_count,
                "recover_fail_count": self.recover_fail_count,
                "last_recover": dict(self.last_recover_result),
                "recovery_cooldown_sec": self.recovery_cooldown_sec,
            }
        return out


class DigitalTwinRequestHandler(SimpleHTTPRequestHandler):
    server_version = "DigitalTwinDev/1.0"

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        ts = _now_iso()
        msg = fmt % args
        print(f"[{ts}] {self.client_address[0]} {self.command} {self.path} :: {msg}")

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        srv = self.server  # type: ignore[assignment]
        if path in ("/imu", "/api/imu", "/telemetry/imu"):
            ok, payload = srv.fetch_imu()
            payload["ok"] = bool(ok)
            payload["ts"] = time.time()
            return self._write_json(HTTPStatus.OK, payload)
        if path == "/__dt/health":
            return self._write_json(HTTPStatus.OK, srv.health_snapshot())
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        srv = self.server  # type: ignore[assignment]
        if path != "/__dt/recover":
            return self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found", "path": path})
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except Exception:
            length = 0
        payload: dict[str, Any] = {}
        if length > 0:
            raw = self.rfile.read(length)
            try:
                obj = json.loads(raw.decode("utf-8", errors="replace"))
                if isinstance(obj, dict):
                    payload = obj
            except Exception:
                payload = {}
        reason = str(payload.get("reason") or "imu_offline")
        client = str(payload.get("client") or "digitaltwin_page")
        auto = bool(payload.get("auto", True))
        out = srv.trigger_recover(reason=reason, client=client, auto=auto)
        return self._write_json(HTTPStatus.OK, out)


def _serve_once(args: argparse.Namespace) -> int:
    code_root = Path(args.code_root).resolve()
    if not code_root.exists():
        print(f"ERROR: code_root not found: {code_root}", file=sys.stderr)
        return 2
    handler = functools.partial(DigitalTwinRequestHandler, directory=str(code_root))
    try:
        server = DigitalTwinDevServer(
            (args.host, args.port),
            handler,
            code_root=code_root,
            pi_host=args.pi_host,
            recovery_cooldown_sec=args.recovery_cooldown_sec,
            allow_ssh_recover=args.allow_ssh_recover,
        )
    except OSError as exc:
        print(f"ERROR: bind failed {args.host}:{args.port} ({exc})", file=sys.stderr)
        return 3

    page_url = f"http://{args.host}:{args.port}/{DEFAULT_PAGE_REL}"
    print(f"DigitalTwin dev server running at {page_url}")
    print(f"IMU proxy upstream priority: {', '.join(server.imu_upstreams)}")

    stop_event = threading.Event()

    def _handle_signal(signum, frame):  # noqa: ANN001
        stop_event.set()
        try:
            server.shutdown()
        except Exception:
            pass

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


def _run_watchdog(args: argparse.Namespace) -> int:
    page_url = f"http://{args.host}:{args.port}/{DEFAULT_PAGE_REL}"
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--serve-once",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--pi-host",
        args.pi_host,
        "--code-root",
        str(Path(args.code_root).resolve()),
        "--recovery-cooldown-sec",
        str(args.recovery_cooldown_sec),
    ]
    if args.allow_ssh_recover:
        cmd.append("--allow-ssh-recover")

    child: subprocess.Popen[str] | None = None
    print(f"Watchdog enabled. Target page: {page_url}")
    if args.notify:
        _notify_macos("DigitalTwin Watchdog", f"Monitoring {args.host}:{args.port}")

    try:
        while True:
            page_alive = _url_alive(page_url, timeout=1.1)
            if page_alive:
                if child is not None and child.poll() is not None:
                    child = None
                time.sleep(max(0.4, args.watch_interval_sec))
                continue

            if child is None or child.poll() is not None:
                child = subprocess.Popen(cmd)
                print(f"[{_now_iso()}] watchdog: started server pid={child.pid}")
                if args.notify:
                    _notify_macos("DigitalTwin Server Restart", f"Restarted on {args.host}:{args.port}")
            time.sleep(max(0.4, args.watch_interval_sec))
    except KeyboardInterrupt:
        pass
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=2.0)
            except Exception:
                child.kill()
    return 0


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description="DigitalTwin local dev server + watchdog")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--pi-host", default=DEFAULT_PI_HOST)
    p.add_argument("--code-root", default=str(default_root))
    p.add_argument("--serve-once", action="store_true", help="Run one server instance (no watchdog loop).")
    p.add_argument("--watch-interval-sec", type=float, default=DEFAULT_WATCH_INTERVAL_SEC)
    p.add_argument("--recovery-cooldown-sec", type=int, default=DEFAULT_RECOVERY_COOLDOWN_SEC)
    p.add_argument("--allow-ssh-recover", action="store_true", help="Allow SSH systemctl restart fallback on failed /video/recover API.")
    p.add_argument("--notify", action="store_true", help="Enable macOS notifications for watchdog restart events.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.serve_once:
        return _serve_once(args)
    return _run_watchdog(args)


if __name__ == "__main__":
    sys.exit(main())
