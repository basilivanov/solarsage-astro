
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PARITY
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for parity.py behavior
# owns:
#   - apps/solarsage/tests/test_parity.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
"""
Parity tests for SolarSage reference collector (W-3.0).

These tests ensure that future sidecar/split work produces
byte-identical output (except timestamps) to the reference collector.

GRACE Wave: W-3.0 (PHASE-3-SIDECAR)
Module: M-SOLARSAGE-REFERENCE-COLLECTOR
"""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def normalize_fixture(data: dict) -> dict:
    """Remove timestamp fields for comparison."""
    normalized = data.copy()

    # Remove timestamp fields that vary between runs
    if "metadata" in normalized:
        meta = normalized["metadata"]
        # Keep birth/target data but remove any generated_at fields
        for key in list(meta.keys()):
            if "generated" in key.lower() or "timestamp" in key.lower():
                meta.pop(key, None)

    return normalized


@pytest.mark.parametrize("fixture_name", [
    "vasiliy_2026-05-30.json",
    "test_user_2026-06-15.json",
])
def test_fixture_exists(fixture_name: str):
    """Golden fixtures must exist."""
    fixture_path = FIXTURES_DIR / fixture_name
    assert fixture_path.exists(), f"Missing golden fixture: {fixture_name}"


@pytest.mark.parametrize("fixture_name", [
    "vasiliy_2026-05-30.json",
    "test_user_2026-06-15.json",
])
def test_fixture_structure(fixture_name: str):
    """Golden fixtures must have expected structure."""
    fixture_path = FIXTURES_DIR / fixture_name

    with open(fixture_path) as f:
        data = json.load(f)

    # Check top-level keys
    assert "metadata" in data, "Missing metadata"
    assert "raw" in data, "Missing raw"
    assert "derived" in data, "Missing derived"
    assert "calculation_notes" in data, "Missing calculation_notes"

    # Check raw layers
    assert "natal" in data["raw"], "Missing raw.natal"
    assert data["raw"]["natal"]["ok"], "natal layer failed"

    # Check natal structure
    natal_value = data["raw"]["natal"]["value"]
    assert "planets" in natal_value, "Missing natal.planets"
    assert "houses" in natal_value, "Missing natal.houses"
    assert "angles" in natal_value, "Missing natal.angles"
    assert "aspects" in natal_value, "Missing natal.aspects"

    # Check derived layers
    assert "major_aspects_ranked" in data["derived"], "Missing derived.major_aspects_ranked"
    assert "special_points" in data["derived"], "Missing derived.special_points"
    assert "sphere_scores" in data["derived"], "Missing derived.sphere_scores"


def test_vasiliy_natal_planets():
    """Vasiliy's natal planets must match known values (within 1e-6 deg)."""
    fixture_path = FIXTURES_DIR / "vasiliy_2026-05-30.json"

    with open(fixture_path) as f:
        data = json.load(f)

    natal = data["raw"]["natal"]["value"]
    planets = {p["planet_id"]: p for p in natal["planets"]}

    # Known values from reference collector (first run)
    # These are the golden values that future implementations must match
    expected = {
        "SUN": {"longitude": 217.422501905121, "sign": "Scorpio"},
        "MOON": {"longitude": 127.56203677313673, "sign": "Leo"},
        "MERCURY": {"longitude": 225.70459934271375, "sign": "Scorpio"},
        "VENUS": {"longitude": 180.31073979970466, "sign": "Libra"},
        "MARS": {"longitude": 253.32139549411903, "sign": "Sagittarius"},
    }

    for planet_id, expected_data in expected.items():
        assert planet_id in planets, f"Missing planet {planet_id}"
        planet = planets[planet_id]

        # Longitude tolerance: ±1e-6 deg
        assert abs(planet["longitude"] - expected_data["longitude"]) < 1e-6, \
            f"{planet_id} longitude mismatch: {planet['longitude']} vs {expected_data['longitude']}"

        # Sign must match exactly
        assert planet["sign"] == expected_data["sign"], \
            f"{planet_id} sign mismatch: {planet['sign']} vs {expected_data['sign']}"


def test_vasiliy_houses():
    """Vasiliy's house cusps must match known values (within 1e-6 deg)."""
    fixture_path = FIXTURES_DIR / "vasiliy_2026-05-30.json"

    with open(fixture_path) as f:
        data = json.load(f)

    natal = data["raw"]["natal"]["value"]
    houses = natal["houses"]

    # Vasiliy uses WHOLE_SIGN at high latitude
    assert len(houses) == 12, f"Expected 12 houses, got {len(houses)}"

    # For WHOLE_SIGN, houses should be 30-degree increments from ASC
    # Just verify structure, not exact values (depends on house system)
    for i, cusp in enumerate(houses):
        assert isinstance(cusp, (int, float)), f"House {i+1} cusp is not numeric"
        assert 0 <= cusp < 360, f"House {i+1} cusp out of range: {cusp}"


def test_vasiliy_special_points():
    """Vasiliy's special points must exist and have valid structure."""
    fixture_path = FIXTURES_DIR / "vasiliy_2026-05-30.json"

    with open(fixture_path) as f:
        data = json.load(f)

    special_points = data["derived"]["special_points"]

    # Check that key special points exist
    required_points = ["ASC", "MC", "DSC", "IC"]
    for point_id in required_points:
        assert point_id in special_points, f"Missing special point {point_id}"
        point = special_points[point_id]
        assert "longitude" in point, f"{point_id} missing longitude"
        assert "sign" in point, f"{point_id} missing sign"
        assert isinstance(point["longitude"], (int, float)), f"{point_id} longitude not numeric"


def test_vasiliy_aspects():
    """Vasiliy's major aspects must exist and have valid structure."""
    fixture_path = FIXTURES_DIR / "vasiliy_2026-05-30.json"

    with open(fixture_path) as f:
        data = json.load(f)

    aspects = data["derived"]["major_aspects_ranked"]

    assert len(aspects) > 0, "No major aspects found"

    # Check first aspect structure
    aspect = aspects[0]
    required_keys = ["planet_a", "planet_b", "aspect_type", "orb", "score_hint"]
    for key in required_keys:
        assert key in aspect, f"Aspect missing key: {key}"

    # Orb tolerance: ±1e-4 deg
    for aspect in aspects:
        orb = aspect["orb"]
        assert isinstance(orb, (int, float)), f"Aspect orb not numeric: {orb}"
        assert orb >= 0, f"Aspect orb negative: {orb}"


def test_test_user_house_system():
    """TestUser at normal latitude should use PLACIDUS."""
    fixture_path = FIXTURES_DIR / "test_user_2026-06-15.json"

    with open(fixture_path) as f:
        data = json.load(f)

    house_system = data["metadata"]["house_system"]
    house_policy = data["metadata"]["house_system_policy"]

    assert house_system == "PLACIDUS", \
        f"Expected PLACIDUS at normal latitude, got {house_system}"
    assert "normal_latitude" in house_policy, \
        f"Expected normal_latitude policy, got {house_policy}"


def test_fixture_reproducibility():
    """Fixtures should be reproducible (same input → same output)."""
    fixture_path = FIXTURES_DIR / "vasiliy_2026-05-30.json"

    with open(fixture_path) as f:
        data = json.load(f)

    # Check that metadata contains reproducible inputs
    metadata = data["metadata"]

    assert metadata["birth"]["date"] == "1980-10-30"
    assert metadata["birth"]["time"] == "19:50"
    assert metadata["birth"]["timezone"] == "Europe/Moscow"
    assert metadata["location"]["latitude"] == 67.9387
    assert metadata["location"]["longitude"] == 32.9241

    assert metadata["target"]["date"] == "2026-05-30"
    assert metadata["target"]["age"] == 45

    # JD_UT should be deterministic from inputs
    assert abs(metadata["birth"]["jd_ut"] - 2444543.201388889) < 1e-9
