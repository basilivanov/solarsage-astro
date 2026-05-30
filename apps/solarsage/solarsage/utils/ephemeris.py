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
        })

    return planets


def calculate_houses_cusps(jd: float, lat: float, lon: float) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Calculate houses and special points.

    W-SOLARSAGE-SVC: Centralized house calculation.

    Returns:
        (houses, special_points, house_system_name)
    """
    # Use Placidus house system (or Whole Sign for high latitudes)
    house_system = b'P'  # Placidus

    # Check if high latitude (>= 60 deg)
    if abs(lat) >= 60:
        house_system = b'W'  # Whole Sign

    # Calculate houses
    cusps, ascmc = swe.houses(jd, lat, lon, house_system)

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

    house_system_name = "PLACIDUS" if house_system == b'P' else "WHOLE_SIGN"

    return houses, special_points, house_system_name
