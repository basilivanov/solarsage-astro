"""Tests for sidecar W3.4 lunar return activations."""
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


def test_lunar_return_service_precision():
    """Lunar return longitude residual <= 0.001°."""
    from solarsage.services.returns import calculate_lunar_return
    lr = calculate_lunar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    residual = abs(lr.return_moon_lon - lr.natal_moon_lon) % 360.0
    if residual > 180.0:
        residual = 360.0 - residual
    assert residual <= 0.001, f"Lunar return longitude residual {residual} > 0.001°"


def test_lunar_return_before_target():
    """Lunar return JD is at or before target JD."""
    from solarsage.services.returns import calculate_lunar_return
    from solarsage.utils.ephemeris import calculate_julian_day
    lr = calculate_lunar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    target_jd = calculate_julian_day("2026-07-08", "12:00", "Europe/Moscow")
    assert lr.return_jd <= target_jd, f"LR JD {lr.return_jd} > target JD {target_jd}"
    assert target_jd - lr.return_jd < 30, \
        f"LR JD {lr.return_jd} more than 30 days before target"


def test_lunar_return_timestamp_stable():
    """Lunar return UTC timestamp is stable across calls."""
    from solarsage.services.returns import calculate_lunar_return
    lr1 = calculate_lunar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    lr2 = calculate_lunar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    assert lr1.return_utc_iso == lr2.return_utc_iso


def test_lunar_return_moon_activation():
    """Lunar return Moon house activation exists."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    lr_acts = [a for a in layer["activations"] if a["technique"] == "lunar_return"]
    # Must have at least Moon house activation
    moon_acts = [a for a in lr_acts if a["kind"] == "return_moon_house"]
    assert len(moon_acts) >= 1, "Expected at least one lunar return Moon house activation"


def test_lunar_return_angle_activations():
    """Lunar return ASC/MC natal house activations exist."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    lr_acts = [a for a in layer["activations"] if a["technique"] == "lunar_return"]
    angle_acts = [a for a in lr_acts if a["kind"] == "return_angle_in_natal_house"]
    assert len(angle_acts) >= 1, "Expected at least one lunar return ASC/MC activation"


def test_lunar_return_debug_fields():
    """Lunar return activations include all required debug fields."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    lr_acts = [a for a in layer["activations"] if a["technique"] == "lunar_return"]
    for a in lr_acts:
        d = a.get("debug", {})
        assert d.get("return_type") == "lunar"
        assert d.get("return_jd", 0) > 0, f"Missing return_jd in {a['id']}"
        assert d.get("return_utc_iso"), f"Missing return_utc_iso in {a['id']}"
        assert d.get("target_jd", 0) > 0, f"Missing target_jd in {a['id']}"
        assert d.get("return_location_policy") == "current_location_if_known_else_birth_location"
        assert d.get("return_location_source") in ("birth_location", "current_location")
        assert d.get("return_location_reason"), f"Missing return_location_reason in {a['id']}"
        assert "return_lat" in d, f"Missing return_lat in {a['id']}"
        assert "return_lon" in d, f"Missing return_lon in {a['id']}"
        assert d.get("return_tz") is not None, f"Missing return_tz in {a['id']}"
        assert d.get("resolved_house_system"), f"Missing resolved_house_system in {a['id']}"


def test_lunar_return_indexes():
    """Every lunar return activation is referenced in appropriate index."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    lr_acts = [a for a in layer["activations"] if a["technique"] == "lunar_return"]
    valid_ids = {a["id"] for a in lr_acts}

    # Every LR activation must have its ID in the appropriate index
    for a in lr_acts:
        if a["target_type"] == "house":
            idx = layer.get("by_house", {})
            assert a["target_key"] in idx, f"by_house missing key {a['target_key']} for {a['id']}"
            assert a["id"] in idx[a["target_key"]], f"by_house[{a['target_key']}] missing {a['id']}"
        elif a["target_type"] == "planet":
            idx = layer.get("by_planet", {})
            assert a["target_key"] in idx, f"by_planet missing key {a['target_key']} for {a['id']}"
            assert a["id"] in idx[a["target_key"]], f"by_planet[{a['target_key']}] missing {a['id']}"

    # Every index ref must point to a valid activation
    for idx_name, idx in [("by_house", layer.get("by_house", {})),
                           ("by_planet", layer.get("by_planet", {}))]:
        for key, refs in idx.items():
            for ref_id in refs:
                assert ref_id in valid_ids, f"{idx_name}[{key}] refs '{ref_id}' not in {idx_name}"


def test_lunar_return_latest_crossing_July():
    """Lunar return chooses latest valid crossing for Jul 16 target."""
    from solarsage.services.returns import calculate_lunar_return
    lr = calculate_lunar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-16", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    expected_latest = 2461236.9515122585
    assert abs(lr.return_jd - expected_latest) < 0.01, \
        f"Expected latest LR JD near {expected_latest}, got {lr.return_jd}"


def test_lunar_return_latest_crossing_August():
    """Lunar return chooses latest valid crossing for Aug 12 target (Aug regression)."""
    from solarsage.services.returns import calculate_lunar_return
    lr = calculate_lunar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-08-12", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    # Must be the late-August crossing, not the late-June one
    expected_latest = 2461264.375656118
    assert abs(lr.return_jd - expected_latest) < 0.01, \
        f"Expected latest LR JD near {expected_latest}, got {lr.return_jd}"
    # Also verify it's NOT the old broken value
    broken_value = 2461236.9515122585
    assert abs(lr.return_jd - broken_value) > 1.0, \
        f"LR JD {lr.return_jd} is still the old broken value {broken_value}"
    # Within 30 days of target
    from solarsage.utils.ephemeris import calculate_julian_day
    target_jd = calculate_julian_day("2026-08-12", "12:00", "Europe/Moscow")
    assert target_jd - lr.return_jd < 30, "LR not within 30 days of target"
    assert lr.return_jd <= target_jd, "LR after target"


def test_lunar_return_location_changes_results():
    """Lunar return with current_location changes activation IDs."""
    base = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    base_ids = [a["id"] for a in base.json()["activation_layer"]["activations"]
                if a["technique"] == "lunar_return"]

    reloc = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
        "current_location": {"lat": 0.0, "lon": 0.0, "tz": "UTC"},
    })
    reloc_ids = [a["id"] for a in reloc.json()["activation_layer"]["activations"]
                  if a["technique"] == "lunar_return"]
    assert base_ids != reloc_ids, "Lunar return IDs must change with relocation"


def test_lunar_return_only_when_requested():
    """Only lunar_return emitted when specifically requested."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    assert resp.status_code == 200
    techniques = {a["technique"] for a in resp.json()["activation_layer"]["activations"]}
    assert "lunar_return" in techniques
    assert "solar_return" not in techniques


def test_lunar_return_deterministic():
    """Two builds produce identical lunar return activation ids."""
    resp1 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    resp2 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["lunar_return"],
    })
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] == "lunar_return"]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] == "lunar_return"]
    assert ids1 == ids2
