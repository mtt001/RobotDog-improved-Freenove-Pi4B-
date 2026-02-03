# Freenove Robot Dog – Hybrid Vision Architecture  
## YOLO (Semantic Detection) + OpenCV (Geometric Refinement)

Author: Mengta  
Context: Freenove Robot Dog (Raspberry Pi + Mac Client)  
Status: Design Baseline (v1.0)

---

## 1. Problem Statement

The robot dog must evolve from **single-object tracking (ball only)** to **multi-object perception**, including:

- Ball (play / chase)
- Human foot (avoid / yield)
- Dog (follow / ignore / react differently)

Key constraints:

- Camera is floor-level
- Scene contains strong reflections (wood floor)
- Control requires precise geometry, not just detection
- Raspberry Pi requires deterministic, low-latency control
- Mac client can handle heavier AI inference

---

## 2. Core Insight (Design Principle)

Semantic understanding and geometric precision are different problems.

- AI (YOLO / CNN) answers: *what is it?*
- OpenCV + geometry answers: *where exactly is it?*
- Behavior logic answers: *what should I do?*

A hybrid architecture is mandatory.

---

## 3. High-Level Architecture

Camera Frame  
→ YOLO / CNN (Semantic Detection)  
→ ROI Extraction  
→ Object-Specific OpenCV Refinement  
→ True Physical Position  
→ Behavior State Machine  
→ Servo / Gait Control

---

## 4. Perception Layer – YOLO

Purpose: Identify object class.

Output:
- class: ball | foot | dog
- bbox: (x1, y1, x2, y2)
- confidence: 0.0–1.0

YOLO provides semantics, not geometry.

---

## 5. Geometry Layer – OpenCV (Ball Example)

Key facts:
- Ball is spherical
- Ball touches the floor
- Lower hemisphere is contaminated by reflection

### Refinement Steps

1. Adaptive HSV learning inside ROI  
2. Reflection suppression (lower ROI rejection)  
3. Upper-hemisphere extraction  
4. Edge-based ellipse / circle fitting  
5. Floor-contact correction:  
   y_center = y_floor_contact - radius

This yields the true physical center.

---

## 6. Why YOLO Alone Is Insufficient

YOLO predicts human-labeled bounding boxes.
It does not model:
- floor plane
- contact physics
- reflections
- camera height

YOLO must be followed by geometry.

---

## 7. Behavior Layer

Vision does not decide behavior.

Example mapping:

Ball (far) → chase  
Ball (near) → slow / stop  
Foot → avoid  
Dog → follow / observe  
Nothing → explore

---

## 8. System Split

Mac Client:
- YOLO inference
- multi-object tracking
- behavior planning
- debugging

Raspberry Pi:
- servo control
- IMU fusion
- safety limits
- reflexes

---

## 9. Roadmap

Phase 1:
- YOLO + ROI + OpenCV ball refinement
- confidence scoring

Phase 2:
- foot detection
- dog detection

Phase 3:
- temporal memory
- behavior personality tuning

---

## 10. Final Truth

AI explains the world.  
Geometry grounds the world.  
State machines control behavior.

This hybrid approach is the correct long-term solution.