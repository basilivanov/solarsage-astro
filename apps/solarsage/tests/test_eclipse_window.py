"""Tests for sidecar W3.6 eclipse window activations."""
import pytest
from fastapi.testclient import TestClient

from solarsage.app import app

client = TestClient(app)

BASIL_AUG_12 = {
    "birth": {
        "date": "1980-10-30",
        "time": "19:50",
        "lat": 67.9394,
        "lon": 32.8144,
        "tz": "Europe/Moscow",
    },
    "target": {
        "date": "2026-08-12",
        "time": "12:00",
        "tz": "Europe/Moscow",
    },
    "house_system": "PLACIDUS",
    "techniques": [],
}

BASIL_JUL_08 = {
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


# ── Config strictness ────────────────────────────────────────────────────


def test_config_missing_key():
    """Missing eclipse_window config keys raise KeyError."""
    from solarsage.services.eclipses import _load_canon_config
    from solarsage.services.eclipses import _resolve_canon_path
    import yaml
    import copy
    path = _resolve_canon_path("grace/canon/activation_rules.v1.yml")
    with open(path) as f:
        rules = yaml.safe_load(f)
    tech = copy.deepcopy(rules["techniques"]["eclipse_window"])
    for key in ("days_before", "days_after", "orb_to_natal", "strength"):
        bad = copy.deepcopy(rules)
        del bad["techniques"]["eclipse_window"][key]
        import solarsage.services.eclipses as em
        original_path = em._resolve_canon_path
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tf:
            yaml.dump(bad, tf)
            tf_path = tf.name
        def fake_path(rel):
            return tf_path
        em._resolve_canon_path = fake_path
        try:
            with pytest.raises(KeyError, match=key):
                em._load_canon_config()
        finally:
            em._resolve_canon_path = original_path
            os.unlink(tf_path)


def test_config_non_numeric():
    """Non-numeric eclipse_window config values raise KeyError."""
    from solarsage.services.eclipses import _load_canon_config, _resolve_canon_path
    import yaml, copy, tempfile, os
    import solarsage.services.eclipses as em

    path = _resolve_canon_path("grace/canon/activation_rules.v1.yml")
    with open(path) as f:
        rules = yaml.safe_load(f)
    bad = copy.deepcopy(rules)
    bad["techniques"]["eclipse_window"]["days_before"] = "bad"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as tf:
        yaml.dump(bad, tf)
        tf_path = tf.name
    original = em._resolve_canon_path
    em._resolve_canon_path = lambda rel: tf_path
    try:
        with pytest.raises((KeyError, ValueError)):
            em._load_canon_config()
    finally:
        em._resolve_canon_path = original
        os.unlink(tf_path)


# ── Positive: Aug 12 eclipse ─────────────────────────────────────────────


def test_basil_aug12_has_eclipse_activation():
    """Basil 2026-08-12 produces at least one eclipse_window activation."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    assert len(ecl_acts) >= 1, f"Expected at least 1 eclipse activation, got {len(ecl_acts)}"


def test_basil_aug12_nearest_eclipse_is_solar():
    """Nearest eclipse selected for 2026-08-12 is the solar eclipse on that date."""
    from solarsage.services.eclipses import find_eclipses, _load_canon_config
    from solarsage.utils.ephemeris import calculate_julian_day
    config = _load_canon_config()
    target_jd = calculate_julian_day("2026-08-12", "12:00", "Europe/Moscow")
    from solarsage.services.eclipses import _find_eclipse_candidates
    candidates = _find_eclipse_candidates(target_jd, config)
    assert len(candidates) >= 1
    nearest = candidates[0]
    assert nearest["kind"] == "solar", f"Expected solar eclipse, got {nearest['kind']}"
    # The eclipse should be close to target date
    assert abs(nearest["days_delta"]) < 1, f"Eclipse not on target date: delta={nearest['days_delta']}"


def test_basil_aug12_eclipse_ids_stable():
    """Eclipse activation IDs are stable and uppercase."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    for a in ecl_acts:
        assert a["id"].startswith("eclipse_window__")
        parts = a["id"].split("__")
        assert parts[1] in ("SOLAR", "LUNAR")
        assert parts[2] == parts[2].upper()  # type uppercase


def test_basil_aug12_eclipse_evidence():
    """Eclipse evidence contains eclipse kind, type, date, target — not broad text."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    for a in ecl_acts:
        ev = a["evidence"]
        assert "eclipse" in ev.lower()
        # Should mention specific target, not just "eclipse season"
        assert "conjunct" in ev


# ── Negative: Jul 08 no eclipse ──────────────────────────────────────────


def test_basil_jul08_no_eclipse():
    """Basil 2026-07-08 produces no eclipse_window activations (no eclipse in window)."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_JUL_08,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    assert len(ecl_acts) == 0, f"Expected no eclipse activations for Jul 8, got {len(ecl_acts)}"


# ── Debug fields ─────────────────────────────────────────────────────────


def test_eclipse_debug_fields():
    """Eclipse activation debug contains all required fields."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    for a in ecl_acts:
        d = a["debug"]
        for key in ("eclipse_kind", "eclipse_type", "eclipse_retflag", "eclipse_jd",
                     "eclipse_utc_iso", "eclipse_date", "days_delta", "eclipse_longitude",
                     "target_longitude", "orb", "orb_to_natal", "orb_factor",
                     "window_factor", "base_strength", "resolved_house_system"):
            assert key in d, f"Missing key {key} in {a['id']}"


def test_eclipse_debug_formula():
    """Eclipse strength matches base * orb_factor * window_factor."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    for a in ecl_acts:
        d = a["debug"]
        expected = round(min(1.0, float(d["base_strength"]) * float(d["orb_factor"]) * float(d["window_factor"])), 4)
        assert a["strength"] == expected, f"{a['id']}: strength {a['strength']} != expected {expected}"


# ── Indexes ──────────────────────────────────────────────────────────────


def test_eclipse_indexes():
    """Every eclipse activation is referenced in appropriate index."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    valid_ids = {a["id"] for a in ecl_acts}

    for a in ecl_acts:
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
                assert ref_id in valid_ids, f"{idx_name}[{key}] refs '{ref_id}' not in eclipse activations"


def test_eclipse_deterministic():
    """Two builds produce identical eclipse activation ids."""
    resp1 = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    resp2 = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] == "eclipse_window"]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] == "eclipse_window"]
    assert ids1 == ids2


def test_eclipse_conjunction_polarity():
    """Eclipse activations use conjunction aspect, mixed polarity, period phase."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUG_12,
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ecl_acts = [a for a in layer["activations"] if a["technique"] == "eclipse_window"]
    for a in ecl_acts:
        assert a["aspect"] == "conjunction"
        assert a["polarity"] == "mixed"
        assert a["phase"] == "period"
        assert a["source_frame"] == "eclipse"
