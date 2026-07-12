# ############################################################################
# AI_HEADER: MODULE_HORIZON_SELECTION_SCHEMA — strict internal B2A selection result contracts.
# ROLE: Owns timing, mapping, candidate, triple, diagnostics, and result models for B2A only.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-SELECTION-SCHEMA
# purpose: Reject impossible internal B2A states before B2B can consume a selection result.
# owns:
#   - apps/api/app/schemas/horizon_selection.py
# inputs: Pure machine fields from timing, scoring, canon, and selection services.
# outputs: Frozen, non-public Pydantic models with typed machine warnings and diagnostics.
# dependencies: math/typing stdlib, pydantic, app.schemas.today_horizons.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No human evidence, debug payload, PII, or prose fields are modelled.
#   - Normalized scores are finite in 0..1 and serialized computed scores have six decimals.
#   - Horizon lists and triple items preserve the canonical long, medium, fast order.
# failure_policy: raises Pydantic ValidationError with hide_input_in_errors enabled.
# END_MODULE_CONTRACT: M-HORIZON-SELECTION-SCHEMA

# START_MODULE_MAP: M-HORIZON-SELECTION-SCHEMA
# public_entrypoints:
#   - HorizonTimingAssessment
#   - HorizonSphereMapping
#   - HorizonCandidateFeatureScores
#   - HorizonCandidate
#   - SelectedHorizonAnchor
#   - SelectedHorizonTriple
#   - HorizonSelectionDiagnostics
#   - HorizonSelectionResult
# semantic_blocks:
#   - HORIZON_SELECTION_INTERNAL_TYPES: literals and validation helpers.
#   - HORIZON_SELECTION_INTERNAL_MODELS: frozen selection result models.
# owned_tests:
#   - apps/api/tests/test_horizon_timing_service.py
#   - apps/api/tests/test_horizon_sphere_mapping_service.py
#   - apps/api/tests/test_horizon_selection_service.py
# END_MODULE_MAP: M-HORIZON-SELECTION-SCHEMA

# START_BLOCK: HORIZON_SELECTION_INTERNAL_TYPES
from __future__ import annotations

import math
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.today_horizons import (
    TodayV2HorizonId,
    TodayV2ProductSphereKey,
    TodayV2TimingPrecision,
    TodayV2TimingState,
)

HORIZON_ORDER: tuple[TodayV2HorizonId, ...] = ("long", "medium", "fast")
PAIR_OVERLAP_KEYS: frozenset[str] = frozenset({"long_medium", "medium_fast", "long_fast"})
HorizonTimingWarningCode = Literal[
    "missing_timing",
    "partial_timing",
    "mixed_precision",
    "invalid_timing",
    "invalid_target_clock",
    "target_before_window",
    "target_after_window",
    "unknown_technique",
    "unknown_source_speed",
    "no_product_sphere",
    "below_impact_threshold",
]
HorizonExclusionReason = HorizonTimingWarningCode
HorizonSelectionReason = Literal[
    "selected",
    "invalid_target_clock",
    "missing_long",
    "missing_medium",
    "missing_fast",
    "no_coherent_triple",
]
RelativeTargetPosition = Literal["before", "inside", "after"]


class HorizonSelectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


def _ensure_unit_interval(value: float, path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_unit_interval
    # purpose: Validate an internal normalized score without including its raw value in errors.
    # inputs: value - numeric score; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError unless value is finite in 0..1.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_unit_interval
    if not math.isfinite(value) or value < 0 or value > 1:
        raise ValueError(f"{path}: expected finite value in 0..1")


def _ensure_finite_non_negative(value: float, path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_finite_non_negative
    # purpose: Validate a non-negative machine duration or linked amount.
    # inputs: value - numeric value; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for negative or non-finite values.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_finite_non_negative
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{path}: expected finite non-negative value")


def _ensure_unique(values: Sequence[str], path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_unique
    # purpose: Enforce stable set-like lists without altering their caller-owned order.
    # inputs: values - ordered machine values; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError when a duplicate is present.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_unique
    if len(values) != len(set(values)):
        raise ValueError(f"{path}: duplicate values are not allowed")


def _ensure_canonical_horizons(values: list[TodayV2HorizonId], path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_canonical_horizons
    # purpose: Enforce a unique long, medium, fast subsequence for timing horizon lists.
    # inputs: values - ordered horizon identifiers; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for duplicates or noncanonical order.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_canonical_horizons
    _ensure_unique(values, path)
    if values != [horizon for horizon in HORIZON_ORDER if horizon in values]:
        raise ValueError(f"{path}: expected canonical long/medium/fast subsequence")


def _ensure_round6(value: float, path: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_round6
    # purpose: Ensure a serialized computed score is already stable at six decimals.
    # inputs: value - normalized score; path - structural field path.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for non-normalized or non-six-decimal values.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA._ensure_round6
    _ensure_unit_interval(value, path)
    if round(value, 6) != value:
        raise ValueError(f"{path}: expected six-decimal rounded value")
# END_BLOCK: HORIZON_SELECTION_INTERNAL_TYPES


# START_BLOCK: HORIZON_SELECTION_INTERNAL_MODELS
class HorizonTimingAssessment(HorizonSelectionModel):
    activation_id: str
    precision: TodayV2TimingPrecision | None = None
    active_from: str | None = None
    exact_at: str | None = None
    active_until: str | None = None
    timezone: str
    target_local: str
    target_utc: str
    duration_seconds: float | None = None
    duration_days: float | None = None
    relative_position: RelativeTargetPosition
    timing_state: TodayV2TimingState | None = None
    timing_completeness: float
    eligible_horizons: list[TodayV2HorizonId] = Field(default_factory=list)
    preferred_horizons: list[TodayV2HorizonId] = Field(default_factory=list)
    warning_codes: list[HorizonTimingWarningCode] = Field(default_factory=list)
    is_anchor_eligible: bool

    @model_validator(mode="after")
    def validate_model(self) -> "HorizonTimingAssessment":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonTimingAssessment.validate_model
        # purpose: Validate timing completeness, paired durations, canonical eligibility, and anchor requirements.
        # inputs: self - parsed timing assessment.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on an impossible internal timing state.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonTimingAssessment.validate_model
        _ensure_unit_interval(self.timing_completeness, "HorizonTimingAssessment.timing_completeness")
        if (self.duration_seconds is None) != (self.duration_days is None):
            raise ValueError("HorizonTimingAssessment: duration_seconds and duration_days must both be null or present")
        if self.duration_seconds is not None and self.duration_days is not None:
            _ensure_finite_non_negative(self.duration_seconds, "HorizonTimingAssessment.duration_seconds")
            _ensure_finite_non_negative(self.duration_days, "HorizonTimingAssessment.duration_days")
        _ensure_canonical_horizons(self.eligible_horizons, "HorizonTimingAssessment.eligible_horizons")
        _ensure_canonical_horizons(self.preferred_horizons, "HorizonTimingAssessment.preferred_horizons")
        if not set(self.preferred_horizons).issubset(self.eligible_horizons):
            raise ValueError("HorizonTimingAssessment.preferred_horizons: must be a subset of eligible_horizons")
        _ensure_unique(self.warning_codes, "HorizonTimingAssessment.warning_codes")
        if self.relative_position in {"before", "after"} and self.is_anchor_eligible:
            raise ValueError("HorizonTimingAssessment: before/after targets cannot be anchor eligible")
        if self.is_anchor_eligible:
            if self.relative_position != "inside":
                raise ValueError("HorizonTimingAssessment: eligible anchor requires inside target position")
            if not self.eligible_horizons:
                raise ValueError("HorizonTimingAssessment: eligible anchor requires at least one horizon")
            if self.precision not in {"date", "instant"}:
                raise ValueError("HorizonTimingAssessment: eligible anchor requires date or instant precision")
            if self.active_from is None or self.active_until is None:
                raise ValueError("HorizonTimingAssessment: eligible anchor requires active boundaries")
            if self.timing_state is None:
                raise ValueError("HorizonTimingAssessment: eligible anchor requires timing_state")
        return self


class HorizonSphereMapping(HorizonSelectionModel):
    technical_spheres: list[str] = Field(default_factory=list)
    product_spheres: list[TodayV2ProductSphereKey] = Field(default_factory=list)
    theme_keys: list[str] = Field(default_factory=list)
    linked_abs_amount: float = 0.0
    best_technical_rank: int | None = None

    @model_validator(mode="after")
    def validate_model(self) -> "HorizonSphereMapping":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonSphereMapping.validate_model
        # purpose: Validate ordered technical/product/theme mapping and empty-link semantics.
        # inputs: self - parsed activation sphere mapping.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError when mapping metadata contradicts its linkage.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonSphereMapping.validate_model
        _ensure_unique(self.technical_spheres, "HorizonSphereMapping.technical_spheres")
        _ensure_unique(self.product_spheres, "HorizonSphereMapping.product_spheres")
        _ensure_unique(self.theme_keys, "HorizonSphereMapping.theme_keys")
        if len(self.product_spheres) > 3 or len(self.theme_keys) > 4:
            raise ValueError("HorizonSphereMapping: product/theme mapping exceeds v1 bounds")
        _ensure_finite_non_negative(self.linked_abs_amount, "HorizonSphereMapping.linked_abs_amount")
        if self.best_technical_rank is not None and self.best_technical_rank < 1:
            raise ValueError("HorizonSphereMapping.best_technical_rank: expected null or >=1")
        if not self.technical_spheres:
            if self.product_spheres or self.theme_keys or self.linked_abs_amount != 0 or self.best_technical_rank is not None:
                raise ValueError("HorizonSphereMapping: empty technical mapping must have empty zero metadata")
        return self


class HorizonCandidateFeatureScores(HorizonSelectionModel):
    strength: float
    sphere_rank: float
    contribution: float
    convergence: float
    timing_relevance: float
    timing_completeness: float
    technique_priority: float

    @model_validator(mode="after")
    def validate_model(self) -> "HorizonCandidateFeatureScores":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonCandidateFeatureScores.validate_model
        # purpose: Ensure all seven candidate features remain normalized.
        # inputs: self - parsed feature score vector.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for an invalid feature value.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonCandidateFeatureScores.validate_model
        for field_name, value in self.model_dump().items():
            _ensure_unit_interval(value, f"HorizonCandidateFeatureScores.{field_name}")
        return self


class HorizonCandidate(HorizonSelectionModel):
    activation_id: str
    horizon: TodayV2HorizonId
    technique: str
    technique_family: str
    polarity: Literal["supportive", "neutral", "tense", "mixed"]
    target_type: Literal["planet", "house", "lot", "angle", "sphere"]
    target_key_normalized: str
    source_planet_normalized: str | None = None
    target_planet_normalized: str | None = None
    house_target_key: str | None = None
    timing: HorizonTimingAssessment
    technical_spheres: list[str]
    product_spheres: list[TodayV2ProductSphereKey]
    theme_keys: list[str]
    target_family_convergence_count: int = Field(ge=1)
    feature_scores: HorizonCandidateFeatureScores
    impact_score: float

    @model_validator(mode="after")
    def validate_model(self) -> "HorizonCandidate":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonCandidate.validate_model
        # purpose: Bind a candidate exactly to its eligible timing assessment and bounded mapping data.
        # inputs: self - parsed candidate.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on identity, eligibility, list, or score contradictions.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonCandidate.validate_model
        if self.activation_id != self.timing.activation_id:
            raise ValueError("HorizonCandidate: activation_id must equal timing.activation_id")
        if not self.timing.is_anchor_eligible or self.horizon not in self.timing.eligible_horizons:
            raise ValueError("HorizonCandidate: horizon must be timing-eligible")
        _ensure_unique(self.technical_spheres, "HorizonCandidate.technical_spheres")
        _ensure_unique(self.product_spheres, "HorizonCandidate.product_spheres")
        _ensure_unique(self.theme_keys, "HorizonCandidate.theme_keys")
        if len(self.product_spheres) > 3 or len(self.theme_keys) > 4:
            raise ValueError("HorizonCandidate: product/theme mapping exceeds v1 bounds")
        _ensure_round6(self.impact_score, "HorizonCandidate.impact_score")
        return self

    def tie_break_key(self) -> tuple[float, float, float, float, str]:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonCandidate.tie_break_key
        # purpose: Provide the canonical stable sort key for bounded candidate ranking.
        # inputs: self - valid candidate.
        # returns: score-descending tuple with activation id as final ascending tie break.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonCandidate.tie_break_key
        return (
            -self.impact_score,
            -self.feature_scores.timing_completeness,
            -self.feature_scores.strength,
            -self.feature_scores.technique_priority,
            self.activation_id,
        )


class SelectedHorizonAnchor(HorizonSelectionModel):
    horizon: TodayV2HorizonId
    activation_id: str
    technique: str
    technique_family: str
    polarity: Literal["supportive", "neutral", "tense", "mixed"]
    target_type: Literal["planet", "house", "lot", "angle", "sphere"]
    target_key_normalized: str
    source_planet_normalized: str | None = None
    target_planet_normalized: str | None = None
    house_target_key: str | None = None
    timing: HorizonTimingAssessment
    technical_spheres: list[str]
    product_spheres: list[TodayV2ProductSphereKey]
    theme_keys: list[str]
    target_family_convergence_count: int = Field(ge=1)
    feature_scores: HorizonCandidateFeatureScores
    impact_score: float

    @model_validator(mode="after")
    def validate_model(self) -> "SelectedHorizonAnchor":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.SelectedHorizonAnchor.validate_model
        # purpose: Keep selected anchors self-contained for B2B without recomputing timing or candidate math.
        # inputs: self - parsed selected anchor.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError when a selected anchor is not a valid eligible candidate fact set.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.SelectedHorizonAnchor.validate_model
        if self.activation_id != self.timing.activation_id:
            raise ValueError("SelectedHorizonAnchor: activation_id must equal timing.activation_id")
        if not self.timing.is_anchor_eligible or self.horizon not in self.timing.eligible_horizons:
            raise ValueError("SelectedHorizonAnchor: horizon must be timing-eligible")
        _ensure_unique(self.technical_spheres, "SelectedHorizonAnchor.technical_spheres")
        _ensure_unique(self.product_spheres, "SelectedHorizonAnchor.product_spheres")
        _ensure_unique(self.theme_keys, "SelectedHorizonAnchor.theme_keys")
        if len(self.product_spheres) > 3 or len(self.theme_keys) > 4:
            raise ValueError("SelectedHorizonAnchor: product/theme mapping exceeds v1 bounds")
        _ensure_round6(self.impact_score, "SelectedHorizonAnchor.impact_score")
        return self


class SelectedHorizonTriple(HorizonSelectionModel):
    items: list[SelectedHorizonAnchor] = Field(min_length=3, max_length=3)
    pair_overlap_scores: dict[Literal["long_medium", "medium_fast", "long_fast"], float]
    mean_overlap: float
    mean_impact: float
    family_diversity_score: float
    unique_family_count: int = Field(ge=1, le=3)
    total_score: float
    shared_theme_keys: list[str]
    shared_product_spheres: list[TodayV2ProductSphereKey]
    unique_anchor_activation_ids: list[str]

    @model_validator(mode="after")
    def validate_model(self) -> "SelectedHorizonTriple":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.SelectedHorizonTriple.validate_model
        # purpose: Validate ordered unique anchors and all bounded, rounded triple score fields.
        # inputs: self - parsed selected triple.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on invalid order, identity, score, family, or summary lists.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.SelectedHorizonTriple.validate_model
        if [item.horizon for item in self.items] != list(HORIZON_ORDER):
            raise ValueError("SelectedHorizonTriple.items: expected long, medium, fast order")
        if set(self.pair_overlap_scores) != PAIR_OVERLAP_KEYS:
            raise ValueError("SelectedHorizonTriple.pair_overlap_scores: expected exact v1 pair keys")
        _ensure_unique(self.unique_anchor_activation_ids, "SelectedHorizonTriple.unique_anchor_activation_ids")
        if self.unique_anchor_activation_ids != [item.activation_id for item in self.items]:
            raise ValueError("SelectedHorizonTriple.unique_anchor_activation_ids: must match ordered items")
        for key, value in self.pair_overlap_scores.items():
            _ensure_round6(value, f"SelectedHorizonTriple.pair_overlap_scores.{key}")
        for field_name in ("mean_overlap", "mean_impact", "family_diversity_score", "total_score"):
            _ensure_round6(getattr(self, field_name), f"SelectedHorizonTriple.{field_name}")
        actual_family_count = len({item.technique_family for item in self.items})
        if self.unique_family_count != actual_family_count:
            raise ValueError("SelectedHorizonTriple.unique_family_count: must equal actual item family count")
        _ensure_unique(self.shared_theme_keys, "SelectedHorizonTriple.shared_theme_keys")
        _ensure_unique(self.shared_product_spheres, "SelectedHorizonTriple.shared_product_spheres")
        if len(self.shared_theme_keys) > 4 or len(self.shared_product_spheres) > 3:
            raise ValueError("SelectedHorizonTriple: shared summary exceeds v1 bounds")
        return self


class HorizonSelectionDiagnostics(HorizonSelectionModel):
    input_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    classified_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    per_horizon_pre_bound_counts: dict[TodayV2HorizonId, int]
    per_horizon_post_bound_counts: dict[TodayV2HorizonId, int]
    excluded_counts_by_reason: dict[HorizonExclusionReason, int] = Field(default_factory=dict)
    combinations_evaluated: int = Field(ge=0)
    input_truncated: bool = False

    @model_validator(mode="after")
    def validate_model(self) -> "HorizonSelectionDiagnostics":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonSelectionDiagnostics.validate_model
        # purpose: Bind bounded candidate diagnostics to their exact v1 accounting semantics.
        # inputs: self - parsed selection diagnostics.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for inconsistent counts, keys, or v1 bounds.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonSelectionDiagnostics.validate_model
        if set(self.per_horizon_pre_bound_counts) != set(HORIZON_ORDER):
            raise ValueError("HorizonSelectionDiagnostics.per_horizon_pre_bound_counts: expected exact horizon keys")
        if set(self.per_horizon_post_bound_counts) != set(HORIZON_ORDER):
            raise ValueError("HorizonSelectionDiagnostics.per_horizon_post_bound_counts: expected exact horizon keys")
        if not self.input_count >= self.active_count >= self.classified_count:
            raise ValueError("HorizonSelectionDiagnostics: expected input_count >= active_count >= classified_count")
        for horizon in HORIZON_ORDER:
            pre = self.per_horizon_pre_bound_counts[horizon]
            post = self.per_horizon_post_bound_counts[horizon]
            if pre < 0 or post < 0:
                raise ValueError("HorizonSelectionDiagnostics: horizon counts must be non-negative")
            if post > pre or post > 12:
                raise ValueError("HorizonSelectionDiagnostics: post-bound count exceeds pre-bound count or v1 max")
        if self.candidate_count != sum(self.per_horizon_pre_bound_counts.values()):
            raise ValueError("HorizonSelectionDiagnostics.candidate_count: must equal sum of pre-bound counts")
        if self.combinations_evaluated > 1728:
            raise ValueError("HorizonSelectionDiagnostics.combinations_evaluated: exceeds v1 max")
        for count in self.excluded_counts_by_reason.values():
            if count <= 0:
                raise ValueError("HorizonSelectionDiagnostics.excluded_counts_by_reason: counts must be positive")
        return self


class HorizonSelectionResult(HorizonSelectionModel):
    selection: SelectedHorizonTriple | None = None
    reason: HorizonSelectionReason
    diagnostics: HorizonSelectionDiagnostics
    warnings: list[HorizonTimingWarningCode] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_model(self) -> "HorizonSelectionResult":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonSelectionResult.validate_model
        # purpose: Keep the selected/null reason contract and typed warning list honest.
        # inputs: self - parsed selection result.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for contradictory selection/reason or duplicate warnings.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SCHEMA.HorizonSelectionResult.validate_model
        _ensure_unique(self.warnings, "HorizonSelectionResult.warnings")
        if self.selection is None and self.reason == "selected":
            raise ValueError("HorizonSelectionResult.reason: selected requires selection")
        if self.selection is not None and self.reason != "selected":
            raise ValueError("HorizonSelectionResult.reason: non-selected reason requires null selection")
        return self
# END_BLOCK: HORIZON_SELECTION_INTERNAL_MODELS


__all__ = [
    "HorizonTimingWarningCode",
    "HorizonExclusionReason",
    "HorizonSelectionReason",
    "RelativeTargetPosition",
    "HorizonTimingAssessment",
    "HorizonSphereMapping",
    "HorizonCandidateFeatureScores",
    "HorizonCandidate",
    "SelectedHorizonAnchor",
    "SelectedHorizonTriple",
    "HorizonSelectionDiagnostics",
    "HorizonSelectionResult",
]
