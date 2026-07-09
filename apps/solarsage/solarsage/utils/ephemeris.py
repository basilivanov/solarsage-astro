
# ############################################################################
# AI_HEADER: MODULE_UTILS_EPHEMERIS
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: ephemeris.py
# owns:
#   - apps/solarsage/solarsage/utils/ephemeris.py
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-SOLARSAGE-EPHEMERIS-UTILS
# wave: W-SOLARSAGE-SVC
# purpose: Ephemeris calculation utilities

import swisseph as swe
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Any

from ..core.config import settings


# Initialize Swiss Ephemeris
swe.set_ephe_path(settings.ephemeris_path)


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
    planets = []

    for name, planet_id in PLANETS.items():
        result = swe.calc_ut(jd, planet_id)
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
