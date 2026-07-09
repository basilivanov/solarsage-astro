"""Tests for sidecar /v1/activation-layer endpoint."""

import pytest
from fastapi.testclient import TestClient

from solarsage.app import app

client = TestClient(app)


def test_activation_layer_endpoint_returns_200():
    """POST /v1/activation-layer returns 200 and valid response shape."""
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
    assert data["meta"]["house_system"] == "PLACIDUS"

    # Check activation layer
    assert "activation_layer" in data
    layer = data["activation_layer"]
    assert layer["schema_version"] == "activation-layer.v1"
    assert layer["activation_layer_version"] == "al-1.0"
    assert layer["target_date"] == "2026-07-08"
    assert layer["target_time"] == "12:00"
    assert layer["target_tz"] == "Europe/Moscow"
    assert layer["activations"] == []
    assert layer["by_planet"] == {}
    assert layer["by_house"] == {}
    assert layer["by_lot"] == {}
    assert layer["by_angle"] == {}
    # W2: contract-only warning
    assert "contract_only_no_techniques_built_yet" in str(layer["warnings"])


def test_activation_layer_endpoint_rejects_missing_fields():
    """Missing required fields return 422."""
    response = client.post(
        "/v1/activation-layer",
        json={},
    )
    assert response.status_code == 422
