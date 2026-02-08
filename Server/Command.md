# Robot Dog Command Reference

Version: v1.3.0
Updated: 2026-02-08 10:05 (local time)

This document lists server-side commands handled on control TCP port `5001`.

## Transport
- Control/telemetry TCP: `5001`
- Video TCP: `8001` (proprietary JPEG stream)

Control messages are UTF-8 text lines terminated by `\n`:
- `COMMAND#param1#param2#param3#param4\n`

## Multi-Client Policy (v1.3.0)
- Port `5001` supports **multiple concurrent client connections**.
- Telemetry/query responses are sent back to the requesting connection.
- Write/actuation commands are guarded by a **control owner**.
- Non-owner write command response:
  - `CMD_BUSY#OWNER:<ip:port>\n`
- Safety overrides are accepted from any client:
  - `CMD_MOVE_STOP`, `CMD_RELAX`, `CMD_STOP_PWM`

## Command Summary
| Command | Params | Description | Response |
| --- | --- | --- | --- |
| CMD_MOVE_STOP | none | Stop motion immediately. | none |
| CMD_MOVE_FORWARD | speed | Walk forward at speed. | none |
| CMD_MOVE_BACKWARD | speed | Walk backward at speed. | none |
| CMD_MOVE_LEFT | speed | Step left at speed. | none |
| CMD_MOVE_RIGHT | speed | Step right at speed. | none |
| CMD_TURN_LEFT | speed | Turn left at speed. | none |
| CMD_TURN_RIGHT | speed | Turn right at speed. | none |
| CMD_RELAX | none | Enter relax posture (PWM stays on). | none |
| CMD_STOP_PWM | none | Disable all servo PWM outputs. | none |
| CMD_HEIGHT | value | Adjust body height. | none |
| CMD_HORIZON | value | Shift body forward/back. | none |
| CMD_ATTITUDE | roll#pitch#yaw | Set body attitude angles. | none |
| CMD_BALANCE | 1 | Enable balance/IMU mode. | none |
| CMD_HEAD | angle | Set head servo angle (0-180). | none |
| CMD_CALIBRATION | one/two/three/four#x#y#z | Update calibration point for a leg. | none |
| CMD_CALIBRATION | save | Save calibration to point.txt. | none |
| CMD_LED | mode#r#g#b | Set LED mode and color. | none |
| CMD_LED_MOD | mode#r#g#b | Same as CMD_LED; allows mode change. | none |
| CMD_BUZZER | value | Buzzer on/off (use 1 or 0). | none |
| CMD_SONIC | none | Request ultrasonic distance. | CMD_SONIC#distance\n |
| CMD_POWER | none | Request battery voltage. | CMD_POWER#voltage\n |
| CMD_WORKING_TIME | none | Request working time/overuse info. | CMD_WORKING_TIME#active#rest\n |

## Owner-Arbitration Notes
- Owner-gated writes include motion, head/body posture writes, LED/buzzer, calibration, and balance.
- `CMD_ATTITUDE` behavior:
  - query form (`CMD_ATTITUDE`) is read-only
  - set form (`CMD_ATTITUDE#roll#pitch#yaw`) is owner-gated write

## Low-Battery Lockout
When low-battery mode is active, command acceptance is restricted server-side.
Allowed commands:
- `CMD_POWER`, `CMD_SONIC`, `CMD_WORKING_TIME`, `CMD_RELAX`, `CMD_STOP_PWM`, `CMD_ATTITUDE`

## Socket Auto-Recovery
Health monitor keeps LISTEN sockets alive:
- auto-reopen on `5001` and `8001` if listener disappears
- periodic health logs (when enabled)
