# IMU Dog Viewer (Live from Pi)

## Description
Minimal 3D dog viewer that animates pitch, roll, and yaw using live IMU data from the Raspberry Pi Server.

## Requirements
- Pi Server running and reachable on the network
- Control port 5001 open (Server uses CMD_ATTITUDE)
- Local Three.js assets (included in `vendor/three/`)

## Quick Start
From this folder:

```
python3 Demo_IMU_server.py --pi-host 192.168.0.32 --pi-port 5001 --http-port 8080
```

Or with a full path:

```
python3 /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/imu_viewer/Demo_IMU_server.py --pi-host 192.168.0.32 --pi-port 5001 --http-port 8080
```

Open:

```
http://localhost:8080
```

## Pages
- `/` Landing page with diagnostics and version.
- `/simple` Simple box model.
- `/color` Color (pug) model with load status.

## Diagnostics
The HUD shows:
- Proxy status, last error, and last OK age.
- Proxy version and timestamp (from `/version`).
- Model load status on `/color`.

## Notes
- The viewer polls `/imu` at 10 Hz.
- To expose the page to other devices, use `--listen 0.0.0.0` and open `http://<your-mac-ip>:8080`.
- The Server control port (5001) accepts one client at a time. Disconnect the main Client UI before using this viewer.
- IMU data is read via `CMD_ATTITUDE` without parameters.

## Model
- Default: Colored Pug model (OBJ/MTL) from “Farm Animals by @Quaternius” (CC0).
- Fallback: Simple box-based dog if OBJ/MTL fails to load.
- License: `assets/quaternius_pug/License.txt`

## File Overview
- `Demo_IMU_server.py`: HTTP server that serves pages and proxies IMU queries to the Pi.
- `index.html`: Landing page with mode selection and diagnostics.
- `index_simple.html`: Simple box model viewer page.
- `index_color.html`: Color model viewer page with load status.
- `app.js`: Main JavaScript for the viewer, handling IMU polling, model updates, and diagnostics.
- `app_simple.js`: JavaScript for the simple box model viewer.
- `app_color.js`: JavaScript for the color model viewer, including model load status and diagnostics.
- `vendor/three/`: Local copy of Three.js and loaders to avoid CDN issues.

    # Note: The IMU viewer is a standalone tool that runs an HTTP server to serve the viewer pages and proxy IMU data from the Pi. It is separate from the main Client UI and should be run independently.
    # The viewer connects to the Pi's control port (5001) to send `CMD_ATTITUDE` commands and receive IMU data, which it uses to animate the 3D model. The viewer also includes diagnostics and will display proxy status, errors, and model load status on the page.
    # To use the viewer, ensure the Pi Server is running and accessible, then run `Demo_IMU_server.py` with the appropriate host and port parameters. Open the provided URL in a web browser to see the live IMU data visualized on the 3D dog model.   
    # Usage: `python3 Demo_IMU_server.py --pi-host <pi-ip> --pi-port 5001 --http-port 8080` 
    then open `http://localhost:8080` in a browser. If the main Client UI is connected to the Pi, disconnect it first since the control port only allows one client at a time.
    # The viewer includes two modes: a simple box model and a colored Pug model. The Pug model is loaded from OBJ/MTL files, and if it fails to load, the viewer falls back to the simple box model. The viewer also displays diagnostics such as proxy status, errors, and model load status on the page for troubleshooting.
    # The IMU data is polled at 10 Hz, and the viewer updates the model's orientation based on the received pitch, roll, and yaw values. This tool is useful for visualizing the robot dog's orientation in real-time based on the IMU data from the Raspberry Pi Server.
    # Note: Ensure that the Pi Server is running and that the control port (5001) is not being used by another client (like the main Client UI) before starting the IMU viewer, as it requires exclusive access to receive IMU data.
    # The viewer is designed to be simple and lightweight, using Three.js for rendering the 3D model and standard JavaScript for handling the HTTP requests and model updates. It serves as a useful tool for debugging and visualizing the robot dog's orientation based on the IMU data from the Raspberry Pi Server.
    # The included Pug model is sourced from Quaternius and is licensed under CC0, allowing for free use and modification. If you want to use a different model, you can replace the OBJ/MTL files in the `assets/quaternius_pug/` directory and update the paths in `app_color.js` accordingly.
    # The viewer also includes error handling and diagnostics to help troubleshoot issues with the proxy connection or model loading. If the viewer cannot connect to the Pi or receive IMU data, it will display error messages on the page to assist with debugging.
    # Overall, this IMU viewer provides a real-time visualization of the robot dog's orientation based on the IMU data from the Raspberry Pi Server, making it a valuable tool for development and debugging.
    # To stop the viewer, simply terminate the `Demo_IMU_server.py` process in the terminal. Terminate the process by pressing `Ctrl+C` in the terminal where it's running. This will shut down the HTTP server and stop the viewer from running.
    # Note: If you want to run the viewer again, ensure that the previous instance is fully terminated and that the control port (5001) is free before starting a new instance of the viewer.
    # the Demo_IMU_server.py script will continue running and serving the viewer pages until it is manually stopped. You can have the viewer running in the background while you work on other tasks, and it will continue to display live IMU data from the Pi as long as it is running and connected to the control port.

## Deep Dive: How Everything Works

### 1) End-to-End Data Flow
1. **Browser loads a viewer page** (`/`, `/simple`, or `/color`).
2. **Viewer JavaScript starts polling** the proxy endpoints:
     - `/imu` for live IMU values (roll, pitch, yaw).
     - `/diag` for connectivity status and the last error.
     - `/version` for the proxy version/time (so you can verify the running server is up-to-date).
3. **Proxy connects to the Pi** over TCP and sends `CMD_ATTITUDE` on the control port (default 5001).
4. **Pi server responds** with a single-line text payload containing IMU values.
5. **Proxy parses the line** into JSON and returns it to the browser.
6. **Viewer applies smoothing** and updates the 3D model rotation at render time.

### 2) Proxy Responsibilities (`Demo_IMU_server.py`)
- **HTTP server**: Serves HTML/JS pages and static assets from this folder.
- **IMU proxy**: Opens a TCP connection to the Pi and requests IMU data via `CMD_ATTITUDE`.
- **Parser**: Extracts `roll`, `pitch`, and `yaw` from the Pi response.
- **Diagnostics**:
    - `/diag` returns host/port, last error, and last successful timestamp.
    - `/version` returns a version string and timestamp so you can validate which proxy build is running.

### 3) Pi Control Port Behavior
- The Pi control port accepts **one client at a time**.
- If the main Client UI is connected, the viewer cannot connect; `/diag` will show errors.
- If the Pi is reachable but the server process is not running, `/diag` will show a connection error.

### 4) Viewer Pages and Scripts
- **Landing page (`/`)**: Shows diagnostics and offers mode selection.
- **Simple view (`/simple`)**: Uses a lightweight box model for fast loading and minimal assets.
- **Color view (`/color`)**: Loads OBJ/MTL assets and shows model load status.

### 5) Polling and Rendering Loop
- **Polling**: JS fetches `/imu` every 100 ms (10 Hz).
- **Smoothing**: Each frame eases the model toward the latest IMU values to reduce jitter.
- **Rendering**: Three.js renders at the browser’s refresh rate for smooth animation.

### 6) Offline Detection and Popups
- If repeated `/imu` requests fail, the viewer shows an **offline popup** with steps to recover:
    1. Ensure the Pi is powered and on the same network.
    2. Confirm `--pi-host` and `--pi-port` values.
    3. Start the Pi server (e.g., `smartdog.sh` or `main.py`).
    4. Check firewall/router settings.

### 7) Model Loading in Color Mode
- The viewer loads **MTL first**, then **OBJ**.
- Progress and errors are displayed in the HUD (Model / Model Err).
- If load fails, the **placeholder box model** remains visible.

### 8) Common Failure Modes (and Where to Look)
- **Blank page or no UI**: Check that the proxy is running and serving `/simple` or `/color`.
- **Status stuck on “starting”**: `/imu` is not returning data; check `/diag`.
- **Color model not showing**: Check Model status/errors; verify OBJ/MTL files exist under `assets/quaternius_pug/`.
- **No live data**: Confirm the Pi server is running and that control port 5001 is free.

### 9) Why the Version/Time Matters
- The `/version` endpoint confirms **which proxy build** is active.
- The timestamp helps verify you restarted the proxy after making changes.

### 10) Extending the Viewer
- Replace the OBJ/MTL model by updating `assets/` and the paths in `app_color.js`.
- Change polling rate or smoothing in the JS files.
- Add new diagnostics in `Demo_IMU_server.py` and expose them via JSON.