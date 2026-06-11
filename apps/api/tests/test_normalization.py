
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NORMALIZATION
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for normalization.py behavior
# owns:
#   - apps/api/tests/test_normalization.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-NORMALIZATION
# wave: W-4.1
# purpose: Normalization service tests

import pytest

from app.services.normalization_service import NormalizationService


@pytest.fixture
def sample_natal():
    return {
        "planets": [
            {"name": "Sun", "longitude": 69.5, "sign": "Gemini"},
            {"name": "Moon", "longitude": 120.0, "sign": "Leo"},
        ],
        "houses": [
            {"number": 1, "cusp": 0.0},
            {"number": 2, "cusp": 30.0},
            {"number": 3, "cusp": 60.0},
            {"number": 4, "cusp": 90.0},
            {"number": 5, "cusp": 120.0},
            {"number": 6, "cusp": 150.0},
            {"number": 7, "cusp": 180.0},
            {"number": 8, "cusp": 210.0},
            {"number": 9, "cusp": 240.0},
            {"number": 10, "cusp": 270.0},
            {"number": 11, "cusp": 300.0},
            {"number": 12, "cusp": 330.0},
        ],
    }


@pytest.fixture
def sample_transits():
    return {
        "planets": [
            {"name": "Sun", "longitude": 70.0, "sign": "Gemini"},
        ],
    }


def test_planets_in_houses(sample_natal):
    """Normalization generates planet_in_house signals."""
    service = NormalizationService()
    signals = service._planets_in_houses(sample_natal)

    assert len(signals) == 2
    assert signals[0].type == "planet_in_house"
    assert signals[0].planet == "Sun"
    assert signals[0].house == 3  # 69.5 deg is in house 3 (60-90)


def test_planets_in_signs(sample_natal):
    """Normalization generates planet_in_sign signals."""
    service = NormalizationService()
    signals = service._planets_in_signs(sample_natal)

    assert len(signals) == 2
    assert signals[0].type == "planet_in_sign"
    assert signals[0].planet == "Sun"
    assert signals[0].sign == "Gemini"


def test_natal_aspects(sample_natal):
    """Normalization generates natal aspect signals."""
    service = NormalizationService()
    signals = service._natal_aspects(sample_natal)

    # Sun (69.5) and Moon (120.0) are ~50.5 deg apart
    # No major aspect within orb
    assert len(signals) == 0  # No aspects within orb


def test_transit_aspects(sample_natal, sample_transits):
    """Normalization generates transit aspect signals."""
    service = NormalizationService()
    signals = service._transit_aspects(sample_transits, sample_natal)

    # Transit Sun (70.0) and Natal Sun (69.5) are ~0.5 deg apart
    # This is a conjunction (orb 0.5 < 8.0)
    assert len(signals) >= 1
    conjunction = next((s for s in signals if s.aspect_type == "conjunction"), None)
    assert conjunction is not None
    assert conjunction.planet == "Transit_Sun"
    assert conjunction.target_planet == "Sun"
    assert conjunction.orb < 1.0
    assert conjunction.strength > 0.9  # Very tight orb


def test_normalize_full(sample_natal, sample_transits):
    """Full normalization pipeline."""
    service = NormalizationService()
    signals = service.normalize(sample_natal, sample_transits)

    # Should have: 2 planet_in_house + 2 planet_in_sign + 0 natal_aspects + 1+ transit_aspects
    assert len(signals) >= 5

    # Check types
    types = [s.type for s in signals]
    assert "planet_in_house" in types
    assert "planet_in_sign" in types
    assert "aspect" in types
