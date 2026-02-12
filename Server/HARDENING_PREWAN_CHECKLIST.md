# Hardening Pre-WAN Checklist

## Version
v1.0 (2026-02-09 20:54 local time)

## Revision History
- 2026-02-09 20:54 v1.0  Initial concrete pre-WAN hardening checklist for auth + TLS + TURN execution gate.

## Objective
Provide a concrete gate before allowing remote or untrusted-network access.

## Gate A: Authentication
1. Telemetry/command API:
- Enable `telemetry_api_server.py --api-token <strong-token>` (or systemd env equivalent).
- Verify unauthorized request returns HTTP `401` on:
  - `/api/telemetry`
  - `/api/session`
  - `/api/command`
  - `/api/diagnostics`
2. SFU stream path access:
- Require publish/read credentials in MediaMTX config.
- Verify anonymous RTSP/WHEP access is blocked.
3. Viewer page:
- Avoid embedding secrets in HTML.
- If token is required, inject via secure runtime path (not hardcoded file).

## Gate B: TLS
1. Terminate HTTPS for viewer and APIs (reverse proxy or direct server certs).
2. Ensure WHEP signaling endpoint is exposed as HTTPS/WSS-capable route.
3. Verify certificate trust on Safari/iOS/macOS clients.
4. Confirm `http://` redirects or is LAN-only blocked by firewall.

## Gate C: TURN/STUN
1. Configure STUN/TURN for remote NAT traversal.
2. Add ICE server list to viewer configuration.
3. Validate:
- same-LAN connectivity
- cellular or external network connectivity
- TURN relay fallback behavior under symmetric NAT.

## Gate D: Network Controls
1. Restrict open ports by source IP/subnet where possible.
2. Separate management SSH access from viewer/API access paths.
3. Disable unused services and remove stale unit files.

## Gate E: Operational Verification
1. Run restart drill:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
./phase5_restart_drill.sh
```
2. Run 24h soak probe:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
DURATION_SEC=86400 INTERVAL_SEC=10 ./phase5_soak_probe.sh
```
3. Record results in `PHASE5_VERIFICATION_REPORT.md`.

## Exit Criteria
All gates A-E pass with evidence attached in release notes before WAN exposure.
