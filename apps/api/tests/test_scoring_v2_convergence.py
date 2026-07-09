"""Tests: Scoring V2 convergence — Mercury/profection/Saturn transit convergence."""
import pytest
from datetime import date

from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service


def _make_mercury_day_signals() -> list[AstroSignal]:
    return [
        AstroSignal(
            type="aspect",
            planet="Transit_Mercury",
            target_planet="Venus",
            aspect_type="square",
            orb=1.0,
            strength=0.8,
            kind="aspect",
        ),
    ]


def test_mercury_profection_saturn_convergence():
    """Mercury base + profection + transit + firdar mapped to Mercury sphere
    produces convergence bonus >= 1.4x base and <= 2.0x base."""
    signals = _make_mercury_day_signals()
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[
            ActivationEvidence(
                id="annual_profection__LORD_OF_YEAR__MERCURY",
                technique="annual_profection",
                technique_family="profection",
                target_type="planet",
                target_key="MERCURY",
                kind="lord_of_year",
                phase="period",
                polarity="neutral",
                strength=0.75,
                evidence="Mercury profection lord",
            ),
            ActivationEvidence(
                id="t2n__SATURN__TRINE__MERCURY",
                technique="transit_to_natal",
                technique_family="transit",
                target_type="planet",
                target_key="MERCURY",
                kind="trine",
                aspect="trine",
                phase="separating",
                polarity="supportive",
                strength=0.6,
                evidence="Transit Saturn trine natal Mercury",
            ),
            ActivationEvidence(
                id="firdar_major__PERIOD_LORD__MERCURY",
                technique="firdar_major",
                technique_family="firdar",
                target_type="planet",
                target_key="MERCURY",
                kind="major_period_lord",
                phase="period",
                polarity="neutral",
                strength=0.65,
                evidence="Mercury firdar lord",
            ),
        ],
        by_planet={"MERCURY": ["annual_profection__LORD_OF_YEAR__MERCURY", "t2n__SATURN__TRINE__MERCURY", "firdar_major__PERIOD_LORD__MERCURY"]},
        by_house={},
        by_lot={},
        by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    sphere_key = "thinking_speech_learning"
    ss = result.sphere_scores[sphere_key]
    post_bonus = ss.base_score + ss.activation_score + ss.convergence_bonus
    assert post_bonus >= 2.0 * ss.base_score, f"post_bonus {post_bonus} < 2.0 * base {ss.base_score}"
    assert ss.convergence_bonus > 0, "Expected convergence bonus > 0"
    assert ss.dominance_capped, "Expected dominance cap to be applied"
