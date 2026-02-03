"""
Server-side Test Script - Dog Head Servo Sweep

Version: 2.0.0
Date: 2025-12-23
Author: Refactored from Client-side control

Description:
    Direct server-side control for sweeping the dog head servo through a sequence
    of angles: 90° -> 45° -> 90° -> 135° (1° steps, 0.2s delay per step, 2s hold).
    Controls servos, buzzer, and LEDs directly without network socket communication.
    
Changes from v1.0:
    - Refactored from Client socket control (port 5001) to direct Server-side control
    - Uses Servo, Buzzer, and Led modules directly instead of Client commands
    - Removed network dependencies (Client, IP.txt, socket communication)
    - Maintains same behavior and timing characteristics
    - Servo channel 15 is used for head control (matches server CMD_HEAD mapping)

Usage:
    Run directly on the robot dog Raspberry Pi:
    python3 testHeadMoving.py
    
    Press 'q' then Enter to stop the sweep loop gracefully.
"""
import time
import threading
from typing import Optional

from Servo import Servo
from Buzzer import Buzzer
from Led import Led

HEAD_SERVO_CHANNEL = 15  # Servo channel for head control (same as Server CMD_HEAD)
STEP_DEG = 1
STEP_DELAY_S = 0.2
HOLD_S = 2.0
SAFE_MIN = 18      # Hardware minimum angle
SAFE_MAX = 162     # Hardware maximum angle

# ----------------------------------------------------------------------------------
def clamp_angle(angle: float) -> int:
    """Clamp angle to safe servo range."""
    return max(SAFE_MIN, min(SAFE_MAX, int(round(angle))))


def set_head_angle(servo: Servo, angle_deg: int) -> None:
    """
    Set head servo angle directly on the hardware.
    """
    clamped = clamp_angle(angle_deg)
    servo.setServoAngle(HEAD_SERVO_CHANNEL, clamped)


def stop_all_servos(servo: Servo) -> None:
    """
    Stop all servo PWM outputs for safe power-down.
    """
    servo.stop_all_pwm()    # Call the method from Servo class in Servo.py


def beep(buzzer: Buzzer, duration: float = 0.1, pause: float = 0.1, count: int = 1) -> None:
    """
    Drive the buzzer with simple on/off pulses.
    """
    for _ in range(count):
        buzzer.run("1")
        time.sleep(duration)
        buzzer.run("0")
        time.sleep(pause)


def flash_blue_led(led: Led, duration: float = 0.2) -> None:
    """Flash solid blue on all LEDs."""
    # Blue: R=0, G=0, B=255
    led.colorWipe(led.strip, 0x0000FF, wait_ms=0)
    time.sleep(duration)
    led.colorWipe(led.strip, 0x000000, wait_ms=0)  # Turn off


def ramp(servo: Servo, buzzer: Buzzer, led: Led, start: int, target: int, 
         stop_event: Optional[threading.Event] = None) -> int:
    """Smoothly ramp from start angle to target angle with visual feedback."""
    step = STEP_DEG if target >= start else -STEP_DEG
    for ang in range(start, target + step, step):
        if stop_event is not None and stop_event.is_set():
            return clamp_angle(ang)
        clamped = clamp_angle(ang)
        set_head_angle(servo, clamped)
        print(f"Head: {clamped}°", end='\r', flush=True)
        time.sleep(STEP_DELAY_S)
    print(f"Head: {target}° [target reached]")
    beep(buzzer, count=1)
    time.sleep(HOLD_S)
    # Beep when reaching 90 deg target
    if target == 90:
        beep(buzzer, count=1)
        flash_blue_led(led)
    return target

# =================================================================================
def main():
    """Main execution loop for head servo sweep test."""
    # Initialize hardware modules
    servo = Servo()
    buzzer = Buzzer()
    led = Led()
    
    print("Initializing robot dog head servo sweep test (server-side)...")
    print("Hardware modules loaded: Servo, Buzzer, LED")
    
    try:
        # Set all servos to 90° at start
        print("Setting all servos to 90°...")
        for channel in range(16):
            servo.setServoAngle(channel, 90)
        time.sleep(1.0)
        
        # Power off all servos for 5 seconds
        stop_all_servos(servo)
        print("All servo PWM outputs disabled (servos limp for 5 seconds)...")
        time.sleep(5.0)
        
        # Head to 90° before looping
        current = clamp_angle(90)
        set_head_angle(servo, current)
        print(f"Head centered at {current}°")
        time.sleep(HOLD_S)
        beep(buzzer, count=2)
        flash_blue_led(led)

        # Input listener for 'q' to quit loop and exit
        stop_event = threading.Event()

        def wait_for_q():
            while not stop_event.is_set():
                try:
                    line = input()
                except EOFError:
                    break
                if line.strip().lower() == 'q':
                    stop_event.set()

        threading.Thread(target=wait_for_q, daemon=True).start()

        sequence = [90, 45, 90, 135]
        print(f"Starting continuous head sweep with Sequence: {sequence} deg.")
        print("** Press 'q' then Enter to stop. **")

        while not stop_event.is_set():
            for target in sequence:
                if stop_event.is_set():
                    break
                target_clamped = clamp_angle(target)
                current = ramp(servo, buzzer, led, current, target_clamped, stop_event=stop_event)

    finally:
        try:
            print("\nShutting down...")
            # Keep servos engaged but at rest position
            set_head_angle(servo, 90)
            print("Head Servos engaged at 90° for 2 seconds...")
            beep(buzzer, count=1)
            time.sleep(2.0)
            
            beep(buzzer, count=2)
            flash_blue_led(led)
            
            # Power off all servos
            stop_all_servos(servo)
            
            print("All servo PWM outputs disabled (servos now limp)...")
            beep(buzzer, count=3)
            time.sleep(2.0)
            
            print("Test completed. Hardware shutdown complete.")
        except Exception as e:
            print(f"Error during shutdown: {e}")
# =================================================================================

if __name__ == "__main__":
    main()
