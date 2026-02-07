# Freenove Robot Dog - Server

## Description
Server-side runtime for the Freenove Robot Dog on Raspberry Pi. It exposes two TCP ports (control + video), manages hardware drivers (servo, IMU, ADC, LED, buzzer, ultrasonic), and provides calibration/test tooling. This README is written for new users who need a full-system view and how the Server interacts with the Client.

## Version
1.2.1

## Date
2026-02-06

## Revision History (newest first)
- 2026-02-06 22:07 v1.2.1  Added timestamps to revision history (older entries had no recorded time).
- 2026-02-06 (time n/a) v1.2.0  Added battery/power notes and UBEC/BEC search results.
- 2026-02-06 (time n/a) v1.1.0  Expanded system overview, client/server interaction, startup, troubleshooting.
- 2026-02-06 (time n/a) v1.0.0  Initial Server directory overview and file structure summary.

## System Overview (Client <-> Server)
The full system is split into:
- Client (laptop/PC): UI and control logic. Sends commands and receives telemetry/video.
- Server (Raspberry Pi): hardware control, sensors, video streaming, TCP endpoints.

Data paths:
- Control channel (TCP 5001): Client sends commands; Server responds with telemetry/queries.
- Video channel (TCP 8001): Server streams JPEG frames to Client.

High-level flow:
1) Client connects to Server control port (5001) and video port (8001).
2) Server receives commands, dispatches them into Control.py.
3) Control.py drives servo/LED/buzzer and reads sensors.
4) Server streams video frames over 8001 and replies to queries over 5001.

## Startup (Server side)
Common ways to start the Server:
- Headless (no GUI): `python3 main.py -tn`
- With UI: `python3 main.py -t`
- Wrapper script: `./smartdog.sh start`

Stop the Server:
- `./smartdog.sh stop`

Status check:
- `./smartdog.sh status`

## Key Modules and Responsibilities
- main.py: entry point, GUI vs headless, starts TCP threads.
- Server.py: core TCP server (video + control), health monitoring, battery guard.
- Control.py: motion control loop and posture management.
- Command.py: command IDs and protocol definitions.
- IMU.py, ADS7830.py, Ultrasonic.py: sensor access.
- Servo.py, Led.py, Buzzer.py: hardware drivers.
- Thread.py: thread helper utilities.
- ui_server.py: PyQt UI.

## Command / Telemetry
Reference docs:
- Command reference: `Command.md`
- Command flow: `COMMAND_FLOW.md`

Example behaviors:
- CMD_MOVE_*/CMD_TURN_* -> Control.py motion updates
- CMD_POWER -> ADC voltage read and reply
- CMD_ATTITUDE -> set or query IMU (bidirectional)
- CMD_STOP_PWM / CMD_RELAX -> power save or posture behavior

## File Structure (with short descriptions)
```
/Server
├── main.py                           - Entry point; GUI/headless flags; starts TCP threads
├── Server.py                         - Core TCP server: video stream + command RX; health & battery monitors
├── Control.py                        - Motion control loop; gait state; relax/stop PWM behavior
├── Command.py                        - Command IDs / protocol definitions
├── IMU.py                            - IMU read + attitude computation
├── ADS7830.py                        - Battery ADC reads
├── Servo.py                          - Servo driver
├── Led.py                            - LED control
├── Buzzer.py                         - Buzzer control
├── Ultrasonic.py                     - Distance sensor
├── PID.py                            - PID helper
├── Kalman.py                         - Kalman filter helper
├── Thread.py                         - Thread helpers/stop utilities
├── ui_server.py                      - PyQt UI definitions
├── smartdog.sh                       - Start/stop/status wrapper + logging
├── smartdog_xx.sh                    - systemd control wrapper (template)
├── Action.py                         - Demo action sequences
├── calibrateServo.py                 - Servo calibration tool
├── calibrateServo.md                 - Calibration usage notes
├── calibration_Explain.md            - Calibration explanation/diagrams
├── COMMAND_FLOW.md                   - Command flow docs
├── Command.md                        - Command reference
├── testServo.py                      - Servo test tool
├── testHeadMoving.py                 - Head movement test
├── testBatADS.py                     - Battery ADC test
├── test_buzzer.py                    - Buzzer test (python)
├── test_buzzer.sh                    - Buzzer test (shell)
├── backup/                           - Backups of core files
├── experimental/                     - Experimental scripts
└── __pycache__/                      - Python bytecode cache
```

## Logs and Diagnostics
- Runtime log (wrapper): `smartdog.log`
- PID file: `smartdog.pid`
- Quick health and port status: `./smartdog.sh status`

If the Server shuts down unexpectedly, check:
- Battery voltage and low-voltage warnings in logs
- System logs on the Pi (undervoltage, OOM, or reboot)

## Battery and Power Notes (from kit docs)
- About_Battery.pdf: Robot Dog kit uses two 3.7V 18650 cells with >10A discharge. Capacity mainly affects run time; recommended range is ~2000-3500 mAh. Push cells toward the + ends in the holder.
- Tutorial.pdf: Raspberry Pi power supply should be at least 5V/2.5A to avoid instability.
- Tutorial.pdf: Robot shield uses two 18650 3.7V cells and includes charging. The S1 (LOAD) switch powers servos/buzzer/ultrasonic/LED, and S2 (CTRL) powers PCA9685, ADS7830, and the Raspberry Pi.

## UBEC/BEC Search Result
Searched all PDFs in the kit (About_Battery, Tutorial, datasheets, calibration docs, and the additional supplement). No explicit mention of UBEC or BEC was found. Datasheets mention generic power supply/regulator terms only.

## Notes
- Files with .bak or .Original.py are historical backups.
- Logs (e.g., smartdog.log) are generated at runtime and may not exist in all copies.
