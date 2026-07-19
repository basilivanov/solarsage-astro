"""Tests for sidecar W3.5 secondary progression activations."""
import pytest

pytestmark = pytest.mark.usefixtures("moshier_mode")
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


# ── Sun transition tests ────────────────────────────────────────────────


def test_progressed_sun_sign_transition_direct():
    """Progressed Sun near a sign boundary is detected (direct helper test)."""
    from solarsage.services.progressions import progressed_sun_transitions
    from datetime import date
    from unittest.mock import patch

    class FakeCtx:
        birth_jd = 2444543.2
        progressed_sun_lon = 29.5  # 0.5° from Aries→Taurus boundary at 30°
        max_orb = 1.0
        resolved_house_system = "PLACIDUS"
        age_years = 45.68
        progressed_jd = 2444588.88
        progressed_utc_iso = "1981-01-01T00:00:00+00:00"
        target_jd = 2461229.5
        progressed_moon_lon = 0.0
        natal_moon_lon = 0.0
        natal_sun_lon = 0.0
        natal_positions = {}
        natal_angles = {}
        natal_lots = []
        natal_houses = []

    transitions = progressed_sun_transitions(FakeCtx(), 55.0, 37.0, "PLACIDUS", 1.0)
    sign_trans = [t for t in transitions if t["transition_type"] == "sign"]
    assert len(sign_trans) >= 1, "Expected at least one sign transition with Sun at 29.5°"
    t = sign_trans[0]
    assert t["current_sign"] == "Aries"
    assert t["next_sign"] == "Taurus"
    assert t["base_strength"] == 0.5
    assert "orb_factor" in t
    assert "distance_to_boundary" in t


def test_progressed_sun_house_transition_direct():
    """Progressed Sun near a natal house cusp (direct helper test with monkeypatch)."""
    from solarsage.services.progressions import progressed_sun_transitions

    class FakeCtx:
        birth_jd = 2444543.2
        progressed_sun_lon = 45.0  # Arbitrary, house cusp determines proximity
        max_orb = 1.0
        resolved_house_system = "PLACIDUS"
        age_years = 45.68
        progressed_jd = 2444588.88
        progressed_utc_iso = "1981-01-01T00:00:00+00:00"
        target_jd = 2461229.5
        progressed_moon_lon = 0.0
        natal_moon_lon = 0.0
        natal_sun_lon = 0.0
        natal_positions = {}
        natal_angles = {}
        natal_lots = []
        natal_houses = []

    # Monkeypatch calculate_houses_cusps to return a cusp at 44.5° (0.5° from Sun)
    from solarsage.services import progressions as pm
    original = pm.calculate_houses_cusps

    def fake_houses(jd, lat, lon, hs="PLACIDUS"):
        houses = [{"number": 1, "cusp": 44.5, "sign": "Taurus"}]
        for i in range(2, 13):
            houses.append({"number": i, "cusp": float(44.5 + (i - 1) * 30), "sign": "Taurus"})
        special = [{"name": "ASC", "longitude": 44.5, "sign": "Taurus"},
                   {"name": "MC", "longitude": 134.5, "sign": "Leo"}]
        return houses, special, "PLACIDUS"

    pm.calculate_houses_cusps = fake_houses
    try:
        transitions = progressed_sun_transitions(FakeCtx(), 55.0, 37.0, "PLACIDUS", 1.0)
        house_trans = [t for t in transitions if t["transition_type"] == "house"]
        assert len(house_trans) >= 1, "Expected at least one house transition"
        t = house_trans[0]
        assert t["target_house"] == 1
        assert t["base_strength"] == 0.5
        assert "orb_factor" in t
    finally:
        pm.calculate_houses_cusps = original


def test_sun_transition_wrap_around_direct():
    """Aries/Pisces 0-degree wrap-around handled correctly (direct)."""
    from solarsage.services.progressions import progressed_sun_transitions

    class FakeCtx:
        birth_jd = 2444543.2
        progressed_sun_lon = 359.5  # 0.5° from Pisces→Aries at 360/0°
        max_orb = 1.0
        resolved_house_system = "PLACIDUS"
        age_years = 45.68
        progressed_jd = 2444588.88
        progressed_utc_iso = "1981-01-01T00:00:00+00:00"
        target_jd = 2461229.5
        progressed_moon_lon = 0.0
        natal_moon_lon = 0.0
        natal_sun_lon = 0.0
        natal_positions = {}
        natal_angles = {}
        natal_lots = []
        natal_houses = []

    transitions = progressed_sun_transitions(FakeCtx(), 55.0, 37.0, "PLACIDUS", 1.0)
    sign_trans = [t for t in transitions if t["transition_type"] == "sign"]
    assert len(sign_trans) >= 1, "Expected wrap-around sign transition at 359.5°"
    t = sign_trans[0]
    # The forward distance to next boundary at 360° should be 0.5°
    assert abs(t["distance_to_boundary"] - 0.5) < 0.01, f"Expected distance 0.5, got {t['distance_to_boundary']}"
    assert t["current_sign"] in ("Pisces",)
    assert t["next_sign"] in ("Aries",)


def test_sun_transition_builder_sign(monkeypatch):
    """Builder/endpoint produces sign transition activation with full debug keys."""
    from solarsage.services import progressions as pm
    from solarsage.services.activation_builder import build_activation_layer
    from solarsage.schemas.activation import ActivationLayer

    # Monkeypatch progressed_sun_transitions to return a deterministic sign transition
    fake_transitions = [{
        "transition_type": "sign",
        "current_sign": "Aries",
        "previous_sign": None,
        "next_sign": "Taurus",
        "current_house": None,
        "target_house": None,
        "boundary_longitude": 30.0,
        "distance_to_boundary": 0.5,
        "strength": 0.25,
        "base_strength": 0.5,
        "orb_factor": 0.5,
    }]

    def fake_progressed_sun_transitions(ctx, *args, **kwargs):
        return fake_transitions

    monkeypatch.setattr(pm, "progressed_sun_transitions", fake_progressed_sun_transitions)

    result = build_activation_layer(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
        techniques=["secondary_progression"],
    )
    sign_acts = [a for a in result.activations if a.kind == "progressed_sun_sign_transition"]
    assert len(sign_acts) >= 1, "Expected sign transition activation"
    a = sign_acts[0]
    d = a.debug
    assert d.get("transition_type") == "sign"
    assert d.get("current_sign") == "Aries"
    assert d.get("next_sign") == "Taurus"
    assert d.get("current_house") is None
    assert d.get("target_house") is None
    assert d.get("base_strength") == 0.5
    assert d.get("orb_factor") == 0.5
    assert a.strength == 0.25


def test_sun_transition_builder_house(monkeypatch):
    """Builder/endpoint produces house transition activation with full debug keys."""
    from solarsage.services import progressions as pm

    fake_transitions = [{
        "transition_type": "house",
        "current_sign": None,
        "previous_sign": None,
        "next_sign": None,
        "current_house": 5,
        "target_house": 6,
        "boundary_longitude": 150.0,
        "distance_to_boundary": 0.3,
        "strength": 0.35,
        "base_strength": 0.5,
        "orb_factor": 0.7,
    }]

    def fake_progressed_sun_transitions(ctx, *args, **kwargs):
        return fake_transitions

    monkeypatch.setattr(pm, "progressed_sun_transitions", fake_progressed_sun_transitions)

    from solarsage.services.activation_builder import build_activation_layer

    result = build_activation_layer(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
        techniques=["secondary_progression"],
    )
    house_acts = [a for a in result.activations if a.kind == "progressed_sun_house_transition"]
    assert len(house_acts) >= 1, "Expected house transition activation"
    a = house_acts[0]
    d = a.debug
    assert d.get("transition_type") == "house"
    assert d.get("current_house") == 5
    assert d.get("target_house") == 6
    assert d.get("current_sign") is None
    assert d.get("base_strength") == 0.5
    assert d.get("orb_factor") == 0.7
    assert a.strength == 0.35
