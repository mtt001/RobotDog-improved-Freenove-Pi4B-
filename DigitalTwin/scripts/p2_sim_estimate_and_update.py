#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/p2_sim_estimate_and_update.py
Version: v1.1 (2026-02-28 12:33)
Revision History:
- 2026-02-28 12:33 v1.1 - Relocated to `Code/DigitalTwin/scripts/`; removed `Test/` from path builder.
- 2026-02-26 11:11 v1.0 - Added P2 simulator-based estimator for speed/latency/backlash on S11/S12/S13 with JSON+CSV update and optional Phase E verification.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Estimate P2 dynamics from DigitalTwin simulation and update specs/log")
    p.add_argument("--code-root", default="/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code")
    p.add_argument("--date", default="2026-02-26")
    p.add_argument("--owner", default="copilot")
    p.add_argument("--speed", type=int, default=8)
    p.add_argument("--start", type=int, default=70)
    p.add_argument("--end", type=int, default=110)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--verify", action="store_true")
    return p.parse_args()


def _paths(code_root: Path) -> tuple[Path, Path, Path, Path]:
    base = code_root / "DigitalTwin"
    return (
        base / "pages" / "freenove_robotdog_3d_render.html",
        base / "resources" / "specs" / "robot_specs_template.json",
        base / "resources" / "specs" / "measurement_log_template.csv",
        base / "scripts" / "run_phase_verification.py",
    )


def _run_channel(page, channel: int, start: int, end: int, speed: int) -> tuple[float, float, float]:
    page.click("#servoTestToggleBtn")
    page.fill("#servoTestStartDeg", str(start))
    page.fill("#servoTestEndDeg", str(end))
    page.fill("#servoTestRepeat", "2")
    page.fill("#servoTestSpeed", str(speed))
    page.click("#servoTestAll")
    page.click("#servoTestAll")
    page.check(f'input.servo-test-ch[data-ch="{channel}"]')

    click_t = time.perf_counter()
    page.click("#servoTestRunBtn")

    times: list[float] = []
    vals: list[float] = []
    latency = None
    t0 = time.perf_counter()
    while (time.perf_counter() - t0) < 4.2:
        cmd = page.evaluate("window.__robotDogDebug.getServoCommandDeg()")
        v = float(cmd.get(str(channel), 0.0))
        now = time.perf_counter()
        times.append(now)
        vals.append(v)
        if latency is None and v > (start + 0.5):
            latency = now - click_t
        page.wait_for_timeout(70)

    page.click("#servoTestRunBtn")
    page.click("#servoTestToggleBtn")

    if latency is None:
        latency = 0.0

    min_v = min(vals) if vals else float(start)
    max_v = max(vals) if vals else float(start)
    rising = [(t, v) for t, v in zip(times, vals) if (v >= min_v + 2.0 and v <= max_v - 2.0)]
    if len(rising) >= 2:
        dt = max(1e-6, rising[-1][0] - rising[0][0])
        dv = rising[-1][1] - rising[0][1]
        speed_est = abs(dv / dt)
    else:
        speed_est = 0.0

    # Simulated backlash: use very small reversal sweep and detect plateau around center.
    page.click("#servoTestToggleBtn")
    page.fill("#servoTestStartDeg", "89")
    page.fill("#servoTestEndDeg", "91")
    page.fill("#servoTestRepeat", "2")
    page.fill("#servoTestSpeed", "8")
    page.click("#servoTestAll")
    page.click("#servoTestAll")
    page.check(f'input.servo-test-ch[data-ch="{channel}"]')
    page.click("#servoTestRunBtn")

    bvals: list[float] = []
    bt0 = time.perf_counter()
    while (time.perf_counter() - bt0) < 1.6:
        cmd = page.evaluate("window.__robotDogDebug.getServoCommandDeg()")
        bvals.append(float(cmd.get(str(channel), 0.0)))
        page.wait_for_timeout(60)

    page.click("#servoTestRunBtn")
    page.click("#servoTestToggleBtn")

    backlash = max(0.0, (max(bvals) - min(bvals) - 2.0)) if bvals else 0.0
    return speed_est, latency * 1000.0, backlash


def _update_csv_row(rows: list[dict[str, str]], phase: str, parameter: str, value: float, unit: str, source: str, confidence: int, date_str: str, owner: str, notes: str) -> None:
    value_s = f"{value:.3f}".rstrip("0").rstrip(".")
    for row in rows:
        if row.get("phase") == phase and row.get("parameter") == parameter:
            row.update({
                "value": value_s,
                "unit": unit,
                "source": source,
                "confidence": str(confidence),
                "date": date_str,
                "owner": owner,
                "notes": notes,
            })
            return


def _verify_phase_e(code_root: Path, runner: Path, headless: bool) -> int:
    cmd = [sys.executable, str(runner)]
    if headless:
        cmd.append("--headless")
    cmd.extend(["--only-phase", "E"])
    print("VERIFY:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(code_root))


def main() -> int:
    args = parse_args()
    code_root = Path(args.code_root).resolve()
    page, json_path, csv_path, runner = _paths(code_root)

    if not all(p.exists() for p in [page, json_path, csv_path, runner]):
        print("ERROR: required files missing")
        return 2

    url = f"file://{page}"
    channels = [11, 12, 13]
    speed_vals = []
    latency_vals = []
    backlash_vals = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        pg = browser.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(1400)
        for ch in channels:
            spd, lat, back = _run_channel(pg, ch, args.start, args.end, args.speed)
            speed_vals.append(spd)
            latency_vals.append(lat)
            backlash_vals.append(back)
            print(f"ch{ch}: speed={spd:.2f} deg/s, latency={lat:.2f} ms, backlash={back:.2f} deg")
        browser.close()

    speed_mean = statistics.mean(speed_vals)
    latency_mean = statistics.mean(latency_vals)
    backlash_mean = statistics.mean(backlash_vals)

    print(f"EST mean speed={speed_mean:.2f} deg/s")
    print(f"EST mean latency={latency_mean:.2f} ms")
    print(f"EST mean backlash={backlash_mean:.2f} deg")

    if not args.apply:
        print("DRY-RUN: no JSON/CSV writes")
        return 0

    data = json.loads(json_path.read_text(encoding="utf-8"))
    data.setdefault("servo_dynamics_assumed", {})["max_velocity_deg_per_sec"] = round(speed_mean, 2)
    data.setdefault("servo_dynamics_assumed", {})["command_to_motion_latency_ms"] = round(latency_mean, 2)
    data.setdefault("servo_backlash_estimated", {})["S11_deg"] = round(backlash_vals[0], 3)
    data.setdefault("servo_backlash_estimated", {})["S12_deg"] = round(backlash_vals[1], 3)
    data.setdefault("servo_backlash_estimated", {})["S13_deg"] = round(backlash_vals[2], 3)
    data.setdefault("servo_backlash_estimated", {})["source"] = "SIMULATED_DIGITAL_TWIN"
    data.setdefault("provenance", {})["last_updated"] = "2026-02-26 11:11 CST"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    _update_csv_row(rows, "E", "servo_speed_under_load", speed_mean, "deg_per_sec", "SIMULATED", 55, args.date, args.owner, "Estimated from DigitalTwin servo command progression")
    _update_csv_row(rows, "E", "command_to_motion_latency", latency_mean, "ms", "SIMULATED", 55, args.date, args.owner, "Estimated from click-to-command-change in DigitalTwin")
    _update_csv_row(rows, "F", "backlash_deadband_S11", backlash_vals[0], "deg", "SIMULATED", 40, args.date, args.owner, "Estimated in DigitalTwin low-amplitude reversal test")
    _update_csv_row(rows, "F", "backlash_deadband_S12", backlash_vals[1], "deg", "SIMULATED", 40, args.date, args.owner, "Estimated in DigitalTwin low-amplitude reversal test")
    _update_csv_row(rows, "F", "backlash_deadband_S13", backlash_vals[2], "deg", "SIMULATED", 40, args.date, args.owner, "Estimated in DigitalTwin low-amplitude reversal test")

    fieldnames = ["phase", "parameter", "value", "unit", "source", "confidence", "date", "owner", "notes"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print("APPLY: JSON/CSV updated with simulated P2 estimates")

    if args.verify:
        rc = _verify_phase_e(code_root, runner, args.headless)
        print("VERIFY RESULT:", "PASS" if rc == 0 else f"FAIL (rc={rc})")
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
