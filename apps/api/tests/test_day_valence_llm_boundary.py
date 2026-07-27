# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_LLM_BOUNDARY
# ROLE: Boundary spy test proving LLM receives NO numeric valence fields (§15).
# DEPENDENCIES: pytest, app.services.today_interpretation_service, app.services.llm_service
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-LLM-BOUNDARY
# purpose: Prove LLM prompts and context payloads never carry numeric assessment/verdict/balance fields from DayValenceService (§15).
# owns:
#   - apps/api/tests/test_day_valence_llm_boundary.py
# inputs: synthetic signals and activations
# outputs: assertions over LLM call args
# dependencies: app.services.today_interpretation_service, app.services.llm_service
# side_effects: test-local LLM mock spies
# failure_policy: fails test if numeric valence fields reach the LLM prompt
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-LLM-BOUNDARY

# START_MODULE_MAP: M-TEST-DAY-VALENCE-LLM-BOUNDARY
# public_entrypoints:
#   - test_llm_prompt_and_context_free_of_numeric_valence_fields
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_llm_boundary.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-LLM-BOUNDARY

import json
from datetime import date as Date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.normalization import AstroSignal
from app.services.day_scoring_runtime_service import DayScoringRuntimeService
from app.services.today_interpretation_service import TodayInterpretationService


@pytest.mark.asyncio
async def test_llm_prompt_and_context_free_of_numeric_valence_fields():
    """Prove LLM receives NO numeric assessment/verdict/balance fields from DayValenceService."""
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
         patch("app.core.config.settings") as mock_core_settings, \
         patch("app.services.today_interpretation_service.LLMService") as mock_llm_cls:

        mock_settings.solarsage_v2_enabled = True
        mock_settings.solarsage_v2_dual_run = True
        mock_settings.today_valence_v1_enabled = True
        mock_settings.today_valence_v1_dual_run = False
        mock_core_settings.today_valence_v1_enabled = True

        mock_llm = mock_llm_cls.return_value
        mock_llm.generate_concrete_advice = AsyncMock(return_value=None)
        mock_llm.generate_planet_interpretations = AsyncMock(return_value=None)

        res = runtime.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")

        mock_sem = MagicMock()
        mock_sem.day_theme = "Тема дня"

        await interpretation.build(
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
            force_no_llm=False,
        )

        mock_llm.generate_concrete_advice.assert_called_once()
        call_args = mock_llm.generate_concrete_advice.call_args
        contexts = call_args[0][0]  # list[dict] passed to generate_concrete_advice

        # Verify that contexts sent to LLM do NOT carry numeric valence fields
        forbidden_numeric_keys = {"support_score", "tension_score", "balance", "salience_score", "factor_count", "effective_factor_count"}

        for ctx in contexts:
            for forbidden in forbidden_numeric_keys:
                assert forbidden not in ctx, f"Forbidden numeric key {forbidden} found in LLM context for {ctx.get('key')}"

        # Dump entire context payload as JSON string and verify absence of numeric scores
        raw_json = json.dumps(contexts, ensure_ascii=False)
        assert "salience_score" not in raw_json
        assert "support_score" not in raw_json
        assert "tension_score" not in raw_json
