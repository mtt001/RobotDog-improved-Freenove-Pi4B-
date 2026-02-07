#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servo Test Utility - testServo.py

Version: 1.3.0
Date: 2026-01-04
Author: Freenove

Description:
    Command-line utility for testing all 16 servo channels on the PCA9685.
    Supports angle set, PWM OFF, calibration, RELAX via Control.py, interactive MOVE
    mode (w/s/a/d/tl/tr/x/relax/off), and legacy Chapter-3 exercise patterns.
    Includes audio/visual feedback (beeps, LED blinks), ESC-to-quit, and detailed
    status reporting.

Usage:
    python3 testServo.py <command>
    
    Commands:
        testServo.py OFF          - Disable all servo PWM outputs (servos go limp)
        testServo.py calib        - Set servos to default calibration position
        testServo.py relax        - Move to RELAX position via Control (resting pose)
        testServo.py MOVE         - Interactive drive mode (w/s/a/d/tl/tr/x/relax/off, q/Esc = RELAX+OFF+quit)
        testServo.py <0-180>      - Set all 16 servos to specified angle (0-180°)
        testServo.py TEST [delay] - Run class-based servo exercise (default delay 0.02s)
        testServo.py test [delay] - Run legacy test_Servo() pattern (default delay 0.01s)
        testServo.py help         - Show help message

Examples:
    python3 testServo.py 90           # Set all servos to 90° (center position)
    python3 testServo.py 0            # Set all servos to 0° (min angle)
    python3 testServo.py 180          # Set all servos to 180° (max angle)
    python3 testServo.py OFF          # Release all servos (disable PWM)
    python3 testServo.py calib        # Set servos to default calibration position
    python3 testServo.py test         # Run legacy sweep pattern
    python3 testServo.py test 0.02    # Legacy pattern with custom delay
    python3 testServo.py TEST 0.05    # Class exercise with custom delay

🔊 AUDIO/LED FEEDBACK:
   Before action:   2 beeps (1000Hz) + 1 blue LED blink
   After action:    3 beeps (1500Hz) + 2 blue LED blinks
   On error:        No completion feedback; PWM disabled and exit

⚙️  HARDWARE DETAILS:
   • PCA9685 I2C address: 0x40
   • I2C bus number: 1
   • PWM frequency: 50 Hz
   • Servo range: 0–180° (102–512 pulse counts)
   • Total channels: 16

📝 NOTES:
   • Use 'OFF' to release servos and reduce power consumption
   • Use angles 0°, 90°, 180° for diagnostic positions
   • All 16 channels are set to the same angle simultaneously
   • PWM is automatically disabled after successful completion

Revision History:
    1.3.0 (2026-01-04) - Added MOVE interactive mode, RELAX via Control, ESC-to-quit
                         across loops; updated docs/help text.
    1.2.0 (2025-12-23) - Added legacy `test` command to run test_Servo();
                         updated header/docs and help output.
    1.1.0 (2025-12-22) - Added audio/LED feedback, enhanced UX
                         - 2 beeps + 1 blue LED blink before action
                         - 3 beeps + 2 blue LED blinks after completion
                         - Running status messages for each action
    1.0.0 (2025-12-22) - Initial utility: OFF and degree commands, user-friendly CLI
"""

import sys
import time
import signal
import select
import atexit
import termios 
import tty
from Servo import Servo
from Buzzer import Buzzer
from Led import Led
from Command import COMMAND as cmd
from Control import Control

HEAD_SERVO_CHANNEL = 15  # Head servo channel (limited 45°–135°)


def init_buzzer():
    try:
        return Buzzer()
    except Exception:
        return None


def init_led():
    try:
        return Led()
    except Exception:
        return None


def beep_device(buzzer, count=1, duration=0.1, pause=0.1):
    if buzzer is None:
        return
    try:
        for _ in range(count):
            buzzer.run('1')
            time.sleep(duration)
            buzzer.run('0')
            time.sleep(pause)
    except Exception:
        pass


def flash_led_device(led, count=1, on_time=0.2, off_time=0.2):
    if led is None:
        return
    try:
        for _ in range(count):
            led.light([cmd.CMD_LED, '1', '0', '0', '255'])
            time.sleep(on_time)
            led.light([cmd.CMD_LED, '0', '0', '0', '0'])
            time.sleep(off_time)
    except Exception:
        pass


_tty_cbreak_enabled = False
_tty_old_settings = None


def _ensure_tty_cbreak() -> None:
    """Put stdin into cbreak mode so single-key reads work immediately."""
    global _tty_cbreak_enabled, _tty_old_settings
    if _tty_cbreak_enabled:
        return
    if not sys.stdin.isatty():
        return
    try:
        _tty_old_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        _tty_cbreak_enabled = True
        atexit.register(_restore_tty)
    except Exception:
        _tty_cbreak_enabled = False


def _restore_tty() -> None:
    global _tty_cbreak_enabled, _tty_old_settings
    if not _tty_cbreak_enabled or _tty_old_settings is None:
        return
    try:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _tty_old_settings)
    except Exception:
        pass
    _tty_cbreak_enabled = False


def user_requested_quit() -> bool:
    """Return True if the user pressed ESC or 'q' (non-blocking)."""
    try:
        if not sys.stdin.isatty():
            return False
        _ensure_tty_cbreak()
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        if rlist:
            ch = sys.stdin.read(1)
            return ch in ('\x1b', 'q', 'Q')
        return False
    except Exception:
        return False


def test_Servo(delay: float = 0.01, repeat: bool = False) -> bool:
    """Legacy servo test pattern with head motion and mirrored return.

    Sequence:
        - Initialize all 16 servos to 90°.
        - Forward sweeps (3 passes) with head motion limited to 45°–135°.
        - Double beep + double LED flash, wait 2s.
        - Reverse sweeps back to 90° at the same speed.
        - If repeat=True, loop continuously until Ctrl+C or q/ESC entered.

    Args:
        delay: Sleep time between steps (seconds). Default 0.01.
        repeat: If True, loop cycles continuously. Default False.

    Returns:
        True on completion, False if interrupted or on error.
    """
    s = Servo()
    buzzer = init_buzzer()
    led = init_led()
    cycle_count = 0

    def head_clamp(angle: float) -> float:
        return max(45.0, min(135.0, angle))

    def set_head(delta: float) -> None:
        s.setServoAngle(HEAD_SERVO_CHANNEL, int(round(head_clamp(90.0 + delta))))

    def do_beep(count: int = 2) -> None:
        beep_device(buzzer, count=count, duration=0.1, pause=0.1)

    def flash_led(count: int = 2) -> None:
        flash_led_device(led, count=count, on_time=0.2, off_time=0.2)

    quit_done = False

    def graceful_quit() -> None:
        """Move to RELAX posture and stop PWM outputs (best-effort)."""
        nonlocal quit_done
        if quit_done:
            return
        quit_done = True
        try:
            Control().relax(True)
        except Exception:
            pass
        try:
            s.stop_all_pwm()
        except Exception:
            pass

    def run_cycle() -> bool:
        """Run a single test cycle. Returns False if interrupted."""
        try:
            # Initialize all servos to 90°
            for ch in range(16):
                s.setServoAngle(ch, 90)
            set_head(0)
            time.sleep(0.5)

            # Forward passes
            for i in range(90):
                s.setServoAngle(4, 90 - i)
                s.setServoAngle(7, 90 - i)
                s.setServoAngle(8, 90 + i)
                s.setServoAngle(11, 90 + i)
                set_head(i / 2)  # Head: 90→135
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                time.sleep(delay)

            for i in range(90):
                s.setServoAngle(2, 90 - i)
                s.setServoAngle(5, 90 - i)
                s.setServoAngle(10, 90 + i)
                s.setServoAngle(13, 90 + i)
                set_head(-i / 2)  # Head: 135→45
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                time.sleep(delay)

            for i in range(60):
                s.setServoAngle(3, 90 - i)
                s.setServoAngle(6, 90 - i)
                s.setServoAngle(9, 90 + i)
                s.setServoAngle(12, 90 + i)
                set_head(i / 2)  # Head: 45→75
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                time.sleep(delay)

            # Midpoint feedback
            do_beep(count=2)
            flash_led(count=2)
            time.sleep(2.0)

            # Reverse passes (mirror back to 90°)
            for i in reversed(range(60)):
                s.setServoAngle(3, 90 - i)
                s.setServoAngle(6, 90 - i)
                s.setServoAngle(9, 90 + i)
                s.setServoAngle(12, 90 + i)
                set_head(i / 2)  # Head: ~75→90
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                time.sleep(delay)

            for i in reversed(range(90)):
                s.setServoAngle(2, 90 - i)
                s.setServoAngle(5, 90 - i)
                s.setServoAngle(10, 90 + i)
                s.setServoAngle(13, 90 + i)
                set_head(-i / 2)  # Head: 45→90
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                time.sleep(delay)

            for i in reversed(range(90)):
                s.setServoAngle(4, 90 - i)
                s.setServoAngle(7, 90 - i)
                s.setServoAngle(8, 90 + i)
                s.setServoAngle(11, 90 + i)
                set_head(i / 2)  # Head: 135→90
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                time.sleep(delay)

            return True
        except KeyboardInterrupt:
            return False

    try:
        if not repeat:
            # Single run mode
            if run_cycle():
                # Return to 90° and cleanup
                print("\nReturning servos to 90°...")
                for ch in range(16):
                    s.setServoAngle(ch, 90)
                time.sleep(0.5)
                print("Stopping PWM...")
                s.stop_all_pwm()
                print("End of program")
                return True
            else:
                # Return to 90° and cleanup even on interrupt
                print("\nReturning servos to 90°...")
                for ch in range(16):
                    s.setServoAngle(ch, 90)
                time.sleep(0.5)
                print("Stopping PWM...")
                s.stop_all_pwm()
                print("End of program")
                return False
        else:
            # Repeat mode - loop until Ctrl+C or q/ESC entered
            print("\n🔄 Running in repeat mode. Press Ctrl+C or q/ESC to stop.\n")
            while True:
                cycle_count += 1
                print(f"\n{'='*60}")
                print(f"  Cycle #{cycle_count}")
                print(f"{'='*60}")
                
                if user_requested_quit():
                    graceful_quit()
                    raise KeyboardInterrupt()
                
                if not run_cycle():
                    break
                    
                print(f"\n✅ Cycle #{cycle_count} completed. Starting next cycle...\n")
                time.sleep(1)  # Brief pause between cycles
            
            # Return to 90° and cleanup
            print("\nReturning servos to 90°...")
            for ch in range(16):
                s.setServoAngle(ch, 90)
            time.sleep(0.5)
            print("Stopping PWM...")
            s.stop_all_pwm()
            print("End of program")
            return True
    except KeyboardInterrupt:
        print("\n\nCtrl+C received, stopping...")
        # Return to 90° and cleanup
        print("Returning servos to 90°...")
        for ch in range(16):
            s.setServoAngle(ch, 90)
        time.sleep(0.5)
        print("Stopping PWM...")
        s.stop_all_pwm()
        print("End of program")
        return False
    except Exception as e:
        print(f"\n❌ ERROR in test_Servo: {e}")
        # Return to 90° and cleanup
        print("Returning servos to 90°...")
        for ch in range(16):
            s.setServoAngle(ch, 90)
        time.sleep(0.5)
        print("Stopping PWM...")
        s.stop_all_pwm()
        return False

class ServoTester:
    def __init__(self):
        self.stop_requested = False  # Set when Ctrl+C arrives
        self._graceful_done = False
        signal.signal(signal.SIGINT, self._handle_sigint)
        self.servo = Servo()
        self.control = Control()
        self.buzzer = init_buzzer()
        self.led = init_led()
        
        if self.buzzer is None:
            print(f"⚠️  Note: Buzzer requires sudo for GPIO access. Continuing without beeps.\n")
        if self.led is None:
            print(f"⚠️  Note: LED feedback requires sudo. Continuing without LED.\n")

    def _handle_sigint(self, signum, frame):
        """Handle Ctrl+C promptly by setting a stop flag."""
        if self.stop_requested:
            # Second Ctrl+C: allow immediate exit
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            return
        self.stop_requested = True
        print("\n\n⚠️  Ctrl+C received, stopping...", flush=True)

    def _graceful_stop(self, reason: str = ""):
        """Move to RELAX posture, stop PWM, and mark stop requested."""
        if self._graceful_done:
            return
        self._graceful_done = True
        self.stop_requested = True
        if reason:
            print(f"\n🛑 {reason}: relaxing and stopping servos...")
        try:
            self.control.relax(True)
        except Exception as e:
            print(f"   └─ RELAX warning: {e}")
        try:
            self.servo.stop_all_pwm()
        except Exception as e:
            print(f"   └─ STOP_PWM warning: {e}")
    
    def beep(self, count=1, duration=0.1, pause=0.1):
        """Emit beeps as feedback using proven on/off pulse method."""
        beep_device(self.buzzer, count=count, duration=duration, pause=pause)

    def blink_led(self, count=1, color='b', on_time=0.2, off_time=0.2):
        """Blink LED by turning it on and off.
        
        Args:
            count (int): Number of blinks.
            color (str): LED color (not used, kept for compatibility).
            on_time (float): Duration LED is on (seconds).
            off_time (float): Duration LED is off (seconds).
        """
        flash_led_device(self.led, count=count, on_time=on_time, off_time=off_time)
    
    def print_banner(self):
        """Print startup banner."""
        print("\n" + "="*70)
        print("         Freenove Robot Dog - Servo Test Utility (v1.2.0)")
        print("="*70 + "\n")
    
    def print_separator(self):
        """Print visual separator."""
        print("-" * 70)
    
    def set_all_servos_to_angle(self, angle):
        """Set all 16 servos to a specific angle."""
        try:
            # Validate angle
            if not (0 <= angle <= 180):
                print(f"❌ ERROR: Angle must be 0-180°, got {angle}")
                return False
            
            print(f"\n📢 Pre-action feedback:")
            print(f"   ├─ Beeping 2 times...")
            self.beep(count=2)
            print(f"   └─ Blinking blue LED 1 time...")
            self.blink_led(count=1, color='b')
            
            self.print_separator()
            print(f"\n⚙️  ACTION: Setting all 16 servos to {angle}°")
            print(f"   Pulse mapping: {angle}° → ~{int((512-102) * angle / 180 + 102)} counts")
            self.print_separator()
            
            for ch in range(16):
                self.servo.setServoAngle(ch, angle)
                status = "✓"
                if (ch + 1) % 4 == 0:
                    print(f"   Channels {ch-3:2d}–{ch:2d} set to {angle}° {status}")
            
            print(f"\n✅ SUCCESS: All 16 servos set to {angle}° successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to set servos: {e}")
            return False
    
    def stop_all_pwm(self):
        """Disable all servo PWM outputs."""
        try:
            print(f"\n📢 Pre-action feedback:")
            print(f"   ├─ Beeping 2 times...")
            self.beep(count=2)
            print(f"   └─ Blinking blue LED 1 time...")
            self.blink_led(count=1, color='b')
            
            self.print_separator()
            print(f"\n⚙️  ACTION: Disabling all servo PWM outputs (CMD_STOP_PWM)")
            print(f"   Disabling channels 0–15...")
            self.print_separator()
            
            self.servo.stop_all_pwm()
            
            print(f"\n✅ SUCCESS: All servo PWM outputs disabled!")
            print(f"   → All servos should now be limp (no holding torque)")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to stop PWM: {e}")
            return False
    
    def completion_feedback(self):
        """Play completion feedback: 3 beeps + 2 LED blinks."""
        print(f"\n📢 Completion feedback:")
        print(f"   ├─ Beeping 3 times...")
        self.beep(count=3)
        print(f"   └─ Blinking blue LED 2 times...")
        self.blink_led(count=2, color='b')
    
    def coordinateToAngle(self, x, y, z, l1=23, l2=55, l3=55):
        """Convert cartesian coordinates to joint angles (inverse kinematics).
        
        Args:
            x, y, z: Target foot position (mm)
            l1: Hip link length (23mm)
            l2: Upper leg length (55mm)
            l3: Lower leg length (55mm)
        
        Returns:
            (a, b, c): Joint angles in degrees
                a: Hip angle (lateral)
                b: Shoulder angle
                c: Knee angle
        """
        import math
        
        # Hip angle (lateral rotation)
        a = math.pi/2 - math.atan2(z, y)
        
        # Project leg into 2D plane
        x_3 = 0
        x_4 = l1 * math.sin(a)
        x_5 = l1 * math.cos(a)
        
        # Distance from hip to foot in 2D
        l23 = math.sqrt((z - x_5)**2 + (y - x_4)**2 + (x - x_3)**2)
        
        # Shoulder angle using law of cosines
        w = (x - x_3) / l23
        v = (l2*l2 + l23*l23 - l3*l3) / (2 * l2 * l23)
        b = math.asin(round(w, 2)) - math.acos(round(v, 2))
        
        # Knee angle
        c = math.pi - math.acos(round((l2**2 + l3**2 - l23**2) / (2 * l3 * l2), 2))
        
        # Convert radians to degrees
        a = round(math.degrees(a))
        b = round(math.degrees(b))
        c = round(math.degrees(c))
        
        return a, b, c
    
    def set_calibration_position(self):
        """Set servos to default calibration position.
        
        Default calibration position (from Control.py):
            Front-Left:  [0, 99, 10]
            Front-Right: [0, 99, 10]
            Rear-Left:   [0, 99, -10]
            Rear-Right:  [0, 99, -10]
        """
        import math
        
        try:
            print(f"\n📢 Pre-action feedback:")
            print(f"   ├─ Beeping 2 times...")
            self.beep(count=2)
            print(f"   └─ Blinking blue LED 1 time...")
            self.blink_led(count=1, color='b')
            
            self.print_separator()
            print(f"\n⚙️  ACTION: Setting servos to default calibration position")
            print(f"   Position coordinates (x, y, z):")
            print(f"   ├─ Front-Left:  [0, 99, 10]")
            print(f"   ├─ Front-Right: [0, 99, 10]")
            print(f"   ├─ Rear-Left:   [0, 99, -10]")
            print(f"   └─ Rear-Right:  [0, 99, -10]")
            self.print_separator()
            
            # Define default calibration positions for each leg
            point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
            angle = [[90, 0, 0], [90, 0, 0], [90, 0, 0], [90, 0, 0]]
            
            # Convert coordinates to angles
            print(f"\n   Converting coordinates to joint angles...")
            for i in range(4):
                angle[i][0], angle[i][1], angle[i][2] = self.coordinateToAngle(
                    point[i][0], point[i][1], point[i][2]
                )
            
            # Apply transformations for front and rear legs
            print(f"   Applying servo transformations...")
            for i in range(2):
                # Front legs (0, 1)
                angle[i][0] = max(0, min(180, angle[i][0]))
                angle[i][1] = max(0, min(180, 90 - angle[i][1]))
                angle[i][2] = max(0, min(180, angle[i][2]))
                
                # Rear legs (2, 3)
                angle[i+2][0] = max(0, min(180, angle[i+2][0]))
                angle[i+2][1] = max(0, min(180, 90 + angle[i+2][1]))
                angle[i+2][2] = max(0, min(180, 180 - angle[i+2][2]))
            
            # Set servos to calculated angles
            print(f"\n   Setting servo angles:")
            for i in range(2):
                # Front legs
                self.servo.setServoAngle(4+i*3, angle[i][0])  # Hip
                self.servo.setServoAngle(3+i*3, angle[i][1])  # Shoulder
                self.servo.setServoAngle(2+i*3, angle[i][2])  # Knee
                print(f"   ├─ Leg {i} (Front): Hip={angle[i][0]}° Shoulder={angle[i][1]}° Knee={angle[i][2]}°")
                
                # Rear legs
                self.servo.setServoAngle(8+i*3, angle[i+2][0])  # Hip
                self.servo.setServoAngle(9+i*3, angle[i+2][1])  # Shoulder
                self.servo.setServoAngle(10+i*3, angle[i+2][2])  # Knee
                print(f"   ├─ Leg {i+2} (Rear): Hip={angle[i+2][0]}° Shoulder={angle[i+2][1]}° Knee={angle[i+2][2]}°")
            
            print(f"\n✅ SUCCESS: Servos set to default calibration position!")
            print(f"   → Robot is now in neutral stance for calibration")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to set calibration position: {e}")
            return False

    def set_relax_position(self):
        """Set servos to RELAX position using Control.relax() method.
        
        The Control class handles the movement to relax position [55, 78, 0]
        and disables PWM for power saving.
        """
        try:
            print(f"\n📢 Pre-action feedback:")
            print(f"   ├─ Beeping 2 times...")
            self.beep(count=2)
            print(f"   └─ Blinking blue LED 1 time...")
            self.blink_led(count=1, color='b')
            
            self.print_separator()
            print(f"\n⚙️  ACTION: Setting servos to RELAX position")
            print(f"   Sending CMD_RELAX to Control module...")
            print(f"   Target position: [55, 78, 0] (all legs)")
            self.print_separator()
            
            # Call Control.relax(True) to move to relax position
            self.control.relax(True)
            
            print(f"\n✅ SUCCESS: Robot moved to RELAX position!")
            print(f"   → Legs tucked in resting pose")
            print(f"   → PWM disabled for power saving")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to set relax position: {e}")
            return False

    def servo_exercise(self, delay=0.02):
        """Run the Chapter 3 servo exercise pattern.

        Args:
            delay (float): Sleep time between steps; default 0.02s.
        """
        print(f"\n📢 Pre-action feedback:")
        print(f"   ├─ Beeping 2 times...")
        self.beep(count=2)
        print(f"   └─ Blinking blue LED 1 time...")
        self.blink_led(count=1, color='b')

        self.print_separator()
        print(f"\n⚙️  ACTION: Running servo exercise pattern (delay={delay:.3f}s)")
        self.print_separator()

        try:
            # Initialize all servos to 90 degrees
            print(f"   Setting all servos to 90° (center position)...")
            for ch in range(16):
                self.servo.setServoAngle(ch, 90)
            time.sleep(0.5)
            
            # Single beep before starting exercise
            print(f"   Starting exercise...")
            self.beep(count=1)
            time.sleep(0.3)
            
            for i in range(90):
                self.servo.setServoAngle(4, 90 - i)
                self.servo.setServoAngle(7, 90 - i)
                self.servo.setServoAngle(8, 90 + i)
                self.servo.setServoAngle(11, 90 + i)
                if user_requested_quit():
                    self._graceful_stop("Quit requested")
                    raise KeyboardInterrupt()
                time.sleep(delay)

            for i in range(90):
                self.servo.setServoAngle(2, 90 - i)
                self.servo.setServoAngle(5, 90 - i)
                self.servo.setServoAngle(10, 90 + i)
                self.servo.setServoAngle(13, 90 + i)
                if user_requested_quit():
                    self._graceful_stop("Quit requested")
                    raise KeyboardInterrupt()
                time.sleep(delay)

            for i in range(60):
                self.servo.setServoAngle(3, 90 - i)
                self.servo.setServoAngle(6, 90 - i)
                self.servo.setServoAngle(9, 90 + i)
                self.servo.setServoAngle(12, 90 + i)
                if user_requested_quit():
                    self._graceful_stop("Quit requested")
                    raise KeyboardInterrupt()
                time.sleep(delay)

            print("\n✅ Exercise complete")
            return True
        except KeyboardInterrupt:
            print("\n⚠️  Exercise interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ ERROR: Exercise failed: {e}")
            return False

    def move_console(self):
        """Interactive MOVE mode: accepts commands and dispatches to Control.

        Accepted inputs (case-insensitive):
          w / forward          → CMD_MOVE_FORWARD [speed]
          s / backward         → CMD_MOVE_BACKWARD [speed]
          a / left             → CMD_MOVE_LEFT [speed]
          d / right            → CMD_MOVE_RIGHT [speed]
          tl / turn_left       → CMD_TURN_LEFT [speed]
          tr / turn_right      → CMD_TURN_RIGHT [speed]
          x / stop             → CMD_MOVE_STOP
          relax                → CMD_RELAX (toggle)
          off                  → CMD_STOP_PWM
          q / esc              → RELAX + OFF + quit (cleanup)

        Optional speed (int) can follow movement commands, defaulting to current speed.
        """
        # Ensure the control condition thread is running so commands are processed
        if not self.control.Thread_conditiona.is_alive():
            try:
                self.control.Thread_conditiona.daemon = True
                self.control.Thread_conditiona.start()
            except RuntimeError:
                pass
        default_speed = self.control.speed if hasattr(self.control, "speed") else 8

        def dispatch(command_name, speed=None):
            nonlocal default_speed
            if speed is not None:
                default_speed = speed
            self.control.order = [command_name, str(speed) if speed is not None else "", "", "", ""]
            print(f"→ Sent {command_name}" + (f" speed={speed}" if speed is not None else ""))

        print("\n🔄 MOVE mode: enter commands (q or Esc = RELAX + OFF + quit)")
        print("   Examples: 'w 6', 's', 'tl 5', 'x', 'relax', 'off'")

        def quit_and_release():
            """Stop motion, move to RELAX, then release PWM outputs (servos limp)."""
            dispatch(cmd.CMD_MOVE_STOP)
            self._graceful_stop("Quit requested")

        try:
            while True:
                # Non-blocking quit check
                if user_requested_quit():
                    quit_and_release()
                    return True

                if self.stop_requested:
                    quit_and_release()
                    return True

                line = input("MOVE> ").strip()
                if not line:
                    continue

                # Quit immediately
                if line.lower() == 'esc' or line.lower() == 'q':
                    quit_and_release()
                    return True

                parts = line.split()
                key = parts[0].lower()
                speed = None
                if len(parts) > 1:
                    try:
                        speed = int(float(parts[1]))
                    except ValueError:
                        print("⚠️  Speed must be a number")
                        continue
                if speed is None:
                    speed = default_speed

                if key in ('w', 'forward', 'f'):
                    dispatch(cmd.CMD_MOVE_FORWARD, speed)
                elif key in ('s', 'backward', 'b'):
                    dispatch(cmd.CMD_MOVE_BACKWARD, speed)
                elif key in ('a', 'left'):
                    dispatch(cmd.CMD_MOVE_LEFT, speed)
                elif key in ('d', 'right'):
                    dispatch(cmd.CMD_MOVE_RIGHT, speed)
                elif key in ('tl', 'turn_left'):
                    dispatch(cmd.CMD_TURN_LEFT, speed)
                elif key in ('tr', 'turn_right'):
                    dispatch(cmd.CMD_TURN_RIGHT, speed)
                elif key in ('x', 'stop'):
                    dispatch(cmd.CMD_MOVE_STOP)
                elif key == 'relax':
                    dispatch(cmd.CMD_RELAX)
                elif key == 'off':
                    dispatch(cmd.CMD_STOP_PWM)
                else:
                    print("⚠️  Unknown command. Use w/s/a/d/tl/tr/x/relax/off or q/Esc to quit.")
        except KeyboardInterrupt:
            quit_and_release()
            return True
        except Exception as e:
            print(f"\n❌ ERROR: MOVE mode failed: {e}")
            return False
    # ==== Individual Servo Channel Cycling =====================================
    def servo_cycle(self, channel, angles, delay=0.1):
        """Cycle a single servo through specified angles repeatedly.

        Args:
            channel (int): Servo channel (0-15).
            angles (list): List of target angles to cycle through.
            delay (float): Sleep time between angle changes; default 0.1s.

        Returns:
            bool: True on completion, False if interrupted or on error.
        """
        if not (0 <= channel <= 15):
            print(f"❌ ERROR: Channel must be 0-15, got {channel}")
            return False

        if not angles or len(angles) == 0:
            print(f"❌ ERROR: At least one angle required")
            return False

        # Validate all angles
        for angle in angles:
            if not (0 <= angle <= 180):
                print(f"❌ ERROR: Angle must be 0-180°, got {angle}")
                return False

        print(f"\n📢 Pre-action feedback:")
        print(f"   ├─ Beeping 2 times...")
        self.beep(count=2)
        print(f"   └─ Blinking blue LED 1 time...")
        self.blink_led(count=1, color='b')

        self.print_separator()
        print(f"\n⚙️  ACTION: Individual servo cycling test")
        print(f"   Channel:       {channel}")
        print(f"   Target angles: {angles}")
        print(f"   Delay:         {delay:.3f}s per angle")
        self.print_separator()

        try:
            print(f"\n   Starting cycle... (Ctrl+C to stop)\n")
            cycle_count = 0

            while not self.stop_requested:
                cycle_count += 1
                for angle in angles:
                    if self.stop_requested:
                        self._graceful_stop("Stop requested")
                        raise KeyboardInterrupt()
                    if user_requested_quit():
                        self._graceful_stop("Quit requested")
                        raise KeyboardInterrupt()
                    # Move servo to target angle
                    self.servo.setServoAngle(channel, angle)    # Move channel servo to angle
                    
                    # Wait before feedback (delay is the main wait time)
                    time.sleep(delay)
                    if self.stop_requested:
                        self._graceful_stop("Stop requested")
                        raise KeyboardInterrupt()
                    
                    print(f"   Cycle {cycle_count}: Channel {channel} → {angle}° ", end="")

                    # Feedback: double beeps + double LED flashes
                    print("🔊 ", end="", flush=True)
                    self.beep(count=2, duration=0.1, pause=0.1)
                    print("💡 ", end="", flush=True)
                    self.blink_led(count=2, on_time=0.1, off_time=0.1)
                    print("✓") 

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Cycling interrupted by user (after {cycle_count} cycles)")
            return True
        except Exception as e:
            print(f"\n❌ ERROR: Cycling failed: {e}")
            return False
    # ==== All Servo Channels Cycling ============================================
    def servo_cycle_all(self, angles, delay=0.1):
        """Cycle all 16 servos through specified angles repeatedly.

        Args:
            angles (list): List of target angles to cycle through.
            delay (float): Sleep time between angle changes; default 0.1s.

        Returns:
            bool: True on completion, False if interrupted or on error.
        """
        if not angles or len(angles) == 0:
            print(f"❌ ERROR: At least one angle required")
            return False

        # Validate all angles
        for angle in angles:
            if not (0 <= angle <= 180):
                print(f"❌ ERROR: Angle must be 0-180°, got {angle}")
                return False

        print(f"\n📢 Pre-action feedback:")
        print(f"   ├─ Beeping 2 times...")
        self.beep(count=2)
        print(f"   └─ Blinking blue LED 1 time...")
        self.blink_led(count=1, color='b')

        self.print_separator()
        print(f"\n⚙️  ACTION: All servos cycling test")
        print(f"   Channels:      0-15 (all)")
        print(f"   Target angles: {angles}")
        print(f"   Delay:         {delay:.3f}s per angle")
        self.print_separator()

        try:
            print(f"\n   Starting cycle... (Ctrl+C to stop)\n")
            cycle_count = 0

            while not self.stop_requested:
                cycle_count += 1
                for angle in angles:
                    if self.stop_requested:
                        self._graceful_stop("Stop requested")
                        raise KeyboardInterrupt()
                    if user_requested_quit():
                        self._graceful_stop("Quit requested")
                        raise KeyboardInterrupt()
                    # Move all servos to target angle
                    for ch in range(16):
                        self.servo.setServoAngle(ch, angle)
                    
                    # Wait before feedback (delay is the main wait time)
                    time.sleep(delay)
                    if self.stop_requested:
                        self._graceful_stop("Stop requested")
                        raise KeyboardInterrupt()
                    
                    print(f"   Cycle {cycle_count}: All channels → {angle}° ", end="")

                    # Feedback: double beeps + double LED flashes
                    print("🔊 ", end="", flush=True)
                    self.beep(count=2, duration=0.1, pause=0.1)
                    print("💡 ", end="", flush=True)
                    self.blink_led(count=2, on_time=0.1, off_time=0.1)
                    print("✓") 

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Cycling interrupted by user (after {cycle_count} cycles)")
            return True
        except Exception as e:
            print(f"\n❌ ERROR: Cycling failed: {e}")
            return False

    def set_single_servo_angle(self, channel, angle):
        """Set a single servo to a specific angle (no looping, no feedback).
        
        Args:
            channel (int): Servo channel (0-15), or -1 for all channels.
            angle (int): Target angle (0-180).
        
        Returns:
            bool: True on success, False on error.
        """
        try:
            if channel == -1:
                # Set all channels
                for ch in range(16):
                    self.servo.setServoAngle(ch, angle)
                print(f"✓ All 16 servos set to {angle}°")
            else:
                # Set single channel
                self.servo.setServoAngle(channel, angle)
                print(f"✓ Channel {channel} set to {angle}°")
            return True
        except Exception as e:
            print(f"❌ ERROR: Failed to set servo angle: {e}")
            return False

    def cleanup(self, release_servos=True):
        """Final cleanup: stop buzzer, optionally disable PWM.
        
        Args:
            release_servos (bool): If True, disable all servo PWM outputs.
                                  If False, leave servos at their current position.
        """
        print(f"\n🛑 Cleaning up...")
        try:
            if self.buzzer is not None:
                # Stop any ongoing buzzer output
                self.buzzer.run('0')
                time.sleep(0.2)
        except Exception as e:
            pass
        
        if release_servos:
            try:
                self.servo.stop_all_pwm()
                print(f"   └─ Servos released (PWM disabled)")
            except Exception as e:
                print(f"   └─ Cleanup warning: {e}")
        else:
            # Inform the user that servos were intentionally left powered/engaged
            print("   └─ Note: Servos left engaged (PWM still active). Use 'OFF' to release them.")
                
    # --------------------------------------------------------
    def run(self, args):
        """Main entry point."""
        self.print_banner()
        
        if len(args) < 1:
            raw_command = 'test'
        else:
            raw_command = args[0]
        command = raw_command.upper()
        
        # Help command
        if command == 'HELP' or command == '-H' or command == '--HELP':
            self.print_help()
            return
        
        # OFF command
        if command == 'OFF':
            success = self.stop_all_pwm()
            release_servos = True  # OFF command should release servos
        # CALIB command
        elif command == 'CALIB':
            success = self.set_calibration_position()
            release_servos = False  # Keep servos at calibration position
        # RELAX command
        elif command == 'RELAX':
            success = self.set_relax_position()
            release_servos = False  # Relax already disables PWM, no need to release again
        # MOVE command (interactive)
        elif command == 'MOVE':
            success = self.move_console()
            release_servos = True  # Stop/cleanup after exiting MOVE
        # 'test' command → run legacy test_Servo() function (optional delay)
        elif raw_command.lower() == 'test':
            delay = 0.01  # Default delay for legacy pattern
            repeat = True  # Default: repeat continuously
            
            if len(args) >= 2:
                try:
                    delay = float(args[1])
                except ValueError:
                    print(f"❌ ERROR: Invalid delay '{args[1]}'. Use a number (e.g., 0.01).\n")
                    return
                if delay < 0:
                    print(f"❌ ERROR: Delay must be non-negative.\n")
                    return
            
            # Check for --once flag to disable repeat (run only single cycle)
            if len(args) >= 3 and args[2].lower() == '--once':
                repeat = False
            
            success = test_Servo(delay=delay, repeat=repeat)
            release_servos = True  # legacy test should release servos afterward
        # TEST command (optional delay argument) → class-based exercise
        elif command == 'TEST':
            delay = 0.02
            if len(args) >= 2:
                try:
                    delay = float(args[1])
                except ValueError:
                    print(f"❌ ERROR: Invalid delay '{args[1]}'. Use a number (e.g., 0.02).\n")
                    return
                if delay < 0:
                    print(f"❌ ERROR: Delay must be non-negative.\n")
                    return
            success = self.servo_exercise(delay=delay)
            release_servos = False  # Keep final pose after exercise

        # === Individual servo channel cycling: ch## <angle1> <angle2> ... [delay] ===
        elif raw_command.lower().startswith('ch'):
            # Check if 'ch' is alone (no number) → cycle all channels
            if raw_command.lower() == 'ch':
                channel = None  # Signal to cycle all channels
            else:
                try:
                    channel = int(raw_command[2:])
                except (ValueError, IndexError):
                    print(f"❌ ERROR: Invalid channel format '{raw_command}'. Use 'ch00'-'ch15' or 'ch' for all channels.\n")
                    return
            
            # Parse angles from remaining args, and look for --delay=X flag
            angles = []
            delay = 0.01  # Default delay 0.1 sec if not specified
            
            for i in range(1, len(args)):
                arg = args[i]
                
                # Check for explicit --delay=X flag
                if arg.lower().startswith('--delay='):
                    try:
                        delay = float(arg.split('=')[1])
                        if delay < 0:
                            print(f"❌ ERROR: Delay must be non-negative.\n")
                            return
                    except (ValueError, IndexError):
                        print(f"❌ ERROR: Invalid delay format '{arg}'. Use '--delay=20.0'.\n")
                        return
                    continue
                
                try:
                    val = float(arg)
                    # Check if this might be a delay (happens to be last arg and > 180)
                    if i == len(args) - 1 and val > 180:
                        # Last arg and > 180, treat as delay
                        delay = val
                        break
                    # Otherwise treat as an angle
                    if 0 <= val <= 180:
                        angles.append(int(val))
                    else:
                        # Could be delay value, try to use as delay
                        delay = val
                        break
                except ValueError:
                    print(f"❌ ERROR: Invalid angle/delay value '{arg}'.\n")
                    return
            
            # If no angles provided, use default pattern
            if not angles:
                angles = [90, 60, 90, 120]
                print(f"   Using default angles: {angles}")
            
            if delay <= 0:
                print(f"❌ ERROR: Delay must be positive.\n")
                return
            
            # Single angle: no looping, no feedback
            if len(angles) == 1:
                if channel is None:
                    success = self.set_single_servo_angle(-1, angles[0])
                else:
                    success = self.set_single_servo_angle(channel, angles[0])
                release_servos = False  # Keep servos at position
            # Multiple angles: cycle through them
            else:
                # Call appropriate method based on channel
                if channel is None:
                    success = self.servo_cycle_all(angles, delay=delay)
                else:
                    success = self.servo_cycle(channel, angles, delay=delay)
                release_servos = True  # release servos after cycling
        # -------------------------------------------------------------------

        # Angle command   ,  eg. 90
        else:
            try:
                angle = int(command)
                success = self.set_all_servos_to_angle(angle)
                release_servos = False  # Angle command should keep servos at position
            except ValueError:
                print(f"❌ ERROR: Invalid command '{command}'")
                print(f"   Use 'python3 testServo.py help' for usage.\n")
                return
        
        # == Completion sequence  ==
        if success:
            self.completion_feedback()
            self.cleanup(release_servos=release_servos)
            print(f"\n✅ Test completed successfully. Exiting.\n")
        else:
            print(f"\n⚠️  Test failed. Cleaning up and exiting.\n")
            self.cleanup(release_servos=False)  # Don't release on error
    # --------------------------------------------------------

    def print_help(self):
        """Print help message."""
        help_text = """
📖 USAGE:
   python3 testServo.py <command>

🎯 COMMANDS:
     OFF                                Disable all servo PWM outputs (servos go limp)
     calib                              Set servos to default calibration position
     relax                              Move to RELAX position (resting pose, PWM disabled)
    MOVE                               Interactive drive mode (w/s/a/d/tl/tr/x/relax/off, q/Esc = RELAX+OFF+quit)
     TEST [delay]                       Run class-based servo exercise (default delay 0.02s)
     test [delay] [--once]              Run legacy test_Servo() sweep in repeat mode (default delay 0.01s)
                                        Use --once to run a single cycle only
     <0-180>                            Set all 16 servos to specified angle (degrees)
     ch <angle> [...] [--delay=X]       Test all servos (0-15) with cycling angles
     ch## <angle> [...] [--delay=X]     Test individual servo with cycling angles
     help                               Show this help message

📋 EXAMPLES:
   python3 testServo.py 90
      Set all servos to 90° (center position)
   
   python3 testServo.py OFF
      Release all servos (disable PWM)
   
   python3 testServo.py calib
      Set servos to default calibration position (neutral stance)
   
   python3 testServo.py relax
      Move to RELAX position (legs tucked, power-saving mode)
   
    python3 testServo.py MOVE
    Enter interactive MOVE mode (w/s/a/d/tl/tr/x/relax/off, q/Esc = RELAX+OFF+quit)
   
   python3 testServo.py TEST 0.05
      Run servo exercise with 0.05s delay between steps
   
   python3 testServo.py test
      Run legacy servo sweep in continuous loop mode
      Press Ctrl+C to stop
   
   python3 testServo.py test 0.02
      Run legacy servo sweep in continuous loop with 0.02s delay
      Press Ctrl+C to stop
   
   python3 testServo.py test 0.02 --once
      Run legacy servo sweep as single cycle only (no repeating)
      Cycle ALL servos (0-15) through angles: 90° → 45° → 90° → 135° → repeat
      Double beeps + double LED flashes for each angle, default 0.01s delay
   
   python3 testServo.py ch 90 45 --delay=5.0
      Cycle ALL servos through [90, 45] with 5.0 second delay between angles
   
   python3 testServo.py ch08 90 45 90 135
      Cycle servo channel 8 through angles: 90° → 45° → 90° → 135° → repeat
      Double beeps + double LED flashes for each angle, default 0.01s delay
   
   python3 testServo.py ch08 90 45 90 135 201
      Same as above but with 201 seconds delay (must be > 180 to be treated as delay)
   
   python3 testServo.py ch08 --delay=20.0
      Use default angles [90, 45, 90, 135] with 20.0 second delay between angles
   
   python3 testServo.py ch08 45 90 135 --delay=10.0
      Cycle through custom angles [45, 90, 135] with 10.0 second delay

🔊 FEEDBACK (Servo Cycling):
   • Double beeps + double LED flashes occur after the delay, before moving to next angle
   • Press Ctrl+C to stop the cycling at any time
   • Servo maintains final position after interruption

"""
        print(help_text)

def main():
    tester = ServoTester()
    try:
        tester.run(sys.argv[1:])
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Cleaning up...")
        tester.cleanup()
        print("Exiting.\n")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        tester.cleanup()
        print("Exiting.\n")

if __name__ == '__main__':
    main()
