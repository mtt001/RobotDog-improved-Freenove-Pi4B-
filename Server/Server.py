# -*- coding: utf-8 -*-
"""
Freenove Robot Dog - Server Core Module
File: Server.py   ,Date Created: 2024
Version: 1.1.1   , Author: Freenove

Description:
        Core server module handling TCP communication, video streaming,
        and command processing for the Freenove Robot Dog system.

        Fault-tolerant networking (2026-01):
            - Keeps both ports listening across disconnects:
                    * 8001: video stream (length-prefixed JPEG frames)
                    * 5001: control/telemetry commands
            - Built-in health monitoring (log-only):
                    * Periodically reports LISTEN/CONNECTED states
                    * Detects when a listening socket is missing/closed and re-opens it
                    * Emits clear “what happened” + “how to recover” messages

        Battery protection:
            - Low voltage monitoring with time-based debouncing,
                configurable thresholds, and warning signals (LED + Buzzer).

Version Control:
    v1.3.0  (2026-02-08 09:56)    : Multi-client control socket (5001) with owner arbitration.
        - Accept and serve multiple concurrent control clients with per-client handler threads.
        - Route telemetry/query replies to requesting socket (not global shared connection).
        - Add control-owner guard for write/actuation commands; allow STOP/RELAX safety override.
        - Preserve legacy proprietary MJPEG path on 8001 for original Freenove clients.
    v1.2.1  (2026-02-02 20:31)    : Make CMD_ATTITUDE bidirectional (query + set).
    v1.2.0 - Fault-tolerant server sockets + health monitoring (2026-01-14)
        - Do not close LISTEN sockets after accept; allow clients to reconnect
        - Recover from dropped clients without restarting the whole server
        - Add periodic health logs and auto re-open LISTEN sockets if needed
    v1.1.1 - Added CMD_STOP_PWM command routing; logging of client commands
        - FPS + frame size telemetry during video streaming
    v1.1.0 - Battery monitoring enhancement (2025-12-21)
        - Configurable low voltage threshold (LOW_VOLTAGE_THRESHOLD)
        - Time-based debouncing with 3-second persistence (LOW_VOLTAGE_DEBOUNCE_TIME)
        - Warning signals: red LED flash + buzzer beep on voltage dips
        - Graceful shutdown after sustained low voltage condition
        - Voltage recovery detection and warning reset
    
    v1.0.0 - Initial implementation
        - TCP server for video transmission and commands
        - Camera streaming via picamera
        - Socket-based client communication
        - Hardware interface (LED, Servo, ADC, Buzzer, etc.)
        - Dual-port architecture (8001 for video, 5001 for commands)

Revision History:
    Date        | Version | Author    | Changes
    ------------|---------|-----------|-----------------------------------------------
    2026-02-08  | 1.3.0   | Codex     | Multi-client 5001 + owner arbitration (safe write path)
    2026-01-14  | 1.2.0   | Copilot   | Fault-tolerant ports + health monitoring
    2025-12-21  | 1.1.1   | Freenove  | Added CMD_STOP_PWM, client command logging, FPS/frame size telemetry
    2025-12-21  | 1.1.0   | Freenove  | Battery debouncing & warning signals
    2024-12-21  | 1.0.0   | Freenove  | Initial release

Key Classes:
    - Server: Main server class handling TCP connections and streaming

Key Methods:
    - turn_on_server(): Initialize TCP server sockets
    - turn_off_server(): Close connections
    - transmission_video(): Stream video to connected client
    - receive_instruction(): Process incoming commands
    - get_interface_ip(): Retrieve network interface IP

Dependencies:
    - picamera: Raspberry Pi camera module
    - socket: Network communication
    - threading: Multi-threaded operations
    - Led, Servo, Buzzer, etc.: Hardware control modules
    - Control, ADS7830, Ultrasonic: Sensor/control interfaces

"""

import sys, os, time, traceback
def _sdlog(msg):
    with open('/tmp/smartdog.log','a') as _f:
        _f.write(time.strftime('%F %T ')+str(msg)+'\n')
try:
    # unbuffer so journald shows in realtime too
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception: pass
    _sdlog('START Server.py headless=' + str(os.getenv('SMARTDOG_HEADLESS')))
except Exception as _e:
    pass

# -*- coding: utf-8 -*-
import io
import os
import signal
import time
import fcntl
import socket
import struct
import picamera
import threading
from Led import *
from Servo import *
from Thread import *
from Buzzer import *
from Control import *
from ADS7830 import *
from Ultrasonic import *
from Command import COMMAND as cmd

# Configuration: Low voltage threshold and debounce time
LOW_VOLTAGE_THRESHOLD = 6.1          # Voltage cutoff threshold (V)
LOW_VOLTAGE_DEBOUNCE_TIME = 3.0      # Time to persist before shutdown (seconds)

# Battery monitor behavior
BATTERY_MONITOR_ENABLED = True
BATTERY_POLL_INTERVAL_SEC = 1.0
BATTERY_WARNING_INTERVAL_SEC = 5.0
LOW_BATTERY_RELAX_DELAY_SEC = 3.0    # After low voltage is confirmed, RELAX immediately; STOP_PWM after this delay

# Logging controls (set True to re-enable).
LOG_VIDEO_TELEMETRY = False          # "Video FPS ..." spam during streaming
LOG_BATTERY_STATUS = False           # "Battery voltage: ..." spam on CMD_POWER polling
SUPPRESS_COMMAND_LOGS = {            # Hide per-command logs for very frequent commands
    cmd.CMD_SONIC,
    cmd.CMD_POWER,
    cmd.CMD_LED,
    cmd.CMD_LED_MOD,
    cmd.CMD_BUZZER,
}

# Command sequence debug: correlate RX (server) with EXEC (control)
DEBUG_COMMAND_SEQUENCE = False
SEQUENCE_INCLUDE_SUPPRESSED = False

# Health monitoring / recovery (log-only + socket re-open)
HEALTH_MONITOR_ENABLED = True
HEALTH_LOG_ENABLED = False
HEALTH_LOG_INTERVAL_SEC = 15.0
HEALTH_REOPEN_BACKOFF_SEC = 2.0

MOTION_COMMANDS = {
    cmd.CMD_MOVE_FORWARD,
    cmd.CMD_MOVE_BACKWARD,
    cmd.CMD_MOVE_LEFT,
    cmd.CMD_MOVE_RIGHT,
    cmd.CMD_TURN_LEFT,
    cmd.CMD_TURN_RIGHT,
}

# Multi-client control (5001) policy:
# - Telemetry/read commands can be served per connection.
# - Actuation/write commands are accepted only from the current control owner.
# - Safety commands (STOP/RELAX/STOP_PWM) are accepted from any client.
CTRL_OWNER_TIMEOUT_SEC = 8.0
CTRL_WRITE_COMMANDS = {
    cmd.CMD_MOVE_FORWARD,
    cmd.CMD_MOVE_BACKWARD,
    cmd.CMD_MOVE_LEFT,
    cmd.CMD_MOVE_RIGHT,
    cmd.CMD_TURN_LEFT,
    cmd.CMD_TURN_RIGHT,
    cmd.CMD_HEAD,
    cmd.CMD_HEIGHT,
    cmd.CMD_HORIZON,
    cmd.CMD_CALIBRATION,
    cmd.CMD_BALANCE,
    cmd.CMD_LED,
    cmd.CMD_LED_MOD,
    cmd.CMD_BUZZER,
}
CTRL_SAFETY_OVERRIDE_COMMANDS = {
    cmd.CMD_MOVE_STOP,
    cmd.CMD_RELAX,
    cmd.CMD_STOP_PWM,
}

class Server:

    def __init__(self):
        self.tcp_flag=False
        self.led=Led()
        self.servo=Servo()
        self.adc=ADS7830()
        self.buzzer=Buzzer()
        self.control=Control()
        self.sonic=Ultrasonic()
        self.control.Thread_conditiona.start()
        self.battery_voltage=[8.4,8.4,8.4,8.4,8.4]

        # Battery monitor state
        self._battery_thread = None
        self._adc_lock = threading.Lock()
        self._battery_latest_v = None
        self._battery_last_sample_ts = 0.0
        self._battery_last_warn_ts = 0.0
        self._low_battery_active = False
        self._low_battery_active_since = None
        self._low_battery_relax_queued = False
        self._low_battery_stop_pwm_queued = False
        self._last_low_bat_ignore_ts = 0.0
        
        # Low voltage debouncing state
        self.low_voltage_start_time = None
        self.low_voltage_warning_active = False
        self._cmd_seq = 0

        # Health / fault-tolerance state
        self._health_thread = None
        self._last_health_log_ts = 0.0
        self._last_reopen_attempt_ts = 0.0
        self._video_client_connected = False
        self._ctrl_client_connected = False
        self._ctrl_client_count = 0
        self._last_video_frame_ts = 0.0
        self._last_ctrl_rx_ts = 0.0
        self._video_disconnects = 0
        self._ctrl_disconnects = 0
        self._camera_failures = 0
        self._ctrl_clients = {}
        self._ctrl_clients_lock = threading.Lock()
        self._control_state_lock = threading.Lock()
        self._control_owner_id = None
        self._control_owner_addr = None
        self._control_owner_last_ts = 0.0

    def _fmt_age(self, ts):
        if not ts:
            return "n/a"
        return f"{(time.time() - ts):.1f}s"

    def _client_id(self, addr):
        try:
            return f"{addr[0]}:{addr[1]}"
        except Exception:
            return str(addr)

    def _register_ctrl_client(self, client_id, conn):
        with self._ctrl_clients_lock:
            self._ctrl_clients[client_id] = conn
            self._ctrl_client_count = len(self._ctrl_clients)
            self._ctrl_client_connected = self._ctrl_client_count > 0

    def _unregister_ctrl_client(self, client_id):
        with self._ctrl_clients_lock:
            try:
                self._ctrl_clients.pop(client_id, None)
            except Exception:
                pass
            self._ctrl_client_count = len(self._ctrl_clients)
            self._ctrl_client_connected = self._ctrl_client_count > 0
            if self._control_owner_id == client_id:
                self._control_owner_id = None
                self._control_owner_addr = None
                self._control_owner_last_ts = 0.0

    def _set_control_order(self, order_data, seq, raw):
        with self._control_state_lock:
            self.control.order = list(order_data)
            self.control.order_seq = seq
            self.control.last_rx_seq = seq
            self.control.last_rx_raw = raw
            self.control.last_rx_ts = time.time()
            self.control.timeout = time.time()

    def _touch_control_owner(self, client_id, client_addr):
        now = time.time()
        stale = (now - float(self._control_owner_last_ts or 0.0)) > CTRL_OWNER_TIMEOUT_SEC
        if self._control_owner_id is None or stale:
            self._control_owner_id = client_id
            self._control_owner_addr = client_addr
            self._control_owner_last_ts = now
            return True
        if self._control_owner_id == client_id:
            self._control_owner_last_ts = now
            self._control_owner_addr = client_addr
            return True
        return False

    def _is_control_write_cmd(self, data):
        cmd0 = data[0] if data else ""
        if cmd0 == cmd.CMD_ATTITUDE and len(data) >= 4:
            return True
        return cmd0 in CTRL_WRITE_COMMANDS or cmd0 in CTRL_SAFETY_OVERRIDE_COMMANDS

    def _authorize_control_write(self, client_id, client_addr, data):
        cmd0 = data[0] if data else ""
        if cmd0 in CTRL_SAFETY_OVERRIDE_COMMANDS:
            return True
        ok = self._touch_control_owner(client_id, client_addr)
        return ok

    def _is_socket_open(self, sock):
        try:
            return sock is not None and sock.fileno() != -1
        except Exception:
            return False

    def _open_listeners(self, notify_user=False):
        """Ensure LISTEN sockets exist and are open.

        Safety: when called from the health monitor, use notify_user=False to
        avoid buzzer/LED side effects.
        """
        # Always listen on all interfaces; clients still connect to the Pi's LAN IP.
        HOST = "0.0.0.0"

        if not self._is_socket_open(getattr(self, 'server_socket', None)):
            try:
                self.server_socket = socket.socket()
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind((HOST, 8001))
                self.server_socket.listen(1)
                self.server_socket.settimeout(1.0)
                print("[HEALTH] Video port 8001 LISTEN re-opened (clients may reconnect).")
            except Exception as e:
                print(f"[HEALTH] ERROR reopening video port 8001: {e}")

        if not self._is_socket_open(getattr(self, 'server_socket1', None)):
            try:
                self.server_socket1 = socket.socket()
                self.server_socket1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                self.server_socket1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket1.bind((HOST, 5001))
                self.server_socket1.listen(8)
                self.server_socket1.settimeout(1.0)
                print("[HEALTH] Control port 5001 LISTEN re-opened (clients may reconnect).")
            except Exception as e:
                print(f"[HEALTH] ERROR reopening control port 5001: {e}")

        if notify_user:
            # Notify user: sockets established (double beeps + double blue LED flashes)
            try:
                # Double beeps
                for _ in range(2):
                    self.buzzer.run('1')
                    time.sleep(0.1)
                    self.buzzer.run('0')
                    time.sleep(0.1)
                # Double blue LED flashes
                for _ in range(2):
                    self.led.light([cmd.CMD_LED, '1', '0', '0', '255'])  # Blue on
                    time.sleep(0.2)
                    self.led.light([cmd.CMD_LED, '0', '0', '0', '0'])    # LED off
                    time.sleep(0.2)
            except Exception as e:
                print(f"Server ready notification error: {e}")

    def _health_monitor(self):
        """Periodic log-only monitor. Re-opens LISTEN sockets if they vanish."""
        while True:
            try:
                if not HEALTH_MONITOR_ENABLED:
                    time.sleep(1.0)
                    continue

                if not self.tcp_flag:
                    time.sleep(1.0)
                    continue

                now = time.time()

                # Attempt to re-open sockets if needed, with a small backoff.
                need_reopen = (
                    (not self._is_socket_open(getattr(self, 'server_socket', None)))
                    or (not self._is_socket_open(getattr(self, 'server_socket1', None)))
                )
                if need_reopen and (now - self._last_reopen_attempt_ts) >= HEALTH_REOPEN_BACKOFF_SEC:
                    self._last_reopen_attempt_ts = now
                    if HEALTH_LOG_ENABLED:
                        print(
                            "[HEALTH] Detected missing LISTEN socket(s). "
                            "Auto-reopening ports 8001/5001 now..."
                        )
                        print(
                            "[HEALTH] If this repeats, check: camera busy, low voltage shutdown, "
                            "or restart via 'Code/Server/smartdog.sh restart'."
                        )
                    self._open_listeners(notify_user=False)

                if HEALTH_LOG_ENABLED and (now - self._last_health_log_ts) >= HEALTH_LOG_INTERVAL_SEC:
                    self._last_health_log_ts = now
                    v_listen = self._is_socket_open(getattr(self, 'server_socket', None))
                    c_listen = self._is_socket_open(getattr(self, 'server_socket1', None))
                    print(
                        "[HEALTH] "
                        f"video: {'LISTEN' if v_listen else 'DOWN'} "
                        f"| client={'YES' if self._video_client_connected else 'NO'} "
                        f"| last_frame={self._fmt_age(self._last_video_frame_ts)} "
                        f"| disconnects={self._video_disconnects} "
                        f"| cam_failures={self._camera_failures}"
                    )
                    print(
                        "[HEALTH] "
                        f"control: {'LISTEN' if c_listen else 'DOWN'} "
                        f"| clients={int(getattr(self, '_ctrl_client_count', 0) or 0)} "
                        f"| owner={self._control_owner_id or 'none'} "
                        f"| last_rx={self._fmt_age(self._last_ctrl_rx_ts)} "
                        f"| disconnects={self._ctrl_disconnects}"
                    )
            except Exception as e:
                # Never let the health thread die.
                if HEALTH_LOG_ENABLED:
                    try:
                        print(f"[HEALTH] monitor error: {e}")
                    except Exception:
                        pass
            time.sleep(1.0)

    def _ensure_health_thread(self):
        if self._health_thread is not None and self._health_thread.is_alive():
            return
        self._health_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self._health_thread.start()

    def _ensure_battery_thread(self):
        if not BATTERY_MONITOR_ENABLED:
            return
        if self._battery_thread is not None and self._battery_thread.is_alive():
            return
        self._battery_thread = threading.Thread(target=self._battery_monitor, daemon=True)
        self._battery_thread.start()

    def _read_battery_voltage(self):
        """Read battery voltage from ADC.

        Uses a lock to avoid concurrent I2C reads from multiple threads.
        """
        try:
            with self._adc_lock:
                return round(self.adc.power(0), 2)
        except Exception:
            return None

    def _queue_control_cmd(self, cmd_name):
        """Force a Control command (overwrites current order)."""
        try:
            self.control.order = [cmd_name, '', '', '', '']
            self.control.order_seq = -1
            self.control.last_rx_seq = -1
            self.control.last_rx_raw = f"{cmd_name}#(battery_guard)"
            self.control.last_rx_ts = time.time()
            self.control.timeout = time.time()
        except Exception:
            pass

    def _battery_monitor(self):
        """Background low-voltage guard.

        Requirements:
        - Works even with no client connected.
        - Never shuts down the system and never closes ports.
        - When low-voltage is confirmed (debounced), force RELAX posture, then STOP_PWM after 3s.
        - While low-voltage condition persists, warn every 5s: 2 short beeps + 1 red LED flash.
        """
        while True:
            try:
                if not self.tcp_flag:
                    time.sleep(0.5)
                    continue

                v = self._read_battery_voltage()
                now = time.time()
                if v is not None:
                    self._battery_latest_v = v
                    self._battery_last_sample_ts = now
                    # Keep existing window updated for CMD_POWER replies
                    try:
                        self.battery_voltage.pop(0)
                        self.battery_voltage.append(v)
                    except Exception:
                        pass

                # Update guard state and emit warnings/actions.
                self.battery_reminder(source="monitor")

            except Exception as e:
                try:
                    print(f"[BAT] monitor error: {e}")
                except Exception:
                    pass
            time.sleep(BATTERY_POLL_INTERVAL_SEC)
    def get_interface_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                            0x8915,
                                            struct.pack('256s',b'wlan0'[:15])
                                            )[20:24])

    def turn_on_server(self):
        self._open_listeners(notify_user=True)
        self._ensure_health_thread()
        self._ensure_battery_thread()

    def turn_off_server(self):
        # Close video connection (if present)
        try:
            if getattr(self, "connection", None) is not None:
                self.connection.close()
        except Exception:
            pass
        # Close all control client sockets
        try:
            with self._ctrl_clients_lock:
                for _cid, c in list(self._ctrl_clients.items()):
                    try:
                        c.close()
                    except Exception:
                        pass
                self._ctrl_clients.clear()
                self._ctrl_client_count = 0
                self._ctrl_client_connected = False
        except Exception:
            pass
        # Backward compatibility field
        try:
            if getattr(self, "connection1", None) is not None:
                self.connection1.close()
        except Exception:
            pass

    def reset_server(self):
        self.turn_off_server()
        self.turn_on_server()
        self.video=threading.Thread(target=self.transmission_video)
        self.instruction=threading.Thread(target=self.receive_instruction)
        self.video.start()
        self.instruction.start()
    def send_data(self,connect,data):
        try:
            connect.send(data.encode('utf-8'))
            #print("send",data)
        except Exception as e:
            print(e)
    def transmission_video(self):
        # Keep the video port alive across client reconnects.
        while self.tcp_flag:
            conn = None
            conn_file = None
            try:
                try:
                    conn, self.client_address = self.server_socket.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.tcp_flag:
                        print(f"[VIDEO] accept failed: {e} (will retry)")
                        print("[VIDEO] Recovery: waiting for next client; ports should stay LISTEN.")
                        time.sleep(0.5)
                        continue
                    break

                conn_file = conn.makefile('wb')
                self.connection = conn_file
                self._video_client_connected = True
                print(f"[VIDEO] client connected from {self.client_address}")

                try:
                    with picamera.PiCamera() as camera:
                        camera.resolution = (400,300)       # pi camera resolution
                        camera.framerate = 15               # 15 frames/sec
                        camera.saturation = 80              # Set image video saturation
                        camera.brightness = 50              # Set the brightness of the image (50 indicates the state of white balance)
                        stream = io.BytesIO()
                        frame_count = 0
                        total_bytes = 0
                        fps_interval = 1.0  # Update FPS display every 1 second
                        last_fps_time = time.time()
                        # send jpeg format video stream
                        print("Start transmit ...")
                        for _ in camera.capture_continuous(stream, 'jpeg', use_video_port=True):
                            if not self.tcp_flag:
                                break
                            try:
                                conn_file.flush()
                                stream.seek(0)
                                b = stream.read()
                                frame_size = len(b)
                                lengthBin = struct.pack('L', frame_size)
                                conn_file.write(lengthBin)
                                conn_file.write(b)
                                self._last_video_frame_ts = time.time()
                                stream.seek(0)
                                stream.truncate()

                                # Calculate and display FPS with frame size info
                                frame_count += 1
                                total_bytes += frame_size
                                current_time = time.time()
                                elapsed = current_time - last_fps_time
                                if elapsed >= fps_interval:
                                    fps = frame_count / elapsed
                                    avg_frame_size = total_bytes / frame_count
                                    if LOG_VIDEO_TELEMETRY:
                                        print(
                                            f"\rVideo FPS: {fps:.1f} | Frame Size: {avg_frame_size:,.0f}B, 400x300",
                                            end='',
                                            flush=True,
                                        )
                                    frame_count = 0
                                    total_bytes = 0
                                    last_fps_time = current_time
                            except BaseException:
                                self._video_disconnects += 1
                                print("\n[VIDEO] client disconnected; returning to LISTEN on 8001")
                                break
                except BaseException:
                    self._camera_failures += 1
                    print("[VIDEO] Camera init/capture failed (camera may be busy or missing).")
                    print("[VIDEO] Recovery: will keep port 8001 LISTEN and retry on next connection.")
            finally:
                self._video_client_connected = False
                try:
                    if conn_file is not None:
                        conn_file.close()
                except Exception:
                    pass
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass

        # Exit when tcp_flag is cleared.

    def measuring_voltage(self,connect):
        try:
            for i in range(5):
                v = self._read_battery_voltage()
                if v is None:
                    continue
                self.battery_voltage[i]=v
            command=cmd.CMD_POWER+'#'+str(max(self.battery_voltage))+"\n"
            self.send_data(connect,command)
            self.sednRelaxFlag(connect)
            self.battery_reminder(source="cmd_power")
        except Exception as e:
            print(e)

    def battery_reminder(self, source="unknown"):
        current_voltage = max(self.battery_voltage) if self.battery_voltage else None
        if LOG_BATTERY_STATUS:
            if current_voltage is not None:
                print(f"Battery voltage: {current_voltage:.2f} V")

        # If we can't read voltage, do nothing.
        if current_voltage is None:
            return

        now = time.time()

        if current_voltage < LOW_VOLTAGE_THRESHOLD:
            # Start / continue debouncing window
            if not self.low_voltage_warning_active:
                self.low_voltage_warning_active = True
                self.low_voltage_start_time = now
                print(
                    f"⚠️  [BAT] LOW VOLTAGE detected: {current_voltage:.2f}V < {LOW_VOLTAGE_THRESHOLD}V "
                    f"(debounce {LOW_VOLTAGE_DEBOUNCE_TIME}s, source={source})"
                )

            elapsed_time = now - (self.low_voltage_start_time or now)
            if elapsed_time >= LOW_VOLTAGE_DEBOUNCE_TIME:
                # Low battery condition confirmed
                if not self._low_battery_active:
                    self._low_battery_active = True
                    self._low_battery_active_since = now
                    self._low_battery_relax_queued = False
                    self._low_battery_stop_pwm_queued = False
                    print(
                        f"🔴 [BAT] LOW BATTERY CONFIRMED: {current_voltage:.2f}V persisted for {elapsed_time:.1f}s "
                        f"(will RELAX now, STOP_PWM in {LOW_BATTERY_RELAX_DELAY_SEC}s)"
                    )

                # Force RELAX posture once
                if not self._low_battery_relax_queued:
                    self._queue_control_cmd(cmd.CMD_RELAX)
                    self._low_battery_relax_queued = True

                # After delay, force STOP_PWM once
                if (
                    self._low_battery_active_since is not None
                    and not self._low_battery_stop_pwm_queued
                    and (now - self._low_battery_active_since) >= LOW_BATTERY_RELAX_DELAY_SEC
                ):
                    self._queue_control_cmd(cmd.CMD_STOP_PWM)
                    self._low_battery_stop_pwm_queued = True

                # Warning signals every 5 seconds while low persists
                if (now - self._battery_last_warn_ts) >= BATTERY_WARNING_INTERVAL_SEC:
                    self._battery_last_warn_ts = now
                    print(
                        f"⚠️  [BAT] LOW BATTERY WARNING: {current_voltage:.2f}V < {LOW_VOLTAGE_THRESHOLD}V "
                        f"(warn every {BATTERY_WARNING_INTERVAL_SEC}s)"
                    )
                    try:
                        self.led_warning_blink()
                        self.buzzer_warning_beep(count=2)
                    except Exception as e:
                        print(f"[BAT] warning signal error: {e}")
        else:
            # Voltage recovered - reset warning state
            if self.low_voltage_warning_active:
                print(f"✅ Battery voltage recovered to {current_voltage:.2f}V (above {LOW_VOLTAGE_THRESHOLD}V)")
                self.low_voltage_warning_active = False
                self.low_voltage_start_time = None

            if self._low_battery_active:
                print(f"✅ [BAT] Leaving low-battery mode (voltage={current_voltage:.2f}V)")
            self._low_battery_active = False
            self._low_battery_active_since = None
            self._low_battery_relax_queued = False
            self._low_battery_stop_pwm_queued = False
    
    def led_warning_blink(self):
        """Flash red LED as low voltage warning"""
        try:
            # Turn on red LED (assuming LED control supports color)
            # Format: [CMD_LED, 'r', brightness, on_time, cycle_count]
            self.led.light([cmd.CMD_LED, 'r', '100', '0.2', '1'])
        except Exception as e:
            print(f"LED warning error: {e}")
    
    def buzzer_warning_beep(self, count=2, on_sec=0.10, off_sec=0.08):
        """Emit short beeps using the GPIO buzzer.

        Note: Buzzer.run() is a simple ON/OFF toggle (it does not parse tone strings).
        """
        try:
            for i in range(int(count)):
                self.buzzer.run('1')
                time.sleep(on_sec)
                self.buzzer.run('0')
                if i < int(count) - 1:
                    time.sleep(off_sec)
        except Exception as e:
            try:
                self.buzzer.run('0')
            except Exception:
                pass
            print(f"Buzzer warning error: {e}")
    
    def sednRelaxFlag(self, connect=None):
        if self.control.move_flag!=2:
            command=cmd.CMD_RELAX+"#"+str(self.control.move_flag)+"\n"
            if connect is None:
                connect = getattr(self, "connection1", None)
            if connect is not None:
                self.send_data(connect,command)
            self.control.move_flag= 2
    def receive_instruction(self):
        def _ts_ms():
            now = time.time()
            return time.strftime('%H:%M:%S', time.localtime(now)) + f".{int((now % 1) * 1000):03d}"

        def _handle_ctrl_client(conn, client_addr):
            client_id = self._client_id(client_addr)
            thread_led = None
            recv_buffer = ""
            self.connection1 = conn  # Backward compatibility for legacy helpers.
            self._register_ctrl_client(client_id, conn)
            print(f"[CTRL] client connected from {client_addr} ({client_id})")
            try:
                try:
                    conn.settimeout(1.0)
                except Exception:
                    pass

                while self.tcp_flag:
                    try:
                        chunk = conn.recv(1024)
                        if not chunk:
                            break
                        allData = chunk.decode('utf-8', errors='ignore')
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[CTRL] recv error ({client_id}): {e}")
                        break

                    if not allData:
                        break

                    recv_buffer += allData
                    while '\n' in recv_buffer:
                        oneCmd, recv_buffer = recv_buffer.split('\n', 1)
                        oneCmd = oneCmd.strip()
                        if not oneCmd:
                            continue

                        self._last_ctrl_rx_ts = time.time()
                        self._cmd_seq += 1
                        seq = self._cmd_seq

                        _cmd0 = oneCmd.split('#', 1)[0]
                        if DEBUG_COMMAND_SEQUENCE and (SEQUENCE_INCLUDE_SUPPRESSED or _cmd0 not in SUPPRESS_COMMAND_LOGS):
                            print(f"[RX {_ts_ms()}] client={client_id} seq={seq} raw='{oneCmd}'")

                        if _cmd0 not in SUPPRESS_COMMAND_LOGS:
                            print(f"📥 [{client_id}] Received: {oneCmd}")

                        data = oneCmd.split("#")
                        if data is None or data[0] == '':
                            continue

                        # Low-battery lockout: keep the dog in power-save mode.
                        if self._low_battery_active:
                            allow = {
                                cmd.CMD_POWER,
                                cmd.CMD_SONIC,
                                cmd.CMD_WORKING_TIME,
                                cmd.CMD_RELAX,
                                cmd.CMD_STOP_PWM,
                                cmd.CMD_ATTITUDE,
                            }
                            if data[0] not in allow:
                                now = time.time()
                                if (now - self._last_low_bat_ignore_ts) >= 2.0:
                                    self._last_low_bat_ignore_ts = now
                                    print(f"[BAT] low-battery lockout: ignoring {data[0]} from {client_id}")
                                continue

                        # Write command ownership guard.
                        if self._is_control_write_cmd(data):
                            if not self._authorize_control_write(client_id, client_addr, data):
                                owner = self._control_owner_id or "none"
                                if data[0] not in SUPPRESS_COMMAND_LOGS:
                                    print(f"[CTRL] reject non-owner write from {client_id}; owner={owner}; cmd={data[0]}")
                                self.send_data(conn, f"CMD_BUSY#OWNER:{owner}\n")
                                continue

                        if data[0] not in SUPPRESS_COMMAND_LOGS:
                            print(f"📋 [{client_id}] Processing command: {data[0]}", end='')
                            if len(data) > 1:
                                print(f" with params: {data[1:]}")
                            else:
                                print()

                        if data[0] == cmd.CMD_TURN_LEFT:
                            raw_speed = data[1] if len(data) > 1 else ''
                            try:
                                parsed_speed = int(raw_speed)
                                speed_note = f"speed={parsed_speed} (raw='{raw_speed}')"
                            except Exception:
                                speed_note = f"speed=<invalid> (raw='{raw_speed}')"
                            print(f"↩️  TURN_LEFT details: {speed_note}; dispatched to Control via self.control.order")

                        if data[0] == cmd.CMD_RELAX:
                            try:
                                self.buzzer.run('1')
                                time.sleep(0.05)
                                self.buzzer.run('0')
                            except Exception as e:
                                print(f"[CTRL] CMD_RELAX beep failed: {e}")

                        if cmd.CMD_BUZZER in data:
                            if len(data) > 1 and data[1] != '':
                                self.buzzer.run(data[1])
                            else:
                                print("⚠️  CMD_BUZZER ignored: missing params")
                        elif cmd.CMD_LED in data:
                            try:
                                if thread_led is not None:
                                    stop_thread(thread_led)
                            except Exception:
                                pass
                            thread_led = threading.Thread(target=self.led.light, args=(data,))
                            thread_led.start()
                        elif cmd.CMD_LED_MOD in data:
                            try:
                                if thread_led is not None:
                                    stop_thread(thread_led)
                            except Exception:
                                pass
                            thread_led = threading.Thread(target=self.led.light, args=(data,))
                            thread_led.start()
                        elif cmd.CMD_HEAD in data:
                            if len(data) > 1 and data[1] != '':
                                self.servo.setServoAngle(15, int(data[1]))
                            else:
                                print("⚠️  CMD_HEAD ignored: missing angle parameter")
                        elif cmd.CMD_SONIC in data:
                            command = cmd.CMD_SONIC + '#' + str(self.sonic.getDistance()) + "\n"
                            self.send_data(conn, command)
                        elif cmd.CMD_POWER in data:
                            self.measuring_voltage(conn)
                        elif cmd.CMD_STOP_PWM in data:
                            self._set_control_order([cmd.CMD_STOP_PWM, '', '', '', ''], seq, oneCmd)
                        elif cmd.CMD_ATTITUDE in data:
                            if len(data) >= 4:
                                self._set_control_order(data, seq, oneCmd)
                            else:
                                try:
                                    pitch, roll, yaw = self.control.imu.imuUpdate()
                                except Exception:
                                    pitch, roll, yaw = 0.0, 0.0, 0.0
                                command = (
                                    cmd.CMD_ATTITUDE
                                    + f"#ROLL:{roll:.2f}#PITCH:{pitch:.2f}#YAW:{yaw:.2f}\n"
                                )
                                self.send_data(conn, command)
                        elif cmd.CMD_WORKING_TIME in data:
                            if 'OVERUSE_PROTECTION_ENABLED' in globals() and OVERUSE_PROTECTION_ENABLED:
                                active_limit = OVERUSE_ACTIVE_LIMIT_SEC if 'OVERUSE_ACTIVE_LIMIT_SEC' in globals() else 180
                                if self.control.move_timeout != 0 and self.control.relax_flag == True:
                                    if self.control.move_count > active_limit:
                                        command = (
                                            cmd.CMD_WORKING_TIME
                                            + '#'
                                            + str(active_limit)
                                            + '#'
                                            + str(round(self.control.move_count - active_limit))
                                            + "\n"
                                        )
                                    else:
                                        if self.control.move_count == 0:
                                            command = (
                                                cmd.CMD_WORKING_TIME
                                                + '#'
                                                + str(round(self.control.move_count))
                                                + '#'
                                                + str(round((time.time() - self.control.move_timeout) + 60))
                                                + "\n"
                                            )
                                        else:
                                            command = (
                                                cmd.CMD_WORKING_TIME
                                                + '#'
                                                + str(round(self.control.move_count))
                                                + '#'
                                                + str(round(time.time() - self.control.move_timeout))
                                                + "\n"
                                            )
                                else:
                                    command = cmd.CMD_WORKING_TIME + '#' + str(round(self.control.move_count)) + '#' + str(0) + "\n"
                            else:
                                command = cmd.CMD_WORKING_TIME + '#' + str(round(self.control.move_count)) + '#' + str(0) + "\n"
                            self.send_data(conn, command)
                        else:
                            self._set_control_order(data, seq, oneCmd)
                            if data[0] in MOTION_COMMANDS:
                                with self._control_state_lock:
                                    self.control.last_motion_order = (data + ['', '', '', ''])[:5]
                                    self.control.last_motion_seq = seq
                                    self.control.last_motion_rx_ts = time.time()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                self._unregister_ctrl_client(client_id)
                if self.tcp_flag:
                    self._ctrl_disconnects += 1
                    print(f"[CTRL] client disconnected: {client_id}; waiting for reconnect ...")

        # Keep control port alive and accept multiple concurrent clients.
        while self.tcp_flag:
            try:
                try:
                    conn, client_addr = self.server_socket1.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.tcp_flag:
                        print(f"[CTRL] accept failed: {e} (will retry)")
                        print("[CTRL] Recovery: waiting for next client; port 5001 should stay LISTEN.")
                        time.sleep(0.5)
                        continue
                    break
                t = threading.Thread(target=_handle_ctrl_client, args=(conn, client_addr), daemon=True)
                t.start()
            except Exception as e:
                if self.tcp_flag:
                    print(f"[CTRL] handler spawn error: {e}")
                    time.sleep(0.2)
if __name__ == '__main__':
    pass
