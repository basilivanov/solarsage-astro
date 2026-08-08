# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_SELECTION — deterministic presentation selection tests.
# ROLE: Proves the pure selector projects canonical ledger/group/tone records into public blocks.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SELECTION
# purpose: Validate deterministic hero, main-event, impulse, physical-cap, and fail-closed selection.
# owns:
#   - apps/api/tests/test_today_convergence_selection.py
# inputs: Immutable canonical ledger, grouping, tone, and frozen canon records.
# outputs: pytest assertions for the P2-C2 presentation boundary.
# dependencies: today_convergence_canon, today_convergence_units, today_convergence_ledger, today_convergence_groups, today_convergence_tone, today_convergence_selection.
# side_effects: none.
# emitted_logs: none.
# invariants: selected records are frozen, public, deterministic, and never widen upstream eligibility.
# failure_policy: typed selector errors fail tests; no fallback presentation is accepted.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SELECTION

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SELECTION
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - CONVERGENCE: hero/medium group ranking and evidence pairs.
#   - QUIET: rare main event and impulse ranking.
#   - SPHERES: resolver-backed sphere/facet projection and first-appearance order.
#   - VALIDATION: timezone, references, polarity, and immutable-record failures.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SELECTION

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone
from itertools import permutations

import pytest

from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_groups import build_canonical_groups
from app.services.today_convergence_ledger import CanonicalLedger, build_canonical_ledger
from app.services.today_convergence_selection import (
    CanonicalSelectionResult,
    TodayConvergenceSelectionError,
    select_canonical_presentation,
)
from app.services.today_convergence_tone import compute_canonical_tone
from app.services.today_convergence_units import RawPhysicalFact, build_canonical_unit


CANON = load_today_convergence_canon()
TARGET_DATE = date(2026, 7, 31)
UTC_NOON = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


def fact(**overrides) -> RawPhysicalFact:
    values = {
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "source_key": "Transit_Jupiter",
        "target_key": "Natal_SATURN",
        "target_type": "natal_planet",
        "target_salience": 0.8,
        "aspect_type": "SEXTILE",
        "orb": 1.0,
        "event_class": None,
        "house": None,
        "exact_at": UTC_NOON,
        "phase": "exact",
        "active_from": None,
        "active_until": None,
        "data_quality": "high",
        "birth_time_mode": "exact",
        "birth_time_robustness": "robust",
        "technical_spheres": ("work_status_achievement",),
        "polarity": "supportive",
        "strength": 0.8,
        "temporal_role": "anchor_today",
        "producer": "activation",
        "provenance_ids": ("row",),
    }
    values.update(overrides)
    return RawPhysicalFact(**values)


def pipeline(*rows: RawPhysicalFact) -> tuple[CanonicalLedger, object, object]:
    ledger = build_canonical_ledger(list(rows), CANON)
    grouping = build_canonical_groups(ledger, CANON)
    selected = tuple(
        unit.canonical_event_id
        for unit in ledger.units
        if unit.evidence_eligible and unit.exclusion_reason is None and unit.temporal_role != "background"
    )
    tone = compute_canonical_tone(ledger, grouping, TARGET_DATE, "UTC", selected, CANON)
    return ledger, grouping, tone


def select(*rows: RawPhysicalFact, timezone_name: str = "UTC") -> CanonicalSelectionResult:
    ledger, grouping, tone = pipeline(*rows)
    return select_canonical_presentation(ledger, grouping, tone, TARGET_DATE, timezone_name, CANON)


def unit_for(raw: RawPhysicalFact):
    result = build_canonical_unit(raw, CANON)
    assert result.unit is not None
    return result.unit


# START_BLOCK: CONVERGENCE
def test_hero_evidence_selection_excludes_non_evidence_group_members() -> None:
    hero_anchor = fact(source_key="Transit_JUPITER", target_key="Natal_SATURN")
    hero_confirmation = fact(
        source_key="Transit_SATURN",
        target_key="Natal_SATURN",
        aspect_type="TRINE",
        temporal_role="supporting",
    )
    hero_extra = fact(
        source_key="Transit_JUPITER",
        target_key="Natal_SATURN",
        aspect_type="TRINE",
        temporal_role="supporting",
        exact_at=datetime(2026, 7, 31, 13, 0, tzinfo=timezone.utc),
    )
    ledger, _, _ = pipeline(hero_anchor, hero_confirmation, hero_extra)
    grouping = build_canonical_groups(ledger, CANON)
    selected = tuple(unit.canonical_event_id for unit in ledger.units)
    tone = compute_canonical_tone(ledger, grouping, TARGET_DATE, "UTC", selected, CANON)
    result = select_canonical_presentation(ledger, grouping, tone, TARGET_DATE, "UTC", CANON)

    assert result.state == "convergence_today"
    assert len(result.convergences) == 1
    assert result.convergences[0].group.hero_eligible is True
    assert len(result.convergences[0].group.member_units) > 2
    assert result.convergences[0].evidence_event_ids == (
        unit_for(hero_anchor).canonical_event_id,
        unit_for(hero_confirmation).canonical_event_id,
    )
    expected_evidence_ids = tuple(
        sorted(event_id for convergence in result.convergences for event_id in convergence.evidence_event_ids)
    )
    assert result.selected_unit_ids == expected_evidence_ids
    assert result.audit.selected_event_count == len(expected_evidence_ids) == 2
    assert result.audit.unmapped_sphere_exclusion_count == 0
    assert unit_for(hero_extra).canonical_event_id not in result.selected_unit_ids
    assert result.selected_spheres == ("work",)
    assert result.main_event is None
    assert result.impulses == ()


def test_convergence_caps_groups_without_diversity_gate() -> None:
    rows = [
        fact(source_key="Transit_JUPITER", target_key="Natal_SATURN", technical_spheres=("work_status_achievement",)),
        fact(source_key="Transit_SATURN", target_key="Natal_SATURN", aspect_type="TRINE", temporal_role="supporting", technical_spheres=("work_status_achievement",)),
        fact(source_key="Transit_MOON", target_key="Natal_MOON", technical_spheres=("money_security_resources",)),
        fact(source_key="Transit_MERCURY", target_key="Natal_MOON", aspect_type="TRINE", temporal_role="supporting", technical_spheres=("money_security_resources",)),
        fact(source_key="Transit_VENUS", target_key="Natal_VENUS", technical_spheres=("relationships_partnership",)),
        fact(source_key="Transit_MARS", target_key="Natal_VENUS", aspect_type="TRINE", temporal_role="supporting", technical_spheres=("relationships_partnership",)),
        fact(source_key="Transit_URANUS", target_key="Natal_URANUS", technical_spheres=("thinking_speech_learning",)),
        fact(source_key="Transit_NEPTUNE", target_key="Natal_URANUS", aspect_type="TRINE", temporal_role="supporting", technical_spheres=("thinking_speech_learning",)),
    ]

    ledger, grouping, tone = pipeline(*rows)
    result = select_canonical_presentation(ledger, grouping, tone, TARGET_DATE, "UTC", CANON)
    candidate_event_ids = {
        member.canonical_event_id
        for group in grouping.groups
        for member in group.member_units
    }
    candidate_occurrences = sum(len(group.member_units) for group in grouping.groups)

    assert result.state == "convergence_today"
    assert 1 <= len(result.convergences) <= 3
    assert result.selected_spheres == tuple(
        dict.fromkeys(selected.group.sphere for selected in result.convergences)
    )
    assert len({item.group.group_id for item in result.convergences}) == len(result.convergences)
    assert sum(item.group.sphere == "work" for item in result.convergences) == 2
    assert candidate_occurrences > len(candidate_event_ids)
    assert result.audit.candidate_event_count == len(candidate_event_ids)
    assert result.audit.selection_cap_exclusion_count == 0


# END_BLOCK: CONVERGENCE


# START_BLOCK: QUIET
def test_medium_only_groups_remain_quiet_day() -> None:
    result = select(
        fact(source_key="Transit_MOON", target_key="Natal_SATURN"),
        fact(source_key="Transit_MERCURY", target_key="Natal_SATURN", aspect_type="TRINE", temporal_role="supporting"),
    )

    assert result.state == "quiet_day"
    assert result.convergences == ()


def test_single_rare_anchor_is_quiet_main_event_not_convergence() -> None:
    rare = fact(source_key="Transit_JUPITER", target_key="Natal_SATURN")

    result = select(rare)

    assert result.state == "quiet_day"
    assert result.main_event is not None
    assert result.main_event.unit.canonical_event_id == unit_for(rare).canonical_event_id
    assert result.main_event.evidence_level == "medium"
    assert result.main_event.polarity == "supportive"
    assert result.impulses == ()


def test_main_event_and_three_impulses_are_unique_without_sphere_cap() -> None:
    main = fact(source_key="Transit_JUPITER", target_key="Natal_SATURN", strength=0.95)
    moon = fact(source_key="Transit_MOON", target_key="Natal_MOON", technical_spheres=("money_security_resources",), strength=0.9)
    mercury = fact(source_key="Transit_MERCURY", target_key="Natal_MERCURY", technical_spheres=("relationships_partnership",), strength=0.8)
    venus = fact(source_key="Transit_VENUS", target_key="Natal_VENUS", technical_spheres=("thinking_speech_learning",), strength=0.7)
    fourth = fact(source_key="Transit_MOON", target_key="Natal_MARS", technical_spheres=("work_status_achievement",), strength=0.75)

    ledger, _, _ = pipeline(main, moon, mercury, venus, fourth)
    grouping = build_canonical_groups(ledger, CANON)
    selected = tuple(unit.canonical_event_id for unit in ledger.units)
    tone = compute_canonical_tone(ledger, grouping, TARGET_DATE, "UTC", selected, CANON)
    result = select_canonical_presentation(ledger, grouping, tone, TARGET_DATE, "UTC", CANON)

    assert result.state == "quiet_day"
    assert result.main_event is not None
    assert len(result.impulses) == 3
    selected_ids = result.selected_unit_ids
    assert len(selected_ids) == len(set(selected_ids)) == 4
    expected_impulse_ids = tuple(unit_for(row).canonical_event_id for row in (moon, mercury, fourth))
    assert tuple(event.unit.canonical_event_id for event in result.impulses) == expected_impulse_ids
    assert unit_for(venus).canonical_event_id not in result.selected_unit_ids
    assert len(result.selected_spheres) == 3
    assert result.selected_spheres[0] == result.main_event.sphere
    assert result.audit.selection_cap_exclusion_count >= 1


def test_impulses_rank_strength_then_local_time_then_event_id_and_permute_stably() -> None:
    early = fact(source_key="Transit_MOON", target_key="Natal_MOON", strength=0.8, exact_at=datetime(2026, 7, 30, 23, 30, tzinfo=timezone.utc))
    late = fact(source_key="Transit_MERCURY", target_key="Natal_MERCURY", strength=0.8, exact_at=datetime(2026, 7, 31, 0, 30, tzinfo=timezone.utc), technical_spheres=("money_security_resources",))
    weaker = fact(source_key="Transit_VENUS", target_key="Natal_VENUS", strength=0.7, technical_spheres=("relationships_partnership",))
    ledger, grouping, tone = pipeline(early, late, weaker)
    outputs = [
        select_canonical_presentation(
            replace(ledger, units=order),
            grouping,
            tone,
            TARGET_DATE,
            "Europe/Moscow",
            CANON,
        )
        for order in permutations(ledger.units)
    ]

    assert all(output == outputs[0] for output in outputs)
    assert tuple(event.unit.canonical_event_id for event in outputs[0].impulses) == tuple(
        event.unit.canonical_event_id for event in sorted(outputs[0].impulses, key=lambda event: (-event.unit.strength, event.unit.exact_at))
    )
    assert outputs[0].selected_spheres[0] == "work"


def test_equal_strength_and_local_time_use_canonical_event_id_ascending() -> None:
    left = fact(source_key="Transit_MOON", target_key="Natal_MOON", strength=0.8, exact_at=UTC_NOON)
    right = fact(source_key="Transit_MERCURY", target_key="Natal_MERCURY", strength=0.8, exact_at=UTC_NOON)

    result = select(left, right)
    selected_ids = tuple(event.unit.canonical_event_id for event in result.impulses)

    assert selected_ids == tuple(sorted(selected_ids))


def test_long_running_supporting_unit_is_not_a_today_impulse() -> None:
    ongoing = fact(
        source_key="Transit_JUPITER",
        temporal_role="supporting",
        exact_at=date(2026, 7, 1),
    )

    result = select(ongoing)

    assert result.state == "quiet_day"
    assert result.main_event is None
    assert result.impulses == ()


def test_unmapped_top_impulse_is_skipped_and_next_resolvable_impulse_is_selected() -> None:
    unmapped = fact(
        source_key="Transit_URANUS",
        target_key="Natal_URANUS",
        technical_spheres=("unknown_factor",),
        strength=0.95,
    )
    resolved = fact(
        source_key="Transit_MERCURY",
        target_key="Natal_MERCURY",
        technical_spheres=("money_security_resources",),
        strength=0.8,
    )

    result = select(unmapped, resolved)

    assert result.state == "quiet_day"
    assert result.main_event is None
    assert tuple(event.unit.canonical_event_id for event in result.impulses) == (
        unit_for(resolved).canonical_event_id,
    )
    # Slow-source unmapped unit is counted in both rare-main and impulse loops.
    assert result.audit.unmapped_sphere_exclusion_count == 2


def test_unmapped_rare_main_is_skipped_before_ranking() -> None:
    unmapped = fact(
        source_key="Transit_URANUS",
        target_key="Natal_URANUS",
        aspect_type="SQUARE",
        technical_spheres=("unknown_factor",),
        strength=0.95,
    )
    resolved = fact(
        source_key="Transit_JUPITER",
        target_key="Natal_SATURN",
        strength=0.8,
    )
    ledger, grouping, tone = pipeline(unmapped, resolved)
    unmapped_id = unit_for(unmapped).canonical_event_id
    ledger = replace(
        ledger,
        units=tuple(
            replace(unit, impulse_eligible=False) if unit.canonical_event_id == unmapped_id else unit
            for unit in ledger.units
        ),
    )

    result = select_canonical_presentation(ledger, grouping, tone, TARGET_DATE, "UTC", CANON)

    assert result.state == "quiet_day"
    assert result.main_event is not None
    assert result.main_event.unit.canonical_event_id == unit_for(resolved).canonical_event_id
    assert result.audit.unmapped_sphere_exclusion_count == 1


def test_all_unmapped_quiet_candidates_produce_empty_quiet_day() -> None:
    result = select(
        fact(
            source_key="Transit_URANUS",
            target_key="Natal_URANUS",
            technical_spheres=("unknown_factor",),
        )
    )

    assert result.state == "quiet_day"
    assert result.main_event is None
    assert result.impulses == ()
    # Counted once in the rare-main loop and once in the impulse loop.
    assert result.audit.unmapped_sphere_exclusion_count == 2


# END_BLOCK: QUIET


# START_BLOCK: VALIDATION
def test_steady_only_hero_fails_closed_instead_of_mapping_to_public_polarity() -> None:
    with pytest.raises(TodayConvergenceSelectionError, match="hero_without_public_polarity"):
        select(
            fact(source_key="Transit_JUPITER", polarity="neutral"),
            fact(source_key="Transit_SATURN", polarity="neutral", aspect_type="TRINE", temporal_role="supporting"),
        )


def test_foreign_and_missing_group_references_are_typed_errors() -> None:
    ledger, grouping, tone = pipeline(
        fact(source_key="Transit_JUPITER"),
        fact(source_key="Transit_SATURN", aspect_type="TRINE", temporal_role="supporting"),
    )
    group = grouping.groups[0]
    foreign = unit_for(fact(source_key="Transit_MOON", target_key="Natal_MOON"))
    foreign_grouping = replace(
        grouping,
        groups=(replace(group, member_units=group.member_units + (foreign,)),),
    )
    with pytest.raises(TodayConvergenceSelectionError, match="foreign_group_member"):
        select_canonical_presentation(ledger, foreign_grouping, tone, TARGET_DATE, "UTC", CANON)

    missing_grouping = replace(grouping, groups=(replace(group, anchor_unit_id="missing"),))
    with pytest.raises(TodayConvergenceSelectionError, match="group_anchor_reference"):
        select_canonical_presentation(ledger, missing_grouping, tone, TARGET_DATE, "UTC", CANON)


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda ledger, grouping, tone: (ledger, grouping, replace(tone, group_tones=())), "tone_group_ids"),
        (lambda ledger, grouping, tone: (replace(ledger, units=(ledger.units[0], ledger.units[0])), grouping, tone), "duplicate_ledger_unit_id"),
    ],
)
def test_mismatched_or_duplicate_input_records_are_typed_errors(mutator, reason) -> None:
    ledger, grouping, tone = pipeline(
        fact(source_key="Transit_JUPITER"),
        fact(source_key="Transit_SATURN", aspect_type="TRINE", temporal_role="supporting"),
    )
    bad_ledger, bad_grouping, bad_tone = mutator(ledger, grouping, tone)

    with pytest.raises(TodayConvergenceSelectionError, match=reason):
        select_canonical_presentation(bad_ledger, bad_grouping, bad_tone, TARGET_DATE, "UTC", CANON)


@pytest.mark.parametrize(
    ("target_date", "timezone_name", "reason"),
    [
        (TARGET_DATE, "Not/AZone", "invalid_timezone"),
        (datetime(2026, 7, 31, 0, 0), "UTC", "target_date"),
    ],
)
def test_invalid_date_and_timezone_are_typed_errors(target_date, timezone_name, reason) -> None:
    ledger, grouping, tone = pipeline(fact(source_key="Transit_MOON"))

    with pytest.raises(TodayConvergenceSelectionError, match=reason):
        select_canonical_presentation(ledger, grouping, tone, target_date, timezone_name, CANON)


def test_naive_exact_datetime_is_a_typed_selection_error() -> None:
    ledger, grouping, tone = pipeline(fact(source_key="Transit_MOON"))
    bad_units = tuple(replace(unit, exact_at=datetime(2026, 7, 31, 12, 0)) for unit in ledger.units)
    bad_ledger = replace(ledger, units=bad_units)
    by_id = {unit.canonical_event_id: unit for unit in bad_units}
    bad_grouping = replace(
        grouping,
        groups=tuple(
            replace(group, member_units=tuple(by_id[unit.canonical_event_id] for unit in group.member_units))
            for group in grouping.groups
        ),
    )

    with pytest.raises(TodayConvergenceSelectionError, match="naive_exact_at"):
        select_canonical_presentation(bad_ledger, bad_grouping, tone, TARGET_DATE, "UTC", CANON)


def test_selection_records_are_frozen_and_do_not_expose_compatibility_aliases() -> None:
    result = select(fact(source_key="Transit_MOON"))

    with pytest.raises(FrozenInstanceError):
        result.state = "convergence_today"  # type: ignore[misc]
    assert not hasattr(result, "groups")
    assert not hasattr(result, "polarity_counts")
    assert not hasattr(result, "selected_events")


# END_BLOCK: VALIDATION
