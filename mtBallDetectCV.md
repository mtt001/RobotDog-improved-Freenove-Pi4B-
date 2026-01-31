# mtBallDetectCV — CV Ball Detection (Lab a + HSV)

## Overview
mtBallDetectCV provides a fast, non‑ML ball detector focused on orange/red balls. It is designed to be robust on reflective surfaces and to generate rich debug visuals for calibration and analysis. The detector returns a single best circle with a confidence‑oriented rejection path and a conservative fallback for reflection cases.

## Key Goals
- Reliable baseline without ML dependencies.
- Stable ROI for downstream tracking and UI overlays.
- Debug visibility into thresholds, masks, contour scoring, and refinement.
- Strong false‑positive suppression with post‑checks.

## Data Model
A detected ball is represented by CVBall:
- x, y: circle center in image coordinates.
- r: radius in pixels.
- area: contour area.
- circularity: contour circularity.

## Processing Pipeline (Step‑by‑Step)

### 1) Pre‑Checks
- If the input frame is empty, the detector returns no detection.

### 2) Color Gating (Lab a + HSV H/S/V)
1. Convert BGR → Lab and extract the a channel (redness).
2. Compute a dynamic a‑threshold:
   - a_thr = max(a_min, percentile(a, a_percentile))
3. Create mask_lab = a ≥ a_thr.

4. Convert BGR → HSV and extract H, S, V.
5. Create mask_sv = (S ≥ s_min) AND (V ≥ v_min).
6. Create mask_h = red/orange hue gates (with wrap‑around red range).
7. Combine masks: mask = mask_lab AND mask_h.

### 3) Mask Cleanup
- median blur (5)
- morphological open (9×9 ellipse, 1 iteration)

### 4) Contour Extraction
- Find external contours on the cleaned combined mask.

### 5) Candidate Gating + Scoring
For each contour:
- Reject if area is too small or too large (area ratio against image area).
- Compute circularity:
  $$\text{circularity} = \frac{4\pi A}{P^2}$$
- Compute enclosing circle and radius bounds.
- Compute fill ratio:
  $$\text{fill} = \frac{A}{\pi r^2}$$

Two‑stage gating is used:
- Loose gate: very low thresholds to keep reflection‑distorted shapes.
- Strict gate: higher thresholds for confident contours.

Median V is computed inside the inner circle (0.75× radius). This is the primary
brightness test and a major factor in ranking candidates.

A soft score selects the best candidate:
- score = area × (0.25 + circularity) × (0.25 + fill)
- strict candidates get a 1.35× bonus.
- low median V scales the score down; higher median V scales it up.

When multiple candidates exist, the detector prefers the one with higher
median V inside the inner circle, with score as a tiebreaker.

### 6) Refinement (Hough Circle)
The best contour center/radius is refined with Hough circles in a local ROI:
- ROI: padded window around the contour estimate.
- Hough parameters tuned for small‑to‑medium circles.
- If two circles exist (ball + reflection), the upper circle is preferred.

### 7) Post‑Checks (Confidence Filters)
These checks reduce false positives before acceptance:
- Inner mask coverage: require sufficient mask fill inside 0.75× radius.
- Edge ring density: require circular edge energy near the radius.
- Hue coverage: require sufficient HSV‑gate coverage inside the inner circle.
- Median V: require sufficient median brightness inside the inner circle.
- Radial edge symmetry: if edge coverage is sufficient, require radial alignment.

Two thresholds are used for edge ring density:
- Strict candidates use a lower minimum.
- Non‑strict candidates require a higher edge density.

### 8) Radial Edge Symmetry (Geometry Validation)
If ring edges are present, compute radial alignment of gradients and require:
- radial_score ≥ 0.55
- coverage ≥ 0.15

Radial symmetry also scales the final score:
$$\text{score} = \text{base} \times (0.5 + 0.5 \times \text{radial\_score})$$

### 9) Distance‑Transform Fallback (Reflection Handling)
If no contour candidate is acceptable, the fallback attempts to infer a circle from the distance transform of the combined mask:
- Find strong peaks in the distance map.
- Prefer upper peaks to avoid reflection duplicates.
- Apply inner mask coverage and ring density checks.
- Refine via Hough; if refinement fails, fallback is rejected.

### 10) Output + Debug
On success, the radius is inflated by 1.10× to cover the full ball area.
The detector also publishes:
- thresholds used
- contour counts
- best candidate stats
- reject list (top‑N)
- debug mosaic with 4 panes:
  - Lab a mask
  - HSV mask (H,S,V gates)
  - Combined mask (now shows circle overlay)
  - Overlay + contours + edges inset
  - Overlay includes a radial symmetry inset (aligned edges in green)

## Thresholds and Defaults
These defaults are tuned for an orange/red ball on dark, reflective surfaces:
- a_percentile: 97.0
- a_min: 155
- s_min: 60
- v_min: 40
- h_use: True
- h_red_max: 10
- h_red_min2: 160
- h_orange_min: 8
- h_orange_max: 35
- min_area: 800
- max_area_ratio: 0.15
- min_circularity: 0.55
- min_fill: 0.55
- min_radius: 10
- max_radius_ratio: 0.40
- inner_ratio: 0.75
- min_inner_mask_coverage: 0.35
- min_edge_ring_density: 0.012
- min_edge_ring_density_non_strict: 0.018
- min_hue_coverage: 0.22
- min_solid_sat_coverage: 0.30
- min_v_coverage: 0.35
- min_v_median: 120
- v_strong: 110
- min_radial_score: 0.55
- min_radial_coverage: 0.15

## Debug Output Fields
- thresholds: {a_percentile, a_min, a_thr, a_p, s_min, v_min, min_v_median, v_strong, h_use, h_red_max, h_red_min2, h_orange_min, h_orange_max}
- counts: {contours_total, considered, strict}
- best: {score, area, circularity, fill, inner_cov, hue_cov, v_med, v_cov, ring_den, radial_score, radial_cov}
- rejects: top‑N rejected contours with reasons
- refine: refinement metadata (ROI, edges, selection)
- fallback: distance transform details (if used)

## Common Failure Modes
- Warm lighting can shift white surfaces into the Lab a threshold.
- Large uniform areas can pass the combined mask, especially with elevated S/V.
- Specular reflections can distort contour shape into a peanut‑like blob.

## Tuning Guidance
- If white/gray regions become false positives, raise a_min or reduce a_percentile.
- If saturation is too permissive, raise s_min.
- If shadows are included, raise v_min.
- If reflections dominate, increase ring density thresholds or inner mask coverage.
- If the detector misses genuine balls, slightly reduce min_area or min_circularity.

## Integration Points
- Used by mtDogBallTrack.BallTracker.process_with_cv
- Debug mosaic is displayed by CV Ball debug window in mtDogMain
- Counts and thresholds feed the UI overlay and histogram tools

## Notes
- The detector prioritizes correctness over high recall in ambiguous scenes.
- The fallback path is intentionally conservative; no refinement means no accept.
- The 1.10× radius inflation is a UI/ROI convenience and not a confidence metric.
