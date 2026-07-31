# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_UNITS — canonical physical event units.
# ROLE: Normalizes heterogeneous producers into immutable, fail-closed units.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-UNITS
# purpose: Convert raw physical facts into deterministic canonical event units.
# owns:
#   - apps/api/app/services/today_convergence_units.py
# inputs: RawPhysicalFact values and the frozen TodayConvergenceCanon.
# outputs: producer-independent CanonicalUnitBuildResult records.
# dependencies: today_convergence_canon and Python standard library only.
# side_effects: none; this boundary is pure and does not log or write.
# emitted_logs: none.
# invariants: identity contains physical fields and event windows only; unknown values are excluded.
# failure_policy: malformed facts return a stable ExclusionReason; no fallback eligibility is granted.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-UNITS

# START_MODULE_MAP: M-TODAY-CONVERGENCE-UNITS
# public_entrypoints:
#   - RawPhysicalFact
#   - CanonicalUnit
#   - CanonicalUnitBuildResult
#   - ExclusionReason
#   - build_canonical_unit
# semantic_blocks:
#   - RAW_NORMALIZATION: normalize physical fields, windows, provenance, and data quality.
#   - CANONICAL_IDENTITY: hash normalized physical fields and event-window axes.
#   - ELIGIBILITY: apply explicit canon significance and nested eligibility policies.
# owned_tests:
#   - apps/api/tests/test_today_convergence_units.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-UNITS

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Sequence

from app.services.today_convergence_canon import (
    TodayConvergenceCanon,
    aspect_weight,
    event_class_significance,
    hero_confirmation_policy,
    is_fast_source,
    is_rare_source,
    load_today_convergence_canon,
    map_factor_to_product_spheres,
    source_max_orb,
)


# START_BLOCK: RAW_NORMALIZATION
class ExclusionReason(str, Enum):
    """Stable machine-readable reasons for a unit that cannot be published."""

    UNMAPPED_FACTOR = "unmapped_factor"
    UNKNOWN_EVENT_CLASS = "unknown_event_class"
    INSIGNIFICANT_EVENT_CLASS = "insignificant_event_class"
    UNKNOWN_ASPECT = "unknown_aspect"
    ASPECT_BELOW_THRESHOLD = "aspect_below_threshold"
    UNKNOWN_SOURCE_ORB = "unknown_source_orb"
    INVALID_ORB = "invalid_orb"
    ORB_RATIO_EXCEEDED = "orb_ratio_exceeded"
    EVENT_WINDOW_MISSING = "event_window_missing"
    NAIVE_DATETIME = "naive_datetime"
    INVALID_EVENT_WINDOW = "invalid_event_window"
    EMPTY_DRIVER = "empty_driver"
    UNKNOWN_TARGET_TYPE = "unknown_target_type"
    INVALID_HOUSE = "invalid_house"
    INVALID_DATA_QUALITY = "invalid_data_quality"
    INVALID_BIRTH_TIME_ROBUSTNESS = "invalid_birth_time_robustness"
    INVALID_BIRTH_TIME_MODE = "invalid_birth_time_mode"
    INVALID_TEMPORAL_ROLE = "invalid_temporal_role"
    INVALID_POLARITY = "invalid_polarity"
    INVALID_STRENGTH = "invalid_strength"
    INVALID_TARGET_SALIENCE = "invalid_target_salience"
    INVALID_PROVENANCE = "invalid_provenance"
    INVALID_TECHNICAL_SPHERES = "invalid_technical_spheres"
    TIME_SENSITIVE_BIRTH_TIME = "time_sensitive_birth_time"
    BACKGROUND = "background"


WindowValue = date | datetime


@dataclass(frozen=True)
class RawPhysicalFact:
    """The smallest producer-neutral physical fact accepted by this boundary."""

    technique: str = ""
    technique_family: str = ""
    source_key: str | None = None
    target_key: str | None = None
    target_type: str = ""
    target_salience: float = 0.0
    aspect_type: str | None = None
    orb: float | None = None
    event_class: str | None = None
    house: int | None = None
    exact_at: WindowValue | None = None
    phase: str | None = None
    active_from: WindowValue | None = None
    active_until: WindowValue | None = None
    data_quality: str | None = None
    birth_time_mode: str = "unknown"
    birth_time_robustness: str = "robust"
    technical_spheres: Sequence[str] = ()
    polarity: str = "neutral"
    strength: float = 0.0
    temporal_role: str = "anchor_today"
    producer: str | None = None
    provenance_ids: Sequence[str] = ()


@dataclass(frozen=True)
class CanonicalUnit:
    """Immutable normalized unit used by later grouping and presentation layers."""

    canonical_event_id: str
    semantic_key: str
    driver_key: str
    technique_horizon: str
    event_class: str | None
    source_key: str | None
    target_key: str
    target_type: str
    target_salience: float
    aspect_type: str | None
    orb: float | None
    max_orb: float | None
    orb_ratio: float | None
    exact_at: WindowValue | None
    phase: str | None
    active_from: WindowValue | None
    active_until: WindowValue | None
    data_quality: str
    birth_time_mode: str
    birth_time_robustness: str
    product_spheres: tuple[str, ...]
    polarity: str
    strength: float
    impulse_eligible: bool
    evidence_eligible: bool
    rare_anchor_eligible: bool
    hero_confirmation_eligible: bool
    exclusion_reason: ExclusionReason | None
    provenance_ids: tuple[str, ...]
    house: int | None
    temporal_role: str


@dataclass(frozen=True)
class CanonicalUnitBuildResult:
    """Result wrapper preserving an exclusion reason without raising for bad input."""

    unit: CanonicalUnit | None
    exclusion_reason: ExclusionReason | None
    accepted: bool


def _exclude(reason: ExclusionReason) -> CanonicalUnitBuildResult:
    return CanonicalUnitBuildResult(unit=None, exclusion_reason=reason, accepted=False)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _source(value: str | None) -> str | None:
    normalized = _text(value)
    if normalized is None:
        return None
    key = normalized.upper()
    for prefix in ("TRANSIT_", "NATAL_"):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return key or None


def _technique(value: str | None) -> str | None:
    normalized = _text(value)
    return normalized.lower() if normalized is not None else None


def _key(value: str | None) -> str | None:
    return _source(value)


def _family(value: str | None) -> str | None:
    normalized = _text(value)
    return normalized.lower() if normalized is not None else None


def _event_class(value: str | None) -> str | None:
    normalized = _text(value)
    return normalized.lower() if normalized is not None else None


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _window(value: WindowValue | None) -> tuple[WindowValue | None, ExclusionReason | None]:
    if value is None:
        return None, None
    if isinstance(value, datetime):
        try:
            if value.tzinfo is None or value.utcoffset() is None:
                return None, ExclusionReason.NAIVE_DATETIME
            return value.astimezone(timezone.utc), None
        except (OverflowError, TypeError, ValueError):
            return None, ExclusionReason.INVALID_EVENT_WINDOW
    if isinstance(value, date):
        return value, None
    return None, ExclusionReason.INVALID_EVENT_WINDOW


def _window_token(value: WindowValue | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value.isoformat()


def _text_sequence(value: Any, reason: ExclusionReason) -> tuple[str, ...] | ExclusionReason:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return reason
    normalized = []
    for item in value:
        if not isinstance(item, str):
            return reason
        text = item.strip()
        if text:
            normalized.append(text)
    return tuple(normalized)


def _provenance(values: Sequence[str]) -> tuple[str, ...]:
    normalized = {_text(value) for value in values}
    return tuple(sorted(value for value in normalized if value is not None))


def _identity_payload(
    *,
    technique: str,
    technique_family: str,
    source_key: str | None,
    target_key: str,
    target_type: str,
    aspect_type: str | None,
    event_class: str | None,
    house: int | None,
    exact_at: WindowValue | None,
    active_from: WindowValue | None,
    active_until: WindowValue | None,
) -> dict[str, Any]:
    return {
        "identity_version": "evt_v1",
        "physical": {
            "technique": technique,
            "technique_family": technique_family,
            "source_key": source_key,
            "target_key": target_key,
            "target_type": target_type,
            "aspect_type": aspect_type,
            "event_class": event_class,
            "house": house,
        },
        "event_window": {
            "exact_at": _window_token(exact_at),
            "active_from": _window_token(active_from),
            "active_until": _window_token(active_until),
        },
    }


def _canonical_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "evt_v1_" + hashlib.sha256(encoded).hexdigest()[:32]


def _semantic_key(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload["physical"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return encoded


def _driver_key(canon: TodayConvergenceCanon, family: str, source: str | None) -> str | None:
    if family in {
        "firdar", "profection", "solar_return", "lunar_return", "return", "progression", "progressive",
    }:
        return family
    if family == "transit":
        return source if canon.driver_rules.get("transit") == "source_planet" else None
    return source


def _target_type(value: str | None) -> str | None:
    normalized = _text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    return "natal_planet" if normalized == "planet" else normalized


def _accepted_result(
    raw: RawPhysicalFact,
    canon: TodayConvergenceCanon,
) -> CanonicalUnitBuildResult:
    technique = _technique(raw.technique)
    family = _family(raw.technique_family)
    source = _source(raw.source_key)
    target = _key(raw.target_key)
    target_type = _target_type(raw.target_type)
    if technique is None or family is None or target is None:
        return _exclude(ExclusionReason.UNMAPPED_FACTOR)
    if target_type not in {"natal_planet", "house", "lot", "angle", "sphere"}:
        return _exclude(ExclusionReason.UNKNOWN_TARGET_TYPE)
    if target_type == "house" and (not isinstance(raw.house, int) or isinstance(raw.house, bool) or not 1 <= raw.house <= 12):
        return _exclude(ExclusionReason.INVALID_HOUSE)

    technical_spheres = _text_sequence(raw.technical_spheres, ExclusionReason.INVALID_TECHNICAL_SPHERES)
    if isinstance(technical_spheres, ExclusionReason):
        return _exclude(technical_spheres)
    provenance_ids = _text_sequence(raw.provenance_ids, ExclusionReason.INVALID_PROVENANCE)
    if isinstance(provenance_ids, ExclusionReason):
        return _exclude(provenance_ids)
    mapped_spheres = map_factor_to_product_spheres(canon, technical_spheres, source, target)
    if not mapped_spheres:
        return _exclude(ExclusionReason.UNMAPPED_FACTOR)

    normalized_aspect = _text(raw.aspect_type)
    normalized_aspect = normalized_aspect.lower() if normalized_aspect is not None else None
    weight: float | None = None
    max_orb: float | None = None
    orb_ratio: float | None = None
    if normalized_aspect is not None:
        weight = aspect_weight(canon, normalized_aspect)
        if weight is None:
            return _exclude(ExclusionReason.UNKNOWN_ASPECT)
        if weight < canon.aspect_weight_min:
            return _exclude(ExclusionReason.ASPECT_BELOW_THRESHOLD)
        if not _finite(raw.orb) or float(raw.orb) < 0:
            return _exclude(ExclusionReason.INVALID_ORB)
        max_orb = source_max_orb(canon, source)
        if max_orb is None:
            return _exclude(ExclusionReason.UNKNOWN_SOURCE_ORB)
        orb_ratio = float(raw.orb) / max_orb
        if orb_ratio > canon.orb_ratio_max:
            return _exclude(ExclusionReason.ORB_RATIO_EXCEEDED)
    elif raw.orb is not None:
        if not _finite(raw.orb) or float(raw.orb) < 0:
            return _exclude(ExclusionReason.INVALID_ORB)

    event_class = _event_class(raw.event_class)
    if event_class is not None and event_class_significance(canon, event_class) is None:
        return _exclude(ExclusionReason.UNKNOWN_EVENT_CLASS)
    if normalized_aspect is None:
        significance = event_class_significance(canon, event_class)
        if significance is None:
            return _exclude(ExclusionReason.UNKNOWN_EVENT_CLASS)
        if significance is False:
            return _exclude(ExclusionReason.INSIGNIFICANT_EVENT_CLASS)

    exact_at, reason = _window(raw.exact_at)
    if reason is not None:
        return _exclude(reason)
    active_from, reason = _window(raw.active_from)
    if reason is not None:
        return _exclude(reason)
    active_until, reason = _window(raw.active_until)
    if reason is not None:
        return _exclude(reason)
    if exact_at is None and active_from is None and active_until is None:
        return _exclude(ExclusionReason.EVENT_WINDOW_MISSING)
    window_values = (active_from, exact_at, active_until)
    has_date = any(type(value) is date for value in window_values if value is not None)
    has_datetime = any(isinstance(value, datetime) for value in window_values if value is not None)
    if has_date and has_datetime:
        return _exclude(ExclusionReason.INVALID_EVENT_WINDOW)
    try:
        if active_from is not None and exact_at is not None and active_from > exact_at:
            return _exclude(ExclusionReason.INVALID_EVENT_WINDOW)
        if exact_at is not None and active_until is not None and exact_at > active_until:
            return _exclude(ExclusionReason.INVALID_EVENT_WINDOW)
        if active_from is not None and active_until is not None and active_from > active_until:
            return _exclude(ExclusionReason.INVALID_EVENT_WINDOW)
    except TypeError:
        return _exclude(ExclusionReason.INVALID_EVENT_WINDOW)

    data_quality = _text(raw.data_quality)
    if data_quality is None or data_quality.lower() == "invalid":
        return _exclude(ExclusionReason.INVALID_DATA_QUALITY)
    data_quality = data_quality.lower()
    birth_time_mode = _text(raw.birth_time_mode)
    if birth_time_mode is None or birth_time_mode.lower() not in {"exact", "bucket", "unknown"}:
        return _exclude(ExclusionReason.INVALID_BIRTH_TIME_MODE)
    birth_time_mode = birth_time_mode.lower()
    birth_time_robustness = _text(raw.birth_time_robustness)
    if birth_time_robustness is None or birth_time_robustness.lower() not in {"robust", "time_sensitive"}:
        return _exclude(ExclusionReason.INVALID_BIRTH_TIME_ROBUSTNESS)
    birth_time_robustness = birth_time_robustness.lower()

    temporal_role = _text(raw.temporal_role)
    if temporal_role is None or temporal_role.lower() not in {"anchor_today", "supporting", "background", "unrelated"}:
        return _exclude(ExclusionReason.INVALID_TEMPORAL_ROLE)
    temporal_role = temporal_role.lower()
    polarity = _text(raw.polarity)
    if polarity is None or polarity.lower() not in {"supportive", "tense", "mixed", "neutral"}:
        return _exclude(ExclusionReason.INVALID_POLARITY)
    polarity = polarity.lower()
    if not _finite(raw.strength) or not 0 <= float(raw.strength) <= 1:
        return _exclude(ExclusionReason.INVALID_STRENGTH)
    if not _finite(raw.target_salience) or not 0 <= float(raw.target_salience) <= 1:
        return _exclude(ExclusionReason.INVALID_TARGET_SALIENCE)
    phase = _text(raw.phase)
    phase = phase.lower() if phase is not None else None

    driver = _driver_key(canon, family, source)
    if driver is None or not driver.strip():
        return _exclude(ExclusionReason.EMPTY_DRIVER)

    payload = _identity_payload(
        technique=technique,
        technique_family=family,
        source_key=source,
        target_key=target,
        target_type=target_type,
        aspect_type=normalized_aspect,
        event_class=event_class,
        house=raw.house,
        exact_at=exact_at,
        active_from=active_from,
        active_until=active_until,
    )
    rare = is_rare_source(
        canon,
        source,
        technique_family=family,
        event_class=event_class,
        aspect_type=normalized_aspect,
    )
    fast = is_fast_source(canon, source)
    hero = hero_confirmation_policy(canon, source, technique_family=family, event_class=event_class)
    time_sensitive = birth_time_robustness == "time_sensitive" and birth_time_mode in {"bucket", "unknown"}
    background = temporal_role == "background"
    if time_sensitive:
        impulse = evidence = rare = hero = False
        exclusion_reason = ExclusionReason.TIME_SENSITIVE_BIRTH_TIME
    elif background:
        impulse = evidence = rare = hero = False
        exclusion_reason: ExclusionReason | None = ExclusionReason.BACKGROUND
    else:
        impulse = True
        evidence = True
        if fast:
            rare = False
            hero = False
        exclusion_reason = None

    unit = CanonicalUnit(
        canonical_event_id=_canonical_id(payload),
        semantic_key=_semantic_key(payload),
        driver_key=driver,
        technique_horizon=family,
        event_class=event_class,
        source_key=source,
        target_key=target,
        target_type=target_type,
        target_salience=float(raw.target_salience),
        aspect_type=normalized_aspect,
        orb=float(raw.orb) if raw.orb is not None else None,
        max_orb=max_orb,
        orb_ratio=orb_ratio,
        exact_at=exact_at,
        phase=phase,
        active_from=active_from,
        active_until=active_until,
        data_quality=data_quality,
        birth_time_mode=birth_time_mode,
        birth_time_robustness=birth_time_robustness,
        product_spheres=mapped_spheres,
        polarity=polarity,
        strength=float(raw.strength),
        impulse_eligible=impulse,
        evidence_eligible=evidence,
        rare_anchor_eligible=rare,
        hero_confirmation_eligible=hero,
        exclusion_reason=exclusion_reason,
        provenance_ids=_provenance(provenance_ids),
        house=raw.house,
        temporal_role=temporal_role,
    )
    return CanonicalUnitBuildResult(unit=unit, exclusion_reason=exclusion_reason, accepted=True)


# END_BLOCK: RAW_NORMALIZATION


# START_BLOCK: CANONICAL_IDENTITY
def build_canonical_unit(
    raw: RawPhysicalFact,
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalUnitBuildResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-UNITS.build_canonical_unit
    # purpose: Normalize one physical fact and assign producer-independent canonical identity.
    # inputs: raw — producer-neutral physical fact; canon — frozen canon, loaded when omitted.
    # returns: accepted immutable unit or typed fail-closed exclusion result.
    # side_effects: reads canon YAML only when canon is omitted; never writes or logs.
    # emitted_logs: none.
    # error_behavior: malformed domain input returns ExclusionReason; canon errors propagate.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-UNITS.build_canonical_unit
    return _accepted_result(raw, canon or load_today_convergence_canon())


# END_BLOCK: CANONICAL_IDENTITY


# START_BLOCK: ELIGIBILITY
__all__ = [
    "CanonicalUnit",
    "CanonicalUnitBuildResult",
    "ExclusionReason",
    "RawPhysicalFact",
    "build_canonical_unit",
]
# END_BLOCK: ELIGIBILITY
