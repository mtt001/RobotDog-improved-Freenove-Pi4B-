#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : mtBallDetectYOLO.py
 Author : MT & GitHub Copilot

 Description:
     Optional YOLO-based detection helpers (local inference).
     Supports single-class ball detection and multi-class queries.

 v1.01  (2026-02-01)          : Multi-class inference support
     • Add analyze_classes() for COCO multi-class usage while keeping analyze() stable.
 v1.00  (2026-01-31)          : Initial version
     • Single-class sports-ball detection via Ultralytics YOLO.
===============================================================================
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np


@dataclass
class YOLOBox:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    cls: int
    label: str = ""

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0


class YOLOBallDetector:
    def __init__(
        self,
        *,
        model_path: Optional[str] = None,
        ball_class_id: int = 32,
        conf: float = 0.02,     # default is 0.1 (10%) in Ultralytics YOLO model yolov8n.pt. lower to catch small balls
        imgsz: int = 640,    # default 640 in Ultralytics YOLO, can be 320, 640, 1280, etc. smaller=faster but less accurate
    ):
        self.model_path = model_path or os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        self.ball_class_id = int(ball_class_id)
        self.conf = float(conf)
        self.imgsz = int(imgsz)

        self.last_error: Optional[str] = None
        self.last_latency_s: Optional[float] = None
        self.last_probe_error: Optional[str] = None
        self.last_probe_latency_s: Optional[float] = None
        self.last_probe_boxes: List[YOLOBox] = []
        self._model: Any = None
        self._names: dict[int, str] | None = None

    def _load(self) -> bool:
        if self._model is not None:
            return True
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as e:
            self.last_error = f"ultralytics not installed: {e}"
            return False
        try:
            self._model = YOLO(self.model_path)
            self._names = getattr(self._model, "names", None)
            return True
        except Exception as e:
            self.last_error = f"YOLO load failed: {e}"
            self._model = None
            return False

    def analyze_classes(
        self,
        frame_bgr: np.ndarray,
        *,
        classes: Optional[Sequence[int]] = None,
        conf: Optional[float] = None,
        max_det: int = 30,
    ) -> List[YOLOBox]:
        """Return YOLO bounding boxes (pixel coords) for specified classes.

        - If classes is None: returns all detections.
        - If classes is provided: YOLO will filter to those class IDs.
        """
        t0 = time.time()
        self.last_error = None
        self.last_latency_s = None

        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            self.last_error = "empty frame"
            return []
        if not self._load():
            return []

        try:
            kwargs = {
                "source": frame_bgr,
                "conf": float(self.conf if conf is None else conf),
                "imgsz": self.imgsz,
                "max_det": int(max_det),
                "verbose": False,
            }
            if classes is not None:
                kwargs["classes"] = [int(c) for c in classes]
            results = self._model.predict(**kwargs)
        except Exception as e:
            self.last_error = f"YOLO predict failed: {e}"
            return []

        boxes: List[YOLOBox] = []
        try:
            r0 = results[0]
            b = getattr(r0, "boxes", None)
            if b is None:
                self.last_error = "no boxes returned"
                return []

            xyxy = getattr(b, "xyxy", None)
            confs = getattr(b, "conf", None)
            clss = getattr(b, "cls", None)
            if xyxy is None or confs is None or clss is None:
                self.last_error = "unexpected YOLO boxes format"
                return []

            xyxy_np = xyxy.detach().cpu().numpy() if hasattr(xyxy, "detach") else np.asarray(xyxy)
            conf_np = confs.detach().cpu().numpy() if hasattr(confs, "detach") else np.asarray(confs)
            cls_np = clss.detach().cpu().numpy() if hasattr(clss, "detach") else np.asarray(clss)

            for (x1, y1, x2, y2), cf, ci in zip(xyxy_np, conf_np, cls_np):
                try:
                    ci_i = int(round(float(ci)))
                except Exception:
                    ci_i = -1
                label = f"cls{ci_i}"
                try:
                    if self._names and ci_i in self._names:
                        label = str(self._names[ci_i])
                except Exception:
                    pass
                boxes.append(
                    YOLOBox(
                        x1=float(x1),
                        y1=float(y1),
                        x2=float(x2),
                        y2=float(y2),
                        conf=float(cf),
                        cls=ci_i,
                        label=label,
                    )
                )
        except Exception as e:
            self.last_error = f"YOLO parse failed: {e}"
            return []
        finally:
            self.last_latency_s = time.time() - t0

        boxes.sort(key=lambda bb: bb.conf, reverse=True)
        return boxes

    def analyze(self, frame_bgr: np.ndarray) -> List[YOLOBox]:
        """Return YOLO bounding boxes for sports-ball class in pixel coords."""
        boxes = self.analyze_classes(
            frame_bgr,
            classes=[self.ball_class_id],
            conf=self.conf,
            max_det=10,
        )
        # Ensure strict behavior: keep only the requested ball class.
        try:
            boxes = [b for b in boxes if int(getattr(b, "cls", -1) or -1) == int(self.ball_class_id)]
        except Exception:
            pass
        return boxes

    def probe(self, frame_bgr: np.ndarray, *, conf: float = 0.001, max_det: int = 10) -> List[YOLOBox]:
        """Debug helper: run YOLO without class filter at lower conf."""
        t0 = time.time()
        self.last_probe_error = None
        self.last_probe_latency_s = None
        self.last_probe_boxes = []

        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            self.last_probe_error = "empty frame"
            return []
        if not self._load():
            self.last_probe_error = self.last_error
            return []

        try:
            results = self._model.predict(
                source=frame_bgr,
                conf=float(conf),
                imgsz=self.imgsz,
                max_det=int(max_det),
                verbose=False,
            )
        except Exception as e:
            self.last_probe_error = f"YOLO probe failed: {e}"
            return []

        boxes: List[YOLOBox] = []
        try:
            r0 = results[0]
            b = getattr(r0, "boxes", None)
            if b is None:
                self.last_probe_error = "no boxes returned"
                return []

            xyxy = getattr(b, "xyxy", None)
            confs = getattr(b, "conf", None)
            clss = getattr(b, "cls", None)
            if xyxy is None or confs is None or clss is None:
                self.last_probe_error = "unexpected YOLO boxes format"
                return []

            xyxy_np = xyxy.detach().cpu().numpy() if hasattr(xyxy, "detach") else np.asarray(xyxy)
            conf_np = confs.detach().cpu().numpy() if hasattr(confs, "detach") else np.asarray(confs)
            cls_np = clss.detach().cpu().numpy() if hasattr(clss, "detach") else np.asarray(clss)

            for (x1, y1, x2, y2), cf, ci in zip(xyxy_np, conf_np, cls_np):
                try:
                    ci_i = int(round(float(ci)))
                except Exception:
                    ci_i = -1
                label = f"cls{ci_i}"
                try:
                    if self._names and ci_i in self._names:
                        label = str(self._names[ci_i])
                except Exception:
                    pass
                boxes.append(
                    YOLOBox(
                        x1=float(x1),
                        y1=float(y1),
                        x2=float(x2),
                        y2=float(y2),
                        conf=float(cf),
                        cls=ci_i,
                        label=label,
                    )
                )
        except Exception as e:
            self.last_probe_error = f"YOLO probe parse failed: {e}"
            return []
        finally:
            self.last_probe_latency_s = time.time() - t0

        boxes.sort(key=lambda bb: bb.conf, reverse=True)
        self.last_probe_boxes = boxes
        return boxes
