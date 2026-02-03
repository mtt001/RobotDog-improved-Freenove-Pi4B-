# -*- coding: utf-8 -*-
"""
Application: Freenove Robot Dog Client (PyQt5)
Authors   : MT & GitHub Copilot
Summary   : Desktop client UI to control the Freenove Robot Dog, stream video, and run features.
Filename: Main.py      (used to be "MainMT.py", The original code is renamed "Main_Freenove.py".)
Architecture snapshot (client-side):
  - Two TCP channels to the Pi
      • 5001 "command/telemetry": text lines "CMD_*#value"
      • 8001 "video": binary stream "<len><jpeg>" where len is 4‑byte little‑endian unsigned (<I).
  - Networking lives in Client.py threads. They write the latest decoded BGR frame to Client.image
    under Client.image_lock and signal readiness via Client.video_flag (False = new frame ready).
  - GUI (this file) never blocks on sockets. It uses QTimer to:
      • refresh and paint frames on a QLabel (refresh_image)
      • poll power and sonic distance
      • print a debug heartbeat (optional)
  - Rendering pipeline rules (must be preserved):
      • Always copy the numpy frame under image_lock before drawing overlays
      • Convert BGR→RGB then QImage(..., stride=rgb.strides[0]).copy() before setPixmap
      • Toggle Client.video_flag = True after consuming a frame

What’s new in this revision line:
  - In‑app debug viewer: imports DebugStreamWindow from testVideoStream.py (press T to open).
    It reads the shared frame buffer (no extra sockets) and uses the proven overlay from
    testVideoStream. This isolates any QLabel pipeline issues in the main window.
  - Overlay: compact, outlined top bar with IP/port, elapsed/state, distance, voltage, FPS.
    A small “stalled X.Xs” badge appears if no producer frame arrives for >2s.
  - Safer QImage handling (.copy()) and explicit stride usage to avoid Qt memory aliasing.
  - GUI never paints placeholders over valid frames; last good frame is kept during hiccups.

Maintenance quick map:
  Threads started in connect():
    - self.video_thread       -> Client.receiving_video (port 8001)
    - self.instruction_thread -> self.receive_instruction (port 5001)
  Timers:
    - self.timer        -> refresh_image (GUI paint loop)
    - self.timer_power  -> power()
    - self.timer_sonic  -> getSonicData()
    - self.debug_timer  -> _debug_tick() (optional CLI heartbeat)
    - self.overlay_timer-> _overlay_refresh_if_stalled() (keeps telemetry overlay live)
  Shared state with Client.py:
    - self.client.image              (numpy BGR)
    - self.client.image_lock         (threading.Lock)
    - self.client.video_flag         (False=new frame ready; set True after consume)
    - self.client.video_last_frame_ts (producer timestamp, used for FPS)
    - frames_produced / frames_displayed (diagnostics; see _debug_tick)

Coding conventions (enforced here and in Client.py):
  - Never use struct.pack('L'); server and client must use struct '<I' for frame length.
  - Never block the Qt main thread (no long sleeps, no socket reads).
  - Always copy and draw overlays on a working frame, not on the shared buffer.

 === COPILOT SAFE MODE ====================
    Before making ANY modification:
    1. Create a backup copy of this file (filename_backup.py).
    2. NEVER delete or rewrite existing functions unless explicitly instructed.
    3. ONLY add code or modify small blocks with clear comments.
 ==========================================

Revision History: # Reminder to Copilot : Keep revision history and rich comments .
- 1.20 (2025-11-15): UI tweak — add a visible “DebugWin” button placed above “Close Video” for quick access.
- (2025-11-15) renamed the "MainMT.py" back to "Main.py".  The original Freenove code is saved as "Main_Freenove.py".
- 1.19 (2025-11-13): Integrate testVideoStream.DebugStreamWindow (press T to open).
                     Clarify thread/timer map; add richer file header and comments.
- 1.18 (2025-11-13): Shrink status bar; add GUI heartbeat; continuous placeholder updates.
- 1.17 (2025-11-12): Correct QImage stride; redraw placeholder per tick before first frame.
- 1.16 (2025-11-12): Auto‑start video after connect; draw status on placeholder.
- 1.15 (2025-11-12): Add iOS‑style status bar; safer connect flow and UX.
- 1.00: Port of original Main.py (Freenove).

"""
__version__ = "1.20 (2025-11-15)"
# =======================================================================================
# Imports:
#  - Wildcard imports (from Client import *) can obscure origin of names; kept for compatibility.
#  - Consider replacing with explicit imports (e.g., from Client import Client, cmd) in a future cleanup.

from ui_led import Ui_led
from ui_face import Ui_Face
from ui_client import Ui_client
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPainter, QPen, QColor, QKeySequence, QBrush
from PyQt5.QtWidgets import QShortcut
from Calibration import *
import sys, time, threading, cv2, numpy as np
import socket, re
import testVideoStream as tv
from testVideoStream import DebugStreamWindow
from Thread import stop_thread                 # for graceful cleanup (still unsafe, but resolves NameError)
from controllers.dog_command_controller import COMMAND as cmd  # make 'cmd' explicit (avoid Pylance unresolved reference)

import Client as ClientModule                  # module
from Client import Client as ClientClass       # class

print("Main is using Client module at:", ClientModule.__file__)
# ---------------------------------------------------------------------------------------
# Overlay helpers (Main window reuses tv.draw_top_bar for consistency)
# ---------------------------------------------------------------------------------------

class MyWindow(QMainWindow,Ui_client):
    def __init__(self):
        super(MyWindow,self).__init__()
        # UI setup
        self.setupUi(self)
        self.setWindowIcon(QIcon('Picture/logo_Mini.png'))

        # Focus and key capturing
        self.setFocusPolicy(Qt.StrongFocus)
        if hasattr(self, "centralwidget") and self.centralwidget is not None:
            self.centralwidget.setFocusPolicy(Qt.StrongFocus)
        QApplication.instance().installEventFilter(self)

        # Video label
        self.Video.setScaledContents(False)
        self.Video.setAlignment(Qt.AlignCenter)
        self.Video.setStyleSheet("background:#111;")

        # Startup art and placeholder
        self._startup_pix = QPixmap('Picture/dog_client.png')
        self._showing_startup_art = False
        self._set_startup_art()
        self._draw_status_placeholder("Disconnected", (0,0,255))

        # Keyboard shortcuts (plus robust eventFilter below)
        for k in ('T','t'):
            sc = QShortcut(QKeySequence(k), self); sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(self.showDebugStreamWindow)
        self._sc_dbg = QShortcut(QKeySequence('F10'), self)
        self._sc_dbg.setContext(Qt.ApplicationShortcut)
        self._sc_dbg.activated.connect(self.showDebugStreamWindow)
    
        # Visible fallback button: place above the Video button for easier access
        # Button_Video geometry in `ui_client.py` is QRect(155, 380, 90, 30)
        # so place DebugWin directly above it at y=350
        self.Button_DebugWin = QPushButton("DebugWin", self)
        self.Button_DebugWin.setGeometry(155, 350, 90, 24)
        self.Button_DebugWin.clicked.connect(self.showDebugStreamWindow)

        # Diagnostics
        self._fps = 0.0
        self._prev_frame_ts = time.time()
        self._producer_ts_prev = 0.0
        self.last_frame_time = 0.0
        self._last_frame_bgr = None

        # Key state
        self.Key_W=self.Key_A=self.Key_S=False
        self.Key_D=self.Key_Q=self.Key_E=False
        self.Key_Space=False

        # Client + speed
        self.client=ClientClass()
        self.client.move_speed=str(self.slider_speed.value())

        # IP persistence
        try:
            with open('IP.txt', 'r') as f:
                self.lineEdit_IP_Adress.setText(f.readline().strip())
        except FileNotFoundError:
            self.lineEdit_IP_Adress.setText("")

        # Power bar
        self.progress_Power.setRange(0,100)
        self.progress_Power.setValue(90)

        # Telemetry for overlay
        self.tele_batt_v = None
        self.tele_dist_cm = None
        self.state_text = "Resting"
        self.state_since = time.time()      # timestamp of last state change

        # Buttons
        self.Button_Connect.clicked.connect(self.connect)
        self.Button_Video.clicked.connect(self.video)
        self.Button_Ball_And_Face.clicked.connect(self.chase_ball_and_find_face)
        self.Button_IMU.clicked.connect(self.imu)
        self.Button_Calibration.clicked.connect(self.showCalibrationWindow)
        self.Button_LED.clicked.connect(self.showLedWindow)
        self.Button_Sonic.clicked.connect(self.sonic)   # sonic button
        self.Button_Relax.clicked.connect(self.relax)
        self.Button_Face_ID.clicked.connect(self.showFaceWindow)

        # Movement press/release
        self.Button_ForWard.pressed.connect(self.forward);   self.Button_ForWard.released.connect(self.stop)
        self.Button_BackWard.pressed.connect(self.backward); self.Button_BackWard.released.connect(self.stop)
        self.Button_Left.pressed.connect(self.left);         self.Button_Left.released.connect(self.stop)
        self.Button_Right.pressed.connect(self.right);       self.Button_Right.released.connect(self.stop)
        self.Button_Step_Left.pressed.connect(self.step_left);  self.Button_Step_Left.released.connect(self.stop)
        self.Button_Step_Right.pressed.connect(self.step_right); self.Button_Step_Right.released.connect(self.stop)
        self.Button_Buzzer.pressed.connect(self.buzzer);     self.Button_Buzzer.released.connect(self.buzzer)

        # Sliders
        self.slider_head.setRange(50,180); self.slider_head.setValue(90); self.slider_head.valueChanged.connect(self.head)
        self.slider_horizon.setRange(-20,20); self.slider_horizon.setValue(0); self.slider_horizon.valueChanged.connect(self.horizon)
        self.slider_height.setRange(-20,20); self.slider_height.setValue(0); self.slider_height.valueChanged.connect(self.height)

        self.slider_pitch.setRange(-20,20); self.slider_pitch.setValue(0); self.slider_pitch.valueChanged.connect(lambda:self.attitude(self.label_pitch,self.slider_pitch))
        self.slider_yaw.setRange(-20,20); self.slider_yaw.setValue(0); self.slider_yaw.valueChanged.connect(lambda:self.attitude(self.label_yaw,self.slider_yaw))
        self.slider_roll.setRange(-20,20); self.slider_roll.setValue(0); self.slider_roll.valueChanged.connect(lambda:self.attitude(self.label_roll,self.slider_roll))

        self.slider_speed.setRange(2,10); self.slider_speed.setValue(8); self.slider_speed.valueChanged.connect(self.speed)

        # Timers
        self.timer=QTimer(self);        self.timer.timeout.connect(self.refresh_image)
        self.timer_power = QTimer(self); self.timer_power.timeout.connect(self.power)       # power timer
        self.timer_sonic = QTimer(self); self.timer_sonic.timeout.connect(self.getSonicData)

        # Attitude view
        self.drawpoint=[585,135]
        self.initial=True

        # Connect state
        self.IP = ""
        self.Button_Video.setEnabled(False)

        # Overlay keep-alive
        self.overlay_timer = QTimer(self)
        self.overlay_timer.setInterval(500)
        self.overlay_timer.timeout.connect(self._overlay_refresh_if_stalled)

        # RX debug gate (OFF by default per your request)
        self.debug_rx_enabled = False
        # UI/flow debug gate (OFF by default). Set True to see [DEBUG] prints.
        self.debug_ui_enabled = False

        self._dbg_win = None

    def _dbg(self, msg: str):
        """Print only when UI debug is enabled."""
        if getattr(self, "debug_ui_enabled", False):
            print(msg)

    # Robust 'T' detection (works across IMEs/layouts)
    def _is_T_key(self, event):
        try:
            k = event.key()
            txt = event.text()
            native_vk = event.nativeVirtualKey() if hasattr(event,'nativeVirtualKey') else None
            native_scan = event.nativeScanCode() if hasattr(event,'nativeScanCode') else None
            if k == Qt.Key_T: return True
            if txt and txt.lower() == 't': return True
            if (k & 0xFF) in (ord('t'), ord('T')): return True
            if native_vk in (ord('t'), ord('T')): return True
            if native_scan in (17,): return True  # heuristic
            return False
        except Exception:
            return False

    # Global key filter
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            # Debug logging accesses self.debug_rx_enabled without thread safety
            if getattr(self, "debug_rx_enabled", False):
                print(f"[DEBUG][Keys] ...")  # Potential race if changed during runtime
            if self._is_T_key(event):
                self._dbg("[DEBUG][T] detected -> open debug window")
                self.showDebugStreamWindow()
                return True
        return super().eventFilter(obj, event)

    def _draw_status_placeholder(self, status_text: str, bgr_color=(0,0,255)):
        try:
            h, w = 240, 320
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            # Use requested background color (BGR)
            frame[:] = tuple(int(c) for c in bgr_color)
            # Reuse tested top bar from tv
            tv.draw_top_bar(frame, fps=0.0, battery_v=0.0, distance_cm=0.0,
                            state_text=status_text, state_since=time.time())
            self._blit_to_label(frame)
        except Exception as e:
            print(f"[DEBUG][GUI] status_placeholder error: {e}")

    # ==== position the Debug Stream window to the left of the main window ===
    def showDebugStreamWindow(self):
        try:
            self._dbg("[DEBUG][T] showDebugStreamWindow()")
            if getattr(self, "_dbg_win", None) is None:
                self._dbg_win = tv.DebugStreamWindow(
                    self.client,
                    lambda: (self.tele_batt_v, self.tele_dist_cm, self.state_text, self.state_since),
                    self.IP
                )
                self._dbg("[DEBUG][T] DebugStreamWindow created")
            
            # Position the debug window to the left of the main window
            main_geo = self.geometry()
            debug_width = self._dbg_win.width() if self._dbg_win.width() > 0 else 400
            debug_height = self._dbg_win.height() if self._dbg_win.height() > 0 else 300
            
            # Place debug window to the left of main window with a small gap
            gap = 10
            new_x = main_geo.x() - debug_width - gap
            new_y = main_geo.y()
            
            # Ensure the window stays on screen
            if new_x < 0:
                new_x = gap  # If not enough space on left, place at left edge of screen
            
            self._dbg_win.setGeometry(new_x, new_y, debug_width, debug_height)
            
            self._dbg_win.show(); self._dbg_win.raise_(); self._dbg_win.activateWindow()
            self._dbg("[DEBUG][T] DebugStreamWindow visible")
        except Exception as e:
            print(f"[WARN][T] Debug window open failed: {e}")    

    def keyPressEvent(self, event):
        try:
            if self._is_T_key(event):
                self._dbg("[DEBUG][T] keyPressEvent -> open debug window")
                self.showDebugStreamWindow()
                return
            if(event.key() == Qt.Key_C): self.connect()
            if(event.key() == Qt.Key_V): self.video(); return
            if(event.key() == Qt.Key_R): self.relax()
            if(event.key() == Qt.Key_L): self.showLedWindow()
            if(event.key() == Qt.Key_Space): self.stop()
            if(event.key() == Qt.Key_W) and (self.Key_W==False): self.Key_W=True; self.forward()
            if(event.key() == Qt.Key_S) and (self.Key_S==False): self.Key_S=True; self.backward()
            if(event.key() == Qt.Key_A) and (self.Key_A==False): self.Key_A=True; self.left()
            if(event.key() == Qt.Key_D) and (self.Key_D==False): self.Key_D=True; self.right()
            if(event.key() == Qt.Key_Q) and (self.Key_Q==False): self.Key_Q=True; self.step_left()
            if(event.key() == Qt.Key_E) and (self.Key_E==False): self.Key_E=True; self.step_right()
            if(event.key() == Qt.Key_F): self.chase_ball_and_find_face()
        except Exception as e:
            print(e)

    def keyReleaseEvent(self, event):
        try:
            if(event.key() == Qt.Key_W): self.Key_W=False; self.stop()
            if(event.key() == Qt.Key_S): self.Key_S=False; self.stop()
            if(event.key() == Qt.Key_A): self.Key_A=False; self.stop()
            if(event.key() == Qt.Key_D): self.Key_D=False; self.stop()
            if(event.key() == Qt.Key_Q): self.Key_Q=False; self.stop()
            if(event.key() == Qt.Key_E): self.Key_E=False; self.stop()
        except Exception as e:
            print(e)

    def paintEvent(self,e):
        try:
            qp=QPainter(); qp.begin(self)
            pen=QPen(Qt.white,2,Qt.SolidLine); qp.setPen(pen); qp.drawRect(485,35,200,200)
            pen=QPen(QColor(0,138,255),2,Qt.SolidLine); qp.setPen(pen)
            qp.drawLine(self.drawpoint[0],35,self.drawpoint[0],235)
            qp.drawLine(485,self.drawpoint[1],685,self.drawpoint[1])
            self.label_point.move(self.drawpoint[0] + 10, self.drawpoint[1] + 10)
            pitch = round((self.drawpoint[1] - 135) / 100.0 * 20)
            yaw = round((self.drawpoint[0] - 585) / 100.0 * 20)
            self.label_point.setText(str((yaw, pitch)))
            qp.end()
            if pitch != self.slider_pitch.value(): self.slider_pitch.setValue(pitch)
            if yaw != self.slider_yaw.value(): self.slider_yaw.setValue(yaw)
        except Exception as e:
            print(e)

    def mouseMoveEvent(self, event):
        x=event.pos().x(); y=event.pos().y()
        if 485 < x < 685 and 35 < y < 235:
            try:
                self.drawpoint[0]=x; self.drawpoint[1]=y; self.update()
            except Exception as e:
                print(e)

    def mousePressEvent(self, event):
        x=event.pos().x(); y=event.pos().y()
        if 485 < x < 685 and 35 < y < 235:
            try:
                self.drawpoint[0]=x; self.drawpoint[1]=y; self.update()
            except Exception as e:
                print(e)

    def closeEvent(self, event):
        self._dbg("[DEBUG] closeEvent triggered, beginning shutdown")
        try:
            self.client.video_thread_running = False
            self.client.instruction_thread_running = False
            if hasattr(self, 'video_thread') and self.video_thread.is_alive():
                self.video_thread.join(timeout=2.0)  # Wait gracefully

            if hasattr(self, "timer_power"): self.timer_power.stop()
            if hasattr(self, "timer"): self.timer.stop()
            self.client.tcp_flag = False
            if hasattr(self.client, 'video_thread_running'):
                self.client.video_thread_running = False
            for tname in ("video_thread", "instruction_thread"):
                t = getattr(self, tname, None)
                if t and hasattr(t, "is_alive") and t.is_alive():
                    try:
                        stop_thread(t)  # Unsafe! Uses deprecated thread termination
                    except Exception as e:
                        print(f"[WARN] Failed to stop thread {tname}: {e}")
            if hasattr(self.client, "turn_off_client"):
                self.client.turn_off_client(); self._dbg("[DEBUG] Client turned off successfully")
        finally:
            self._dbg("[DEBUG] Exiting application"); QCoreApplication.instance().quit()

    def video(self):
        if not self.timer.isActive():
            self.timer.start(33); self.Button_Video.setText('Close Video')
        else:
            self.timer.stop(); self.Button_Video.setText('Open Video')

    # ---------- Telemetry receiver (fixed) ----------
    def receive_instruction(self, ip):
        try:
            if self.debug_rx_enabled: print(f"[DEBUG][RX] Connecting to {ip}:5001 ...")
            self.client.client_socket1.connect((ip, 5001))
            self.client.client_socket1.settimeout(2.0)
            self.client.tcp_flag = True
            if self.debug_rx_enabled: print("[DEBUG][RX] Command socket connected")
        except Exception as e:
            if self.debug_rx_enabled: print(f"[DEBUG][RX] connect error: {e}")
            self.client.tcp_flag = False
            return

        sock = self.client.client_socket1
        buf = ""
        try:
            while self.client.tcp_flag:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        if self.debug_rx_enabled: print("[DEBUG][RX] peer closed")
                        break
                    buf += chunk.decode("utf-8", errors="ignore")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._handle_server_line(line)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.debug_rx_enabled: print(f"[DEBUG][RX] recv error: {e}")
                    break
        finally:
            self.client.tcp_flag = False
            try: sock.close()
            except Exception: pass
            if self.debug_rx_enabled: print("[DEBUG][RX] Instruction thread exiting")

    def _handle_server_line(self, line: str):
        if self.debug_rx_enabled: print(f"[DEBUG][RX] {line}")
        parts = [p.strip() for p in line.split("#")]
        if not parts: return
        tag = parts[0].upper()

        def first_float(tokens):
            for t in tokens:
                cleaned = re.sub(r"[^0-9.\-]", "", t)
                try: return float(cleaned)
                except Exception: pass
            return None

        # Battery
        if any(k in tag for k in ("POWER", "VOLT", "BAT")):
            v = first_float(parts[1:])
            if v is not None:
                self.tele_batt_v = v
                pct = int(max(0, min(100, (v - 7.00) / 1.40 * 100)))
                QtCore.QTimer.singleShot(0, lambda p=pct: self.progress_Power.setValue(p))
            return

        # Distance
        if any(k in tag for k in ("SONIC", "DIST", "RANGE")):
            d = first_float(parts[1:])
            if d is not None:
                self.tele_dist_cm = d
            return
        # Others ignored silently

    def resizeEvent(self, e):
        try:
            if getattr(self, "_showing_startup_art", False):
                self._set_startup_art()
        except Exception:
            pass
        return super().resizeEvent(e)

    def _blit_to_label(self, frame_bgr: np.ndarray):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg).scaled(self.Video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.Video.setPixmap(pix)

    def _set_startup_art(self):
        try:
            if not hasattr(self, "_startup_pix") or self._startup_pix.isNull():
                self._startup_pix = QPixmap('Picture/dog_client.png')
            if not self._startup_pix.isNull():
                pix = self._startup_pix.scaled(self.Video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.Video.setPixmap(pix); self._showing_startup_art = True
            else:
                self.Video.clear(); self._showing_startup_art = False
        except Exception as e:
            print(f"[DEBUG][GUI] startup_art error: {e}"); self._showing_startup_art = False

    def _overlay_refresh_if_stalled(self):
        try:
            if not self.timer.isActive(): return
            if self.last_frame_time == 0.0:
                h, w = 240, 320
                placeholder = np.zeros((h, w, 3), dtype=np.uint8)
                placeholder[:] = (25, 25, 25)
                tv.draw_top_bar(placeholder, fps=self._fps, battery_v=self.tele_batt_v,
                                distance_cm=self.tele_dist_cm, state_text=self.state_text,
                                state_since=self.state_since)
                self._blit_to_label(placeholder)
                return
            stall_age = time.time() - self.last_frame_time
            if stall_age > 0.4 and isinstance(self._last_frame_bgr, np.ndarray) and self._last_frame_bgr.size > 0:
                frame = self._last_frame_bgr.copy()
                tv.draw_top_bar(frame, fps=self._fps, battery_v=self.tele_batt_v,
                                distance_cm=self.tele_dist_cm, state_text=self.state_text,
                                state_since=self.state_since)
                self._blit_to_label(frame)
        except Exception as e:
            print(f"[DEBUG][GUI] overlay_refresh error: {e}")

    def refresh_image(self):
        try:
            base = None
            prod_ts = getattr(self.client, 'video_last_frame_ts', 0.0)
            with self.client.image_lock:
                if isinstance(self.client.image, np.ndarray) and self.client.image.size > 0:
                    base = self.client.image.copy()
                    self.client.video_flag = True
            if base is None:
                if not getattr(self, "_showing_startup_art", False):
                    self._set_startup_art()
                return
            self._showing_startup_art = False
            if prod_ts and prod_ts != getattr(self, "_producer_ts_prev", 0.0):
                now = time.time()
                dt = now - getattr(self, "_prev_frame_ts", now)
                self._prev_frame_ts = now
                if dt > 1e-6:
                    self._fps = 0.9 * getattr(self, "_fps", 0.0) + 0.1 * (1.0 / dt)
                self.last_frame_time = now
                self._producer_ts_prev = prod_ts

            frame = base
            tv.draw_top_bar(frame,
                            fps=getattr(self, "_fps", 0.0),
                            battery_v=getattr(self, 'tele_batt_v', None),
                            distance_cm=getattr(self, 'tele_dist_cm', None),
                            state_text=getattr(self, 'state_text', 'Resting'),
                            state_since=getattr(self, 'state_since', time.time()))
            self._last_frame_bgr = frame.copy()
            self._blit_to_label(frame)
            if hasattr(self.client, 'frames_displayed'):
                self.client.frames_displayed += 1
        except Exception as e:
            print(f"[DEBUG][GUI] refresh_image error: {e}")

    # ==== Robot control API (unchanged from v1192) ====
    def chase_ball_and_find_face(self):
        try:
            text = self.Button_Ball_And_Face.text()
            if text == 'Face':
                self.client.face_flag = True; self.client.ball_flag = False; self.Button_Ball_And_Face.setText('Ball')
            elif text == 'Ball':
                self.client.face_flag = False; self.client.ball_flag = True; self.Button_Ball_And_Face.setText('Close')
            else:
                self.client.face_flag = False; self.client.ball_flag = False; self.stop(); self.Button_Ball_And_Face.setText('Face')
        except Exception as e: print(e)

    def connect(self):
        file=open('IP.txt','w'); file.write(self.lineEdit_IP_Adress.text()); file.close()
        if self.Button_Connect.text()=='Connect':
            self.IP = self.lineEdit_IP_Adress.text().strip()
            if not self.IP:
                QMessageBox.warning(self, "Connect", "Please enter the robot IP address."); return
            self._dbg(f"[DEBUG] Attempting connection to {self.IP}: (5001 + a)")    # self.IP is 192.168.0.32 now, 5001 + a means port 5001 and 8001
            self.client.turn_on_client(self.IP)                             # turn on client sockets which
            self.video_thread = threading.Thread(target=self.client.receiving_video,args=(self.IP,))        # create video thread for receiving video from port 8001
            self.instruction_thread = threading.Thread(target=self.receive_instruction,args=(self.IP,))     # create instruction thread for receiving instructions from port 5001
            self.video_thread.start(); self.instruction_thread.start()                                      # start both threads
            self._dbg("[DEBUG] Threads started (video_thread, instruction_thread)")
            self.Button_Connect.setEnabled(False); self.Button_Connect.setText('Connecting…')
            self.Button_Video.setEnabled(False)
            def post_check():
                ok_cmd = bool(self.client.tcp_flag)
                ok_vid = bool(self.client.connection is not None)
                if ok_cmd and ok_vid:
                    self._dbg("[DEBUG] Both channels connected. Entering online state.")
                    self.Button_Connect.setText('Disconnect'); self.Button_Connect.setEnabled(True)
                    self.Button_Video.setEnabled(True)
                    self.timer_power.start(1000); self.timer_sonic.start(1000); self.Button_Sonic.setText('Close')
                    self.overlay_timer.start()
                    if not self.timer.isActive():
                        self.timer.start(33); self.Button_Video.setText('Close Video')
                    self._dbg("[DEBUG] Connection successful: ports 5001/8001 ready")
                else:
                    self._draw_status_placeholder("Connect Failed", (0,0,255))
                    print(f"[WARN] Connection failed (cmd={ok_cmd}, video={ok_vid}). Cleaning up.")
                    for tname in ("video_thread","instruction_thread"):
                        t = getattr(self, tname, None)
                        if t:
                            try:
                                stop_thread(t)  # Unsafe! Uses deprecated thread termination
                            except Exception as e:
                                print(f"[WARN] Failed to stop thread {tname}: {e}")
                    self.client.tcp_flag=False; self.client.turn_off_client()
                    self.timer_power.stop(); self.timer_sonic.stop(); self.Button_Sonic.setText('Sonic')
                    self.Button_Connect.setText('Connect'); self.Button_Connect.setEnabled(True)
                    self.Button_Video.setEnabled(False)
            QTimer.singleShot(1200, post_check)
        else:
            self._dbg("[DEBUG] Initiating disconnection...")
            for tname in ("video_thread","instruction_thread"):
                t = getattr(self, tname, None)
                if t:
                    try:
                        stop_thread(t)  # Unsafe! Uses deprecated thread termination
                    except Exception as e:
                        print(f"[WARN] Failed to stop thread {tname}: {e}")
            self.client.tcp_flag=False; self.client.turn_off_client(); self._dbg("[DEBUG] Client sockets closed")
            self.timer_power.stop(); self.timer_sonic.stop(); self.Button_Sonic.setText('Sonic')
            self.overlay_timer.stop()
            if self.timer.isActive(): self.timer.stop()
            self.Button_Video.setText('Open Video'); self.Button_Video.setEnabled(False)
            self.Button_Connect.setText('Connect'); print("[DEBUG] Disconnection complete !! \n")

    def stand(self):
        self.initial=False; self.Button_IMU.setText('Balance')
        QTimer.singleShot(0,   lambda: self.slider_roll.setValue(0))
        QTimer.singleShot(100, lambda: self.slider_pitch.setValue(0))
        QTimer.singleShot(200, lambda: self.slider_yaw.setValue(0))
        QTimer.singleShot(300, lambda: self.slider_horizon.setValue(0))
        QTimer.singleShot(400, lambda: setattr(self, 'initial', True))

    def stop(self):
        self.client.send_data(cmd.CMD_MOVE_STOP+"#"+str(self.slider_speed.value())+'\n')

    def forward(self):
        self.stand(); self.client.send_data(cmd.CMD_MOVE_FORWARD+"#"+str(self.slider_speed.value())+'\n')

    def backward(self):
        self.stand(); self.client.send_data(cmd.CMD_MOVE_BACKWARD+"#"+str(self.slider_speed.value())+'\n')

    def step_left(self):
        self.stand(); self.client.send_data(cmd.CMD_MOVE_LEFT+"#"+str(self.slider_speed.value())+'\n')

    def step_right(self):
        self.stand(); self.client.send_data(cmd.CMD_MOVE_RIGHT+"#"+str(self.slider_speed.value())+'\n')

    def left(self):
        self.stand(); self.client.send_data(cmd.CMD_TURN_LEFT+"#"+str(self.slider_speed.value())+'\n')

    def right(self):
        self.stand(); self.client.send_data(cmd.CMD_TURN_RIGHT+"#"+str(self.slider_speed.value())+'\n')

    def speed(self):
        self.client.move_speed=str(self.slider_speed.value()); self.label_speed.setText(str(self.slider_speed.value()))

    def relax(self):
        if self.Button_Relax.text() == 'Relax':
            self.client.send_data(cmd.CMD_RELAX+'\n')

    def buzzer(self):
        try:
            if self.Button_Buzzer.text() == 'Buzzer':
                self.client.send_data(cmd.CMD_BUZZER + '#1' + '\n'); self.Button_Buzzer.setText('Noise')
            else:
                self.client.send_data(cmd.CMD_BUZZER + '#0' + '\n'); self.Button_Buzzer.setText('Buzzer')
        except Exception as e: print(e)

    def imu(self):
        if self.Button_IMU.text()=='Balance':
            self.client.send_data(cmd.CMD_BALANCE+'#1'+'\n'); self.Button_IMU.setText("Close")
        else:
            self.client.send_data(cmd.CMD_BALANCE+'#0'+'\n'); self.Button_IMU.setText('Balance')

    def sonic(self):
        if self.Button_Sonic.text() == 'Sonic':
            self.timer_sonic.start(100); self.Button_Sonic.setText('Close')
        else:
            self.timer_sonic.stop(); self.Button_Sonic.setText('Sonic')

    def getSonicData(self):
        self.client.send_data(cmd.CMD_SONIC+'\n')

    def height(self):
        try:
            hei=str(self.slider_height.value()); self.label_height.setText(hei)
            self.client.send_data(cmd.CMD_HEIGHT+"#"+hei+'\n')
        except Exception as e: print(e)

    def horizon(self):
        try:
            hor=str(self.slider_horizon.value()); self.label_horizon.setText(hor)
            if self.initial: self.client.send_data(cmd.CMD_HORIZON+"#"+hor+'\n')
        except Exception as e: print(e)

    def head(self):
        try:
            angle=str(self.slider_head.value()); self.label_head.setText(angle)
            self.client.send_data(cmd.CMD_HEAD+"#"+angle+'\n')
        except Exception as e: print(e)

    def power(self):
        try:
            self.client.send_data(cmd.CMD_POWER+'\n')
            self.client.send_data("CMD_WORKING_TIME\n")
        except Exception as e: print(e)

    def attitude(self,target1,target2):
        try:
            r=str(self.slider_roll.value()); p=str(self.slider_pitch.value()); y=str(self.slider_yaw.value())
            command = cmd.CMD_ATTITUDE + '#' + r + '#' + p + '#' + y + '\n'
            if self.initial: self.client.send_data(command)
            target1.setText(str(target2.value()))
            self.drawpoint[0]=585+self.slider_yaw.value()*5
            self.drawpoint[1]=135+self.slider_pitch.value()*5
            self.update()
        except Exception as e: print(e)

    def showCalibrationWindow(self):
        self.stop()
        self.calibrationWindow=calibrationWindow(self.client)
        self.calibrationWindow.setWindowModality(Qt.ApplicationModal)
        self.calibrationWindow.show()

    def showLedWindow(self):
        try:
            self.ledWindow=ledWindow(self.client)
            self.ledWindow.setWindowModality(Qt.ApplicationModal)
            self.ledWindow.show()
        except Exception as e: print(e)

    def showFaceWindow(self):
        try:
            self.faceWindow = faceWindow(self.client)
            self.faceWindow.setWindowModality(Qt.ApplicationModal)
            self.faceWindow.show()
            self.client.face_id = True
        except Exception as e: print(e)

# ---------------- Face window ----------------
class faceWindow(QMainWindow,Ui_Face):
    def __init__(self,client):
        super(faceWindow,self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon('Picture/logo_Mini.png'))
        self.label_video.setScaledContents(True)
        self.label_video.setPixmap(QPixmap('Picture/dog_client.png'))
        self.Button_Read_Face.clicked.connect(self.readFace)
        self.client = client
        self.face_image=''
        self.photoCount=0
        self.timeout=0
        self.name = ''
        self.readFaceFlag=False
        self.timer1 = QTimer(self); self.timer1.timeout.connect(self.faceDetection); self.timer1.start(10)
        self.timer2 = QTimer(self); self.timer2.timeout.connect(self.facePhoto)

    def closeEvent(self, event):
        self.timer1.stop(); self.client.face_id = False
        
    def readFace(self):
        try:
            if self.Button_Read_Face.text()=="Read Face":
                self.Button_Read_Face.setText("Reading"); self.timer2.start(10); self.timeout=time.time()
            else:
                self.timer2.stop()
                if self.photoCount!=0:
                    self.Button_Read_Face.setText("Waiting "); self.client.face.trainImage()
                    QMessageBox.information(self, "Message", "success", QMessageBox.Yes)
                self.Button_Read_Face.setText("Read Face"); self.lineEdit.setText(""); self.name = ''; self.photoCount = 0
        except Exception as e: print(e)

    def facePhoto(self):
        try:
            if self.photoCount == 30:
                self.photoCount = 0; self.timer2.stop()
                self.Button_Read_Face.setText("Waiting "); self.client.face.trainImage()
                QMessageBox.information(self, "Message", "success", QMessageBox.Yes)
                self.Button_Read_Face.setText("Read Face"); self.lineEdit.setText(""); self.name = ''
            else:
                if len(self.face_image)>0:
                    self.name = self.lineEdit.text()
                    if len(self.name) > 0:
                        h, w = self.face_image.shape[:2]
                        QImg = QImage(self.face_image.data.tobytes(), w, h, 3*w, QImage.Format_RGB888)
                        self.label_photo.setPixmap(QPixmap.fromImage(QImg))
                        elapsed = time.time() - self.timeout
                        if elapsed > 1:
                            self.saveFcaePhoto(); self.timeout=time.time()
                        else:
                            remaining = max(0, 1-int(elapsed))
                            self.Button_Read_Face.setText(f"Reading {remaining}S   {self.photoCount}/30")
                        self.face_image=''
                    else:
                        QMessageBox.information(self, "Message", "Please enter your name", QMessageBox.Yes)
                        self.timer2.stop(); self.Button_Read_Face.setText("Read Face")
        except Exception as e: print(e)

    def saveFcaePhoto(self):
        cv2.imwrite('Face/'+str(len(self.client.face.name))+'.jpg', self.face_image)
        self.client.face.name.append([str(len(self.client.face.name)),str(self.name)])
        self.client.face.Save_to_txt(self.client.face.name, 'Face/name')
        self.client.face.name = self.client.face.Read_from_txt('Face/name')
        self.photoCount += 1
        self.Button_Read_Face.setText("Reading "+str(0)+" S "+str(self.photoCount)+"/30")

    def faceDetection(self):
        try:
            # Safely copy the latest frame (guard None/empty, use lock)
            if not isinstance(self.client.image, np.ndarray) or self.client.image.size == 0:
                return
            with self.client.image_lock:
                frame = self.client.image.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.client.face.detector.detectMultiScale(gray, 1.2, 5)
            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    x1 = max(0, x-5); y1 = max(0, y-5)
                    x2 = min(frame.shape[1], x + w + 5); y2 = min(frame.shape[0], y + h + 5)
                    self.face_image = frame[y1:y2, x1:x2]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Respect producer/consumer flag
            if self.client.video_flag == False:
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                QImg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                self.label_video.setPixmap(QPixmap.fromImage(QImg))
                self.client.video_flag = True
        except Exception as e:
            print(e)

# ---------------- Calibration window ----------------
class calibrationWindow(QMainWindow,Ui_calibration):
    def __init__(self,client):
        super(calibrationWindow,self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon('Picture/logo_Mini.png'))
        self.label_picture.setScaledContents (True)
        self.label_picture.setPixmap(QPixmap('Picture/dog_calibration.png'))
        self.point=self.Read_from_txt('point')
        self.set_point(self.point)
        self.client=client
        self.leg='one'
        self.x=self.y=self.z=0
        self.radioButton_one.setChecked(True)
        self.radioButton_one.toggled.connect(lambda: self.leg_point(self.radioButton_one))
        self.radioButton_two.setChecked(False)
        self.radioButton_two.toggled.connect(lambda: self.leg_point(self.radioButton_two))
        self.radioButton_three.setChecked(False)
        self.radioButton_three.toggled.connect(lambda: self.leg_point(self.radioButton_three))
        self.radioButton_four.setChecked(False)
        self.radioButton_four.toggled.connect(lambda: self.leg_point(self.radioButton_four))
        self.Button_Save.clicked.connect(self.save)
        self.Button_X1.clicked.connect(self.X1); self.Button_X2.clicked.connect(self.X2)
        self.Button_Y1.clicked.connect(self.Y1); self.Button_Y2.clicked.connect(self.Y2)
        self.Button_Z1.clicked.connect(self.Z1); self.Button_Z2.clicked.connect(self.Z2)

    def X1(self):
        self.get_point(); self.x +=1
        command=cmd.CMD_CALIBRATION+'#'+self.leg+'#'+str(self.x)+'#'+str(self.y)+'#'+str(self.z)+'\n'
        self.client.send_data(command); self.set_point()

    def X2(self):
        self.get_point(); self.x -= 1
        command=cmd.CMD_CALIBRATION+'#'+self.leg+'#'+str(self.x)+'#'+str(self.y)+'#'+str(self.z)+'\n'
        self.client.send_data(command); self.set_point()

    def Y1(self):
        self.get_point(); self.y += 1
        command=cmd.CMD_CALIBRATION+'#'+self.leg+'#'+str(self.x)+'#'+str(self.y)+'#'+str(self.z)+'\n'
        self.client.send_data(command); self.set_point()

    def Y2(self):
        self.get_point(); self.y -= 1
        command=cmd.CMD_CALIBRATION+'#'+self.leg+'#'+str(self.x)+'#'+str(self.y)+'#'+str(self.z)+'\n'
        self.client.send_data(command); self.set_point()

    def Z1(self):
        self.get_point(); self.z += 1
        command=cmd.CMD_CALIBRATION+'#'+self.leg+'#'+str(self.x)+'#'+str(self.y)+'#'+str(self.z)+'\n'
        self.client.send_data(command); self.set_point()

    def Z2(self):
        self.get_point(); self.z -= 1
        command=cmd.CMD_CALIBRATION+'#'+self.leg+'#'+str(self.x)+'#'+str(self.y)+'#'+str(self.z)+'\n'
        self.client.send_data(command); self.set_point()

    def set_point(self,data=None):
        if data is None:
            if self.leg== "one":
                self.one_x.setText(str(self.x)); self.one_y.setText(str(self.y)); self.one_z.setText(str(self.z))
                self.point[0][0]=self.x; self.point[0][1]=self.y; self.point[0][2]=self.z
            elif self.leg== "two":
                self.two_x.setText(str(self.x)); self.two_y.setText(str(self.y)); self.two_z.setText(str(self.z))
                self.point[1][0]=self.x; self.point[1][1]=self.y; self.point[1][2]=self.z
            elif self.leg== "three":
                self.three_x.setText(str(self.x)); self.three_y.setText(str(self.y)); self.three_z.setText(str(self.z))
                self.point[2][0]=self.x; self.point[2][1]=self.y; self.point[2][2]=self.z
            elif self.leg== "four":
                self.four_x.setText(str(self.x)); self.four_y.setText(str(self.y)); self.four_z.setText(str(self.z))
                self.point[3][0]=self.x; self.point[3][1]=self.y; self.point[3][2]=self.z
        else:
            self.one_x.setText(str(data[0][0])); self.one_y.setText(str(data[0][1])); self.one_z.setText(str(data[0][2]))
            self.two_x.setText(str(data[1][0])); self.two_y.setText(str(data[1][1])); self.two_z.setText(str(data[1][2]))
            self.three_x.setText(str(data[2][0])); self.three_y.setText(str(data[2][1])); self.three_z.setText(str(data[2][2]))
            self.four_x.setText(str(data[3][0])); self.four_y.setText(str(data[3][1])); self.four_z.setText(str(data[3][2]))

    def get_point(self):
        if self.leg== "one":
            self.x = int(self.one_x.text()); self.y = int(self.one_y.text()); self.z = int(self.one_z.text())
        elif self.leg== "two":
            self.x = int(self.two_x.text()); self.y = int(self.two_y.text()); self.z = int(self.two_z.text())
        elif self.leg== "three":
            self.x = int(self.three_x.text()); self.y = int(self.three_y.text()); self.z = int(self.three_z.text())
        elif self.leg== "four":
            self.x = int(self.four_x.text()); self.y = int(self.four_y.text()); self.z = int(self.four_z.text())

    def save(self):
        command=cmd.CMD_CALIBRATION+'#'+'save'+'\n'; self.client.send_data(command)
        self.point[0][0] = self.one_x.text();   self.point[0][1] = self.one_y.text();   self.point[0][2] = self.one_z.text()
        self.point[1][0] = self.two_x.text();   self.point[1][1] = self.two_y.text();   self.point[1][2] = self.two_z.text()
        self.point[2][0] = self.three_x.text(); self.point[2][1] = self.three_y.text(); self.point[2][2] = self.three_z.text()
        self.point[3][0] = self.four_x.text();  self.point[3][1] = self.four_y.text();  self.point[3][2] = self.four_z.text()
        self.Save_to_txt(self.point,'point')
        QMessageBox.information(self, "Message", "Saved successfully", QMessageBox.Yes)

    def Read_from_txt(self,filename):
        file1 = open(filename + ".txt", "r")
        list_row = file1.readlines()
        list_source = []
        for i in range(len(list_row)):
            column_list = list_row[i].strip().split("\t")
            list_source.append(column_list)
        for i in range(len(list_source)):
            for j in range(len(list_source[i])):
                list_source[i][j] = int(list_source[i][j])
        file1.close()
        return list_source

    def Save_to_txt(self,list, filename):
        file2 = open(filename + '.txt', 'w')
        for i in range(len(list)):
            for j in range(len(list[i])):
                file2.write(str(list[i][j])); file2.write('\t')
            file2.write('\n')
        file2.close()
        
    def leg_point(self,leg):
        if leg.text() == "One":
            if leg.isChecked() == True: self.leg = "one"
        elif leg.text() == "Two":
            if leg.isChecked() == True: self.leg = "two"
        elif leg.text() == "Three":
            if leg.isChecked() == True: self.leg = "three"
        elif leg.text() == "Four":
            if leg.isChecked() == True: self.leg = "four"

# ---------------- LED window ----------------
class ColorDialog(QtWidgets.QColorDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOptions(self.options() | QtWidgets.QColorDialog.DontUseNativeDialog)
        for children in self.findChildren(QtWidgets.QWidget):
            classname = children.metaObject().className()
            if classname not in ("QColorPicker", "QColorLuminancePicker"):
                children.hide()

class ledWindow(QMainWindow,Ui_led):
    def __init__(self,client):
        super(ledWindow,self).__init__()
        self.setupUi(self)
        self.client = client
        self.setWindowIcon(QIcon('Picture/logo_Mini.png'))
        self.hsl = [0, 0, 1]; self.rgb = [0, 0, 0]
        self.dial_color.setRange(0, 360); self.dial_color.setNotchesVisible(True)
        self.dial_color.setWrapping(True); self.dial_color.setPageStep(10); self.dial_color.setNotchTarget(10)
        self.dial_color.valueChanged.connect(self.dialValueChanged)
        composite_2f = lambda f, g: lambda t: g(f(t))
        self.hsl_to_rgb255 = composite_2f(self.hsl_to_rgb01, self.rgb01_to_rgb255)
        self.hsl_to_rgbhex = composite_2f(self.hsl_to_rgb255, self.rgb255_to_rgbhex)
        self.rgb255_to_hsl = composite_2f(self.rgb255_to_rgb01, self.rgb01_to_hsl)
        self.rgbhex_to_hsl = composite_2f(self.rgbhex_to_rgb255, self.rgb255_to_hsl)
        self.colordialog = ColorDialog()
        self.colordialog.currentColorChanged.connect(self.onCurrentColorChanged)
        lay = QtWidgets.QVBoxLayout(self.widget)
        lay.addWidget(self.colordialog, alignment=QtCore.Qt.AlignCenter)
        self.pushButtonLightsOut.clicked.connect(self.turnOff)
        self.radioButtonOne.setChecked(True)
        self.radioButtonOne.toggled.connect(lambda: self.ledMode(self.radioButtonOne))
        self.radioButtonTwo.setChecked(False)
        self.radioButtonTwo.toggled.connect(lambda: self.ledMode(self.radioButtonTwo))
        self.radioButtonThree.setChecked(False)
        self.radioButtonThree.toggled.connect(lambda: self.ledMode(self.radioButtonThree))
        self.radioButtonFour.setChecked(False)
        self.radioButtonFour.toggled.connect(lambda: self.ledMode(self.radioButtonFour))
        self.radioButtonFive.setChecked(False)
        self.radioButtonFive.toggled.connect(lambda: self.ledMode(self.radioButtonFive))

    def turnOff(self):
        self.client.send_data(cmd.CMD_LED_MOD + '#' + '0' + '\n')

    def ledMode(self,index):
        if index.text() == "Mode 1":
            if index.isChecked() == True:
                self.client.send_data(cmd.CMD_LED_MOD + '#' + '1' + '\n')
        elif index.text() == "Mode 2":
            if index.isChecked() == True:
                self.client.send_data(cmd.CMD_LED_MOD + '#' + '2' + '\n')
        elif index.text() == "Mode 3":
            if index.isChecked() == True:
                self.client.send_data(cmd.CMD_LED_MOD + '#' + '3' + '\n')
        elif index.text() == "Mode 4":
            if index.isChecked() == True:
                self.client.send_data(cmd.CMD_LED_MOD + '#' + '4' + '\n')
        elif index.text() == "Mode 5":
            if index.isChecked() == True:
                self.client.send_data(cmd.CMD_LED_MOD + '#' + '5' + '\n')

    def mode1Color(self):
        if (self.radioButtonOne.isChecked() == True) or (self.radioButtonThree.isChecked() == True):
            command = cmd.CMD_LED + '#' + '255' + '#' + str(self.rgb[0]) + '#' + str(self.rgb[1]) + '#' + str(self.rgb[2]) + '\n'
            self.client.send_data(command)

    def onCurrentColorChanged(self, color):
        try:
            self.rgb = self.rgbhex_to_rgb255(color.name()); self.hsl = self.rgb255_to_hsl(self.rgb)
            self.changeHSLText(); self.changeRGBText()
            self.mode1Color(); self.update()
        except Exception as e: print(e)

    def paintEvent(self, e):
        try:
            qp = QPainter(); qp.begin(self)
            brush = QBrush(QColor(self.rgb[0], self.rgb[1], self.rgb[2])); qp.setBrush(brush)
            qp.drawRect(20, 10, 80, 30); qp.end()
        except Exception as e: print(e)

    def dialValueChanged(self):
        try:
            self.lineEdit_H.setText(str(self.dial_color.value()))
            self.changeHSL(); self.hex = self.hsl_to_rgbhex((self.hsl[0], self.hsl[1], self.hsl[2]))
            self.rgb = self.rgbhex_to_rgb255(self.hex); self.changeRGBText()
            self.mode1Color(); self.update()
        except Exception as e: print(e)

    def changeHSL(self):
        self.hsl[0] = float(self.lineEdit_H.text()); self.hsl[1] = float(self.lineEdit_S.text()); self.hsl[2] = float(self.lineEdit_L.text())

    def changeHSLText(self):
        self.lineEdit_H.setText(str(int(self.hsl[0]))); self.lineEdit_S.setText(str(round(self.hsl[1], 1))); self.lineEdit_L.setText(str(round(self.hsl[2], 1)))

    def changeRGBText(self):
        self.lineEdit_R.setText(str(self.rgb[0])); self.lineEdit_G.setText(str(self.rgb[1])); self.lineEdit_B.setText(str(self.rgb[2]))

    def rgb255_to_rgbhex(self, rgb: np.array) -> str:
        f = lambda n: 0 if n < 0 else 255 if n > 255 else int(n)
        return '#%02x%02x%02x' % (f(rgb[0]), f(rgb[1]), f(rgb[2]))

    def rgbhex_to_rgb255(self, rgbhex: str) -> np.array:
        if rgbhex[0] == '#': rgbhex = rgbhex[1:]
        r = int(rgbhex[0:2], 16); g = int(rgbhex[2:4], 16); b = int(rgbhex[4:6], 16)
        return np.array((r, g, b))

    def rgb01_to_rgb255(self, rgb: np.array) -> np.array: return rgb * 255
    def rgb255_to_rgb01(self, rgb: np.array) -> np.array: return rgb / 255

    def rgb01_to_hsl(self, rgb: np.array) -> np.array:
        r, g, b = rgb
        lmin = min(r, g, b); lmax = max(r, g, b)
        if lmax == lmin: h = 0
        elif lmin == b: h = 60 + 60 * (g - r) / (lmax - lmin)
        elif lmin == r: h = 180 + 60 * (b - g) / (lmax - lmin)
        elif lmin == g: h = 300 + 60 * (r - b) / (lmax - lmin)
        else: h = 0
        s = lmax - lmin; l = (lmax + lmin) / 2
        return np.array((h, s, l))

    def hsl_to_rgb01(self, hsl: np.array) -> np.array:
        h, s, l = hsl
        lmin = l - s / 2; lmax = l + s / 2; ldif = lmax - lmin
        if h < 60:   r, g, b = lmax, lmin + ldif * (0 + h) / 60, lmin
        elif h < 120: r, g, b = lmin + ldif * (120 - h) / 60, lmax, lmin
        elif h < 180: r, g, b = lmin, lmax, lmin + ldif * (h - 120) / 60
        elif h < 240: r, g, b = lmin, lmin + ldif * (240 - h) / 60, lmax
        elif h < 300: r, g, b = lmin + ldif * (h - 240) / 60, lmin, lmax
        else:         r, g, b = lmax, lmin, lmin + ldif * (360 - h) / 60
        return np.array((r, g, b))

# ==================================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    myshow=MyWindow()
    myshow.show()
    sys.exit(app.exec_())
# ==================================================================================
