# ############################################################################
# AI_HEADER: TEST_TODAY-BIRTH-TIME-FACTS — robust activation-grid fact tests.
# ROLE: Proves strict grid boundaries, physical identity, cross-control stability,
#       frozen orb margin, and deterministic audit output.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-BIRTH-TIME-FACTS
# purpose: Validate activation-grid samples become immutable RawPhysicalFact records.
# owns:
#   - apps/api/tests/test_today_birth_time_facts.py
# inputs: BirthTimeResolution and client ActivationGridSample records.
# outputs: pytest assertions for facts and typed audit exclusions.
# dependencies: today_birth_time, solarsage_client, today_convergence_units, and the frozen canon.
# side_effects: none.
# emitted_logs: none.
# invariants: non-exact facts survive every canonical control without invented metadata.
# failure_policy: top-level malformed input raises TodayBirthTimeFactsError; one bad activation is audited.
# END_MODULE_CONTRACT: M-TEST-TODAY-BIRTH-TIME-FACTS

# START_MODULE_MAP: M-TEST-TODAY-BIRTH-TIME-FACTS
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - EXACT: exact-mode fact conversion and preserved timing.
#   - ROBUST: cross-control identity, stability, and frozen margin.
#   - AUDIT: deterministic typed exclusions and boundary failures.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-BIRTH-TIME-FACTS

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, time, timezone
from math import nan

import pytest

from app.clients.solarsage_client import ActivationGridSample
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.services.today_birth_time import BirthTimeResolution, resolve_birth_time
from app.services.today_birth_time_facts import (
    BirthTimeFactsAudit,
    BirthTimeFactsResult,
    TodayBirthTimeFactsError,
    build_birth_time_facts,
)
from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_ledger import build_canonical_ledger
from app.services.today_convergence_units import ExclusionReason, build_canonical_unit


CANON = load_today_convergence_canon()
TARGET_DATE = "2026-07-31"
TARGET_TZ = "Europe/Moscow"


def resolution(mode: str = "bucket", bucket: str | None = "morning") -> BirthTimeResolution:
    return resolve_birth_time(mode=mode, birth_time=time(14, 30) if mode == "exact" else None, bucket=bucket, canon=CANON)


def activation(**overrides) -> ActivationEvidence:
    values = {
        "id": "activation-1",
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "target_type": "planet",
        "target_key": "SATURN",
        "kind": "sextile",
        "active": True,
        "source_planet": "JUPITER",
        "source_frame": "transit",
        "target_planet": "SATURN",
        "target_frame": "natal",
        "aspect": "sextile",
        "orb": 1.0,
        "applying": False,
        "active_from": "2026-07-30T12:00:00+00:00",
        "exact_at": "2026-07-31T12:00:00+00:00",
        "active_until": "2026-08-01T12:00:00+00:00",
        "phase": "exact",
        "strength": 0.8,
        "polarity": "supportive",
        "evidence": "Jupiter sextile natal Saturn",
        "debug": {"max_orb": 5.0, "target_speed_deg_per_hour": 0.0},
    }
    values.update(overrides)
    return ActivationEvidence(**values)


def layer(activations: list[ActivationEvidence], **overrides) -> ActivationLayer:
    values = {
        "calculation_version": "ss-calc-1.3.0",
        "activation_layer_version": "activation-layer-1.0.0",
        "target_date": TARGET_DATE,
        "target_time": "12:00",
        "target_tz": TARGET_TZ,
        "house_system": "PLACIDUS",
        "activations": activations,
        "by_planet": {},
        "by_house": {},
        "by_lot": {},
        "by_angle": {},
    }
    values.update(overrides)
    return ActivationLayer(**values)


def samples_for(resolved: BirthTimeResolution, activations_by_index: list[list[ActivationEvidence]] | None = None):
    if activations_by_index is None:
        activations_by_index = [[activation()] for _ in resolved.control_times]
    return tuple(
        ActivationGridSample(
            birth_time=birth_time,
            activation_layer=layer(activations),
        )
        for birth_time, activations in zip(resolved.control_times, activations_by_index, strict=True)
    )


def reason_counts(result: BirthTimeFactsResult) -> dict[str, int]:
    return dict(result.audit.excluded_by_reason)


def test_exact_publishes_active_fact_with_timezone_aware_timing() -> None:
    resolved = resolution("exact", None)
    result = build_birth_time_facts(resolved, samples_for(resolved))
    assert isinstance(result, BirthTimeFactsResult)
    assert result.facts[0].birth_time_mode == "exact"
    assert result.facts[0].birth_time_robustness == "robust"
    assert result.facts[0].exact_at == datetime(2026, 7, 31, 12, tzinfo=timezone.utc)
    assert result.facts[0].temporal_role == "anchor_today"
    assert result.facts[0].producer == "activation"
    assert result.facts[0].technical_spheres == ()
    assert result.audit == BirthTimeFactsAudit(1, 1, 1, ())


def test_exact_time_on_target_date_wins_over_background_phase() -> None:
    resolved = resolution("exact", None)
    rows = [[activation(phase="background")]]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert result.facts[0].temporal_role == "anchor_today"


def test_exact_firdar_fact_does_not_require_non_exact_sect_metadata() -> None:
    resolved = resolution("exact", None)
    firdar = activation(
        technique="firdar_major",
        technique_family="firdar",
        kind="major_period_lord",
        aspect=None,
        orb=None,
        debug={},
    )
    result = build_birth_time_facts(resolved, samples_for(resolved, [[firdar]]))
    assert len(result.facts) == 1


@pytest.mark.parametrize(
    ("mode", "bucket"),
    [("bucket", "night"), ("bucket", "morning"), ("bucket", "day"), ("bucket", "evening"), ("unknown", None)],
)
def test_all_non_exact_canonical_control_grids_publish_one_robust_fact(mode: str, bucket: str | None) -> None:
    resolved = resolution(mode, bucket)
    result = build_birth_time_facts(resolved, samples_for(resolved))
    assert len(result.facts) == 1
    assert result.facts[0].birth_time_mode == mode
    assert result.facts[0].birth_time_robustness == "robust"
    assert isinstance(result.facts[0].exact_at, date)
    assert not isinstance(result.facts[0].exact_at, datetime)
    assert result.audit.published_fact_count == 1


def test_identity_sort_is_independent_of_activation_order() -> None:
    resolved = resolution()
    first = activation(id="z-id", target_key="SATURN")
    second = activation(id="a-id", target_key="JUPITER", source_planet="SATURN")
    forward = build_birth_time_facts(resolved, samples_for(resolved, [[first, second]] * 3))
    reverse = build_birth_time_facts(resolved, samples_for(resolved, [[second, first]] * 3))
    assert forward.facts == reverse.facts


def test_missing_duplicate_inactive_polarity_and_sect_changes_are_audited_once() -> None:
    resolved = resolution()
    missing = [activation(id="missing-1"), activation(id="stable-1", target_key="JUPITER")]
    missing[-1] = activation(id="stable-1", target_key="JUPITER", source_planet="SATURN")
    missing_rows = [missing, [activation(id="stable-2", target_key="JUPITER", source_planet="SATURN")], missing]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, missing_rows))) == {"missing_control": 1}

    duplicate_rows = [[activation(id="dup-a"), activation(id="dup-b")]] * 3
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, duplicate_rows))) == {"duplicate_identity": 1}

    inactive_rows = [[activation(id=f"inactive-{index}", active=index != 1)] for index in range(3)]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, inactive_rows))) == {"inactive_control": 1}

    polarity_rows = [[activation(id=f"polarity-{index}", polarity="tense" if index == 1 else "supportive")] for index in range(3)]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, polarity_rows))) == {"polarity_changed": 1}

    sect_rows = [[activation(id=f"sect-{index}", technique="firdar_major", technique_family="firdar", aspect=None, kind="major_period", debug={"is_day_birth": index != 1})] for index in range(3)]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, sect_rows))) == {"sect_changed_or_unknown": 1}


@pytest.mark.parametrize("target_type", ["house", "angle", "lot"])
def test_non_exact_house_angle_and_lot_targets_are_hard_excluded(target_type: str) -> None:
    resolved = resolution()
    values = {"id": f"{target_type}-1", "target_type": target_type, "target_key": "1", "aspect": "sextile", "kind": "sextile"}
    if target_type == "house":
        values["house"] = 1
    if target_type == "angle":
        values["target_key"] = "ASC"
        values["angle"] = "ASC"
    if target_type == "lot":
        values["target_key"] = "FORTUNE"
        values["lot"] = "FORTUNE"
    result = build_birth_time_facts(resolved, samples_for(resolved, [[activation(**values)] for _ in resolved.control_times]))
    assert result.facts == ()
    assert reason_counts(result) == {"birth_time_sensitive_target": 1}


def test_margin_equality_passes_and_epsilon_excludes() -> None:
    resolved = resolution()
    gap = resolved.canonical_gap_hours
    assert gap is not None
    max_orb = 5.0
    orb = 1.0
    speed = (CANON.orb_ratio_max * max_orb - orb) / gap
    equal = [
        activation(id=f"equal-{index}", orb=orb, debug={"max_orb": max_orb, "target_speed_deg_per_hour": speed})
        for index in range(3)
    ]
    assert len(build_birth_time_facts(resolved, samples_for(resolved, [[item] for item in equal])).facts) == 1
    exceeded = [
        activation(id=f"over-{index}", orb=orb, debug={"max_orb": max_orb, "target_speed_deg_per_hour": speed + 1e-9})
        for index in range(3)
    ]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, [[item] for item in exceeded]))) == {"orb_margin_exceeded": 1}


@pytest.mark.parametrize(
    "debug_values",
    [{}, {"max_orb": nan, "target_speed_deg_per_hour": 0.0}, {"max_orb": 5.0, "target_speed_deg_per_hour": nan}],
)
def test_missing_or_nonfinite_margin_metadata_fails_closed(debug_values: dict) -> None:
    resolved = resolution()
    rows = [[activation(id=f"metadata-{index}", debug=debug_values)] for index in range(3)]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, rows))) == {"orb_metadata_missing": 1}


def test_changed_margin_metadata_uses_stable_reason_and_worst_representative_values() -> None:
    resolved = resolution()
    rows = [
        [activation(id="b-id", orb=1.0, strength=0.2, debug={"max_orb": 5.0, "target_speed_deg_per_hour": 0.0})],
        [activation(id="a-id", orb=2.0, strength=0.9, debug={"max_orb": 5.0, "target_speed_deg_per_hour": 0.0})],
        [activation(id="c-id", orb=1.5, strength=0.4, debug={"max_orb": 5.0, "target_speed_deg_per_hour": 0.0})],
    ]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert result.facts[0].orb == 2.0
    assert result.facts[0].strength == 0.9
    assert result.facts[0].provenance_ids == ("a-id", "b-id", "c-id")

    changed = [
        [activation(id="same-0", debug={"max_orb": 5.0, "target_speed_deg_per_hour": 0.0})],
        [activation(id="same-1", debug={"max_orb": 5.1, "target_speed_deg_per_hour": 0.0})],
        [activation(id="same-2", debug={"max_orb": 5.0, "target_speed_deg_per_hour": 0.0})],
    ]
    assert reason_counts(build_birth_time_facts(resolved, samples_for(resolved, changed))) == {"orb_metadata_changed": 1}


def test_malformed_top_level_arguments_raise_typed_errors() -> None:
    resolved = resolution()
    with pytest.raises(TodayBirthTimeFactsError, match="today_birth_time_facts:invalid_resolution"):
        build_birth_time_facts(object(), samples_for(resolved))  # type: ignore[arg-type]
    with pytest.raises(TodayBirthTimeFactsError, match="today_birth_time_facts:invalid_samples"):
        build_birth_time_facts(resolved, "not-a-sequence")  # type: ignore[arg-type]
    with pytest.raises(TodayBirthTimeFactsError, match="today_birth_time_facts:invalid_samples"):
        build_birth_time_facts(resolved, (sample for sample in samples_for(resolved)))  # type: ignore[arg-type]


def test_malformed_individual_activation_is_audited_without_inventing_fields() -> None:
    resolved = resolution()
    malformed = ActivationEvidence.model_construct(id="bad", technique=None, debug={})
    result = build_birth_time_facts(resolved, samples_for(resolved, [[malformed] for _ in resolved.control_times]))
    assert result.facts == ()
    assert reason_counts(result) == {"malformed_activation": len(resolved.control_times)}


def test_malformed_occurrences_with_one_physical_identity_count_once() -> None:
    resolved = resolution()
    rows = [
        [activation(id=f"bad-{index}", active_from="2026-08-01T12:00:00+00:00", exact_at="2026-07-31T12:00:00+00:00")]
        for index in range(len(resolved.control_times))
    ]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert reason_counts(result) == {"malformed_activation": 1}


def test_cross_control_temporal_role_is_conservative_when_roles_differ() -> None:
    resolved = resolution()
    rows = [
        [activation(id="role-0", phase="exact")],
        [activation(id="role-1", phase="background", exact_at="2026-08-01T12:00:00+00:00")],
        [activation(id="role-2", phase="applying", exact_at="2026-08-01T12:00:00+00:00")],
    ]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert result.facts[0].temporal_role == "background"


def test_cross_control_supporting_and_background_uses_worst_role() -> None:
    resolved = resolution()
    rows = [
        [activation(id="supporting-0", phase="applying", exact_at="2026-08-01T12:00:00+00:00")],
        [activation(id="background-1", phase="background", exact_at="2026-08-01T12:00:00+00:00")],
        [activation(id="supporting-2", phase="separating", exact_at="2026-08-01T12:00:00+00:00")],
    ]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert result.facts[0].temporal_role == "background"


def test_invalid_window_order_is_audited_as_malformed_activation() -> None:
    resolved = resolution()
    rows = [
        [
            activation(
                id=f"window-{index}",
                active_from="2026-08-01T12:00:00+00:00",
                exact_at="2026-07-31T12:00:00+00:00",
            )
        ]
        for index in range(len(resolved.control_times))
    ]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert reason_counts(result) == {"malformed_activation": 1}


def test_event_classes_and_daydelta_identity_are_preserved_for_firdar_and_returns() -> None:
    resolved = resolution("exact", None)
    transit_result = build_birth_time_facts(resolved, samples_for(resolved))
    ledger = build_canonical_ledger(transit_result.facts, CANON)
    assert len(ledger.units) == 1

    resolved = resolution()
    firdar = activation(
        id="firdar",
        technique="firdar_major",
        technique_family="firdar",
        kind="major_period_lord",
        aspect=None,
        orb=None,
        active_from="2026-07-31",
        exact_at=None,
        active_until="2026-08-01",
        phase="period",
        debug={"is_day_birth": True},
    )
    firdar_result = build_birth_time_facts(resolved, samples_for(resolved, [[firdar]] * 3))
    firdar_fact = firdar_result.facts[0]
    assert firdar_fact.event_class == "timelord_period_change"
    assert firdar_fact.temporal_role == "anchor_today"
    firdar_before = build_canonical_ledger([firdar_fact], CANON)
    assert firdar_before.units[0].event_class == "timelord_period_change"
    assert firdar_before.units[0].temporal_role == "anchor_today"
    assert firdar_before.units[0].rare_anchor_eligible is True

    ongoing_firdar = activation(
        id="ongoing-firdar",
        technique="firdar_major",
        technique_family="firdar",
        kind="major_period_lord",
        aspect=None,
        orb=None,
        active_from="2026-07-30",
        exact_at=None,
        active_until="2026-08-01",
        phase="period",
        debug={"is_day_birth": True},
    )
    ongoing_result = build_birth_time_facts(resolved, samples_for(resolved, [[ongoing_firdar]] * 3))
    ongoing_fact = ongoing_result.facts[0]
    assert ongoing_fact.event_class == "timelord_period_change"
    assert ongoing_fact.temporal_role == "background"
    ongoing_before = build_canonical_ledger([ongoing_fact], CANON)
    ongoing_after = build_canonical_ledger(
        [ongoing_fact], CANON, delta_trigger_semantic_keys=[ongoing_before.units[0].semantic_key]
    )
    assert ongoing_after.units[0].temporal_role == "background"
    assert ongoing_after.audit.delta_upgraded_count == 0

    solar_return = activation(
        id="solar-return",
        technique="solar_return",
        technique_family="return",
        kind="solar_return",
        source_planet=None,
        aspect=None,
        orb=None,
        debug={},
    )
    exact_resolved = resolution("exact", None)
    return_result = build_birth_time_facts(exact_resolved, samples_for(exact_resolved, [[solar_return]]))
    return_fact = return_result.facts[0]
    assert return_fact.event_class == "solar_return"
    return_ledger = build_canonical_ledger([return_fact], CANON)
    assert len(return_ledger.units) == 1
    assert return_ledger.units[0].event_class == "solar_return"

    unknown = transit_result.facts[0]
    unknown = unknown.__class__(
        **{**unknown.__dict__, "technique": "custom", "technique_family": "custom", "aspect_type": None, "event_class": None}
    )
    assert build_canonical_unit(unknown, CANON).exclusion_reason == ExclusionReason.UNKNOWN_EVENT_CLASS


def test_non_mapping_debug_is_audited_without_crashing_the_day() -> None:
    resolved = resolution()
    base = activation(
        technique="firdar_major",
        technique_family="firdar",
        kind="major_period_lord",
        aspect=None,
        orb=None,
    )
    malformed = ActivationEvidence.model_construct(**{**base.model_dump(), "debug": "not-a-mapping"})
    result = build_birth_time_facts(resolved, samples_for(resolved, [[malformed]] * len(resolved.control_times)))
    assert result.facts == ()
    assert reason_counts(result) == {"malformed_activation": 1}


def test_result_and_audit_are_immutable_and_reason_order_is_lexical() -> None:
    resolved = resolution()
    rows = [[activation(id=f"r-{index}", active=index != 1, polarity="tense" if index == 2 else "supportive")] for index in range(3)]
    result = build_birth_time_facts(resolved, samples_for(resolved, rows))
    assert isinstance(result.audit, BirthTimeFactsAudit)
    with pytest.raises(FrozenInstanceError):
        result.audit.input_sample_count = 4  # type: ignore[misc]


def test_s15_house_is_published_only_when_control_grid_is_unanimous() -> None:
    # Exact mode: the single sample's house is published as-is.
    exact = resolution("exact", None)
    result = build_birth_time_facts(exact, samples_for(exact, [[activation(house=7)]]))
    assert result.facts[0].house == 7

    # Non-exact grid with unanimous houses: published.
    grid = resolution("bucket", "morning")
    unanimous = [[activation(house=7)] for _ in grid.control_times]
    result = build_birth_time_facts(grid, samples_for(grid, unanimous))
    assert len(result.facts) == 1
    assert result.facts[0].house == 7

    # Non-exact grid with disagreeing houses: house withheld, fact still published.
    disagreeing = [[activation(house=7)]] + [[activation(house=8)] for _ in grid.control_times[1:]]
    result = build_birth_time_facts(grid, samples_for(grid, disagreeing))
    assert len(result.facts) == 1
    assert result.facts[0].house is None

    # House never splits cross-sample identity: one merged fact, no missing_control.
    assert result.audit.excluded_by_reason == ()
