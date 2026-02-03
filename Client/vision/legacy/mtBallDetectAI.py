#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mtBallDetectAI.py

AI-assisted ball candidate detection (test module).

- Provides AIVisionBallDetector: sends a frame to a vision-capable model
  (if OpenAI SDK + API key are available) and returns candidate circles.
- Provides AIVisionBallWindow: shows annotated AI detections.

Notes:
- This is a lightweight test harness; it falls back to empty detections
  if the SDK/key are missing or the API call fails.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any

import cv2
import numpy as np

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap


@dataclass
class AICircle:
    x: float
    y: float
    r: float
    score: float = 0.0
    hsv: tuple[int, int, int] | None = None


class AIVisionBallDetector:
    """Call a low-cost vision model to find ball-like circles."""

    def __init__(self, *, model: str = "gpt-4o-mini", cv_fallback: bool = False):
        env_model = (os.environ.get("OPENAI_VISION_MODEL") or os.environ.get("OPENAI_MODEL") or "").strip()
        self.model = env_model or model
        self.cv_fallback_enabled = bool(cv_fallback)
        self.last_error: str | None = None
        self.last_latency_s: float | None = None
        self.last_raw_text: str | None = None
        self.last_parsed: Dict[str, Any] | None = None

    def analyze(self, frame_bgr: np.ndarray) -> List[AICircle]:
        """Return a list of AI-detected circles in image coordinates."""
        t0 = time.time()
        self.last_error = None
        self.last_raw_text = None
        self.last_parsed = None

        # Try OpenAI SDK first (AI Vision has priority)
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            self.last_error = "OPENAI_API_KEY not set"
            return []

        try:
            # Late import so this module is optional
            from openai import OpenAI  # type: ignore
        except Exception as e:
            self.last_error = f"openai SDK not available: {e}"
            return []

        try:
            # Encode as JPEG to reduce payload
            ok, jpg = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                self.last_error = "jpeg encode failed"
                return []

            b64 = base64.b64encode(jpg.tobytes()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64}"

            client = OpenAI(api_key=api_key)
            h, w = frame_bgr.shape[:2]
            # Use a permissive size range; an overly strict minimum can make the model
            # ignore the true ball and pick a different circular-ish object.
            min_d = max(10, int(round(w / 25)))
            max_d = max(min_d + 1, int(round(w / 2)))
            prompt = (
                "You are a vision module that finds the most likely red/orange solid-color spherical ball. "
                "Ignore non-ball objects, textures, and elongated shapes. "
                f"Hint: expected ball diameter is roughly {min_d}..{max_d} pixels. "
                "Prefer the most ball-like circular object (not necessarily the largest). "
                f"Image size: {w}x{h} pixels. "
                "Coordinate system: origin (0,0) is top-left; x increases to the right, y increases downward. "
                "Return ONLY JSON (no markdown, no extra text): "
                "{\"circles\":[{\"x\":float,\"y\":float,\"r\":float,\"x_px\":int,\"y_px\":int,\"r_px\":int,\"score\":float,\"hsv\":[int,int,int]}]}. "
                "IMPORTANT: Return BOTH normalized and pixel coordinates. "
                "- x,y,r MUST be NORMALIZED floats in [0,1] based on the FULL image size given above. "
                "- x_px,y_px,r_px MUST be PIXELS in that same FULL image. "
                "Use x = x_px / width; y = y_px / height; r = r_px / min(width,height). "
                "Return a SINGLE best circle (or empty list if none). "
                "Also return HSV at the circle center (OpenCV HSV: H 0-179, S 0-255, V 0-255). "
                "If confidence < 0.7 or no ball is visible, return {\"circles\":[]} instead of guessing."
            )

            # Request higher visual detail when supported by the API.
            content = [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": data_url, "detail": "high"},
            ]
            try:
                resp = client.responses.create(
                    model=self.model,
                    temperature=0,
                    max_output_tokens=300,
                    input=[{"role": "user", "content": content}],
                )
            except Exception as e:
                # Fallback for older SDK/API surfaces that don't accept image detail.
                msg = str(e)
                if "detail" in msg or "unexpected" in msg or "unknown" in msg:
                    resp = client.responses.create(
                        model=self.model,
                        temperature=0,
                        max_output_tokens=300,
                        input=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "input_text", "text": prompt},
                                    {"type": "input_image", "image_url": data_url},
                                ],
                            }
                        ],
                    )
                else:
                    raise

            # Extract JSON from the model output
            text = ""
            try:
                text = resp.output_text
            except Exception:
                # Fallback: iterate output items
                try:
                    text = "".join(getattr(resp, "output_text", "") or "")
                except Exception:
                    text = ""

            self.last_raw_text = text
            parsed = _safe_json(text)
            self.last_parsed = parsed if isinstance(parsed, dict) else None
            circles = parsed.get("circles", []) if isinstance(parsed, dict) else []
            results: List[AICircle] = []
            coord_checks = []
            for c in circles:
                try:
                    # Optional dual-coord sanity check: if the model returns both
                    # normalized and pixel coords, verify they match.
                    try:
                        x_px = int(c.get("x_px")) if isinstance(c, dict) and c.get("x_px") is not None else None
                        y_px = int(c.get("y_px")) if isinstance(c, dict) and c.get("y_px") is not None else None
                        r_px = int(c.get("r_px")) if isinstance(c, dict) and c.get("r_px") is not None else None
                    except Exception:
                        x_px = y_px = r_px = None

                    x_norm = float(c.get("x", 0))
                    y_norm = float(c.get("y", 0))
                    r_norm = float(c.get("r", 0))

                    if x_px is not None and y_px is not None:
                        x_from_px = float(x_px) / float(w) if w > 0 else 0.0
                        y_from_px = float(y_px) / float(h) if h > 0 else 0.0
                        r_from_px = (
                            float(r_px) / float(min(w, h))
                            if (r_px is not None and min(w, h) > 0)
                            else None
                        )
                        dx = abs(x_norm - x_from_px)
                        dy = abs(y_norm - y_from_px)
                        dr = abs(r_norm - r_from_px) if (r_from_px is not None) else None
                        coord_checks.append(
                            {
                                "x": x_norm,
                                "y": y_norm,
                                "r": r_norm,
                                "x_px": x_px,
                                "y_px": y_px,
                                "r_px": r_px,
                                "x_from_px": x_from_px,
                                "y_from_px": y_from_px,
                                "r_from_px": r_from_px,
                                "dx": dx,
                                "dy": dy,
                                "dr": dr,
                            }
                        )

                    hsv_val = None
                    hsv_raw = c.get("hsv") if isinstance(c, dict) else None
                    if isinstance(hsv_raw, (list, tuple)) and len(hsv_raw) >= 3:
                        try:
                            hsv_val = (int(hsv_raw[0]), int(hsv_raw[1]), int(hsv_raw[2]))
                        except Exception:
                            hsv_val = None
                    results.append(
                        AICircle(
                            x=x_norm,
                            y=y_norm,
                            r=r_norm,
                            score=float(c.get("score", 0.0)),
                            hsv=hsv_val,
                        )
                    )
                except Exception:
                    continue

            self.last_latency_s = time.time() - t0
            if isinstance(parsed, dict) and "source" not in parsed:
                try:
                    parsed = {"source": "ai", **parsed}
                except Exception:
                    pass
            # Attach coordinate sanity-check details for debugging.
            if isinstance(parsed, dict) and coord_checks:
                try:
                    parsed["coord_checks"] = coord_checks
                except Exception:
                    pass
            self.last_parsed = parsed if isinstance(parsed, dict) else None

            if results:
                return results

            # Optional CV fallback if AI returns no detections (disabled by default)
            if self.cv_fallback_enabled:
                cv_circles = _detect_red_orange_ball(frame_bgr)
                if cv_circles:
                    self.last_parsed = {
                        "source": "cv",
                        "circles": [
                            {"x": c.x, "y": c.y, "r": c.r, "score": c.score}
                            for c in cv_circles
                        ],
                    }
                    self.last_raw_text = json.dumps(self.last_parsed, ensure_ascii=False)
                    return cv_circles

            return []
        except Exception as e:
            self.last_error = f"AI call failed: {e}"
            return []


def _detect_red_orange_ball(frame_bgr: np.ndarray) -> List[AICircle]:
    """Detect a red/orange ball using color segmentation + contour circle fitting."""
    if frame_bgr is None or frame_bgr.size == 0:
        return []

    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = cv2.split(hsv)
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    a_ch = lab[:, :, 1]
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    cr_ch = ycrcb[:, :, 1]
    b_ch, g_ch, r_ch = cv2.split(frame_bgr)
    r_f = r_ch.astype(np.float32)
    g_f = g_ch.astype(np.float32)
    b_f = b_ch.astype(np.float32)
    red_ratio = r_f / (r_f + g_f + b_f + 1.0)
    red_boost = r_f - np.maximum(g_f, b_f)

    # Adaptive thresholds to handle dark wood floors and low light
    try:
        s_p90 = float(np.percentile(s_ch, 90))
        v_p90 = float(np.percentile(v_ch, 90))
        a_p85 = float(np.percentile(a_ch, 85))
        rr_p90 = float(np.percentile(red_ratio, 90))
        rb_p90 = float(np.percentile(red_boost, 90))
        cr_p90 = float(np.percentile(cr_ch, 90))
    except Exception:
        s_p90 = 120.0
        v_p90 = 120.0
        a_p85 = 150.0
        rr_p90 = 0.45
        rb_p90 = 25.0
        cr_p90 = 160.0

    def _build_mask(s_min: int, v_min: int, extra_mask: np.ndarray | None = None) -> np.ndarray:
        # Red has two hue ranges; include orange-ish hues as well
        lower_red1 = np.array([0, s_min, v_min])
        upper_red1 = np.array([12, 255, 255])
        lower_red2 = np.array([170, s_min, v_min])
        upper_red2 = np.array([179, 255, 255])
        lower_orange = np.array([12, s_min, v_min])
        upper_orange = np.array([30, 255, 255])

        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
        mask = cv2.bitwise_or(mask_red1, mask_red2)
        mask = cv2.bitwise_or(mask, mask_orange)
        if extra_mask is not None:
            mask = cv2.bitwise_and(mask, extra_mask)

        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        return mask

    def _pick_best_contour(contours, s_min: int, v_min: int) -> List[AICircle]:
        if not contours:
            return []
        h, w = frame_bgr.shape[:2]
        max_area = float(h * w) * 0.35
        best = None
        best_score = 0.0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200 or area > max_area:
                continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter <= 0:
                continue
            circularity = 4.0 * np.pi * area / (perimeter * perimeter)
            if circularity <= 0.15:
                continue
            mask_c = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(mask_c, [cnt], -1, 255, -1)
            pts = hsv[mask_c > 0]
            if pts is None or len(pts) == 0:
                continue
            h_mean = float(np.mean(pts[:, 0]))
            s_mean = float(np.mean(pts[:, 1]))
            v_mean = float(np.mean(pts[:, 2]))
            if not (0 <= h_mean <= 30 or 170 <= h_mean <= 179):
                a_pts = a_ch[mask_c > 0]
                a_mean = float(np.mean(a_pts)) if a_pts is not None and len(a_pts) > 0 else 128.0
                rr_pts = red_ratio[mask_c > 0]
                rr_mean = float(np.mean(rr_pts)) if rr_pts is not None and len(rr_pts) > 0 else 0.0
                if a_mean < 145.0 and rr_mean < 0.40:
                    continue
            if s_mean < s_min or v_mean < v_min:
                a_pts = a_ch[mask_c > 0]
                a_mean = float(np.mean(a_pts)) if a_pts is not None and len(a_pts) > 0 else 128.0
                rr_pts = red_ratio[mask_c > 0]
                rr_mean = float(np.mean(rr_pts)) if rr_pts is not None and len(rr_pts) > 0 else 0.0
                if a_mean < 140.0 and rr_mean < 0.38:
                    continue
            rel_area = min(1.0, area / max(1.0, float(h * w)))
            score = max(0.0, min(1.0, 0.7 * circularity + 0.3 * (rel_area * 10)))
            if score > best_score:
                (x, y), r = cv2.minEnclosingCircle(cnt)
                if r > 0:
                    best_score = score
                    best = (x, y, r, score)
        if best is None:
            return []
        bx, by, br, bscore = best
        return [AICircle(x=float(bx), y=float(by), r=float(br), score=float(bscore))]

    # Strict mask first, then relaxed if needed
    mask = _build_mask(80, 80)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    picks = _pick_best_contour(contours, 80, 80)
    if picks:
        return picks

    # Relaxed pass with adaptive thresholds + red/alpha gating for dark wood floors
    s_min_rel = max(25, int(round(0.35 * s_p90)))
    v_min_rel = max(25, int(round(0.35 * v_p90)))
    red_ratio_min = max(0.36, rr_p90 - 0.06)
    red_boost_min = max(8.0, rb_p90 * 0.3)
    a_min = max(135.0, a_p85 - 8.0)
    cr_min = max(140.0, cr_p90 - 10.0)
    red_dom = (r_f > (g_f * 1.08)) & (r_f > (b_f * 1.12))
    red_ratio_mask = red_ratio > red_ratio_min
    red_boost_mask = red_boost > red_boost_min
    a_mask = a_ch.astype(np.float32) > a_min
    cr_mask = cr_ch.astype(np.float32) > cr_min
    color_gate = (a_mask | cr_mask)
    extra_mask = ((red_dom | (red_ratio_mask & red_boost_mask)) & color_gate).astype(np.uint8) * 255
    mask = _build_mask(s_min_rel, v_min_rel, extra_mask=extra_mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    picks = _pick_best_contour(contours, s_min_rel, v_min_rel)
    if picks:
        return picks

    # Ratio-only pass (helps when hue is unreliable in warm lighting)
    s_min_ratio = max(10, int(round(0.2 * s_p90)))
    v_min_ratio = max(10, int(round(0.2 * v_p90)))
    ratio_mask = ((red_ratio > red_ratio_min) & (red_boost > red_boost_min) & color_gate).astype(np.uint8) * 255
    ratio_mask = cv2.morphologyEx(ratio_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)
    ratio_mask = cv2.morphologyEx(ratio_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=2)
    contours, _ = cv2.findContours(ratio_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    picks = _pick_best_contour(contours, s_min_ratio, v_min_ratio)
    if picks:
        return picks

    # Fallback: circle detection with Hough (helps when color segmentation fails),Hough is to detect circles in the image
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 2.0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    h, w = gray.shape[:2]
    min_r = max(6, int(round(min(h, w) * 0.02)))
    max_r = int(round(min(h, w) * 0.35))

    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, int(round(min(h, w) * 0.15))),
        param1=120,
        param2=28,
        minRadius=min_r,
        maxRadius=max_r,
    )

    if circles is None:
        return []

    circles = np.round(circles[0, :]).astype(int)

    def _hue_in_ranges(h_val: float) -> bool:
        for lo, hi in [(0, 12), (12, 30), (170, 179)]:
            if lo <= h_val <= hi:
                return True
        return False

    s_min_rel = max(25, int(round(0.3 * s_p90)))
    v_min_rel = max(25, int(round(0.3 * v_p90)))

    best = None
    best_score = 0.0
    for (x, y, r) in circles:
        if r <= 0:
            continue
        mask_c = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask_c, (x, y), int(r), 255, -1)
        pts = hsv[mask_c > 0]
        if pts is None or len(pts) == 0:
            continue
        h_mean = float(np.mean(pts[:, 0]))
        s_mean = float(np.mean(pts[:, 1]))
        v_mean = float(np.mean(pts[:, 2]))
        if not _hue_in_ranges(h_mean):
            a_pts = a_ch[mask_c > 0]
            a_mean = float(np.mean(a_pts)) if a_pts is not None and len(a_pts) > 0 else 128.0
            rr_pts = red_ratio[mask_c > 0]
            rr_mean = float(np.mean(rr_pts)) if rr_pts is not None and len(rr_pts) > 0 else 0.0
            if a_mean < 145.0 and rr_mean < 0.40:
                continue
        if s_mean < s_min_rel or v_mean < v_min_rel:
            a_pts = a_ch[mask_c > 0]
            a_mean = float(np.mean(a_pts)) if a_pts is not None and len(a_pts) > 0 else 128.0
            rr_pts = red_ratio[mask_c > 0]
            rr_mean = float(np.mean(rr_pts)) if rr_pts is not None and len(rr_pts) > 0 else 0.0
            if a_mean < 140.0 and rr_mean < 0.38:
                continue

        score = max(0.0, min(1.0, (s_mean / 255.0) * 0.6 + (v_mean / 255.0) * 0.4))
        if score > best_score:
            best_score = score
            best = (x, y, r, score)

    if best is None:
        return []

    bx, by, br, bscore = best
    return [AICircle(x=float(bx), y=float(by), r=float(br), score=float(bscore))]


def _safe_json(text: str) -> Dict[str, Any]:
    """Extract JSON object from a text blob."""
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        # Try to locate first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
    return {}


class AIVisionBallWindow(QWidget):
    """Simple window to display AI detections."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BallDetection with GPT Vision")
        self.resize(640, 480)

        self.view = QLabel("GPT Vision")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background-color:#101010; color:#9aa6b2;")
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.view, stretch=1)
        self.setLayout(layout)

    def update_frame(self, frame_bgr: np.ndarray):
        if frame_bgr is None:
            return
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        self.view.setPixmap(QPixmap.fromImage(qimg))
