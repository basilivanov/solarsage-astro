# ############################################################################
# AI_HEADER: TODAY_CONVERGENCE_SELECTION — deterministic presentation selector.
# ROLE: Projects canonical ledger, direct groups, and tone into immutable public selection records.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SELECTION
# purpose: Select the deterministic convergence, main-event, and impulse presentation from accepted canonical records.
# owns:
#   - apps/api/app/services/today_convergence_selection.py
# inputs: CanonicalLedger, CanonicalGroupingResult, CanonicalToneResult, target date/timezone, and optional validated canon.
# outputs: Immutable CanonicalSelectionResult with public-polarity blocks and deterministic audit.
# dependencies: today_convergence_canon, today_convergence_units, today_convergence_ledger, today_convergence_groups, today_convergence_tone, and Python standard library only.
# side_effects: reads frozen canon when omitted; no writes, network, database, or runtime logs.
# emitted_logs: none.
# invariants: only upstream-accepted units are selected; public polarity and
# physical content caps fail closed; output is permutation-deterministic.
# failure_policy: malformed records, invalid timezone/date, naive datetimes, foreign references, and invalid public mappings raise TodayConvergenceSelectionError.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SELECTION

# START_MODULE_MAP: M-TODAY-CONVERGENCE-SELECTION
# public_entrypoints:
#   - CanonicalSelectedConvergence
#   - CanonicalSelectedEvent
#   - CanonicalSelectionAudit
#   - CanonicalSelectionResult
#   - TodayConvergenceSelectionError
#   - select_canonical_presentation
# semantic_blocks:
#   - INPUT_VALIDATION: validate one immutable ledger/group/tone universe and IANA local-time boundary.
#   - GROUP_SELECTION: rank public hero/medium groups and preserve exact evidence pairs.
#   - QUIET_SELECTION: select one rare main event and up to three fresh impulses.
#   - SPHERE_PROJECTION: preserve first-appearance unique spheres without using them as a selection gate.
#   - AUDIT: materialize frozen sorted IDs and deterministic exclusion counters.
# owned_tests:
#   - apps/api/tests/test_today_convergence_selection.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-SELECTION

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from math import isfinite
from typing import Literal, NoReturn, Sequence, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.today_convergence_canon import (
    TodayConvergenceCanon,
    load_today_convergence_canon,
    resolve_product_sphere,
)
from app.services.today_convergence_groups import CanonicalConvergenceGroup, CanonicalGroupingResult
from app.services.today_convergence_ledger import CanonicalLedger
from app.services.today_convergence_tone import CanonicalToneResult
from app.services.today_convergence_units import CanonicalUnit


PublicPolarity = Literal["supportive", "tense", "mixed"]
EvidenceLevel = Literal["high", "medium"]
_PUBLIC_POLARITIES = frozenset({"supportive", "tense", "mixed"})
_INTERNAL_POLARITIES = frozenset({"supportive", "tense", "mixed", "steady"})


class TodayConvergenceSelectionError(ValueError):
    """Programming misuse or an invariant violation at the presentation boundary."""


@dataclass(frozen=True)
class CanonicalSelectedConvergence:
    """One selected physical group with its public polarity and evidence pair."""

    group: CanonicalConvergenceGroup
    polarity: PublicPolarity
    evidence_event_ids: tuple[str, str]


@dataclass(frozen=True)
class CanonicalSelectedEvent:
    """One selected main-event or impulse unit with one public sphere."""

    unit: CanonicalUnit
    sphere: str
    facet: str | None
    polarity: PublicPolarity
    evidence_level: EvidenceLevel


@dataclass(frozen=True)
class CanonicalSelectionAudit:
    """Immutable candidate, selected, steady, and physical-cap diagnostics."""

    candidate_convergence_count: int
    selected_convergence_count: int
    candidate_event_count: int
    selected_event_count: int
    steady_exclusion_count: int
    selection_cap_exclusion_count: int


@dataclass(frozen=True)
class CanonicalSelectionResult:
    """Immutable public presentation selection."""

    state: Literal["convergence_today", "quiet_day"]
    convergences: tuple[CanonicalSelectedConvergence, ...]
    main_event: CanonicalSelectedEvent | None
    impulses: tuple[CanonicalSelectedEvent, ...]
    selected_unit_ids: tuple[str, ...]
    selected_spheres: tuple[str, ...]
    audit: CanonicalSelectionAudit


@dataclass(frozen=True)
class _ValidatedInputs:
    unit_by_id: dict[str, CanonicalUnit]
    local_zone: ZoneInfo
    tone_by_group_id: dict[str, str]


def _fail(reason: str) -> NoReturn:
    raise TodayConvergenceSelectionError(f"today_convergence_selection:{reason}")


def _require_sequence(value: object, reason: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _fail(reason)
    return cast(Sequence[object], value)


def _finite_unit_strength(unit: CanonicalUnit) -> float:
    strength = unit.strength
    if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not isfinite(float(strength)):
        _fail("invalid_strength")
    normalized = float(strength)
    if not 0.0 <= normalized <= 1.0:
        _fail("invalid_strength")
    return normalized


def _validate_datetime(value: object, reason: str) -> None:
    if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
        _fail(reason)
    if value is not None and not isinstance(value, (date, datetime)):
        _fail("invalid_event_window")


def _validate_group_sphere(value: object, canonical_spheres: frozenset[str], reason: str) -> str:
    if not isinstance(value, str) or not value or value not in canonical_spheres:
        _fail(reason)
    return value


# START_BLOCK: INPUT_VALIDATION
def _validate_inputs(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
    tone: CanonicalToneResult,
    target_date: date,
    timezone_name: str,
    canon: TodayConvergenceCanon,
) -> _ValidatedInputs:
    if not isinstance(ledger, CanonicalLedger):
        _fail("ledger")
    if not isinstance(grouping, CanonicalGroupingResult):
        _fail("grouping")
    if not isinstance(tone, CanonicalToneResult):
        _fail("tone")
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

    unit_by_id: dict[str, CanonicalUnit] = {}
    for unit in ledger.units:
        if not isinstance(unit, CanonicalUnit):
            _fail("ledger_unit_type")
        unit_id = unit.canonical_event_id
        if not isinstance(unit_id, str) or not unit_id:
            _fail("ledger_unit_id")
        if unit_id in unit_by_id:
            _fail("duplicate_ledger_unit_id")
        unit_by_id[unit_id] = unit
        _finite_unit_strength(unit)
        _validate_datetime(unit.exact_at, "naive_exact_at")
        _validate_datetime(unit.active_from, "naive_event_window")
        _validate_datetime(unit.active_until, "naive_event_window")

    if not isinstance(grouping.groups, tuple):
        _fail("group_tuple")
    group_by_id: dict[str, CanonicalConvergenceGroup] = {}
    canonical_spheres = frozenset(canon.canonical_spheres)
    for group in grouping.groups:
        if not isinstance(group, CanonicalConvergenceGroup):
            _fail("group_type")
        if not isinstance(group.group_id, str) or not group.group_id:
            _fail("group_id")
        if group.group_id in group_by_id:
            _fail("duplicate_group_id")
        group_by_id[group.group_id] = group
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
        if group.anchor_unit_id not in member_ids:
            _fail("group_anchor_reference")
        if (group.hero_anchor_id is None) != (group.hero_confirmation_id is None):
            _fail("hero_pair_reference")
        if group.hero_anchor_id is not None:
            if group.hero_anchor_id not in member_ids or group.hero_confirmation_id not in member_ids:
                _fail("hero_pair_reference")
            if group.hero_anchor_id == group.hero_confirmation_id:
                _fail("hero_pair_reference")
        if group.evidence_level not in {"high", "medium"}:
            _fail("invalid_evidence_level")
        _validate_group_sphere(group.sphere, canonical_spheres, "unmapped_group_sphere")
        if group.facet is not None:
            if not isinstance(group.facet, str) or not group.facet.strip():
                _fail("unmapped_group_facet")
            product_sphere = canon.product_spheres.get(group.sphere)
            if product_sphere is None or group.facet not in {facet.key for facet in product_sphere.facets}:
                _fail("unmapped_group_facet")

    if not isinstance(tone.group_tones, tuple):
        _fail("tone_group_tuple")
    tone_by_group_id: dict[str, str] = {}
    for group_tone in tone.group_tones:
        group_id = group_tone.group_id
        if not isinstance(group_id, str) or group_id not in group_by_id:
            _fail("tone_group_reference")
        if group_id in tone_by_group_id:
            _fail("duplicate_tone_group_id")
        if group_tone.polarity not in _INTERNAL_POLARITIES:
            _fail("invalid_group_polarity")
        for score in (group_tone.supportive_score, group_tone.tense_score):
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not isfinite(float(score)):
                _fail("invalid_group_score")
        tone_by_group_id[group_id] = group_tone.polarity
    if set(tone_by_group_id) != set(group_by_id):
        _fail("tone_group_ids")
    return _ValidatedInputs(unit_by_id=unit_by_id, local_zone=local_zone, tone_by_group_id=tone_by_group_id)


# END_BLOCK: INPUT_VALIDATION


# START_BLOCK: RANKING
def _local_rank_time(unit: CanonicalUnit, local_zone: ZoneInfo) -> tuple[int, datetime]:
    exact_at = unit.exact_at
    if isinstance(exact_at, datetime):
        return 0, exact_at.astimezone(local_zone).replace(tzinfo=None)
    if type(exact_at) is date:
        return 1, datetime.combine(exact_at, time.min)
    if exact_at is None:
        return 2, datetime.max
    _fail("invalid_exact_at")


def _unit_rank(unit: CanonicalUnit, local_zone: ZoneInfo) -> tuple[float, int, datetime, str]:
    return (-_finite_unit_strength(unit), *_local_rank_time(unit, local_zone), unit.canonical_event_id)


def _is_fresh(unit: CanonicalUnit, target_date: date, local_zone: ZoneInfo) -> bool:
    if unit.temporal_role == "anchor_today":
        return True
    exact_at = unit.exact_at
    if isinstance(exact_at, datetime):
        return exact_at.astimezone(local_zone).date() == target_date
    if type(exact_at) is date:
        return exact_at == target_date
    if exact_at is None:
        return False
    _fail("invalid_exact_at")


def _public_polarity(unit: CanonicalUnit, canon: TodayConvergenceCanon) -> PublicPolarity | None:
    if not isinstance(unit.polarity, str):
        _fail("invalid_polarity")
    polarity = unit.polarity.strip().lower()
    if polarity == "neutral":
        polarity = canon.tone_policy.neutral_maps_to
    if polarity not in _INTERNAL_POLARITIES:
        _fail("invalid_polarity")
    if polarity not in _PUBLIC_POLARITIES:
        return None
    return cast(PublicPolarity, polarity)


def _presentation_sphere_facet(
    unit: CanonicalUnit,
    canon: TodayConvergenceCanon,
) -> tuple[str, str | None]:
    resolved = resolve_product_sphere(
        canon,
        house=unit.house,
        technical_spheres=unit.technical_spheres,
        theme_keys=unit.theme_keys,
        source_key=unit.source_key,
        target_key=unit.target_key,
    )
    if resolved is None:
        _fail("unmapped_presentation_sphere")
    return resolved


def _group_rank(
    group: CanonicalConvergenceGroup,
    unit_by_id: dict[str, CanonicalUnit],
    canon: TodayConvergenceCanon,
    local_zone: ZoneInfo,
) -> tuple[int, int, float, int, str]:
    anchor = unit_by_id.get(group.anchor_unit_id)
    if anchor is None:
        _fail("group_anchor_reference")
    sphere_order = {sphere: index for index, sphere in enumerate(canon.canonical_spheres)}
    evidence_rank = 0 if group.evidence_level == "high" else 1
    return (
        -len(group.independent_driver_keys),
        evidence_rank,
        -_finite_unit_strength(anchor),
        sphere_order[group.sphere],
        group.group_id,
    )


# END_BLOCK: RANKING


# START_BLOCK: GROUP_SELECTION
def _evidence_pair(
    group: CanonicalConvergenceGroup,
    unit_by_id: dict[str, CanonicalUnit],
    canon: TodayConvergenceCanon,
    local_zone: ZoneInfo,
) -> tuple[str, str] | None:
    if group.hero_eligible:
        if group.hero_anchor_id is None or group.hero_confirmation_id is None:
            _fail("hero_pair_reference")
        pair = (group.hero_anchor_id, group.hero_confirmation_id)
    else:
        anchor = unit_by_id.get(group.anchor_unit_id)
        if anchor is None:
            _fail("group_anchor_reference")
        candidates = [
            member
            for member in group.member_units
            if member.canonical_event_id != anchor.canonical_event_id
            and member.driver_key != anchor.driver_key
            and _public_polarity(member, canon) is not None
        ]
        if not candidates:
            return None
        confirmation = min(candidates, key=lambda unit: _unit_rank(unit, local_zone))
        pair = (anchor.canonical_event_id, confirmation.canonical_event_id)
    if any(_public_polarity(unit_by_id[event_id], canon) is None for event_id in pair):
        return None
    return pair


def _selected_convergences(
    grouping: CanonicalGroupingResult,
    inputs: _ValidatedInputs,
    canon: TodayConvergenceCanon,
) -> tuple[tuple[CanonicalSelectedConvergence, ...], int, int, int]:
    public_groups: list[tuple[CanonicalConvergenceGroup, PublicPolarity, tuple[str, str]]] = []
    steady_exclusions = 0
    for group in grouping.groups:
        group_polarity = inputs.tone_by_group_id[group.group_id]
        if group_polarity not in _PUBLIC_POLARITIES:
            steady_exclusions += 1
            continue
        polarity = cast(PublicPolarity, group_polarity)
        pair = _evidence_pair(group, inputs.unit_by_id, canon, inputs.local_zone)
        if pair is not None:
            public_groups.append((group, polarity, pair))

    heroes = [candidate for candidate in public_groups if candidate[0].hero_eligible]
    if any(group.hero_eligible for group in grouping.groups) and not heroes:
        _fail("hero_without_public_polarity")
    ordered = sorted(
        heroes,
        key=lambda candidate: _group_rank(candidate[0], inputs.unit_by_id, canon, inputs.local_zone),
    ) + sorted(
        (candidate for candidate in public_groups if not candidate[0].hero_eligible),
        key=lambda candidate: _group_rank(candidate[0], inputs.unit_by_id, canon, inputs.local_zone),
    )

    selected: list[CanonicalSelectedConvergence] = []
    selected_spheres: list[str] = []
    selected_sphere_set: set[str] = set()
    selection_cap_exclusions = 0
    for group, polarity, pair in ordered:
        if len(selected) >= 3:
            selection_cap_exclusions += 1
            continue
        selected.append(
            CanonicalSelectedConvergence(group=group, polarity=polarity, evidence_event_ids=pair)
        )
        if group.sphere not in selected_sphere_set:
            selected_spheres.append(group.sphere)
            selected_sphere_set.add(group.sphere)
    return tuple(selected), steady_exclusions, selection_cap_exclusions, len(selected_spheres)


# END_BLOCK: GROUP_SELECTION


# START_BLOCK: QUIET_SELECTION
def _candidate_units(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
) -> tuple[CanonicalUnit, ...]:
    if grouping.groups:
        members = {member.canonical_event_id: member for group in grouping.groups for member in group.member_units}
        return tuple(sorted(members.values(), key=lambda unit: unit.canonical_event_id))
    return tuple(sorted(ledger.units, key=lambda unit: unit.canonical_event_id))


def _selected_event(
    unit: CanonicalUnit,
    canon: TodayConvergenceCanon,
) -> CanonicalSelectedEvent:
    polarity = _public_polarity(unit, canon)
    if polarity is None:
        _fail("steady_event_polarity")
    sphere, facet = _presentation_sphere_facet(unit, canon)
    return CanonicalSelectedEvent(
        unit=unit,
        sphere=sphere,
        facet=facet,
        polarity=polarity,
        evidence_level="medium",
    )


def _quiet_selection(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
    inputs: _ValidatedInputs,
    canon: TodayConvergenceCanon,
    target_date: date,
) -> tuple[CanonicalSelectedEvent | None, tuple[CanonicalSelectedEvent, ...], tuple[str, ...], int, int]:
    candidates = _candidate_units(ledger, grouping)
    steady_exclusions = 0
    rare_candidates: list[CanonicalUnit] = []
    for unit in candidates:
        if (
            unit.temporal_role != "anchor_today"
            or not unit.rare_anchor_eligible
            or not _is_fresh(unit, target_date, inputs.local_zone)
        ):
            continue
        polarity = _public_polarity(unit, canon)
        if polarity is None:
            steady_exclusions += 1
            continue
        rare_candidates.append(unit)
    main = _selected_event(min(rare_candidates, key=lambda unit: _unit_rank(unit, inputs.local_zone)), canon) if rare_candidates else None

    impulse_by_semantic: dict[str, CanonicalUnit] = {}
    for unit in candidates:
        if not unit.impulse_eligible or unit.temporal_role == "background":
            continue
        if main is not None and unit.canonical_event_id == main.unit.canonical_event_id:
            continue
        if not _is_fresh(unit, target_date, inputs.local_zone):
            continue
        polarity = _public_polarity(unit, canon)
        if polarity is None:
            steady_exclusions += 1
            continue
        if not isinstance(unit.semantic_key, str) or not unit.semantic_key:
            _fail("invalid_semantic_key")
        previous = impulse_by_semantic.get(unit.semantic_key)
        if previous is None or _unit_rank(unit, inputs.local_zone) < _unit_rank(previous, inputs.local_zone):
            impulse_by_semantic[unit.semantic_key] = unit

    ordered_impulses = sorted(impulse_by_semantic.values(), key=lambda unit: _unit_rank(unit, inputs.local_zone))
    selected_events: list[CanonicalSelectedEvent] = []
    selected_spheres: list[str] = []
    if main is not None:
        selected_events.append(main)
        selected_spheres.append(main.sphere)
    selection_cap_exclusions = 0
    max_event_count = 3 + (1 if main is not None else 0)
    for unit in ordered_impulses:
        if len(selected_events) >= max_event_count:
            selection_cap_exclusions += 1
            continue
        event = _selected_event(unit, canon)
        selected_events.append(event)
        if event.sphere not in selected_spheres:
            selected_spheres.append(event.sphere)
    impulse_start = 1 if main is not None else 0
    impulses = tuple(selected_events[impulse_start:])
    return main, impulses, tuple(selected_spheres), steady_exclusions, selection_cap_exclusions


# END_BLOCK: QUIET_SELECTION


# START_BLOCK: SELECTION_BUILD
def select_canonical_presentation(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
    tone: CanonicalToneResult,
    target_date: date,
    timezone_name: str,
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalSelectionResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SELECTION.select_canonical_presentation
    # purpose: Select public convergence groups or quiet-day main/impulse blocks from one canonical universe.
    # inputs: ledger, grouping, tone, target_date, IANA timezone_name, and optional strict canon.
    # returns: frozen CanonicalSelectionResult; selector never creates unavailable state or wire payload.
    # side_effects: reads frozen canon when omitted; no writes, network, database, or logs.
    # emitted_logs: none.
    # error_behavior: malformed references, invalid local time, unmapped public polarity/sphere, and invariant misuse raise TodayConvergenceSelectionError.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SELECTION.select_canonical_presentation
    resolved_canon = load_today_convergence_canon() if canon is None else canon
    inputs = _validate_inputs(ledger, grouping, tone, target_date, timezone_name, resolved_canon)
    selected_convergences, group_steady_exclusions, group_sphere_exclusions, _ = _selected_convergences(
        grouping, inputs, resolved_canon
    )
    if selected_convergences and any(group.group.hero_eligible for group in selected_convergences):
        selected_ids = tuple(
            sorted(
                {
                    event_id
                    for selected in selected_convergences
                    for event_id in selected.evidence_event_ids
                }
            )
        )
        selected_sphere_values: list[str] = []
        for selected in selected_convergences:
            if selected.group.sphere not in selected_sphere_values:
                selected_sphere_values.append(selected.group.sphere)
        selected_spheres = tuple(selected_sphere_values)
        return CanonicalSelectionResult(
            state="convergence_today",
            convergences=selected_convergences,
            main_event=None,
            impulses=(),
            selected_unit_ids=selected_ids,
            selected_spheres=selected_spheres,
            audit=CanonicalSelectionAudit(
                candidate_convergence_count=len(grouping.groups),
                selected_convergence_count=len(selected_convergences),
                candidate_event_count=len(
                    {
                        member.canonical_event_id
                        for group in grouping.groups
                        for member in group.member_units
                    }
                ),
                selected_event_count=len(selected_ids),
                steady_exclusion_count=group_steady_exclusions,
                selection_cap_exclusion_count=group_sphere_exclusions,
            ),
        )

    main, impulses, selected_spheres, event_steady_exclusions, event_sphere_exclusions = _quiet_selection(
        ledger, grouping, inputs, resolved_canon, target_date
    )
    selected_id_values = {event.unit.canonical_event_id for event in impulses}
    if main is not None:
        selected_id_values.add(main.unit.canonical_event_id)
    selected_ids = tuple(sorted(selected_id_values))
    return CanonicalSelectionResult(
        state="quiet_day",
        convergences=(),
        main_event=main,
        impulses=impulses,
        selected_unit_ids=selected_ids,
        selected_spheres=selected_spheres,
        audit=CanonicalSelectionAudit(
            candidate_convergence_count=len(grouping.groups),
            selected_convergence_count=0,
            candidate_event_count=len(_candidate_units(ledger, grouping)),
            selected_event_count=len(selected_ids),
            steady_exclusion_count=group_steady_exclusions + event_steady_exclusions,
            selection_cap_exclusion_count=group_sphere_exclusions + event_sphere_exclusions,
        ),
    )


# END_BLOCK: SELECTION_BUILD


__all__ = [
    "CanonicalSelectedConvergence",
    "CanonicalSelectedEvent",
    "CanonicalSelectionAudit",
    "CanonicalSelectionResult",
    "TodayConvergenceSelectionError",
    "select_canonical_presentation",
]
