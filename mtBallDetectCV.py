#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""===============================================================================
 Project : Freenove Robot Dog - Video Client
 File    : mtBallDetectCV.py
 Author  : MT & GitHub Copilot (GPT)

 Description:
     Basic CV-based (non-ML) red/orange ball detection.
     Designed as a reliable baseline and to provide a safe ROI for downstream logic.

 Version Control:
     - Tracked in this project's Git workspace.

 Revision History:
    v1.46 (2026-01-24): Remove ring-band threshold/overlay text from debug window.
    v1.45 (2026-01-24): Disable ring-density rejection gate.
    v1.44 (2026-01-24): Draw ring band for rank #1 on color overlay pane.
    v1.43 (2026-01-24): Show ring density in threshold line and candidate list.
    v1.42 (2026-01-24): Lowered minimum V-med to 100 and always show 3 ranked lines in debug list.
    v1.41 (2026-01-24): Use per-split area/circ in candidate debug list to avoid duplicate A/C for split blobs.
    v1.40 (2026-01-24): Show reject reason + Vmed N/A in candidate list.
    v1.40 (2026-01-24): Align overlay labels with ranked debug list.
    v1.39 (2026-01-24): Fill ranked contour masks from combined mask when fewer than 3.
     v1.38 (2026-01-24): Export top-3 ranked contour masks for CV histograms.
    v1.37 (2026-01-23): Prefer upper split using hue/sat/inner coverage heuristic.
    v1.36 (2026-01-23): Strengthen peanut split using local maxima + mask cut.
    v1.35 (2026-01-23): Add refined-candidate contour mask for debug + histogram.
     v1.34 (2026-01-23): Split peanut blobs into multiple candidates via distance peaks.
     v1.33 (2026-01-23): Show all contour candidates ranked by V-med in debug text.
     v1.32 (2026-01-23): Reformat CV debug metrics to prioritize Vmed.
     v1.31 (2026-01-22): Label top-3 rejects on color overlay pane.
     v1.30 (2026-01-22): Use masked V-median for candidate checks; draw rejected circles in debug overlay.
     v1.29 (2026-01-22): Log reject V-median + show top reject stats; relax loose circ/fill gating for reflection blobs.
     v1.28 (2026-01-21): Relaxed CV thresholds (a_min/V/S coverage & v-median) for warm/dim scenes to improve ball detection stability.
    v1.27 (2026-01-21): Log rectangular ROI stats (circ/fill/v_med) for the refine ROI in debug text and mtBallDetectCV.log.
     v1.26 (2026-01-21): Added candidate V-median floor (min_v_median_candidate=180) and ring-waive at high V (>=200) to suppress low-V ghost blobs and reduce false No Ball on bright balls.
     v1.25 (2026-01-21): Tightened loose circ/fill filters (0.45) and prefer strict-only candidates when available to avoid jumping to large ghost blobs.
     v1.24 (2026-01-21): Strengthen v_med priority in multi-candidate selection: prefer upper if v_med within 20 of lower; always pick highest v_med last; log cand_v_med list.
     v1.23 (2026-01-21): Fully disabled ring gate for non-strict blobs; rely on color/brightness only to eliminate "No Ball" in shadow/soft-focus.
     v1.22 (2026-01-21): Relaxed non-strict ring threshold (0.018→0.010) and added shape-based escape for zero-ring shadow blobs (circ>0.55, inner_cov>0.70, v_med>150).
     v1.21 (2026-01-21): Enlarged color overlay pane 2x in debug mosaic for readability.
     v1.20 (2026-01-21): Use median V in inner circle for scoring/selection and multi-candidate preference.
     v1.19 (2026-01-21): Tightened ring-waive to prevent refine-failed, ring-free ghost blobs.
     v1.18 (2026-01-21): Added solid-saturation coverage scoring/gating to reject low-sat ghost blobs.
     v1.17 (2026-01-21): Enforced V-coverage gating and stronger score bias to reject low-V reflections.
     v1.16 (2026-01-21): Reduced edge-ring gating when color coverage is strong; avoid radial gate on weak samples.
    v1.15 (2026-01-21): Relaxed radial gate when ring evidence/refine is strong to reduce flicker misses.
    v1.14 (2026-01-21): Removed mask closing to prevent ball/reflection blob merging.
    v1.13 (2026-01-21): Added V-coverage preference to reject dark reflection blobs.
    v1.12 (2026-01-21): Prefer upper contour when ball+reflection split into two blobs.
    v1.11 (2026-01-21): Relaxed radial gate to avoid rejecting reflection-shaped contours before refinement.
     v1.10 (2026-01-21): Added radial gate enable toggle support for UI-config control.
     v1.09 (2026-01-21): Reset CV log on detector init; reorder history newest-first.
     v1.08 (2026-01-21): Added per-run CV log with explicit Detected/No Ball markers and detailed metrics.
     v1.07 (2026-01-21): Enforced radial edge confidence filter with coverage/score stats; enlarged debug mosaic.
     v1.06 (2026-01-21): Added radial edge symmetry test + solid-saturation preference for upper circle.
     v1.05 (2026-01-20): Added HSV hue gating + hue coverage checks to reduce false positives on wood/refs.
     v1.04 (2026-01-20): Draw detected circle on combined-mask debug pane for easier alignment checks.
     v1.03 (2026-01-19): Prefer the upper circle when ball+reflection yields two circles (upper peak + upper Hough selection).
     v1.02 (2026-01-19): Reduced false positives using edge-ring + mask-coverage confidence checks; tightened distance-transform fallback.
     v1.01 (2026-01-19): Added rich debug outputs (thresholds, mask panes, contour stats).
     v1.00 (2026-01-19): Initial baseline CV detector (Lab a-channel + SV gating + refinement).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from typing import Optional, Tuple

import cv2
import numpy as np


@dataclass
class CVBall:
    x: float
    y: float
    r: float   # expected radius
    area: float
    circularity: float


class CVBallDetector:
    def __init__(self):
        # Thresholds tuned for orange/red ball on dark/reflective wood.
        self.a_percentile = 97.0
        self.a_min = 135
        self.s_min = 60
        self.v_min = 40

        # Hue gating (HSV): keep red/orange hues to reduce wood/skin false positives.
        # H ranges: red wraps (0..h_red_max) U (h_red_min2..179), orange (h_orange_min..h_orange_max)
        self.h_use = True
        self.h_red_max = 12
        self.h_red_min2 = 155
        self.h_orange_min = 6
        self.h_orange_max = 40

        # Candidate gating
        self.min_area = 500.0
        self.max_area_ratio = 0.15
        self.min_circularity = 0.48
        self.min_fill = 0.45
        self.min_radius = 10.0
        self.max_radius_ratio = 0.40

        # Confidence / anti-false-positive checks
        # - mask coverage: ensures the detected circle actually contains enough of the combined mask
        # - edge ring density: ensures there is a circular edge around the estimated radius
        self.inner_ratio = 0.5
        self.min_inner_mask_coverage = 0.35
        self.min_edge_ring_density = 0.012
        self.min_edge_ring_density_non_strict = 0.010
        self.min_hue_coverage = 0.18
        self.min_solid_sat_coverage = 0.22
        self.min_v_coverage = 0.28
        self.v_strong = 90
        self.min_v_median = 100     # highest priority for candidate selection
        self.min_v_median_candidate = 100
        self.v_med_ring_waive = 180
        self.min_radial_score = 0.55
        self.min_radial_coverage = 0.15
        self._radial_score_default = float(self.min_radial_score)
        self._radial_cov_default = float(self.min_radial_coverage)
        self.radial_gate_enabled = True

        # Debug data for UI
        self.last_debug: dict = {}
        self._refine_debug: dict = {}
        self.debug_top_n_rejects = 6
        self.log_enabled = True
        self.log_path = os.path.join(os.path.dirname(__file__), "mtBallDetectCV.log")
        self._run_id = 0
        self._reset_log()

    def set_radial_gate_enabled(self, enabled: bool) -> None:
        try:
            self.radial_gate_enabled = bool(enabled)
            if self.radial_gate_enabled:
                self.min_radial_score = float(self._radial_score_default)
                self.min_radial_coverage = float(self._radial_cov_default)
            else:
                self.min_radial_score = 0.0
                self.min_radial_coverage = 0.0
        except Exception:
            return

    def _reset_log(self) -> None:
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            return

    def _log_detection(self, status: str, reason: str, ball: Optional[CVBall]) -> None:
        if not bool(self.log_enabled):
            return
        try:
            self._run_id += 1
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            dbg = self.last_debug or {}
            thr = dbg.get("thresholds", {}) or {}
            counts = dbg.get("counts", {}) or {}
            best = dbg.get("best", {}) or {}
            fb = dbg.get("fallback", {}) or {}
            refine = dbg.get("refine", {}) or {}
            roi = dbg.get("roi_stats", {}) or {}
            parts = [
                f"[{ts}] run={self._run_id:06d} status={status}",
                f"reason={reason}",
                f"ball=({ball.x:.1f},{ball.y:.1f}) r={ball.r:.1f}" if ball is not None else "ball=None",
                (
                    "thr:"
                    f" a_min={thr.get('a_min')} a_thr={thr.get('a_thr')} a_p={thr.get('a_p'):.1f}"
                    f" s_min={thr.get('s_min')} v_min={thr.get('v_min')} v_med_min={thr.get('min_v_median')} h_use={thr.get('h_use')}"
                    f" h_red_max={thr.get('h_red_max')} h_red_min2={thr.get('h_red_min2')}"
                    f" h_orange={thr.get('h_orange_min')}-{thr.get('h_orange_max')}"
                ),
                f"counts: contours={counts.get('contours_total')} considered={counts.get('considered')} strict={counts.get('strict')}",
                f"cand_v_med={counts.get('cand_v_med', [])}" if counts.get('cand_v_med') else "",
                (
                    "best:"
                    f" score={best.get('score'):.1f} adj={best.get('score_adj', -1):.1f}"
                    f" area={best.get('area'):.1f} circ={best.get('circularity'):.3f} fill={best.get('fill'):.3f}"
                    f" inner_cov={best.get('inner_cov', -1):.2f} hue_cov={best.get('hue_cov', -1):.2f}"
                    f" v_med={best.get('v_med', -1):.0f} v_cov={best.get('v_cov', -1):.2f} sat_cov={best.get('sat_cov', -1):.2f} ring_den={best.get('ring_den', -1):.3f}"
                    f" radial={best.get('radial_score', -1):.2f} cov={best.get('radial_cov', -1):.2f}"
                ),
                (
                    "roi:"
                    f" circ={roi.get('circ', -1):.3f} fill={roi.get('fill', -1):.3f} v_med={roi.get('v_med', -1):.0f}"
                ) if roi else "",
                f"refine: attempted={int(bool(refine.get('attempted')))} ok={int(bool(refine.get('ok')))}",
                (
                    "fallback:"
                    f" method={fb.get('method', 'none')} accepted={fb.get('accepted', True)}"
                    f" center={fb.get('center', None)} r_est={fb.get('r_est', None)}"
                ),
            ]

            rej_lines = []
            for rj in (dbg.get("rejects", []) or [])[: int(self.debug_top_n_rejects)]:
                try:
                    area_rj = float(rj.get("area", 0.0) or 0.0)
                    why = str(rj.get("reason", ""))
                    circ_rj = rj.get("circ", None)
                    fill_rj = rj.get("fill", None)
                    rad_rj = rj.get("r", None)
                    rad_score = rj.get("radial_score", None)
                    rad_cov = rj.get("radial_cov", None)
                    v_med_rj = rj.get("v_med", None)
                    line = f"reject: {why} A{area_rj:.0f}"
                    if circ_rj is not None:
                        line += f" C{float(circ_rj):.3f}"
                    if fill_rj is not None:
                        line += f" F{float(fill_rj):.3f}"
                    if rad_rj is not None:
                        line += f" r{float(rad_rj):.1f}"
                    if v_med_rj is not None:
                        line += f" V{float(v_med_rj):.0f}"
                    if rad_score is not None:
                        line += f" rs{float(rad_score):.2f}"
                    if rad_cov is not None:
                        line += f" rc{float(rad_cov):.2f}"
                    rej_lines.append(line)
                except Exception:
                    continue

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(" | ".join(parts) + "\n")
                if rej_lines:
                    for line in rej_lines:
                        f.write("  " + line + "\n")
        except Exception:
            return

    def analyze(self, frame_bgr: np.ndarray) -> Tuple[Optional[CVBall], Optional[np.ndarray]]:
        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            return None, None

        h, w = frame_bgr.shape[:2]

        self._refine_debug = {}

        lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        _, a, _ = cv2.split(lab)
        try:
            a_p = float(np.percentile(a, float(self.a_percentile)))
        except Exception:
            a_p = 0.0
        a_thr = int(max(int(self.a_min), a_p))
        mask_lab = (a >= a_thr).astype(np.uint8) * 255

        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        h_ch = hsv[:, :, 0]
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]
        s_min = int(self.s_min)
        v_min = int(self.v_min)
        mask_sv = ((s >= s_min) & (v >= v_min)).astype(np.uint8) * 255

        # Hue gate (red/orange) - keeps only plausible ball colors
        if bool(self.h_use):
            h_red_max = int(self.h_red_max)
            h_red_min2 = int(self.h_red_min2)
            h_orange_min = int(self.h_orange_min)
            h_orange_max = int(self.h_orange_max)
            hue_red1 = (h_ch <= h_red_max)
            hue_red2 = (h_ch >= h_red_min2)
            hue_orange = (h_ch >= h_orange_min) & (h_ch <= h_orange_max)
            mask_h = ((hue_red1 | hue_red2 | hue_orange) & (s >= s_min) & (v >= v_min)).astype(np.uint8) * 255
        else:
            mask_h = mask_sv.copy()

        mask = cv2.bitwise_and(mask_lab, mask_h)

        mask = cv2.medianBlur(mask, 5)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best = None
        best_score = -1.0

        img_area = float(h * w)
        max_r = float(self.max_radius_ratio) * float(min(h, w))

        n_total = 0
        n_considered = 0
        n_strict = 0

        rejects: list[dict] = []

        best_area = 0.0
        best_circ = 0.0
        best_fill = 0.0
        best_score_dbg = -1.0
        best_strict = False
        best_radial_score = 0.0
        best_radial_cov = 0.0
        best_radial_total = 0
        best_radial_ring_area = 0

        # For reflection cases, the ball + reflection often forms a peanut-shaped blob.
        # Hard circularity gating can reject it even though a circle exists. We use:
        #   1) loose validity checks (area/radius + very low circ/fill)
        #   2) score-based selection
        #   3) circle refinement (Hough) to lock onto the true ball circle.
        loose_circ_min = 0.30
        loose_fill_min = 0.30

        def _safe_min_circle(cnt) -> Tuple[Optional[float], Optional[float], Optional[float]]:
            try:
                (cx_t, cy_t), r_t = cv2.minEnclosingCircle(cnt)
                return float(cx_t), float(cy_t), float(r_t)
            except Exception:
                return None, None, None

        def _append_reject(
            reason: str,
            area_r: float,
            circ_r: Optional[float] = None,
            fill_r: Optional[float] = None,
            r_r: Optional[float] = None,
            v_med_r: Optional[float] = None,
            radial_score_r: Optional[float] = None,
            radial_cov_r: Optional[float] = None,
            cx_r: Optional[float] = None,
            cy_r: Optional[float] = None,
            area_dbg_r: Optional[float] = None,
            ring_den_r: Optional[float] = None,
        ) -> None:
            try:
                item = {"reason": str(reason), "area": float(area_r)}
                if circ_r is not None:
                    item["circ"] = float(circ_r)
                if fill_r is not None:
                    item["fill"] = float(fill_r)
                if r_r is not None:
                    item["r"] = float(r_r)
                if v_med_r is not None:
                    item["v_med"] = float(v_med_r)
                if radial_score_r is not None:
                    item["radial_score"] = float(radial_score_r)
                if radial_cov_r is not None:
                    item["radial_cov"] = float(radial_cov_r)
                if cx_r is not None:
                    item["cx"] = float(cx_r)
                if cy_r is not None:
                    item["cy"] = float(cy_r)
                if area_dbg_r is not None:
                    item["area_dbg"] = float(area_dbg_r)
                if ring_den_r is not None:
                    item["ring_den"] = float(ring_den_r)
                rejects.append(item)
            except Exception:
                return

        def _circle_mask_coverage(cx_f: float, cy_f: float, r_f: float, src_mask: np.ndarray) -> float:
            try:
                rr = float(r_f)
                if rr <= 1.0:
                    return 0.0
                cx_i = int(round(float(cx_f)))
                cy_i = int(round(float(cy_f)))
                rr_i = int(round(rr))
                if rr_i <= 1:
                    return 0.0

                # ROI clip
                x0 = max(0, cx_i - rr_i)
                y0 = max(0, cy_i - rr_i)
                x1 = min(w, cx_i + rr_i + 1)
                y1 = min(h, cy_i + rr_i + 1)
                if x1 <= x0 or y1 <= y0:
                    return 0.0

                sub = src_mask[y0:y1, x0:x1]
                if sub is None or getattr(sub, "size", 0) == 0:
                    return 0.0

                rr_sub = int(round(rr))
                cx_sub = cx_i - x0
                cy_sub = cy_i - y0
                rr_sub = max(1, min(rr_sub, min(sub.shape[1], sub.shape[0]) // 2))

                circle = np.zeros(sub.shape[:2], dtype=np.uint8)
                cv2.circle(circle, (cx_sub, cy_sub), rr_sub, 255, -1)
                circle_area = float(cv2.countNonZero(circle))
                if circle_area <= 1.0:
                    return 0.0
                covered = float(cv2.countNonZero(cv2.bitwise_and(sub, circle)))
                return float(covered / circle_area)
            except Exception:
                return 0.0

        def _circle_v_coverage(cx_f: float, cy_f: float, r_f: float, v_ch: np.ndarray) -> float:
            try:
                rr = float(r_f)
                if rr <= 1.0:
                    return 0.0
                cx_i = int(round(float(cx_f)))
                cy_i = int(round(float(cy_f)))
                rr_i = int(round(rr))
                if rr_i <= 1:
                    return 0.0

                x0 = max(0, cx_i - rr_i)
                y0 = max(0, cy_i - rr_i)
                x1 = min(w, cx_i + rr_i + 1)
                y1 = min(h, cy_i + rr_i + 1)
                if x1 <= x0 or y1 <= y0:
                    return 0.0

                sub_v = v_ch[y0:y1, x0:x1]
                if sub_v is None or getattr(sub_v, "size", 0) == 0:
                    return 0.0

                rr_sub = int(round(rr))
                cx_sub = cx_i - x0
                cy_sub = cy_i - y0
                rr_sub = max(1, min(rr_sub, min(sub_v.shape[1], sub_v.shape[0]) // 2))

                circle = np.zeros(sub_v.shape[:2], dtype=np.uint8)
                cv2.circle(circle, (cx_sub, cy_sub), rr_sub, 255, -1)
                circle_area = float(cv2.countNonZero(circle))
                if circle_area <= 1.0:
                    return 0.0
                v_mask = (sub_v >= int(self.v_strong)).astype(np.uint8) * 255
                covered = float(cv2.countNonZero(cv2.bitwise_and(v_mask, circle)))
                return float(covered / circle_area)
            except Exception:
                return 0.0

        def _circle_v_median(
            cx_f: float,
            cy_f: float,
            r_f: float,
            v_ch: np.ndarray,
            mask_ref: Optional[np.ndarray] = None,
        ) -> float:
            try:
                rr = float(r_f)
                if rr <= 1.0:
                    return 0.0
                cx_i = int(round(float(cx_f)))
                cy_i = int(round(float(cy_f)))
                rr_i = int(round(rr))
                if rr_i <= 1:
                    return 0.0

                x0 = max(0, cx_i - rr_i)
                y0 = max(0, cy_i - rr_i)
                x1 = min(w, cx_i + rr_i + 1)
                y1 = min(h, cy_i + rr_i + 1)
                if x1 <= x0 or y1 <= y0:
                    return 0.0

                sub_v = v_ch[y0:y1, x0:x1]
                if sub_v is None or getattr(sub_v, "size", 0) == 0:
                    return 0.0

                rr_sub = int(round(rr))
                cx_sub = cx_i - x0
                cy_sub = cy_i - y0
                rr_sub = max(1, min(rr_sub, min(sub_v.shape[1], sub_v.shape[0]) // 2))

                circle = np.zeros(sub_v.shape[:2], dtype=np.uint8)
                cv2.circle(circle, (cx_sub, cy_sub), rr_sub, 255, -1)
                circle_area = float(cv2.countNonZero(circle))
                if circle_area <= 1.0:
                    return 0.0

                if mask_ref is not None:
                    try:
                        sub_m = mask_ref[y0:y1, x0:x1]
                        if sub_m is not None and getattr(sub_m, "size", 0) > 0:
                            mask_in = cv2.bitwise_and(sub_m, circle)
                            mask_area = float(cv2.countNonZero(mask_in))
                            if mask_area >= circle_area * 0.15:
                                vals = sub_v[mask_in > 0]
                                if vals is not None and vals.size > 0:
                                    return float(np.median(vals))
                    except Exception:
                        pass

                vals = sub_v[circle > 0]
                if vals.size <= 0:
                    return 0.0
                return float(np.median(vals))
            except Exception:
                return 0.0

        def _rect_roi_stats(cx_f: float, cy_f: float, r_f: float, src_mask: np.ndarray, src_v: np.ndarray) -> Optional[dict]:
            try:
                rr = float(r_f)
                if rr <= 1.0:
                    return None
                pad = int(max(20, round(rr * 1.6)))
                h, w = src_mask.shape[:2]
                x0 = max(0, int(round(cx_f)) - pad)
                y0 = max(0, int(round(cy_f)) - pad)
                x1 = min(w, int(round(cx_f)) + pad)
                y1 = min(h, int(round(cy_f)) + pad)
                if (x1 - x0) <= 2 or (y1 - y0) <= 2:
                    return None

                roi_mask = src_mask[y0:y1, x0:x1]
                roi_v = src_v[y0:y1, x0:x1]
                if roi_mask.size == 0 or roi_v.size == 0:
                    return None

                roi_bin = (roi_mask > 0).astype(np.uint8)
                v_vals = roi_v[roi_bin > 0]
                v_med = float(np.median(v_vals)) if v_vals.size > 0 else float(np.median(roi_v))

                cnts_roi, _ = cv2.findContours(roi_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not cnts_roi:
                    return {
                        "circ": 0.0,
                        "fill": 0.0,
                        "v_med": v_med,
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                    }
                c = max(cnts_roi, key=lambda cnt: float(cv2.contourArea(cnt)))
                area = float(cv2.contourArea(c))
                peri = float(cv2.arcLength(c, True))
                circ = (4.0 * np.pi * area / (peri * peri)) if peri > 1e-6 else 0.0
                (_, _), r_en = cv2.minEnclosingCircle(c)
                fill = (area / (np.pi * r_en * r_en)) if r_en > 1e-6 else 0.0
                return {
                    "circ": float(circ),
                    "fill": float(fill),
                    "v_med": float(v_med),
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                }
            except Exception:
                return None

        def _circle_sat_coverage(cx_f: float, cy_f: float, r_f: float, s_ch: np.ndarray, v_ch: np.ndarray) -> float:
            try:
                rr = float(r_f)
                if rr <= 1.0:
                    return 0.0
                cx_i = int(round(float(cx_f)))
                cy_i = int(round(float(cy_f)))
                rr_i = int(round(rr))
                if rr_i <= 1:
                    return 0.0

                x0 = max(0, cx_i - rr_i)
                y0 = max(0, cy_i - rr_i)
                x1 = min(w, cx_i + rr_i + 1)
                y1 = min(h, cy_i + rr_i + 1)
                if x1 <= x0 or y1 <= y0:
                    return 0.0

                sub_s = s_ch[y0:y1, x0:x1]
                sub_v = v_ch[y0:y1, x0:x1]
                if sub_s is None or sub_v is None or getattr(sub_s, "size", 0) == 0:
                    return 0.0

                rr_sub = int(round(rr))
                cx_sub = cx_i - x0
                cy_sub = cy_i - y0
                rr_sub = max(1, min(rr_sub, min(sub_s.shape[1], sub_s.shape[0]) // 2))

                circle = np.zeros(sub_s.shape[:2], dtype=np.uint8)
                cv2.circle(circle, (cx_sub, cy_sub), rr_sub, 255, -1)
                circle_area = float(cv2.countNonZero(circle))
                if circle_area <= 1.0:
                    return 0.0
                solid = cv2.bitwise_and(
                    circle,
                    ((sub_s >= int(self.s_min)) & (sub_v >= int(self.v_min))).astype(np.uint8) * 255,
                )
                covered = float(cv2.countNonZero(solid))
                return float(covered / circle_area)
            except Exception:
                return 0.0

        def _edge_ring_density(cx_f: float, cy_f: float, r_f: float) -> float:
            try:
                rr = float(r_f)
                if rr <= 3.0:
                    return 0.0
                cx_i = int(round(float(cx_f)))
                cy_i = int(round(float(cy_f)))
                rr_i = int(round(rr))

                pad = int(max(18, round(rr_i * 1.5)))
                x0 = max(0, cx_i - pad)
                y0 = max(0, cy_i - pad)
                x1 = min(w, cx_i + pad + 1)
                y1 = min(h, cy_i + pad + 1)
                roi = frame_bgr[y0:y1, x0:x1]
                if roi is None or getattr(roi, "size", 0) == 0:
                    return 0.0

                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (7, 7), 1.2)
                edges = cv2.Canny(gray, 60, 120)

                cx_r = int(cx_i - x0)
                cy_r = int(cy_i - y0)

                # Annulus mask around expected radius (fairly thick to tolerate blur/reflections)
                r_in = int(max(2, round(rr_i * 0.78)))
                r_out = int(max(r_in + 2, round(rr_i * 1.18)))

                ann = np.zeros(edges.shape[:2], dtype=np.uint8)
                cv2.circle(ann, (cx_r, cy_r), r_out, 255, -1)
                cv2.circle(ann, (cx_r, cy_r), r_in, 0, -1)

                ann_area = float(cv2.countNonZero(ann))
                if ann_area <= 1.0:
                    return 0.0
                e = float(cv2.countNonZero(cv2.bitwise_and(edges, ann)))
                return float(e / ann_area)
            except Exception:
                return 0.0

        def _radial_edge_symmetry(cx_f: float, cy_f: float, r_f: float):
            try:
                rr = float(r_f)
                if rr <= 4.0:
                    return 0.0, 0.0, None, None, 0, 0
                cx_i = int(round(float(cx_f)))
                cy_i = int(round(float(cy_f)))
                rr_i = int(round(rr))

                pad = int(max(18, round(rr_i * 1.6)))
                x0 = max(0, cx_i - pad)
                y0 = max(0, cy_i - pad)
                x1 = min(w, cx_i + pad + 1)
                y1 = min(h, cy_i + pad + 1)
                roi = frame_bgr[y0:y1, x0:x1]
                if roi is None or getattr(roi, "size", 0) == 0:
                    return 0.0, 0.0, None, None

                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (7, 7), 1.2)
                edges = cv2.Canny(gray, 60, 120)
                gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)

                cx_r = int(cx_i - x0)
                cy_r = int(cy_i - y0)

                r_in = int(max(2, round(rr_i * 0.85)))
                r_out = int(max(r_in + 2, round(rr_i * 1.15)))
                ring = np.zeros(edges.shape[:2], dtype=np.uint8)
                cv2.circle(ring, (cx_r, cy_r), r_out, 255, -1)
                cv2.circle(ring, (cx_r, cy_r), r_in, 0, -1)

                ring_edges = cv2.bitwise_and(edges, ring)
                ys, xs = np.where(ring_edges > 0)
                total = int(len(xs))
                if total <= 0:
                    vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                    cv2.circle(vis, (cx_r, cy_r), r_out, (255, 255, 0), 1)
                    cv2.circle(vis, (cx_r, cy_r), r_in, (255, 255, 0), 1)
                    return 0.0, 0.0, vis, (x0, y0, x1, y1), 0, 0

                ring_area = int(cv2.countNonZero(ring))
                if ring_area <= 0:
                    return 0.0, 0.0, None, None, 0, 0

                rx = xs.astype(np.float32) - float(cx_r)
                ry = ys.astype(np.float32) - float(cy_r)
                gxv = gx[ys, xs]
                gyv = gy[ys, xs]
                gmag = np.sqrt(gxv * gxv + gyv * gyv)
                rmag = np.sqrt(rx * rx + ry * ry)
                valid = (gmag > 1e-6) & (rmag > 1e-6)
                if not np.any(valid):
                    return 0.0, 0.0, None, None, 0, 0
                gxv = gxv[valid]
                gyv = gyv[valid]
                rx = rx[valid]
                ry = ry[valid]
                gmag = gmag[valid]
                rmag = rmag[valid]
                cos_t = (gxv * rx + gyv * ry) / (gmag * rmag)
                aligned = int(np.sum(cos_t > 0.7))
                total_valid = int(cos_t.size)

                vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                cv2.circle(vis, (cx_r, cy_r), r_out, (255, 255, 0), 1)
                cv2.circle(vis, (cx_r, cy_r), r_in, (255, 255, 0), 1)
                step = max(1, total_valid // 180)
                try:
                    xs_v = xs[valid]
                    ys_v = ys[valid]
                    for i in range(0, total_valid, step):
                        x = int(xs_v[i])
                        y = int(ys_v[i])
                        if float(cos_t[i]) > 0.7:
                            cv2.circle(vis, (x, y), 1, (0, 255, 0), -1)
                        else:
                            cv2.circle(vis, (x, y), 1, (0, 0, 255), -1)
                except Exception:
                    pass

                radial_score = float(aligned / max(1, total_valid))
                radial_cov = float(total_valid / max(1, ring_area))
                return radial_score, radial_cov, vis, (x0, y0, x1, y1), total_valid, ring_area
            except Exception:
                return 0.0, 0.0, None, None, 0, 0

        candidates: list[dict] = []
        refined_candidates: list[dict] = []
        best_item = None

        def _split_peanut_candidates(contour, max_r_px: float) -> list[dict]:
            try:
                if contour is None:
                    return []
                mask_cnt = np.zeros_like(mask, dtype=np.uint8)
                cv2.drawContours(mask_cnt, [contour], -1, 255, -1)
                if int(cv2.countNonZero(mask_cnt)) < int(self.min_area):
                    return []
                dist = cv2.distanceTransform(mask_cnt, cv2.DIST_L2, 5)
                _, max_val, _, _ = cv2.minMaxLoc(dist)
                global_max = float(max_val)
                if global_max < float(self.min_radius):
                    return []
                # Local maxima in distance map (peaks for possible split)
                peaks: list[tuple[int, int, float]] = []
                try:
                    dist_norm = dist.copy()
                    dil = cv2.dilate(dist_norm, np.ones((5, 5), np.uint8))
                    peaks_mask = (dist_norm >= dil - 1e-6) & (dist_norm >= (0.70 * global_max))
                    ys, xs = np.where(peaks_mask)
                    for (px, py) in zip(xs.tolist(), ys.tolist()):
                        mv = float(dist_norm[py, px])
                        peaks.append((int(px), int(py), mv))
                except Exception:
                    peaks = []

                if not peaks:
                    dist_work = dist.copy()
                    for _ in range(4):
                        _, mv, _, ml = cv2.minMaxLoc(dist_work)
                        mv = float(mv)
                        if mv <= 0.0:
                            break
                        px, py = int(ml[0]), int(ml[1])
                        peaks.append((px, py, mv))
                        sup_r = int(max(6, round(mv * 0.85)))
                        cv2.circle(dist_work, (px, py), sup_r, 0.0, -1)

                strong = [p for p in peaks if p[2] >= 0.75 * global_max]
                if len(strong) < 2:
                    return []

                strong.sort(key=lambda t: (-t[2], t[1]))
                p0, p1 = strong[0], strong[1]
                r0, r1 = float(p0[2]), float(p1[2])
                r_min = float(min(r0, r1))
                dx = abs(float(p0[0]) - float(p1[0]))
                dy = abs(float(p0[1]) - float(p1[1]))

                # Prefer vertical stacked peaks (ball + reflection) with similar size.
                if dx > (0.90 * r_min):
                    return []
                if dy < (0.50 * r_min):
                    return []
                if r0 > float(max_r_px) or r1 > float(max_r_px):
                    return []

                # Try to split the blob by cutting a line between the two peaks.
                try:
                    split = mask_cnt.copy()
                    vx = float(p1[0] - p0[0])
                    vy = float(p1[1] - p0[1])
                    norm = max(1e-6, (vx * vx + vy * vy) ** 0.5)
                    ux, uy = vx / norm, vy / norm
                    px, py = -uy, ux
                    midx = float(p0[0] + p1[0]) * 0.5
                    midy = float(p0[1] + p1[1]) * 0.5
                    cut_len = max(6.0, 1.6 * r_min)
                    cut_thick = int(max(2, round(0.22 * r_min)))
                    x1 = int(round(midx + px * cut_len))
                    y1 = int(round(midy + py * cut_len))
                    x2 = int(round(midx - px * cut_len))
                    y2 = int(round(midy - py * cut_len))
                    cv2.line(split, (x1, y1), (x2, y2), 0, cut_thick)
                    cnts_split, _ = cv2.findContours(split, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if cnts_split and len(cnts_split) >= 2:
                        cnts_split.sort(key=cv2.contourArea, reverse=True)
                        out = []
                        for c_s in cnts_split[:2]:
                            (cx_s, cy_s), r_s = cv2.minEnclosingCircle(c_s)
                            if r_s <= 1.0:
                                continue
                            area_s = float(cv2.contourArea(c_s))
                            peri_s = float(cv2.arcLength(c_s, True))
                            if peri_s > 1e-6:
                                circ_s = float(4.0 * np.pi * area_s / (peri_s * peri_s))
                            else:
                                circ_s = 0.0
                            out.append({
                                "cx": float(cx_s),
                                "cy": float(cy_s),
                                "r": float(r_s),
                                "area_dbg": float(area_s),
                                "circ_dbg": float(circ_s),
                                "contour": c_s,
                            })
                        if len(out) >= 2:
                            return out[:2]
                except Exception:
                    pass

                # Fallback: return peak-based circles
                return [
                    {
                        "cx": float(p0[0]),
                        "cy": float(p0[1]),
                        "r": float(r0),
                        "area_dbg": float(np.pi * float(r0) * float(r0)),
                        "circ_dbg": 1.0,
                        "contour": None,
                    },
                    {
                        "cx": float(p1[0]),
                        "cy": float(p1[1]),
                        "r": float(r1),
                        "area_dbg": float(np.pi * float(r1) * float(r1)),
                        "circ_dbg": 1.0,
                        "contour": None,
                    },
                ]
            except Exception:
                return []

        for c in cnts:
            n_total += 1
            area = float(cv2.contourArea(c))
            if area < float(self.min_area) or area > img_area * float(self.max_area_ratio):
                cx_r, cy_r, r_r = _safe_min_circle(c)
                _append_reject("area", area, r_r=r_r, cx_r=cx_r, cy_r=cy_r)
                continue

            peri = float(cv2.arcLength(c, True))
            if peri <= 1e-6:
                cx_r, cy_r, r_r = _safe_min_circle(c)
                _append_reject("peri", area, r_r=r_r, cx_r=cx_r, cy_r=cy_r)
                continue

            circ = 4.0 * np.pi * area / (peri * peri)
            (cx, cy), r = cv2.minEnclosingCircle(c)
            if r < float(self.min_radius) or r > max_r:
                _append_reject("radius", area, circ_r=float(circ), r_r=float(r), cx_r=float(cx), cy_r=float(cy))
                continue

            fill = area / (np.pi * r * r) if r > 1e-6 else 0.0

            strict_ok = (circ >= float(self.min_circularity)) and (fill >= float(self.min_fill))
            if strict_ok:
                n_strict += 1

            inner_r_c = float(r) * float(self.inner_ratio)
            v_med_c = _circle_v_median(float(cx), float(cy), inner_r_c, v, mask)

            split_peaks = _split_peanut_candidates(c, max_r)
            if split_peaks:
                for split_item in split_peaks:
                    cx_s = float(split_item.get("cx", 0.0) or 0.0)
                    cy_s = float(split_item.get("cy", 0.0) or 0.0)
                    r_s = float(split_item.get("r", 0.0) or 0.0)
                    area_dbg_s = float(split_item.get("area_dbg", 0.0) or 0.0)
                    circ_dbg_s = float(split_item.get("circ_dbg", 1.0) or 0.0)
                    area_s_use = float(area_dbg_s) if float(area_dbg_s) > 0.0 else float(area)
                    circ_s_use = float(circ_dbg_s) if float(circ_dbg_s) > 0.0 else 1.0
                    if r_s < float(self.min_radius) or r_s > float(max_r):
                        _append_reject(
                            "radius",
                            area,
                            circ_r=float(circ_dbg_s),
                            r_r=float(r_s),
                            cx_r=float(cx_s),
                            cy_r=float(cy_s),
                            area_dbg_r=float(area_dbg_s),
                        )
                        continue

                    fill_s = _circle_mask_coverage(float(cx_s), float(cy_s), float(r_s), mask)
                    ring_den_s = _edge_ring_density(float(cx_s), float(cy_s), float(r_s))

                    if float(fill_s) < float(loose_fill_min):
                        _append_reject(
                            "fill",
                            area,
                            circ_r=float(circ_dbg_s),
                            fill_r=float(fill_s),
                            r_r=float(r_s),
                            cx_r=float(cx_s),
                            cy_r=float(cy_s),
                            area_dbg_r=float(area_dbg_s),
                            ring_den_r=float(ring_den_s),
                        )
                        continue

                    strict_ok_s = (float(circ_s_use) >= float(self.min_circularity)) and (float(fill_s) >= float(self.min_fill))
                    if strict_ok_s:
                        n_strict += 1

                    inner_r_s = float(r_s) * float(self.inner_ratio)
                    v_med_s = _circle_v_median(float(cx_s), float(cy_s), inner_r_s, v, mask)
                    v_cov_s = _circle_v_coverage(float(cx_s), float(cy_s), inner_r_s, v)
                    sat_cov_s = _circle_sat_coverage(float(cx_s), float(cy_s), inner_r_s, s, v)
                    hue_cov_s = _circle_mask_coverage(float(cx_s), float(cy_s), inner_r_s, mask_h)
                    inner_cov_s = _circle_mask_coverage(float(cx_s), float(cy_s), inner_r_s, mask)

                    radial_score_s, radial_cov_s, radial_vis_s, radial_roi_s, radial_total_s, radial_ring_area_s = _radial_edge_symmetry(
                        float(cx_s), float(cy_s), float(r_s)
                    )
                    radial_pass_s = (float(radial_score_s) >= float(self.min_radial_score)) and (
                        float(radial_cov_s) >= float(self.min_radial_coverage)
                    )
                    radial_gate_applicable_s = (int(radial_total_s) >= 80) and (
                        float(radial_cov_s) >= float(self.min_radial_coverage) * 0.5
                    )
                    if bool(self.radial_gate_enabled) and bool(strict_ok_s) and bool(radial_gate_applicable_s) and (not radial_pass_s):
                        _append_reject(
                            "radial",
                            area,
                            circ_r=float(circ_dbg_s),
                            fill_r=float(fill_s),
                            r_r=float(r_s),
                            v_med_r=float(v_med_s),
                            radial_score_r=float(radial_score_s),
                            radial_cov_r=float(radial_cov_s),
                            cx_r=float(cx_s),
                            cy_r=float(cy_s),
                            area_dbg_r=float(area_dbg_s),
                            ring_den_r=float(ring_den_s),
                        )
                        continue

                    if v_med_s < float(self.min_v_median_candidate):
                        _append_reject(
                            "v-med",
                            area,
                            circ_r=float(circ_dbg_s),
                            fill_r=float(fill_s),
                            r_r=float(r_s),
                            v_med_r=float(v_med_s),
                            cx_r=float(cx_s),
                            cy_r=float(cy_s),
                            area_dbg_r=float(area_dbg_s),
                            ring_den_r=float(ring_den_s),
                        )
                        continue

                    n_considered += 1
                    score_s = float(area_s_use) * (0.25 + float(circ_s_use)) * (0.25 + float(fill_s))
                    if strict_ok_s:
                        score_s *= 1.35
                    if v_med_s < float(self.min_v_median):
                        score_s *= 0.30
                    else:
                        try:
                            v_boost_s = 1.0 + 0.35 * float(
                                min(
                                    1.0,
                                    (float(v_med_s) - float(self.min_v_median))
                                    / max(1e-6, (255.0 - float(self.min_v_median))),
                                )
                            )
                            score_s *= float(v_boost_s)
                        except Exception:
                            pass
                    if sat_cov_s < float(self.min_solid_sat_coverage):
                        score_s *= 0.35
                    else:
                        try:
                            sat_boost_s = 1.0 + 0.25 * float(
                                min(
                                    1.0,
                                    (float(sat_cov_s) - float(self.min_solid_sat_coverage))
                                    / max(1e-6, (1.0 - float(self.min_solid_sat_coverage))),
                                )
                            )
                            score_s *= float(sat_boost_s)
                        except Exception:
                            pass

                    candidates.append({
                        "cx": float(cx_s),
                        "cy": float(cy_s),
                        "r": float(r_s),
                        "area": float(area_s_use),
                        "circ": float(circ_s_use),
                        "fill": float(fill_s),
                        "area_dbg": float(area_dbg_s),
                        "circ_dbg": float(circ_dbg_s),
                        "ring_den": float(ring_den_s),
                        "strict": bool(strict_ok_s),
                        "score": float(score_s),
                        "v_cov": float(v_cov_s),
                        "v_med": float(v_med_s),
                        "sat_cov": float(sat_cov_s),
                        "hue_cov": float(hue_cov_s),
                        "inner_cov": float(inner_cov_s),
                        "contour": split_item.get("contour", None),
                        "circle": (float(cx_s), float(cy_s), float(r_s)),
                        "radial_score": float(radial_score_s),
                        "radial_cov": float(radial_cov_s),
                        "radial_total": int(radial_total_s),
                        "radial_ring_area": int(radial_ring_area_s),
                        "radial_vis": radial_vis_s,
                        "radial_roi": radial_roi_s,
                    })
                continue

            if circ < loose_circ_min:
                _append_reject(
                    "circ",
                    area,
                    circ_r=float(circ),
                    fill_r=float(fill),
                    r_r=float(r),
                    v_med_r=float(v_med_c),
                    cx_r=float(cx),
                    cy_r=float(cy),
                )
                continue
            if fill < loose_fill_min:
                _append_reject(
                    "fill",
                    area,
                    circ_r=float(circ),
                    fill_r=float(fill),
                    r_r=float(r),
                    v_med_r=float(v_med_c),
                    cx_r=float(cx),
                    cy_r=float(cy),
                )
                continue

            radial_score_c, radial_cov_c, radial_vis_c, radial_roi_c, radial_total_c, radial_ring_area_c = _radial_edge_symmetry(float(cx), float(cy), float(r))
            radial_pass_c = (float(radial_score_c) >= float(self.min_radial_score)) and (float(radial_cov_c) >= float(self.min_radial_coverage))
            radial_gate_applicable = (int(radial_total_c) >= 80) and (float(radial_cov_c) >= float(self.min_radial_coverage) * 0.5)
            if bool(self.radial_gate_enabled) and bool(strict_ok) and bool(radial_gate_applicable) and (not radial_pass_c):
                _append_reject(
                    "radial",
                    area,
                    circ_r=float(circ),
                    fill_r=float(fill),
                    r_r=float(r),
                    v_med_r=float(v_med_c),
                    radial_score_r=float(radial_score_c),
                    radial_cov_r=float(radial_cov_c),
                    cx_r=float(cx),
                    cy_r=float(cy),
                )
                continue

            n_considered += 1

            ring_den_c = _edge_ring_density(float(cx), float(cy), float(r))

            # Soft score: keep circ/fill influence but avoid hard rejection near thresholds.
            # Add a small bonus if it already passes strict thresholds.
            score = area * (0.25 + float(circ)) * (0.25 + float(fill))
            if strict_ok:
                score *= 1.35

            # Downweight dark/reflection blobs (low median V inside circle)
            v_cov_c = _circle_v_coverage(float(cx), float(cy), inner_r_c, v)
            if v_med_c < float(self.min_v_median):
                score *= 0.30
            else:
                try:
                    v_boost = 1.0 + 0.35 * float(
                        min(
                            1.0,
                            (float(v_med_c) - float(self.min_v_median))
                            / max(1e-6, (255.0 - float(self.min_v_median))),
                        )
                    )
                    score *= float(v_boost)
                except Exception:
                    pass

            sat_cov_c = _circle_sat_coverage(float(cx), float(cy), inner_r_c, s, v)
            hue_cov_c = _circle_mask_coverage(float(cx), float(cy), inner_r_c, mask_h)
            inner_cov_c = _circle_mask_coverage(float(cx), float(cy), inner_r_c, mask)
            if sat_cov_c < float(self.min_solid_sat_coverage):
                score *= 0.35
            else:
                try:
                    sat_boost = 1.0 + 0.25 * float(
                        min(
                            1.0,
                            (float(sat_cov_c) - float(self.min_solid_sat_coverage))
                            / max(1e-6, (1.0 - float(self.min_solid_sat_coverage))),
                        )
                    )
                    score *= float(sat_boost)
                except Exception:
                    pass

            if v_med_c < float(self.min_v_median_candidate):
                _append_reject(
                    "v-med",
                    area,
                    circ_r=float(circ),
                    fill_r=float(fill),
                    r_r=float(r),
                    v_med_r=float(v_med_c),
                    cx_r=float(cx),
                    cy_r=float(cy),
                )
                continue

            candidates.append({
                "cx": float(cx),
                "cy": float(cy),
                "r": float(r),
                "area": float(area),
                "circ": float(circ),
                "fill": float(fill),
                "ring_den": float(ring_den_c),
                "strict": bool(strict_ok),
                "score": float(score),
                "v_cov": float(v_cov_c),
                "v_med": float(v_med_c),
                "sat_cov": float(sat_cov_c),
                "hue_cov": float(hue_cov_c),
                "inner_cov": float(inner_cov_c),
                "contour": c,
                "circle": (float(cx), float(cy), float(r)),
                "radial_score": float(radial_score_c),
                "radial_cov": float(radial_cov_c),
                "radial_total": int(radial_total_c),
                "radial_ring_area": int(radial_ring_area_c),
                "radial_vis": radial_vis_c,
                "radial_roi": radial_roi_c,
            })

        if candidates:
            select_candidates = candidates
            try:
                strict_candidates = [c for c in candidates if bool(c.get("strict"))]
                if strict_candidates:
                    select_candidates = strict_candidates
                    try:
                        self._refine_debug["select_pool"] = f"strict-only ({len(strict_candidates)})"
                    except Exception:
                        pass
            except Exception:
                select_candidates = candidates

            try:
                refined_candidates = list(select_candidates)
            except Exception:
                refined_candidates = []

            # Export top-3 ranked contour masks for histogram panels
            try:
                ranked = sorted(
                    select_candidates,
                    key=lambda d: (float(d.get("v_med", 0.0)), float(d.get("score", -1.0))),
                    reverse=True,
                )
                ranked_masks: list[dict] = []
                for idx, item in enumerate(ranked[:3], start=1):
                    mask_r = np.zeros_like(mask, dtype=np.uint8)
                    cnt = item.get("contour", None)
                    if cnt is not None:
                        try:
                            cv2.drawContours(mask_r, [cnt], -1, 255, -1)
                        except Exception:
                            pass
                    else:
                        try:
                            cx_r, cy_r, rr_r = item.get("circle", (0.0, 0.0, 0.0))
                            cx_i = int(round(float(cx_r)))
                            cy_i = int(round(float(cy_r)))
                            rr_i = int(round(float(rr_r)))
                            if rr_i > 1:
                                cv2.circle(mask_r, (cx_i, cy_i), rr_i, 255, -1)
                        except Exception:
                            pass
                    ranked_masks.append({
                        "rank": int(idx),
                        "mask": mask_r,
                        "v_med": float(item.get("v_med", 0.0)),
                        "score": float(item.get("score", -1.0)),
                        "area": float(cv2.countNonZero(mask_r)) if mask_r is not None else 0.0,
                    })

                # If fewer than 3 ranked masks, fill with largest combined-mask contours
                try:
                    if len(ranked_masks) < 3:
                        used_mask = np.zeros_like(mask, dtype=np.uint8)
                        for rm in ranked_masks:
                            m = rm.get("mask", None)
                            if m is not None and getattr(m, "size", 0) > 0:
                                used_mask = cv2.bitwise_or(used_mask, m)

                        cnts_all, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        cnts_all = sorted(cnts_all, key=cv2.contourArea, reverse=True)
                        for cnt in cnts_all:
                            if len(ranked_masks) >= 3:
                                break
                            if cv2.contourArea(cnt) <= 0:
                                continue
                            mask_c = np.zeros_like(mask, dtype=np.uint8)
                            try:
                                cv2.drawContours(mask_c, [cnt], -1, 255, -1)
                            except Exception:
                                continue
                            overlap = cv2.countNonZero(cv2.bitwise_and(used_mask, mask_c))
                            area_c = float(cv2.countNonZero(mask_c))
                            if area_c <= 0:
                                continue
                            if overlap / max(1.0, area_c) > 0.6:
                                continue
                            ranked_masks.append({
                                "rank": int(len(ranked_masks) + 1),
                                "mask": mask_c,
                                "v_med": 0.0,
                                "score": -1.0,
                                "area": float(area_c),
                            })
                            used_mask = cv2.bitwise_or(used_mask, mask_c)
                except Exception:
                    pass
                self._refine_debug["ranked_masks"] = ranked_masks
            except Exception:
                self._refine_debug["ranked_masks"] = []

            try:
                best_item = max(select_candidates, key=lambda d: float(d.get("score", -1.0)))
            except Exception:
                best_item = select_candidates[0]

            # If we see two similar blobs (ball + reflection), prefer the upper one.
            try:
                pairs = []
                for i in range(len(select_candidates)):
                    for j in range(i + 1, len(select_candidates)):
                        a = select_candidates[i]
                        b = select_candidates[j]
                        r0 = float(min(a["r"], b["r"]))
                        if r0 <= 1.0:
                            continue
                        dx = abs(float(a["cx"]) - float(b["cx"]))
                        dy = abs(float(a["cy"]) - float(b["cy"]))
                        dr = abs(float(a["r"]) - float(b["r"]))
                        if dx > float(0.85 * r0):
                            continue
                        if dr > float(0.35 * r0):
                            continue
                        if dy < float(0.45 * r0):
                            continue
                        pairs.append((a, b, dx + dy + dr))

                if pairs:
                    pairs.sort(key=lambda t: float(t[2]))
                    a, b, _ = pairs[0]
                    upper = a if float(a["cy"]) <= float(b["cy"]) else b
                    lower = b if upper is a else a

                    inner_r_u = float(upper["r"]) * float(self.inner_ratio)
                    inner_r_l = float(lower["r"]) * float(self.inner_ratio)
                    hue_u = _circle_mask_coverage(float(upper["cx"]), float(upper["cy"]), inner_r_u, mask_h)
                    hue_l = _circle_mask_coverage(float(lower["cx"]), float(lower["cy"]), inner_r_l, mask_h)
                    inner_u = _circle_mask_coverage(float(upper["cx"]), float(upper["cy"]), inner_r_u, mask)
                    inner_l = _circle_mask_coverage(float(lower["cx"]), float(lower["cy"]), inner_r_l, mask)
                    v_u = float(upper.get("v_med", 0.0))
                    v_l = float(lower.get("v_med", 0.0))
                    sat_u = float(upper.get("sat_cov", 0.0))
                    sat_l = float(lower.get("sat_cov", 0.0))

                    # Prefer upper if metrics are comparable or v_med is close.
                    v_close = (v_u + 12.0) >= v_l
                    score_u = (0.45 * (v_u / 255.0)) + (0.25 * sat_u) + (0.20 * hue_u) + (0.10 * inner_u)
                    score_l = (0.45 * (v_l / 255.0)) + (0.25 * sat_l) + (0.20 * hue_l) + (0.10 * inner_l)
                    metrics_ok = score_u >= (score_l * 0.90)
                    if v_close or metrics_ok:
                        best_item = upper
                        try:
                            self._refine_debug["select"] = "upper-pair-heuristic"
                            self._refine_debug["pair_dx"] = float(dx)
                            self._refine_debug["pair_dy"] = float(dy)
                        except Exception:
                            pass
            except Exception:
                pass

            # Final: always pick highest v_med (primary), then score (secondary).
            try:
                if len(select_candidates) > 1:
                    cand_v_list = sorted([int(c.get("v_med", 0)) for c in select_candidates], reverse=True)
                    self._refine_debug["cand_v_med"] = cand_v_list
                    best_item = max(
                        select_candidates,
                        key=lambda d: (float(d.get("v_med", 0.0)), float(d.get("score", -1.0))),
                    )
                    self._refine_debug["select"] = "v-med-priority"
            except Exception:
                pass

            best_score = float(best_item.get("score", -1.0))
            best = CVBall(
                x=float(best_item["cx"]),
                y=float(best_item["cy"]),
                r=float(best_item["r"]),
                area=float(best_item["area"]),
                circularity=float(best_item["circ"]),
            )
            best_area = float(best_item["area"])
            best_circ = float(best_item["circ"])
            best_fill = float(best_item["fill"])
            best_score_dbg = float(best_item.get("score", best_score))
            best_strict = bool(best_item.get("strict", False))
            best_radial_score = float(best_item.get("radial_score", 0.0))
            best_radial_cov = float(best_item.get("radial_cov", 0.0))
            best_radial_total = int(best_item.get("radial_total", 0))
            best_radial_ring_area = int(best_item.get("radial_ring_area", 0))
            if best_item.get("radial_vis") is not None and best_item.get("radial_roi") is not None:
                self._refine_debug["radial_vis"] = best_item.get("radial_vis")
                self._refine_debug["radial_roi"] = best_item.get("radial_roi")

        # Build refined-candidate mask (post-refine/selection pool) for debug/hist.
        try:
            refined_mask = None
            if refined_candidates:
                refined_mask = np.zeros_like(mask, dtype=np.uint8)
                for c in refined_candidates:
                    try:
                        cx = int(round(float(c.get("cx", 0.0))))
                        cy = int(round(float(c.get("cy", 0.0))))
                        rr = int(round(float(c.get("r", 0.0))))
                    except Exception:
                        continue
                    if rr > 1:
                        cv2.circle(refined_mask, (cx, cy), rr, 255, -1)
            if refined_mask is not None:
                self._refine_debug["refined_mask"] = refined_mask
        except Exception:
            pass

        # Always publish debug, even when no detection.
        self.last_debug = {
            "thresholds": {
                "a_percentile": float(self.a_percentile),
                "a_min": int(self.a_min),
                "a_thr": int(a_thr),
                "a_p": float(a_p),
                "s_min": int(s_min),
                "v_min": int(v_min),
                "h_use": bool(self.h_use),
                "h_red_max": int(self.h_red_max),
                "h_red_min2": int(self.h_red_min2),
                "h_orange_min": int(self.h_orange_min),
                "h_orange_max": int(self.h_orange_max),
                "min_solid_sat_coverage": float(self.min_solid_sat_coverage),
                "min_v_coverage": float(self.min_v_coverage),
                "min_v_median": int(self.min_v_median),
                "v_strong": int(self.v_strong),
                "min_radial_score": float(self.min_radial_score),
                "min_radial_coverage": float(self.min_radial_coverage),
                "radial_gate_enabled": bool(self.radial_gate_enabled),
            },
            "counts": {
                "contours_total": int(n_total),
                "considered": int(n_considered),
                "strict": int(n_strict),
                "cand_v_med": self._refine_debug.get("cand_v_med", []),
            },
            "best": {
                "score": float(best_score_dbg),
                "area": float(best_area),
                "circularity": float(best_circ),
                "fill": float(best_fill),
                "v_cov": float(best_item.get("v_cov", 0.0)) if best_item is not None else 0.0,
                "v_med": float(best_item.get("v_med", 0.0)) if best_item is not None else 0.0,
                "sat_cov": float(best_item.get("sat_cov", 0.0)) if best_item is not None else 0.0,
                "radial_score": float(best_radial_score),
                "radial_cov": float(best_radial_cov),
                "radial_edge_total": int(best_radial_total),
                "radial_ring_area": int(best_radial_ring_area),
            },
        }

        # Top-N rejected contours (largest-first) with reason breakdown.
        try:
            rejects_sorted = sorted(rejects, key=lambda d: float(d.get("area", 0.0) or 0.0), reverse=True)
            self.last_debug["rejects"] = rejects_sorted[: int(self.debug_top_n_rejects)]
        except Exception:
            self.last_debug["rejects"] = []

        try:
            self.last_debug["masks"] = {
                "lab": mask_lab,
                "sv": mask_sv,
                "hue": mask_h,
                "combined": mask,
                "refined": self._refine_debug.get("refined_mask", None),
                "ranked": self._refine_debug.get("ranked_masks", []),
            }
        except Exception:
            self.last_debug["masks"] = {}

        def _format_candidate_rankings(accept_best: bool, best_item_ref: Optional[dict], reject_reason: str = "") -> str:
            try:
                items: list[dict] = []
                for c in candidates:
                    items.append({
                        "kind": "candidate",
                        "cx": c.get("cx", None),
                        "cy": c.get("cy", None),
                        "r": c.get("r", None),
                        "area": c.get("area", 0.0),
                        "circ": c.get("circ", 0.0),
                        "fill": c.get("fill", 0.0),
                        "v_med": c.get("v_med", 0.0),
                        "_ref": c,
                    })
                for rj in rejects:
                    items.append({
                        "kind": "reject",
                        "cx": rj.get("cx", None),
                        "cy": rj.get("cy", None),
                        "r": rj.get("r", None),
                        "area": rj.get("area", 0.0),
                        "circ": rj.get("circ", 0.0),
                        "fill": rj.get("fill", 0.0),
                        "v_med": rj.get("v_med", None),
                        "reason": rj.get("reason", ""),
                        "_ref": None,
                    })

                def _same_candidate(item: dict, ref: Optional[dict]) -> bool:
                    if ref is None:
                        return False
                    if item.get("_ref", None) is ref:
                        return True
                    try:
                        if item.get("cx") is None or item.get("cy") is None or item.get("r") is None:
                            return False
                        return (
                            abs(float(item.get("cx", 0.0)) - float(ref.get("cx", 0.0))) < 0.5
                            and abs(float(item.get("cy", 0.0)) - float(ref.get("cy", 0.0))) < 0.5
                            and abs(float(item.get("r", 0.0)) - float(ref.get("r", 0.0))) < 0.5
                        )
                    except Exception:
                        return False

                items_sorted = sorted(items, key=lambda d: float(d.get("v_med", 0.0) or 0.0), reverse=True)
                try:
                    ranked_items = []
                    for idx, item in enumerate(items_sorted, start=1):
                        ranked_items.append({
                            "rank": int(idx),
                            "cx": item.get("cx", None),
                            "cy": item.get("cy", None),
                            "r": item.get("r", None),
                            "kind": item.get("kind", ""),
                            "accepted": bool(accept_best) and _same_candidate(item, best_item_ref),
                        })
                    self.last_debug["ranked_items"] = ranked_items
                except Exception:
                    self.last_debug["ranked_items"] = []
                lines: list[str] = []
                lines.append(
                    "Detecting Threshold: ("
                    f"A{float(self.min_area):.0f} "
                    f"C{float(self.min_circularity):.3f} "
                    f"F{float(self.min_fill):.3f} "
                    f"r{float(self.min_radius):.1f} "
                    f"V{float(self.min_v_median_candidate):.0f}"
                    ")"
                )
                lines.append(
                    f"Contour Candidates: {len(items_sorted)} (considered:{n_considered} strict:{n_strict})"
                )
                for idx, item in enumerate(items_sorted, start=1):
                    v_med_raw = item.get("v_med", None)
                    v_med = float(v_med_raw) if v_med_raw is not None else 0.0
                    area = float(item.get("area_dbg", item.get("area", 0.0)) or 0.0)
                    circ = float(item.get("circ_dbg", item.get("circ", 0.0)) or 0.0)
                    fill = float(item.get("fill", 0.0) or 0.0)
                    rr = float(item.get("r", 0.0) or 0.0)
                    accepted = bool(accept_best) and _same_candidate(item, best_item_ref)
                    status = "Accepted" if accepted else "Rejected"
                    color = "#55e36b" if accepted else "#ff6b6b"
                    suffix = " ***" if accepted else ""
                    reason = ""
                    if item.get("kind") == "reject":
                        reason = str(item.get("reason", "") or "")
                    elif (not accept_best) and reject_reason and _same_candidate(item, best_item_ref):
                        reason = str(reject_reason or "")
                    vmed_label = f"V-med {v_med:.0f}" if v_med_raw is not None else "V-med N/A"
                    vmed_token = f"{v_med:.0f}" if v_med_raw is not None else "NA"
                    line = (
                        f"#{idx}. {status}: {vmed_label} "
                        f"( A{area:.0f} C{circ:.3f} F{fill:.3f} r{rr:.1f} V{vmed_token} ){suffix}"
                    )
                    if reason:
                        line = f"{line} [reason: {reason}]"
                    lines.append(f"<span style=\"color:{color};\">{line}</span>")
                # Pad to always show #1-#3
                if len(items_sorted) < 3:
                    for idx in range(len(items_sorted) + 1, 4):
                        line = f"#{idx}. Rejected: V-med N/A ( A0 C0.000 F0.000 r0.0 VNA )"
                        lines.append(f"<span style=\"color:#ff6b6b;\">{line}</span>")
                return "\n".join(lines).strip()
            except Exception:
                return ""

        def _attempt_distance_fallback() -> Optional[CVBall]:
            # Fallback for merged ball+reflection blobs: use distance transform peak.
            try:
                if mask is None or getattr(mask, "size", 0) == 0:
                    return None
                if int(cv2.countNonZero(mask)) < int(self.min_area):
                    return None

                # Connected component stats to reject huge background blobs.
                num, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), connectivity=8)
                if num <= 1:
                    return None

                dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(dist)

                # In shiny-floor cases the mask can contain two similar circles: ball (upper)
                # and its reflection (lower). Prefer the UPPER peak among strong peaks.
                peaks: list[tuple[int, int, float]] = []
                try:
                    dist_work = dist.copy()
                    global_max = float(max_val)
                    for _ in range(6):
                        _, mv, _, ml = cv2.minMaxLoc(dist_work)
                        mv = float(mv)
                        if mv <= 0.0:
                            break
                        px, py = int(ml[0]), int(ml[1])
                        peaks.append((px, py, mv))
                        # Suppress a neighborhood so we can find another peak.
                        sup_r = int(max(6, round(mv * 0.85)))
                        cv2.circle(dist_work, (px, py), sup_r, 0.0, -1)

                    # Keep only peaks close to global max (similar circle size), then pick upper-most.
                    strong = [p for p in peaks if p[2] >= 0.90 * global_max]
                    if strong:
                        strong_sorted = sorted(strong, key=lambda t: (t[1], -t[2]))
                        cx_i, cy_i, est_r = strong_sorted[0]
                    else:
                        cx_i, cy_i = int(max_loc[0]), int(max_loc[1])
                        est_r = float(max_val)
                except Exception:
                    cx_i, cy_i = int(max_loc[0]), int(max_loc[1])
                    est_r = float(max_val)

                if est_r < 8.0 or est_r > float(max_r):
                    return None

                lbl = int(labels[cy_i, cx_i]) if 0 <= cy_i < labels.shape[0] and 0 <= cx_i < labels.shape[1] else 0
                if lbl <= 0:
                    return None
                comp_area = float(stats[lbl, cv2.CC_STAT_AREA])
                if comp_area < float(self.min_area) or comp_area > img_area * float(self.max_area_ratio):
                    return None

                # Sanity: the inner circle should be largely covered by the combined mask.
                inner_r = float(est_r) * float(self.inner_ratio)
                inner_cov = _circle_mask_coverage(float(cx_i), float(cy_i), float(inner_r), mask)
                if inner_cov < float(self.min_inner_mask_coverage):
                    return None

                # Sanity: require some circular edge energy around the estimated radius.
                ring_den = _edge_ring_density(float(cx_i), float(cy_i), float(est_r))
                if ring_den < float(self.min_edge_ring_density_non_strict):
                    return None

                # Try refine circle edges around this seed.
                refined2 = self._refine_circle_edges(frame_bgr, float(cx_i), float(cy_i), float(est_r))
                if refined2 is not None:
                    x2, y2, r2 = refined2
                    if float(self.min_radius) <= float(r2) <= float(max_r):
                        det2 = CVBall(x=float(x2), y=float(y2), r=float(r2), area=float(comp_area), circularity=0.0)
                        self.last_debug["fallback"] = {
                            "method": "distance",
                            "center": (cx_i, cy_i),
                            "r_est": float(est_r),
                            "comp_area": float(comp_area),
                            "inner_cov": float(inner_cov),
                            "ring_den": float(ring_den),
                            "peaks_n": int(len(peaks) if isinstance(peaks, list) else 0),
                            "upper_pref": True,
                        }
                        return det2

                # If refinement fails, do not accept distance-only (too many false positives).
                self.last_debug["fallback"] = {
                    "method": "distance",
                    "center": (cx_i, cy_i),
                    "r_est": float(est_r),
                    "comp_area": float(comp_area),
                    "inner_cov": float(inner_cov),
                    "ring_den": float(ring_den),
                    "peaks_n": int(len(peaks) if isinstance(peaks, list) else 0),
                    "upper_pref": True,
                    "refine": "failed",
                    "accepted": False,
                }
                return None
            except Exception:
                return None

        if best is None:
            fb = _attempt_distance_fallback()
            if fb is not None:
                fb.r = float(fb.r) * 1.10
                self.last_debug["refine"] = {"attempted": True, "ok": bool(self._refine_debug), **(self._refine_debug or {})}
                cand_report = _format_candidate_rankings(False, best_item)
                self.last_debug["text"] = (
                    "CVexpert (Lab a + HSV)\n"
                    f"a>=max({int(self.a_min)},p{int(self.a_percentile)}={a_p:.1f}) => {a_thr} | S>={s_min} V>={v_min}"
                    + (
                        f" | H:red<= {int(self.h_red_max)} or >= {int(self.h_red_min2)}, orange {int(self.h_orange_min)}-{int(self.h_orange_max)}\n"
                        if self.h_use
                        else "\n"
                    )
                    + f"contours:{n_total} considered:{n_considered} strict:{n_strict}\n"
                    + (cand_report + "\n" if cand_report else "")
                    + f"best: none -> fallback distance @ ({fb.x:.0f},{fb.y:.0f}) r~{fb.r:.1f}\n"
                ).strip()
                self.last_debug["vis"] = self._make_debug_mosaic(frame_bgr, mask_lab, mask_h, mask, (fb.x, fb.y), fb.r)
                self._log_detection("Detected !", "fallback-distance", fb)
                return fb, mask

            self.last_debug["refine"] = {"attempted": False, "ok": False}
            cand_report = _format_candidate_rankings(False, best_item)
            self.last_debug["text"] = (
                "CVexpert (Lab a + HSV)\n"
                f"a>=max({int(self.a_min)},p{int(self.a_percentile)}={a_p:.1f}) => {a_thr} | S>={s_min} V>={v_min}"
                + (f" | H:red<= {int(self.h_red_max)} or >= {int(self.h_red_min2)}, orange {int(self.h_orange_min)}-{int(self.h_orange_max)}\n" if self.h_use else "\n")
                + f"contours:{n_total} considered:{n_considered} strict:{n_strict}\n"
                + (cand_report + "\n" if cand_report else "")
                + "best: none"
            )
            self.last_debug["vis"] = self._make_debug_mosaic(frame_bgr, mask_lab, mask_h, mask, None, None)
            self._log_detection("No Ball", "no-contour-or-fallback", None)
            return None, mask

        refined = self._refine_circle_edges(frame_bgr, best.x, best.y, best.r)
        refine_ok = False
        if refined is not None:
            best.x, best.y, best.r = refined
            refine_ok = True

        self.last_debug["refine"] = {"attempted": True, "ok": bool(refine_ok), **(self._refine_debug or {})}

        # Post-check confidence: avoid accepting flat reflections / random red patches.
        inner_r_best = float(best.r) * float(self.inner_ratio)
        inner_cov_best = _circle_mask_coverage(best.x, best.y, inner_r_best, mask)
        hue_cov_best = _circle_mask_coverage(best.x, best.y, inner_r_best, mask_h)
        v_cov_best = _circle_v_coverage(best.x, best.y, inner_r_best, v)
        v_med_best = _circle_v_median(best.x, best.y, inner_r_best, v, mask)
        sat_cov_best = _circle_sat_coverage(best.x, best.y, inner_r_best, s, v)
        ring_den_best = _edge_ring_density(best.x, best.y, best.r)
        self.last_debug["best"]["inner_cov"] = float(inner_cov_best)
        self.last_debug["best"]["hue_cov"] = float(hue_cov_best)
        self.last_debug["best"]["v_cov"] = float(v_cov_best)
        self.last_debug["best"]["v_med"] = float(v_med_best)
        self.last_debug["best"]["sat_cov"] = float(sat_cov_best)
        self.last_debug["best"]["ring_den"] = float(ring_den_best)

        roi_stats = _rect_roi_stats(best.x, best.y, best.r, mask, v)
        if roi_stats:
            self.last_debug["roi_stats"] = roi_stats

        radial_score, radial_cov, radial_vis, radial_roi, radial_total, radial_ring_area = _radial_edge_symmetry(best.x, best.y, best.r)
        self.last_debug["best"]["radial_score"] = float(radial_score)
        self.last_debug["best"]["radial_cov"] = float(radial_cov)
        self.last_debug["best"]["radial_edge_total"] = int(radial_total)
        self.last_debug["best"]["radial_ring_area"] = int(radial_ring_area)
        try:
            if float(radial_cov) >= float(self.min_radial_coverage):
                score_adj = float(best_score_dbg) * (0.5 + 0.5 * float(radial_score))
            else:
                score_adj = float(best_score_dbg)
        except Exception:
            score_adj = float(best_score_dbg)
        self.last_debug["best"]["score_adj"] = float(score_adj)
        if radial_vis is not None and radial_roi is not None:
            try:
                self._refine_debug["radial_vis"] = radial_vis
                self._refine_debug["radial_roi"] = radial_roi
            except Exception:
                pass

        accept = True
        accept_reason = ""
        ring_waive = (
            (float(hue_cov_best) >= 0.85)
            and (float(inner_cov_best) >= 0.75)
            and (float(best_circ) >= 0.56)
            and (
                bool(refine_ok)
                or (float(ring_den_best) >= float(self.min_edge_ring_density_non_strict) * 0.80)
            )
        )
        if float(v_med_best) >= float(self.v_med_ring_waive):
            ring_waive = True
        if best_strict:
            # Ring-density gate disabled (strict). Keep ring_den for diagnostics only.
            # if (not refine_ok) and (ring_den_best < float(self.min_edge_ring_density)) and (not ring_waive):
            #     accept = False
            #     accept_reason = f"strict-but-weak-ring (ring<{self.min_edge_ring_density})"
            pass
        else:
            # Non-strict: skip ring gate entirely; rely on color/brightness checks only (shadow/blur tolerance)
            # if (not refine_ok) and (ring_den_best < float(self.min_edge_ring_density_non_strict)) and (not ring_waive):
            #     accept = False
            #     accept_reason = f"non-strict-weak-ring (ring<{self.min_edge_ring_density_non_strict})"
            if inner_cov_best < float(self.min_inner_mask_coverage):
                accept = False
                accept_reason = f"low-inner-cov (cov<{self.min_inner_mask_coverage})"
        if hue_cov_best < float(self.min_hue_coverage):
            accept = False
            accept_reason = f"low-hue-cov (cov<{self.min_hue_coverage})"
        if v_med_best < float(self.min_v_median):
            accept = False
            accept_reason = f"low-v-med (med<{self.min_v_median})"
        if sat_cov_best < float(self.min_solid_sat_coverage):
            accept = False
            accept_reason = f"low-sat-cov (cov<{self.min_solid_sat_coverage})"
        if bool(self.radial_gate_enabled) and bool(best_strict):
            radial_weak = (float(radial_score) < float(self.min_radial_score)) and (float(radial_cov) < float(self.min_radial_coverage))
            ring_strong = float(ring_den_best) >= float(self.min_edge_ring_density) * 1.25
            if radial_weak and (not refine_ok) and (not ring_strong):
                accept = False
                accept_reason = (
                    f"weak-radial (score<{self.min_radial_score} and cov<{self.min_radial_coverage})"
                )

        if not accept:
            # Last chance: distance fallback, but only if it passes the stricter checks (and refine)
            fb = _attempt_distance_fallback()
            if fb is not None:
                fb.r = float(fb.r) * 1.10
                cand_report = _format_candidate_rankings(False, best_item, accept_reason)
                roi_stats = self.last_debug.get("roi_stats", {}) or {}
                roi_line = ""
                if roi_stats:
                    roi_line = (
                        f"roi: Vmed={float(roi_stats.get('v_med', 0.0)):.0f} "
                        f"circ={float(roi_stats.get('circ', 0.0)):.3f} "
                        f"fill={float(roi_stats.get('fill', 0.0)):.3f}\n"
                    )
                self.last_debug["text"] = (
                    "CVexpert (Lab a + HSV)\n"
                    f"a>=max({int(self.a_min)},p{int(self.a_percentile)}={a_p:.1f}) => {a_thr} | S>={s_min} V>={v_min}"
                    + (f" | H:red<= {int(self.h_red_max)} or >= {int(self.h_red_min2)}, orange {int(self.h_orange_min)}-{int(self.h_orange_max)}\n" if self.h_use else "\n")
                    + f"contours:{n_total} considered:{n_considered} strict:{n_strict}\n"
                    + (cand_report + "\n" if cand_report else "")
                    + f"best(contour): score={best_score_dbg:.0f} adj={score_adj:.0f} area={best_area:.0f} circ={best_circ:.3f} fill={best_fill:.3f} (rejected:{accept_reason})\n"
                    + f"metrics: Vmed={v_med_best:.0f} | inner_cov={inner_cov_best:.2f} hue_cov={hue_cov_best:.2f} v_cov={v_cov_best:.2f} sat_cov={sat_cov_best:.2f} ring_den={ring_den_best:.3f} radial={radial_score:.2f} cov={radial_cov:.2f}\n"
                    + roi_line
                    + f"fallback: distance+refine @ ({fb.x:.0f},{fb.y:.0f}) r~{fb.r:.1f}\n"
                ).strip()
                self.last_debug["vis"] = self._make_debug_mosaic(frame_bgr, mask_lab, mask_h, mask, (fb.x, fb.y), fb.r)
                self._log_detection("Detected !", "fallback-distance", fb)
                return fb, mask

            roi_stats = self.last_debug.get("roi_stats", {}) or {}
            roi_line = ""
            if roi_stats:
                roi_line = (
                    f"roi: Vmed={float(roi_stats.get('v_med', 0.0)):.0f} "
                    f"circ={float(roi_stats.get('circ', 0.0)):.3f} "
                    f"fill={float(roi_stats.get('fill', 0.0)):.3f}\n"
                )
            cand_report = _format_candidate_rankings(False, best_item, accept_reason)
            self.last_debug["text"] = (
                "CVexpert (Lab a + HSV)\n"
                f"a>=max({int(self.a_min)},p{int(self.a_percentile)}={a_p:.1f}) => {a_thr} | S>={s_min} V>={v_min}"
                + (f" | H:red<= {int(self.h_red_max)} or >= {int(self.h_red_min2)}, orange {int(self.h_orange_min)}-{int(self.h_orange_max)}\n" if self.h_use else "\n")
                + f"contours:{n_total} considered:{n_considered} strict:{n_strict}\n"
                + (cand_report + "\n" if cand_report else "")
                + f"best(contour): score={best_score_dbg:.0f} adj={score_adj:.0f} area={best_area:.0f} circ={best_circ:.3f} fill={best_fill:.3f} (rejected:{accept_reason})\n"
                + f"metrics: Vmed={v_med_best:.0f} | inner_cov={inner_cov_best:.2f} hue_cov={hue_cov_best:.2f} v_cov={v_cov_best:.2f} sat_cov={sat_cov_best:.2f} ring_den={ring_den_best:.3f} radial={radial_score:.2f} cov={radial_cov:.2f} refine_ok={int(bool(refine_ok))}"
                + ("\n" + roi_line if roi_line else "")
            ).strip()
            self.last_debug["vis"] = self._make_debug_mosaic(frame_bgr, mask_lab, mask_h, mask, None, None)
            self._log_detection("No Ball", accept_reason or "rejected", None)
            return None, mask

        # If we got here, accept the contour-based estimate (ideally refined).
        best.r = float(best.r) * 1.10

        cand_report = _format_candidate_rankings(True, best_item)
        roi_stats = self.last_debug.get("roi_stats", {}) or {}
        roi_line = ""
        if roi_stats:
            roi_line = (
                f"roi: Vmed={float(roi_stats.get('v_med', 0.0)):.0f} "
                f"circ={float(roi_stats.get('circ', 0.0)):.3f} "
                f"fill={float(roi_stats.get('fill', 0.0)):.3f}\n"
            )
        self.last_debug["text"] = (
            "CVexpert (Lab a + HSV)\n"
            f"a>=max({int(self.a_min)},p{int(self.a_percentile)}={a_p:.1f}) => {a_thr} | S>={s_min} V>={v_min}"
            + (
                f" | H:red<= {int(self.h_red_max)} or >= {int(self.h_red_min2)}, orange {int(self.h_orange_min)}-{int(self.h_orange_max)}\n"
                if self.h_use
                else "\n"
            )
            + f"contours:{n_total} considered:{n_considered} strict:{n_strict}\n"
            + (cand_report + "\n" if cand_report else "")
            + f"best: score={best_score_dbg:.0f} adj={score_adj:.0f} area={best_area:.0f} circ={best_circ:.3f} fill={best_fill:.3f}"
            + (" (strict)" if best_strict else "")
            + (" (refined)" if refine_ok else "")
            + f" | Vmed={v_med_best:.0f} | inner_cov={inner_cov_best:.2f} hue_cov={hue_cov_best:.2f} v_cov={v_cov_best:.2f} sat_cov={sat_cov_best:.2f} ring_den={ring_den_best:.3f} radial={radial_score:.2f} cov={radial_cov:.2f}"
            + "\n"
            + (roi_line if roi_line else "")
            + f"circle: ({best.x:.1f},{best.y:.1f}) r={best.r:.1f} (inflated 1.10x)"
        )
        self.last_debug["vis"] = self._make_debug_mosaic(
            frame_bgr,
            mask_lab,
            mask_h,
            mask,
            (best.x, best.y),
            best.r,
        )

        self._log_detection("Detected !", "contour", best)
        return best, mask

    def _make_debug_mosaic(
        self,
        frame_bgr: np.ndarray,
        mask_lab: np.ndarray,
        mask_hsv: np.ndarray,
        mask_combined: np.ndarray,
        center_xy: Optional[Tuple[float, float]],
        radius: Optional[float],
    ) -> Optional[np.ndarray]:
        try:
            h, w = frame_bgr.shape[:2]
        except Exception:
            return None

        def to_bgr(m):
            try:
                if m is None:
                    return None
                if len(m.shape) == 2:
                    return cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)
                return m.copy()
            except Exception:
                return None

        tl = to_bgr(mask_lab)
        tr = to_bgr(mask_hsv)
        bl = to_bgr(mask_combined)

        def _draw_dotted_circle(img: np.ndarray, center: Tuple[int, int], r_px: int, color, thickness: int = 1) -> None:
            try:
                if r_px <= 1:
                    return
                cx_d, cy_d = center
                step_deg = 18
                for ang in range(0, 360, step_deg):
                    rad = np.deg2rad(float(ang))
                    x = int(round(cx_d + r_px * np.cos(rad)))
                    y = int(round(cy_d + r_px * np.sin(rad)))
                    cv2.circle(img, (x, y), max(1, thickness), color, -1)
            except Exception:
                return

        def _draw_ranked_labels(img: Optional[np.ndarray]) -> None:
            try:
                if img is None:
                    return
                ranked_dbg = self.last_debug.get("ranked_items", []) or []
                for item in ranked_dbg:
                    try:
                        rank = int(item.get("rank", 0) or 0)
                        if rank <= 0:
                            continue
                        cx_r = item.get("cx", None)
                        cy_r = item.get("cy", None)
                        rr_r = item.get("r", None)
                        if cx_r is None or cy_r is None or rr_r is None:
                            continue
                        cx_i = int(round(float(cx_r)))
                        cy_i = int(round(float(cy_r)))
                        rr_i = int(round(float(rr_r)))
                        cx_i = max(0, min(w - 1, cx_i))
                        cy_i = max(0, min(h - 1, cy_i))
                        if rr_i > 0:
                            _draw_dotted_circle(img, (cx_i, cy_i), rr_i, (255, 0, 255), thickness=1)
                        cv2.circle(img, (cx_i, cy_i), 1, (255, 0, 255), -1)
                        tx = max(2, min(w - 2, cx_i + max(6, int(round(rr_i * 0.6)))))
                        ty = max(12, min(h - 2, cy_i - max(2, int(round(rr_i * 0.6)))))
                        tag = f"#{rank}"
                        cv2.putText(img, tag, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                        cv2.putText(img, tag, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 1)
                    except Exception:
                        continue
            except Exception:
                return


        _draw_ranked_labels(bl)

        if bl is not None and center_xy is not None:
            try:
                cx, cy = int(round(float(center_xy[0]))), int(round(float(center_xy[1])))
                rr = int(round(float(radius or 0.0)))
                cx = max(0, min(w - 1, cx))
                cy = max(0, min(h - 1, cy))
                if rr > 0:
                    cv2.circle(bl, (cx, cy), rr, (0, 255, 255), 2)
                cv2.circle(bl, (cx, cy), 2, (0, 255, 255), -1)
            except Exception:
                pass

        br = None
        try:
            br = frame_bgr.copy()
            # Contour overlay (combined mask) on BR pane., in yellow., 
            try:
                cnts, _ = cv2.findContours(mask_combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(br, cnts, -1, (0, 255, 255), 1)
            except Exception:
                pass
            # Contour overlay (refined candidate mask) on BR pane., in green.
            try:
                refined_mask = self._refine_debug.get("refined_mask", None)
                if refined_mask is not None and getattr(refined_mask, "size", 0) > 0:
                    cnts_ref, _ = cv2.findContours(refined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.drawContours(br, cnts_ref, -1, (0, 255, 0), 1)
            except Exception:
                pass
            _draw_ranked_labels(br)
            if center_xy is not None:
                cx, cy = int(round(float(center_xy[0]))), int(round(float(center_xy[1])))   # Draw detected circle, cx,cy is center
                rr = int(round(float(radius or 0.0)))   # Draw detected circle. rr is radius
                cx = max(0, min(w - 1, cx))     # w is width of image
                cy = max(0, min(h - 1, cy))
                if rr > 0:
                    cv2.circle(br, (cx, cy), rr, (0, 255, 255), 2)
                cv2.circle(br, (cx, cy), 2, (0, 255, 255), -1)
        except Exception:
            br = None

        # Optional refine edges preview as an inset on BR., it's for debug purposes. it appears as a small box in the top-left corner of the BR pane.
        try:
            edges = self._refine_debug.get("roi_edges", None)
            x0 = int(self._refine_debug.get("roi_x0", 0) or 0)
            y0 = int(self._refine_debug.get("roi_y0", 0) or 0)
            if br is not None and edges is not None and getattr(edges, "size", 0) > 0:  # if edges exist, br is not None
                e = to_bgr(edges)
                eh, ew = e.shape[:2]
                # Resize inset to fit
                inset_w = max(60, int(round(br.shape[1] * 0.35)))
                inset_h = max(45, int(round(inset_w * (eh / max(1, ew)))))
                inset = cv2.resize(e, (inset_w, inset_h), interpolation=cv2.INTER_NEAREST)
                br[0:inset_h, 0:inset_w] = inset
                cv2.rectangle(br, (0, 0), (inset_w - 1, inset_h - 1), (0, 255, 255), 1)
                # Draw ROI rectangle
                if x0 or y0:
                    cv2.rectangle(br, (x0, y0), (int(self._refine_debug.get("roi_x1", 0) or 0), int(self._refine_debug.get("roi_y1", 0) or 0)), (0, 255, 255), 1)
            radial_vis = self._refine_debug.get("radial_vis", None)
            if br is not None and radial_vis is not None and getattr(radial_vis, "size", 0) > 0:
                rv = to_bgr(radial_vis)
                rvh, rvw = rv.shape[:2]
                inset_w = max(60, int(round(br.shape[1] * 0.35)))
                inset_h = max(45, int(round(inset_w * (rvh / max(1, rvw)))))
                inset = cv2.resize(rv, (inset_w, inset_h), interpolation=cv2.INTER_NEAREST)
                x_off = max(0, br.shape[1] - inset_w)
                br[0:inset_h, x_off : x_off + inset_w] = inset
                cv2.rectangle(br, (x_off, 0), (x_off + inset_w - 1, inset_h - 1), (0, 255, 255), 1)
        except Exception:
            pass

        panes = [tl, tr, bl, br]    # Order: top-left, top-right, bottom-left, bottom-right, BR pane has overlay
        if any(p is None for p in panes):
            return br if br is not None else None

        # Normalize pane sizes
        ph = max(1, int(round(h / 2)))
        pw = max(1, int(round(w / 2)))

        def draw_title(img: np.ndarray, title: str):
            try:
                if img is None or getattr(img, "size", 0) == 0:
                    return
                t = str(title or "")
                if not t:
                    return
                # Outline for readability on any background
                cv2.putText(img, t, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
                cv2.putText(img, t, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            except Exception:
                pass

        # Resize individual panes; make the color overlay pane (BR) 2x size
        tl_r = cv2.resize(panes[0], (pw, ph), interpolation=cv2.INTER_NEAREST)
        tr_r = cv2.resize(panes[1], (pw, ph), interpolation=cv2.INTER_NEAREST)
        bl_r = cv2.resize(panes[2], (pw, ph), interpolation=cv2.INTER_NEAREST)
        br_r = cv2.resize(panes[3], (pw * 2, ph * 2), interpolation=cv2.INTER_NEAREST)

        draw_title(tl_r, "Lab a-mask (redness)")
        draw_title(tr_r, "HSV mask (H,S,V gates)")
        draw_title(bl_r, "Combined mask")
        draw_title(br_r, "Overlay + contours (edges inset)")

        # Assemble custom canvas: 3x3 cells where BR occupies 2x2 cells.
        canvas_h = ph * 3
        canvas_w = pw * 3
        mosaic = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

        # Place TL, TR, BL
        mosaic[0:ph, 0:pw] = tl_r
        mosaic[0:ph, pw : 2 * pw] = tr_r
        mosaic[ph : 2 * ph, 0:pw] = bl_r
        # Place enlarged BR spanning bottom-right 2x2 cells
        mosaic[ph : 3 * ph, pw : 3 * pw] = br_r

        # Resize to a stable debug window size
        mosaic = cv2.resize(mosaic, (800, 600), interpolation=cv2.INTER_NEAREST)
        return mosaic

    def _refine_circle_edges(self, img_bgr: np.ndarray, cx: float, cy: float, r: float) -> Optional[Tuple[float, float, float]]:
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

        try:
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            s_roi = hsv_roi[:, :, 1]
            v_roi = hsv_roi[:, :, 2]
        except Exception:
            hsv_roi = None
            s_roi = None
            v_roi = None

        # For debug: edges within ROI (helps diagnose reflections)
        try:
            edges = cv2.Canny(gray, 60, 120)
        except Exception:
            edges = None

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
            self._refine_debug = {
                "roi_x0": x0,
                "roi_y0": y0,
                "roi_x1": x1,
                "roi_y1": y1,
                "roi_edges": edges,
                "hough_n": 0,
            }
            return None

        circles = np.round(circles[0, :]).astype(int)
        self._refine_debug = {
            "roi_x0": x0,
            "roi_y0": y0,
            "roi_x1": x1,
            "roi_y1": y1,
            "roi_edges": edges,
            "hough_n": int(len(circles)),
        }
        target = np.array([int(round(cx)) - x0, int(round(cy)) - y0], dtype=np.float32)

        # Prefer the upper circle when there are two circles (ball + reflection),
        # but require solid saturation coverage to avoid selecting the reflection.
        # Strategy:
        #   1) consider circles reasonably close to the seed (target)
        #   2) among them, prefer those with solid saturation coverage
        #   3) within that set, pick smallest y (upper-most)
        #   4) tie-breaker: closest distance to target
        best = None
        best_d = 1e9
        best_y = 1e9
        max_d_allow = float(max(30.0, 0.9 * float(r)))

        def _sat_coverage(x: int, y: int, rr: int) -> float:
            try:
                if s_roi is None or v_roi is None:
                    return 0.0
                rr = int(max(2, rr))
                x0c = max(0, x - rr)
                y0c = max(0, y - rr)
                x1c = min(s_roi.shape[1], x + rr + 1)
                y1c = min(s_roi.shape[0], y + rr + 1)
                if x1c <= x0c or y1c <= y0c:
                    return 0.0
                sub_s = s_roi[y0c:y1c, x0c:x1c]
                sub_v = v_roi[y0c:y1c, x0c:x1c]
                rr_sub = int(min(rr, min(sub_s.shape[1], sub_s.shape[0]) // 2))
                if rr_sub <= 1:
                    return 0.0
                cx_sub = int(x - x0c)
                cy_sub = int(y - y0c)
                circle = np.zeros(sub_s.shape[:2], dtype=np.uint8)
                cv2.circle(circle, (cx_sub, cy_sub), rr_sub, 255, -1)
                circle_area = float(cv2.countNonZero(circle))
                if circle_area <= 1.0:
                    return 0.0
                solid = cv2.bitwise_and(circle, ((sub_s >= int(self.s_min)) & (sub_v >= int(self.v_min))).astype(np.uint8) * 255)
                return float(cv2.countNonZero(solid)) / float(circle_area)
            except Exception:
                return 0.0

        # First pass: find candidates within distance threshold
        candidates = []
        for x, y, rr in circles:
            d = float(np.linalg.norm(np.array([x, y], dtype=np.float32) - target))
            if d <= max_d_allow:
                sat_cov = _sat_coverage(int(x), int(y), int(round(rr * 0.70)))
                candidates.append((x, y, rr, d, sat_cov))

        if candidates:
            solid = [c for c in candidates if float(c[4]) >= float(self.min_solid_sat_coverage)]
            chosen = solid if solid else candidates
            for x, y, rr, d, sat_cov in chosen:
                if (y < best_y) or (y == best_y and d < best_d):
                    best_y = float(y)
                    best_d = float(d)
                    best = (x, y, rr)
                    try:
                        self._refine_debug["sat_cov"] = float(sat_cov)
                        self._refine_debug["sat_cov_ok"] = bool(float(sat_cov) >= float(self.min_solid_sat_coverage))
                    except Exception:
                        pass
            try:
                self._refine_debug["select"] = "upper"
                self._refine_debug["max_d_allow"] = float(max_d_allow)
                self._refine_debug["solid_pref"] = bool(len(solid) > 0)
            except Exception:
                pass
        else:
            # Fallback: original closest-to-seed selection
            for x, y, rr in circles:
                d = float(np.linalg.norm(np.array([x, y], dtype=np.float32) - target))
                if d < best_d:
                    best_d = d
                    best = (x, y, rr)
            try:
                self._refine_debug["select"] = "closest"
                self._refine_debug["max_d_allow"] = float(max_d_allow)
            except Exception:
                pass

        if best is None:
            return None

        x, y, rr = best
        if best_d > max(30.0, 0.6 * float(r)):
            return None

        try:
            self._refine_debug["best_d"] = float(best_d)
        except Exception:
            pass

        return (float(x + x0), float(y + y0), float(rr))
