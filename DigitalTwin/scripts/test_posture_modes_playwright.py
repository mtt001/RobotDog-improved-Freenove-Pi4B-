#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/test_posture_modes_playwright.py
Version: v1.2 (2026-02-26 08:33)
Revision History:
- 2026-02-26 08:33 v1.2 - Finalized script path metadata and default page path to canonical `Code/DigitalTwin/pages`.
- 2026-02-26 10:08 v1.1 - Updated script metadata and default test page path for relocated `test/WebAnimation/DigitalTwin/pages` workspace layout.
- 2026-02-26 08:21 v1.0 - Added posture mode regression test for Walk/RELAX/S11 Swing with debug-mode and servo-command assertions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Posture mode regression test for Digital Twin page")
    p.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    return p.parse_args()


def get_mode(page) -> str:
    return page.evaluate("window.__robotDogDebug.getMode()")


def get_cmd(page) -> dict:
    return page.evaluate("window.__robotDogDebug.getServoCommandDeg()")


def channel_value(cmd: dict, ch: int) -> float:
    return float(cmd.get(str(ch), 0.0))


def approx(v: float, target: float, tol: float = 1.5) -> bool:
    return abs(v - target) <= tol


def run(args: argparse.Namespace) -> tuple[bool, list[str]]:
    logs: list[str] = []

    page_path = args.page.replace("file://", "") if args.page.startswith("file://") else ""
    if page_path and not Path(page_path).exists():
        return False, [f"ERROR: page not found: {page_path}"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        frame = page.locator("#frameCheck").inner_text()
        logs.append(f"frame_check={frame}")
        if "PASS" not in frame:
            browser.close()
            return False, logs + ["FAIL: frame check not PASS"]

        page.click("#modeRelaxBtn")
        page.wait_for_timeout(400)
        mode_relax = get_mode(page)
        cmd_relax = get_cmd(page)
        logs.append(f"mode_relax={mode_relax}")
        for ch in [11, 12, 13, 8, 7, 4, 15]:
            logs.append(f"relax_ch{ch}={channel_value(cmd_relax, ch):.2f}")

        relax_ok = mode_relax == "relax_90" and all(approx(channel_value(cmd_relax, ch), 90.0) for ch in [11, 12, 13, 8, 7, 4, 15])
        if not relax_ok:
            browser.close()
            return False, logs + ["FAIL: RELAX mode values are not near 90deg"]

        page.click("#modeS11SwingBtn")
        page.wait_for_timeout(300)
        mode_s11 = get_mode(page)
        logs.append(f"mode_s11={mode_s11}")
        if mode_s11 != "s11_swing":
            browser.close()
            return False, logs + ["FAIL: S11 Swing mode not active"]

        s11_values: list[float] = []
        s12_values: list[float] = []
        s13_values: list[float] = []
        for _ in range(12):
            cmd = get_cmd(page)
            s11_values.append(channel_value(cmd, 11))
            s12_values.append(channel_value(cmd, 12))
            s13_values.append(channel_value(cmd, 13))
            page.wait_for_timeout(120)

        s11_range = max(s11_values) - min(s11_values)
        s12_range = max(s12_values) - min(s12_values)
        s13_range = max(s13_values) - min(s13_values)
        logs.append(f"s11_range={s11_range:.2f}")
        logs.append(f"s12_range={s12_range:.2f}")
        logs.append(f"s13_range={s13_range:.2f}")

        page.click("#modeWalkBtn")
        page.wait_for_timeout(300)
        mode_walk = get_mode(page)
        logs.append(f"mode_walk={mode_walk}")

        browser.close()

    ok = (
        mode_walk == "walk"
        and s11_range > 8.0
        and s12_range < 1.5
        and s13_range < 1.5
    )
    if not ok:
        logs.append("FAIL: posture transitions or S11-only swing isolation failed")
    else:
        logs.append("PASS: posture mode regression passed")
    return ok, logs


def main() -> int:
    ok, logs = run(parse_args())
    for line in logs:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
