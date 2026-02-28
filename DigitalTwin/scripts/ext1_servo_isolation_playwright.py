#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/ext1_servo_isolation_playwright.py
Version: v1.0 (2026-02-27 20:06)
Revision History:
- 2026-02-27 20:06 v1.0 - Added post-success EXT-1 servo stress/isolation sweep for S11/S12/S13 single and combined channels with JSON artifact output.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EXT-1 servo isolation stress test")
    p.add_argument(
        "--page",
        default="http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--samples", type=int, default=34)
    p.add_argument("--sample-ms", type=int, default=80)
    p.add_argument("--tolerance", type=float, default=1.6)
    p.add_argument(
        "--out-json",
        default="iCloud/AI_Reports/ext1_servo_isolation.json",
    )
    return p.parse_args()


def _rng(values: list[float]) -> float:
    return (max(values) - min(values)) if values else 0.0


def run(args: argparse.Namespace) -> dict:
    groups = [[11], [12], [13], [11, 12], [12, 13]]
    channels = [11, 12, 13]
    cases: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1400)

        page.click("#modeRelaxBtn")
        page.click("#dogStopBtn")
        page.wait_for_timeout(260)

        for group in groups:
            page.click("#servoTestToggleBtn")
            page.fill("#servoTestStartDeg", "70")
            page.fill("#servoTestEndDeg", "110")
            page.fill("#servoTestRepeat", "2")
            page.fill("#servoTestSpeed", "8")
            page.evaluate("document.querySelectorAll('input.servo-test-ch').forEach(el => el.checked = false)")
            for ch in group:
                page.check(f'input.servo-test-ch[data-ch="{ch}"]')

            page.click("#servoTestRunBtn")
            page.wait_for_timeout(120)
            st = page.evaluate("window.__robotDogDebug.getServoTestState()") or {}

            sampled = {ch: [] for ch in channels}
            for _ in range(args.samples):
                cmd = page.evaluate("window.__robotDogDebug.getServoCommandDeg()") or {}
                for ch in channels:
                    sampled[ch].append(float(cmd.get(str(ch), 0.0)))
                page.wait_for_timeout(args.sample_ms)

            st_after = page.evaluate("window.__robotDogDebug.getServoTestState()") or {}
            if st_after.get("running"):
                page.click("#servoTestRunBtn")

            selected_range = {str(ch): _rng(sampled[ch]) for ch in group}
            unintended = {str(ch): _rng(sampled[ch]) for ch in channels if ch not in group}
            max_unintended = max(unintended.values()) if unintended else 0.0
            selected_ok = all(v >= 8.0 for v in selected_range.values())
            isolated_ok = max_unintended <= args.tolerance

            cases.append(
                {
                    "group": group,
                    "started_running": bool(st.get("running")),
                    "selected_range_deg": selected_range,
                    "unintended_range_deg": unintended,
                    "max_unintended_deg": max_unintended,
                    "selected_ok": selected_ok,
                    "isolated_ok": isolated_ok,
                }
            )

        browser.close()

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M %Z"),
        "tolerance_deg": args.tolerance,
        "cases": cases,
        "pass": all(c["selected_ok"] and c["isolated_ok"] and c["started_running"] for c in cases),
    }
    return payload


def main() -> int:
    args = parse_args()
    payload = run(args)
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
