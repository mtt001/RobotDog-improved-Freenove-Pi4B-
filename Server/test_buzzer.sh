#!/usr/bin/env bash
# Simple buzzer test: 400 Hz, 200 ms on, 3 repeats (BCM pin 17)
PIN=17
FREQ=600
DURATION_MS=200
REPEATS=3

# reset any leftover GPIO state (safe)
sudo /usr/bin/python3 - <<PY
import RPi.GPIO as GPIO
GPIO.cleanup()
PY

# run PWM beep
sudo /usr/bin/python3 - <<PY
import RPi.GPIO as GPIO, time
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
pin = int(${PIN})
freq = ${FREQ}
dur = ${DURATION_MS} / 1000.0
reps = int(${REPEATS})
GPIO.setup(pin, GPIO.OUT)
p = GPIO.PWM(pin, freq)
try:
    for _ in range(reps):
        p.start(50)
        time.sleep(dur)
        p.stop()
        time.sleep(0.07)
finally:
    GPIO.cleanup()
PY
