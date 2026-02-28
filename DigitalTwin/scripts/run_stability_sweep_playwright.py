#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/run_stability_sweep_playwright.py
Version: v1.0 (2026-02-27 06:59)
Revision History:
- 2026-02-27 06:59 v1.0 - Added 27-case deterministic gait stability sweep (stride/speed/duty variations) with JSON report output for pre-torque validation.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run 3x3x3 Digital Twin stability sweep")
    p.add_argument(
        "--page",
        default="file:///Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--samples", type=int, default=18)
    p.add_argument("--sample-ms", type=int, default=120)
    p.add_argument("--warmup-ms", type=int, default=1200)
    p.add_argument(
        "--report-json",
        default="/Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/DigitalTwin/logs/Stability_Sweep_Report.json",
    )
    return p.parse_args()


def _sample_case(page, page_url: str, cfg: dict[str, float], samples: int, sample_ms: int, warmup_ms: int) -> dict:
    page.goto(page_url, wait_until="domcontentloaded")
    page.wait_for_timeout(warmup_ms)
    page.evaluate("window.__robotDogDebug.resetGaitTuning()")
    page.evaluate(
        "(cfg) => window.__robotDogDebug.setGaitTuning(cfg)",
        {
            "strideScale": cfg["stride_scale"],
            "forwardSpeedScale": cfg["forward_speed_scale"],
            "dutyFactorOffset": cfg["duty_factor_offset"],
        },
    )

    page.click("#modeWalkBtn")
    page.wait_for_timeout(120)
    page.click("#dogForwardBtn")
    page.wait_for_timeout(250)

    margins: list[float] = []
    anti_phase_flag = False
    swing_error = False
    penetration_flag = False
    anti_skate_flag = False

    for _ in range(samples):
        report = page.evaluate("window.__robotDogDebug.getHilReport()")
        margins.append(float(report.get("margin", 0.0)))
        anti_phase_flag = anti_phase_flag or int(report.get("antiPhaseViolations", 0)) > 0
        swing_error = swing_error or int(report.get("swingClearViolations", 0)) > 0
        penetration_flag = penetration_flag or int(report.get("penetrationViolations", 0)) > 0
        anti_skate_flag = anti_skate_flag or int(report.get("antiSkateViolations", 0)) > 0
        page.wait_for_timeout(sample_ms)

    min_margin = min(margins) if margins else float("-inf")
    mean_margin = statistics.fmean(margins) if margins else float("-inf")
    return {
        **cfg,
        "support_margin": min_margin,
        "mean_margin": mean_margin,
        "anti_phase_flag": anti_phase_flag,
        "anti_skate_flag": anti_skate_flag,
        "swing_error": swing_error,
        "penetration_flag": penetration_flag,
    }


def run(args: argparse.Namespace) -> tuple[dict, list[str]]:
    logs: list[str] = []

    page_path = args.page.replace("file://", "") if args.page.startswith("file://") else ""
    if page_path and not Path(page_path).exists():
        raise FileNotFoundError(f"page not found: {page_path}")

    stride_scales = [0.9, 1.0, 1.1]
    speed_scales = [0.9, 1.0, 1.1]
    duty_offsets = [-0.036, 0.0, 0.036]

    results: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(args.page, wait_until="domcontentloaded")

        for stride in stride_scales:
            for speed in speed_scales:
                for duty in duty_offsets:
                    cfg = {
                        "stride_scale": stride,
                        "forward_speed_scale": speed,
                        "duty_factor_offset": duty,
                    }
                    case = _sample_case(page, args.page, cfg, args.samples, args.sample_ms, args.warmup_ms)
                    results.append(case)
                    logs.append(
                        "case stride={:.2f} speed={:.2f} duty={:+.3f} margin={:.4f} anti_phase={} swing_error={} penetration={}".format(
                            stride,
                            speed,
                            duty,
                            case["support_margin"],
                            case["anti_phase_flag"],
                            case["swing_error"],
                            case["penetration_flag"],
                        )
                    )

        browser.close()

    worst_case_margin = min(float(x["support_margin"]) for x in results)
    mean_margin = statistics.fmean(float(x["mean_margin"]) for x in results)
    failing = [
        x
        for x in results
        if float(x["support_margin"]) < 0.18
        or bool(x["anti_phase_flag"])
        or bool(x["penetration_flag"])
        or bool(x["swing_error"])
    ]
    ready = (
        worst_case_margin >= 0.18
        and all(not x["anti_phase_flag"] for x in results)
        and all(not x["penetration_flag"] for x in results)
    )
    recommendations: list[str] = []
    if not ready:
        if worst_case_margin < 0.18:
            recommendations.append("Increase stance width or reduce stride amplitude to expand support margin.")
            recommendations.append("Shift nominal COM toward stance midpoint by adjusting body X/Z bias.")
            recommendations.append("Increase duty factor slightly to keep >=3-point support for longer windows.")
        if any(x["anti_phase_flag"] for x in results):
            recommendations.append("Re-check diagonal phase offsets to enforce FR+RL in-phase and FL+RR anti-phase.")
        if any(x["penetration_flag"] for x in results):
            recommendations.append("Raise swing clearance floor or reduce body bob amplitude to prevent foot penetration.")

    payload = {
        "status": "READY_FOR_TORQUE_PROXY" if ready else "REFINE",
        "combinations": len(results),
        "worst_case_margin": worst_case_margin,
        "mean_margin": mean_margin,
        "results": results,
        "failing_configurations": failing,
        "recommendations": recommendations,
    }

    out_path = Path(args.report_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logs.append(f"report_json={out_path}")
    logs.append(f"worst_case_margin={worst_case_margin:.4f}")
    logs.append(f"mean_margin={mean_margin:.4f}")
    logs.append(f"decision={payload['status']}")
    return payload, logs


def main() -> int:
    try:
        _, logs = run(parse_args())
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: {exc}")
        return 1
    for line in logs:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
