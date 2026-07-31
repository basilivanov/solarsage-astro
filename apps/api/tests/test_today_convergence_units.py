# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_UNITS — canonical physical-unit boundary tests.
# ROLE: Proves producer-independent identity, immutable records, and fail-closed eligibility.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-UNITS
# purpose: Validate raw-fact normalization into deterministic canonical units.
# owns:
#   - apps/api/tests/test_today_convergence_units.py
# inputs: typed RawPhysicalFact instances and frozen canon.
# outputs: pytest assertions for accepted units and typed exclusions.
# dependencies: app.services.today_convergence_canon, app.services.today_convergence_units.
# side_effects: none.
# emitted_logs: none.
# invariants: physical identity excludes producer/provenance; malformed facts never raise.
# failure_policy: pytest failure on identity, normalization, or eligibility drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-UNITS

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-UNITS
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - IDENTITY: canonical JSON event identity and window normalization.
#   - FAIL_CLOSED: typed exclusion reasons for malformed facts.
#   - ELIGIBILITY: significance, background, and nested eligibility policies.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-UNITS

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone
from math import nan

import pytest

from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_units import (
    ExclusionReason,
    RawPhysicalFact,
    build_canonical_unit,
)


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
        "polarity": "TENse",
        "strength": 0.8,
        "temporal_role": "anchor_today",
        "producer": "activation",
        "provenance_ids": ("z-provenance", "a-provenance"),
    }
    values.update(overrides)
    return RawPhysicalFact(**values)


def assert_excluded(raw: RawPhysicalFact, reason: ExclusionReason) -> None:
    result = build_canonical_unit(raw, CANON)
    assert result.unit is None
    assert result.exclusion_reason == reason
    assert result.accepted is False


def test_valid_unit_normalizes_fields_and_is_immutable() -> None:
    result = build_canonical_unit(fact(), CANON)
    assert result.accepted is True
    assert result.unit is not None
    unit = result.unit
    assert unit.canonical_event_id.startswith("evt_v1_")
    assert len(unit.canonical_event_id) == len("evt_v1_") + 32
    assert unit.source_key == "JUPITER"
    assert unit.target_key == "SATURN"
    assert unit.aspect_type == "sextile"
    assert unit.polarity == "tense"
    assert unit.data_quality == "high"
    assert unit.provenance_ids == ("a-provenance", "z-provenance")
    assert unit.impulse_eligible is True
    assert unit.evidence_eligible is True
    assert unit.rare_anchor_eligible is True
    assert unit.hero_confirmation_eligible is True
    with pytest.raises(FrozenInstanceError):
        unit.source_key = "MOON"  # type: ignore[misc]


def test_target_domain_and_normalized_non_enum_fields_are_preserved() -> None:
    planet = build_canonical_unit(fact(target_type="planet", data_quality="Custom-Quality"), CANON).unit
    sphere = build_canonical_unit(fact(target_type="sphere"), CANON).unit
    assert planet is not None and sphere is not None
    assert planet.target_type == "natal_planet"
    assert planet.data_quality == "custom-quality"
    assert sphere.target_type == "sphere"


def test_phase_is_normalized_but_unknown_non_empty_values_do_not_exclude() -> None:
    result = build_canonical_unit(fact(phase="Entering"), CANON)
    unknown = build_canonical_unit(fact(phase="future_phase"), CANON)
    assert result.unit is not None and unknown.unit is not None
    assert result.unit.phase == "entering"
    assert unknown.unit.phase == "future_phase"
    assert unknown.unit.exclusion_reason is None


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (fact(polarity="unknown"), ExclusionReason.INVALID_POLARITY),
        (fact(polarity=""), ExclusionReason.INVALID_POLARITY),
        (fact(strength=1.01), ExclusionReason.INVALID_STRENGTH),
        (fact(strength=nan), ExclusionReason.INVALID_STRENGTH),
        (fact(target_salience=-0.01), ExclusionReason.INVALID_TARGET_SALIENCE),
        (fact(target_salience=nan), ExclusionReason.INVALID_TARGET_SALIENCE),
    ],
)
def test_numeric_and_polarity_domains_fail_closed_without_clamping(
    raw: RawPhysicalFact,
    reason: ExclusionReason,
) -> None:
    assert_excluded(raw, reason)


def test_neutral_polarity_and_inclusive_numeric_bounds_are_valid() -> None:
    result = build_canonical_unit(fact(polarity=" Neutral ", strength=0.0, target_salience=1.0), CANON)
    assert result.unit is not None
    assert result.unit.polarity == "neutral"
    assert result.unit.strength == 0.0
    assert result.unit.target_salience == 1.0


def test_producer_and_provenance_changes_do_not_change_identity() -> None:
    first = build_canonical_unit(fact(producer="activation", provenance_ids=("act-1",)), CANON).unit
    second = build_canonical_unit(fact(producer="day_signal", provenance_ids=("sig-2", "sig-1")), CANON).unit
    assert first is not None and second is not None
    assert first.canonical_event_id == second.canonical_event_id
    assert first.provenance_ids == ("act-1",)
    assert second.provenance_ids == ("sig-1", "sig-2")


def test_technique_and_factor_prefix_variants_preserve_canonical_identity() -> None:
    plain = build_canonical_unit(
        fact(technique="transit_to_natal", source_key="JUPITER", target_key="SATURN"), CANON
    ).unit
    producer_variant = build_canonical_unit(
        fact(technique="TRANSIT_TO_NATAL", source_key="Transit_JUPITER", target_key="Natal_SATURN"), CANON
    ).unit
    assert plain is not None and producer_variant is not None
    assert plain.canonical_event_id == producer_variant.canonical_event_id


@pytest.mark.parametrize(
    "field",
    ["technique", "technique_family", "source_key", "target_key", "target_type", "aspect_type", "event_class", "house"],
)
def test_each_physical_identity_axis_changes_id(field: str) -> None:
    base = fact()
    changes = {
        "technique": "secondary_progression",
        "technique_family": "progressive",
        "source_key": "Transit_SATURN",
        "target_key": "Natal_MOON",
        "target_type": "angle",
        "aspect_type": "TRINE",
        "event_class": "solar_return",
        "house": 3,
    }
    changed = replace(base, **{field: changes[field]})
    first = build_canonical_unit(base, CANON).unit
    second = build_canonical_unit(changed, CANON).unit
    assert first is not None and second is not None
    assert first.canonical_event_id != second.canonical_event_id


@pytest.mark.parametrize(
    "window_change",
    [
        {"exact_at": datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)},
        {"exact_at": None, "active_from": date(2026, 7, 31)},
        {"exact_at": None, "active_until": date(2026, 8, 1)},
    ],
)
def test_each_event_window_axis_changes_id(window_change: dict) -> None:
    base = fact(**({} if "exact_at" in window_change else {"exact_at": None, "active_from": date(2026, 7, 30)}))
    changed = replace(base, **window_change)
    first = build_canonical_unit(base, CANON).unit
    second = build_canonical_unit(changed, CANON).unit
    assert first is not None and second is not None
    assert first.canonical_event_id != second.canonical_event_id


def test_datetime_window_is_utc_canonicalized_and_naive_is_excluded() -> None:
    aware = build_canonical_unit(fact(exact_at=datetime(2026, 7, 31, 15, 0, tzinfo=timezone.utc)), CANON).unit
    offset = build_canonical_unit(fact(exact_at=datetime(2026, 7, 31, 18, 0, tzinfo=timezone.utc)), CANON).unit
    assert aware is not None and offset is not None
    assert aware.canonical_event_id != offset.canonical_event_id
    assert_excluded(fact(exact_at=datetime(2026, 7, 31, 12, 0)), ExclusionReason.NAIVE_DATETIME)
    assert_excluded(fact(exact_at=None, active_from=None, active_until=None), ExclusionReason.EVENT_WINDOW_MISSING)


def test_event_window_interval_is_inclusive_and_mixed_types_fail_closed() -> None:
    boundary = build_canonical_unit(
        fact(active_from=EXACT_AT, exact_at=EXACT_AT, active_until=EXACT_AT), CANON
    )
    assert boundary.unit is not None
    assert_excluded(
        fact(active_from=date(2026, 7, 31), exact_at=EXACT_AT),
        ExclusionReason.INVALID_EVENT_WINDOW,
    )
    assert_excluded(
        fact(active_from=datetime(2026, 7, 31, 13, 0, tzinfo=timezone.utc), exact_at=EXACT_AT),
        ExclusionReason.INVALID_EVENT_WINDOW,
    )
    assert_excluded(
        fact(active_from=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc), exact_at=EXACT_AT),
        ExclusionReason.INVALID_EVENT_WINDOW,
    )
    assert_excluded(
        fact(exact_at=EXACT_AT, active_until=datetime(2026, 7, 31, 11, 0, tzinfo=timezone.utc)),
        ExclusionReason.INVALID_EVENT_WINDOW,
    )


@pytest.mark.parametrize("birth_time_mode", ["bucket", "unknown"])
def test_time_sensitive_non_exact_birth_time_is_audit_only(birth_time_mode: str) -> None:
    result = build_canonical_unit(
        fact(birth_time_mode=birth_time_mode, birth_time_robustness="time_sensitive"), CANON
    )
    assert result.unit is not None
    assert result.accepted is True
    assert result.exclusion_reason == ExclusionReason.TIME_SENSITIVE_BIRTH_TIME
    assert result.unit.birth_time_mode == birth_time_mode
    assert result.unit.birth_time_robustness == "time_sensitive"
    assert (
        result.unit.impulse_eligible,
        result.unit.evidence_eligible,
        result.unit.rare_anchor_eligible,
        result.unit.hero_confirmation_eligible,
    ) == (False, False, False, False)


def test_exact_time_sensitive_birth_time_remains_eligible() -> None:
    result = build_canonical_unit(
        fact(birth_time_mode="exact", birth_time_robustness="time_sensitive"), CANON
    )
    assert result.unit is not None
    assert result.exclusion_reason is None
    assert result.unit.impulse_eligible is True


@pytest.mark.parametrize(
    ("family", "expected_driver"),
    [
        ("firdar", "firdar"),
        ("profection", "profection"),
        ("solar_return", "solar_return"),
        ("lunar_return", "lunar_return"),
        ("return", "return"),
        ("progression", "progression"),
        ("progressive", "progressive"),
        ("transit", "JUPITER"),
    ],
)
def test_driver_key_matches_frozen_family_parity(family: str, expected_driver: str) -> None:
    result = build_canonical_unit(fact(technique_family=family), CANON)
    assert result.unit is not None
    assert result.unit.driver_key == expected_driver


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (fact(aspect_type="QUINTILE"), ExclusionReason.UNKNOWN_ASPECT),
        (fact(aspect_type="QUINCUNX"), ExclusionReason.ASPECT_BELOW_THRESHOLD),
        (fact(orb=3.5001), ExclusionReason.ORB_RATIO_EXCEEDED),
        (fact(orb=-1.0), ExclusionReason.INVALID_ORB),
        (fact(orb=nan), ExclusionReason.INVALID_ORB),
        (fact(source_key="Transit_CERES"), ExclusionReason.UNKNOWN_SOURCE_ORB),
        (fact(orb=None), ExclusionReason.INVALID_ORB),
        (fact(target_type="house", house=None), ExclusionReason.INVALID_HOUSE),
        (fact(target_type="unknown_target"), ExclusionReason.UNKNOWN_TARGET_TYPE),
        (fact(source_key="CERES", target_key="UNKNOWN", technical_spheres=()), ExclusionReason.UNMAPPED_FACTOR),
        (fact(data_quality=""), ExclusionReason.INVALID_DATA_QUALITY),
        (fact(data_quality="invalid"), ExclusionReason.INVALID_DATA_QUALITY),
        (fact(birth_time_robustness="unstable"), ExclusionReason.INVALID_BIRTH_TIME_ROBUSTNESS),
        (fact(provenance_ids=42), ExclusionReason.INVALID_PROVENANCE),
        (fact(technical_spheres=42), ExclusionReason.INVALID_TECHNICAL_SPHERES),
        (fact(technical_spheres=("work_status_achievement", 42)), ExclusionReason.INVALID_TECHNICAL_SPHERES),
    ],
)
def test_malformed_facts_return_typed_fail_closed_results(raw: RawPhysicalFact, reason: ExclusionReason) -> None:
    assert_excluded(raw, reason)


@pytest.mark.parametrize(
    ("event_class", "expected_rare"),
    [
        ("timelord_period_change", True),
        ("lunar_return", False),
        ("monthly_profection", False),
        ("structural_lunar_event", False),
    ],
)
def test_non_aspect_event_class_policy_has_no_structural_auto_pass(event_class: str, expected_rare: bool) -> None:
    result = build_canonical_unit(
        fact(
            aspect_type=None,
            event_class=event_class,
            source_key=None,
            target_key="Natal_SATURN",
            technique="period_change",
            technique_family="firdar",
        ),
        CANON,
    )
    if event_class == "structural_lunar_event":
        assert result.exclusion_reason == ExclusionReason.UNKNOWN_EVENT_CLASS
        assert result.unit is None
    else:
        assert result.unit is not None
        assert result.unit.rare_anchor_eligible is expected_rare


def test_background_is_audit_unit_but_never_publicly_eligible() -> None:
    result = build_canonical_unit(fact(temporal_role="background"), CANON)
    assert result.unit is not None
    assert result.unit.exclusion_reason == ExclusionReason.BACKGROUND
    assert result.unit.impulse_eligible is False
    assert result.unit.evidence_eligible is False
    assert result.unit.rare_anchor_eligible is False
    assert result.unit.hero_confirmation_eligible is False


def test_fast_slow_and_sun_mars_eligibility_nesting() -> None:
    moon = build_canonical_unit(fact(source_key="Transit_MOON"), CANON).unit
    jupiter = build_canonical_unit(fact(source_key="Transit_JUPITER"), CANON).unit
    mars = build_canonical_unit(fact(source_key="Transit_MARS", orb=3.0), CANON).unit
    sun = build_canonical_unit(fact(source_key="Transit_SUN"), CANON).unit
    assert moon is not None and jupiter is not None and mars is not None and sun is not None
    assert (moon.impulse_eligible, moon.evidence_eligible, moon.rare_anchor_eligible, moon.hero_confirmation_eligible) == (True, True, False, False)
    assert jupiter.rare_anchor_eligible is True
    assert jupiter.evidence_eligible is True
    assert jupiter.impulse_eligible is True
    assert mars.hero_confirmation_eligible is True
    assert mars.rare_anchor_eligible is False
    assert sun.hero_confirmation_eligible is True
    assert sun.rare_anchor_eligible is False
    for unit in (moon, jupiter, mars, sun):
        assert (not unit.rare_anchor_eligible) or unit.evidence_eligible
        assert (not unit.evidence_eligible) or unit.impulse_eligible
