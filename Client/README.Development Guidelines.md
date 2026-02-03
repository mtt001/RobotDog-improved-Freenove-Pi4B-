## 🛠️ Development Guidelines

### Before Making Changes
- Create backup: `cp Main.py Main_backup_$(date +%Y%m%d).py`
- Check revision history: verify you modify the latest version.
- Read threading contract: never block the Qt main thread. Summary: avoid `sleep`, blocking I/O, or long loops in the GUI thread; use `QTimer` or worker threads (`threading.Thread`, `QThread`). See [Threading Contract](#threading-contract-never-block-the-qt-main-thread).
- Test video pipeline: run with `debug_ui_enabled = True`.

### Adding New Features

Example: Add gyroscope telemetry

1) Server-side (Robot Pi):
```python
# Send gyroscope telemetry periodically (server-side)
gyro_x, gyro_y, gyro_z = read_gyroscope()  # Returns floats
client_socket.send(f"Gyro#{gyro_x}#{gyro_y}#{gyro_z}#\n".encode("utf-8"))
```

2) Client-side (Main.py):
```python
# In MyWindow.__init__():
self.tele_gyro_xyz = None

# In _handle_server_line():
if "GYRO" in tag:
    if len(parts) >= 4:
        try:
            gx, gy, gz = float(parts[1]), float(parts[2]), float(parts[3])
            self.tele_gyro_xyz = (gx, gy, gz)
        except ValueError:
            pass
    return
```

3) Display overlay (optional, e.g., in testVideoStream.draw_top_bar):
```python
if gyro_xyz:
    gx, gy, gz = gyro_xyz
    cv2.putText(frame, f"Gyro {gx:.1f},{gy:.1f},{gz:.1f}",
                (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
```

### Performance Tuning

Video Stream Optimization
```python
# Client-side (Main.py)
TIMER_INTERVAL_MS = 33       # ~30 FPS. Use 50ms for lower CPU, 16ms for higher FPS.
OVERLAY_TIMER_MS = 500       # Update overlay every 0.5s

# Server-side (Pi)
JPEG_QUALITY = 75            # 50-95 (lower = faster, lower quality)
RESOLUTION = (640, 480)      # Use (320, 240) for higher FPS on slower networks
FPS_TARGET = 25
```

Network Optimization
```python
# Client.py
SOCKET_TIMEOUT = 2.0         # Seconds
RECV_BUFFER_SIZE = 65536     # Increase for high-res streams (e.g., 131072)
```

```bash
# Raspberry Pi sysctls (optional)
sudo sysctl -w net.ipv4.tcp_window_scaling=1
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
```

Memory Management
```python
# In refresh_image(), always work on a copy
with self.client.image_lock:
    if isinstance(self.client.image, np.ndarray):
        base = self.client.image.copy()
        self.client.video_flag = True

# Periodic GC (optional)
if hasattr(self.client, 'frames_displayed') and self.client.frames_displayed % 1000 == 0:
    import gc; gc.collect()
```

CPU Usage Optimization
```python
# Avoid heavy per-frame allocations; reuse buffers when possible
# Keep overlay drawing simple (small fonts, minimal blending)
```

Battery Life Optimization
```python
def enter_low_power_mode(self):
    # Slow down telemetry
    if hasattr(self, 'timer_power'):
        self.timer_power.setInterval(5000)
    if hasattr(self, 'timer_sonic'):
        self.timer_sonic.stop()
    # Dim LEDs
    self.client.send_data("CMD_LED#static#10#10#10#\n")
```

---

## ⚠️ Error Codes Reference

Connection Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| E001 | Connect Failed | Robot unreachable | Check IP, ping robot, verify WiFi and power |
| E002 | Port 5001 refused | Command server down | Restart server on Pi |
| E003 | Port 8001 refused | Video server down | Check camera, restart video service |
| E004 | Connection timeout | High latency/packet loss | Move closer to router; increase timeouts |

Video Stream Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| V001 | JPEG decode failed | Corrupt frame | Lower JPEG quality; check WiFi |
| V002 | Frame size mismatch | struct format mismatch | Ensure both ends use '<I' little-endian |
| V003 | Video stalled >5s | Producer died | Check server logs; restart video |
| V004 | FPS <5 | CPU/network bottleneck | Lower resolution; increase timer interval |
| V005 | QImage creation failed | Invalid dims/stride | Validate frame shape and stride |

Hardware Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| H001 | Battery <7.0V | Low battery | Charge immediately |
| H002 | Servo timeout | Wiring/power issue | Check servo wiring, supply |
| H003 | IMU read failed | I2C error | Re-seat IMU; i2cdetect -y 1 |
| H004 | Camera not found | /dev/video0 missing | Enable camera; reboot; test raspistill |
| H005 | Ultrasonic timeout | Sensor not responding | Check TRIG/ECHO pins; test script |

Debug Commands
```bash
# Connectivity
ping <robot_ip>
traceroute <robot_ip>

# Open ports
nmap -p 5001,8001 <robot_ip>

# Live traffic
sudo tcpdump -i wlan0 host <robot_ip> and '(port 5001 or port 8001)'
```

---

## 🐛 Troubleshooting

Video not displaying
- Symptoms: Black screen or only placeholder.
- Checks:
  - Confirm server: ports 5001/8001 listening on Pi.
  - Confirm frames arrive: Client.receiving_video prints frame sizes.
  - Ensure image_lock usage around shared buffers.
  - Call self.Video.update() after setPixmap if needed.

Connection timeout
- Verify robot IP (router DHCP, nmap, or hostname -I on Pi).
- Check firewall on macOS (System Settings → Network → Firewall).
- Try increasing Client.py socket timeouts.

Frame rate drops
- Lower resolution or JPEG quality on server.
- Increase timer interval to 50ms in Main.py.
- Close CPU-heavy tasks on Pi; check WiFi quality.

Battery drains quickly
- Disable LED animations or use dim static color.
- Reduce telemetry frequency; stop ultrasonic polling when idle.

---

## 📚 Related Files
- Server code (Pi): ./Server/
- Hardware drivers: Servo, IMU, ultrasonic, camera modules
- Archived reference: Main_Freenove.py

---

## 🤝 Contributing
- Keep UI responsive; no blocking calls in Qt thread.
- Update file headers and Revision History when changing behavior.
- Include sanity checks for new telemetry parsers.
- Document new commands in Communication Protocols section.

Pull Request checklist
- Tested connect/disconnect and graceful shutdown.
- Verified video pipeline works 5+ minutes without leaks.
- Checked telemetry parsing with simulated lines and edge cases.
- Updated README Feature Modules/Revision History if applicable.

---

## 📄 License
See the project’s LICENSE file.

---

╔══════════════════════════════════════════════════════════════════════════╗
║                          END OF DOCUMENTATION                            ║
╚══════════════════════════════════════════════════════════════════════════╝

Document Version  : 1.1  
Last Updated      : 2025-11-17 15:45 PST  
Maintained By     : MT (Lead Developer), GitHub Copilot (AI Assistant)  
Repository        : /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/  
Status            : Production - Actively Maintained

## Threading Contract: Never Block the Qt Main Thread

Rule
The Qt (GUI) main thread must only process events, paint, and dispatch lightweight callbacks. Any blocking I/O, sleeps, heavy CPU work, waits, or long loops must run in a worker thread (threading.Thread, QThread) or be sliced via QTimer.

Why
- Blocking stops event loop → frozen window (no repaint, no input).
- Increases frame latency and drops FPS.
- Can trigger macOS “Application Not Responding”.
- Deadlocks if locks held during repaint.

Common Blocking Mistakes (Avoid in GUI thread)
```python
time.sleep(2)                  # Freezes UI for 2s
socket.recv(4096)              # Blocks until data arrives
while condition: ...           # Long loop without returning to event loop
cv2.VideoCapture.read()        # Can block camera device
json.loads(huge_string)        # Large parsing, heavy CPU
```

Correct Patterns

1) Use a Worker Thread for Blocking I/O
```python
# BAD (inside a button callback)
data = self.sock.recv(4096)  # Blocks GUI

# GOOD
def start_receiver(self):
    t = threading.Thread(target=self._recv_loop, daemon=True)
    t.start()

def _recv_loop(self):
    while self.tcp_flag:
        try:
            data = self.sock.recv(4096)
            QTimer.singleShot(0, lambda d=data: self._handle_data(d))
        except socket.timeout:
            continue
```

2) Replace sleep() with QTimer
```python
# BAD
time.sleep(1)
self.status_label.setText("Ready")

# GOOD
QTimer.singleShot(1000, lambda: self.status_label.setText("Ready"))
```

3) Heavy CPU Task Offloaded
```python
# BAD
def compute_path(self):
    result = slow_astar(grid)   # Blocks UI for 500ms
    self.label.setText(result)

# GOOD
def compute_path(self):
    threading.Thread(target=self._astar_worker, args=(self.grid,), daemon=True).start()

def _astar_worker(self, grid):
    result = slow_astar(grid)
    QTimer.singleShot(0, lambda r=result: self.label.setText(r))
```

4) Periodic Work via QTimer Instead of Loop
```python
# BAD
def poll(self):
    while True:
        self.updateTelemetry()
        time.sleep(1)

# GOOD
self.timer_power = QTimer(self)
self.timer_power.timeout.connect(self.updateTelemetry)
self.timer_power.start(1000)
```

5) Non-Blocking Socket
```python
# Setup
self.sock.settimeout(0.2)

# Loop in thread (never GUI)
def _recv_loop(self):
    while self.tcp_flag:
        try:
            chunk = self.sock.recv(4096)
        except socket.timeout:
            continue
```

6) Protect Shared Frame Access
```python
# Producer (thread)
with self.image_lock:
    self.image = frame.copy()
    self.video_flag = False

# Consumer (GUI thread)
with self.image_lock:
    if isinstance(self.image, np.ndarray):