#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 Project : Freenove Robot Dog - Enhanced Video Client (Mac)
 File   : mtDogLogicMixin.py
 Author : MT & Copilot ChatGPT

 v2.14  (2026-02-02 20:31)    : Add IMU polling + attitude parsing for client telemetry.
 v2.13  (2026-02-01)
     • Fix Client import path (use legacy/Client.py).
 v2.12  (2026-01-22)
     • Log server responses to mtDogMain.log via the centralized log hook.
     • Guard STOP during FULL close-enough relax/off sequence.
 v2.11  (2026-01-22)
     • Added centralized command send hook to support UI command feed + logging.

 v2.10  (2025-12-01)
   • Extracted Dog logic (network, telemetry, motion, buzzer, LEDs)
     into a mixin class to keep mtDogMain.py focused on UI / video.
   • All functions here assume they are mixed into a QWidget subclass
     that defines the necessary attributes (see mtDogMain.CameraWindow).

 Notes:
   - This mixin is purely logic/threads/commands; it has no direct
     dependency on Qt widgets (labels, buttons, etc.).
   - CameraWindow in mtDogMain.py inherits this mixin.
===============================================================================
"""

import socket
import threading
import time
import re

from controllers.dog_command_controller import COMMAND as CMD
from legacy.Client import Client


class DogLogicMixin:
    """
    Mixin providing:
      • ping_ip / test_tcp_port
      • periodic_server_check / server_check_worker
      • Dog client start/stop
      • Telemetry polling and parsing
      • Buzzer / LED patterns
      • Motion / Play / Calib buttons
    """

    # ==================================================================
    # Network helpers & status checks
    # ==================================================================
    def _send_cmd(self, payload: str, tag: str = "CMD") -> bool:
        """Send a raw command payload to Dog server and record it for UI/logging."""
        if self.dog_client is None or not getattr(self.dog_client, "tcp_flag", False):
            return False
        try:
            self.dog_client.send_data(str(payload))
            try:
                if hasattr(self, "_log_cmd"):
                    self._log_cmd(str(payload), tag=tag)
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[CMD] send failed: {e}")
            return False
    def ping_ip(self, ip: str) -> bool:
        """Simple ICMP ping wrapper used as a basic liveness check."""
        import subprocess  # kept local to avoid global dependency
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "0.3", ip],
                capture_output=True,
                text=True,
            )
            ok = result.returncode == 0
            
            # Smart logging: Only print on state change to avoid spam
            if not hasattr(self, "_ping_cache"):
                self._ping_cache = {}
            
            last_ok = self._ping_cache.get(ip)
            if last_ok != ok:
                print(f"[PING] IP {ip}: {'OK' if ok else 'NOT reachable'}")
                self._ping_cache[ip] = ok
            
            return ok
        except Exception as e:
            print(f"[PING] Ping failed: {e}")
            return False

    def test_tcp_port(self, ip: str, port: int) -> bool:
        """Short TCP connect/poke used to check if a given port is accepting."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect((ip, port))
            s.close()
            print(f"[PORT] {ip}:{port} OK (poke success).")
            return True
        except Exception:
            print(f"[PORT] {ip}:{port} FAILED (poke failed).")
            return False

    def periodic_server_check(self):
        """
        Background status check, called every few seconds by server_check_worker.

        DOG MODE:
          - Trust fresh frames when we see them (dog_has_recent_frame).
          - If no recent frames:
              · ping IP.
              · If IP fails → all red, telemetry invalid.
              · If IP OK → rely on command flag + frame age to detect STALL.

        MAC MODE:
          - Ping IP always.
          - Control+Video ports via test_tcp_port().
          - No commands are sent in Mac mode (video-only).
        """
        now = time.time()

        # ---------- DOG MODE ----------
        if self.use_dog_video:
            if self.dog_has_recent_frame:
                self.dog_connected = True
                self.server_ip_ok = True
                self.server_control_ok = True
                self.server_video_ok = True
                self.video_stall = False
                self.dog_has_recent_frame = False
                return

            ip_ok = self.ping_ip(self.ip)
            self.server_ip_ok = ip_ok

            if not ip_ok:
                self.server_control_ok = False
                self.server_video_ok = False
                self.video_stall = False
                self.dog_connected = False
                self.telemetry_valid = False
                return

            ctrl_ok = (
                self.dog_client is not None
                and getattr(self.dog_client, "tcp_flag", False)
            )
            self.server_control_ok = ctrl_ok

            if (
                ctrl_ok
                and self.dog_last_frame_time is not None
                and now - self.dog_last_frame_time > 2.0
            ):
                self.server_video_ok = True
                self.video_stall = True
            else:
                self.server_video_ok = (ip_ok and ctrl_ok)
                self.video_stall = False

            self.dog_connected = (
                self.server_ip_ok
                and self.server_control_ok
                and self.server_video_ok
                and not self.video_stall
            )
            return

        # ---------- MAC MODE (video-only) ----------
        ip_ok = self.ping_ip(self.ip)
        self.server_ip_ok = ip_ok

        if not ip_ok:
            self.server_control_ok = False
            self.server_video_ok = False
            self.video_stall = False
            self.dog_connected = False
            self.telemetry_valid = False
            return

        ctrl_ok = self.test_tcp_port(self.ip, self.control_port)
        video_ok = self.test_tcp_port(self.ip, self.video_port)

        self.server_control_ok = ctrl_ok
        self.server_video_ok = video_ok
        self.video_stall = False
        self.dog_connected = ip_ok and ctrl_ok and video_ok

    def server_check_worker(self):
        """Thread function: periodically call periodic_server_check()."""
        while not self.stop_server_check:
            try:
                self.periodic_server_check()
            except Exception as e:
                print(f"[CHECK] periodic_server_check error: {e}")
            time.sleep(3.0)

    # ==================================================================
    # Dog client & telemetry
    # ==================================================================
    def start_dog_client(self):
        """
        Start the Freenove Client object and its video + command threads.
        Assumes:
          • self.ip
          • self.control_port
        are set by the owner (CameraWindow).
        """
        self.stop_cmd_thread = False
        self.dog_client = Client()
        try:
            self.dog_client.turn_on_client(self.ip)
        except Exception as e:
            print(f"[DOG] Warning: turn_on_client failed: {e}")

        # Video thread from Freenove Client
        self.video_thread = threading.Thread(
            target=self.dog_client.receiving_video,
            args=(self.ip,),
            daemon=True,
        )
        self.video_thread.start()

        # Command/telemetry receiver thread
        self.cmd_thread = threading.Thread(
            target=self.command_receiver_worker,
            daemon=True,
        )
        self.cmd_thread.start()

    def shutdown_dog_client(self):
        """Cleanly shut down the Dog client when switching to Mac video."""
        print("[DOG] Shutting down Dog client (Dog→Mac).")
        self.stop_cmd_thread = True

        if self.dog_client is not None:
            try:
                if hasattr(self.dog_client, "turn_off_client"):
                    self.dog_client.turn_off_client()
            except Exception as e:
                print(f"[DOG] Error in turn_off_client: {e}")

        self.dog_client = None
        self.video_thread = None
        self.cmd_thread = None
        self.last_dog_frame = None
        self.dog_last_frame_time = None
        self.dog_has_recent_frame = False
        self.video_stall = False

    def poll_telemetry(self):
        """
        Periodic telemetry poll (1 Hz) in Dog mode.
        Owner (CameraWindow) hooks this to a QTimer.
        """
        if not self.use_dog_video:
            return
        if self.dog_client is None:
            return
        if not getattr(self.dog_client, "tcp_flag", False):
            return

        try:
            self._send_cmd(CMD.CMD_POWER + "\n", tag="TEL")
            self._send_cmd(CMD.CMD_SONIC + "\n", tag="TEL")
            # Working/rest timer (firmware-side 180s work / 60s rest rule)
            # This drives the "<left>s  Resting  <right>s" overlay in mtDogMain.
            self._send_cmd(CMD.CMD_WORKING_TIME + "\n", tag="TEL")
        except Exception as e:
            print(f"[TEL] send telemetry failed: {e}")

        self.check_low_voltage_beep()

    def poll_imu(self):
        """
        Periodic IMU attitude poll (default 2 Hz) in Dog mode.
        """
        if not self.use_dog_video:
            return
        if self.dog_client is None:
            return
        if not getattr(self.dog_client, "tcp_flag", False):
            return

        try:
            self._send_cmd(CMD.CMD_ATTITUDE + "\n", tag="IMU")
        except Exception as e:
            print(f"[IMU] send attitude failed: {e}")

    def command_receiver_worker(self):
        """
        Connect to Dog command port (5001) and parse messages line-by-line.
        """
        ip = self.ip
        port = self.control_port

        while not self.stop_cmd_thread and not self.stop_server_check:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                print(f"[CMD] Connecting to {ip}:{port} ...")
                sock.connect((ip, port))
                sock.settimeout(2.0)

                if self.dog_client is not None:
                    self.dog_client.client_socket1 = sock
                    self.dog_client.tcp_flag = True
                print("[CMD] Command channel connected.")

                buf = ""
                while not self.stop_cmd_thread and not self.stop_server_check:
                    try:
                        chunk = sock.recv(1024)
                        if not chunk:
                            raise ConnectionError("command socket closed by peer")
                        buf += chunk.decode("utf-8", errors="ignore")
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            line = line.strip()
                            if line:
                                self.handle_cmd_line(line)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[CMD] recv error: {e}")
                        break
            except Exception as e:
                print(f"[CMD] command channel error: {e} – reconnecting in 2s ...")
            finally:
                try:
                    if sock is not None:
                        sock.close()
                except Exception:
                    pass
                if self.dog_client is not None:
                    self.dog_client.tcp_flag = False

            if self.stop_cmd_thread or self.stop_server_check:
                break
            time.sleep(2.0)

    def _first_float(self, tokens):
        """Return the first valid float found inside a list of tokens."""
        for t in tokens:
            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", t)
            if m:
                try:
                    return float(m.group(0))
                except ValueError:
                    pass
        return None

    def handle_cmd_line(self, line: str):
        """
        Parse a single text line from the Dog server (POWER / SONIC).
        """
        upper = line.upper()
        parts = [p.strip() for p in line.split("#")]
        if not parts:
            return

        try:
            if hasattr(self, "_log_cmd"):
                self._log_cmd(line, tag="SVR")
        except Exception:
            pass

        # Normalize key: allow both CMD_FOO and FOO
        key = parts[0].strip()
        key_upper = key.upper()
        if key_upper.startswith("CMD_"):
            key_upper = key_upper[4:]

        # Some firmwares use alternate separators (e.g. WORKING_TIME:12,34).
        # Normalize to known keys when the prefix matches.
        if key_upper.startswith("WORKING_TIME"):
            key_upper = "WORKING_TIME"
        elif key_upper.startswith("STATE"):
            key_upper = "STATE"
        elif key_upper.startswith("MODE"):
            key_upper = "MODE"
        elif key_upper.startswith("ACTION"):
            key_upper = "ACTION"
        elif key_upper.startswith("RELAX"):
            key_upper = "RELAX"

        if any(k in upper for k in ("POWER", "VOLT", "BAT")):
            v = self._first_float(parts[1:])
            if v is not None:
                self.battery_v = v
                self.telemetry_valid = True
                self.last_telemetry_ok_time = time.time()
            return

        if any(k in upper for k in ("SONIC", "DIST", "RANGE")):
            d = self._first_float(parts[1:])
            if d is not None:
                self.distance_cm = d
                self.telemetry_valid = True
                self.last_telemetry_ok_time = time.time()
            return

        if any(k in upper for k in ("ATTITUDE", "IMU")):
            roll = None
            pitch = None
            yaw = None

            # Prefer labeled tokens when the firmware includes R/P/Y tags.
            for tok in parts[1:]:
                tok_upper = tok.upper()
                val = self._first_float([tok])
                if val is None:
                    continue
                if "ROLL" in tok_upper or tok_upper.startswith("R"):
                    roll = val
                elif "PITCH" in tok_upper or tok_upper.startswith("P"):
                    pitch = val
                elif "YAW" in tok_upper or tok_upper.startswith("Y"):
                    yaw = val

            # If we still don't have full values, parse labeled values from the full line.
            if roll is None or pitch is None or yaw is None:
                try:
                    matches = re.findall(
                        r"(roll|pitch|yaw)\s*[:=]\s*([-+]?[0-9]*\.?[0-9]+)",
                        line,
                        flags=re.IGNORECASE,
                    )
                except Exception:
                    matches = []
                for name, val_str in matches:
                    try:
                        val = float(val_str)
                    except Exception:
                        continue
                    n = name.lower()
                    if n == "roll":
                        roll = val
                    elif n == "pitch":
                        pitch = val
                    elif n == "yaw":
                        yaw = val

            # Final fallback: take the first 3 floats from the line.
            if roll is None or pitch is None or yaw is None:
                nums = []
                for m in re.findall(r"[-+]?[0-9]*\.?[0-9]+", line):
                    try:
                        nums.append(float(m))
                    except Exception:
                        pass
                if len(nums) >= 3:
                    roll, pitch, yaw = nums[0], nums[1], nums[2]

            if roll is None or pitch is None or yaw is None:
                return

            now = time.time()
            alpha = float(getattr(self, "imu_smoothing_alpha", 0.35))
            try:
                if float(getattr(self, "imu_last_ts", 0.0)) > 0.0:
                    self.imu_roll = float(self.imu_roll) + alpha * (float(roll) - float(self.imu_roll))
                    self.imu_pitch = float(self.imu_pitch) + alpha * (float(pitch) - float(self.imu_pitch))
                    self.imu_yaw = float(self.imu_yaw) + alpha * (float(yaw) - float(self.imu_yaw))
                else:
                    self.imu_roll = float(roll)
                    self.imu_pitch = float(pitch)
                    self.imu_yaw = float(yaw)
            except Exception:
                self.imu_roll = float(roll)
                self.imu_pitch = float(pitch)
                self.imu_yaw = float(yaw)

            prev_ts = getattr(self, "_imu_prev_ts", None)
            if isinstance(prev_ts, (int, float)) and prev_ts > 0:
                dt = now - float(prev_ts)
                if 0.0 < dt < 5.0:
                    hz = 1.0 / dt
                    try:
                        self.imu_hz = (0.7 * float(self.imu_hz)) + (0.3 * hz)
                    except Exception:
                        self.imu_hz = hz
            self._imu_prev_ts = float(now)
            self.imu_last_ts = float(now)
            return

        # Working/rest timer + simple state text.
        # Firmware typically enforces: 180s working, then 60s resting.
        # Expected variants seen across versions:
        #   CMD_WORKING_TIME#<left>#<state>#<right>
        #   WORKING_TIME#<left>#<right>
        #   STATE#Resting
        if key_upper in ("WORKING_TIME", "STATE", "MODE", "ACTION", "RELAX"):
            # STATE / MODE / ACTION: just a text label
            if key_upper in ("STATE", "MODE", "ACTION"):
                if len(parts) > 1:
                    state = parts[1].strip()
                elif ":" in line:
                    state = line.split(":", 1)[1].strip()
                else:
                    state = ""
                # Keep the work/rest overlay stable; store this separately.
                if state:
                    self.dog_state_name = state
                return

            # RELAX: firmware often replies RELAX#0 or RELAX#1 ("Too tired...")
            if key_upper == "RELAX":
                val = parts[1].strip() if len(parts) > 1 else ""
                if val == "1":
                    self.dog_state_name = "Too tired..."
                else:
                    # Prefer a human-friendly default
                    self.dog_state_name = "Resting"
                return

            # WORKING_TIME: best-effort parsing for left/state/right
            left_s = None
            right_s = None
            state = None

            # If we have explicit 3-payload form, prefer it.
            # e.g. WORKING_TIME#12#Resting#34
            if len(parts) >= 4:
                try:
                    left_s = int(float(parts[1]))
                except Exception:
                    left_s = None
                state = parts[2].strip() or None
                try:
                    right_s = int(float(parts[3]))
                except Exception:
                    right_s = None
            else:
                # Otherwise: scrape integers from payload tokens.
                ints: list[int] = []
                for tok in parts[1:]:
                    for m in re.findall(r"[-+]?\d+", tok):
                        try:
                            ints.append(int(m))
                        except Exception:
                            pass
                    s = re.sub(r"[-+]?\d+", "", tok).strip(" ,:\t")
                    if s:
                        state = s

                # If firmware packs everything after ':' into the key token.
                if not ints and ":" in line:
                    for m in re.findall(r"[-+]?\d+", line):
                        try:
                            ints.append(int(m))
                        except Exception:
                            pass

                if len(ints) >= 2:
                    left_s, right_s = ints[0], ints[1]
                elif len(ints) == 1:
                    # Some firmwares only report one side.
                    right_s = ints[0]

            if left_s is not None:
                self.left_state_seconds = max(0, int(left_s))
            if right_s is not None:
                self.right_state_seconds = max(0, int(right_s))

            # Some firmwares append transient text (e.g., "too tired...") here.
            # Keep the on-screen overlay stable (WORK/REST) and store any extra
            # wording separately.
            if state:
                self.dog_state_name = state
            if 0 < int(self.right_state_seconds) < 60:
                self.state_name = "REST"
            elif int(self.left_state_seconds) < 180:
                self.state_name = "WORK"
            else:
                self.state_name = "REST"

            # Track update time and infer which counters are ticking so the overlay
            # can update smoothly (even if firmware repeats values briefly).
            now = time.time()
            prev_left = getattr(self, "_working_time_prev_left", None)
            prev_right = getattr(self, "_working_time_prev_right", None)
            dir_left = int(getattr(self, "_working_time_left_dir", 0) or 0)
            dir_right = int(getattr(self, "_working_time_right_dir", 0) or 0)

            if isinstance(prev_left, int) and left_s is not None:
                dl = int(left_s) - int(prev_left)
                if dl != 0 and abs(dl) <= 5:
                    dir_left = 1 if dl > 0 else -1
            if isinstance(prev_right, int) and right_s is not None:
                dr = int(right_s) - int(prev_right)
                if dr != 0 and abs(dr) <= 5:
                    dir_right = 1 if dr > 0 else -1

            # Heuristic defaults when firmware isn't changing (common at boundaries):
            # - If left is at max (180), we're likely resting → tick right up.
            # - If right is 0 and left < 180, we're likely working → tick left up.
            if dir_left == 0 and dir_right == 0:
                try:
                    if self.left_state_seconds >= 180 and self.right_state_seconds < 60:
                        dir_right = 1
                        dir_left = 0
                    elif self.right_state_seconds == 0 and self.left_state_seconds < 180:
                        dir_left = 1
                        dir_right = 0
                except Exception:
                    pass

            self._working_time_prev_left = int(self.left_state_seconds)
            self._working_time_prev_right = int(self.right_state_seconds)
            self._working_time_left_dir = int(dir_left)
            self._working_time_right_dir = int(dir_right)
            self._working_time_last_rx_ts = float(now)

            # Anchor for interpolation: only advance the anchor when the firmware
            # values actually change; this avoids display "sticking" when packets
            # repeat the same numbers around state boundaries.
            anchor_left = getattr(self, "_working_time_anchor_left", None)
            anchor_right = getattr(self, "_working_time_anchor_right", None)
            if (
                not isinstance(anchor_left, int)
                or not isinstance(anchor_right, int)
                or int(anchor_left) != int(self.left_state_seconds)
                or int(anchor_right) != int(self.right_state_seconds)
                or not isinstance(getattr(self, "_working_time_anchor_ts", None), (int, float))
            ):
                self._working_time_anchor_left = int(self.left_state_seconds)
                self._working_time_anchor_right = int(self.right_state_seconds)
                self._working_time_anchor_ts = float(now)

            # Optional low-rate debug to verify REST counters are updating.
            if getattr(self, "debug_working_time", False):
                try:
                    print(
                        f"[TEL] WORKING_TIME -> {self.left_state_seconds}s {self.state_name} {self.right_state_seconds}s (raw: {line})"
                    )
                except Exception:
                    pass
            return

    # ==================================================================
    # Beep & low-battery helpers
    # ==================================================================
    def schedule_dog_entry_beep(self):
        """When entering Dog mode, play a 2-beep confirmation."""
        def worker():
            start = time.time()
            while time.time() - start < 3.0:
                if (
                    self.dog_client is not None
                    and getattr(self.dog_client, "tcp_flag", False)
                ):
                    break
                time.sleep(0.1)
            if self.dog_client is None or not getattr(
                self.dog_client, "tcp_flag", False
            ):
                return
            self._beep_pattern(beeps=2)

        threading.Thread(target=worker, daemon=True).start()

    def _beep_pattern(self, beeps=1, on_s=0.15, off_s=0.15):
        """Dog-mode buzzer helper (on_s/off_s in seconds)."""
        if not self.use_dog_video:
            return
        if self.dog_client is None:
            return

        def run_dog():
            for _ in range(beeps):
                if not getattr(self.dog_client, "tcp_flag", False):
                    break
                try:
                    self._send_cmd(CMD.CMD_BUZZER + "#1\n", tag="BEEP")
                    time.sleep(on_s)
                    self._send_cmd(CMD.CMD_BUZZER + "#0\n", tag="BEEP")
                    time.sleep(off_s)
                except Exception as e:
                    print(f"[BEEP] error while sending buzzer: {e}")
                    break

        threading.Thread(target=run_dog, daemon=True).start()

    def _led_flash(self, flashes=1, on_s=0.25, off_s=0.25, color=(255, 0, 0)):
        """
        Generic LED flash helper (Dog mode only).

        Args:
            flashes: number of flashes
            on_s: seconds LED stays on per flash
            off_s: seconds between flashes
            color: (r, g, b)
        """
        if not self.use_dog_video:
            return
        if self.dog_client is None or not getattr(self.dog_client, "tcp_flag", False):
            return

        try:
            r, g, b = color
        except Exception:
            r, g, b = 255, 0, 0

        r = int(max(0, min(255, r)))
        g = int(max(0, min(255, g)))
        b = int(max(0, min(255, b)))

        def run_led():
            try:
                for _ in range(int(max(1, flashes))):
                    self._send_cmd(CMD.CMD_LED_MOD + "#1\n", tag="LED")
                    self._send_cmd(f"{CMD.CMD_LED}#255#{r}#{g}#{b}\n", tag="LED")
                    time.sleep(on_s)
                    self._send_cmd(CMD.CMD_LED_MOD + "#0\n", tag="LED")
                    time.sleep(off_s)
            except Exception as e:
                print(f"[LED] flash error: {e}")

        threading.Thread(target=run_led, daemon=True).start()

    def _low_batt_led_flash(self, flashes=1, on_s=0.25, off_s=0.25):
        """
        Low-battery LED alert:
        Quick red flashes on the Dog LEDs (Dog mode only).
        """
        self._led_flash(flashes=flashes, on_s=on_s, off_s=off_s, color=(255, 0, 0))

    def check_low_voltage_beep(self):
        """
        If V <= threshold, trigger a 1 Hz beep + red LED flash in Dog mode.
        """
        if not self.use_dog_video:
            return
        if (
            self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not self.server_control_ok
        ):
            return

        v = self.battery_v
        if v <= 0:
            return

        if v <= self.low_voltage_threshold:
            now = time.time()
            if now - self.last_low_beep_time >= 1.0:
                print(
                    f"[TEL] Low battery ({v:.2f} V) "
                    f"<= {self.low_voltage_threshold:.2f} V"
                )
                self._beep_pattern(beeps=1, on_s=0.25, off_s=0.25)
                self._low_batt_led_flash(flashes=1, on_s=0.25, off_s=0.25)
                self.last_low_beep_time = now

    # ==================================================================
    # Button handlers (Dog-mode only commands)
    # ==================================================================
    def handle_led_button(self):
        """L key / LED: ~2s color cycle using CMD_LED_MOD / CMD_LED."""
        print("[LED] LED pattern requested (Dog mode only).")

        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
        ):
            print("[LED] Skipped (Dog mode inactive or control not ready).")
            return

        colors = [
            (255,   0,   0),
            (255, 128,   0),
            (255, 255,   0),
            (  0, 255,   0),
            (  0, 255, 255),
            (  0,   0, 255),
            (128,   0, 255),
            (255, 255, 255),
        ]

        def run_led():
            try:
                self._send_cmd(CMD.CMD_LED_MOD + "#1\n", tag="LED")
                for r, g, b in colors:
                    cmd = f"{CMD.CMD_LED}#255#{r}#{g}#{b}\n"
                    self._send_cmd(cmd, tag="LED")
                    time.sleep(0.25)
                self._send_cmd(CMD.CMD_LED_MOD + "#0\n", tag="LED")
                print("[LED] LED pattern done.")
            except Exception as e:
                print(f"[LED] LED error: {e}")

        threading.Thread(target=run_led, daemon=True).start()

    def handle_calib_button(self):
        """K key / Calib: send CMD_CALIBRATION."""
        print("[CALIB] Calibration requested.")
        cmd = CMD.CMD_CALIBRATION

        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
        ):
            print("[CALIB] Dog not ready.")
            return

        try:
            self._send_cmd(cmd + "\n", tag="CALIB")
            print("[CALIB] CMD_CALIBRATION sent (Dog mode).")
        except Exception as e:
            print(f"[CALIB] send failed: {e}")

    def handle_play_button(self):
        """P key / Play: simple forward/left/right/backward sequence."""
        print("[PLAY] Play motion requested.")

        play_sequence = [
            CMD.CMD_RELAX,
            CMD.CMD_MOVE_FORWARD,
            CMD.CMD_MOVE_LEFT,
            CMD.CMD_MOVE_RIGHT,
            CMD.CMD_MOVE_BACKWARD,
            CMD.CMD_RELAX,
        ]

        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
        ):
            print("[PLAY] Dog not ready.")
            return

        def execute_dog_sequence():
            try:
                for command in play_sequence:
                    self._send_cmd(command + "\n", tag="PLAY")
                    time.sleep(0.4)
                print("[PLAY] Sequence completed (Dog mode).")
            except Exception as error:
                print(f"[PLAY] Error sending sequence: {error}")

        threading.Thread(target=execute_dog_sequence, daemon=True).start()

    def handle_beep_key(self):
        """B key: 2-beep test."""
        self._beep_pattern(beeps=2)

    def handle_ball_button(self):
        print("[AI] Ball button pressed (placeholder).")

    def handle_face_button(self):
        print("[AI] Face button pressed (placeholder).")

    # ==================================================================
    # Motion command helper
    # ==================================================================
    def send_stop_motion(self, *, force: bool = False):
        """Send a CMD_MOVE_STOP#speed command (used for button release)."""
        try:
            if not force and bool(getattr(self, "_close_enough_latched", False)):
                seq = str(getattr(self, "_close_enough_seq_state", ""))
                if seq in ("relax", "off"):
                    return
        except Exception:
            pass
        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not self.server_control_ok
        ):
            return

        speed = int(getattr(self, "move_speed", 8))
        speed = max(2, min(10, speed))
        payload = f"{CMD.CMD_MOVE_STOP}#{speed}\n"
        try:
            self._send_cmd(payload, tag="CMD")
            print(f"[CMD] (Dog) STOP → {payload.strip()}")
            # Remember last motion so turn logic can avoid redundant stops.
            self._last_sent_motion_cmd_str = CMD.CMD_MOVE_STOP
            self._last_sent_motion_ts = time.time()
            self._last_sent_motion_speed = int(speed)
        except Exception as e:
            print(f"[CMD] stop failed: {e}")

    def send_motion_command(self, key_char: str, speed_override: int | None = None):
        """Map W/E/R/S/D/F/C to CMD_* and send in Dog mode.

        speed_override: Optional int speed (2..10) to use for this one command.
        """
        key = key_char.lower()
        cmd_str = None

        if key == "w":
            cmd_str = CMD.CMD_TURN_LEFT
        elif key == "e":
            cmd_str = CMD.CMD_MOVE_FORWARD
        elif key == "r":
            cmd_str = CMD.CMD_TURN_RIGHT
        elif key == "s":
            cmd_str = CMD.CMD_MOVE_LEFT
        elif key == "d":
            cmd_str = CMD.CMD_RELAX
        elif key == "f":
            cmd_str = CMD.CMD_MOVE_RIGHT
        elif key == "c":
            cmd_str = CMD.CMD_MOVE_BACKWARD

        if cmd_str is None:
            return

        # Protocol note (matches Freenove server):
        # Movement/turn/stop commands expect a speed value after '#', e.g. "CMD_TURN_LEFT#8".
        # Relax (and other non-motion commands) are sent without a speed.
        speed = int(speed_override) if speed_override is not None else int(getattr(self, "move_speed", 8))
        speed = max(2, min(10, speed))

        payload = cmd_str + "\n" if cmd_str == CMD.CMD_RELAX else f"{cmd_str}#{speed}\n"

        if (
            not self.use_dog_video
            or self.dog_client is None
            or not getattr(self.dog_client, "tcp_flag", False)
            or not self.server_control_ok
        ):
            print("[CMD] Cannot send motion: Dog/port 5001 not ready.")
            return

        try:
            # Some server/firmware builds behave better if we stop before turning.
            # Do this only when transitioning from a translation into a turn,
            # otherwise it spams STOP on every turn packet.
            if cmd_str in (CMD.CMD_TURN_LEFT, CMD.CMD_TURN_RIGHT):
                last_cmd = getattr(self, "_last_sent_motion_cmd_str", None)
                if last_cmd in (
                    CMD.CMD_MOVE_FORWARD,
                    CMD.CMD_MOVE_BACKWARD,
                    CMD.CMD_MOVE_LEFT,
                    CMD.CMD_MOVE_RIGHT,
                ):
                    stop_payload = f"{CMD.CMD_MOVE_STOP}#{speed}\n"
                    self._send_cmd(stop_payload, tag="CMD")
                    time.sleep(0.05)
                    print(f"[CMD] (Dog) pre-turn → {stop_payload.strip()}")
            self._send_cmd(payload, tag="CMD")
            print(f"[CMD] (Dog) {key.upper()} → {payload.strip()}")

            # Remember last motion packet we sent.
            self._last_sent_motion_cmd_str = cmd_str
            self._last_sent_motion_ts = time.time()
            self._last_sent_motion_speed = int(speed)
            
            # Special case: "D:Relax" also sends beep/LED flash then CMD_STOP_PWM to release servos
            if key == "d":
                # IMPORTANT: do not release servos immediately, or the posture can collapse.
                # Schedule STOP_PWM after a short delay (non-blocking, keeps UI responsive).
                stop_delay_s = 5.0

                # Cancel any previous pending STOP_PWM (avoid stacking timers).
                prev_timer = getattr(self, "_stop_pwm_timer", None)
                try:
                    if prev_timer is not None and prev_timer.is_alive():
                        prev_timer.cancel()
                except Exception:
                    pass

                def _do_stop_pwm():
                    if self.dog_client is None or not getattr(self.dog_client, "tcp_flag", False):
                        return
                    try:
                        # One beep + one LED flash right before releasing servos.
                        # Do this synchronously here so STOP_PWM happens *after* the cue.
                        try:
                            self._send_cmd(CMD.CMD_BUZZER + "#1\n", tag="BEEP")
                            self._send_cmd(CMD.CMD_LED_MOD + "#1\n", tag="LED")
                            # Green flash
                            self._send_cmd(f"{CMD.CMD_LED}#255#0#255#0\n", tag="LED")
                            time.sleep(0.15)
                        finally:
                            self._send_cmd(CMD.CMD_BUZZER + "#0\n", tag="BEEP")
                            self._send_cmd(CMD.CMD_LED_MOD + "#0\n", tag="LED")
                        time.sleep(0.05)
                        self._send_cmd(CMD.CMD_STOP_PWM + "\n", tag="STOP_PWM")
                        print(f"[CMD] (Dog) D → {CMD.CMD_STOP_PWM} (after {stop_delay_s:.1f}s)")
                    except Exception as e:
                        print(f"[CMD] stop_pwm failed: {e}")

                self._stop_pwm_timer = threading.Timer(stop_delay_s, _do_stop_pwm)
                self._stop_pwm_timer.daemon = True
                self._stop_pwm_timer.start()
                print(f"[CMD] (Dog) D → scheduled {CMD.CMD_STOP_PWM} in {stop_delay_s:.1f}s")
        except Exception as e:
            print(f"[CMD] send failed: {e}")
