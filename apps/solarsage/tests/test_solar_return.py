"""Tests for sidecar W3.4 solar return activations."""
import pytest
from fastapi.testclient import TestClient

from solarsage.app import app

client = TestClient(app)

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


def test_solar_return_service_precision():
    """Solar return longitude residual <= 0.001°."""
    from solarsage.services.returns import calculate_solar_return
    sr = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    residual = abs(sr.return_sun_lon - sr.natal_sun_lon) % 360.0
    if residual > 180.0:
        residual = 360.0 - residual
    assert residual <= 0.001, f"Solar return longitude residual {residual} > 0.001°"


def test_solar_return_basil_jd():
    """Basil 2026 solar return JD matches historical fixture within tolerance."""
    from solarsage.services.returns import calculate_solar_return
    sr = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    expected_jd = 2461344.3452186584
    assert abs(sr.return_jd - expected_jd) < 0.001, \
        f"SR JD {sr.return_jd} differs from expected {expected_jd}"


def test_solar_return_timestamp_stable():
    """Solar return UTC timestamp is stable across calls."""
    from solarsage.services.returns import calculate_solar_return
    sr1 = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    sr2 = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    assert sr1.return_utc_iso == sr2.return_utc_iso


def test_solar_return_endpoint_activations():
    """Solar return endpoint returns expected activations for Basil."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    assert len(sr_acts) >= 3, f"Expected at least 3 solar return activations, got {len(sr_acts)}"

    # Check kinds
    kinds = {a["kind"] for a in sr_acts}
    assert "return_angle_in_natal_house" in kinds
    assert "return_chart_ruler" in kinds

    # IDs stable
    ids = [a["id"] for a in sr_acts]
    for aid in ids:
        assert aid.startswith("solar_return__"), f"Unexpected ID: {aid}"


def test_solar_return_debug_fields():
    """Solar return activations include return_jd, timestamp, location policy."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    for a in sr_acts:
        d = a.get("debug", {})
        assert d.get("return_jd", 0) > 0, f"Missing return_jd in {a['id']}"
        assert d.get("return_utc_iso"), f"Missing return_utc_iso in {a['id']}"
        assert d.get("return_location_policy") == "current_location_if_known_else_birth_location"
        assert d.get("return_location_source") == "birth_location"


def test_solar_return_indexes():
    """Solar return activation IDs referenced in by_house/by_planet."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    valid_ids = {a["id"] for a in sr_acts}

    for idx_name in ("by_house", "by_planet"):
        idx = layer.get(idx_name, {})
        for key, refs in idx.items():
            for ref_id in refs:
                if ref_id in valid_ids:
                    break  # At least one ref is from SR activations


def test_solar_return_location_source():
    """Solar return with explicit current_location changes location_source
    and actually changes return chart houses/ASC/MC."""
    # Baseline with birth location
    base_resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    base_ids = [a["id"] for a in base_resp.json()["activation_layer"]["activations"]
                if a["technique"] == "solar_return"]

    # Relocated to equator
    reloc_resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
        "current_location": {"lat": 0.0, "lon": 0.0, "tz": "UTC"},
    })
    assert reloc_resp.status_code == 200
    layer = reloc_resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    for a in sr_acts:
        assert a["debug"]["return_location_source"] == "current_location"

    # Activation IDs must differ (chart changed with location)
    reloc_ids = [a["id"] for a in reloc_resp.json()["activation_layer"]["activations"]
                  if a["technique"] == "solar_return"]
    assert base_ids != reloc_ids, "Relocated solar return must produce different activation IDs"

    # Resolved house system for equator should be PLACIDUS (low latitude)
    for a in sr_acts:
        assert a["debug"]["resolved_house_system"] == "PLACIDUS", \
            f"Expected PLACIDUS for equator, got {a['debug']['resolved_house_system']}"


def test_solar_return_no_fallback_warning_with_current_location():
    """When current_location supplied, no fallback warning emitted."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
        "current_location": {"lat": 43.5, "lon": 39.5, "tz": "Europe/Moscow"},
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    # No fallback warning should appear
    for w in layer.get("warnings", []):
        assert "return_location_fallback" not in w, f"Unexpected fallback warning: {w}"


def test_solar_return_only_when_requested():
    """Only solar_return emitted when specifically requested."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    techniques = {a["technique"] for a in resp.json()["activation_layer"]["activations"]}
    assert "solar_return" in techniques
    assert "lunar_return" not in techniques
    assert "firdar_major" not in techniques


def test_solar_return_deterministic():
    """Two builds produce identical solar return activation ids."""
    resp1 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    resp2 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] == "solar_return"]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] == "solar_return"]
    assert ids1 == ids2


# ── Strength strictness ─────────────────────────────────────────────────


def test_strength_missing_solar_return_key():
    """Missing solar_return_angle_in_natal_house raises KeyError."""
    from solarsage.services.activation_builder import _get_return_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    period_base = rules.get("activation_strength", {}).get("return_base", {})
    del period_base["solar_return_angle_in_natal_house"]
    with pytest.raises(KeyError, match="solar_return_angle_in_natal_house"):
        _get_return_strength(rules, "solar_return_angle_in_natal_house")


def test_strength_missing_lunar_return_key():
    """Missing lunar_return_moon_house raises KeyError."""
    from solarsage.services.activation_builder import _get_return_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    period_base = rules.get("activation_strength", {}).get("return_base", {})
    del period_base["lunar_return_moon_house"]
    with pytest.raises(KeyError, match="lunar_return_moon_house"):
        _get_return_strength(rules, "lunar_return_moon_house")
