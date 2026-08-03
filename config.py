# Sensor metadata + default display config for BimmerDash.
# gmin/gmax = gauge sweep range; low/high = danger thresholds (None = no limit).

import json
from pathlib import Path

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

# --- display units -----------------------------------------------------
# Sensor values stay in their base unit (C, km/h) everywhere upstream; these
# prefs only control how ui.py formats them on screen.

TEMP_UNITS = ["C", "F"]
SPEED_UNITS = ["km/h", "mph"]
UNIT_PREFS = {"temp": "C", "speed": "km/h"}


# --- saved layouts ---------------------------------------------------------
# One file per drive mode holds that mode's dashboard; settings.json remembers
# which mode to boot into, so the gauges come up already in position.

SETTINGS_DIR = Path(__file__).parent / "settings"
SETTINGS_FILE = "settings.json"
THRESHOLDS_FILE = "thresholds.json"
MODE_FILES = {
    "Comfort": "comfort.json",
    "Sport": "sport.json",
    "Sport+": "sport_plus.json",
    "ECO PRO": "eco_pro.json",
}


def _read(name, default):
    # ponytail: a corrupt/missing file just falls back to defaults, no repair pass
    try:
        return json.loads((SETTINGS_DIR / name).read_text())
    except (OSError, ValueError):
        return default


def load_layout(mode):
    """(selected, gauge_types) for a drive mode. Unknown keys/types are dropped."""
    saved = _read(MODE_FILES.get(mode, ""), {}) if mode in MODE_FILES else {}
    types = saved.get("gauge_types") or {}
    selected = [k for k in saved.get("selected") or DEFAULT_SENSORS if k in SENSORS][:MAX_SENSORS]
    gauges = {k: (types.get(k) if types.get(k) in GAUGE_TYPES else DEFAULT_GAUGE) for k in SENSORS}
    return selected, gauges


def save_layout(mode, selected, gauge_types):
    """Write this mode's dashboard and remember it as the boot mode."""
    SETTINGS_DIR.mkdir(exist_ok=True)
    if mode in MODE_FILES:
        (SETTINGS_DIR / MODE_FILES[mode]).write_text(json.dumps(
            {"selected": selected, "gauge_types": {k: gauge_types[k] for k in selected}}, indent=2))
    (SETTINGS_DIR / SETTINGS_FILE).write_text(json.dumps({"boot_mode": mode}, indent=2))


def boot_mode():
    m = _read(SETTINGS_FILE, {}).get("boot_mode")
    return m if m in MODE_FILES else "Comfort"


# --- redline thresholds ------------------------------------------------
# Personalized low/high danger values, overriding the SENSORS defaults above.

def load_thresholds():
    """Apply any saved low/high overrides onto SENSORS, in place."""
    for k, v in _read(THRESHOLDS_FILE, {}).items():
        if k in SENSORS:
            SENSORS[k]["low"] = v.get("low", SENSORS[k]["low"])
            SENSORS[k]["high"] = v.get("high", SENSORS[k]["high"])


def save_thresholds():
    SETTINGS_DIR.mkdir(exist_ok=True)
    data = {k: {"low": m["low"], "high": m["high"]} for k, m in SENSORS.items()}
    (SETTINGS_DIR / THRESHOLDS_FILE).write_text(json.dumps(data, indent=2))


UNITS_FILE = "units.json"


def load_units():
    """Apply any saved temp/speed unit prefs onto UNIT_PREFS, in place."""
    saved = _read(UNITS_FILE, {})
    if saved.get("temp") in TEMP_UNITS:
        UNIT_PREFS["temp"] = saved["temp"]
    if saved.get("speed") in SPEED_UNITS:
        UNIT_PREFS["speed"] = saved["speed"]


def save_units():
    SETTINGS_DIR.mkdir(exist_ok=True)
    (SETTINGS_DIR / UNITS_FILE).write_text(json.dumps(UNIT_PREFS, indent=2))


if __name__ == "__main__":  # ponytail: round-trip check against a throwaway dir
    import tempfile

    for mode in MODE_FILES:                      # shipped files must all be valid
        sel, g = load_layout(mode)
        assert sel and set(sel) <= set(SENSORS) and len(sel) <= MAX_SENSORS, mode
        assert set(g[k] for k in sel) <= set(GAUGE_TYPES), mode
    assert boot_mode() in MODE_FILES

    with tempfile.TemporaryDirectory() as tmp:
        SETTINGS_DIR = Path(tmp)
        save_layout("Sport+", ["rpm", "turbo"], {"rpm": "Bar", "turbo": "Digital"})
        assert load_layout("Sport+")[0] == ["rpm", "turbo"]
        assert load_layout("Sport+")[1]["rpm"] == "Bar"
        assert boot_mode() == "Sport+"
        assert load_layout("Comfort")[0] == DEFAULT_SENSORS      # missing file -> defaults
        (Path(tmp) / "sport.json").write_text("{ not json")
        assert load_layout("Sport")[0] == DEFAULT_SENSORS        # corrupt file -> defaults

        old_high = SENSORS["oil"]["high"]
        SENSORS["oil"]["high"] = 111
        save_thresholds()
        SENSORS["oil"]["high"] = old_high                        # simulate a fresh process
        load_thresholds()
        assert SENSORS["oil"]["high"] == 111

        UNIT_PREFS["temp"], UNIT_PREFS["speed"] = "F", "mph"
        save_units()
        UNIT_PREFS["temp"], UNIT_PREFS["speed"] = "C", "km/h"     # simulate a fresh process
        load_units()
        assert UNIT_PREFS == {"temp": "F", "speed": "mph"}
        (Path(tmp) / "units.json").write_text("{ not json")
        UNIT_PREFS["temp"], UNIT_PREFS["speed"] = "C", "km/h"
        load_units()                                              # corrupt file -> unchanged
        assert UNIT_PREFS == {"temp": "C", "speed": "km/h"}
    print("config self-check ok")
