## File Structure of Main.py and related code (.py)

Overview (file + top-level classes)

Main module: Main.py defines the GUI windows and the runtime glue:
Main.MyWindow — main application window (inherits ui_client.Ui_client).
Main.faceWindow — face capture / train UI (inherits ui_face.Ui_Face).
Main.calibrationWindow — leg calibration UI (inherits Calibration.Ui_calibration).
Main.ledWindow — LED control UI (inherits ui_led.Ui_led).
Main.ColorDialog — small QColorDialog subclass used by ledWindow.
How other .py files are used (mapping)

UI classes (auto-generated from .ui)

ui_client.Ui_client provides widgets (buttons, sliders, labels) used by Main.MyWindow. See ui_client.py.
ui_face.Ui_Face provides face dialog widgets used by Main.faceWindow. See ui_face.py.
ui_led.Ui_led provides LED dialog widgets used by Main.ledWindow. See ui_led.py.
Client runtime / networking

Client.Client is instantiated in Main.MyWindow.__init__ as self.client; Main uses:
self.client.send_data(...) to send commands (used across movement, LEDs, calibration, sensors).
self.client.receiving_video(...) is started in a thread for video receive ([Client/Main.py:connect]).
self.client.receive_data() is used by the receive loop ([Client/Main.py:receive_instruction]).
image data and flags (self.client.image, self.client.video_flag) are read by refresh_image / face detection.
See Client.py and symbol Client.Client.
Face logic

Face.Face is created in the client (self.client.face) and used by Main.faceWindow for detection and training (detectMultiScale, trainImage, Save/Read face names). See Face.py.
Calibration UI & persistence

Calibration.Ui_calibration defines widgets and is the base for Main.calibrationWindow.
calibrationWindow reads/writes calibration points using its Read_from_txt / Save_to_txt helpers and sends calibration commands to the robot via cmd.CMD_CALIBRATION using self.client.send_data(...). See Calibration.py.
Command definitions

COMMAND (aliased to cmd) contains the command constants (CMD_MOVE_FORWARD, CMD_LED, CMD_CALIBRATION, etc.). It is imported in the client module and thus available in Main. See Command.py and symbol Command.COMMAND.
Runtime interactions and threads

Connection sequence (in Main.MyWindow.connect):
Writes IP to IP.txt.
Calls Client.Client.turn_on_client and starts two threads:
video thread -> Client.Client.receiving_video
instruction thread -> Main.receive_instruction which calls Client.Client.receive_data
UI → robot interaction:
User actions (button presses, slider changes, keyboard events) call methods on Main windows which build command strings using cmd constants and forward them via Client.Client.send_data.
Face and image pipeline:
Video frames arrive via the client thread into self.client.image; Main.refresh_image and faceWindow.faceDetection display/process them and use [Face.Face] detection/training.
Files referenced from Main.py (openable)

Main.py — active file (this overview)
ui_client.py — UI layout for main window (symbol: ui_client.Ui_client)
ui_face.py — UI layout for face dialog (symbol: ui_face.Ui_Face)
ui_led.py — UI layout for LED dialog (symbol: ui_led.Ui_led)
Client.py — networking client and image helpers (symbol: Client.Client, Client.is_valid_image_4_bytes)
Face.py — face detection / training logic (symbol: Face.Face)
Calibration.py — calibration UI class (symbol: Calibration.Ui_calibration)
Command.py — command constants (symbol: Command.COMMAND)

## ==========================================
Concise call / data flow (Main.py centric)

MyWindow

Creates: Client(), QPushButton DebugWin, timers (video refresh, power, sonic, overlay), optional DebugStreamWindow.
Starts threads in connect():
video_thread -> Client.receiving_video (fills client.image, sets video_flag False when new frame ready).
instruction_thread -> MyWindow.receive_instruction (reads lines via Client.receive_data, passes each to _handle_server_line).
Periodic GUI:
timer -> refresh_image(): locks client.image, copies frame, overlays telemetry, sets video_flag True.
timer_power -> power(): requests/updates battery.
timer_sonic -> getSonicData(): sends CMD_SONIC; telemetry parsed in _handle_server_line.
overlay_timer -> _overlay_refresh_if_stalled(): redraw overlay if producer stalled.
User input:
Buttons / key events -> movement / posture methods -> client.send_data("CMD_*#speed\n").
Sliders -> head / horizon / height / attitude adjustments -> send corresponding CMD_*.
faceWindow

Uses client.face (Face.Face instance created inside Client).
timer1 -> faceDetection(): reads client.image for detection.
timer2 -> facePhoto(): captures & saves, updates face name list.
calibrationWindow

Reads point.txt (Read_from_txt), populates fields.
Button_X/Y/Z adjust -> send CMD_CALIBRATION#leg#x#y#z.
Save -> writes back to point.txt and sends CMD_CALIBRATION#save.
ledWindow

Color / mode changes -> send CMD_LED_MOD / CMD_LED_RGB (or similar) via client.send_data.
ColorDialog feeds onCurrentColorChanged -> HSL/RGB conversions -> command send.
Shared state (Client)

client.image (numpy BGR frame), client.image_lock (thread lock).
client.video_flag (False = new frame; GUI sets True after consume).
client.video_last_frame_ts (producer timestamp for FPS).
Sockets: client_socket1 (instruction), client_socket2 (video).
Telemetry parsing (_handle_server_line)

Lines "POWER#/VOLT#/BAT#" -> tele_batt_v.
Lines "SONIC#/DIST#/RANGE#" -> tele_dist_cm.
Others ignored.
Minimal call graph (arrows = calls, dashed = thread start)
MyWindow.connect
├─ client.turn_on_client (internal socket setup)
├─ (thread) → client.receiving_video
└─ (thread) → MyWindow.receive_instruction
MyWindow.receive_instruction
├─ client.receive_data
└─ MyWindow._handle_server_line
MyWindow.refresh_image
├─ client.image_lock (acquire/copy)
├─ MyWindow.blit_to_label
└─ sets client.video_flag True
Movement / posture / LED / calibration methods
└─ client.send_data("CMD*...")

If you need inline annotations added to Main.py or a dependency diagram in Graphviz DOT form, just say so.

## ====================================================================

Ball tracking

Purpose: Detect a colored ball in the live video stream and steer the robot to center it (and optionally approach).

Where logic lives:
- Entry point: Main.MyWindow.chase_ball_and_find_face() (button click).
- Frame source: self.client.image (BGR numpy frame guarded by self.client.image_lock).
- Command output: self.client.send_data("CMD_*#value\n") for yaw/step/forward adjustments.

Typical pipeline (color-based):
1. Copy current frame under lock.
2. Convert BGR→HSV.
3. Apply inRange(hsv, lower, upper) for the ball color.
4. Morphology (erode/dilate) to clean mask.
5. Find largest contour; compute its center (cx, cy) and radius.
6. Decide:
   - If no contour: optionally rotate slowly (search).
   - If contour exists:
       * Horizontal offset -> left/right or yaw command.
       * Radius (distance proxy) -> forward/stop.
7. Overlay diagnostics (circle, crosshair) before display (never modify shared buffer directly).

Commands suggestion (adjust to your constants):
- Small horizontal error: CMD_STEP_LEFT / CMD_STEP_RIGHT.
- Large horizontal error: CMD_TURN_LEFT / CMD_TURN_RIGHT.
- Radius too small (far): CMD_MOVE_FORWARD.
- Radius big (close): CMD_STOP or CMD_RELAX.

Face combo mode:
- You can run ball detection first; if no ball found, fall back to face detection (reuse self.client.face).

Threading / UI:
- Run a QTimer (e.g. self.ball_timer) instead of a blocking loop; keep main thread responsive.
- Stop timer when feature disabled.

Extensible:
- Replace color threshold with ML detector (e.g. YOLO) later without changing command interface.

Disable / cleanup:
- Provide a toggle button: start -> create timer; stop -> kill timer and clear overlays.

Safety:
- Always clamp movement frequency (avoid spamming commands every frame).
- Include a minimum interval (e.g. 80–120 ms) between movement decisions.

Required imports (if not present in Main.py):
import cv2
import numpy as np
import time