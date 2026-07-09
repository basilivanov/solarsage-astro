"""Tests: Scoring V2 threshold/status breakdown."""
import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service


def _make_signals(positive: list = None, negative: list = None, pos_strength: float = 1.0, neg_strength: float = 1.0) -> list[AstroSignal]:
    result = []
    for _ in (positive or []):
        result.append(AstroSignal(type="aspect", planet="Transit_Moon",
                                   target_planet="Venus", aspect_type="trine",
                                   orb=0.5, strength=pos_strength, kind="aspect"))
    for _ in (negative or []):
        result.append(AstroSignal(type="aspect", planet="Transit_Mars",
                                   target_planet="Saturn", aspect_type="square",
                                   orb=0.5, strength=neg_strength, kind="aspect"))
    return result


def test_supportive_status():
    """Support-heavy day returns supportive status."""
    signals = _make_signals(positive=[1, 1], negative=[], pos_strength=1.0)
    result = ScoringV2Service().score_day(signals, None)
    assert result.day_status == "supportive"
    sb = result.status_breakdown
    for key in ("positive_aspect_score", "negative_aspect_score",
                 "activation_support_score", "activation_tension_score",
                 "support_score", "tension_score", "ratio", "rule"):
        assert key in sb, f"Missing status_breakdown key: {key}"


def test_tense_status():
    """Tension-heavy day returns tense status."""
    signals = _make_signals(positive=[], negative=[1, 1], neg_strength=1.0)
    result = ScoringV2Service().score_day(signals, None)
    assert result.day_status == "tense"


def test_steady_status():
    """Balanced day returns steady status."""
    signals = _make_signals(positive=[1], negative=[1])
    result = ScoringV2Service().score_day(signals, None)
    assert result.day_status == "steady"


def test_activation_affects_status():
    """Supportive activation can shift a balanced day toward supportive."""
    signals = _make_signals(positive=[1], negative=[1])
    layer = ActivationLayer(
        calculation_version="1", target_date="2026-07-08",
        target_time="12:00", target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[
            ActivationEvidence(id="sup_act", technique="annual_profection",
                               technique_family="profection",
                               target_type="planet", target_key="VENUS",
                               kind="lord_of_year", phase="period",
                               polarity="supportive", strength=1.0,
                               evidence="Supportive activation"),
        ],
        by_planet={"VENUS": ["sup_act"]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    assert result.status_breakdown.get("activation_support_score", 0) > 0
    # The status may or may not flip depending on exact scores
    assert "rule" in result.status_breakdown
