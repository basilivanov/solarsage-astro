"""Tests for sidecar W3.5 secondary progression activations."""
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


def test_secondary_progression_age_formula():
    """Progressed JD follows birth_jd + age_years (day-for-year)."""
    from solarsage.services.progressions import calculate_secondary_progression_context
    ctx = calculate_secondary_progression_context(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    expected_progressed_jd = ctx.birth_jd + ctx.age_years
    assert abs(ctx.progressed_jd - expected_progressed_jd) < 0.001


def test_secondary_progression_endpoint_has_activations():
    """Secondary progression endpoint returns at least one activation for Basil."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["secondary_progression"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sp_acts = [a for a in layer["activations"] if a["technique"] == "secondary_progression"]
    assert len(sp_acts) >= 1, f"Expected at least 1 progression activation, got {len(sp_acts)}"
    for a in sp_acts:
        assert a["id"].startswith("secondary_progression__")


def test_secondary_progression_debug_fields():
    """Secondary progression activations include required debug fields."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["secondary_progression"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sp_acts = [a for a in layer["activations"] if a["technique"] == "secondary_progression"]
    for a in sp_acts:
        d = a.get("debug", {})
        assert d.get("progression_method") == "secondary_progression"
        assert d.get("birth_jd", 0) > 0
        assert d.get("target_jd", 0) > 0
        assert d.get("age_years", 0) > 0
        assert d.get("progressed_jd", 0) > 0
        assert d.get("progressed_utc_iso")
        assert d.get("max_orb", 0) > 0
        assert d.get("resolved_house_system")


def test_secondary_progression_moon_aspects():
    """Progressed Moon aspects are detected within configured orb."""
    from solarsage.services.progressions import (
        calculate_secondary_progression_context, progressed_moon_aspects,
    )
    ctx = calculate_secondary_progression_context(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    aspects = progressed_moon_aspects(ctx)
    # Should find at least some aspects
    assert len(aspects) >= 1
    for asp in aspects:
        assert asp["orb"] <= ctx.max_orb


def test_secondary_progression_frames():
    """Secondary progression activations use correct frames."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["secondary_progression"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sp_acts = [a for a in layer["activations"] if a["technique"] == "secondary_progression"]
    for a in sp_acts:
        assert a["source_frame"] == "progressed"
        assert a["target_frame"] in ("natal", "angle", "lot")


def test_secondary_progression_indexes():
    """Every progression activation is referenced in appropriate index."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["secondary_progression"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sp_acts = [a for a in layer["activations"] if a["technique"] == "secondary_progression"]
    valid_ids = {a["id"] for a in sp_acts}

    for a in sp_acts:
        if a["target_type"] == "planet":
            idx = layer.get("by_planet", {})
            assert a["target_key"] in idx, f"by_planet missing {a['target_key']} for {a['id']}"
            assert a["id"] in idx[a["target_key"]]
        elif a["target_type"] == "angle":
            idx = layer.get("by_angle", {})
            assert a["target_key"] in idx, f"by_angle missing {a['target_key']} for {a['id']}"
            assert a["id"] in idx[a["target_key"]]
        elif a["target_type"] == "lot":
            idx = layer.get("by_lot", {})
            assert a["target_key"] in idx, f"by_lot missing {a['target_key']} for {a['id']}"
            assert a["id"] in idx[a["target_key"]]
        elif a["target_type"] == "house":
            idx = layer.get("by_house", {})
            assert a["target_key"] in idx, f"by_house missing {a['target_key']} for {a['id']}"
            assert a["id"] in idx[a["target_key"]]

    for idx_name, idx in [("by_planet", layer.get("by_planet", {})),
                           ("by_angle", layer.get("by_angle", {})),
                           ("by_lot", layer.get("by_lot", {})),
                           ("by_house", layer.get("by_house", {}))]:
        for key, refs in idx.items():
            for ref_id in refs:
                assert ref_id in valid_ids, f"{idx_name}[{key}] refs '{ref_id}' not in SP activations"


def test_secondary_progression_strength_strict():
    """Missing progressed_moon_aspect strength key raises KeyError."""
    from solarsage.services.progressions import _get_progression_strength
    from solarsage.services.progressions import _load_activation_rules
    rules = _load_activation_rules()
    base = rules.get("activation_strength", {}).get("progression_base", {})
    del base["progressed_moon_aspect"]
    with pytest.raises(KeyError, match="progressed_moon_aspect"):
        _get_progression_strength("progressed_moon_aspect", rules_override=rules)


def test_secondary_progression_deterministic():
    """Two builds produce identical progression activation ids."""
    resp1 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["secondary_progression"],
    })
    resp2 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["secondary_progression"],
    })
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] == "secondary_progression"]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] == "secondary_progression"]
    assert ids1 == ids2
