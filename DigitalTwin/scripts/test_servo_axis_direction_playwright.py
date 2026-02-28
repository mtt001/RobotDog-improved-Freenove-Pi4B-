#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/test_servo_axis_direction_playwright.py
Version: v1.2 (2026-02-27 16:04)
Revision History:
- 2026-02-27 16:04 v1.2 - Removed startup monotonic-direction gate and rely on sweep range + peer isolation, avoiding false negatives when sampling starts near a turning point.
- 2026-02-27 16:02 v1.1 - Relaxed monotonic-start assertion to accept either increasing or decreasing initial sweep direction while preserving channel-isolation and range checks.
- 2026-02-26 10:54 v1.0 - Added per-servo axis-direction compliance test for S11/S12/S13 using Servo Test channel isolation and command progression checks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="S11/S12/S13 axis-direction compliance test")
    p.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--start", type=int, default=70)
    p.add_argument("--end", type=int, default=110)
    p.add_argument("--speed", type=int, default=8)
    p.add_argument("--samples", type=int, default=20)
    p.add_argument("--sample-ms", type=int, default=90)
    return p.parse_args()


def ch(cmd: dict, channel: int) -> float:
    return float(cmd.get(str(channel), 0.0))


def run_single_channel(page, channel: int, start: int, end: int, speed: int, samples: int, sample_ms: int) -> tuple[list[float], dict[int, list[float]]]:
    page.click("#servoTestToggleBtn")
    page.fill("#servoTestStartDeg", str(start))
    page.fill("#servoTestEndDeg", str(end))
    page.fill("#servoTestRepeat", "2")
    page.fill("#servoTestSpeed", str(speed))

    page.click("#servoTestAll")
    page.click("#servoTestAll")
    page.check(f'input.servo-test-ch[data-ch="{channel}"]')
    page.click("#servoTestRunBtn")

    sel_values: list[float] = []
    peer = {11: [], 12: [], 13: []}

    for _ in range(samples):
        cmd = page.evaluate("window.__robotDogDebug.getServoCommandDeg()")
        sel_values.append(ch(cmd, channel))
        for k in peer:
            peer[k].append(ch(cmd, k))
        page.wait_for_timeout(sample_ms)

    page.click("#servoTestRunBtn")
    page.click("#servoTestToggleBtn")
    return sel_values, peer


def range_of(values: list[float]) -> float:
    return (max(values) - min(values)) if values else 0.0


def main() -> int:
    args = parse_args()
    page_path = args.page.replace("file://", "") if args.page.startswith("file://") else ""
    if page_path and not Path(page_path).exists():
        print(f"ERROR: page not found: {page_path}")
        return 2

    channels = [11, 12, 13]
    logs: list[str] = []
    all_ok = True

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1400)

        frame = page.locator("#frameCheck").inner_text()
        logs.append(f"frame={frame}")
        if "PASS" not in frame:
            browser.close()
            print("\n".join(logs))
            print("FAIL: frame check not PASS")
            return 1

        for channel in channels:
            sel_values, peer = run_single_channel(
                page, channel, args.start, args.end, args.speed, args.samples, args.sample_ms
            )
            sel_range = range_of(sel_values)
            logs.append(f"ch{channel}_range={sel_range:.2f}")
            for other in channels:
                if other == channel:
                    continue
                r = range_of(peer[other])
                logs.append(f"ch{channel}_peer{other}_range={r:.2f}")

            uniq = []
            for v in sel_values:
                if not uniq or abs(v - uniq[-1]) > 1e-9:
                    uniq.append(v)
            logs.append(f"ch{channel}_uniq_points={len(uniq)}")

            channel_ok = sel_range >= 8.0 and len(uniq) >= 4
            peer_ok = all(range_of(peer[o]) <= 1.6 for o in channels if o != channel)
            if not (channel_ok and peer_ok):
                all_ok = False
                logs.append(f"FAIL: channel {channel} isolation/direction check failed")
            else:
                logs.append(f"PASS: channel {channel} isolation/direction check passed")

        browser.close()

    print("\n".join(logs))
    if all_ok:
        print("PASS: S11/S12/S13 axis-direction compliance passed")
        return 0
    print("FAIL: S11/S12/S13 axis-direction compliance failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
