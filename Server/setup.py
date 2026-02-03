from setuptools import setup

# Minimal, tutorial-style installer for Freenove Robot Dog (Bullseye-friendly)
# If your tutorial listed slightly different libs, we can adjust later.

setup(
    name="freenove-smartdog",
    version="0.1.0",
    description="Freenove Robot Dog dependencies installer",
    author="You",
    python_requires=">=3.7",
    install_requires=[
        # Web/HTTP
        "flask>=2.0,<3.0",
        "flask-cors>=3.0,<4.0",
        "requests>=2.25",

        # I2C / sensors / PWM
        "smbus2>=0.4",
        "adafruit-circuitpython-pca9685>=3.4",
        "adafruit-circuitpython-mpu6050>=1.0",

        # LEDs (ws281x / neopixel)
        "rpi-ws281x>=4.3",
        "adafruit-circuitpython-neopixel>=6.0",

        # Camera / image handling (headless OpenCV is lighter)
        "opencv-python-headless>=4.5",
    ],
)
