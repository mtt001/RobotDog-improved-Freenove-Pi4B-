#!/usr/bin/env python3
# ==============================================================
# Freenove Robot Dog - Battery Voltage Test (ADS7830 class)
# --------------------------------------------------------------
# Uses ADS7830.power(0) to read battery voltage via I2C ADC
# ==============================================================

try:
    import ADS7830
    adc = ADS7830.ADS7830()
    voltage = adc.power(0)
    print(f"✅ ADS7830 module loaded successfully.")
    print(f"🔋 Battery voltage: {voltage:.2f} V")
except ModuleNotFoundError as e:
    print("❌ Could not import ADS7830 module:", e)
except AttributeError as e:
    print("❌ The ADS7830 module does not contain expected methods:", e)
except Exception as e:
    print("⚠️ Unexpected error while reading voltage:", e)
