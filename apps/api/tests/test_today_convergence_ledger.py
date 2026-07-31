# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_LEDGER — canonical ledger and delta tests.
# ROLE: Proves deterministic deduplication, immutable audit, and semantic DayDelta upgrades.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-LEDGER
# purpose: Validate the pure canonical ledger between raw facts and grouping.
# owns:
#   - apps/api/tests/test_today_convergence_ledger.py
# inputs: RawPhysicalFact sequences and frozen TodayConvergenceCanon values.
# outputs: pytest assertions for ledger units, audit counts, and typed misuse errors.
# dependencies: app.services.today_convergence_canon, app.services.today_convergence_units, app.services.today_convergence_ledger.
# side_effects: none.
# emitted_logs: none.
# invariants: ledger output is immutable, sorted, producer-independent, and fail-closed per row.
# failure_policy: pytest failure on deduplication, provenance, audit, or delta contract drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-LEDGER

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-LEDGER
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - DEDUPLICATION: producer precedence, winner selection, provenance union, and conflicts.
#   - FAIL_CLOSED_AUDIT: malformed rows, producer reasons, and audit-only units.
#   - DELTA_TRIGGERS: exact semantic-key upgrades and planet-name negative cases.
#   - IMMUTABILITY: frozen records, sorted output, and misuse errors.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-LEDGER

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from itertools import permutations
from math import nan

import pytest

from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_ledger import (
    CanonicalLedger,
    TodayConvergenceLedgerError,
    build_canonical_ledger,
)
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
        "orb": 3.5,
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
        "provenance_ids": ("activation-row",),
    }
    values.update(overrides)
    return RawPhysicalFact(**values)


def unit_for(raw: RawPhysicalFact):
    result = build_canonical_unit(raw, CANON)
    assert result.unit is not None
    return result.unit


def audit_map(ledger: CanonicalLedger) -> dict[str, int]:
    return dict(ledger.audit.excluded_by_reason)


# START_BLOCK: DEDUPLICATION
def test_activation_wins_duplicate_and_provenance_is_union() -> None:
    activation = fact(producer="activation", provenance_ids=("activation-row",), polarity="supportive")
    day_signal = fact(producer="day_signal", provenance_ids=("signal-row",), polarity="supportive")

    ledger = build_canonical_ledger([day_signal, activation], CANON)

    assert len(ledger.units) == 1
    assert ledger.units[0].canonical_event_id.startswith("evt_v1_")
    assert ledger.units[0].polarity == "supportive"
    assert ledger.units[0].provenance_ids == ("activation-row", "signal-row")
    assert ledger.audit.duplicate_fact_count == 1
    assert ledger.audit.duplicate_conflict_count == 0
    assert ledger.audit.producer_counts == (("activation", 1), ("day_signal", 1))


def test_raw_and_provenance_permutations_are_byte_equal() -> None:
    rows = [
        fact(producer="activation", provenance_ids=("z", "a")),
        fact(producer="day_signal", provenance_ids=("b",)),
        fact(target_key="Natal_MOON", provenance_ids=("moon",)),
    ]

    ledgers = [build_canonical_ledger(order, CANON) for order in permutations(rows)]

    assert all(ledger == ledgers[0] for ledger in ledgers)


def test_same_producer_conflict_has_deterministic_winner_and_counter() -> None:
    supportive = fact(producer="activation", polarity="supportive", strength=0.2)
    tense = fact(producer="activation", polarity="tense", strength=0.9)

    forward = build_canonical_ledger([supportive, tense], CANON)
    reverse = build_canonical_ledger([tense, supportive], CANON)

    assert forward == reverse
    assert forward.audit.duplicate_fact_count == 1
    assert forward.audit.duplicate_conflict_count == 1
    assert forward.units[0].polarity == "supportive"


def test_distinct_physical_ids_remain_distinct_with_same_driver() -> None:
    first = fact(exact_at=EXACT_AT)
    second = fact(exact_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc))

    ledger = build_canonical_ledger([first, second], CANON)

    assert len(ledger.units) == 2
    assert [unit.canonical_event_id for unit in ledger.units] == sorted(
        unit.canonical_event_id for unit in ledger.units
    )
    assert ledger.audit.duplicate_fact_count == 0


# END_BLOCK: DEDUPLICATION


# START_BLOCK: FAIL_CLOSED_AUDIT
def test_malformed_rows_and_producers_aggregate_without_aborting_valid_rows() -> None:
    ledger = build_canonical_ledger(
        [
            fact(polarity="unknown"),
            object(),
            fact(producer=None),
            fact(producer="legacy"),
            fact(provenance_ids=("valid",)),
        ],
        CANON,
    )

    reasons = audit_map(ledger)
    assert len(ledger.units) == 1
    assert ledger.audit.accepted_fact_count == 1
    assert reasons["invalid_polarity"] == 1
    assert reasons["non_raw_fact"] == 1
    assert reasons["empty_producer"] == 1
    assert reasons["unknown_producer"] == 1


def test_background_and_time_sensitive_units_remain_audit_only() -> None:
    background = fact(target_key="Natal_MOON", temporal_role="background")
    time_sensitive = fact(
        target_key="Natal_VENUS",
        birth_time_mode="bucket",
        birth_time_robustness="time_sensitive",
        temporal_role="supporting",
    )
    supporting = fact(target_key="Natal_MARS", temporal_role="supporting")
    trigger_keys = [unit_for(row).semantic_key for row in (background, time_sensitive, supporting)]

    ledger = build_canonical_ledger(
        [background, time_sensitive, supporting],
        CANON,
        delta_trigger_semantic_keys=trigger_keys,
    )

    by_target = {unit.target_key: unit for unit in ledger.units}
    assert by_target["MOON"].temporal_role == "background"
    assert by_target["VENUS"].temporal_role == "supporting"
    assert by_target["MARS"].temporal_role == "anchor_today"
    assert by_target["MOON"].impulse_eligible is False
    assert by_target["VENUS"].evidence_eligible is False
    assert ledger.audit.delta_upgraded_count == 1


# END_BLOCK: FAIL_CLOSED_AUDIT


# START_BLOCK: DELTA_TRIGGERS
def test_delta_matches_exact_semantic_key_and_planet_name_does_not() -> None:
    supporting = fact(target_key="Natal_MARS", temporal_role="supporting")
    semantic_key = unit_for(supporting).semantic_key

    upgraded = build_canonical_ledger(
        [supporting], CANON, delta_trigger_semantic_keys=[semantic_key, semantic_key, "JUPITER"]
    )
    no_upgrade = build_canonical_ledger([supporting], CANON, delta_trigger_semantic_keys=["JUPITER"])

    assert upgraded.units[0].temporal_role == "anchor_today"
    assert upgraded.audit.delta_upgraded_count == 1
    assert upgraded.audit.unmatched_delta_trigger_count == 1
    assert no_upgrade.units[0].temporal_role == "supporting"
    assert no_upgrade.audit.delta_upgraded_count == 0
    assert no_upgrade.audit.unmatched_delta_trigger_count == 1


def test_semantic_trigger_does_not_reupgrade_existing_anchor() -> None:
    anchor = fact(temporal_role="anchor_today", provenance_ids=("anchor",))
    before = unit_for(anchor)

    ledger = build_canonical_ledger([anchor], CANON, delta_trigger_semantic_keys=[before.semantic_key])

    assert ledger.units == (before,)
    assert ledger.audit.delta_upgraded_count == 0


def test_duplicate_unmatched_delta_triggers_count_once() -> None:
    ledger = build_canonical_ledger(
        [fact()], CANON, delta_trigger_semantic_keys=["missing-semantic-key", "missing-semantic-key"]
    )

    assert ledger.audit.unmatched_delta_trigger_count == 1


def test_delta_upgrade_changes_only_temporal_role() -> None:
    supporting = fact(temporal_role="supporting", provenance_ids=("z", "a"))
    before = unit_for(supporting)
    ledger = build_canonical_ledger([supporting], CANON, delta_trigger_semantic_keys=[before.semantic_key])
    after = ledger.units[0]

    assert after.temporal_role == "anchor_today"
    assert after == replace(before, temporal_role="anchor_today")
    assert after.canonical_event_id == before.canonical_event_id
    assert after.semantic_key == before.semantic_key
    assert after.provenance_ids == before.provenance_ids
    assert (
        after.impulse_eligible,
        after.evidence_eligible,
        after.rare_anchor_eligible,
        after.hero_confirmation_eligible,
    ) == (
        before.impulse_eligible,
        before.evidence_eligible,
        before.rare_anchor_eligible,
        before.hero_confirmation_eligible,
    )


# END_BLOCK: DELTA_TRIGGERS


# START_BLOCK: IMMUTABILITY
def test_ledger_records_are_frozen_and_misuse_is_typed() -> None:
    ledger = build_canonical_ledger([fact()], CANON)

    with pytest.raises(FrozenInstanceError):
        ledger.units = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ledger.audit.raw_fact_count = 0  # type: ignore[misc]
    with pytest.raises(TodayConvergenceLedgerError, match="raw_facts"):
        build_canonical_ledger(iter([fact()]), CANON)
    with pytest.raises(TodayConvergenceLedgerError, match="delta_trigger_semantic_keys"):
        build_canonical_ledger([fact()], CANON, delta_trigger_semantic_keys=[nan])  # type: ignore[list-item]


# END_BLOCK: IMMUTABILITY
