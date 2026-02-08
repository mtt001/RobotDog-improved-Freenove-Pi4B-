# Real-Time WebRTC Stack (Low-Latency Multi-Client)

## Goal
Provide a low-latency, stable, browser-compatible control/video stack for ground robots:
- Robot Pi publishes one stream
- SFU fans out to many subscribers
- Mac AI client has motion authority
- iPhone/browser is monitor-only by default

## Architecture
- Video: WebRTC RTP/UDP
- Topology: `Pi Publisher -> SFU -> (Mac AI, iPhone Monitor, other viewers)`
- Codec: H.264 (hardware path on Pi when available)
- Control + telemetry: WebRTC DataChannel via control gateway

## Components
1. `sfu/` - Media relay (no transcoding) configuration and compose file
2. `robot/` - Pi publisher script and service file
3. `control/` - WebRTC DataChannel authority gateway (Mac has motion authority)
4. `mac/` - AI subscriber skeleton (frame callback for YOLO/OpenCV)
5. `monitor/` - Browser monitor scaffolding
6. `docs/` - rollout and operations notes

## Why this split
- SFU is optimized for video fanout and low latency
- Control requires explicit authority + safety policy, handled by gateway
- Decoupling avoids control regressions when video churns

## Rollout order
1. Bring up SFU and verify browser playback
2. Move Pi camera publish into SFU
3. Bring up DataChannel gateway and authority lock
4. Attach Mac AI loop + command publishing
5. Keep monitor as receive-only role

## Current repo state
Your existing `Client/tools/imu_viewer` remains usable as fallback.
This folder is the migration path to production low-latency teleop.
