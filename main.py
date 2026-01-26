import os

# =========================================================
# FORCE CORRECT 800x480 SCALING ON PI TOUCH
# =========================================================
os.environ["QT_QPA_PLATFORM"] = "eglfs"
os.environ["QT_QPA_EGLFS_HIDECURSOR"] = "1"
os.environ["QT_QPA_EGLFS_PHYSICAL_WIDTH"] = "154"
os.environ["QT_QPA_EGLFS_PHYSICAL_HEIGHT"] = "86"
os.environ["QT_FONT_DPI"] = "96"

# =========================================================
# IMPORTS
# =========================================================
import sys
import random
import json
import time
from pathlib import Path
from enum import Enum

from PyQt5 import QtWidgets, QtGui, QtCore

# =========================================================
# APP CONSTANTS
# =========================================================
WIDTH, HEIGHT = 800, 480

# =========================================================
# SENSOR LIB IMPORTS 
# =========================================================
try:
    import board
    import busio
    import adafruit_scd4x
    import adafruit_bme680
    SENSORS_AVAILABLE = True
except Exception as e:
    print("Sensor libs not available:", repr(e))
    SENSORS_AVAILABLE = False

# =========================================================
# GLOBAL SENSOR STATE (single source of truth)
# =========================================================
_i2c = None
_scd41 = None
_scd41_last_co2 = None
_bme688 = None


_scd41_miss = 0
_bme688_miss = 0
MISS_LIMIT = 5

class SensorState(Enum):
    MISSING = 0
    WARMUP  = 1
    READY   = 2
    STALE   = 3
    ERROR   = 4

SENSOR_STATUS = {
    "scd41":  SensorState.MISSING,
    "bme688": SensorState.MISSING,
    "pm25":   SensorState.MISSING,  # not installed yet
    "co":     SensorState.MISSING,  # not installed yet
}

SENSOR_SINCE = {
    "scd41":  None,
    "bme688": None,
}

def _i2c_scan(i2c):
    addrs = []
    try:
        while not i2c.try_lock():
            pass
        addrs = i2c.scan()
    finally:
        try:
            i2c.unlock()
        except Exception:
            pass
    return set(addrs)


def init_sensors():
    global _i2c, _scd41, _bme688, _scd41_miss, _bme688_miss

    if not SENSORS_AVAILABLE:
        SENSOR_STATUS["scd41"] = SensorState.MISSING
        SENSOR_STATUS["bme688"] = SensorState.MISSING
        SENSOR_SINCE["scd41"] = None
        SENSOR_SINCE["bme688"] = None
        _scd41 = None
        _bme688 = None
        return False

    try:
        if _i2c is None:
            _i2c = busio.I2C(board.SCL, board.SDA)

        addrs = _i2c_scan(_i2c)
        print("I2C scan:", [hex(a) for a in sorted(addrs)])

        # Empty scan = transient bus hiccup.
        # Mark installed sensors as STALE (blinking) instead of MISSING.
        if not addrs:
            if _scd41 is not None and SENSOR_STATUS["scd41"] == SensorState.READY:
                SENSOR_STATUS["scd41"] = SensorState.STALE
            if _bme688 is not None and SENSOR_STATUS["bme688"] == SensorState.READY:
                SENSOR_STATUS["bme688"] = SensorState.STALE
            return True

        has_scd41 = 0x62 in addrs
        has_bme = (0x76 in addrs) or (0x77 in addrs)

        # ---- SCD41 ----
        if has_scd41:
            _scd41_miss = 0
            if _scd41 is None:
                _scd41 = adafruit_scd4x.SCD4X(_i2c)
                _scd41.start_periodic_measurement()
                SENSOR_STATUS["scd41"] = SensorState.WARMUP
                SENSOR_SINCE["scd41"] = time.time()
            else:
                if SENSOR_STATUS["scd41"] in (SensorState.MISSING, SensorState.ERROR, SensorState.STALE):
                    SENSOR_STATUS["scd41"] = SensorState.WARMUP
                    if SENSOR_SINCE.get("scd41") is None:
                        SENSOR_SINCE["scd41"] = time.time()
        else:
            _scd41_miss += 1
            if _scd41_miss >= MISS_LIMIT:
                _scd41 = None
                SENSOR_STATUS["scd41"] = SensorState.MISSING
                SENSOR_SINCE["scd41"] = None
            else:
                if _scd41 is not None:
                    SENSOR_STATUS["scd41"] = SensorState.STALE

        # ---- BME688 ----
        if has_bme:
            _bme688_miss = 0
            if _bme688 is None:
                _bme688 = adafruit_bme680.Adafruit_BME680_I2C(_i2c)
                _bme688.sea_level_pressure = 1013.25
                SENSOR_STATUS["bme688"] = SensorState.WARMUP
                SENSOR_SINCE["bme688"] = time.time()
            else:
                if SENSOR_STATUS["bme688"] in (SensorState.MISSING, SensorState.ERROR, SensorState.STALE):
                    SENSOR_STATUS["bme688"] = SensorState.WARMUP
                    if SENSOR_SINCE.get("bme688") is None:
                        SENSOR_SINCE["bme688"] = time.time()
        else:
            _bme688_miss += 1
            if _bme688_miss >= MISS_LIMIT:
                _bme688 = None
                SENSOR_STATUS["bme688"] = SensorState.MISSING
                SENSOR_SINCE["bme688"] = None
            else:
                if _bme688 is not None:
                    SENSOR_STATUS["bme688"] = SensorState.STALE

        # PM2.5 + CO not installed yet
        SENSOR_STATUS["pm25"] = SensorState.MISSING
        SENSOR_STATUS["co"] = SensorState.MISSING

        return True

    except Exception as e:
        print("init_sensors() failed:", repr(e))
        SENSOR_STATUS["scd41"] = SensorState.ERROR
        SENSOR_STATUS["bme688"] = SensorState.ERROR
        return False




# ---------------------------
# CO danger threshold
# ---------------------------
CO_DANGER_THRESHOLD = 35  # ppm


def add_watermark(parent, x, y, w=350, opacity=0.06):
    label = QtWidgets.QLabel(parent)
    pix = QtGui.QPixmap("assets/logo.png").scaled(
        w, w,
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation
    )
    label.setPixmap(pix)
    label.move(x, y)
    label.lower()  # keep behind everything

    effect = QtWidgets.QGraphicsOpacityEffect()
    effect.setOpacity(opacity)
    label.setGraphicsEffect(effect)

    return label


# ---------------------------
# Mock data (replace later)
# ---------------------------
def mock_readings():
    return {
        "co2": random.randint(450, 2000),
        "pm25": round(random.uniform(2, 500), 1),
        "voc": round(random.uniform(0.2, 2.8), 2),
        "temp": round(random.uniform(68, 78), 1),
        "humidity": round(random.uniform(35, 55), 1),
        "co": round(random.uniform(0, 30), 1),
    }
    
# === SENSOR BACKEND ===
def read_sensors():
    global _scd41_last_co2

    ok = init_sensors()
    if not ok:
        return mock_readings()

    # --- SCD41 CO2 ---
    co2 = None
    if _scd41 is not None:
        try:
            warmup_s = 10
            since = SENSOR_SINCE.get("scd41") or time.time()
            warmed = (time.time() - since) >= warmup_s
            print("SCD41 data_ready:", _scd41.data_ready, "last_co2:", _scd41_last_co2)

            if _scd41.data_ready:
                co2 = int(_scd41.CO2)  # NOTE: Adafruit uses .CO2 (caps) on SCD4x
                _scd41_last_co2 = co2
                SENSOR_STATUS["scd41"] = SensorState.READY
            else:
                # No new sample yet
                if _scd41_last_co2 is None:
                    SENSOR_STATUS["scd41"] = SensorState.WARMUP
                else:
                    co2 = _scd41_last_co2
                    SENSOR_STATUS["scd41"] = SensorState.STALE if warmed else SensorState.WARMUP

        except Exception as e:
            print("SCD41 read error:", repr(e))
            SENSOR_STATUS["scd41"] = SensorState.ERROR


    # --- BME688 temp/humidity + gas ---
    temp_f = None
    humidity = None
    gas = None

    if _bme688 is not None:
        try:
            temp_f = (_bme688.temperature * 9/5) + 32
            humidity = _bme688.relative_humidity
            gas = getattr(_bme688, "gas", None)

            warmup_s = 60
            since = SENSOR_SINCE.get("bme688") or time.time()
            if (time.time() - since) < warmup_s:
                SENSOR_STATUS["bme688"] = SensorState.WARMUP
            else:
                SENSOR_STATUS["bme688"] = SensorState.READY

        except Exception:
            SENSOR_STATUS["bme688"] = SensorState.ERROR

    voc = None
    if gas is not None and SENSOR_STATUS["bme688"] == SensorState.READY:
        voc = voc_proxy_from_gas_ohms(float(gas))

    ## Only fallback to a number if the sensor exists but no sample yet.
    # If sensor is missing, keep None so UI shows "--".
    #if co2 is None and _scd41 is not None:
    #    co2 = 450

    if temp_f is None:
        temp_f = 72.0
    if humidity is None:
        humidity = 45.0

    return {
        "co2": int(co2),
        "pm25": None,      # not installed yet
        "voc": voc,        # None until BME688 ready
        "temp": round(float(temp_f), 1),
        "humidity": round(float(humidity), 1),
        "co": None,        # not installed yet
    }


from enum import Enum

class AlertState(Enum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2


def penalty_color(points):
    # points are negative numbers
    if points <= -20:
        return "#f44336"  # red
    if points <= -10:
        return "#ff9800"  # orange
    return "#ffeb3b"      # yellow


def evaluate_readings(d, history):
    """
    Returns:
      score (int),
      breakdown (list of dicts),
      how_to_improve (list of str),
      state (AlertState)
    """
    breakdown = []
    how = []

    co  = nval(d.get("co"), 0.0)
    pm  = nval(d.get("pm25"), 0.0)
    co2 = nval(d.get("co2"), 450)
    voc = nval(d.get("voc"), 0.0)

    has_co  = installed_state("co")
    has_pm  = installed_state("pm25")
    has_co2 = installed_state("scd41")
    has_voc = installed_state("bme688")  # proxy from BME688 gas

    # -------------------------
    # Alert state (safety first)
    # -------------------------
    if has_co and co >= CO_DANGER_THRESHOLD:
        state = AlertState.CRITICAL
    elif (has_pm and pm > 35) or (has_co2 and co2 > 1200) or (has_voc and voc > 2.0) or (has_co and co >= 9):
        state = AlertState.WARNING
    else:
        state = AlertState.NORMAL

    score = 100


    # -------------------------
    # PM2.5 analysis & penalty
    # -------------------------
    if has_pm:
        pm25_analysis = analyze_pm25(pm, history.get("pm25", []))

        pm_pen = 0
        if pm > 35:
            pm_pen = -25
        elif pm > 12:
            pm_pen = -10

        if pm_pen:
            score += pm_pen
            breakdown.append({
                "metric": "PM2.5",
                "points": pm_pen,
                "label": pm25_severity(pm)[0],
                "color": penalty_color(pm_pen),
                "analysis": pm25_analysis
            })
            how.extend(pm25_analysis["recommendations"])



    # -------------------------
    # CO2 penalty
    # -------------------------
    if has_co2:
        co2_pen = 0
        if co2 > 1200:
            co2_pen = -20
            how.append("Increase fresh air ventilation; consider checking HVAC outside air settings.")
        elif co2 > 800:
            co2_pen = -10
            how.append("Ventilation could be improved (open door/window briefly or increase outside air).")

        if co2_pen:
            score += co2_pen
            breakdown.append({
                "metric": "CO₂",
                "points": co2_pen,
                "label": co2_severity(co2)[0],
                "color": penalty_color(co2_pen),
            })


    # -------------------------
    # VOC penalty (VOC can be None during warmup)
    # -------------------------
    if has_voc:
        voc_pen = 0
        if voc > 2.0:
            voc_pen = -20
            how.append("Reduce VOC sources (cleaners/solvents); increase ventilation; consider activated carbon filtration.")
        elif voc > 1.0:
            voc_pen = -10
            how.append("Ventilate and reduce VOC sources (fragrances, sprays, harsh cleaners).")

        if voc_pen:
            score += voc_pen
            breakdown.append({
                "metric": "VOC",
                "points": voc_pen,
                "label": "High" if voc > 2.0 else "Elevated",
                "color": penalty_color(voc_pen),
            })

        
    # -------------------------
    # CO penalty (dominant safety factor)
    # -------------------------
    if has_co:
        co_pen = 0
        if co >= CO_DANGER_THRESHOLD:
            co_pen = -60
            how.insert(0, "CO is dangerous — ventilate immediately and shut off combustion sources.")
            how.insert(1, "Evacuate if levels remain high; verify with a calibrated meter.")
        elif co >= 9:
            co_pen = -20
            how.insert(0, "CO detected — investigate combustion sources and improve ventilation.")

        if co_pen:
            score += co_pen
            breakdown.append({
                "metric": "CO",
                "points": co_pen,
                "label": co_severity(co)[0],
                "color": penalty_color(co_pen),
            })


    # Hard safety cap: if CRITICAL, cap the score so it never looks “okay”
    if state == AlertState.CRITICAL:
        score = min(score, 30)

    score = max(min(int(score), 100), 0)

    # Keep how-to clean (no duplicates)
    seen = set()
    how_unique = []
    for item in how:
        if item not in seen:
            seen.add(item)
            how_unique.append(item)

    return score, breakdown, how_unique, state

# ---------------------------
# Non-Integer Helper
# ---------------------------
def nval(x, default=0.0):
    """Numeric value or default (handles None)."""
    return default if x is None else x

def installed_state(sensor_key: str) -> bool:
    return SENSOR_STATUS.get(sensor_key) in (
        SensorState.WARMUP, SensorState.READY, SensorState.STALE
    )


# ---------------------------
# Severity helpers
# ---------------------------
def pm25_severity(v):
    if v <= 12:
        return ("Good", "#4caf50", "Air quality is healthy.")
    elif v <= 35:
        return ("Moderate", "#ffeb3b", "Sensitive individuals may be affected.")
    elif v <= 55:
        return ("Poor", "#ff9800", "Unhealthy for sensitive groups.")
    else:
        return ("Unhealthy", "#f44336", "Unhealthy for everyone.")

def co2_severity(v):
    if v <= 800:
        return ("Good", "#4caf50", "Ventilation is adequate.")
    elif v <= 1200:
        return ("Elevated", "#ff9800", "Ventilation could be improved.")
    else:
        return ("High", "#f44336", "Fresh air strongly recommended.")

def humidity_severity(v):
    if 30 <= v <= 50:
        return ("Optimal", "#4caf50", "Comfortable humidity level.")
    elif v < 30:
        return ("Low", "#03a9f4", "May cause dry skin and irritation.")
    else:
        return ("High", "#ff9800", "May encourage mold growth.")
        
def co_severity(v):
    if v <= 9:
        return ("Safe", "#4caf50", "Carbon monoxide levels are safe.")
    elif v <= 35:
        return ("Elevated", "#ff9800", "CO detected — investigate sources.")
    else:
        return ("Danger", "#f44336", "Dangerous CO levels — ventilate immediately.")
# ---------------------------
# Rolling analysis helpers
# ---------------------------
def rolling_avg(values):
    return sum(values) / len(values) if values else 0

def peak_count(values, threshold):
    return sum(1 for v in values if v >= threshold)

def sustained(values, threshold, ratio=0.5):
    if not values:
        return False
    return peak_count(values, threshold) / len(values) >= ratio

def analyze_pm25(current, history):
    """
    Returns structured PM2.5 analysis for detail view
    """
    analysis = {
        "status": "",
        "confidence": "Low",
        "summary": "",
        "health": "",
        "recommendations": [],
        "window": "Instant"
    }

    if not history or len(history) < 5:
        analysis["status"] = "Initial reading"
        analysis["summary"] = "Not enough data collected to determine trends yet."
        analysis["health"] = "Short-term exposure risk cannot yet be assessed."
        return analysis

    # 🔧 IMPORTANT: normalize deque → list ONCE
    values = list(history)

    avg = rolling_avg(values)
    peaks = peak_count(values, 35)
    sustained_high = sustained(values, 35, ratio=0.75)

    recent = values[-5:]
    recent_high = any(v > 35 for v in recent)

    analysis["confidence"] = "High" if len(values) >= 20 else "Medium"
    analysis["window"] = "Rolling (~1 min)"

    if sustained_high:
        analysis["status"] = "Sustained elevation"
        analysis["summary"] = "PM2.5 levels have remained consistently elevated over time."
        analysis["health"] = (
            "Longer exposure to elevated PM2.5 increases risk of respiratory and cardiovascular stress."
        )
        analysis["recommendations"].append(
            "Continuous filtration with a HEPA purifier is strongly recommended."
        )

    elif peaks >= 5:
        analysis["status"] = "Repeated spikes"
        analysis["summary"] = "Multiple PM2.5 spikes detected, suggesting intermittent particle sources."
        analysis["health"] = "Short-term spikes may aggravate asthma and sensitive individuals."
        analysis["recommendations"].append(
            "Identify intermittent sources such as cooking, candles, or dust disturbance."
        )

    elif recent_high:
        analysis["status"] = "Recently elevated"
        analysis["summary"] = "PM2.5 was elevated recently but is now declining."
        analysis["health"] = "Recent exposure may still affect sensitive individuals."
        analysis["recommendations"].append(
            "Continue ventilation or filtration to ensure levels remain low."
        )

    elif avg <= 12:
        analysis["status"] = "Stable / Healthy"
        analysis["summary"] = "PM2.5 levels have remained consistently low."
        analysis["health"] = "Air quality is within healthy limits for extended exposure."

    else:
        analysis["status"] = "Moderate elevation"
        analysis["summary"] = "PM2.5 levels are moderately elevated but not persistently high."
        analysis["health"] = "Sensitive individuals may experience irritation or discomfort."

    return analysis

# === VOC PROXY ===
def voc_proxy_from_gas_ohms(gas_ohms: float) -> float:
    """
    This is a simple proxy scaled 0.0–3.0 where LOWER gas resistance -> higher 'VOC'.
    """
    if not gas_ohms or gas_ohms <= 0:
        return 0.0

    # Typical indoor gas resistance might be ~5k–500k depending on conditions.
    # Clamp and map inversely.
    lo, hi = 5_000.0, 500_000.0
    g = max(min(gas_ohms, hi), lo)

    # Normalize (hi -> 0, lo -> 1)
    t = (hi - g) / (hi - lo)

    # Scale to 0–3
    return round(t * 3.0, 2)


def analyze_co2(current, history):
    """
    Returns structured CO₂ analysis for detail view
    """
    analysis = {
        "status": "",
        "confidence": "Low",
        "summary": "",
        "health": "",
        "recommendations": [],
        "window": "Instant"
    }

    # Not enough data yet
    if not history or len(history) < 5:
        analysis["status"] = "Initial reading"
        analysis["summary"] = "Not enough data collected to determine ventilation trends yet."
        analysis["health"] = "Short-term CO₂ exposure at this level cannot yet be assessed."
        return analysis

    # 🔧 Normalize deque → list ONCE
    values = list(history)

    avg = rolling_avg(values)
    sustained_high = sustained(values, 1200, ratio=0.7)

    recent = values[-5:]
    recent_high = any(v > 1200 for v in recent)

    analysis["confidence"] = "High" if len(values) >= 20 else "Medium"
    analysis["window"] = "Rolling (~1 min)"

    if sustained_high:
        analysis["status"] = "Sustained elevation"
        analysis["summary"] = (
            "CO₂ levels have remained consistently elevated, indicating insufficient ventilation."
        )
        analysis["health"] = (
            "Prolonged elevated CO₂ may cause fatigue, headaches, and reduced cognitive performance."
        )
        analysis["recommendations"].extend([
            "Increase fresh air ventilation (open windows or doors where safe).",
            "Inspect HVAC outside-air intake and damper operation."
        ])

    elif current > 1200:
        analysis["status"] = "High"
        analysis["summary"] = "CO₂ is currently elevated, suggesting poor air exchange."
        analysis["health"] = "Short-term exposure may reduce concentration and cause drowsiness."
        analysis["recommendations"].append(
            "Ventilate the space to reduce CO₂ buildup."
        )

    elif recent_high:
        analysis["status"] = "Recently elevated"
        analysis["summary"] = "CO₂ levels were elevated recently but are now improving."
        analysis["health"] = "Recent exposure may still affect comfort and alertness."
        analysis["recommendations"].append(
            "Continue ventilation to ensure levels remain stable."
        )

    elif current > 800:
        analysis["status"] = "Moderate"
        analysis["summary"] = "CO₂ is moderately elevated and may increase with occupancy."
        analysis["health"] = "Sensitive individuals may notice mild fatigue."

    else:
        analysis["status"] = "Healthy"
        analysis["summary"] = "CO₂ levels indicate adequate ventilation."
        analysis["health"] = "Air quality supports comfort and cognitive performance."

    return analysis

    
def analyze_voc(current, history):
    """
    Returns structured VOC analysis for detail view
    """
    analysis = {
        "status": "",
        "confidence": "Low",
        "summary": "",
        "health": "",
        "recommendations": [],
        "window": "Instant"
    }

    # Not enough data yet
    if not history or len(history) < 5:
        analysis["status"] = "Initial reading"
        analysis["summary"] = "Not enough data collected to determine VOC trends yet."
        analysis["health"] = "Short-term VOC exposure risk cannot yet be assessed."
        return analysis

    # 🔧 Normalize deque → list ONCE
    values = list(history)

    avg = rolling_avg(values)
    peaks = peak_count(values, 2.0)
    sustained_high = sustained(values, 2.0, ratio=0.6)

    recent = values[-5:]
    recent_high = any(v > 2.0 for v in recent)

    analysis["confidence"] = "High" if len(values) >= 20 else "Medium"
    analysis["window"] = "Rolling (~1 min)"

    if sustained_high:
        analysis["status"] = "Sustained elevation"
        analysis["summary"] = (
            "VOC levels have remained consistently elevated over time."
        )
        analysis["health"] = (
            "Prolonged exposure to elevated VOCs may irritate airways and increase headaches or nausea."
        )
        analysis["recommendations"].extend([
            "Increase ventilation to remove indoor VOC buildup.",
            "Reduce or eliminate VOC sources (cleaners, fragrances, solvents).",
            "Consider activated carbon or charcoal filtration."
        ])

    elif current > 2.0:
        analysis["status"] = "High"
        analysis["summary"] = "VOC levels are currently elevated."
        analysis["health"] = "Short-term exposure may irritate eyes, throat, or sensitive individuals."
        analysis["recommendations"].append(
            "Ventilate the space and reduce active VOC sources."
        )

    elif recent_high:
        analysis["status"] = "Recently elevated"
        analysis["summary"] = "VOC levels were elevated recently but are now declining."
        analysis["health"] = "Recent exposure may still cause mild irritation."
        analysis["recommendations"].append(
            "Continue ventilation until VOC levels stabilize."
        )

    elif avg <= 1.0:
        analysis["status"] = "Stable / Healthy"
        analysis["summary"] = "VOC levels have remained consistently low."
        analysis["health"] = "Air quality supports comfort with minimal chemical exposure."

    else:
        analysis["status"] = "Moderate elevation"
        analysis["summary"] = "VOC levels are moderately elevated but not persistently high."
        analysis["health"] = "Some individuals may experience mild irritation or odor sensitivity."

    return analysis

def analyze_humidity(current, history):
    analysis = {
        "status": "",
        "confidence": "Low",
        "summary": "",
        "health": "",
        "recommendations": [],
        "window": "Instant"
    }

    if not history or len(history) < 5:
        analysis["status"] = "Initial reading"
        analysis["summary"] = "Not enough data to determine humidity trends yet."
        analysis["health"] = "Short-term comfort impact only."
        return analysis

    values = list(history)
    avg = rolling_avg(values)

    analysis["confidence"] = "High" if len(values) >= 20 else "Medium"
    analysis["window"] = "Rolling (~1 min)"

    if avg > 55:
        analysis["status"] = "High"
        analysis["summary"] = "Humidity has remained elevated."
        analysis["health"] = "High humidity increases mold risk and discomfort."
        analysis["recommendations"].extend([
            "Reduce humidity with dehumidification.",
            "Check HVAC condensate drainage and airflow."
        ])

    elif avg < 30:
        analysis["status"] = "Low"
        analysis["summary"] = "Humidity has remained low."
        analysis["health"] = "Low humidity may cause dry skin and respiratory irritation."
        analysis["recommendations"].append(
            "Increase humidity using a humidifier or controlled ventilation."
        )

    else:
        analysis["status"] = "Optimal"
        analysis["summary"] = "Humidity is within the ideal comfort range."
        analysis["health"] = "Supports comfort and respiratory health."

    return analysis

def analyze_temp(current, history):
    analysis = {
        "status": "",
        "confidence": "Low",
        "summary": "",
        "health": "",
        "recommendations": [],
        "window": "Instant"
    }

    if not history or len(history) < 5:
        analysis["status"] = "Initial reading"
        analysis["summary"] = "Not enough data to determine temperature stability yet."
        analysis["health"] = "Comfort impact only."
        return analysis

    values = list(history)
    avg = rolling_avg(values)
    swing = max(values) - min(values)

    analysis["confidence"] = "High" if len(values) >= 20 else "Medium"
    analysis["window"] = "Rolling (~1 min)"

    if avg > 78:
        analysis["status"] = "Warm"
        analysis["summary"] = "Temperature is consistently above comfort range."
        analysis["health"] = "May reduce comfort and increase fatigue."
        analysis["recommendations"].append(
            "Improve cooling or reduce internal heat loads."
        )

    elif avg < 68:
        analysis["status"] = "Cool"
        analysis["summary"] = "Temperature is consistently below comfort range."
        analysis["health"] = "May cause discomfort or cold stress."
        analysis["recommendations"].append(
            "Increase heating or reduce drafts."
        )

    elif swing > 6:
        analysis["status"] = "Unstable"
        analysis["summary"] = "Noticeable temperature swings detected."
        analysis["health"] = "Fluctuations may reduce comfort."
        analysis["recommendations"].append(
            "Check thermostat placement and HVAC cycling."
        )

    else:
        analysis["status"] = "Comfortable"
        analysis["summary"] = "Temperature is stable and within comfort range."
        analysis["health"] = "Supports comfort and productivity."

    return analysis

def analyze_co(current, history):
    """
    Returns structured Carbon Monoxide (CO) analysis for detail view
    """
    analysis = {
        "status": "",
        "confidence": "Low",
        "summary": "",
        "health": "",
        "recommendations": [],
        "window": "Instant"
    }

    if not history or len(history) < 5:
        analysis["status"] = "Initial reading"
        analysis["summary"] = "Not enough data collected to determine CO patterns yet."
        analysis["health"] = "Carbon monoxide exposure risk cannot yet be assessed."
        return analysis

    values = list(history)
    avg = rolling_avg(values)
    peaks = peak_count(values, 9)
    sustained_high = sustained(values, 9, ratio=0.3)

    analysis["confidence"] = "High" if len(values) >= 20 else "Medium"
    analysis["window"] = "Rolling (~1 min)"

    if current >= 35:
        analysis["status"] = "Dangerous"
        analysis["summary"] = "Carbon monoxide is currently at a dangerous level."
        analysis["health"] = (
            "High CO levels can cause dizziness, nausea, confusion, and loss of consciousness."
        )
        analysis["recommendations"].extend([
            "Ventilate immediately and shut off combustion sources.",
            "Evacuate the space if levels do not drop quickly.",
            "Verify readings with a calibrated CO meter."
        ])

    elif sustained_high:
        analysis["status"] = "Repeated detection"
        analysis["summary"] = "Carbon monoxide has been detected repeatedly over time."
        analysis["health"] = (
            "Repeated low-level CO exposure can cause headaches, fatigue, and long-term health risks."
        )
        analysis["recommendations"].extend([
            "Inspect combustion appliances and exhaust systems.",
            "Ensure proper ventilation in the space."
        ])

    elif current >= 9:
        analysis["status"] = "Elevated"
        analysis["summary"] = "Carbon monoxide is currently elevated."
        analysis["health"] = (
            "Even moderate CO levels may cause symptoms in sensitive individuals."
        )
        analysis["recommendations"].append(
            "Investigate possible combustion sources and improve ventilation."
        )

    else:
        analysis["status"] = "Safe"
        analysis["summary"] = "Carbon monoxide levels are within safe limits."
        analysis["health"] = "No health effects expected at current levels."

    return analysis




# ---------------------------
# Shared metric detail renderer
# ---------------------------
def render_analysis_detail(analysis, accent="#ff9800"):
    html = (
        "<div style='font-size:16px;'>"

        "<div style='margin-bottom:12px;'>"
        "<div style='color:#aaaaaa; font-size:13px;'>SEVERITY</div>"
        f"<div style='font-size:18px; font-weight:600; color:white;'>"
        f"{analysis['status']}"
        "</div></div>"

        "<div style='margin-bottom:12px;'>"
        "<div style='color:#aaaaaa; font-size:13px;'>CONFIDENCE</div>"
        f"<div style='font-size:15px; color:#dddddd;'>"
        f"{analysis['confidence']} · {analysis['window']}"
        "</div></div>"

        "<div style='margin-bottom:12px;'>"
        "<div style='color:#aaaaaa; font-size:13px;'>SUMMARY</div>"
        f"<div style='font-size:15px; color:#dddddd;'>"
        f"{analysis['summary']}"
        "</div></div>"

        "<div style='margin-bottom:12px;'>"
        "<div style='color:#aaaaaa; font-size:13px;'>HEALTH IMPACT</div>"
        f"<div style='font-size:15px; color:#dddddd;'>"
        f"{analysis['health']}"
        "</div></div>"
    )

    if analysis.get("recommendations"):
        html += (
            "<div style='margin-top:24px; padding-top:12px; border-top:1px solid #222;'>"
            "<div style='color:#aaaaaa; font-size:13px;'>RECOMMENDED ACTIONS</div>"
        )
        for r in analysis["recommendations"]:
            html += (
                "<div style='margin-top:8px; "
                f"border-left:4px solid {accent}; "
                "padding:10px 12px; "
                "background:#141414; "
                "border-radius:6px; "
                "color:#dddddd;'>"
                f"• {r}</div>"
            )
        html += "</div>"

    html += "</div>"
    return html
# ---------------------------
# Smart advice engine (pattern-based)
# ---------------------------
def smart_advice(history):
    advice = []

    pm_avg = rolling_avg(history["pm25"])
    pm_peaks = peak_count(history["pm25"], 35)

    if pm_avg > 35:
        advice.append(
            "PM2.5 has remained elevated over time, indicating a continuous particle source rather than a brief event."
        )
    elif pm_peaks >= 3:
        advice.append(
            "Repeated PM2.5 spikes detected, often caused by cooking, candles, or intermittent airflow."
        )

    co2_avg = rolling_avg(history["co2"])
    if co2_avg > 1200:
        advice.append(
            "CO₂ has remained elevated over time, suggesting insufficient ventilation for current occupancy."
        )

    voc_peaks = peak_count([v for v in history["voc"] if isinstance(v, (int, float))], 2.0)
    if voc_peaks >= 3:
        advice.append(
            "Repeated VOC spikes detected, commonly linked to cleaners, fragrances, or off-gassing materials."
        )

    if sustained(history["co"], 9, ratio=0.3):
        advice.insert(
            0,
            "Carbon monoxide has appeared repeatedly; combustion appliances should be inspected even if levels fluctuate."
        )

    hum_avg = rolling_avg(history["humidity"])
    if hum_avg > 55:
        advice.append(
            "Humidity has stayed elevated over time, increasing the risk of mold growth."
        )
    elif hum_avg < 30:
        advice.append(
            "Humidity has remained low, which may worsen dryness and respiratory irritation."
        )

    return advice

# ---------------------------
# Base modal overlay & graphing
# ---------------------------
class IdleOverlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color:#0b0b0b;")
        self.hide()

        self.fact_index = 0
        self.logo_left = True

        # ---------- Layout ----------
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        self.logo = QtWidgets.QLabel()
        pix = QtGui.QPixmap("assets/logo.png").scaled(
            220, 220,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        self.logo.setPixmap(pix)
        self.logo.setAlignment(QtCore.Qt.AlignCenter)

        self.text = QtWidgets.QLabel("")
        self.text.setAlignment(QtCore.Qt.AlignCenter)
        self.text.setWordWrap(True)
        self.text.setStyleSheet(
            "font-size:22px; color:#dddddd; padding:0 60px;"
        )

        layout.addWidget(self.logo)
        layout.addSpacing(20)
        layout.addWidget(self.text)

        # ---------- Effects ----------
        self.text_fx = QtWidgets.QGraphicsOpacityEffect(self.text)
        self.text.setGraphicsEffect(self.text_fx)
        self.text_fx.setOpacity(1.0)

        # ---------- Data ----------
        self.facts = [
            "PM2.5 particles are small enough to enter the bloodstream.",
            "Poor ventilation can cause fatigue and headaches.",
            "Carbon monoxide is odorless and invisible.",
            "Ventilation and filtration solve different IAQ problems.",
            "Indoor air quality affects sleep and focus."
        ]
        self.text.setText(self.facts[0])

        # ---------- Timer ----------
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.next_fact)

    def start(self):
        self.show()
        self.raise_()
        self.timer.start(5000)

    def stop(self):
        self.timer.stop()
        self.hide()

    def next_fact(self):
        fade_out = QtCore.QPropertyAnimation(self.text_fx, b"opacity")
        fade_out.setDuration(600)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(self._swap)
        fade_out.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _swap(self):
        self.fact_index = (self.fact_index + 1) % len(self.facts)
        self.text.setText(self.facts[self.fact_index])

        fade_in = QtCore.QPropertyAnimation(self.text_fx, b"opacity")
        fade_in.setDuration(600)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def mousePressEvent(self, event):
        self.parent().exit_idle_mode()

class TrendGraph(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumHeight(90)

    def set_data(self, values):
        self.values = list(values)
        self.update()

    def paintEvent(self, event):
        if len(self.values) < 2:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        pad = 8

        vmin, vmax = 0, 100
        step_x = (w - pad * 2) / (len(self.values) - 1)

        path = QtGui.QPainterPath()
        for i, v in enumerate(self.values):
            x = pad + i * step_x
            y = h - pad - ((v - vmin) / (vmax - vmin)) * (h - pad * 2)
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)

        last = self.values[-1]
        color = "#4caf50" if last >= 80 else "#ff9800" if last >= 60 else "#f44336"

        pen = QtGui.QPen(QtGui.QColor(color), 3)
        painter.setPen(pen)
        painter.drawPath(path)
class DetailOverlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setStyleSheet("background-color:#0b0b0b; color:white;")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.hide()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        # Top bar
        top = QtWidgets.QHBoxLayout()

        logo = QtWidgets.QLabel()
        logo_pix = QtGui.QPixmap("assets/logo.png").scaled(
            80, 80,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        logo.setPixmap(logo_pix)
        top.addWidget(logo, alignment=QtCore.Qt.AlignLeft)

        self.title = QtWidgets.QLabel("")
        self.title.setStyleSheet("font-size:26px; font-weight:bold;")
        top.addWidget(self.title)
        top.addStretch()

        layout.addLayout(top)

        self.value = QtWidgets.QLabel("")
        # Score summary (created once)
        self.score_summary = QtWidgets.QLabel("")
        self.score_summary.setStyleSheet("font-size:18px; margin-bottom:6px;")
        layout.addWidget(self.score_summary)

        self.value.setStyleSheet("font-size:44px; font-weight:bold;")
        layout.addWidget(self.value)
        #disabled trend line (uncomment to activate) 
        #self.trend = TrendGraph()
        #layout.addWidget(self.trend)

        # Scrollable description area
        self.desc = QtWidgets.QLabel("")
        self.desc.setWordWrap(True)
        self.desc.setAlignment(QtCore.Qt.AlignTop)
        self.desc.setStyleSheet("font-size:16px; color:#cccccc;")
        self.desc.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.desc_container = QtWidgets.QWidget()
        desc_layout = QtWidgets.QVBoxLayout(self.desc_container)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.addWidget(self.desc)
        desc_layout.addStretch()

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.desc_container)

        QtWidgets.QScroller.grabGesture(
            self.scroll.viewport(),
            QtWidgets.QScroller.LeftMouseButtonGesture
        )

        layout.addWidget(self.scroll, stretch=1)




        back = QtWidgets.QPushButton("← Back")
        back.setFixedHeight(42)

        def _close_detail():
            self.current_key = None
            self.hide()

        back.clicked.connect(_close_detail)
        layout.addWidget(back)


        self.current_key = None
    def show_score_detail(self, score, breakdown, how_to):
        self.desc.clear()
        #trend line disabled below
        #self.trend.show()
        #self.trend.set_data(self.parent().score_history)

        self.current_key = "score"

        # --- SCORE HEADER BLOCK ---
        self.title.setText("IAQ Health Score")

        score_color = "#4caf50" if score >= 80 else "#ff9800" if score >= 60 else "#f44336"

        self.value.setText(f"{score}/100")
        if score >= 80:
            summary = "Healthy indoor air quality"
        elif score >= 60:
            summary = "Fair air quality — some improvements recommended"
        else:
            summary = "Poor air quality — action recommended"

        self.value.setStyleSheet(
            f"""
            font-size:64px;
            font-weight:800;
            color:{score_color};
            """
        )

        # Build breakdown text
        html = []
        html.append("<div style='font-size:16px; color:#cccccc;'>")

        # Section header
        html.append("<div style='font-size:20px; font-weight:600; color:white; margin-bottom:12px;'>Breakdown</div>")

        for item in breakdown:
            pts = item["points"]
            sign = "−" if pts < 0 else "+"
            color = item.get("color", "#888888")

            html.append(
                f"""
                <div style="
                    margin-bottom:10px;
                    padding:12px;
                    background:#151515;
                    border-left:6px solid {color};
                    border-radius:12px;
                ">
                    <div style="font-size:16px; font-weight:600; color:white;">
                        {item['metric']}
                    </div>
                    <div style="font-size:14px; color:{color}; font-weight:700;">
                        {sign}{abs(pts)} points
                    </div>
                    <div style="font-size:13px; color:#aaaaaa;">
                        {item['label']}
                    </div>
                </div>
                """
            )

        # How-to section
        if how_to:
            html.append("<div style='margin-top:18px; font-size:20px; font-weight:600; color:white;'>How to improve</div>")

            for h in how_to:
                html.append(
                    f"""
                    <div style="
                        margin-top:8px;
                        padding:12px;
                        background:#151515;
                        border-left:6px solid #3a7bd5;
                        border-radius:12px;
                        font-size:14px;
                        color:#dddddd;
                    ">
                        {h}
                    </div>
                    """
                )

        html.append("</div>")
        self.desc.setText("".join(html))
        self.show()



    def show_detail(self, key, title, value_text, color, description):
        #self.trend.hide()
        self.current_key = key
        self.title.setText(title)
        self.value.setText(value_text)
        self.value.setStyleSheet(
            f"font-size:56px; font-weight:bold; color:{color};"
        )
        self.desc.setText(description)
        self.show()
    def update_value(self, value_text, color=None):
        if not self.isVisible():
            return

        self.value.setText(value_text)

        if color:
            self.value.setStyleSheet(
                f"font-size:44px; font-weight:700; color:{color}; margin-bottom:6px;"
            )



# ---------------------------
# CO Danger Fullscreen Overlay
# ---------------------------
class CODangerOverlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setGeometry(0, 0, WIDTH, HEIGHT)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.flash_state = False
        self.flash_timer = QtCore.QTimer(self)
        self.flash_timer.timeout.connect(self._flash)

        self.hide()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(20)

        title = QtWidgets.QLabel("⚠️ CARBON MONOXIDE — THREAT TO LIFE")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("font-size:32px; font-weight:bold;")

        self.value = QtWidgets.QLabel("-- ppm")
        self.value.setAlignment(QtCore.Qt.AlignCenter)
        self.value.setStyleSheet("font-size:72px; font-weight:bold;")

        msg = QtWidgets.QLabel(
            "Dangerous carbon monoxide levels detected! Incapacitation likely! \n\n"
            "• Ventilate immediately\n"
            "• Shut off combustion sources\n"
            "• Evacuate if levels remain high"
        )
        msg.setAlignment(QtCore.Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size:20px;")

        dismiss = QtWidgets.QPushButton("Acknowledge / Dismiss")
        dismiss.setFixedHeight(50)
        dismiss.setStyleSheet("""
            QPushButton {
                background:#2a2a2a;
                color:white;
                font-size:18px;
                border-radius:12px;
            }
            QPushButton:pressed {
                background:#111;
            }
        """)
        dismiss.clicked.connect(self.dismiss)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(self.value)
        layout.addWidget(msg)
        layout.addStretch()
        layout.addWidget(dismiss)

    def show_level(self, co_ppm):
        self.value.setText(f"{co_ppm} ppm")
        self.show()
        self.raise_()
        self.flash_timer.start(500)  # flash every 500ms

    def _flash(self):
        self.flash_state = not self.flash_state
        color = "#8b0000" if self.flash_state else "#b00000"
        self.setStyleSheet(f"background-color:{color}; color:white;")

    def dismiss(self):
        """
        User acknowledgment.
        Real alarms will re-trigger automatically.
        """
        self.hide()
        self.flash_timer.stop()

        # Test mode exits permanently
        if self.parent.co_test_mode:
            self.parent.co_test_mode = False
            self.parent.test_co_btn.setText("Test CO Danger")


# ---------------------------
# Dashboard
# ---------------------------
class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # ---- SAFETY INIT (prevents race condition on fast user interaction) ----
        self.last_co2 = 0
        self.last_pm25 = 0
        self.last_voc = 0
        self.last_temp = 0
        self.last_humidity = 0
        self.last_co = 0
        self.co_test_mode = False
        # === ENABLE REAL SENSORS ===
        self.USE_REAL_SENSORS = True

        # ---------------------------
        # Survey mode state
        # ---------------------------
        self.survey_mode = False
        self.survey_meta = {
            "customer": None,
            "job_id": None,
            "start_ts": None,
        }
        # ---------------------------
        # Survey storage paths
        # ---------------------------
        self.base_path = Path.home() / ".howlx_scout"
        self.surveys_path = self.base_path / "surveys"
        self.surveys_path.mkdir(parents=True, exist_ok=True)
        
        self.last_score = 100
        self.last_breakdown = []
        self.last_how_to = []
        self.last_state = AlertState.NORMAL
        from collections import deque
        self.score_history = deque(maxlen=40)  # ~1 min rolling window\
        
        # Rolling history for smart advice (AdviceEngine) 
        self.history = {
            "pm25": deque(maxlen=40),
            "co2": deque(maxlen=40),
            "voc": deque(maxlen=40),
            "co": deque(maxlen=40),
            "humidity": deque(maxlen=40),
            "temp": deque(maxlen=40),
}
   


        # --------------------------------

        self.setWindowTitle("HowlX IAQ Scout")
        self.setFixedSize(WIDTH, HEIGHT)
        self.move(0, 0)
        self.setStyleSheet("background-color:#0d0d0d; color:white;")
        self.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)
        self.setContentsMargins(0, 0, 0, 0)


        # ---------------------------
        # Root layout (LEFT + RIGHT)
        # ---------------------------
        self.root = QtWidgets.QHBoxLayout(self)
        self.root.setContentsMargins(12, 12, 12, 12)
        self.root.setSpacing(12)

        # ===========================
        # LEFT INFO PANEL
        # ===========================
        self.left_panel = QtWidgets.QFrame()
        self.left_panel.setFixedWidth(260)
        self.left_panel.setStyleSheet(
            "background:#111111; border-radius:14px;"
        )

        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(14)

        # Logo (solid, visible)
        logo = QtWidgets.QLabel()
        logo_pix = QtGui.QPixmap("assets/logo.png").scaled(
            200, 200,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        logo.setPixmap(logo_pix)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.addWidget(logo)
        # State icon 
        self.state_icon = QtWidgets.QLabel("✓")
        self.state_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.state_icon.setStyleSheet("font-size:32px; color:#4caf50;")
        left_layout.addWidget(self.state_icon)


        
        # Dynamic info text (scrollable)
        self.info_text = QtWidgets.QLabel("")
        self.info_text.setWordWrap(True)
        self.info_text.setAlignment(QtCore.Qt.AlignTop)
        self.info_text.setStyleSheet("font-size:14px; color:#cccccc;")

        info_container = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.info_text)
        info_layout.addStretch()

        self.info_scroll = QtWidgets.QScrollArea()
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.info_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.info_scroll.setWidget(info_container)

        QtWidgets.QScroller.grabGesture(
            self.info_scroll.viewport(),
            QtWidgets.QScroller.LeftMouseButtonGesture
        )

        left_layout.addWidget(self.info_scroll, stretch=1)

        # ===========================
        # RIGHT GRID PANEL
        # ===========================
        grid_container = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(grid_container)
        self.grid.setSpacing(12)
        self.grid.setContentsMargins(0, 0, 0, 0)

        self.tiles = {}
        labels = [
             "CO (ppm)",
             "CO₂ (ppm)",
             "PM2.5 (µg/m³)",
             "VOC Index",
             "Temp (°F)",
             "Humidity (%)",
             "Score"
]


        for i, label in enumerate(labels):
            tile = self._build_tile(label)
            self.grid.addWidget(tile, i // 3, i % 3)
            self.tiles[label] = tile.findChild(QtWidgets.QLabel, "value")

        self.root.addWidget(grid_container)

        # ===========================
        # Overlay (detail screens)
        # ===========================
        self.detail = DetailOverlay(self)
        self.idle_overlay = IdleOverlay(self)
        # ===========================
        # CO danger overlay
        # ===========================
        self.co_danger = CODangerOverlay(self)
        # ===========================
        # Idle / Attract mode timer
        # ===========================
        self.idle_timer = QtCore.QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self.enter_idle_mode)

        self.reset_idle_timer()
        # ---------------------------
        # Update loop (SINGLE INSTANCE)
        # ---------------------------
        self.fact_index = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1500)
        self._flash = False

        self.idle_active = False

        # ===========================
        # Floating power menu
        # ===========================
        self.menu_open = False

        # Main power button
        self.power_btn = QtWidgets.QPushButton("⏻", self)
        self.power_btn.setFixedSize(44, 44)
        self.power_btn.move(WIDTH - 50, 6)
        self.power_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: white;
                border-radius: 22px;
                font-size: 20px;
            }
            QPushButton:pressed {
                background-color: #444;
            }
        """)
        self.power_btn.clicked.connect(self.toggle_power_menu)
        self.power_btn.raise_()

        # Dropdown menu container
        self.power_menu = QtWidgets.QFrame(self)
        self.power_menu.setGeometry(WIDTH - 190, 54, 180, 0)
        self.power_menu.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-radius: 12px;
            }
        """)
        self.power_menu.hide()
        self.power_menu.raise_()

        menu_layout = QtWidgets.QVBoxLayout(self.power_menu)
        menu_layout.setContentsMargins(10, 10, 10, 10)
        menu_layout.setSpacing(8)

        # Exit button
        exit_btn = QtWidgets.QPushButton("Exit to Desktop")
        exit_btn.setFixedHeight(36)
        exit_btn.setStyleSheet("""
            QPushButton {
                background:#2a2a2a;
                color:white;
                border-radius:8px;
                font-size:14px;
            }
            QPushButton:pressed {
                background:#aa0000;
            }
        """)
        exit_btn.clicked.connect(self.confirm_exit)
       
        # Test CO button
        self.test_co_btn = QtWidgets.QPushButton("Test CO Danger")
        self.test_co_btn.setFixedHeight(36)
        self.test_co_btn.setStyleSheet("""
            QPushButton {
                background:#2a2a2a;
                color:white;
                border-radius:8px;
                font-size:14px;
            }
            QPushButton:pressed {
                background:#ff9800;
            }
        """)
        self.test_co_btn.clicked.connect(self.toggle_co_test)

        menu_layout.addWidget(exit_btn)
        menu_layout.addWidget(self.test_co_btn)

        # click handler
        self.grid.itemAtPosition(0, 0).widget().mousePressEvent = lambda e: self.open_detail("co")
        self.grid.itemAtPosition(0, 1).widget().mousePressEvent = lambda e: self.open_detail("co2")
        self.grid.itemAtPosition(0, 2).widget().mousePressEvent = lambda e: self.open_detail("pm25")
        self.grid.itemAtPosition(1, 0).widget().mousePressEvent = lambda e: self.open_detail("voc")
        self.grid.itemAtPosition(1, 1).widget().mousePressEvent = lambda e: self.open_detail("temp")
        self.grid.itemAtPosition(1, 2).widget().mousePressEvent = lambda e: self.open_detail("humidity")
        self.grid.itemAtPosition(2, 0).widget().mousePressEvent = lambda e: self.open_detail("score")

    # ---------------------------
    # Survey sample writer
    # ---------------------------
    def _record_survey_sample(self, d, score, state):
        if not self.survey_meta["customer"] or not self.survey_meta["job_id"]:
            return

        job_path = (
            self.surveys_path
            / self.survey_meta["customer"]
            / self.survey_meta["job_id"]
        )
        job_path.mkdir(parents=True, exist_ok=True)

        data_file = job_path / "readings.csv"

        header = "timestamp,co,co2,pm25,voc,temp,humidity,score,state\n"

        row = (
            f"{int(time.time())},"
            f"{d['co']},{d['co2']},{d['pm25']},"
            f"{'' if d.get('voc') is None else d['voc']},{d['temp']},{d['humidity']},"
            f"{score},{state.name}\n"
        )

        if not data_file.exists():
            data_file.write_text(header)

        with data_file.open("a") as f:
            f.write(row)

    # ---------------------------
    # Exit confirmation
    # ---------------------------
    def confirm_exit(self):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Exit HowlX Scout")
        dlg.setText("Exit to desktop?")
        dlg.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        dlg.setDefaultButton(QtWidgets.QMessageBox.No)
        dlg.setStyleSheet("""
            QMessageBox {
                background-color: #0d0d0d;
                color: white;
                font-size: 16px;
            }
            QPushButton {
                padding: 10px 18px;
                font-size: 14px;
            }
        """)

        if dlg.exec_() == QtWidgets.QMessageBox.Yes:
            QtWidgets.QApplication.quit()

    # ---------------------------
    # Power menu toggle
    # ---------------------------
    def toggle_power_menu(self):
        if self.menu_open:
            self.power_menu.hide()
            self.menu_open = False
        else:
            self.power_menu.setFixedHeight(96)
            self.power_menu.show()
            self.menu_open = True

    # ---------------------------
    # CO danger test toggle
    # ---------------------------
    def toggle_co_test(self):
        if self.co_test_mode:
            # Stop test mode
            self.co_test_mode = False
            self.co_danger.hide()
            self.test_co_btn.setText("Test CO Danger")
        else:
            # Start test mode
            self.co_test_mode = True
            self.last_co = 50  # forced dangerous value
            self.co_danger.show_level(self.last_co)
            self.test_co_btn.setText("Stop CO Test")

    # ---------------------------
    # Tile builder
    # ---------------------------
    def _build_tile(self, label):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet(
            "background:#1a1a1a; border-radius:14px;"
        )

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        # --- TITLE ROW (label + status dot) ---
        title_row = QtWidgets.QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        title = QtWidgets.QLabel(label)
        title.setStyleSheet("font-size:16px; color:#aaaaaa;")

        status = QtWidgets.QLabel("●")
        status.setObjectName("status")
        status.setStyleSheet("font-size:16px; color:#f44336;")  # default red

        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(status)

        layout.addLayout(title_row)

        # --- VALUE ---
        value = QtWidgets.QLabel("--")
        value.setObjectName("value")
        value.setStyleSheet("font-size:38px; font-weight:bold;")

        # --- BADGE ---
        badge = QtWidgets.QLabel("")
        badge.setObjectName("badge")
        badge.setStyleSheet("font-size:14px; color:#888888;")

        layout.addWidget(value)
        layout.addWidget(badge)
        layout.addStretch()

        return frame

    # ---------------------------
    # Left Panel UI 
    # ---------------------------

    def update_left_panel_context(self, d, score, state, how_to):
        lines = []

        if state == AlertState.CRITICAL:
            lines.append("⛔ Immediate action recommended.")
        elif state == AlertState.WARNING:
            lines.append("⚠ Air quality needs attention.")
        else:
            lines.append("✓ Air quality looks good.")

        co  = nval(d.get("co"), 0.0)
        pm  = nval(d.get("pm25"), 0.0)
        co2 = nval(d.get("co2"), 450)
        voc = nval(d.get("voc"), 0.0)

        drivers = []
        if installed_state("co") and co >= 9:
            drivers.append(f"CO {co} ppm")
        if installed_state("pm25") and pm > 12:
            drivers.append(f"PM2.5 {pm} µg/m³")
        if installed_state("scd41") and co2 > 800:
            drivers.append(f"CO₂ {co2} ppm")
        if installed_state("bme688") and d.get("voc") is not None and voc > 1.0:
            drivers.append(f"VOC {voc}")

        if drivers:
            lines.append("Drivers: " + " · ".join(drivers[:2]))

        lines.append(f"IAQ Score: {score}/100")

        suggestions = []
        for s in (how_to or []):
            s = (s or "").strip()
            if s and s not in suggestions:
                suggestions.append(s)
        suggestions = suggestions[:3]

        lines.append("")
        lines.append("Suggestions:")
        if suggestions:
            for s in suggestions:
                lines.append(f"• {s}")
        else:
            lines.append("• Keep monitoring. No changes recommended right now.")

        self.info_text.setText("\n".join(lines))



    # ---------------------------
    # Alert state UI
    # ---------------------------
    def update_alert_state_ui(self):
        if self.last_state == AlertState.CRITICAL:
            self.state_icon.setText("⛔")
            self.state_icon.setStyleSheet("font-size:32px; color:#f44336;")

        elif self.last_state == AlertState.WARNING:
            self.state_icon.setText("⚠")
            self.state_icon.setStyleSheet("font-size:32px; color:#ff9800;")

        else:
            self.state_icon.setText("✓")
            self.state_icon.setStyleSheet("font-size:32px; color:#4caf50;")

    # ---------------------------
    # Data update
    # ---------------------------
    def safe_readings(self):
        if not getattr(self, "USE_REAL_SENSORS", False):
            return mock_readings()
        try:
            return read_sensors()
        except Exception as e:
            print("read_sensors() failed:", repr(e))
            return mock_readings()

    def update_data(self):
        d = self.safe_readings()
        self._flash = not self._flash  # toggles each tick for warmup flashing


        # NEW unified evaluation
        s, breakdown, how_to, state = evaluate_readings(d, self.history)
        if installed_state("pm25") and d.get("pm25") is not None:
            self.last_pm25_analysis = analyze_pm25(d["pm25"], list(self.history["pm25"]))
        else:
            self.last_pm25_analysis = None


        # Pattern-based smart advice
        pattern_advice = smart_advice(self.history)
        for msg in pattern_advice:
            if msg not in how_to:
                how_to.append(msg)


        # Store for later use (score detail, advice engine, alerts)
        self.last_score = s
        self.score_history.append(s)
        self.last_breakdown = breakdown
        self.last_how_to = how_to
        self.last_state = state
        self.update_alert_state_ui()


        self.tiles["CO₂ (ppm)"].setText("--" if d.get("co2") is None else str(d["co2"]))
        self.tiles["PM2.5 (µg/m³)"].setText("--" if d.get("pm25") is None else str(d["pm25"]))
        self.tiles["VOC Index"].setText("--" if d.get("voc") is None else str(d["voc"]))
        self.tiles["Temp (°F)"].setText(str(d["temp"]))
        self.tiles["Humidity (%)"].setText(str(d["humidity"]))
        self.tiles["Score"].setText(f"{s}/100")
        self.tiles["CO (ppm)"].setText("--" if d.get("co") is None else str(d["co"]))

        

        self.last_co2 = d.get("co2")
        if self.last_co2 is None:
            self.last_co2 = 450  # only for analysis funcs, not UI display
        self.last_pm25 = d["pm25"]
        self.last_voc = d.get("voc")
        self.last_temp = d["temp"]
        self.last_humidity = d["humidity"]
        self.last_co = d.get("co")
        # ---------------------------
        # Survey mode data capture
        # ---------------------------
        if self.survey_mode:
            self._record_survey_sample(d, s, state)

        # Update rolling history
        for k in self.history:
            val = d.get(k)
            if val is None:
                continue
            self.history[k].append(val)


        # Auto-trigger CO danger overlay (skip if test mode)
        if not self.co_test_mode:
            co_val = d.get("co")  # use the fresh reading directly
            if isinstance(co_val, (int, float)) and co_val >= CO_DANGER_THRESHOLD:
                self.co_danger.show_level(co_val)
            elif self.co_danger.isVisible():
                self.co_danger.hide()


        # --- Live detail refresh (single source of truth) ---
        if self.detail.isVisible() and self.detail.current_key:
            self.open_detail(self.detail.current_key)




        # ---------------------------
        # Severity-based tile coloring
        # ---------------------------

        # CO2 + humidity are always present in your current design
        co2_label, co2_color, _ = co2_severity(self.last_co2)
        hum_label, hum_color, _ = humidity_severity(self.last_humidity)

        # PM2.5 may be None (not installed yet)
        if self.last_pm25 is None:
            pm_label, pm_color = "Not installed", "#888888"
        else:
            pm_label, pm_color, _ = pm25_severity(self.last_pm25)

        # CO may be None (not installed yet)
        if self.last_co is None:
            co_label, co_color = "Not installed", "#888888"
        else:
            co_label, co_color, _ = co_severity(self.last_co)


        # Left-panel contextual suggestions 
        self.update_left_panel_context(d, s, state, how_to)
        
        # Status dots (availability)
        self.set_tile_status("CO₂ (ppm)", SENSOR_STATUS["scd41"])
        self.set_tile_status("Temp (°F)", SENSOR_STATUS["bme688"])
        self.set_tile_status("Humidity (%)", SENSOR_STATUS["bme688"])

        # VOC uses BME688 gas proxy (warmup until ready)
        self.set_tile_status("VOC Index", SENSOR_STATUS["bme688"])

        # Not installed yet
        self.set_tile_status("PM2.5 (µg/m³)", SENSOR_STATUS["pm25"])
        self.set_tile_status("CO (ppm)", SENSOR_STATUS["co"])

        # Score depends on “overall”
        overall = SensorState.READY if (SENSOR_STATUS["scd41"] == SensorState.READY and SENSOR_STATUS["bme688"] in (SensorState.WARMUP, SensorState.READY)) else SensorState.WARMUP
        if (SENSOR_STATUS["scd41"] in (SensorState.MISSING, SensorState.ERROR)) and (SENSOR_STATUS["bme688"] in (SensorState.MISSING, SensorState.ERROR)):
            overall = SensorState.ERROR
        self.set_tile_status("Score", overall)

    # ---------------------------
    # Sensor State Helper
    # ---------------------------
    def set_tile_status(self, label, state: SensorState):
        dot = self.tiles[label].parent().findChild(QtWidgets.QLabel, "status")
        if not dot:
            return

        if state in (SensorState.MISSING, SensorState.ERROR):
            dot.setStyleSheet("font-size:16px; color:#f44336;")  # red
        elif state == SensorState.READY:
            dot.setStyleSheet("font-size:16px; color:#4caf50;")  # green
        else:
            # WARMUP or STALE -> flashing yellow
            color = "#ffeb3b" if self._flash else "#b59b00"
            dot.setStyleSheet(f"font-size:16px; color:{color};")


    # ---------------------------
    # Idle mode helpers
    # ---------------------------
    def reset_idle_timer(self):
        # Never idle over critical overlays
        if self.detail.isVisible() or self.co_danger.isVisible():
            return
        self.idle_timer.start(30000)  # 30 seconds (tune later)

    def enter_idle_mode(self):
        if self.idle_active:
            return
        if self.detail.isVisible() or self.co_danger.isVisible():
            return
        self.idle_active = True
        self.idle_overlay.start()

    def exit_idle_mode(self):
        if not self.idle_active:
            return
        self.idle_active = False
        self.idle_overlay.stop()
        self.reset_idle_timer()
    # ---------------------------
    # Tile actions
    # ---------------------------
    def open_detail(self, key):
        self.reset_idle_timer()

        if key == "pm25":
            # --- SAFE HANDLING WHEN SENSOR NOT INSTALLED ---
            if self.last_pm25 is None:
                self.detail.show_detail(
                    key="pm25",
                    title="PM2.5 — Fine Particulate Matter",
                    value_text="--",
                    color="#888888",
                    description=render_analysis_detail(
                        {
                            "status": "Not installed",
                            "confidence": "—",
                            "summary": "PM2.5 sensor is not installed yet.",
                            "health": "No PM2.5 measurement available.",
                            "recommendations": ["Install a PM2.5 sensor to enable particulate monitoring."],
                            "window": "—",
                        },
                        accent="#ff9800",
                    ),
                )
                return

            analysis = analyze_pm25(self.last_pm25, list(self.history["pm25"]))
            _, pm_color, _ = pm25_severity(self.last_pm25)

            self.detail.show_detail(
                key="pm25",
                title="PM2.5 — Fine Particulate Matter",
                value_text=f"{self.last_pm25} µg/m³",
                color=pm_color,
                description=render_analysis_detail(analysis, accent="#ff9800"),
            )

        elif key == "co2":
            analysis = analyze_co2(self.last_co2, list(self.history["co2"]))
            _, co2_color, _ = co2_severity(self.last_co2)

            self.detail.show_detail(
                key="co2",
                title="CO₂ — Carbon Dioxide",
                value_text=f"{self.last_co2} ppm",
                color=co2_color,
                description=render_analysis_detail(analysis, accent="#03a9f4"),
            )

        elif key == "voc":
            # Handle warmup/None VOC safely
            voc_current = self.last_voc
            voc_for_analysis = voc_current if voc_current is not None else 0.0

            analysis = analyze_voc(voc_for_analysis, list(self.history["voc"]))

            if voc_current is None:
                voc_color = "#888888"
                value_text = "--"
            else:
                if voc_current <= 1.0:
                    voc_color = "#4caf50"
                elif voc_current <= 2.0:
                    voc_color = "#ff9800"
                else:
                    voc_color = "#f44336"
                value_text = str(voc_current)

            self.detail.show_detail(
                key="voc",
                title="VOC — Volatile Organic Compounds",
                value_text=value_text,
                color=voc_color,
                description=render_analysis_detail(analysis, accent="#9c27b0"),
            )

        elif key == "temp":
            analysis = analyze_temp(self.last_temp, list(self.history["temp"]))
            self.detail.show_detail(
                key="temp",
                title="Temperature",
                value_text=f"{self.last_temp} °F",
                color="#03a9f4",
                description=render_analysis_detail(analysis, accent="#03a9f4"),
            )

        elif key == "humidity":
            analysis = analyze_humidity(self.last_humidity, list(self.history["humidity"]))
            _, color, _ = humidity_severity(self.last_humidity)
            self.detail.show_detail(
                key="humidity",
                title="Relative Humidity",
                value_text=f"{self.last_humidity} %",
                color=color,
                description=render_analysis_detail(analysis, accent="#00bcd4"),
            )

        elif key == "co":
            # --- SAFE HANDLING WHEN SENSOR NOT INSTALLED ---
            if self.last_co is None:
                self.detail.show_detail(
                    key="co",
                    title="Carbon Monoxide",
                    value_text="--",
                    color="#888888",
                    description=render_analysis_detail(
                        {
                            "status": "Not installed",
                            "confidence": "—",
                            "summary": "CO sensor is not installed yet.",
                            "health": "No carbon monoxide measurement available.",
                            "recommendations": ["Install a CO sensor to enable safety monitoring."],
                            "window": "—",
                        },
                        accent="#f44336",
                    ),
                )
                return

            analysis = analyze_co(self.last_co, list(self.history["co"]))
            _, color, _ = co_severity(self.last_co)

            self.detail.show_detail(
                key="co",
                title="Carbon Monoxide",
                value_text=f"{self.last_co} ppm",
                color=color,
                description=render_analysis_detail(analysis, accent="#f44336"),
            )

        elif key == "score":
            self.detail.show_score_detail(
                score=self.last_score,
                breakdown=self.last_breakdown,
                how_to=self.last_how_to,
            )


# ---------------------------
# App start
# ---------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    w = Dashboard()
    w.show()
    sys.exit(app.exec_())

