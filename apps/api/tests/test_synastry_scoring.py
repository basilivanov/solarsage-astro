"""Unit tests for SynastryScoringEngine."""

from app.services.synastry_scoring import (
    RawAspectInput,
    SynastryScoringEngine,
)


def test_synastry_scoring_import():
    assert SynastryScoringEngine is not None


def test_determine_tone():
    assert SynastryScoringEngine.determine_tone("Sun", "Moon", "trine") == "supportive"
    assert SynastryScoringEngine.determine_tone("Venus", "Mars", "sextile") == "supportive"
    assert SynastryScoringEngine.determine_tone("Saturn", "Sun", "square") == "tense"
    assert SynastryScoringEngine.determine_tone("Pluto", "Moon", "opposition") == "tense"
    assert SynastryScoringEngine.determine_tone("Uranus", "Sun", "conjunction") == "mixed"


def test_calculate_score_exact_time():
    aspects = [
        RawAspectInput(owner_planet="Sun", partner_planet="Moon", aspect_type="trine", orb_degrees=1.2),
        RawAspectInput(owner_planet="Venus", partner_planet="Mars", aspect_type="sextile", orb_degrees=2.0),
        RawAspectInput(owner_planet="Mercury", partner_planet="Mercury", aspect_type="conjunction", orb_degrees=0.5),
        RawAspectInput(owner_planet="Saturn", partner_planet="Sun", aspect_type="square", orb_degrees=4.0),
    ]

    res = SynastryScoringEngine.calculate_score(aspects, partner_time_precision="exact")

    assert 0 <= res.score <= 100
    assert res.status in ("good", "mid", "bad")
    assert res.counters["good"] == 3
    assert res.counters["bad"] == 1
    assert res.precision_flags["houses_available"] is True
    assert res.precision_flags["report_precision"] == "exact"
    assert len(res.spheres) == 4


def test_calculate_score_approximate_time_invariants():
    aspects = [
        RawAspectInput(owner_planet="Sun", partner_planet="Sun", aspect_type="trine", orb_degrees=1.0),
        RawAspectInput(owner_planet="Sun", partner_planet="Moon", aspect_type="square", orb_degrees=2.0),
        RawAspectInput(owner_planet="Venus", partner_planet="Ascendant", aspect_type="trine", orb_degrees=1.5),
    ]

    res = SynastryScoringEngine.calculate_score(aspects, partner_time_precision="approximate")

    assert res.precision_flags["houses_available"] is False
    assert res.precision_flags["asc_available"] is False
    assert res.precision_flags["moon_precision"] == "approximate"
    assert res.precision_flags["report_precision"] == "approximate"

    # Partner Moon and Ascendant aspects must have weight = 0 and low confidence
    moon_aspect = next(a for a in res.aspects if a.partner_planet == "Moon")
    asc_aspect = next(a for a in res.aspects if a.partner_planet == "Ascendant")

    assert moon_aspect.weight == 0.0
    assert moon_aspect.confidence == "low"
    assert asc_aspect.weight == 0.0
    assert asc_aspect.confidence == "low"

    # Counter for good aspects should only count Sun-Sun (since Moon & ASC have weight 0)
    assert res.counters["good"] == 1
    assert res.counters["bad"] == 0
