# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_SHADOW
# ROLE: Unit and dual-run tests for W2-VALENCE shadow wiring, observability events, and metrics.
# DEPENDENCIES: pytest, app.services.day_scoring_runtime_service, app.core.metrics
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-SHADOW
# purpose: Verify shadow dual-run mode, fail-closed error handling, observability event emission, and metrics incrementing.
# owns:
#   - apps/api/tests/test_day_valence_shadow.py
# inputs: synthetic signals and activations
# outputs: assertions
# dependencies: app.services.day_scoring_runtime_service, app.core.config, app.core.metrics
# side_effects: test-local setting overrides
# failure_policy: fails test on dual-run regression or metric failure
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-SHADOW

# START_MODULE_MAP: M-TEST-DAY-VALENCE-SHADOW
# public_entrypoints:
#   - test_shadow_dual_run_emits_events_and_preserves_selected_result
#   - test_shadow_engine_failure_fails_closed
#   - test_valence_enabled_emits_selected_event
#   - test_valence_metrics_increment
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_shadow.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-SHADOW

from unittest.mock import MagicMock, patch
import pytest
from app.core.metrics import get_metrics_snapshot
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.normalization import AstroSignal
from app.services.day_scoring_runtime_service import DayScoringRuntimeService


from app.core.versions import LEGACY_SCORING_VERSION, SCORING_V2_VERSION

@pytest.fixture
def sample_inputs():
    sigs = [
        AstroSignal(type="aspect", planet="Transit_Venus", target_planet="Uranus", aspect_type="sextile", strength=0.80),
        AstroSignal(type="planet_in_house", planet="Transit_Mars", house=10, strength=0.60),
    ]
    act = {
        "id": "act_1",
        "activation_id": "act_1",
        "kind": "aspect",
        "evidence": "Transit Venus sextile natal Uranus",
        "active": True,
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "polarity": "supportive",
        "strength": 0.90,
        "planet": "Venus",
        "target_type": "planet",
        "target_key": "URANUS",
        "aspect_type": "sextile",
    }
    layer = MagicMock()
    layer.activations = [act]
    return sigs, layer


def test_shadow_dual_run_emits_events_and_preserves_selected_result(sample_inputs):
    """When DUAL_RUN=true, valence computes in shadow, emits diff events, and selected_result remains legacy."""
    sigs, layer = sample_inputs
    service = DayScoringRuntimeService()

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings, \
         patch("app.services.day_scoring_runtime_service.log_event") as mock_log:

        mock_settings.solarsage_v2_enabled = False
        mock_settings.solarsage_v2_dual_run = False
        mock_settings.today_valence_v1_enabled = False
        mock_settings.today_valence_v1_dual_run = True

        res = service.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")

        # Public result is legacy V1 result
        assert res.selected_scoring_version == LEGACY_SCORING_VERSION
        assert "day_status" in res.selected_result

        # Log event calls: scoring.factor_deduplicated and scoring.valence_diff emitted
        event_names = [call.args[0] for call in mock_log.call_args_list]
        assert "scoring.factor_deduplicated" in event_names
        assert "scoring.valence_diff" in event_names
        assert "scoring.valence_selected" not in event_names


def test_shadow_engine_failure_fails_closed(sample_inputs):
    """Exception in shadow valence path emits scoring.valence_failed and legacy payload proceeds."""
    sigs, layer = sample_inputs
    service = DayScoringRuntimeService()

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings, \
         patch("app.services.day_scoring_runtime_service.DayValenceService") as mock_valence_cls, \
         patch("app.services.day_scoring_runtime_service.log_event") as mock_log:

        mock_settings.solarsage_v2_enabled = False
        mock_settings.solarsage_v2_dual_run = False
        mock_settings.today_valence_v1_enabled = False
        mock_settings.today_valence_v1_dual_run = True

        # Force exception inside DayValenceService.compute
        mock_instance = MagicMock()
        mock_instance.compute.side_effect = RuntimeError("Simulated valence engine failure")
        mock_valence_cls.return_value = mock_instance

        # Service.compute does NOT raise when enabled=false
        res = service.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")

        assert res.selected_scoring_version == LEGACY_SCORING_VERSION
        event_names = [call.args[0] for call in mock_log.call_args_list]
        assert "scoring.valence_failed" in event_names


def test_valence_enabled_emits_selected_event(sample_inputs):
    """When TODAY_VALENCE_V1_ENABLED=true, logs scoring.valence_selected."""
    sigs, layer = sample_inputs
    service = DayScoringRuntimeService()

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings, \
         patch("app.services.day_scoring_runtime_service.log_event") as mock_log:

        mock_settings.solarsage_v2_enabled = False
        mock_settings.solarsage_v2_dual_run = False
        mock_settings.today_valence_v1_enabled = True
        mock_settings.today_valence_v1_dual_run = False

        res = service.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")

        event_names = [call.args[0] for call in mock_log.call_args_list]
        assert "scoring.valence_selected" in event_names


def test_valence_metrics_increment(sample_inputs):
    """Valence calculation increments in-memory counters."""
    sigs, layer = sample_inputs
    service = DayScoringRuntimeService()

    with patch("app.services.day_scoring_runtime_service.settings") as mock_settings:
        mock_settings.solarsage_v2_enabled = False
        mock_settings.solarsage_v2_dual_run = False
        mock_settings.today_valence_v1_enabled = False
        mock_settings.today_valence_v1_dual_run = True

        service.compute(day_signals=sigs, activation_layer=layer, target_date="2026-07-27")

        metrics = get_metrics_snapshot()
        assert len(metrics["today_day_status_total"]) > 0
        assert len(metrics["today_sphere_verdict_total"]) > 0
        assert "signal_activation" in metrics["today_valence_duplicate_factors"]
        assert "transit" in metrics["today_valence_effective_factors"]
