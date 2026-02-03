# Full Tracking (Ball) — Behavior Specification

This document describes the current **FULL tracking** behavior implemented in the client.

Primary code path:
- FULL logic: [Code/Client/mtDogMain.py](Code/Client/mtDogMain.py)
- Tracker config/UI: [Code/Client/mtDogBallTrack.py](Code/Client/mtDogBallTrack.py)
- Dog command/telemetry helpers: [Code/Client/mtDogLogicMixin.py](Code/Client/mtDogLogicMixin.py)

---

## 1) What “FULL tracking” means

When Ball mode is ON and Tracking mode is `full`:

- **Head tracking** tries to keep the ball vertically centered (servo pitch).
- **Body tracking** tries to:
  1) **Turn first** (left/right) until the ball is X-centered.
  2) Only then **approach forward** toward the ball.
  3) **Stop approaching** when the ball looks “close enough” (based on ball size).

FULL mode uses **two different “control loops”** that run each frame:
- Head loop (servo): uses Y-position only.
- Body loop (robot motion): uses X-position first; forward motion is gated by X centering.

---

## 2) Preconditions / when FULL logic runs

FULL tracking actions occur only when all are true:

- Ball mode enabled (`self.ball_mode_enabled`)
- Tracking mode is FULL (`TRACKING_MODE_FULL`)
- Dog control is ready (`use_dog_video == True`, TCP connected)

There are also important runtime gates:

- **Body tracking** only runs when the ball is considered “locked”:
  - `ball_center is not None` AND `missed_frames == 0`
- If the ball is not locked:
  - `missed_frames == 1` → immediate `Stop` (one-time) to prevent continuing a previous turn
  - `missed_frames >= 2` → the **lost-ball search / obstacle avoidance** behavior can run

---

## 3) Inputs used by FULL mode

### Vision inputs (from BallTracker)

- `last_center = (x, y)` — ball center in pixels
- `last_radius` — ball radius in pixels
- `missed_frames` — consecutive frames without an accepted detection

### Telemetry input (from SONIC)

- `distance_cm` — ultrasonic distance to obstacle
- Telemetry freshness gate:
  - if telemetry is stale (>2s), obstacle/search logic will `Stop` for safety

---

## 4) Body tracking policy in FULL mode (turn-first + gated forward)

Body tracking uses a *hysteresis axis selector* (`self._body_hyst_axis`):

### 4.1 Deadzone and centering tolerance

- Compute frame center:
  - `center_x = w/2`, `center_y = h/2`
- Offsets:
  - `x_off = ball_x - center_x` (positive means ball is to the RIGHT)
  - `y_off = ball_y - center_y` (positive means ball is BELOW)
- Body deadzone:
  - `x_dead = max(20, w * deadzone_ratio)`
  - `y_dead = max(20, h * deadzone_ratio)`
- **X-centered** condition (required before forward):
  - `abs(x_off) <= x_dead`

### 4.2 Turn-first rule

- If the ball is not X-centered, FULL mode sends a turn command:
  - `Turn-L` if the ball is left of center
  - `Turn-R` if the ball is right of center

This happens **before** any forward motion is allowed.

### 4.3 Forward approach rule (FULL mode)

If X is centered AND the ball is not “close enough”, FULL mode moves forward:

- Command: `Forward`
- Speed can be scaled by Body-Kp (see below).

### 4.4 “Close enough” rule (ball-size threshold)

FULL mode estimates apparent ball diameter:

- `ball_diameter = 2 * last_radius`

Then:

- `close_enough = (ball_diameter >= w/3)`

If `close_enough` is true, FULL mode stops forward approach.

---

## 5) Body-Kp proportional speed scaling (optional)

Body-Kp is an optional proportional speed override.

- If `body_kp == 0.0` → fixed-speed behavior (uses the UI speed setting)
- If `body_kp > 0.0` → speed increases with error magnitude, clamped to 2..10

In FULL mode:

- Turn speed scales with X error
- Forward speed scales with how far the ball diameter is from the threshold:
  - `approach_err = (w/3) - ball_diameter`

---

## 6) FULL-mode completion sequence when close enough

When FULL mode detects `close_enough == True`, it triggers a **one-shot completion sequence**.

### 6.1 Trigger

- Condition: `ball_diameter >= w/3`
- It is **latched** (`_close_enough_latched = True`) so it only triggers once.

### 6.2 Actions (in order)

1) Double beep
2) Double green LED flash
3) `Stop`
4) `Relax`
5) After 5 seconds: `Off` (sends `CMD_STOP_PWM`)

### 6.3 Motion gating during completion

Once latched, FULL mode will:

- Stop sending body motion commands
- Keep issuing `Stop` defensively
- Show a dedicated message in the Mask window debug HUD:
  - `GOAL:close_enough → Stop, Relax, Off (5s)`
  - `SEQ:...` showing sequence phase and elapsed time

Note: head tracking may still attempt to send servo angles while the ball is locked. If servos are powered off (`Off`), the head will not physically move.

---

## 7) Lost-ball behavior while in FULL mode

When FULL mode does **not** have a stable ball lock:

- `missed_frames == 1`:
  - Sends `Stop` once (prevents continuing an old turn/forward)
  - HUD shows `SEARCH:hold (lost=1)`

- `missed_frames >= 2`:
  - Runs a **search + obstacle avoidance** state machine.

### 7.1 Search pattern (default)

If “Search forward” is enabled, the search behavior repeats:

- Turn-left scan for 2.0s (`Turn-L`)
- Forward for 1.0s (`Forward`)
- Repeat

Mask HUD shows the phase:

- `PATTERN:scan 0.7/2.0s ...` or
- `PATTERN:forward 0.2/1.0s ...`

### 7.2 Scan-only mode

If “Search forward” is disabled, it will continuously:

- Turn-left scan (`Turn-L`)

HUD shows:

- `PATTERN:scan-only`

### 7.3 Telemetry safety gate

If SONIC telemetry is stale (>2 seconds):

- The client sends `Stop`
- Enters `SEARCH:idle (telemetry stale)`

This prevents blind obstacle behavior when distance is unknown.

---

## 8) Obstacle avoidance during search

Obstacle avoidance is only used while searching (ball lost) and telemetry is fresh.

- If `distance_cm <= obstacle_near_cm`:
  - Enter escape mode: turn-left (`Turn-L`) until distance clears

- Escape ends when `distance_cm > obstacle_clear_cm`
  - Then search resumes, restarting from scan phase

---

## 9) On-screen UI / debug messages

### 9.1 Color window

- Draws dashed vertical lines showing the **body X deadzone**
- Draws dashed horizontal lines showing the **head Y deadband**
- Draws a center `+`

### 9.2 Mask window (debug HUD)

The Mask window displays current decisions via `ball_tracker.body_debug_lines`:

- Normal FULL tracking:
  - `TRACK:full axis:x cmd:Turn-L` (or `Turn-R`, `Forward`, `Stop`)
  - `diam:... thr:... close:...`

- Lost-ball search:
  - `SEARCH:pattern cmd:Turn-L ...` (or `Forward`)
  - `PATTERN:...`
  - `dist:... near:... clear:...`

- Close-enough completion:
  - `GOAL:close_enough → Stop, Relax, Off (5s)`
  - `SEQ:relax +0.8s` etc.

---

## 10) Command name mapping (human-friendly)

The UI/HUD uses these labels:

- `Turn-L` → `CMD_TURN_LEFT` (key `w`)
- `Turn-R` → `CMD_TURN_RIGHT` (key `r`)
- `Forward` → `CMD_MOVE_FORWARD` (key `e`)
- `Stop` → `CMD_MOVE_STOP`
- `Relax` → `CMD_RELAX`
- `Off` → `CMD_STOP_PWM`

---

## 11) Config knobs that affect FULL mode

These are persisted in `mtBall_Calib.json` under `tracking` (via the Mask window):

- `deadzone_ratio` (Body-Deadzone)
- `body_interval` (command rate limit)
- `body_kp` (optional proportional speed scaling)

Lost-ball / obstacle:

- `search_forward_enabled`
- `search_forward_speed`
- `obstacle_avoid_enabled`
- `obstacle_near_cm`
- `obstacle_clear_cm`
- `obstacle_turn_speed`

---

## 12) Practical notes / tuning

- If you see “wiggling” during approach: increase Body-Deadzone slightly or lower Body-Kp.
- If the robot searches too aggressively when ball is lost: increase `body_interval` or lower search speeds.
- If obstacles cause late reactions: lower `obstacle_near_cm` is *more risky*; usually raise it slightly instead.
