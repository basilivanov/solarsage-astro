# ############################################################################
# AI_HEADER: MODULE_SIDECAR_ACTIVATION_BUILDER — sidecar activation layer builder.
# ROLE: W3.1 transit activation extraction for transit_to_natal, transit_to_angle,
#       transit_to_lot, transit_planet_in_house.
# ############################################################################

from __future__ import annotations

import math
import os
import pathlib
from typing import Any

import yaml

from solarsage.schemas.activation import ActivationLayer, ActivationEvidence
from solarsage.utils.ephemeris import (
    calculate_julian_day,
    calculate_positions,
    calculate_houses_cusps,
    get_sign,
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


def _load_aspect_rules() -> dict[str, Any]:
    path = _resolve_canon_path("grace/canon/aspect_rules.v1.yml")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_orb(rules: dict, source_planet: str, target_key: str | None) -> float:
    """Determine max orb for a transit->target pair."""
    profile = rules.get("orb_profile_default", {})
    if target_key and target_key in profile:
        return float(profile[target_key])
    if source_planet.upper() in profile:
        return float(profile[source_planet.upper()])
    return 5.0


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

def _is_day_chart(natal_sun_house: int | None) -> bool:
    """Day chart if Sun is in houses 7..12 (above horizon)."""
    if natal_sun_house is None:
        return True  # default to day
    return natal_sun_house >= 7


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
    applying: bool,
    phase: str,
    strength: float,
    polarity: str,
    exact_at: str | None,
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
        exact_at=exact_at,
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

W3_1_SUPPORTED = {"transit_to_natal", "transit_to_angle", "transit_to_lot", "transit_planet_in_house"}
ALL_TECHNIQUES = list(W3_1_SUPPORTED)  # ordered default list


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
) -> ActivationLayer:
    """Build activation layer for a given birth + target context.

    W3.1: real transit activation extraction using Swiss Ephemeris.
    Supports transit_to_natal, transit_to_angle, transit_to_lot, transit_planet_in_house.

    Unsupported W3+ techniques generate deterministic warnings and are skipped.
    """
    if techniques is None or len(techniques) == 0:
        requested = list(ALL_TECHNIQUES)
    else:
        requested = list(techniques)

    # Filter to supported + collect warnings for unsupported
    active = [t for t in requested if t in W3_1_SUPPORTED]
    warnings_list: list[str] = []
    for t in requested:
        if t not in W3_1_SUPPORTED:
            warnings_list.append(f"unsupported_technique_deferred:{t}")

    if not active:
        # No supported techniques requested — return contract-only layer
        return ActivationLayer(
            calculation_version="1",
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

    # ── 2. Calculate natal chart ─────────────────────────────────────
    natal_jd = calculate_julian_day(birth_date, birth_time, birth_tz)
    natal_positions = calculate_positions(natal_jd)
    natal_houses_raw, natal_special_points, resolved_house_system = calculate_houses_cusps(
        natal_jd, birth_lat, birth_lon,
    )

    # Build useful lookup maps
    natal_by_name: dict[str, dict] = {}
    for p in natal_positions:
        natal_by_name[p["name"]] = p

    # Find natal Sun house for day/night determination
    natal_sun = natal_by_name.get("Sun", {})
    natal_sun_house = None
    if natal_sun:
        natal_sun_house = _find_house(natal_sun.get("longitude", 0.0), natal_houses_raw)

    is_day = _is_day_chart(natal_sun_house)

    # Angles
    def _find_special(name: str) -> dict | None:
        for sp in natal_special_points:
            if sp["name"] == name:
                return sp
        return None

    asc_sp = _find_special("ASC")
    mc_sp = _find_special("MC")
    asc_lon = asc_sp["longitude"] if asc_sp else 0.0
    mc_lon = mc_sp["longitude"] if mc_sp else 0.0
    dsc_lon = (asc_lon + 180.0) % 360.0
    ic_lon = (mc_lon + 180.0) % 360.0

    angles = {
        "ASC": asc_lon,
        "MC": mc_lon,
        "DSC": dsc_lon,
        "IC": ic_lon,
    }

    # ── 3. Calculate transit positions ───────────────────────────────
    target_jd = calculate_julian_day(target_date, target_time, target_tz)
    transit_positions = calculate_positions(target_jd)
    transit_by_name: dict[str, dict] = {}
    for p in transit_positions:
        transit_by_name[p["name"]] = p

    # ── 4. Compute lots (always, for indexing) ───────────────────────
    natal_mercury = natal_by_name.get("Mercury", {})
    natal_venus = natal_by_name.get("Venus", {})
    natal_jupiter = natal_by_name.get("Jupiter", {})
    natal_saturn = natal_by_name.get("Saturn", {})

    lots = _compute_lots(
        asc_lon=asc_lon,
        sun_lon=natal_sun.get("longitude", 0.0),
        moon_lon=natal_by_name.get("Moon", {}).get("longitude", 0.0),
        mercury_lon=natal_mercury.get("longitude", 0.0),
        venus_lon=natal_venus.get("longitude", 0.0),
        jupiter_lon=natal_jupiter.get("longitude", 0.0),
        saturn_lon=natal_saturn.get("longitude", 0.0),
        dsc_lon=dsc_lon,
        is_day=is_day,
    )

    # Find lot houses
    for lot in lots:
        lot["house"] = _find_house(lot["longitude"], natal_houses_raw)
        lot["sign"] = get_sign(lot["longitude"])

    # ── 5. Build activations ─────────────────────────────────────────
    activations: list[ActivationEvidence] = []
    by_planet: dict[str, list[str]] = {}
    by_house: dict[str, list[str]] = {}
    by_lot: dict[str, list[str]] = {}
    by_angle: dict[str, list[str]] = {}

    planet_names = list(transit_by_name.keys())

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
                target_type_prefix = "planet"
            elif tech == "transit_to_angle":
                targets = {}
                for aname, alon in angles.items():
                    targets[aname] = ("angle", alon)
                target_frame = "angle"
                target_type_prefix = "angle"
            else:  # transit_to_lot
                targets = {}
                for lot in lots:
                    targets[lot["name"]] = ("lot", lot["longitude"])
                target_frame = "lot"
                target_type_prefix = "lot"

            for tname, tpos in transit_by_name.items():
                tlon = tpos["longitude"]
                for tkey, (ttype, tlon_target) in targets.items():
                    adist = _angular_distance(tlon, tlon_target)
                    max_orb = _get_orb(aspect_rules, tname, tkey if ttype == "planet" else None)

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

                    # Phase / applying
                    probe_jd = target_jd + 0.1
                    probe_positions = calculate_positions(probe_jd)
                    probe_by_name: dict[str, dict] = {}
                    for pp in probe_positions:
                        probe_by_name[pp["name"]] = pp
                    probe_tlon = probe_by_name.get(tname, {}).get("longitude", tlon)
                    probe_adist = _angular_distance(probe_tlon, tlon_target)

                    # Tolerance for "exact"
                    if abs(probe_adist - adist) < 1e-6:
                        applying = False
                        phase = "exact"
                    elif probe_adist < adist:
                        applying = True
                        phase = "applying"
                    else:
                        applying = False
                        phase = "separating"

                    # Evidence string with frame
                    source_clean = tname
                    target_clean = tkey
                    if tech == "transit_to_natal":
                        evidence = (
                            f"Transit {source_clean} {best_aspect} natal {target_clean}, "
                            f"orb {orb}°"
                        )
                    elif tech == "transit_to_angle":
                        evidence = (
                            f"Transit {source_clean} {best_aspect} natal {target_clean}, "
                            f"orb {orb}°"
                        )
                    else:  # transit_to_lot
                        evidence = (
                            f"Transit {source_clean} {best_aspect} lot {target_clean}, "
                            f"orb {orb}°"
                        )

                    debug_info: dict[str, Any] = {
                        "source_longitude": round(tlon, 4),
                        "target_longitude": round(tlon_target, 4),
                        "angular_distance": round(adist, 4),
                        "max_orb": round(max_orb, 4),
                        "aspect_angle": ASPECT_ANGLES[best_aspect],
                        "aspect_weight": aspect_weight,
                        "applying_probe_days": 0.1,
                    }

                    extra_kw: dict[str, Any] = {}
                    if ttype == "angle":
                        extra_kw["angle"] = tkey
                    if ttype == "lot":
                        extra_kw["lot"] = tkey
                        # Include lot debug info
                        matching_lots = [l for l in lots if l["name"] == tkey]
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
                        exact_at=None,
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

    return ActivationLayer(
        calculation_version="1",
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
