# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_PIPELINE — end-to-end W2 orchestration tests.
# ROLE: Proves the pure canon-to-presentation pipeline and fixed-probe parity.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-PIPELINE
# purpose: Validate deterministic composition of the accepted W2 convergence stages.
# owns:
#   - apps/api/tests/test_today_convergence_pipeline.py
# inputs: RawPhysicalFact sequences, frozen canon, and the committed probe fixture.
# outputs: pytest assertions for built/unavailable pipeline records and mutation parity.
# dependencies: app.services.today_convergence_pipeline and accepted W2 stage services.
# side_effects: none.
# emitted_logs: none.
# invariants: orchestration is pure, immutable, fail-closed at typed stage boundaries, and deterministic.
# failure_policy: pytest failure on stage routing, projection drift, mutation parity, or alias exposure.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-PIPELINE

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-PIPELINE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - ORCHESTRATION: stage composition and tone rebind invariants.
#   - FAILURE_BOUNDARIES: typed unavailable stages and ordinary row exclusions.
#   - FIXED_PROBE: literal projection and serialization digest parity.
#   - MUTATIONS: end-to-end mutation fixtures one through six.
#   - IMMUTABILITY: frozen records and absence of compatibility aliases.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-PIPELINE

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timezone
from itertools import permutations
from pathlib import Path

import pytest

from app.services import today_convergence_pipeline as pipeline_module
from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_groups import build_canonical_groups
from app.services.today_convergence_ledger import build_canonical_ledger
from app.services.today_convergence_pipeline import (
    CanonicalPipelineBuilt,
    CanonicalPipelineUnavailable,
    run_canonical_today_pipeline,
)
from app.services.today_convergence_selection import select_canonical_presentation
from app.services.today_convergence_tone import compute_canonical_tone
from app.services.today_convergence_units import RawPhysicalFact, build_canonical_unit


CANON = load_today_convergence_canon()
TARGET_DATE = date(2026, 7, 31)
UTC_NOON = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / "fixtures" / "today_convergence_pipeline_probe.v1.json"


def fact(**overrides) -> RawPhysicalFact:
    values = {
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "source_key": "Transit_JUPITER",
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


def unit_for(raw: RawPhysicalFact):
    result = build_canonical_unit(raw, CANON)
    assert result.unit is not None
    return result.unit


def direct_records(*rows: RawPhysicalFact, timezone_name: str = "UTC", delta_keys=None):
    ledger = build_canonical_ledger(list(rows), CANON, delta_keys)
    grouping = build_canonical_groups(ledger, CANON)
    provisional = compute_canonical_tone(ledger, grouping, TARGET_DATE, timezone_name, (), CANON)
    selection = select_canonical_presentation(
        ledger, grouping, provisional, TARGET_DATE, timezone_name, CANON
    )
    final = compute_canonical_tone(
        ledger, grouping, TARGET_DATE, timezone_name, selection.selected_unit_ids, CANON
    )
    return ledger, grouping, provisional, selection, final


def projection(result: CanonicalPipelineBuilt) -> dict:
    return {
        "formula_version": result.formula_version,
        "state": result.state,
        "ledger": {
            "event_ids": [unit.canonical_event_id for unit in result.ledger.units],
            "audit": {
                "raw_fact_count": result.ledger.audit.raw_fact_count,
                "accepted_fact_count": result.ledger.audit.accepted_fact_count,
                "canonical_unit_count": result.ledger.audit.canonical_unit_count,
                "duplicate_fact_count": result.ledger.audit.duplicate_fact_count,
                "delta_upgraded_count": result.ledger.audit.delta_upgraded_count,
                "excluded_by_reason": [list(item) for item in result.ledger.audit.excluded_by_reason],
            },
        },
        "groups": [
            {
                "group_id": group.group_id,
                "member_ids": [unit.canonical_event_id for unit in group.member_units],
                "hero_eligible": group.hero_eligible,
                "hero_anchor_id": group.hero_anchor_id,
                "hero_confirmation_id": group.hero_confirmation_id,
                "evidence_level": group.evidence_level,
                "primary_sphere": group.primary_sphere,
                "secondary_sphere": group.secondary_sphere,
            }
            for group in result.grouping.groups
        ],
        "tone": {
            "policy_version": result.tone.tone_policy_version,
            "day_tone": result.tone.day_tone,
            "selected_unit_ids": list(result.tone.audit.selected_unit_ids),
        },
        "selection": {
            "state": result.selection.state,
            "selected_unit_ids": list(result.selection.selected_unit_ids),
            "selected_spheres": list(result.selection.selected_spheres),
            "main_event_id": None if result.selection.main_event is None else result.selection.main_event.unit.canonical_event_id,
            "impulse_ids": [event.unit.canonical_event_id for event in result.selection.impulses],
            "convergence_evidence_ids": [
                list(convergence.evidence_event_ids) for convergence in result.selection.convergences
            ],
            "audit": {
                "candidate_convergence_count": result.selection.audit.candidate_convergence_count,
                "candidate_event_count": result.selection.audit.candidate_event_count,
                "selected_event_count": result.selection.audit.selected_event_count,
                "steady_exclusion_count": result.selection.audit.steady_exclusion_count,
                "sphere_cap_exclusion_count": result.selection.audit.sphere_cap_exclusion_count,
            },
        },
    }


def load_probe() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def parse_probe_fact(raw: dict, defaults: dict) -> RawPhysicalFact:
    values = dict(defaults)
    values.update(raw)
    for key in ("exact_at", "active_from", "active_until"):
        value = values[key]
        if value is None:
            continue
        if "T" in value:
            values[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            values[key] = date.fromisoformat(value)
    values["technical_spheres"] = tuple(values["technical_spheres"])
    values["provenance_ids"] = tuple(values["provenance_ids"])
    return RawPhysicalFact(**values)


# START_BLOCK: ORCHESTRATION
def test_built_result_matches_direct_stage_composition_and_tone_rebind() -> None:
    anchor = fact(source_key="Transit_JUPITER")
    confirmation = fact(
        source_key="Transit_SATURN",
        aspect_type="TRINE",
        temporal_role="supporting",
    )
    direct = direct_records(anchor, confirmation)
    result = run_canonical_today_pipeline([anchor, confirmation], TARGET_DATE, "UTC", canon=CANON)

    assert isinstance(result, CanonicalPipelineBuilt)
    assert result.ledger == direct[0]
    assert result.grouping == direct[1]
    assert result.selection == direct[3]
    assert result.tone == direct[4]
    assert result.tone.audit.selected_unit_ids == result.selection.selected_unit_ids
    assert result.tone.day_tone == direct[2].day_tone == direct[4].day_tone
    assert result.tone.group_tones == direct[2].group_tones == direct[4].group_tones
    assert result.formula_version == CANON.formula_version


def test_input_and_provenance_permutations_are_equal() -> None:
    rows = (
        fact(source_key="Transit_JUPITER", provenance_ids=("z", "a")),
        fact(source_key="Transit_SATURN", aspect_type="TRINE", temporal_role="supporting", provenance_ids=("b",)),
    )
    results = [run_canonical_today_pipeline(order, TARGET_DATE, "UTC", canon=CANON) for order in permutations(rows)]

    assert all(result == results[0] for result in results)


def test_empty_input_is_built_quiet_steady_without_selected_events() -> None:
    result = run_canonical_today_pipeline([], TARGET_DATE, "UTC", canon=CANON)

    assert isinstance(result, CanonicalPipelineBuilt)
    assert result.state == "quiet_day"
    assert result.tone.day_tone == "steady"
    assert result.selection.selected_unit_ids == ()
    assert result.selection.main_event is None
    assert result.selection.impulses == ()


def test_exact_delta_keys_upgrade_only_matching_unit() -> None:
    matching = fact(source_key="Transit_MARS", temporal_role="supporting")
    bare_planet = fact(source_key="Transit_VENUS", temporal_role="supporting")
    matching_key = unit_for(matching).semantic_key

    result = run_canonical_today_pipeline(
        [matching, bare_planet],
        TARGET_DATE,
        "UTC",
        delta_trigger_semantic_keys=(matching_key, "VENUS"),
        canon=CANON,
    )

    assert isinstance(result, CanonicalPipelineBuilt)
    by_source = {unit.source_key: unit for unit in result.ledger.units}
    assert by_source["MARS"].temporal_role == "anchor_today"
    assert by_source["VENUS"].temporal_role == "supporting"
    assert result.ledger.audit.delta_upgraded_count == 1
    assert result.ledger.audit.unmatched_delta_trigger_count == 1


# END_BLOCK: ORCHESTRATION


# START_BLOCK: FAILURE_BOUNDARIES
def test_invalid_timezone_is_unavailable_at_tone_with_typed_reason() -> None:
    result = run_canonical_today_pipeline([], TARGET_DATE, "Not/AZone", canon=CANON)

    assert isinstance(result, CanonicalPipelineUnavailable)
    assert result.failure_stage == "tone"
    assert result.failure_reason == "today_convergence_tone:invalid_timezone"
    assert result.ledger is not None
    assert result.grouping is not None
    assert result.tone is None


def test_steady_only_hero_is_unavailable_at_selection() -> None:
    result = run_canonical_today_pipeline(
        [
            fact(source_key="Transit_JUPITER", polarity="neutral"),
            fact(source_key="Transit_SATURN", polarity="neutral", aspect_type="TRINE", temporal_role="supporting"),
        ],
        TARGET_DATE,
        "UTC",
        canon=CANON,
    )

    assert isinstance(result, CanonicalPipelineUnavailable)
    assert result.failure_stage == "selection"
    assert result.failure_reason == "today_convergence_selection:hero_without_public_polarity"
    assert result.ledger is not None
    assert result.grouping is not None
    assert result.tone is not None


def test_ordinary_excluded_rows_remain_a_built_quiet_day() -> None:
    result = run_canonical_today_pipeline(
        [fact(aspect_type="unknown")], TARGET_DATE, "UTC", canon=CANON
    )

    assert isinstance(result, CanonicalPipelineBuilt)
    assert result.state == "quiet_day"
    assert result.ledger.units == ()
    assert result.ledger.audit.excluded_by_reason == (("unknown_aspect", 1),)


def test_exact_robust_bucket_unknown_and_time_sensitive_audit_rows() -> None:
    exact = fact(source_key="Transit_JUPITER", birth_time_mode="exact", birth_time_robustness="robust")
    bucket = fact(source_key="Transit_SATURN", birth_time_mode="bucket", birth_time_robustness="robust", aspect_type="TRINE")
    unknown = fact(source_key="Transit_MARS", birth_time_mode="unknown", birth_time_robustness="robust", aspect_type="OPPOSITION")
    sensitive = fact(source_key="Transit_VENUS", birth_time_mode="bucket", birth_time_robustness="time_sensitive", aspect_type="TRINE")

    result = run_canonical_today_pipeline([exact, bucket, unknown, sensitive], TARGET_DATE, "UTC", canon=CANON)

    assert isinstance(result, CanonicalPipelineBuilt)
    by_source = {unit.source_key: unit for unit in result.ledger.units}
    assert by_source["JUPITER"].evidence_eligible is True
    assert by_source["SATURN"].evidence_eligible is True
    assert by_source["MARS"].evidence_eligible is True
    assert by_source["VENUS"].evidence_eligible is False
    assert by_source["VENUS"].exclusion_reason.value == "time_sensitive_birth_time"


def test_invalid_canon_object_returns_typed_canon_unavailable() -> None:
    result = run_canonical_today_pipeline([], TARGET_DATE, "UTC", canon=object())  # type: ignore[arg-type]

    assert isinstance(result, CanonicalPipelineUnavailable)
    assert result.failure_stage == "canon"
    assert result.failure_reason == "today_convergence_canon:invalid_type"
    assert result.formula_version is None
    assert result.ledger is None
    assert result.grouping is None
    assert result.tone is None


def test_invalid_raw_facts_collection_returns_typed_ledger_unavailable() -> None:
    result = run_canonical_today_pipeline("not-a-sequence", TARGET_DATE, "UTC", canon=CANON)  # type: ignore[arg-type]

    assert isinstance(result, CanonicalPipelineUnavailable)
    assert result.failure_stage == "ledger"
    assert result.failure_reason == "raw_facts must be a sequence"
    assert result.formula_version == CANON.formula_version
    assert result.ledger is None
    assert result.grouping is None
    assert result.tone is None


def test_tone_rebind_dependency_returns_changed_final_tone_record(monkeypatch) -> None:
    real_compute = pipeline_module.compute_canonical_tone
    calls = 0

    def compute_with_changed_rebind(*args, **kwargs):
        nonlocal calls
        calls += 1
        real_result = real_compute(*args, **kwargs)
        if calls == 2:
            return replace(real_result, day_tone="supportive")
        return real_result

    monkeypatch.setattr(pipeline_module, "compute_canonical_tone", compute_with_changed_rebind)

    result = pipeline_module.run_canonical_today_pipeline([], TARGET_DATE, "UTC", canon=CANON)

    assert calls == 2
    assert isinstance(result, CanonicalPipelineUnavailable)
    assert result.failure_stage == "tone_rebind"
    assert result.failure_reason == "today_convergence_pipeline:tone_selection_dependency"
    assert result.tone is not None
    assert result.tone.day_tone == "supportive"


# END_BLOCK: FAILURE_BOUNDARIES


# START_BLOCK: FIXED_PROBE
def test_fixed_probe_projection_and_sha_are_literal() -> None:
    fixture = load_probe()
    assert fixture["schema_version"] == "today_convergence_pipeline_probe.v1"
    probe_encoded = json.dumps(
        [case["expected"] for case in fixture["cases"]],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert hashlib.sha256(probe_encoded).hexdigest() == fixture["probe_sha256"]

    for case in fixture["cases"]:
        rows = [parse_probe_fact(raw, fixture["raw_defaults"]) for raw in case["raw_facts"]]
        probe_date = date.fromisoformat(fixture["target_date"])
        result = run_canonical_today_pipeline(rows, probe_date, case["timezone"], canon=CANON)
        assert isinstance(result, CanonicalPipelineBuilt), case["name"]
        actual = projection(result)
        assert actual == case["expected"], case["name"]
        encoded = json.dumps(actual, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(encoded).hexdigest() == case["expected_sha256"], case["name"]


# END_BLOCK: FIXED_PROBE


# START_BLOCK: MUTATIONS
def test_mutation_1_two_ordinary_lunar_aspects_one_target_are_not_hero() -> None:
    result = run_canonical_today_pipeline(
        [
            fact(source_key="Transit_MOON"),
            fact(source_key="Transit_MOON", aspect_type="TRINE", temporal_role="supporting"),
        ],
        TARGET_DATE,
        "UTC",
        canon=CANON,
    )

    assert isinstance(result, CanonicalPipelineBuilt)
    assert result.state == "quiet_day"
    assert result.grouping.audit.hero_count == 0


def test_mutation_2_same_physical_fact_from_two_producers_is_one_unit() -> None:
    activation = fact(producer="activation", provenance_ids=("activation",))
    signal = fact(producer="day_signal", provenance_ids=("day-signal",))
    result = run_canonical_today_pipeline([signal, activation], TARGET_DATE, "UTC", canon=CANON)

    assert isinstance(result, CanonicalPipelineBuilt)
    assert len(result.ledger.units) == 1
    assert result.ledger.audit.duplicate_fact_count == 1


def test_mutation_3_edge_orb_is_excluded_noise() -> None:
    result = run_canonical_today_pipeline(
        [fact(orb=100.0)], TARGET_DATE, "UTC", canon=CANON
    )

    assert isinstance(result, CanonicalPipelineBuilt)
    assert result.ledger.units == ()
    assert result.ledger.audit.excluded_by_reason == (("orb_ratio_exceeded", 1),)


def test_mutation_4_two_independent_units_need_rare_anchor_for_hero() -> None:
    hero = run_canonical_today_pipeline(
        [
            fact(source_key="Transit_JUPITER"),
            fact(source_key="Transit_SATURN", aspect_type="TRINE", temporal_role="supporting"),
        ],
        TARGET_DATE,
        "UTC",
        canon=CANON,
    )
    no_rare = run_canonical_today_pipeline(
        [
            fact(source_key="Transit_MOON"),
            fact(source_key="Transit_MARS", aspect_type="TRINE", temporal_role="supporting"),
        ],
        TARGET_DATE,
        "UTC",
        canon=CANON,
    )

    assert isinstance(hero, CanonicalPipelineBuilt)
    assert isinstance(no_rare, CanonicalPipelineBuilt)
    assert hero.state == "convergence_today"
    assert no_rare.state == "quiet_day"


def test_mutation_5_a_b_c_does_not_create_transitive_group() -> None:
    result = run_canonical_today_pipeline(
        [
            fact(source_key="Transit_JUPITER", target_key="Natal_SATURN"),
            fact(source_key="Transit_MOON", target_key="Natal_MERCURY", aspect_type="TRINE", temporal_role="supporting"),
            fact(source_key="Transit_MERCURY", target_key="Natal_MERCURY", aspect_type="OPPOSITION", technical_spheres=("thinking_speech_learning",), temporal_role="supporting"),
        ],
        TARGET_DATE,
        "UTC",
        canon=CANON,
    )

    assert isinstance(result, CanonicalPipelineBuilt)
    assert len(result.grouping.groups) == 1
    assert {unit.source_key for unit in result.grouping.groups[0].member_units} == {"JUPITER", "MOON"}


def test_mutation_6_single_rare_anchor_is_quiet_main_event() -> None:
    row = fact(source_key="Transit_JUPITER")
    result = run_canonical_today_pipeline([row], TARGET_DATE, "UTC", canon=CANON)

    assert isinstance(result, CanonicalPipelineBuilt)
    assert result.state == "quiet_day"
    assert result.selection.main_event is not None
    assert result.selection.main_event.unit.canonical_event_id == unit_for(row).canonical_event_id


def test_background_and_fast_factor_do_not_create_groups_or_day_tone() -> None:
    background = run_canonical_today_pipeline(
        [fact(source_key="Transit_JUPITER", temporal_role="background")], TARGET_DATE, "UTC", canon=CANON
    )
    fast = run_canonical_today_pipeline(
        [fact(source_key="Transit_MOON", polarity="tense")], TARGET_DATE, "UTC", canon=CANON
    )

    assert isinstance(background, CanonicalPipelineBuilt)
    assert isinstance(fast, CanonicalPipelineBuilt)
    assert background.grouping.groups == ()
    assert background.tone.day_tone == "steady"
    assert fast.grouping.groups == ()
    assert fast.tone.day_tone == "steady"


# END_BLOCK: MUTATIONS


# START_BLOCK: IMMUTABILITY
def test_pipeline_records_are_frozen_and_have_no_legacy_aliases() -> None:
    result = run_canonical_today_pipeline([], TARGET_DATE, "UTC", canon=CANON)
    assert isinstance(result, CanonicalPipelineBuilt)

    with pytest.raises(FrozenInstanceError):
        result.state = "quiet_day"  # type: ignore[misc]
    assert not hasattr(result, "groups")
    assert not hasattr(result, "selection_result")
    assert not hasattr(result, "tone_result")


# END_BLOCK: IMMUTABILITY
