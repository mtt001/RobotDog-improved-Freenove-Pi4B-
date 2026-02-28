#!/usr/bin/env python3
"""
File: DigitalTwin/scripts/ext4_performance_audit_playwright.py
Version: v1.0 (2026-02-27 20:06)
Revision History:
- 2026-02-27 20:06 v1.0 - Added EXT-4 performance/frame timing audit with simulation-rate and render-rate metrics exported to JSON.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EXT-4 performance and frame timing audit")
    p.add_argument(
        "--page",
        default="http://127.0.0.1:8766/DigitalTwin/pages/freenove_robotdog_3d_render.html",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--duration-ms", type=int, default=5000)
    p.add_argument(
        "--out-json",
        default="iCloud/AI_Reports/ext4_performance.json",
    )
    return p.parse_args()


def run(args: argparse.Namespace) -> dict:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=args.headless,
            args=["--disable-frame-rate-limit", "--disable-gpu-vsync"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(args.page, wait_until="domcontentloaded")
        page.wait_for_timeout(1300)
        page.click("#modeWalkBtn")
        page.click("#dogForwardBtn")

        tick_0 = int(page.evaluate("window.__robotDogDebug.getHilReport().tick"))
        wall_0 = int(page.evaluate("Date.now()"))

        render = page.evaluate(
            """
            async (durationMs) => {
              const deltas = [];
              let last = performance.now();
              const start = last;
              await new Promise((resolve) => {
                function step(now) {
                  deltas.push(now - last);
                  last = now;
                  if ((now - start) >= durationMs) resolve();
                  else requestAnimationFrame(step);
                }
                requestAnimationFrame(step);
              });
              const vals = deltas.slice(1);
              const mean = vals.reduce((a,b) => a+b, 0) / Math.max(1, vals.length);
              const variance = vals.reduce((a,b) => a + ((b-mean)*(b-mean)), 0) / Math.max(1, vals.length);
              return {
                frame_count: vals.length,
                frame_time_mean_ms: mean,
                frame_time_variance_ms2: variance,
                frame_time_max_ms: Math.max(...vals),
                frame_time_min_ms: Math.min(...vals),
                cpu_spike_proxy_over_25ms: vals.filter(v => v > 25).length,
                render_fps_avg: mean > 0 ? (1000 / mean) : 0,
              };
            }
            """,
            args.duration_ms,
        )

        tick_1 = int(page.evaluate("window.__robotDogDebug.getHilReport().tick"))
        wall_1 = int(page.evaluate("Date.now()"))
        wall_sec = max(1e-6, (wall_1 - wall_0) / 1000.0)
        sim_fps = (tick_1 - tick_0) / wall_sec

        world_inv = page.evaluate("window.__robotDogDebug.getWorldInvariant()")
        browser.close()

    payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M %Z"),
        "url": args.page,
        **render,
        "simulation_fps_avg": sim_fps,
        "goal_gt_55fps": bool(sim_fps > 55.0),
        "world_invariance_ok": bool(world_inv.get("worldInvariant")),
        "world_invariance_last": world_inv,
    }
    return payload


def main() -> int:
    args = parse_args()
    payload = run(args)
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["goal_gt_55fps"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
