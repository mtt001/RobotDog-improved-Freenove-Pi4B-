"""
Command Constants Module

Version: 1.1.0
Date: 2025-12-21
Author: Freenove

Revision History:
    1.1.0 (2025-12-21) - Added CMD_STOP_PWM to disable all servo PWM outputs.
    1.0.0 (2024-12-21) - Initial command set for movement, sensors, and control.
"""

class COMMAND:
    CMD_MOVE_STOP = "CMD_MOVE_STOP"     # Key 'x'
    CMD_MOVE_FORWARD = "CMD_MOVE_FORWARD" # Key 'w'
    CMD_MOVE_BACKWARD = "CMD_MOVE_BACKWARD"  # Key 's'
    CMD_MOVE_LEFT = "CMD_MOVE_LEFT"  # Key 'a'
    CMD_MOVE_RIGHT = "CMD_MOVE_RIGHT"  # Key 'd'
    CMD_TURN_LEFT = "CMD_TURN_LEFT" # Key 'q'
    CMD_TURN_RIGHT = "CMD_TURN_RIGHT"   # Key 'e'
    CMD_BUZZER = "CMD_BUZZER"       # Key 'b'
    CMD_LED_MOD = "CMD_LED_MOD"     # Key 'l'
    CMD_LED = "CMD_LED"             # Key 'k'
    CMD_BALANCE = "CMD_BALANCE"     # Key 'p'     
    CMD_SONIC = "CMD_SONIC"         # Key 'o'
    CMD_HEIGHT = "CMD_HEIGHT"       # Key 'h'
    CMD_HORIZON = "CMD_HORIZON"     # Key 'j'
    CMD_HEAD = "CMD_HEAD"           # Key 'h'
    CMD_CALIBRATION = "CMD_CALIBRATION" # Key 'c'
    CMD_POWER = "CMD_POWER"         # Key 'u'
    CMD_ATTITUDE = "CMD_ATTITUDE"   # Key 'i'
    CMD_RELAX = "CMD_RELAX"         # Key 'r'
    CMD_WORKING_TIME = "CMD_WORKING_TIME"   # Key 't'
    CMD_STOP_PWM = "CMD_STOP_PWM"   # Key 'Space' - Disable all servo PWM outputs
    def __init__(self):
        pass
