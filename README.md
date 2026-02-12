# Freenove Robot Dog - Code Overview

## Version
v1.0.0 (2026-02-11 17:32 local time)

This folder contains all operational code for the Freenove Robot Dog.

| Subfolder | Platform | Description |
|-----------|----------|-------------|
| [`Client/`](Client/) | macOS / Desktop | PyQt GUI for control, video, and YOLO vision runtime. |
| [`Server/`](Server/) | Raspberry Pi | Camera streaming, servo control, telemetry, and web runtime services. |

## Quick Start
1. On Pi:
```bash
cd Server
python3 main.py -tn
```
2. On Mac client:
```bash
cd Client
python3 mtDogMain.py
```

## YOLO Vision Method (`mtDogMain.py`)
Current `mtDogMain.py` uses a dual-model YOLO pipeline managed by `Client/vision/yolo_runtime.py`.

- `best.pt` (custom mt_ball model):
  - Path: `Client/runs/detect/train5/weights/best.pt`
  - Detector role: dedicated custom ball detector (`class_id=0` in this model).
  - Runtime name in status/debug: `MT (best.pt)`.
- `yolov8n.pt` (baseline COCO model):
  - Path: `Client/yolov8n.pt`
  - Detector role: general-object detector, with key classes used by runtime targeting:
    - `cls=32` sports ball
    - `cls=16` dog
    - `cls=0` person
  - Runtime name in status/debug: `Yolo (yolov8n.pt)`.

How both models are used right now:
- Both detectors run per inference cycle (FPS-capped by `YOLO_DUAL_CAP_FPS_DEFAULT`).
- Results are merged into a shared candidate list for target selection.
- Priority logic is ball-first (`mt_ball` or `sports ball`), then `dog`, then `person`.
- A compare mode shows side-by-side outputs: `best.pt` (left) vs `yolov8n.pt` sports-ball detections (right).
- Runtime status text reports per-model latency, counts, selected target, and refine-mask HSV summary.

## Notes
- The `Client/` folder is the active working area for enhanced development.
- `Client(Original)/` (if present in your full repo) keeps original Freenove baseline references.

## Revision History
- 2026-02-11 17:32 v1.0.0  Rewrote top-level README and added dual-model YOLO Vision method documentation for current `mtDogMain.py` runtime.
