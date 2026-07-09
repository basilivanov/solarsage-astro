"""Tests: Scoring V2 family deduplication."""
import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service


def test_annual_plus_monthly_profection_same_family():
    """Annual + monthly profection both on Mercury count as 1 family,
    convergence bonus = 0."""
    signals = [
        AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                     aspect_type="trine", orb=0.5, strength=0.5, kind="aspect"),
    ]
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08", target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
        activations=[
            ActivationEvidence(id="annual", technique="annual_profection",
                               technique_family="profection",
                               target_type="planet", target_key="MERCURY",
                               kind="lord_of_year", phase="period",
                               polarity="neutral", strength=0.75,
                               evidence="Annual"),
            ActivationEvidence(id="monthly", technique="monthly_profection",
                               technique_family="profection",
                               target_type="planet", target_key="MERCURY",
                               kind="lord_of_month", phase="period",
                               polarity="neutral", strength=0.45,
                               evidence="Monthly"),
        ],
        by_planet={"MERCURY": ["annual", "monthly"]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    sphere_key = "thinking_speech_learning"
    ss = result.sphere_scores[sphere_key]
    assert ss.convergence_bonus == 0, f"Expected 0 convergence bonus, got {ss.convergence_bonus}"
    # Verify family dedup
    dbg = result.debug.get("convergence_by_sphere", {})
    if sphere_key in dbg:
        assert dbg[sphere_key]["family_count"] == 1


def test_different_families_convergence():
    """Profection + firdar + transit on Mercury: family count=3, bonus=0.65."""
    signals = [
        AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                     aspect_type="trine", orb=0.5, strength=0.5, kind="aspect"),
    ]
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08", target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
        activations=[
            ActivationEvidence(id="p", technique="annual_profection",
                               technique_family="profection",
                               target_type="planet", target_key="MERCURY",
                               kind="lord_of_year", phase="period",
                               polarity="neutral", strength=0.75,
                               evidence="P"),
            ActivationEvidence(id="f", technique="firdar_major",
                               technique_family="firdar",
                               target_type="planet", target_key="MERCURY",
                               kind="major_period_lord", phase="period",
                               polarity="neutral", strength=0.65,
                               evidence="F"),
            ActivationEvidence(id="t", technique="transit_to_natal",
                               technique_family="transit",
                               target_type="planet", target_key="MERCURY",
                               kind="trine", aspect="trine", phase="separating",
                               polarity="supportive", strength=0.6,
                               evidence="T"),
        ],
        by_planet={"MERCURY": ["p", "f", "t"]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    sphere_key = "thinking_speech_learning"
    ss = result.sphere_scores[sphere_key]
    assert ss.convergence_bonus > 0, "Expected convergence bonus > 0"
    dbg = result.debug.get("convergence_by_sphere", {})
    assert sphere_key in dbg
    assert dbg[sphere_key]["family_count"] == 3
