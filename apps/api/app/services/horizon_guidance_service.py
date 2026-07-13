# ############################################################################
# AI_HEADER: HORIZON_GUIDANCE_SERVICE — deterministic B2B2 guidance construction.
# ROLE: Builds a complete TodayV2HorizonsBlock from accepted B2B1 context.
#       Owns only preflight, theme resolution, orchestration, public block
#       construction. Delegates manifestations/claims/actions/technique to
#       HorizonGuidanceBuilders.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-GUIDANCE-SERVICE
# purpose: Accept validated HorizonGuidanceContext and produce a typed public
#          TodayV2HorizonsBlock with deterministic intro, horizons,
#          manifestations, actions, strength/risk, and technique explanations.
# owns:
#   - apps/api/app/services/horizon_guidance_service.py
# inputs: HorizonGuidanceContext, cached content canons, formatter, builders.
# outputs: TodayV2HorizonsBlock with schema_version="today-horizons.v1",
#          guidance_mode="deterministic".
# dependencies: typing stdlib, B1/B2A/B2B schemas, guidance formatter,
#               guidance builders, content canon service.
# side_effects: reads cached content canon only.
# emitted_logs: none.
# invariants:
#   - No catch-and-partial return; structural errors propagate as
#     HorizonGuidanceError.
#   - Medium/fast missing exact_at or peak_label rejects with dedicated codes.
#   - Output is byte-identical for identical typed inputs.
# failure_policy: raises HorizonGuidanceError on preflight, boundary, or
#   missing-canon failures.
# END_MODULE_CONTRACT: M-HORIZON-GUIDANCE-SERVICE

# START_MODULE_MAP: M-HORIZON-GUIDANCE-SERVICE
# public_entrypoints:
#   - HorizonGuidanceService.build
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_service.py
# END_MODULE_MAP: M-HORIZON-GUIDANCE-SERVICE

# START_BLOCK: GUIDANCE_SERVICE
from __future__ import annotations

from app.schemas.horizon_content_canon import HorizonContentCanonBundle
from app.schemas.horizon_guidance import (
    HorizonGuidanceContext,
    HorizonGuidanceError,
)
from app.schemas.horizon_selection import SelectedHorizonTriple
from app.schemas.today_horizons import (
    TodayV2Horizon,
    TodayV2HorizonIntro,
    TodayV2HorizonsBlock,
)
from app.services.horizon_content_canon_service import load_horizon_content_canons
from app.services.horizon_guidance_builders import (
    assign_claims,
    build_actions,
    build_eligible_claims,
    build_manifestations,
    build_technique_explanation,
)
from app.services.horizon_guidance_formatter import HorizonGuidanceFormatter


class HorizonGuidanceService:
    """Deterministic guidance builder consuming accepted B2B1 context."""

    def __init__(
        self,
        formatter: HorizonGuidanceFormatter | None = None,
    ) -> None:
        self._formatter = formatter or HorizonGuidanceFormatter()
        self._bundle: HorizonContentCanonBundle | None = None

    @property
    def bundle(self) -> HorizonContentCanonBundle:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE.bundle
        # purpose: Lazy-load content canons once per service instance.
        # inputs: self.
        # returns: HorizonContentCanonBundle.
        # side_effects: reads canons from disk on first access.
        # emitted_logs: none.
        # error_behavior: propagates file/parse errors.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE.bundle
        if self._bundle is None:
            self._bundle = load_horizon_content_canons()
        return self._bundle

    @property
    def formatter(self) -> HorizonGuidanceFormatter:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE.formatter
        # purpose: Expose held formatter reference.
        # inputs: self.
        # returns: HorizonGuidanceFormatter.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE.formatter
        return self._formatter

    def build(
        self,
        *,
        context: HorizonGuidanceContext,
    ) -> TodayV2HorizonsBlock:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE.build
        # purpose: Build a complete deterministic TodayV2HorizonsBlock from
        #          validated context.
        # inputs: context - validated HorizonGuidanceContext.
        # returns: typed TodayV2HorizonsBlock.
        # side_effects: reads cached content canon.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError on any
        #   preflight/boundary/missing-canon failure.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE.build
        self._preflight(context)
        primary_theme = self._resolve_primary_theme(context.selection)
        intro = self._build_intro(context, primary_theme)
        canon = self.bundle
        items: list[TodayV2Horizon] = []
        eligible_facts = build_eligible_claims(context.fact_pack)
        used_fact_ids: set[str] = set()

        for anchor, tone_assessment in zip(
            context.selection.items,
            context.tone_result.items,
            strict=True,
        ):
            horizon = anchor.horizon
            horizon_theme = self._resolve_horizon_theme(anchor, primary_theme)
            timing = anchor.timing
            presented = self.formatter.format_timing(
                horizon=horizon, timing=timing
            )
            tone = tone_assessment.tone
            language = canon.language

            final_timing = presented.public_timing
            eyebrow = language.horizons[horizon].eyebrow
            theme_lang = language.themes[horizon_theme]
            title = getattr(theme_lang, horizon).title
            summary = getattr(theme_lang, horizon).plain_explanation
            tone_label = language.tone_labels.get(tone, "")
            state_label_canon = language.timing_state_labels.get(
                timing.timing_state or "background", ""
            )
            plain_explanation = (
                f"{tone_label}. {state_label_canon}. "
                f"{final_timing.range_label}."
            )

            likely_spheres = list(anchor.product_spheres)

            manifestations = build_manifestations(
                horizon=horizon,
                likely_spheres=likely_spheres,
                activation_id=anchor.activation_id,
                canon=canon,
                formatter=self.formatter,
            )

            strength, risk = assign_claims(
                horizon=horizon,
                anchor=anchor,
                eligible_facts=eligible_facts,
                used_fact_ids=used_fact_ids,
                horizon_theme=horizon_theme,
                likely_spheres=likely_spheres,
                canon=canon,
            )

            actions = build_actions(
                horizon=horizon,
                anchor=anchor,
                horizon_theme=horizon_theme,
                tone=tone,
                sphere_verdicts=context.sphere_verdicts,
                timing=final_timing,
                valid_until_label=presented.valid_until_label,
                canon=canon,
            )

            technique_explanation = build_technique_explanation(
                horizon=horizon,
                anchor=anchor,
                horizon_theme=horizon_theme,
                timing=final_timing,
                active_from_label=presented.active_from_label,
                active_until_label=presented.active_until_label,
                exact_at_label=presented.exact_at_label,
                valid_until_label=presented.valid_until_label,
                timezone_suffix=presented.timezone_suffix,
                range_label=final_timing.range_label,
                peak_label=final_timing.peak_label,
                state_label=final_timing.state_label,
                tone=tone,
                likely_spheres=likely_spheres,
                canon=canon,
                formatter=self.formatter,
            )

            horizon_model = TodayV2Horizon(
                id=f"horizon.{horizon}",
                horizon=horizon,
                tone=tone,
                eyebrow=eyebrow,
                title=title,
                summary=summary,
                plain_explanation=plain_explanation,
                timing=final_timing,
                likely_spheres=likely_spheres,
                manifestations=manifestations,
                strength=strength,
                risk=risk,
                actions=actions,
                technique_explanations=[technique_explanation],
                activation_ids=[anchor.activation_id],
            )
            items.append(horizon_model)

        return TodayV2HorizonsBlock(
            schema_version="today-horizons.v1",
            guidance_mode="deterministic",
            intro=intro,
            items=items,
            warnings=[],
        )

    # END_BLOCK: GUIDANCE_SERVICE

    # START_BLOCK: GUIDANCE_PREFLIGHT
    def _preflight(self, context: HorizonGuidanceContext) -> None:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE._preflight
        # purpose: Validate input context before any construction work.
        # inputs: context - HorizonGuidanceContext.
        # returns: none.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError with dedicated code.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SERVICE._preflight
        for anchor in context.selection.items:
            if anchor.horizon in ("medium", "fast"):
                if anchor.timing.exact_at is None:
                    raise HorizonGuidanceError(
                        f"{anchor.horizon}_peak_missing",
                        f"items[{anchor.horizon}].timing.exact_at",
                    )
            t = anchor.timing
            if t.precision is None or t.timing_state is None:
                raise HorizonGuidanceError(
                    "invalid_timing_value",
                    f"items[{anchor.horizon}].timing.precision",
                )
            if t.active_from is None or t.active_until is None:
                raise HorizonGuidanceError(
                    "invalid_timing_value",
                    f"items[{anchor.horizon}].timing.bounds",
                )
            if not anchor.product_spheres or len(anchor.product_spheres) > 3:
                raise HorizonGuidanceError(
                    "invalid_timing_value",
                    f"items[{anchor.horizon}].product_spheres",
                )
            if not anchor.theme_keys:
                raise HorizonGuidanceError(
                    "unknown_theme",
                    f"items[{anchor.horizon}].theme_keys",
                )
            if not anchor.activation_id or len(anchor.activation_id) > 160:
                raise HorizonGuidanceError(
                    "context_alignment_invalid",
                    f"items[{anchor.horizon}].activation_id",
                )

        canon = self.bundle
        for anchor in context.selection.items:
            for sphere in anchor.product_spheres:
                if sphere not in canon.language.product_spheres:
                    raise HorizonGuidanceError(
                        "unknown_entity_label",
                        "sphere",
                    )
            for theme in anchor.theme_keys:
                if theme not in canon.language.themes:
                    raise HorizonGuidanceError(
                        "unknown_theme", "theme"
                    )

    # END_BLOCK: GUIDANCE_PREFLIGHT

    # START_BLOCK: GUIDANCE_THEME_INTRO
    def _resolve_primary_theme(
        self, selection: SelectedHorizonTriple
    ) -> str:
        if not selection.shared_theme_keys:
            raise HorizonGuidanceError(
                "unknown_theme", "selection.shared_theme_keys"
            )
        return selection.shared_theme_keys[0]

    def _resolve_horizon_theme(
        self, anchor: object, primary_theme: str
    ) -> str:
        a = anchor
        if primary_theme in a.theme_keys:
            return primary_theme
        if a.theme_keys:
            return a.theme_keys[0]
        raise HorizonGuidanceError(
            "unknown_theme",
            f"items[{a.horizon}].theme_keys",
        )

    def _build_intro(
        self, context: HorizonGuidanceContext, primary_theme: str
    ) -> TodayV2HorizonIntro:
        canon = self.bundle.language
        theme = canon.themes.get(primary_theme)
        if theme is None:
            raise HorizonGuidanceError(
                "unknown_theme", "intro"
            )
        selected_ids = [
            item.activation_id for item in context.selection.items
        ]
        return TodayV2HorizonIntro(
            eyebrow="Личная логика периода",
            headline=theme.headline,
            body=theme.intro_body,
            theme_key=primary_theme,
            activation_ids=selected_ids,
        )

    # END_BLOCK: GUIDANCE_THEME_INTRO


__all__ = ["HorizonGuidanceService"]
