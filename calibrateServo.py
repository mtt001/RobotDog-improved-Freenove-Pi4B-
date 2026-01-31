#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servo Calibration Utility - calibrateServo.py

Version: 2.0.0
Date: 2025-12-26
Author: Freenove

Description:
    Coordinate-based calibration utility for the robot dog following the original
    Freenove method. Calibrates leg positions by adjusting x, y, z coordinates
    instead of individual servo angles.

Features:
    • Set robot to calibration posture (default neutral position)
    • Adjust individual leg positions using x, y, z coordinates
    • Real-time preview of coordinate changes
    • Save calibration to point.txt (Freenove standard format)
    • Load existing calibration from point.txt
    • Audio/visual feedback

Usage:
    python3 calibrateServo.py           # Interactive mode with current calibration
    python3 calibrateServo.py reset     # Reset to default neutral position

Coordinate System:
    X-axis: Forward/backward (positive = forward, range: -50 to 50 mm)
    Y-axis: Up/down (positive = up, range: 70 to 120 mm)
    Z-axis: Left/right (positive = left, range: -30 to 30 mm)

Default Neutral Position:
    Front-Left:  [0, 99, 10]
    Front-Right: [0, 99, 10]
    Rear-Left:   [0, 99, -10]
    Rear-Right:  [0, 99, -10]

Revision History:
    2.0.0 (2025-12-26) - Complete rewrite for coordinate-based calibration
                         following Freenove method, saves to point.txt
    1.0.0 (2025-12-25) - Initial servo angle-based calibration
"""

import sys
import time
import math
import os
import signal
from Servo import Servo
from Buzzer import Buzzer
from Led import Led
from Command import COMMAND as cmd


class ServoCalibrator:
    """Coordinate-based servo calibration tool (Freenove method)."""
    
    def __init__(self):
        self.servo = Servo()
        self.buzzer = self._init_buzzer()
        self.led = self._init_led()
        
        # Default neutral calibration positions
        self.default_point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
        
        # Current calibration points (load from point.txt or use defaults)
        self.calibration_point = self.load_calibration()
        
        # Current leg being edited
        self.current_leg = 0
        
        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_interrupt)
    
    def _init_buzzer(self):
        try:
            return Buzzer()
        except Exception:
            return None
    
    def _init_led(self):
        try:
            return Led()
        except Exception:
            return None
    
    def _handle_interrupt(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n\n⚠️  Calibration interrupted. Exiting...")
        self.servo.stop_all_pwm()
        sys.exit(0)
    
    def _beep(self, count=1, duration=0.05, pause=0.05):
        """Emit beeps as feedback."""
        if self.buzzer is None:
            return
        try:
            for _ in range(count):
                self.buzzer.run('1')
                time.sleep(duration)
                self.buzzer.run('0')
                time.sleep(pause)
        except Exception:
            pass
    
    def _flash_led(self, count=1, on_time=0.1, off_time=0.1):
        """Flash LED for feedback."""
        if self.led is None:
            return
        try:
            for _ in range(count):
                self.led.light([cmd.CMD_LED, '1', '0', '0', '255'])
                time.sleep(on_time)
                self.led.light([cmd.CMD_LED, '0', '0', '0', '0'])
                time.sleep(off_time)
        except Exception:
            pass
    
    def load_calibration(self):
        """Load calibration data from point.txt, or return defaults."""
        try:
            if os.path.exists('point.txt'):
                with open('point.txt', 'r') as f:
                    lines = f.readlines()
                    calibration = []
                    for line in lines:
                        values = line.strip().split('\t')
                        if len(values) >= 3:
                            calibration.append([int(values[0]), int(values[1]), int(values[2])])
                    if len(calibration) == 4:
                        print("✓ Loaded calibration from point.txt")
                        return calibration
        except Exception as e:
            print(f"⚠️  Could not load point.txt: {e}")
        
        print("✓ Using default neutral position")
        return [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
    
    def save_calibration(self):
        """Save calibration data to point.txt."""
        try:
            with open('point.txt', 'w') as f:
                for i in range(4):
                    f.write(f"{self.calibration_point[i][0]}\t")
                    f.write(f"{self.calibration_point[i][1]}\t")
                    f.write(f"{self.calibration_point[i][2]}\t\n")
            print("\n✅ Calibration saved to point.txt")
            self._beep(count=3)
            self._flash_led(count=2)
            return True
        except Exception as e:
            print(f"\n❌ Failed to save calibration: {e}")
            return False
    
    def coordinateToAngle(self, x, y, z, l1=23, l2=55, l3=55):
        """Convert cartesian coordinates to joint angles (inverse kinematics).
        
        Args:
            x, y, z: Target foot position (mm)
            l1: Hip link length (23mm)
            l2: Upper leg length (55mm)
            l3: Lower leg length (55mm)
        
        Returns:
            (a, b, c): Joint angles in degrees
        """
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
    
    def apply_calibration(self):
        """Apply current calibration coordinates to servos."""
        angle = [[90, 0, 0], [90, 0, 0], [90, 0, 0], [90, 0, 0]]
        
        # Convert coordinates to angles
        for i in range(4):
            angle[i][0], angle[i][1], angle[i][2] = self.coordinateToAngle(
                self.calibration_point[i][0],
                self.calibration_point[i][1],
                self.calibration_point[i][2]
            )
        
        # Apply transformations for front and rear legs
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
        for i in range(2):
            # Front legs
            self.servo.setServoAngle(4+i*3, angle[i][0])  # Hip
            self.servo.setServoAngle(3+i*3, angle[i][1])  # Shoulder
            self.servo.setServoAngle(2+i*3, angle[i][2])  # Knee
            
            # Rear legs
            self.servo.setServoAngle(8+i*3, angle[i+2][0])  # Hip
            self.servo.setServoAngle(9+i*3, angle[i+2][1])  # Shoulder
            self.servo.setServoAngle(10+i*3, angle[i+2][2])  # Knee
            # Rear legs
            self.servo.setServoAngle(8+i*3, angle[i+2][0])  # Hip
            self.servo.setServoAngle(9+i*3, angle[i+2][1])  # Shoulder
            self.servo.setServoAngle(10+i*3, angle[i+2][2])  # Knee
    
    def print_banner(self):
        """Print startup banner."""
        print("\n" + "="*70)
        print("    Freenove Robot Dog - Coordinate Calibration (v2.0.0)")
        print("="*70)
        print("\n📐 COORDINATE SYSTEM:")
        print("   X-axis: Forward(+) / Backward(-), range: -50 to 50 mm")
        print("   Y-axis: Up(+) / Down(-), range: 70 to 120 mm")  
        print("   Z-axis: Left(+) / Right(-), range: -30 to 30 mm")
        print("\n🦿 LEG NUMBERING:")
        print("   0: Front-Left   1: Front-Right")
        print("   2: Rear-Left    3: Rear-Right\n")
    
    def print_current_calibration(self):
        """Print current calibration values."""
        leg_names = ["Front-Left", "Front-Right", "Rear-Left", "Rear-Right"]
        print("\n📊 CURRENT CALIBRATION:")
        print("   " + "="*60)
        for i in range(4):
            x, y, z = self.calibration_point[i]
            print(f"   Leg {i} ({leg_names[i]:11s}): X={x:3d}, Y={y:3d}, Z={z:3d}")
        print("   " + "="*60)
    
    def print_menu(self):
        """Print main menu."""
        menu_text = """
📋 CALIBRATION MENU:
   1. Adjust Leg 0 (Front-Left) coordinates
   2. Adjust Leg 1 (Front-Right) coordinates
   3. Adjust Leg 2 (Rear-Left) coordinates
   4. Adjust Leg 3 (Rear-Right) coordinates
   5. Reset to default neutral position
   6. Save calibration to point.txt
   7. Show current calibration values
   8. Apply and preview current calibration
   9. Exit (release servos)

Select option (1-9): """
        return menu_text
    
    def adjust_leg_coordinates(self, leg):
        """Adjust X, Y, Z coordinates for a specific leg."""
        leg_names = ["Front-Left", "Front-Right", "Rear-Left", "Rear-Right"]
        print(f"\n🎯 Adjusting Leg {leg} ({leg_names[leg]})")
        print(f"   Current: X={self.calibration_point[leg][0]}, "
              f"Y={self.calibration_point[leg][1]}, "
              f"Z={self.calibration_point[leg][2]}")
        print("\n   Commands:")
        print("     x+/x- : Adjust X coordinate (±1mm)")
        print("     y+/y- : Adjust Y coordinate (±1mm)")
        print("     z+/z- : Adjust Z coordinate (±1mm)")
        print("     X+/X- : Adjust X coordinate (±5mm)")
        print("     Y+/Y- : Adjust Y coordinate (±5mm)")
        print("     Z+/Z- : Adjust Z coordinate (±5mm)")
        print("     set   : Set exact values")
        print("     apply : Apply changes to servos")
        print("     q     : Return to main menu")
        
        while True:
            x, y, z = self.calibration_point[leg]
            cmd_input = input(f"\n   [{leg_names[leg]}] X={x:3d} Y={y:3d} Z={z:3d} > ").strip()
            
            if cmd_input == 'q':
                break
            elif cmd_input == 'x+':
                self.calibration_point[leg][0] = min(50, x + 1)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'x-':
                self.calibration_point[leg][0] = max(-50, x - 1)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'y+':
                self.calibration_point[leg][1] = min(120, y + 1)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'y-':
                self.calibration_point[leg][1] = max(70, y - 1)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'z+':
                self.calibration_point[leg][2] = min(30, z + 1)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'z-':
                self.calibration_point[leg][2] = max(-30, z - 1)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'X+':
                self.calibration_point[leg][0] = min(50, x + 5)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'X-':
                self.calibration_point[leg][0] = max(-50, x - 5)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'Y+':
                self.calibration_point[leg][1] = min(120, y + 5)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'Y-':
                self.calibration_point[leg][1] = max(70, y - 5)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'Z+':
                self.calibration_point[leg][2] = min(30, z + 5)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'Z-':
                self.calibration_point[leg][2] = max(-30, z - 5)
                self._beep(count=1, duration=0.02)
            elif cmd_input == 'set':
                try:
                    x_new = int(input("   Enter X (-50 to 50): "))
                    y_new = int(input("   Enter Y (70 to 120): "))
                    z_new = int(input("   Enter Z (-30 to 30): "))
                    self.calibration_point[leg][0] = max(-50, min(50, x_new))
                    self.calibration_point[leg][1] = max(70, min(120, y_new))
                    self.calibration_point[leg][2] = max(-30, min(30, z_new))
                    self._beep(count=2)
                    print("   ✓ Values updated")
                except ValueError:
                    print("   ❌ Invalid input")
            elif cmd_input == 'apply':
                print("   📍 Applying calibration to servos...")
                self.apply_calibration()
                self._flash_led(count=1)
                print("   ✓ Applied")
            else:
                print("   ❌ Unknown command")
    
    def reset_to_default(self):
        """Reset calibration to default neutral position."""
        print("\n⚠️  Reset to default neutral position?")
        confirm = input("   Type 'yes' to confirm: ").strip().lower()
        if confirm == 'yes':
            self.calibration_point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
            print("   ✓ Reset to defaults")
            print("   📍 Applying to servos...")
            self.apply_calibration()
            self._beep(count=2)
        else:
            print("   Cancelled")
    
    def run(self):
        """Main interactive loop."""
        self.print_banner()
        print("⚙️  Initializing and applying current calibration...")
        self.apply_calibration()
        time.sleep(0.3)
        print("✓ Robot set to calibration posture\n")
        
        while True:
            try:
                choice = input(self.print_menu()).strip()
                
                if choice == '1':
                    self.adjust_leg_coordinates(0)
                elif choice == '2':
                    self.adjust_leg_coordinates(1)
                elif choice == '3':
                    self.adjust_leg_coordinates(2)
                elif choice == '4':
                    self.adjust_leg_coordinates(3)
                elif choice == '5':
                    self.reset_to_default()
                elif choice == '6':
                    self.save_calibration()
                elif choice == '7':
                    self.print_current_calibration()
                elif choice == '8':
                    print("\n📍 Applying calibration...")
                    self.apply_calibration()
                    self._flash_led(count=2)
                    print("✓ Applied")
                elif choice == '9':
                    print("\n🛑 Exiting calibration...")
                    self.servo.stop_all_pwm()
                    print("✓ All servos released (PWM disabled)")
                    break
                else:
                    print("❌ Invalid choice. Please select 1-9")
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    calibrator = ServoCalibrator()
    
    # Check command-line arguments
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == 'reset':
            print("Resetting to default neutral position...")
            calibrator.calibration_point = [[0, 99, 10], [0, 99, 10], [0, 99, -10], [0, 99, -10]]
            calibrator.save_calibration()
            calibrator.apply_calibration()
            print("✓ Reset complete")
        else:
            print("⚠️  Unknown command. Starting interactive mode...")
            calibrator.run()
    else:
        # Start interactive mode
        calibrator.run()


if __name__ == '__main__':
    main()
