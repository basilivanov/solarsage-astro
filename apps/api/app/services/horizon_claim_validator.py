# ############################################################################
# AI_HEADER: HORIZON_CLAIM_VALIDATOR — deterministic claim validation for B2B2 output.
# ROLE: Validates every public claim in a TodayV2HorizonsBlock against its
#       guidance context and activation evidence. Delegates policy checks
#       to HorizonClaimPolicy and HorizonGuidanceBuilders.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CLAIM-VALIDATOR
# purpose: Validate deterministic output by cross-referencing every public
#          claim, timing label, sphere reference, action authorization,
#          conditional policy, privacy sentinel, and date/number integrity.
#          Delegates detailed policy to horizon_claim_policy and builders.
# owns:
#   - apps/api/app/services/horizon_claim_validator.py
# inputs: TodayV2HorizonsBlock, HorizonGuidanceContext, ActivationEvidence seq.
# outputs: The same block when valid; raises HorizonClaimValidationError.
# dependencies: re/typing stdlib, B1 schemas, guidance context/error schemas,
#               activation, guidance builders, claim policy, formatter.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Returns the same block object/value when valid.
#   - Every validation error is a sanitized HorizonClaimValidationError.
# failure_policy: raises HorizonClaimValidationError on first violation.
# END_MODULE_CONTRACT: M-HORIZON-CLAIM-VALIDATOR

# START_MODULE_MAP: M-HORIZON-CLAIM-VALIDATOR
# public_entrypoints:
#   - HorizonClaimValidator.validate
# semantic_blocks:
#   - VALIDATOR_SOURCE_MAPS: index building from context and evidence.
#   - VALIDATOR_ORCHESTRATION: cross-ref, alignment, timing, claims,
#     manifestations, technique, delegation to policy.
#   - VALIDATOR_FAILURE_HELPER: sanitized error constructor.
# owned_tests:
#   - apps/api/tests/test_horizon_claim_validator.py
# END_MODULE_MAP: M-HORIZON-CLAIM-VALIDATOR

# START_BLOCK: VALIDATOR_IMPORTS
from __future__ import annotations

from typing import Sequence

from app.schemas.activation import ActivationEvidence
from app.schemas.horizon_content_canon import HorizonContentCanonBundle
from app.schemas.horizon_guidance import (
    HorizonClaimValidationError,
    HorizonGuidanceContext,
)
from app.schemas.horizon_selection import (
    HORIZON_ORDER,
    SelectedHorizonAnchor,
    SelectedHorizonTriple,
)
from app.schemas.personal_fact_pack import PersonalFact, PersonalFactPack
from app.schemas.today_horizons import (
    TodayV2HorizonId,
    TodayV2HorizonsBlock,
    validate_horizons_against_evidence,
)
from app.services.horizon_claim_policy import (
    check_action_authorization,
    check_conditional_and_unsupported_policy,
    check_no_raw_leakage,
    check_numeric_integrity,
)
from app.services.horizon_content_canon_service import load_horizon_content_canons
from app.services.horizon_guidance_builders import (
    build_technique_explanation,
    ordered_intersection,
    statement_text_for_fact,
    build_manifestations,
    build_actions,
    build_eligible_claims,
    assign_claims,
)
from app.services.horizon_guidance_formatter import HorizonGuidanceFormatter

# END_BLOCK: VALIDATOR_IMPORTS


# START_BLOCK: VALIDATOR_SERVICE
class HorizonClaimValidator:
    """Deterministic claim validator delegating to policy module."""

    def __init__(
        self, formatter: HorizonGuidanceFormatter | None = None,
    ) -> None:
        self._formatter = formatter or HorizonGuidanceFormatter()
        self._bundle: HorizonContentCanonBundle | None = None

    @property
    def bundle(self) -> HorizonContentCanonBundle:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-VALIDATOR.bundle
        # purpose: Lazy-load content canons once per validator instance.
        # inputs: self.
        # returns: HorizonContentCanonBundle.
        # side_effects: reads canons from disk on first access.
        # emitted_logs: none.
        # error_behavior: propagates file/parse errors.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-VALIDATOR.bundle
        if self._bundle is None:
            self._bundle = load_horizon_content_canons()
        return self._bundle

    def validate(
        self,
        *,
        block: TodayV2HorizonsBlock,
        context: HorizonGuidanceContext,
        activation_evidence: Sequence[ActivationEvidence],
    ) -> TodayV2HorizonsBlock:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-VALIDATOR.validate
        # purpose: Validate all public claims in a deterministic block.
        # inputs: block, context, activation_evidence.
        # returns: validated TodayV2HorizonsBlock.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonClaimValidationError on first violation.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-CLAIM-VALIDATOR.validate
        canon = self.bundle
        anchor_by_h = self._anchor_map(context.selection)
        fact_by_id = self._fact_map(context.fact_pack)
        tone_by_h = self._tone_map(context)

        # Whole block requirements
        if block.schema_version != "today-horizons.v1":
            _fail("intro_alignment_invalid", "schema_version")
        if block.guidance_mode != "deterministic":
            _fail("intro_alignment_invalid", "guidance_mode")
        if block.warnings != []:
            _fail("intro_alignment_invalid", "warnings")

        # Check for duplicate evidence IDs before cross-reference
        ev_ids = [e.id for e in activation_evidence]
        if len(ev_ids) != len(set(ev_ids)):
            _fail("evidence_duplicate", "duplicate_evidence")

        # Step 1: Policy scans first — forbidden, unsupported, leakage, numeric
        # across ALL user-visible fields before exact alignment.
        check_action_authorization(
            block=block, context=context,
            anchor_by_horizon=anchor_by_h, canon=canon,
        )
        check_conditional_and_unsupported_policy(block=block, canon=canon)
        leaked_ids = {e.id for e in activation_evidence} | set(fact_by_id)
        check_no_raw_leakage(
            block=block, forbidden_ids=leaked_ids,
            forbidden_tokens={"RAW_EVIDENCE_SENTINEL", "RAW_DEBUG_SENTINEL",
                              "PROFILE_NAME_SENTINEL", "PROFILE_CITY_SENTINEL",
                              "COORDINATE_SENTINEL", "SESSION_SENTINEL"},
        )
        check_numeric_integrity(block=block, canon=canon)

        # Step 2: Exact deterministic alignment
        self._align(block, context, anchor_by_h, tone_by_h, fact_by_id, canon)
        self._check_timing(block, anchor_by_h, tone_by_h, canon)
        self._check_claims(block, anchor_by_h, fact_by_id, canon, context)
        self._check_manifestations(block, anchor_by_h, canon)
        self._check_actions(block, anchor_by_h, tone_by_h, canon, context)
        self._check_technique(block, anchor_by_h, canon, context, tone_by_h)

        # Step 3: Public cross-reference defense in depth
        try:
            validate_horizons_against_evidence(block, activation_evidence)
        except ValueError as exc:
            raise HorizonClaimValidationError(
                "public_cross_reference_invalid", "cross_reference_mismatch"
            ) from exc
        return block

    def _anchor_map(
        self, sel: SelectedHorizonTriple,
    ) -> dict[TodayV2HorizonId, SelectedHorizonAnchor]:
        return {i.horizon: i for i in sel.items}

    def _fact_map(
        self, fp: PersonalFactPack,
    ) -> dict[str, PersonalFact]:
        return {f.id: f for f in fp.facts}

    def _tone_map(
        self, ctx: HorizonGuidanceContext,
    ) -> dict[TodayV2HorizonId, str]:
        return {i.horizon: i.tone for i in ctx.tone_result.items}

    def _align(
        self, block, ctx, a_map, t_map, f_map, canon,
    ) -> None:
        pk = ctx.selection.shared_theme_keys[0]
        if block.intro.theme_key != pk:
            _fail("intro_alignment_invalid", "theme_key")
        eids = [a.activation_id for a in ctx.selection.items]
        if block.intro.activation_ids != eids:
            _fail("intro_alignment_invalid", "activation_ids")
        if block.intro.eyebrow != "Личная логика периода":
            _fail("intro_alignment_invalid", "eyebrow")
        theme_lang = canon.language.themes.get(pk)
        if theme_lang:
            if block.intro.headline != theme_lang.headline:
                _fail("intro_alignment_invalid", "headline")
            if block.intro.body != theme_lang.intro_body:
                _fail("intro_alignment_invalid", "body")
        if [h.horizon for h in block.items] != list(HORIZON_ORDER):
            _fail("horizon_alignment_invalid", "order")
        seen = set()
        for h_idx, hi in enumerate(block.items):
            h = hi.horizon
            a = a_map.get(h)
            if a is None:
                _fail("horizon_alignment_invalid", f"items[{h_idx}]")
            if hi.id != f"horizon.{h}":
                _fail("horizon_alignment_invalid", f"items[{h_idx}].id")
            hl = canon.language.horizons.get(h)
            if hl and hi.eyebrow != hl.eyebrow:
                _fail("horizon_alignment_invalid", f"items[{h_idx}].eyebrow")
            h_theme_keys = a.theme_keys
            h_theme = pk if pk in h_theme_keys else (h_theme_keys[0] if h_theme_keys else pk)
            ht = canon.language.themes.get(h_theme)
            if ht:
                title = getattr(ht, h, None)
                if title and hi.title != getattr(title, "title", ""):
                    _fail("horizon_alignment_invalid", f"items[{h_idx}].title")
                if title and hi.summary != getattr(title, "plain_explanation", ""):
                    _fail("horizon_alignment_invalid", f"items[{h_idx}].summary")
            if hi.activation_ids != [a.activation_id]:
                _fail("horizon_alignment_invalid", f"items[{h_idx}].activation_ids")
            et = t_map.get(h)
            if et and hi.tone != et:
                _fail("tone_alignment_invalid", f"items[{h_idx}].tone")
            if list(hi.likely_spheres) != list(a.product_spheres):
                _fail("sphere_alignment_invalid", f"items[{h_idx}].likely_spheres")
            if hi.strength:
                for fid in hi.strength.provenance.natal_fact_ids:
                    if fid in seen:
                        _fail("fact_reused", f"items[{h_idx}].strength.provenance.natal_fact_ids")
                    seen.add(fid)
            if hi.risk:
                for fid in hi.risk.provenance.natal_fact_ids:
                    if fid in seen:
                        _fail("fact_reused", f"items[{h_idx}].risk.provenance.natal_fact_ids")
                    seen.add(fid)

    def _check_timing(self, block, a_map, t_map, canon) -> None:
        for h_idx, hi in enumerate(block.items):
            h = hi.horizon
            a = a_map.get(h)
            if a is None:
                continue
            pres = self._formatter.format_timing(horizon=h, timing=a.timing)
            if hi.timing.model_dump() != pres.public_timing.model_dump():
                _fail("timing_alignment_invalid", f"items[{h_idx}].timing")
            if hi.actions.valid_until != pres.public_timing.active_until:
                _fail("timing_alignment_invalid", f"items[{h_idx}].actions.valid_until")
            if hi.actions.valid_until_label != pres.valid_until_label:
                _fail("timing_alignment_invalid", f"items[{h_idx}].actions.valid_until_label")
            tone_lbl = (canon.language.tone_labels.get(t_map.get(h, ""), "")
                        if t_map else "")
            state_lbl = pres.public_timing.state_label or ""
            range_lbl = pres.public_timing.range_label or ""
            expected_plain = f"{tone_lbl}. {state_lbl}. {range_lbl}."
            if hi.plain_explanation != expected_plain:
                _fail("timing_alignment_invalid", f"items[{h_idx}].plain_explanation")

    def _check_claims(self, block, a_map, f_map, canon, context) -> None:
        eligible_facts = build_eligible_claims(context.fact_pack)
        used_fact_ids: set[str] = set()

        for h_idx, h in enumerate(HORIZON_ORDER):
            hi = next((item for item in block.items if item.horizon == h), None)
            if hi is None:
                _fail("horizon_alignment_invalid", f"items[{h_idx}]")
            a = a_map.get(h)
            if a is None:
                _fail("horizon_alignment_invalid", f"items[{h_idx}]")

            pk = context.selection.shared_theme_keys[0]
            h_theme_keys = a.theme_keys
            h_theme = pk if pk in h_theme_keys else (h_theme_keys[0] if h_theme_keys else pk)

            exp_strength, exp_risk = assign_claims(
                horizon=h,
                anchor=a,
                eligible_facts=eligible_facts,
                used_fact_ids=used_fact_ids,
                horizon_theme=h_theme,
                likely_spheres=a.product_spheres,
                canon=canon,
            )

            for item_name, item, exp in [("strength", hi.strength, exp_strength), ("risk", hi.risk, exp_risk)]:
                if (item is None) != (exp is None):
                    _fail("fact_provenance_invalid", f"items[{h_idx}].{item_name}")
                if item is not None and exp is not None:
                    if item.model_dump() != exp.model_dump():
                        _fail("fact_provenance_invalid", f"items[{h_idx}].{item_name}")

    def _check_manifestations(self, block, a_map, canon) -> None:
        for h_idx, hi in enumerate(block.items):
            h = hi.horizon
            a = a_map.get(h)
            if a is None:
                continue

            exp_manis = build_manifestations(
                horizon=h,
                likely_spheres=a.product_spheres,
                activation_id=a.activation_id,
                canon=canon,
                formatter=self._formatter,
            )

            if len(hi.manifestations) != len(exp_manis):
                _fail("manifestation_invalid", f"items[{h_idx}].manifestations")

            for m_idx, m in enumerate(hi.manifestations):
                em = exp_manis[m_idx]
                if m.model_dump() != em.model_dump():
                    _fail("manifestation_invalid", f"items[{h_idx}].manifestations[{m_idx}]")

    def _check_actions(self, block, a_map, t_map, canon, context) -> None:
        for h_idx, hi in enumerate(block.items):
            h = hi.horizon
            a = a_map.get(h)
            if a is None:
                continue

            pk = context.selection.shared_theme_keys[0]
            h_theme_keys = a.theme_keys
            h_theme = pk if pk in h_theme_keys else (h_theme_keys[0] if h_theme_keys else pk)

            pres = self._formatter.format_timing(horizon=h, timing=a.timing)

            exp_actions = build_actions(
                horizon=h,
                anchor=a,
                horizon_theme=h_theme,
                tone=t_map.get(h),
                sphere_verdicts=context.sphere_verdicts,
                timing=pres.public_timing,
                valid_until_label=pres.valid_until_label,
                canon=canon,
            )

            if hi.actions.model_dump() != exp_actions.model_dump():
                _fail("action_not_authorized", f"items[{h_idx}].actions")

    def _check_technique(self, block, a_map, canon, ctx=None, t_map=None) -> None:
        for h_idx, hi in enumerate(block.items):
            h = hi.horizon
            a = a_map.get(h)
            if a is None:
                continue
            pk = ctx.selection.shared_theme_keys[0]
            h_theme_keys = a.theme_keys
            h_theme = pk if pk in h_theme_keys else (h_theme_keys[0] if h_theme_keys else pk)
            pres = self._formatter.format_timing(horizon=h, timing=a.timing)
            exp_tx = build_technique_explanation(
                horizon=h, anchor=a, horizon_theme=h_theme,
                timing=pres.public_timing,
                active_from_label=pres.active_from_label,
                active_until_label=pres.active_until_label,
                exact_at_label=pres.exact_at_label,
                valid_until_label=pres.valid_until_label,
                timezone_suffix=pres.timezone_suffix,
                range_label=pres.public_timing.range_label,
                peak_label=pres.public_timing.peak_label,
                state_label=pres.public_timing.state_label,
                tone=t_map.get(h, "neutral"),
                likely_spheres=list(a.product_spheres),
                canon=canon, formatter=self._formatter,
            )
            if len(hi.technique_explanations) != 1:
                _fail("technique_invalid", f"items[{h_idx}].technique_explanations")
            if hi.technique_explanations[0].model_dump() != exp_tx.model_dump():
                _fail("technique_invalid", f"items[{h_idx}].technique_explanations[0]")


def _fail(code: str, detail: str = "") -> None:
    raise HorizonClaimValidationError(code, detail)


# END_BLOCK: VALIDATOR_SERVICE


__all__ = ["HorizonClaimValidator"]
