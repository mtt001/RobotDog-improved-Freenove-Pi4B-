#coding:utf-8
"""
Servo Control Module

Version: 1.1.0
Date: 2025-12-21
Author: Freenove

Description:
    Provides a thin wrapper around the PCA9685 PWM driver to position hobby
    servos with clamped angle limits and a convenience main routine for quick
    centering (90°) during setup or maintenance.

Revision History:
    1.1.0 (2025-12-21) - Added stop_all_pwm() to disable all servo outputs.
    1.0.0 (2024-12-21) - Initial servo control implementation.
"""

import Adafruit_PCA9685
import time

class Servo:
    def __init__(self):
        self.angleMin = 18
        self.angleMax = 162
        # initialize PCA9685 (address and busnum may vary on your board)
        self.pwm = Adafruit_PCA9685.PCA9685(address=0x40, busnum=1)
        self.pwm.set_pwm_freq(50)               # Set the cycle frequency of PWM, period is 20ms for frequency 50Hz, 
        #   for 90° servo the pulse width is typically 1.5ms, which is 1.5/20*4096=307, 0° is 1ms(204), 180° is 2ms(409), 

    # Convert the input angle to the value for PCA9685
    def map(self, value, fromLow, fromHigh, toLow, toHigh):
        return (toHigh - toLow) * (value - fromLow) / (fromHigh - fromLow) + toLow

    def setServoAngle(self, channel, angle):
        if angle < self.angleMin:
            angle = self.angleMin
        elif angle > self.angleMax:
            angle = self.angleMax
        pulse = self.map(angle, 0, 180, 102, 512)
        # print(pulse, pulse / 4096 * 0.02)
        self.pwm.set_pwm(channel, 0, int(pulse))

    def stop_all_pwm(self):
        """Stop PWM pulses on all 16 channels (servos go limp)."""
        try:
            # On this hardware, OFF=0 gates outputs and frees the servos
            for channel in range(16):
                self.pwm.set_pwm(channel, 0, 0)
            print("✓ stop_all_pwm(), All servo PWM outputs disabled (servos now limp and released ...)")
        except Exception as e:
            print(f"❌ stop_all_pwm error: {e}")

# Main program logic follows:
if __name__ == '__main__':
    print("Now servos will rotate to 90°.")
    print("If they have already been at 90°, nothing will be observed.")
    print("Please keep the program running when installing the servos.")
    print("After that, you can press ctrl-C to end the program.")
    S = Servo()
    try:
        while True:
            for i in range(16):
                S.setServoAngle(i, 90)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nEnd of program")
