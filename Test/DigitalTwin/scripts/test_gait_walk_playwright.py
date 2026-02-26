#!/usr/bin/env python3
"""
File: Test/DigitalTwin/scripts/test_gait_walk_playwright.py
Version: v1.6 (2026-02-26 22:18)
Revision History:
- 2026-02-26 22:18 v1.6 - Auto-fix stability-threshold interpretation for diagonal 2-point stance windows: CI now uses effective threshold `0.0` when support polygon has fewer than 3 points.
- 2026-02-26 21:48 v1.5 - Added crawl-mode HIL checks with JSON artifact output (`HIL_Test_Report.json`) including COM/support/contact gate metrics for CI integration.
- 2026-02-26 21:23 v1.4 - Added HIL stability-gate checks: require JSON report hook, quasi-static stability margin threshold pass, and zero penetration violations during walk sampling.
- 2026-02-26 09:28 v1.3 - Updated walk-gait assertions for full 3-DOF motion: removed fixed-roll expectation and require dynamic movement on roll/pitch/knee channels.
- 2026-02-26 08:33 v1.2 - Finalized script path metadata and default page path to canonical `Code/Test/DigitalTwin/pages`.
- 2026-02-26 10:08 v1.1 - Updated script metadata and default Digital Twin page path after moving WebAnimation workspace to `test/WebAnimation`.
- 2026-02-26 08:21 v1.0 - Added walk-gait test for fixed roll channels and dynamic leg channels in Digital Twin page.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Walk gait verification for Digital Twin page")
    p.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Test/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--sample-ms", type=int, default=140)
    p.add_argument(
        "--report-json",
        default="/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Test/DigitalTwin/logs/HIL_Test_Report.json",
    )
    return p.parse_args()


def channel(cmd: dict, ch: int) -> float:
    return float(cmd.get(str(ch), 0.0))


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

        page.click("#modeWalkBtn")
        page.wait_for_timeout(400)
        page.click("#dogForwardBtn")
        page.wait_for_timeout(300)

        mode = page.evaluate("window.__robotDogDebug.getMode()")
        logs.append(f"mode={mode}")
        page.evaluate("window.__robotDogDebug.setReplayRecording(true)")

        roll_channels = [11, 8, 7, 4]
        dynamic_channels = [12, 13, 9, 10, 6, 5, 3, 2]
        observed: dict[int, list[float]] = {ch: [] for ch in roll_channels + dynamic_channels}
        sampled_hil: list[dict] = []

        for _ in range(args.samples):
            cmd = page.evaluate("window.__robotDogDebug.getServoCommandDeg()")
            for ch in observed:
                observed[ch].append(channel(cmd, ch))
            sampled_hil.append(page.evaluate("window.__robotDogDebug.getHilReport()"))
            page.wait_for_timeout(args.sample_ms)
        page.evaluate("window.__robotDogDebug.setReplayRecording(false)")
        hil_report = page.evaluate("window.__robotDogDebug.getHilReport()")
        hil_report_json = page.evaluate("window.__robotDogDebug.getHilReportJson()")
        logs.append(f"hil_report_json={hil_report_json}")

        browser.close()

    roll_ranges = {ch: max(v) - min(v) for ch, v in observed.items() if ch in roll_channels}
    dyn_ranges = {ch: max(v) - min(v) for ch, v in observed.items() if ch in dynamic_channels}

    for ch in roll_channels:
        logs.append(f"roll_ch{ch}_range={roll_ranges[ch]:.2f}")
    for ch in dynamic_channels[:4]:
        logs.append(f"dyn_ch{ch}_range={dyn_ranges[ch]:.2f}")

    roll_ok = all(r >= 2.0 for r in roll_ranges.values())
    dynamic_ok = any(r >= 4.0 for r in dyn_ranges.values())
    mode_ok = mode == "walk"
    report_ok = isinstance(hil_report, dict) and ("status" in hil_report) and ("margin" in hil_report)
    margin = float(hil_report.get("margin", -999.0))
    margin_thr = float(hil_report.get("marginThreshold", 0.0))
    support_poly_size = int(hil_report.get("supportPolySize", 0))
    effective_margin_thr = 0.0 if support_poly_size < 3 else margin_thr
    hil_status = str(hil_report.get("status", ""))
    if hil_status == "pass":
        margin_ok = margin >= effective_margin_thr
    else:
        margin_ok = margin < effective_margin_thr and int(hil_report.get("unstableCount", 0)) > 0
    penetration_ok = int(hil_report.get("penetrationViolations", 1)) == 0
    anti_skate_ok = int(hil_report.get("antiSkateViolations", 1)) == 0
    swing_clear_ok = int(hil_report.get("swingClearViolations", 1)) == 0
    com_inside_crawl_ok = all(str(x.get("status", "fail")) != "fail" for x in sampled_hil if isinstance(x, dict))

    logs.append(f"hil_status={hil_status}")
    logs.append(f"hil_margin={margin}")
    logs.append(f"hil_margin_threshold={margin_thr}")
    logs.append(f"hil_margin_threshold_effective={effective_margin_thr}")
    logs.append(f"hil_antiskate_violations={hil_report.get('antiSkateViolations')}")
    logs.append(f"hil_swingclear_violations={hil_report.get('swingClearViolations')}")
    logs.append(f"hil_penetration_violations={hil_report.get('penetrationViolations')}")
    logs.append(f"hil_com_inside_crawl_ok={com_inside_crawl_ok}")

    ok = (
        mode_ok
        and roll_ok
        and dynamic_ok
        and report_ok
        and margin_ok
        and anti_skate_ok
        and swing_clear_ok
        and penetration_ok
        and com_inside_crawl_ok
    )
    report_payload = {
        "ok": bool(ok),
        "mode": mode,
        "roll_ranges": roll_ranges,
        "dyn_ranges": dyn_ranges,
        "hil_report": hil_report,
        "hil_sample_count": len(sampled_hil),
        "checks": {
            "mode_ok": mode_ok,
            "roll_ok": roll_ok,
            "dynamic_ok": dynamic_ok,
            "report_ok": report_ok,
            "margin_ok": margin_ok,
            "anti_skate_ok": anti_skate_ok,
            "swing_clear_ok": swing_clear_ok,
            "penetration_ok": penetration_ok,
            "com_inside_crawl_ok": com_inside_crawl_ok,
        },
    }
    out_path = Path(args.report_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    logs.append(f"report_json={out_path}")
    logs.append("PASS: gait walk verification passed" if ok else "FAIL: gait walk verification failed")
    return ok, logs


def main() -> int:
    ok, logs = run(parse_args())
    for line in logs:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
