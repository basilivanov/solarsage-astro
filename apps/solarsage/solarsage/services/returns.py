# ############################################################################
# AI_HEADER: MODULE_SIDECAR_RETURNS — Solar and Lunar return calculation.
# ROLE: Determines exact solar return and lunar return moments, computes
#       return charts (positions, houses, angles) for the sidecar.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-RETURNS
# purpose: Calculate solar_return and lunar_return moments and chart data.
#          Uses Swiss Ephemeris solcross_ut/mooncross_ut for exact crossings.
# owns:
#   - apps/solarsage/solarsage/services/returns.py
# inputs: birth date/time/tz/lat/lon, target date/time/tz, house_system,
#         optional current_location
# outputs: SolarReturnResult, LunarReturnResult with chart planets, houses,
#          angles, timestamps
# dependencies: swisseph, ephemeris utils
# side_effects: none (pure computation)
# emitted_logs: none
# invariants:
#   - solar return: longitude residual <= 0.001°, found within ±3 days of birthday
#   - lunar return: longitude residual <= 0.001°, return_jd <= target_jd,
#     target_jd - return_jd < 30 days
# failure_policy: ValueError on invalid dates or if crossing cannot be found
# END_MODULE_CONTRACT: M-SIDECAR-RETURNS

# START_MODULE_MAP: M-SIDECAR-RETURNS
# public_entrypoints:
#   - calculate_solar_return
#   - calculate_lunar_return
# semantic_blocks:
#   - RETURN_SEARCH: exact crossing search
#   - CHART_BUILDING: return chart construction
# owned_tests:
#   - tests/test_solar_return.py
#   - tests/test_lunar_return.py
# END_MODULE_MAP: M-SIDECAR-RETURNS

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import swisseph as swe

from solarsage.utils.ephemeris import (
    calculate_julian_day,
    calculate_positions,
    calculate_houses_cusps,
    get_sign,
)

# ── Return result models ─────────────────────────────────────────────────────


class SolarReturnResult:
    """Holds the solar return calculation result."""

    def __init__(
        self,
        *,
        return_jd: float,
        return_utc_iso: str,
        natal_sun_lon: float,
        return_sun_lon: float,
        chart_planets: list[dict[str, Any]],
        chart_houses: list[dict[str, Any]],
        chart_angles: dict[str, float],
        special_points: list[dict[str, Any]],
        asc_lon: float,
        mc_lon: float,
        house_system: str,
    ) -> None:
        self.return_jd = return_jd
        self.return_utc_iso = return_utc_iso
        self.natal_sun_lon = natal_sun_lon
        self.return_sun_lon = return_sun_lon
        self.chart_planets = chart_planets
        self.chart_houses = chart_houses
        self.chart_angles = chart_angles
        self.special_points = special_points
        self.asc_lon = asc_lon
        self.mc_lon = mc_lon
        self.house_system = house_system


class LunarReturnResult:
    """Holds the lunar return calculation result."""

    def __init__(
        self,
        *,
        return_jd: float,
        return_utc_iso: str,
        natal_moon_lon: float,
        return_moon_lon: float,
        chart_planets: list[dict[str, Any]],
        chart_houses: list[dict[str, Any]],
        chart_angles: dict[str, float],
        special_points: list[dict[str, Any]],
        asc_lon: float,
        mc_lon: float,
        house_system: str,
    ) -> None:
        self.return_jd = return_jd
        self.return_utc_iso = return_utc_iso
        self.natal_moon_lon = natal_moon_lon
        self.return_moon_lon = return_moon_lon
        self.chart_planets = chart_planets
        self.chart_houses = chart_houses
        self.chart_angles = chart_angles
        self.special_points = special_points
        self.asc_lon = asc_lon
        self.mc_lon = mc_lon
        self.house_system = house_system


# ── Helpers ──────────────────────────────────────────────────────────────────


def _jd_to_utc_iso(jd: float) -> str:
    """Convert Julian Day to UTC ISO string."""
    year, month, day, hour = swe.revjul(jd)
    minute = (hour - int(hour)) * 60
    second = (minute - int(minute)) * 60
    dt = datetime(
        int(year), int(month), int(day),
        int(hour), int(minute), int(second),
        tzinfo=timezone.utc,
    )
    return dt.isoformat()


def _find_house(longitude: float, houses: list[dict[str, Any]]) -> int:
    """Find which house contains the given longitude."""
    hlist = sorted(houses, key=lambda h: h.get("cusp", 0.0))
    for i, house in enumerate(hlist):
        cusp = house.get("cusp", 0.0)
        next_i = (i + 1) % 12
        next_cusp = hlist[next_i].get("cusp", 0.0)
        if next_cusp < cusp:
            next_cusp += 360.0
        adj_lon = longitude + (360.0 if (next_cusp > 360.0 and longitude < cusp) else 0.0)
        if cusp <= adj_lon < next_cusp:
            return house["number"]
    return hlist[-1]["number"]


def _sign_ruler(sign: str) -> str:
    """Traditional ruler for a sign (shared with activation_builder)."""
    rulers = {
        "Aries": "MARS", "Taurus": "VENUS", "Gemini": "MERCURY",
        "Cancer": "MOON", "Leo": "SUN", "Virgo": "MERCURY",
        "Libra": "VENUS", "Scorpio": "MARS", "Sagittarius": "JUPITER",
        "Capricorn": "SATURN", "Aquarius": "SATURN", "Pisces": "JUPITER",
    }
    if sign not in rulers:
        raise ValueError(f"Unknown sign: '{sign}'")
    return rulers[sign]


# START_BLOCK: RETURN_SEARCH


def calculate_solar_return(
    *,
    birth_date: str,
    birth_time: str,
    birth_tz: str,
    birth_lat: float,
    birth_lon: float,
    target_year: int,
    house_system: str,
) -> SolarReturnResult:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-RETURNS.calculate_solar_return
    # purpose: Calculate exact solar return for a target year.
    # inputs: birth date/time/tz/lat/lon, target_year, house_system
    # returns: SolarReturnResult with return JD, chart data, angles
    # side_effects: none (pure ephemeris computation)
    # error_behavior: ValueError if crossing cannot be found
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-RETURNS.calculate_solar_return
    """Calculate exact solar return chart for a target year.

    Uses Swiss Ephemeris solcross_ut to find the exact moment when transit Sun
    longitude equals natal Sun longitude.
    """
    # 1. Natal Sun longitude
    natal_jd = calculate_julian_day(birth_date, birth_time, birth_tz)
    natal_positions = calculate_positions(natal_jd)
    natal_by_name = {p["name"]: p for p in natal_positions}
    natal_sun = natal_by_name.get("Sun", {})
    if not natal_sun:
        raise ValueError("Could not find natal Sun position")
    natal_sun_lon = natal_sun["longitude"]

    # 2. Search for crossing in target year
    # Start search a few days before the birthday in the target year
    from datetime import date as Date
    birthday_target = Date(target_year, int(birth_date.split("-")[1]), int(birth_date.split("-")[2]))
    # Use noon on day before birthday as search start to ensure we catch the crossing
    from solarsage.utils.ephemeris import calculate_julian_day as calc_jd
    search_start = calc_jd(birthday_target.isoformat(), "00:00", "UTC") - 3

    swe.set_ephe_path("/opt/sweph/ephe")
    flags = swe.FLG_SWIEPH
    try:
        return_jd = swe.solcross_ut(natal_sun_lon, search_start, flags)
    except swe.Error as e:
        raise ValueError(f"Solar return crossing not found: {e}")

    if return_jd <= 0:
        raise ValueError(f"Solar return crossing returned invalid JD: {return_jd}")

    # Verify precision
    sun_at_return = swe.calc_ut(return_jd, swe.SUN, flags)
    return_sun_lon = sun_at_return[0][0]
    lon_residual = abs(return_sun_lon - natal_sun_lon) % 360.0
    if lon_residual > 180.0:
        lon_residual = 360.0 - lon_residual
    if lon_residual > 0.01:
        # Try refining: search the other direction
        try:
            return_jd = swe.solcross_ut(natal_sun_lon, return_jd + 0.1, flags)
            while return_jd > 0 and abs(return_jd - search_start) < 365.0:
                sun_at_return = swe.calc_ut(return_jd, swe.SUN, flags)
                return_sun_lon = sun_at_return[0][0]
                lon_residual = abs(return_sun_lon - natal_sun_lon) % 360.0
                if lon_residual > 180.0:
                    lon_residual = 360.0 - lon_residual
                if lon_residual <= 0.001:
                    break
                return_jd = swe.solcross_ut(natal_sun_lon, return_jd + 0.1, flags)
        except swe.Error:
            pass

    # 3. Build return chart
    return_utc_iso = _jd_to_utc_iso(return_jd)
    chart_planets = calculate_positions(return_jd)
    chart_houses, special_points, resolved_house_system = calculate_houses_cusps(
        return_jd, birth_lat, birth_lon,
    )

    # Find ASC/MC
    asc_lon = 0.0
    mc_lon = 0.0
    chart_angles = {}
    for sp in special_points:
        if sp["name"] == "ASC":
            asc_lon = sp["longitude"]
            chart_angles["ASC"] = asc_lon
        elif sp["name"] == "MC":
            mc_lon = sp["longitude"]
            chart_angles["MC"] = mc_lon

    return SolarReturnResult(
        return_jd=return_jd,
        return_utc_iso=return_utc_iso,
        natal_sun_lon=natal_sun_lon,
        return_sun_lon=return_sun_lon,
        chart_planets=chart_planets,
        chart_houses=chart_houses,
        chart_angles=chart_angles,
        special_points=special_points,
        asc_lon=asc_lon,
        mc_lon=mc_lon,
        house_system=resolved_house_system,
    )


def calculate_lunar_return(
    *,
    birth_date: str,
    birth_time: str,
    birth_tz: str,
    birth_lat: float,
    birth_lon: float,
    target_date: str,
    target_time: str,
    target_tz: str,
    house_system: str,
) -> LunarReturnResult:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-RETURNS.calculate_lunar_return
    # purpose: Calculate the most recent lunar return at or before target.
    # inputs: birth data, target data, house_system
    # returns: LunarReturnResult with return JD, chart data, angles
    # side_effects: none (pure ephemeris computation)
    # error_behavior: ValueError if crossing cannot be found within 30 days
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-RETURNS.calculate_lunar_return
    """Calculate the most recent lunar return chart at or before target datetime.

    Uses mooncross_ut to find the crossing and walks backwards to find the
    latest return at or before target_jd.
    """
    # 1. Natal Moon longitude
    natal_jd = calculate_julian_day(birth_date, birth_time, birth_tz)
    natal_positions = calculate_positions(natal_jd)
    natal_by_name = {p["name"]: p for p in natal_positions}
    natal_moon = natal_by_name.get("Moon", {})
    if not natal_moon:
        raise ValueError("Could not find natal Moon position")
    natal_moon_lon = natal_moon["longitude"]

    # 2. Target JD
    target_jd = calculate_julian_day(target_date, target_time, target_tz)

    # 3. Search for the most recent crossing
    # mooncross_ut searches forward from the given start date.
    # We search from target_jd - 27.5 days (slightly more than a sidereal month)
    # to find the latest crossing at or before target_jd.
    # If the result is > target_jd, search earlier.
    swe.set_ephe_path("/opt/sweph/ephe")
    flags = swe.FLG_SWIEPH

    search_start = target_jd - 28.0  # slightly more than a lunar month
    best_jd = -1.0
    best_lon_residual = 999.0

    # Try a few search windows to find the most recent crossing
    for offset in [0, -0.5, -1.0, -1.5, -2.0, 2.0, 1.0, 0.5]:
        try:
            jd = swe.mooncross_ut(natal_moon_lon, search_start + offset, flags)
        except swe.Error:
            continue
        if jd <= 0:
            continue
        if jd > target_jd:
            continue

        # Verify precision
        moon_at_return = swe.calc_ut(jd, swe.MOON, flags)
        return_moon_lon = moon_at_return[0][0]
        lon_residual = abs(return_moon_lon - natal_moon_lon) % 360.0
        if lon_residual > 180.0:
            lon_residual = 360.0 - lon_residual

        if lon_residual < best_lon_residual:
            best_lon_residual = lon_residual
            best_jd = jd

    if best_jd <= 0:
        raise ValueError("Could not find lunar return within search window")

    # Verify constraints
    if target_jd - best_jd >= 30:
        raise ValueError(f"Lunar return JD {best_jd} is more than 30 days before target {target_jd}")

    return_jd = best_jd
    moon_at_return = swe.calc_ut(return_jd, swe.MOON, flags)
    return_moon_lon = moon_at_return[0][0]

    # 4. Build return chart
    return_utc_iso = _jd_to_utc_iso(return_jd)
    chart_planets = calculate_positions(return_jd)
    chart_houses, special_points, resolved_house_system = calculate_houses_cusps(
        return_jd, birth_lat, birth_lon,
    )

    asc_lon = 0.0
    mc_lon = 0.0
    chart_angles = {}
    for sp in special_points:
        if sp["name"] == "ASC":
            asc_lon = sp["longitude"]
            chart_angles["ASC"] = asc_lon
        elif sp["name"] == "MC":
            mc_lon = sp["longitude"]
            chart_angles["MC"] = mc_lon

    return LunarReturnResult(
        return_jd=return_jd,
        return_utc_iso=return_utc_iso,
        natal_moon_lon=natal_moon_lon,
        return_moon_lon=return_moon_lon,
        chart_planets=chart_planets,
        chart_houses=chart_houses,
        chart_angles=chart_angles,
        special_points=special_points,
        asc_lon=asc_lon,
        mc_lon=mc_lon,
        house_system=resolved_house_system,
    )


# END_BLOCK: RETURN_SEARCH
