#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/test_imu_feedback_playwright.py
Version: v1.2 (2026-02-26 08:33)
Revision History:
- 2026-02-26 08:33 v1.2 - Finalized script path metadata and default page path to canonical `Code/DigitalTwin/pages`.
- 2026-02-26 10:08 v1.1 - Updated script metadata and default page path for relocated Digital Twin workspace under `test/WebAnimation`.
- 2026-02-26 08:21 v1.0 - Added IMU/pose readout validation script to verify frame PASS state and numeric ENU/FLU telemetry text rendering.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

POSE_RE = re.compile(
    r"Pose ENU XYZ=\(([-\d.]+), ([-\d.]+), ([-\d.]+)\) \| FLU RPY=\(([-\d.]+)°, ([-\d.]+)°, ([-\d.]+)°\)"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IMU/pose text verification for Digital Twin page")
    p.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    return p.parse_args()


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

        frame_text = page.locator("#frameCheck").inner_text()
        pose_text_1 = page.locator("#poseReadout").inner_text()
        page.wait_for_timeout(400)
        pose_text_2 = page.locator("#poseReadout").inner_text()

        browser.close()

    logs.append(f"frame={frame_text}")
    logs.append(f"pose_1={pose_text_1}")
    logs.append(f"pose_2={pose_text_2}")

    if "PASS" not in frame_text:
        return False, logs + ["FAIL: frame convention check is not PASS"]

    m1 = POSE_RE.search(pose_text_1)
    m2 = POSE_RE.search(pose_text_2)
    if not m1 or not m2:
        return False, logs + ["FAIL: pose readout format mismatch"]

    values = [float(x) for x in m1.groups() + m2.groups()]
    finite_ok = all(abs(v) < 10000 for v in values)
    rpy_ok = all(-360.0 <= float(v) <= 360.0 for v in (m1.group(4), m1.group(5), m1.group(6), m2.group(4), m2.group(5), m2.group(6)))

    ok = finite_ok and rpy_ok
    logs.append("PASS: IMU/pose readout verification passed" if ok else "FAIL: IMU/pose readout verification failed")
    return ok, logs


def main() -> int:
    ok, logs = run(parse_args())
    for line in logs:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
