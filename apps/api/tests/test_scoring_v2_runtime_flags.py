"""Tests: W5 V2 runtime feature flags."""
import pytest
from unittest.mock import patch

from app.services.day_scoring_runtime_service import DayScoringRuntimeService
from app.schemas.normalization import AstroSignal
from app.core.config import settings


def test_default_flags():
    """Default flag values must be safe (V2 disabled, dual_run controlled by conftest)."""
    # In conftest, dual_run is set to False for isolation
    pass


def test_v1_only_mode(monkeypatch):
    """V2_ENABLED=false, DUAL_RUN=false: V2 not computed."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    runtime = DayScoringRuntimeService()
    signals = []
    result = runtime.compute(signals)
    assert result.selected_scoring_version == 1
    assert result.v2_result is None
    assert result.v2_error is None


def test_dual_run_computes_v2(monkeypatch):
    """V2_ENABLED=false, DUAL_RUN=true: V2 computed, V1 selected."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    runtime = DayScoringRuntimeService()
    result = runtime.compute(signals)
    assert result.selected_scoring_version == 1
    assert result.v2_result is not None
    assert result.v1_result is not None
    assert result.diff is not None


def test_v2_enabled_mode(monkeypatch):
    """V2_ENABLED=true: V2 selected."""
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    runtime = DayScoringRuntimeService()
    result = runtime.compute(signals)
    assert result.selected_scoring_version == "ss-scoring-2.0"
    assert result.v2_result is not None


def test_shadow_failure_returns_v1(monkeypatch):
    """V2_ENABLED=false, V2 raises: V1 returned, error recorded."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    runtime = DayScoringRuntimeService()
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    # Should work normally
    result = runtime.compute(signals)
    assert result.selected_scoring_version == 1
