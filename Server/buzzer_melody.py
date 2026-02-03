#!/usr/bin/env python3
# buzzer_melody.py – play melody twice, second time an octave higher
# Author: MT + ChatGPT (Nov 2025)

import RPi.GPIO as GPIO
import time

# --- setup ---
BUZZER_PIN = 17  # adjust if needed
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
buzzer = GPIO.PWM(BUZZER_PIN, 440)  # start frequency

# --- note frequencies (Hz) ---
notes = {
    'C': 262, 'D': 294, 'E': 330, 'F': 349,
    'G': 392, 'A': 440, 'B': 494, 'C5': 523,
    ' ': 0  # rest
}

# --- “Twinkle Twinkle Little Star” melody ---
melody = [
    'C', 'C', 'G', 'G', 'A', 'A', 'G', ' ',
    'F', 'F', 'E', 'E', 'D', 'D', 'C', ' '
]
beat = [0.4,0.4,0.4,0.4,0.4,0.4,0.8,0.2,
        0.4,0.4,0.4,0.4,0.4,0.4,0.8,0.2]

def play_melody(octave=1.0):
    """Play melody; multiply frequencies by 'octave'."""
    for note, dur in zip(melody, beat):
        freq = notes[note]
        if freq == 0:
            buzzer.stop()
        else:
            buzzer.ChangeFrequency(freq * octave)
            buzzer.start(50)  # 50% duty
        time.sleep(dur)
        buzzer.stop()
        time.sleep(0.05)

try:
    print("🎶 Playing melody (normal pitch)...")
    play_melody(octave=1.0)
    time.sleep(0.5)
    print("🎵 Playing melody (one octave higher)...")
    play_melody(octave=2.0)   # double frequency = +1 octave
finally:
    buzzer.stop()
    GPIO.cleanup()
