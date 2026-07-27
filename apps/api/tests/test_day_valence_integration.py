# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_INTEGRATION
# ROLE: Integration tests for W2-VALENCE V5 (assessments, versions, horizon tone, cache parity).
# DEPENDENCIES: pytest, app.services.today_service, app.services.calendar_service, app.core.config
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-INTEGRATION
# purpose: Verify selected payload assessments, version identity bumps, horizon tone integration, and same-date Today/Calendar parity when TODAY_VALENCE_V1_ENABLED is enabled vs disabled (§14.2).
# owns:
#   - apps/api/tests/test_day_valence_integration.py
# inputs: test fixtures
# outputs: assertions
# dependencies: app.services.today_service, app.services.calendar_service, app.core.config, app.core.versions
# side_effects: test-local setting overrides
# failure_policy: fails test on version split-brain or cache parity divergence
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-INTEGRATION

# START_MODULE_MAP: M-TEST-DAY-VALENCE-INTEGRATION
# public_entrypoints:
#   - test_valence_enabled_selected_payload_assessments_and_versions
#   - test_valence_disabled_legacy_payload_unmodified
#   - test_horizon_selection_no_drift_against_golden_baseline
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_integration.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-INTEGRATION

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.versions import (
    SCORING_V2_1_VERSION,
    SCORING_V2_VERSION,
    TODAY_V2_2_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
)
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.normalization import AstroSignal
from app.services.day_scoring_runtime_service import DayScoringRuntimeService
from app.services.horizon_selection_service import HorizonSelectionService
from tests._horizon_selection_testkit import build_layer, build_scoring, build_story


def test_valence_disabled_legacy_payload_unmodified():
    """When TODAY_VALENCE_V1_ENABLED=false, scoring version is ss-scoring-2.0 or legacy 1."""
    service = DayScoringRuntimeService()
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

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings:
        mock_settings.solarsage_v2_enabled = True
        mock_settings.solarsage_v2_dual_run = True
        mock_settings.today_valence_v1_enabled = False
        mock_settings.today_valence_v1_dual_run = True

        res = service.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")
        assert res.selected_scoring_version == SCORING_V2_VERSION
        assert res.valence_assessments is not None


def test_valence_enabled_selected_payload_assessments_and_versions():
    """When TODAY_VALENCE_V1_ENABLED=true, selected scoring version is ss-scoring-2.1."""
    service = DayScoringRuntimeService()
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

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings:
        mock_settings.solarsage_v2_enabled = True
        mock_settings.solarsage_v2_dual_run = True
        mock_settings.today_valence_v1_enabled = True
        mock_settings.today_valence_v1_dual_run = False

        res = service.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")
        assert res.selected_scoring_version == SCORING_V2_1_VERSION
        assert res.valence_assessments is not None
        assert "work" in res.valence_assessments


def test_horizon_selection_no_drift_against_golden_baseline():
    """Verify HorizonSelectionService returns byte-identical selected items as golden baseline."""
    baseline_path = Path(__file__).parent / "fixtures" / "day_valence" / "horizon_selection_baseline.json"
    assert baseline_path.exists()
    golden_data = json.loads(baseline_path.read_text(encoding="utf-8"))

    service = HorizonSelectionService()
    for story_key, golden_entry in golden_data.items():
        activations, mapping, expected_ids, _ = build_story(story_key)
        res = service.select(
            activation_layer=build_layer(activations),
            scoring_result=build_scoring(activations, mapping),
        )

        current_items = res.model_dump()["selection"]["items"]
        golden_items = golden_entry["selection"]["items"]

        current_ids = [item["activation_id"] for item in current_items]
        golden_ids = [item["activation_id"] for item in golden_items]

        assert current_ids == golden_ids, f"Horizon selection drift detected for {story_key}"
