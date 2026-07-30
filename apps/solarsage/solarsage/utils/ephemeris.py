
# ############################################################################
# AI_HEADER: MODULE_UTILS_EPHEMERIS — ephemeris calculation utilities.
# ROLE: Provides Swiss Ephemeris calculations, Julian Day converters, and date/time formatters.
# DEPENDENCIES: swisseph, datetime, zoneinfo, typing
# ############################################################################

# START_MODULE_CONTRACT: M-SOLARSAGE-EPHEMERIS-UTILS
# purpose: Ephemeris calculation utilities.
# owns:
#   - apps/solarsage/solarsage/utils/ephemeris.py
# inputs: date, time, timezone, JD.
# outputs: Julian Day, planetary positions, geometric solar altitude, house
#   cusps, UTC ISO formatted timestamps.
# dependencies: swisseph, zoneinfo, datetime.
# side_effects: none (pure ephemeris computation).
# emitted_logs: none.
# invariants:
#   - julian_day_to_utc_iso converts JD to UTC ISO string with 'Z' suffix up to seconds precision.
#   - calculate_solar_altitude is geometric and independent of house system.
# failure_policy: propagates ValueError or swisseph errors.
# END_MODULE_CONTRACT: M-SOLARSAGE-EPHEMERIS-UTILS

# START_MODULE_MAP: M-SOLARSAGE-EPHEMERIS-UTILS
# public_entrypoints:
#   - get_sign
#   - calculate_julian_day
#   - calculate_positions
#   - calculate_solar_altitude
#   - calculate_houses_cusps
#   - julian_day_to_utc_iso
# semantic_blocks:
#   - EPHEMERIS_HELPERS: sign, JD and positions calculators.
#   - FORMATTERS: UTC ISO formatters.
# owned_tests:
#   - apps/solarsage/tests/test_geometric_sect.py
# END_MODULE_MAP: M-SOLARSAGE-EPHEMERIS-UTILS

import swisseph as swe
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Any

from ..core.ephemeris_runtime import calc_ut_checked, get_ephe_path


def _ensure_configured() -> None:
    # Lazy single-owner configuration: verification runs at first actual
    # calculation (or at the FastAPI startup gate), never at module import.
    get_ephe_path()


PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


# START_BLOCK: EPHEMERIS_HELPERS
def get_sign(longitude: float) -> str:
    """
    Get zodiac sign from longitude.

    W-SOLARSAGE-SVC: Centralized sign calculation.
    """
    return SIGNS[int(longitude / 30) % 12]


def calculate_julian_day(date_str: str, time_str: str, tz_str: str) -> float:
    """
    Calculate Julian Day from date/time/timezone.

    W-SOLARSAGE-SVC: Centralized JD calculation.
    """
    # Parse date and time
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    # Apply timezone
    tz = ZoneInfo(tz_str)
    dt_tz = dt.replace(tzinfo=tz)

    # Convert to UTC
    dt_utc = dt_tz.astimezone(ZoneInfo("UTC"))

    # Calculate Julian Day
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0
    )

    return jd


def calculate_positions(jd: float) -> List[Dict[str, Any]]:
    """
    Calculate planetary positions for given Julian Day.

    W-SOLARSAGE-SVC: Centralized ephemeris calculations.
    """
    _ensure_configured()
    planets = []

    for name, planet_id in PLANETS.items():
        result = calc_ut_checked(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
        lon, lat, dist, speed_lon, speed_lat, speed_dist = result[0]

        planets.append({
            "name": name,
            "longitude": lon,
            "latitude": lat,
            "speed": speed_lon,
            "sign": get_sign(lon),
            "retrograde": bool(speed_lon < 0),
        })

    return planets


# START_FUNCTION_CONTRACT: F-M-SOLARSAGE-EPHEMERIS-UTILS.calculate_solar_altitude
# purpose: Calculate the geometric altitude of the Sun centre above the local
#   astronomical horizon for a Julian day and terrestrial coordinates.
# inputs: jd - Julian day UT; lat/lon - geographic degrees.
# returns: float - true (unrefracted) solar altitude in degrees.
# side_effects: reads the configured Swiss Ephemeris artifact on first call.
# emitted_logs: none.
# error_behavior: raises ValueError for invalid coordinates and propagates
#   ephemeris runtime errors fail-closed.
# END_FUNCTION_CONTRACT: F-M-SOLARSAGE-EPHEMERIS-UTILS.calculate_solar_altitude
def calculate_solar_altitude(jd: float, lat: float, lon: float) -> float:
    """Return true solar altitude; positive means the Sun is above horizon."""
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"Latitude outside [-90, 90]: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"Longitude outside [-180, 180]: {lon}")

    solar_position, _ = calc_ut_checked(
        jd,
        swe.SUN,
        swe.FLG_SWIEPH | swe.FLG_SPEED,
    )
    _azimuth, true_altitude, _apparent_altitude = swe.azalt(
        jd,
        swe.ECL2HOR,
        (lon, lat, 0.0),
        0.0,
        0.0,
        solar_position[:3],
    )
    return float(true_altitude)


def calculate_houses_cusps(
    jd: float,
    lat: float,
    lon: float,
    house_system: str = "PLACIDUS",
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Calculate houses and special points.

    W-SOLARSAGE-SVC: Centralized house calculation.

    Supported house systems:
      - PLACIDUS -> Swiss Ephemeris 'P'
      - WHOLE_SIGN -> Swiss Ephemeris 'W'

    High-latitude resolution: if abs(lat) >= 60 and requested house_system is
    PLACIDUS, resolved to WHOLE_SIGN.

    Args:
        jd: Julian Day
        lat: Latitude
        lon: Longitude
        house_system: Requested house system ("PLACIDUS" or "WHOLE_SIGN")

    Returns:
        (houses, special_points, resolved_house_system_name)

    Raises:
        ValueError: if house_system is not supported
    """
    _ensure_configured()
    # Map requested house system to Swiss Ephemeris code
    hs_upper = house_system.upper().strip()
    if hs_upper == "PLACIDUS":
        requested_code = b'P'
    elif hs_upper == "WHOLE_SIGN":
        requested_code = b'W'
    else:
        raise ValueError(f"Unsupported house system: '{house_system}'. Supported: PLACIDUS, WHOLE_SIGN")

    # High-latitude override: if PLACIDUS requested but lat >= 60, use WHOLE_SIGN
    resolved_code = requested_code
    resolved_name = hs_upper
    if requested_code == b'P' and abs(lat) >= 60:
        resolved_code = b'W'
        resolved_name = "WHOLE_SIGN"

    # Calculate houses
    cusps, ascmc = swe.houses(jd, lat, lon, resolved_code)

    # Houses (12 cusps)
    houses = []
    for i, cusp in enumerate(cusps, start=1):
        houses.append({
            "number": i,
            "cusp": cusp,
            "sign": get_sign(cusp),
        })

    # Special points (ASC, MC, ARMC, Vertex, etc)
    special_points = [
        {"name": "ASC", "longitude": ascmc[0], "sign": get_sign(ascmc[0])},
        {"name": "MC", "longitude": ascmc[1], "sign": get_sign(ascmc[1])},
        {"name": "ARMC", "longitude": ascmc[2], "sign": get_sign(ascmc[2])},
        {"name": "Vertex", "longitude": ascmc[3], "sign": get_sign(ascmc[3])},
    ]

    return houses, special_points, resolved_name
# END_BLOCK: EPHEMERIS_HELPERS

# START_BLOCK: FORMATTERS
# START_FUNCTION_CONTRACT: F-M-SOLARSAGE-EPHEMERIS-UTILS.julian_day_to_utc_iso
# purpose: Convert Julian Day to UTC ISO-Z string with second precision.
# inputs: jd - Julian Day float.
# returns: str - ISO YYYY-MM-DDTHH:MM:SSZ format.
# side_effects: none.
# emitted_logs: none.
# error_behavior: propagates ValueError.
# END_FUNCTION_CONTRACT: F-M-SOLARSAGE-EPHEMERIS-UTILS.julian_day_to_utc_iso
def julian_day_to_utc_iso(jd: float) -> str:
    unix_seconds = (jd - 2440587.5) * 86400.0
    dt = datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")
# END_BLOCK: FORMATTERS
