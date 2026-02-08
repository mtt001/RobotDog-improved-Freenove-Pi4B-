# Freenove Robot Dog - Client

## Version
v1.4.0 (2026-02-08 10:06 local time)

## Quick Start (new users)
1. Enter client environment first:
```bash
smartdog
```
2. Launch main console:
```bash
python3 mtDogMain.py
```

## Quick Start (SFU low-latency video)
1. Start SFU on Mac:
```bash
/opt/homebrew/opt/mediamtx/bin/mediamtx /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/realtime_webrtc/sfu/mediamtx.yml
```
2. Start Pi publisher:
```bash
ssh pi@192.168.0.32 'cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/tools/realtime_webrtc/robot && nohup env SFU_HOST=192.168.0.198 STREAM_PATH=robotdog PUBLISH_MODE=rtsp WIDTH=1280 HEIGHT=720 FPS=30 BITRATE=3500000 ./pi_publish_webrtc.sh >/tmp/pi_publish_webrtc.log 2>&1 < /dev/null &'
```
3. Launch client:
```bash
smartdog python3 mtDogMain.py
```

## Major Changes (v1.4.0)
- Pi server `5001` now supports multiple concurrent control socket clients.
- Write commands are owner-arbitrated on server side for safety.
- Read/query telemetry can be served concurrently.
- Legacy proprietary MJPEG (`8001`) compatibility preserved on Pi side.

## Multi-Client Usage (Mac + iPhone example)
- MacBook:
  - Use `mtDogMain.py` as main operator console (control + telemetry + video).
- iPhone web viewer:
  - Use web live viewer for additional monitoring.
  - If issuing write commands from iPhone while Mac owns control, server returns `CMD_BUSY#OWNER:<ip:port>`.
  - Safety stop commands remain accepted.

## Architecture Overview
- Control + telemetry + IMU: Pi TCP `5001`
- Video default: SFU RTSP (`rtsp://<sfu>:8554/<stream>`)
- Legacy video fallback path: Pi proprietary JPEG stream on `8001`

## Configuration (`config/mtDogConfig.py`)
- `VIDEO_BACKEND = "sfu_rtsp"` or `"legacy_socket"`
- `SFU_HOST`, `SFU_RTSP_PORT`, `SFU_STREAM_PATH`, `SFU_RTSP_URL`, `SFU_RTSP_TRANSPORT`
- `VIDEO_TARGET_WIDTH`, `VIDEO_TARGET_HEIGHT`, `VIDEO_TARGET_FPS`, `VIDEO_TARGET_BITRATE`

## Key Files
- `mtDogMain.py`
- `mtDogLogicMixin.py`
- `controllers/video_source_controller.py`
- `controllers/frame_update_controller.py`
- `controllers/server_reconnect_controller.py`

## Diagnostics
- 5001/8001 reachability:
```bash
smartdog python3 - <<'PY'
import socket
for h,p in [('192.168.0.32',5001),('192.168.0.32',8001)]:
 s=socket.socket(); s.settimeout(2)
 try:
  s.connect((h,p)); print('OK',h,p)
 except Exception as e:
  print('FAIL',h,p,e)
 s.close()
PY
```
- Client log:
```bash
tail -n 200 /Users/mengtatsai/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Client/mtDogMain.log
```

## Code Scale Analysis (2026-02-08)

Overall project LOC (code-like extensions in Code/): **253,382**

By extension:
- .py: 93,039
- .js: 55,742
- .ts: 12,302
- .html: 615
- .md: 22,616
- .json: 24,657
- .yml: 42,681
- .yaml: 248
- .sh: 1,482

mtDogMain-related LOC subtotal: **9,890**

Per-file LOC:
- [mtDogMain.py](mtDogMain.py): 1,875
- [mtDogLogicMixin.py](mtDogLogicMixin.py): 1,040
- [config/mtDogConfig.py](config/mtDogConfig.py): 61
- [controllers/ball_tracking_controller.py](controllers/ball_tracking_controller.py): 825
- [controllers/client_camera_controller.py](controllers/client_camera_controller.py): 291
- [controllers/dog_command_controller.py](controllers/dog_command_controller.py): 153
- [controllers/frame_update_controller.py](controllers/frame_update_controller.py): 857
- [controllers/server_reconnect_controller.py](controllers/server_reconnect_controller.py): 113
- [controllers/telemetry_controller.py](controllers/telemetry_controller.py): 73
- [controllers/video_source_controller.py](controllers/video_source_controller.py): 219
- [ui/status_ui_controller.py](ui/status_ui_controller.py): 75
- [ui/ui_event_handlers.py](ui/ui_event_handlers.py): 422
- [ui/control_panel_sections.py](ui/control_panel_sections.py): 133
- [vision/ai_vision_controller.py](vision/ai_vision_controller.py): 425
- [vision/cv_hist_debug.py](vision/cv_hist_debug.py): 135
- [vision/mask_picker.py](vision/mask_picker.py): 180
- [vision/yolo_runtime.py](vision/yolo_runtime.py): 1,883
- [vision/legacy/cv_ball_detection.py](vision/legacy/cv_ball_detection.py): 198
- [vision/utils/motion_grid_builder.py](vision/utils/motion_grid_builder.py): 170
- [vision/utils/overlay_renderer.py](vision/utils/overlay_renderer.py): 403
- [tools/yolo/yolo_labeling.py](tools/yolo/yolo_labeling.py): 359

## Revision History
- 2026-02-08 10:06 v1.4.0  Added multi-client 5001 behavior notes and owner-arbitration usage guidance.
- 2026-02-07 20:45 v1.3.0  Added SFU backend + smartdog launcher major changes.
