# ############################################################################
# AI_HEADER: MODULE_SIDECAR_PROGRESSIONS — Solar arc and secondary progression.
# ROLE: Computes solar_arc and secondary_progression planetary positions,
#       aspect detections, and Sun transitions for W3.5 activation layer.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-PROGRESSIONS
# purpose: Calculate solar arc aspects, progressed Moon aspects, and
#          progressed Sun transitions for the activation layer.
# owns:
#   - apps/solarsage/solarsage/services/progressions.py
# inputs: birth date/time/tz/lat/lon, target date/time/tz, house_system
# outputs: SolarArcContext, SecondaryProgressionContext
# dependencies: swisseph, ephemeris utils, activation_rules.v1.yml
# side_effects: none (pure computation)
# emitted_logs: none
# invariants:
#   - solar_arc_delta = normalize(progressed_sun - natal_sun)
#   - progressed JD = birth_JD + age_years (day-for-year)
# failure_policy: ValueError on invalid dates or inability to calculate
# END_MODULE_CONTRACT: M-SIDECAR-PROGRESSIONS

# START_MODULE_MAP: M-SIDECAR-PROGRESSIONS
# public_entrypoints:
#   - calculate_solar_arc_context
#   - calculate_secondary_progression_context
#   - solar_arc_aspects
#   - progressed_moon_aspects
#   - progressed_sun_transitions
# semantic_blocks:
#   - PROGRESSION_MATH: age/position calculation
#   - ASPECT_DETECTION: canonical aspect matching
#   - SUN_TRANSITIONS: sign/house boundary detection
# owned_tests:
#   - tests/test_solar_arc.py
#   - tests/test_secondary_progressions.py
# END_MODULE_MAP: M-SIDECAR-PROGRESSIONS

from __future__ import annotations

import os
import pathlib
from datetime import datetime, timezone
from typing import Any

import swisseph as swe
import yaml

from solarsage.utils.ephemeris import (
    calculate_julian_day,
    calculate_positions,
    calculate_houses_cusps,
)

# ── Canonical aspect map (reused from activation_builder) ────────────────────

from solarsage.services.activation_builder import ASPECT_ANGLES, _classify_polarity


def _angular_distance(lon1: float, lon2: float) -> float:
    raw = abs(lon1 - lon2) % 360.0
    if raw > 180.0:
        raw = 360.0 - raw
    return raw


def _normalize(lon: float) -> float:
    return lon % 360.0


def _find_house(longitude: float, houses: list[dict[str, Any]]) -> int:
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


# ── Canon loading ────────────────────────────────────────────────────────────


def _resolve_canon_path(relative: str) -> str:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent.parent.parent
    return os.path.join(root, relative)


def _load_aspect_rules() -> dict[str, Any]:
    path = _resolve_canon_path("grace/canon/aspect_rules.v1.yml")
    with open(path) as f:
        return yaml.safe_load(f)


def _load_activation_rules() -> dict[str, Any]:
    path = _resolve_canon_path("grace/canon/activation_rules.v1.yml")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_progression_orb(technique: str) -> float:
    """Load progression orb from canon for a specific technique.
    Raises KeyError if missing or non-numeric."""
    rules = _load_activation_rules()
    techniques = rules.get("techniques", {})
    tech = techniques.get(technique)
    if tech is None:
        raise KeyError(f"{technique}.orb not found in activation_rules.v1.yml")
    orb = tech.get("orb")
    if orb is None:
        raise KeyError(f"{technique}.orb not found in activation_rules.v1.yml")
    try:
        return float(orb)
    except (ValueError, TypeError):
        raise KeyError(f"{technique}.orb is non-numeric: {orb}")


def _get_progression_strength(kind: str, rules_override: dict | None = None) -> float:
    """Look up progression_base strength from canon. Raises KeyError if missing."""
    if rules_override is not None:
        base = rules_override.get("activation_strength", {}).get("progression_base", {})
        return float(base[kind])
    rules = _load_activation_rules()
    base = rules.get("activation_strength", {}).get("progression_base", {})
    return float(base[kind])


# ── Progression math ─────────────────────────────────────────────────────────


def _jd_to_utc_iso(jd: float) -> str:
    year, month, day, hour = swe.revjul(jd)
    minute = (hour - int(hour)) * 60
    second = (minute - int(minute)) * 60
    dt = datetime(
        int(year), int(month), int(day),
        int(hour), int(minute), int(second),
        tzinfo=timezone.utc,
    )
    return dt.isoformat()


def _compute_progressed_jd(birth_date: str, birth_time: str, birth_tz: str,
                           target_date: str, target_time: str, target_tz: str) -> float:
    """Compute progressed JD using day-for-year model:
    age_years = (target_jd - birth_jd) / 365.2425
    progressed_jd = birth_jd + age_years
    """
    birth_jd = calculate_julian_day(birth_date, birth_time, birth_tz)
    target_jd = calculate_julian_day(target_date, target_time, target_tz)
    age_years = (target_jd - birth_jd) / 365.2425
    progressed_jd = birth_jd + age_years
    return birth_jd, target_jd, age_years, progressed_jd


# ── Solar arc ────────────────────────────────────────────────────────────────


class SolarArcContext:
    """Holds solar arc calculation results."""

    def __init__(
        self,
        *,
        birth_jd: float,
        target_jd: float,
        age_years: float,
        progressed_jd: float,
        progressed_utc_iso: str,
        solar_arc_delta: float,
        natal_sun_lon: float,
        progressed_sun_lon: float,
        solar_arc_positions: dict[str, float],
        natal_positions: dict[str, dict],
        natal_houses: list[dict[str, Any]],
        natal_angles: dict[str, float],
        natal_lots: list[dict[str, Any]],
        resolved_house_system: str,
        max_orb: float,
    ) -> None:
        self.birth_jd = birth_jd
        self.target_jd = target_jd
        self.age_years = age_years
        self.progressed_jd = progressed_jd
        self.progressed_utc_iso = progressed_utc_iso
        self.solar_arc_delta = solar_arc_delta
        self.natal_sun_lon = natal_sun_lon
        self.progressed_sun_lon = progressed_sun_lon
        self.solar_arc_positions = solar_arc_positions
        self.natal_positions = natal_positions
        self.natal_houses = natal_houses
        self.natal_angles = natal_angles
        self.natal_lots = natal_lots
        self.resolved_house_system = resolved_house_system
        self.max_orb = max_orb


def calculate_solar_arc_context(
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
) -> SolarArcContext:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-PROGRESSIONS.calculate_solar_arc_context
    # purpose: Calculate solar arc delta and all solar arc positions.
    # inputs: birth data, target data, house_system
    # returns: SolarArcContext with delta, positions, natal data
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-PROGRESSIONS.calculate_solar_arc_context
    """Calculate solar arc context: progressed Sun, delta, and solar arc positions."""
    # Engine path is configured by core/ephemeris_runtime (single owner).
    birth_jd, target_jd, age_years, progressed_jd = _compute_progressed_jd(
        birth_date, birth_time, birth_tz, target_date, target_time, target_tz,
    )
    progressed_utc_iso = _jd_to_utc_iso(progressed_jd)

    # Natal positions
    natal_positions = calculate_positions(birth_jd)
    natal_by_name = {p["name"]: p for p in natal_positions}

    # Natal Sun
    natal_sun = natal_by_name.get("Sun", {})
    natal_sun_lon = natal_sun.get("longitude", 0.0)

    # Progressed Sun
    progressed_positions = calculate_positions(progressed_jd)
    progressed_by_name = {p["name"]: p for p in progressed_positions}
    progressed_sun = progressed_by_name.get("Sun", {})
    progressed_sun_lon = progressed_sun.get("longitude", 0.0)

    # Solar arc delta
    solar_arc_delta = _normalize(progressed_sun_lon - natal_sun_lon)

    # Natal houses and angles
    natal_houses_raw, natal_special_points, resolved_house_system = calculate_houses_cusps(
        birth_jd, birth_lat, birth_lon, house_system,
    )
    natal_angles = {}
    for sp in natal_special_points:
        if sp["name"] in ("ASC", "MC", "DSC", "IC"):
            natal_angles[sp["name"]] = sp["longitude"]
    # DSC = ASC + 180, IC = MC + 180
    if "ASC" in natal_angles:
        natal_angles["DSC"] = _normalize(natal_angles["ASC"] + 180.0)
    if "MC" in natal_angles:
        natal_angles["IC"] = _normalize(natal_angles["MC"] + 180.0)

    # Natal lots
    from solarsage.services.activation_builder import _is_day_chart
    from solarsage.services.activation_builder import _compute_lots
    natal_sun_house = _find_house(natal_sun_lon, natal_houses_raw) if natal_sun else None
    is_day = _is_day_chart(natal_sun_house)
    asc_lon = natal_angles.get("ASC", 0.0)
    dsc_lon = natal_angles.get("DSC", (asc_lon + 180.0) % 360.0)

    lots = _compute_lots(
        asc_lon=asc_lon,
        sun_lon=natal_sun_lon,
        moon_lon=natal_by_name.get("Moon", {}).get("longitude", 0.0),
        mercury_lon=natal_by_name.get("Mercury", {}).get("longitude", 0.0),
        venus_lon=natal_by_name.get("Venus", {}).get("longitude", 0.0),
        jupiter_lon=natal_by_name.get("Jupiter", {}).get("longitude", 0.0),
        saturn_lon=natal_by_name.get("Saturn", {}).get("longitude", 0.0),
        dsc_lon=dsc_lon,
        is_day=is_day,
    )
    for lot in lots:
        lot["house"] = _find_house(lot["longitude"], natal_houses_raw)

    # Solar arc positions
    solar_arc_positions: dict[str, float] = {}
    for pname, pdata in natal_by_name.items():
        sa_lon = _normalize(pdata["longitude"] + solar_arc_delta)
        solar_arc_positions[pname.upper()] = sa_lon

    # Add angles and lots
    for aname, alon in natal_angles.items():
        solar_arc_positions[f"ANGLE_{aname}"] = _normalize(alon + solar_arc_delta)
    for lot in lots:
        solar_arc_positions[f"LOT_{lot['name']}"] = _normalize(lot["longitude"] + solar_arc_delta)

    max_orb = _get_progression_orb("solar_arc")

    return SolarArcContext(
        birth_jd=birth_jd,
        target_jd=target_jd,
        age_years=age_years,
        progressed_jd=progressed_jd,
        progressed_utc_iso=progressed_utc_iso,
        solar_arc_delta=solar_arc_delta,
        natal_sun_lon=natal_sun_lon,
        progressed_sun_lon=progressed_sun_lon,
        solar_arc_positions=solar_arc_positions,
        natal_positions=natal_by_name,
        natal_houses=natal_houses_raw,
        natal_angles=natal_angles,
        natal_lots=lots,
        resolved_house_system=resolved_house_system,
        max_orb=max_orb,
    )


# ── Secondary progression ────────────────────────────────────────────────────


class SecondaryProgressionContext:
    """Holds secondary progression calculation results."""

    def __init__(
        self,
        *,
        birth_jd: float,
        target_jd: float,
        age_years: float,
        progressed_jd: float,
        progressed_utc_iso: str,
        progressed_moon_lon: float,
        natal_moon_lon: float,
        progressed_sun_lon: float,
        natal_sun_lon: float,
        natal_positions: dict[str, dict],
        natal_houses: list[dict[str, Any]],
        natal_angles: dict[str, float],
        natal_lots: list[dict[str, Any]],
        resolved_house_system: str,
        max_orb: float,
    ) -> None:
        self.birth_jd = birth_jd
        self.target_jd = target_jd
        self.age_years = age_years
        self.progressed_jd = progressed_jd
        self.progressed_utc_iso = progressed_utc_iso
        self.progressed_moon_lon = progressed_moon_lon
        self.natal_moon_lon = natal_moon_lon
        self.progressed_sun_lon = progressed_sun_lon
        self.natal_sun_lon = natal_sun_lon
        self.natal_positions = natal_positions
        self.natal_houses = natal_houses
        self.natal_angles = natal_angles
        self.natal_lots = natal_lots
        self.resolved_house_system = resolved_house_system
        self.max_orb = max_orb


def calculate_secondary_progression_context(
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
) -> SecondaryProgressionContext:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-PROGRESSIONS.calculate_secondary_progression_context
    # purpose: Calculate secondary progression context (progressed JD, positions, targets).
    # inputs: birth data, target data, house_system
    # returns: SecondaryProgressionContext
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-PROGRESSIONS.calculate_secondary_progression_context
    """Calculate secondary progression context."""
    # Engine path is configured by core/ephemeris_runtime (single owner).
    birth_jd, target_jd, age_years, progressed_jd = _compute_progressed_jd(
        birth_date, birth_time, birth_tz, target_date, target_time, target_tz,
    )
    progressed_utc_iso = _jd_to_utc_iso(progressed_jd)

    # Natal positions
    natal_positions = calculate_positions(birth_jd)
    natal_by_name = {p["name"]: p for p in natal_positions}

    # Progressed positions
    progressed_positions = calculate_positions(progressed_jd)
    progressed_by_name = {p["name"]: p for p in progressed_positions}

    natal_sun = natal_by_name.get("Sun", {})
    natal_sun_lon = natal_sun.get("longitude", 0.0)
    natal_moon = natal_by_name.get("Moon", {})
    natal_moon_lon = natal_moon.get("longitude", 0.0)
    progressed_sun = progressed_by_name.get("Sun", {})
    progressed_sun_lon = progressed_sun.get("longitude", 0.0)
    progressed_moon = progressed_by_name.get("Moon", {})
    progressed_moon_lon = progressed_moon.get("longitude", 0.0)

    # Natal houses/angles
    natal_houses_raw, natal_special_points, resolved_house_system = calculate_houses_cusps(
        birth_jd, birth_lat, birth_lon, house_system,
    )
    natal_angles = {}
    for sp in natal_special_points:
        if sp["name"] in ("ASC", "MC", "DSC", "IC"):
            natal_angles[sp["name"]] = sp["longitude"]
    if "ASC" in natal_angles:
        natal_angles["DSC"] = _normalize(natal_angles["ASC"] + 180.0)
    if "MC" in natal_angles:
        natal_angles["IC"] = _normalize(natal_angles["MC"] + 180.0)

    # Natal lots
    from solarsage.services.activation_builder import _is_day_chart
    from solarsage.services.activation_builder import _compute_lots
    natal_sun_house = _find_house(natal_sun_lon, natal_houses_raw) if natal_sun else None
    is_day = _is_day_chart(natal_sun_house)
    asc_lon = natal_angles.get("ASC", 0.0)
    dsc_lon = natal_angles.get("DSC", (asc_lon + 180.0) % 360.0)

    lots = _compute_lots(
        asc_lon=asc_lon,
        sun_lon=natal_sun_lon,
        moon_lon=natal_moon_lon,
        mercury_lon=natal_by_name.get("Mercury", {}).get("longitude", 0.0),
        venus_lon=natal_by_name.get("Venus", {}).get("longitude", 0.0),
        jupiter_lon=natal_by_name.get("Jupiter", {}).get("longitude", 0.0),
        saturn_lon=natal_by_name.get("Saturn", {}).get("longitude", 0.0),
        dsc_lon=dsc_lon,
        is_day=is_day,
    )
    for lot in lots:
        lot["house"] = _find_house(lot["longitude"], natal_houses_raw)

    max_orb = _get_progression_orb("secondary_progression")

    return SecondaryProgressionContext(
        birth_jd=birth_jd,
        target_jd=target_jd,
        age_years=age_years,
        progressed_jd=progressed_jd,
        progressed_utc_iso=progressed_utc_iso,
        progressed_moon_lon=progressed_moon_lon,
        natal_moon_lon=natal_moon_lon,
        progressed_sun_lon=progressed_sun_lon,
        natal_sun_lon=natal_sun_lon,
        natal_positions=natal_by_name,
        natal_houses=natal_houses_raw,
        natal_angles=natal_angles,
        natal_lots=lots,
        resolved_house_system=resolved_house_system,
        max_orb=max_orb,
    )


# ── Solar arc aspects ────────────────────────────────────────────────────────


def solar_arc_aspects(ctx: SolarArcContext) -> list[dict[str, Any]]:
    """Compute solar arc aspects: SA planets to natal personal planets,
    natal angles, and natal lots within orb."""
    aspects: list[dict[str, Any]] = []

    personal_targets = ["SUN", "MOON", "MERCURY", "VENUS", "MARS"]
    source_planets = sorted(
        k for k in ctx.solar_arc_positions.keys()
        if not k.startswith("ANGLE_") and not k.startswith("LOT_")
    )

    base_strength = _get_progression_strength("solar_arc_aspect")

    for sp_key in source_planets:
        sp_lon = ctx.solar_arc_positions[sp_key]

        # Against natal personal planets
        for tp_name in personal_targets:
            tp_data = ctx.natal_positions.get(tp_name.capitalize())
            if not tp_data:
                continue
            tp_lon = tp_data["longitude"]
            _check_and_add_aspect(aspects, sp_key, sp_lon, tp_name, "planet", tp_lon, ctx, base_strength)

        # Against natal angles
        for aname in sorted(ctx.natal_angles.keys()):
            alon = ctx.natal_angles[aname]
            _check_and_add_aspect(aspects, sp_key, sp_lon, aname, "angle", alon, ctx, base_strength)

        # Against natal lots
        for lot in ctx.natal_lots:
            _check_and_add_aspect(aspects, sp_key, sp_lon, lot["name"], "lot", lot["longitude"], ctx, base_strength)

    return aspects


def _check_and_add_aspect(
    aspects: list[dict[str, Any]],
    source_key: str,
    source_lon: float,
    target_key: str,
    target_type: str,
    target_lon: float,
    ctx: SolarArcContext | SecondaryProgressionContext,
    base_strength: float,
) -> None:
    """Check if source and target are within orb for any canonical aspect."""
    adist = _angular_distance(source_lon, target_lon)
    best_aspect: str | None = None
    best_diff: float | None = None
    for aname, aangle in ASPECT_ANGLES.items():
        diff = abs(adist - aangle)
        if diff <= ctx.max_orb:
            if best_diff is None or diff < best_diff:
                best_aspect = aname
                best_diff = diff

    if best_aspect is None:
        return

    orb = round(best_diff, 4)
    orb_factor = round(max(0, 1 - orb / ctx.max_orb), 4)
    strength = round(min(1.0, base_strength * orb_factor), 4)
    polarity = _classify_polarity(best_aspect)

    aspects.append({
        "source_key": source_key,
        "source_lon": round(source_lon, 4),
        "target_key": target_key,
        "target_type": target_type,
        "target_lon": round(target_lon, 4),
        "aspect": best_aspect,
        "orb": orb,
        "strength": strength,
        "polarity": polarity,
        "angular_distance": round(adist, 4),
        "base_strength": base_strength,
        "orb_factor": orb_factor,
    })


# ── Progressed Moon aspects ──────────────────────────────────────────────────


def progressed_moon_aspects(ctx: SecondaryProgressionContext) -> list[dict[str, Any]]:
    """Compute progressed Moon aspects to natal planets, angles, and lots."""
    aspects: list[dict[str, Any]] = []
    moon_lon = ctx.progressed_moon_lon
    base_strength = _get_progression_strength("progressed_moon_aspect")

    # Against all natal planets (sorted for determinism)
    for pname in sorted(ctx.natal_positions.keys()):
        pdata = ctx.natal_positions[pname]
        _check_and_add_aspect(aspects, "MOON", moon_lon, pname.upper(), "planet", pdata["longitude"], ctx, base_strength)

    # Against natal angles (sorted for determinism)
    for aname in sorted(ctx.natal_angles.keys()):
        _check_and_add_aspect(aspects, "MOON", moon_lon, aname, "angle", ctx.natal_angles[aname], ctx, base_strength)

    # Against natal lots
    for lot in ctx.natal_lots:
        _check_and_add_aspect(aspects, "MOON", moon_lon, lot["name"], "lot", lot["longitude"], ctx, base_strength)

    return aspects


# ── Progressed Sun transitions ───────────────────────────────────────────────


def progressed_sun_transitions(
    ctx: SecondaryProgressionContext,
    birth_lat: float,
    birth_lon: float,
    house_system: str,
    max_orb: float,
) -> list[dict[str, Any]]:
    """Detect progressed Sun near sign boundaries or natal house cusps."""
    transitions: list[dict[str, Any]] = []
    ps_lon = ctx.progressed_sun_lon
    sign_base = _get_progression_strength("progressed_sun_sign_transition")
    house_base = _get_progression_strength("progressed_sun_house_transition")

    # Sign boundaries
    current_sign_idx = int(ps_lon / 30)
    next_boundary = (current_sign_idx + 1) * 30.0
    prev_boundary = current_sign_idx * 30.0

    # Distance to next sign boundary (forward) — handles wrap-around
    dist_to_next = next_boundary - ps_lon
    if dist_to_next < 0:
        dist_to_next += 360.0
    # Distance to previous sign boundary (backward)
    dist_to_prev = ps_lon - prev_boundary

    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

    # Forward transition (toward next sign)
    if dist_to_next <= max_orb:
        target_sign_idx = (current_sign_idx + 1) % 12
        orb_factor = round(max(0, 1 - dist_to_next / max_orb), 4)
        transitions.append({
            "transition_type": "sign",
            "current_sign": signs[current_sign_idx],
            "previous_sign": None,
            "next_sign": signs[target_sign_idx],
            "current_house": None,
            "target_house": None,
            "boundary_longitude": round(next_boundary, 4),
            "distance_to_boundary": round(dist_to_next, 4),
            "strength": round(min(1.0, sign_base * orb_factor), 4),
            "base_strength": sign_base,
            "orb_factor": orb_factor,
        })

    # Backward transition (from previous sign) — only for signs > 0,
    # since Pisces→Aries is handled by the forward case with wrap-around
    if dist_to_prev <= max_orb and current_sign_idx > 0:
        orb_factor = round(max(0, 1 - dist_to_prev / max_orb), 4)
        transitions.append({
            "transition_type": "sign",
            "current_sign": signs[current_sign_idx],
            "previous_sign": signs[current_sign_idx - 1],
            "next_sign": None,
            "current_house": None,
            "target_house": None,
            "boundary_longitude": round(prev_boundary, 4),
            "distance_to_boundary": round(dist_to_prev, 4),
            "strength": round(min(1.0, sign_base * orb_factor), 4),
            "base_strength": sign_base,
            "orb_factor": orb_factor,
        })

    # Natal house cusp boundaries
    natal_houses_raw, _, _ = calculate_houses_cusps(ctx.birth_jd, birth_lat, birth_lon, house_system)
    for h in natal_houses_raw:
        cusp = h["cusp"]
        dist = _angular_distance(ps_lon, cusp)
        if dist <= max_orb:
            orb_factor = round(max(0, 1 - dist / max_orb), 4)
            transitions.append({
                "transition_type": "house",
                "current_sign": None,
                "previous_sign": None,
                "next_sign": None,
                "current_house": _find_house(ps_lon, natal_houses_raw),
                "target_house": h["number"],
                "boundary_longitude": round(cusp, 4),
                "distance_to_boundary": round(dist, 4),
                "strength": round(min(1.0, house_base * orb_factor), 4),
                "base_strength": house_base,
                "orb_factor": orb_factor,
            })

    return transitions
