# Freenove Robot Dog – Hybrid Vision Architecture
## YOLO (Semantic Detection) + OpenCV (Geometric Refinement)

Author: Mengta  
Context: Freenove Robot Dog (Raspberry Pi + Mac Client)  
Status: Design Baseline (v1.2 – CV Geometry Enhanced)

---

## 1. Problem Statement

The robot dog must evolve from **single-object color-based tracking** to a **robust, future-proof perception stack** that supports:

- Ball (various colors, materials)
- Human foot (avoid / yield)
- Dog (follow / react)

Key constraints:

- Camera is floor-level (strong perspective distortion)
- Wood floor & furniture cause specular reflections
- Color alone is unreliable long-term
- Control requires **precise geometry**, not just detection
- Mac client can run AI; Raspberry Pi must stay deterministic

---

## 2. Core Design Principle

> **Separate semantics from geometry.**

- **AI (YOLO / CNN)** answers: *What is this object?*
- **OpenCV + geometry** answers: *Where exactly is it in physical space?*
- **Behavior logic** answers: *What should the robot do?*

This separation allows each layer to evolve independently.

---

## 3. End-to-End Processing Chain (Ball Example)

```text
Camera Frame (400×300)
   ↓
YOLO Object Detection
   - class = ball
   - bbox = (x1,y1,x2,y2)
   - confidence
   ↓
ROI Extraction (with margin)
   ↓
OpenCV Refinement Pipeline
   1. Adaptive color hint (HSV / Lab) from ROI
   2. Mask generation & cleanup
   3. Contour candidates
   4. Geometric scoring
   5. Radial edge symmetry test
   6. Optional Hough refinement
   ↓
Final Ball Geometry
   - center (cx,cy)
   - radius r
   - confidence score
   ↓
Behavior State Machine
   ↓
Servo / Gait Control
```

---

## 4. YOLO Layer – Semantic Detection

Purpose: **Confirm object identity and restrict search space**.

YOLO outputs:
- `class`: ball | foot | dog
- `bbox`: pixel rectangle
- `confidence`

Important notes:
- YOLO does **not** provide accurate geometry
- Bounding boxes are human-labeled, not physics-aware
- YOLO eliminates most false positives (e.g., furniture)

YOLO is therefore the *gatekeeper*, not the final authority.

---

## 5. OpenCV Layer – Geometric Refinement (Ball)

### 5.1 Input from YOLO

- ROI rectangle
- Expected object class = ball
- Optional color hint (HSV / Lab percentile ranges)

Color is treated as a **soft prior**, not a hard assumption.

---

### 5.2 CV Refinement Pipeline (Detailed)

1. **Adaptive Color Mask (Optional)**
   - HSV or Lab thresholds learned *inside ROI*
   - Used to suppress background, not decide class

2. **Mask Cleanup**
   - Median blur
   - Morphological open / close

3. **Contour Candidate Extraction**
   - Area gating (min / max area ratio)
   - Radius bounds (distance-aware)

4. **Basic Shape Metrics**
   - Circularity
   - Fill ratio

5. **Radial Edge Symmetry Test**
   - Geometry-only validation
   - Color-independent

6. **Optional Hough Circle Refinement**
   - Local ROI only
   - Used for sub-pixel stability

7. **Final Scoring & Acceptance**

---

## 6. Radial Edge Symmetry Test

### 6.1 Motivation

A real ball exhibits:
- Circular boundary
- Image gradients pointing **radially outward** from center

Wood, furniture, and reflections may be round-ish, but:
- Edge gradients are directional or linear
- Radial alignment is weak

---

### 6.2 Algorithm Overview

For a candidate circle `(cx, cy, r)`:

1. Convert ROI to grayscale
2. Compute:
   - Canny edges
   - Sobel gradients (gx, gy)
3. Evaluate pixels in a **ring** around the circle:
   - inner radius = `0.85 × r`
   - outer radius = `1.15 × r`

For each edge pixel `(x,y)`:

- Radial vector: `R = (x−cx, y−cy)`
- Gradient vector: `G = (gx, gy)`
- Compute normalized dot product:

```
cosθ = (G · R) / (|G||R|)
```

- If `cosθ > 0.7`, the edge supports a spherical boundary

---

### 6.3 Radial Symmetry Score

```
radial_score = aligned_edges / total_ring_edges
coverage     = total_ring_edges / (2πr)
```

Recommended thresholds:
- `coverage ≥ 0.15`
- `radial_score ≥ 0.55`

---

## 7. Visualization Overlay

Recommended debug overlays:

- Evaluation ring (0.85r–1.15r)
- Short arrows at sampled edge pixels
  - Green: aligned gradients
  - Red: misaligned gradients
- HUD text:
```
radial: 0.68
coverage: 0.21
edges: 134
```

---

## 8. Scoring Integration

Radial symmetry influences final confidence:

```
final_score = base_score × (0.5 + 0.5 × radial_score)
```

Where:
- `base_score` = area × circularity × fill

---

## 9. Why CV-Only Mode Still Matters

- Enables fast iteration and debugging
- Provides fallback when AI confidence is low
- Geometry improvements apply unchanged

---

## 10. Final Takeaway

- YOLO answers *what*
- Radial symmetry answers *is it physically a ball*
- Geometry answers *where exactly*

This hybrid design is the correct long-term perception foundation.

