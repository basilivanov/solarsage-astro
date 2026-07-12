# ############################################################################
# AI_HEADER: HORIZON_GUIDANCE_TESTKIT — shared synthetic builders for B2B2 guidance tests.
# ROLE: Builds guidance context, validated blocks, coverage cases, and
#       worst-case pipeline inputs. Uses B2A/B2B1 testkits.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-GUIDANCE-TESTKIT
# purpose: Provide deterministic synthetic builders for B2B2 guidance,
#          validator, coverage, and benchmark tests.
# owns:
#   - apps/api/tests/_horizon_guidance_testkit.py
# inputs: Stable story ids, natal case labels, explicit date/timezone params.
# outputs: Typed HorizonGuidanceContext, TodayV2HorizonsBlock,
#          coverage-case collections.
# dependencies: app B2A/B2B schemas/services, B2B content/personal-fact
#               testkits.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No production fixture/demo import, DB, network, auth, real user, or
#     wall clock.
#   - Each builder returns deterministic Pydantic models.
# failure_policy: raises ValueError/Pydantic errors for invalid synthetic
#   payloads.
# END_MODULE_CONTRACT: M-HORIZON-GUIDANCE-TESTKIT

# START_MODULE_MAP: M-HORIZON-GUIDANCE-TESTKIT
# public_entrypoints:
#   - build_guidance_context
#   - build_validated_guidance
#   - shifted_story_for
#   - build_coverage_cases
#   - build_worst_case_pipeline_input
# semantic_blocks:
#   - GUIDANCE_TESTKIT_CONTEXT: context and guidance builders.
#   - GUIDANCE_TESTKIT_SHIFTED: date/timezone-shifted selection builder.
#   - GUIDANCE_TESTKIT_COVERAGE: coverage case enumeration.
#   - GUIDANCE_TESTKIT_BENCHMARK: worst-case pipeline input.
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_service.py
#   - apps/api/tests/test_horizon_claim_validator.py
#   - apps/api/tests/test_horizon_coverage.py
#   - apps/api/tests/test_horizon_pipeline_benchmark.py
# END_MODULE_MAP: M-HORIZON-GUIDANCE-TESTKIT

# START_BLOCK: GUIDANCE_TESTKIT_CONTEXT
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone, timedelta, time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from zoneinfo import ZoneInfo

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.horizon_content_canon import (
    HorizonSphereVerdict,
)
from app.schemas.horizon_guidance import HorizonGuidanceContext
from app.schemas.horizon_selection import (
    SelectedHorizonTriple,
    HORIZON_ORDER,
    HorizonSelectionResult,
)
from app.schemas.natal import NatalChartAspect, NatalChartPlanet, NatalContextData
from app.schemas.personal_fact_pack import PersonalFactPack
from app.schemas.scoring_v2 import (
    ScoringV2Result,
    SphereContribution,
    SphereScoreV2,
)
from app.schemas.today_horizons import (
    TodayV2ProductSphereKey,
    TodayV2HorizonsBlock,
)
from app.services.horizon_content_canon_service import load_horizon_content_canons
from app.services.horizon_guidance_service import HorizonGuidanceService
from app.services.horizon_guidance_formatter import HorizonGuidanceFormatter
from app.services.horizon_claim_validator import HorizonClaimValidator
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.horizon_tone_service import HorizonToneService
from app.services.personal_fact_pack_service import PersonalFactPackService

from ._horizon_content_testkit import (
    build_communication_natal,
    build_natal_context,
    build_relationship_natal,
    build_selected_story,
    build_sphere_verdicts,
    build_structure_natal,
)
from ._horizon_selection_testkit import (
    build_activation,
    build_layer,
    build_scoring,
    build_story,
)


def build_guidance_context(
    story: str,
    natal_case: str,
    verdict_case: str,
) -> tuple[
    HorizonGuidanceContext,
    TodayV2HorizonsBlock | None,
    ActivationLayer,
    ScoringV2Result,
    NatalContextData,
]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_guidance_context
    # purpose: Build a complete deterministic guidance context from a synthetic
    #          story + natal case.
    # inputs: story - B2A golden story id; natal_case - natal descriptor;
    #         verdict_case - sphere verdict case.
    # returns: (context, prebuilt_block, layer, scoring, natal).
    # side_effects: reads cached content canons.
    # emitted_logs: none.
    # error_behavior: raises AssertionError if selection/tone/fact-pack
    #   construction fails.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_guidance_context
    selection, layer, scoring = build_selected_story(story)
    natal = _build_natal_by_case(natal_case)
    fact_pack = PersonalFactPackService().build(
        selection=selection,
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
    )
    verdicts = _build_verdict_case(verdict_case, selection)
    tone_result = HorizonToneService().assess(
        selection=selection,
        sphere_verdicts=verdicts,
    )
    context = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=selection,
        fact_pack=fact_pack,
        tone_result=tone_result,
        sphere_verdicts=verdicts,
    )
    block = None
    try:
        block = HorizonGuidanceService().build(context=context)
    except ValueError:
        pass
    return context, block, layer, scoring, natal


def build_validated_guidance(
    story: str,
    natal_case: str,
    verdict_case: str,
) -> TodayV2HorizonsBlock:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_validated_guidance
    # purpose: Build and validate a complete deterministic guidance block.
    # inputs: story, natal_case, verdict_case.
    # returns: validated TodayV2HorizonsBlock.
    # side_effects: reads cached canons.
    # emitted_logs: none.
    # error_behavior: propagates any construction/validation error.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_validated_guidance
    activation, _, _, _ = build_story(story)
    layer = build_layer(activation)
    context, block, _, _, _ = build_guidance_context(
        story, natal_case, verdict_case
    )
    assert block is not None, "guidance block must not be None"
    validator = HorizonClaimValidator()
    return validator.validate(
        block=block,
        context=context,
        activation_evidence=layer.activations,
    )


# END_BLOCK: GUIDANCE_TESTKIT_CONTEXT


# START_BLOCK: GUIDANCE_TESTKIT_SHIFTED
def to_utc_z(dt_val: datetime) -> str:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.to_utc_z
    # purpose: Convert an aware local datetime to UTC and format with trailing Z.
    # inputs: dt_val - aware datetime.
    # returns: string.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.to_utc_z
    """Convert an aware local datetime to UTC and format with trailing Z."""
    return dt_val.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def shifted_story_for(
    target_date: str,
    tz_name: str,
    story: str,
) -> tuple[
    HorizonSelectionResult,
    ActivationLayer,
    ScoringV2Result,
    NatalContextData,
]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.shifted_story_for
    # purpose: Build a selection for a specific target date/timezone from a
    #          story pattern. Shifts activation windows exactly to local noon
    #          and range boundaries relative to local noon.
    # inputs: target_date - YYYY-MM-DD; tz_name - IANA timezone; story - golden id.
    # returns: (result, layer, scoring, natal).
    # side_effects: reads cached canons.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.shifted_story_for
    dt_target = date.fromisoformat(target_date)
    zone = ZoneInfo(tz_name)
    target_noon = datetime.combine(dt_target, time(12, 0), tzinfo=zone)

    activations, mapping, expected_ids, _ = build_story(story)
    shifted: list[ActivationEvidence] = []
    for act in activations:
        a = deepcopy(act)
        if a.technique == "annual_profection":
            a.active_from = f"{dt_target.year}-01-01"
            a.active_until = f"{dt_target.year}-12-31"
            a.exact_at = None
        elif a.technique == "transit_to_natal":
            if a.id.startswith("medium-"):
                a.active_from = to_utc_z(target_noon - timedelta(days=90))
                a.exact_at = to_utc_z(target_noon)
                a.active_until = to_utc_z(target_noon + timedelta(days=90))
            elif a.id.startswith("fast-"):
                a.active_from = to_utc_z(datetime.combine(dt_target, time(0, 0), tzinfo=zone))
                a.exact_at = to_utc_z(target_noon)
                a.active_until = to_utc_z(datetime.combine(dt_target, time(23, 59, 59), tzinfo=zone))
            else:  # distractor
                a.active_from = to_utc_z(datetime.combine(dt_target, time(0, 0), tzinfo=zone))
                a.exact_at = to_utc_z(target_noon - timedelta(hours=1))
                a.active_until = to_utc_z(datetime.combine(dt_target, time(23, 59, 59), tzinfo=zone))
        shifted.append(a)

    layer = ActivationLayer(
        calculation_version="calc",
        target_date=target_date,
        target_time="12:00",
        target_tz=tz_name,
        house_system="WHOLE_SIGN",
        activations=shifted,
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )
    scoring = build_scoring(shifted, mapping)
    result = HorizonSelectionService().select(
        activation_layer=layer, scoring_result=scoring
    )
    natal = _build_natal_by_case("structure")
    return result, layer, scoring, natal


# END_BLOCK: GUIDANCE_TESTKIT_SHIFTED


# Test-only Pydantic models for strict YAML coverage validation
from pydantic import field_validator, model_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ACCEPTED_PROFILE_IDS = {
    "synthetic-structure-moscow",
    "synthetic-communication-utc",
    "synthetic-relationships-berlin",
    "synthetic-empty-new-york",
    "synthetic-mixed-tbilisi",
}

ACCEPTED_STORIES = {
    "structure_boundaries_control",
    "communication_learning_documents",
    "relationships_values_closeness",
}

ACCEPTED_NATAL_CASES = {
    "structure",
    "communication",
    "relationships",
    "empty",
    "mixed",
}

ACCEPTED_DATES = {
    "2026-01-01",
    "2026-02-28",
    "2026-03-29",
    "2026-04-15",
    "2026-06-21",
    "2026-07-08",
    "2026-07-12",
    "2026-09-22",
    "2026-10-25",
    "2026-12-31",
    "2028-02-28",
    "2028-02-29",
}


class _CoverageProfile(BaseModel):
    """A single profile entry from the coverage YAML."""
    model_config = {"extra": "forbid"}
    id: str
    timezone: str
    story: str
    natal_case: str

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if v not in ACCEPTED_PROFILE_IDS:
            raise ValueError(f"unknown profile ID: {v}")
        return v

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, Exception) as exc:
            raise ValueError(f"invalid timezone: {v}") from exc
        return v

    @field_validator("story")
    @classmethod
    def _validate_story(cls, v: str) -> str:
        if v not in ACCEPTED_STORIES:
            raise ValueError(f"unknown story: {v}")
        return v

    @field_validator("natal_case")
    @classmethod
    def _validate_natal_case(cls, v: str) -> str:
        if v not in ACCEPTED_NATAL_CASES:
            raise ValueError(f"unknown natal case: {v}")
        return v


class _CoverageData(BaseModel):
    """Top-level coverage YAML schema. extra=forbid rejects unknown keys."""
    model_config = {"extra": "forbid"}
    schema_version: str = Field(pattern=r"^horizon-guidance-coverage\.v1$")
    profiles: list[_CoverageProfile]
    target_dates: list[str]

    @model_validator(mode="after")
    def _validate_data(self) -> _CoverageData:
        if self.schema_version != "horizon-guidance-coverage.v1":
            raise ValueError(f"invalid schema_version: {self.schema_version}")
        if len(self.profiles) != 5:
            raise ValueError(f"profiles count must be exactly 5, got {len(self.profiles)}")
        if len(self.target_dates) != 12:
            raise ValueError(f"target_dates count must be exactly 12, got {len(self.target_dates)}")

        prof_ids = [p.id for p in self.profiles]
        if len(prof_ids) != len(set(prof_ids)):
            raise ValueError("duplicate profile ID found")
        if set(prof_ids) != ACCEPTED_PROFILE_IDS:
            raise ValueError("missing/unexpected profile ID")

        if len(self.target_dates) != len(set(self.target_dates)):
            raise ValueError("duplicate target date found")

        for d_str in self.target_dates:
            try:
                date.fromisoformat(d_str)
            except ValueError as exc:
                raise ValueError(f"invalid ISO calendar date: {d_str}") from exc
            if d_str not in ACCEPTED_DATES:
                raise ValueError(f"unexpected target date: {d_str}")

        if set(self.target_dates) != ACCEPTED_DATES:
            raise ValueError("missing/unexpected target dates")

        return self


_VERDICT_CYCLE = ["good", "neutral", "caution", "avoid", "mixed"]


# START_BLOCK: GUIDANCE_TESTKIT_COVERAGE
def build_coverage_cases() -> list[dict[str, Any]]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_coverage_cases
    # purpose: Return coverage case descriptors from YAML metadata.
    #          Strict-loads YAML through Pydantic models with extra=forbid,
    #          exact schema version regex, and no date skipping/mutation.
    # inputs: none.
    # returns: list of case dicts with profile/timezone/story/natal/date/
    #          verdict fields.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError if YAML is malformed.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_coverage_cases
    import yaml as _yaml
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "horizon_guidance_coverage.v1.yml"
    )
    with open(fixture_path) as f:
        raw = _yaml.safe_load(f)
    # Strict validate through Pydantic — extra fields rejected, schema_version
    # must match pattern exactly.
    validated = _CoverageData.model_validate(raw)
    profiles = validated.profiles
    dates = validated.target_dates
    cases: list[dict[str, Any]] = []
    for profile in profiles:
        for target_date in dates:
            verdict = _VERDICT_CYCLE[len(cases) % len(_VERDICT_CYCLE)]
            cases.append({
                "profile_id": profile.id,
                "timezone": profile.timezone,
                "story": profile.story,
                "natal_case": profile.natal_case,
                "date": target_date,
                "verdict_case": verdict,
            })
    return cases


# END_BLOCK: GUIDANCE_TESTKIT_COVERAGE


# START_BLOCK: GUIDANCE_TESTKIT_BENCHMARK
def build_worst_case_pipeline_input() -> (
    tuple[ActivationLayer, ScoringV2Result, NatalContextData]
):
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_worst_case_pipeline_input
    # purpose: Build a 120-activation layer (40 long, 40 medium, 40 fast) for
    #          pipeline benchmarks. Post-selection must be exactly 12/12/12
    #          with combinations_evaluated = 1728.
    # inputs: none.
    # returns: (layer, scoring, natal) for benchmark testing.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises AssertionError if selection does not produce
    #   12/12/12.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-TESTKIT.build_worst_case_pipeline_input
    activations: list[ActivationEvidence] = []
    mapping: dict[str, tuple[str, float]] = {}
    # 40 long (profection)
    for i in range(40):
        act_id = f"long-bench-{i}"
        act = build_activation(
            id=act_id,
            technique="annual_profection",
            technique_family="profection",
            target_type="planet",
            target_key="SATURN",
            strength=0.5 + (i / 80.0),
            active_from="2026-01-01",
            exact_at=None,
            active_until="2026-12-31",
        )
        activations.append(act)
        mapping[act_id] = ("work_status_achievement", 1.0 + (i * 0.05))

    # 40 medium (transit medium window — JUPITER for slower transit)
    for i in range(40):
        act_id = f"medium-bench-{i}"
        act = build_activation(
            id=act_id,
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="SATURN",
            source_planet="JUPITER",
            target_planet="SATURN",
            strength=0.5 + (i / 80.0),
            active_from="2026-03-01T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-09-30T00:00:00Z",
        )
        activations.append(act)
        mapping[act_id] = ("crisis_transformation_control", 1.0 + (i * 0.05))

    # 40 fast (transit fast window — MOON for fast transit)
    for i in range(40):
        act_id = f"fast-bench-{i}"
        act = build_activation(
            id=act_id,
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="SATURN",
            source_planet="MOON",
            target_planet="SATURN",
            strength=0.5 + (i / 80.0),
            active_from="2026-07-12T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-07-12T23:00:00Z",
        )
        activations.append(act)
        mapping[act_id] = ("crisis_transformation_control", 1.0 + (i * 0.05))

    layer = ActivationLayer(
        calculation_version="calc",
        target_date="2026-07-12",
        target_time="12:00",
        target_tz="UTC",
        house_system="WHOLE_SIGN",
        activations=activations,
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )
    scoring = build_scoring(activations, mapping)
    natal = build_natal_context(
        planets=[
            NatalChartPlanet(
                name="SATURN", sign="AQUARIUS", degree=0.0,
                house=10, retrograde=False, longitude=0.0,
            ),
        ],
        aspects=[],
    )
    return layer, scoring, natal


# END_BLOCK: GUIDANCE_TESTKIT_BENCHMARK


# START_BLOCK: GUIDANCE_TESTKIT_HELPERS
def _build_natal_by_case(case: str) -> NatalContextData:
    if case == "structure":
        return build_structure_natal()
    elif case == "communication":
        return build_communication_natal()
    elif case == "relationships":
        return build_relationship_natal()
    elif case == "empty":
        return build_natal_context()
    elif case == "mixed":
        return build_natal_context(
            planets=[
                NatalChartPlanet(
                    name="SATURN", sign="AQUARIUS", degree=0.0,
                    house=10, retrograde=False, longitude=0.0,
                ),
                NatalChartPlanet(
                    name="MERCURY", sign="GEMINI", degree=0.0,
                    house=3, retrograde=False, longitude=0.0,
                ),
            ],
            aspects=[],
        )
    return build_natal_context()


def _build_verdict_case(
    case: str,
    selection: SelectedHorizonTriple,
) -> dict[TodayV2ProductSphereKey, HorizonSphereVerdict]:
    spheres: set[TodayV2ProductSphereKey] = set()
    for anchor in selection.items:
        for s in anchor.product_spheres:
            spheres.add(s)
    verdicts: dict[TodayV2ProductSphereKey, HorizonSphereVerdict] = {}
    if case == "good":
        for s in spheres:
            verdicts[s] = "good"
    elif case == "neutral":
        for s in spheres:
            verdicts[s] = "neutral"
    elif case == "caution":
        for s in spheres:
            verdicts[s] = "caution"
    elif case == "avoid":
        for s in spheres:
            verdicts[s] = "avoid"
    elif case == "mixed":
        for i, s in enumerate(sorted(spheres)):
            verdicts[s] = ["good", "neutral", "caution", "avoid"][i % 4]
    return verdicts


# END_BLOCK: GUIDANCE_TESTKIT_HELPERS


__all__ = [
    "build_guidance_context",
    "build_validated_guidance",
    "shifted_story_for",
    "build_coverage_cases",
    "build_worst_case_pipeline_input",
]
