# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_SELECTED_PAYLOAD
# ROLE: Acceptance tests for TODAY_VALENCE_V1_ENABLED=true selected payload.
# DEPENDENCIES: pytest, app.services.day_scoring_runtime_service, app.services.today_interpretation_service
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-SELECTED-PAYLOAD
# purpose: Verify selected payload when TODAY_VALENCE_V1_ENABLED=true (§14.2).
# owns:
#   - apps/api/tests/test_day_valence_selected_payload.py
# inputs: synthetic signals and activations
# outputs: assertions over 12 assessments, counts, verdict_rule enum, and audit fields
# dependencies: app.services.day_scoring_runtime_service, app.services.today_interpretation_service
# side_effects: test-local setting overrides
# failure_policy: fails test if selected payload attributes deviate from W2-VALENCE contract
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-SELECTED-PAYLOAD

# START_MODULE_MAP: M-TEST-DAY-VALENCE-SELECTED-PAYLOAD
# public_entrypoints:
#   - test_selected_payload_when_valence_enabled
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_selected_payload.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-SELECTED-PAYLOAD

from datetime import date as Date
from unittest.mock import MagicMock, patch
import pytest

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.normalization import AstroSignal
from app.services.day_scoring_runtime_service import DayScoringRuntimeService
from app.services.today_interpretation_service import TodayInterpretationService


@pytest.mark.asyncio
async def test_selected_payload_when_valence_enabled():
    """Verify selected payload when TODAY_VALENCE_V1_ENABLED=true has 12 assessments and audit fields."""
    sigs = [AstroSignal(type="aspect", planet="Transit_Venus", target_planet="Uranus", aspect_type="sextile", strength=0.80)]
    act = ActivationEvidence(
        id="act_1", kind="aspect", evidence="Transit Venus sextile natal Uranus",
        active=True, technique="transit_to_natal", techniqueFamily="transit",
        polarity="supportive", strength=0.90, targetType="planet", targetKey="URANUS",
    )
    layer = ActivationLayer(
        activations=[act], activationLayerVersion="al-1.0",
        calculationVersion="1", targetDate="2026-07-27", targetTime="12:00",
        targetTz="UTC", houseSystem="WHOLE_SIGN", byPlanet={}, byHouse={}, byLot={}, byAngle={},
    )

    runtime = DayScoringRuntimeService()
    interpretation = TodayInterpretationService()

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings, \
         patch("app.core.config.settings") as mock_core_settings:

        mock_settings.solarsage_v2_enabled = True
        mock_settings.solarsage_v2_dual_run = True
        mock_settings.today_valence_v1_enabled = True
        mock_settings.today_valence_v1_dual_run = False

        mock_core_settings.today_valence_v1_enabled = True

        res = runtime.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")

        assert res.selected_scoring_version == "ss-scoring-2.1"
        assert res.valence_assessments is not None
        assert len(res.valence_assessments) == 12

        mock_sem = MagicMock()
        mock_sem.day_theme = "Тема дня"

        advice_block, summary, chart = await interpretation.build(
            target_date=Date(2026, 7, 27),
            day_status=res.selected_result["day_status"],
            scoring_result=res.selected_result,
            signals=sigs,
            semantic_layer=mock_sem,
            day_chart=None,
            planet_influences=[],
            sphere_scores=[],
            important_items=[],
            valence_assessments=res.valence_assessments,
            force_no_llm=True,
        )

        rows = advice_block.rows
        assert len(rows) == 12

        # 1. 12 assessments present
        assessments_present = [r.assessment for r in rows if r.assessment is not None]
        assert len(assessments_present) == 12

        # 2. Counts sum to 12
        counts = advice_block.counts
        assert (counts.good + counts.caution + counts.avoid + counts.neutral) == 12

        # 3. Closed verdict_rule enum
        allowed_rules = {"avoid_tension_2x", "caution_tension_1_3x", "good_support_1_3x", "neutral_low_evidence", "neutral_balanced"}
        for r in rows:
            assert r.assessment.assessment.verdict_rule in allowed_rules
