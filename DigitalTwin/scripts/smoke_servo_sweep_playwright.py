#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/smoke_servo_sweep_playwright.py
Version: v1.2 (2026-02-26 08:33)
Revision History:
- 2026-02-26 08:33 v1.2 - Finalized path migration to `Code/DigitalTwin` and updated default page location to the canonical `DigitalTwin/pages` path.
- 2026-02-26 10:08 v1.1 - Updated script path metadata and default target page to relocated Digital Twin page under `test/WebAnimation/DigitalTwin/pages`.
- 2026-02-26 07:59 v1.0 - Added Playwright smoke test for Temp web animation servo sweep smoothness and channel isolation checks.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass
class SweepResult:
    samples: list[float]
    uniq: list[float]
    diffs: list[float]
    status_text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test for servo sweep smoothness in Digital Twin animation page."
    )
    parser.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/pages/freenove_robotdog_3d_render.html",
        help="Target page URL or file:// path.",
    )
    parser.add_argument("--channel", type=int, default=11, help="Servo channel to test.")
    parser.add_argument("--start", type=int, default=90, help="Start degree.")
    parser.add_argument("--end", type=int, default=180, help="End degree.")
    parser.add_argument("--repeat", type=int, default=2, help="Repeat count.")
    parser.add_argument("--speed", type=int, default=8, help="Speed value (1-20).")
    parser.add_argument("--samples", type=int, default=30, help="Sample count.")
    parser.add_argument("--sample-ms", type=int, default=80, help="Sample interval ms.")
    parser.add_argument("--headless", action="store_true", help="Run headless browser.")
    return parser.parse_args()


def _read_state(page) -> dict:
    return page.evaluate(
        "window.__robotDogDebug && window.__robotDogDebug.getServoTestState ? "
        "window.__robotDogDebug.getServoTestState() : null"
    ) or {}


def _prepare_panel(page, args: argparse.Namespace) -> None:
    page.click("#servoTestToggleBtn")
    page.fill("#servoTestStartDeg", str(args.start))
    page.fill("#servoTestEndDeg", str(args.end))
    page.fill("#servoTestRepeat", str(args.repeat))
    page.fill("#servoTestSpeed", str(args.speed))

    page.click("#servoTestAll")
    page.click("#servoTestAll")
    page.check(f'input.servo-test-ch[data-ch="{args.channel}"]')
    page.click("#servoTestRunBtn")


def run_sweep_check(args: argparse.Namespace) -> SweepResult:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        _prepare_panel(page, args)

        samples: list[float] = []
        for _ in range(args.samples):
            state = _read_state(page)
            if state:
                samples.append(float(state.get("currentDeg", 0.0)))
            page.wait_for_timeout(args.sample_ms)

        status_text = page.locator("#servoTestStatus").inner_text()
        browser.close()

    uniq: list[float] = []
    for value in samples:
        if not uniq or abs(value - uniq[-1]) > 1e-9:
            uniq.append(value)

    diffs = [round(uniq[i] - uniq[i - 1], 4) for i in range(1, len(uniq))]
    return SweepResult(samples=samples, uniq=uniq, diffs=diffs, status_text=status_text)


def main() -> int:
    args = parse_args()

    page_path = args.page.replace("file://", "") if args.page.startswith("file://") else None
    if page_path and not Path(page_path).exists():
        print(f"ERROR: target page not found: {page_path}")
        return 2

    try:
        result = run_sweep_check(args)
    except PlaywrightTimeoutError as exc:
        print(f"ERROR: Playwright timeout: {exc}")
        return 3
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: unexpected failure: {exc}")
        return 4

    if not result.samples:
        print("FAIL: no servo samples captured")
        return 5

    unique_diffs = sorted(set(result.diffs))
    monotonic_positive = all(d > 0 for d in result.diffs[: min(12, len(result.diffs))]) if result.diffs else False
    smooth_step_like = any(abs(abs(d) - 2.0) < 1e-6 for d in unique_diffs)

    print("Servo Sweep Smoke Result")
    print(f"- samples_captured: {len(result.samples)}")
    print(f"- uniq_points: {len(result.uniq)}")
    print(f"- first_samples: {[int(v) for v in result.samples[:16]]}")
    print(f"- first_uniq: {[int(v) for v in result.uniq[:16]]}")
    print(f"- diff_set: {unique_diffs}")
    if result.samples:
        print(f"- sample_mean: {statistics.mean(result.samples):.2f}")
    print(f"- status: {result.status_text}")

    if not smooth_step_like:
        print("FAIL: smooth step signature (2-degree increments) not detected")
        return 6
    if not monotonic_positive:
        print("WARN: initial segment not strictly monotonic positive; verify manually")

    print("PASS: smooth servo sweep behavior detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
