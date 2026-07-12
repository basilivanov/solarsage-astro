# ############################################################################
# AI_HEADER: MODULE_HORIZON_CANON_SCHEMA — closed typed schema for B2A selection canon.
# ROLE: Validates the versioned selection canon before pure B2A services consume it.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CANON-SCHEMA
# purpose: Validate grace/canon/horizon_selection.v1.yml as a fail-closed frozen model.
# owns:
#   - apps/api/app/schemas/horizon_canon.py
# inputs: Parsed YAML mappings for the horizon selection canon.
# outputs: Validated frozen canon models with normalized numeric and identity invariants.
# dependencies: math/re/typing stdlib, pydantic, app.schemas.today_horizons.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Canon numeric values consumed as normalized scores are finite values in 0..1.
#   - Horizon lists are unique canonical subsequences of long, medium, fast.
#   - Runtime planet lookups use the same canonical spelling required by this model.
# failure_policy: raises Pydantic ValidationError without raw YAML values in error text.
# END_MODULE_CONTRACT: M-HORIZON-CANON-SCHEMA

# START_MODULE_MAP: M-HORIZON-CANON-SCHEMA
# public_entrypoints:
#   - HorizonSelectionCanon
# semantic_blocks:
#   - HORIZON_CANON_CONSTANTS: closed ids and validation primitives.
#   - HORIZON_CANON_MODELS: nested frozen canon models and cross-field validators.
# owned_tests:
#   - apps/api/tests/test_horizon_canon_service.py
# END_MODULE_MAP: M-HORIZON-CANON-SCHEMA

# START_BLOCK: HORIZON_CANON_CONSTANTS
from __future__ import annotations

import math
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.today_horizons import TodayV2HorizonId, TodayV2ProductSphereKey

HORIZON_IDS: tuple[TodayV2HorizonId, ...] = ("long", "medium", "fast")
TECHNICAL_SPHERE_KEYS: frozenset[str] = frozenset(
    {
        "thinking_speech_learning",
        "work_status_achievement",
        "relationships_partnership",
        "money_security_resources",
        "body_energy_health",
        "home_family_roots",
        "inner_background_unconscious",
        "crisis_transformation_control",
        "meaning_expansion_vector",
    }
)
PUBLIC_PRODUCT_SPHERES: frozenset[str] = frozenset(
    {
        "work", "money", "documents", "relationships", "sport", "communication",
        "health", "decisions", "travel", "creativity", "study", "shopping",
    }
)
KNOWN_TECHNIQUES: frozenset[str] = frozenset(
    {
        "annual_profection", "monthly_profection", "firdar_major", "firdar_minor",
        "solar_return", "lunar_return", "secondary_progression", "solar_arc",
        "eclipse_window", "transit_to_natal", "transit_to_angle", "transit_to_lot",
        "transit_planet_in_house", "primary_direction",
    }
)
KNOWN_SPEED_GROUPS: frozenset[str] = frozenset({"fast", "medium", "slow"})
THEME_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
PREFIX_RE = re.compile(r"^(?:TRANSIT_|NATAL_)+")
ThemeKey = Annotated[str, Field(pattern=THEME_ID_RE.pattern, min_length=1, max_length=80)]


class HorizonCanonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


def _require_finite_non_negative(value: float, path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._require_finite_non_negative
    # purpose: Reject invalid non-negative canon numbers without echoing their input.
    # inputs: value - candidate numeric value; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for non-finite or negative values.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._require_finite_non_negative
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{path}: expected finite non-negative number")


def _require_unit_interval(value: float, path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._require_unit_interval
    # purpose: Reject a score that cannot participate in normalized downstream formulas.
    # inputs: value - candidate normalized value; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError unless value is finite in 0..1.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._require_unit_interval
    if not math.isfinite(value) or value < 0 or value > 1:
        raise ValueError(f"{path}: expected finite value in 0..1")


def _require_sum_one(values: dict[str, float], path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._require_sum_one
    # purpose: Validate a convex weight group.
    # inputs: values - named normalized weight mapping; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError when a member is invalid or the sum differs from one.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._require_sum_one
    for key, value in values.items():
        _require_unit_interval(value, f"{path}.{key}")
    if abs(sum(values.values()) - 1.0) > 1e-9:
        raise ValueError(f"{path}: weights must sum to 1.0")


def _normalize_planet_name(value: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._normalize_planet_name
    # purpose: Produce the sole planet comparison representation used by canon and runtime lookup.
    # inputs: value - raw planet identifier.
    # returns: uppercase identifier with known wire prefixes removed.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._normalize_planet_name
    return PREFIX_RE.sub("", value.strip().upper())


def _is_canonical_horizon_subsequence(values: list[TodayV2HorizonId]) -> bool:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._is_canonical_horizon_subsequence
    # purpose: Check ordered unique horizon membership against long, medium, fast canon order.
    # inputs: values - ordered horizon ids.
    # returns: true when values are a canonical subsequence.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA._is_canonical_horizon_subsequence
    return values == [horizon for horizon in HORIZON_IDS if horizon in values]
# END_BLOCK: HORIZON_CANON_CONSTANTS


# START_BLOCK: HORIZON_CANON_MODELS
class CanonLimits(HorizonCanonModel):
    max_input_activations: int = Field(gt=0)
    max_candidates_per_horizon: int = Field(gt=0)
    max_product_spheres_per_candidate: int = Field(gt=0, le=3)
    max_theme_keys_per_candidate: int = Field(gt=0, le=4)
    max_anchor_combinations: int = Field(gt=0, le=1728)


class DurationBand(HorizonCanonModel):
    eligible_min_days: float = Field(ge=0)
    eligible_max_days: float | None = Field(default=None, ge=0)
    preferred_min_days: float = Field(ge=0)
    preferred_max_days: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> "DurationBand":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.DurationBand.validate_order
        # purpose: Validate finite ordered eligible and preferred duration intervals.
        # inputs: self - parsed duration band.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on non-finite or unordered bounds.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.DurationBand.validate_order
        for field_name in (
            "eligible_min_days", "eligible_max_days", "preferred_min_days", "preferred_max_days",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _require_finite_non_negative(value, f"duration_bands.{field_name}")
        if self.eligible_max_days is not None and self.eligible_min_days > self.eligible_max_days:
            raise ValueError("duration_bands: eligible_min_days must be <= eligible_max_days")
        if self.preferred_max_days is not None and self.preferred_min_days > self.preferred_max_days:
            raise ValueError("duration_bands: preferred_min_days must be <= preferred_max_days")
        if self.preferred_min_days < self.eligible_min_days:
            raise ValueError("duration_bands: preferred_min_days must be >= eligible_min_days")
        if (
            self.eligible_max_days is not None
            and self.preferred_max_days is not None
            and self.preferred_max_days > self.eligible_max_days
        ):
            raise ValueError("duration_bands: preferred_max_days must be <= eligible_max_days")
        return self


class DurationBands(HorizonCanonModel):
    long: DurationBand
    medium: DurationBand
    fast: DurationBand


class StateRelevance(HorizonCanonModel):
    upcoming: float
    building: float
    active: float
    exact: float
    peaked: float
    fading: float
    background: float

    @model_validator(mode="after")
    def validate_values(self) -> "StateRelevance":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.StateRelevance.validate_values
        # purpose: Restrict all timing relevance values to the normalized unit interval.
        # inputs: self - parsed state relevance mapping.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for invalid normalized values.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.StateRelevance.validate_values
        for field_name, value in self.model_dump().items():
            _require_unit_interval(value, f"timing.state_relevance.{field_name}")
        return self


class TimingConfig(HorizonCanonModel):
    instant_exact_tolerance_seconds: int = Field(ge=0)
    peaked_min_seconds: int = Field(ge=0)
    peaked_post_exact_fraction: float
    date_exact_tolerance_days: int = Field(ge=0)
    completeness_with_exact: float
    completeness_without_exact: float
    state_relevance: StateRelevance

    @model_validator(mode="after")
    def validate_values(self) -> "TimingConfig":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.TimingConfig.validate_values
        # purpose: Restrict normalized timing configuration values to the unit interval.
        # inputs: self - parsed timing configuration.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for invalid timing configuration.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.TimingConfig.validate_values
        _require_unit_interval(self.peaked_post_exact_fraction, "timing.peaked_post_exact_fraction")
        _require_unit_interval(self.completeness_with_exact, "timing.completeness_with_exact")
        _require_unit_interval(self.completeness_without_exact, "timing.completeness_without_exact")
        return self


class ImpactWeights(HorizonCanonModel):
    strength: float
    sphere_rank: float
    contribution: float
    convergence: float
    timing_relevance: float
    timing_completeness: float
    technique_priority: float

    @model_validator(mode="after")
    def validate_values(self) -> "ImpactWeights":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.ImpactWeights.validate_values
        # purpose: Validate the convex candidate impact weights.
        # inputs: self - parsed impact weight group.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on invalid weight values or sum.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.ImpactWeights.validate_values
        _require_sum_one(self.model_dump(), "impact_weights")
        return self


class MinCandidateImpact(HorizonCanonModel):
    long: float
    medium: float
    fast: float

    @model_validator(mode="after")
    def validate_values(self) -> "MinCandidateImpact":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.MinCandidateImpact.validate_values
        # purpose: Validate normalized per-horizon candidate thresholds.
        # inputs: self - parsed threshold mapping.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for values outside 0..1.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.MinCandidateImpact.validate_values
        for field_name, value in self.model_dump().items():
            _require_unit_interval(value, f"min_candidate_impact.{field_name}")
        return self


class StoryOverlapWeights(HorizonCanonModel):
    same_target: float
    shared_theme: float
    shared_product_sphere: float
    same_planet_or_house: float
    shared_technical_sphere: float

    @model_validator(mode="after")
    def validate_values(self) -> "StoryOverlapWeights":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.StoryOverlapWeights.validate_values
        # purpose: Validate the convex pair-story overlap weights.
        # inputs: self - parsed overlap weight group.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on invalid weight values or sum.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.StoryOverlapWeights.validate_values
        _require_sum_one(self.model_dump(), "story_overlap_weights")
        return self


class MinPairOverlap(HorizonCanonModel):
    long_medium: float
    medium_fast: float
    long_fast: float
    triple_mean: float

    @model_validator(mode="after")
    def validate_values(self) -> "MinPairOverlap":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.MinPairOverlap.validate_values
        # purpose: Validate normalized pair and triple overlap thresholds.
        # inputs: self - parsed overlap threshold mapping.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for values outside 0..1.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.MinPairOverlap.validate_values
        for field_name, value in self.model_dump().items():
            _require_unit_interval(value, f"min_pair_overlap.{field_name}")
        return self


class TripleScoreWeights(HorizonCanonModel):
    mean_impact: float
    mean_overlap: float
    family_diversity: float

    @model_validator(mode="after")
    def validate_values(self) -> "TripleScoreWeights":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.TripleScoreWeights.validate_values
        # purpose: Validate the convex triple-score weights.
        # inputs: self - parsed triple-score weight group.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on invalid weight values or sum.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.TripleScoreWeights.validate_values
        _require_sum_one(self.model_dump(), "triple_score_weights")
        return self


class PlanetSpeedGroups(HorizonCanonModel):
    fast: list[str]
    medium: list[str]
    slow: list[str]

    @model_validator(mode="after")
    def validate_groups(self) -> "PlanetSpeedGroups":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.PlanetSpeedGroups.validate_groups
        # purpose: Enforce non-empty, disjoint, normalized planet speed groups.
        # inputs: self - parsed planet speed group mapping.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on blank, noncanonical, duplicate, or overlapping members.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.PlanetSpeedGroups.validate_groups
        seen: set[str] = set()
        for group_name, members in self.model_dump().items():
            if not members:
                raise ValueError(f"planet_speed_groups.{group_name}: must be non-empty")
            local_seen: set[str] = set()
            for member in members:
                normalized = _normalize_planet_name(member)
                if not normalized or member != normalized:
                    raise ValueError(f"planet_speed_groups.{group_name}: member must be canonical normalized")
                if normalized in local_seen:
                    raise ValueError(f"planet_speed_groups.{group_name}: duplicate member after normalization")
                if normalized in seen:
                    raise ValueError("planet_speed_groups: groups must be disjoint")
                local_seen.add(normalized)
                seen.add(normalized)
        return self


TimingMode = Literal["peak", "period", "window"]


class TechniqueRule(HorizonCanonModel):
    allowed_horizons: list[TodayV2HorizonId]
    preferred_horizon: TodayV2HorizonId
    timing_mode: TimingMode
    priority_by_horizon: dict[TodayV2HorizonId, float]

    @model_validator(mode="after")
    def validate_rule(self) -> "TechniqueRule":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.TechniqueRule.validate_rule
        # purpose: Make technique horizon eligibility and direct priority lookup total and ordered.
        # inputs: self - parsed technique rule.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for empty, reordered, duplicate, or incomplete priorities.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.TechniqueRule.validate_rule
        allowed = list(self.allowed_horizons)
        if not allowed:
            raise ValueError("technique_rules: allowed_horizons must be non-empty")
        if len(set(allowed)) != len(allowed):
            raise ValueError("technique_rules: allowed_horizons must be unique")
        if not _is_canonical_horizon_subsequence(allowed):
            raise ValueError("technique_rules: allowed_horizons must use canonical order")
        if self.preferred_horizon not in allowed:
            raise ValueError("technique_rules: preferred_horizon must be allowed")
        if set(self.priority_by_horizon) != set(allowed):
            raise ValueError("technique_rules: priority keys must exactly equal allowed_horizons")
        for horizon, value in self.priority_by_horizon.items():
            if horizon not in HORIZON_IDS:
                raise ValueError("technique_rules: unknown horizon")
            _require_unit_interval(value, f"technique_rules.priority_by_horizon.{horizon}")
        return self


class HorizonSelectionCanon(HorizonCanonModel):
    schema_version: Literal["horizon_selection.v1"]
    version: Literal["v1"]
    limits: CanonLimits
    duration_bands: DurationBands
    timing: TimingConfig
    impact_weights: ImpactWeights
    min_candidate_impact: MinCandidateImpact
    story_overlap_weights: StoryOverlapWeights
    min_pair_overlap: MinPairOverlap
    triple_score_weights: TripleScoreWeights
    planet_speed_groups: PlanetSpeedGroups
    transit_speed_eligibility: dict[TodayV2HorizonId, list[Literal["fast", "medium", "slow"]]]
    technique_rules: dict[str, TechniqueRule]
    technical_to_product_spheres: dict[str, list[TodayV2ProductSphereKey]]
    technical_sphere_themes: dict[str, list[ThemeKey]]
    target_planet_themes: dict[str, list[ThemeKey]]

    @model_validator(mode="after")
    def validate_canon(self) -> "HorizonSelectionCanon":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.HorizonSelectionCanon.validate_canon
        # purpose: Enforce cross-field, coverage, and lookup invariants for the entire B2A canon.
        # inputs: self - parsed top-level horizon selection canon.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on any invalid closed-canon invariant.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SCHEMA.HorizonSelectionCanon.validate_canon
        if self.limits.max_candidates_per_horizon ** 3 > self.limits.max_anchor_combinations:
            raise ValueError("limits: max_candidates_per_horizon ** 3 must be <= max_anchor_combinations")
        if set(self.transit_speed_eligibility) != set(HORIZON_IDS):
            raise ValueError("transit_speed_eligibility: expected exact long/medium/fast keys")
        for horizon, groups in self.transit_speed_eligibility.items():
            if not groups:
                raise ValueError(f"transit_speed_eligibility.{horizon}: must be non-empty")
            if len(groups) != len(set(groups)):
                raise ValueError(f"transit_speed_eligibility.{horizon}: values must be unique")
            if not set(groups).issubset(KNOWN_SPEED_GROUPS):
                raise ValueError(f"transit_speed_eligibility.{horizon}: unknown speed group")
        for technique_name in self.technique_rules:
            if technique_name not in KNOWN_TECHNIQUES:
                raise ValueError(f"technique_rules.{technique_name}: unknown technique")
        if set(self.technical_to_product_spheres) != TECHNICAL_SPHERE_KEYS:
            raise ValueError("technical_to_product_spheres: expected exact nine technical keys")
        if set(self.technical_sphere_themes) != TECHNICAL_SPHERE_KEYS:
            raise ValueError("technical_sphere_themes: expected exact nine technical keys")
        product_union: set[str] = set()
        for technical_key, values in self.technical_to_product_spheres.items():
            if not values:
                raise ValueError(f"technical_to_product_spheres.{technical_key}: must be non-empty")
            if len(values) != len(set(values)):
                raise ValueError(f"technical_to_product_spheres.{technical_key}: duplicate product sphere")
            product_union.update(values)
        if product_union != PUBLIC_PRODUCT_SPHERES:
            raise ValueError("technical_to_product_spheres: union must cover all 12 public product keys")
        for technical_key, values in self.technical_sphere_themes.items():
            if not values:
                raise ValueError(f"technical_sphere_themes.{technical_key}: must be non-empty")
            if len(values) != len(set(values)):
                raise ValueError(f"technical_sphere_themes.{technical_key}: duplicate theme id")
        normalized_target_keys: set[str] = set()
        for planet_key, values in self.target_planet_themes.items():
            normalized = _normalize_planet_name(planet_key)
            if not normalized or planet_key != normalized:
                raise ValueError("target_planet_themes: keys must be canonical normalized")
            if normalized in normalized_target_keys:
                raise ValueError("target_planet_themes: duplicate key after normalization")
            normalized_target_keys.add(normalized)
            if not values:
                raise ValueError(f"target_planet_themes.{planet_key}: must be non-empty")
            if len(values) != len(set(values)):
                raise ValueError(f"target_planet_themes.{planet_key}: duplicate theme id")
        return self
# END_BLOCK: HORIZON_CANON_MODELS


__all__ = [
    "HorizonSelectionCanon",
    "HORIZON_IDS",
    "TECHNICAL_SPHERE_KEYS",
    "KNOWN_TECHNIQUES",
]
