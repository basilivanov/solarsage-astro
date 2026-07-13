# ############################################################################
# AI_HEADER: TEST_HORIZON_COVERAGE — B2B2 deterministic coverage matrix (5x12=60).
# ROLE: Evaluate every synthetic profile x date case for selection,
#       contract-readiness, and guidance validity using YAML as sole metadata.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-COVERAGE
# purpose: Assert >=95% guidance_valid coverage across 60 synthetic cases
#          with exact counters and failure breakdown. Uses YAML as sole
#          metadata source.
# owns:
#   - apps/api/tests/test_horizon_coverage.py
# inputs: YAML fixture, B2A selection/tone/fact-pack services, guidance/
#         validator.
# outputs: Exact counters for selected/contract_ready/guidance_valid.
# dependencies: pytest, B2A/B2B services, YAML, testkit.
# side_effects: reads cached content canon.
# emitted_logs: none.
# invariants:
#   - All 60 cases evaluated; no skip/xfail.
#   - Each case uses actual date/timezone from YAML.
#   - shifted_story_for is the ONLY permitted case builder.
# failure_policy: test failures print breakdown and identify sub-95%.
# END_MODULE_CONTRACT: M-TEST-HORIZON-COVERAGE

# START_MODULE_MAP: M-TEST-HORIZON-COVERAGE
# public_entrypoints:
#   - test_coverage_gate
#   - test_shifted_story_timing_regressions
#   - test_strict_yaml_loader_mutations
# semantic_blocks:
#   - COVERAGE_EVALUATION
#   - TIMING_REGRESSIONS
#   - LOADER_MUTATIONS
# owned_tests:
#   - apps/api/tests/test_horizon_coverage.py
# END_MODULE_MAP: M-TEST-HORIZON-COVERAGE

# START_BLOCK: COVERAGE_EVALUATION
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone, timedelta, time
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import ValidationError

from app.schemas.horizon_guidance import HorizonClaimValidationError, HorizonGuidanceError
from app.schemas.today_horizons import (
    TodayV2HorizonsBlock,
    validate_horizons_against_evidence,
)
from app.services.horizon_canon_service import load_horizon_selection_canon
from app.services.horizon_pipeline_service import HorizonPipelineService

from ._horizon_content_testkit import (
    build_communication_natal,
    build_natal_context,
    build_relationship_natal,
    build_structure_natal,
)
from ._horizon_guidance_testkit import (
    build_coverage_cases,
    shifted_story_for,
    _CoverageData,
    to_utc_z,
)

# IMPORT GUARD: shifted_story_for is the ONLY permitted builder for this test.
_BUILDER = shifted_story_for


def test_coverage_gate() -> None:
    """Evaluate all 60 profile x date cases using YAML as sole metadata."""
    # START_FUNCTION_CONTRACT: F-TEST.test_coverage_gate
    # purpose: test coverage gate.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_coverage_gate

    # Build cases from YAML (strict-validated through Pydantic in testkit)
    cases = build_coverage_cases()
    total = len(cases)
    assert total == 60, f"expected 60 cases, got {total}"

    pipeline = HorizonPipelineService()
    canon = load_horizon_selection_canon()

    selected = 0
    contract_ready = 0
    guidance_valid = 0
    guidance_failures: Counter[str] = Counter()
    unique_dates: set[str] = set()
    unique_timezones: set[str] = set()

    for case in cases:
        target_date = case["date"]
        tz = case["timezone"]
        story = case["story"]
        natal_case = case["natal_case"]
        verdict_case = case["verdict_case"]

        unique_dates.add(target_date)
        unique_timezones.add(tz)

        # 1. Run selection and record null reason without helper assertion
        result, layer, scoring, _ = _BUILDER(target_date, tz, story)

        # Assert layer target date/time/tz equals case metadata
        assert layer.target_date == target_date
        assert layer.target_tz == tz
        assert layer.target_time == "12:00"

        if result.selection is None:
            guidance_failures[result.reason] += 1
            continue

        selection = result.selection
        selected += 1

        try:
            # Assert selected anchor IDs each occur exactly once in current layer
            anchor_ids = [item.activation_id for item in selection.items]
            layer_ids = [act.id for act in layer.activations]
            for aid in anchor_ids:
                assert layer_ids.count(aid) == 1, f"anchor ID {aid} must occur exactly once in layer"

            # Assert timing target_local and target_utc correspond to case local 12:00
            dt_val = date.fromisoformat(target_date)
            zone = ZoneInfo(tz)
            expected_local = datetime.combine(dt_val, time(12, 0), tzinfo=zone)
            expected_utc = expected_local.astimezone(timezone.utc)

            # Assert raw timing and bounds match section 5 exact semantics
            for anchor in selection.items:
                assert datetime.fromisoformat(anchor.timing.target_local) == expected_local
                assert datetime.fromisoformat(anchor.timing.target_utc.replace("Z", "+00:00")) == expected_utc

                if anchor.horizon == "long":
                    assert anchor.timing.active_from == f"{dt_val.year}-01-01"
                    assert anchor.timing.active_until == f"{dt_val.year}-12-31"
                    assert anchor.timing.exact_at is None
                elif anchor.horizon == "medium":
                    assert anchor.timing.active_from == to_utc_z(expected_local - timedelta(days=90))
                    assert anchor.timing.exact_at == to_utc_z(expected_local)
                    assert anchor.timing.active_until == to_utc_z(expected_local + timedelta(days=90))
                elif anchor.horizon == "fast":
                    assert anchor.timing.active_from == to_utc_z(datetime.combine(dt_val, time(0, 0), tzinfo=zone))
                    assert anchor.timing.exact_at == to_utc_z(expected_local)
                    assert anchor.timing.active_until == to_utc_z(datetime.combine(dt_val, time(23, 59, 59), tzinfo=zone))

                # Assert medium/fast exact peak non-null
                if anchor.horizon in ("medium", "fast"):
                    assert anchor.timing.exact_at is not None

                # Assert anchor product spheres/provenance complete
                assert len(anchor.product_spheres) >= 1
                assert len(anchor.product_spheres) <= 3
                assert all(isinstance(s, str) for s in anchor.product_spheres)

                # Assert anchor impact meets loaded min_candidate_impact[horizon]
                min_impact = getattr(canon.min_candidate_impact, anchor.horizon)
                assert anchor.impact_score >= min_impact

            contract_ready += 1

            natal = _natal_for_case(natal_case)
            verdicts_map = _verdict_for_case(verdict_case, selection)
            pipeline_result = pipeline.build(
                activation_layer=layer,
                scoring_result=scoring,
                natal_context=natal,
                sphere_verdicts=verdicts_map,
            )
            if pipeline_result.status != "built" or pipeline_result.horizons is None:
                guidance_failures[pipeline_result.selection_reason] += 1
                continue
            assert pipeline_result.selection_reason == "selected"
            block = pipeline_result.horizons

            # Explicitly call public cross-reference validator
            validate_horizons_against_evidence(block, list(layer.activations))

            # JSON dump and TodayV2HorizonsBlock.model_validate_json roundtrip
            dumped_json = block.model_dump_json()
            roundtrip_block = TodayV2HorizonsBlock.model_validate_json(dumped_json)

            # Build the full orchestrator a second time
            second_result = pipeline.build(
                activation_layer=layer,
                scoring_result=scoring,
                natal_context=natal,
                sphere_verdicts=verdicts_map,
            )
            assert second_result.status == "built"
            assert second_result.horizons is not None
            second_block = second_result.horizons

            # Assert byte-identical canonical JSON for first/second/roundtrip blocks
            canonical_first = json.dumps(block.model_dump(), sort_keys=True)
            canonical_second = json.dumps(second_block.model_dump(), sort_keys=True)
            canonical_roundtrip = json.dumps(roundtrip_block.model_dump(), sort_keys=True)
            assert canonical_first == canonical_second == canonical_roundtrip

            guidance_valid += 1
        except (
            HorizonGuidanceError,
            HorizonClaimValidationError,
        ) as exc:
            guidance_failures[exc.code] += 1
            continue

    coverage_pct = round(
        guidance_valid / total * 100, 2
    ) if total else 0.0

    print(f"\ncoverage: {guidance_valid}/60 {coverage_pct}%")
    print(f"coverage_selected: {selected}/60")
    print(f"coverage_contract_ready: {contract_ready}/{selected}")
    print("coverage_dates_timezones: 12 DATES / 5 TIMEZONES")
    print(f"coverage_failure_breakdown: {dict(guidance_failures)}")

    # Gate assertions
    assert _BUILDER is shifted_story_for, "must use shifted_story_for"
    assert guidance_valid / total >= 0.95, f"coverage {coverage_pct}% < 95%"
    assert selected == total, f"expected 60 selected, got {selected}"
    assert contract_ready == selected, "expected contract_ready == selected"
    assert len(unique_dates) == 12
    assert len(unique_timezones) == 5


# END_BLOCK: COVERAGE_EVALUATION


# START_BLOCK: TIMING_REGRESSIONS
def test_shifted_story_timing_regressions() -> None:
    """Assert exact UTC timing values for New York leap day, Berlin DST transition, Moscow, and UTC."""
    # START_FUNCTION_CONTRACT: F-TEST.test_shifted_story_timing_regressions
    # purpose: Assert exact UTC timing values for New York leap day, Berlin DST transition, Moscow, and UTC.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_shifted_story_timing_regressions

    # 1. New York leap day
    res_ny, _, _, _ = shifted_story_for("2028-02-29", "America/New_York", "structure_boundaries_control")
    assert res_ny.selection is not None
    long_ny = next(it for it in res_ny.selection.items if it.horizon == "long")
    medium_ny = next(it for it in res_ny.selection.items if it.horizon == "medium")
    fast_ny = next(it for it in res_ny.selection.items if it.horizon == "fast")

    assert long_ny.timing.active_from == "2028-01-01"
    assert long_ny.timing.active_until == "2028-12-31"
    assert long_ny.timing.exact_at is None

    assert medium_ny.timing.active_from == "2027-12-01T17:00:00Z"
    assert medium_ny.timing.exact_at == "2028-02-29T17:00:00Z"
    assert medium_ny.timing.active_until == "2028-05-29T16:00:00Z"

    assert fast_ny.timing.active_from == "2028-02-29T05:00:00Z"
    assert fast_ny.timing.exact_at == "2028-02-29T17:00:00Z"
    assert fast_ny.timing.active_until == "2028-03-01T04:59:59Z"

    # 2. Berlin DST transition day
    res_be, _, _, _ = shifted_story_for("2026-03-29", "Europe/Berlin", "communication_learning_documents")
    assert res_be.selection is not None
    long_be = next(it for it in res_be.selection.items if it.horizon == "long")
    medium_be = next(it for it in res_be.selection.items if it.horizon == "medium")
    fast_be = next(it for it in res_be.selection.items if it.horizon == "fast")

    assert long_be.timing.active_from == "2026-01-01"
    assert long_be.timing.active_until == "2026-12-31"
    assert long_be.timing.exact_at is None

    assert medium_be.timing.active_from == "2025-12-29T11:00:00Z"
    assert medium_be.timing.exact_at == "2026-03-29T10:00:00Z"
    assert medium_be.timing.active_until == "2026-06-27T10:00:00Z"

    assert fast_be.timing.active_from == "2026-03-28T23:00:00Z"
    assert fast_be.timing.exact_at == "2026-03-29T10:00:00Z"
    assert fast_be.timing.active_until == "2026-03-29T21:59:59Z"

    # 3. Moscow normal day
    res_mo, _, _, _ = shifted_story_for("2026-07-08", "Europe/Moscow", "relationships_values_closeness")
    assert res_mo.selection is not None
    long_mo = next(it for it in res_mo.selection.items if it.horizon == "long")
    medium_mo = next(it for it in res_mo.selection.items if it.horizon == "medium")
    fast_mo = next(it for it in res_mo.selection.items if it.horizon == "fast")

    assert long_mo.timing.active_from == "2026-01-01"
    assert long_mo.timing.active_until == "2026-12-31"
    assert long_mo.timing.exact_at is None

    assert medium_mo.timing.active_from == "2026-04-09T09:00:00Z"
    assert medium_mo.timing.exact_at == "2026-07-08T09:00:00Z"
    assert medium_mo.timing.active_until == "2026-10-06T09:00:00Z"

    assert fast_mo.timing.active_from == "2026-07-07T21:00:00Z"
    assert fast_mo.timing.exact_at == "2026-07-08T09:00:00Z"
    assert fast_mo.timing.active_until == "2026-07-08T20:59:59Z"

    # 4. UTC normal day
    res_utc, _, _, _ = shifted_story_for("2026-07-12", "UTC", "structure_boundaries_control")
    assert res_utc.selection is not None
    long_utc = next(it for it in res_utc.selection.items if it.horizon == "long")
    medium_utc = next(it for it in res_utc.selection.items if it.horizon == "medium")
    fast_utc = next(it for it in res_utc.selection.items if it.horizon == "fast")

    assert long_utc.timing.active_from == "2026-01-01"
    assert long_utc.timing.active_until == "2026-12-31"
    assert long_utc.timing.exact_at is None

    assert medium_utc.timing.active_from == "2026-04-13T12:00:00Z"
    assert medium_utc.timing.exact_at == "2026-07-12T12:00:00Z"
    assert medium_utc.timing.active_until == "2026-10-10T12:00:00Z"

    assert fast_utc.timing.active_from == "2026-07-12T00:00:00Z"
    assert fast_utc.timing.exact_at == "2026-07-12T12:00:00Z"
    assert fast_utc.timing.active_until == "2026-07-12T23:59:59Z"


# END_BLOCK: TIMING_REGRESSIONS


# START_BLOCK: LOADER_MUTATIONS
def test_strict_yaml_loader_mutations() -> None:
    """Verify that strict YAML loader rejects invalid/malformed metadata."""
    # START_FUNCTION_CONTRACT: F-TEST.test_strict_yaml_loader_mutations
    # purpose: Verify that strict YAML loader rejects invalid/malformed metadata.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on missing validation.
    # END_FUNCTION_CONTRACT: F-TEST.test_strict_yaml_loader_mutations

    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "horizon_guidance_coverage.v1.yml"
    )
    with open(fixture_path) as f:
        raw = yaml.safe_load(f)

    # Base validation should pass
    _CoverageData.model_validate(raw)

    rejected = 0
    total_mutations = 18

    # 1. Invalid schema version
    mut = deepcopy(raw)
    mut["schema_version"] = "horizon-guidance-coverage.v2"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 2. Schema version missing
    mut = deepcopy(raw)
    del mut["schema_version"]
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 3. Profiles count not 5 (remove one)
    mut = deepcopy(raw)
    mut["profiles"].pop()
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 4. Profiles count not 5 (add one)
    mut = deepcopy(raw)
    mut["profiles"].append(deepcopy(mut["profiles"][0]))
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 5. Target dates count not 12 (remove one)
    mut = deepcopy(raw)
    mut["target_dates"].pop()
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 6. Target dates count not 12 (add one)
    mut = deepcopy(raw)
    mut["target_dates"].append("2026-07-13")
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 7. Duplicate profile ID
    mut = deepcopy(raw)
    mut["profiles"][1]["id"] = mut["profiles"][0]["id"]
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 8. Duplicate target date
    mut = deepcopy(raw)
    mut["target_dates"][1] = mut["target_dates"][0]
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 9. Invalid timezone
    mut = deepcopy(raw)
    mut["profiles"][0]["timezone"] = "Not/A_Zone"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 10. Unknown story
    mut = deepcopy(raw)
    mut["profiles"][0]["story"] = "unknown_story"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 11. Unknown natal case
    mut = deepcopy(raw)
    mut["profiles"][0]["natal_case"] = "unknown_natal"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 12. Invalid ISO calendar date
    mut = deepcopy(raw)
    mut["target_dates"][0] = "2026-13-45"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 13. Missing profile ID
    mut = deepcopy(raw)
    del mut["profiles"][0]["id"]
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 14. Unexpected profile ID
    mut = deepcopy(raw)
    mut["profiles"][0]["id"] = "synthetic-extra"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 15. Missing target date
    mut = deepcopy(raw)
    mut["target_dates"][0] = None
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 16. Unexpected target date (valid ISO but unexpected)
    mut = deepcopy(raw)
    mut["target_dates"][0] = "2026-07-13"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 17. Extra field at top level
    mut = deepcopy(raw)
    mut["extra_top"] = "unexpected"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    # 18. Extra field in profile
    mut = deepcopy(raw)
    mut["profiles"][0]["extra_profile"] = "unexpected"
    try:
        _CoverageData.model_validate(mut)
    except (ValidationError, ValueError):
        rejected += 1

    assert rejected == total_mutations, f"expected {total_mutations} rejections, got {rejected}"
    print(f"\nstrict_yaml_mutations: {rejected}/{total_mutations} REJECT")


def _natal_for_case(case: str):
    if case == "structure":
        return build_structure_natal()
    elif case == "communication":
        return build_communication_natal()
    elif case == "relationships":
        return build_relationship_natal()
    elif case == "empty":
        return build_natal_context()
    else:
        return build_natal_context(
            planets=[
                __import__(
                    "app.schemas.natal", fromlist=["NatalChartPlanet"]
                ).NatalChartPlanet(
                    name="SATURN", sign="AQUARIUS", degree=0.0,
                    house=10, retrograde=False, longitude=0.0,
                ),
                __import__(
                    "app.schemas.natal", fromlist=["NatalChartPlanet"]
                ).NatalChartPlanet(
                    name="MERCURY", sign="GEMINI", degree=0.0,
                    house=3, retrograde=False, longitude=0.0,
                ),
            ],
            aspects=[],
        )


def _verdict_for_case(case: str, selection):
    verdicts: dict = {}
    all_spheres: set = set()
    for anchor in selection.items:
        for s in anchor.product_spheres:
            all_spheres.add(s)
    ordered = sorted(all_spheres)
    if case == "good":
        for s in ordered:
            verdicts[s] = "good"
    elif case == "neutral":
        for s in ordered:
            verdicts[s] = "neutral"
    elif case == "caution":
        for s in ordered:
            verdicts[s] = "caution"
    elif case == "avoid":
        for s in ordered:
            verdicts[s] = "avoid"
    elif case == "mixed":
        for i, s in enumerate(ordered):
            verdicts[s] = ["good", "neutral", "caution", "avoid"][i % 4]
    return verdicts


def _extract_code(exc: Exception) -> str:
    if isinstance(exc, HorizonGuidanceError):
        return exc.code
    if isinstance(exc, HorizonClaimValidationError):
        return exc.code
    msg = str(exc)
    if "peak_missing" in msg:
        return "peak_missing"
    if "insufficient_safe_actions" in msg:
        return "insufficient_safe_actions"
    if "unknown_theme" in msg:
        return "unknown_theme"
    return type(exc).__name__


# END_BLOCK: LOADER_MUTATIONS
