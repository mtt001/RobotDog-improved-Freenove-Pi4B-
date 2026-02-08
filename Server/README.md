# Freenove Robot Dog - Server

> **Server-only README** — this file documents the Raspberry Pi Server code and **syncs with the Pi Server side**.

## Version
v1.3.0 (2026-02-08 10:05 local time)

## Quick Start
1. Start server (headless):
```bash
cd /home/pi/Freenove_Robot_Dog_Kit_for_Raspberry_Pi/Code/Server
python3 main.py -tn
```
2. Confirm ports:
```bash
ss -lntp | egrep ':5001|:8001'
```

## Major Changes (v1.3.0)
- Added **multi-client concurrent control socket handlers** on TCP `5001`.
- Kept request/reply routing **per client connection** for telemetry queries.
- Added **control-owner arbitration** for write/actuation commands:
  - first writer becomes owner
  - non-owner write commands are rejected with `CMD_BUSY#OWNER:<ip:port>`
  - safety overrides (`CMD_MOVE_STOP`, `CMD_RELAX`, `CMD_STOP_PWM`) are always accepted
- Preserved proprietary MJPEG path on `8001` for original Freenove clients.

## Concurrency Model
- Port `5001`:
  - Accept loop + per-client worker thread.
  - Multiple concurrent clients can query telemetry at the same time.
  - Write commands are owner-gated for safety.
- Port `8001`:
  - Legacy proprietary JPEG stream remains unchanged.

## Command Safety Policy (5001)
- Read-only/query commands (examples):
  - `CMD_POWER`, `CMD_SONIC`, `CMD_ATTITUDE` (query form), `CMD_WORKING_TIME`
- Owner-gated write commands (examples):
  - motion commands, `CMD_HEAD`, `CMD_HEIGHT`, `CMD_HORIZON`, `CMD_ATTITUDE` (set form), LED/buzzer, calibration, balance
- Always-allowed safety commands:
  - `CMD_MOVE_STOP`, `CMD_RELAX`, `CMD_STOP_PWM`

## Compatibility Notes
- Original Freenove ecosystem remains supported:
  - Original control protocol text format on `5001` preserved.
  - Original proprietary MJPEG stream on `8001` preserved.
- SFU/WebRTC stack is independent and unaffected by this server change.

## Key Files
- `main.py` - entry/startup
- `Server.py` - TCP server core (multi-client control + video socket)
- `Control.py` - actuation loop and command execution
- `Command.md` - command reference

## Diagnostics
- Show listeners:
```bash
ss -lntp | egrep ':5001|:8001'
```
- Show control clients:
```bash
ss -tnp | grep ':5001'
```
- Tail server log:
```bash
tail -n 200 /tmp/smartdog.log
```

## Revision History
- 2026-02-08 10:05 v1.3.0  Added multi-client 5001 concurrency with owner arbitration and preserved 8001 MJPEG compatibility.
- 2026-02-06 22:07 v1.2.1  Added timestamps to revision history.
- 2026-02-06 v1.2.0  Added battery/power notes and UBEC/BEC search results.
