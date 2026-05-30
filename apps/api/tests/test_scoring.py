# AI_HEADER
# module: M-TEST-SCORING
# wave: W-4.2
# purpose: Scoring service tests

import pytest

from app.services.scoring_service import ScoringService
from app.schemas.normalization import AstroSignal


@pytest.fixture
def supportive_signals():
    """Signals with strong positive aspects."""
    return [
        AstroSignal(
            type="aspect",
            planet="Sun",
            target_planet="Jupiter",
            aspect_type="trine",
            orb=1.0,
            strength=0.9,
        ),
        AstroSignal(
            type="aspect",
            planet="Venus",
            target_planet="Mars",
            aspect_type="sextile",
            orb=2.0,
            strength=0.8,
        ),
        AstroSignal(
            type="planet_in_house",
            planet="Sun",
            house=10,
            strength=1.0,
        ),
    ]


@pytest.fixture
def tense_signals():
    """Signals with strong negative aspects."""
    return [
        AstroSignal(
            type="aspect",
            planet="Mars",
            target_planet="Saturn",
            aspect_type="square",
            orb=1.5,
            strength=0.85,
        ),
        AstroSignal(
            type="aspect",
            planet="Sun",
            target_planet="Pluto",
            aspect_type="opposition",
            orb=2.0,
            strength=0.8,
        ),
    ]


@pytest.fixture
def steady_signals():
    """Signals with mixed or weak aspects."""
    return [
        AstroSignal(
            type="aspect",
            planet="Moon",
            target_planet="Venus",
            aspect_type="conjunction",
            orb=3.0,
            strength=0.6,
        ),
        AstroSignal(
            type="planet_in_sign",
            planet="Sun",
            sign="Gemini",
            strength=1.0,
        ),
    ]


def test_day_status_supportive(supportive_signals):
    """Supportive day has strong positive aspects."""
    service = ScoringService()
    result = service.score(supportive_signals)

    assert result["day_status"] == "supportive"


def test_day_status_tense(tense_signals):
    """Tense day has strong negative aspects."""
    service = ScoringService()
    result = service.score(tense_signals)

    assert result["day_status"] == "tense"


def test_day_status_steady(steady_signals):
    """Steady day has mixed or weak aspects."""
    service = ScoringService()
    result = service.score(steady_signals)

    assert result["day_status"] == "steady"


def test_sphere_scores(supportive_signals):
    """Sphere scores are calculated."""
    service = ScoringService()
    result = service.score(supportive_signals)

    assert "sphere_scores" in result
    assert "career" in result["sphere_scores"]
    assert "relationships" in result["sphere_scores"]


def test_top_signals(supportive_signals):
    """Top signals are returned."""
    service = ScoringService()
    result = service.score(supportive_signals)

    assert "top_signals" in result
    assert len(result["top_signals"]) <= 5

    # Top signals should be sorted by strength
    strengths = [s.strength for s in result["top_signals"]]
    assert strengths == sorted(strengths, reverse=True)
