# ############################################################################
# AI_HEADER: MODULE_SIDECAR_ECLIPSES — Eclipse window activation calculation.
# ROLE: Finds nearest solar/lunar eclipses within a configured window around
#       the target date and generates conjunction activations for natal
#       planets, angles, and lots within orb.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-ECLIPSES
# purpose: Find nearest solar/lunar eclipses within days_before/days_after
#          of the target JD. Generate conjunction ActivationEvidence for
#          natal targets within orb_to_natal.
# owns:
#   - apps/solarsage/solarsage/services/eclipses.py
# inputs: birth data, target data, house_system, canon config
# outputs: list of eclipse_window ActivationEvidence-ready dicts
# dependencies: swisseph, ephemeris utils, activation_rules.v1.yml
# side_effects: none (pure ephemeris computation)
# emitted_logs: none
# failure_policy: KeyError on missing config keys; ValueError on zero limits
# END_MODULE_CONTRACT: M-SIDECAR-ECLIPSES

# START_MODULE_MAP: M-SIDECAR-ECLIPSES
# public_entrypoints:
#   - find_eclipses
# semantic_blocks:
#   - ECLIPSE_SEARCH: forward/backward eclipse lookup
#   - ACTIVATION_BUILD: conjunction activation generation
# owned_tests:
#   - tests/test_eclipse_window.py
# END_MODULE_MAP: M-SIDECAR-ECLIPSES

from __future__ import annotations

import os
import pathlib
from datetime import datetime, timezone
from typing import Any

import swisseph as swe
import yaml

from solarsage.utils.ephemeris import (
    calculate_julian_day,
    calculate_houses_cusps,
    get_sign,
)

# ── Eclipse type mapping ─────────────────────────────────────────────────────

SOLAR_TYPE_MAP: dict[int, str] = {
    swe.ECL_TOTAL: "total",
    swe.ECL_ANNULAR: "annular",
    swe.ECL_ANNULAR_TOTAL: "annular_total",
    swe.ECL_PARTIAL: "partial",
}

LUNAR_TYPE_MAP: dict[int, str] = {
    swe.ECL_TOTAL: "total",
    swe.ECL_PARTIAL: "partial",
    swe.ECL_PENUMBRAL: "penumbral",
}


def _resolve_eclipse_type(retflag: int, is_solar: bool) -> str:
    """Map retflag to eclipse type string."""
    mapping = SOLAR_TYPE_MAP if is_solar else LUNAR_TYPE_MAP
    for flag, name in mapping.items():
        if retflag & flag:
            return name
    return "unknown"


# ── Canon loading ────────────────────────────────────────────────────────────


def _resolve_canon_path(relative: str) -> str:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent.parent.parent
    return os.path.join(root, relative)


def _load_canon_config() -> dict[str, Any]:
    """Load eclipse_window config from activation_rules.v1.yml.
    Strict: missing or non-numeric keys raise."""
    path = _resolve_canon_path("grace/canon/activation_rules.v1.yml")
    with open(path) as f:
        rules = yaml.safe_load(f)
    tech = rules.get("techniques", {}).get("eclipse_window")
    if tech is None:
        raise KeyError("eclipse_window not found in activation_rules.v1.yml")
    config = {}
    for key in ("days_before", "days_after", "orb_to_natal", "strength"):
        val = tech.get(key)
        if val is None:
            raise KeyError(f"eclipse_window.{key} not found in activation_rules.v1.yml")
        try:
            config[key] = float(val)
        except (ValueError, TypeError):
            raise KeyError(f"eclipse_window.{key} is non-numeric: {val}")
    if config["days_before"] <= 0 or config["days_after"] <= 0:
        raise ValueError(f"eclipse_window days_before/days_after must be > 0")
    if config["orb_to_natal"] <= 0:
        raise ValueError(f"eclipse_window orb_to_natal must be > 0")
    return config


# ── Helpers ──────────────────────────────────────────────────────────────────


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


def _angular_distance(lon1: float, lon2: float) -> float:
    raw = abs(lon1 - lon2) % 360.0
    if raw > 180.0:
        raw = 360.0 - raw
    return raw


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


# START_BLOCK: ECLIPSE_SEARCH


def _find_eclipse_candidates(target_jd: float, config: dict) -> list[dict]:
    """Find eclipse candidates within the configured window."""
    swe.set_ephe_path("/opt/sweph/ephe")
    flags = swe.FLG_SWIEPH
    candidates: list[dict] = []

    for is_solar, search_fn in [
        (True, lambda jd, back: swe.sol_eclipse_when_glob(jd, flags, 0, back)),
        (False, lambda jd, back: swe.lun_eclipse_when(jd, flags, 0, back)),
    ]:
        for backwards in (False, True):
            try:
                retflag, tret = search_fn(target_jd, backwards)
            except swe.Error:
                continue
            if retflag == swe.ECL_NUT:
                continue
            eclipse_jd = tret[0]
            if eclipse_jd <= 0:
                continue

            days_delta = eclipse_jd - target_jd
            if backwards and days_delta > 0:
                continue
            if not backwards and days_delta < 0:
                continue

            abs_delta = abs(days_delta)
            limit = config["days_after"] if days_delta >= 0 else config["days_before"]

            if abs_delta > limit:
                continue

            eclipse_type = _resolve_eclipse_type(retflag, is_solar)

            # Longitude at maximum eclipse
            body = swe.SUN if is_solar else swe.MOON
            pos = swe.calc_ut(eclipse_jd, body, flags)
            eclipse_lon = pos[0][0]

            candidates.append({
                "is_solar": is_solar,
                "kind": "solar" if is_solar else "lunar",
                "type": eclipse_type,
                "retflag": retflag,
                "jd": eclipse_jd,
                "utc_iso": _jd_to_utc_iso(eclipse_jd),
                "date_str": datetime(*swe.revjul(eclipse_jd)[:3]).strftime("%Y_%m_%d"),
                "days_delta": days_delta,
                "abs_delta": abs_delta,
                "longitude": eclipse_lon,
            })

    # Sort: nearest by abs_delta, then by jd, then solar before lunar
    candidates.sort(key=lambda c: (c["abs_delta"], c["jd"], 0 if c["is_solar"] else 1))
    return candidates


# END_BLOCK: ECLIPSE_SEARCH

# START_BLOCK: ACTIVATION_BUILD


def find_eclipses(
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
) -> list[dict[str, Any]]:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-ECLIPSES.find_eclipses
    # purpose: Find eclipse candidates within window, build conjunction
    #          activations for natal targets within orb.
    # inputs: birth data, target data, house_system
    # returns: list of ActivationEvidence-ready dicts
    # side_effects: ephemeris computations
    # error_behavior: KeyError on missing config; ValueError on zero limits
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-ECLIPSES.find_eclipses
    """Find eclipse candidates and build conjunction activations."""
    config = _load_canon_config()
    target_jd = calculate_julian_day(target_date, target_time, target_tz)

    # Natal chart
    natal_jd = calculate_julian_day(birth_date, birth_time, birth_tz)
    from solarsage.utils.ephemeris import calculate_positions
    natal_positions = calculate_positions(natal_jd)
    natal_by_name = {p["name"]: p for p in natal_positions}

    natal_houses_raw, natal_special_points, resolved_house_system = calculate_houses_cusps(
        natal_jd, birth_lat, birth_lon, house_system,
    )

    # Natal angles
    natal_angles: dict[str, float] = {}
    for sp in natal_special_points:
        if sp["name"] in ("ASC", "MC"):
            natal_angles[sp["name"]] = sp["longitude"]
    if "ASC" in natal_angles:
        natal_angles["DSC"] = (natal_angles["ASC"] + 180.0) % 360.0
    if "MC" in natal_angles:
        natal_angles["IC"] = (natal_angles["MC"] + 180.0) % 360.0

    # Natal lots
    from solarsage.services.activation_builder import _local_date, _is_day_chart, _compute_lots
    birth_local = _local_date(birth_date, birth_tz)
    natal_sun = natal_by_name.get("Sun", {})
    natal_sun_lon = natal_sun.get("longitude", 0.0)
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

    candidates = _find_eclipse_candidates(target_jd, config)
    activations: list[dict] = []
    orb_to_natal = config["orb_to_natal"]
    base_strength = config["strength"]
    days_before = config["days_before"]
    days_after = config["days_after"]

    # Debug base for all activations
    debug_base = {
        "days_before": days_before,
        "days_after": days_after,
        "orb_to_natal": orb_to_natal,
        "base_strength": base_strength,
        "resolved_house_system": resolved_house_system,
    }

    for cand in candidates:
        ecl_lon = cand["longitude"]
        ecl_kind = cand["kind"]
        ecl_type = cand["type"]
        ecl_jd = cand["jd"]
        days_delta = cand["days_delta"]
        abs_delta = cand["abs_delta"]
        window_limit = days_after if days_delta >= 0 else days_before
        window_factor = max(0, 1 - abs_delta / window_limit) if window_limit > 0 else 0.0

        # Determine ID prefix
        kind_prefix = "SOLAR" if cand["is_solar"] else "LUNAR"

        # Natal planets
        for pname, pdata in natal_by_name.items():
            tlon = pdata["longitude"]
            orb = _angular_distance(ecl_lon, tlon)
            if orb > orb_to_natal:
                continue
            orb_factor = max(0, 1 - orb / orb_to_natal)
            strength = round(min(1.0, base_strength * orb_factor * window_factor), 4)
            tkey = pname.upper()
            aid = f"eclipse_window__{kind_prefix}__{ecl_type.upper()}__{cand['date_str']}__CONJUNCTION__NATAL_{tkey}"
            activations.append({
                "id": aid,
                "technique": "eclipse_window",
                "technique_family": "eclipse",
                "target_type": "planet",
                "target_key": tkey,
                "kind": f"{ecl_kind}_eclipse_window",
                "source_frame": "eclipse",
                "target_frame": "natal",
                "target_planet": tkey,
                "aspect": "conjunction",
                "orb": round(orb, 4),
                "phase": "period",
                "polarity": "mixed",
                "strength": strength,
                "evidence": f"{ecl_kind.capitalize()} {ecl_type} eclipse conjunct natal {pname}, orb {round(orb, 4)}°, eclipse {cand['date_str'].replace('_', '-')}",
                "debug": {
                    **debug_base,
                    "eclipse_kind": ecl_kind,
                    "eclipse_type": ecl_type,
                    "eclipse_retflag": cand["retflag"],
                    "eclipse_jd": round(ecl_jd, 4),
                    "eclipse_utc_iso": cand["utc_iso"],
                    "eclipse_date": cand["date_str"],
                    "target_jd": round(target_jd, 4),
                    "days_delta": round(days_delta, 4),
                    "eclipse_longitude": round(ecl_lon, 4),
                    "target_longitude": round(tlon, 4),
                    "angular_distance": round(orb, 4),
                    "orb": round(orb, 4),
                    "orb_factor": round(orb_factor, 4),
                    "window_factor": round(window_factor, 4),
                },
            })

        # Natal angles
        for aname, alon in natal_angles.items():
            orb = _angular_distance(ecl_lon, alon)
            if orb > orb_to_natal:
                continue
            orb_factor = max(0, 1 - orb / orb_to_natal)
            strength = round(min(1.0, base_strength * orb_factor * window_factor), 4)
            aid = f"eclipse_window__{kind_prefix}__{ecl_type.upper()}__{cand['date_str']}__CONJUNCTION__NATAL_ANGLE_{aname}"
            activations.append({
                "id": aid,
                "technique": "eclipse_window",
                "technique_family": "eclipse",
                "target_type": "angle",
                "target_key": aname,
                "kind": f"{ecl_kind}_eclipse_window",
                "source_frame": "eclipse",
                "target_frame": "angle",
                "angle": aname,
                "aspect": "conjunction",
                "orb": round(orb, 4),
                "phase": "period",
                "polarity": "mixed",
                "strength": strength,
                "evidence": f"{ecl_kind.capitalize()} {ecl_type} eclipse conjunct natal {aname}, orb {round(orb, 4)}°, eclipse {cand['date_str'].replace('_', '-')}",
                "debug": {
                    **debug_base,
                    "eclipse_kind": ecl_kind,
                    "eclipse_type": ecl_type,
                    "eclipse_retflag": cand["retflag"],
                    "eclipse_jd": round(ecl_jd, 4),
                    "eclipse_utc_iso": cand["utc_iso"],
                    "eclipse_date": cand["date_str"],
                    "target_jd": round(target_jd, 4),
                    "days_delta": round(days_delta, 4),
                    "eclipse_longitude": round(ecl_lon, 4),
                    "target_longitude": round(alon, 4),
                    "angular_distance": round(orb, 4),
                    "orb": round(orb, 4),
                    "orb_factor": round(orb_factor, 4),
                    "window_factor": round(window_factor, 4),
                },
            })

        # Natal lots
        for lot in lots:
            llon = lot["longitude"]
            orb = _angular_distance(ecl_lon, llon)
            if orb > orb_to_natal:
                continue
            orb_factor = max(0, 1 - orb / orb_to_natal)
            strength = round(min(1.0, base_strength * orb_factor * window_factor), 4)
            lname = lot["name"]
            aid = f"eclipse_window__{kind_prefix}__{ecl_type.upper()}__{cand['date_str']}__CONJUNCTION__NATAL_LOT_{lname}"
            activations.append({
                "id": aid,
                "technique": "eclipse_window",
                "technique_family": "eclipse",
                "target_type": "lot",
                "target_key": lname,
                "kind": f"{ecl_kind}_eclipse_window",
                "source_frame": "eclipse",
                "target_frame": "lot",
                "lot": lname,
                "aspect": "conjunction",
                "orb": round(orb, 4),
                "phase": "period",
                "polarity": "mixed",
                "strength": strength,
                "evidence": f"{ecl_kind.capitalize()} {ecl_type} eclipse conjunct lot {lname}, orb {round(orb, 4)}°, eclipse {cand['date_str'].replace('_', '-')}",
                "debug": {
                    **debug_base,
                    "eclipse_kind": ecl_kind,
                    "eclipse_type": ecl_type,
                    "eclipse_retflag": cand["retflag"],
                    "eclipse_jd": round(ecl_jd, 4),
                    "eclipse_utc_iso": cand["utc_iso"],
                    "eclipse_date": cand["date_str"],
                    "target_jd": round(target_jd, 4),
                    "days_delta": round(days_delta, 4),
                    "eclipse_longitude": round(ecl_lon, 4),
                    "target_longitude": round(llon, 4),
                    "angular_distance": round(orb, 4),
                    "orb": round(orb, 4),
                    "orb_factor": round(orb_factor, 4),
                    "window_factor": round(window_factor, 4),
                },
            })

    return activations


# END_BLOCK: ACTIVATION_BUILD
