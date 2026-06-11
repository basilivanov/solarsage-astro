
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SCORING
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_scoring.py
# owns:
#   - apps/api/tests/test_scoring.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-TEST-SCORING
# wave: W-4.2
# purpose: Scoring service tests

import pytest

from app.services.scoring_service import ScoringService
from app.schemas.normalization import AstroSignal


@pytest.fixture
def supportive_signals():
    """Signals with strong positive aspects (pass canon thresholds)."""
    return [
        AstroSignal(
            type="aspect", planet="Sun", target_planet="Jupiter",
            aspect_type="trine", orb=1.0, strength=0.95,
        ),
        AstroSignal(
            type="aspect", planet="Venus", target_planet="Mars",
            aspect_type="trine", orb=2.0, strength=0.85,
        ),
        AstroSignal(
            type="planet_in_house", planet="Sun", house=10, strength=1.0,
        ),
    ]


@pytest.fixture
def tense_signals():
    """Signals with strong negative aspects (pass canon thresholds)."""
    return [
        AstroSignal(
            type="aspect", planet="Mars", target_planet="Saturn",
            aspect_type="square", orb=1.5, strength=0.95,
        ),
        AstroSignal(
            type="aspect", planet="Sun", target_planet="Pluto",
            aspect_type="opposition", orb=2.0, strength=0.90,
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
    """Sphere scores are calculated from canon."""
    service = ScoringService()
    result = service.score(supportive_signals)

    assert "sphere_scores" in result
    # Canon keys — not hardcoded career/relationships
    assert "work_status_achievement" in result["sphere_scores"] or "thinking_speech_learning" in result["sphere_scores"]


def test_top_signals(supportive_signals):
    """Top signals are returned."""
    service = ScoringService()
    result = service.score(supportive_signals)

    assert "top_signals" in result
    assert len(result["top_signals"]) <= 5

    # Top signals should be sorted by strength
    strengths = [s.strength for s in result["top_signals"]]
    assert strengths == sorted(strengths, reverse=True)


def test_fast_planet_outranks_slow_at_equal_strength():
    """Moon (fast) should outrank Neptune (slow) at equal strength — velocity_factor."""
    service = ScoringService()
    signals = [
        AstroSignal(type="aspect", planet="Neptune", target_planet="Sun", aspect_type="trine", orb=1.0, strength=0.9),
        AstroSignal(type="aspect", planet="Moon", target_planet="Venus", aspect_type="sextile", orb=1.0, strength=0.9),
    ]
    top = service._get_top_signals(signals, limit=2)
    assert "Moon" in (top[0].planet or ""), "Fast Moon should outrank slow Neptune"


def test_guaranteed_moon_slot():
    """When top-5 has no Moon signal, best Moon signal replaces last element."""
    service = ScoringService()
    signals = [
        AstroSignal(type="aspect", planet="Jupiter", target_planet="Sun", aspect_type="trine", orb=1.0, strength=0.95),
        AstroSignal(type="aspect", planet="Saturn", target_planet="Venus", aspect_type="sextile", orb=2.0, strength=0.90),
        AstroSignal(type="planet_in_house", planet="Mars", house=10, strength=0.85),
        AstroSignal(type="aspect", planet="Neptune", target_planet="Moon", aspect_type="square", orb=3.0, strength=0.50),
        AstroSignal(type="aspect", planet="Pluto", target_planet="Mercury", aspect_type="opposition", orb=4.0, strength=0.40),
        AstroSignal(type="aspect", planet="Moon", target_planet="Mars", aspect_type="square", orb=2.0, strength=0.60),
    ]
    top = service._get_top_signals(signals, limit=5)
    has_moon = any(s.planet and "Moon" in s.planet for s in top)
    assert has_moon, "Top signals must contain at least one Moon signal"


def test_top_signals_velocity_sorted():
    """Daily salience = strength × velocity_factor. Moon (1.0) beats Neptune (0.45)."""
    service = ScoringService()
    signals = [
        AstroSignal(type="aspect", planet="Neptune", target_planet="Sun", aspect_type="trine", orb=1.0, strength=0.95),
        AstroSignal(type="aspect", planet="Moon", target_planet="Venus", aspect_type="sextile", orb=2.0, strength=0.80),
    ]
    top = service._get_top_signals(signals, limit=2)
    # Moon: 0.80 × 1.0 = 0.80, Neptune: 0.95 × 0.45 = 0.43
    assert top[0].planet == "Moon", f"Moon should rank first, got {top[0].planet}"


def test_transit_moon_uses_fast_velocity_factor():
    """Transit_Moon must be recognized as Moon → fast class → velocity_factor 1.0."""
    service = ScoringService()
    signals = [
        AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Sun", aspect_type="sextile", orb=1.0, strength=0.8),
        AstroSignal(type="aspect", planet="Transit_Neptune", target_planet="Venus", aspect_type="trine", orb=1.0, strength=0.9),
    ]
    top = service._get_top_signals(signals, limit=2)
    assert top[0].planet == "Transit_Moon", f"Transit_Moon (0.8×1.0=0.8) should outrank Transit_Neptune (0.9×0.45=0.41), got {top[0].planet}"


def test_transit_neptune_uses_slow_velocity_factor():
    """Transit_Neptune → slow class → velocity_factor 0.45."""
    service = ScoringService()
    signals = [
        AstroSignal(type="aspect", planet="Transit_Neptune", target_planet="Sun", aspect_type="trine", orb=1.0, strength=0.95),
        AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus", aspect_type="sextile", orb=2.0, strength=0.70),
    ]
    top = service._get_top_signals(signals, limit=2)
    # Mercury: 0.70×1.0=0.70, Neptune: 0.95×0.45=0.43
    assert top[0].planet == "Transit_Mercury", f"Fast Mercury should outrank slow Neptune, got {top[0].planet}"


def test_transit_prefix_is_stripped_for_velocity_lookup():
    """_base_planet_name drops Transit_ prefix."""
    from app.services.scoring_service import _base_planet_name
    assert _base_planet_name("Transit_Moon") == "MOON"
    assert _base_planet_name("Transit_Neptune") == "NEPTUNE"
    assert _base_planet_name("Moon") == "MOON"
    assert _base_planet_name("Sun") == "SUN"
    assert _base_planet_name(None) == ""
    assert _base_planet_name("") == ""
