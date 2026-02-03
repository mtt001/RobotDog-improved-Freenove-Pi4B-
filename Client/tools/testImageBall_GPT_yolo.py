#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# Ensure project root (Client/) is importable even when running from Temp/
HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import cv2
import numpy as np

from vision.legacy.mtBallDetectAI import AIVisionBallDetector
from vision.legacy.mtBallDetectYOLO import YOLOBallDetector


def _denorm_circle_to_px(circle, w, h):
    """Return (x_px, y_px, r_px) from an AICircle/dict that may be normalized."""
    if circle is None:
        return None
    if isinstance(circle, dict):
        x_val = circle.get("x", 0)
        y_val = circle.get("y", 0)
        r_val = circle.get("r", 0)
    else:
        x_val = getattr(circle, "x", 0)
        y_val = getattr(circle, "y", 0)
        r_val = getattr(circle, "r", 0)
    try:
        x_f = float(x_val)
        y_f = float(y_val)
        r_f = float(r_val)
    except Exception:
        return None

    # normalized -> pixels
    if 0.0 < x_f <= 1.0 and 0.0 < y_f <= 1.0 and w > 1 and h > 1:
        x_f *= w
        y_f *= h
    if 0.0 < r_f <= 1.0 and min(w, h) > 1:
        r_f *= min(w, h)
    return int(round(x_f)), int(round(y_f)), max(1, int(round(r_f)))


def find_red_roi(frame_bgr, pad_frac=0.25):
    """Find a ROI around the largest red/orange-ish region. Returns (x1,y1,x2,y2) or None."""
    if frame_bgr is None or frame_bgr.size == 0:
        return None
    h, w = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    # broad-ish red/orange; tuned to be permissive for indoor lighting
    mask_red1 = cv2.inRange(hsv, (0, 60, 60), (14, 255, 255))
    mask_red2 = cv2.inRange(hsv, (170, 60, 60), (179, 255, 255))
    mask_orange = cv2.inRange(hsv, (14, 60, 60), (35, 255, 255))
    mask = cv2.bitwise_or(mask_red1, mask_red2)
    mask = cv2.bitwise_or(mask, mask_orange)
    mask = cv2.medianBlur(mask, 7)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    if area < 500:  # too tiny
        return None
    x, y, ww, hh = cv2.boundingRect(c)
    pad_x = int(round(ww * float(pad_frac)))
    pad_y = int(round(hh * float(pad_frac)))
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + ww + pad_x)
    y2 = min(h, y + hh + pad_y)
    if x2 - x1 < 10 or y2 - y1 < 10:
        return None
    return (x1, y1, x2, y2)


def draw_ai(out, circles, w, h):
    for c in circles[:3]:
        try:
            if isinstance(c, dict):
                x_f, y_f, r_f = float(c.get("x", 0)), float(c.get("y", 0)), float(c.get("r", 0))
            else:
                x_f, y_f, r_f = float(c.x), float(c.y), float(c.r)
        except Exception:
            continue
        # Support normalized coordinates from the AI prompt.
        if 0.0 < x_f <= 1.0 and 0.0 < y_f <= 1.0 and w > 1 and h > 1:
            x_f *= w
            y_f *= h
        if 0.0 < r_f <= 1.0 and min(w, h) > 1:
            r_f *= min(w, h)
        x, y, r = int(round(x_f)), int(round(y_f)), int(round(r_f))
        x = max(0, min(w - 1, x))
        y = max(0, min(h - 1, y))
        r = max(1, min(max(w, h), r if r > 0 else 6))
        cv2.circle(out, (x, y), r, (0, 255, 255), 2)
        cv2.circle(out, (x, y), 2, (0, 255, 255), -1)
        cv2.putText(out, "AI", (x + 6, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(out, "AI", (x + 6, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)


def draw_ai_roi(out, circles_roi_as_full_px, w, h):
    """Draw ROI-based AI result (already mapped to full-image pixel coords)."""
    for c in circles_roi_as_full_px[:3]:
        px = _denorm_circle_to_px(c, w, h)
        if not px:
            continue
        x, y, r = px
        x = max(0, min(w - 1, x))
        y = max(0, min(h - 1, y))
        r = max(1, min(max(w, h), r))
        cv2.circle(out, (x, y), r, (255, 0, 255), 2)
        cv2.circle(out, (x, y), 2, (255, 0, 255), -1)
        cv2.putText(out, "AI-ROI", (x + 6, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(out, "AI-ROI", (x + 6, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)


def draw_cv_red_baseline(out, frame_bgr, w, h):
    """Draw a simple CV baseline circle from red mask (cyan)."""
    roi = find_red_roi(frame_bgr, pad_frac=0.0)
    if not roi:
        return None
    x1, y1, x2, y2 = roi
    crop = frame_bgr[y1:y2, x1:x2]
    if crop is None or crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.bitwise_or(
        cv2.inRange(hsv, (0, 60, 60), (14, 255, 255)),
        cv2.inRange(hsv, (170, 60, 60), (179, 255, 255)),
    )
    mask = cv2.medianBlur(mask, 5)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    (cx, cy), r = cv2.minEnclosingCircle(c)
    cx_full = int(round(cx + x1))
    cy_full = int(round(cy + y1))
    r_i = max(1, int(round(r)))
    cv2.circle(out, (cx_full, cy_full), r_i, (255, 255, 0), 2)
    cv2.circle(out, (cx_full, cy_full), 2, (255, 255, 0), -1)
    cv2.putText(out, "CV", (cx_full + 6, max(15, cy_full - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(out, "CV", (cx_full + 6, max(15, cy_full - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
    return (cx_full, cy_full, r_i)


def draw_yolo(out, boxes, w, h):
    for b in boxes[:3]:
        try:
            x1, y1, x2, y2 = int(round(b.x1)), int(round(b.y1)), int(round(b.x2)), int(round(b.y2))
            conf = float(b.conf)
        except Exception:
            continue
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(0, min(w - 1, x2))
        y2 = max(0, min(h - 1, y2))
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"YOLO {int(round(conf * 100))}%"
        cv2.putText(out, label, (x1 + 2, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(out, label, (x1 + 2, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)


def main():
    in_files = ["TestImageAI.png", "TestImageAI-1.png"]
    out_dir = os.path.join("Temp", "ai_yolo_compare")
    os.makedirs(out_dir, exist_ok=True)

    api_key_present = bool(os.getenv("OPENAI_API_KEY"))
    print("OPENAI_API_KEY set:", api_key_present)

    ai = AIVisionBallDetector(model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"))
    yolo = YOLOBallDetector(model_path=os.getenv("YOLO_MODEL_PATH", "yolov8n.pt"))

    for fn in in_files:
        img = cv2.imread(fn)
        if img is None:
            print("ERR: could not read", fn)
            continue
        h, w = img.shape[:2]
        print(f"\n=== {fn} ({w}x{h}) ===")

        circles = []
        circles_roi_full_px = []
        if api_key_present:
            circles = ai.analyze(img)
            print("AI circles:", len(circles), "err:", ai.last_error, "latency:", ai.last_latency_s)
            if ai.last_raw_text:
                print("AI raw:", ai.last_raw_text.strip().replace("\n", " ")[:240])
            try:
                checks = (ai.last_parsed or {}).get("coord_checks", [])
            except Exception:
                checks = []
            if checks:
                c0 = checks[0]
                # dx,dy are in normalized units; multiply by image size for pixels.
                try:
                    dx_px = float(c0.get("dx", 0.0)) * float(w)
                    dy_px = float(c0.get("dy", 0.0)) * float(h)
                except Exception:
                    dx_px = dy_px = 0.0
                print(
                    "AI coord_check:",
                    {
                        "x_norm": c0.get("x"),
                        "y_norm": c0.get("y"),
                        "r_norm": c0.get("r"),
                        "x_px": c0.get("x_px"),
                        "y_px": c0.get("y_px"),
                        "r_px": c0.get("r_px"),
                        "dx_px": round(dx_px, 1),
                        "dy_px": round(dy_px, 1),
                        "dr_norm": c0.get("dr"),
                    },
                )

            # Run AI on a red ROI crop (cheap pre-step) to test whether the model
            # can localize correctly when distractions are removed.
            roi = find_red_roi(img, pad_frac=0.25)
            if roi:
                x1, y1, x2, y2 = roi
                crop = img[y1:y2, x1:x2]
                ch, cw = crop.shape[:2]
                circles_roi = ai.analyze(crop)
                px = _denorm_circle_to_px(circles_roi[0], cw, ch) if circles_roi else None
                print(f"AI-ROI crop: ({x1},{y1})..({x2},{y2}) size={cw}x{ch} circles={len(circles_roi)}")
                if px:
                    x_roi, y_roi, r_roi = px
                    circles_roi_full_px = [
                        {"x": int(x1 + x_roi), "y": int(y1 + y_roi), "r": int(r_roi)}
                    ]
                    print("AI-ROI mapped px:", circles_roi_full_px[0])
            else:
                print("AI-ROI crop: none found")
        else:
            print("AI skipped: OPENAI_API_KEY missing")

        boxes = yolo.analyze(img)
        print("YOLO boxes:", len(boxes), "err:", yolo.last_error, "latency:", yolo.last_latency_s)
        if boxes:
            b0 = boxes[0]
            print("YOLO top:", {"x1": b0.x1, "y1": b0.y1, "x2": b0.x2, "y2": b0.y2, "conf": b0.conf, "cls": b0.cls, "label": b0.label})

        out = img.copy()
        draw_ai(out, circles, w, h)
        if circles_roi_full_px:
            draw_ai_roi(out, circles_roi_full_px, w, h)
        cv_baseline = draw_cv_red_baseline(out, img, w, h)
        if cv_baseline:
            cx, cy, rr = cv_baseline
            print("CV baseline px:", {"x": cx, "y": cy, "r": rr})
        draw_yolo(out, boxes, w, h)

        out_path = os.path.join(out_dir, "overlay_" + os.path.basename(fn))
        ok = cv2.imwrite(out_path, out)
        print("Wrote:", out_path, "ok=" + str(ok))

    print("\nDone. Open Temp/ai_yolo_compare/overlay_*.png")


if __name__ == "__main__":
    main()
