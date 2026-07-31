# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_TONE — deterministic canonical tone layers.
# ROLE: Computes unit, group, and timezone-aware day tone without selection or wire behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-TONE
# purpose: Apply the frozen tone-candidate-0.1 policy to an immutable ledger and grouping result.
# owns:
#   - apps/api/app/services/today_convergence_tone.py
# inputs: CanonicalLedger, CanonicalGroupingResult, target date/timezone, selected audit IDs, validated canon.
# outputs: immutable CanonicalToneResult with group tones, day tone, scores, and selected/context audit.
# dependencies: today_convergence_canon, today_convergence_ledger, today_convergence_groups, today_convergence_units, Python standard library.
# side_effects: none; this module is pure and emits no runtime logs.
# emitted_logs: none.
# invariants: all coefficients come from TonePolicyCanon; fresh dates use aware IANA timezone conversion; selection affects audit only.
# failure_policy: malformed API input, invalid timezone, and foreign references raise TodayConvergenceToneError.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-TONE

# START_MODULE_MAP: M-TODAY-CONVERGENCE-TONE
# public_entrypoints:
#   - CanonicalGroupTone
#   - CanonicalToneScores
#   - CanonicalToneAudit
#   - CanonicalToneResult
#   - TodayConvergenceToneError
#   - compute_canonical_tone
# semantic_blocks:
#   - INPUT_VALIDATION: validate immutable ledger/group references and audit selection.
#   - UNIT_POLARITY: normalize polarity and calculate canon-driven unit weights.
#   - GROUP_TONE: deduplicate distinct drivers and calculate weighted group balance.
#   - DAY_TONE: calculate timezone-aware fresh non-fast day tone.
#   - AUDIT: materialize sorted immutable result records and legacy diagnostics.
# owned_tests:
#   - apps/api/tests/test_today_convergence_tone.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-TONE

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Literal, NoReturn, Sequence, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.today_convergence_canon import TodayConvergenceCanon, load_today_convergence_canon
from app.services.today_convergence_groups import CanonicalConvergenceGroup, CanonicalGroupingResult
from app.services.today_convergence_ledger import CanonicalLedger
from app.services.today_convergence_units import CanonicalUnit


UnitPolarity = Literal["supportive", "tense", "mixed", "steady"]
GroupPolarity = Literal["supportive", "tense", "mixed", "steady"]
DayTone = Literal["supportive", "tense", "mixed", "steady"]


class TodayConvergenceToneError(ValueError):
    """Programming misuse or invariant violation at the pure tone boundary."""


@dataclass(frozen=True)
class CanonicalGroupTone:
    """Weighted polarity for one already-formed canonical group."""

    group_id: str
    polarity: GroupPolarity
    supportive_score: float
    tense_score: float
    independent_unit_count: int
    driver_keys: tuple[str, ...]
    unit_polarity_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class CanonicalToneScores:
    """Immutable day-tone counts and high-confidence anchor flags."""

    fresh_supportive_units: int
    fresh_tense_units: int
    high_confidence_supportive_anchor: bool
    high_confidence_tense_anchor: bool
    context_supportive_units: int
    context_tense_units: int


@dataclass(frozen=True)
class CanonicalToneAudit:
    """Immutable selected-only, context, group, and trigger diagnostics."""

    unit_polarity_counts: tuple[tuple[str, int], ...]
    context_polarity_counts: tuple[tuple[str, int], ...]
    group_polarity_counts: tuple[tuple[str, int], ...]
    tone_scores: CanonicalToneScores
    tone_trigger_keys: tuple[str, ...]
    selected_unit_ids: tuple[str, ...]
    context_unit_ids: tuple[str, ...]
    legacy_any_selected_tense: bool


@dataclass(frozen=True)
class CanonicalToneResult:
    """Immutable output of the three tone layers."""

    tone_policy_version: str
    day_tone: DayTone
    group_tones: tuple[CanonicalGroupTone, ...]
    audit: CanonicalToneAudit


@dataclass(frozen=True)
class _ToneUnit:
    unit: CanonicalUnit
    polarity: UnitPolarity
    weight: float


# START_BLOCK: INPUT_VALIDATION
def _fail(reason: str) -> NoReturn:
    raise TodayConvergenceToneError(f"today_convergence_tone:{reason}")


def _require_sequence(value: object, reason: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _fail(reason)
    return cast(Sequence[object], value)


def _validate_inputs(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
    target_date: date,
    timezone_name: str,
    selected_unit_ids: Sequence[str],
    canon: TodayConvergenceCanon,
) -> tuple[dict[str, CanonicalUnit], dict[str, CanonicalUnit], ZoneInfo]:
    if not isinstance(ledger, CanonicalLedger):
        _fail("ledger")
    if not isinstance(grouping, CanonicalGroupingResult):
        _fail("grouping")
    if type(target_date) is not date:
        _fail("target_date")
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        _fail("invalid_timezone")
    try:
        local_zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        _fail("invalid_timezone")
    if not isinstance(canon, TodayConvergenceCanon):
        _fail("canon")
    if not isinstance(ledger.units, tuple):
        _fail("ledger_units")
    units = ledger.units
    if any(not isinstance(unit, CanonicalUnit) for unit in units):
        _fail("ledger_unit_type")
    unit_by_id: dict[str, CanonicalUnit] = {}
    for unit in units:
        if not isinstance(unit.canonical_event_id, str) or not unit.canonical_event_id:
            _fail("ledger_unit_id")
        if unit.canonical_event_id in unit_by_id:
            _fail("duplicate_ledger_unit_id")
        unit_by_id[unit.canonical_event_id] = unit

    selected = _require_sequence(selected_unit_ids, "selected_unit_ids")
    selected_ids = list(selected)
    if any(not isinstance(unit_id, str) or not unit_id for unit_id in selected_ids):
        _fail("selected_unit_id")
    if len(selected_ids) != len(set(selected_ids)):
        _fail("duplicate_selected_unit_id")
    public_by_id = {
        unit_id: unit
        for unit_id, unit in unit_by_id.items()
        if unit.evidence_eligible and unit.exclusion_reason is None and unit.temporal_role != "background"
    }
    if any(unit_id not in public_by_id for unit_id in selected_ids):
        _fail("unknown_selected_unit")

    if not isinstance(grouping.groups, tuple):
        _fail("group_tuple")
    group_ids: set[str] = set()
    for group in grouping.groups:
        if not isinstance(group, CanonicalConvergenceGroup):
            _fail("group_type")
        if not isinstance(group.group_id, str) or not group.group_id:
            _fail("group_id")
        if group.group_id in group_ids:
            _fail("duplicate_group_id")
        group_ids.add(group.group_id)
        if not isinstance(group.member_units, tuple) or not group.member_units:
            _fail("group_members")
        member_ids: set[str] = set()
        for member in group.member_units:
            if not isinstance(member, CanonicalUnit):
                _fail("group_member_type")
            member_id = member.canonical_event_id
            if member_id in member_ids or unit_by_id.get(member_id) != member:
                _fail("foreign_group_member")
            member_ids.add(member_id)
            if member_id not in public_by_id:
                _fail("nonpublic_group_member")
    return unit_by_id, public_by_id, local_zone


# END_BLOCK: INPUT_VALIDATION


# START_BLOCK: UNIT_POLARITY
def _unit_polarity(unit: CanonicalUnit, canon: TodayConvergenceCanon) -> UnitPolarity:
    policy = canon.tone_policy
    polarity = unit.polarity.strip().lower() if isinstance(unit.polarity, str) else ""
    if polarity == "neutral":
        polarity = policy.neutral_maps_to
    if polarity not in policy.unit_polarities:
        _fail("invalid_polarity")
    return cast(UnitPolarity, polarity)


def _tone_weight(unit: CanonicalUnit, canon: TodayConvergenceCanon) -> float:
    strength = unit.strength
    if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not isfinite(float(strength)):
        _fail("invalid_strength")
    if not 0.0 <= float(strength) <= 1.0:
        _fail("invalid_strength")
    policy = canon.tone_policy
    if unit.temporal_role == "background":
        role_weight = policy.role_weights["background"]
    elif unit.temporal_role == "anchor_today":
        role_weight = policy.role_weights["anchor_today"]
    elif unit.temporal_role in {"supporting", "unrelated"}:
        role_weight = policy.role_weights["supporting_context"]
    else:
        _fail("invalid_temporal_role")
    weight = float(strength) * role_weight
    if not isfinite(weight) or weight < 0.0:
        _fail("invalid_weight")
    return weight


def _tone_units(units: Sequence[CanonicalUnit], canon: TodayConvergenceCanon) -> tuple[_ToneUnit, ...]:
    result: list[_ToneUnit] = []
    for unit in units:
        if not isinstance(unit.driver_key, str) or not unit.driver_key.strip():
            _fail("empty_driver")
        result.append(_ToneUnit(unit, _unit_polarity(unit, canon), _tone_weight(unit, canon)))
    return tuple(result)


def _counts(values: Sequence[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(values).items()))


# END_BLOCK: UNIT_POLARITY


# START_BLOCK: GROUP_TONE
def _deduplicate_drivers(rows: Sequence[_ToneUnit]) -> tuple[_ToneUnit, ...]:
    best: dict[str, _ToneUnit] = {}
    for row in rows:
        if row.unit.temporal_role == "background" or row.weight <= 0.0:
            continue
        key = row.unit.driver_key.strip()
        previous = best.get(key)
        if previous is None or row.weight > previous.weight or (
            row.weight == previous.weight
            and row.unit.canonical_event_id < previous.unit.canonical_event_id
        ):
            best[key] = row
    return tuple(sorted(best.values(), key=lambda row: row.unit.canonical_event_id))


def _group_tone(group: CanonicalConvergenceGroup, canon: TodayConvergenceCanon) -> CanonicalGroupTone:
    rows = _deduplicate_drivers(_tone_units(group.member_units, canon))
    supportive = 0.0
    tense = 0.0
    counts = Counter(row.polarity for row in rows)
    split = canon.tone_policy.role_weights["mixed_split"]
    for row in rows:
        if row.polarity == "supportive":
            supportive += row.weight
        elif row.polarity == "tense":
            tense += row.weight
        elif row.polarity == "mixed":
            supportive += row.weight * split
            tense += row.weight * split

    minimum = canon.tone_policy.min_side_weight
    margin = canon.tone_policy.mixed_margin
    if supportive < minimum and tense < minimum:
        polarity: GroupPolarity = "steady"
    elif supportive >= minimum and tense >= minimum:
        total = supportive + tense
        polarity = "mixed" if abs(supportive - tense) <= max(margin, total * margin) else (
            "supportive" if supportive > tense else "tense"
        )
    else:
        polarity = "supportive" if supportive > tense else "tense"
    return CanonicalGroupTone(
        group_id=group.group_id,
        polarity=polarity,
        supportive_score=round(supportive, 6),
        tense_score=round(tense, 6),
        independent_unit_count=len(rows),
        driver_keys=tuple(sorted(row.unit.driver_key for row in rows)),
        unit_polarity_counts=tuple(sorted(counts.items())),
    )


# END_BLOCK: GROUP_TONE


# START_BLOCK: DAY_TONE
def _is_fresh(unit: CanonicalUnit, target_date: date, local_zone: ZoneInfo) -> bool:
    exact_at = unit.exact_at
    if isinstance(exact_at, datetime):
        if exact_at.tzinfo is None or exact_at.utcoffset() is None:
            _fail("naive_exact_at")
        if unit.temporal_role == "anchor_today":
            return True
        return exact_at.astimezone(local_zone).date() == target_date
    if isinstance(exact_at, date):
        if unit.temporal_role == "anchor_today":
            return True
        return exact_at == target_date
    if exact_at is None:
        if unit.temporal_role == "anchor_today":
            return True
        return False
    _fail("invalid_exact_at")


def _hero_flags(
    groups: Sequence[CanonicalConvergenceGroup],
    unit_by_id: dict[str, CanonicalUnit],
    canon: TodayConvergenceCanon,
) -> tuple[bool, bool]:
    high_conf_tense = False
    high_conf_supportive = False
    threshold = canon.tone_policy.high_confidence_strength
    for group in groups:
        if not group.hero_eligible or group.hero_anchor_id is None:
            continue
        anchor = unit_by_id.get(group.hero_anchor_id)
        if anchor is None:
            _fail("hero_anchor_reference")
        polarity = _unit_polarity(anchor, canon)
        if anchor.strength < threshold:
            continue
        if polarity == "tense":
            high_conf_tense = True
        elif polarity == "supportive":
            high_conf_supportive = True
    return high_conf_supportive, high_conf_tense


def _day_tone(
    public_units: Sequence[CanonicalUnit],
    target_date: date,
    local_zone: ZoneInfo,
    groups: Sequence[CanonicalConvergenceGroup],
    unit_by_id: dict[str, CanonicalUnit],
    canon: TodayConvergenceCanon,
) -> tuple[DayTone, CanonicalToneScores, tuple[str, ...], tuple[str, ...], tuple[tuple[str, int], ...]]:
    policy = canon.tone_policy
    rows = _tone_units(public_units, canon)
    fresh = _deduplicate_drivers(
        tuple(row for row in rows if _is_fresh(row.unit, target_date, local_zone))
    )
    context = tuple(row for row in rows if not _is_fresh(row.unit, target_date, local_zone))
    context_ids = tuple(sorted(row.unit.canonical_event_id for row in context))
    context_polarities = _counts(tuple(row.polarity for row in context))
    day_units = tuple(row for row in fresh if row.unit.source_key not in policy.fast_sources_detail_only)
    supportive_units = tuple(row for row in day_units if row.polarity == "supportive")
    tense_units = tuple(row for row in day_units if row.polarity == "tense")
    mixed_units = tuple(row for row in day_units if row.polarity == "mixed")
    high_conf_supportive, high_conf_tense = _hero_flags(groups, unit_by_id, canon)
    supportive_count = len(supportive_units)
    tense_count = len(tense_units)
    if mixed_units and len(day_units) > 1:
        supportive_count += 1
        tense_count += 1
    meaningful_supportive = high_conf_supportive or supportive_count >= policy.min_independent_supportive_units
    meaningful_tense = high_conf_tense or tense_count >= policy.min_independent_tense_units
    supportive_weight = sum(row.weight for row in supportive_units)
    tense_weight = sum(row.weight for row in tense_units)
    fresh_pair_is_mixed = (
        policy.mixed_requires_fresh_support_and_tense
        and supportive_weight >= policy.min_side_weight
        and tense_weight >= policy.min_side_weight
    )
    if fresh_pair_is_mixed:
        day_tone: DayTone = "mixed"
    elif meaningful_tense:
        day_tone = "tense"
    elif meaningful_supportive:
        day_tone = "supportive"
    else:
        day_tone = "steady"
    tone_scores = CanonicalToneScores(
        fresh_supportive_units=supportive_count,
        fresh_tense_units=tense_count,
        high_confidence_supportive_anchor=high_conf_supportive,
        high_confidence_tense_anchor=high_conf_tense,
        context_supportive_units=dict(context_polarities).get("supportive", 0),
        context_tense_units=dict(context_polarities).get("tense", 0),
    )
    tone_trigger_keys = tuple(sorted(row.unit.semantic_key for row in day_units if row.unit.semantic_key))
    return day_tone, tone_scores, tone_trigger_keys, context_ids, context_polarities


# END_BLOCK: DAY_TONE


# START_BLOCK: AUDIT
def compute_canonical_tone(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
    target_date: date,
    timezone_name: str,
    selected_unit_ids: Sequence[str],
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalToneResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-TONE.compute_canonical_tone
    # purpose: Compute immutable unit/group/day tone layers from accepted convergence records.
    # inputs: ledger, grouping, target_date, IANA timezone_name, selected audit IDs, optional strict canon.
    # returns: CanonicalToneResult; selected IDs affect legacy audit only, never day_tone.
    # side_effects: reads frozen canon when omitted; no writes, network, database, or logs.
    # emitted_logs: none.
    # error_behavior: malformed records, invalid timezone, duplicate/unknown selected IDs, and foreign groups raise TodayConvergenceToneError.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-TONE.compute_canonical_tone
    resolved_canon = load_today_convergence_canon() if canon is None else canon
    unit_by_id, public_by_id, local_zone = _validate_inputs(
        ledger, grouping, target_date, timezone_name, selected_unit_ids, resolved_canon
    )
    selected_ids = tuple(sorted(selected_unit_ids))
    selected_rows = tuple(public_by_id[unit_id] for unit_id in selected_ids)
    selected_polarities = tuple(_unit_polarity(unit, resolved_canon) for unit in selected_rows)
    selected_counts = _counts(selected_polarities)
    group_tones = tuple(
        sorted(
            (_group_tone(group, resolved_canon) for group in grouping.groups),
            key=lambda tone: tone.group_id,
        )
    )
    day_tone, tone_scores, trigger_keys, context_ids, context_counts = _day_tone(
        tuple(public_by_id.values()),
        target_date,
        local_zone,
        grouping.groups,
        unit_by_id,
        resolved_canon,
    )
    group_counts = _counts(tuple(tone.polarity for tone in group_tones))
    audit = CanonicalToneAudit(
        unit_polarity_counts=selected_counts,
        context_polarity_counts=context_counts,
        group_polarity_counts=group_counts,
        tone_scores=tone_scores,
        tone_trigger_keys=trigger_keys,
        selected_unit_ids=selected_ids,
        context_unit_ids=context_ids,
        legacy_any_selected_tense="tense" in selected_polarities,
    )
    return CanonicalToneResult(
        tone_policy_version=resolved_canon.tone_policy.version,
        day_tone=day_tone,
        group_tones=group_tones,
        audit=audit,
    )


# END_BLOCK: AUDIT


__all__ = [
    "CanonicalGroupTone",
    "CanonicalToneScores",
    "CanonicalToneAudit",
    "CanonicalToneResult",
    "TodayConvergenceToneError",
    "compute_canonical_tone",
]
