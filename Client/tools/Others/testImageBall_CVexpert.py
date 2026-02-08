#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cv2
import numpy as np


def detect_red_ball(img_bgr):
    """Return (cx, cy, r, area, circularity), plus the binary mask used.

    This is intentionally conservative: it avoids "background circles" (e.g. wood reflections)
    by using Lab 'a' (redness) + saturation gating, then scoring by circularity/fill.
    """

    h, w = img_bgr.shape[:2]

    # --- Primary mask: Lab 'a' channel (green<->red) is much more stable than HSV here.
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    _, a, _ = cv2.split(lab)

    # Dynamic threshold: focus on the most "red" pixels in the frame.
    a_thr = int(max(155, float(np.percentile(a, 97))))
    mask_lab = (a >= a_thr).astype(np.uint8) * 255

    # Saturation/value gate to reduce false positives on dull/brown surfaces.
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    mask_sv = ((s >= 60) & (v >= 40)).astype(np.uint8) * 255

    mask = cv2.bitwise_and(mask_lab, mask_sv)

    # Clean-up
    mask = cv2.medianBlur(mask, 5)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = -1.0

    img_area = float(h * w)
    max_r = 0.40 * float(min(h, w))

    for c in cnts:
        area = float(cv2.contourArea(c))
        if area < 800 or area > img_area * 0.15:
            continue

        peri = float(cv2.arcLength(c, True))
        if peri <= 1e-6:
            continue

        circ = 4.0 * np.pi * area / (peri * peri)
        if circ < 0.55:
            continue

        (cx, cy), r = cv2.minEnclosingCircle(c)
        if r < 10 or r > max_r:
            continue

        # How well the contour fills its enclosing circle (1.0 for a solid circle)
        fill = area / (np.pi * r * r) if r > 1e-6 else 0.0
        if fill < 0.55:
            continue

        # Score prefers: large + circular + well-filled
        score = area * circ * fill
        if score > best_score:
            best_score = score
            best = (cx, cy, r, area, circ)

    # Optional refinement: snap circle to strong edges inside the found ROI.
    if best is not None:
        cx, cy, r, area, circ = best
        refined = refine_circle_edges(img_bgr, cx, cy, r)
        if refined is not None:
            cx2, cy2, r2 = refined
            best = (cx2, cy2, r2, area, circ)

        # Use a slightly inflated radius as a safer ROI for downstream refinement.
        cx, cy, r, area, circ = best
        best = (cx, cy, float(r) * 1.10, area, circ)

    return best, mask


def refine_circle_edges(img_bgr, cx, cy, r):
    """Try to refine (cx,cy,r) using edges + constrained HoughCircles in a local ROI."""

    h, w = img_bgr.shape[:2]
    pad = int(max(20, round(r * 1.6)))
    x0 = max(0, int(round(cx)) - pad)
    y0 = max(0, int(round(cy)) - pad)
    x1 = min(w, int(round(cx)) + pad)
    y1 = min(h, int(round(cy)) + pad)

    roi = img_bgr[y0:y1, x0:x1]
    if roi.size == 0:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 1.5)

    min_r = int(max(8, round(r * 0.70)))
    max_r = int(round(r * 1.35))

    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, int(round(r))),
        param1=120,
        param2=24,
        minRadius=min_r,
        maxRadius=max_r,
    )

    if circles is None:
        return None

    circles = np.round(circles[0, :]).astype(int)
    target = np.array([int(round(cx)) - x0, int(round(cy)) - y0], dtype=np.float32)

    best = None
    best_d = 1e9
    for x, y, rr in circles:
        d = float(np.linalg.norm(np.array([x, y], dtype=np.float32) - target))
        if d < best_d:
            best_d = d
            best = (x, y, rr)

    if best is None:
        return None

    x, y, rr = best
    # Require the refined center to be reasonably close to initial center.
    if best_d > max(30.0, 0.6 * float(r)):
        return None

    # Slightly inflate to behave like a safe ROI (as you requested).
    rr = int(round(rr * 1.08))
    return (float(x + x0), float(y + y0), float(rr))


def main():
    in_files = ["TestImageBallFloor.png", "TestImageBallGlass.png"]
    out_dir = "."  # Save output in the same directory as the script

    for fn in in_files:
        img = cv2.imread(fn)
        if img is None:
            print("ERR read", fn)
            continue
        h, w = img.shape[:2]
        det, mask = detect_red_ball(img)

        out = img.copy()

        # Embed a small alpha mask thumbnail in top-left (debug)
        m_small = cv2.resize(mask, (max(1, w // 4), max(1, h // 4)), interpolation=cv2.INTER_NEAREST)
        m_small_bgr = cv2.cvtColor(m_small, cv2.COLOR_GRAY2BGR)
        out[0 : m_small_bgr.shape[0], 0 : m_small_bgr.shape[1]] = cv2.addWeighted(
            out[0 : m_small_bgr.shape[0], 0 : m_small_bgr.shape[1]], 0.6, m_small_bgr, 0.4, 0
        )

        if det is None:
            cv2.putText(out, "CV: no red ball found", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            print(fn, "NO DETECTION")
        else:
            cx, cy, r, area, circ = det
            cx_i, cy_i, r_i = int(round(cx)), int(round(cy)), int(round(r))
            cv2.circle(out, (cx_i, cy_i), r_i, (255, 255, 0), 3)
            cv2.circle(out, (cx_i, cy_i), 3, (255, 255, 0), -1)
            cv2.putText(out, f"CV ball ({cx_i},{cy_i}) r={r_i}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
            cv2.putText(out, f"CV ball ({cx_i},{cy_i}) r={r_i}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
            print(fn, {"x": cx_i, "y": cy_i, "r": r_i, "area": int(area), "circularity": round(float(circ), 3)})

        base, ext = os.path.splitext(os.path.basename(fn))
        out_path = os.path.join(out_dir, f"{base}_cv_overlay{ext}")  # Save output in the same directory as the script
        ok = cv2.imwrite(out_path, out)
        print("Wrote", out_path, "ok=" + str(ok))

    print("Done")


if __name__ == "__main__":
    main()
