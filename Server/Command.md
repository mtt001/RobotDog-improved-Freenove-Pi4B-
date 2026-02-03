# Robot Dog Command Reference

Date: 2026-01-22

This document lists all server-side commands handled by the control socket and how to use them.

## Transport

- Control/telemetry TCP: port 5001
- Video TCP: port 8001 (JPEG stream, length-prefixed frames)

Control commands are UTF-8 text lines terminated by \n. Fields are separated by #:

- Format: COMMAND#param1#param2#param3#param4\n
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

## Details and Notes

### Motion commands
- All motion commands accept a single integer speed parameter.
- The server does not clamp `speed`; it is used as the step size in gait loops. Larger values update targets faster (quicker/jerkier). Smaller values update targets slower (smoother).
- Avoid 0 or negative values (they can stall the loop). Default speed is 8.
- Motion commands are not queued. Each incoming command overwrites the current `order`, so the latest command wins.
- CMD_MOVE_STOP is applied immediately, but the server may ignore rapid STOP packets right after a move command to smooth joystick noise.

Examples:
- CMD_MOVE_FORWARD#8\n
### Relax and PWM
- CMD_RELAX forces relax posture (no toggle). Servos remain powered.
- CMD_STOP_PWM fully disables servo PWM outputs.

Examples:
- CMD_RELAX\n
### Head and posture
- CMD_HEAD uses a single angle in degrees (0-180).
- CMD_HEIGHT and CMD_HORIZON expect integer values used by the gait controller.
- CMD_ATTITUDE uses three numeric parameters: roll, pitch, yaw.

Examples:
- CMD_HEAD#90\n
### Calibration
- Update a single leg calibration point and recompute offsets:
  - CMD_CALIBRATION#one#x#y#z
  - CMD_CALIBRATION#two#x#y#z
  - CMD_CALIBRATION#three#x#y#z
  - CMD_CALIBRATION#four#x#y#z
- Save current calibration to point.txt:
  - CMD_CALIBRATION#save

### LEDs
Format is handled by Led.light(data):
- mode is a string digit:
  - 0: off
  - 1: solid color
  - 2: RGB wipe loop
  - 3: theater chase loop
  - 4: rainbow loop
  - 5: rainbow cycle loop
- r/g/b are 0-255 integers.

Example:
- CMD_LED#1#255#0#0\n (solid red)

### Buzzer
- CMD_BUZZER#1 turns buzzer on.
- CMD_BUZZER#0 turns buzzer off.

### Sensors and telemetry
- CMD_SONIC returns ultrasonic distance as centimeters.
- CMD_POWER returns the highest of the last 5 ADC samples as voltage (V).
- CMD_WORKING_TIME returns active time and rest time. If overuse protection is disabled, rest time is 0.

### Low-battery lockout
Low-battery protection runs continuously on the server (even with no client connected).

Behavior summary:
- Voltage is sampled from the ADC once per second.
- Low-battery threshold: 6.1 V.
- A low-voltage condition is declared only after it stays below the threshold for 3 seconds (debounce).
- Once confirmed, the server forces a safe posture (CMD_RELAX) immediately, then disables PWM (CMD_STOP_PWM) after 3 seconds.
- While low voltage persists, the server emits warning signals every 5 seconds (2 short buzzer beeps + 1 red LED flash).
- The server does not shut down or close ports; it only enforces motion lockout and safety posture.

Command lockout:
- When low-battery mode is active, only these commands are accepted:
  - CMD_POWER, CMD_SONIC, CMD_WORKING_TIME, CMD_RELAX, CMD_STOP_PWM
- All other commands are ignored until voltage recovers above the threshold.

### Socket auto-recovery (ports 5001 and 8001)
The server runs a health monitor that keeps both LISTEN sockets open:
- If a LISTEN socket is missing/closed, it auto-reopens ports 8001 (video) and 5001 (control).
- Health logs print every 15 seconds.
- Reopen attempts are rate-limited with a 2-second backoff.
