"""
MT_BallTracking.py - interactive color-calibrated ball tracker

Real-time orange/red ball tracker using the MacBook camera and OpenCV.

Author: MT & GitHub Copilot
Version: 1.3.4
Date: 2025-11-08

Purpose
- Capture video from a local camera, detect and track an orange/red ball,
  draw tracking annotations, provide FPS/status overlay and interactive HSV
  sampling for fast calibration.

Requirements
- Python 3.8+ (macOS)
- opencv-python, numpy
  Install: python3 -m pip install opencv-python numpy

Usage
- Run from the project's Client folder:
    python3 MT_BallTracking.py
  Optional flags:
    --camera N    Use camera index N (default 0)
    --mask        Start with mask window visible

Controls
- Move cursor; left-click to set a sampling point.
- Press 'c' to calibrate using 64x64 ROI median HSV at cursor (or center if none).
- Press 's' to sample a single pixel HSV (no save).
- Press 'm' to toggle mask display.
- Press 'q' to quit the application.

Notes
- HSV = Hue, Saturation, Value. Hue range in OpenCV is 0–179.
- Calibration uses robust stats from the 64x64 ROI: H median/IQR, S_p10, V_p10.
- Mask HSV thresholds are derived from those stats; see Mask window overlay.
- Terminal shows: live “Cursor : x , y”, calibration summary after 'c', and lock/unlock events with ΔHSV.

Revision History (major changes)
- 1.0.0  2025-10-31  Initial prototype.
- 1.1.x  2025-11-01..03  Trails and FPS overlay.
- 1.2.0  2025-11-08  Multi-range HSV + status text.
- 1.3.0–1.3.2  2025-11-08  Interactive sampling, save/load, thumbnail, guides.
- 1.3.3  2025-11-08  64x64 ROI square, thumbnail alignment, ΔHSV overlay baseline.
- 1.3.4  2025-11-08  Terminal cursor + status logs, robust calibration stats load/save,
                     temporal consistency and adaptive S/V, mask debug overlay.
"""

import os, json, math, time, argparse
import cv2
import numpy as np
from collections import deque
import sys
import select
import termios
import tty
import atexit
from typing import List, Tuple

# -----------------------------------------------------------------------------
# Configuration: HSV ranges and detection tuning constants
# -----------------------------------------------------------------------------
# Fixed HSV thresholds (edit these to tune your mask)
FIXED_H0_LOW  = 171         # default 171 
FIXED_H0_HIGH = 179         # default 179
FIXED_H1_LOW  = 0           # default 0
FIXED_H1_HIGH = 12           # default 8  
FIXED_S_MIN   = 150         # default 100
FIXED_V_MIN   = 50          # default 50

# Optional: keep example initial ranges for reference (not used directly)
# hsv_ranges = [
#     (np.array([0, 100, 70]),  np.array([10, 255, 255])),
#     (np.array([170, 100, 70]), np.array([180, 255, 255])),
#     (np.array([5, 100, 100]),  np.array([25, 255, 255])),
# ]

MIN_RADIUS_PX = 8
MAX_RADIUS_PX = 160
MIN_AREA = 200
MIN_CIRCULARITY = 0.60
MIN_SOLIDITY = 0.80
MAX_ASPECT_RATIO_DEV = 0.35
MIN_SATURATION = 80
MIN_VALUE = 60

# --- Simple window placement configuration (no CLI) ---
# Adjust these two tuples to set your preferred fixed positions.
# IMPORTANT: Raw config (main screen only; negative Y often ignored by HighGUI on macOS)
WINDOW_MASK_POS = (10, 0)
WINDOW_TRACK_POS = (10, 450)

WINDOW_DECOR_OFFSET_TRACK = None
WINDOW_DECOR_OFFSET_MASK = None
WINDOW_USE_OFFSET_COMP = True  # set False to see raw client coords

# Add runtime offset calibration
WINDOW_POS_OFFSET_TRACK = None
WINDOW_POS_OFFSET_MASK = None
WINDOW_ENFORCE_EVERY_N_FRAMES = 30   # how often to re-check
SHOW_MASK_AT_START = True
ALWAYS_SHOW_WINPOS_OVERLAY = True
AUTO_ENFORCE = False  # NEW: False disables auto window reposition

# Manual HSV builder (two hue bands + S/V minima)
def build_manual_hsv_ranges(h0_lo, h0_hi, h1_lo, h1_hi, s_min, v_min):
    def ch(x): return max(0, min(179, int(x)))
    def c8(x): return max(0, min(255, int(x)))
    lo0 = np.array([ch(h0_lo), c8(s_min), c8(v_min)], dtype=np.uint8)
    hi0 = np.array([ch(h0_hi), 255, 255], dtype=np.uint8)
    lo1 = np.array([ch(h1_lo), c8(s_min), c8(v_min)], dtype=np.uint8)
    hi1 = np.array([ch(h1_hi), 255, 255], dtype=np.uint8)
    return [(lo0, hi0), (lo1, hi1)]

def get_fixed_hsv_ranges():
    return build_manual_hsv_ranges(FIXED_H0_LOW, FIXED_H0_HIGH, FIXED_H1_LOW, FIXED_H1_HIGH, FIXED_S_MIN, FIXED_V_MIN)

sampling_point = None      # (x,y) clicked
sampled_hsv = None         # tuple (H,S,V) from calibration or single pixel
cursor_point = None        # current mouse mapped to frame coordinates
last_frame_size = (640, 480)

CALIB_FILE = "MT_BallCalibration.jpg"
CALIB_META = "MT_BallCalibration.json"
calibrated_img = None
calibrated = False
calib_sample_point = None   # (x,y) within saved ROI
show_calib_alert = False

# Reference-only: median HSV of the saved 60x60 calibration image
calib_hsv_median = None

# Removed: calib_hsv_stats, ball_color_history, adapt_* variables

# -----------------------------------------------------------------------------
# Calibration load/save (reference only; does not affect mask thresholds)
# -----------------------------------------------------------------------------
def _median_hsv_of_bgr(img_bgr):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    med = np.median(hsv.reshape(-1, 3), axis=0).astype(int)
    return (int(med[0]), int(med[1]), int(med[2]))

def try_load_calibration():
    global calibrated_img, calibrated, sampled_hsv, calib_sample_point, show_calib_alert, calib_hsv_median
    calibrated_img = None
    calib_sample_point = None
    sampled_hsv = None
    calib_hsv_median = None
    if os.path.isfile(CALIB_FILE):
        img = cv2.imread(CALIB_FILE)
        if img is not None and img.size > 0:
            calibrated_img = img
            calibrated = True
            show_calib_alert = False
            # Load optional metadata (sample point)
            if os.path.isfile(CALIB_META):
                try:
                    with open(CALIB_META, "r") as f:
                        meta = json.load(f)
                    sr = meta.get("sample_rel")
                    if isinstance(sr, list) and len(sr) == 2:
                        calib_sample_point = (int(sr[0]), int(sr[1]))
                except Exception:
                    pass
            # Compute median HSV of the saved image for display
            calib_hsv_median = _median_hsv_of_bgr(calibrated_img)
            sampled_hsv = calib_hsv_median
            if calib_sample_point is None:
                h, w = calibrated_img.shape[:2]
                calib_sample_point = (w // 2, h // 2)
        else:
            calibrated = False
            show_calib_alert = True
    else:
        calibrated = False
        show_calib_alert = True

def save_calibration(roi_bgr, sample_rel):
    global calib_sample_point, sampled_hsv, calib_hsv_median
    cv2.imwrite(CALIB_FILE, roi_bgr)
    calib_sample_point = sample_rel
    try:
        calib_hsv_median = _median_hsv_of_bgr(roi_bgr)
        sampled_hsv = calib_hsv_median
        meta = {
            "sample_rel": [int(sample_rel[0]), int(sample_rel[1])],
            "sample_hsv": list(sampled_hsv),
        }
        with open(CALIB_META, "w") as f:
            json.dump(meta, f)
    except Exception:
        pass

def overlay_thumbnail_topleft(frame, thumb, top_left=(10, 40)):
    th_h, th_w = thumb.shape[:2]
    x, y = top_left
    fh, fw = frame.shape[:2]
    if x < 0 or y < 0 or x + th_w > fw or y + th_h > fh:
        return
    frame[y:y+th_h, x:x+th_w] = thumb

def roi_rect_around(cx, cy, size, img_w, img_h):
    """
    Return (x1,y1,x2,y2) exclusive bounding a square of side 'size'
    centered on (cx,cy), clamped inside image.
    """
    half = size // 2
    x1 = cx - half
    y1 = cy - half
    x1 = max(0, min(x1, img_w - size))
    y1 = max(0, min(y1, img_h - size))
    x2 = x1 + size
    y2 = y1 + size
    return x1, y1, x2, y2

def contour_median_hsv(hsv_img, contour):
    mask_c = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask_c, [contour], -1, 255, -1)
    pixels = hsv_img[mask_c==255]
    if pixels.size < 3: return None
    med = np.median(pixels, axis=0).astype(int)
    return tuple(int(x) for x in med)

def hue_distance(h1, h2):
    d = abs(h1 - h2)
    return min(d, 180 - d)

class TerminalKeyWatcher:
    """Non-blocking single-char reader for terminal (POSIX)."""
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.orig = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        atexit.register(self.restore)
    def restore(self):
        try:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.orig)
        except Exception:
            pass
    def poll_char(self):
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            ch = sys.stdin.read(1)
            return ch
        return None

# ---------- Terminal status (non-scrolling) helpers ----------
STATUS_LINES = 3  # Cursor, Calib, Lock

def _fmt_hsv(hsv_tuple):
    if hsv_tuple is None:
        return "-"
    h, s, v = [int(x) for x in hsv_tuple]
    return f"({h},{s},{v})"

def _fmt_ranges_short(ranges):
    if not ranges:
        return "-"
    parts = []
    for i, (lo, hi) in enumerate(ranges[:2]):  # show up to 2 ranges compactly
        lh = int(lo[0]); hh = int(hi[0])
        ls = int(lo[1]); lv = int(lo[2])
        parts.append(f"R{i}:H[{lh}-{hh}] S>={ls} V>={lv}")
    return " | ".join(parts)

def print_status_in_place(cursor_xy, calib_hsv, ranges, lock_found, lock_xy, lock_hsv, roi_hsv, roi_delta=None):
    """Render 3 lines (Cursor / Calib / Lock + ΔHSV) in terminal and move cursor back up."""
    # Build lines
    if cursor_xy is None:
        line1 = "Cursor : - , -"
    else:
        line1 = f"Cursor : {int(cursor_xy[0])} , {int(cursor_xy[1])}"

    line2 = f"Calib  : HSV={_fmt_hsv(calib_hsv)}"
    rng_txt = _fmt_ranges_short(ranges)
    if rng_txt != "-":
        line2 += f"  {rng_txt}"

    # Delta uses ROI median HSV vs calibration (more stable reference than contour color)
    dtxt = _fmt_hsv(roi_delta) if roi_delta else "-"
    if lock_found and lock_xy is not None and lock_hsv is not None:
        line3 = f"Lock   : FOUND ({int(lock_xy[0])},{int(lock_xy[1])}) ΔHSV={dtxt} ROI={_fmt_hsv(roi_hsv)}"
    else:
        line3 = f"Lock   : NOT FOUND ΔHSV={dtxt} ROI={_fmt_hsv(roi_hsv)}"

    # Emit with line clear and move-up so it doesn't scroll
    out = (
        f"\r\x1b[2K{line1}\n"  # clear line and write
        f"\x1b[2K{line2}\n"
        f"\x1b[2K{line3}\n"
        f"\x1b[{STATUS_LINES}A"  # move cursor up to start overwriting next time
    )
    try:
        sys.stdout.write(out)
        sys.stdout.flush()
    except Exception:
        pass

# --- Display helpers (macOS multi-display) ---

def _list_displays() -> List[Tuple[int,int,int,int]]:
    """Return list of (x,y,w,h) for all screens using AppKit (macOS). Fallback to default if unavailable."""
    out = []
    try:
        import platform
        if platform.system() == "Darwin":
            try:
                from AppKit import NSScreen
                screens = NSScreen.screens()
                for s in screens:
                    f = s.frame()
                    # f is NSRect; origin.y can be negative when screen is above main.
                    out.append((int(f.origin.x), int(f.origin.y), int(f.size.width), int(f.size.height)))
            except Exception:
                pass
        else:
            # Fallback: single display, default size
            out.append((0, 0, 1920, 1080))
    except Exception:
        # Fallback: single display, default size
        out.append((0, 0, 1920, 1080))
    return out

def _displays_union_top_left() -> Tuple[int,int,int,int]:
    """Compute union bounds in a top-left origin coordinate space (y down).
    AppKit frames use bottom-left origin. Convert by flipping using the max y2.
    Returns (x_tl, y_tl, w, h). Fallback is (0,0, 3840, 2160).
    """
    screens = _list_displays()
    if not screens:
        return (0, 0, 3840, 2160)
    # Find max y2 in BL space
    max_y2 = max(y + h for (_, y, _, h) in screens)
    # Convert each to TL space
    tl_rects = []
    for (x, y, w, h) in screens:
        y_tl = max_y2 - (y + h)
        tl_rects.append((x, y_tl, w, h))
    min_x = min(x for (x, y, w, h) in tl_rects)
    min_y = min(y for (x, y, w, h) in tl_rects)
    max_x = max(x + w for (x, y, w, h) in tl_rects)
    max_y = max(y + h for (x, y, w, h) in tl_rects)
    return (min_x, min_y, max_x - min_x, max_y - min_y)

def _clamp_to_visible(x: int, y: int, w: int, h: int, pad: int = 8) -> Tuple[int,int]:
    """Clamp a desired top-left (x,y) to the union of all displays in TL space."""
    ux, uy, uw, uh = _displays_union_top_left()
    x = max(ux + pad, min(x, ux + uw - pad - max(1, w)))
    y = max(uy + pad, min(y, uy + uh - pad - max(1, h)))
    return (int(x), int(y))

# --- Coordinate conversions between raw cv2 and our config (top-left of main display) ---
def _main_tl_origin() -> Tuple[int, int]:
    """Top-left of the main display in TL-union coordinates (y down)."""
    try:
        import platform
        if platform.system() == "Darwin":
            try:
                from AppKit import NSScreen
                screens_bl = _list_displays()
                if not screens_bl:
                    return (0, 0)
                max_y2 = max(y + h for (_, y, _, h) in screens_bl)
                main = NSScreen.mainScreen()
                if main is None:
                    return (0, 0)
                f = main.frame()
                mx_bl, my_bl, mw, mh = int(f.origin.x), int(f.origin.y), int(f.size.width), int(f.size.height)
                main_tl_y = max_y2 - (my_bl + mh)
                return (int(mx_bl), int(main_tl_y))
            except Exception:
                return (0, 0)
        else:
            return (0, 0)
    except Exception:
        return (0, 0)

def _raw_to_config(wx: int, wy: int, ww: int, wh: int) -> Tuple[int, int]:
    """Convert raw client rect (cv2.getWindowImageRect) to config coords (main TL)."""
    try:
        screens_bl = _list_displays()
        if not screens_bl:
            return (int(wx), int(wy))
        max_y2 = max(y + h for (_, y, _, h) in screens_bl)
        # Convert BL to TL for the client rect
        y_tl_union = max_y2 - (wy + wh)
        ox, oy = _main_tl_origin()
        return (int(wx - ox), int(y_tl_union - oy))
    except Exception:
        return (int(wx), int(wy))

def _config_to_raw(cx: int, cy: int, ww: int, wh: int) -> Tuple[int, int]:
    """Convert desired config coords (main TL) to raw client TL for moveWindow target.
    Note: moveWindow takes frame TL; we will calibrate a small offset to compensate.
    """
    try:
        screens_bl = _list_displays()
        if not screens_bl:
            return (int(cx), int(cy))
        max_y2 = max(y + h for (_, y, _, h) in screens_bl)
        ox, oy = _main_tl_origin()
        y_tl_union = cy + oy
        wx = int(cx + ox)
        wy_client = int(max_y2 - (y_tl_union + wh))
        return (wx, wy_client)
    except Exception:
        return (int(cx), int(cy))

def _apply_window_pos(name, cfg_pos, _slot=None):
    """Simple move (no decoration math). Works after the window has been shown."""
    try:
        cv2.moveWindow(name, int(cfg_pos[0]), int(cfg_pos[1]))
    except Exception:
        pass

def main(camera_index=0):
    global sampling_point, sampled_hsv, calibrated_img, calibrated, calib_sample_point, show_calib_alert, stable_frames, ball_locked

    try_load_calibration()

    show_mask = SHOW_MASK_AT_START

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    pts = deque(maxlen=32)
    prev_time = time.time()
    fps = 0.0
    frame_counter = 0
    fps_display_text = "FPS: 0.0"

    window_name = "Ball Tracking"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 720)
    mask_w, mask_h = 640, 480

    # Remove early moves; they’re ignored on macOS before first imshow
    # _apply_window_pos(window_name, WINDOW_TRACK_POS, "track")

    placed_track = False
    placed_mask = False

    # Place windows directly using raw coordinates (config values are raw positions)
    if show_mask:
        try:
            cv2.namedWindow("Mask", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Mask", mask_w, mask_h)
            _apply_window_pos("Mask", WINDOW_MASK_POS, "mask")
        except Exception:
            pass
    _apply_window_pos(window_name, WINDOW_TRACK_POS, "track")

    enforce_positions = 0  # disable initial repeated enforcement

    def on_mouse(event, x, y, flags, param):
        global sampling_point, cursor_point, last_frame_size
        mapped_x, mapped_y = x, y
        try:
            wx, wy, ww, wh = cv2.getWindowImageRect(window_name)
            fw, fh = last_frame_size
            if ww > 0 and wh > 0:
                mapped_x = int(x * fw / float(ww))
                mapped_y = int(y * fh / float(wh))
        except Exception:
            pass
        fw, fh = last_frame_size
        mapped_x = max(0, min(fw - 1, mapped_x))
        mapped_y = max(0, min(fh - 1, mapped_y))
        if event == cv2.EVENT_MOUSEMOVE:
            cursor_point = (mapped_x, mapped_y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            sampling_point = (mapped_x, mapped_y)
            cursor_point = (mapped_x, mapped_y)

    cv2.setMouseCallback(window_name, on_mouse)
    tkw = TerminalKeyWatcher()

    guide_lines = [
        "Calibration: move the o over the ball, LEFT-CLICK, then press 'c' to save",
        "(saves a 60x60 ROI; shows HSV median only; does not change mask)",
        "Press 'm' to toggle Mask image, 'q' to quit"
    ]

    required_stability = 5
    stable_frames = 0
    ball_locked = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, int(frame.shape[0] * 640 / frame.shape[1])))
        last_frame_size = (frame.shape[1], frame.shape[0])
        raw_frame = frame.copy()

        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # Fixed (hard-coded) HSV ranges
        current_ranges = get_fixed_hsv_ranges()

        # Build mask from fixed ranges
        mask = None
        for lower, upper in current_ranges:
            m = cv2.inRange(hsv, lower, upper)
            mask = m if mask is None else cv2.bitwise_or(mask, m)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center = None
        best = None
        best_score = -1

        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_AREA:
                continue
            per = cv2.arcLength(c, True)
            if per <= 0:
                continue
            circ = 4 * math.pi * area / (per * per)
            if circ < MIN_CIRCULARITY:
                continue
            (cen, rad) = cv2.minEnclosingCircle(c)
            rad = int(rad)
            if rad < MIN_RADIUS_PX or rad > MAX_RADIUS_PX:
                continue

            # Score by geometric quality only (color already enforced by mask)
            score = area * (circ ** 2)
            if score > best_score:
                best_score = score
                # Median HSV only for display
                mask_c = np.zeros(hsv.shape[:2], dtype=np.uint8)
                cv2.drawContours(mask_c, [c], -1, 255, -1)
                pixels = hsv[mask_c == 255]
                med_hsv = tuple(np.median(pixels, axis=0).astype(int)) if pixels.size >= 9 else (0, 0, 0)
                best = (int(cen[0]), int(cen[1]), rad, med_hsv)

        if best:
            bx, by, br, med_hsv = best
            center = (bx, by)
            stable_frames = min(required_stability, stable_frames + 1)
        else:
            stable_frames = max(0, stable_frames - 2)

        ball_locked = (stable_frames >= required_stability)
        found = ball_locked

        if best and found:
            bx, by, br, med_hsv = best
            cv2.circle(frame, (bx, by), br, (0, 255, 255), 2)
            cv2.circle(frame, (bx, by), 5, (0, 0, 255), -1)
            label = f"Ball ({bx}, {by}) r={br}"
            cv2.putText(frame, label, (bx + 10, by - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(frame, label, (bx + 10, by - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255,255,255), 1, cv2.LINE_AA)
            hsv_label = f"HSV: ({int(med_hsv[0])},{int(med_hsv[1])},{int(med_hsv[2])})"
            cv2.putText(frame, hsv_label, (bx + 10, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(frame, hsv_label, (bx + 10, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1, cv2.LINE_AA)
            if calib_hsv_median is not None:
                dH = hue_distance(med_hsv[0], calib_hsv_median[0])
                dS = med_hsv[1] - calib_hsv_median[1]
                dV = med_hsv[2] - calib_hsv_median[2]
                delta_label = f"ΔHSV: ({dH},{dS},{dV})"
                cv2.putText(frame, delta_label, (bx + 10, by + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, delta_label, (bx + 10, by + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0,255,0), 1, cv2.LINE_AA)
        pts.appendleft(center)
        for i in range(1, len(pts)):
            if pts[i - 1] is None or pts[i] is None:
                continue
            thickness = int(np.sqrt(len(pts) / float(i + 1)) * 2.5)
            cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

        now = time.time()
        dt = now - prev_time
        prev_time = now
        inst_fps = 1.0 / dt if dt > 0 else 0.0
        fps = 0.9 * fps + 0.1 * inst_fps
        frame_counter += 1
        # Enforce positions periodically (now guarded)
        if AUTO_ENFORCE and frame_counter % WINDOW_ENFORCE_EVERY_N_FRAMES == 0:
            _apply_window_pos(window_name, WINDOW_TRACK_POS, "track")
            if show_mask:
                _apply_window_pos("Mask", WINDOW_MASK_POS, "mask")

        if frame_counter % 8 == 0:
            fps_display_text = f"FPS: {fps:.1f}"

        font = cv2.FONT_HERSHEY_SIMPLEX
        margin = 10
        fps_scale = 0.50
        fps_pos = (frame.shape[1] - 160, margin + 12)
        status_pos = (frame.shape[1] - 160, margin + 36)
        cv2.putText(frame, fps_display_text, fps_pos, font, fps_scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, fps_display_text, fps_pos, font, fps_scale, (255,255,255), 1, cv2.LINE_AA)
        status_text = "Ball: FOUND" if ball_locked else "Ball: NOT FOUND"
        status_color = (50, 205, 50) if ball_locked else (0, 0, 255)
        cv2.putText(frame, status_text, status_pos, font, fps_scale, (0,0,0), 3, cv2.LINE_AA)
        cv2.putText(frame, status_text, status_pos, font, fps_scale, status_color, 1, cv2.LINE_AA)

        guide_max_width = frame.shape[1] // 2
        guide_scale = 0.30
        guide_color = (0, 255, 255)
        y0 = 18
        for line in guide_lines:
            line_scale = guide_scale
            while line_scale > 0.12:
                (tw, th), _ = cv2.getTextSize(line, font, line_scale, 1)
                if tw <= guide_max_width:
                    break
                line_scale -= 0.04
            cv2.putText(frame, line, (10, y0), font, line_scale, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(frame, line, (10, y0), font, line_scale, guide_color, 1, cv2.LINE_AA)
            y0 += int(th * 1.9)

        if calibrated_img is not None:
            # Show the saved 60x60 image as-is (no resizing)
            thumb = calibrated_img  # expected 60x60
            thumb_x = 10
            thumb_y = y0 + 6
            overlay_thumbnail_topleft(frame, thumb, top_left=(thumb_x, thumb_y))
            if calib_hsv_median is not None:
                hsv_text = f"calibrated HSV {_fmt_hsv(calib_hsv_median)}"
                cv2.putText(frame, hsv_text, (thumb_x, thumb_y + thumb.shape[0] + 12), font, 0.40, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, hsv_text, (thumb_x, thumb_y + thumb.shape[0] + 12), font, 0.40, (255,255,255), 1, cv2.LINE_AA)
            y0 = thumb_y + thumb.shape[0] + 28

        if not calibrated:
            reminder = "NO Calibration data! Press 'c' to calibrate (improves detection)."
            rem_scale = 0.36
            rem_x = 10
            rem_y = y0 + 6
            cv2.putText(frame, reminder, (rem_x, rem_y), font, rem_scale, (0,0,0), 4, cv2.LINE_AA)
            cv2.putText(frame, reminder, (rem_x, rem_y), font, rem_scale, (0,0,255), 1, cv2.LINE_AA)
            aw, ah = cv2.getTextSize(reminder, font, rem_scale, 1)[0]
            y0 = rem_y + ah + 6

        # Window position overlay (raw; same system as config)
        try:
            wx, wy, ww, wh = cv2.getWindowImageRect(window_name)
            if ALWAYS_SHOW_WINPOS_OVERLAY:
                cv2.putText(frame, f"Win:{wx},{wy} {ww}x{wh}", (10, frame.shape[0]-10),
                            font, 0.40, (0,0,0), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Win:{wx},{wy} {ww}x{wh}", (10, frame.shape[0]-10),
                            font, 0.40, (0,255,0), 1, cv2.LINE_AA)
        except Exception:
            pass

        if cursor_point is not None:
            cx, cy = cursor_point
            # Draw cursor tip and show pixel HSV near the tip (Ball Tracking window)
            try:
                px_h, px_s, px_v = [int(x) for x in hsv[cy, cx]]
            except Exception:
                px_h, px_s, px_v = (0, 0, 0)
            cv2.circle(frame, (cx, cy), 3, (0, 255, 255), -1)
            tip_label = f"HSV({px_h},{px_s},{px_v})"
            (ttw, tth), _ = cv2.getTextSize(tip_label, font, 0.45, 1)
            tx = min(frame.shape[1] - ttw - 2, cx + 8)
            ty = max(tth + 2, cy - 8)
            cv2.putText(frame, tip_label, (tx, ty), font, 0.45, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(frame, tip_label, (tx, ty), font, 0.45, (0,255,255), 1, cv2.LINE_AA)

            x1, y1, x2, y2 = roi_rect_around(cx, cy, 64, frame.shape[1], frame.shape[0])
            cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), (0,0,0), 3, cv2.LINE_AA)
            cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), (255,255,255), 1, cv2.LINE_AA)
            coord_label = f"({cx},{cy})"
            (tw, th), _ = cv2.getTextSize(coord_label, font, 0.45, 1)
            tx = max(2, min(frame.shape[1] - tw - 2, x1 + (64 - tw) // 2))
            ty = min(frame.shape[0] - 8, y2 + th + 6)
            cv2.putText(frame, coord_label, (tx, ty), font, 0.45, (0,0,0), 3, cv2.LINE_AA)
            cv2.putText(frame, coord_label, (tx, ty), font, 0.45, (255,255,255), 1, cv2.LINE_AA)
            roi_hsv = hsv[y1:y2, x1:x2]
            if roi_hsv.size:
                med_vals = np.median(roi_hsv.reshape(-1, 3), axis=0).astype(int)
                med_label = f"ROI HSV med: ({med_vals[0]},{med_vals[1]},{med_vals[2]})"
                (mw, mh), _ = cv2.getTextSize(med_label, font, 0.40, 1)
                mtx = max(2, min(frame.shape[1] - mw - 2, x1 + (64 - mw) // 2))
                mty = min(frame.shape[0] - 8, ty + mh + 4)
                cv2.putText(frame, med_label, (mtx, mty), font, 0.40, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(frame, med_label, (mtx, mty), font, 0.40, (255,255,255), 1, cv2.LINE_AA)

        cv2.imshow(window_name, frame)

        # Place the tracking window once, AFTER it’s visible
        if not placed_track:
            _apply_window_pos(window_name, WINDOW_TRACK_POS, "track")
            placed_track = True

        if show_mask:
            mask_vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            dbg_lines = []
            for i, (lo, hi) in enumerate(current_ranges):
                dbg_lines.append(f"R{i}: H[{int(lo[0])}-{int(hi[0])}] S>={int(lo[1])} V>={int(lo[2])}")
            try:
                if ALWAYS_SHOW_WINPOS_OVERLAY:
                    mx, my, mw, mh = cv2.getWindowImageRect("Mask")
                    cv2.putText(mask_vis, f"Win:{mx},{my} {mw}x{mh}", (10, mask_vis.shape[0]-10), font, 0.40, (0,0,0), 2, cv2.LINE_AA)
                    cv2.putText(mask_vis, f"Win:{mx},{my} {mw}x{mh}", (10, mask_vis.shape[0]-10), font, 0.40, (0,255,0), 1, cv2.LINE_AA)
            except Exception:
                pass
            ydbg = 16
            for line in dbg_lines:
                cv2.putText(mask_vis, line, (8, ydbg), font, 0.40, (0,0,0), 2, cv2.LINE_AA)
                cv2.putText(mask_vis, line, (8, ydbg), font, 0.40, (255,255,255), 1, cv2.LINE_AA)
                ydbg += 16

            # Draw cursor tip + HSV on Mask window too
            if cursor_point is not None:
                cx, cy = cursor_point
                try:
                    px_h, px_s, px_v = [int(x) for x in hsv[cy, cx]]
                except Exception:
                    px_h, px_s, px_v = (0, 0, 0)
                cv2.circle(mask_vis, (cx, cy), 3, (0, 255, 255), -1)
                tip_label = f"HSV({px_h},{px_s},{px_v})"
                (ttw, tth), _ = cv2.getTextSize(tip_label, font, 0.45, 1)
                tx = min(mask_vis.shape[1] - ttw - 2, cx + 8)
                ty = max(tth + 2, cy - 8)
                cv2.putText(mask_vis, tip_label, (tx, ty), font, 0.45, (0,0,0), 3, cv2.LINE_AA)
                cv2.putText(mask_vis, tip_label, (tx, ty), font, 0.45, (0,255,255), 1, cv2.LINE_AA)

            cv2.imshow("Mask", mask_vis)

            # Place the mask window once, AFTER it’s visible
            if not placed_mask:
                _apply_window_pos("Mask", WINDOW_MASK_POS, "mask")
                placed_mask = True
        # ...existing code...

        key = cv2.waitKey(1) & 0xFF
        ch = tkw.poll_char()
        if key == ord('q') or ch in ('q', 'Q'):
            sys.stdout.write("\n")
            sys.stdout.flush()
            break
        elif key == ord('m'):
            show_mask = not show_mask
            if show_mask:
                try:
                    cv2.namedWindow("Mask", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow("Mask", mask_w, mask_h)
                    placed_mask = False
                except Exception:
                    pass
                sys.stdout.write("\n[MASK] ON\n")
            else:
                try:
                    cv2.destroyWindow("Mask")
                except Exception:
                    pass
                sys.stdout.write("\n[MASK] OFF\n")
            sys.stdout.flush()
        elif key == ord('r'):
            _apply_window_pos(window_name, WINDOW_TRACK_POS, "track")
            if show_mask:
                _apply_window_pos("Mask", WINDOW_MASK_POS, "mask")
            sys.stdout.write("\n[WINPOS] Reset applied.\n")
            sys.stdout.flush()
        elif key == ord('c'):
            if cursor_point is None:
                sx, sy = frame.shape[1] // 2, frame.shape[0] // 2
            else:
                sx, sy = cursor_point
            roi_size = 60  # 60x60 calibration ROI (reference only)
            x1, y1, x2, y2 = roi_rect_around(sx, sy, roi_size, frame.shape[1], frame.shape[0])
            roi_bgr = raw_frame[y1:y2, x1:x2].copy()
            if roi_bgr.size > 0:
                sample_rel = (sx - x1, sy - y1)
                save_calibration(roi_bgr, sample_rel)
                calibrated_img = roi_bgr
                calib_sample_point = sample_rel
                calibrated = True
                stable_frames = 0
                ball_locked = False
                # Status line using fixed ranges
                print_status_in_place(cursor_point, calib_hsv_median, get_fixed_hsv_ranges(), False, None, None, roi_hsv=None)
        elif key == ord('s'):
            if cursor_point is not None:
                sx, sy = cursor_point
                hsv_px = hsv[sy, sx]
                sampled_hsv = (int(hsv_px[0]), int(hsv_px[1]), int(hsv_px[2]))

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MT Orange/Red Ball Tracking (fixed HSV thresholds)")
    parser.add_argument("--camera", type=int, default=0, help="camera index")
    args = parser.parse_args()
    main(camera_index=args.camera)
