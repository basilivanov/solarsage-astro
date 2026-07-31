# ############################################################################
# AI_HEADER: MODULE_SIDECAR_ACTIVATION_BUILDER — sidecar activation layer builder.
# ROLE: W3.1+ transit, profection, and firdar activation extraction.
#       Supports transit_to_natal, transit_to_angle, transit_to_lot,
#       transit_planet_in_house, annual_profection, monthly_profection,
#       firdar_major, firdar_minor.
# ############################################################################

from __future__ import annotations

import calendar
import os
import pathlib
from copy import deepcopy
from dataclasses import dataclass
from datetime import date as Date, timedelta
from functools import lru_cache
from typing import Any, Literal

import yaml

from solarsage.core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
from solarsage.services import firdar as firdar_service
from solarsage.services.returns import (
    calculate_lunar_return,
    calculate_solar_return,
    find_next_lunar_return_jd,
    find_solar_return_jd,
)
from solarsage.services.transit_timing import TransitTimingSolver, TransitTimingError
from solarsage.schemas.activation import ActivationLayer, ActivationEvidence
from solarsage.utils.ephemeris import (
    calculate_julian_day,
    calculate_positions,
    calculate_solar_altitude,
    calculate_houses_cusps,
    get_sign,
    julian_day_to_utc_iso,
)

# ── Canon aspect map ─────────────────────────────────────────────────────────
# Lowercase names are the canonical activation output names.
ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "semi_sextile": 30.0,
    "semi_square": 45.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "sesqui_quadrate": 135.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}

# Reverse map: uppercase YAML key -> lowercase output name.
ASPECT_NAME_BY_UPPER: dict[str, str] = {k.upper(): k for k in ASPECT_ANGLES}

# Polarity classification
def _classify_polarity(aspect_name: str) -> str:
    if aspect_name in ("trine", "sextile"):
        return "supportive"
    if aspect_name in ("square", "opposition", "semi_square", "sesqui_quadrate"):
        return "tense"
    if aspect_name == "conjunction":
        return "mixed"
    return "neutral"


# ── Canon loading ────────────────────────────────────────────────────────────

def _resolve_canon_path(relative: str) -> str:
    """Resolve a path relative to the project root (grace/canon/…)."""
    # The builder lives at apps/solarsage/solarsage/services/activation_builder.py
    # Project root is four levels up.
    here = pathlib.Path(__file__).resolve().parent  # services/
    # Walk up to project root
    root = here.parent.parent.parent.parent  # 4 levels: services -> solarsage -> solarsage -> apps -> root
    return os.path.join(root, relative)


@lru_cache(maxsize=8)
def _load_yaml_mapping_cached(path: str, mtime_ns: int, size: int) -> dict[str, Any]:
    """Read one immutable canon revision once per worker process."""
    del mtime_ns, size  # cache-key material; path owns the actual read
    with open(path) as f:
        return yaml.safe_load(f)


def _load_aspect_rules() -> dict[str, Any]:
    path = _resolve_canon_path("grace/canon/aspect_rules.v1.yml")
    stat = os.stat(path)
    return deepcopy(_load_yaml_mapping_cached(path, stat.st_mtime_ns, stat.st_size))


def _get_orb(rules: dict, source_planet: str, target_key: str | None) -> float | None:
    """Determine max orb for a transit->target pair."""
    profile = rules.get("orb_profile_default", {})
    if target_key and target_key in profile:
        return float(profile[target_key])
    if source_planet.upper() in profile:
        return float(profile[source_planet.upper()])
    return None


def _get_aspect_weight(rules: dict, aspect_name: str) -> float:
    """Get weight from aspect_weights, default 0.5."""
    weights = rules.get("aspect_weights", {})
    return float(weights.get(aspect_name.upper(), 0.5))


# ── Angle helpers ────────────────────────────────────────────────────────────

def _normalize_longitude(lon: float) -> float:
    """Normalize to 0..360."""
    return lon % 360.0


def _angular_distance(lon1: float, lon2: float) -> float:
    """Shortest angular distance between two longitudes, normalized to 0..180."""
    raw = abs(lon1 - lon2) % 360.0
    if raw > 180.0:
        raw = 360.0 - raw
    return raw


# ── Lot calculations ─────────────────────────────────────────────────────────


def _normalize_degrees(val: float) -> float:
    return val % 360.0


def _find_house(longitude: float, houses: list[dict[str, Any]]) -> int:
    """Find which natal house contains the given longitude."""
    hlist = sorted(houses, key=lambda h: h.get("cusp", 0.0))
    for i, house in enumerate(hlist):
        cusp = house.get("cusp", 0.0)
        next_cusp = hlist[(i + 1) % 12].get("cusp", 0.0) + (360.0 if i == 11 else 0.0)
        # Handle wrap-around for houses 12->1
        adj_lon = longitude + (360.0 if i == 11 and longitude < cusp else 0.0)
        if i < 11:
            adj_next = next_cusp
            if next_cusp < cusp:
                adj_next = next_cusp + 360.0
        else:
            adj_next = next_cusp if next_cusp > cusp else next_cusp + 360.0
        if cusp <= adj_lon < adj_next:
            return house["number"]
    # Fallback: last house
    return hlist[-1]["number"]


def _compute_lots(
    asc_lon: float,
    sun_lon: float,
    moon_lon: float,
    mercury_lon: float,
    venus_lon: float,
    jupiter_lon: float,
    saturn_lon: float,
    dsc_lon: float,
    is_day: bool,
) -> list[dict[str, Any]]:
    """Compute the seven requested lots with debug fields."""
    # ── Helper for two-operand Hermetic lots ──
    def lot(a: float, b: float, c: float) -> float:
        return _normalize_degrees(a + b - c)

    spirit_day = lot(asc_lon, sun_lon, moon_lon)
    spirit_night = lot(asc_lon, moon_lon, sun_lon)
    fortune_day = lot(asc_lon, moon_lon, sun_lon)
    fortune_night = lot(asc_lon, sun_lon, moon_lon)

    if is_day:
        fortune_lon = fortune_day
        spirit_lon = spirit_day
    else:
        fortune_lon = fortune_night
        spirit_lon = spirit_night

    return [
        {
            "name": "FORTUNE",
            "longitude": fortune_lon,
            "formula": "fortune_day_asc_moon_sun" if is_day else "fortune_night_asc_sun_moon",
        },
        {
            "name": "SPIRIT",
            "longitude": spirit_lon,
            "formula": "spirit_day_asc_sun_moon" if is_day else "spirit_night_asc_moon_sun",
        },
        {
            "name": "EROS",
            "longitude": _normalize_degrees(asc_lon + venus_lon - spirit_lon) if is_day
                         else _normalize_degrees(asc_lon + spirit_lon - venus_lon),
            "formula": "eros_day_asc_venus_spirit" if is_day else "eros_night_asc_spirit_venus",
        },
        {
            "name": "NECESSITY",
            "longitude": _normalize_degrees(asc_lon + fortune_lon - mercury_lon) if is_day
                         else _normalize_degrees(asc_lon + mercury_lon - fortune_lon),
            "formula": "necessity_day_asc_fortune_mercury" if is_day else "necessity_night_asc_mercury_fortune",
        },
        {
            "name": "VICTORY",
            "longitude": _normalize_degrees(asc_lon + jupiter_lon - spirit_lon) if is_day
                         else _normalize_degrees(asc_lon + spirit_lon - jupiter_lon),
            "formula": "victory_day_asc_jupiter_spirit" if is_day else "victory_night_asc_spirit_jupiter",
        },
        {
            "name": "NEMESIS",
            "longitude": _normalize_degrees(asc_lon + fortune_lon - saturn_lon) if is_day
                         else _normalize_degrees(asc_lon + saturn_lon - fortune_lon),
            "formula": "nemesis_day_asc_fortune_saturn" if is_day else "nemesis_night_asc_saturn_fortune",
        },
        {
            # MARRIAGE: non-reversing formula ASC + DSC - Venus
            "name": "MARRIAGE",
            "longitude": _normalize_degrees(asc_lon + dsc_lon - venus_lon),
            "formula": "marriage_asc_dsc_venus_non_reversing",
        },
    ]


# ── Build a single transit->target aspect activation ─────────────────────────

def _build_aspect_id(prefix: str, source: str, aspect: str, target: str) -> str:
    """Deterministic stable ID."""
    return f"{prefix}__{source.upper()}__{aspect.upper()}__{target.upper()}"


def _build_planet_in_house_id(planet: str, house: int) -> str:
    return f"tih__{planet.upper()}__{house}"


def _build_aspect_activation(
    *,
    technique: str,
    family: str,
    source_planet: str,
    source_longitude: float,
    target_key: str,
    target_type: str,
    target_frame: str,
    target_longitude: float,
    aspect_name: str,
    orb: float,
    applying: bool | None,
    phase: str,
    strength: float,
    polarity: str,
    active_from: str | None = None,
    exact_at: str | None = None,
    active_until: str | None = None,
    evidence: str,
    debug: dict[str, Any] | None = None,
    angle: str | None = None,
    lot: str | None = None,
    house: int | None = None,
) -> ActivationEvidence:
    aid = _build_aspect_id(
        {"transit_to_natal": "t2n", "transit_to_angle": "t2a", "transit_to_lot": "t2l"}.get(technique, "t2x"),
        source_planet, aspect_name, target_key,
    )
    return ActivationEvidence(
        id=aid,
        technique=technique,
        technique_family=family,
        target_type=target_type,
        target_key=target_key,
        kind=aspect_name,
        source_planet=source_planet,
        source_frame="transit",
        target_frame=target_frame,
        target_planet=target_key if target_type == "planet" else None,
        aspect=aspect_name,
        orb=round(orb, 4),
        applying=applying,
        active_from=active_from,
        exact_at=exact_at,
        active_until=active_until,
        phase=phase,
        strength=round(strength, 4),
        polarity=polarity,
        evidence=evidence,
        debug=debug or {},
        angle=angle,
        lot=lot,
        house=house,
    )


def _build_house_activation(
    *,
    source_planet: str,
    house: int,
    target_longitude: float,
    evidence: str,
    debug: dict[str, Any] | None = None,
) -> ActivationEvidence:
    aid = _build_planet_in_house_id(source_planet, house)
    return ActivationEvidence(
        id=aid,
        technique="transit_planet_in_house",
        technique_family="transit",
        target_type="house",
        target_key=str(house),
        kind="planet_in_house",
        source_planet=source_planet,
        source_frame="transit",
        target_frame="natal",
        house=house,
        strength=1.0,
        polarity="neutral",
        evidence=evidence,
        debug=debug or {},
    )


# ── Main builder ─────────────────────────────────────────────────────────────

# Ordered tuple for deterministic default ordering (PYTHONHASHSEED-independent).
W3_1_SUPPORTED_ORDER = (
    "transit_to_natal",
    "transit_to_angle",
    "transit_planet_in_house",
    "transit_to_lot",
)
W3_2_SUPPORTED_ORDER = (
    "annual_profection",
    "monthly_profection",
)
W3_3_SUPPORTED_ORDER = (
    "firdar_major",
    "firdar_minor",
)
W3_4_SUPPORTED_ORDER = (
    "solar_return",
    "lunar_return",
)
W3_5_SUPPORTED_ORDER = (
    "solar_arc",
    "secondary_progression",
)
W3_6_SUPPORTED_ORDER = (
    "eclipse_window",
)
SUPPORTED_ORDER = W3_1_SUPPORTED_ORDER + W3_2_SUPPORTED_ORDER + W3_3_SUPPORTED_ORDER + W3_4_SUPPORTED_ORDER + W3_5_SUPPORTED_ORDER + W3_6_SUPPORTED_ORDER
W3_1_SUPPORTED = set(W3_1_SUPPORTED_ORDER)
W3_2_SUPPORTED = set(W3_2_SUPPORTED_ORDER)
W3_3_SUPPORTED = set(W3_3_SUPPORTED_ORDER)
W3_4_SUPPORTED = set(W3_4_SUPPORTED_ORDER)
W3_5_SUPPORTED = set(W3_5_SUPPORTED_ORDER)
W3_6_SUPPORTED = set(W3_6_SUPPORTED_ORDER)
SUPPORTED = W3_1_SUPPORTED | W3_2_SUPPORTED | W3_3_SUPPORTED | W3_4_SUPPORTED | W3_5_SUPPORTED | W3_6_SUPPORTED
ALL_TECHNIQUES = list(SUPPORTED_ORDER)


# Title-case display names for evidence strings (target_key remains uppercase).
_DISPLAY_NAMES: dict[str, str] = {
    "SUN": "Sun",
    "MOON": "Moon",
    "MERCURY": "Mercury",
    "VENUS": "Venus",
    "MARS": "Mars",
    "JUPITER": "Jupiter",
    "SATURN": "Saturn",
    "URANUS": "Uranus",
    "NEPTUNE": "Neptune",
    "PLUTO": "Pluto",
    "ASC": "ASC",
    "MC": "MC",
    "DSC": "DSC",
    "IC": "IC",
    "NORTH_NODE_TRUE": "North Node",
    "SOUTH_NODE": "South Node",
}


def _display_name(key: str) -> str:
    """Return display name for a target key (planet, angle, or lot)."""
    return _DISPLAY_NAMES.get(key.upper(), key)


# ── Sign rulers (traditional) for profections ────────────────────────────────

SIGN_RULERS: dict[str, str] = {
    "Aries": "MARS",
    "Taurus": "VENUS",
    "Gemini": "MERCURY",
    "Cancer": "MOON",
    "Leo": "SUN",
    "Virgo": "MERCURY",
    "Libra": "VENUS",
    "Scorpio": "MARS",
    "Sagittarius": "JUPITER",
    "Capricorn": "SATURN",
    "Aquarius": "SATURN",
    "Pisces": "JUPITER",
}


def _ruler_of_sign(sign: str) -> str:
    """Return traditional ruler for a sign name. Raises ValueError for unknown signs."""
    if sign not in SIGN_RULERS:
        raise ValueError(f"Unknown sign: '{sign}'. Valid signs: {', '.join(SIGN_RULERS)}")
    return SIGN_RULERS[sign]


# ── Profection helpers ───────────────────────────────────────────────────────

def _load_activation_rules() -> dict[str, Any]:
    """Load activation_rules.v1.yml for period strengths."""
    path = _resolve_canon_path("grace/canon/activation_rules.v1.yml")
    stat = os.stat(path)
    return deepcopy(_load_yaml_mapping_cached(path, stat.st_mtime_ns, stat.st_size))


def _load_convergence_rules() -> dict[str, Any]:
    """Load the current convergence canon for explicit offline timing scope."""
    path = _resolve_canon_path("grace/canon/today_convergence.v1.yml")
    stat = os.stat(path)
    return deepcopy(_load_yaml_mapping_cached(path, stat.st_mtime_ns, stat.st_size))


def _get_period_strength(rules: dict, technique: str) -> float:
    """Return canon period strength; raises KeyError if missing."""
    period_base = rules.get("activation_strength", {}).get("period_base", {})
    return float(period_base[technique])


def _get_return_strength(rules: dict, kind: str) -> float:
    """Return canon return strength; raises KeyError if missing."""
    return_base = rules.get("activation_strength", {}).get("return_base", {})
    return float(return_base[kind])


def safe_replace_year(
    d: Date,
    year: int,
    *,
    feb29_policy: str = "feb28",
) -> Date:
    """Replace year on a date with an explicit Feb 29 policy.

    Default policy ``feb28`` maps Feb 29 births onto Feb 28 in non-leap years.
    ``mar01`` maps them onto March 1 instead.
    """
    try:
        return d.replace(year=year)
    except ValueError:
        if d.month == 2 and d.day == 29:
            if feb29_policy == "feb28":
                return Date(year, 2, 28)
            if feb29_policy == "mar01":
                return Date(year, 3, 1)
            raise ValueError(f"Unknown feb29_policy: {feb29_policy}") from None
        raise


def _completed_years(birth_local: Date, target_local: Date) -> int:
    """Completed full years between two local dates.

    Feb 29 births use the feb28 policy birthday in non-leap years.
    """
    birthday_this_year = safe_replace_year(birth_local, target_local.year)
    age = target_local.year - birth_local.year
    if target_local < birthday_this_year:
        age -= 1
    return max(0, age)


def _add_months_with_clamp(d: Date, months: int) -> Date:
    """Add months to a date, clamping day to month max."""
    total_month = d.month - 1 + months
    year = d.year + total_month // 12
    month = total_month % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    day = min(d.day, max_day)
    return Date(year, month, day)


def _local_date(date_str: str, tz_str: str) -> Date:
    """Convert a date-only string to a date. Time is irrelevant for local date."""
    # For profections, we use the date as given (birth date or target date in target_tz).
    # The target_time is already the middle of the day (12:00), not midnight boundary.
    # For simplicity and to match TZ expectations, we parse the YYYY-MM-DD directly
    # and treat it as the local calendar date.
    return Date.fromisoformat(date_str)


@dataclass(frozen=True)
class NatalCalculationContext:
    """Immutable-per-request natal inputs reusable across target dates."""

    birth_date: str
    birth_time: str
    birth_lat: float
    birth_lon: float
    birth_tz: str
    requested_house_system: str
    natal_jd: float
    natal_positions: tuple[dict[str, Any], ...]
    natal_houses_raw: tuple[dict[str, Any], ...]
    natal_special_points: tuple[dict[str, Any], ...]
    resolved_house_system: str
    natal_by_name: dict[str, dict[str, Any]]
    natal_sun_house: int | None
    sun_altitude_deg: float
    is_day: bool
    sect_polar_condition: str | None
    angles: dict[str, float]
    lots: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class TargetCalculationContext:
    """Transit positions reusable across charts at one target moment."""

    target_date: str
    target_time: str
    target_tz: str
    target_jd: float
    transit_positions: tuple[dict[str, Any], ...]
    transit_by_name: dict[str, dict[str, Any]]


# START_BLOCK: PRECOMPUTED_CONTEXTS
def _sect_polar_condition(birth_date: str, birth_tz: str, birth_lat: float, birth_lon: float) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-ACTIVATION-BUILDER._sect_polar_condition
    # purpose: Classify continuous-daylight ("polar_day") or continuous-darkness
    #   ("polar_night") on the local birth date, or None for a normal day/night cycle.
    # inputs: birth_date, birth_tz, birth_lat, birth_lon.
    # returns: "polar_day" | "polar_night" | None.
    # side_effects: Swiss Ephemeris altitude evaluations (48 per birth date).
    # emitted_logs: none.
    # error_behavior: propagates ephemeris errors fail-closed.
    # END_FUNCTION_CONTRACT
    # Sample every 30 minutes of the local birth date; at polar latitudes the
    # diurnal altitude curve is flat, so half-hour sampling is decisive.
    midnight_jd = calculate_julian_day(birth_date, "00:00", birth_tz)
    altitudes = [
        calculate_solar_altitude(midnight_jd + step / 48.0, birth_lat, birth_lon)
        for step in range(49)
    ]
    if min(altitudes) > 0.0:
        return "polar_day"
    if max(altitudes) <= 0.0:
        return "polar_night"
    return None


def prepare_natal_context(
    *,
    birth_date: str,
    birth_time: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    house_system: str,
) -> NatalCalculationContext:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-ACTIVATION-BUILDER.prepare_natal_context
    # purpose: Calculate invariant natal geometry once for many target dates.
    # inputs: exact birth event and requested house system.
    # returns: NatalCalculationContext shared by activation builds.
    # side_effects: Swiss Ephemeris calculations and canon reads.
    # emitted_logs: none.
    # error_behavior: propagates calculation errors fail-closed.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-ACTIVATION-BUILDER.prepare_natal_context
    natal_jd = calculate_julian_day(birth_date, birth_time, birth_tz)
    natal_positions = tuple(calculate_positions(natal_jd))
    sun_altitude_deg = calculate_solar_altitude(natal_jd, birth_lat, birth_lon)
    is_day = sun_altitude_deg > 0.0
    sect_polar_condition = _sect_polar_condition(birth_date, birth_tz, birth_lat, birth_lon)
    houses, special_points, resolved_house_system = calculate_houses_cusps(
        natal_jd, birth_lat, birth_lon, house_system,
    )
    natal_by_name = {item["name"]: item for item in natal_positions}
    natal_sun = natal_by_name.get("Sun", {})
    natal_sun_house = (
        _find_house(natal_sun.get("longitude", 0.0), houses)
        if natal_sun
        else None
    )

    special_by_name = {item["name"]: item for item in special_points}
    asc_lon = special_by_name.get("ASC", {}).get("longitude", 0.0)
    mc_lon = special_by_name.get("MC", {}).get("longitude", 0.0)
    angles = {
        "ASC": asc_lon,
        "MC": mc_lon,
        "DSC": (asc_lon + 180.0) % 360.0,
        "IC": (mc_lon + 180.0) % 360.0,
    }

    lots = _compute_lots(
        asc_lon=asc_lon,
        sun_lon=natal_sun.get("longitude", 0.0),
        moon_lon=natal_by_name.get("Moon", {}).get("longitude", 0.0),
        mercury_lon=natal_by_name.get("Mercury", {}).get("longitude", 0.0),
        venus_lon=natal_by_name.get("Venus", {}).get("longitude", 0.0),
        jupiter_lon=natal_by_name.get("Jupiter", {}).get("longitude", 0.0),
        saturn_lon=natal_by_name.get("Saturn", {}).get("longitude", 0.0),
        dsc_lon=angles["DSC"],
        is_day=is_day,
    )
    for lot in lots:
        lot["house"] = _find_house(lot["longitude"], houses)
        lot["sign"] = get_sign(lot["longitude"])

    return NatalCalculationContext(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_tz=birth_tz,
        requested_house_system=house_system,
        natal_jd=natal_jd,
        natal_positions=natal_positions,
        natal_houses_raw=tuple(houses),
        natal_special_points=tuple(special_points),
        resolved_house_system=resolved_house_system,
        natal_by_name=natal_by_name,
        natal_sun_house=natal_sun_house,
        sun_altitude_deg=sun_altitude_deg,
        is_day=is_day,
        sect_polar_condition=sect_polar_condition,
        angles=angles,
        lots=tuple(lots),
    )


def prepare_target_context(
    *,
    target_date: str,
    target_time: str,
    target_tz: str,
) -> TargetCalculationContext:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-ACTIVATION-BUILDER.prepare_target_context
    # purpose: Calculate transit geometry once for a target moment.
    # inputs: target local date, time, and timezone.
    # returns: TargetCalculationContext reusable across charts.
    # side_effects: Swiss Ephemeris calculations.
    # emitted_logs: none.
    # error_behavior: propagates calculation errors fail-closed.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-ACTIVATION-BUILDER.prepare_target_context
    target_jd = calculate_julian_day(target_date, target_time, target_tz)
    positions = tuple(calculate_positions(target_jd))
    return TargetCalculationContext(
        target_date=target_date,
        target_time=target_time,
        target_tz=target_tz,
        target_jd=target_jd,
        transit_positions=positions,
        transit_by_name={item["name"]: item for item in positions},
    )
# END_BLOCK: PRECOMPUTED_CONTEXTS


def build_activation_layer(
    *,
    birth_date: str,
    birth_time: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    target_date: str,
    target_time: str,
    target_tz: str,
    house_system: str,
    techniques: list[str] | None = None,
    current_location: dict[str, Any] | None = None,
    timing_scope: Literal["all", "convergence_eligible"] = "all",
    natal_context: NatalCalculationContext | None = None,
    target_context: TargetCalculationContext | None = None,
    timing_solver: TransitTimingSolver | None = None,
) -> ActivationLayer:
    """Build activation layer for a given birth + target context.

    W3.1-W3.4: transit, profection, firdar, and return activations.

    Unsupported W3+ techniques generate deterministic warnings and are skipped.
    """
    if timing_scope not in ("all", "convergence_eligible"):
        raise ValueError(f"Unsupported timing_scope: {timing_scope}")

    if techniques is None or len(techniques) == 0:
        requested = list(ALL_TECHNIQUES)
    else:
        requested = list(techniques)

    # Filter to supported + collect warnings for unsupported
    active = [t for t in requested if t in SUPPORTED]
    warnings_list: list[str] = []
    for t in requested:
        if t not in SUPPORTED:
            warnings_list.append(f"unsupported_technique_deferred:{t}")

    if not active:
        # No supported techniques requested — return contract-only layer
        return ActivationLayer(
            calculation_version=CALCULATION_VERSION,
            activation_layer_version=ACTIVATION_LAYER_VERSION,
            target_date=target_date,
            target_time=target_time,
            target_tz=target_tz,
            house_system=house_system,
            activations=[],
            by_planet={},
            by_house={},
            by_lot={},
            by_angle={},
            warnings=warnings_list or ["contract_only_no_techniques_built_yet"],
        )

    # ── 1. Load aspect rules ─────────────────────────────────────────
    aspect_rules = _load_aspect_rules()

    # ── 2. Reuse invariant natal/target geometry when supplied by replay.
    if natal_context is None:
        natal_context = prepare_natal_context(
            birth_date=birth_date,
            birth_time=birth_time,
            birth_lat=birth_lat,
            birth_lon=birth_lon,
            birth_tz=birth_tz,
            house_system=house_system,
        )
    elif (
        natal_context.birth_date != birth_date
        or natal_context.birth_time != birth_time
        or natal_context.birth_tz != birth_tz
        or natal_context.requested_house_system != house_system
        or natal_context.birth_lat != birth_lat
        or natal_context.birth_lon != birth_lon
    ):
        raise ValueError("natal_context does not match activation birth context")

    if target_context is None:
        target_context = prepare_target_context(
            target_date=target_date,
            target_time=target_time,
            target_tz=target_tz,
        )
    elif (
        target_context.target_date != target_date
        or target_context.target_time != target_time
        or target_context.target_tz != target_tz
    ):
        raise ValueError("target_context does not match activation target context")

    natal_houses_raw = list(natal_context.natal_houses_raw)
    resolved_house_system = natal_context.resolved_house_system
    natal_by_name = natal_context.natal_by_name
    natal_sun = natal_by_name.get("Sun", {})
    natal_sun_house = natal_context.natal_sun_house
    sun_altitude_deg = natal_context.sun_altitude_deg
    is_day = natal_context.is_day
    sect_polar_condition = natal_context.sect_polar_condition
    angles = natal_context.angles
    lots = [dict(item) for item in natal_context.lots]
    target_jd = target_context.target_jd
    transit_by_name = target_context.transit_by_name

    # ── 5. Build activations ─────────────────────────────────────────
    activations: list[ActivationEvidence] = []
    by_planet: dict[str, list[str]] = {}
    by_house: dict[str, list[str]] = {}
    by_lot: dict[str, list[str]] = {}
    by_angle: dict[str, list[str]] = {}

    # Cache for firdar context (computed once when both techniques are active)
    firdar_ctx: tuple | None = None

    # Request-scoped by default.  Offline replay may pass a target-moment
    # workspace shared sequentially across birth-time control points; the
    # ephemeris grids depend on transit planet + target moment, not natal data.
    has_transit_tech = any(t in active for t in ("transit_to_natal", "transit_to_angle", "transit_to_lot"))
    if timing_solver is not None and abs(timing_solver.target_jd - target_jd) > 1e-9:
        raise ValueError("timing_solver target_jd does not match activation target context")
    if timing_solver is None and has_transit_tech:
        timing_solver = TransitTimingSolver(target_jd=target_jd)
    convergence_timing_thresholds: tuple[float, float] | None = None
    if timing_scope == "convergence_eligible":
        significance_rules = _load_convergence_rules().get("significance", {})
        convergence_timing_thresholds = (
            float(significance_rules["aspect_weight_min"]),
            float(significance_rules["orb_ratio_max"]),
        )

    for tech in active:
        if tech == "transit_planet_in_house":
            for tname, tpos in transit_by_name.items():
                tlon = tpos["longitude"]
                house_num = _find_house(tlon, natal_houses_raw)
                ev = _build_house_activation(
                    source_planet=tname,
                    house=house_num,
                    target_longitude=tlon,
                    evidence=f"Transit {tname} in natal house {house_num}, strength 1.00",
                    debug={"longitude": tlon, "house": house_num},
                )
                activations.append(ev)
                by_house.setdefault(str(house_num), []).append(ev.id)

        elif tech in ("transit_to_natal", "transit_to_angle", "transit_to_lot"):
            # Determine targets based on technique
            if tech == "transit_to_natal":
                targets: dict[str, tuple[str, float]] = {}
                for nname, npos in natal_by_name.items():
                    targets[nname.upper()] = ("planet", npos["longitude"])
                target_frame = "natal"
            elif tech == "transit_to_angle":
                targets = {}
                for aname, alon in angles.items():
                    targets[aname] = ("angle", alon)
                target_frame = "angle"
            else:  # transit_to_lot
                targets = {}
                for lot in lots:
                    targets[lot["name"]] = ("lot", lot["longitude"])
                target_frame = "lot"

            for tname, tpos in transit_by_name.items():
                tlon = tpos["longitude"]
                for tkey, (ttype, tlon_target) in targets.items():
                    adist = _angular_distance(tlon, tlon_target)
                    max_orb = _get_orb(aspect_rules, tname, tkey if ttype == "planet" else None)
                    if max_orb is None:
                        warning = f"orb_profile_missing:{tname.upper()}"
                        if warning not in warnings_list:
                            warnings_list.append(warning)
                        continue

                    # Check each canonical aspect
                    best_aspect: str | None = None
                    best_adiff: float | None = None
                    for aname, aangle in ASPECT_ANGLES.items():
                        diff = abs(adist - aangle)
                        if diff <= max_orb:
                            if best_adiff is None or diff < best_adiff:
                                best_aspect = aname
                                best_adiff = diff

                    if best_aspect is None:
                        continue

                    # Compute orb (difference from exact aspect)
                    orb = round(best_adiff, 4)

                    # Compute strength
                    aspect_weight = _get_aspect_weight(aspect_rules, best_aspect)
                    orb_factor = max(0.0, 1.0 - orb / max_orb)
                    strength = round(min(1.0, aspect_weight * orb_factor), 4)

                    # Polarity
                    polarity = _classify_polarity(best_aspect)

                    # Phase / applying — compare orb to aspect, not raw distance
                    # Try using the request-scoped solver first. Offline replay
                    # can defer exact timing for facts that cannot pass the
                    # convergence significance gate; the raw fact is retained.
                    timing_result = None
                    timing_error_code: str | None = None
                    timing_requested = True
                    if convergence_timing_thresholds is not None:
                        min_weight, max_orb_ratio = convergence_timing_thresholds
                        timing_requested = (
                            aspect_weight >= min_weight
                            and max_orb > 0.0
                            and orb / max_orb <= max_orb_ratio
                        )
                    try:
                        if timing_solver and timing_requested:
                            timing_result = timing_solver.solve(
                                source_planet=tname,
                                target_longitude=tlon_target,
                                aspect_angle=ASPECT_ANGLES[best_aspect],
                                max_orb=max_orb,
                            )
                    except TransitTimingError as e:
                        # Append a warning with format transit_timing:<activation_id>:<code>
                        # but keep the activation using fallback logic
                        aid_for_warning = _build_aspect_id(
                            {"transit_to_natal": "t2n", "transit_to_angle": "t2a", "transit_to_lot": "t2l"}.get(tech, "t2x"),
                            tname, best_aspect, tkey,
                        )
                        timing_error_code = e.code
                        warnings_list.append(f"transit_timing:{aid_for_warning}:{timing_error_code}")

                    if timing_result:
                        applying = timing_result.applying
                        phase = timing_result.phase
                        active_from = timing_result.active_from_utc
                        exact_at = timing_result.exact_at_utc
                        active_until = timing_result.active_until_utc
                    else:
                        if timing_requested:
                            probe_jd = target_jd + 0.1
                            probe_positions = calculate_positions(probe_jd)
                            probe_by_name: dict[str, dict] = {}
                            for pp in probe_positions:
                                probe_by_name[pp["name"]] = pp
                            probe_tlon = probe_by_name.get(tname, {}).get("longitude", tlon)
                        else:
                            # A linear 0.1-day probe is sufficient for the raw
                            # applying/separating label; no extra ephemeris call.
                            speed = float(tpos.get("speed", 0.0) or 0.0)
                            probe_tlon = (tlon + speed * 0.1) % 360.0
                        probe_adist = _angular_distance(probe_tlon, tlon_target)

                        aspect_angle = ASPECT_ANGLES[best_aspect]
                        current_orb = abs(adist - aspect_angle)
                        probe_orb = abs(probe_adist - aspect_angle)

                        tolerance = 1e-6
                        if abs(probe_orb - current_orb) < tolerance:
                            applying = False
                            phase = "exact"
                        elif probe_orb < current_orb:
                            applying = True
                            phase = "applying"
                        else:
                            applying = False
                            phase = "separating"
                        active_from = None
                        exact_at = None
                        active_until = None

                    # Evidence string with frame — human-readable display names
                    src_display = tname
                    tgt_display = _display_name(tkey)
                    if tech == "transit_to_natal":
                        evidence = (
                            f"Transit {src_display} {best_aspect} natal {tgt_display}, "
                            f"orb {orb}°"
                        )
                    elif tech == "transit_to_angle":
                        evidence = (
                            f"Transit {src_display} {best_aspect} natal {tgt_display}, "
                            f"orb {orb}°"
                        )
                    else:  # transit_to_lot
                        evidence = (
                            f"Transit {src_display} {best_aspect} lot {tgt_display}, "
                            f"orb {orb}°"
                        )

                    debug_info: dict[str, Any] = {
                        "source_longitude": round(tlon, 4),
                        "target_longitude": round(tlon_target, 4),
                        "angular_distance": round(adist, 4),
                        "max_orb": round(max_orb, 4),
                        "aspect_angle": ASPECT_ANGLES[best_aspect],
                        "aspect_weight": aspect_weight,
                    }
                    if timing_result:
                        debug_info["timing"] = {
                            "selected_branch": timing_result.selected_branch,
                            "selected_exact_longitude": round(timing_result.selected_exact_longitude, 6),
                            "occurrence_index": timing_result.occurrence_index,
                            "exact_hits_in_window": list(timing_result.exact_hits_in_window),
                            "warning_code": timing_result.warning_code,
                            "boundary_tolerance_seconds": 300,
                            "exact_tolerance_seconds": 60,
                        }
                    elif timing_error_code:
                        debug_info["applying_probe_days"] = 0.1
                        debug_info["timing"] = {
                            "warning_code": timing_error_code,
                            "boundary_tolerance_seconds": 300,
                            "exact_tolerance_seconds": 60,
                        }
                    elif not timing_requested:
                        debug_info["applying_probe_days"] = 0.1
                        debug_info["timing"] = {
                            "status": "not_requested",
                            "scope": "convergence_eligible",
                            "reason": "below_convergence_significance_gate",
                        }

                    extra_kw: dict[str, Any] = {}
                    if ttype == "angle":
                        extra_kw["angle"] = tkey
                    if ttype == "lot":
                        extra_kw["lot"] = tkey
                        # Include lot debug info
                        matching_lots = [lot_item for lot_item in lots if lot_item["name"] == tkey]
                        if matching_lots:
                            debug_info["lot"] = {
                                "name": matching_lots[0]["name"],
                                "longitude": round(matching_lots[0]["longitude"], 4),
                                "house": matching_lots[0]["house"],
                                "formula": matching_lots[0]["formula"],
                            }

                    ev = _build_aspect_activation(
                        technique=tech,
                        family="transit",
                        source_planet=tname,
                        source_longitude=tlon,
                        target_key=tkey,
                        target_type=ttype,
                        target_frame=target_frame,
                        target_longitude=tlon_target,
                        aspect_name=best_aspect,
                        orb=orb,
                        applying=applying,
                        phase=phase,
                        strength=strength,
                        polarity=polarity,
                        active_from=active_from,
                        exact_at=exact_at,
                        active_until=active_until,
                        evidence=evidence,
                        debug=debug_info,
                        **extra_kw,
                    )
                    activations.append(ev)

                    # Index
                    if ttype == "planet":
                        by_planet.setdefault(tkey.upper(), []).append(ev.id)
                    elif ttype == "angle":
                        by_angle.setdefault(tkey.upper(), []).append(ev.id)
                    elif ttype == "lot":
                        by_lot.setdefault(tkey.upper(), []).append(ev.id)

        elif tech in ("annual_profection", "monthly_profection"):
            if tech == "annual_profection":
                # ── Annual profection ──────────────────────────────
                birth_local = _local_date(birth_date, birth_tz)
                target_local = _local_date(target_date, target_tz)
                age = _completed_years(birth_local, target_local)
                annual_house = (age % 12) + 1

                # Find sign on annual house cusp
                annual_house_cusp = None
                for h in natal_houses_raw:
                    if h["number"] == annual_house:
                        annual_house_cusp = h
                        break
                annual_house_sign = annual_house_cusp["sign"] if annual_house_cusp else "Aries"
                annual_house_lon = annual_house_cusp["cusp"] if annual_house_cusp else 0.0
                lord_of_year = _ruler_of_sign(annual_house_sign)

                activation_rules = _load_activation_rules()
                annual_strength = _get_period_strength(activation_rules, "annual_profection")

                # calculate annual start and until dates
                annual_start = safe_replace_year(birth_local, target_local.year)
                if annual_start > target_local:
                    annual_start = safe_replace_year(birth_local, target_local.year - 1)
                annual_next = safe_replace_year(birth_local, annual_start.year + 1)
                annual_until = annual_next - timedelta(days=1)

                annual_start_iso = annual_start.isoformat()
                annual_until_iso = annual_until.isoformat()

                # House activation
                house_ev_id = f"annual_profection__HOUSE__{annual_house}"
                house_ev = ActivationEvidence(
                    id=house_ev_id,
                    technique="annual_profection",
                    technique_family="profection",
                    target_type="house",
                    target_key=str(annual_house),
                    kind="profected_house",
                    source_frame="natal",
                    target_frame="natal",
                    house=annual_house,
                    active_from=annual_start_iso,
                    exact_at=None,
                    active_until=annual_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=annual_strength,
                    evidence=f"Annual profection activates house {annual_house}",
                    debug={
                        "age": age,
                        "birth_local_date": birth_date,
                        "target_local_date": target_date,
                        "annual_year_start": annual_start_iso,
                        "house": annual_house,
                        "house_cusp_longitude": round(annual_house_lon, 4),
                        "house_cusp_sign": annual_house_sign,
                        "ruler": lord_of_year,
                        "ruler_system": "traditional",
                        "resolved_house_system": resolved_house_system,
                    },
                )
                activations.append(house_ev)
                by_house.setdefault(str(annual_house), []).append(house_ev_id)

                # Lord activation
                lord_ev_id = f"annual_profection__LORD_OF_YEAR__{lord_of_year}"
                lord_ev = ActivationEvidence(
                    id=lord_ev_id,
                    technique="annual_profection",
                    technique_family="profection",
                    target_type="planet",
                    target_key=lord_of_year,
                    kind="lord_of_year",
                    source_frame="natal",
                    target_frame="natal",
                    target_planet=lord_of_year,
                    active_from=annual_start_iso,
                    exact_at=None,
                    active_until=annual_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=annual_strength,
                    evidence=f"{_display_name(lord_of_year)} is lord of year for annual profection house {annual_house}",
                    debug={
                        "age": age,
                        "birth_local_date": birth_date,
                        "target_local_date": target_date,
                        "house": annual_house,
                        "house_cusp_longitude": round(annual_house_lon, 4),
                        "house_cusp_sign": annual_house_sign,
                        "ruler": lord_of_year,
                        "ruler_system": "traditional",
                        "resolved_house_system": resolved_house_system,
                    },
                )
                activations.append(lord_ev)
                by_planet.setdefault(lord_of_year, []).append(lord_ev_id)

            elif tech == "monthly_profection":
                # ── Monthly profection ─────────────────────────────
                birth_local = _local_date(birth_date, birth_tz)
                target_local = _local_date(target_date, target_tz)
                age = _completed_years(birth_local, target_local)
                annual_house = (age % 12) + 1

                # Annual year start = most recent birthday on or before target
                annual_year_start = safe_replace_year(birth_local, target_local.year)
                if annual_year_start > target_local:
                    annual_year_start = safe_replace_year(birth_local, target_local.year - 1)

                # Count completed monthly anniversaries — non-drifting from annual_year_start
                completed_month_steps = 0
                for step in range(1, 13):
                    anniversary = _add_months_with_clamp(annual_year_start, step)
                    if anniversary <= target_local:
                        completed_month_steps = step
                    else:
                        break

                monthly_house = ((annual_house - 1 + completed_month_steps) % 12) + 1

                # Find sign on monthly house cusp
                monthly_house_cusp = None
                for h in natal_houses_raw:
                    if h["number"] == monthly_house:
                        monthly_house_cusp = h
                        break
                monthly_house_sign = monthly_house_cusp["sign"] if monthly_house_cusp else "Aries"
                monthly_house_lon = monthly_house_cusp["cusp"] if monthly_house_cusp else 0.0
                lord_of_month = _ruler_of_sign(monthly_house_sign)

                activation_rules = _load_activation_rules()
                monthly_strength = _get_period_strength(activation_rules, "monthly_profection")

                # calculate monthly start and until dates
                monthly_start = _add_months_with_clamp(annual_year_start, completed_month_steps)
                monthly_next = _add_months_with_clamp(annual_year_start, completed_month_steps + 1)
                monthly_until = monthly_next - timedelta(days=1)

                monthly_start_iso = monthly_start.isoformat()
                monthly_until_iso = monthly_until.isoformat()

                # House activation
                house_ev_id = f"monthly_profection__HOUSE__{monthly_house}"
                house_ev = ActivationEvidence(
                    id=house_ev_id,
                    technique="monthly_profection",
                    technique_family="profection",
                    target_type="house",
                    target_key=str(monthly_house),
                    kind="monthly_profected_house",
                    source_frame="natal",
                    target_frame="natal",
                    house=monthly_house,
                    active_from=monthly_start_iso,
                    exact_at=None,
                    active_until=monthly_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=monthly_strength,
                    evidence=f"Monthly profection activates house {monthly_house}",
                    debug={
                        "age": age,
                        "birth_local_date": birth_date,
                        "target_local_date": target_date,
                        "annual_year_start": annual_year_start.isoformat(),
                        "completed_month_steps": completed_month_steps,
                        "house": monthly_house,
                        "house_cusp_longitude": round(monthly_house_lon, 4),
                        "house_cusp_sign": monthly_house_sign,
                        "ruler": lord_of_month,
                        "ruler_system": "traditional",
                        "resolved_house_system": resolved_house_system,
                    },
                )
                activations.append(house_ev)
                by_house.setdefault(str(monthly_house), []).append(house_ev_id)

                # Lord activation
                lord_ev_id = f"monthly_profection__LORD_OF_MONTH__{lord_of_month}"
                lord_ev = ActivationEvidence(
                    id=lord_ev_id,
                    technique="monthly_profection",
                    technique_family="profection",
                    target_type="planet",
                    target_key=lord_of_month,
                    kind="lord_of_month",
                    source_frame="natal",
                    target_frame="natal",
                    target_planet=lord_of_month,
                    active_from=monthly_start_iso,
                    exact_at=None,
                    active_until=monthly_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=monthly_strength,
                    evidence=f"{_display_name(lord_of_month)} is lord of month for monthly profection house {monthly_house}",
                    debug={
                        "age": age,
                        "birth_local_date": birth_date,
                        "target_local_date": target_date,
                        "annual_year_start": annual_year_start.isoformat(),
                        "completed_month_steps": completed_month_steps,
                        "house": monthly_house,
                        "house_cusp_longitude": round(monthly_house_lon, 4),
                        "house_cusp_sign": monthly_house_sign,
                        "ruler": lord_of_month,
                        "ruler_system": "traditional",
                        "resolved_house_system": resolved_house_system,
                    },
                )
                activations.append(lord_ev)
                by_planet.setdefault(lord_of_month, []).append(lord_ev_id)

        elif tech in ("firdar_major", "firdar_minor"):
            # Firdar context is computed once for both techniques before the loop.
            # firdar_ctx is a tuple (context, major_strength, minor_strength, bounds) set
            # before the loop when any firdar technique is active.
            if firdar_ctx is None:
                firdar_canon = firdar_service._load_firdar_canon()
                birth_date_parsed = _local_date(birth_date, birth_tz)
                firdar_result = firdar_service.calculate_firdar(
                    birth_local=birth_date_parsed,
                    target_local=_local_date(target_date, target_tz),
                    is_day_birth=is_day,
                    sun_house=natal_sun_house,
                    canon=firdar_canon,
                )
                ar = _load_activation_rules()
                major_strength = _get_period_strength(ar, "firdar_major")
                minor_strength = _get_period_strength(ar, "firdar_minor")
                firdar_bounds = firdar_service.calculate_firdar_period_bounds(
                    birth_local=birth_date_parsed,
                    context=firdar_result,
                )
                firdar_ctx = (firdar_result, major_strength, minor_strength, firdar_bounds)
            else:
                firdar_result, major_strength, minor_strength, firdar_bounds = firdar_ctx

            if tech == "firdar_major":
                major_ev_id = f"firdar_major__PERIOD_LORD__{firdar_result.major_lord}"
                major_ev = ActivationEvidence(
                    id=major_ev_id,
                    technique="firdar_major",
                    technique_family="firdar",
                    target_type="planet",
                    target_key=firdar_result.major_lord,
                    kind="major_period_lord",
                    source_frame="natal",
                    target_frame="natal",
                    target_planet=firdar_result.major_lord,
                    active_from=firdar_bounds.major_active_from.isoformat(),
                    exact_at=None,
                    active_until=firdar_bounds.major_active_until.isoformat(),
                    phase="period",
                    polarity="neutral",
                    strength=major_strength,
                    evidence=f"{_display_name(firdar_result.major_lord)} is major firdar lord on {target_date}",
                    debug={
                        "schema_version": firdar_result.schema_version,
                        "is_day_birth": firdar_result.is_day_birth,
                        "sect_basis": "geometric_sun_altitude",
                        "sect_polar_condition": sect_polar_condition,
                        "sun_altitude_deg": round(sun_altitude_deg, 6),
                        "sun_house": firdar_result.sun_house,
                        "sun_house_role": "audit_only",
                        "birth_local_date": birth_date,
                        "target_local_date": target_date,
                        "age_years": round(firdar_result.age_years, 8),
                        "cycle_age": round(firdar_result.cycle_age, 8),
                        "cycle_index": firdar_result.cycle_index,
                        "cycle_years": firdar_result.cycle_years,
                        "major_lord": firdar_result.major_lord,
                        "major_start_age": round(firdar_result.major_start_age, 4),
                        "major_end_age": round(firdar_result.major_end_age, 4),
                        "major_years": round(firdar_result.major_years, 4),
                    },
                )
                activations.append(major_ev)
                by_planet.setdefault(firdar_result.major_lord, []).append(major_ev_id)

            if tech == "firdar_minor":
                minor_ev_id = f"firdar_minor__SUBPERIOD_LORD__{firdar_result.minor_lord}"
                minor_ev = ActivationEvidence(
                    id=minor_ev_id,
                    technique="firdar_minor",
                    technique_family="firdar",
                    target_type="planet",
                    target_key=firdar_result.minor_lord,
                    kind="minor_period_lord",
                    source_frame="natal",
                    target_frame="natal",
                    target_planet=firdar_result.minor_lord,
                    active_from=firdar_bounds.minor_active_from.isoformat(),
                    exact_at=None,
                    active_until=firdar_bounds.minor_active_until.isoformat(),
                    phase="period",
                    polarity="neutral",
                    strength=minor_strength,
                    evidence=f"{_display_name(firdar_result.minor_lord)} is minor firdar lord on {target_date} within {_display_name(firdar_result.major_lord)} major firdar",
                    debug={
                        "schema_version": firdar_result.schema_version,
                        "is_day_birth": firdar_result.is_day_birth,
                        "sect_basis": "geometric_sun_altitude",
                        "sect_polar_condition": sect_polar_condition,
                        "sun_altitude_deg": round(sun_altitude_deg, 6),
                        "sun_house": firdar_result.sun_house,
                        "sun_house_role": "audit_only",
                        "birth_local_date": birth_date,
                        "target_local_date": target_date,
                        "age_years": round(firdar_result.age_years, 8),
                        "cycle_age": round(firdar_result.cycle_age, 8),
                        "cycle_index": firdar_result.cycle_index,
                        "cycle_years": firdar_result.cycle_years,
                        "major_lord": firdar_result.major_lord,
                        "major_start_age": round(firdar_result.major_start_age, 4),
                        "major_end_age": round(firdar_result.major_end_age, 4),
                        "major_years": round(firdar_result.major_years, 4),
                        "minor_lord": firdar_result.minor_lord,
                        "minor_index": firdar_result.minor_index,
                        "minor_start_age": round(firdar_result.minor_start_age, 10),
                        "minor_end_age": round(firdar_result.minor_end_age, 10),
                        "minor_sequence": firdar_result.minor_sequence,
                    },
                )
                activations.append(minor_ev)
                by_planet.setdefault(firdar_result.minor_lord, []).append(minor_ev_id)

        elif tech in ("solar_return", "lunar_return"):
            # Load activation rules for return strengths
            activation_rules = _load_activation_rules()

            # Location policy
            if current_location:
                ret_lat = current_location["lat"]
                ret_lon = current_location["lon"]
                ret_tz = current_location.get("tz", target_tz)
                location_source = "current_location"
                location_reason = "explicit_current_location"
            else:
                ret_lat = birth_lat
                ret_lon = birth_lon
                ret_tz = birth_tz
                location_source = "birth_location"
                location_reason = "current_location_missing"
                fallback_warning = "return_location_fallback:birth_location:current_location_missing"
                if fallback_warning not in warnings_list:
                    warnings_list.append(fallback_warning)

            location_policy = "current_location_if_known_else_birth_location"

            if tech == "solar_return":
                # ── Solar return ──────────────────────────────────
                target_year = _local_date(target_date, target_tz).year

                # Determine correct solar return year based on target date
                natal_sun_lon_tmp = natal_sun.get("longitude", 0.0)

                birth_parts = birth_date.split("-")
                birth_month = int(birth_parts[1])
                birth_day = int(birth_parts[2])

                candidate_jd = find_solar_return_jd(
                    natal_sun_longitude=natal_sun_lon_tmp,
                    birth_month=birth_month,
                    birth_day=birth_day,
                    target_year=target_year,
                )
                if candidate_jd > target_jd:
                    # Current return is previous year
                    sr_year = target_year - 1
                else:
                    sr_year = target_year

                sr = calculate_solar_return(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    birth_tz=birth_tz,
                    birth_lat=birth_lat,
                    birth_lon=birth_lon,
                    target_year=sr_year,
                    house_system=house_system,
                    return_lat=ret_lat,
                    return_lon=ret_lon,
                    return_tz=ret_tz,
                    natal_sun_longitude=natal_sun_lon_tmp,
                )

                # Next solar return for bounds
                next_sr_jd = find_solar_return_jd(
                    natal_sun_longitude=natal_sun_lon_tmp,
                    birth_month=birth_month,
                    birth_day=birth_day,
                    target_year=sr_year + 1,
                )

                active_from_iso = julian_day_to_utc_iso(sr.return_jd)
                exact_at_iso = active_from_iso
                active_until_iso = julian_day_to_utc_iso(next_sr_jd - 1.0 / 86400.0)
                if not sr.return_jd <= target_jd < next_sr_jd:
                    raise ValueError(
                        f"Solar return window invariant violated: {sr.return_jd} <= {target_jd} < {next_sr_jd}"
                    )

                # Find SR ASC/MC in natal houses
                sr_asc_natal_house = _find_house(sr.asc_lon, natal_houses_raw)
                sr_mc_natal_house = _find_house(sr.mc_lon, natal_houses_raw)

                # Chart ruler: ruler of SR ASC sign
                sr_asc_sign = get_sign(sr.asc_lon)
                chart_ruler = _ruler_of_sign(sr_asc_sign)

                # SR Moon return-chart house
                sr_moon = None
                for p in sr.chart_planets:
                    if p["name"] == "Moon":
                        sr_moon = p
                        break
                sr_moon_house = _find_house(sr_moon["longitude"], sr.chart_houses) if sr_moon else 1

                # Angular houses: 1, 4, 7, 10
                angular_houses = {1, 4, 7, 10}
                angular_planets = []
                for p in sr.chart_planets:
                    ph = _find_house(p["longitude"], sr.chart_houses)
                    if ph in angular_houses:
                        angular_planets.append((p, ph))

                # Debug common
                return_debug_base: dict[str, Any] = {
                    "return_type": "solar",
                    "return_jd": round(sr.return_jd, 8),
                    "return_utc_iso": sr.return_utc_iso,
                    "target_jd": target_jd,
                    "return_location_policy": location_policy,
                    "return_location_source": location_source,
                    "return_location_reason": location_reason,
                    "return_lat": ret_lat,
                    "return_lon": ret_lon,
                    "return_tz": ret_tz,
                    "resolved_house_system": sr.house_system,
                    "next_return_jd": round(next_sr_jd, 8),
                    "next_return_utc_iso": julian_day_to_utc_iso(next_sr_jd),
                    "active_until_utc": active_until_iso,
                }

                # 1. SR ASC in natal house
                asc_id = f"solar_return__ANGLE_ASC__NATAL_HOUSE_{sr_asc_natal_house}"
                asc_ev = ActivationEvidence(
                    id=asc_id,
                    technique="solar_return",
                    technique_family="return",
                    target_type="house",
                    target_key=str(sr_asc_natal_house),
                    kind="return_angle_in_natal_house",
                    source_frame="solar_return",
                    target_frame="natal",
                    house=sr_asc_natal_house,
                    active_from=active_from_iso,
                    exact_at=exact_at_iso,
                    active_until=active_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=_get_return_strength(activation_rules, "solar_return_angle_in_natal_house"),
                    evidence=f"Solar Return ASC falls in natal house {sr_asc_natal_house}",
                    debug={**return_debug_base, "return_angle": "ASC", "natal_house": sr_asc_natal_house},
                )
                activations.append(asc_ev)
                by_house.setdefault(str(sr_asc_natal_house), []).append(asc_id)

                # 2. SR MC in natal house
                mc_id = f"solar_return__ANGLE_MC__NATAL_HOUSE_{sr_mc_natal_house}"
                mc_ev = ActivationEvidence(
                    id=mc_id,
                    technique="solar_return",
                    technique_family="return",
                    target_type="house",
                    target_key=str(sr_mc_natal_house),
                    kind="return_angle_in_natal_house",
                    source_frame="solar_return",
                    target_frame="natal",
                    house=sr_mc_natal_house,
                    active_from=active_from_iso,
                    exact_at=exact_at_iso,
                    active_until=active_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=_get_return_strength(activation_rules, "solar_return_angle_in_natal_house"),
                    evidence=f"Solar Return MC falls in natal house {sr_mc_natal_house}",
                    debug={**return_debug_base, "return_angle": "MC", "natal_house": sr_mc_natal_house},
                )
                activations.append(mc_ev)
                by_house.setdefault(str(sr_mc_natal_house), []).append(mc_id)

                # 3. Chart ruler
                ruler_id = f"solar_return__CHART_RULER__{chart_ruler}"
                ruler_ev = ActivationEvidence(
                    id=ruler_id,
                    technique="solar_return",
                    technique_family="return",
                    target_type="planet",
                    target_key=chart_ruler,
                    kind="return_chart_ruler",
                    source_frame="solar_return",
                    target_frame="natal",
                    target_planet=chart_ruler,
                    active_from=active_from_iso,
                    exact_at=exact_at_iso,
                    active_until=active_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=_get_return_strength(activation_rules, "solar_return_chart_ruler"),
                    evidence=f"{_display_name(chart_ruler)} is Solar Return chart ruler",
                    debug={**return_debug_base, "chart_ruler": chart_ruler, "asc_sign": sr_asc_sign},
                )
                activations.append(ruler_ev)
                by_planet.setdefault(chart_ruler, []).append(ruler_id)

                # 4. SR Moon in return house
                if sr_moon:
                    moon_id = f"solar_return__MOON_HOUSE__{sr_moon_house}"
                    moon_ev = ActivationEvidence(
                        id=moon_id,
                        technique="solar_return",
                        technique_family="return",
                        target_type="house",
                        target_key=str(sr_moon_house),
                        kind="return_moon_house",
                        source_frame="solar_return",
                        target_frame="solar_return",
                        house=sr_moon_house,
                        active_from=active_from_iso,
                        exact_at=exact_at_iso,
                        active_until=active_until_iso,
                        phase="period",
                        polarity="neutral",
                        strength=_get_return_strength(activation_rules, "solar_return_moon_house"),
                        evidence=f"Solar Return Moon is in Solar Return house {sr_moon_house}",
                        debug={**return_debug_base, "moon_house": sr_moon_house},
                    )
                    activations.append(moon_ev)
                    by_house.setdefault(str(sr_moon_house), []).append(moon_id)

                # 5. SR angular planets
                for pdata, phouse in angular_planets:
                    pname = pdata["name"]
                    if pname == "Moon":
                        continue  # Moon already handled
                    ang_id = f"solar_return__ANGULAR_PLANET__{pname.upper()}__HOUSE_{phouse}"
                    ang_ev = ActivationEvidence(
                        id=ang_id,
                        technique="solar_return",
                        technique_family="return",
                        target_type="planet",
                        target_key=pname.upper(),
                        kind="return_angular_planet",
                        source_frame="solar_return",
                        target_frame="solar_return",
                        target_planet=pname.upper(),
                        house=phouse,
                        active_from=active_from_iso,
                        exact_at=exact_at_iso,
                        active_until=active_until_iso,
                        phase="period",
                        polarity="neutral",
                        strength=_get_return_strength(activation_rules, "solar_return_angular_planet"),
                        evidence=f"Solar Return {_display_name(pname.upper())} is angular in Solar Return house {phouse}",
                        debug={**return_debug_base, "angular_planet": pname, "angular_house": phouse},
                    )
                    activations.append(ang_ev)
                    by_house.setdefault(str(phouse), []).append(ang_id)
                    by_planet.setdefault(pname.upper(), []).append(ang_id)

            elif tech == "lunar_return":
                # ── Lunar return ──────────────────────────────────
                lr = calculate_lunar_return(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    birth_tz=birth_tz,
                    birth_lat=birth_lat,
                    birth_lon=birth_lon,
                    target_date=target_date,
                    target_time=target_time,
                    target_tz=target_tz,
                    house_system=house_system,
                    return_lat=ret_lat,
                    return_lon=ret_lon,
                    return_tz=ret_tz,
                    natal_moon_longitude=natal_by_name.get("Moon", {}).get("longitude", 0.0),
                )

                # Next lunar return for bounds
                next_lr_jd = find_next_lunar_return_jd(
                    natal_moon_longitude=lr.natal_moon_lon,
                    after_jd=lr.return_jd,
                )

                active_from_iso = julian_day_to_utc_iso(lr.return_jd)
                exact_at_iso = active_from_iso
                active_until_iso = julian_day_to_utc_iso(next_lr_jd - 1.0 / 86400.0)
                if not lr.return_jd <= target_jd < next_lr_jd:
                    raise ValueError(
                        f"Lunar return window invariant violated: {lr.return_jd} <= {target_jd} < {next_lr_jd}"
                    )

                # LR ASC/MC in natal houses
                lr_asc_natal_house = _find_house(lr.asc_lon, natal_houses_raw)
                lr_mc_natal_house = _find_house(lr.mc_lon, natal_houses_raw)

                # LR Moon return-chart house
                lr_moon = None
                for p in lr.chart_planets:
                    if p["name"] == "Moon":
                        lr_moon = p
                        break
                lr_moon_house = _find_house(lr_moon["longitude"], lr.chart_houses) if lr_moon else 1

                # Angular houses
                angular_houses = {1, 4, 7, 10}
                lr_angular_planets = []
                for p in lr.chart_planets:
                    ph = _find_house(p["longitude"], lr.chart_houses)
                    if ph in angular_houses:
                        lr_angular_planets.append((p, ph))

                lr_return_debug: dict[str, Any] = {
                    "return_type": "lunar",
                    "return_jd": round(lr.return_jd, 8),
                    "return_utc_iso": lr.return_utc_iso,
                    "target_jd": target_jd,
                    "return_location_policy": location_policy,
                    "return_location_source": location_source,
                    "return_location_reason": location_reason,
                    "return_lat": ret_lat,
                    "return_lon": ret_lon,
                    "return_tz": ret_tz,
                    "resolved_house_system": lr.house_system,
                    "next_return_jd": round(next_lr_jd, 8),
                    "next_return_utc_iso": julian_day_to_utc_iso(next_lr_jd),
                    "active_until_utc": active_until_iso,
                }

                # 1. LR Moon in return house
                if lr_moon:
                    moon_id = f"lunar_return__MOON_HOUSE__{lr_moon_house}"
                    moon_ev = ActivationEvidence(
                        id=moon_id,
                        technique="lunar_return",
                        technique_family="return",
                        target_type="house",
                        target_key=str(lr_moon_house),
                        kind="return_moon_house",
                        source_frame="lunar_return",
                        target_frame="lunar_return",
                        house=lr_moon_house,
                        active_from=active_from_iso,
                        exact_at=exact_at_iso,
                        active_until=active_until_iso,
                        phase="period",
                        polarity="neutral",
                        strength=_get_return_strength(activation_rules, "lunar_return_moon_house"),
                        evidence=f"Lunar Return Moon is in Lunar Return house {lr_moon_house}",
                        debug={**lr_return_debug, "moon_house": lr_moon_house},
                    )
                    activations.append(moon_ev)
                    by_house.setdefault(str(lr_moon_house), []).append(moon_id)

                # 2. LR ASC in natal house
                asc_id = f"lunar_return__ANGLE_ASC__NATAL_HOUSE_{lr_asc_natal_house}"
                asc_ev = ActivationEvidence(
                    id=asc_id,
                    technique="lunar_return",
                    technique_family="return",
                    target_type="house",
                    target_key=str(lr_asc_natal_house),
                    kind="return_angle_in_natal_house",
                    source_frame="lunar_return",
                    target_frame="natal",
                    house=lr_asc_natal_house,
                    active_from=active_from_iso,
                    exact_at=exact_at_iso,
                    active_until=active_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=_get_return_strength(activation_rules, "lunar_return_angle_in_natal_house"),
                    evidence=f"Lunar Return ASC falls in natal house {lr_asc_natal_house}",
                    debug={**lr_return_debug, "return_angle": "ASC", "natal_house": lr_asc_natal_house},
                )
                activations.append(asc_ev)
                by_house.setdefault(str(lr_asc_natal_house), []).append(asc_id)

                # 3. LR MC in natal house
                mc_id = f"lunar_return__ANGLE_MC__NATAL_HOUSE_{lr_mc_natal_house}"
                mc_ev = ActivationEvidence(
                    id=mc_id,
                    technique="lunar_return",
                    technique_family="return",
                    target_type="house",
                    target_key=str(lr_mc_natal_house),
                    kind="return_angle_in_natal_house",
                    source_frame="lunar_return",
                    target_frame="natal",
                    house=lr_mc_natal_house,
                    active_from=active_from_iso,
                    exact_at=exact_at_iso,
                    active_until=active_until_iso,
                    phase="period",
                    polarity="neutral",
                    strength=_get_return_strength(activation_rules, "lunar_return_angle_in_natal_house"),
                    evidence=f"Lunar Return MC falls in natal house {lr_mc_natal_house}",
                    debug={**lr_return_debug, "return_angle": "MC", "natal_house": lr_mc_natal_house},
                )
                activations.append(mc_ev)
                by_house.setdefault(str(lr_mc_natal_house), []).append(mc_id)

                # 4. LR angular planets
                for pdata, phouse in lr_angular_planets:
                    pname = pdata["name"]
                    if pname == "Moon":
                        continue
                    ang_id = f"lunar_return__ANGULAR_PLANET__{pname.upper()}__HOUSE_{phouse}"
                    ang_ev = ActivationEvidence(
                        id=ang_id,
                        technique="lunar_return",
                        technique_family="return",
                        target_type="planet",
                        target_key=pname.upper(),
                        kind="return_angular_planet",
                        source_frame="lunar_return",
                        target_frame="lunar_return",
                        target_planet=pname.upper(),
                        house=phouse,
                        active_from=active_from_iso,
                        exact_at=exact_at_iso,
                        active_until=active_until_iso,
                        phase="period",
                        polarity="neutral",
                        strength=_get_return_strength(activation_rules, "lunar_return_angular_planet"),
                        evidence=f"Lunar Return {_display_name(pname.upper())} is angular in Lunar Return house {phouse}",
                        debug={**lr_return_debug, "angular_planet": pname, "angular_house": phouse},
                    )
                    activations.append(ang_ev)
                    by_house.setdefault(str(phouse), []).append(ang_id)
                    by_planet.setdefault(pname.upper(), []).append(ang_id)

        elif tech == "solar_arc":
            from solarsage.services.progressions import (
                calculate_solar_arc_context, solar_arc_aspects, _get_progression_strength,
            )
            sa_ctx = calculate_solar_arc_context(
                birth_date=birth_date, birth_time=birth_time, birth_tz=birth_tz,
                birth_lat=birth_lat, birth_lon=birth_lon,
                target_date=target_date, target_time=target_time, target_tz=target_tz,
                house_system=house_system,
            )
            aspects = solar_arc_aspects(sa_ctx)
            base_strength = _get_progression_strength("solar_arc_aspect")

            for asp in aspects:
                source_key = asp["source_key"]
                target_key = asp["target_key"]
                target_type = asp["target_type"]
                aspect_name = asp["aspect"]
                orb = asp["orb"]
                strength = asp["strength"]
                polarity = asp["polarity"]

                if target_type == "planet":
                    tgt = target_key
                    aid = f"solar_arc__{source_key}__{aspect_name.upper()}__NATAL_{target_key}"
                elif target_type == "angle":
                    tgt = target_key
                    aid = f"solar_arc__{source_key}__{aspect_name.upper()}__NATAL_ANGLE_{target_key}"
                else:
                    tgt = target_key
                    aid = f"solar_arc__{source_key}__{aspect_name.upper()}__NATAL_LOT_{target_key}"

                ev = ActivationEvidence(
                    id=aid,
                    technique="solar_arc",
                    technique_family="progression",
                    target_type=target_type,
                    target_key=tgt,
                    kind="solar_arc_aspect",
                    source_frame="solar_arc",
                    target_frame="natal" if target_type == "planet" else target_type,
                    target_planet=tgt if target_type == "planet" else None,
                    angle=tgt if target_type == "angle" else None,
                    lot=tgt if target_type == "lot" else None,
                    aspect=aspect_name,
                    orb=orb,
                    phase="period",
                    polarity=polarity,
                    strength=strength,
                    evidence=f"Solar Arc {_display_name(asp['source_key'])} {aspect_name} natal {_display_name(tgt)}, orb {orb}°",
                    debug={
                        "progression_method": "solar_arc",
                        "birth_jd": round(sa_ctx.birth_jd, 4),
                        "target_jd": round(sa_ctx.target_jd, 4),
                        "age_years": round(sa_ctx.age_years, 8),
                        "progressed_jd": round(sa_ctx.progressed_jd, 4),
                        "progressed_utc_iso": sa_ctx.progressed_utc_iso,
                        "max_orb": sa_ctx.max_orb,
                        "resolved_house_system": sa_ctx.resolved_house_system,
                        "solar_arc_delta": round(sa_ctx.solar_arc_delta, 4),
                        "natal_sun_longitude": round(sa_ctx.natal_sun_lon, 4),
                        "progressed_sun_longitude": round(sa_ctx.progressed_sun_lon, 4),
                        "solar_arc_source_longitude": round(asp["source_lon"], 4),
                        "source_longitude": round(asp["source_lon"], 4),
                        "target_longitude": round(asp["target_lon"], 4),
                        "angular_distance": asp["angular_distance"],
                        "aspect_angle": ASPECT_ANGLES.get(aspect_name, 0),
                        "orb": orb,
                        "orb_factor": round(max(0, 1 - orb / sa_ctx.max_orb), 4),
                        "base_strength": base_strength,
                    },
                )
                activations.append(ev)

                if target_type == "planet":
                    by_planet.setdefault(target_key, []).append(aid)
                elif target_type == "angle":
                    by_angle.setdefault(target_key, []).append(aid)
                elif target_type == "lot":
                    by_lot.setdefault(target_key, []).append(aid)

        elif tech == "secondary_progression":
            from solarsage.services.progressions import (
                calculate_secondary_progression_context,
                progressed_moon_aspects, _get_progression_strength,
            )
            sp_ctx = calculate_secondary_progression_context(
                birth_date=birth_date, birth_time=birth_time, birth_tz=birth_tz,
                birth_lat=birth_lat, birth_lon=birth_lon,
                target_date=target_date, target_time=target_time, target_tz=target_tz,
                house_system=house_system,
            )

            # Progressed Moon aspects
            moon_aspects = progressed_moon_aspects(sp_ctx)
            moon_base = _get_progression_strength("progressed_moon_aspect")
            for asp in moon_aspects:
                target_key = asp["target_key"]
                target_type = asp["target_type"]
                aspect_name = asp["aspect"]
                orb = asp["orb"]

                if target_type == "planet":
                    aid = f"secondary_progression__MOON__{aspect_name.upper()}__NATAL_{target_key}"
                elif target_type == "angle":
                    aid = f"secondary_progression__MOON__{aspect_name.upper()}__NATAL_ANGLE_{target_key}"
                else:
                    aid = f"secondary_progression__MOON__{aspect_name.upper()}__NATAL_LOT_{target_key}"

                ev = ActivationEvidence(
                    id=aid,
                    technique="secondary_progression",
                    technique_family="progression",
                    target_type=target_type,
                    target_key=target_key,
                    kind="progressed_moon_aspect",
                    source_frame="progressed",
                    target_frame="natal" if target_type == "planet" else target_type,
                    target_planet=target_key if target_type == "planet" else None,
                    angle=target_key if target_type == "angle" else None,
                    lot=target_key if target_type == "lot" else None,
                    aspect=aspect_name,
                    orb=orb,
                    phase="period",
                    polarity=asp["polarity"],
                    strength=asp["strength"],
                    evidence=f"Progressed Moon {aspect_name} natal {_display_name(target_key)}, orb {orb}°",
                    debug={
                        "progression_method": "secondary_progression",
                        "birth_jd": round(sp_ctx.birth_jd, 4),
                        "target_jd": round(sp_ctx.target_jd, 4),
                        "age_years": round(sp_ctx.age_years, 8),
                        "progressed_jd": round(sp_ctx.progressed_jd, 4),
                        "progressed_utc_iso": sp_ctx.progressed_utc_iso,
                        "max_orb": sp_ctx.max_orb,
                        "resolved_house_system": sp_ctx.resolved_house_system,
                        "source_longitude": round(asp["source_lon"], 4),
                        "target_longitude": round(asp["target_lon"], 4),
                        "angular_distance": asp["angular_distance"],
                        "aspect_angle": ASPECT_ANGLES.get(aspect_name, 0),
                        "orb": orb,
                        "orb_factor": round(max(0, 1 - orb / sp_ctx.max_orb), 4),
                        "base_strength": moon_base,
                    },
                )
                activations.append(ev)

                if target_type == "planet":
                    by_planet.setdefault(target_key, []).append(aid)
                elif target_type == "angle":
                    by_angle.setdefault(target_key, []).append(aid)
                elif target_type == "lot":
                    by_lot.setdefault(target_key, []).append(aid)

            # Progressed Sun transitions
            from solarsage.services.progressions import progressed_sun_transitions as pst_fn
            transitions = pst_fn(sp_ctx, birth_lat, birth_lon, house_system, sp_ctx.max_orb)
            for trans in transitions:
                tt = trans["transition_type"]
                if tt == "sign":
                    next_s = trans.get("next_sign", "")
                    prev_s = trans.get("previous_sign", "")
                    sig = next_s or prev_s
                    aid = f"secondary_progression__SUN_SIGN_TRANSITION__{sig}"
                    ev = ActivationEvidence(
                        id=aid,
                        technique="secondary_progression",
                        technique_family="progression",
                        target_type="planet",
                        target_key="SUN",
                        kind="progressed_sun_sign_transition",
                        source_frame="progressed",
                        target_frame="natal",
                        target_planet="SUN",
                        phase="period",
                        polarity="neutral",
                        strength=trans["strength"],
                        evidence=f"Progressed Sun near {sig} sign transition, distance {trans['distance_to_boundary']}°",
                        debug={
                            "progression_method": "secondary_progression",
                            "birth_jd": round(sp_ctx.birth_jd, 4),
                            "target_jd": round(sp_ctx.target_jd, 4),
                            "age_years": round(sp_ctx.age_years, 8),
                            "progressed_jd": round(sp_ctx.progressed_jd, 4),
                            "progressed_utc_iso": sp_ctx.progressed_utc_iso,
                            "max_orb": sp_ctx.max_orb,
                            "resolved_house_system": sp_ctx.resolved_house_system,
                            "transition_type": trans.get("transition_type"),
                            "current_sign": trans.get("current_sign"),
                            "previous_sign": trans.get("previous_sign"),
                            "next_sign": trans.get("next_sign"),
                            "current_house": trans.get("current_house"),
                            "target_house": trans.get("target_house"),
                            "boundary_longitude": trans["boundary_longitude"],
                            "distance_to_boundary": trans["distance_to_boundary"],
                            "base_strength": trans.get("base_strength"),
                            "orb_factor": trans.get("orb_factor"),
                        },
                    )
                    activations.append(ev)
                    by_planet.setdefault("SUN", []).append(aid)

                elif tt == "house":
                    th = trans["target_house"]
                    aid = f"secondary_progression__SUN_HOUSE_TRANSITION__{th}"
                    ev = ActivationEvidence(
                        id=aid,
                        technique="secondary_progression",
                        technique_family="progression",
                        target_type="house",
                        target_key=str(th),
                        kind="progressed_sun_house_transition",
                        source_frame="progressed",
                        target_frame="natal",
                        house=th,
                        phase="period",
                        polarity="neutral",
                        strength=trans["strength"],
                        evidence=f"Progressed Sun near natal house {th} cusp, distance {trans['distance_to_boundary']}°",
                        debug={
                            "progression_method": "secondary_progression",
                            "birth_jd": round(sp_ctx.birth_jd, 4),
                            "target_jd": round(sp_ctx.target_jd, 4),
                            "age_years": round(sp_ctx.age_years, 8),
                            "progressed_jd": round(sp_ctx.progressed_jd, 4),
                            "progressed_utc_iso": sp_ctx.progressed_utc_iso,
                            "max_orb": sp_ctx.max_orb,
                            "resolved_house_system": sp_ctx.resolved_house_system,
                            "transition_type": trans.get("transition_type"),
                            "current_sign": trans.get("current_sign"),
                            "previous_sign": trans.get("previous_sign"),
                            "next_sign": trans.get("next_sign"),
                            "current_house": trans.get("current_house"),
                            "target_house": trans.get("target_house"),
                            "boundary_longitude": trans["boundary_longitude"],
                            "distance_to_boundary": trans["distance_to_boundary"],
                            "base_strength": trans.get("base_strength"),
                            "orb_factor": trans.get("orb_factor"),
                        },
                    )
                    activations.append(ev)
                    by_house.setdefault(str(th), []).append(aid)

        elif tech == "eclipse_window":
            from solarsage.services.eclipses import find_eclipses
            ecl_activations = find_eclipses(
                birth_date=birth_date, birth_time=birth_time, birth_tz=birth_tz,
                birth_lat=birth_lat, birth_lon=birth_lon,
                target_date=target_date, target_time=target_time, target_tz=target_tz,
                house_system=house_system,
            )
            for ed in ecl_activations:
                ev = ActivationEvidence(**ed)
                activations.append(ev)
                tt = ed["target_type"]
                if tt == "planet":
                    by_planet.setdefault(ed["target_key"], []).append(ed["id"])
                elif tt == "angle":
                    by_angle.setdefault(ed["target_key"], []).append(ed["id"])
                elif tt == "lot":
                    by_lot.setdefault(ed["target_key"], []).append(ed["id"])

    return ActivationLayer(
        calculation_version=CALCULATION_VERSION,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
        target_date=target_date,
        target_time=target_time,
        target_tz=target_tz,
        house_system=resolved_house_system,
        activations=activations,
        by_planet=by_planet,
        by_house=by_house,
        by_lot=by_lot,
        by_angle=by_angle,
        warnings=warnings_list,
    )
