# Remote Safari Access Runbook (Outside Home Network)

## Version
v1.0 (2026-02-10 07:40 local time)

## Revision History
- 2026-02-10 07:40 v1.0  Initial remote-access runbook with recommended Tailscale path and advanced direct-WAN path.

## Goal
Enable iPhone Safari access to the Pi-hosted viewer when the phone is outside home LAN.

## Current Blockers (Observed)
- `mediamtx.yml` is LAN-only:
  - `webrtcAdditionalHosts` includes only `192.168.0.32` and `127.0.0.1`.
  - no STUN/TURN configuration.
  - `webrtcEncryption: no` (HTTP/WHEP only).
- Outside home network, Safari cannot reach LAN ICE candidates, so WebRTC setup fails.

## Recommended Resolution Path (Priority)
Use Tailscale first (fastest, safest, lowest ops risk), then evaluate direct WAN if needed.

### Path A (Recommended): Tailscale Private Remote Access
Why:
- No router port-forwarding.
- Encrypted private overlay network.
- Fast to deploy and easy to rollback.

### Steps (Pi)
1. Install and login Tailscale on Pi.
2. Enable/start service.
3. Record Pi Tailscale IPv4 (typically `100.x.y.z`).
4. Add that IP to MediaMTX ICE host list (`webrtcAdditionalHosts`).
5. Restart `robot-sfu.service`.

### Steps (iPhone)
1. Install Tailscale app and join same tailnet.
2. Turn Tailscale VPN on.
3. Open Safari URL using Pi Tailscale IP:
   - `http://<pi-tailscale-ip>:8080/webrtc_view.html`

### Verify
- Viewer loads and shows build badge.
- WHEP connect works and `Peer connected` is reached.
- Telemetry overlay updates.

### Security notes
- Still LAN-baseline auth model unless API token gate is turned on.
- Recommended for trusted-user private remote operations only.

## Path B (Advanced): Direct Internet (Public WAN)
Use only when VPNless/public access is required.

Prerequisites:
- Domain name + DNS control.
- HTTPS/TLS certs for viewer/API/signaling.
- TURN server for NAT traversal reliability.
- Explicit auth policy.

High-level steps:
1. Configure public DNS to home endpoint.
2. Enable TLS for viewer + API + WHEP endpoints.
3. Add STUN/TURN servers in MediaMTX WebRTC config.
4. Expose required ports on router/firewall (carefully).
5. Enforce auth controls and rate limits.
6. Validate via cellular and non-home Wi-Fi.

Do not skip:
- `Server/HARDENING_PREWAN_CHECKLIST.md`

## Minimal Acceptance (Remote)
- iPhone Safari outside home LAN can:
  - load viewer page
  - connect and view video
  - receive telemetry updates
- command safety behavior remains unchanged:
  - disarmed by default
  - owner/session gate enforced

## Rollback
If remote access is unstable or risky:
1. Disable remote route (Tailscale off or WAN exposure removed).
2. Keep local LAN mode only.
3. Restart `robot-sfu.service`, `robot-viewer.service`, `robot-telemetry.service`.

## Useful Commands (Pi)
```bash
systemctl is-active robot-sfu.service robot-viewer.service robot-telemetry.service
ss -lntup | egrep ':8080|:8090|:8889|:8554'
```

```bash
# Viewer/API quick checks from Pi
curl -I http://127.0.0.1:8080/webrtc_view.html | head -n 1
curl -s http://127.0.0.1:8090/api/telemetry
```
