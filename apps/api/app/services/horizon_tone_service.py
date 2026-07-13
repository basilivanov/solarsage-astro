# ############################################################################
# AI_HEADER: HORIZON_TONE_SERVICE — pure deterministic B2B1 machine tone assessment.
# ROLE: Combines accepted B2A anchor features with supplied product-sphere verdicts without reading human copy.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-TONE-SERVICE
# purpose: Produce deterministic long/medium/fast tone assessments from selected anchor data and verdict mapping.
# owns:
#   - apps/api/app/services/horizon_tone_service.py
# inputs: SelectedHorizonTriple and explicit product-sphere verdict mapping.
# outputs: HorizonToneResult with score provenance only.
# dependencies: math/typing stdlib, B2A selection schema, B2B content canon loader, tone schema.
# side_effects: reads cached content canon only.
# emitted_logs: none.
# invariants:
#   - Does not inspect Russian labels, public actions, CSS, DB, LLM, network, or clocks.
#   - Mapping insertion order cannot affect output.
# failure_policy: rejects unknown verdict input; invalid canon or model state propagates.
# END_MODULE_CONTRACT: M-HORIZON-TONE-SERVICE

# START_MODULE_MAP: M-HORIZON-TONE-SERVICE
# public_entrypoints:
#   - HorizonToneService.assess
# semantic_blocks:
#   - HORIZON_TONE_HELPERS: score rounding and closed input validation.
#   - HORIZON_TONE_SERVICE: per-anchor tone assessment algorithm.
# owned_tests:
#   - apps/api/tests/test_horizon_tone_service.py
# END_MODULE_MAP: M-HORIZON-TONE-SERVICE

# START_BLOCK: HORIZON_TONE_HELPERS
from __future__ import annotations

from typing import Mapping

from app.schemas.horizon_content_canon import HorizonSphereVerdict, PRODUCT_SPHERE_ORDER
from app.schemas.horizon_selection import SelectedHorizonTriple
from app.schemas.horizon_tone import HorizonToneAssessment, HorizonToneResult
from app.schemas.today_horizons import TodayV2ProductSphereKey
from app.services.horizon_content_canon_service import load_horizon_content_canons

_POLARITY_VALUES: dict[str, float] = {
    "supportive": 1.0,
    "neutral": 0.0,
    "tense": -1.0,
    "mixed": 0.0,
}


def _round_canon(value: float, digits: int) -> float:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SERVICE._round_canon
    # purpose: Apply the exact reviewed score precision supplied by the loaded tone canon.
    # inputs: value - computed finite tone component; digits - canon rounding precision.
    # returns: canon-precision rounded float.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SERVICE._round_canon
    return round(value + 0.0, digits)


def _validate_verdicts(verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict]) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SERVICE._validate_verdicts
    # purpose: Reject unknown sphere keys or verdict strings before any score computation.
    # inputs: verdicts - caller-provided explicit product-sphere verdict mapping.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for unknown keys or verdicts.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SERVICE._validate_verdicts
    allowed_keys = set(PRODUCT_SPHERE_ORDER)
    allowed_verdicts = {"good", "neutral", "caution", "avoid"}
    for sphere, verdict in verdicts.items():
        if sphere not in allowed_keys or verdict not in allowed_verdicts:
            raise ValueError("sphere_verdicts: unknown sphere or verdict")


# END_BLOCK: HORIZON_TONE_HELPERS


# START_BLOCK: HORIZON_TONE_SERVICE
class HorizonToneService:
    def assess(
        self,
        *,
        selection: SelectedHorizonTriple,
        sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
    ) -> HorizonToneResult:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SERVICE.HorizonToneService.assess
        # purpose: Assess deterministic machine tone for every accepted selected horizon anchor.
        # inputs: selection - B2A selected triple; sphere_verdicts - explicit caller-owned verdict mapping.
        # returns: ordered HorizonToneResult.
        # side_effects: reads cached content canon only.
        # emitted_logs: none.
        # error_behavior: raises ValueError on unknown verdict input; canon/model errors propagate.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SERVICE.HorizonToneService.assess
        _validate_verdicts(sphere_verdicts)
        rules = load_horizon_content_canons().language.tone_rules
        digits = rules.rounding_digits
        assessments: list[HorizonToneAssessment] = []
        for anchor in selection.items:
            features = anchor.feature_scores
            activation_confidence = _round_canon(
                features.strength * rules.feature_weights.strength
                + features.contribution * rules.feature_weights.contribution
                + features.convergence * rules.feature_weights.convergence
                + anchor.impact_score * rules.feature_weights.impact,
                digits,
            )
            activation_component = _round_canon(_POLARITY_VALUES[anchor.polarity] * activation_confidence, digits)
            used_spheres = tuple(sphere for sphere in anchor.product_spheres if sphere in sphere_verdicts)
            if used_spheres:
                sphere_component = _round_canon(
                    sum(rules.verdict_values[sphere_verdicts[sphere]] for sphere in used_spheres) / len(used_spheres),
                    digits,
                )
            else:
                sphere_component = 0.0
            net_score = _round_canon(
                activation_component * rules.activation_weight + sphere_component * rules.sphere_verdict_weight,
                digits,
            )
            opposing = (
                activation_component * sphere_component < 0
                and abs(activation_component) >= rules.mixed_opposing_min
                and abs(sphere_component) >= rules.mixed_opposing_min
            )
            if anchor.polarity == "mixed" or opposing:
                tone = "mixed"
            elif net_score >= rules.supportive_min:
                tone = "supportive"
            elif net_score <= rules.tense_max:
                tone = "tense"
            else:
                tone = "neutral"
            assessments.append(
                HorizonToneAssessment(
                    horizon=anchor.horizon,
                    tone=tone,
                    activation_confidence=activation_confidence,
                    activation_component=activation_component,
                    sphere_component=sphere_component,
                    net_score=net_score,
                    opposing_material_evidence=opposing,
                    activation_ids=(anchor.activation_id,),
                    sphere_keys=used_spheres,
                )
            )
        return HorizonToneResult(schema_version="horizon-tone.v1", items=tuple(assessments))


# END_BLOCK: HORIZON_TONE_SERVICE


__all__ = ["HorizonToneService"]
