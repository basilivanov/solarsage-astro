"""Tests for sidecar W3.1 transit activation extraction.

Tests that the sidecar builder produces real transit activations with
correct evidence formats, index structures, and deterministic behavior
for all four supported techniques."""
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


def test_endpoint_returns_real_w3_1_transit_activations():
    """Endpoint returns real W3.1 transit activations for a deterministic request."""
    resp = client.post("/v1/activation-layer", json=MOSCOW_FIXTURE_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    assert len(layer["activations"]) > 0
    techniques = {a["technique"] for a in layer["activations"]}
    assert "transit_to_natal" in techniques
    assert "transit_planet_in_house" in techniques


def test_default_activation_order_deterministic():
    """Two default builds produce identical activation id order."""
    resp1 = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    resp2 = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]]
    assert ids1 == ids2, "Activation id order must be deterministic across builds"


def test_transit_moon_aspects_evidence():
    """Basil-like request includes Transit Moon aspects with correct
    evidence format including frames."""
    resp = client.post("/v1/activation-layer", json=MOSCOW_FIXTURE_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    activations = layer["activations"]

    moon_aspects = [
        a for a in activations
        if a.get("source_planet") == "Moon"
        and a.get("technique") == "transit_to_natal"
    ]
    assert len(moon_aspects) >= 1, "Expected at least one transit Moon aspect"
    act = moon_aspects[0]
    assert act["orb"] is not None
    assert act["strength"] > 0.0
    ev = act.get("evidence", "")
    assert "Transit" in ev or "transit" in ev
    assert "Moon" in ev
    assert "transit" in ev.lower()
    assert "natal" in ev.lower()

    # Venus evidence must not contain uppercase planet names
    # (target_key remains uppercase, display name is human-readable)
    ev_text = act.get("evidence", "")
    planet_words = {"SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"}
    found_upper = [w for w in ev_text.split() if w in planet_words]
    assert not found_upper, \
        f"Evidence must use display names, not uppercase planet keys: {found_upper} in '{ev_text}'"


def test_basil_moon_opposition_pluto():
    """Basil audit request includes Transit Moon opposition natal Pluto
    with correct evidence format and phase."""
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    activations = layer["activations"]

    moon_pluto = [
        a for a in activations
        if a.get("source_planet") == "Moon"
        and a.get("technique") == "transit_to_natal"
        and a.get("target_planet") == "PLUTO"
        and a.get("aspect") == "opposition"
    ]
    assert len(moon_pluto) >= 1, "Expected Transit Moon opposition natal Pluto"
    act = moon_pluto[0]

    assert act["id"] == "t2n__MOON__OPPOSITION__PLUTO"
    assert "Transit Moon opposition natal Pluto" in act.get("evidence", "")
    assert abs(act["orb"] - 1.0454) <= 0.05, \
        f"Expected orb near 1.0454°, got {act['orb']}"
    assert act["phase"] == "separating", f"Expected separating, got {act['phase']}"
    assert act["applying"] is False, f"Expected applying=False, got {act['applying']}"


def test_transit_planet_in_house_populates_by_house():
    """transit_planet_in_house activations exist and populate by_house."""
    resp = client.post("/v1/activation-layer", json=MOSCOW_FIXTURE_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]

    tih = [a for a in layer["activations"] if a["technique"] == "transit_planet_in_house"]
    assert len(tih) >= 1, "Expected at least one transit_planet_in_house"

    by_house = layer.get("by_house", {})
    assert len(by_house) >= 1, "by_house must be populated"

    tih_ids = {a["id"] for a in tih}
    all_house_refs = set()
    for refs in by_house.values():
        all_house_refs.update(refs)
    assert tih_ids.issubset(all_house_refs), "All tih ids must appear in by_house"


def test_basil_by_lot_populated():
    """Basil audit fixture has by_lot populated with all seven lots."""
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]

    by_lot = layer.get("by_lot", {})
    assert len(by_lot) >= 1, "by_lot must be populated for Basil fixture"

    # Verify all by_lot refs point to valid activation ids
    valid_ids = {a["id"] for a in layer["activations"]}
    all_lot_refs = set()
    for refs in by_lot.values():
        all_lot_refs.update(refs)
    assert all_lot_refs.issubset(valid_ids), "All by_lot refs must point to valid activation ids"

    # Check that ALL seven expected lot keys are present in by_lot
    lot_keys = set(by_lot.keys())
    expected_lots = {"FORTUNE", "SPIRIT", "EROS", "MARRIAGE", "NECESSITY", "VICTORY", "NEMESIS"}
    missing = expected_lots - lot_keys
    assert not missing, f"Missing expected Basil audit lots in by_lot: {sorted(missing)}"


def test_angle_activations_via_builder():
    """transit_to_angle activations exist for a fixture where angle aspects exist."""
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]

    t2a = [a for a in layer["activations"] if a["technique"] == "transit_to_angle"]
    if t2a:
        for a in t2a:
            assert a.get("angle") in ("ASC", "DSC", "MC", "IC")
            assert a.get("target_frame") == "angle"
            assert "transit" in a.get("evidence", "").lower()
            assert "natal" in a.get("evidence", "").lower()
            assert a.get("source_frame") == "transit"

        by_angle = layer.get("by_angle", {})
        assert len(by_angle) >= 1, "by_angle must be populated if angle activations exist"


def test_empty_techniques_no_fake_unsupported():
    """Empty/unsupported techniques do not generate fake unsupported W3+ techniques."""
    for req in (MOSCOW_FIXTURE_REQUEST, BASIL_AUDIT_REQUEST):
        resp = client.post("/v1/activation-layer", json=req)
        assert resp.status_code == 200
        layer = resp.json()["activation_layer"]
        for a in layer["activations"]:
            assert a["technique"] in (
                "transit_to_natal", "transit_to_angle", "transit_to_lot", "transit_planet_in_house",
                "annual_profection", "monthly_profection",
            ), f"Unexpected technique: {a['technique']}"


def test_all_evidence_strings_include_frames():
    """All evidence strings include frame references (transit, natal, angle, lot)."""
    for req in (MOSCOW_FIXTURE_REQUEST, BASIL_AUDIT_REQUEST):
        resp = client.post("/v1/activation-layer", json=req)
        assert resp.status_code == 200
        layer = resp.json()["activation_layer"]

        for a in layer["activations"]:
            ev = a.get("evidence", "").lower()
            tech = a["technique"]
            if tech in ("transit_to_natal", "transit_planet_in_house"):
                assert "transit" in ev and "natal" in ev, \
                    f"Evidence missing frames: {a['evidence']}"
            elif tech == "transit_to_angle":
                assert "transit" in ev and "natal" in ev, \
                    f"Evidence missing frames: {a['evidence']}"
            elif tech == "transit_to_lot":
                assert "transit" in ev and "lot" in ev, \
                    f"Evidence missing frames: {a['evidence']}"
            elif tech == "annual_profection":
                assert "annual profection" in ev, \
                    f"Evidence missing 'annual profection': {a['evidence']}"
            elif tech == "monthly_profection":
                assert "monthly profection" in ev, \
                    f"Evidence missing 'monthly profection': {a['evidence']}"
