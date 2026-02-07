# Freenove Robot Dog - Client

## Description
Client-side UI and control logic for the Freenove Robot Dog. The Client connects to the Raspberry Pi Server over TCP, sends commands, receives telemetry, and displays the live video stream.

## Version
1.1.9

## Date
2026-02-06

## Revision History (newest first)
- 2026-02-06 23:00:26 v1.1.9  Bundled Three.js locally to avoid CDN blocking.
- 2026-02-06 22:55:33 v1.1.8  Re-enabled colored pug model with fallback placeholder.
- 2026-02-06 22:53:40 v1.1.7  Added localhost/127.0.0.1 note for IMU viewer.
- 2026-02-06 22:51:02 v1.1.6  Reverted IMU viewer to simple box model for reliability.
- 2026-02-06 22:33:30 v1.1.5  Added Quaternius pug model for IMU viewer and static assets support.
- 2026-02-06 22:19:14 v1.1.4  Renamed IMU viewer script to Demo_IMU_server.py.
- 2026-02-06 22:15:40 v1.1.3  Clarified IMU viewer note about control-port exclusivity.
- 2026-02-06 22:15 v1.1.2  Added IMU 3D viewer section.
- 2026-02-06 22:07 v1.1.1  Added timestamps to revision history (older entries had no recorded time).
- 2026-02-06 (time n/a) v1.1.0  New user overview, client/server interaction, and file structure summary.

## System Overview (Client <-> Server)
The full system is split into:
- Client (laptop/PC): UI and control logic. Sends commands and receives telemetry/video.
- Server (Raspberry Pi): hardware control, sensors, video streaming, TCP endpoints.

Data paths:
- Control channel (TCP 5001): Client sends commands; Server responds with telemetry/queries.
- Video channel (TCP 8001): Server streams JPEG frames to Client.

High-level flow:
1) Client connects to Server control port (5001) and video port (8001).
2) Client sends commands (move, posture, LEDs, buzzer, etc.).
3) Client receives telemetry/queries on control channel and video frames on video channel.

## Where to Start
- Main entry point: `mtDogMain.py`
- Command controller: `controllers/dog_command_controller.py`

## IMU 3D Viewer (Live)
- Tool: `tools/imu_viewer/`
- Starts a local HTTP server that proxies CMD_ATTITUDE to the Pi and renders a simple 3D dog model.
- Run: `python3 tools/imu_viewer/Demo_IMU_server.py --pi-host 192.168.0.32 --pi-port 5001 --http-port 8080`
- Open: `http://localhost:8080`

## Client/Server Interaction Notes
- The Client must connect to the Server IP address on the same network.
- If video is unavailable but control works, check port 8001 or camera availability.
- If control is unavailable, check port 5001, server status, and logs on the Pi.

## File Structure (common files)
```
/Client
├── mtDogMain.py                      - Client entry point (UI + main loop)
├── controllers/
│   └── dog_command_controller.py     - Command dispatch and protocol handling
└── (other UI/support modules)        - UI widgets, resources, and helpers
```

## Notes
- If you are new, start by running the Server and confirming both ports (5001, 8001) are reachable.
- The Client is designed to tolerate reconnects; if the Server restarts, reconnect the Client.
