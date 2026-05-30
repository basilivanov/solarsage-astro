# AI_HEADER
# module: M-SIDECAR-CALCULATOR
# wave: W-3.2, W-3.3
# purpose: Astrological calculations via pyswisseph

import swisseph as swe
from datetime import datetime
from zoneinfo import ZoneInfo

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
    """Get zodiac sign from longitude."""
    return SIGNS[int(longitude / 30) % 12]


def calculate_julian_day(date_str: str, time_str: str, tz_str: str) -> float:
    """Calculate Julian Day from date/time/timezone."""
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


def calculate_planets(jd: float) -> list[dict]:
    """Calculate planet positions."""
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


def calculate_transits(jd: float) -> list[dict]:
    """
    Calculate transit planets for a given Julian Day.

    W-3.3: Same as calculate_planets, but for transits context.
    """
    return calculate_planets(jd)


def calculate_houses(jd: float, lat: float, lon: float) -> tuple[list[dict], list[dict], str]:
    """
    Calculate houses and special points.

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


def probe_calculation() -> bool:
    """
    Probe calculation for health check.

    Calculate SUN position on now.
    Returns True if successful, False otherwise.
    """
    try:
        jd = swe.julday(2026, 5, 30, 12.0)  # Fixed date for probe
        result = swe.calc_ut(jd, swe.SUN)
        lon = result[0][0]

        # Check that longitude is reasonable (0-360)
        return 0 <= lon <= 360
    except Exception:
        return False
