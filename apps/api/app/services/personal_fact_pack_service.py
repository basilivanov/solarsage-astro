# ############################################################################
# AI_HEADER: PERSONAL_FACT_PACK_SERVICE — pure deterministic B2B1 fact extraction.
# ROLE: Grounds selected sphere facts and strictly matched natal strength/risk facts without exposing raw personal inputs.
# ############################################################################

# START_MODULE_CONTRACT: M-PERSONAL-FACT-PACK-SERVICE
# purpose: Convert accepted B2A selection plus exact natal/scoring facts into a privacy-safe internal fact pack.
# owns:
#   - apps/api/app/services/personal_fact_pack_service.py
# inputs: SelectedHorizonTriple, ActivationLayer, ScoringV2Result, and NatalContextData.
# outputs: Deterministic PersonalFactPack containing sphere/strength/risk facts only.
# dependencies: math/re stdlib, B2A schemas, B2B content canon/personal fact schemas, natal/scoring schemas.
# side_effects: reads cached content canon only.
# emitted_logs: none.
# invariants:
#   - Only selected activation-linked non-zero scoring contributions can ground sphere facts.
#   - Natal matching uses only planets/aspects and emits generic source ids without raw values.
# failure_policy: invalid internal integrity raises compact ValueError; weak/unlinked rules are omitted.
# END_MODULE_CONTRACT: M-PERSONAL-FACT-PACK-SERVICE

# START_MODULE_MAP: M-PERSONAL-FACT-PACK-SERVICE
# public_entrypoints:
#   - PersonalFactPackService.build
# semantic_blocks:
#   - PERSONAL_FACT_PACK_HELPERS: normalization, integrity, and finite predicate matching.
#   - PERSONAL_FACT_PACK_SERVICE: stable sphere and personal fact construction.
# owned_tests:
#   - apps/api/tests/test_personal_fact_pack_service.py
# END_MODULE_MAP: M-PERSONAL-FACT-PACK-SERVICE

# START_BLOCK: PERSONAL_FACT_PACK_HELPERS
from __future__ import annotations

import math
import re

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.horizon_content_canon import (
    AspectPredicate,
    PersonalPatternRule,
    PlanetInHousePredicate,
    PlanetInSignPredicate,
    PLANET_ORDER,
)
from app.schemas.horizon_selection import SelectedHorizonAnchor, SelectedHorizonTriple
from app.schemas.natal import NatalChartAspect, NatalChartPlanet, NatalContextData
from app.schemas.personal_fact_pack import PersonalFact, PersonalFactPack
from app.schemas.scoring_v2 import ScoringV2Result
from app.services.horizon_content_canon_service import load_horizon_content_canons

PREFIX_RE = re.compile(r"^(?:TRANSIT_|NATAL_)+", re.IGNORECASE)


def _round6(value: float) -> float:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._round6
    # purpose: Serialize computed fact confidence at the fixed B2B1 precision.
    # inputs: value - finite computed confidence.
    # returns: six-decimal rounded float.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._round6
    return round(value + 0.0, 6)


def _normalize_planet(value: str | None) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._normalize_planet
    # purpose: Apply the accepted B2A prefix-stripping comparison normalization without changing wire values.
    # inputs: value - raw optional planet identifier.
    # returns: normalized uppercase planet id or null.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._normalize_planet
    if value is None:
        return None
    normalized = PREFIX_RE.sub("", value.strip().upper())
    return normalized or None


def _normalize_token(value: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._normalize_token
    # purpose: Normalize controlled sign/aspect tokens for finite predicate comparisons.
    # inputs: value - raw controlled token.
    # returns: trimmed uppercase token.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._normalize_token
    return value.strip().upper()


def _canonical_pair(left: str, right: str) -> tuple[str, str]:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._canonical_pair
    # purpose: Return a stable known-planet ordering for aspect comparison and generic source ids.
    # inputs: left/right - normalized planet ids.
    # returns: canonical pair.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for unknown or duplicate points without echoing raw values.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._canonical_pair
    if left not in PLANET_ORDER or right not in PLANET_ORDER or left == right:
        raise ValueError("natal.aspect: invalid normalized points")
    return tuple(sorted((left, right), key=PLANET_ORDER.index))


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._ordered_unique
    # purpose: Deduplicate provenance/list values while retaining the first canonical traversal order.
    # inputs: values - ordered machine values.
    # returns: first-occurrence tuple.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._ordered_unique
    return tuple(dict.fromkeys(values))


def _activation_map(layer: ActivationLayer) -> dict[str, ActivationEvidence]:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._activation_map
    # purpose: Index activation evidence and reject duplicate internal identities before selected lookup.
    # inputs: layer - source activation layer.
    # returns: activation id to evidence mapping.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for duplicate activation ids.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._activation_map
    mapping = {activation.id: activation for activation in layer.activations}
    if len(mapping) != len(layer.activations):
        raise ValueError("activation_layer.activations: duplicate ids")
    return mapping


def _validate_anchor_evidence(anchor: SelectedHorizonAnchor, evidence: ActivationEvidence) -> None:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._validate_anchor_evidence
    # purpose: Confirm selected anchor identity/timing remains identical to its active activation evidence.
    # inputs: anchor - selected B2A anchor; evidence - matching source activation.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError with stable anchor id on integrity mismatch.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._validate_anchor_evidence
    if not evidence.active:
        raise ValueError(f"selected-anchor-inactive:{anchor.activation_id}")
    same_identity = (
        evidence.technique == anchor.technique
        and evidence.technique_family == anchor.technique_family
        and evidence.target_type == anchor.target_type
        and _normalize_planet(evidence.target_key) == anchor.target_key_normalized
        and _normalize_planet(evidence.source_planet) == anchor.source_planet_normalized
        and _normalize_planet(evidence.target_planet) == anchor.target_planet_normalized
    )
    same_timing = (
        evidence.active_from == anchor.timing.active_from
        and evidence.exact_at == anchor.timing.exact_at
        and evidence.active_until == anchor.timing.active_until
    )
    if not same_identity or not same_timing:
        raise ValueError(f"selected-anchor-integrity:{anchor.activation_id}")


def _validate_natal_context(
    natal_context: NatalContextData,
) -> tuple[dict[str, NatalChartPlanet], tuple[NatalChartAspect, ...]]:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._validate_natal_context
    # purpose: Build finite permitted natal lookup inputs and reject duplicate planets or invalid aspect orbs.
    # inputs: natal_context - cached natal context.
    # returns: normalized planet lookup and original aspect tuple for finite matching.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError on invalid structural natal data without raw values.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._validate_natal_context
    planets: dict[str, NatalChartPlanet] = {}
    for planet in natal_context.planets:
        normalized = _normalize_planet(planet.name)
        if normalized is None or normalized in planets:
            raise ValueError("natal.planets: invalid or duplicate normalized name")
        planets[normalized] = planet
    for aspect in natal_context.aspects:
        if not math.isfinite(aspect.orb) or aspect.orb < 0:
            raise ValueError("natal.aspects: invalid orb")
    return planets, tuple(natal_context.aspects)


def _match_rule(
    rule: PersonalPatternRule,
    planets: dict[str, NatalChartPlanet],
    aspects: tuple[NatalChartAspect, ...],
) -> tuple[float, tuple[str, ...]] | None:
    # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._match_rule
    # purpose: Evaluate one finite all-AND natal predicate rule and return confidence plus generic sources.
    # inputs: rule - canonical pattern; planets/aspects - validated exact natal data.
    # returns: confidence and generic natal source ids, or null when any predicate does not match.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError only for invalid internal normalized aspect state.
    # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE._match_rule
    qualities: list[float] = []
    sources: list[str] = []
    for predicate in rule.requirements:
        if isinstance(predicate, PlanetInSignPredicate):
            planet = planets.get(predicate.planet)
            if planet is None or _normalize_token(planet.sign) not in predicate.signs:
                return None
            qualities.append(1.0)
            sources.append(f"natal:planet:{predicate.planet.lower()}")
        elif isinstance(predicate, PlanetInHousePredicate):
            planet = planets.get(predicate.planet)
            if planet is None or planet.house not in predicate.houses:
                return None
            qualities.append(1.0)
            sources.append(f"natal:house:{predicate.planet.lower()}")
        else:
            required_pair = _canonical_pair(predicate.point_a, predicate.point_b)
            matches: list[tuple[float, tuple[str, str], str]] = []
            for aspect in aspects:
                left = _normalize_planet(aspect.planet_a)
                right = _normalize_planet(aspect.planet_b)
                if left is None or right is None:
                    continue
                pair = _canonical_pair(left, right)
                aspect_type = _normalize_token(aspect.aspect_type)
                if pair == required_pair and aspect_type in predicate.aspect_types and aspect.orb <= predicate.max_orb:
                    matches.append((aspect.orb, pair, aspect_type))
            if not matches:
                return None
            orb, pair, _ = min(matches, key=lambda item: (item[0], item[1], item[2]))
            qualities.append(1.0 - 0.25 * min(orb / predicate.max_orb, 1.0))
            sources.append(f"natal:aspect:{pair[0].lower()}:{pair[1].lower()}")
    confidence = _round6(rule.base_confidence * min(qualities))
    if confidence < rule.min_confidence:
        return None
    return confidence, _ordered_unique(sources)


# END_BLOCK: PERSONAL_FACT_PACK_HELPERS


# START_BLOCK: PERSONAL_FACT_PACK_SERVICE
class PersonalFactPackService:
    def build(
        self,
        *,
        selection: SelectedHorizonTriple,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
    ) -> PersonalFactPack:
        # START_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE.PersonalFactPackService.build
        # purpose: Build an ordered privacy-safe B2B1 fact pack from accepted selected anchors only.
        # inputs: selection, activation_layer, scoring_result, natal_context - exact typed B2A/natal inputs.
        # returns: deterministic PersonalFactPack with sphere facts followed by matched strength/risk facts.
        # side_effects: reads cached content canon only.
        # emitted_logs: none.
        # error_behavior: raises ValueError for invalid selected/scoring/natal integrity; omits weak/unlinked patterns.
        # END_FUNCTION_CONTRACT: F-M-PERSONAL-FACT-PACK-SERVICE.PersonalFactPackService.build
        bundle = load_horizon_content_canons()
        activation_by_id = _activation_map(activation_layer)
        selected_ids = tuple(anchor.activation_id for anchor in selection.items)
        facts: list[PersonalFact] = []
        for anchor in selection.items:
            evidence = activation_by_id.get(anchor.activation_id)
            if evidence is None:
                raise ValueError(f"selected-anchor-missing:{anchor.activation_id}")
            _validate_anchor_evidence(anchor, evidence)
            linked_amount_found = False
            for technical_sphere in anchor.technical_spheres:
                score = scoring_result.sphere_scores.get(technical_sphere)
                if score is None:
                    continue
                if score.key != technical_sphere:
                    raise ValueError("scoring.sphere_score: key mismatch")
                for contribution in score.contributions:
                    if not math.isfinite(contribution.amount):
                        raise ValueError("scoring.contribution: non-finite amount")
                    if contribution.source == "activation" and contribution.source_id == anchor.activation_id:
                        if contribution.sphere != technical_sphere or contribution.amount == 0:
                            raise ValueError("scoring.contribution: invalid selected anchor linkage")
                        linked_amount_found = True
            if not linked_amount_found:
                raise ValueError(f"selected-anchor-without-scoring-contribution:{anchor.activation_id}")
            for sphere in anchor.product_spheres:
                facts.append(
                    PersonalFact(
                        id=f"pf:v1:sphere:{anchor.horizon}:{sphere}",
                        kind="sphere",
                        statement_key=f"sphere.active.{sphere}",
                        confidence=anchor.impact_score,
                        horizon_ids=(anchor.horizon,),
                        theme_keys=tuple(anchor.theme_keys),
                        activation_ids=(anchor.activation_id,),
                        natal_source_ids=(),
                        profile_source_ids=(),
                        sphere_keys=(sphere,),
                    )
                )
        planets, aspects = _validate_natal_context(natal_context)
        for rule in bundle.patterns.patterns:
            linked: list[tuple[SelectedHorizonAnchor, tuple[str, ...], tuple[str, ...]]] = []
            for anchor in selection.items:
                themes = tuple(theme for theme in anchor.theme_keys if theme in rule.theme_keys)
                spheres = tuple(sphere for sphere in anchor.product_spheres if sphere in rule.sphere_keys)
                if themes and spheres:
                    linked.append((anchor, themes, spheres))
            if not linked:
                continue
            matched = _match_rule(rule, planets, aspects)
            if matched is None:
                continue
            confidence, natal_sources = matched
            facts.append(
                PersonalFact(
                    id=f"pf:v1:{rule.kind}:{rule.id}",
                    kind=rule.kind,
                    statement_key=rule.statement_key,
                    confidence=confidence,
                    horizon_ids=tuple(item[0].horizon for item in linked),
                    theme_keys=_ordered_unique([theme for _, themes, _ in linked for theme in themes]),
                    activation_ids=tuple(item[0].activation_id for item in linked),
                    natal_source_ids=natal_sources,
                    profile_source_ids=(),
                    sphere_keys=_ordered_unique([sphere for _, _, spheres in linked for sphere in spheres]),
                )
            )
        return PersonalFactPack(
            schema_version="personal-fact-pack.v1",
            selected_activation_ids=selected_ids,
            facts=tuple(facts),
        )


# END_BLOCK: PERSONAL_FACT_PACK_SERVICE


__all__ = ["PersonalFactPackService"]
