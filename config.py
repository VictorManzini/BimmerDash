# Sensor metadata + default display config for BimmerDash.
# gmin/gmax = gauge sweep range; low/high = danger thresholds (None = no limit).

GAUGE_TYPES = ["Circular", "Arc", "Bar", "Digital"]

SENSORS = {
    "turbo":        {"label": "Turbo",      "attr": "turbo_pressure",           "src": "engine",  "gmin": 0.0,  "gmax": 2.0,  "low": None, "high": None, "unit": "bar",  "dec": 1},
    "rpm":          {"label": "RPM",        "attr": "rpm",                      "src": "engine",  "gmin": 0,    "gmax": 7000, "low": None, "high": 5000, "unit": "",     "dec": 0},
    "oil":          {"label": "Oil Temp",   "attr": "oil_temp",                 "src": "engine",  "gmin": 40,   "gmax": 120,  "low": None, "high": 115,  "unit": "C",    "dec": 0},
    "water":        {"label": "Water Temp", "attr": "water_temperature",        "src": "engine",  "gmin": 40,   "gmax": 120,  "low": None, "high": 110,  "unit": "C",    "dec": 0},
    "transmission": {"label": "Trans Temp", "attr": "transmission_temperature", "src": "engine",  "gmin": 60,   "gmax": 120,  "low": None, "high": 96,   "unit": "C",    "dec": 0},
    "fuel":         {"label": "Fuel",       "attr": "fuel_consumption",         "src": "engine",  "gmin": 0,    "gmax": 15,   "low": None, "high": None, "unit": "km/L", "dec": 1},
    "speed":        {"label": "Speed",      "attr": "speed",                    "src": "vehicle", "gmin": 0,    "gmax": 260,  "low": None, "high": None, "unit": "km/h", "dec": 0},
    "voltage":      {"label": "Voltage",    "attr": "battery_voltage",          "src": "vehicle", "gmin": 10.0, "gmax": 15.0, "low": 11.8, "high": None, "unit": "V",    "dec": 1},
}

MAX_SENSORS = 6
DEFAULT_GAUGE = "Circular"
DEFAULT_SENSORS = ["rpm", "speed", "water", "oil", "turbo", "voltage"]  # up to MAX_SENSORS
