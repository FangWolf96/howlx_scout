#!/usr/bin/env python3

import os

# ---- HARD REQUIREMENT FOR LGPIO ----
os.environ["LGPIO_FILEDIR"] = "/var/run/lgpio"

# lgpio STILL tries to create files in CWD in some code paths
# Force a safe working directory
os.chdir("/var/run/lgpio")
# ----------------------------------------------
import sys
import time

print("\n=== HowlX IAQ Scout — Sensor Diagnostics ===\n")

# ----------------------------------------------
# I2C / Blinka init
# ----------------------------------------------
try:
    import board
    import busio
    i2c = busio.I2C(board.SCL, board.SDA)
    print("✔ I2C bus initialized")
except Exception as e:
    print("✖ I2C bus failed to initialize")
    print(e)
    sys.exit(1)

# ----------------------------------------------
# Helper: scan I2C devices
# ----------------------------------------------
def scan_i2c(i2c):
    devices = []
    while not i2c.try_lock():
        pass
    try:
        devices = i2c.scan()
    finally:
        i2c.unlock()
    return devices

devices = scan_i2c(i2c)

if not devices:
    print("✖ No I2C devices detected")
else:
    print("✔ I2C devices found:")
    for d in devices:
        print(f"  - 0x{d:02X}")

print()

# ----------------------------------------------
# SCD41 (CO₂)
# ----------------------------------------------
try:
    import adafruit_scd4x
    scd = adafruit_scd4x.SCD4X(i2c)
    scd.start_periodic_measurement()
    time.sleep(5)

    if scd.data_ready:
        print("✔ SCD41 detected")
        print(f"  CO₂: {scd.CO2} ppm")
        print(f"  Temp: {scd.temperature:.1f} °C")
        print(f"  RH: {scd.relative_humidity:.1f} %")
    else:
        print("⚠ SCD41 detected but no data yet")

except Exception as e:
    print("✖ SCD41 not detected")
    print(e)

print()

# ----------------------------------------------
# BME688 (Temp / Humidity / Pressure / Gas)
# ----------------------------------------------
try:
    import adafruit_bme680
    bme = adafruit_bme680.Adafruit_BME680_I2C(i2c)
    time.sleep(1)

    print("✔ BME688 detected")
    print(f"  Temp: {bme.temperature:.1f} °C")
    print(f"  RH: {bme.relative_humidity:.1f} %")
    print(f"  Pressure: {bme.pressure:.1f} hPa")
    print(f"  Gas: {bme.gas} Ω")

except Exception as e:
    print("✖ BME688 not detected")
    print(e)

print()

# ----------------------------------------------
# SGP40 (VOC Index)
# ----------------------------------------------
try:
    import adafruit_sgp40
    sgp = adafruit_sgp40.SGP40(i2c)
    time.sleep(1)

    voc = sgp.measure_index(temperature=25, relative_humidity=50)
    print("✔ SGP40 detected")
    print(f"  VOC Index: {voc}")

except Exception as e:
    print("✖ SGP40 not detected")
    print(e)

print("\n=== Diagnostics complete ===\n")
