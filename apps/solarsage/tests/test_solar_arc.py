"""Tests for sidecar W3.5 solar arc activations."""
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


def test_solar_arc_delta_deterministic():
    """Solar arc delta equals progressed_sun - natal_sun within tolerance."""
    from solarsage.services.progressions import calculate_solar_arc_context
    ctx = calculate_solar_arc_context(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    expected_delta = (ctx.progressed_sun_lon - ctx.natal_sun_lon) % 360.0
    assert abs(ctx.solar_arc_delta - expected_delta) < 0.001 or \
           abs(ctx.solar_arc_delta - expected_delta + 360.0) < 0.001


def test_solar_arc_endpoint_has_activations():
    """Solar arc endpoint returns at least one activation for Basil."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_arc"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sa_acts = [a for a in layer["activations"] if a["technique"] == "solar_arc"]
    assert len(sa_acts) >= 1, f"Expected at least 1 solar arc activation, got {len(sa_acts)}"
    for a in sa_acts:
        assert a["id"].startswith("solar_arc__"), f"Unexpected ID: {a['id']}"


def test_solar_arc_debug_fields():
    """Solar arc activations include all required debug fields."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_arc"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sa_acts = [a for a in layer["activations"] if a["technique"] == "solar_arc"]
    for a in sa_acts:
        d = a.get("debug", {})
        assert d.get("progression_method") == "solar_arc"
        assert d.get("birth_jd", 0) > 0
        assert d.get("target_jd", 0) > 0
        assert d.get("age_years", 0) > 0
        assert d.get("progressed_jd", 0) > 0
        assert d.get("progressed_utc_iso")
        assert d.get("max_orb", 0) > 0
        assert d.get("resolved_house_system")
        assert "solar_arc_delta" in d
        assert "natal_sun_longitude" in d
        assert "progressed_sun_longitude" in d


def test_solar_arc_frames():
    """Solar arc activations use correct source/target frames."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_arc"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sa_acts = [a for a in layer["activations"] if a["technique"] == "solar_arc"]
    for a in sa_acts:
        assert a["source_frame"] == "solar_arc"
        assert a["target_frame"] in ("natal", "angle", "lot")


def test_solar_arc_indexes():
    """Every solar arc activation is referenced in appropriate index."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_arc"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sa_acts = [a for a in layer["activations"] if a["technique"] == "solar_arc"]
    valid_ids = {a["id"] for a in sa_acts}

    for a in sa_acts:
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

    for idx_name, idx in [("by_planet", layer.get("by_planet", {})),
                           ("by_angle", layer.get("by_angle", {})),
                           ("by_lot", layer.get("by_lot", {}))]:
        for key, refs in idx.items():
            for ref_id in refs:
                assert ref_id in valid_ids, f"{idx_name}[{key}] refs '{ref_id}' not in SA activations"


def test_solar_arc_strength_strict():
    """Missing solar_arc_aspect strength key raises KeyError."""
    from solarsage.services.progressions import _get_progression_strength
    from solarsage.services.progressions import _load_activation_rules
    rules = _load_activation_rules()
    base = rules.get("activation_strength", {}).get("progression_base", {})
    del base["solar_arc_aspect"]
    # rules_override allows testing with modified rules
    with pytest.raises(KeyError, match="solar_arc_aspect"):
        _get_progression_strength("solar_arc_aspect", rules_override=rules)


def test_solar_arc_deterministic():
    """Two builds produce identical solar arc activation ids."""
    resp1 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_arc"],
    })
    resp2 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_arc"],
    })
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] == "solar_arc"]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] == "solar_arc"]
    assert ids1 == ids2


# ── Missing orb key ──────────────────────────────────────────────────────


def _patch_progression_orb(value):
    """Context manager to patch _load_activation_rules for orb tests."""
    import solarsage.services.progressions as pm
    from solarsage.services.progressions import _load_activation_rules
    import copy
    rules = _load_activation_rules()
    return rules


def test_missing_solar_arc_orb_key():
    """Missing solar_arc.orb raises KeyError."""
    from solarsage.services.progressions import _get_progression_orb
    from solarsage.services.progressions import _load_activation_rules
    import copy
    rules = _load_activation_rules()
    del rules["techniques"]["solar_arc"]["orb"]
    import solarsage.services.progressions as pm
    original_load = pm._load_activation_rules
    pm._load_activation_rules = lambda: rules
    try:
        with pytest.raises(KeyError, match="solar_arc.orb"):
            _get_progression_orb("solar_arc")
    finally:
        pm._load_activation_rules = original_load


def test_missing_secondary_progression_orb_key():
    """Missing secondary_progression.orb raises KeyError."""
    from solarsage.services.progressions import _get_progression_orb
    from solarsage.services.progressions import _load_activation_rules
    import copy
    rules = _load_activation_rules()
    del rules["techniques"]["secondary_progression"]["orb"]
    import solarsage.services.progressions as pm
    original_load = pm._load_activation_rules
    pm._load_activation_rules = lambda: rules
    try:
        with pytest.raises(KeyError, match="secondary_progression.orb"):
            _get_progression_orb("secondary_progression")
    finally:
        pm._load_activation_rules = original_load


@pytest.mark.parametrize("technique", ["solar_arc", "secondary_progression"])
def test_non_numeric_orb_raises(technique):
    """Non-numeric orb value raises KeyError for both progression techniques."""
    from solarsage.services.progressions import _get_progression_orb
    from solarsage.services.progressions import _load_activation_rules
    import copy
    rules = _load_activation_rules()
    rules["techniques"][technique]["orb"] = "bad"
    import solarsage.services.progressions as pm
    original_load = pm._load_activation_rules
    pm._load_activation_rules = lambda: rules
    try:
        with pytest.raises((KeyError, ValueError)):
            _get_progression_orb(technique)
    finally:
        pm._load_activation_rules = original_load


# ── Shared aspect canon ─────────────────────────────────────────────────


def test_progression_aspects_match_builder_map():
    """Progression ASPECT_ANGLES matches activation_builder's canonical map."""
    from solarsage.services.progressions import ASPECT_ANGLES as prog_angles
    from solarsage.services.activation_builder import ASPECT_ANGLES as build_angles
    assert prog_angles == build_angles, "Aspect maps must be identical"
    # Also verify they are the same object (imported, not duplicated)
    assert prog_angles is build_angles, "Aspect maps should be shared, not duplicated"
