# AI_YOLO_Datasets.md
Author: MT  
Project: Freenove Robot Dog – YOLO + CV Hybrid Vision  
Last Updated: 2026-01-29

---

## 0. Purpose

This document defines the **authoritative rules** for designing, collecting, labeling,
storing, and curating YOLO datasets for the Freenove Robot Dog project.

It is written for:
- Human readers (future MT, collaborators)
- VS Code Copilot / GPT-5.2-Codex (code generation guidance)

If any code, script, or comment conflicts with this document,  
**this document takes precedence.**

---

## 1. Core Concepts & Terminology

### 1.1 Label (YOLO Ground Truth)

A YOLO label represents **ground truth object existence**.
Once written, it is assumed to be **100% correct**.

YOLO label format is **strict and unchangeable**:

```
<class_id> <cx> <cy> <w> <h>
```

- All values are normalized (0.0–1.0)
- One object per line (single-ball case = one line)
- No extra fields allowed

❗ **Confidence must NEVER be written into YOLO label files.**

---

### 1.2 Confidence

Confidence is a **property of a detector**, not of the object itself.

- Confidence is used for dataset analysis and curation
- Confidence is NOT ground truth
- Confidence must be stored as **metadata only**

---

### 1.3 Dataset

A dataset is a structured collection of:
- images
- YOLO label files
- metadata (confidence, difficulty, conditions)

Datasets are versioned and immutable once used for training.

---

## 2. Dataset Root Folder Rules

All AI datasets must live under:

```
Client/AI_datasets/
```

Naming rules:
- lowercase preferred
- underscores allowed
- no spaces
- versioned from day one

Example:
```
Client/AI_datasets/yolo_ball_v1/
```

---

## 3. Mandatory Dataset Folder Structure

Each dataset must follow **exactly** this structure:

```
AI_datasets/
 └── yolo_ball_v01/
      ├── images/
      │    ├── img000001.jpg
      │    ├── img000002.jpg
      │    └── ...
      ├── labels/
      │    ├── img000001.txt
      │    ├── img000002.txt
      │    └── ...
      ├── meta/
      │    ├── img000001.meta.json
      │    ├── img000002.meta.json
      │    └── ...
      ├── dataset.yaml
      └── README.md
```

Rules:
- Every image MUST have a matching label file
- Filenames must match exactly (except extension)
- Metadata files are optional but strongly recommended
- No images without labels are allowed

---

## 4. Image Naming Rules

Image filenames:

```
img000001.jpg
img000002.jpg
```

Rules:
- monotonic increasing index
- zero-padded
- no timestamps in filenames

Reason:
- easier debugging
- stable dataset ordering
- easier sampling and auditing

---

## 5. YOLO Label File Rules (CRITICAL)

Example label file:

```
img000001.txt
```

Content:
```
0 0.512341 0.684212 0.146233 0.195112
```

Rules:
- exactly 5 numeric values per line
- no comments
- no confidence values
- no additional columns

❗ Any deviation will break YOLO training.

---

## 6. Metadata Files (Confidence & Difficulty)

Metadata files store **non-ground-truth information** such as confidence,
difficulty, and environmental conditions.

Location:
```
AI_datasets/yolo_ball_v1/meta/
```

Filename:
```
img000001.meta.json
```

### 6.1 Metadata Example

```json
{
  "label_source": "yolo_low_conf",
  "yolo_confidence": 0.07,
  "difficulty": "hard",
  "lighting": "low",
  "view_angle": "low",
  "floor": "dark_wood_reflective",
  "notes": "strong reflection, low saturation"
}
```

### 6.2 Mandatory Metadata Fields

- `label_source` : `"cv_clean" | "yolo_low_conf" | "manual"`
- `difficulty`  : `"easy" | "medium" | "hard"`

### 6.3 Optional (Recommended) Fields

- `yolo_confidence`
- `lighting`
- `view_angle`
- `floor`
- `notes`

❗ Metadata is NEVER read by YOLO.
It is used only for dataset curation and analysis.

---

## 7. Difficulty Definition & Target Distribution

Difficulty describes **how hard detection is**, not correctness.

### 7.1 Difficulty Categories

| Difficulty | Definition |
|-----------|------------|
| Easy | Clear lighting, high contrast, canonical view |
| Medium | Partial reflection, angle distortion |
| Hard | Low light, strong reflection, low contrast, unusual colors |

### 7.2 Target Dataset Distribution

| Category | Target Ratio |
|--------|--------------|
| Easy | 30% |
| Medium | 40% |
| Hard | 30% |

This distribution is enforced **during dataset selection**, not by YOLO itself.

---

## 8. Using YOLO as a Weak Auto-Label Generator (Approved)

The pretrained YOLO model (COCO) may be used as a **proposal generator**.

### 8.1 Confidence Range for Harvesting

Default (recommended) for weak-label harvesting:

```
0.01 ≤ confidence ≤ 0.99
```

However, **Ball Training capture may choose to disable this restriction**
to allow **all confidence values** for broader dataset coverage.
Low confidence samples are still considered **hard examples**.

---

## 9. Mandatory Filters for YOLO-Based Auto-Labeling

Confidence alone is NOT sufficient.

All YOLO-proposed labels must satisfy **ALL** filters below.

---

### 9.1 Bounding Box Sanity Filter

Reject detection if:
- width < 12 pixels
- height < 12 pixels
- aspect ratio > 1.6
- bounding box area > 40% of image area

---

### 9.2 Temporal Stability Filter (CRITICAL)

Accept detection only if:
- similar bounding box appears in ≥ 3 consecutive frames
- IoU between frames ≥ 0.5

This removes most false positives and reflections.

---

### 9.3 Optional Shape Consistency Check (Recommended)

Inside YOLO bounding box:
- apply circularity check via contour or Hough
- no color thresholding required

Purpose:
- reject highlights and reflections
- confirm ball-like geometry

---

## 10. Dataset Composition Rules

❌ Do NOT create datasets consisting only of worst-case samples.

Recommended mix:
- 30% Easy
- 40% Medium
- 30% Hard

Worst-case-only datasets cause:
- overfitting
- hallucination
- poor generalization

---

## 11. dataset.yaml Template (YOLO)

File:
```
AI_datasets/yolo_ball_v1/dataset.yaml
```

Content:
```yaml
path: .
train: images
val: images

nc: 1
names: [ball]
```

Paths are resolved relative to this file.

---

## 12. Rules for VS Code Copilot / GPT-5.2-Codex

### DO
- Save images under `AI_datasets/yolo_ball_v1/images/`
- Save labels in standard YOLO format under `labels/`
- Save confidence and difficulty in `.meta.json` under `meta/`
- Enforce all filters in Sections 8–9

### DO NOT
- Modify YOLO label format
- Store confidence inside `.txt` label files
- Save unstable or single-frame detections
- Save images without labels

---

## 13. Canonical Copilot-Ready Instruction

Use the following instruction verbatim when generating code:

> Implement YOLO-based auto-labeling according to AI_YOLO_Datasets.md.  
> Save images under AI_datasets/yolo_ball_v1/images/.  
> Save YOLO labels in standard YOLO format under labels/.  
> Store detection confidence and difficulty in a separate .meta.json file under meta/.  
> Only save detections that pass bounding-box sanity checks and temporal stability (≥3 frames, IoU ≥0.5).  
> Do NOT modify the YOLO label format.

---

## 14. Design Philosophy

- YOLO is used for **exploration**
- Geometry and temporal logic provide **sanity**
- Metadata provides **control**
- Distribution prevents bias
- Versioning prevents regression

This design scales from experimentation to production robotics.

---

## 15. Implementation (by VS Code Copilot Agent, GPT-5.2-Codex)

This section records the agreed implementation plan for **Ball-class (class_id=0)**
auto-labeling using **Yolo Vision** in the client UI.

### 15.1 Entry Point and UI (Yolo Vision Debug Window)

- Add a toggle button labeled **"Ball Trainning"** inside the Yolo Vision debug window.
- When ON, the system enters **YOLO Training (Ball class) capture mode**.
- When OFF, **all capture and labeling stop immediately**.

### 15.2 Overlay in Main Color Window

- While capture is active, overlay a visible status line on the main Color window:
  - `YOLO datasets creating...  #78/1000`
  - Include current dataset version (e.g., `yolo_ball_v02`) in the overlay.
- Overlay updates in real time and disappears when capture stops or completes.

### 15.3 Capture Target and Control

- Capture **1000 labeled images** per session.
- Each **saved sample must include**:
  - image file (`images/`)
  - label file (`labels/`)
  - meta file (`meta/`)
- If YOLO returns **no valid detection**, nothing is saved and the counter does not increment.
- If the user toggles OFF before reaching 1000, capture stops with a partial dataset.

### 15.4 Labeling Rules (Ground Truth)

- Use the **highest-confidence YOLO box** as the label for that image.
- Write label in strict YOLO format **without confidence**:

```
0 <cx> <cy> <w> <h>
```

### 15.5 Metadata Rules (Confidence and Difficulty)

- Store confidence in a `.meta.json` file:
  - `yolo_confidence`
  - `label_source` (e.g., `"yolo_low_conf"`)
  - `difficulty` (required by this document; default `"medium"` unless specified)
- Confidence **must never** be written into the YOLO label file.

### 15.6 Dataset Versioning (Required)

- Dataset root is always `Client/AI_datasets/`.
- Dataset folder naming uses **two-digit versioning**:
  - `yolo_ball_v01`, `yolo_ball_v02`, ... `yolo_ball_v99`
- When the next version reaches `v99`, **wrap to v01** and continue incrementing.
- Each dataset folder must include:
  - `images/`, `labels/`, `meta/`, `dataset.yaml`, `README.md`

### 15.7 Confidence Distribution Window (Live)

- When capture mode is active, open a small window that shows **confidence distribution**.
- Distribution range: **0.01 → 1.00**.
- Histogram updates as new samples are captured.
- Show **current percentage** per difficulty (Easy/Medium/Hard) alongside the **target mix** (30/40/30).
- Update the display **in real time** during training (every capture tick).

### 15.8 Capture Cadence (Fast Mode)

- While **Ball Trainning** is active, YOLO detection updates should be faster:
  - Prefer **0.25s** per tick.
  - If YOLO inference is slower, clamp to `max(0.25s, last_latency * 1.2)`.
- This keeps UI updates real-time without queue backlog.

### 15.9 Filters (Must Follow Sections 8–9)

- Only save detections that pass:
  - Bounding box sanity checks
  - Temporal stability (≥3 consecutive frames, IoU ≥ 0.5)
- Optional circularity check can be added for extra filtering.

### 15.10 Distribution Targeting (30/40/30)

- Enforce dataset composition during capture:
  - Easy 30%, Medium 40%, Hard 30%.
- Use **bucket quotas** and prioritize saving samples from the most underfilled bucket.
- Difficulty can be tagged by:
  - quick UI tag, or
  - heuristic from confidence/lighting conditions (documented in meta).

### 15.11 User Guidance Overlay

- During capture, show a short rotating prompt in the main Color window to encourage variation:
  - ball near edges / corners
  - different distance / scale
  - bright vs low light
  - reflective floors / cluttered backgrounds
  - partial occlusions / motion blur

### 15.12 Behavior Summary

- **Ball Trainning ON** → start capture, overlay status, count to 1000, update confidence histogram.
- **Ball Trainning OFF** → stop capture immediately, keep dataset intact.
- Full compliance with Sections **8–12** of this document is mandatory.

---

End of document.

========================================
### What you now have

- ✅ One **single, self-contained `.md`**
- ✅ Folder name and document name aligned
- ✅ Safe for YOLO training
- ✅ Explicit enough for Copilot
- ✅ Future-proof for multiple datasets

When you’re ready later, the **natural next step** is to say something like:

> “Generate Copilot code to implement Sections 8–9 of AI_YOLO_Datasets.md inside `mtDogMain.py`.”

and we’ll move forward cleanly, without re-explaining foundations.
::contentReference[oaicite:0]{index=0}


## =======================================
The natural follow-ups (later) are:

How to evaluate v01 objectively (metrics that matter)

How to decide what samples to add for v02

How to prevent self-reinforcing YOLO bias

How to integrate YOLO + CV confidence cleanly

## =======================================
Next steps:

Here’s the minimal training flow for v01:

1. Split v01 into train/val folders (images and labels must mirror). Recommended structure: images/train, images/val, labels/train, labels/val under AI_datasets/yolo_ball_v01/.
2. Update dataset.yaml to point to the split folders (train: images/train, val: images/val).
3. Train Ultralytics YOLO using the venv and the v01 dataset.yaml. Example command (inline): ~/.venvs/freenove-client/bin/python -m ultralytics yolo train model=yolov8n.pt dataset.yaml imgsz=640 epochs=100 batch=16.
4. Evaluate mAP/precision/recall and iterate (add more hard samples if needed).

## =======================================
Training Status (2026-01-29)

Completed:
- v01 split into train/val and flat files removed. Counts: train=1005, val=251.
- dataset.yaml updated to point to images/train and images/val (absolute dataset path for Ultralytics).
- YOLO training started from yolov8n.pt. Outputs are under runs/detect/train4/ (best.pt, last.pt, results.csv).
- Training params used: imgsz=640, epochs=100, batch=16, model=yolov8n.pt, data=AI_datasets/yolo_ball_v01/dataset.yaml.

Next step:
- Monitor runs/detect/train4/results.csv until training finishes, then select runs/detect/train4/weights/best.pt for inference.
- (Optional) export best.pt to ONNX/CoreML if needed for deployment.



## =======================================

Beginner Guide: What YOLO Training Does (100 Epochs)

Think of an “epoch” as one full pass through all training images. With 100 epochs, YOLO will:
- Repeatedly see your train images and adjust its internal weights to better fit the ball boxes.
- Measure performance on the validation set after each epoch.
- Track and save the best-performing weights so far.

At each epoch, YOLO records metrics like:
- Precision: how often predicted boxes are correct.
- Recall: how many real balls it finds.
- mAP50 and mAP50-95: overall quality of detection (higher is better).

Output Files You Need (for Deployment)

In runs/detect/train4/weights/ you will see:
- best.pt: the best model across all epochs (this is the one to deploy).
- last.pt: the model from the final epoch.

Additional logs in runs/detect/train4/:
- results.csv: per-epoch metrics (use this to evaluate training progress).
- args.yaml: the exact training settings used.
- labels.jpg and train_batch*.jpg: dataset sanity checks.

How to Evaluate the Trained Model (Beginner Flow)

1. Open results.csv and look at the last few lines.
  - If mAP50 and mAP50-95 are stable and high, training is working well.
2. If mAP is low, collect more “hard” images and retrain (this is normal).
3. If precision is high but recall is low, the model is too conservative (add varied samples).

How to Deploy the Model (Beginner Flow)

1. Use runs/detect/train4/weights/best.pt as your deployment model.
2. In the client app, point the YOLO detector to best.pt.
  - If you are using mtBallDetectYOLO.py, update it to load best.pt instead of yolov8n.pt.
3. Test on live camera feed and confirm detection quality.

Optional formats:
- Export best.pt to ONNX/CoreML if you need faster or portable inference.

Final Step: Use the Trained Result

Once training is complete and you confirm the model works:
1. Replace the default yolov8n.pt with best.pt in your detection pipeline.
2. Run the client and verify ball detection in real scenarios.
3. If detection is unstable, collect new samples and start v02.

Summary (Simple Flow)

Collect data → Train (100 epochs) → Evaluate results.csv → Use best.pt → Test in real world → Improve with v02

## =======================================
Important Note: MacBook Pro M5 Training Setup (Speed)

To fully use Apple GPU, run YOLO with Metal (MPS):
- Use device=mps (otherwise it will fall back to CPU).
- Recommended speed settings on macOS:
  - imgsz=512 (or 416 for faster runs)
  - batch=32 (reduce if you hit memory issues)
  - cache=True (loads images into memory for faster epochs)
  - workers=0 (macOS often works best with 0 or 2 workers)

Example command (MPS):
- yolo train model=yolov8n.pt data=AI_datasets/yolo_ball_v01/dataset.yaml imgsz=512 epochs=100 batch=32 device=mps cache=True workers=0

Expected behavior:
- MPS should show “MPS (Apple M5)” at startup.
- If it shows CPU, you are not using GPU acceleration.