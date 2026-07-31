# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_GROUPS — direct-star grouping contract tests.
# ROLE: Proves direct physical grouping, C1 hero selection, independence, and per-group spheres.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-GROUPS
# purpose: Validate deterministic grouping of accepted canonical ledger units.
# owns:
#   - apps/api/tests/test_today_convergence_groups.py
# inputs: Immutable CanonicalLedger records and the frozen TodayConvergenceCanon.
# outputs: pytest assertions for direct stars, hero C1, independence, sphere votes, and typed misuse.
# dependencies: app.services.today_convergence_canon, app.services.today_convergence_units, app.services.today_convergence_ledger, app.services.today_convergence_groups.
# side_effects: none.
# emitted_logs: none.
# invariants: grouping is direct, input-order invariant, producer-independent, and presentation-free.
# failure_policy: pytest failure on grouping, hero, independence, sphere, audit, or immutability drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-GROUPS

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-GROUPS
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - DIRECT_STARS: target/theme links and no transitive bridge.
#   - INDEPENDENCE: distinct drivers, anchor choice, and public member pool.
#   - HERO_C1: rare anchor and direct independent confirmation.
#   - SPHERE_PROJECTION: majority, tie-breaks, threshold, and per-group cap.
#   - DETERMINISM: immutable records, group IDs, ordering, and typed misuse.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-GROUPS

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from itertools import permutations

import pytest

from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_groups import (
    CanonicalGroupingResult,
    TodayConvergenceGroupingError,
    build_canonical_groups,
)
from app.services.today_convergence_ledger import CanonicalLedger, build_canonical_ledger
from app.services.today_convergence_units import RawPhysicalFact, build_canonical_unit


CANON = load_today_convergence_canon()
EXACT_AT = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


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
        "exact_at": EXACT_AT,
        "phase": "Exact",
        "active_from": None,
        "active_until": None,
        "data_quality": "High",
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


def unit_for(raw: RawPhysicalFact):
    result = build_canonical_unit(raw, CANON)
    assert result.unit is not None
    return result.unit


def ledger_for(*rows: RawPhysicalFact) -> CanonicalLedger:
    return build_canonical_ledger(list(rows), CANON)


def groups_for(ledger: CanonicalLedger) -> CanonicalGroupingResult:
    return build_canonical_groups(ledger, CANON)


def with_spheres(ledger: CanonicalLedger, spheres: tuple[tuple[str, ...], ...]) -> CanonicalLedger:
    assert len(ledger.units) == len(spheres)
    return replace(
        ledger,
        units=tuple(replace(unit, product_spheres=unit_spheres) for unit, unit_spheres in zip(ledger.units, spheres)),
    )


# START_BLOCK: DIRECT_STARS
def test_shared_target_requires_two_distinct_drivers_for_medium_group() -> None:
    anchor = fact(source_key="Transit_JUPITER", temporal_role="anchor_today")
    confirmation = fact(source_key="Transit_MOON", aspect_type="TRINE", temporal_role="supporting")

    result = groups_for(ledger_for(anchor, confirmation))

    assert len(result.groups) == 1
    assert result.groups[0].evidence_level == "medium"
    assert result.groups[0].hero_eligible is False
    assert result.groups[0].independent_driver_keys == ("JUPITER", "MOON")


def test_theme_intersection_links_and_disjoint_themes_do_not() -> None:
    anchor = fact(source_key="Transit_JUPITER", target_key="Natal_SATURN")
    linked = fact(
        source_key="Transit_MERCURY",
        target_key="Natal_MERCURY",
        aspect_type="TRINE",
        technical_spheres=("work_status_achievement",),
        temporal_role="supporting",
    )
    disjoint = fact(
        source_key="Transit_MERCURY",
        target_key="Natal_MERCURY",
        aspect_type="OPPOSITION",
        technical_spheres=("thinking_speech_learning",),
        temporal_role="supporting",
    )

    linked_result = groups_for(ledger_for(anchor, linked))
    disjoint_result = groups_for(ledger_for(anchor, disjoint))

    assert len(linked_result.groups) == 1
    assert len(disjoint_result.groups) == 0
    assert disjoint_result.audit.insufficient_independence_count == 1


def test_background_and_ineligible_units_are_not_members_witnesses_or_bridges() -> None:
    anchor = fact(source_key="Transit_JUPITER", temporal_role="anchor_today")
    background = fact(source_key="Transit_MARS", aspect_type="TRINE", temporal_role="background")
    time_sensitive = fact(
        source_key="Transit_VENUS",
        aspect_type="OPPOSITION",
        birth_time_mode="bucket",
        birth_time_robustness="time_sensitive",
        temporal_role="supporting",
    )

    result = groups_for(ledger_for(anchor, background, time_sensitive))

    assert result.groups == ()
    assert result.audit.background_exclusion_count == 1
    assert result.audit.ineligible_exclusion_count == 1
    assert result.audit.candidate_star_count == 1
    assert result.audit.insufficient_independence_count == 1


def test_direct_star_does_not_follow_a_to_b_to_c_bridge() -> None:
    anchor_a = fact(
        source_key="Transit_JUPITER",
        target_key="Natal_SATURN",
        technical_spheres=("work_status_achievement",),
        temporal_role="anchor_today",
    )
    bridge_b = fact(
        source_key="Transit_MOON",
        target_key="Natal_MERCURY",
        aspect_type="TRINE",
        technical_spheres=("work_status_achievement",),
        temporal_role="supporting",
    )
    endpoint_c = fact(
        source_key="Transit_MERCURY",
        target_key="Natal_MERCURY",
        aspect_type="OPPOSITION",
        technical_spheres=("thinking_speech_learning",),
        temporal_role="supporting",
    )

    result = groups_for(ledger_for(anchor_a, bridge_b, endpoint_c))

    assert len(result.groups) == 1
    assert {unit.source_key for unit in result.groups[0].member_units} == {"JUPITER", "MOON"}
    assert "MERCURY" not in {unit.source_key for unit in result.groups[0].member_units}


# END_BLOCK: DIRECT_STARS


# START_BLOCK: INDEPENDENCE
def test_producer_duplicate_does_not_raise_independence_and_second_driver_is_required() -> None:
    anchor = fact(source_key="Transit_JUPITER", temporal_role="anchor_today")
    supporting = fact(source_key="Transit_MARS", aspect_type="TRINE", temporal_role="supporting")
    duplicate = replace(supporting, producer="day_signal", provenance_ids=("duplicate",))

    with_duplicate = groups_for(ledger_for(anchor, supporting, duplicate))
    without_second_driver = groups_for(ledger_for(anchor))

    assert len(with_duplicate.groups) == 1
    assert with_duplicate.groups[0].member_units == tuple(
        sorted(with_duplicate.groups[0].member_units, key=lambda unit: unit.canonical_event_id)
    )
    assert without_second_driver.groups == ()
    assert without_second_driver.audit.insufficient_independence_count == 1


def test_two_ordinary_moon_events_same_target_do_not_form_group_or_hero() -> None:
    first = fact(source_key="Transit_MOON", temporal_role="anchor_today")
    second = fact(source_key="Transit_MOON", aspect_type="TRINE", temporal_role="supporting")

    result = groups_for(ledger_for(first, second))

    assert result.groups == ()
    assert result.audit.insufficient_independence_count == 1
    assert result.audit.hero_count == 0


def test_anchor_selection_uses_strength_salience_then_event_id() -> None:
    weaker = fact(source_key="Transit_MOON", target_salience=0.9, strength=0.4, temporal_role="anchor_today")
    stronger = fact(
        source_key="Transit_MERCURY",
        aspect_type="TRINE",
        target_salience=0.1,
        strength=0.8,
        temporal_role="anchor_today",
    )
    result = groups_for(ledger_for(weaker, stronger))

    assert len(result.groups) == 1
    assert result.groups[0].anchor_unit_id == unit_for(stronger).canonical_event_id


# END_BLOCK: INDEPENDENCE


# START_BLOCK: HERO_C1
def test_rare_planet_anchor_and_direct_slow_confirmation_are_hero_high() -> None:
    rare = fact(source_key="Transit_JUPITER", target_key="Natal_SATURN", strength=0.9, temporal_role="anchor_today")
    confirmation = fact(
        source_key="Transit_SATURN",
        target_key="Natal_SATURN",
        aspect_type="TRINE",
        strength=0.8,
        temporal_role="supporting",
    )

    result = groups_for(ledger_for(rare, confirmation))

    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.hero_eligible is True
    assert group.evidence_level == "high"
    assert group.hero_anchor_id == unit_for(rare).canonical_event_id
    assert group.hero_confirmation_id == unit_for(confirmation).canonical_event_id


def test_fast_confirmation_and_lot_target_rare_anchor_remain_medium() -> None:
    rare = fact(source_key="Transit_JUPITER", target_key="Natal_SATURN", temporal_role="anchor_today")
    fast = fact(source_key="Transit_MOON", target_key="Natal_SATURN", aspect_type="TRINE", temporal_role="supporting")
    lot = fact(
        source_key="Transit_JUPITER",
        target_key="Natal_SATURN",
        target_type="lot",
        aspect_type="OPPOSITION",
        temporal_role="anchor_today",
    )
    slow = fact(source_key="Transit_SATURN", target_key="Natal_SATURN", aspect_type="TRINE", temporal_role="supporting")

    fast_result = groups_for(ledger_for(rare, fast))
    lot_result = groups_for(ledger_for(lot, slow))

    assert fast_result.groups[0].hero_eligible is False
    assert fast_result.groups[0].evidence_level == "medium"
    assert lot_result.groups[0].hero_eligible is False
    assert lot_result.groups[0].evidence_level == "medium"


def test_hero_confirmer_must_be_direct_to_rare_anchor_not_only_bridge_member() -> None:
    rare = fact(
        source_key="Transit_JUPITER",
        target_key="Natal_SATURN",
        technical_spheres=("work_status_achievement",),
        temporal_role="anchor_today",
    )
    bridge_anchor = fact(
        source_key="Transit_MOON",
        target_key="Natal_MERCURY",
        aspect_type="TRINE",
        technical_spheres=("work_status_achievement",),
        temporal_role="anchor_today",
    )
    indirect_confirmation = fact(
        source_key="Transit_NEPTUNE",
        target_key="Natal_MERCURY",
        aspect_type="OPPOSITION",
        technical_spheres=("thinking_speech_learning",),
        temporal_role="supporting",
    )

    result = groups_for(ledger_for(rare, bridge_anchor, indirect_confirmation))

    assert result.groups
    assert all(group.hero_eligible is False for group in result.groups)


# END_BLOCK: HERO_C1


# START_BLOCK: SPHERE_PROJECTION
def test_group_sphere_majority_and_secondary_threshold_are_per_group() -> None:
    rows = [
        fact(source_key="Transit_MOON", temporal_role="anchor_today"),
        fact(source_key="Transit_MERCURY", aspect_type="TRINE", temporal_role="supporting"),
        fact(source_key="Transit_VENUS", aspect_type="OPPOSITION", temporal_role="supporting"),
    ]
    ledger = with_spheres(ledger_for(*rows), (("work", "money"), ("work", "money"), ("work", "documents")))

    result = groups_for(ledger)

    assert len(result.groups) == 1
    assert result.groups[0].primary_sphere == "work"
    assert result.groups[0].secondary_sphere == "money"


def test_sphere_ties_use_anchor_then_canonical_order_and_do_not_clone_group() -> None:
    anchor_tie = with_spheres(
        ledger_for(
            fact(source_key="Transit_MOON", temporal_role="anchor_today"),
            fact(source_key="Transit_MERCURY", aspect_type="TRINE", temporal_role="supporting"),
        ),
        (("money",), ("work",)),
    )
    canonical_tie = with_spheres(
        ledger_for(
            fact(source_key="Transit_MOON", temporal_role="anchor_today"),
            fact(source_key="Transit_MERCURY", aspect_type="TRINE", temporal_role="supporting"),
            fact(source_key="Transit_VENUS", aspect_type="OPPOSITION", temporal_role="supporting"),
        ),
        ((), ("money",), ("work",)),
    )

    anchor_result = groups_for(anchor_tie)
    canonical_result = groups_for(canonical_tie)

    assert len(anchor_result.groups) == 1
    assert anchor_result.groups[0].primary_sphere == "money"
    assert canonical_result.groups[0].primary_sphere == "work"
    assert canonical_result.groups[0].secondary_sphere is None
    assert len(canonical_result.groups) == 1


def test_two_driver_star_without_product_spheres_is_not_published() -> None:
    ledger = with_spheres(
        ledger_for(
            fact(source_key="Transit_MOON", temporal_role="anchor_today"),
            fact(source_key="Transit_MERCURY", aspect_type="TRINE", temporal_role="supporting"),
        ),
        ((), ()),
    )

    result = groups_for(ledger)

    assert result.groups == ()
    assert result.audit.group_without_sphere_count == 1


# END_BLOCK: SPHERE_PROJECTION


# START_BLOCK: DETERMINISM
def test_star_dedup_permutation_group_id_and_records_are_immutable() -> None:
    rows = [
        fact(source_key="Transit_MOON", temporal_role="anchor_today", provenance_ids=("a",)),
        fact(source_key="Transit_MERCURY", aspect_type="TRINE", temporal_role="anchor_today", provenance_ids=("b",)),
        fact(source_key="Transit_VENUS", aspect_type="OPPOSITION", temporal_role="supporting", provenance_ids=("c",)),
    ]
    ledger = ledger_for(*rows)
    result = groups_for(ledger)
    permuted = [groups_for(replace(ledger, units=order)) for order in permutations(ledger.units)]

    assert result.audit.candidate_star_count == 2
    assert result.audit.duplicate_star_count == 1
    assert len(result.groups) == 1
    assert all(candidate == result for candidate in permuted)
    assert result.groups[0].group_id.startswith("cvg_v1_")
    with pytest.raises(FrozenInstanceError):
        result.groups = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.groups[0].primary_sphere = "money"  # type: ignore[misc]


def test_group_id_ignores_provenance_and_sphere_fanout() -> None:
    rows = [
        fact(source_key="Transit_MOON", temporal_role="anchor_today", provenance_ids=("a",)),
        fact(source_key="Transit_MERCURY", aspect_type="TRINE", temporal_role="supporting", provenance_ids=("b",)),
    ]
    ledger = ledger_for(*rows)
    baseline = groups_for(ledger)
    altered = with_spheres(
        replace(
            ledger,
            units=tuple(replace(unit, provenance_ids=("changed",)) for unit in ledger.units),
        ),
        (("work", "money"), ("relationships", "documents")),
    )

    changed = groups_for(altered)

    assert len(baseline.groups) == len(changed.groups) == 1
    assert baseline.groups[0].group_id == changed.groups[0].group_id


def test_duplicate_ledger_id_and_malformed_api_are_typed_errors() -> None:
    ledger = ledger_for(fact())
    duplicate = replace(ledger, units=(ledger.units[0], ledger.units[0]))

    with pytest.raises(TodayConvergenceGroupingError, match="duplicate canonical_event_id"):
        groups_for(duplicate)
    with pytest.raises(TodayConvergenceGroupingError, match="ledger"):
        build_canonical_groups(object(), CANON)  # type: ignore[arg-type]


# END_BLOCK: DETERMINISM
