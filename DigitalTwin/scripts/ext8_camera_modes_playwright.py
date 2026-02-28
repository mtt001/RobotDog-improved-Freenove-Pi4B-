#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/ext8_camera_modes_playwright.py
Version: v1.1 (2026-02-27 20:13)
Revision History:
- 2026-02-27 20:13 v1.1 - Fixed Playwright mode setter evaluation call signature to pass argument safely.
- 2026-02-27 20:06 v1.0 - Added EXT-8 camera mode switch audit for FOLLOW/FREE/FPV/HORIZON/TOPDOWN with invariance checks.
"""

from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EXT-8 advanced camera modes audit")
    p.add_argument(
        "--page",
        default="http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--out-md", default="iCloud/AI_Reports/ext8_camera_modes.md")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    modes = ["FOLLOW", "FREE", "FPV", "HORIZON", "TOPDOWN", "FOLLOW"]
    rows: list[tuple[str, str, float, bool]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1400)
        page.click("#modeWalkBtn")
        page.click("#dogForwardBtn")

        prev = page.evaluate("window.__robotDogDebug.getCameraState()")
        for mode in modes:
            got = page.evaluate("(m) => window.__robotDogDebug.setCameraMode(m)", mode)
            page.wait_for_timeout(420)
            cur = page.evaluate("window.__robotDogDebug.getCameraState()")
            delta = math.dist(
                [prev["cameraPos"]["x"], prev["cameraPos"]["y"], prev["cameraPos"]["z"]],
                [cur["cameraPos"]["x"], cur["cameraPos"]["y"], cur["cameraPos"]["z"]],
            )
            inv = page.evaluate("window.__robotDogDebug.getWorldInvariant()")
            rows.append((mode, str(got), delta, bool(inv.get("worldInvariant"))))
            prev = cur

        browser.close()

    out = Path(args.out_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# EXT-8 Advanced Camera Modes",
        "",
        f"- Timestamp: {time.strftime('%Y-%m-%d %H:%M %Z')}",
        f"- URL: {args.page}",
        "",
        "| Requested | Applied | Camera delta | World invariant |",
        "|---|---|---:|---|",
    ]
    ok = True
    for req, applied, delta, inv_ok in rows:
        line_ok = (req == applied) and inv_ok
        ok = ok and line_ok
        lines.append(f"| {req} | {applied} | {delta:.4f} | {'PASS' if inv_ok else 'FAIL'} |")
    lines.append("")
    lines.append(f"- Overall: {'PASS' if ok else 'FAIL'}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out.read_text())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
