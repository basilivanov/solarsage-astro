"""Tests for sidecar /v1/activation-layer endpoint."""

import pytest
from fastapi.testclient import TestClient

from solarsage.app import app

client = TestClient(app)

MOSCOW_FIXTURE_REQUEST = {
    "birth": {
        "date": "1990-01-15",
        "time": "14:30",
        "lat": 55.7558,
        "lon": 37.6173,
        "tz": "Europe/Moscow",
    },
    "target": {
        "date": "2026-07-08",
        "time": "12:00",
        "tz": "Europe/Moscow",
    },
    "house_system": "PLACIDUS",
    "techniques": [],
}

BASIL_AUDIT_REQUEST = {
    "birth": {
        "date": "1980-10-30",
        "time": "19:50",
        "lat": 67.9394,
        "lon": 32.8144,
        "tz": "Europe/Moscow",
    },
    "target": {
        "date": "2026-07-08",
        "time": "12:00",
        "tz": "Europe/Moscow",
    },
    "house_system": "PLACIDUS",
    "techniques": [],
}


def test_activation_layer_endpoint_returns_200():
    """POST /v1/activation-layer returns 200 with real W3.1 transit activations."""
    response = client.post("/v1/activation-layer", json=MOSCOW_FIXTURE_REQUEST)
    assert response.status_code == 200
    data = response.json()

    assert "meta" in data
    assert data["meta"]["activation_layer_version"] == "al-1.0"
    assert data["meta"]["calculation_version"] == "1"
    assert data["meta"]["house_system"] in ("PLACIDUS", "WHOLE_SIGN")

    assert "activation_layer" in data
    layer = data["activation_layer"]
    assert layer["schema_version"] == "activation-layer.v1"
    assert layer["activation_layer_version"] == "al-1.0"
    assert layer["target_date"] == "2026-07-08"
    assert layer["target_time"] == "12:00"
    assert layer["target_tz"] == "Europe/Moscow"

    # W3.1: must have real activations (not empty)
    assert len(layer["activations"]) > 0, "Expected W3.1 real transit activations"

    # Indices must reference valid ids
    valid_ids = {a["id"] for a in layer["activations"]}
    for idx_name in ("by_planet", "by_house", "by_lot", "by_angle"):
        idx = layer.get(idx_name, {})
        for key, refs in idx.items():
            for ref_id in refs:
                assert ref_id in valid_ids, f"{idx_name}[{key}] refs '{ref_id}' not in activations"


def test_activation_layer_endpoint_techniques_default_all():
    """Empty techniques list defaults to all supported transit techniques."""
    response = client.post("/v1/activation-layer", json=MOSCOW_FIXTURE_REQUEST)
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    techniques_found = {a["technique"] for a in layer["activations"]}
    assert "transit_to_natal" in techniques_found
    assert "transit_planet_in_house" in techniques_found
    assert "annual_profection" in techniques_found
    assert "monthly_profection" in techniques_found
    assert "firdar_major" in techniques_found
    assert "firdar_minor" in techniques_found
    assert "solar_return" in techniques_found
    assert "lunar_return" in techniques_found


def test_activation_layer_endpoint_unsupported_technique_warning():
    """Unsupported W3+ techniques produce deterministic warnings, no fake data.
    solar_return/lunar_return are now supported in W3.4; solar_arc remains unsupported."""
    response = client.post(
        "/v1/activation-layer",
        json={**MOSCOW_FIXTURE_REQUEST, "techniques": ["solar_arc", "secondary_progression"]},
    )
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    warnings_text = " ".join(layer.get("warnings", []))
    assert "unsupported_technique_deferred:solar_arc" in warnings_text
    assert "unsupported_technique_deferred:secondary_progression" in warnings_text
    for a in layer["activations"]:
        assert a["technique"] not in ("solar_arc", "secondary_progression")


def test_activation_layer_endpoint_rejects_missing_fields():
    """Missing required fields return 422."""
    response = client.post("/v1/activation-layer", json={})
    assert response.status_code == 422


def test_activation_layer_endpoint_basil_moon_opposition_pluto():
    """Basil audit fixture: Transit Moon opposition natal Pluto with correct
    evidence, orb ~1.0454°, phase=separating, applying=false."""
    response = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    activations = layer["activations"]

    # Find the specific Moon-Pluto transit_to_natal activation
    t2n_moon_pluto = [
        a for a in activations
        if a.get("source_planet") == "Moon"
        and a.get("technique") == "transit_to_natal"
        and a.get("target_planet") == "PLUTO"
        and a.get("aspect") == "opposition"
    ]
    assert len(t2n_moon_pluto) >= 1, "Expected Transit Moon opposition natal Pluto"
    act = t2n_moon_pluto[0]

    # Evidence is human-readable (Pluto, not PLUTO)
    assert act["id"] == "t2n__MOON__OPPOSITION__PLUTO"
    assert "Transit Moon opposition natal Pluto" in act.get("evidence", "")
    assert "PLUTO" not in act.get("evidence", ""), \
        f"Evidence must use display name, not uppercase: {act['evidence']}"

    # Orb within tolerance of 1.0454
    assert act["orb"] is not None
    assert abs(act["orb"] - 1.0454) <= 0.05, \
        f"Expected orb near 1.0454°, got {act['orb']}"

    # For 2026-07-08, Moon-Pluto is separating
    assert act["applying"] is False, f"Expected separating, got applying={act['applying']}"
    assert act["phase"] == "separating", f"Expected separating, got {act['phase']}"

    # Evidence includes frame references
    ev = act.get("evidence", "")
    assert "transit" in ev.lower()
    assert "natal" in ev.lower()


def test_activation_layer_endpoint_moscow_evidence():
    """Moscow fixture request returns transit_to_natal activations with correct
    evidence format including frame references (transit/natal)."""
    response = client.post(
        "/v1/activation-layer",
        json={**MOSCOW_FIXTURE_REQUEST, "techniques": ["transit_to_natal", "transit_planet_in_house"]},
    )
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    activations = layer["activations"]

    t2n = [a for a in activations if a["technique"] == "transit_to_natal"]
    assert len(t2n) >= 5, "Expected substantial transit_to_natal activations"
    for a in t2n:
        evidence = a.get("evidence", "").lower()
        assert "transit" in evidence, f"Evidence missing 'transit' frame: {evidence}"
        assert "natal" in evidence, f"Evidence missing 'natal' frame: {evidence}"

    # At least one Moon transit-to-natal aspect exists
    moon_aspects = [a for a in t2n if a.get("source_planet") == "Moon"]
    assert len(moon_aspects) >= 1, "Expected at least one Moon transit-to-natal aspect"
    ma = moon_aspects[0]
    assert ma.get("orb") is not None
    assert ma.get("strength") > 0.0
    assert ma.get("target_planet") is not None

    tih = [a for a in activations if a["technique"] == "transit_planet_in_house"]
    assert len(tih) >= 1, "Expected at least one transit_planet_in_house activation"


# ── Current location validation ──────────────────────────────────────────────


def test_current_location_valid_returns_200():
    """Valid current_location with lat/lon/tz returns 200."""
    response = client.post(
        "/v1/activation-layer",
        json={
            **MOSCOW_FIXTURE_REQUEST,
            "techniques": ["solar_return"],
            "current_location": {"lat": 55.0, "lon": 37.0, "tz": "Europe/Moscow"},
        },
    )
    assert response.status_code == 200


def test_current_location_missing_lat_returns_422():
    """Missing current_location.lat returns 422."""
    response = client.post(
        "/v1/activation-layer",
        json={
            **MOSCOW_FIXTURE_REQUEST,
            "techniques": ["solar_return"],
            "current_location": {"lon": 37.0, "tz": "Europe/Moscow"},
        },
    )
    assert response.status_code == 422


def test_current_location_missing_lon_returns_422():
    """Missing current_location.lon returns 422."""
    response = client.post(
        "/v1/activation-layer",
        json={
            **MOSCOW_FIXTURE_REQUEST,
            "techniques": ["solar_return"],
            "current_location": {"lat": 55.0, "tz": "Europe/Moscow"},
        },
    )
    assert response.status_code == 422


def test_current_location_empty_dict_returns_422():
    """Empty current_location dict returns 422."""
    response = client.post(
        "/v1/activation-layer",
        json={
            **MOSCOW_FIXTURE_REQUEST,
            "techniques": ["solar_return"],
            "current_location": {},
        },
    )
    assert response.status_code == 422
