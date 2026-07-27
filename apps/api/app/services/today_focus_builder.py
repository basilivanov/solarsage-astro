# ############################################################################
# AI_HEADER: MODULE_TODAY_FOCUS_BUILDER
# ROLE: Pure service module building normalized TodayFactor and classifying temporal roles.
# DEPENDENCIES: datetime, zoneinfo, app.schemas.day_valence, app.services.astro_utils
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-FOCUS-BUILDER
# purpose: Build normalized TodayFactor list from factor ledger and activation layer, classifying temporal roles relative to user's IANA timezone and date (§4.2).
# owns:
#   - apps/api/app/services/today_focus_builder.py
# inputs: ledger (FactorLedger | list), activation_layer (list | dict | None), day_delta (dict | None), target_date (date), tz_info (str | ZoneInfo)
# outputs: TodayFactor, local_day_bounds, classify_temporal_role, normalize_factors
# dependencies: datetime, zoneinfo, app.schemas.day_valence, app.services.astro_utils
# side_effects: none (pure calculation)
# emitted_logs: none
# failure_policy: safe fallbacks, invalid factors skipped or classified as unrelated
# END_MODULE_CONTRACT: M-TODAY-FOCUS-BUILDER

# START_MODULE_MAP: M-TODAY-FOCUS-BUILDER
# public_entrypoints:
#   - TodayFactor
#   - local_day_bounds
#   - classify_temporal_role
#   - normalize_factors
# semantic_blocks:
#   - TIME_BOUNDS: DST-safe UTC boundary calculation
#   - ROLE_CLASSIFICATION: temporal role classifier (anchor_today, supporting, background, unrelated)
#   - FACTOR_NORMALIZER: factor ledger + activation layer normalization and merging
# owned_tests:
#   - tests/test_today_focus_builder.py
# END_MODULE_MAP: M-TODAY-FOCUS-BUILDER

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from app.schemas.day_valence import DayValenceFactor, FactorLedger
from app.services.astro_utils import strip_prefix

TemporalRole = Literal["anchor_today", "supporting", "background", "unrelated"]

CANONICAL_PRODUCT_KEYS: tuple[str, ...] = (
    "work", "money", "documents", "relationships", "sport", "communication",
    "health", "decisions", "travel", "creativity", "study", "shopping"
)

TECH_SPHERE_TO_PRODUCT_MAP: dict[str, str] = {
    "work_status_achievement": "work",
    "career": "work",
    "career_social_status": "work",
    "public_image": "work",
    "technology_innovation": "work",
    "finance_money": "money",
    "money_security_resources": "money",
    "legal_affairs": "documents",
    "partnerships_contracts": "documents",
    "relationships_partnership": "relationships",
    "relationships": "relationships",
    "home_family_roots": "relationships",
    "home_family": "relationships",
    "inheritance": "relationships",
    "body_energy_health": "sport",
    "daily_routine": "sport",
    "service_routine": "sport",
    "communication_learning": "communication",
    "thinking_speech_learning": "communication",
    "friendship_social": "communication",
    "spirituality_inner_growth": "health",
    "inner_background_unconscious": "health",
    "healing": "health",
    "hidden_matters": "health",
    "career_ambition": "decisions",
    "crisis_transformation": "decisions",
    "crisis_transformation_control": "decisions",
    "philosophy": "decisions",
    "travel_adventure": "travel",
}

PLANET_TO_PRODUCT_MAP: dict[str, list[str]] = {
    "SUN": ["work", "decisions"],
    "MARS": ["work", "sport", "decisions"],
    "VENUS": ["money", "relationships", "shopping"],
    "MERCURY": ["documents", "communication", "study"],
    "JUPITER": ["work", "money", "decisions"],
    "SATURN": ["work", "decisions", "documents"],
    "MOON": ["relationships", "health"],
    "URANUS": ["decisions", "travel"],
    "NEPTUNE": ["creativity", "health"],
    "PLUTO": ["decisions", "work"],
}


@dataclass(frozen=True)
class TodayFactor:
    """Immutable normalized factor model (§4.2)."""

    factor_id: str
    activation_ids: tuple[str, ...]
    technique: str
    technique_family: str
    source_key: str | None
    target_key: str | None
    theme_keys: tuple[str, ...]
    product_spheres: tuple[str, ...]
    polarity: str
    strength: float
    salience: float
    active_from: datetime | date | None
    exact_at: datetime | date | None
    active_until: datetime | date | None
    phase: str | None
    temporal_role: TemporalRole


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# START_BLOCK: TIME_BOUNDS
def local_day_bounds(target_date: date, tz_info: str | ZoneInfo) -> tuple[datetime, datetime]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.local_day_bounds
    # purpose: Compute DST-safe UTC boundary range [local_start_utc, local_end_utc) for target_date.
    # inputs: target_date (date), tz_info (str | ZoneInfo)
    # returns: (start_utc, end_utc)
    # side_effects: none
    # emitted_logs: none
    # error_behavior: falls back to UTC if tz_info is invalid
    # END_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.local_day_bounds
    if isinstance(tz_info, str):
        try:
            tz = ZoneInfo(tz_info)
        except Exception:
            tz = ZoneInfo("UTC")
    elif isinstance(tz_info, ZoneInfo):
        tz = tz_info
    else:
        tz = ZoneInfo("UTC")

    local_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=tz)
    next_date = target_date + timedelta(days=1)
    local_end = datetime(next_date.year, next_date.month, next_date.day, 0, 0, 0, tzinfo=tz)

    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)
# END_BLOCK: TIME_BOUNDS


def _to_utc_datetime(value: datetime | date | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


# START_BLOCK: ROLE_CLASSIFICATION
def classify_temporal_role(
    factor: TodayFactor | DayValenceFactor | dict | Any,
    local_start_utc: datetime,
    local_end_utc: datetime,
    day_delta: dict | None = None,
) -> TemporalRole:
    # START_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.classify_temporal_role
    # purpose: Classify temporal role (anchor_today, supporting, background, unrelated) relative to user's local day UTC bounds.
    # inputs: factor, local_start_utc, local_end_utc, day_delta
    # returns: TemporalRole
    # side_effects: none
    # emitted_logs: none
    # error_behavior: falls back to unrelated for malformed factors
    # END_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.classify_temporal_role
    exact_raw = _get_field(factor, "exact_at")
    active_from_raw = _get_field(factor, "active_from")
    active_until_raw = _get_field(factor, "active_until")

    exact_dt = _to_utc_datetime(exact_raw)
    active_from_dt = _to_utc_datetime(active_from_raw)
    active_until_dt = _to_utc_datetime(active_until_raw)

    tech_family = str(_get_field(factor, "technique_family") or "").lower()
    technique = str(_get_field(factor, "technique") or "").lower()
    factor_id = str(_get_field(factor, "factor_id") or "")
    activation_ids = _get_field(factor, "activation_ids") or ()
    if isinstance(activation_ids, str):
        activation_ids = (activation_ids,)

    # Check DayDelta peak or new_today triggers
    is_delta_trigger = False
    if day_delta and isinstance(day_delta, dict):
        new_today = day_delta.get("new_today", [])
        peaks = day_delta.get("peak", [])
        triggers = set(new_today) | set(peaks)
        if factor_id in triggers or any(act_id in triggers for act_id in activation_ids):
            is_delta_trigger = True

    # 1. Anchor Today:
    # - exact_at falls within [local_start_utc, local_end_utc)
    # - active_from falls within [local_start_utc, local_end_utc) and represents entering action
    # - DayDelta marks it as peak/new_today
    if exact_dt and (local_start_utc <= exact_dt < local_end_utc):
        return "anchor_today"
    if active_from_dt and (local_start_utc <= active_from_dt < local_end_utc):
        phase = str(_get_field(factor, "phase") or "").lower()
        if phase in ("exact", "building", "starts", "entering", "new") or not phase:
            return "anchor_today"
    if is_delta_trigger:
        return "anchor_today"

    # 2. Background:
    # Firdar, profection, solar/lunar return, progression or long-term transit without daily peak
    if tech_family in ("firdar", "profection", "solar_return", "progression", "lunar_return") or \
       technique in ("firdar", "profection", "solar_return", "progression", "return"):
        return "background"

    # 3. Check active window for supporting vs unrelated
    is_active = True
    if active_from_dt and active_from_dt >= local_end_utc:
        is_active = False
    if active_until_dt and active_until_dt < local_start_utc:
        is_active = False

    if is_active:
        return "supporting"

    return "unrelated"
# END_BLOCK: ROLE_CLASSIFICATION


def _map_to_product_spheres(
    tech_spheres: list[str] | tuple[str, ...],
    source_key: str | None,
    target_key: str | None,
) -> tuple[str, ...]:
    res = set()
    for ts in tech_spheres:
        p_key = TECH_SPHERE_TO_PRODUCT_MAP.get(ts.lower())
        if p_key:
            res.add(p_key)

    for k in (source_key, target_key):
        if k:
            k_clean = strip_prefix(k).upper()
            mapped = PLANET_TO_PRODUCT_MAP.get(k_clean)
            if mapped:
                for p_key in mapped:
                    res.add(p_key)

    ordered = [k for k in CANONICAL_PRODUCT_KEYS if k in res]
    return tuple(ordered) if ordered else ("work",)


# START_BLOCK: FACTOR_NORMALIZER
def normalize_factors(
    ledger: FactorLedger | list[Any] | None,
    activation_layer: list[Any] | dict[str, Any] | None = None,
    day_delta: dict | None = None,
    target_date: date | None = None,
    tz_info: str | ZoneInfo = "UTC",
) -> list[TodayFactor]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.normalize_factors
    # purpose: Normalize and merge factor ledger and activation layer into immutable TodayFactor instances.
    # inputs: ledger, activation_layer, day_delta, target_date, tz_info
    # returns: list[TodayFactor]
    # side_effects: none
    # emitted_logs: none
    # error_behavior: skips malformed inputs gracefully
    # END_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.normalize_factors
    if target_date is None:
        target_date = date.today()

    local_start_utc, local_end_utc = local_day_bounds(target_date, tz_info)

    # Extract activations into map by activation_id and semantic_key/factor_id
    activations_list: list[Any] = []
    if isinstance(activation_layer, list):
        activations_list = activation_layer
    elif isinstance(activation_layer, dict):
        activations_list = activation_layer.get("activations") or activation_layer.get("items") or []

    activations_by_id: dict[str, Any] = {}
    activations_by_sem_key: dict[str, list[Any]] = {}

    for act in activations_list:
        act_id = _get_field(act, "id") or _get_field(act, "activation_id")
        if act_id:
            activations_by_id[str(act_id)] = act

        # Extract semantic matching info (aspect/planets)
        planet = strip_prefix(str(_get_field(act, "planet") or "")).upper()
        target = strip_prefix(str(_get_field(act, "target_planet") or "")).upper()
        aspect = str(_get_field(act, "aspect_type") or "").lower()
        if planet and target and aspect:
            sem = f"aspect:{planet}:{aspect}:{target}"
            activations_by_sem_key.setdefault(sem, []).append(act)

    # Factors from ledger
    ledger_factors: list[DayValenceFactor] = []
    if isinstance(ledger, FactorLedger):
        ledger_factors = ledger.factors
    elif isinstance(ledger, list):
        ledger_factors = [f for f in ledger if isinstance(f, DayValenceFactor)]

    normalized_map: dict[str, TodayFactor] = {}

    for f in ledger_factors:
        fid = f.factor_id
        sem_key = f.semantic_key

        matched_acts = []
        # Find matching activation by semantic_key or factor_id
        for act_id, act in activations_by_id.items():
            act_sem = f"aspect:{strip_prefix(str(_get_field(act, 'planet') or '')).upper()}:{str(_get_field(act, 'aspect_type') or '').lower()}:{strip_prefix(str(_get_field(act, 'target_planet') or '')).upper()}"
            if act_sem == sem_key or str(act_id) in fid:
                matched_acts.append(act)

        if not matched_acts and sem_key in activations_by_sem_key:
            matched_acts.extend(activations_by_sem_key[sem_key])

        act_ids = tuple(sorted({str(_get_field(a, "id") or _get_field(a, "activation_id")) for a in matched_acts if _get_field(a, "id") or _get_field(a, "activation_id")}))

        primary_act = matched_acts[0] if matched_acts else None

        technique = f.technique
        technique_family = f.technique_family
        if primary_act:
            technique = _get_field(primary_act, "technique") or technique
            technique_family = _get_field(primary_act, "technique_family") or technique_family

        exact_at = _to_utc_datetime(_get_field(primary_act, "exact_at")) if primary_act else None
        active_from = _to_utc_datetime(_get_field(primary_act, "active_from")) if primary_act else None
        active_until = _to_utc_datetime(_get_field(primary_act, "active_until")) if primary_act else None
        phase = _get_field(primary_act, "phase") if primary_act else None

        theme_keys = tuple(_get_field(primary_act, "theme_keys") or ()) if primary_act else ()

        source_key = f.source_planet.upper() if f.source_planet else None
        target_key = f.target_key.upper() if f.target_key else None
        product_spheres = _map_to_product_spheres(f.technical_spheres, source_key, target_key)

        strength = f.strength
        salience = strength

        temp_factor_dict = {
            "factor_id": fid,
            "activation_ids": act_ids,
            "technique": technique,
            "technique_family": technique_family,
            "source_key": source_key,
            "target_key": target_key,
            "theme_keys": theme_keys,
            "product_spheres": product_spheres,
            "polarity": f.polarity,
            "strength": strength,
            "salience": salience,
            "active_from": active_from,
            "exact_at": exact_at,
            "active_until": active_until,
            "phase": phase,
        }

        role = classify_temporal_role(temp_factor_dict, local_start_utc, local_end_utc, day_delta)

        today_factor = TodayFactor(
            factor_id=fid,
            activation_ids=act_ids,
            technique=technique,
            technique_family=technique_family,
            source_key=source_key,
            target_key=target_key,
            theme_keys=theme_keys,
            product_spheres=product_spheres,
            polarity=f.polarity,
            strength=strength,
            salience=salience,
            active_from=active_from,
            exact_at=exact_at,
            active_until=active_until,
            phase=phase,
            temporal_role=role,
        )

        normalized_map[fid] = today_factor

    result = list(normalized_map.values())
    result.sort(key=lambda x: (-x.strength, x.factor_id))
    return result
# END_BLOCK: FACTOR_NORMALIZER
