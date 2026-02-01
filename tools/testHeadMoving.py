"""
Test script to sweep the dog head servo.
Moves: -45° -> 90° -> 45° (1° steps, 50 ms/step, 1 s hold at each target).
Requires the server running on the dog (command port 5001).

Usage:
  python3 testHeadMoving.py          # Run default sweep sequence
  python3 testHeadMoving.py 110      # Send fixed angle 110°
"""
import sys
import time
import threading
from pathlib import Path

from Client import Client
from controllers.dog_command_controller import COMMAND as cmd

CMD_PORT = 5001
IP_FILE = Path(__file__).with_name("IP.txt")
STEP_DEG = 1
STEP_DELAY_S = 0.02 # 20 ms
HOLD_S = 0.5
SAFE_MIN = 30      # server will further clamp to 18° internally
SAFE_MAX = 150

def load_ip() -> str:
    if not IP_FILE.exists():
        raise FileNotFoundError(f"Missing IP file: {IP_FILE}")
    ip = IP_FILE.read_text().strip()
    if not ip:
        raise ValueError("IP.txt is empty")
    return ip

def clamp_angle(angle: float) -> int:
    return max(SAFE_MIN, min(SAFE_MAX, int(round(angle))))


def send_head_angle(client: Client, angle_deg: int) -> None:
    """
    Send a CMD_HEAD command over the command socket.
    """
    if not client.tcp_flag or client.client_socket1 is None:
        raise ConnectionError("Command socket not connected")
    payload = f"{cmd.CMD_HEAD}#{angle_deg}\n"
    client.send_data(payload)


def send_relax(client: Client) -> None:
    """
    Toggle relax on the server (affects all servos). The Control loop toggles relax
    state each time it receives CMD_RELAX, so we send once at start and once on exit
    to ensure servos are released.
    """
    if not client.tcp_flag or client.client_socket1 is None:    # when not connected to server then do nothing and show error
        raise ConnectionError("Command socket not connected")
    client.send_data(f"{cmd.CMD_RELAX}#0\n")


def send_stop_pwm(client: Client) -> None:
    """
    Stop all servo PWM outputs for safe power-down.
    """
    if not client.tcp_flag or client.client_socket1 is None:
        raise ConnectionError("Command socket not connected")
    client.send_data(f"{cmd.CMD_STOP_PWM}\n")


def send_beep(client: Client, duration: float = 0.1, pause: float = 0.1, count: int = 1) -> None:
    """
    Drive the buzzer with simple on/off pulses.
    """
    if not client.tcp_flag or client.client_socket1 is None:
        raise ConnectionError("Command socket not connected")
    for _ in range(count):
        client.send_data(f"{cmd.CMD_BUZZER}#1\n")
        time.sleep(duration)
        client.send_data(f"{cmd.CMD_BUZZER}#0\n")
        time.sleep(pause)


def flash_blue_led(client: Client, duration: float = 0.2) -> None:
    """Flash solid blue once using CMD_LED."""
    if not client.tcp_flag or client.client_socket1 is None:
        raise ConnectionError("Command socket not connected")
    client.send_data(f"{cmd.CMD_LED}#255#0#0#255\n")
    time.sleep(duration)
    client.send_data(f"{cmd.CMD_LED}#255#0#0#0\n")


def ramp(client: Client, start: int, target: int, stop_event: threading.Event | None = None) -> int:
    step = STEP_DEG if target >= start else -STEP_DEG
    for ang in range(start, target + step, step):
        if stop_event is not None and stop_event.is_set():
            return clamp_angle(ang)
        clamped = clamp_angle(ang)
        send_head_angle(client, clamped)
        print(f"Head: {clamped}°", end='\r', flush=True)
        time.sleep(STEP_DELAY_S)
    print(f"Head: {target}° [target reached]")
    send_beep(client, count=1)
    time.sleep(HOLD_S)
    # Beep when reaching 90 deg target
    if target == 90:
        send_beep(client, count=1)
        flash_blue_led(client)
    return target


def main():
    ip = load_ip()
    client = Client()

    # Check for command-line argument (fixed angle mode)
    fixed_angle = None
    if len(sys.argv) > 1:
        try:
            fixed_angle = clamp_angle(float(sys.argv[1]))
        except ValueError:
            print(f"Error: Invalid angle '{sys.argv[1]}'. Expected a number.")
            return

    # Prepare sockets
    client.turn_on_client(ip)
    client.client_socket1.settimeout(5)
    client.client_socket1.connect((ip, CMD_PORT))
    client.tcp_flag = True
    print(f"Connected to dog at {ip}:{CMD_PORT}")
    
    try:
        # If fixed angle specified, just send it and exit
        if fixed_angle is not None:
            print(f"Sending fixed angle: {fixed_angle}°")
            send_head_angle(client, fixed_angle)
            send_beep(client, count=1)
            flash_blue_led(client)
            print(f"Head angle set to {fixed_angle}°")
            return

        # Otherwise, run default sweep sequence
        # Relax all servos at start
        #send_relax(client)
        #send_stop_pwm(client)   # disable all servo PWM outputs  <-- COMMENTED OUT: was preventing head movement
        #print(f"send_stop_pwm commands \"{cmd.CMD_STOP_PWM}\". The servos are powered off now for next 2 seconds !! :-) ")
        
        # Head to 90° before looping
        current = clamp_angle(90)
        send_head_angle(client, current)
        time.sleep(HOLD_S)
        send_beep(client, count=2)
        flash_blue_led(client)

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

        sequence = [90,45, 90, 135]
        print(f"Starting continuous head sweep with Sequence: {sequence} deg. ** Press 'q' then Enter to stop. **")

        while not stop_event.is_set():
            for target in sequence:
                if stop_event.is_set():
                    break
                target_clamped = clamp_angle(target)
                current = ramp(client, current, target_clamped, stop_event=stop_event)

    finally:
        try:
            if client.tcp_flag and client.client_socket1 is not None:
                #send_relax(client)  # release servos but still powered and servo pwm active.
                #print(f"send_relax() \"{cmd.CMD_RELAX}#0\n\". The servos are [RELAX] but engaged for next 10 seconds !! :-) ") 
                #send_beep(client, count=1)
                #time.sleep(10.0)
                send_beep(client, count=2)
                flash_blue_led(client)
                send_stop_pwm(client)   # disable all servo PWM outputs
                print(f"send_stop_pwm commands \"{cmd.CMD_STOP_PWM}\". The servos are [Power Off] now for next 10 seconds !! :-) ") 
                send_beep(client, count=3)
                #time.sleep(10.0)
            client.turn_off_client()
            print("Disconnected from dog....")
        except Exception:
            pass


if __name__ == "__main__":
    main()
