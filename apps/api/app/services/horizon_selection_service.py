# ############################################################################
# AI_HEADER: MODULE_HORIZON_SELECTION_SERVICE — coherent long/medium/fast B2A selector.
# ROLE: Build bounded candidates from activation+scoring, rank them canonically, and select a coherent triple.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-SELECTION-SERVICE
# purpose: Convert an ActivationLayer and ScoringV2Result into a typed internal horizon selection result.
# owns:
#   - apps/api/app/services/horizon_selection_service.py
# inputs: ActivationLayer and ScoringV2Result.
# outputs: HorizonSelectionResult with deterministic diagnostics, honest fallback, and no public integration.
# dependencies: collections/itertools/re stdlib, app.schemas activation/scoring/horizon_selection, horizon canon/timing/sphere services.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - ignores inactive evidences and bounds work to canon limits.
#   - does not consult DB/network/LLM/random/server clock.
#   - never forces an incoherent triple when honest null fallback applies.
# failure_policy: invalid canon/programming invariant raises; ordinary lack of evidence returns selection=None with typed reason.
# END_MODULE_CONTRACT: M-HORIZON-SELECTION-SERVICE

# START_MODULE_MAP: M-HORIZON-SELECTION-SERVICE
# public_entrypoints:
#   - HorizonSelectionService.select
# semantic_blocks:
#   - HORIZON_SELECTION_HELPERS: normalization, scoring, overlap, and deterministic ordering helpers.
#   - HORIZON_SELECTION_SERVICE: bounded candidate generation and coherent triple selection.
# owned_tests:
#   - apps/api/tests/test_horizon_selection_service.py
#   - apps/api/tests/test_horizon_selection_benchmark.py
# END_MODULE_MAP: M-HORIZON-SELECTION-SERVICE

# START_BLOCK: HORIZON_SELECTION_HELPERS
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from itertools import product
import re
from typing import TypeVar
from zoneinfo import ZoneInfoNotFoundError

from app.schemas.activation import ActivationLayer
from app.schemas.horizon_selection import (
    HorizonCandidate,
    HorizonCandidateFeatureScores,
    HorizonSelectionDiagnostics,
    HorizonSelectionResult,
    SelectedHorizonAnchor,
    SelectedHorizonTriple,
)
from app.schemas.scoring_v2 import ScoringV2Result
from app.services.horizon_canon_service import load_horizon_selection_canon
from app.services.horizon_sphere_mapping_service import HorizonSphereMappingService
from app.services.horizon_timing_service import HorizonTimingService, _parse_target_clock
from app.schemas.today_horizons import TodayV2HorizonId

PREFIX_RE = re.compile(r"^(?:TRANSIT_|NATAL_)+")
_TStr = TypeVar("_TStr", bound=str)


def _normalize_planet(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = PREFIX_RE.sub("", value.strip().upper())
    return normalized or None


def _round6(value: float) -> float:
    return round(value + 0.0, 6)


def _ordered_union_by_frequency(
    items: Sequence[Sequence[_TStr]],
) -> list[_TStr]:
    order: dict[_TStr, tuple[int, int]] = {}
    counter: Counter[_TStr] = Counter()
    for outer_index, seq in enumerate(items):
        for inner_index, value in enumerate(seq):
            counter[value] += 1
            order.setdefault(value, (outer_index, inner_index))
    return [
        key for key, _ in sorted(counter.items(), key=lambda item: (-item[1], order[item[0]][0], order[item[0]][1], item[0]))
    ]


def _intersection_in_first_order(
    first: Sequence[_TStr],
    others: Sequence[Sequence[_TStr]],
) -> list[_TStr]:
    other_sets = [set(values) for values in others]
    return [value for value in first if all(value in values for values in other_sets)]


def _max_technique_priority(technique: str) -> float:
    canon = load_horizon_selection_canon()
    rule = canon.technique_rules.get(technique)
    if rule is None:
        return 0.0
    return max(rule.priority_by_horizon.values(), default=0.0)


def _family_diversity_score(unique_family_count: int) -> float:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE._family_diversity_score
    # purpose: Convert the number of independent technique families into the canonical normalized diversity score.
    # inputs: unique_family_count - count of unique technique family ids in one triple.
    # returns: rounded normalized clamp((count - 1) / 2, 0, 1).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none; counts below one clamp to zero for defensive pure use.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE._family_diversity_score
    return _round6(max(0.0, min(1.0, (unique_family_count - 1) / 2)))


def _triple_total_score(
    *,
    mean_impact: float,
    mean_overlap: float,
    family_diversity_score: float,
) -> float:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE._triple_total_score
    # purpose: Calculate the canon-weighted rounded score for one coherent anchor triple.
    # inputs: mean_impact, mean_overlap, family_diversity_score - normalized triple feature values.
    # returns: rounded normalized total triple score.
    # side_effects: reads cached typed horizon canon only.
    # emitted_logs: none.
    # error_behavior: propagates invalid canon loading errors.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE._triple_total_score
    weights = load_horizon_selection_canon().triple_score_weights
    return _round6(
        weights.mean_impact * mean_impact
        + weights.mean_overlap * mean_overlap
        + weights.family_diversity * family_diversity_score
    )


def _triple_sort_key(
    *,
    total_score: float,
    mean_overlap: float,
    mean_impact: float,
    unique_family_count: int,
    activation_ids: tuple[str, str, str],
) -> tuple[float, float, float, int, tuple[str, str, str]]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE._triple_sort_key
    # purpose: Provide the single canonical stable descending-score ordering for candidate triples.
    # inputs: total_score, mean_overlap, mean_impact, unique_family_count, activation_ids - computed triple facts.
    # returns: ascending Python sort key implementing the documented production tie-break order.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE._triple_sort_key
    return (-total_score, -mean_overlap, -mean_impact, -unique_family_count, activation_ids)
# END_BLOCK: HORIZON_SELECTION_HELPERS


# START_BLOCK: HORIZON_SELECTION_SERVICE
class HorizonSelectionService:
    def __init__(self) -> None:
        self._timing = HorizonTimingService()
        self._mapping = HorizonSphereMappingService()

    def select(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
    ) -> HorizonSelectionResult:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE.HorizonSelectionService.select
        # purpose: Select a coherent long/medium/fast anchor triple from active activation evidence.
        # inputs: activation_layer and scoring_result.
        # returns: HorizonSelectionResult.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: invalid canon/programming invariant raises; ordinary absence returns typed fallback.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE.HorizonSelectionService.select
        canon = load_horizon_selection_canon()
        diagnostics = HorizonSelectionDiagnostics(
            input_count=len(activation_layer.activations),
            active_count=0,
            classified_count=0,
            candidate_count=0,
            per_horizon_pre_bound_counts={"long": 0, "medium": 0, "fast": 0},
            per_horizon_post_bound_counts={"long": 0, "medium": 0, "fast": 0},
            excluded_counts_by_reason={},
            combinations_evaluated=0,
            input_truncated=False,
        )
        try:
            _parse_target_clock(
                target_date=activation_layer.target_date,
                target_time=activation_layer.target_time,
                target_tz=activation_layer.target_tz,
            )
        except (ValueError, ZoneInfoNotFoundError):
            return HorizonSelectionResult(selection=None, reason="invalid_target_clock", diagnostics=diagnostics, warnings=["invalid_target_clock"])

        active = [evidence for evidence in activation_layer.activations if evidence.active]
        diagnostics = diagnostics.model_copy(update={"active_count": len(active)})
        prebound = sorted(
            active,
            key=lambda evidence: (
                -max(min(evidence.strength, 1.0), 0.0),
                -_max_technique_priority(evidence.technique),
                evidence.id,
            ),
        )
        if len(prebound) > canon.limits.max_input_activations:
            prebound = prebound[: canon.limits.max_input_activations]
            diagnostics = diagnostics.model_copy(update={"input_truncated": True})

        diagnostics = diagnostics.model_copy(update={"classified_count": len(prebound)})
        warnings_seen: list[str] = []
        excluded: dict[str, int] = defaultdict(int)
        family_sets: dict[tuple[str, str], set[str]] = defaultdict(set)
        for evidence in prebound:
            family_sets[(evidence.target_type, _normalize_planet(evidence.target_key) or "")].add(evidence.technique_family)
        family_counts = {key: len(value) for key, value in family_sets.items()}
        global_max_linked_abs_amount = 0.0
        mappings = {}
        timings = {}
        for evidence in prebound:
            timings[evidence.id] = self._timing.classify(
                evidence,
                target_date=activation_layer.target_date,
                target_time=activation_layer.target_time,
                target_tz=activation_layer.target_tz,
            )
            mappings[evidence.id] = self._mapping.map_activation(
                evidence.id,
                scoring_result,
                source_planet=evidence.source_planet,
                target_planet_or_key=evidence.target_planet or evidence.target_key,
            )
            global_max_linked_abs_amount = max(global_max_linked_abs_amount, mappings[evidence.id].linked_abs_amount)
            warnings_seen.extend(timings[evidence.id].warning_codes)

        sphere_count = max(len(scoring_result.sphere_scores), 1)
        candidates_by_horizon: dict[TodayV2HorizonId, list[HorizonCandidate]] = {"long": [], "medium": [], "fast": []}
        state_relevance = canon.timing.state_relevance.model_dump()
        impact_weights = canon.impact_weights.model_dump()
        for evidence in prebound:
            timing = timings[evidence.id]
            mapping = mappings[evidence.id]
            if not mapping.product_spheres:
                excluded["no_product_sphere"] += 1
                warnings_seen.append("no_product_sphere")
                continue
            if not timing.is_anchor_eligible:
                for warning in timing.warning_codes:
                    excluded[warning] += 1
                continue
            rule = canon.technique_rules.get(evidence.technique)
            if rule is None:
                excluded["unknown_technique"] += 1
                continue
            normalized_target_key = _normalize_planet(evidence.target_key) or ""
            family_count = family_counts[(evidence.target_type, normalized_target_key)]
            best_rank = mapping.best_technical_rank or sphere_count
            features = {
                "strength": max(0.0, min(1.0, evidence.strength)),
                "sphere_rank": 1.0 if sphere_count == 1 else 1.0 - ((best_rank - 1) / (sphere_count - 1)),
                "contribution": 0.0 if global_max_linked_abs_amount <= 0 else mapping.linked_abs_amount / global_max_linked_abs_amount,
                "convergence": max(0.0, min(1.0, (family_count - 1) / 2)),
                "timing_relevance": state_relevance[timing.timing_state] if timing.timing_state is not None else 0.0,
                "timing_completeness": timing.timing_completeness,
            }
            for horizon in timing.eligible_horizons:
                if horizon in ("medium", "fast") and timing.exact_at is None:
                    excluded["no_exact_hit_in_window"] += 1
                    warnings_seen.append("no_exact_hit_in_window")
                    continue
                technique_priority = rule.priority_by_horizon[horizon]
                feature_model = HorizonCandidateFeatureScores(
                    **features,
                    technique_priority=technique_priority,
                )
                impact = _round6(sum(getattr(feature_model, key) * impact_weights[key] for key in impact_weights))
                if impact < getattr(canon.min_candidate_impact, horizon):
                    excluded["below_impact_threshold"] += 1
                    warnings_seen.append("below_impact_threshold")
                    continue
                candidate = HorizonCandidate(
                    activation_id=evidence.id,
                    horizon=horizon,
                    technique=evidence.technique,
                    technique_family=evidence.technique_family,
                    polarity=evidence.polarity,
                    target_type=evidence.target_type,
                    target_key_normalized=normalized_target_key,
                    source_planet_normalized=_normalize_planet(evidence.source_planet),
                    target_planet_normalized=_normalize_planet(evidence.target_planet),
                    house_target_key=str(evidence.house) if evidence.target_type == "house" and evidence.house is not None else None,
                    timing=timing,
                    technical_spheres=mapping.technical_spheres,
                    product_spheres=mapping.product_spheres,
                    theme_keys=mapping.theme_keys,
                    target_family_convergence_count=family_count,
                    feature_scores=feature_model,
                    impact_score=impact,
                )
                candidates_by_horizon[horizon].append(candidate)

        pre_counts = {horizon: len(items) for horizon, items in candidates_by_horizon.items()}
        bounded_by_horizon: dict[TodayV2HorizonId, list[HorizonCandidate]] = {}
        for horizon, items in candidates_by_horizon.items():
            ordered = sorted(items, key=lambda candidate: candidate.tie_break_key())
            bounded_by_horizon[horizon] = ordered[: canon.limits.max_candidates_per_horizon]
        post_counts = {horizon: len(items) for horizon, items in bounded_by_horizon.items()}

        diagnostics = diagnostics.model_copy(update={
            "candidate_count": sum(pre_counts.values()),
            "per_horizon_pre_bound_counts": pre_counts,
            "per_horizon_post_bound_counts": post_counts,
            "excluded_counts_by_reason": dict(sorted(excluded.items())),
        })

        distinct_warnings = list(dict.fromkeys(warnings_seen))
        if not bounded_by_horizon["long"]:
            return HorizonSelectionResult(selection=None, reason="missing_long", diagnostics=diagnostics, warnings=distinct_warnings)
        if not bounded_by_horizon["medium"]:
            return HorizonSelectionResult(selection=None, reason="missing_medium", diagnostics=diagnostics, warnings=distinct_warnings)
        if not bounded_by_horizon["fast"]:
            return HorizonSelectionResult(selection=None, reason="missing_fast", diagnostics=diagnostics, warnings=distinct_warnings)

        best_triple: SelectedHorizonTriple | None = None
        best_key: tuple[float, float, float, int, tuple[str, str, str]] | None = None
        combinations = 0
        for long_candidate, medium_candidate, fast_candidate in product(
            bounded_by_horizon["long"], bounded_by_horizon["medium"], bounded_by_horizon["fast"]
        ):
            combinations += 1
            if combinations > canon.limits.max_anchor_combinations:
                raise AssertionError("combinations exceeded canon limit")
            if len({long_candidate.activation_id, medium_candidate.activation_id, fast_candidate.activation_id}) != 3:
                continue
            pair_scores = {
                "long_medium": self._pair_overlap(long_candidate, medium_candidate),
                "medium_fast": self._pair_overlap(medium_candidate, fast_candidate),
                "long_fast": self._pair_overlap(long_candidate, fast_candidate),
            }
            if pair_scores["long_medium"] < canon.min_pair_overlap.long_medium:
                continue
            if pair_scores["medium_fast"] < canon.min_pair_overlap.medium_fast:
                continue
            if pair_scores["long_fast"] < canon.min_pair_overlap.long_fast:
                continue
            mean_overlap = _round6(sum(pair_scores.values()) / 3.0)
            if mean_overlap < canon.min_pair_overlap.triple_mean:
                continue
            mean_impact = _round6((long_candidate.impact_score + medium_candidate.impact_score + fast_candidate.impact_score) / 3.0)
            unique_family_count = len({long_candidate.technique_family, medium_candidate.technique_family, fast_candidate.technique_family})
            family_diversity_score = _family_diversity_score(unique_family_count)
            total_score = _triple_total_score(
                mean_impact=mean_impact,
                mean_overlap=mean_overlap,
                family_diversity_score=family_diversity_score,
            )
            activation_ids = (
                long_candidate.activation_id,
                medium_candidate.activation_id,
                fast_candidate.activation_id,
            )
            sort_key = _triple_sort_key(
                total_score=total_score,
                mean_overlap=mean_overlap,
                mean_impact=mean_impact,
                unique_family_count=unique_family_count,
                activation_ids=activation_ids,
            )
            if best_key is not None and sort_key >= best_key:
                continue
            shared_themes = _intersection_in_first_order(long_candidate.theme_keys, [medium_candidate.theme_keys, fast_candidate.theme_keys])
            if not shared_themes:
                shared_themes = _ordered_union_by_frequency([long_candidate.theme_keys, medium_candidate.theme_keys, fast_candidate.theme_keys])[: canon.limits.max_theme_keys_per_candidate]
            shared_products = _intersection_in_first_order(long_candidate.product_spheres, [medium_candidate.product_spheres, fast_candidate.product_spheres])
            if not shared_products:
                shared_products = _ordered_union_by_frequency([list(long_candidate.product_spheres), list(medium_candidate.product_spheres), list(fast_candidate.product_spheres)])[: canon.limits.max_product_spheres_per_candidate]
            triple = SelectedHorizonTriple(
                items=[
                    self._to_anchor(long_candidate),
                    self._to_anchor(medium_candidate),
                    self._to_anchor(fast_candidate),
                ],
                pair_overlap_scores=pair_scores,
                mean_overlap=mean_overlap,
                mean_impact=mean_impact,
                family_diversity_score=family_diversity_score,
                unique_family_count=unique_family_count,
                total_score=total_score,
                shared_theme_keys=shared_themes,
                shared_product_spheres=shared_products,
                unique_anchor_activation_ids=list(activation_ids),
            )
            best_key = sort_key
            best_triple = triple

        diagnostics = diagnostics.model_copy(update={"combinations_evaluated": combinations})
        if best_triple is None:
            return HorizonSelectionResult(selection=None, reason="no_coherent_triple", diagnostics=diagnostics, warnings=distinct_warnings)
        return HorizonSelectionResult(selection=best_triple, reason="selected", diagnostics=diagnostics, warnings=distinct_warnings)

    def _pair_overlap(self, left: HorizonCandidate, right: HorizonCandidate) -> float:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE.HorizonSelectionService._pair_overlap
        # purpose: Compute canon-driven overlap between two candidate anchors.
        # inputs: left and right candidate anchors.
        # returns: clamped 0..1 overlap score rounded before every threshold comparison.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-SERVICE.HorizonSelectionService._pair_overlap
        canon = load_horizon_selection_canon()
        score = 0.0
        if (left.target_type, left.target_key_normalized) == (right.target_type, right.target_key_normalized):
            score += canon.story_overlap_weights.same_target
        if set(left.theme_keys) & set(right.theme_keys):
            score += canon.story_overlap_weights.shared_theme
        if set(left.product_spheres) & set(right.product_spheres):
            score += canon.story_overlap_weights.shared_product_sphere
        left_planets = {value for value in (left.source_planet_normalized, left.target_planet_normalized) if value}
        right_planets = {value for value in (right.source_planet_normalized, right.target_planet_normalized) if value}
        same_house_target = left.target_type == right.target_type == "house" and left.house_target_key is not None and left.house_target_key == right.house_target_key
        if left_planets & right_planets or same_house_target:
            score += canon.story_overlap_weights.same_planet_or_house
        if set(left.technical_spheres) & set(right.technical_spheres):
            score += canon.story_overlap_weights.shared_technical_sphere
        return _round6(max(0.0, min(1.0, score)))

    def _to_anchor(self, candidate: HorizonCandidate) -> SelectedHorizonAnchor:
        return SelectedHorizonAnchor(
            horizon=candidate.horizon,
            activation_id=candidate.activation_id,
            technique=candidate.technique,
            technique_family=candidate.technique_family,
            polarity=candidate.polarity,
            target_type=candidate.target_type,
            target_key_normalized=candidate.target_key_normalized,
            source_planet_normalized=candidate.source_planet_normalized,
            target_planet_normalized=candidate.target_planet_normalized,
            house_target_key=candidate.house_target_key,
            timing=candidate.timing,
            technical_spheres=candidate.technical_spheres,
            product_spheres=candidate.product_spheres,
            theme_keys=candidate.theme_keys,
            target_family_convergence_count=candidate.target_family_convergence_count,
            feature_scores=candidate.feature_scores,
            impact_score=candidate.impact_score,
        )
# END_BLOCK: HORIZON_SELECTION_SERVICE


__all__ = ["HorizonSelectionService"]
