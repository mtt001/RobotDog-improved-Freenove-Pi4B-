"""
Command Constants Module

Version: 1.1.1
Date: 2026-01-10
Author: Freenove

Revision History:
    1.1.1 (2026-01-10) - Added keyboard mapping notes for client usage.
    1.1.0 (2025-12-21) - Added CMD_STOP_PWM to disable all servo PWM outputs.
        new command useful for safely powering down servos. Usage: 
            command = cmd.CMD_STOP_PWM + "\n"
            self.send_data(command)
    1.0.0 (2024-12-21) - Initial command set for movement, sensors, and control.

Keyboard mapping (mtDogMain.py):
    Space : stop          -> CMD_MOVE_STOP
    E     : forward       -> CMD_MOVE_FORWARD
    C     : backward      -> CMD_MOVE_BACKWARD
    S     : strafe left   -> CMD_MOVE_LEFT
    F     : strafe right  -> CMD_MOVE_RIGHT
    W     : turn left     -> CMD_TURN_LEFT
    R     : turn right    -> CMD_TURN_RIGHT
    D     : relax         -> CMD_RELAX

Note: motion/turn commands are typically sent as `CMD_*#<speed>`.
"""

class COMMAND:
    CMD_MOVE_STOP = "CMD_MOVE_STOP"            # Space
    CMD_MOVE_FORWARD = "CMD_MOVE_FORWARD"      # E
    CMD_MOVE_BACKWARD = "CMD_MOVE_BACKWARD"    # C
    CMD_MOVE_LEFT = "CMD_MOVE_LEFT"            # S
    CMD_MOVE_RIGHT = "CMD_MOVE_RIGHT"          # F
    CMD_TURN_LEFT = "CMD_TURN_LEFT"            # W
    CMD_TURN_RIGHT = "CMD_TURN_RIGHT"          # R
    CMD_BUZZER = "CMD_BUZZER"
    CMD_LED_MOD = "CMD_LED_MOD"
    CMD_LED = "CMD_LED"
    CMD_BALANCE = "CMD_BALANCE"
    CMD_SONIC = "CMD_SONIC"
    CMD_HEIGHT = "CMD_HEIGHT"
    CMD_HORIZON = "CMD_HORIZON"
    CMD_HEAD = "CMD_HEAD"
    CMD_CALIBRATION = "CMD_CALIBRATION"
    CMD_POWER = "CMD_POWER"              # Power status# show voltage
    CMD_ATTITUDE = "CMD_ATTITUDE"
    CMD_RELAX = "CMD_RELAX"                    # D
    CMD_WORKING_TIME = "CMD_WORKING_TIME"
    CMD_STOP_PWM = "CMD_STOP_PWM"
    def __init__(self):
        pass
