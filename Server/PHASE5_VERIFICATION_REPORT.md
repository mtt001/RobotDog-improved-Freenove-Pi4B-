# Phase 5 Verification Report

## Version
v1.5 (2026-02-09 21:23 local time)

## Revision History
- 2026-02-09 21:23 v1.5  Added executed failure-injection results (publisher/SFU interruption and measured recovery times) and resumed 24h soak.
- 2026-02-09 21:20 v1.4  Added failure-injection drill artifact and result section for publisher/SFU interruption recovery.
- 2026-02-09 21:01 v1.3  Added 24h soak-launch status with background process/log monitoring commands.
- 2026-02-09 20:56 v1.2  Added optional API auth-gate verification results and hardening checklist artifact.
- 2026-02-09 20:50 v1.1  Added executed restart-drill results and 180s soak-probe pass metrics after Pi connectivity recovery.
- 2026-02-09 20:44 v1.0  Initial Phase-5 execution report with completed checks, created artifacts, and current Pi connectivity blocker.

## Scope
Phase-5 progress verification for:
- startup ordering and dependency checks
- diagnostics endpoint
- cache-control strategy
- restart/soak verification tooling

## Completed Validation (Before Connectivity Loss)
Executed and passed on Pi:
1. Service reload/restart after updated units:
- `robot-sfu.service`
- `robot-publisher.service`
- `robot-viewer.service`
- `robot-telemetry.service`
2. Expanded health checker:
- `./phase1_health_check.sh` passed with:
  - viewer `200`
  - WHEP OPTIONS `204`
  - telemetry/session/diagnostics APIs `200`
  - RTSP DESCRIBE `200`
3. Diagnostics endpoint:
- `GET /api/diagnostics` returned service/port/session summary JSON.
4. Viewer cache/health:
- `GET /webrtc_view.html` includes `Cache-Control: no-store`
- `GET /health` verified with single `Cache-Control: no-store` after `static_viewer_server.py` v1.1 fix.

## Artifacts Prepared Locally
1. `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/phase5_restart_drill.sh`
- restart drill for smartdog/SFU/publisher/viewer/telemetry with endpoint checks
2. `/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/phase5_soak_probe.sh`
- short soak probe loop for service and endpoint continuity

## Connectivity Incident (Recovered)
At 2026-02-09 20:43~20:44 local time:
- Pi became unreachable intermittently:
  - `ssh: connect to host 192.168.0.32 port 22: Host is down`
  - ping showed unstable response / high loss.
Recovery:
- Connectivity recovered and deployment/testing resumed.

## Restart Drill Results (Executed)
Command:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
./phase5_restart_drill.sh
```
Observed:
- Service active recovery (ms):
  - smartdog: 255
  - robot-sfu: 341
  - robot-publisher: 305
  - robot-telemetry: 290
  - robot-viewer: 291
- Endpoint checks: all pass (`viewer`, `/health`, WHEP OPTIONS, telemetry/session/diagnostics API).
- RTSP DESCRIBE needed warm-up retry after restart sequence; final result passed (`200 OK`).

## Soak Probe Results (Executed)
Command:
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
DURATION_SEC=180 INTERVAL_SEC=5 ./phase5_soak_probe.sh
```
Observed:
- rounds: `31`
- fails: `0`
- result: `pass`

## Optional API Auth Gate Verification (Executed)
Implementation:
- `telemetry_api_server.py` supports `--api-token <token>` (default empty = disabled).

Validation (isolated test instance on Pi, port `8192`):
- no auth header: `401`
- `Authorization: Bearer testtoken`: `200`

Result:
- optional auth gate works as designed and does not affect default deployment when token is unset.

## Hardening Artifact Added
- `HARDENING_PREWAN_CHECKLIST.md`
- Includes concrete gates for authentication, TLS, TURN/STUN, network controls, and operational verification.

## 24h Soak (Started)
Launch command (Pi):
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
nohup env DURATION_SEC=86400 INTERVAL_SEC=10 ./phase5_soak_probe.sh > /tmp/phase5_soak_24h.log 2>&1 &
```
Live monitor:
```bash
tail -f /tmp/phase5_soak_24h.log
pgrep -af phase5_soak_probe.sh
```

## Failure Injection Drill Artifact
- `phase5_failure_injection.sh`
- Purpose:
  - stop publisher briefly and verify RTSP interruption/recovery
  - stop SFU briefly and verify WHEP interruption/recovery
  - confirm post-check health on viewer/telemetry/diagnostics/RTSP

## Failure Injection Results
- Executed on Pi (`2026-02-09 21:22~21:23`):
  - baseline checks: viewer/telemetry/WHEP/RTSP all pass
  - Drill A (publisher interruption):
    - RTSP interruption observed as expected
    - RTSP recovery: `4s`
  - Drill B (SFU interruption):
    - WHEP interruption observed as expected
    - WHEP recovery: `1s`
  - post checks: viewer/telemetry/diagnostics/RTSP all pass
- Log file:
  - `/tmp/phase5_failure_injection_last.log`

## 24h Soak (Resumed)
- Restarted after failure-injection run via transient unit:
  - unit: `phase5-soak2.service`
  - log: `/home/pi/phase5_soak_24h.log`

## Resume Checklist (When Pi Is Back)
1. Copy latest scripts and server files to Pi:
```bash
scp Server/phase5_restart_drill.sh pi@192.168.0.32:/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
scp Server/phase5_soak_probe.sh pi@192.168.0.32:/home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/
```
2. Ensure executable bits:
```bash
ssh pi@192.168.0.32 "chmod +x /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/phase5_restart_drill.sh /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server/phase5_soak_probe.sh"
```
3. Run restart drill:
```bash
ssh pi@192.168.0.32 "cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server && ./phase5_restart_drill.sh"
```
4. Run short soak probe (example 10 min):
```bash
ssh pi@192.168.0.32 "cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server && DURATION_SEC=600 INTERVAL_SEC=5 ./phase5_soak_probe.sh"
```
5. Run long soak (24h target, still pending):
```bash
ssh pi@192.168.0.32 "cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server && DURATION_SEC=86400 INTERVAL_SEC=10 ./phase5_soak_probe.sh"
```
