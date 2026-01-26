#!/usr/bin/env python3

import time
import sys

print("\n=== HowlX IAQ Scout — Sensor Diagnostics ===\n")

# -------------------------
# I2C / board init
# -------------------------
try:
    import board
    import busio
    i2c = busio.I2C(board.SCL, board.SDA)
    print("✔ I2C bus initialized")
except Exception as e:
    print("✖ I2C bus failed to initialize")
    print(e)
    sys.exit(1)

print()

# -------------------------
# SCD41 (CO2 / Temp / RH)
# -------------------------
scd41 = None
try:
    import adafruit_scd4x
    scd41 = adafruit_scd4x.SCD4X(i2c)
    scd41.start_periodic_measurement()
    print("✔ SCD41 detected")
except Exception as e:
    print("✖ SCD41 not detected")
    print(e)

# -------------------------
# BME688 (Temp / RH / Pressure / Gas)
# -------------------------
bme688 = None
try:
    import adafruit_bme680
    bme688 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
    print("✔ BME688 detected")
except Exception as e:
    print("✖ BME688 not detected")
    print(e)

# -------------------------
# SGP40 (VOC)
# -------------------------
sgp40 = None
try:
    import adafruit_sgp40
    sgp40 = adafruit_sgp40.SGP40(i2c)
    print("✔ SGP40 detected")
except Exception as e:
    print("✖ SGP40 not detected")
    print(e)

print("\n--- Polling live values (10 seconds) ---\n")

start = time.time()
while time.time() - start < 10:
    print("Reading snapshot:")

    if scd41 and scd41.data_ready:
        print(
            f"  SCD41 → CO₂: {scd41.CO2} ppm | "
            f"Temp: {scd41.temperature:.1f} °C | "
            f"RH: {scd41.relative_humidity:.1f} %"
        )
    elif scd41:
        print("  SCD41 → waiting for data...")

    if bme688:
        print(
            f"  BME688 → Temp: {bme688.temperature:.1f} °C | "
            f"RH: {bme688.humidity:.1f} % | "
            f"Pressure: {bme688.pressure:.1f} hPa | "
            f"Gas: {bme688.gas} Ω"
        )

    if sgp40:
        # SGP40 requires humidity/temp compensation (use BME if present)
        if bme688:
            voc = sgp40.measure_raw(
                temperature=bme688.temperature,
                relative_humidity=bme688.humidity
            )
        else:
            voc = sgp40.measure_raw()

        print(f"  SGP40 → Raw VOC index: {voc}")

    print()
    time.sleep(2)

print("=== Diagnostics complete ===\n")
