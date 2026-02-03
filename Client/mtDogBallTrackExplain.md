# Ball Locking Decision Logic - Detailed Explanation

## Overview
The ball locking mechanism is a **multi-stage filtering system** that ensures robust, stable ball tracking even with noise, occlusions, and lighting changes. It uses **three key decision gates**:

1. **Contour Selection** (which blob is the ball?)
2. **Jump Rejection** (is this a real movement or noise?)
3. **Temporal Smoothing** (smooth out jitter while preserving responsiveness)

---

## Stage 1: Contour Selection (MAX AREA Strategy)

### Decision Logic
```python
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area < min_area:
        continue
    if area > max_area:
        max_area = area
        chosen_cnt = cnt
```

### Parameters
| Parameter | Value | Meaning |
|-----------|-------|---------|
| `min_area` | 0.0004 × (w × h) | Ignore blobs < 0.04% of frame area |
| Strategy | MAX AREA | Pick the **largest blob** |

### Why MAX AREA?
- **Assumption**: The ball is the largest colored object in the HSV range
- **Robustness**: Ignores noise (small random pixels) and background reflections
- **Trade-off**: 
  - ✅ Simple, fast, no complex math
  - ❌ Fails if another object (hand, wall) is larger and same color
  - ⚠️ Mitigated by good HSV calibration

### Example Scenario
```
Frame has 5 blobs from HSV mask:
- Blob 1: 50 pixels (tiny noise) → REJECTED (< min_area)
- Blob 2: 800 pixels (ball)      → ✅ CHOSEN (max area)
- Blob 3: 200 pixels (glare)     → skipped
- Blob 4: 100 pixels (shadow)    → skipped
```

---

## Stage 2: Jump Rejection (Temporal Outlier Detection)

### Decision Logic
```python
if self.filtered_center is not None:
    dx = raw_center[0] - self.filtered_center[0]
    dy = raw_center[1] - self.filtered_center[1]
    dist2 = dx*dx + dy*dy
    max_jump = self.max_jump_ratio * min(w, h)
    
    if dist2 > max_jump * max_jump:
        # REJECT this frame's detection
        return mask, frame_bgr  # Don't update filtered_center
```

### Parameters
| Parameter | Value | Meaning |
|-----------|-------|---------|
| `max_jump_ratio` | 0.35 | Max jump = 35% of shortest dimension |
| Threshold | 35% of `min(width, height)` | For 640×480: **35% × 480 = 168 pixels** |

### Why Jump Rejection?
- **Problem**: HSV threshold can flicker, detecting different object momentarily
- **Solution**: Detect **impossible movements** (ball can't teleport 168px in 1 frame)
- **Benefit**: Noise spike detection with physical plausibility check

### Example Scenario
```
480p height = 480 pixels
max_jump threshold = 0.35 × 480 = 168 pixels

Scenario A: Smooth tracking
- Previous center: (320, 240)
- New detected: (325, 245)
- Distance: sqrt(5² + 5²) = 7 pixels ✅ ACCEPTED

Scenario B: HSV flicker (wrong blob detected)
- Previous center: (320, 240)
- New detected: (80, 400)  [unrelated object]
- Distance: sqrt(240² + 160²) = 288 pixels ❌ REJECTED
- Keeps using previous filtered_center
```

---

## Stage 3: Temporal Smoothing (EMA - Exponential Moving Average)

### Decision Logic
```python
if self.filtered_center is None:
    # First detection → use raw center directly
    fx, fy = raw_center
else:
    # Blend: 35% new + 65% previous
    fx = int(0.35 * raw_center[0] + 0.65 * self.filtered_center[0])
    fy = int(0.35 * raw_center[1] + 0.65 * self.filtered_center[1])

self.filtered_center = (fx, fy)
self.last_center = self.filtered_center  # This is what gets drawn/tracked
```

### Parameters
| Parameter | Value | Meaning |
|-----------|-------|---------|
| `smooth_alpha` | 0.35 | 35% weight to current frame, 65% to history |
| Formula | `new = α × current + (1-α) × previous` | EMA blending |

### Why EMA Smoothing?

**Problem**: Mask noise causes jitter even after detecting correct blob
- Raw center bounces ±5-10 pixels every frame
- Servo would vibrate, wasting power

**Solution**: Weighted average gives **temporal coherence**
- Smooths out noise
- Preserves quick movements (ball suddenly moves)
- Prevents overshoot/lag

### Mathematical Behavior

| α Value | Characteristic | Trade-off |
|---------|----------------|-----------|
| **0.05** | Heavy smoothing | Lags behind ball, smooth but unresponsive |
| **0.35** | Medium (CURRENT) | Good balance: smooth + responsive |
| **0.70** | Light smoothing | Responsive but noisier |
| **1.00** | No smoothing | Raw detection (very noisy) |

### Example Smoothing Sequence
```
Raw detection (noisy):
Frame 1: x = 320
Frame 2: x = 325 (noise)
Frame 3: x = 318 (noise)
Frame 4: x = 322 (real movement)

EMA with α=0.35:
Frame 1 filtered: 320
Frame 2 filtered: 0.35×325 + 0.65×320 = 321.75 ≈ 322
Frame 3 filtered: 0.35×318 + 0.65×322 = 320.6 ≈ 321
Frame 4 filtered: 0.35×322 + 0.65×321 = 321.35 ≈ 321

Result: Smooth curve instead of jittery detection
```

---

## Integration: Complete Decision Flow

```
Frame arrives
    ↓
[1] Compute HSV mask → find all contours
    ↓
[2] Filter by min_area → reject tiny noise
    ↓
[3] Select MAX AREA contour → choose most likely ball
    ↓
    No contour? → Keep previous filtered_center (ghost mode)
    ↓
[4] Check jump distance → reject impossible teleports
    ↓
    Too far? → Ignore detection, keep previous center
    ↓
[5] Apply EMA smoothing → blend with history
    ↓
[6] Update last_center → ready for drawing/servo
    ↓
Head servo uses this smoothed center for tracking
```

---

## Body Tracking (Full / Body modes)

After the ball lock produces a stable `last_center = (cx, cy)`, the client can optionally drive the **dog body** (walking/turning) based on the ball’s position relative to the image center.

### Tracking modes

The system supports three tracking modes (stored in `mtBall_Calib.json` under `tracking.mode`):

| Mode | Meaning | Head servo | Body motion |
|------|---------|-----------|------------|
| `full` (default) | Full tracking | ✅ ON | ✅ ON |
| `head` | Head tracking only | ✅ ON | ❌ OFF |
| `body` | Body tracking only | ❌ OFF | ✅ ON |

This is useful for debugging: **Body Tracking** keeps head tracking quiet so you can clearly observe the motion commands received by the server.

### Decision logic (center offsets → motion command)

Body tracking runs only when:
- Tracking mode is `full` or `body`
- The dog control socket is connected
- The ball is currently “locked” (`ball_center != None` and `missed_frames == 0`)

The method computes pixel offsets from the frame center:

```python
center_x = w / 2
center_y = h / 2
x_off = cx - center_x
y_off = cy - center_y

x_dead = max(20, w * 0.18)
y_dead = max(20, h * 0.18)

# Priority: horizontal first, then vertical
if abs(x_off) > x_dead:
    key = 'w' if x_off < 0 else 'r'      # turn left / turn right
elif abs(y_off) > y_dead:
    key = 'c' if y_off < 0 else 'e'      # backward / forward
else:
    key = None
```

Notes:
- **Horizontal has priority** so the dog turns to face the ball before moving forward/back.
- `x_dead` / `y_dead` prevent jitter when the ball is near the center.

### Throttle (anti-spam)

Even if a key is chosen, body commands are **rate-limited**:

```python
if now - last_body_cmd_time < body_tracking_interval:
    return
```

This prevents sending commands every frame.

### Command protocol (what the server receives)

The client ultimately sends motion as **Freenove command strings** in the format:

```
CMD_TURN_LEFT#<speed>
CMD_TURN_RIGHT#<speed>
CMD_MOVE_FORWARD#<speed>
CMD_MOVE_BACKWARD#<speed>
```

Important:
- The server expects the `#<speed>` part for movement/turn commands.
- The `key` (`w/e/r/c/...`) is only an internal mapping.

---

## Failure Modes & Robustness

### When Ball Locking Fails

| Scenario | Why | Mitigation |
|----------|-----|-----------|
| **Multiple same-color objects** | MAX AREA picks wrong blob | Good HSV calibration |
| **Ball occluded** | No blob detected | Maintains previous center (momentum) |
| **Rapid movement** | Exceeds max_jump threshold | Increase `max_jump_ratio` (0.35→0.50) |
| **Poor lighting** | Mask has gaps, wrong blobs | HSV calibration with good Kp slider |
| **Noisy servo commands** | Jitter from raw detection | EMA smoothing with tuned α |

### Adaptive Behavior

The system has **memory**:
- If ball disappears briefly → uses last known position (3-second trace buffer)
- If ball reappears near last position → accepts it (within jump threshold)
- If ball vanishes completely → trace fades, servo holds last angle

---

## Tunable Parameters for Fine Control

### In `mtDogBallTrack.py` → `BallTracker.__init__()`

```python
# Detection tuning
self.smooth_alpha = 0.35        # ↑ = more responsive, ↓ = smoother
self.max_jump_ratio = 0.35      # ↑ = more tolerant of jumps, ↓ = stricter
# In compute_mask():
min_area = 0.0004 * (w * h)     # ↑ = ignore more noise
```

### In `HeadConfig`

```python
deadband: float = 0.02          # ↓ = finer control, ↑ = less jitter
max_step_deg: float = 1.0       # ↓ = slower servo, ↑ = faster
kp: float = 4.0                 # Servo gain (set via slider)
```

---

## Summary: Why This Design?

| Decision | Benefit |
|----------|---------|
| **MAX AREA** | Fast, simple, assumes ball is largest colored object |
| **Jump Rejection** | Prevents flicker/occlusion from causing servo jitter |
| **EMA Smoothing** | Noise reduction while maintaining responsiveness |
| **Trace History** | Continues tracking even if ball briefly disappears |
| **Layered Filtering** | Each stage handles different types of noise |

**Result**: Robust, stable ball locking that handles noise, shadows, lighting changes, and brief occlusions while maintaining real-time responsiveness for head servo tracking.

---

## Testing/Tuning Checklist

- [ ] Move ball slowly → should follow smoothly without lag
- [ ] Move ball quickly → should keep up without overshooting
- [ ] Flicker HSV threshold (use Mask window sliders) → head servo should NOT jitter
- [ ] Occlude ball momentarily → should maintain position, resume tracking
- [ ] Change lighting → should re-detect without false positives
- [ ] Adjust `smooth_alpha` slider → observe responsiveness trade-off
