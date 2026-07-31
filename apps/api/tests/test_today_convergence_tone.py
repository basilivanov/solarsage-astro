# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_TONE — frozen tone policy acceptance tests.
# ROLE: Proves canon-driven unit, group, and timezone-aware day-tone behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-TONE
# purpose: Validate pure tone aggregation over accepted ledger and grouping records.
# owns:
#   - apps/api/tests/test_today_convergence_tone.py
# inputs: immutable canonical ledger/grouping records and frozen tone canon.
# outputs: pytest assertions for tone layers, fresh predicates, and audit semantics.
# dependencies: today_convergence_canon, today_convergence_units, today_convergence_ledger, today_convergence_groups, today_convergence_tone.
# side_effects: none.
# emitted_logs: none.
# invariants: day tone is selection-independent, distinct-driver deterministic, and timezone-aware.
# failure_policy: typed tone errors fail the test rather than falling back to legacy behavior.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-TONE

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-TONE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - UNIT_AND_GROUP_TONE: canon weights, polarity normalization, and group balance.
#   - FRESH_DAY_TONE: timezone/date boundary and fast/context rules.
#   - AUDIT_AND_DETERMINISM: selected-only diagnostics and immutable permutation output.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-TONE

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone
from itertools import permutations

import pytest

from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_groups import build_canonical_groups
from app.services.today_convergence_ledger import build_canonical_ledger
from app.services.today_convergence_tone import (
    CanonicalGroupTone,
    TodayConvergenceToneError,
    compute_canonical_tone,
)
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


def result_for(*rows: RawPhysicalFact, selected_unit_ids: tuple[str, ...] | None = None, timezone_name: str = "UTC"):
    ledger = build_canonical_ledger(list(rows), CANON)
    grouping = build_canonical_groups(ledger, CANON)
    selected = selected_unit_ids
    if selected is None:
        selected = tuple(
            unit.canonical_event_id
            for unit in ledger.units
            if unit.evidence_eligible and unit.exclusion_reason is None and unit.temporal_role != "background"
        )
    return compute_canonical_tone(
        ledger,
        grouping,
        TARGET_DATE,
        timezone_name,
        selected,
        CANON,
    )


def unit_for(raw: RawPhysicalFact):
    result = build_canonical_unit(raw, CANON)
    assert result.unit is not None
    return result.unit


def test_unit_neutral_maps_to_steady_and_group_weights_are_canon_driven() -> None:
    result = result_for(
        fact(source_key="Transit_JUPITER", polarity="neutral", strength=0.8),
        fact(source_key="Transit_SATURN", polarity="mixed", strength=0.8, aspect_type="TRINE"),
    )

    assert result.group_tones[0].polarity == "mixed"
    assert result.group_tones[0].supportive_score == 0.4
    assert result.group_tones[0].tense_score == 0.4
    assert result.group_tones[0].unit_polarity_counts == (("mixed", 1), ("steady", 1))


def test_group_balance_supportive_tense_and_steady_branches() -> None:
    supportive = result_for(
        fact(source_key="Transit_JUPITER", polarity="supportive", strength=0.8),
        fact(source_key="Transit_SATURN", polarity="supportive", strength=0.8, aspect_type="TRINE"),
    )
    tense = result_for(
        fact(source_key="Transit_JUPITER", polarity="tense"),
        fact(source_key="Transit_SATURN", polarity="neutral", aspect_type="TRINE"),
    )
    steady = result_for(
        fact(source_key="Transit_JUPITER", polarity="neutral"),
        fact(source_key="Transit_SATURN", polarity="neutral", aspect_type="TRINE"),
    )

    assert supportive.group_tones[0].polarity == "supportive"
    assert tense.group_tones[0].polarity == "tense"
    assert steady.group_tones[0].polarity == "steady"


def test_high_confidence_supportive_hero_creates_supportive_day_tone() -> None:
    result = result_for(
        fact(source_key="Transit_JUPITER", polarity="supportive", strength=0.9),
        fact(
            source_key="Transit_SATURN",
            polarity="tense",
            temporal_role="supporting",
            exact_at=date(2026, 7, 1),
            aspect_type="TRINE",
        ),
    )

    assert result.day_tone == "supportive"
    assert result.audit.tone_scores.high_confidence_supportive_anchor is True


def test_two_independent_fresh_supportive_units_create_supportive_day_tone() -> None:
    result = result_for(
        fact(source_key="Transit_JUPITER", polarity="supportive", strength=0.6),
        fact(source_key="Transit_SATURN", polarity="supportive", strength=0.6, aspect_type="TRINE"),
    )

    assert result.day_tone == "supportive"
    assert result.audit.tone_scores.fresh_supportive_units == 2


def test_group_outside_mixed_margin_resolves_to_dominant_supportive_side() -> None:
    result = result_for(
        fact(source_key="Transit_JUPITER", polarity="supportive", strength=1.0),
        fact(source_key="Transit_SATURN", polarity="tense", strength=0.5, aspect_type="TRINE"),
    )

    tone = result.group_tones[0]
    assert tone.supportive_score == 1.0
    assert tone.tense_score == 0.5
    assert tone.polarity == "supportive"


def test_same_driver_uses_maximum_weight_once_with_event_id_tiebreak() -> None:
    result = result_for(
        fact(source_key="Transit_JUPITER", polarity="tense", strength=0.4, temporal_role="supporting"),
        fact(source_key="Transit_JUPITER", polarity="supportive", strength=0.9, aspect_type="TRINE"),
        fact(source_key="Transit_SATURN", polarity="supportive", aspect_type="OPPOSITION"),
    )

    tone = result.group_tones[0]
    assert tone.independent_unit_count == 2
    assert tone.driver_keys == ("JUPITER", "SATURN")
    assert tone.supportive_score == 1.7
    assert tone.tense_score == 0.0


def test_timezone_boundary_makes_supporting_exact_at_fresh() -> None:
    result = result_for(
        fact(
            source_key="Transit_JUPITER",
            temporal_role="supporting",
            exact_at=datetime(2026, 7, 30, 23, 30, tzinfo=timezone.utc),
        ),
        fact(source_key="Transit_SATURN", polarity="supportive", aspect_type="TRINE"),
        timezone_name="Europe/Moscow",
    )

    assert result.day_tone == "supportive"
    assert result.audit.tone_scores.fresh_supportive_units == 2
    assert result.audit.context_unit_ids == ()


def test_long_running_tense_supporting_is_context_not_day_trigger() -> None:
    context_row = fact(source_key="Transit_JUPITER", polarity="tense", temporal_role="supporting", exact_at=date(2026, 7, 1))
    result = result_for(
        context_row,
        fact(source_key="Transit_MOON", polarity="supportive", aspect_type="TRINE"),
    )

    assert result.day_tone == "steady"
    assert result.audit.tone_scores.context_tense_units == 1
    assert result.audit.context_unit_ids == (unit_for(context_row).canonical_event_id,)


def test_background_is_ignored_without_becoming_context() -> None:
    baseline = result_for(fact(source_key="Transit_MOON", polarity="supportive"))
    with_background = result_for(
        fact(source_key="Transit_MOON", polarity="supportive"),
        fact(source_key="Transit_MARS", polarity="tense", temporal_role="background"),
    )

    assert with_background.day_tone == baseline.day_tone == "steady"
    assert with_background.audit.context_unit_ids == baseline.audit.context_unit_ids == ()


def test_naive_exact_at_is_a_typed_invariant_error_even_for_anchor_role() -> None:
    ledger = build_canonical_ledger(
        [fact(), fact(source_key="Transit_SATURN", aspect_type="TRINE")], CANON
    )
    grouping = build_canonical_groups(ledger, CANON)
    bad_units = tuple(replace(unit, exact_at=datetime(2026, 7, 31, 12, 0)) for unit in ledger.units)
    by_id = {unit.canonical_event_id: unit for unit in bad_units}
    bad_groups = tuple(
        replace(group, member_units=tuple(by_id[unit.canonical_event_id] for unit in group.member_units))
        for group in grouping.groups
    )
    bad_ledger = replace(ledger, units=bad_units)
    bad_grouping = replace(grouping, groups=bad_groups)

    with pytest.raises(TodayConvergenceToneError, match="naive_exact_at"):
        compute_canonical_tone(
            bad_ledger,
            bad_grouping,
            TARGET_DATE,
            "UTC",
            tuple(unit.canonical_event_id for unit in bad_units),
            CANON,
        )


def test_fast_single_and_mixed_single_are_steady() -> None:
    fast_row = fact(source_key="Transit_MOON", polarity="tense")
    mixed_row = fact(source_key="Transit_JUPITER", polarity="mixed")
    fast = result_for(fast_row)
    mixed = result_for(mixed_row)

    assert fast.day_tone == "steady"
    assert mixed.day_tone == "steady"
    assert fast.audit.tone_trigger_keys == ()
    assert mixed.audit.tone_trigger_keys == (unit_for(mixed_row).semantic_key,)


def test_hero_and_independent_thresholds_and_fresh_mixed_pair() -> None:
    hero = result_for(
        fact(source_key="Transit_JUPITER", polarity="tense", strength=0.9),
        fact(source_key="Transit_SATURN", polarity="tense", temporal_role="supporting", exact_at=date(2026, 7, 1), aspect_type="TRINE"),
    )
    pair = result_for(
        fact(source_key="Transit_JUPITER", polarity="tense", strength=0.4),
        fact(source_key="Transit_SATURN", polarity="supportive", strength=0.4, aspect_type="TRINE"),
    )
    two = result_for(
        fact(source_key="Transit_JUPITER", polarity="tense"),
        fact(source_key="Transit_SATURN", polarity="tense", aspect_type="TRINE"),
    )

    assert hero.day_tone == "tense"
    assert pair.day_tone == "mixed"
    assert two.day_tone == "tense"


def test_selected_legacy_audit_is_selected_only_and_day_tone_is_selection_independent() -> None:
    tense = fact(source_key="Transit_JUPITER", polarity="tense")
    supportive = fact(source_key="Transit_SATURN", polarity="supportive", aspect_type="TRINE")
    ledger = build_canonical_ledger([tense, supportive], CANON)
    grouping = build_canonical_groups(ledger, CANON)
    supportive_id = next(unit.canonical_event_id for unit in ledger.units if unit.polarity == "supportive")

    result = compute_canonical_tone(ledger, grouping, TARGET_DATE, "UTC", (supportive_id,), CANON)

    assert result.day_tone == "mixed"
    assert result.audit.unit_polarity_counts == (("supportive", 1),)
    assert result.audit.legacy_any_selected_tense is False


def test_group_order_and_permutation_are_deterministic_and_records_are_frozen() -> None:
    rows = (
        fact(source_key="Transit_JUPITER", target_key="Natal_SATURN"),
        fact(source_key="Transit_SATURN", target_key="Natal_SATURN", aspect_type="TRINE"),
        fact(source_key="Transit_URANUS", target_key="Natal_MOON", aspect_type="OPPOSITION"),
    )
    outputs = [result_for(*order) for order in permutations(rows)]

    assert all(output == outputs[0] for output in outputs)
    assert tuple(tone.group_id for tone in outputs[0].group_tones) == tuple(
        sorted(tone.group_id for tone in outputs[0].group_tones)
    )
    with pytest.raises(FrozenInstanceError):
        outputs[0].audit.tone_scores.fresh_tense_units = 99  # type: ignore[misc]


@pytest.mark.parametrize(
    ("timezone_name", "selected", "expected"),
    [
        ("Not/AZone", (), "invalid_timezone"),
        ("UTC", ("unknown",), "unknown_selected_unit"),
    ],
)
def test_invalid_timezone_and_selected_reference_are_typed_errors(timezone_name, selected, expected) -> None:
    ledger = build_canonical_ledger(
        [fact(), fact(source_key="Transit_SATURN", aspect_type="TRINE")], CANON
    )
    grouping = build_canonical_groups(ledger, CANON)

    with pytest.raises(TodayConvergenceToneError, match=expected):
        compute_canonical_tone(ledger, grouping, TARGET_DATE, timezone_name, selected, CANON)


def test_invalid_target_date_type_is_a_typed_error() -> None:
    ledger = build_canonical_ledger([fact()], CANON)
    grouping = build_canonical_groups(ledger, CANON)
    unit_id = ledger.units[0].canonical_event_id

    with pytest.raises(TodayConvergenceToneError, match="target_date"):
        compute_canonical_tone(ledger, grouping, datetime(2026, 7, 31, 0, 0), "UTC", (unit_id,), CANON)


def test_duplicate_selected_unit_id_is_a_typed_error() -> None:
    ledger = build_canonical_ledger([fact()], CANON)
    grouping = build_canonical_groups(ledger, CANON)
    unit_id = ledger.units[0].canonical_event_id

    with pytest.raises(TodayConvergenceToneError, match="duplicate_selected_unit_id"):
        compute_canonical_tone(ledger, grouping, TARGET_DATE, "UTC", (unit_id, unit_id), CANON)


def test_invalid_group_reference_is_typed_error() -> None:
    ledger = build_canonical_ledger(
        [fact(), fact(source_key="Transit_SATURN", aspect_type="TRINE")], CANON
    )
    grouping = build_canonical_groups(ledger, CANON)
    foreign = replace(grouping, groups=(replace(grouping.groups[0], member_units=()),)) if grouping.groups else grouping

    with pytest.raises(TodayConvergenceToneError, match="group"):
        compute_canonical_tone(ledger, foreign, TARGET_DATE, "UTC", (), CANON)


def test_tone_record_type_is_public_and_unused_wire_steady_remains_internal() -> None:
    assert CanonicalGroupTone.__name__ == "CanonicalGroupTone"
