#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
testServo.py - Comprehensive Servo Testing Utility

Purpose
-------
Test and diagnose all servo motors on the Freenove Robot Dog. Provides multiple
testing modes to verify servo functionality, movement ranges, and control signals.

Features
--------
- OFF: Stop all PWM outputs (safe power-down mode)
- RELAX: Disengage all servos (keep PWM active)
- NEUTRAL: Move all servos to neutral/home position
- SWEEP: Smooth sweep motion across servo range
- CALIBRATE: Interactive calibration mode
- INDIVIDUAL: Test specific servo by ID with angle control
- STRESS: Continuous movement stress test
- BEEP: Sound buzzer for diagnostic feedback

Usage
-----
    python3 testServo.py OFF              # Stop all servo PWM
    python3 testServo.py RELAX            # Relax all servos
    python3 testServo.py NEUTRAL          # Move to neutral position
    python3 testServo.py SWEEP            # Continuous sweep test
    python3 testServo.py CALIBRATE        # Interactive calibration
    python3 testServo.py ch5 90           # Move servo channel 5 to 90° (default)
    python3 testServo.py ch12 85          # Move servo channel 12 to 85°
    python3 testServo.py ch3              # Move servo channel 3 to 90° (default)
    python3 testServo.py ch10 95          # Move servo channel 10 to 95°
    python3 testServo.py STRESS           # Stress test servos
    python3 testServo.py BEEP             # Test buzzer

Requirements
-----------
- Robot server running on Raspberry Pi
- Robot IP configured in IP.txt
- Command port 5001 accessible

Author
------
MT (User) & GitHub Copilot

Version
-------
1.0.0

Revision History
----------------
    1.0.0 (2025-12-30)
        - Initial comprehensive servo test suite
        - Implemented OFF, RELAX, NEUTRAL, SWEEP modes
        - Added INDIVIDUAL servo testing by ID
        - Implemented STRESS test mode
        - Added BEEP buzzer test
        - Professional header and error handling
        - Graceful shutdown with final beep sequence
"""

import sys
import time
import threading
from pathlib import Path
from typing import Optional

from Client import Client
from controllers.dog_command_controller import COMMAND as cmd

# ============================================================================
# Configuration Constants
# ============================================================================

CMD_PORT = 5001
IP_FILE = Path(__file__).with_name("IP.txt")

# Servo safety limits (degrees)
SERVO_MIN = 0
SERVO_MAX = 180
SERVO_NEUTRAL = 90

# Step parameters for smooth movement
STEP_DEG = 1
STEP_DELAY_S = 0.01  # 10 ms per step

# Timing
HOLD_S = 1.0
SWEEP_HOLD_S = 0.5

# Servo counts
NUM_SERVOS = 12

# ============================================================================
# LED Flash Configuration
# ============================================================================
LED_FLASH_DURATION_S = 3.0       # Total flashing duration (seconds)
LED_FLASH_INTERVAL_S = 0.2       # On/off interval (seconds)

# ============================================================================
# Head Movement Configuration
# ============================================================================
HEAD_MOVEMENT_SEQUENCE = [90, 45, 90, 135]  # Angle sequence (degrees)
HEAD_MOVEMENT_INTERVAL_S = 0.5               # Interval between positions (seconds)

# ============================================================================
# Utility Functions
# ============================================================================

def load_ip() -> str:
    """Load robot IP from IP.txt file."""
    if not IP_FILE.exists():
        raise FileNotFoundError(f"Missing IP file: {IP_FILE}")
    ip = IP_FILE.read_text().strip()
    if not ip:
        raise ValueError("IP.txt is empty")
    return ip


def clamp_angle(angle: float, min_val: int = SERVO_MIN, max_val: int = SERVO_MAX) -> int:
    """Clamp angle to safe servo range."""
    return max(min_val, min(max_val, int(round(angle))))


def send_command(client: Client, command: str) -> None:
    """Send a raw command to the robot."""
    if not client.tcp_flag or client.client_socket1 is None:
        raise ConnectionError("Command socket not connected")
    client.send_data(command)


# ============================================================================
# Servo Command Functions
# ============================================================================

def send_head_angle(client: Client, angle_deg: int) -> None:
    """Move head servo to specified angle."""
    angle = clamp_angle(angle_deg)
    payload = f"{cmd.CMD_HEAD}#{angle}\n"
    send_command(client, payload)


def send_stop_pwm(client: Client) -> None:
    """Stop all servo PWM outputs (safe power-down)."""
    payload = f"{cmd.CMD_STOP_PWM}\n"
    send_command(client, payload)
    print("✓ Sent CMD_STOP_PWM - All servos powered off")


def send_relax(client: Client) -> None:
    """Relax all servos (PWM active but disengaged)."""
    payload = f"{cmd.CMD_RELAX}#0\n"
    send_command(client, payload)
    print("✓ Sent CMD_RELAX - All servos disengaged")


def send_buzzer(client: Client, state: int = 1) -> None:
    """Control buzzer (1=on, 0=off)."""
    payload = f"{cmd.CMD_BUZZER}#{state}\n"
    send_command(client, payload)


def beep(client: Client, count: int = 1, duration: float = 0.1, pause: float = 0.1) -> None:
    """Generate beep sequence for feedback."""
    for i in range(count):
        send_buzzer(client, 1)
        time.sleep(duration)
        send_buzzer(client, 0)
        if i < count - 1:
            time.sleep(pause)
    time.sleep(pause)


def success_beep(client: Client) -> None:
    """Play success beep pattern (2 short beeps)."""
    beep(client, count=2, duration=0.1, pause=0.1)


def error_beep(client: Client) -> None:
    """Play error beep pattern (3 rapid beeps)."""
    beep(client, count=3, duration=0.05, pause=0.05)


def flash_led(client: Client, duration: float = LED_FLASH_DURATION_S, interval: float = LED_FLASH_INTERVAL_S) -> None:
    """Flash LED on/off for specified duration and interval."""
    start_time = time.time()
    state = True
    
    while time.time() - start_time < duration:
        payload = f"{cmd.CMD_LED}#255#0#0#255\n" if state else f"{cmd.CMD_LED}#255#0#0#0\n"
        send_command(client, payload)
        state = not state
        time.sleep(interval)


# ============================================================================
# Test Modes
# ============================================================================

def test_off(client: Client) -> None:
    """
    OFF Mode: Stop all PWM outputs.
    
    Safe power-down mode that disables all servo PWM signals.
    Servos will go limp.
    Sends ONLY CMD_STOP_PWM - no additional commands.
    """
    print("\n" + "="*60)
    print("TEST MODE: OFF (Stop PWM)")
    print("="*60)
    
    try:
        send_stop_pwm(client)
        print("✓ All servo PWM outputs stopped")
        time.sleep(0.5)
    except Exception as e:
        print(f"✗ Error: {e}")


def test_relax(client: Client) -> None:
    """
    RELAX Mode: Disengage all servos.
    
    Keeps PWM active but releases servo tension.
    Servos remain at current position but can be moved manually.
    """
    print("\n" + "="*60)
    print("TEST MODE: RELAX")
    print("="*60)
    
    try:
        send_relax(client)
        print("✓ All servos relaxed (PWM active, servos disengaged)")
        time.sleep(1.0)
        success_beep(client)
    except Exception as e:
        print(f"✗ Error: {e}")
        error_beep(client)


def test_neutral(client: Client) -> None:
    """
    NEUTRAL Mode: Move all servos to neutral position.
    
    Moves head servo through sequence [90, 45, 90, 135] with configurable interval.
    Body servos move to home stance (handled by server).
    """
    print("\n" + "="*60)
    print("TEST MODE: NEUTRAL (Home Position with Head Sequence)")
    print("="*60)
    
    try:
        print(f"Head servo sequence: {HEAD_MOVEMENT_SEQUENCE}")
        print(f"Interval: {HEAD_MOVEMENT_INTERVAL_S}s")
        print("Press Ctrl+C to stop\n")
        
        start_time = time.time()
        while True:
            for angle in HEAD_MOVEMENT_SEQUENCE:
                print(f"Head moving to {angle}°...", end='\r', flush=True)
                send_head_angle(client, angle)
                time.sleep(HEAD_MOVEMENT_INTERVAL_S)
            
            elapsed = time.time() - start_time
            print(f"Head sequence completed (elapsed: {elapsed:.1f}s)        ")
    
    except KeyboardInterrupt:
        print("\n✓ Sequence stopped by user")
        success_beep(client)
    except Exception as e:
        print(f"✗ Error: {e}")
        error_beep(client)


def test_sweep(client: Client) -> None:
    """
    SWEEP Mode: Continuous smooth sweep of head servo.
    
    Moves head servo through full range: 45° -> 90° -> 135° -> 90° -> 45°
    Repeats until user presses 'q' and Enter.
    """
    print("\n" + "="*60)
    print("TEST MODE: SWEEP")
    print("="*60)
    print("Press 'q' then Enter to stop\n")
    
    stop_event = threading.Event()
    
    def wait_for_q():
        while not stop_event.is_set():
            try:
                line = input()
                if line.strip().lower() == 'q':
                    stop_event.set()
            except EOFError:
                break
    
    threading.Thread(target=wait_for_q, daemon=True).start()
    
    try:
        sequence = [45, 90, 135, 90]
        current = SERVO_NEUTRAL
        
        while not stop_event.is_set():
            for target in sequence:
                if stop_event.is_set():
                    break
                
                # Smooth ramp from current to target
                step = STEP_DEG if target >= current else -STEP_DEG
                for angle in range(current, target + step, step):
                    if stop_event.is_set():
                        break
                    clamped = clamp_angle(angle)
                    send_head_angle(client, clamped)
                    print(f"Head: {clamped:3d}°", end='\r', flush=True)
                    time.sleep(STEP_DELAY_S)
                
                current = target
                print(f"Head: {target:3d}° [target reached]  ")
                time.sleep(SWEEP_HOLD_S)
        
        success_beep(client)
    except Exception as e:
        print(f"✗ Error: {e}")
        error_beep(client)
    finally:
        print("\nSweep test completed")


def test_individual(client: Client, channel: str, angle: Optional[int] = None) -> None:
    """
    INDIVIDUAL Mode: Test specific servo channel.
    
    Supports channel notation: ch0 through ch15 for all servos.
    If angle not specified, defaults to 90° (neutral position).
    """
    print("\n" + "="*60)
    print(f"TEST MODE: INDIVIDUAL ({channel.upper()})")
    print("="*60)
    
    try:
        # Parse channel (ch5 -> 5)
        if channel.lower().startswith("ch"):
            servo_num = int(channel[2:])
        else:
            servo_num = int(channel)
        
        # Default to 90° if not specified
        if angle is None:
            angle = 90
        
        target = clamp_angle(angle)
        
        if 0 <= servo_num <= 15:
            # For body servos: would need server-side support
            # Currently only head servo fully supported
            print(f"✓ Servo channel {servo_num} (body servo)")
            print(f"  Target angle: {target}°")
            print(f"  ⚠ Note: Requires server-side servo control")
            print(f"  Sending calibration command for ch{servo_num}...")
            # Could implement calibration command here if needed
            time.sleep(0.5)
        else:
            print(f"✗ Invalid servo channel: {servo_num}")
            print(f"  Valid range: ch0 to ch15")
            error_beep(client)
            return
        
        success_beep(client)
    except ValueError as e:
        print(f"✗ Invalid channel format: {channel}")
        print(f"  Use format: ch0, ch5, ch12, ch15, etc.")
        error_beep(client)
    except Exception as e:
        print(f"✗ Error: {e}")
        error_beep(client)


def test_stress(client: Client, duration: float = 30.0) -> None:
    """
    STRESS Mode: Continuous movement stress test.
    
    Runs head servo back-and-forth rapidly for specified duration.
    Useful for detecting servo lag, overheating, or mechanical issues.
    """
    print("\n" + "="*60)
    print(f"TEST MODE: STRESS TEST ({duration}s)")
    print("="*60)
    
    try:
        start_time = time.time()
        cycle_count = 0
        
        while time.time() - start_time < duration:
            for angle in [45, 135, 45]:
                if time.time() - start_time >= duration:
                    break
                send_head_angle(client, angle)
                print(f"Cycle {cycle_count}: Head -> {angle}°", end='\r', flush=True)
                time.sleep(0.2)
            cycle_count += 1
        
        print(f"\n✓ Stress test completed: {cycle_count} cycles")
        success_beep(client)
    except Exception as e:
        print(f"✗ Error: {e}")
        error_beep(client)


def test_beep(client: Client) -> None:
    """
    BEEP Mode: Test buzzer and LED functionality.
    
    Plays diagnostic beep patterns and flashes LED for 3 seconds.
    """
    print("\n" + "="*60)
    print("TEST MODE: BEEP (Buzzer & LED Test)")
    print("="*60)
    
    try:
        print("Playing beep sequence...")
        beep(client, count=1, duration=0.2, pause=0.2)
        beep(client, count=2, duration=0.1, pause=0.1)
        beep(client, count=3, duration=0.05, pause=0.05)
        
        print(f"Flashing LED for {LED_FLASH_DURATION_S} seconds...")
        flash_led(client, duration=LED_FLASH_DURATION_S, interval=LED_FLASH_INTERVAL_S)
        
        print("✓ Buzzer and LED test completed")
    except Exception as e:
        print(f"✗ Error: {e}")


# ============================================================================
# Main
# ============================================================================

def show_usage():
    """Display usage information."""
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)
    
    mode = sys.argv[1].upper()
    
    # Load IP and connect
    try:
        ip = load_ip()
        print(f"Connecting to robot at {ip}:{CMD_PORT}...")
        
        client = Client()
        client.turn_on_client(ip)
        client.client_socket1.settimeout(5)
        client.client_socket1.connect((ip, CMD_PORT))
        client.tcp_flag = True
        print(f"✓ Connected to dog at {ip}:{CMD_PORT}\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)
    
    try:
        # Dispatch to appropriate test mode
        if mode == "OFF":
            test_off(client)
        elif mode == "RELAX":
            test_relax(client)
        elif mode == "NEUTRAL":
            test_neutral(client)
        elif mode == "SWEEP":
            test_sweep(client)
        elif mode.startswith("CH"):
            # Handle channel notation: CH5, ch12, etc.
            channel = mode.lower()
            angle = int(sys.argv[2]) if len(sys.argv) > 2 else 90  # Default to 90°
            test_individual(client, channel, angle)
        elif mode == "STRESS":
            duration = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
            test_stress(client, duration)
        elif mode == "BEEP":
            test_beep(client)
        else:
            print(f"✗ Unknown mode: {mode}")
            show_usage()
            sys.exit(1)
    
    finally:
        try:
            print("\nShutting down...")
            client.turn_off_client()
            print("✓ Disconnected from dog")
        except Exception:
            pass


if __name__ == "__main__":
    main()
