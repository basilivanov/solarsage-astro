"""Tests for sidecar W3.1 transit activation extraction.

Tests that the sidecar builder produces real transit activations with
correct evidence formats, index structures, and deterministic behavior
for all four supported techniques."""
from fastapi.testclient import TestClient
import pytest

pytestmark = pytest.mark.usefixtures("moshier_mode")
from datetime import datetime, timezone
import swisseph as swe

from solarsage.app import app
from solarsage.services.transit_timing import TransitTimingSolver, signed_delta
from solarsage.utils.ephemeris import PLANETS, calculate_julian_day

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


def _parse_utc_z(value: str) -> datetime:
    assert value.endswith("Z")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    return parsed.astimezone(timezone.utc)


def _utc_z_to_jd(value: str) -> float:
    return _parse_utc_z(value).timestamp() / 86400.0 + 2440587.5


def _basil_layer() -> dict:
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    return resp.json()["activation_layer"]


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
    assert act["active_from"] is not None
    assert act["exact_at"] is not None
    assert act["active_until"] is not None
    target_jd = calculate_julian_day("2026-07-08", "12:00", "Europe/Moscow")
    assert _utc_z_to_jd(act["active_from"]) <= target_jd <= _utc_z_to_jd(act["active_until"])
    timing = act["debug"]["timing"]
    assert timing["warning_code"] is None
    assert timing["occurrence_index"] == 0
    exact_jd = _utc_z_to_jd(act["exact_at"])
    moon_lon = swe.calc_ut(exact_jd, PLANETS["Moon"], swe.FLG_SWIEPH | swe.FLG_SPEED)[0][0]
    assert abs(signed_delta(moon_lon, timing["selected_exact_longitude"])) <= 1e-3


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
    for act in tih:
        assert act["active_from"] is None
        assert act["exact_at"] is None
        assert act["active_until"] is None


def test_real_plus_and_minus_branch_debug_is_truthful():
    layer = _basil_layer()
    activations = {a["id"]: a for a in layer["activations"]}
    cases = [
        ("t2n__MOON__OPPOSITION__PLUTO", "plus"),
        ("t2n__SUN__TRINE__MERCURY", "minus"),
    ]
    for activation_id, expected_branch in cases:
        act = activations[activation_id]
        timing = act["debug"]["timing"]
        assert timing["selected_branch"] == expected_branch
        exact_jd = _utc_z_to_jd(act["exact_at"])
        source_lon = swe.calc_ut(exact_jd, PLANETS[act["source_planet"]], swe.FLG_SWIEPH | swe.FLG_SPEED)[0][0]
        assert abs(signed_delta(source_lon, timing["selected_exact_longitude"])) <= 1e-3


def test_near_miss_and_typed_failure_warning_channels(monkeypatch):
    from solarsage.services import activation_builder as ab
    from solarsage.services.transit_timing import TransitTimingResult, TransitTimingError

    original_solve = ab.TransitTimingSolver.solve

    def near_miss_solve(self, **kwargs):
        return TransitTimingResult(
            active_from_utc="2026-07-08T00:00:00Z",
            exact_at_utc=None,
            active_until_utc="2026-07-09T00:00:00Z",
            occurrence_index=None,
            exact_hits_in_window=(),
            phase="applying",
            applying=True,
            selected_branch="plus",
            selected_exact_longitude=10.0,
            warning_code="no_exact_hit_in_window",
        )

    monkeypatch.setattr(ab.TransitTimingSolver, "solve", near_miss_solve)
    near = ab.build_activation_layer(
        birth_date="1980-10-30", birth_time="19:50", birth_lat=67.9394, birth_lon=32.8144,
        birth_tz="Europe/Moscow", target_date="2026-07-08", target_time="12:00",
        target_tz="Europe/Moscow", house_system="PLACIDUS", techniques=["transit_to_natal"],
    )
    near_act = next(a for a in near.activations if a.technique == "transit_to_natal")
    assert near_act.exact_at is None
    assert near_act.active_from == "2026-07-08T00:00:00Z"
    assert near_act.debug["timing"]["warning_code"] == "no_exact_hit_in_window"
    assert not any("no_exact_hit_in_window" in warning for warning in near.warnings)

    def typed_failure_solve(self, **kwargs):
        raise TransitTimingError("target_outside_orb", "forced typed failure")

    monkeypatch.setattr(ab.TransitTimingSolver, "solve", typed_failure_solve)
    failed = ab.build_activation_layer(
        birth_date="1980-10-30", birth_time="19:50", birth_lat=67.9394, birth_lon=32.8144,
        birth_tz="Europe/Moscow", target_date="2026-07-08", target_time="12:00",
        target_tz="Europe/Moscow", house_system="PLACIDUS", techniques=["transit_to_natal"],
    )
    failed_act = next(a for a in failed.activations if a.technique == "transit_to_natal")
    assert failed_act.active_from is None
    assert failed_act.exact_at is None
    assert failed_act.active_until is None
    assert failed_act.debug["applying_probe_days"] == 0.1
    assert failed_act.debug["timing"]["warning_code"] == "target_outside_orb"
    assert any(warning.startswith("transit_timing:") and warning.endswith(":target_outside_orb") for warning in failed.warnings)

    monkeypatch.setattr(ab.TransitTimingSolver, "solve", original_solve)


def test_real_moon_short_window_and_slow_source_solver_proofs():
    layer = _basil_layer()
    moon_pluto = next(a for a in layer["activations"] if a["id"] == "t2n__MOON__OPPOSITION__PLUTO")
    window_hours = (_parse_utc_z(moon_pluto["active_until"]) - _parse_utc_z(moon_pluto["active_from"])).total_seconds() / 3600
    assert window_hours < 24

    target_jd = calculate_julian_day("2026-07-08", "12:00", "Europe/Moscow")
    source = "Uranus"
    source_lon = swe.calc_ut(target_jd, PLANETS[source], swe.FLG_SWIEPH | swe.FLG_SPEED)[0][0]
    result = TransitTimingSolver(target_jd=target_jd).solve(
        source_planet=source,
        target_longitude=source_lon,
        aspect_angle=0.0,
        max_orb=1.0,
    )
    assert result.exact_at_utc == "2026-07-08T09:00:00Z"
    assert result.active_from_utc < result.exact_at_utc < result.active_until_utc


def test_full_request_rebuild_byte_identical_timing_and_debug():
    first = _basil_layer()
    second = _basil_layer()
    first_projection = [
        (a["id"], a["active_from"], a["exact_at"], a["active_until"], a["phase"], a["applying"], a.get("debug", {}).get("timing"))
        for a in first["activations"]
    ]
    second_projection = [
        (a["id"], a["active_from"], a["exact_at"], a["active_until"], a["phase"], a["applying"], a.get("debug", {}).get("timing"))
        for a in second["activations"]
    ]
    assert first_projection == second_projection
    assert first["warnings"] == second["warnings"]


def test_request_scoped_solver_and_call_budget(monkeypatch):
    from solarsage.services import activation_builder as ab

    original_solver = ab.TransitTimingSolver
    solver_instances = []

    class SpySolver(original_solver):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            solver_instances.append(self)

    calculate_positions_calls = []
    original_calculate_positions = ab.calculate_positions

    def spy_calculate_positions(jd):
        calculate_positions_calls.append(jd)
        return original_calculate_positions(jd)

    monkeypatch.setattr(ab, "TransitTimingSolver", SpySolver)
    monkeypatch.setattr(ab, "calculate_positions", spy_calculate_positions)

    layer = ab.build_activation_layer(
        birth_date="1980-10-30", birth_time="19:50", birth_lat=67.9394, birth_lon=32.8144,
        birth_tz="Europe/Moscow", target_date="2026-07-08", target_time="12:00",
        target_tz="Europe/Moscow", house_system="PLACIDUS", techniques=[],
    )
    transit_count = sum(1 for a in layer.activations if a.technique in ("transit_to_natal", "transit_to_angle", "transit_to_lot"))
    target_jd = calculate_julian_day("2026-07-08", "12:00", "Europe/Moscow")
    assert len(solver_instances) == 1
    assert transit_count >= 100
    assert not any(abs(jd - (target_jd + 0.1)) < 1e-8 for jd in calculate_positions_calls)
    assert len(calculate_positions_calls) <= 3
    cache = solver_instances[0].cache
    assert cache.misses == len(cache.cache)
    assert cache.misses < 10000  # observed lazy grid 7253; >25% deterministic headroom.


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
                "firdar_major", "firdar_minor",
                "solar_return", "lunar_return",
                "solar_arc", "secondary_progression",
                "eclipse_window",
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
            elif tech in ("firdar_major", "firdar_minor"):
                assert "firdar lord" in ev, \
                    f"Evidence missing 'firdar lord': {a['evidence']}"
            elif tech in ("solar_return", "lunar_return"):
                assert "return" in ev, \
                    f"Evidence missing 'return': {a['evidence']}"
            elif tech in ("solar_arc", "secondary_progression"):
                assert "solar arc" in ev or "progressed" in ev or "Solar Arc" in ev, \
                    f"Evidence missing progression context: {a['evidence']}"
            elif tech == "eclipse_window":
                assert "eclipse" in ev, \
                    f"Evidence missing eclipse: {a['evidence']}"
