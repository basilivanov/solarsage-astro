# ############################################################################
# AI_HEADER: TEST_TODAY-CONVERGENCE-SNAPSHOT — deterministic snapshot document tests.
# ROLE: Proves pure profile/canon/input/result document construction without
#       persistence, network, legacy Today, or public wire behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SNAPSHOT
# purpose: Validate the P3-B deterministic snapshot document boundary.
# owns:
#   - apps/api/tests/test_today_convergence_snapshot.py
# inputs: Direct profile objects, immutable runtime/pipeline records, and copied canons.
# outputs: Hash, privacy, normalization, reference, and determinism assertions.
# dependencies: today_convergence_snapshot and accepted pure W1/W2 record builders.
# side_effects: Reads canon and writes only temporary canon copies.
# emitted_logs: none.
# invariants: No database, HTTP, LLM, legacy Today, raw profile, or test-fixture imports
#   are reachable from the production snapshot builder.
# failure_policy: TodayConvergenceSnapshotError is asserted for every typed boundary.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SNAPSHOT

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SNAPSHOT
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - CANON_HASH: strict three-artifact fingerprinting.
#   - PROFILE_IDENTITY: mode-aware privacy-safe profile identity.
#   - DOCUMENT_SHAPE: normalized quiet/hero input and result documents.
#   - DETERMINISM: repeat/permutation, mutation, privacy, and fail-closed guards.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SNAPSHOT

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
from app.services.today_birth_time import BirthTimeResolution, resolve_profile_birth_time
from app.services.today_birth_time_facts import BirthTimeFactsAudit
from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_groups import build_canonical_groups
from app.services.today_convergence_ledger import build_canonical_ledger
from app.services.today_convergence_pipeline import CanonicalPipelineBuilt
from app.services.today_convergence_runtime import TodayConvergenceCalculationBuilt
from app.services.today_convergence_selection import select_canonical_presentation
from app.services.today_convergence_snapshot import (
    TodayConvergenceSnapshotDocument,
    TodayConvergenceSnapshotError,
    build_today_convergence_snapshot_document,
)
from app.services.today_convergence_tone import compute_canonical_tone
from app.services.today_convergence_units import RawPhysicalFact


CANON = load_today_convergence_canon()
TARGET_DATE = date(2026, 7, 31)
UTC_NOON = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


class SnapshotAuditMarker(Enum):
    READY = "ready"


def profile(**overrides):
    values = {
        "birthday": date(1990, 1, 15),
        "birth_time": time(14, 30),
        "birth_time_mode": "exact",
        "birth_time_bucket": None,
        "birth_lat": 55.75,
        "birth_lon": 37.61,
        "birth_tz": "Europe/Moscow",
        "current_lat": 55.76,
        "current_lon": 37.62,
        "current_tz": "UTC",
        "gender": "other",
        "user_id": "user-secret",
        "telegram_id": 123456,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


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


def pipeline_for(*rows: RawPhysicalFact) -> CanonicalPipelineBuilt:
    ledger = build_canonical_ledger(list(rows), CANON)
    grouping = build_canonical_groups(ledger, CANON)
    selected_ids = tuple(
        unit.canonical_event_id
        for unit in ledger.units
        if unit.evidence_eligible and unit.exclusion_reason is None and unit.temporal_role != "background"
    )
    tone = compute_canonical_tone(ledger, grouping, TARGET_DATE, "UTC", selected_ids, CANON)
    selection = select_canonical_presentation(ledger, grouping, tone, TARGET_DATE, "UTC", CANON)
    return CanonicalPipelineBuilt(
        formula_version=CANON.formula_version,
        state=selection.state,
        ledger=ledger,
        grouping=grouping,
        tone=tone,
        selection=selection,
    )


def calculation_for(
    profile_value,
    pipeline: CanonicalPipelineBuilt,
    *,
    resolution: BirthTimeResolution | None = None,
    artifact: str = "swieph-test-artifact",
):
    resolved = resolve_profile_birth_time(profile_value, CANON) if resolution is None else resolution
    return TodayConvergenceCalculationBuilt(
        state=pipeline.state,
        target_date=TARGET_DATE,
        target_timezone="UTC",
        target_time="12:00",
        birth_time=resolved,
        calculation_version=CALCULATION_VERSION,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
        ephemeris_artifact_id=artifact,
        facts_audit=BirthTimeFactsAudit(
            input_sample_count=len(resolved.control_times),
            input_activation_count=len(pipeline.ledger.units),
            published_fact_count=len(pipeline.ledger.units),
            excluded_by_reason=(),
        ),
        pipeline=pipeline,
    )


def document_for(profile_value=None, pipeline=None, **kwargs) -> TodayConvergenceSnapshotDocument:
    value = profile() if profile_value is None else profile_value
    selected_pipeline = pipeline_for() if pipeline is None else pipeline
    return build_today_convergence_snapshot_document(
        value,
        calculation_for(value, selected_pipeline, **kwargs),
    )


def hero_pipeline() -> CanonicalPipelineBuilt:
    return pipeline_for(
        fact(source_key="Transit_JUPITER", target_key="Natal_SATURN"),
        fact(
            source_key="Transit_SATURN",
            target_key="Natal_SATURN",
            aspect_type="TRINE",
            temporal_role="supporting",
        ),
    )


# START_BLOCK: CANON_HASH
def test_snapshot_canon_hash_is_exposed_and_document_uses_64_hex() -> None:
    document = document_for()

    assert document.target_date == TARGET_DATE
    assert document.timezone == "UTC"
    assert document.canonical_input_json["target"] == {
        "date": TARGET_DATE.isoformat(),
        "time": "12:00",
        "timezone": "UTC",
    }
    assert len(document.canon_hash) == 64
    assert document.canon_hash == document.canon_hash.lower()
    assert len(document.profile_hash) == 64
    assert len(document.input_hash) == 64


# END_BLOCK: CANON_HASH


# START_BLOCK: PROFILE_IDENTITY
@pytest.mark.parametrize(
    ("mode", "birth_time", "bucket"),
    [
        ("exact", time(14, 30), None),
        ("bucket", None, "morning"),
        ("bucket", None, "evening"),
        ("unknown", None, None),
    ],
)
def test_mode_aware_profile_identity_changes_across_modes_and_buckets(mode, birth_time, bucket) -> None:
    value = profile(birth_time_mode=mode, birth_time=birth_time, birth_time_bucket=bucket)
    document = document_for(value)

    other_values = [
        profile(),
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="morning"),
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="evening"),
        profile(birth_time_mode="unknown", birth_time=None, birth_time_bucket=None),
    ]
    other_hashes = {
        document_for(other_value).profile_hash
        for other_value in other_values
        if vars(other_value) != vars(value)
    }

    assert document.profile_hash not in other_hashes


def test_all_six_birth_time_profiles_have_distinct_hashes() -> None:
    values = [
        profile(birth_time_mode="exact", birth_time=time(14, 30), birth_time_bucket=None),
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="night"),
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="morning"),
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="day"),
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="evening"),
        profile(birth_time_mode="unknown", birth_time=None, birth_time_bucket=None),
    ]

    hashes = {document_for(value).profile_hash for value in values}

    assert len(hashes) == 6


@pytest.mark.parametrize(
    "mutation",
    [
        {"birthday": date(1990, 1, 16)},
        {"birth_time": time(14, 31)},
        {"birth_lat": 55.76},
        {"birth_lon": 37.62},
        {"birth_tz": "Asia/Tokyo"},
    ],
)
def test_relevant_birth_identity_mutations_change_profile_hash(mutation) -> None:
    baseline = document_for(profile())

    assert document_for(profile(**mutation)).profile_hash != baseline.profile_hash


def test_profile_hash_ignores_current_location_gender_and_normalizes_negative_zero() -> None:
    baseline = document_for(profile(birth_lat=0.0, birth_lon=-0.0))
    changed = document_for(
        profile(
            birth_lat=-0.0,
            birth_lon=0.0,
            current_lat=1.0,
            current_lon=2.0,
            current_tz="Asia/Tokyo",
            gender="female",
        )
    )

    assert changed.profile_hash == baseline.profile_hash


def test_profile_hash_accepts_sqlalchemy_decimal_coordinates() -> None:
    decimal_document = document_for(profile(birth_lat=Decimal("55.75"), birth_lon=Decimal("37.61")))
    float_document = document_for(profile(birth_lat=55.75, birth_lon=37.61))

    assert decimal_document.profile_hash == float_document.profile_hash


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(birth_lat=float("inf")),
        lambda value: value.update(birth_lon=float("nan")),
        lambda value: value.update(birth_tz="Not/AZone"),
    ],
)
def test_invalid_profile_identity_fails_closed_without_raw_values(mutation) -> None:
    values = vars(profile()).copy()
    mutation(values)

    with pytest.raises(TodayConvergenceSnapshotError, match=r"^today_convergence_snapshot:") as error:
        document_for(SimpleNamespace(**values))

    assert "Not/AZone" not in str(error.value)
    assert "inf" not in str(error.value)
    assert "nan" not in str(error.value)


def test_profile_and_calculation_resolution_must_match() -> None:
    value = profile()
    mismatched = resolve_profile_birth_time(
        profile(birth_time_mode="bucket", birth_time=None, birth_time_bucket="morning"), CANON
    )

    with pytest.raises(TodayConvergenceSnapshotError, match="today_convergence_snapshot:profile_resolution"):
        document_for(value, resolution=mismatched)


# END_BLOCK: PROFILE_IDENTITY


# START_BLOCK: DOCUMENT_SHAPE
def test_quiet_document_has_normalized_result_and_single_factor_pack() -> None:
    document = document_for()

    assert document.deterministic_result_json["state"] == "quiet_day"
    assert document.deterministic_result_json["selected"]["convergences"] == []
    assert document.deterministic_result_json["selected"]["main_event"] is None
    assert document.canonical_input_json["schema_version"] == "today-canonical-input.v1"
    assert document.canonical_input_json["factor_units"] == []
    assert set(document.deterministic_result_json["audit"]) == {
        "birth_time_facts", "ledger", "grouping", "tone", "selection"
    }


def test_hero_document_preserves_exact_selected_references_without_unit_duplication() -> None:
    document = document_for(pipeline=hero_pipeline())
    convergence = document.deterministic_result_json["selected"]["convergences"][0]
    factor_ids = [unit["canonical_event_id"] for unit in document.canonical_input_json["factor_units"]]

    assert document.deterministic_result_json["state"] == "convergence_today"
    assert convergence["group_id"]
    assert convergence["anchor_event_id"] in factor_ids
    assert len(convergence["evidence_event_ids"]) == 2
    assert convergence["member_event_ids"] == sorted(convergence["member_event_ids"])
    assert document.deterministic_result_json["selected"]["main_event"] is None
    assert len(factor_ids) == len(set(factor_ids)) == len(convergence["member_event_ids"])
    assert document.deterministic_result_json["selected"]["selected_unit_ids"] == sorted(
        convergence["evidence_event_ids"]
    )


def test_unselected_extra_groups_do_not_trip_selected_convergence_cap() -> None:
    pipeline = hero_pipeline()
    selected_group = pipeline.grouping.groups[0]
    extra_groups = tuple(
        replace(selected_group, group_id=f"{selected_group.group_id}:unselected:{index}")
        for index in range(3)
    )
    expanded_grouping = replace(pipeline.grouping, groups=pipeline.grouping.groups + extra_groups)

    document = document_for(pipeline=replace(pipeline, grouping=expanded_grouping))

    assert len(expanded_grouping.groups) == 4
    assert len(document.deterministic_result_json["selected"]["convergences"]) == 1
    assert document.deterministic_result_json["audit"]["selection"]["selected_convergence_count"] == 1


def test_input_hash_is_sha256_of_exact_canonical_json_bytes_and_repeat_is_identical() -> None:
    first = document_for()
    second = document_for()
    canonical_bytes = json.dumps(
        first.canonical_input_json,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    assert first == second
    assert first.input_hash == hashlib.sha256(canonical_bytes).hexdigest()


def test_identical_quiet_pipeline_unknown_to_exact_changes_hashes_without_mutation() -> None:
    pipeline = pipeline_for()
    unknown = document_for(
        profile(birth_time_mode="unknown", birth_time=None, birth_time_bucket=None),
        pipeline=pipeline,
    )
    before = json.dumps(
        {
            "canonical_input_json": unknown.canonical_input_json,
            "deterministic_result_json": unknown.deterministic_result_json,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    exact = document_for(
        profile(birth_time_mode="exact", birth_time=time(14, 30), birth_time_bucket=None),
        pipeline=pipeline,
    )
    after = json.dumps(
        {
            "canonical_input_json": unknown.canonical_input_json,
            "deterministic_result_json": unknown.deterministic_result_json,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    assert unknown.profile_hash != exact.profile_hash
    assert unknown.input_hash != exact.input_hash
    assert before == after


def test_enum_values_in_audit_are_explicitly_json_serialized() -> None:
    value = profile()
    calculation = calculation_for(value, pipeline_for())
    audited = replace(
        calculation.facts_audit,
        excluded_by_reason=((SnapshotAuditMarker.READY, 1),),
    )
    document = build_today_convergence_snapshot_document(
        value,
        replace(calculation, facts_audit=audited),
    )

    assert document.deterministic_result_json["audit"]["birth_time_facts"]["excluded_by_reason"] == [
        ["ready", 1]
    ]


def _walk_json_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_json_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json_values(item)


def test_snapshot_json_recursively_excludes_raw_profile_and_telegram_fields() -> None:
    value = profile(
        birthday=date(1901, 2, 3),
        birth_lat=12.345678,
        birth_lon=23.456789,
        birth_tz="Pacific/Apia",
        current_lat=34.56789,
        current_lon=45.6789,
        current_tz="Asia/Tokyo",
        gender="raw-gender-sentinel",
        user_id="raw-user-id-sentinel",
        telegram_id="raw-telegram-id-sentinel",
        name="raw-name-sentinel",
        first_name="raw-first-name-sentinel",
        last_name="raw-last-name-sentinel",
    )
    document = document_for(value)
    payload = {
        "canonical_input_json": document.canonical_input_json,
        "deterministic_result_json": document.deterministic_result_json,
    }
    flattened = list(_walk_json_values(payload))
    keys = {item.lower() for item in flattened if isinstance(item, str)}
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_keys = {
        "user_id",
        "telegram_id",
        "telegram",
        "tg_id",
        "tg_user_id",
        "birthday",
        "birth_lat",
        "birth_lon",
        "birth_tz",
        "current_lat",
        "current_lon",
        "current_tz",
        "gender",
        "name",
        "first_name",
        "last_name",
    }

    assert keys.isdisjoint(forbidden_keys)
    for raw_value in (
        "1901-02-03",
        "12.345678",
        "23.456789",
        "Pacific/Apia",
        "34.56789",
        "45.6789",
        "Asia/Tokyo",
        "raw-gender-sentinel",
        "raw-user-id-sentinel",
        "raw-telegram-id-sentinel",
        "raw-name-sentinel",
        "raw-first-name-sentinel",
        "raw-last-name-sentinel",
    ):
        assert raw_value not in serialized

    assert "birth_time" in keys
    assert "profile_hash" in keys


def test_non_finite_audit_record_fails_closed_before_json_document() -> None:
    value = profile()
    calculation = calculation_for(value, pipeline_for())
    malformed_audit = replace(calculation.facts_audit, input_sample_count=float("nan"))

    with pytest.raises(TodayConvergenceSnapshotError, match="today_convergence_snapshot:non_finite_value"):
        build_today_convergence_snapshot_document(
            value,
            replace(calculation, facts_audit=malformed_audit),
        )


def test_permuted_raw_input_has_identical_document_and_unknown_to_exact_does_not_mutate_old() -> None:
    rows = (
        fact(source_key="Transit_JUPITER"),
        fact(source_key="Transit_SATURN", aspect_type="TRINE", temporal_role="supporting"),
    )
    first = document_for(pipeline=pipeline_for(*rows))
    permuted = document_for(pipeline=pipeline_for(*reversed(rows)))
    old_json = json.dumps(first.canonical_input_json, sort_keys=True)
    exact = document_for(profile(birth_time_mode="exact", birth_time=time(14, 30), birth_time_bucket=None))

    assert first == permuted
    assert old_json == json.dumps(first.canonical_input_json, sort_keys=True)
    assert exact.profile_hash != document_for(profile(birth_time_mode="unknown", birth_time=None, birth_time_bucket=None)).profile_hash
    assert exact.input_hash != first.input_hash


# END_BLOCK: DOCUMENT_SHAPE


# START_BLOCK: DETERMINISM
def test_foreign_reference_version_state_nonfinite_and_impostor_fail_closed() -> None:
    quiet = pipeline_for()
    value = profile()
    foreign_selection = replace(quiet.selection, selected_unit_ids=("evt_foreign",))
    with pytest.raises(TodayConvergenceSnapshotError, match="foreign_event_reference"):
        document_for(value, replace(quiet, selection=foreign_selection))

    with pytest.raises(TodayConvergenceSnapshotError, match="state_disagreement"):
        build_today_convergence_snapshot_document(
            value,
            replace(calculation_for(value, quiet), state="convergence_today"),
        )

    with pytest.raises(TodayConvergenceSnapshotError, match="artifact_id"):
        document_for(value, artifact="")

    with pytest.raises(TodayConvergenceSnapshotError, match="runtime_calculation"):
        build_today_convergence_snapshot_document(value, SimpleNamespace())

    with pytest.raises(TodayConvergenceSnapshotError, match="today_convergence_snapshot:pipeline"):
        build_today_convergence_snapshot_document(
            value,
            replace(calculation_for(value, quiet), pipeline=SimpleNamespace()),
        )


def test_malformed_selected_convergence_polarity_and_evidence_fail_closed() -> None:
    pipeline = hero_pipeline()
    selected = pipeline.selection.convergences[0]
    invalid_polarity = replace(selected, polarity="steady")
    with pytest.raises(TodayConvergenceSnapshotError, match="selected_polarity"):
        document_for(
            pipeline=replace(
                pipeline,
                selection=replace(pipeline.selection, convergences=(invalid_polarity,)),
            )
        )

    invalid_group = replace(selected.group, evidence_level="low")
    invalid_evidence = replace(selected, group=invalid_group)
    with pytest.raises(TodayConvergenceSnapshotError, match="selected_evidence_level"):
        document_for(
            pipeline=replace(
                pipeline,
                grouping=replace(pipeline.grouping, groups=(invalid_group,)),
                selection=replace(pipeline.selection, convergences=(invalid_evidence,)),
            )
        )


def test_snapshot_source_has_no_persistence_network_llm_or_legacy_today_path() -> None:
    source = Path(__file__).resolve().parents[1].joinpath("app/services/today_convergence_snapshot.py").read_text(encoding="utf-8")

    for forbidden in (
        "sqlalchemy",
        "httpx",
        "llm",
        "today_service",
        "TodayPayload",
        "today_payloads_cache",
        "compute_profile_hash",
        "12:00",
        "moshier-only",
    ):
        assert forbidden not in source


# END_BLOCK: DETERMINISM
