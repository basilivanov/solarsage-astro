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
#   - TodayFocusEventResult
#   - TodayFeaturedSphereResult
#   - TodayConvergenceResult
#   - TodayFocusResult
#   - local_day_bounds
#   - classify_temporal_role
#   - normalize_factors
#   - build_today_focus
# semantic_blocks:
#   - TIME_BOUNDS: DST-safe UTC boundary calculation
#   - ROLE_CLASSIFICATION: temporal role classifier (anchor_today, supporting, background, unrelated)
#   - FACTOR_NORMALIZER: factor ledger + activation layer normalization and merging
#   - FOCUS_ASSEMBLY: deterministic grouping, ranking, state determination, events (0..3), and featured spheres (0..3)
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
    elif activation_layer is not None and hasattr(activation_layer, "activations"):
        activations_list = list(getattr(activation_layer, "activations") or [])

    # Semantic keys must match the ledger's 4-part format
    # aspect:<source>:<aspect_type>:<target_type>:<target_key>
    def _act_sem_key(act: Any) -> str | None:
        planet = strip_prefix(str(_get_field(act, "planet") or "")).upper()
        target = strip_prefix(str(_get_field(act, "target_planet") or "")).upper()
        aspect = str(_get_field(act, "aspect_type") or "").lower()
        if not (planet and target and aspect):
            return None
        target_type_raw = str(_get_field(act, "target_type") or "").lower()
        if target_type_raw in ("angle", "lot", "house"):
            target_type = target_type_raw
        elif target.upper() in {"ASC", "MC", "IC", "DESC", "DSC"}:
            target_type = "angle"
        elif target.upper() in {"FORTUNE", "SPIRIT", "EROS", "SCIENCE", "MARRIAGE"}:
            target_type = "lot"
        else:
            target_type = "natal_planet"
        return f"aspect:{planet}:{aspect}:{target_type}:{target}"

    activations_by_id: dict[str, Any] = {}
    activations_by_sem_key: dict[str, list[Any]] = {}

    for act in activations_list:
        act_id = _get_field(act, "id") or _get_field(act, "activation_id")
        if act_id:
            activations_by_id[str(act_id)] = act

        # Extract semantic matching info in the ledger's exact key format
        sem = _act_sem_key(act)
        if sem:
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
        # Find matching activation by exact ledger semantic key
        if sem_key in activations_by_sem_key:
            matched_acts.extend(activations_by_sem_key[sem_key])
        # Fallback: activation id mentioned inside the factor id
        if not matched_acts:
            for act_id, act in activations_by_id.items():
                if act_id and act_id in fid:
                    matched_acts.append(act)

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


PLANET_LABELS_RU: dict[str, str] = {
    "SUN": "Солнце", "MOON": "Луна", "MERCURY": "Меркурий",
    "VENUS": "Венера", "MARS": "Марс", "JUPITER": "Юпитер",
    "SATURN": "Сатурн", "URANUS": "Уран", "NEPTUNE": "Нептун", "PLUTO": "Плутон"
}

ASPECT_LABELS_RU: dict[str, str] = {
    "conjunction": "соединение", "opposition": "оппозиция",
    "trine": "тригон", "square": "квадратура", "sextile": "секстиль"
}


# START_BLOCK: FOCUS_ASSEMBLY
@dataclass(frozen=True)
class TodayFocusEventResult:
    id: str
    kind: Literal["exact", "starts", "peak", "building", "separating"]
    occurs_at: datetime | None
    local_date: date
    timezone: str
    precision: Literal["minute", "date", "window"]
    human_title: str
    technical_title: str | None
    meaning: str | None
    source_activation_ids: tuple[str, ...]


@dataclass(frozen=True)
class TodayFeaturedSphereResult:
    key: str
    relevance_rank: int
    state: Literal["convergence_today"]
    summary: str | None
    action: str | None
    convergence_id: str
    source_event_ids: tuple[str, ...]
    source_activation_ids: tuple[str, ...]


@dataclass(frozen=True)
class TodayConvergenceResult:
    id: str
    theme_key: str
    title: str
    summary: str | None
    independent_factor_count: int
    technique_families: tuple[str, ...]
    source_activation_ids: tuple[str, ...]


@dataclass(frozen=True)
class TodayFocusResult:
    state: Literal["convergence_today", "single_impulses", "background_only", "no_accent", "unavailable"]
    convergence: TodayConvergenceResult | None
    events: tuple[TodayFocusEventResult, ...]
    featured_spheres: tuple[TodayFeaturedSphereResult, ...]
    content_state: Literal["ready", "pending", "unavailable", "not_needed"]


def _format_event_titles(factor: TodayFactor) -> tuple[str, str | None]:
    src = PLANET_LABELS_RU.get((factor.source_key or "").upper(), factor.source_key or "")
    tgt = PLANET_LABELS_RU.get((factor.target_key or "").upper(), factor.target_key or "")

    # Try aspect parsing from factor_id or technique
    parts = factor.factor_id.split(":")
    if len(parts) >= 5 and parts[1] == "aspect":
        asp_raw = parts[3].lower()
        asp_ru = ASPECT_LABELS_RU.get(asp_raw, asp_raw)

        # Human title
        if asp_raw == "opposition":
            human = f"{src} напротив твоего {tgt}"
        elif asp_raw == "conjunction":
            human = f"{src} в соединении с твоим {tgt}"
        elif asp_raw == "square":
            human = f"{src} в напряжении с твоим {tgt}"
        elif asp_raw == "trine":
            human = f"{src} в тригоне к твоему {tgt}"
        elif asp_raw == "sextile":
            human = f"{src} в секстиле к твоему {tgt}"
        else:
            human = f"{src} {asp_ru} {tgt}"

        tech = f"{src} {asp_ru} {tgt}"
        return human, tech

    if len(parts) >= 4 and parts[1] == "house":
        house_num = parts[3]
        human = f"{src} в {house_num} доме"
        return human, human

    human = f"{src} {tgt}".strip() or factor.factor_id
    return human, human


def build_today_focus(
    factors: list[TodayFactor] | None,
    *,
    valence_assessments: dict[str, Any] | None = None,
    tz_name: str = "UTC",
    target_date: date | None = None,
) -> TodayFocusResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.build_today_focus
    # purpose: Assemble deterministic TodayFocusResult (grouping, ranking, product state, events 0..3, featured spheres 0..3) from factors (§2.5–2.6, §3, §4.3–4.5).
    # inputs: factors (list[TodayFactor]), valence_assessments (dict | None), tz_name (str), target_date (date)
    # returns: TodayFocusResult
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns unavailable on malformed or None inputs
    # END_FUNCTION_CONTRACT: F-M-TODAY-FOCUS-BUILDER.build_today_focus
    if factors is None or not isinstance(factors, list):
        return TodayFocusResult(
            state="unavailable",
            convergence=None,
            events=(),
            featured_spheres=(),
            content_state="unavailable",
        )

    if target_date is None:
        target_date = date.today()

    local_start_utc, local_end_utc = local_day_bounds(target_date, tz_name)

    # Filter factors by temporal_role
    anchors = [f for f in factors if f.temporal_role == "anchor_today"]
    supporting = [f for f in factors if f.temporal_role == "supporting"]
    backgrounds = [f for f in factors if f.temporal_role == "background"]

    # 1. Grouping (§4.3)
    # Seed group for each anchor_today
    candidate_groups: list[dict[str, Any]] = []

    for anchor in anchors:
        group_factors = [anchor]
        other_candidates = anchors + supporting
        for other in other_candidates:
            if other.factor_id == anchor.factor_id:
                continue
            # Related check: same target_key OR (common theme_key AND common product_sphere)
            same_target = (anchor.target_key is not None and anchor.target_key == other.target_key)
            common_theme = bool(set(anchor.theme_keys) & set(other.theme_keys))
            common_sphere = bool(set(anchor.product_spheres) & set(other.product_spheres))

            if same_target or (common_theme and common_sphere):
                if other not in group_factors:
                    group_factors.append(other)

        # Count independent physical factors (distinct factor_ids)
        distinct_ids = {f.factor_id for f in group_factors}
        if len(distinct_ids) >= 2:
            # Valid convergence candidate group!
            # Attach related background factors (background factors cannot form a group alone, but can join)
            for bg in backgrounds:
                same_tgt = (anchor.target_key is not None and anchor.target_key == bg.target_key)
                com_theme = bool(set(anchor.theme_keys) & set(bg.theme_keys))
                com_sph = bool(set(anchor.product_spheres) & set(bg.product_spheres))
                if (same_tgt or (com_theme and com_sph)) and bg not in group_factors:
                    group_factors.append(bg)

            candidate_groups.append({
                "anchor": anchor,
                "factors": group_factors,
                "distinct_ids": distinct_ids,
            })

    # Deduplicate candidate clusters by frozen set of factor_ids
    clusters_map: dict[frozenset[str], dict[str, Any]] = {}
    for g in candidate_groups:
        cluster_key = frozenset(g["distinct_ids"])
        if cluster_key not in clusters_map:
            cluster_anchors = [f for f in g["factors"] if f.temporal_role == "anchor_today"]
            cluster_anchors.sort(key=lambda f: (-f.strength, f.factor_id))
            primary_anchor = cluster_anchors[0] if cluster_anchors else g["anchor"]

            g["anchor"] = primary_anchor
            clusters_map[cluster_key] = g

    candidate_groups = list(clusters_map.values())

    # 2. Ranking Candidate Groups (§4.4)
    def rank_group(g: dict[str, Any]) -> tuple[int, int, int, int, float, str]:
        g_factors: list[TodayFactor] = g["factors"]
        anchor: TodayFactor = g["anchor"]

        # 1. Date precision: exact_today (3) -> starts_today (2) -> delta_peak (1) -> 0
        precision_rank = 0
        if any(f.exact_at and (local_start_utc <= f.exact_at < local_end_utc) for f in g_factors):
            precision_rank = 3
        elif any(f.active_from and (local_start_utc <= f.active_from < local_end_utc) for f in g_factors):
            precision_rank = 2
        elif anchor.temporal_role == "anchor_today":
            precision_rank = 1

        # 2. Independent physical factor count (capped at 3)
        vol_rank = min(len(g["distinct_ids"]), 3)

        # 3. Number of distinct technique families
        fam_rank = len({f.technique_family for f in g_factors})

        # 4. Strict connection rank: target_key (2) > theme-only (1)
        conn_rank = 2 if any(f.target_key is not None and f.target_key == anchor.target_key for f in g_factors if f.factor_id != anchor.factor_id) else 1

        # 5. Magnitude: sum of effective strengths with family decay
        family_groups: dict[str, list[float]] = {}
        for f in g_factors:
            family_groups.setdefault(f.technique_family, []).append(f.strength)

        magnitude = 0.0
        family_decay = [1.0, 0.5, 0.25]
        for fam, strengths in family_groups.items():
            strengths.sort(reverse=True)
            for idx, s in enumerate(strengths):
                w = family_decay[idx] if idx < len(family_decay) else 0.25
                magnitude += s * w

        # 6. Tie-breaker: min factor_id
        min_fid = min(g["distinct_ids"])

        return (precision_rank, vol_rank, fam_rank, conn_rank, magnitude, min_fid)

    candidate_groups.sort(key=rank_group, reverse=True)

    # 3. State & Assembly Determination (§3)
    if candidate_groups:
        winning_group = candidate_groups[0]
        winning_factors: list[TodayFactor] = winning_group["factors"]
        winning_anchor: TodayFactor = winning_group["anchor"]

        conv_id = f"conv:{winning_anchor.factor_id}"
        theme_key = winning_anchor.target_key or (winning_anchor.theme_keys[0] if winning_anchor.theme_keys else "general")
        all_act_ids = tuple(sorted({act_id for f in winning_factors for act_id in f.activation_ids}))
        all_families = tuple(sorted({f.technique_family for f in winning_factors}))

        convergence = TodayConvergenceResult(
            id=conv_id,
            theme_key=theme_key,
            title="Что сошлось именно сегодня",
            summary=None,  # LLM-owned in W4-C
            independent_factor_count=len(winning_group["distinct_ids"]),
            technique_families=all_families,
            source_activation_ids=all_act_ids,
        )

        # Build events from winning group factors (0..3)
        event_factors = [f for f in winning_factors if f.exact_at or f.active_from or f.temporal_role == "anchor_today"]
        event_factors.sort(key=lambda f: (f.exact_at or f.active_from or local_start_utc, f.factor_id))

        events_list: list[TodayFocusEventResult] = []
        for f in event_factors[:3]:
            human_t, tech_t = _format_event_titles(f)

            kind: Literal["exact", "starts", "peak", "building", "separating"] = "exact"
            if f.exact_at and (local_start_utc <= f.exact_at < local_end_utc):
                kind = "exact"
            elif f.active_from and (local_start_utc <= f.active_from < local_end_utc):
                kind = "starts"
            elif f.phase == "building":
                kind = "building"
            elif f.phase == "separating":
                kind = "separating"
            elif f.temporal_role == "anchor_today":
                kind = "peak"

            occurs_at = f.exact_at or f.active_from
            precision: Literal["minute", "date", "window"] = "minute" if f.exact_at else "date"

            ev_res = TodayFocusEventResult(
                id=f"ev:{f.factor_id}",
                kind=kind,
                occurs_at=occurs_at,
                local_date=target_date,
                timezone=tz_name,
                precision=precision,
                human_title=human_t,
                technical_title=tech_t,
                meaning=None,  # LLM-owned in W4-C
                source_activation_ids=f.activation_ids,
            )
            events_list.append(ev_res)

        events = tuple(events_list)

        # Build featured spheres (0..3) from winning group factors (§4.5)
        spheres_in_group = set()
        for f in winning_factors:
            for s in f.product_spheres:
                spheres_in_group.add(s)

        canonical_order_map = {k: i for i, k in enumerate(CANONICAL_PRODUCT_KEYS)}
        confidence_rank_map = {"high": 3, "medium": 2, "low": 1}

        sphere_scores: list[tuple[int, int, float, int, int, str]] = []
        for sphere_key in spheres_in_group:
            matching_factors = [f for f in winning_factors if sphere_key in f.product_spheres]
            factor_coverage = len(matching_factors)
            anchor_coverage = sum(1 for f in matching_factors if f.temporal_role == "anchor_today")
            salience = max(f.strength for f in matching_factors)

            val_ass = valence_assessments.get(sphere_key) if valence_assessments else None
            conf_val = confidence_rank_map.get(getattr(val_ass, "confidence", "low"), 1) if val_ass else 1
            canon_idx = canonical_order_map.get(sphere_key, 99)

            sphere_scores.append((factor_coverage, anchor_coverage, salience, conf_val, -canon_idx, sphere_key))

        sphere_scores.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]), reverse=True)

        featured_spheres_list: list[TodayFeaturedSphereResult] = []
        for rank_idx, item in enumerate(sphere_scores[:3], 1):
            s_key = item[5]
            matching_f = [f for f in winning_factors if s_key in f.product_spheres]
            s_act_ids = tuple(sorted({act_id for f in matching_f for act_id in f.activation_ids}))
            s_ev_ids = tuple(sorted({e.id for e in events if any(act in s_act_ids for act in e.source_activation_ids)}))

            fs_res = TodayFeaturedSphereResult(
                key=s_key,
                relevance_rank=rank_idx,
                state="convergence_today",
                summary=None,  # LLM-owned in W4-C
                action=None,   # LLM-owned in W4-C
                convergence_id=conv_id,
                source_event_ids=s_ev_ids,
                source_activation_ids=s_act_ids,
            )
            featured_spheres_list.append(fs_res)

        featured_spheres = tuple(featured_spheres_list)

        return TodayFocusResult(
            state="convergence_today",
            convergence=convergence,
            events=events,
            featured_spheres=featured_spheres,
            content_state="not_needed",
        )

    elif anchors:
        events_list = []
        for f in anchors[:3]:
            human_t, tech_t = _format_event_titles(f)
            occurs_at = f.exact_at or f.active_from
            precision = "minute" if f.exact_at else "date"
            events_list.append(
                TodayFocusEventResult(
                    id=f"ev:{f.factor_id}",
                    kind="exact" if f.exact_at else "peak",
                    occurs_at=occurs_at,
                    local_date=target_date,
                    timezone=tz_name,
                    precision=precision,
                    human_title=human_t,
                    technical_title=tech_t,
                    meaning=None,
                    source_activation_ids=f.activation_ids,
                )
            )
        return TodayFocusResult(
            state="single_impulses",
            convergence=None,
            events=tuple(events_list),
            featured_spheres=(),
            content_state="not_needed",
        )

    elif backgrounds:
        return TodayFocusResult(
            state="background_only",
            convergence=None,
            events=(),
            featured_spheres=(),
            content_state="not_needed",
        )

    else:
        return TodayFocusResult(
            state="no_accent",
            convergence=None,
            events=(),
            featured_spheres=(),
            content_state="not_needed",
        )
# END_BLOCK: FOCUS_ASSEMBLY
