# Deployment (Phase-1)

## 1) SFU host (Mac mini / server)
```bash
cd Client/tools/realtime_webrtc/sfu
docker compose up -d
```

Validate:
```bash
curl -I http://127.0.0.1:8889/
```

## 2) Pi publisher
Copy `robot/` folder to Pi and run:
```bash
cd robot
SFU_HOST=192.168.0.198 STREAM_PATH=robotdog PUBLISH_MODE=whip ./pi_publish_webrtc.sh
```

If ffmpeg WHIP muxer unsupported, fallback:
```bash
SFU_HOST=192.168.0.198 STREAM_PATH=robotdog PUBLISH_MODE=rtsp ./pi_publish_webrtc.sh
```

## 3) DataChannel gateway
On control host:
```bash
python3 Client/tools/realtime_webrtc/control/dc_authority_gateway.py \
  --pi-host 192.168.0.32 --pi-port 5001 --http-port 8787 \
  --authority-token mac-ai-authority
```

## 4) Mac AI client
```bash
python3 Client/tools/realtime_webrtc/mac/mac_ai_webrtc_client.py \
  --whep-url http://192.168.0.198:8889/robotdog/whep \
  --gateway-url http://192.168.0.198:8787 \
  --authority-token mac-ai-authority
```

## 5) iPhone monitor
Serve `monitor/index.html` and open in Safari.
Set player iframe/gateway IPs to SFU host.

## Safety notes
- Only authority token holder can send motion commands.
- Keep emergency stop mapped to `CMD_MOVE_STOP` and `CMD_STOP_PWM`.
- Add watchdog on Pi to force stop on stale authority heartbeat.
