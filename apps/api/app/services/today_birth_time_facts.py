# ############################################################################
# AI_HEADER: MODULE_TODAY-BIRTH-TIME-FACTS — robust activation-grid facts.
# ROLE: Converts one birth-time resolution and its ordered activation grid into
#       deterministic producer-neutral RawPhysicalFact records plus typed audit.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-BIRTH-TIME-FACTS
# purpose: Convert exact or canonical birth-time control samples into robust physical facts.
# owns:
#   - apps/api/app/services/today_birth_time_facts.py
# inputs: BirthTimeResolution and client ActivationGridSample records.
# outputs: Immutable RawPhysicalFact tuple and BirthTimeFactsAudit.
# dependencies: today_birth_time, solarsage_client, activation schemas, frozen convergence canon.
# side_effects: loads the validated canon once per call; no database, HTTP, logging, or analysis.
# emitted_logs: none.
# invariants: non-exact facts survive every control with stable physical identity and frozen orb margin.
# failure_policy: malformed top-level input raises TodayBirthTimeFactsError; malformed individual evidence is audited.
# END_MODULE_CONTRACT: M-TODAY-BIRTH-TIME-FACTS

# START_MODULE_MAP: M-TODAY-BIRTH-TIME-FACTS
# public_entrypoints:
#   - TodayBirthTimeFactsError
#   - BirthTimeFactsAudit
#   - BirthTimeFactsResult
#   - build_birth_time_facts
# semantic_blocks:
#   - BOUNDARY: strict production-type and control-grid validation.
#   - IDENTITY: physical identity and cross-control observation matching.
#   - ROBUSTNESS: active/polarity/sect/orb-margin stability checks.
#   - FACTS: deterministic RawPhysicalFact projection and audit.
# owned_tests:
#   - apps/api/tests/test_today_birth_time_facts.py
# END_MODULE_MAP: M-TODAY-BIRTH-TIME-FACTS

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.clients.solarsage_client import ActivationGridSample
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.services.today_birth_time import BirthTimeResolution, resolve_birth_time
from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_units import RawPhysicalFact


class TodayBirthTimeFactsError(ValueError):
    """Raised when the activation-grid boundary cannot be trusted."""


@dataclass(frozen=True)
class BirthTimeFactsAudit:
    """Deterministic counts for published and excluded activation identities."""

    input_sample_count: int
    input_activation_count: int
    published_fact_count: int
    excluded_by_reason: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class BirthTimeFactsResult:
    """Immutable robust facts and their audit record."""

    facts: tuple[RawPhysicalFact, ...]
    audit: BirthTimeFactsAudit


@dataclass(frozen=True)
class _Observation:
    identity: tuple[str, ...]
    activation: ActivationEvidence
    technique: str
    technique_family: str
    target_type: str
    target_key: str
    source_key: str | None
    aspect: str | None
    windows: tuple[date | datetime | None, date | datetime | None, date | datetime | None]
    phase: str | None
    event_class: str | None


# START_BLOCK: BOUNDARY
def _fail(reason: str) -> None:
    raise TodayBirthTimeFactsError(f"today_birth_time_facts:{reason}")


def _normalized(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _validate_resolution(resolution: BirthTimeResolution, canon: Any) -> None:
    if type(resolution) is not BirthTimeResolution:
        _fail("invalid_resolution")
    if type(resolution.control_times) is not tuple or not resolution.control_times:
        _fail("invalid_control_times")
    if any(type(value) is not str or not value for value in resolution.control_times):
        _fail("invalid_control_times")
    try:
        exact_time = time.fromisoformat(resolution.birth_time) if resolution.birth_time is not None else None
        expected = resolve_birth_time(
            mode=resolution.mode,
            birth_time=exact_time,
            bucket=resolution.bucket,
            canon=canon,
        )
    except (TypeError, ValueError):
        _fail("invalid_resolution")
    if (
        resolution.control_times != expected.control_times
        or resolution.canonical_gap_hours != expected.canonical_gap_hours
        or resolution.range_start != expected.range_start
        or resolution.range_end != expected.range_end
    ):
        _fail("invalid_resolution")
    if resolution.mode == "exact" and len(resolution.control_times) != 1:
        _fail("invalid_resolution")
    if resolution.mode in {"bucket", "unknown"} and (
        not isinstance(resolution.canonical_gap_hours, int)
        or isinstance(resolution.canonical_gap_hours, bool)
        or resolution.canonical_gap_hours <= 0
    ):
        _fail("invalid_resolution")


def _parse_window(value: Any) -> date | datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("window")
    text = value.strip()
    if "T" not in text and " " not in text:
        return date.fromisoformat(text)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("naive window")
    return parsed


def _window_tuple(
    activation: ActivationEvidence,
    *,
    target_tz: ZoneInfo,
    exact: bool,
) -> tuple[date | datetime | None, date | datetime | None, date | datetime | None]:
    windows = tuple(
        _parse_window(value)
        for value in (activation.active_from, activation.exact_at, activation.active_until)
    )
    typed_values = tuple(value for value in windows if value is not None)
    if not typed_values:
        raise ValueError("missing window")
    if any(type(value) is date for value in typed_values) and any(isinstance(value, datetime) for value in typed_values):
        raise ValueError("mixed window")
    try:
        active_from, exact_at, active_until = windows
        if active_from is not None and exact_at is not None and active_from > exact_at:
            raise ValueError("window order")
        if exact_at is not None and active_until is not None and exact_at > active_until:
            raise ValueError("window order")
        if active_from is not None and active_until is not None and active_from > active_until:
            raise ValueError("window order")
    except TypeError as exc:
        raise ValueError("window order") from exc
    if exact:
        return windows
    return tuple(
        value.astimezone(target_tz).date() if isinstance(value, datetime) else value
        for value in windows
    )  # type: ignore[return-value]


def _identity(activation: ActivationEvidence) -> tuple[str, ...]:
    return tuple(
        _normalized(getattr(activation, field, None))
        for field in (
            "technique",
            "technique_family",
            "kind",
            "source_planet",
            "target_type",
            "target_key",
            "aspect",
            "house",
            "lot",
            "angle",
        )
    )


def _has_physical_identity(identity: tuple[str, ...]) -> bool:
    return all(identity[index] for index in (0, 1, 2, 4, 5))


def _event_class(technique: str, aspect: str | None) -> str | None:
    if technique in {"firdar_major", "firdar_minor"}:
        return "timelord_period_change"
    if technique == "solar_return":
        return "solar_return"
    if technique == "lunar_return":
        return "lunar_return"
    if technique == "monthly_profection":
        return "monthly_profection"
    if technique in {"transit_planet_in_house", "planet_in_house"}:
        return "house_ingress"
    if aspect is not None:
        return None
    return None


def _observation(
    activation: ActivationEvidence,
    *,
    target_tz: ZoneInfo,
    exact: bool,
) -> _Observation:
    if type(activation) is not ActivationEvidence:
        raise ValueError("activation type")
    if not isinstance(activation.id, str) or not activation.id.strip() or not isinstance(activation.active, bool):
        raise ValueError("activation identity")
    if not isinstance(activation.debug, Mapping):
        raise ValueError("activation debug")
    technique = _normalized(activation.technique)
    family = _normalized(activation.technique_family)
    target_type = "natal_planet" if _normalized(activation.target_type) == "planet" else _normalized(activation.target_type)
    target_key = _normalized(activation.target_key)
    source_key = _normalized(activation.source_planet) or None
    aspect = _normalized(activation.aspect) or None
    if not technique or not family or not target_type or not target_key:
        raise ValueError("activation identity")
    if aspect is not None and (not _finite(activation.orb) or float(activation.orb) < 0):
        raise ValueError("activation orb")
    if not _finite(activation.strength) or not 0 <= float(activation.strength) <= 1:
        raise ValueError("activation strength")
    if not isinstance(activation.polarity, str) or not activation.polarity.strip():
        raise ValueError("activation polarity")
    windows = _window_tuple(activation, target_tz=target_tz, exact=exact)
    return _Observation(
        identity=_identity(activation),
        activation=activation,
        technique=technique,
        technique_family=family,
        target_type=target_type,
        target_key=target_key,
        source_key=source_key,
        aspect=aspect,
        windows=windows,
        phase=_normalized(activation.phase) or None,
        event_class=_event_class(technique, aspect),
    )


def _validate_samples(
    resolution: BirthTimeResolution,
    samples: Sequence[ActivationGridSample],
) -> tuple[ActivationGridSample, ...]:
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes, bytearray, Mapping)):
        _fail("invalid_samples")
    if len(samples) != len(resolution.control_times):
        _fail("sample_count")
    typed = tuple(samples)
    if any(type(sample) is not ActivationGridSample for sample in typed):
        _fail("invalid_sample")
    if any(sample.birth_time != expected for sample, expected in zip(typed, resolution.control_times, strict=True)):
        _fail("sample_order")
    layers = tuple(sample.activation_layer for sample in typed)
    if any(type(layer) is not ActivationLayer for layer in layers):
        _fail("invalid_layer")
    invariants = tuple(
        (
            layer.target_date,
            layer.target_time,
            layer.target_tz,
            layer.house_system,
            layer.calculation_version,
            layer.activation_layer_version,
        )
        for layer in layers
    )
    if any(item != invariants[0] for item in invariants[1:]):
        _fail("layer_invariant")
    try:
        ZoneInfo(invariants[0][2])
    except (ZoneInfoNotFoundError, ValueError):
        _fail("layer_invariant")
    for layer in layers:
        ids = [activation.id for activation in layer.activations if type(activation) is ActivationEvidence]
        if len(ids) != len(set(ids)):
            _fail("duplicate_activation_id")
    return typed


# END_BLOCK: BOUNDARY


# START_BLOCK: IDENTITY
def _excluded(reason_counts: dict[str, int], reason: str) -> None:
    reason_counts[reason] = reason_counts.get(reason, 0) + 1


def _layer_observations(
    samples: tuple[ActivationGridSample, ...],
    *,
    target_tz: ZoneInfo,
    exact: bool,
    reason_counts: dict[str, int],
) -> tuple[list[dict[tuple[str, ...], list[_Observation]]], int, tuple[set[tuple[str, ...]], ...]]:
    by_sample: list[dict[tuple[str, ...], list[_Observation]]] = []
    malformed_by_sample: list[set[tuple[str, ...]]] = []
    activation_count = 0
    for sample in samples:
        identities: dict[tuple[str, ...], list[_Observation]] = {}
        malformed: set[tuple[str, ...]] = set()
        for activation in sample.activation_layer.activations:
            activation_count += 1
            try:
                observation = _observation(activation, target_tz=target_tz, exact=exact)
            except (AttributeError, TypeError, ValueError, OverflowError):
                identity = _identity(activation)
                if _has_physical_identity(identity):
                    malformed.add(identity)
                else:
                    _excluded(reason_counts, "malformed_activation")
                continue
            identities.setdefault(observation.identity, []).append(observation)
        by_sample.append(identities)
        malformed_by_sample.append(malformed)
    return by_sample, activation_count, tuple(malformed_by_sample)


# END_BLOCK: IDENTITY


# START_BLOCK: ROBUSTNESS
_ROLE_ORDER = ("anchor_today", "supporting", "background", "unrelated")

def _is_time_sensitive_target(observations: Sequence[_Observation]) -> bool:
    return any(observation.target_type in {"house", "angle", "lot"} for observation in observations)


def _sect_is_stable(observations: Sequence[_Observation]) -> bool:
    if not observations or observations[0].technique_family != "firdar":
        return True
    values = [observation.activation.debug.get("is_day_birth") for observation in observations]
    return all(type(value) is bool for value in values) and len(set(values)) == 1


def _margin_is_stable(observations: Sequence[_Observation]) -> str | None:
    if not observations[0].aspect:
        return None
    metadata: list[tuple[float, float]] = []
    for observation in observations:
        debug = observation.activation.debug
        max_orb = debug.get("max_orb")
        speed = debug.get("target_speed_deg_per_hour")
        if not _finite(max_orb) or float(max_orb) <= 0 or not _finite(speed) or float(speed) < 0:
            return "orb_metadata_missing"
        metadata.append((float(max_orb), float(speed)))
    if any(item != metadata[0] for item in metadata[1:]):
        tolerance = 1e-9
        if any(abs(item[0] - metadata[0][0]) > tolerance or abs(item[1] - metadata[0][1]) > tolerance for item in metadata[1:]):
            return "orb_metadata_changed"
    return None


def _representative_fact(
    observations: Sequence[_Observation],
    resolution: BirthTimeResolution,
    *,
    target_date: date,
    target_tz: ZoneInfo,
) -> RawPhysicalFact:
    representative = observations[0]
    activation = representative.activation
    orb = max((float(item.activation.orb) for item in observations if item.activation.orb is not None), default=None)
    strength = max(float(item.activation.strength) for item in observations)
    provenance_ids = tuple(sorted({item.activation.id.strip() for item in observations}))
    exact_at = representative.windows[1]
    roles = []
    for observation in observations:
        observed_exact_at = observation.windows[1]
        if isinstance(observed_exact_at, datetime):
            observed_date = observed_exact_at.astimezone(target_tz).date()
        else:
            observed_date = observed_exact_at
        observed_active_from = observation.windows[0]
        if isinstance(observed_active_from, datetime):
            active_from_date = observed_active_from.astimezone(target_tz).date()
        else:
            active_from_date = observed_active_from
        if observed_date == target_date or active_from_date == target_date:
            role = "anchor_today"
        elif observation.phase in {"background", "period"}:
            role = "background"
        elif observation.phase in {"applying", "separating"}:
            role = "supporting"
        elif observation.phase == "exact":
            role = "anchor_today"
        else:
            role = "unrelated"
        roles.append(role)
    temporal_role = max(roles, key=_ROLE_ORDER.index)
    return RawPhysicalFact(
        technique=representative.technique,
        technique_family=representative.technique_family,
        source_key=representative.source_key,
        target_key=representative.target_key,
        target_type=representative.target_type,
        target_salience=1.0,
        aspect_type=representative.aspect,
        orb=orb,
        event_class=representative.event_class,
        house=activation.house,
        exact_at=exact_at,
        phase=representative.phase,
        active_from=representative.windows[0],
        active_until=representative.windows[2],
        data_quality="valid",
        birth_time_mode=resolution.mode,
        birth_time_robustness="robust",
        technical_spheres=(),
        polarity=_normalized(activation.polarity),
        strength=strength,
        temporal_role=temporal_role,
        producer="activation",
        provenance_ids=provenance_ids,
    )


# END_BLOCK: ROBUSTNESS


# START_BLOCK: FACTS
def build_birth_time_facts(
    resolution: BirthTimeResolution,
    samples: Sequence[ActivationGridSample],
) -> BirthTimeFactsResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-BIRTH-TIME-FACTS.build_birth_time_facts
    # purpose: Convert one exact or control-grid resolution into deterministic raw physical facts.
    # inputs: exact BirthTimeResolution and ordered client ActivationGridSample sequence.
    # returns: immutable facts plus audit counts; unstable identities are excluded once by stable reason.
    # side_effects: loads the frozen convergence canon once; no writes or logs.
    # emitted_logs: none.
    # error_behavior: raises TodayBirthTimeFactsError for top-level boundary violations; audits individual evidence.
    # END_FUNCTION_CONTRACT: F-M-TODAY-BIRTH-TIME-FACTS.build_birth_time_facts
    canon = load_today_convergence_canon()
    _validate_resolution(resolution, canon)
    typed_samples = _validate_samples(resolution, samples)
    layer = typed_samples[0].activation_layer
    try:
        target_date = date.fromisoformat(layer.target_date)
    except (TypeError, ValueError):
        _fail("layer_invariant")
    try:
        target_tz = ZoneInfo(layer.target_tz)
    except (ZoneInfoNotFoundError, ValueError):
        _fail("layer_invariant")
    reason_counts: dict[str, int] = {}
    observations, activation_count, malformed_by_sample = _layer_observations(
        typed_samples,
        target_tz=target_tz,
        exact=resolution.mode == "exact",
        reason_counts=reason_counts,
    )
    identities = sorted(
        set().union(
            *(set(item) for item in observations),
            *(set(item) for item in malformed_by_sample),
        )
    )
    facts: list[RawPhysicalFact] = []
    for identity in identities:
        rows = [sample.get(identity, []) for sample in observations]
        if any(len(row) > 1 for row in rows):
            _excluded(reason_counts, "duplicate_identity")
            continue
        if any(not row and identity not in malformed_by_sample[index] for index, row in enumerate(rows)):
            _excluded(reason_counts, "missing_control")
            continue
        if any(identity in malformed_by_sample[index] for index in range(len(malformed_by_sample))):
            _excluded(reason_counts, "malformed_activation")
            continue
        matched = tuple(row[0] for row in rows)
        if any(not item.activation.active for item in matched):
            _excluded(reason_counts, "inactive_control")
            continue
        if len({_normalized(item.activation.polarity) for item in matched}) != 1:
            _excluded(reason_counts, "polarity_changed")
            continue
        if resolution.mode != "exact" and _is_time_sensitive_target(matched):
            _excluded(reason_counts, "birth_time_sensitive_target")
            continue
        if resolution.mode != "exact" and not _sect_is_stable(matched):
            _excluded(reason_counts, "sect_changed_or_unknown")
            continue
        metadata_reason = _margin_is_stable(matched) if resolution.mode != "exact" else None
        if metadata_reason is not None:
            _excluded(reason_counts, metadata_reason)
            continue
        if resolution.mode != "exact" and matched[0].aspect:
            max_orb = float(matched[0].activation.debug["max_orb"])
            gap_hours = float(resolution.canonical_gap_hours or 0)
            for item in matched:
                orb = float(item.activation.orb)
                speed = float(item.activation.debug["target_speed_deg_per_hour"])
                if orb / max_orb + speed * gap_hours / max_orb > canon.orb_ratio_max:
                    metadata_reason = "orb_margin_exceeded"
                    break
            if metadata_reason is not None:
                _excluded(reason_counts, metadata_reason)
                continue
        facts.append(
            _representative_fact(
                matched,
                resolution,
                target_date=target_date,
                target_tz=target_tz,
            )
        )
    facts.sort(key=lambda fact: (
        _normalized(fact.technique),
        _normalized(fact.technique_family),
        _normalized(fact.source_key),
        _normalized(fact.target_type),
        _normalized(fact.target_key),
        _normalized(fact.aspect_type),
        _normalized(fact.house),
        _normalized(fact.exact_at),
    ))
    audit = BirthTimeFactsAudit(
        input_sample_count=len(typed_samples),
        input_activation_count=activation_count,
        published_fact_count=len(facts),
        excluded_by_reason=tuple(sorted(reason_counts.items())),
    )
    return BirthTimeFactsResult(facts=tuple(facts), audit=audit)


# END_BLOCK: FACTS


__all__ = [
    "BirthTimeFactsAudit",
    "BirthTimeFactsResult",
    "TodayBirthTimeFactsError",
    "build_birth_time_facts",
]
