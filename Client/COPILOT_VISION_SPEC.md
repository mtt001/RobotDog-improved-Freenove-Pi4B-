# Dual-YOLO Vision & Default Object Tracking Specification
(Project reminder for Copilot / Codex Agent)

## 1. Overall Goal
Implement a real-time vision pipeline for a robot dog that:
- Preserves full COCO multi-class detection
- Adds a higher-quality custom ball detector
- Tracks ONE dominant object (ball / dog / person) stably
- Measures detection performance (ms + FPS)
- Keeps perception logic independent from robot behavior

No behavior logic (motion, gait, control) is included here.

---

## 2. YOLO Models (ALWAYS ON)

### Model A — COCO
- Model: `yolov8n.pt`
- Purpose: scene understanding
- Default classes of interest:
  - `person` (id=0)
  - `dog` (id=16)
  - `sports ball` (id=32)
- Default confidence threshold: `0.1`

### Model B — Custom Ball
- Model: `best.pt`
- Purpose: precise ball detection
- Classes:
  - `mt_ball` (single class only)
- Default confidence threshold: `0.1`

Both models MUST:
- Run on the same input frame
- Be executed every inference cycle (unless inference FPS is capped)

---

## 3. Detection Pipeline

Per inference frame:
1. Run COCO YOLO
2. Run custom Ball YOLO
3. Collect all detections
4. Select ONE active target (see Section 4)
5. Apply refinement ONLY if target is a ball
6. Output target metadata for downstream use

---

## 4. Target Selection Policy (Default Mode)

### Candidate classes
- `mt_ball`
- COCO `sports ball`
- COCO `dog`
- COCO `person`

### Selection rule
- Choose the detection with the **highest confidence across both models**

### Temporal Stability (MANDATORY)
To prevent jitter:
- Once a target is selected, keep it for at least:
  - `stickiness_frames = 15`
- Switch target ONLY if:
  - Current target disappears, OR
  - New candidate confidence ≥ (current_confidence + 0.15)

Output fields:
- `target_class`
- `target_bbox`
- `target_confidence`
- `target_source_model` (COCO / MT)

---

## 5. Ball-Specific Refinement (STRICTLY ISOLATED)

### Apply refinement ONLY to:
- `mt_ball`
- COCO `sports ball`

### Refinement steps:
- Extract ROI from bounding box
- Compute HSV histogram from ROI pixels ONLY
- Derive HSV thresholds automatically:
  - Lower bound = 5th percentile
  - Upper bound = 95th percentile
- Generate mask from derived thresholds
- (Optional later) circle fitting / center refinement

### DO NOT apply:
- HSV
- Histogram
- Mask
to non-ball classes (`dog`, `person`, etc.)

---

## 6. Visualization Rules

- Draw bounding boxes:
  - COCO → thin lines
  - `mt_ball` → thicker, high-contrast lines
- Compact labels near boxes:
  - Example:
    - `mt_ball 0.93`
    - `Sport_Ball 0.65`
    - `Dog 0.45`

### System status text
- MUST be displayed in a **bottom message pane widget**
- MUST NOT be painted onto the video frame

---

## 7. Performance Measurement (REQUIRED)

Use `time.perf_counter()` to measure:
- COCO inference time (ms)
- Ball inference time (ms)
- Total pipeline time (ms)

Compute FPS:
