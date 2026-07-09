"""Tests: W5 Calendar V2 dual-run integration."""
import pytest
from unittest.mock import patch

from app.core.config import settings
from app.services.day_scoring_runtime_service import DayScoringRuntimeService


def test_calendar_v2_dual_run_default(monkeypatch):
    """Default dual-run calendar status uses V1 via runtime service."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    from app.schemas.normalization import AstroSignal
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    runtime = DayScoringRuntimeService()
    result = runtime.compute(signals)
    assert result.selected_scoring_version == 1
    assert result.v2_result is not None


def test_calendar_v2_enabled_status(monkeypatch):
    """V2-enabled calendar uses V2 status through runtime service."""
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    from app.schemas.normalization import AstroSignal
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    runtime = DayScoringRuntimeService()
    result = runtime.compute(signals)
    assert result.selected_scoring_version == "ss-scoring-2.0"
