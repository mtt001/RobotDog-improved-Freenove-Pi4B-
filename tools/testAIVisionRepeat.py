#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test AI Vision stability by sending the exact same image multiple times.

Usage:
  python testAIVisionRepeat.py /path/to/image.jpg --runs 3

Notes:
  - Requires OPENAI_API_KEY in environment.
  - Uses mtBallDetectAI.AIVisionBallDetector.
"""

import argparse
import json
import os
import sys
import time
from typing import List

import cv2

from vision.legacy.mtBallDetectAI import AIVisionBallDetector, AICircle


def _format_circles(circles: List[AICircle]) -> str:
    return json.dumps(
        [
            {
                "x": round(c.x, 2),
                "y": round(c.y, 2),
                "r": round(c.r, 2),
                "score": round(c.score, 3),
            }
            for c in circles
        ],
        ensure_ascii=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Repeat AI Vision on same image.")
    parser.add_argument("image", help="Path to image file (jpg/png)")
    parser.add_argument("--runs", type=int, default=3, help="Number of repeats")
    parser.add_argument("--sleep", type=float, default=0.5, help="Delay between runs (s)")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("[ERR] OPENAI_API_KEY not set")
        return 2

    img = cv2.imread(args.image)
    if img is None:
        print(f"[ERR] Failed to read image: {args.image}")
        return 3

    detector = AIVisionBallDetector()
    all_results: List[List[AICircle]] = []

    for i in range(args.runs):
        print(f"\n=== Run {i + 1}/{args.runs} ===")
        circles = detector.analyze(img)
        all_results.append(circles)
        if detector.last_error:
            print(f"[AI] Error: {detector.last_error}")
        if detector.last_latency_s is not None:
            print(f"[AI] Latency: {detector.last_latency_s:.2f}s")
        if detector.last_raw_text:
            print("[AI] Raw response:\n" + detector.last_raw_text)
        print("[AI] Parsed circles:", _format_circles(circles))
        time.sleep(max(0.0, float(args.sleep)))

    # Simple stability summary: compare normalized tuples (x,y,r)
    print("\n=== Stability Summary ===")
    if not all_results:
        print("No results")
        return 0

    base = all_results[0]
    for i, circles in enumerate(all_results):
        if not circles and not base:
            print(f"Run {i + 1}: both empty")
            continue
        if not circles or not base:
            print(f"Run {i + 1}: mismatch (one empty)")
            continue
        # Compare best (highest score) circle only
        best = max(circles, key=lambda c: c.score)
        best0 = max(base, key=lambda c: c.score)
        dx = best.x - best0.x
        dy = best.y - best0.y
        dr = best.r - best0.r
        print(
            f"Run {i + 1}: best Δx={dx:.2f}, Δy={dy:.2f}, Δr={dr:.2f}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
