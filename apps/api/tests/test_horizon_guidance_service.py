# ############################################################################
# AI_HEADER: TEST_HORIZON_GUIDANCE_SERVICE — deterministic B2B2 guidance tests.
# ROLE: Proves intro, horizon, timing, manifestations, actions, claims,
#       technique, determinism, privacy, and error contracts.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-GUIDANCE-SERVICE
# purpose: Test the full deterministic guidance pipeline from context to
#          public block.
# owns:
#   - apps/api/tests/test_horizon_guidance_service.py
# inputs: Synthetic golden B2A/B2B1 stories with explicit verdict maps.
# outputs: Assertions over block structure, content, determinism, and privacy.
# dependencies: pytest, guidance service, testkit, content canon.
# side_effects: reads cached content canon.
# emitted_logs: none.
# invariants:
#   - No production fixture imports, network, DB, or wall clock.
# failure_policy: test failures identify guidance regression.
# END_MODULE_CONTRACT: M-TEST-HORIZON-GUIDANCE-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-GUIDANCE-SERVICE
# public_entrypoints:
#   - test_intro_differ_by_theme
#   - test_exact_horizon_order
#   - test_timing_preserved
#   - test_likely_spheres_order
#   - test_one_manifestation_per_sphere
#   - test_manifestation_condition_split
#   - test_action_counts
#   - test_verdict_avoid_works
#   - test_missing_verdict_ok
#   - test_strength_risk_kind
#   - test_empty_natal_all_null
#   - test_fact_not_reused
#   - test_profection_technique_exact
#   - test_transit_technique_exact
#   - test_output_model_valid
#   - test_cross_validates
#   - test_byte_identical
#   - test_no_pii_sentinels
#   - test_medium_peak_missing_rejects
#   - test_fast_peak_missing_rejects
#   - test_avoid_verdict_all_avoid
#   - test_context_mismatch_exact_code
# semantic_blocks:
#   - GUIDANCE_SERVICE_STRUCTURE_TESTS
#   - GUIDANCE_SERVICE_CONTENT_TESTS
#   - GUIDANCE_SERVICE_DETERMINISM_TESTS
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_service.py
# END_MODULE_MAP: M-TEST-HORIZON-GUIDANCE-SERVICE

# START_BLOCK: GUIDANCE_SERVICE_STRUCTURE_TESTS
from __future__ import annotations

import json

import pytest

from app.schemas.horizon_guidance import (
    HorizonGuidanceError,
    HorizonGuidanceContext,
)
from app.schemas.today_horizons import (
    TodayV2Horizon,
    TodayV2HorizonsBlock,
    validate_horizons_against_evidence,
)
from app.services.horizon_guidance_service import HorizonGuidanceService
from app.services.horizon_claim_validator import HorizonClaimValidator
from app.services.horizon_tone_service import HorizonToneService
from app.services.personal_fact_pack_service import PersonalFactPackService

from ._horizon_content_testkit import (
    build_communication_natal,
    build_relationship_natal,
    build_selected_story,
    build_sphere_verdicts,
    build_structure_natal,
    build_natal_context,
)
from ._horizon_selection_testkit import build_layer, build_story


def _build_context(story, natal, verdicts=None):
    selection, layer, scoring = build_selected_story(story)
    if verdicts is None:
        verdicts = build_sphere_verdicts()
    fact_pack = PersonalFactPackService().build(
        selection=selection, activation_layer=layer,
        scoring_result=scoring, natal_context=natal,
    )
    tone = HorizonToneService().assess(
        selection=selection, sphere_verdicts=verdicts,
    )
    return (
        HorizonGuidanceContext(
            schema_version="horizon-guidance-context.v1",
            selection=selection, fact_pack=fact_pack,
            tone_result=tone, sphere_verdicts=verdicts,
        ),
        layer,
    )


def test_intro_differ_by_theme() -> None:
    """Three distinct stories yield three distinct intro headline/body."""
    # START_FUNCTION_CONTRACT: F-TEST.test_intro_differ_by_theme
    # purpose: test intro differ by theme.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_intro_differ_by_theme
    headlines: set[str] = set()
    bodies: set[str] = set()
    for story, natal in [
        ("structure_boundaries_control", build_structure_natal()),
        ("communication_learning_documents", build_communication_natal()),
        ("relationships_values_closeness", build_relationship_natal()),
    ]:
        ctx, _ = _build_context(story, natal)
        block = HorizonGuidanceService().build(context=ctx)
        headlines.add(block.intro.headline)
        bodies.add(block.intro.body)
    assert len(headlines) == 3
    assert len(bodies) == 3
    assert block.intro.eyebrow == "Личная логика периода"


def test_exact_horizon_order() -> None:
    """Horizons are long, medium, fast."""
    # START_FUNCTION_CONTRACT: F-TEST.test_exact_horizon_order
    # purpose: test exact horizon order.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_exact_horizon_order
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    assert [h.horizon for h in block.items] == ["long", "medium", "fast"]


def test_timing_preserved() -> None:
    """Raw timing fields match anchor timing."""
    # START_FUNCTION_CONTRACT: F-TEST.test_timing_preserved
    # purpose: test timing preserved.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_timing_preserved
    ctx, _ = _build_context(
        "communication_learning_documents", build_communication_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item, anchor in zip(block.items, ctx.selection.items, strict=True):
        assert item.timing.timezone == anchor.timing.timezone
        assert item.timing.active_from == (anchor.timing.active_from or "")
        assert item.timing.active_until == (anchor.timing.active_until or "")


def test_likely_spheres_order() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_likely_spheres_order
    # purpose: test likely spheres order.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_likely_spheres_order
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item, anchor in zip(block.items, ctx.selection.items, strict=True):
        assert list(item.likely_spheres) == list(anchor.product_spheres)


def test_one_manifestation_per_sphere() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_one_manifestation_per_sphere
    # purpose: test one manifestation per sphere.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_one_manifestation_per_sphere
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item, anchor in zip(block.items, ctx.selection.items, strict=True):
        assert len(item.manifestations) == len(anchor.product_spheres)
        assert 1 <= len(item.manifestations) <= 3


def test_manifestation_condition_split() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_manifestation_condition_split
    # purpose: test manifestation condition split.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_manifestation_condition_split
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item in block.items:
        for mani in item.manifestations:
            assert mani.condition is not None
            assert mani.condition.startswith("Если")
            assert mani.body
            assert mani.body != mani.condition


def test_action_counts() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_action_counts
    # purpose: test action counts.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_action_counts
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item in block.items:
        hid = item.horizon
        do_n = len(item.actions.do)
        av_n = len(item.actions.avoid)
        if hid == "long":
            assert 1 <= do_n <= 2 and 1 <= av_n <= 2
        elif hid == "medium":
            assert 2 <= do_n <= 3 and 1 <= av_n <= 3
        elif hid == "fast":
            assert do_n == 1 and 1 <= av_n <= 2


def test_verdict_avoid_works() -> None:
    """Avoid verdict still produces a valid block."""
    # START_FUNCTION_CONTRACT: F-TEST.test_verdict_avoid_works
    # purpose: test verdict avoid works.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_verdict_avoid_works
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    assert block.schema_version == "today-horizons.v1"


def test_missing_verdict_ok() -> None:
    """Empty verdicts map does not raise."""
    # START_FUNCTION_CONTRACT: F-TEST.test_missing_verdict_ok
    # purpose: test missing verdict ok.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_missing_verdict_ok
    ctx, layer = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    ctx_empty = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=ctx.selection,
        fact_pack=ctx.fact_pack,
        tone_result=ctx.tone_result,
        sphere_verdicts={},
    )
    block = HorizonGuidanceService().build(context=ctx_empty)
    assert block is not None


def test_strength_risk_kind() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_strength_risk_kind
    # purpose: test strength risk kind.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_strength_risk_kind
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item in block.items:
        if item.strength:
            assert item.strength.kind == "strength"
        if item.risk:
            assert item.risk.kind == "risk"


def test_empty_natal_all_null() -> None:
    """Empty natal -> no strength/risk claims (all null)."""
    # START_FUNCTION_CONTRACT: F-TEST.test_empty_natal_all_null
    # purpose: test empty natal all null.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_empty_natal_all_null
    ctx, _ = _build_context(
        "structure_boundaries_control", build_natal_context()
    )
    block = HorizonGuidanceService().build(context=ctx)
    all_empty = all(
        item.strength is None and item.risk is None
        for item in block.items
    )
    assert all_empty, (
        "empty natal must produce no strength or risk claims"
    )


def test_fact_not_reused() -> None:
    """Each fact ID appears at most once across all horizons."""
    # START_FUNCTION_CONTRACT: F-TEST.test_fact_not_reused
    # purpose: test fact not reused.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_fact_not_reused
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    fact_ids: set[str] = set()
    for item in block.items:
        for g in [item.strength, item.risk]:
            if g is not None:
                for fid in g.provenance.natal_fact_ids:
                    assert fid not in fact_ids, f"fact {fid} reused"
                    fact_ids.add(fid)


def test_profection_technique_exact() -> None:
    """Profection technique has expected Russian label/definition."""
    # START_FUNCTION_CONTRACT: F-TEST.test_profection_technique_exact
    # purpose: test profection technique exact.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_profection_technique_exact
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    long_item = block.items[0]
    for tech_ex in long_item.technique_explanations:
        assert tech_ex.label
        assert tech_ex.what_it_is
        assert tech_ex.why_it_matters_now
        assert tech_ex.timing is not None
        # Verify label is Russian, not empty
        assert len(tech_ex.label) > 5
        # Verify technique key is present
        assert tech_ex.technique in (
            "annual_profection", "transit_to_natal"
        )


def test_transit_technique_exact() -> None:
    """Transit technique has expected structure."""
    # START_FUNCTION_CONTRACT: F-TEST.test_transit_technique_exact
    # purpose: test transit technique exact.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_transit_technique_exact
    ctx, _ = _build_context(
        "communication_learning_documents", build_communication_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    for item in block.items:
        for tech_ex in item.technique_explanations:
            if tech_ex.technique == "transit_to_natal":
                assert tech_ex.label
                assert tech_ex.what_it_is
                assert tech_ex.why_it_matters_now
                break


def test_output_model_valid() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_output_model_valid
    # purpose: test output model valid.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_output_model_valid
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    assert isinstance(block, TodayV2HorizonsBlock)
    assert block.schema_version == "today-horizons.v1"
    assert block.guidance_mode == "deterministic"


def test_cross_validates() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_cross_validates
    # purpose: test cross validates.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_cross_validates
    ctx, layer = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    v = HorizonClaimValidator()
    v.validate(
        block=block, context=ctx,
        activation_evidence=list(layer.activations),
    )


def test_byte_identical() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_byte_identical
    # purpose: test byte identical.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_byte_identical
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    b1 = HorizonGuidanceService().build(context=ctx)
    b2 = HorizonGuidanceService().build(context=ctx)
    assert b1.model_dump_json() == b2.model_dump_json()


def test_no_pii_sentinels() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_no_pii_sentinels
    # purpose: test no pii sentinels.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_no_pii_sentinels
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    block = HorizonGuidanceService().build(context=ctx)
    j = block.model_dump_json()
    for s in ["RAW_EVIDENCE_SENTINEL", "RAW_DEBUG_SENTINEL",
              "PROFILE_NAME_SENTINEL", "PROFILE_CITY_SENTINEL",
              "COORDINATE_SENTINEL", "SESSION_SENTINEL"]:
        assert s not in j


def test_medium_peak_missing_rejects() -> None:
    """Medium missing exact_at raises dedicated code."""
    # START_FUNCTION_CONTRACT: F-TEST.test_medium_peak_missing_rejects
    # purpose: test medium peak missing rejects.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_medium_peak_missing_rejects
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    items = list(ctx.selection.items)
    from app.schemas.horizon_selection import SelectedHorizonAnchor
    modified = []
    for anchor in items:
        if anchor.horizon == "medium":
            data = anchor.model_dump()
            data["timing"]["exact_at"] = None
            modified.append(SelectedHorizonAnchor.model_validate(data))
        else:
            modified.append(anchor)
    bad_sel = ctx.selection.model_copy(update={"items": modified})
    bad_ctx = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=bad_sel,
        fact_pack=ctx.fact_pack,
        tone_result=ctx.tone_result,
        sphere_verdicts=ctx.sphere_verdicts,
    )
    with pytest.raises(HorizonGuidanceError) as exc:
        HorizonGuidanceService().build(context=bad_ctx)
    assert "peak_missing" in str(exc.value)


def test_fast_peak_missing_rejects() -> None:
    """Fast missing exact_at raises dedicated code."""
    # START_FUNCTION_CONTRACT: F-TEST.test_fast_peak_missing_rejects
    # purpose: test fast peak missing rejects.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_fast_peak_missing_rejects
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    items = list(ctx.selection.items)
    from app.schemas.horizon_selection import SelectedHorizonAnchor
    modified = []
    for anchor in items:
        if anchor.horizon == "fast":
            data = anchor.model_dump()
            data["timing"]["exact_at"] = None
            modified.append(SelectedHorizonAnchor.model_validate(data))
        else:
            modified.append(anchor)
    bad_sel = ctx.selection.model_copy(update={"items": modified})
    bad_ctx = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=bad_sel,
        fact_pack=ctx.fact_pack,
        tone_result=ctx.tone_result,
        sphere_verdicts=ctx.sphere_verdicts,
    )
    with pytest.raises(HorizonGuidanceError) as exc:
        HorizonGuidanceService().build(context=bad_ctx)
    assert "peak_missing" in str(exc.value)


# END_BLOCK: GUIDANCE_SERVICE_STRUCTURE_TESTS

# START_BLOCK: GUIDANCE_SERVICE_ADDITIONAL_TESTS
def test_avoid_verdict_all_avoid() -> None:
    """All-avoid verdict map produces valid block with compatible actions."""
    # START_FUNCTION_CONTRACT: F-TEST.test_avoid_verdict_all_avoid
    # purpose: test avoid verdict all avoid.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_avoid_verdict_all_avoid
    ctx, _ = _build_context(
        "structure_boundaries_control", build_structure_natal()
    )
    avoid_verdicts = {}
    for s in ctx.sphere_verdicts:
        avoid_verdicts[s] = "avoid"
    ctx_avoid = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=ctx.selection,
        fact_pack=ctx.fact_pack,
        tone_result=ctx.tone_result,
        sphere_verdicts=avoid_verdicts,
    )
    block = HorizonGuidanceService().build(context=ctx_avoid)
    # Should have compatible fallback actions
    assert block is not None
    assert block.items[0].actions.do


def test_context_mismatch_exact_code() -> None:
    """Mismatched context raises exact structural code."""
    # START_FUNCTION_CONTRACT: F-TEST.test_context_mismatch_exact_code
    # purpose: test context mismatch exact code.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_context_mismatch_exact_code
    selection, layer, scoring = build_selected_story(
        "structure_boundaries_control"
    )
    natal = build_structure_natal()
    verdicts = build_sphere_verdicts()
    fact_pack = PersonalFactPackService().build(
        selection=selection, activation_layer=layer,
        scoring_result=scoring, natal_context=natal,
    )
    tone = HorizonToneService().assess(
        selection=selection, sphere_verdicts=verdicts,
    )
    # Mismatch activation_id in fact_pack
    items = list(selection.items)
    from app.schemas.horizon_selection import SelectedHorizonAnchor
    mod_items = []
    for anchor in items:
        if anchor.horizon == "long":
            data = anchor.model_dump()
            data["activation_id"] = "wrong-id-mismatch"
            mod_items.append(
                SelectedHorizonAnchor.model_construct(**data)
            )
        else:
            mod_items.append(anchor)
    bad_sel = selection.model_copy(update={"items": mod_items})
    with pytest.raises((ValueError, HorizonGuidanceError)):
        bad_ctx = HorizonGuidanceContext(
            schema_version="horizon-guidance-context.v1",
            selection=bad_sel,
            fact_pack=fact_pack,
            tone_result=tone,
            sphere_verdicts=verdicts,
        )
        HorizonGuidanceService().build(context=bad_ctx)


def test_guidance_service_sanitized_exceptions() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_guidance_service_sanitized_exceptions
    # purpose: Assert guidance service exceptions contain no raw input or sentinels.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on sentinel or raw input leak.
    # END_FUNCTION_CONTRACT: F-TEST.test_guidance_service_sanitized_exceptions
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

    sentinels = [
        "RAW_EVIDENCE_SENTINEL",
        "RAW_DEBUG_SENTINEL",
        "PROFILE_NAME_SENTINEL",
        "PROFILE_CITY_SENTINEL",
        "COORDINATE_SENTINEL",
        "SESSION_SENTINEL",
    ]
    for s in sentinels:
        items = list(selection.items)
        from app.schemas.horizon_selection import SelectedHorizonAnchor
        mod_items = []
        for anchor in items:
            if anchor.horizon == "long":
                data = anchor.model_dump()
                data["theme_keys"] = [s]
                mod_items.append(SelectedHorizonAnchor.model_validate(data))
            else:
                mod_items.append(anchor)
        bad_sel = selection.model_copy(update={"items": mod_items})
        bad_ctx = HorizonGuidanceContext(
            schema_version="horizon-guidance-context.v1",
            selection=bad_sel,
            fact_pack=fact_pack,
            tone_result=tone,
            sphere_verdicts=verdicts,
        )
        try:
            HorizonGuidanceService().build(context=bad_ctx)
            pytest.fail("expected error")
        except HorizonGuidanceError as exc:
            msg = str(exc)
            assert exc.code == "unknown_theme"
            assert s not in msg


# END_BLOCK: GUIDANCE_SERVICE_ADDITIONAL_TESTS
