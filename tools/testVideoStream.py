#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: testVideoStream.py
Project: Freenove Robot Dog — Stream Utilities (Standalone + In‑App Debug)
Purpose:
  This module now provides two complementary tools:
    1) A standalone, dependable OpenCV viewer (main()) for validating the Pi stream.
    2) A reusable PyQt DebugStreamWindow for in‑app debugging inside MainMT.py.

Transport protocol (strict):
  - Pi sends JPEG frames as: <len><jpeg>
      • len = 4‑byte little‑endian unsigned integer (struct '<I')
      • Client tries '<I' first; if out of range, falls back to '<Q' (8‑byte) to handle legacy images
  - Command/telemetry channel (port 5001) sends text lines NAME#payload (e.g., CMD_POWER#7.9)

Design and constraints (per project instructions):
  - Do NOT use struct.pack('L') — it’s platform‑dependent and breaks on macOS.
  - Do NOT use makefile('rb') / file.read(n) — always recv exact bytes (see recvall).
  - GUI mode must never call cv2.imshow() from the Qt thread; this file only uses cv2.imshow()
    in the standalone sanity viewer (when run as __main__).
  - When embedded in MainMT, only use DebugStreamWindow (PyQt + QLabel + QTimer).

Exported API for MainMT.py:
  - draw_top_bar(frame, fps, battery_v, distance_cm, state_text, state_since) -> None
  - class DebugStreamWindow(QMainWindow): safe in‑app viewer that:
      • copies Client.image under Client.image_lock
      • sets client.video_flag = True after consuming (producer/consumer handshake)
      • uses QImage(...).copy() to avoid dangling memory
      • renders independently of the main panel via its own QTimer
  - Module constants HOST/PORT are used only for overlay text; MainMT sets them on open.

Operational tips:
  - Server usually allows one client per port; do not run the standalone viewer while the main GUI
    is connected. The in‑app DebugStreamWindow avoids extra sockets by reusing the shared buffer.
  - If the standalone viewer shows video but the GUI does not, the issue is in the Qt paint path.
  - If both fail, inspect length parsing and network reachability.

Usage (standalone sanity check, macOS zsh):
  - python3 testVideoStream.py          # opens a cv2 window “Pi stream”
  - Quit with q or ESC

Version: 1.0.0
Last Modified: 2025-11-13
Maintainer: MT
Contributors: ChatGPT (GitHub Copilot)

Revision History:
  1.0.0  2025-11-13  Merged PyQt DebugStreamWindow for in‑app use; clarified exported API and
                      one‑client‑per‑port rule. Expanded header and maintenance comments.
  0.9.0  2025-11-13  Documentation refresh: protocol, safety notes, integration guidance.
  0.8.x  2025-11-12  Reconnect logic, SOI checks, graceful shutdown, overlay improvements.
  0.1.x  2025-11-12  Initial minimal standalone viewer.

"""

import socket
import struct
import numpy as np
import cv2
import time
import threading  # for Lock, Thread, Event

# ---------------- Configuration ----------------

HOST, PORT = "192.168.0.32", 8001      # Pi video socket
TELEM_PORT = 5001                      # Pi telemetry socket
TIMEOUT = 10                           # socket timeout (s)
MAX_FRAME = 5_000_000                  # discard frames >5MB (safety)
NO_DATA_TIMEOUT = 5.0                  # if no new frame for this long, reconnect
CONNECT_ATTEMPTS = 15                  # attempts before giving up
RETRY_DELAY = 1.0                      # seconds between connect attempts

TELEMETRY_POLL = True                  # if server doesn't push values, poll
# Per-metric polling plan (cmd -> interval seconds)
POLL_PLAN = {
    b"CMD_SONIC#\n": 0.2,      # ~5 Hz distance
    b"CMD_DISTANCE#\n": 0.2,
    b"CMD_POWER#\n": 1.0,      # ~1 Hz battery
    b"CMD_VOLT#\n": 1.0,
    b"CMD_STATE#\n": 0.5,      # ~2 Hz state
    b"CMD_MODE#\n": 0.5,
}

# Shared telemetry updated by worker thread
telemetry = {
    "battery_v": None,
    "distance_cm": None,
    "state": "Resting",
    "state_since": time.time(),
}
telemetry_lock = threading.Lock()

# ---------------- Styling ----------------

# Colors (BGR)
COLOR_IP = (0, 140, 255)         # Orange-ish
COLOR_DIST = (255, 0, 0)         # Blue
COLOR_BATT = (0, 165, 255)       # Orange
COLOR_FPS = (0, 230, 0)          # Green
COLOR_CENTER_BG = (200, 220, 255)  # Unused if alpha=0; kept for easy tweaks
COLOR_CENTER_TEXT = (255, 255, 255)
COLOR_OUTLINE = (0, 0, 0)

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE_SMALL_BASE = 0.62
FONT_SCALE_CENTER_BASE = 0.70
THICK = 2
OUTLINE_THICK_EXTRA = 2

MARGIN_X = 10
MARGIN_Y = 8
GAP = 14
LINE_GAP_Y = 6
CENTER_BADGE_ALPHA = 0.0         # fully transparent background for center text

# ---------------- Utility helpers ----------------

def make_warning_image(msg: str, sub: str = "", size=(640, 120)):
    """
    Build a simple warning banner image with outlined text.
    Useful before a frame stream exists.
    """
    W, H = size
    img = np.zeros((H, W, 3), dtype=np.uint8)
    # Title
    cv2.putText(img, msg, (16, 50), FONT, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, msg, (16, 50), FONT, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    # Subtitle
    if sub:
        cv2.putText(img, sub, (16, 90), FONT, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, sub, (16, 90), FONT, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return img

def show_warning_window(title: str, msg: str, sub: str = ""):
    """
    Display or update a small warning window.
    """
    img = make_warning_image(msg, sub)
    cv2.imshow(title, img)
    cv2.waitKey(1)

def recvall(sock, n: int) -> bytearray:
    """
    Receive exactly n bytes from the socket using memoryview for efficiency.
    Raises ConnectionError if the peer closes early.
    """
    buf = bytearray(n)
    mv = memoryview(buf)
    got = 0
    while got < n:
        r = sock.recv_into(mv[got:], n - got)
        if r == 0:
            raise ConnectionError("Socket closed while receiving data")
        got += r
    return buf

def read_len(sock) -> int:
    """
    Read the frame length field.
    Try 4-byte little-endian first (<I), then fallback to 8-byte (<Q).
    """
    hdr4 = recvall(sock, 4)
    n32 = struct.unpack('<I', hdr4)[0]
    if 0 < n32 <= MAX_FRAME:
        return n32
    hdr8 = hdr4 + recvall(sock, 4)
    n64 = struct.unpack('<Q', hdr8)[0]
    if 0 < n64 <= MAX_FRAME:
        return n64
    raise ValueError(f"Invalid frame length (32={n32}, 64={n64})")

def _parse_telem_line(txt: str):
    """
    Parse telemetry lines like:
      CMD_POWER#7.9
      DIST#12.3
      STATE#Resting
    Updates globals if recognized; ignore unknown.
    """
    if not txt or '#' not in txt:
        return
    name, payload = txt.split('#', 1)
    key = name.upper().strip()
    if key.startswith('CMD_'):
        key = key[4:]
    try:
        if key in ('POWER', 'BATTERY', 'VOLT'):
            val = float(payload)
            with telemetry_lock:
                telemetry['battery_v'] = val
        elif key in ('SONIC', 'DIST', 'DISTANCE', 'ULTRASONIC'):
            val = float(payload)
            with telemetry_lock:
                telemetry['distance_cm'] = val
        elif key in ('STATE', 'MODE', 'ACTION', 'POSTURE'):
            state = payload.strip() or "Resting"
            now = time.time()
            with telemetry_lock:
                if telemetry['state'] != state:
                    telemetry['state'] = state
                    telemetry['state_since'] = now
    except Exception:
        pass

def telemetry_worker(host: str, port: int, stop_event: threading.Event):
    """
    Background thread:
      - Connects to telemetry port (5001)
      - Reads lines and updates telemetry
      - Polls selected metrics at different rates (best effort)
    """
    while not stop_event.is_set():
        sock = socket.socket()
        sock.settimeout(1.0)
        buf = b""
        last_poll = {cmd: 0.0 for cmd in POLL_PLAN}
        try:
            sock.connect((host, port))
            while not stop_event.is_set():
                # Read (non-blocking feel via short timeout)
                try:
                    data = sock.recv(1024)
                    if not data:
                        break
                    buf += data
                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        txt = line.decode('utf-8', errors='ignore').strip()
                        _parse_telem_line(txt)
                except socket.timeout:
                    pass
                # Poll periodically if enabled
                if TELEMETRY_POLL:
                    now = time.time()
                    for cmd, interval in POLL_PLAN.items():
                        if now - last_poll[cmd] >= interval:
                            try:
                                sock.sendall(cmd)
                                last_poll[cmd] = now
                            except Exception:
                                raise
        except Exception:
            time.sleep(1.0)
        finally:
            try:
                sock.close()
            except Exception:
                pass

def safe_connect_with_feedback(host, port) -> socket.socket:
    """
    Connect with retries and visible feedback.
    Shows warnings if the port is busy (only one client allowed) or if server is down.

    NOTE: Do not close the socket on success; only close when a connect attempt fails.
    """
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        s = socket.socket()
        s.settimeout(TIMEOUT)
        try:
            s.connect((host, port))
        except ConnectionRefusedError:
            # Likely: server not started or already serving another client (one-client limit).
            msg = f"Cannot connect to {host}:{port}"
            sub = "Port busy or server not listening. Close iOS app and restart server."
            show_warning_window("Pi stream", msg, sub + f"  Retry {attempt}/{CONNECT_ATTEMPTS}...")
            try:
                s.close()
            except Exception:
                pass
            time.sleep(RETRY_DELAY)
            continue
        except (TimeoutError, socket.timeout):
            msg = f"{host}:{port} not responding"
            sub = "Network delay or server stalled. Retrying..."
            show_warning_window("Pi stream", msg, sub + f"  Retry {attempt}/{CONNECT_ATTEMPTS}...")
            try:
                s.close()
            except Exception:
                pass
            time.sleep(RETRY_DELAY)
            continue
        except OSError as e:
            msg = f"Socket error: {getattr(e, 'errno', '')}"
            show_warning_window("Pi stream", msg, "Retrying...")
            try:
                s.close()
            except Exception:
                pass
            time.sleep(RETRY_DELAY)
            continue

        # Success: return the connected socket (still open)
        return s

    raise ConnectionError(f"Failed to connect to {host}:{port} after {CONNECT_ATTEMPTS} attempts")

def put_text_outlined(img, text, org, font, scale, color, thick, line_type=cv2.LINE_AA):
    """
    Draw text with a black outline underlay for readability on any background.
    """
    outline_thick = max(1, thick + OUTLINE_THICK_EXTRA)
    cv2.putText(img, text, org, font, scale, COLOR_OUTLINE, outline_thick, line_type)
    cv2.putText(img, text, org, font, scale, color, thick, line_type)

def draw_center_badge(img, text, origin_xy, font, scale, thick, bg_color, fg_color, alpha):
    """
    Center text renderer.
    If alpha==0, draws text only (transparent background). Otherwise blends a rounded-ish rect.
    """
    (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
    pad_x, pad_y = 12, 6
    x, y = origin_xy
    rect = (x - pad_x, y - th - pad_y, x + tw + pad_x, y + pad_y)
    if alpha > 0:
        overlay = img.copy()
        cv2.rectangle(overlay, (rect[0], rect[1]), (rect[2], rect[3]), bg_color, -1)
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    put_text_outlined(img, text, (x, y), font, scale, fg_color, THICK)

def draw_top_bar(frame, fps, battery_v, distance_cm, state_text, state_since):
    """
    iOS-style top area with auto-fit and optional wrap:
      Left:  IP:PORT
      Right: <dist>cm  <volt>V  <fps>fps
      Center: <L>s  <State>  <R>s   (moves to second line if space is tight)
    """
    h, w = frame.shape[:2]

    # Build strings
    elapsed = int(max(0, time.time() - (state_since or time.time())))
    distance_str = f"{(distance_cm if distance_cm is not None else 0.0):.1f}cm"
    battery_str = f"{(battery_v if battery_v is not None else 0.0):.2f}V"
    fps_str = f"{fps:0.2f}fps"
    ip_text = f"{HOST}:{PORT}"
    center_text = f"{elapsed}s  {state_text}  {elapsed}s"

    # Start scales, shrink until things fit on one line; otherwise wrap center text to a second line
    scale_small = FONT_SCALE_SMALL_BASE
    scale_center = FONT_SCALE_CENTER_BASE
    min_small, min_center = 0.48, 0.56

    def measure(scale_small, scale_center):
        (ip_w, ip_h), _ = cv2.getTextSize(ip_text, FONT, scale_small, THICK)
        (center_w, center_h), _ = cv2.getTextSize(center_text, FONT, scale_center, THICK)
        (dist_w, dist_h), _ = cv2.getTextSize(distance_str, FONT, scale_small, THICK)
        (batt_w, batt_h), _ = cv2.getTextSize(battery_str, FONT, scale_small, THICK)
        (fps_w, fps_h), _ = cv2.getTextSize(fps_str, FONT, scale_small, THICK)
        right_w = dist_w + batt_w + fps_w + 2 * GAP
        return (ip_w, ip_h, center_w, center_h, right_w)

    ip_w, ip_h, center_w, center_h, right_w = measure(scale_small, scale_center)

    def fits_one_line(center_w, ip_w, right_w):
        left_end = MARGIN_X + ip_w
        right_start = w - MARGIN_X - right_w
        avail = right_start - left_end - MARGIN_X
        return center_w <= max(0, avail)

    tries = 0
    while not fits_one_line(center_w, ip_w, right_w) and (scale_small > min_small or scale_center > min_center):
        if scale_small > min_small:
            scale_small -= 0.04
        if scale_center > min_center:
            scale_center -= 0.04
        ip_w, ip_h, center_w, center_h, right_w = measure(scale_small, scale_center)
        tries += 1
        if tries > 20:
            break

    one_line = fits_one_line(center_w, ip_w, right_w)

    # Baselines
    top_y = MARGIN_Y + ip_h
    second_line_y = top_y + center_h + LINE_GAP_Y

    # LEFT
    put_text_outlined(frame, ip_text, (MARGIN_X, top_y), FONT, scale_small, COLOR_IP, THICK)

    # RIGHT (aligned to right margin)
    x_cursor = w - MARGIN_X - right_w
    put_text_outlined(frame, distance_str, (x_cursor, top_y), FONT, scale_small, COLOR_DIST, THICK)
    (dist_w, _), _ = cv2.getTextSize(distance_str, FONT, scale_small, THICK)
    x_cursor += dist_w + GAP
    put_text_outlined(frame, battery_str, (x_cursor, top_y), FONT, scale_small, COLOR_BATT, THICK)
    (batt_w, _), _ = cv2.getTextSize(battery_str, FONT, scale_small, THICK)
    x_cursor += batt_w + GAP
    put_text_outlined(frame, fps_str, (x_cursor, top_y), FONT, scale_small, COLOR_FPS, THICK)

    # CENTER (badge is transparent; we still use helper to keep consistent padding/placement)
    if one_line:
        left_end = MARGIN_X + ip_w
        right_start = w - MARGIN_X - right_w
        center_x = (left_end + right_start - center_w) // 2
        center_org = (int(center_x + 12), int(top_y))
    else:
        center_x = (w - center_w) // 2
        center_org = (int(center_x + 12), int(second_line_y))
    draw_center_badge(frame, center_text, center_org, FONT, scale_center, THICK,
                      COLOR_CENTER_BG, COLOR_CENTER_TEXT, CENTER_BADGE_ALPHA)

# ---------------- Main loop ----------------

def main():
    # Start telemetry thread (retries internally)
    stop_event = threading.Event()
    t = threading.Thread(target=telemetry_worker, args=(HOST, TELEM_PORT, stop_event), daemon=True)
    t.start()

    # Outer reconnect loop: tries to keep video alive
    should_quit = False
    while not should_quit:
        s = safe_connect_with_feedback(HOST, PORT)
        s.settimeout(2.0)  # short ops timeout to detect stalls faster

        prev = time.time()
        fps = 0.0
        last_frame_time = time.time()
        bad_jpeg = 0  # counts consecutive decode failures (to trigger reconnect)

        try:
            while True:
                # If no frames for a while, warn and reconnect
                if time.time() - last_frame_time > NO_DATA_TIMEOUT:
                    show_warning_window("Pi stream",
                        "No video frames received",
                        "Port busy or server stalled. Reconnecting...")
                    break

                # Read one frame length and payload
                ln = read_len(s)
                jpg = recvall(s, ln)

                # Optional sanity: JPEG should start with SOI marker 0xFFD8
                if not (len(jpg) >= 2 and jpg[0] == 0xFF and jpg[1] == 0xD8):
                    bad_jpeg += 1
                    if bad_jpeg >= 3:
                        # Probably desynced: warn and reconnect
                        show_warning_window("Pi stream",
                            "Corrupted video frame(s)",
                            "Resyncing connection...")
                        break
                    continue

                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    bad_jpeg += 1
                    if bad_jpeg >= 3:
                        show_warning_window("Pi stream",
                            "Decoder failed repeatedly",
                            "Resyncing connection...")
                        break
                    continue
                bad_jpeg = 0  # reset on success

                # FPS smoothing
                now = time.time()
                dt = now - prev
                prev = now
                last_frame_time = now
                if dt > 1e-6:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt)

                # Snapshot current telemetry (single lock for consistency)
                with telemetry_lock:
                    bv = telemetry['battery_v']
                    dc = telemetry['distance_cm']
                    state = telemetry['state']
                    state_since = telemetry['state_since']

                # Draw iOS-style top bar overlay
                draw_top_bar(frame, fps=fps, battery_v=bv, distance_cm=dc,
                             state_text=state, state_since=state_since)

                cv2.imshow("Pi stream", frame)
                k = cv2.waitKey(1) & 0xFF
                if k in (27, ord('q')):
                    should_quit = True
                    break
        except (ConnectionError, socket.timeout, OSError, ValueError):
            # Any stream error falls through to reconnect
            show_warning_window("Pi stream", "Video connection lost", "Reconnecting...")
        finally:
            try:
                s.close()
            except Exception:
                pass

    # Clean shutdown: stop telemetry worker and close windows
    stop_event.set()
    # Give the thread a brief moment to exit; since it's daemon=True, join is optional
    try:
        t.join(timeout=0.5)
    except Exception:
        pass
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    finally:
        cv2.destroyAllWindows()

# --- Optional PyQt debug window (for in-app use) ---------------------------------------
# The main GUI imports this class and uses it to render video/telemetry in a separate
# window when the primary QLabel pipeline stalls. Standalone cv2 viewer remains unchanged.
try:
    from PyQt5.QtCore import QTimer, Qt
    from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
    from PyQt5.QtGui import QImage, QPixmap
    _QT_AVAILABLE = True
except Exception:
    _QT_AVAILABLE = False

if _QT_AVAILABLE:
    class DebugStreamWindow(QMainWindow):
        """
        Debug video/telemetry viewer for in-app use (PyQt).
        - Reads the shared Client.image buffer under lock (no new sockets).
        - Marks client.video_flag = True after copying so the producer continues.
        - Uses this module's draw_top_bar() (proven overlay).
        - Runs its own QTimer (~30 fps), independent of the main window.
        """
        def __init__(self, client, telemetry_provider, ip: str, port: int = 8001):
            super().__init__()
            self.setWindowTitle("Debug Stream (trial)")
            self.resize(720, 480)

            # Align overlay's left label with the active target
            global HOST, PORT
            HOST = ip or HOST
            PORT = port

            self.client = client
            self.telemetry_provider = telemetry_provider  # callable -> (battery_v, distance_cm, state, since)

            central = QWidget(self)
            self.setCentralWidget(central)
            lay = QVBoxLayout(central)
            self.label = QLabel("Waiting…", alignment=Qt.AlignCenter)
            self.label.setMinimumSize(320, 240)
            self.label.setStyleSheet("background:#111; color:#aaa;")
            lay.addWidget(self.label)

            # FPS based on producer timestamps when available
            self._fps = 0.0
            self._prev_ts = time.time()
            self._producer_ts_prev = 0.0
            self._last_frame_time = 0.0

            self.timer = QTimer(self)
            self.timer.setInterval(33)  # ~30 fps
            self.timer.timeout.connect(self._tick)
            self.timer.start()

        def _tick(self):
            # Copy latest frame; mark consumed so producer keeps flowing even if main UI is blocked
            base = None
            prod_ts = getattr(self.client, 'video_last_frame_ts', 0.0)
            with self.client.image_lock:
                if isinstance(self.client.image, np.ndarray) and self.client.image.size > 0:
                    base = self.client.image.copy()
                    self.client.video_flag = True  # handshake: consumed

            if base is None:
                # Placeholder before first frame
                h, w = 240, 320
                frame = np.zeros((h, w, 3), dtype=np.uint8)
                frame[:] = (32, 32, 32)
            else:
                # Smooth FPS when producer timestamp advances
                if prod_ts and prod_ts != self._producer_ts_prev:
                    now = time.time()
                    dt = now - self._prev_ts
                    self._prev_ts = now
                    if dt > 1e-6:
                        self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt)
                    self._last_frame_time = now
                    self._producer_ts_prev = prod_ts
                frame = base

            # Telemetry snapshot
            bv, dc, state, since = self.telemetry_provider()
            draw_top_bar(frame, fps=self._fps, battery_v=bv, distance_cm=dc,
                         state_text=state, state_since=since)

            # Blit (Qt must own memory → .copy())
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg).scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(pix)

        def closeEvent(self, e):
            try:
                self.timer.stop()
            finally:
                super().closeEvent(e)
else:
    # Fallback stub to keep imports safe in environments without PyQt5
    class DebugStreamWindow(object):
        def __init__(self, *a, **k):
            raise ImportError("PyQt5 is required for DebugStreamWindow; standalone viewer still works.")
# --- end PyQt debug window --------------------------------------------------------------
