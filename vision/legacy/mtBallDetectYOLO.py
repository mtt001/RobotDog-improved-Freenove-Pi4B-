#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mtBallDetectYOLO.py

Optional YOLO-based ball detection (local inference).

- Uses Ultralytics YOLO if installed.
- Targets COCO class "sports ball" (id=32) by default.

This module is intentionally optional: if dependencies or weights are missing,
`YOLOBallDetector.analyze()` returns [] and sets `last_error`.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

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

    def analyze(self, frame_bgr: np.ndarray) -> List[YOLOBox]:
        """Return YOLO bounding boxes for sports-ball class in pixel coords."""
        t0 = time.time()
        self.last_error = None
        self.last_latency_s = None

        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            self.last_error = "empty frame"
            return []
        if not self._load():
            return []

        try:
            # Ultralytics expects BGR ndarray OK.
            results = self._model.predict(
                source=frame_bgr,
                conf=self.conf,
                imgsz=self.imgsz,
                classes=[self.ball_class_id],
                max_det=10,
                verbose=False,
            )
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
                if ci_i != self.ball_class_id:
                    continue
                label = "sports ball"
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

        # Sort by confidence desc
        boxes.sort(key=lambda bb: bb.conf, reverse=True)
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
