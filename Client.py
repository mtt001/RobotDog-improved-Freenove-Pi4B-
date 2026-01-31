# -*- coding: utf-8 -*-
"""
Application: Freenove Robot Dog Client - Network Communication Module
Authors   : MT & GitHub Copilot
Summary   : Socket protocol handling (video + instruction channels), shared image buffer, command send helpers.

# Copilot GPT-5: Remember! Always send 4-byte little-endian length prefix (<I).
# Copilot GPT-5: use recv_exact pattern, not file.read(n), to avoid blocking.

Revision History:
- 1.07 (2025-11-13): Add periodic stall debug: print when no frame for >2s while waiting on recv; expose
                     video_last_frame_ts for GUI; minor log cleanups.
- 1.06 (2025-11-13): Add periodic stall debug: print when no frame for >2s while waiting on recv; expose
                     video_last_frame_ts for GUI; minor log cleanups.
- 1.05 (2025-11-12): Make video reader resilient: loop reconnects on errors; socket timeouts no longer end the
                     thread; mark readiness with self.connection on connect/disconnect; lighter debug.
- 1.04 (2025-11-12): Switch video reader to unbuffered socket recv_exact (no makefile) to avoid freezes;
                     keep self.connection set to the raw socket for readiness checks; add frame counter debug.
- 1.03 (2025-11-12): Robust video framing (try 4B then 8B length), exact-byte reads, JPEG SOI check,
                     connection retry with friendly warnings (busy/not responding), richer inline comments,
                     safer thread stop via video_thread_running flag.
- 1.02 (2025-11-11): Add connection state check in send_data/receive_data to prevent AttributeError; add graceful video thread exit logging.
- 1.01 (2025-11-11): Add defensive socket cleanup with detailed debug logging; prevent AttributeError on 'connection.connection'; add safety checks for socket closure.
- 1.00:   "Client.py" from Freenove Robot Dog Kit. Original code renamed as "Client.original.py" .
"""
__version__ = "1.07 (2025-11-13)"
# =======================================================================================
import io
import copy
import socket
import struct
import threading
import time
from PID import *
from Face import *
import numpy as np
from Thread import *
from PIL import Image
import cv2  # REQUIRED for imdecode in receiving_video
from Command import COMMAND as cmd
# External ball tracking override (disabled until BallTracking.py matured)
# from BallTracking import Looking_for_the_ball  # Uncomment when ready to override method

# ----------------------------- Constants / Tunables -----------------------------
VIDEO_PORT = 8001          # video stream TCP port on the Pi
CMD_PORT = 5001            # command/telemetry TCP port on the Pi (used by MainMT.receive_instruction)
CONNECT_TIMEOUT_S = 5.0    # socket connect timeout
READ_TIMEOUT_S = 5.0       # socket read timeout (detect stalls)
CONNECT_RETRIES = 5        # connection attempts before giving up
RETRY_DELAY_S = 1.0        # delay between attempts
MAX_FRAME = 5_000_000      # safety cap: reject absurdly large frames (protocol desync guard)
JPEG_SOI = b'\xFF\xD8'     # JPEG start-of-image marker

class Client:
    def __init__(self, *args, **kwargs):
        
        self.stop_video = False       # allow external code to stop the video thread
        self.video_debug = False      # set to True if you want full debug spam; set to False for quiet and only occasional warnings

        # Core features
        self.face = Face()
        self.pid = Incremental_PID(1, 0, 0.0025)

        # State flags used by MainMT
        self.tcp_flag = False           # True once command socket connected by MainMT.receive_instruction()
        self.video_flag = True          # Frame handoff flag (producer→consumer), set False when new image ready
        self.ball_flag = False
        self.face_flag = False
        self.face_id = False            # True when Face dialog is active to avoid double-processing

        # Shared frame buffer (numpy BGR image); empty string until first decode
        self.image = ''

        # Sockets / stream handles
        self.client_socket1 = None      # Command/telemetry socket (5001)
        self.client_socket = None       # Video socket (8001)
        self.connection = None          # File-like object from client_socket.makefile('rb')

        # Cooperative control for video receiving thread
        self.video_thread_running = False

        # Optional: last error string for UI to inspect (MainMT currently prints from thread)
        self.video_last_error = ""

        # Timestamp of the last received video frame, for stall detection
        self.video_last_frame_ts = 0.0

        # NEW: guard access to image/video_flag from GUI thread
        self.image_lock = threading.Lock()

        # NEW: counters for debug
        self.frames_produced = 0
        self.frames_displayed = 0

        # NEW: clean shutdown flags
        self.instruction_thread_running = False

        # Bind external function as an instance method (so self.client.Looking_for_the_ball() works)
        # Removed dynamic binding of external Looking_for_the_ball.
        # The class's own method will be used until BallTracking.py is production-ready.

        print("LOADED Client MODULE FROM:", __file__)   # to confirm correct file "Client.py" used

    # ---------------------------------------------------------------------------
    # Lifecycle helpers used by MainMT
    # ---------------------------------------------------------------------------
    def turn_on_client(self, ip):
        """
        Prepare fresh sockets for both channels. Connection is performed in:
          - MainMT.receive_instruction(...) for port 5001, and
          - self.receiving_video(ip) thread for port 8001.
        """
        # Ensure any previous sockets are closed before recreating
        self.turn_off_client()

        # Fresh instances (not yet connected)
        self.client_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print(f"... Preparing connection to {ip} (cmd:{CMD_PORT}, video:{VIDEO_PORT}) ...")

    def turn_off_client(self):
        """
        Safely close all network connections with detailed logging.
        This is safe to call multiple times.
        """
        try:
            # Ask the video thread loop to exit cooperatively
            self.video_thread_running = False

            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception as e:
                    print(f"[DEBUG] Error closing video connection stream: {e}")
                self.connection = None

            if self.client_socket1 is not None:
                try:
                    self.client_socket1.close()
                except Exception as e:
                    print(f"[DEBUG] Error closing command socket: {e}")
                self.client_socket1 = None

            if self.client_socket is not None:
                try:
                    self.client_socket.close()
                except Exception as e:
                    print(f"[DEBUG] Error closing video socket: {e}")
                self.client_socket = None
        except Exception as e:
            print(f"[DEBUG] Unexpected exception during socket close: {e}")

    # ---------------------------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------------------------
    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """
        Receive exactly n bytes from a raw socket.
        Socket timeout will be retried (non-fatal) while video_thread_running is True.
        Prints a stall debug message if no frame has arrived for >2s.
        """
        buf = bytearray(n)
        mv = memoryview(buf)
        got = 0
        while got < n:
            try:
                r = sock.recv_into(mv[got:], n - got)
            except socket.timeout:
                if not self.video_thread_running:
                    raise ConnectionError("Stopped while waiting for data . self.video_thread_running is False")
                # stall debug (once per ~2s)
                if self.video_last_frame_ts:
                    silent_for = time.time() - self.video_last_frame_ts
                    if silent_for > 2.0:
                        print(f"[DEBUG] Video stall ~{silent_for:.1f}s (still waiting for data) \r \n")
                        # avoid spamming: bump timestamp slightly
                        self.video_last_frame_ts = time.time() - 1.0
                continue
            if r == 0:
                raise ConnectionError("Socket closed while receiving data")
            got += r
        return bytes(buf)

    def _read_len(self, sock: socket.socket) -> int:
        """Try 4B <I, then 8B <Q if not sane."""
        hdr4 = self._recv_exact(sock, 4)
        n32 = struct.unpack('<I', hdr4)[0]
        if 0 < n32 <= MAX_FRAME:
            return n32
        hdr8 = hdr4 + self._recv_exact(sock, 4)
        n64 = struct.unpack('<Q', hdr8)[0]
        if 0 < n64 <= MAX_FRAME:
            return n64
        raise ValueError(f"Invalid frame length (32={n32}, 64={n64})")

    # ---------------------------------------------------------------------------
    # Vision helpers
    # ---------------------------------------------------------------------------
    def Looking_for_the_ball(self):
        """
        Simple red-ball tracker. When active (ball_flag True and face_id False),
        it issues movement commands based on target position and apparent distance.
        """
        MIN_RADIUS = 10
        THRESHOLD_LOW = (0, 140, 140)       # HSV lower bound for red
        THRESHOLD_HIGH = (5, 255, 255)      # HSV upper bound for red

        img_filter = cv2.GaussianBlur(self.image.copy(), (3, 3), 0)
        img_filter = cv2.cvtColor(img_filter, cv2.COLOR_BGR2HSV)
        img_binary = cv2.inRange(img_filter.copy(), THRESHOLD_LOW, THRESHOLD_HIGH)
        img_binary = cv2.dilate(img_binary, None, iterations=1)
        contours = cv2.findContours(img_binary.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        center = None
        radius = 0
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            if M["m00"] > 0:
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                if radius < MIN_RADIUS:
                    center = None

        if center is not None:
            cv2.circle(self.image, center, int(radius), (0, 255, 0))
            D = round(2700 / (2 * radius))  # crude distance estimate in cm
            x = self.pid.PID_compute(center[0])
            d = self.pid.PID_compute(D)
            if radius > 15:
                if d < 20:
                    command = cmd.CMD_MOVE_BACKWARD + "#" + self.move_speed + '\n'
                    self.send_data(command)
                elif d > 30:
                    command = cmd.CMD_MOVE_FORWARD + "#" + self.move_speed + '\n'
                    self.send_data(command)
                else:
                    if x < 70:
                        command = cmd.CMD_TURN_LEFT + "#" + self.move_speed + '\n'
                        self.send_data(command)
                    elif x > 270:
                        command = cmd.CMD_TURN_RIGHT + "#" + self.move_speed + '\n'
                        self.send_data(command)
                    else:
                        command = cmd.CMD_MOVE_STOP + "#" + self.move_speed + '\n'
                        self.send_data(command)
        else:
            command = cmd.CMD_MOVE_STOP + "#" + self.move_speed + '\n'
            self.send_data(command)

    # ---------------------------------------------------------------------------
    # Video thread (resilient)
    # ---------------------------------------------------------------------------
    def receiving_video(self, ip: str):
        """
        Background video thread with automatic reconnect.
        It never exits on transient errors/timeouts; it only stops when video_thread_running is set False.
        """
        self.video_last_error = ""
        self.video_thread_running = True
        frame_count = 0

        while self.video_thread_running and not self.stop_video:        
            # ---------- connect phase ----------
            self.connection = None  # not ready until connect succeeds
            if self.client_socket is not None:
                try:
                    self.client_socket.close()
                except Exception:
                    pass
                self.client_socket = None

            connected = False
            for attempt in range(1, CONNECT_RETRIES + 1):
                if not self.video_thread_running:
                    break
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # create fresh socket, fresh socket means no stale state . 
                    s.settimeout(CONNECT_TIMEOUT_S)                         # set connect timeout to avoid hanging indefinitely, which is 5 seconds now
                    if self.video_debug:
                        print(f"[DEBUG] Video: connecting to {ip}:{VIDEO_PORT} (attempt {attempt}/{CONNECT_RETRIES})")
                    s.connect((ip, VIDEO_PORT))                             # connect to video port 8001
                    s.settimeout(READ_TIMEOUT_S)                            # set read timeout to detect stalls , which is 5 seconds now
                    self.client_socket = s                                  # mark readiness with raw socket . where s is the connected socket 
                    self.connection = s                                     # mark readiness with raw socket
                    if self.video_debug:
                        print("[DEBUG] Video: connected and streaming")
                    connected = True
                    break
                except Exception as e:
                    print(f"[WARN] Video connect failed: {e}")
                    time.sleep(RETRY_DELAY_S)

            if not connected:
                # Could not connect; wait a bit and try again
                if not self.video_thread_running:
                    break
                time.sleep(1.0)
                continue

            # ---------- streaming phase ----------
            bad_jpeg = 0
            try:
                while self.video_thread_running and self.client_socket is not None:
                    ln = self._read_len(self.client_socket)
                    jpg = self._recv_exact(self.client_socket, ln)

                    # JPEG SOI sanity
                    if not (len(jpg) >= 2 and jpg[0] == 0xFF and jpg[1] == 0xD8):
                        bad_jpeg += 1
                        if bad_jpeg >= 3:
                            print("[WARN] Video: multiple invalid frames; reconnecting ...")
                            raise ConnectionError("Invalid JPEG")
                        continue

                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        bad_jpeg += 1
                        if bad_jpeg >= 3:
                            print("[WARN] Video: decoder failed repeatedly; reconnecting ...")
                            raise ConnectionError("Decode failed")
                        continue
                    bad_jpeg = 0

                    # Optional processing (ball/face) works on a local copy
                    work = frame
                    if self.ball_flag and not self.face_id:
                        self.image = work.copy()  # temporary publish to let tracker see it
                        self.Looking_for_the_ball()
                        work = self.image
                    elif self.face_flag and not self.face_id:
                        self.image = work.copy()
                        self.face.face_detect(self.image)
                        work = self.image

                    # Atomic publish to GUI
                    with self.image_lock:
                        self.image = work.copy()  # publish a copy to avoid GUI races
                        self.video_flag = False   # signal: fresh frame available

                    # Optional: run ball tracking here when enabled
                    if getattr(self, "ball_flag", False):
                        # tracker reads/writes self.image under lock
                        with self.image_lock:
                            self.image = frame.copy()
                        # Call the class method directly (external override disabled)
                        self.Looking_for_the_ball()
                    else:
                        with self.image_lock:
                            self.image = frame
                    self.video_flag = False
                    self.video_last_frame_ts = time.time()
                    frame_count += 1
                    self.frames_produced += 1
                    if (frame_count % 120) == 0:    # 
                        # producer heartbeat
                        # print(f"[DEBUG][Video] frames_produced={self.frames_produced}\r")
                        pass
            except (ConnectionError, ValueError, OSError) as e:
                # Any stream problem → close and reconnect
                if self.video_debug:
                    print(f"[WARN] Video stream error: {e} -> reconnecting ...")
                else:
                    # print a short, throttled message every N seconds or so
                    now = time.time()
                    if now - getattr(self, "_last_video_error_ts", 0) > 10:     # throttle to once per 10s , to avoid spamming and annoying user in CLI mode .
                        print("[WARN] Video stream error (muted, enable video_debug for details)")
                        self._last_video_error_ts = now

            except Exception as e:
                print(f"[DEBUG] Video loop unexpected error: {e} -> reconnecting ...")
            finally:
                # mark not ready and close socket before next attempt
                try:
                    if self.client_socket:
                        self.client_socket.close()
                except Exception:
                    pass
                self.client_socket = None
                self.connection = None

                # small backoff to avoid tight loop on persistent failure
                if self.video_thread_running:
                    time.sleep(0.3)

        print("[DEBUG] Video receiving thread exiting cleanly")

    # ---------------------------------------------------------------------------
    # Command channel helpers (port 5001)
    # ---------------------------------------------------------------------------
    def send_data(self, data):
        """Send command string to robot via command socket (5001). Silently ignore if not connected."""
        if self.tcp_flag and self.client_socket1 is not None:
            try:
                self.client_socket1.send(data.encode('utf-8'))
            except Exception as e:
                print(f"[DEBUG] send_data error: {e}")

    def receive_data(self):
        """Receive response data from robot command socket."""
        data = ""
        if self.tcp_flag and self.client_socket1 is not None:
            try:
                data = self.client_socket1.recv(1024).decode('utf-8')
            except Exception as e:
                print(f"[DEBUG] receive_data error: {e}")
        return data
