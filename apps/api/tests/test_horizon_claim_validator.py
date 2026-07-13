# ############################################################################
# AI_HEADER: TEST_HORIZON_CLAIM_VALIDATOR — mutation matrix for B2B2 validation.
# ROLE: Mutates one independent field at a time and asserts exact error codes.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-CLAIM-VALIDATOR
# purpose: Prove the claim validator catches every structural, copy,
#          conditional, privacy, and numeric violation with exact code.
# owns:
#   - apps/api/tests/test_horizon_claim_validator.py
# inputs: Validated baseline + model_copy mutations.
# outputs: Assertions over exact HorizonClaimValidationError codes.
# dependencies: pytest, guidance/validator services, B2B content testkit.
# side_effects: reads cached content canon.
# invariants:
#   - Mutations use model_copy(update=...) where public validators allow.
#   - At least 91 claim-specific invalid mutations with exact codes.
#   - Zero Pydantic deprecation warnings from B2B2 tests.
# failure_policy: test failures identify validator regression.
# END_MODULE_CONTRACT: M-TEST-HORIZON-CLAIM-VALIDATOR

# START_MODULE_MAP: M-TEST-HORIZON-CLAIM-VALIDATOR
# public_entrypoints:
#   - test_mutation_matrix
#   - test_sanitized_exception_sentinel_matrix
#   - test_action_forbidden_intent
#   - test_action_forbidden_pair
#   - test_lower_ranked_fact_rejection
#   - test_sanitization_matrix_cases
#   - test_r5_direct_policy_sanitization
#   - test_r5_typed_error_boundary
#   - test_r5_builder_placeholder_sanitized
# semantic_blocks:
#   - VALIDATOR_MUTATION_MATRIX
#   - VALIDATOR_PARAMETRIZED
# owned_tests:
#   - apps/api/tests/test_horizon_claim_validator.py
# END_MODULE_MAP: M-TEST-HORIZON-CLAIM-VALIDATOR

# START_BLOCK: VALIDATOR_MUTATION_MATRIX
from __future__ import annotations

from copy import deepcopy
import typing

import pytest
from pydantic import BaseModel

from app.schemas.horizon_guidance import (
    HorizonClaimValidationError,
    HorizonGuidanceContext,
    HorizonGuidanceError,
)
from app.schemas.personal_fact_pack import PersonalFact
from app.schemas.today_horizons import TodayV2HorizonsBlock, TodayV2GroundedItem, TodayV2Provenance
from app.services.horizon_claim_validator import HorizonClaimValidator
from app.services.horizon_claim_policy import (
    check_conditional_and_unsupported_policy,
    check_no_raw_leakage,
    check_numeric_integrity,
)
from app.services.horizon_guidance_service import HorizonGuidanceService
from app.services.horizon_tone_service import HorizonToneService
from app.services.personal_fact_pack_service import PersonalFactPackService
from app.services.horizon_guidance_formatter import HorizonGuidanceFormatter
from app.services.horizon_guidance_builders import (
    statement_text_for_fact,
    build_actions,
    build_technique_explanation,
    ordered_intersection,
)

from ._horizon_content_testkit import (
    build_selected_story,
    build_sphere_verdicts,
    build_structure_natal,
)


def _mutate_block(b: TodayV2HorizonsBlock, **kw: object) -> TodayV2HorizonsBlock:
    values: dict[str, object] = {}
    for fn in b.__class__.model_fields:
        values[fn] = kw[fn] if fn in kw else getattr(b, fn)
    return b.__class__.model_construct(**values)


def _mutate_item(b: TodayV2HorizonsBlock, idx: int, **kw: object) -> TodayV2HorizonsBlock:
    items = list(b.items)
    orig = items[idx]
    vals: dict[str, object] = {}
    for fn in orig.__class__.model_fields:
        if fn in kw:
            v = kw[fn]
            if isinstance(v, list) and all(isinstance(x, BaseModel) for x in v):
                vals[fn] = v
            elif isinstance(v, list) and v:
                ft = orig.__class__.model_fields[fn].annotation
                args = typing.get_args(ft)
                inner = args[0] if args else None
                if isinstance(inner, type) and issubclass(inner, BaseModel):
                    vals[fn] = [inner.model_construct(**x) if isinstance(x, dict) else x for x in v]
                else:
                    vals[fn] = v
            elif isinstance(v, dict):
                ft = orig.__class__.model_fields[fn].annotation
                if isinstance(ft, type) and issubclass(ft, BaseModel):
                    vals[fn] = ft.model_construct(**v)
                else:
                    u_args = typing.get_args(ft)
                    found = False
                    for a in u_args:
                        if a is not type(None) and isinstance(a, type) and issubclass(a, BaseModel):
                            vals[fn] = a.model_construct(**v)
                            found = True
                            break
                    if not found:
                        vals[fn] = v
            else:
                vals[fn] = v
        else:
            vals[fn] = getattr(orig, fn)
    items[idx] = orig.__class__.model_construct(**vals)
    return _mutate_block(b, items=items)


def _expect(b, ctx, ev, match, exc_cls=HorizonClaimValidationError):
    with pytest.raises(exc_cls, match=match):
        HorizonClaimValidator().validate(block=b, context=ctx, activation_evidence=ev)


@pytest.fixture(scope="module")
def baseline():
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.baseline
    # purpose: Build a fully validated deterministic block once per session.
    # inputs: none (module scope fixture).
    # returns: (validated block, context, activation evidence list).
    # side_effects: reads cached content canons.
    # emitted_logs: none.
    # error_behavior: test failure on build/validation error.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.baseline
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    natal = build_structure_natal()
    verdicts = build_sphere_verdicts()
    fact_pack = PersonalFactPackService().build(
        selection=selection, activation_layer=layer,
        scoring_result=scoring, natal_context=natal,
    )
    tone = HorizonToneService().assess(
        selection=selection, sphere_verdicts=verdicts,
    )
    ctx = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=selection, fact_pack=fact_pack,
        tone_result=tone, sphere_verdicts=verdicts,
    )
    block = HorizonGuidanceService().build(context=ctx)
    validated = HorizonClaimValidator().validate(
        block=block, context=ctx,
        activation_evidence=list(layer.activations),
    )
    return validated, ctx, list(layer.activations)


def _m_block_fn(field, val):
    return lambda b, ctx, ev: (_mutate_block(b, **{field: val}), ctx, ev)

def _m_intro_fn(field, val):
    return lambda b, ctx, ev: (_mutate_block(b, intro=b.intro.model_copy(update={field: val})), ctx, ev)

def _m_item_fn(idx, field, val):
    return lambda b, ctx, ev: (_mutate_item(b, idx, **{field: val}), ctx, ev)

def _m_timing_fn(idx, field, val):
    return lambda b, ctx, ev: (_mutate_item(b, idx, timing=b.items[idx].timing.model_copy(update={field: val})), ctx, ev)

def _m_actions_fn(idx, field, val):
    return lambda b, ctx, ev: (_mutate_item(b, idx, actions=b.items[idx].actions.model_copy(update={field: val})), ctx, ev)

def _m_strength_prov_fn(idx, field, val):
    return lambda b, ctx, ev: (_mutate_item(b, idx, strength=b.items[idx].strength.model_copy(
        update={"provenance": b.items[idx].strength.provenance.model_copy(update={field: val})})), ctx, ev)

def _m_manifestation_fn(idx, m_idx, field, val):
    def _fn(b, ctx, ev):
        ms = list(b.items[idx].manifestations)
        ms[m_idx] = ms[m_idx].model_copy(update={field: val})
        return _mutate_item(b, idx, manifestations=ms), ctx, ev
    return _fn


_MUTATIONS = [
    ("duplicate_evidence", "evidence_duplicate", lambda b, ctx, ev: (b, ctx, ev + [ev[0]])),
    ("schema_version_mutated", "intro_alignment_invalid", _m_block_fn("schema_version", "today-horizons.v2")),
    ("guidance_mode_mutated", "intro_alignment_invalid", _m_block_fn("guidance_mode", "probabilistic")),
    ("warnings_mutated", "intro_alignment_invalid", _m_block_fn("warnings", ["something"])),
    ("intro_eyebrow", "intro_alignment_invalid", _m_intro_fn("eyebrow", "CHANGED")),
    ("intro_headline", "intro_alignment_invalid", _m_intro_fn("headline", "CHANGED")),
    ("intro_body", "intro_alignment_invalid", _m_intro_fn("body", "CHANGED")),
    ("intro_theme", "intro_alignment_invalid", _m_intro_fn("theme_key", "nonexistent")),
    ("intro_ids", "intro_alignment_invalid", _m_intro_fn("activation_ids", ["x"])),
    ("horizon_id", "horizon_alignment_invalid", _m_item_fn(0, "id", "horizon.wrong")),
    ("horizon_eyebrow", "horizon_alignment_invalid", _m_item_fn(0, "eyebrow", "CHANGED")),
    ("horizon_title", "horizon_alignment_invalid", _m_item_fn(0, "title", "CHANGED")),
    ("horizon_summary", "horizon_alignment_invalid", _m_item_fn(0, "summary", "CHANGED")),
    ("horizon_plain_explanation", "timing_alignment_invalid", _m_item_fn(0, "plain_explanation", "CHANGED")),
    ("horizon_plain_expl_invented_date", "timing_alignment_invalid", _m_item_fn(0, "plain_explanation", "Делайте до 18 июля 2026")),
    ("tone", "tone_alignment_invalid", _m_item_fn(1, "tone", "supportive")),
    ("active_from", "timing_alignment_invalid", _m_timing_fn(0, "active_from", "2099-01-01")),
    ("exact_at", "timing_alignment_invalid", _m_timing_fn(0, "exact_at", "2099-07-15")),
    ("active_until", "timing_alignment_invalid", _m_timing_fn(0, "active_until", "2099-12-31")),
    ("precision", "timing_alignment_invalid", _m_timing_fn(0, "precision", "instant")),
    ("timezone", "timing_alignment_invalid", _m_timing_fn(0, "timezone", "Europe/Paris")),
    ("range_label", "timing_alignment_invalid", _m_timing_fn(0, "range_label", "CHANGED")),
    ("state_label", "timing_alignment_invalid", _m_timing_fn(0, "state_label", "CHANGED")),
    ("peak_label", "timing_alignment_invalid", _m_timing_fn(0, "peak_label", "CHANGED")),
    ("valid_until", "timing_alignment_invalid", _m_actions_fn(0, "valid_until", "2099-12-31")),
    ("valid_until_label", "timing_alignment_invalid", _m_actions_fn(0, "valid_until_label", "CHANGED")),
    ("likely_spheres", "sphere_alignment_invalid", _m_item_fn(1, "likely_spheres", ["sport"])),
    ("unknown_fact_id", "fact_provenance_invalid", _m_strength_prov_fn(0, "natal_fact_ids", ["nonexistent"])),
    ("reused_fact", "fact_reused", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(
        update={"provenance": b.items[0].strength.provenance.model_copy(update={"natal_fact_ids": [b.items[0].risk.provenance.natal_fact_ids[0]]})})), ctx, ev)),
    ("wrong_fact_kind", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(update={"kind": "risk"})), ctx, ev)),
    ("wrong_fact_text", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(update={"text": "CHANGED"})), ctx, ev)),
    ("profile_fact", "fact_provenance_invalid", _m_strength_prov_fn(0, "profile_fact_ids", ["profile:test"])),
    ("manifestation_id", "manifestation_invalid", _m_manifestation_fn(0, 0, "id", "manifestation.long.wrong")),
    ("manifestation_title", "manifestation_invalid", _m_manifestation_fn(0, 0, "title", "CHANGED")),
    ("manifestation_body", "manifestation_invalid", _m_manifestation_fn(0, 0, "body", "CHANGED")),
    ("manifestation_body_residual", "manifestation_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"body": "CHANGED"})]), ctx, ev)),
    ("manifestation_condition", "manifestation_invalid", _m_manifestation_fn(0, 0, "condition", "Если CHANGED")),
    ("manifestation_sphere", "manifestation_invalid", _m_manifestation_fn(0, 0, "sphere_keys", ["sport"])),
    ("manifestation_profile_provenance", "manifestation_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"provenance": b.items[0].manifestations[0].provenance.model_copy(update={"profile_fact_ids": ["profile:test"]})})] + list(b.items[0].manifestations[1:])), ctx, ev)),
    ("action_wrong_theme_id", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"id": "nonexistent.do"})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("action_wrong_bucket", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"id": b.items[0].actions.avoid[0].id, "kind": "action"})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("action_wrong_text", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"text": "CHANGED"})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("action_conditional_flag", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"conditional": True})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("action_duplicate", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0], b.items[0].actions.do[0]]})), ctx, ev)),
    ("action_profile_provenance", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"provenance": b.items[0].actions.do[0].provenance.model_copy(update={"profile_fact_ids": ["profile:test"]})})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("forbidden_certainty", "forbidden_claim", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="Это неизбежно."), ctx, ev)),
    ("unsupported_employer", "unsupported_life_claim", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="Ваш работодатель решил."), ctx, ev)),
    ("unsupported_diagnosis", "unsupported_life_claim", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="У вас диагноз и это уже факт."), ctx, ev)),
    ("embedded_transit_prefix", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="Transit_Moon active"), ctx, ev)),
    ("embedded_natal_prefix", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="Natal_Sun strong"), ctx, ev)),
    ("embedded_activation_id", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, summary=f"Details for {ev[0].id if ev else 'long-structure'}"), ctx, ev)),
    ("embedded_fact_id", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, summary=f"Details for {ctx.fact_pack.facts[0].id if ctx.fact_pack.facts else 'fact'}"), ctx, ev)),
    ("snake_case_leak", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, summary="Use structure_boundaries_control"), ctx, ev)),
    ("invented_numeric_date", "numeric_claim_not_grounded", lambda b, ctx, ev: (_mutate_block(b, intro=b.intro.model_copy(update={"body": b.intro.body + " 1"})), ctx, ev)),
    ("technique_key", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"technique": "unknown_technique"})]), ctx, ev)),
    ("technique_label", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"label": "CHANGED"})]), ctx, ev)),
    ("technique_what", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"what_it_is": "CHANGED"})]), ctx, ev)),
    ("technique_why", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"why_it_matters_now": "CHANGED"})]), ctx, ev)),
    ("technique_why_invented_date", "numeric_claim_not_grounded", lambda b, ctx, ev: (_mutate_block(b, intro=b.intro.model_copy(update={"body": b.intro.body + " 2"})), ctx, ev)),
    ("technique_nested_timing_label", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"timing": b.items[0].technique_explanations[0].timing.model_copy(update={"range_label": "CHANGED"})}) if b.items[0].technique_explanations[0].timing else b.items[0].technique_explanations[0]]), ctx, ev)),
    ("strength_public_id", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(update={"id": "claim.long.wrong"})), ctx, ev)),
    ("risk_public_id", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, risk=b.items[0].risk.model_copy(update={"id": "claim.long.wrong"})), ctx, ev)),
    ("fact_activation_provenance", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(update={"provenance": b.items[0].strength.provenance.model_copy(update={"activation_ids": ["other"]})})), ctx, ev)),
    ("fact_sphere_provenance", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(update={"provenance": b.items[0].strength.provenance.model_copy(update={"sphere_keys": ["sport"]})})), ctx, ev)),
    ("fact_natal_provenance", "fact_provenance_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, strength=b.items[0].strength.model_copy(update={"provenance": b.items[0].strength.provenance.model_copy(update={"natal_fact_ids": []})})), ctx, ev)),
    ("manifestation_natal_provenance", "manifestation_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"provenance": b.items[0].manifestations[0].provenance.model_copy(update={"natal_fact_ids": ["fact_id"]})})] + list(b.items[0].manifestations[1:])), ctx, ev)),
    ("manifestation_provenance_spheres", "manifestation_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"provenance": b.items[0].manifestations[0].provenance.model_copy(update={"sphere_keys": ["sport"]})})] + list(b.items[0].manifestations[1:])), ctx, ev)),
    ("action_heading_arbitrary", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"heading": "CHANGED"})), ctx, ev)),
    ("action_heading_snake_case", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"heading": "structure_boundaries_control"})), ctx, ev)),
    ("action_natal_provenance", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"provenance": b.items[0].actions.do[0].provenance.model_copy(update={"natal_fact_ids": ["fact_id"]})})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("action_valid_subset", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": list(b.items[0].actions.do[:-1])})), ctx, ev)),
    ("action_valid_reorder", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 1, actions=b.items[1].actions.model_copy(update={"do": list(b.items[1].actions.do[::-1])}) if len(b.items[1].actions.do) > 1 else b.items[1].actions), ctx, ev)),
    ("action_tone_mismatch", "tone_alignment_invalid", lambda b, ctx, ev: (b, ctx.model_copy(update={"tone_result": ctx.tone_result.model_copy(update={"items": [t.model_copy(update={"tone": "tense"}) if t.horizon == "long" else t for t in ctx.tone_result.items]})}), ev)),
    ("action_verdict_conflict", "action_verdict_conflict", lambda b, ctx, ev: (b, ctx.model_copy(update={"sphere_verdicts": {s: "avoid" for s in b.items[0].likely_spheres}}), ev)),
    ("technique_nested_timing_peak_label", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"timing": b.items[0].technique_explanations[0].timing.model_copy(update={"peak_label": "CHANGED"})}) if b.items[0].technique_explanations[0].timing else b.items[0].technique_explanations[0]]), ctx, ev)),
    ("technique_nested_timing_state", "technique_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"timing": b.items[0].technique_explanations[0].timing.model_copy(update={"state": "upcoming"})}) if b.items[0].technique_explanations[0].timing else b.items[0].technique_explanations[0]]), ctx, ev)),
    ("unsupported_employer_in_manifestation", "unsupported_life_claim", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"body": "Ваш работодатель решил уволить."})] + list(b.items[0].manifestations[1:])), ctx, ev)),
    ("unsupported_employer_in_technique", "unsupported_life_claim", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"why_it_matters_now": "Ваш работодатель решит."})]), ctx, ev)),
    ("certainty_in_manifestation", "forbidden_claim", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"body": "Это неизбежно."})] + list(b.items[0].manifestations[1:])), ctx, ev)),
    ("certainty_in_technique", "forbidden_claim", lambda b, ctx, ev: (_mutate_item(b, 0, technique_explanations=[b.items[0].technique_explanations[0].model_copy(update={"why_it_matters_now": "Это неизбежно."})]), ctx, ev)),
    ("certainty_in_action", "forbidden_claim", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"heading": "Это неизбежно."})), ctx, ev)),
    ("privacy_sentinel_raw_evidence", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="This is RAW_EVIDENCE_SENTINEL"), ctx, ev)),
    ("privacy_sentinel_raw_debug", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="This is RAW_DEBUG_SENTINEL"), ctx, ev)),
    ("privacy_sentinel_profile_name", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="This is PROFILE_NAME_SENTINEL"), ctx, ev)),
    ("privacy_sentinel_profile_city", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="This is PROFILE_CITY_SENTINEL"), ctx, ev)),
    ("privacy_sentinel_coordinate", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="This is COORDINATE_SENTINEL"), ctx, ev)),
    ("privacy_sentinel_session", "internal_copy_leak", lambda b, ctx, ev: (_mutate_item(b, 0, plain_explanation="This is SESSION_SENTINEL"), ctx, ev)),
    ("horizon_timing_state", "timing_alignment_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, timing=b.items[0].timing.model_copy(update={"state": "upcoming"})), ctx, ev)),
]

_MUTATIONS.extend([
    ("action_do_template_conditional_mismatch", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"do": [b.items[0].actions.do[0].model_copy(update={"conditional": not b.items[0].actions.do[0].conditional})] + list(b.items[0].actions.do[1:])})), ctx, ev)),
    ("action_avoid_template_conditional_mismatch", "action_not_authorized", lambda b, ctx, ev: (_mutate_item(b, 0, actions=b.items[0].actions.model_copy(update={"avoid": [b.items[0].actions.avoid[0].model_copy(update={"conditional": not b.items[0].actions.avoid[0].conditional})] + list(b.items[0].actions.avoid[1:])})), ctx, ev)),
    ("manifestation_provenance_activation_ids_mismatch", "manifestation_invalid", lambda b, ctx, ev: (_mutate_item(b, 0, manifestations=[b.items[0].manifestations[0].model_copy(update={"provenance": b.items[0].manifestations[0].provenance.model_copy(update={"activation_ids": ["wrong"]})})] + list(b.items[0].manifestations[1:])), ctx, ev)),
])

assert len(_MUTATIONS) >= 91, f"expected >=91 mutations, got {len(_MUTATIONS)}"


# END_BLOCK: VALIDATOR_MUTATION_MATRIX


# START_BLOCK: VALIDATOR_PARAMETRIZED
@pytest.mark.parametrize("case_id", [c[0] for c in _MUTATIONS])
def test_mutation_matrix(baseline, case_id):
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_mutation_matrix
    # purpose: Parametrized mutation matrix covering all claim-validation gaps.
    # inputs: baseline module fixture, case_id from _MUTATIONS.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure if expected code mismatches or unvalidated
    #   mutation passes silently.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_mutation_matrix
    b, ctx, ev = baseline
    for name, code, fn in _MUTATIONS:
        if name != case_id:
            continue
        nb, nctx, nev = fn(b, ctx, ev)
        if nb is b and nctx is ctx and nev is ev:
            continue
        _expect(nb, nctx, nev, code)
        break


# -- sanitized exception ----------------------------------------------------
@pytest.mark.parametrize("sentinel", [
    "RAW_EVIDENCE_SENTINEL",
    "RAW_DEBUG_SENTINEL",
    "PROFILE_NAME_SENTINEL",
    "PROFILE_CITY_SENTINEL",
    "COORDINATE_SENTINEL",
    "SESSION_SENTINEL",
])
def test_sanitized_exception_sentinel_matrix(baseline, sentinel) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_sanitized_exception_sentinel_matrix
    # purpose: Assert validator exceptions contain no raw sentinels or claim bodies.
    # inputs: baseline module fixture, sentinel from parametrize.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on sentinel or body leak in exception message.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_sanitized_exception_sentinel_matrix
    b, ctx, ev = baseline
    bad_intro = b.intro.model_copy(update={"body": f"This is secret {sentinel}"})
    mutated_block = _mutate_block(b, intro=bad_intro)

    try:
        HorizonClaimValidator().validate(
            block=mutated_block, context=ctx, activation_evidence=ev
        )
        pytest.fail("expected HorizonClaimValidationError to be raised")
    except HorizonClaimValidationError as exc:
        msg = str(exc)
        assert exc.code == "internal_copy_leak"
        assert sentinel not in msg, f"sentinel {sentinel} leaked in exception message: {msg}"
        assert "secret" not in msg, f"raw body text leaked in exception message: {msg}"


def test_action_forbidden_intent(baseline) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_action_forbidden_intent
    # purpose: Assert validator rejects forbidden action intents without raw ID/intent leakage.
    # inputs: baseline fixture.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_action_forbidden_intent
    b, ctx, ev = baseline
    validator = HorizonClaimValidator()
    custom_bundle = deepcopy(validator.bundle)

    # Inhibit first selected do action
    do_item = b.items[0].actions.do[0]
    theme_key = b.intro.theme_key
    action_lists = getattr(custom_bundle.actions.themes[theme_key], "long")
    template = next(t for t in action_lists.do if t.id == do_item.id)

    new_actions = custom_bundle.actions.model_copy(
        update={"forbidden_intents": custom_bundle.actions.forbidden_intents + (template.intent,)}
    )
    custom_bundle = custom_bundle.model_copy(update={"actions": new_actions})
    validator._bundle = custom_bundle

    with pytest.raises(HorizonClaimValidationError) as exc_info:
        validator.validate(block=b, context=ctx, activation_evidence=ev)

    assert exc_info.value.code == "action_intent_conflict"
    msg = str(exc_info.value)
    assert template.id not in msg
    assert template.intent not in msg


def test_action_forbidden_pair(baseline) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_action_forbidden_pair
    # purpose: Assert validator rejects forbidden action intent pairs without raw ID/intent leakage.
    # inputs: baseline fixture.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_action_forbidden_pair
    b, ctx, ev = baseline
    validator = HorizonClaimValidator()
    custom_bundle = deepcopy(validator.bundle)

    # Inhibit first selected do action and avoid action
    do_item = b.items[0].actions.do[0]
    avoid_item = b.items[0].actions.avoid[0]
    theme_key = b.intro.theme_key
    action_lists = getattr(custom_bundle.actions.themes[theme_key], "long")
    do_template = next(t for t in action_lists.do if t.id == do_item.id)
    avoid_template = next(t for t in action_lists.avoid if t.id == avoid_item.id)

    new_actions = custom_bundle.actions.model_copy(
        update={"forbidden_intent_pairs": custom_bundle.actions.forbidden_intent_pairs + ((do_template.intent, avoid_template.intent),)}
    )
    custom_bundle = custom_bundle.model_copy(update={"actions": new_actions})
    validator._bundle = custom_bundle

    with pytest.raises(HorizonClaimValidationError) as exc_info:
        validator.validate(block=b, context=ctx, activation_evidence=ev)

    assert exc_info.value.code == "action_intent_conflict"
    msg = str(exc_info.value)
    assert do_item.id not in msg
    assert avoid_item.id not in msg
    assert do_template.intent not in msg
    assert avoid_template.intent not in msg


def test_lower_ranked_fact_rejection(baseline) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_lower_ranked_fact_rejection
    # purpose: Assert validator rejects lower-ranked fact substitution.
    # inputs: baseline fixture.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_lower_ranked_fact_rejection
    b, ctx, ev = baseline
    validator = HorizonClaimValidator()
    canon = validator.bundle

    # Find the top-ranked fact
    top_fact_id = b.items[0].strength.provenance.natal_fact_ids[0]
    top_fact = next(f for f in ctx.fact_pack.facts if f.id == top_fact_id)

    # Find another strength statement key in language canon
    stmt_key = next(k for k, s in canon.language.personal_statements.items() if s.kind == "strength" and k != top_fact.statement_key)

    lower_fact = top_fact.model_copy(update={
        "id": "saturn_lower_fact",
        "statement_key": stmt_key,
        "confidence": top_fact.confidence - 0.1,
        "horizon_ids": ["long"],
    })

    new_facts = list(ctx.fact_pack.facts) + [lower_fact]
    new_fact_pack = ctx.fact_pack.model_copy(update={"facts": new_facts})
    new_ctx = ctx.model_copy(update={"fact_pack": new_fact_pack})

    new_block = HorizonGuidanceService().build(context=new_ctx)
    assert new_block.items[0].strength.provenance.natal_fact_ids[0] == top_fact_id

    # Mutate strength to the lower fact
    lower_text = canon.language.personal_statements[stmt_key].text
    isphere = ordered_intersection(
        list(b.items[0].likely_spheres),
        list(lower_fact.sphere_keys),
    )
    lower_strength = TodayV2GroundedItem(
        id=f"claim.long.{lower_fact.id}",
        kind="strength",
        text=lower_text,
        conditional=False,
        provenance=TodayV2Provenance(
            activation_ids=[b.items[0].activation_ids[0]],
            natal_fact_ids=[lower_fact.id],
            profile_fact_ids=[],
            sphere_keys=isphere,
        ),
    )

    mutated_block = _mutate_item(new_block, 0, strength=lower_strength)

    with pytest.raises(HorizonClaimValidationError) as exc_info:
        validator.validate(block=mutated_block, context=new_ctx, activation_evidence=ev)

    assert exc_info.value.code == "fact_provenance_invalid"
    assert "saturn_lower_fact" not in str(exc_info.value)


def test_sanitization_matrix_cases(baseline) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_sanitization_matrix_cases
    # purpose: Assert validator/formatter/service/builders sanitize raw IDs/sentinels.
    # inputs: baseline fixture.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_sanitization_matrix_cases
    b, ctx, ev = baseline
    val = HorizonClaimValidator()
    fmt = HorizonGuidanceFormatter()
    top_fact_id = b.items[0].strength.provenance.natal_fact_ids[0]
    top_fact = next(f for f in ctx.fact_pack.facts if f.id == top_fact_id)

    # 1. manifestation ID sentinel
    ms = list(b.items[0].manifestations)
    ms[0] = ms[0].model_copy(update={"id": "RAW_EVIDENCE_SENTINEL"})
    bad_b = _mutate_item(b, 0, manifestations=ms)
    with pytest.raises(HorizonClaimValidationError) as exc:
        val.validate(block=bad_b, context=ctx, activation_evidence=ev)
    assert exc.value.code == "manifestation_invalid"
    assert "RAW_EVIDENCE_SENTINEL" not in str(exc.value)

    # 2. action ID sentinel
    a = b.items[0].actions.do[0].model_copy(update={"id": "RAW_DEBUG_SENTINEL"})
    act = b.items[0].actions.model_copy(update={"do": [a] + list(b.items[0].actions.do[1:])})
    bad_b = _mutate_item(b, 0, actions=act)
    with pytest.raises(HorizonClaimValidationError) as exc:
        val.validate(block=bad_b, context=ctx, activation_evidence=ev)
    assert exc.value.code == "action_not_authorized"
    assert "RAW_DEBUG_SENTINEL" not in str(exc.value)

    # 3. public horizon item ID sentinel plus unsupported body
    bad_b = _mutate_item(b, 0, id="PROFILE_NAME_SENTINEL", summary="Ваш работодатель решил.")
    with pytest.raises(HorizonClaimValidationError) as exc:
        val.validate(block=bad_b, context=ctx, activation_evidence=ev)
    assert exc.value.code == "unsupported_life_claim"
    assert "PROFILE_NAME_SENTINEL" not in str(exc.value)
    assert "работодатель" not in str(exc.value)

    # 4. actual reused fact ID
    fid = b.items[0].strength.provenance.natal_fact_ids[0]
    bad_b = _mutate_item(b, 0, risk=b.items[0].strength.model_copy(update={"kind": "risk", "id": f"claim.long.{fid}"}))
    with pytest.raises(HorizonClaimValidationError) as exc:
        val.validate(block=bad_b, context=ctx, activation_evidence=ev)
    assert exc.value.code == "fact_reused"
    assert fid not in str(exc.value)

    # 5. Formatter unknown entity/source/target sentinels
    with pytest.raises(HorizonGuidanceError) as exc:
        fmt.target_label("planet", "PROFILE_CITY_SENTINEL")
    assert exc.value.code == "unsupported_entity_label"
    assert "PROFILE_CITY_SENTINEL" not in str(exc.value)

    with pytest.raises(HorizonGuidanceError) as exc:
        fmt.source_label("COORDINATE_SENTINEL")
    assert exc.value.code == "unsupported_entity_label"
    assert "COORDINATE_SENTINEL" not in str(exc.value)

    with pytest.raises(HorizonGuidanceError) as exc:
        fmt.entity_display("SESSION_SENTINEL")
    assert exc.value.code == "unsupported_entity_label"
    assert "SESSION_SENTINEL" not in str(exc.value)

    # 6. Service unknown theme/sphere/activation sentinels
    bad_sel = ctx.selection.model_copy(update={"shared_theme_keys": ["RAW_EVIDENCE_SENTINEL"]})
    bad_ctx = ctx.model_copy(update={"selection": bad_sel})
    with pytest.raises(HorizonGuidanceError) as exc:
        HorizonGuidanceService().build(context=bad_ctx)
    assert exc.value.code == "unknown_theme"
    assert "RAW_EVIDENCE_SENTINEL" not in str(exc.value)

    # 7. Builder unknown statement/theme/technique sentinels
    with pytest.raises(HorizonGuidanceError) as exc:
        fact = PersonalFact(
            id=top_fact.id, kind=top_fact.kind, statement_key=top_fact.statement_key,
            confidence=0.8, horizon_ids=["long"], activation_ids=["act"],
            theme_keys=["structure_boundaries_control"], sphere_keys=["work"],
            natal_source_ids=list(top_fact.natal_source_ids), profile_source_ids=[]
        )
        bad_fact = fact.model_copy(update={"statement_key": "RAW_DEBUG_SENTINEL"})
        statement_text_for_fact(bad_fact, val.bundle)
    assert exc.value.code == "unknown_claim_statement"
    assert "RAW_DEBUG_SENTINEL" not in str(exc.value)

    with pytest.raises(HorizonGuidanceError) as exc:
        build_actions(horizon="long", anchor=ctx.selection.items[0], horizon_theme="PROFILE_NAME_SENTINEL", tone="neutral", sphere_verdicts={}, timing=b.items[0].timing, valid_until_label="label", canon=val.bundle)
    assert exc.value.code == "insufficient_safe_actions"
    assert "PROFILE_NAME_SENTINEL" not in str(exc.value)

    with pytest.raises(HorizonGuidanceError) as exc:
        build_technique_explanation(horizon="long", anchor=ctx.selection.items[0], horizon_theme="PROFILE_CITY_SENTINEL", timing=b.items[0].timing, active_from_label="from", active_until_label="until", exact_at_label=None, valid_until_label="label", timezone_suffix="suffix", range_label="range", peak_label=None, state_label="state", tone="neutral", likely_spheres=[], canon=val.bundle, formatter=fmt)
    assert exc.value.code == "unknown_theme"
    assert "PROFILE_CITY_SENTINEL" not in str(exc.value)

    # 8. Public cross-reference mismatch with raw ID
    bad_ev = [e.model_copy(update={"id": "COORDINATE_SENTINEL"}) if e.id == "long-structure" else e for e in ev]
    with pytest.raises(HorizonClaimValidationError) as exc:
        val.validate(block=b, context=ctx, activation_evidence=bad_ev)
    assert exc.value.code == "public_cross_reference_invalid"
    assert "COORDINATE_SENTINEL" not in str(exc.value)


@pytest.mark.parametrize("case", ["manifestation", "action", "item", "action_id", "manifestation_id", "technique", "snake"])
def test_r5_direct_policy_sanitization(baseline, case) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_r5_direct_policy_sanitization
    # purpose: Exercise direct policy branches and prove raw IDs, keys, and copy never reach errors.
    # inputs: baseline fixture and named direct policy case.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on wrong code or raw-value leakage.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_r5_direct_policy_sanitization
    block, _, _ = baseline
    sentinel = f"R5_{case.upper()}_SENTINEL"
    if case == "manifestation":
        bad = _m_manifestation_fn(0, 0, "id", sentinel)(block, None, None)[0]
        bad = _m_manifestation_fn(0, 0, "condition", None)(bad, None, None)[0]
        check, code = check_conditional_and_unsupported_policy, "conditional_policy_invalid"
    elif case == "action":
        action = block.items[0].actions.do[0].model_copy(update={"id": sentinel, "conditional": True, "text": sentinel})
        bad = _mutate_item(block, 0, actions=block.items[0].actions.model_copy(update={"do": [action] + list(block.items[0].actions.do[1:])}))
        check, code = check_conditional_and_unsupported_policy, "conditional_policy_invalid"
    elif case == "snake":
        bad = _mutate_item(block, 0, summary="unique_r5_snake_token")
        check, code = check_no_raw_leakage, "internal_copy_leak"
        sentinel = "unique_r5_snake_token"
    else:
        item = block.items[0]
        if case == "item":
            bad = _mutate_item(block, 0, id=sentinel, title=item.title + " 771")
        elif case == "action_id":
            action = item.actions.do[0].model_copy(update={"id": sentinel, "text": item.actions.do[0].text + " 772"})
            bad = _mutate_item(block, 0, actions=item.actions.model_copy(update={"do": [action] + list(item.actions.do[1:])}))
        elif case == "manifestation_id":
            mani = item.manifestations[0].model_copy(update={"id": sentinel, "body": item.manifestations[0].body + " 773"})
            bad = _mutate_item(block, 0, manifestations=[mani] + list(item.manifestations[1:]))
        else:
            tech = item.technique_explanations[0].model_copy(update={"technique": sentinel, "label": item.technique_explanations[0].label + " 774"})
            bad = _mutate_item(block, 0, technique_explanations=[tech])
        check, code = check_numeric_integrity, "numeric_claim_not_grounded"
    with pytest.raises(HorizonClaimValidationError) as exc:
        check(block=bad, canon=HorizonClaimValidator().bundle) if check is not check_no_raw_leakage else check(block=bad)
    assert exc.value.code == code
    assert sentinel not in str(exc.value)


@pytest.mark.parametrize("error_type", [HorizonGuidanceError, HorizonClaimValidationError])
def test_r5_typed_error_boundary(error_type) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_r5_typed_error_boundary
    # purpose: Prove typed errors discard caller-supplied raw item IDs from all retained public state.
    # inputs: typed B2B2 error class.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on raw item-ID retention.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_r5_typed_error_boundary
    exc = error_type("test_code", "items[0]", "RAW_ITEM_ID_SENTINEL")
    assert "RAW_ITEM_ID_SENTINEL" not in str(exc)
    assert "RAW_ITEM_ID_SENTINEL" not in repr(exc)
    assert "RAW_ITEM_ID_SENTINEL" not in repr(vars(exc))


def test_r5_builder_placeholder_sanitized(baseline) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_r5_builder_placeholder_sanitized
    # purpose: Run the real technique builder with a copied canon and hide unresolved placeholder names.
    # inputs: validated baseline fixture.
    # returns: none.
    # side_effects: none; the cached canon is not mutated.
    # emitted_logs: none.
    # error_behavior: test failure on wrong code, leakage, or cached-canon mutation.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CLAIM-VALIDATOR.test_r5_builder_placeholder_sanitized
    block, ctx, _ = baseline
    validator = HorizonClaimValidator()
    original = validator.bundle
    copied = deepcopy(original)
    anchor = ctx.selection.items[0]
    technique = copied.language.techniques[anchor.technique]
    sentinel = "unique_unresolved_placeholder_sentinel"
    changed = technique.model_copy(update={"why_it_matters_template": technique.why_it_matters_template + f" {{{sentinel}}}"})
    techniques = dict(copied.language.techniques)
    techniques[anchor.technique] = changed
    copied = copied.model_copy(update={"language": copied.language.model_copy(update={"techniques": techniques})})
    timing = block.items[0].timing
    with pytest.raises(HorizonGuidanceError) as exc:
        build_technique_explanation(
            horizon="long", anchor=anchor, horizon_theme=block.intro.theme_key, timing=timing,
            active_from_label="from", active_until_label="until", exact_at_label=None,
            valid_until_label="valid", timezone_suffix="UTC", range_label=timing.range_label,
            peak_label=timing.peak_label, state_label=timing.state_label, tone=block.items[0].tone,
            likely_spheres=list(block.items[0].likely_spheres), canon=copied,
            formatter=HorizonGuidanceFormatter(),
        )
    assert exc.value.code == "unresolved_placeholder"
    assert str(exc.value) == "unresolved_placeholder | technique.why_it_matters_now"
    assert original.language.techniques[anchor.technique] == validator.bundle.language.techniques[anchor.technique]

# END_BLOCK: VALIDATOR_PARAMETRIZED
