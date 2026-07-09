"""Tests: Scoring V2 breakdown contract."""
import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service


def test_final_score_equals_raw_or_capped():
    """Every sphere final_score equals raw_score or capped raw_score."""
    signals = [AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=0.5, kind="aspect")]
    acts = [
        ActivationEvidence(id=f"a{i}", technique="annual_profection",
                           technique_family="profection",
                           target_type="planet", target_key="MERCURY",
                           kind="lord_of_year", phase="period",
                           polarity="neutral", strength=0.5,
                           evidence=f"A{i}")
        for i in range(6)
    ]
    layer = ActivationLayer(
        calculation_version="1", target_date="2026-07-08",
        target_time="12:00", target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=acts,
        by_planet={"MERCURY": [a.id for a in acts]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    for key, ss in result.sphere_scores.items():
        if ss.dominance_capped:
            assert ss.final_score < ss.raw_score, f"{key}: capped but final >= raw"
        else:
            assert ss.final_score == ss.raw_score, f"{key}: not capped but final != raw"


def test_contribution_sources_valid():
    """Contribution sources are only base_signal, activation, convergence, cap."""
    signals = [AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=0.5, kind="aspect")]
    acts = [
        ActivationEvidence(id="a1", technique="annual_profection",
                           technique_family="profection",
                           target_type="planet", target_key="MERCURY",
                           kind="lord_of_year", phase="period",
                           polarity="neutral", strength=0.75,
                           evidence="A1"),
        ActivationEvidence(id="a2", technique="transit_to_natal",
                           technique_family="transit",
                           target_type="planet", target_key="MERCURY",
                           kind="trine", aspect="trine", phase="separating",
                           polarity="supportive", strength=0.6,
                           evidence="A2"),
    ]
    layer = ActivationLayer(
        calculation_version="1", target_date="2026-07-08",
        target_time="12:00", target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=acts,
        by_planet={"MERCURY": ["a1", "a2"]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    valid_sources = {"base_signal", "activation", "convergence", "cap"}
    for key, ss in result.sphere_scores.items():
        for c in ss.contributions:
            assert c.source in valid_sources, f"{key}: invalid source {c.source}"
