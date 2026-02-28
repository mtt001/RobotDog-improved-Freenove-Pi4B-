#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/run_phase_verification.py
Version: v1.4 (2026-02-28 12:33)
Revision History:
- 2026-02-28 12:33 v1.4 - Relocated to `Code/DigitalTwin/scripts/`; updated parents[] index and page_rel path for new folder depth.
- 2026-02-26 13:20 v1.3 - Switched temporary local page host from raw `python -m http.server` to `digitaltwin_dev_server.py --serve-once` so phase runs use IMU proxy and local recovery endpoint wiring on the canonical test port.
- 2026-02-26 10:57 v1.2 - Added transient Playwright connection-refused retry (single retry with short backoff) to stabilize phase runs against intermittent local HTTP race conditions.
- 2026-02-26 10:54 v1.1 - Added per-servo axis-direction compliance check (`test_servo_axis_direction_playwright.py`) into phase C and phase E verification bundles.
- 2026-02-26 08:50 v1.0 - Added phase-by-phase automation runner that verifies HTTP reachability, launches real UI in Safari per phase, executes validation commands, and prints status after each phase.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Phase:
    key: str
    name: str
    commands: list[list[str]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Digital Twin phased verification with real Safari UI launch and per-phase status reports."
    )
    parser.add_argument("--port", type=int, default=8766, help="Local HTTP port for temporary static server.")
    parser.add_argument("--delay-ms", type=int, default=600, help="Delay after Safari launch per phase.")
    parser.add_argument("--headless", action="store_true", help="Run Playwright checks in headless mode.")
    parser.add_argument(
        "--only-phase",
        choices=["A", "B", "C", "D", "E", "F", "G"],
        help="Run a single phase instead of the full sequence.",
    )
    return parser.parse_args()


def _http_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code = int(response.getcode() or 0)
            return 200 <= code < 400, f"HTTP {code}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # pragma: no cover
        return False, f"ERR {exc}"


def _start_server(script_dir: Path, code_root: Path, port: int) -> subprocess.Popen:
    dev_server = script_dir / "digitaltwin_dev_server.py"
    cmd = [
        sys.executable,
        str(dev_server),
        "--serve-once",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--code-root",
        str(code_root),
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _run_command(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, combined.strip()


def _run_command_with_retry(cmd: list[str], retry_on_refused: bool = True) -> tuple[int, str]:
    rc, out = _run_command(cmd)
    if rc == 0 or (not retry_on_refused):
        return rc, out

    transient_markers = ("ERR_CONNECTION_REFUSED", "net::ERR_CONNECTION_REFUSED")
    if any(marker in out for marker in transient_markers):
        time.sleep(0.8)
        rc2, out2 = _run_command(cmd)
        if rc2 == 0:
            merged = (out + "\n[retry] transient connection refused recovered on retry").strip()
            return rc2, merged
        merged = (out + "\n[retry-attempt]\n" + out2).strip()
        return rc2, merged
    return rc, out


def _phase_definitions(script_dir: Path, page_url: str, headless: bool) -> list[Phase]:
    h = ["--headless"] if headless else []
    return [
        Phase(
            key="A",
            name="UI Foundation Gate",
            commands=[[sys.executable, str(script_dir / "test_mujoco_ui_gate_playwright.py"), "--page", page_url, *h]],
        ),
        Phase(
            key="B",
            name="Command Runtime Sweep",
            commands=[[sys.executable, str(script_dir / "smoke_servo_sweep_playwright.py"), "--page", page_url, *h]],
        ),
        Phase(
            key="C",
            name="Kinematics Behavior",
            commands=[
                [sys.executable, str(script_dir / "test_posture_modes_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "test_gait_walk_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "test_servo_axis_direction_playwright.py"), "--page", page_url, *h],
            ],
        ),
        Phase(
            key="D",
            name="IMU / Telemetry Coupling",
            commands=[[sys.executable, str(script_dir / "test_imu_feedback_playwright.py"), "--page", page_url, *h]],
        ),
        Phase(
            key="E",
            name="Regression Bundle",
            commands=[
                [sys.executable, str(script_dir / "test_mujoco_ui_gate_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "smoke_servo_sweep_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "test_posture_modes_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "test_gait_walk_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "test_servo_axis_direction_playwright.py"), "--page", page_url, *h],
                [sys.executable, str(script_dir / "test_imu_feedback_playwright.py"), "--page", page_url, *h],
            ],
        ),
        Phase(
            key="F",
            name="Module Health (Syntax)",
            commands=[[sys.executable, "-m", "py_compile", *[str(p) for p in sorted(script_dir.glob("*.py"))]]],
        ),
        Phase(
            key="G",
            name="Deployment Readiness Final Gate",
            commands=[[sys.executable, str(script_dir / "test_mujoco_ui_gate_playwright.py"), "--page", page_url, *h]],
        ),
    ]


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    code_root = script_dir.parents[1]
    page_rel = "DigitalTwin/pages/freenove_robotdog_3d_render.html"
    page_url = f"http://127.0.0.1:{args.port}/{page_rel}"

    server = _start_server(script_dir, code_root, args.port)
    try:
        time.sleep(0.8)
        ok, status = _http_ok(page_url)
        if not ok:
            print(f"FAIL: page reachability check failed before phase run ({status})")
            return 2
        print(f"PASS: page reachable ({status})")
        print(f"URL: {page_url}")

        phases = _phase_definitions(script_dir, page_url, args.headless)
        if args.only_phase:
            phases = [phase for phase in phases if phase.key == args.only_phase]

        total_pass = 0
        total_fail = 0
        for phase in phases:
            print("\n" + "=" * 72)
            print(f"PHASE {phase.key}: {phase.name}")

            ok_http, status_http = _http_ok(page_url)
            print(f"- UI reachability: {status_http}")
            if not ok_http:
                print(f"- RESULT: FAIL (UI not reachable for phase {phase.key})")
                total_fail += 1
                continue

            launch = subprocess.run(["open", "-a", "Safari", page_url], capture_output=True, text=True)
            if launch.returncode != 0:
                print(f"- Safari launch: FAIL ({launch.stderr.strip()})")
                total_fail += 1
                continue

            print("- Safari launch: PASS (real UI opened)")
            time.sleep(max(0.0, args.delay_ms / 1000.0))

            phase_ok = True
            for idx, cmd in enumerate(phase.commands, start=1):
                rc, out = _run_command_with_retry(cmd)
                print(f"  Command {idx}: {' '.join(cmd)}")
                print(f"  Exit: {rc}")
                if out:
                    print("  Output:")
                    for line in out.splitlines()[:24]:
                        print(f"    {line}")
                    if len(out.splitlines()) > 24:
                        print("    ... (truncated)")
                if rc != 0:
                    phase_ok = False
                    break

            if phase_ok:
                total_pass += 1
                print(f"- RESULT: PASS (phase {phase.key})")
            else:
                total_fail += 1
                print(f"- RESULT: FAIL (phase {phase.key})")

        print("\n" + "=" * 72)
        print("PHASE VERIFICATION SUMMARY")
        print(f"- pass: {total_pass}")
        print(f"- fail: {total_fail}")
        print(f"- page: {page_url}")
        return 0 if total_fail == 0 else 1
    finally:
        server.terminate()
        try:
            server.wait(timeout=2)
        except Exception:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
