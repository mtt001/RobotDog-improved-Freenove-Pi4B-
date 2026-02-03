#!/usr/bin/env python3
"""
Compact buzzer test for the Freenove Robot Dog kit.

This script prefers hardware PWM on the buzzer pin if RPi.GPIO is available
and a pin attribute can be found on the Buzzer instance. If PWM is unavailable
it falls back to the Freenove Buzzer.run(on/off) API using a software toggle.

This variant plays a short (~3s) melody composed of notes with varying durations.
"""

import time
import Buzzer

# Desired tone frequency and timing for beep pattern
# Melody is a list of (frequency_hz, duration_s) tuples totaling ~3 seconds.
MELODY = [
    (440, 0.50),  # A4
    (494, 0.25),  # B4
    (523, 0.40),  # C5
    (587, 0.30),  # D5
    (659, 0.25),  # E5
    (523, 0.40),  # C5
    (440, 0.90),  # A4 (hold)
]
INTER_NOTE_GAP = 0.02  # short silence between notes (seconds)

def _find_pin(obj):
    """
    Inspect the Buzzer instance for a known pin attribute and return it.

    The Freenove Buzzer class may expose different attribute names; check
    several common variants and only return an integer GPIO pin value.
    """
    for name in ("Buzzer_Pin", "buzzer_pin", "buzzerPin", "pin", "PIN"):
        v = getattr(obj, name, None)
        if isinstance(v, int):
            return v
    return None

def _software_toggle(b, freq, duration):
    """
    Approximate a tone by toggling the buzzer on/off in software.

    This is a best-effort fallback when hardware PWM is not available.
    It toggles the Buzzer.run API at roughly the requested frequency by
    sleeping for half a period between on/off transitions.
    - b: Buzzer instance with run(command) method
    - freq: target frequency in Hz (approximate)
    - duration: total duration to emit the tone (seconds)
    """
    half = 1.0 / (freq * 2) if freq > 0 else duration
    end = time.time() + duration

    while time.time() < end:
        try:
            b.run("1")  # many Freenove run() implementations treat non-"0" as ON
        except Exception:
            try:
                b.run(1)
            except Exception:
                break
        time.sleep(half)

        try:
            b.run("0")  # turn off
        except Exception:
            try:
                b.run(0)
            except Exception:
                break
        time.sleep(half)

def main():
    """
    Main entry: instantiate the Freenove Buzzer and play the melody. Use
    hardware PWM when available, otherwise fall back to software toggling.
    """
    try:
        b = Buzzer.Buzzer()  # create the Freenove Buzzer instance
    except Exception as e:
        print("❌ Failed to create Buzzer:", e)
        return

    # Detect a pin exposed on the Buzzer instance (if any)
    pin = _find_pin(b)

    # Try importing RPi.GPIO to see if hardware PWM is available.
    try:
        import RPi.GPIO as GPIO  # type: ignore
    except Exception:
        GPIO = None

    use_pwm = GPIO is not None and pin is not None

    if use_pwm:
        # Configure the pin for PWM and play the melody using hardware PWM.
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT)
            pwm = GPIO.PWM(pin, MELODY[0][0] if MELODY else 440)
            print(f"✅ Using hardware PWM on pin {pin} for melody.")
            pwm.start(0)
            for freq, dur in MELODY:
                # switch frequency and enable tone
                try:
                    pwm.ChangeFrequency(freq)
                except AttributeError:
                    # Some older RPi.GPIO builds require stopping/starting to change freq
                    pwm.stop()
                    pwm = GPIO.PWM(pin, freq)
                pwm.ChangeDutyCycle(50)  # 50% duty cycle -> audible tone
                time.sleep(dur)
                pwm.ChangeDutyCycle(0)   # silence between notes
                time.sleep(INTER_NOTE_GAP)
            pwm.stop()
            print("✅ Melody finished.")
            return
        except Exception as e:
            # If PWM setup or use fails, fall through to the run() fallback.
            print("⚠️ PWM failed, falling back to run():", e)

    # If PWM is not available, fall back to the Buzzer.run-based approach.
    if hasattr(b, "run") and callable(b.run):
        print("ℹ️ PWM unavailable — using Buzzer.run fallback (approximate frequencies).")
        for freq, dur in MELODY:
            _software_toggle(b, freq, dur)
            time.sleep(INTER_NOTE_GAP)
        print("✅ Melody finished.")
        return

    # Neither PWM nor run() were available — nothing to do.
    print("❌ No PWM support and Buzzer.run not available; cannot play melody.")
    
if __name__ == "__main__":
    main()
