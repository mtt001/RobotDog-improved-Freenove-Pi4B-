#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/test_mujoco_ui_gate_playwright.py
Version: v1.0 (2026-02-26 08:50)
Revision History:
- 2026-02-26 08:50 v1.0 - Added MuJoCo-style UI priority gate test with Playwright assertions for controls, telemetry, mode switching, deterministic relax-state replay, and visible error status behavior.
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


REQUIRED_SELECTORS = [
    "#app",
    "canvas",
    "#buildBadge",
    "#frameCheck",
    "#poseReadout",
    "#modeWalkBtn",
    "#modeRelaxBtn",
    "#modeS11SwingBtn",
    "#servoTestToggleBtn",
    "#servoTestPanel",
    "#servoTestStatus",
    "#servoTestRunBtn",
    "#servoTestStartDeg",
    "#servoTestEndDeg",
    "#servoTestRepeat",
    "#servoTestSpeed",
    "#servoTestAll",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MuJoCo-style UI priority gate for Digital Twin page")
    parser.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/pages/freenove_robotdog_3d_render.html",
        help="Target page URL or file:// path.",
    )
    parser.add_argument("--headless", action="store_true", help="Run headless browser.")
    return parser.parse_args()


def _assert_required_selectors(page, logs: list[str]) -> bool:
    missing: list[str] = []
    for selector in REQUIRED_SELECTORS:
        count = page.locator(selector).count()
        if count < 1:
            missing.append(selector)
    if missing:
        logs.append(f"FAIL: missing required selectors: {', '.join(missing)}")
        return False
    logs.append(f"PASS: required selectors present ({len(REQUIRED_SELECTORS)})")
    return True


def _assert_frame_and_pose(page, logs: list[str]) -> bool:
    frame_text = page.locator("#frameCheck").inner_text()
    pose_text = page.locator("#poseReadout").inner_text()
    logs.append(f"frame={frame_text}")
    logs.append(f"pose={pose_text}")
    if "PASS" not in frame_text:
        logs.append("FAIL: frame convention check is not PASS")
        return False
    if not POSE_RE.search(pose_text):
        logs.append("FAIL: pose readout format mismatch")
        return False
    logs.append("PASS: frame and pose telemetry validated")
    return True


def _assert_viewport_interaction_stability(page, logs: list[str]) -> bool:
    canvas = page.locator("canvas").first
    box = canvas.bounding_box()
    if not box:
        logs.append("FAIL: canvas bounding box unavailable")
        return False

    center_x = box["x"] + (box["width"] * 0.5)
    center_y = box["y"] + (box["height"] * 0.5)

    page.mouse.move(center_x, center_y)
    page.mouse.down()
    page.mouse.move(center_x + 110, center_y + 35, steps=10)
    page.mouse.up()
    page.mouse.wheel(0, 480)
    page.wait_for_timeout(250)

    frame_text_after = page.locator("#frameCheck").inner_text()
    pose_text_after = page.locator("#poseReadout").inner_text()
    if "PASS" not in frame_text_after or not POSE_RE.search(pose_text_after):
        logs.append("FAIL: frame/pose telemetry unstable after viewport interaction")
        return False

    logs.append("PASS: viewport interaction keeps telemetry stable")
    return True


def _get_mode(page) -> str:
    return str(page.evaluate("window.__robotDogDebug?.getMode?.() || ''"))


def _get_servo_cmd(page) -> dict:
    return page.evaluate("window.__robotDogDebug?.getServoCommandDeg?.() || {}") or {}


def _assert_mode_switch_and_relax_determinism(page, logs: list[str]) -> bool:
    page.click("#modeWalkBtn")
    page.wait_for_timeout(220)
    mode_walk = _get_mode(page)

    page.click("#modeRelaxBtn")
    page.wait_for_timeout(220)
    mode_relax_1 = _get_mode(page)
    cmd_relax_1 = _get_servo_cmd(page)

    page.click("#modeS11SwingBtn")
    page.wait_for_timeout(220)
    mode_s11 = _get_mode(page)

    page.click("#modeRelaxBtn")
    page.wait_for_timeout(260)
    mode_relax_2 = _get_mode(page)
    cmd_relax_2 = _get_servo_cmd(page)

    logs.append(f"mode_walk={mode_walk}")
    logs.append(f"mode_relax_1={mode_relax_1}")
    logs.append(f"mode_s11={mode_s11}")
    logs.append(f"mode_relax_2={mode_relax_2}")

    relax_keys = ["11", "12", "13", "8", "7", "4", "15"]
    relax_values_1 = [round(float(cmd_relax_1.get(k, 0.0)), 2) for k in relax_keys]
    relax_values_2 = [round(float(cmd_relax_2.get(k, 0.0)), 2) for k in relax_keys]
    logs.append(f"relax_values_1={relax_values_1}")
    logs.append(f"relax_values_2={relax_values_2}")

    mode_ok = mode_walk == "walk" and mode_relax_1 == "relax_90" and mode_s11 == "s11_swing" and mode_relax_2 == "relax_90"
    deterministic_relax = relax_values_1 == relax_values_2 and all(abs(v - 90.0) <= 1.5 for v in relax_values_2)

    if not mode_ok:
        logs.append("FAIL: mode switch sequence mismatch")
        return False
    if not deterministic_relax:
        logs.append("FAIL: relax-state replay is not deterministic near 90 deg")
        return False

    logs.append("PASS: mode switching and relax replay determinism validated")
    return True


def _assert_visible_failure_status(page, logs: list[str]) -> bool:
    page.click("#servoTestToggleBtn")
    page.wait_for_timeout(180)

    panel_hidden = page.evaluate("document.getElementById('servoTestPanel')?.hasAttribute('hidden')")
    toggle_text = page.locator("#servoTestToggleBtn").inner_text()
    if panel_hidden:
        logs.append("FAIL: servo test panel did not open")
        return False

    page.click("#servoTestAll")
    page.click("#servoTestAll")
    page.fill("#servoTestStartDeg", "90")
    page.fill("#servoTestEndDeg", "180")
    page.fill("#servoTestRepeat", "2")
    page.fill("#servoTestSpeed", "8")
    page.click("#servoTestRunBtn")
    page.wait_for_timeout(220)

    status_text = page.locator("#servoTestStatus").inner_text()
    logs.append(f"servo_toggle_text={toggle_text}")
    logs.append(f"servo_status={status_text}")

    if "Select at least one channel" not in status_text:
        logs.append("FAIL: expected visible channel-selection error status not shown")
        return False

    logs.append("PASS: visible failure status behavior validated")
    return True


def run(args: argparse.Namespace) -> tuple[bool, list[str]]:
    logs: list[str] = []

    page_path = args.page.replace("file://", "") if args.page.startswith("file://") else ""
    if page_path and not Path(page_path).exists():
        return False, [f"ERROR: page not found: {page_path}"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        checks = [
            _assert_required_selectors,
            _assert_frame_and_pose,
            _assert_viewport_interaction_stability,
            _assert_mode_switch_and_relax_determinism,
            _assert_visible_failure_status,
        ]

        ok = True
        for check in checks:
            if not check(page, logs):
                ok = False
                break

        browser.close()

    logs.append("PASS: MuJoCo-style UI priority gate passed" if ok else "FAIL: MuJoCo-style UI priority gate failed")
    return ok, logs


def main() -> int:
    ok, logs = run(parse_args())
    for line in logs:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
