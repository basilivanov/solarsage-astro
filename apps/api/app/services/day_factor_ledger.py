# ############################################################################
# AI_HEADER: MODULE_DAY_FACTOR_LEDGER
# ROLE: Pure service module building canonical factor ledger with cross-source deduplication.
# DEPENDENCIES: app.schemas.day_valence, app.services.canon_service, app.services.astro_utils
# GRACE_ANCHORS: [DAY_FACTOR_LEDGER]
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-FACTOR-LEDGER
# purpose: Build canonical factor ledger from day signals and active activations with semantic identity, normalization, and cross-source deduplication (§5).
# owns:
#   - apps/api/app/services/day_factor_ledger.py
# inputs: day_signals (list), activations (list)
# outputs: FactorLedger (factors list, duplicate_count, invalid_count)
# dependencies: app.schemas.day_valence, app.services.canon_service, app.services.astro_utils
# side_effects: none (pure calculation)
# emitted_logs: none
# failure_policy: invalid factors counted in invalid_count without raising exceptions
# END_MODULE_CONTRACT: M-DAY-FACTOR-LEDGER

# START_MODULE_MAP: M-DAY-FACTOR-LEDGER
# public_entrypoints:
#   - build_factor_ledger
# semantic_blocks:
#   - LEDGER_BUILDER: factor normalization, semantic key construction, and cross-source deduplication
# owned_tests:
#   - apps/api/tests/test_day_factor_ledger.py
# END_MODULE_MAP: M-DAY-FACTOR-LEDGER

from __future__ import annotations

from typing import Any
from app.schemas.day_valence import DayValenceFactor, FactorLedger
from app.services.astro_utils import strip_prefix
from app.services.canon_service import load_day_valence_canon
from app.services.scoring_v2_service import _get_spheres

# Canon-only aspect polarities (hidden fallback is forbidden — fail-closed at import)
_VALENCE_CANON = load_day_valence_canon()
_ASPECT_POLARITIES = _VALENCE_CANON.get("aspect_polarities", {})


ANGLES: set[str] = {"ASC", "MC", "IC", "DESC", "DSC"}
LOTS: set[str] = {"FORTUNE", "SPIRIT", "EROS", "SCIENCE", "MARRIAGE"}


def _technical_spheres_for_planet(planet_key: str | None) -> list[str]:
    """Technical spheres where this planet carries a canon weight (spheres.v1.yml)."""
    if not planet_key:
        return []
    key = planet_key.strip().upper()
    spheres = (_get_spheres() or {}).get("spheres") or {}
    return [tech for tech, info in spheres.items() if key in (info.get("planets") or {})]


def _technical_spheres_for_house(house: Any) -> list[str]:
    """Technical spheres whose canon house list contains this house number."""
    try:
        house_int = int(house)
    except (TypeError, ValueError):
        return []
    spheres = (_get_spheres() or {}).get("spheres") or {}
    return [tech for tech, info in spheres.items() if house_int in (info.get("houses") or [])]


def _normalize_target_type(target_type: str | None, target_key: str | None) -> str:
    key_upper = (target_key or "").upper()
    if key_upper in ANGLES:
        return "angle"
    if key_upper in LOTS:
        return "lot"
    if target_type and target_type.lower() in ("angle", "lot", "house"):
        return target_type.lower()
    return "natal_planet"


def _clean_key(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    return strip_prefix(str(value)).strip().upper()


def _clean_aspect(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    return str(value).strip().lower()


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# START_BLOCK: LEDGER_BUILDER
def build_factor_ledger(
    day_signals: list[Any] | None = None,
    activations: list[Any] | None = None,
) -> FactorLedger:
    # START_FUNCTION_CONTRACT: F-M-DAY-FACTOR-LEDGER.build_factor_ledger
    # purpose: Build canonical factor ledger with cross-source deduplication and normalization.
    # inputs: day_signals (list | None), activations (list | None)
    # returns: FactorLedger
    # side_effects: none (pure calculation)
    # emitted_logs: none
    # error_behavior: counts invalid factors in invalid_count fail-closed
    # END_FUNCTION_CONTRACT: F-M-DAY-FACTOR-LEDGER.build_factor_ledger
    day_signals = day_signals or []
    activations = activations or []

    duplicate_count = 0
    invalid_count = 0

    seen_activation_ids: set[str] = set()
    activation_factors: list[DayValenceFactor] = []
    activation_semantic_keys: set[str] = set()

    # 1. Process Activations (source="activation")
    for act in activations:
        active = _get_field(act, "active", True)
        if active is False:
            continue

        act_id = _get_field(act, "activation_id") or _get_field(act, "id")
        if not act_id or not str(act_id).strip():
            invalid_count += 1
            continue

        act_id_str = str(act_id).strip()
        if act_id_str in seen_activation_ids:
            duplicate_count += 1
            continue
        seen_activation_ids.add(act_id_str)

        technique = str(_get_field(act, "technique") or "activation")
        technique_family = str(_get_field(act, "technique_family") or _get_field(act, "techniqueFamily") or "transit")
        polarity = str(_get_field(act, "polarity") or "neutral")
        if polarity not in ("supportive", "tense", "mixed", "neutral"):
            polarity = "neutral"

        strength = float(_get_field(act, "strength") or 0.0)
        strength = max(0.0, min(1.0, strength))

        src_planet = _clean_key(_get_field(act, "planet") or _get_field(act, "source_planet") or _get_field(act, "sourcePlanet"))
        target_key_raw = _clean_key(_get_field(act, "target_key") or _get_field(act, "targetKey") or _get_field(act, "target_planet") or _get_field(act, "house"))
        target_type_raw = _get_field(act, "target_type") or _get_field(act, "targetType")
        target_type = _normalize_target_type(str(target_type_raw) if target_type_raw else None, target_key_raw)
        aspect_type = _clean_aspect(_get_field(act, "aspect_type") or _get_field(act, "aspectType"))

        ev_str = str(_get_field(act, "evidence") or _get_field(act, "title") or "")
        if ev_str:
            import re
            if not src_planet:
                match_p = re.search(r'\b(?:Transit_|Natal_)?([A-Z][a-z]+)\b', ev_str)
                if match_p:
                    src_planet = _clean_key(match_p.group(1))
            if not aspect_type:
                match_a = re.search(r'\b(sextile|trine|square|opposition|conjunction|quincunx|semi_square|sesquisquare)\b', ev_str.lower())
                if match_a:
                    aspect_type = _clean_aspect(match_a.group(1))

        # Build semantic_key per §5.2
        if aspect_type and src_planet and target_key_raw:
            sem_key = f"aspect:{src_planet}:{aspect_type}:{target_type}:{target_key_raw}"
        elif technique_family == "transit" and technique == "transit_planet_in_house" and src_planet and target_key_raw:
            sem_key = f"house:{src_planet}:{target_key_raw}"
        else:
            sem_key = f"activation:{act_id_str}"

        tech_spheres = _get_field(act, "technical_spheres") or []
        if not isinstance(tech_spheres, list):
            tech_spheres = []
        if not tech_spheres:
            # Local activation objects carry no sphere mapping: derive it the
            # same way as for day signals — natal target planet or house number
            # via spheres.v1.yml, otherwise the strongest factors would count
            # only globally and never project into product spheres.
            if target_type == "house":
                tech_spheres = _technical_spheres_for_house(target_key_raw)
            else:
                tech_spheres = _technical_spheres_for_planet(target_key_raw) or _technical_spheres_for_planet(src_planet)

        target_key_final = target_key_raw or "UNKNOWN"

        factor = DayValenceFactor(
            factor_id=f"act:{act_id_str}",
            semantic_key=sem_key,
            source="activation",
            technique=technique,
            technique_family=technique_family,
            polarity=polarity,  # type: ignore[arg-type]
            strength=strength,
            technical_spheres=list(tech_spheres),
            source_planet=src_planet,
            target_type=target_type,
            target_key=target_key_final,
            aspect_type=aspect_type,
        )
        activation_factors.append(factor)
        activation_semantic_keys.add(sem_key)

    # 2. Process Day Signals (source="day_signal")
    signal_candidates: dict[str, list[DayValenceFactor]] = {}

    for sig in day_signals:
        sig_type = _get_field(sig, "type")
        planet = _clean_key(_get_field(sig, "planet"))
        strength = float(_get_field(sig, "strength") or _get_field(sig, "daily_salience") or 0.0)
        strength = max(0.0, min(1.0, strength))

        if not planet:
            invalid_count += 1
            continue

        if sig_type == "aspect":
            target_planet = _clean_key(_get_field(sig, "target_planet"))
            aspect_type = _clean_aspect(_get_field(sig, "aspect_type"))
            if not target_planet or not aspect_type:
                invalid_count += 1
                continue

            target_type = _normalize_target_type(None, target_planet)
            sem_key = f"aspect:{planet}:{aspect_type}:{target_type}:{target_planet}"

            # Cross-source dedup: if activation has same semantic key, activation wins!
            if sem_key in activation_semantic_keys:
                duplicate_count += 1
                continue

            polarity = _ASPECT_POLARITIES.get(aspect_type, "neutral")

            # Technical spheres derive from the natal target planet (spheres.v1.yml),
            # falling back to the transit source planet (normative §6.1 target rule).
            tech_spheres = _technical_spheres_for_planet(target_planet) or _technical_spheres_for_planet(planet)

            factor = DayValenceFactor(
                factor_id=f"sig:aspect:{planet}:{aspect_type}:{target_planet}",
                semantic_key=sem_key,
                source="day_signal",
                technique="transit_to_natal",
                technique_family="transit",
                polarity=polarity,  # type: ignore[arg-type]
                strength=strength,
                technical_spheres=tech_spheres,
                source_planet=planet,
                target_type=target_type,
                target_key=target_planet,
                aspect_type=aspect_type,
            )
            signal_candidates.setdefault(sem_key, []).append(factor)

        elif sig_type == "planet_in_house":
            house = _get_field(sig, "house")
            if house is None:
                invalid_count += 1
                continue

            house_str = str(house)
            sem_key = f"house:{planet}:{house_str}"

            if sem_key in activation_semantic_keys:
                duplicate_count += 1
                continue

            # Technical spheres derive from the house number (spheres.v1.yml house lists).
            tech_spheres = _technical_spheres_for_house(house)

            factor = DayValenceFactor(
                factor_id=f"sig:house:{planet}:{house_str}",
                semantic_key=sem_key,
                source="day_signal",
                technique="transit_planet_in_house",
                technique_family="transit",
                polarity="neutral",
                strength=strength,
                technical_spheres=tech_spheres,
                source_planet=planet,
                target_type="house",
                target_key=house_str,
                aspect_type=None,
            )
            signal_candidates.setdefault(sem_key, []).append(factor)
        else:
            # Non-aspect / non-house day signals without valence rules
            continue

    # Coalesce day_signal candidates with same semantic_key to max strength
    coalesced_signals: list[DayValenceFactor] = []
    for sem_key, cand_list in signal_candidates.items():
        if len(cand_list) > 1:
            duplicate_count += (len(cand_list) - 1)
            best_cand = max(cand_list, key=lambda f: (f.strength, f.factor_id))
            coalesced_signals.append(best_cand)
        else:
            coalesced_signals.append(cand_list[0])

    # 3. Combine and sort deterministically by (-strength, factor_id)
    all_factors = activation_factors + coalesced_signals
    all_factors.sort(key=lambda f: (-f.strength, f.factor_id))

    return FactorLedger(
        factors=all_factors,
        duplicate_count=duplicate_count,
        invalid_count=invalid_count,
    )
# END_BLOCK: LEDGER_BUILDER
