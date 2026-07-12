# ############################################################################
# AI_HEADER: HORIZON_GUIDANCE_BUILDERS — deterministic builders for B2B2 guidance.
# ROLE: Owns stable ordered intersection, manifestations, claim selection,
#       action eligibility, and technique construction. Consumed by service
#       and validator. No import from validator or Today/Semantic.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-GUIDANCE-BUILDERS
# purpose: Provide pure deterministic builder functions for manifestations,
#          strength/risk claims, action selection, and technique explanations.
#          Owns the exact expected-copy helpers shared by the validator.
# owns:
#   - apps/api/app/services/horizon_guidance_builders.py
# inputs: Context, canon, anchor, and selection data.
# outputs: Typed TodayV2 sub-models (manifestations, grounded items, etc.).
# dependencies: typing stdlib, B1/B2A/B2B schemas, guidance formatter, canons.
# side_effects: reads cached content canon only.
# emitted_logs: none.
# invariants:
#   - All functions are deterministic for identical inputs.
#   - No import from horizon_claim_validator or horizon_claim_policy.
#   - No import from Today frontend or Semantic services.
# failure_policy: raises HorizonGuidanceError on missing canon entries.
# END_MODULE_CONTRACT: M-HORIZON-GUIDANCE-BUILDERS

# START_MODULE_MAP: M-HORIZON-GUIDANCE-BUILDERS
# public_entrypoints:
#   - ordered_intersection
#   - build_manifestations
#   - build_eligible_claims
#   - assign_claims
#   - build_actions
#   - build_technique_explanation
#   - determine_claim_kind
#   - statement_text_for_fact
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_service.py
#   - apps/api/tests/test_horizon_claim_validator.py
# END_MODULE_MAP: M-HORIZON-GUIDANCE-BUILDERS

# START_BLOCK: BUILDERS_IMPORTS
from __future__ import annotations

from typing import Sequence

from app.schemas.horizon_content_canon import HorizonContentCanonBundle
from app.schemas.horizon_guidance import HorizonGuidanceError
from app.schemas.horizon_selection import SelectedHorizonAnchor
from app.schemas.personal_fact_pack import PersonalFact, PersonalFactPack
from app.schemas.today_horizons import (
    TodayV2HorizonActions,
    TodayV2HorizonId,
    TodayV2HorizonTiming,
    TodayV2HorizonTone,
    TodayV2GroundedItem,
    TodayV2Manifestation,
    TodayV2ProductSphereKey,
    TodayV2Provenance,
    TodayV2TechniqueExplanation,
)
from app.services.horizon_guidance_formatter import HorizonGuidanceFormatter

# END_BLOCK: BUILDERS_IMPORTS


# START_BLOCK: BUILDERS_ORDERED_INTERSECTION
def ordered_intersection(
    ordered: list[str], candidates: list[str]
) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-BUILDERS.ordered_intersection
    # purpose: Return items from ordered that also appear in candidates.
    # inputs: ordered - priority list; candidates - available set.
    # returns: List preserving ordered, filtered by candidates.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: returns empty list when no intersection.
    # END_FUNCTION_CONTRACT: F-M-BUILDERS.ordered_intersection
    seen = set(candidates)
    return [item for item in ordered if item in seen]


# END_BLOCK: BUILDERS_ORDERED_INTERSECTION


# START_BLOCK: BUILDERS_MANIFESTATIONS
def build_manifestations(
    *,
    horizon: TodayV2HorizonId,
    likely_spheres: list[TodayV2ProductSphereKey],
    activation_id: str,
    canon: HorizonContentCanonBundle,
    formatter: HorizonGuidanceFormatter,
) -> list[TodayV2Manifestation]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_manifestations
    # purpose: Build one manifestation per likely sphere, split into condition+body.
    # inputs: horizon, likely_spheres, activation_id, canon, formatter.
    # returns: list of TodayV2Manifestation in sphere order, exactly one per sphere.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonGuidanceError for unknown sphere.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_manifestations
    manifestations: list[TodayV2Manifestation] = []
    for sphere in likely_spheres:
        sphere_lang = canon.language.product_spheres.get(sphere)
        if sphere_lang is None:
            raise HorizonGuidanceError(
                "unknown_entity_label", "sphere"
            )
        condition, body = formatter.split_manifestation(
            sphere_lang.manifestation_body,
            canon.language.conditional_policy.required_prefixes,
        )
        manifestations.append(
            TodayV2Manifestation(
                id=f"manifestation.{horizon}.{sphere}",
                title=sphere_lang.manifestation_title,
                body=body,
                condition=condition,
                sphere_keys=[sphere],
                provenance=TodayV2Provenance(
                    activation_ids=[activation_id],
                    natal_fact_ids=[],
                    profile_fact_ids=[],
                    sphere_keys=[sphere],
                ),
            )
        )
    return manifestations


# END_BLOCK: BUILDERS_MANIFESTATIONS


# START_BLOCK: BUILDERS_CLAIMS
def build_eligible_claims(
    fact_pack: PersonalFactPack,
) -> list[PersonalFact]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_eligible_claims
    # purpose: Filter fact pack to strength/risk facts only.
    # inputs: fact_pack - full personal fact pack.
    # returns: list of eligible fact entries.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_eligible_claims
    return [f for f in fact_pack.facts if f.kind in {"strength", "risk"}]


def statement_text_for_fact(
    fact: PersonalFact,
    canon: HorizonContentCanonBundle,
) -> str:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.statement_text_for_fact
    # purpose: Look up the canonical statement text for a fact.
    # inputs: fact - personal fact; canon - content bundle.
    # returns: canonical Russian statement text.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonGuidanceError if statement key is missing.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.statement_text_for_fact
    statement = canon.language.personal_statements.get(fact.statement_key)
    if statement is None:
        raise HorizonGuidanceError(
            "unknown_claim_statement", "statement"
        )
    return statement.text


def assign_claims(
    *,
    horizon: TodayV2HorizonId,
    anchor: SelectedHorizonAnchor,
    eligible_facts: Sequence[PersonalFact],
    used_fact_ids: set[str],
    horizon_theme: str,
    likely_spheres: list[TodayV2ProductSphereKey],
    canon: HorizonContentCanonBundle,
) -> tuple[TodayV2GroundedItem | None, TodayV2GroundedItem | None]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.assign_claims
    # purpose: Deterministically select top-ranked unused strength and risk
    #          facts matching this horizon/anchor/theme/sphere.
    # inputs: horizon, anchor, eligible_facts, used_fact_ids, horizon_theme,
    #         likely_spheres, canon.
    # returns: (strength, risk) typed items or None per kind.
    # side_effects: mutates used_fact_ids set.
    # emitted_logs: none.
    # error_behavior: raises HorizonGuidanceError for missing statement.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.assign_claims
    sphere_set = set(likely_spheres)
    anchor_id = anchor.activation_id

    def _rank(fact: PersonalFact) -> tuple[float, int, str]:
        order = 0
        for i, rule in enumerate(canon.patterns.patterns):
            if rule.statement_key == fact.statement_key:
                order = rule.order
                break
        return (-fact.confidence, order, fact.id)

    eligible_here: list[PersonalFact] = []
    for fact in eligible_facts:
        if fact.id in used_fact_ids:
            continue
        if horizon not in fact.horizon_ids:
            continue
        if anchor_id not in fact.activation_ids:
            continue
        if not set(fact.theme_keys) & set(anchor.theme_keys):
            continue
        if not set(fact.sphere_keys) & sphere_set:
            continue
        if fact.statement_key not in canon.language.personal_statements:
            continue
        eligible_here.append(fact)

    eligible_here.sort(key=_rank)
    strength: TodayV2GroundedItem | None = None
    risk: TodayV2GroundedItem | None = None

    for fact in eligible_here:
        if fact.id in used_fact_ids:
            continue
        statement = canon.language.personal_statements.get(fact.statement_key)
        if statement is None:
            continue
        text = statement.text
        if fact.kind == "strength" and strength is None:
            isphere = ordered_intersection(
                likely_spheres, list(fact.sphere_keys)
            )
            strength = TodayV2GroundedItem(
                id=f"claim.{horizon}.{fact.id}",
                kind="strength",
                text=text,
                conditional=False,
                provenance=TodayV2Provenance(
                    activation_ids=[anchor_id],
                    natal_fact_ids=[fact.id],
                    profile_fact_ids=[],
                    sphere_keys=isphere,
                ),
            )
            used_fact_ids.add(fact.id)
        elif fact.kind == "risk" and risk is None:
            isphere = ordered_intersection(
                likely_spheres, list(fact.sphere_keys)
            )
            risk = TodayV2GroundedItem(
                id=f"claim.{horizon}.{fact.id}",
                kind="risk",
                text=text,
                conditional=False,
                provenance=TodayV2Provenance(
                    activation_ids=[anchor_id],
                    natal_fact_ids=[fact.id],
                    profile_fact_ids=[],
                    sphere_keys=isphere,
                ),
            )
            used_fact_ids.add(fact.id)
        if strength is not None and risk is not None:
            break

    return strength, risk


# END_BLOCK: BUILDERS_CLAIMS


# START_BLOCK: BUILDERS_ACTIONS
def build_actions(
    *,
    horizon: TodayV2HorizonId,
    anchor: SelectedHorizonAnchor,
    horizon_theme: str,
    tone: TodayV2HorizonTone,
    sphere_verdicts: dict[TodayV2ProductSphereKey, str],
    timing: TodayV2HorizonTiming,
    valid_until_label: str,
    canon: HorizonContentCanonBundle,
) -> TodayV2HorizonActions:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_actions
    # purpose: Select compatible do/avoid action templates per horizon
    #          theme, tone, and sphere verdicts.
    # inputs: horizon, anchor, horizon_theme, tone, sphere_verdicts, timing,
    #         valid_until_label, canon.
    # returns: typed TodayV2HorizonActions with ordered do/avoid items.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonGuidanceError on insufficient safe actions.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_actions
    canon_action = canon.actions.themes.get(horizon_theme)
    if canon_action is None:
        raise HorizonGuidanceError(
            "insufficient_safe_actions", "theme"
        )
    lists = getattr(canon_action, horizon)
    sphere_set = set(anchor.product_spheres)
    heading = canon.language.horizons[horizon].actions_heading

    def _compatible(template: object) -> bool:
        t = template
        if tone not in t.tones:
            return False
        common = set(t.sphere_keys) & sphere_set
        if not common:
            return False
        safety = canon.actions.safety_classes.get(t.safety_class)
        if safety is None:
            return False
        for sphere in common:
            verdict = sphere_verdicts.get(sphere)
            if verdict is not None and verdict not in safety.compatible_verdicts:
                return False
        return True

    dos = [t for t in lists.do if _compatible(t)]
    avoids = [t for t in lists.avoid if _compatible(t)]

    range_spec = {
        "long": (1, 2, 1, 2),
        "medium": (2, 3, 1, 3),
        "fast": (1, 1, 1, 2),
    }[horizon]
    min_do, max_do, min_avoid, max_avoid = range_spec

    if len(dos) < min_do or len(avoids) < min_avoid:
        raise HorizonGuidanceError(
            "insufficient_safe_actions",
            f"items.{horizon}.actions",
        )

    dos = dos[:max_do]
    avoids = avoids[:max_avoid]

    def _build_items(templates, kind: str) -> list[TodayV2GroundedItem]:
        items: list[TodayV2GroundedItem] = []
        seen_ids: set[str] = set()
        for t in templates:
            if t.id in seen_ids:
                continue
            seen_ids.add(t.id)
            isphere = ordered_intersection(
                list(anchor.product_spheres), list(t.sphere_keys)
            )
            items.append(
                TodayV2GroundedItem(
                    id=t.id,
                    kind=kind,
                    text=t.text,
                    conditional=t.conditional,
                    provenance=TodayV2Provenance(
                        activation_ids=[anchor.activation_id],
                        natal_fact_ids=[],
                        profile_fact_ids=[],
                        sphere_keys=isphere,
                    ),
                )
            )
        return items

    do_items = _build_items(dos, "action")
    avoid_items = _build_items(avoids, "avoid")

    return TodayV2HorizonActions(
        heading=heading,
        valid_until=timing.active_until,
        valid_until_label=valid_until_label or "",
        do=do_items,
        avoid=avoid_items,
    )


# END_BLOCK: BUILDERS_ACTIONS


# START_BLOCK: BUILDERS_TECHNIQUE
def build_technique_explanation(
    *,
    horizon: TodayV2HorizonId,
    anchor: SelectedHorizonAnchor,
    horizon_theme: str,
    timing: TodayV2HorizonTiming,
    active_from_label: str,
    active_until_label: str,
    exact_at_label: str | None,
    valid_until_label: str,
    timezone_suffix: str,
    range_label: str,
    peak_label: str | None,
    state_label: str,
    tone: TodayV2HorizonTone,
    likely_spheres: list[TodayV2ProductSphereKey],
    canon: HorizonContentCanonBundle,
    formatter: HorizonGuidanceFormatter,
) -> TodayV2TechniqueExplanation:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_technique_explanation
    # purpose: Build a technique explanation with fully resolved display labels
    #          and timing. Uses presentation labels, never raw machine values.
    # inputs: All display labels, canon, and formatter.
    # returns: typed TodayV2TechniqueExplanation.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonGuidanceError for unknown technique/theme,
    #   missing source planet, or unresolved template placeholders.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-BUILDERS.build_technique_explanation
    technique = anchor.technique
    tech_lang = canon.language.techniques.get(technique)
    if tech_lang is None:
        raise HorizonGuidanceError(
            "unknown_entity_label", "technique"
        )

    theme_lang = canon.language.themes.get(horizon_theme)
    if theme_lang is None:
        raise HorizonGuidanceError(
            "unknown_theme", "technique"
        )

    theme_label = theme_lang.label
    tech_template = tech_lang.why_it_matters_template
    source_label_str = ""
    if "{source_label}" in tech_template:
        source_label_str = formatter.source_label(
            anchor.source_planet_normalized
        )
    target_label_str = formatter.target_label(
        anchor.target_type, anchor.target_key_normalized
    )

    sphere_label_str = ""
    if likely_spheres:
        sphere_lang = canon.language.product_spheres.get(likely_spheres[0])
        if sphere_lang:
            sphere_label_str = sphere_lang.label

    why = tech_lang.why_it_matters_template
    why = why.replace("{theme_label}", theme_label)
    why = why.replace("{range_label}", range_label)
    _peak_str = peak_label or ""
    why = why.replace("{peak_label}", _peak_str)
    why = why.replace("{state_label}", state_label)
    why = why.replace("{source_label}", source_label_str)
    why = why.replace("{target_label}", target_label_str)
    why = why.replace("{sphere_label}", sphere_label_str)
    why = why.replace("{active_from}", active_from_label)
    why = why.replace("{active_until}", active_until_label)
    _exact_str = exact_at_label or ""
    why = why.replace("{exact_at}", _exact_str)

    if "{" in why and "}" in why:
        import re as _re
        remaining = _re.findall(r"\{[a-z_]+\}", why)
        if remaining:
            raise HorizonGuidanceError(
                "unresolved_placeholder",
                "technique.why_it_matters_now",
            )

    return TodayV2TechniqueExplanation(
        technique=technique,
        label=tech_lang.label,
        what_it_is=tech_lang.what_it_is,
        why_it_matters_now=why,
        timing=timing,
        activation_ids=[anchor.activation_id],
    )


# END_BLOCK: BUILDERS_TECHNIQUE


__all__ = [
    "ordered_intersection",
    "build_manifestations",
    "build_eligible_claims",
    "statement_text_for_fact",
    "assign_claims",
    "build_actions",
    "build_technique_explanation",
]
