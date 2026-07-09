"""Tests for sidecar /v1/activation-layer endpoint."""

import pytest
from fastapi.testclient import TestClient

from solarsage.app import app

client = TestClient(app)


def test_activation_layer_endpoint_returns_200():
    """POST /v1/activation-layer returns 200 with real W3.1 transit activations."""
    response = client.post(
        "/v1/activation-layer",
        json={
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
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Check meta
    assert "meta" in data
    assert data["meta"]["activation_layer_version"] == "al-1.0"
    assert data["meta"]["calculation_version"] == "1"
    assert data["meta"]["house_system"] in ("PLACIDUS", "WHOLE_SIGN")

    # Check activation layer
    assert "activation_layer" in data
    layer = data["activation_layer"]
    assert layer["schema_version"] == "activation-layer.v1"
    assert layer["activation_layer_version"] == "al-1.0"
    assert layer["target_date"] == "2026-07-08"
    assert layer["target_time"] == "12:00"
    assert layer["target_tz"] == "Europe/Moscow"

    # W3.1: must have real activations (not empty)
    assert len(layer["activations"]) > 0, "Expected W3.1 real transit activations"

    # Must include transit_to_natal evidence
    ev_evidence = " ".join(a.get("evidence", "") for a in layer["activations"])
    assert "transit" in ev_evidence.lower()

    # Indices must reference valid ids
    valid_ids = {a["id"] for a in layer["activations"]}
    for idx_name in ("by_planet", "by_house", "by_lot", "by_angle"):
        idx = layer.get(idx_name, {})
        for key, refs in idx.items():
            for ref_id in refs:
                assert ref_id in valid_ids, f"{idx_name}[{key}] refs '{ref_id}' not in activations"


def test_activation_layer_endpoint_techniques_default_all():
    """Empty techniques list defaults to all supported transit techniques."""
    response = client.post(
        "/v1/activation-layer",
        json={
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
        },
    )
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    techniques_found = {a["technique"] for a in layer["activations"]}
    assert "transit_to_natal" in techniques_found
    assert "transit_planet_in_house" in techniques_found


def test_activation_layer_endpoint_unsupported_technique_warning():
    """Unsupported W3+ techniques produce deterministic warnings, no fake data."""
    response = client.post(
        "/v1/activation-layer",
        json={
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
            "techniques": ["annual_profection", "firdar_major"],
        },
    )
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    # Must have warnings for unsupported
    warnings_text = " ".join(layer.get("warnings", []))
    assert "unsupported_technique_deferred:annual_profection" in warnings_text
    assert "unsupported_technique_deferred:firdar_major" in warnings_text
    # No activations for unsupported techniques
    for a in layer["activations"]:
        assert a["technique"] not in ("annual_profection", "firdar_major")


def test_activation_layer_endpoint_rejects_missing_fields():
    """Missing required fields return 422."""
    response = client.post(
        "/v1/activation-layer",
        json={},
    )
    assert response.status_code == 422


def test_activation_layer_endpoint_basil_evidence():
    """Basil-like request returns transit_to_natal activations with correct
    evidence format including frame references (transit/natal)."""
    response = client.post(
        "/v1/activation-layer",
        json={
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
            "techniques": ["transit_to_natal", "transit_planet_in_house"],
        },
    )
    assert response.status_code == 200
    layer = response.json()["activation_layer"]
    activations = layer["activations"]

    # All transit_to_natal activations must have frame-aware evidence
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

    # transit_planet_in_house activations exist
    tih = [a for a in activations if a["technique"] == "transit_planet_in_house"]
    assert len(tih) >= 1, "Expected at least one transit_planet_in_house activation"
