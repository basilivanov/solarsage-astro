"""Tests: Scoring V2 threshold/status breakdown + V1 base score parity."""
import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service
from app.services.scoring_service import ScoringService


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
    assert "rule" in result.status_breakdown


def test_weak_aspects_below_threshold_ignored():
    """Weak positive aspects below V1 threshold produce zero aspect score."""
    signals = [
        AstroSignal(type="aspect", planet=f"Transit_Moon_{i}",
                     target_planet="Mars", aspect_type="trine",
                     orb=4.0, strength=0.2, kind="aspect")
        for i in range(7)
    ]
    v1_status = ScoringService().score_day(signals)["day_status"]
    r = ScoringV2Service().score_day(signals, None)
    assert r.status_breakdown["positive_aspect_score"] == 0.0, \
        f"Expected 0 positive_aspect_score, got {r.status_breakdown['positive_aspect_score']}"
    assert r.status_breakdown["negative_aspect_score"] == 0.0, \
        f"Expected 0 negative_aspect_score"
    assert r.day_status == "steady"
    assert v1_status == "steady", f"V1 status should also be steady, got {v1_status}"


def test_v2_base_score_matches_v1():
    """V2 base score equals V1 pre-convergence/pre-cap sphere score."""
    signals = [
        AstroSignal(type="aspect", planet="Transit_Mercury",
                     target_planet="Venus", aspect_type="square",
                     orb=1.0, strength=1.0, kind="aspect"),
    ]
    v1_helper = ScoringService()._calculate_sphere_scores(signals)
    v2_result = ScoringV2Service().score_day(signals, None)
    for skey in v1_helper:
        v1_val = round(float(v1_helper[skey]), 4)
        v2_val = v2_result.sphere_scores.get(skey)
        if v2_val is not None:
            expected = v2_val.base_score
            assert abs(v1_val - expected) < 0.001, \
                f"{skey}: V1={v1_val} V2_base={expected}"
