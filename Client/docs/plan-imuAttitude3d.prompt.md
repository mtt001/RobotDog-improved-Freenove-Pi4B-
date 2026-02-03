# Plan: 3D IMU Attitude Dog Icon

**Request:** Plan implementing a 3D animation with a Freenove Robo Dog icon based on IMU status.

**Version:** v0.01

**Date/Time:** 2026-02-02 (local)

**Author:** MT & GitHub Copilot
 
Plumb roll/pitch/yaw IMU attitude into the Mac client’s telemetry state (via the existing port-5001 line protocol), then render a small real-time 3D “Robo Dog” icon inside the PyQt5 UI. The key is: (1) ensure the client regularly requests/receives attitude lines, (2) parse/store them consistently (with smoothing + stale handling), and (3) add a lightweight 3D widget (prefer `QOpenGLWidget` to avoid new pip dependencies) that rotates the icon/model based on IMU angles.

### Steps 3–6 steps, 5–20 words each
1. Confirm current telemetry loop in mtDogLogicMixin.py (`poll_telemetry`, `command_receiver_worker`, `handle_cmd_line`).
2. Extend telemetry polling to request `CMD_ATTITUDE\n` at a safe rate (e.g., 5–10 Hz max).
3. Add parsing in `DogLogicMixin.handle_cmd_line` for `CMD_ATTITUDE#roll#pitch#yaw` and store `self.imu_roll/pitch/yaw` + timestamp.
4. Create a new widget class `Attitude3DWidget(QOpenGLWidget)` in ui/attitude_3d_widget.py rendering a textured “dog icon” quad.
5. Embed the widget into the right control panel layout (via ui/control_panel_sections.py / ui/ui_client.py) and update it on an existing QTimer tick.
6. Add UI polish + robustness: smoothing, degree clamping, “stale IMU” dimming, and a disable toggle in settings.

### Further Considerations 1–3, 5–25 words each
1. Asset choice: reuse an existing image from Picture/logo_Mini.png or add a dedicated transparent PNG for the dog.
2. Rendering options: `QOpenGLWidget` (no new deps) vs Qt3D (heavier, packaging friction).
3. Protocol reality: if the Pi/server doesn’t emit attitude without being polled, ensure `poll_telemetry` sends `CMD_ATTITUDE\n` only when connected.
