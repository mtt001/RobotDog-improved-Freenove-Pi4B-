#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - CloseLoop Auto Debug
 File   : clientai_model_consistency_probe.py
 Author : Codex

 Live consistency probe for `/color` ClientAI model choices:
 - switches model choice (`best`, `yolov8n`, `mix`) through page controls
 - samples `/api/clientai` plus detect banner/status text
 - computes lock/confidence stability metrics
 - writes JSON artifact for close-loop evidence

Version
v0.5 (2026-02-13 21:39)

Revision History
v0.5 (2026-02-13 21:39) : Added extended vision-quality metrics for tuning:
confidence percentiles, infer-latency stats, stale/armed ratios, reject-reason
counts, bbox area distribution, and center-jitter summary from
`/api/vision/client-target/latest` top detection snapshots.
v0.4 (2026-02-13 17:59) : Re-arm session before each model-choice phase and
record per-sample session `armed` state to prevent cross-phase disarm bleed.
v0.3 (2026-02-13 17:56) : Added session arm/disarm control during probe so
fresh `last_target` updates are collected for confidence consistency metrics.
v0.2 (2026-02-13 17:55) : Added freshness-aware confidence accounting
(`target_age_ms` gate) so stability metrics are computed from recent targets
instead of stale `last_target` snapshots.
v0.1 (2026-02-13 17:53) : Initial multi-model consistency probe with
deterministic artifact output and summary metrics (`conf_mean`, label switches,
drop events, detect ratio, model ids seen).
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


CHOICES = ("best", "yolov8n", "mix")


def api_json(url: str, *, method: str = "GET", payload: Dict[str, Any] | None = None, timeout: float = 6.0) -> Dict[str, Any]:
    body = None
    headers = {"Cache-Control": "no-store"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, method=method, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def percentile(values: List[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    pp = max(0.0, min(100.0, float(p)))
    idx = (pp / 100.0) * (len(xs) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return xs[lo]
    frac = idx - lo
    return xs[lo] + ((xs[hi] - xs[lo]) * frac)


def summarize_samples(samples: List[Dict[str, Any]], *, lock_conf: float, drop_delta: float, drop_floor: float) -> Dict[str, Any]:
    conf_values: List[float] = []
    infer_values: List[float] = []
    age_values: List[float] = []
    bbox_area_values: List[float] = []
    bbox_cx_values: List[float] = []
    bbox_cy_values: List[float] = []
    labels: List[str] = []
    detect_hits = 0
    model_ids = set()
    drop_events = 0
    prev_conf = None
    prev_label = None
    label_switches = 0
    stale_count = 0
    armed_count = 0
    reject_counts: Dict[str, int] = {}
    mode_mismatch_count = 0

    for s in samples:
        conf = s.get("top_conf")
        infer_ms = s.get("infer_ms")
        age_ms = s.get("target_age_ms")
        label = str(s.get("top_label") or "").strip()
        model_id = str(s.get("model_id") or "").strip()
        active_mode = str(s.get("active_mode") or "")
        reject = str(s.get("last_reject") or "")
        banner = str(s.get("detect_banner") or "")
        fresh = bool(s.get("target_fresh"))
        armed = bool(s.get("session_armed"))
        x1 = s.get("top_x1")
        y1 = s.get("top_y1")
        x2 = s.get("top_x2")
        y2 = s.get("top_y2")
        if model_id:
            model_ids.add(model_id)
        if "DETECTED:" in banner:
            detect_hits += 1
        if armed:
            armed_count += 1
        if active_mode.lower() != "client-ai":
            mode_mismatch_count += 1
        if reject:
            reject_counts[reject] = int(reject_counts.get(reject, 0)) + 1
        if isinstance(age_ms, (int, float)):
            age_values.append(float(age_ms))
            if float(age_ms) > 1500:
                stale_count += 1
        if fresh and isinstance(infer_ms, (int, float)):
            infer_values.append(float(infer_ms))
        if fresh and isinstance(conf, (float, int)) and conf > 0:
            conf = float(conf)
            conf_values.append(conf)
            labels.append(label)
            if prev_conf is not None and prev_conf >= lock_conf and conf <= max(prev_conf - drop_delta, drop_floor):
                drop_events += 1
            prev_conf = conf
            if all(isinstance(v, (int, float)) for v in (x1, y1, x2, y2)):
                w = max(0.0, float(x2) - float(x1))
                h = max(0.0, float(y2) - float(y1))
                if w > 0 and h > 0:
                    area = w * h
                    bbox_area_values.append(area)
                    bbox_cx_values.append((float(x1) + float(x2)) / 2.0)
                    bbox_cy_values.append((float(y1) + float(y2)) / 2.0)
        if label and prev_label and label != prev_label:
            label_switches += 1
        if label:
            prev_label = label

    conf_mean = round(statistics.fmean(conf_values), 4) if conf_values else None
    conf_std = round(statistics.pstdev(conf_values), 4) if len(conf_values) >= 2 else 0.0
    conf_min = round(min(conf_values), 4) if conf_values else None
    conf_max = round(max(conf_values), 4) if conf_values else None
    conf_p10 = round(percentile(conf_values, 10), 4) if conf_values else None
    conf_p50 = round(percentile(conf_values, 50), 4) if conf_values else None
    conf_p90 = round(percentile(conf_values, 90), 4) if conf_values else None

    infer_mean = round(statistics.fmean(infer_values), 3) if infer_values else None
    infer_std = round(statistics.pstdev(infer_values), 3) if len(infer_values) >= 2 else 0.0
    infer_p90 = round(percentile(infer_values, 90), 3) if infer_values else None
    age_mean = round(statistics.fmean(age_values), 2) if age_values else None

    area_mean = round(statistics.fmean(bbox_area_values), 5) if bbox_area_values else None
    area_std = round(statistics.pstdev(bbox_area_values), 5) if len(bbox_area_values) >= 2 else 0.0
    area_min = round(min(bbox_area_values), 5) if bbox_area_values else None
    area_max = round(max(bbox_area_values), 5) if bbox_area_values else None
    cx_std = round(statistics.pstdev(bbox_cx_values), 5) if len(bbox_cx_values) >= 2 else 0.0
    cy_std = round(statistics.pstdev(bbox_cy_values), 5) if len(bbox_cy_values) >= 2 else 0.0
    center_jitter = round(math.sqrt((cx_std ** 2) + (cy_std ** 2)), 5)

    return {
        "samples": len(samples),
        "valid_conf_samples": len(conf_values),
        "fresh_target_samples": sum(1 for s in samples if s.get("target_fresh")),
        "stale_ratio": round((stale_count / len(samples)), 4) if samples else 0.0,
        "armed_ratio": round((armed_count / len(samples)), 4) if samples else 0.0,
        "mode_mismatch_count": mode_mismatch_count,
        "detect_ratio": round((detect_hits / len(samples)), 4) if samples else 0.0,
        "conf_mean": conf_mean,
        "conf_std": conf_std,
        "conf_min": conf_min,
        "conf_max": conf_max,
        "conf_p10": conf_p10,
        "conf_p50": conf_p50,
        "conf_p90": conf_p90,
        "infer_ms_mean": infer_mean,
        "infer_ms_std": infer_std,
        "infer_ms_p90": infer_p90,
        "target_age_ms_mean": age_mean,
        "bbox_area_mean": area_mean,
        "bbox_area_std": area_std,
        "bbox_area_min": area_min,
        "bbox_area_max": area_max,
        "bbox_center_jitter": center_jitter,
        "label_switches": label_switches,
        "drop_events": drop_events,
        "labels_seen": sorted({x for x in labels if x}),
        "model_ids_seen": sorted(model_ids),
        "reject_reasons": dict(sorted(reject_counts.items(), key=lambda kv: kv[0])),
    }


def run(args: argparse.Namespace) -> int:
    if args.choice not in CHOICES and args.choice != "all":
        raise SystemExit(f"invalid --choice: {args.choice}")

    api_base = args.api_base.rstrip("/")
    page_url = args.page_url
    output_dir = Path(args.output_dir)
    ensure_dir(output_dir / "placeholder.txt")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"clientai_model_consistency_probe_{stamp}.json"

    targets = list(CHOICES) if args.choice == "all" else [args.choice]
    report: Dict[str, Any] = {
        "ok": True,
        "ts": time.time(),
        "api_base": api_base,
        "page_url": page_url,
        "scene_tag": args.scene_tag,
        "duration_sec": args.duration_sec,
        "interval_sec": args.interval_sec,
        "results": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.show)
        page = browser.new_page(viewport={"width": 1512, "height": 982})
        page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(2500)

        api_json(
            f"{api_base}/api/clientai",
            method="POST",
            payload={
                "action": "reset_auto",
                "mode": "client-ai",
                "client_ai_capable": True,
                "provider": "wasm",
            },
        )
        page.select_option("#clientai-mode", "client-ai")
        if args.arm_session:
            api_json(f"{api_base}/api/session", method="POST", payload={"armed": True})

        for choice in targets:
            if args.arm_session:
                api_json(f"{api_base}/api/session", method="POST", payload={"armed": True})
            page.select_option("#clientai-model-choice", choice)
            page.click("#clientai-apply")
            page.wait_for_timeout(1800)

            samples: List[Dict[str, Any]] = []
            t_end = time.time() + args.duration_sec
            while time.time() < t_end:
                st = api_json(f"{api_base}/api/clientai")
                sess = api_json(f"{api_base}/api/session")
                target_latest = api_json(f"{api_base}/api/vision/client-target/latest")
                top = (st.get("last_target") or {}) if isinstance(st, dict) else {}
                trk = (target_latest.get("tracking_consumer") or {}) if isinstance(target_latest, dict) else {}
                top_det = (trk.get("target") or {}).get("top_detection") if isinstance((trk.get("target") or {}), dict) else {}
                now_ms = int(time.time() * 1000)
                ts_client_ms = int(top.get("ts_client_ms", 0) or 0)
                age_ms = (now_ms - ts_client_ms) if ts_client_ms > 0 else None
                fresh = bool(age_ms is not None and -500 <= age_ms <= args.target_fresh_ms)
                detect_banner = ""
                status_text = ""
                if page.query_selector("#clientai-detect-banner"):
                    detect_banner = (page.query_selector("#clientai-detect-banner").inner_text() or "").strip()
                if page.query_selector("#clientai-status"):
                    status_text = (page.query_selector("#clientai-status").inner_text() or "").strip()
                samples.append(
                    {
                        "t": time.time(),
                        "active_mode": st.get("active_mode"),
                        "session_armed": bool(sess.get("armed")),
                        "model_id": st.get("model_id"),
                        "top_label": top.get("top_label"),
                        "top_conf": top.get("top_conf"),
                        "infer_ms": top.get("infer_ms"),
                        "target_age_ms": age_ms,
                        "target_fresh": fresh,
                        "top_x1": top_det.get("x1") if isinstance(top_det, dict) else None,
                        "top_y1": top_det.get("y1") if isinstance(top_det, dict) else None,
                        "top_x2": top_det.get("x2") if isinstance(top_det, dict) else None,
                        "top_y2": top_det.get("y2") if isinstance(top_det, dict) else None,
                        "accepted_count": st.get("accepted_count"),
                        "rejected_count": st.get("rejected_count"),
                        "last_reject": st.get("last_reject"),
                        "detect_banner": detect_banner,
                        "status_text": status_text,
                    }
                )
                time.sleep(max(0.2, args.interval_sec))

            report["results"][choice] = {
                "summary": summarize_samples(
                    samples,
                    lock_conf=args.lock_conf,
                    drop_delta=args.drop_delta,
                    drop_floor=args.drop_floor,
                ),
                "samples": samples,
            }

        if args.arm_session:
            api_json(f"{api_base}/api/session", method="POST", payload={"armed": False})
        browser.close()

    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    print(json.dumps({k: v["summary"] for k, v in report["results"].items()}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run model-choice consistency probe on /color")
    p.add_argument("--api-base", default="http://192.168.0.32:8090")
    p.add_argument("--page-url", default="http://192.168.0.32:8081/color")
    p.add_argument("--output-dir", default="Temp/snapshots")
    p.add_argument("--choice", default="all", choices=["all", *CHOICES])
    p.add_argument("--scene-tag", default="live_scene")
    p.add_argument("--duration-sec", type=float, default=12.0)
    p.add_argument("--interval-sec", type=float, default=1.0)
    p.add_argument("--lock-conf", type=float, default=0.75)
    p.add_argument("--drop-delta", type=float, default=0.20)
    p.add_argument("--drop-floor", type=float, default=0.40)
    p.add_argument("--target-fresh-ms", type=int, default=1500)
    p.add_argument("--arm-session", action="store_true", help="arm session during probe for fresh target updates")
    p.add_argument("--show", action="store_true", help="run non-headless browser")
    return p


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))
