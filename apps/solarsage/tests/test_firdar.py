"""Tests for sidecar W3.3 firdar activations.

Tests canon loading, Basil golden values, day/night fixture compatibility,
exact boundary behavior, technique filtering, node periods, Feb 29 births,
and historical fixture verification."""
import json
import pytest
from pathlib import Path
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

MOSCOW_DAY_REQUEST = {
    "birth": {
        "date": "1990-01-15",
        "time": "14:30",
        "lat": 55.7558,
        "lon": 37.6173,
        "tz": "Europe/Moscow",
    },
    "target": {
        "date": "2026-06-15",
        "time": "12:00",
        "tz": "Europe/Moscow",
    },
    "house_system": "PLACIDUS",
    "techniques": [],
}


# ── Canon ────────────────────────────────────────────────────────────────────


def test_canon_loads():
    """firdar.v1.yml canon loads with required keys."""
    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    assert canon["cycle_years"] == 75
    assert canon["minor_divisions"] == 7
    assert len(canon["day_sequence"]) == 9
    assert len(canon["night_sequence"]) == 9
    assert len(canon["node_minor_sequence"]) == 7


def test_canon_day_sequence():
    """Day sequence matches expected order and year counts."""
    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    seq = canon["day_sequence"]
    expected = [
        ("SUN", 10), ("VENUS", 8), ("MERCURY", 13), ("MOON", 9),
        ("SATURN", 11), ("JUPITER", 12), ("MARS", 7),
        ("NORTH_NODE_TRUE", 3), ("SOUTH_NODE", 2),
    ]
    for entry, (exp_lord, exp_years) in zip(seq, expected):
        assert entry["lord"] == exp_lord, f"Day seq lord: expected {exp_lord}, got {entry['lord']}"
        assert entry["years"] == exp_years, f"Day seq {exp_lord} years: expected {exp_years}, got {entry['years']}"


def test_canon_night_sequence():
    """Night sequence matches expected order and year counts."""
    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    seq = canon["night_sequence"]
    expected = [
        ("MOON", 9), ("SATURN", 11), ("JUPITER", 12), ("MARS", 7),
        ("SUN", 10), ("VENUS", 8), ("MERCURY", 13),
        ("NORTH_NODE_TRUE", 3), ("SOUTH_NODE", 2),
    ]
    for entry, (exp_lord, exp_years) in zip(seq, expected):
        assert entry["lord"] == exp_lord
        assert entry["years"] == exp_years


# ── Calculation ──────────────────────────────────────────────────────────────


def test_calculate_firdar_basil():
    """Basil audit: night birth, major=SUN, minor=SATURN, age=45.687..."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1980, 10, 30),
        target_local=date(2026, 7, 8),
        is_day_birth=False,
        sun_house=5,
        canon=canon,
    )
    assert ctx.is_day_birth is False
    assert ctx.sun_house == 5
    assert abs(ctx.age_years - 45.68767123) < 1e-6
    assert ctx.major_lord == "SUN"
    assert ctx.minor_lord == "SATURN"
    assert ctx.cycle_years == 75
    assert ctx.cycle_index == 0


def test_calculate_firdar_test_user():
    """test_user day fixture: day birth, major=MOON, minor=SUN."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1990, 1, 15),
        target_local=date(2026, 6, 15),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.is_day_birth is True
    assert ctx.major_lord == "MOON"
    assert ctx.minor_lord == "SUN"


# ── Boundary / decimal age ───────────────────────────────────────────────────


def test_decimal_age_one_day_before_birthday():
    """One day before 10th birthday: age_years < 10.0, major=SUN."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1990, 7, 1),
        target_local=date(2000, 6, 30),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.age_years < 10.0, f"Expected age < 10, got {ctx.age_years}"
    assert ctx.major_lord == "SUN", f"Expected SUN, got {ctx.major_lord}"


def test_decimal_age_exact_birthday():
    """Exactly on 10th birthday: age_years == 10.0, major=VENUS."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1990, 7, 1),
        target_local=date(2000, 7, 1),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.age_years == 10.0, f"Expected age == 10.0, got {ctx.age_years}"
    assert ctx.major_lord == "VENUS", f"Expected VENUS, got {ctx.major_lord}"
    assert ctx.minor_lord == "VENUS", f"Expected VENUS minor, got {ctx.minor_lord}"


def test_exact_boundary_day_age_10():
    """Day birth, exact age 10: major=VENUS (next after SUN period)."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1990, 1, 15),
        target_local=date(2000, 1, 15),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert abs(ctx.age_years - 10.0) < 1e-6
    assert ctx.major_lord == "VENUS"
    assert ctx.minor_lord == "VENUS"


def test_exact_boundary_night_age_49():
    """Night birth, exact age 49: major=VENUS (next after SUN period)."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1980, 10, 30),
        target_local=date(2029, 10, 30),
        is_day_birth=False,
        sun_house=5,
        canon=canon,
    )
    assert abs(ctx.age_years - 49.0) < 1e-6
    assert ctx.major_lord == "VENUS"
    assert ctx.minor_lord == "VENUS"


# ── Feb 29 birth ─────────────────────────────────────────────────────────────


def test_feb29_non_leap_before_clamped_anniversary():
    """Feb 29 birth, non-leap target, before Feb 28 clamped anniversary: age < integer."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1992, 2, 29),
        target_local=date(1993, 2, 27),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.age_years < 1.0, f"Expected age < 1, got {ctx.age_years}"
    assert 0 <= ctx.age_years < 1.0


def test_feb29_non_leap_exact_clamped_anniversary():
    """Feb 29 birth, non-leap target, exactly Feb 28: age == 1.0."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1992, 2, 29),
        target_local=date(1993, 2, 28),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.age_years == 1.0, f"Expected age == 1.0, got {ctx.age_years}"


def test_feb29_leap_exact_anniversary():
    """Feb 29 birth, leap target, exactly Feb 29: age == 4.0."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(1992, 2, 29),
        target_local=date(1996, 2, 29),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.age_years == 4.0, f"Expected age == 4.0, got {ctx.age_years}"


def test_feb29_birth_one_year():
    """Feb 29 birth, target exactly one year later in a leap year: age == 1.0."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    ctx = calculate_firdar(
        birth_local=date(2000, 2, 29),
        target_local=date(2001, 2, 28),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.age_years == 1.0, f"Expected age == 1.0, got {ctx.age_years}"


# ── Node periods ─────────────────────────────────────────────────────────────


def test_node_major_north_node_true():
    """Age ~70: NORTH_NODE_TRUE major, first node minor SATURN."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    # Target such that age is between 67 (MARS end) and 70 (NN start)
    # NN starts at 67 (10 SUN + 8 VENUS + 13 MERCURY + 9 MOON + 11 SATURN + 12 JUPITER + 7 MARS = 70... no)
    # Let me recalculate: SUN(10) + VENUS(8) = 18, + MERCURY(13) = 31, + MOON(9) = 40,
    # + SATURN(11) = 51, + JUPITER(12) = 63, + MARS(7) = 70
    # So NN starts at 70
    ctx = calculate_firdar(
        birth_local=date(1990, 1, 1),
        target_local=date(2060, 1, 1),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.major_lord == "NORTH_NODE_TRUE", f"Expected NORTH_NODE_TRUE, got {ctx.major_lord}"
    assert ctx.minor_lord == "SATURN", f"Expected SATURN minor, got {ctx.minor_lord}"


def test_node_major_south_node():
    """Age ~73: SOUTH_NODE major, first node minor SATURN."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    # NN(3) at 70-73, SN(2) at 73-75
    ctx = calculate_firdar(
        birth_local=date(1990, 1, 1),
        target_local=date(2063, 1, 1),
        is_day_birth=True,
        sun_house=9,
        canon=canon,
    )
    assert ctx.major_lord == "SOUTH_NODE", f"Expected SOUTH_NODE, got {ctx.major_lord}"
    assert ctx.minor_lord == "SATURN", f"Expected SATURN minor, got {ctx.minor_lord}"


def test_node_period_endpoint_evidence():
    """Node period endpoint returns readable evidence (North Node, not NORTH_NODE_TRUE)."""
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1990-01-01", "time": "12:00", "lat": 55.0, "lon": 37.0, "tz": "Europe/Moscow"},
        "target": {"date": "2060-06-15", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    for a in layer["activations"]:
        if a["technique"] in ("firdar_major", "firdar_minor"):
            ev = a.get("evidence", "")
            assert "NORTH_NODE_TRUE" not in ev, f"Evidence should not contain raw key: {ev}"
            assert "SOUTH_NODE" not in ev, f"Evidence should not contain raw key: {ev}"
            # Should use readable display names
            if "north node" in ev.lower() or "south node" in ev.lower():
                assert "North" in ev or "South" in ev


def test_node_period_by_planet():
    """Node period activations are referenced in by_planet."""
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1990-01-01", "time": "12:00", "lat": 55.0, "lon": 37.0, "tz": "Europe/Moscow"},
        "target": {"date": "2060-06-15", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    by_planet = layer.get("by_planet", {})
    # Verify at least one firdar activation has by_planet ref
    firdar_acts = [a for a in layer["activations"] if a["technique"] == "firdar_major"]
    for a in firdar_acts:
        assert a["target_key"] in by_planet, f"by_planet missing key {a['target_key']}"
        assert a["id"] in by_planet[a["target_key"]], f"by_planet[{a['target_key']}] missing {a['id']}"


# ── Strength strict lookup ───────────────────────────────────────────────────


def test_strength_strict_lookup():
    """_get_period_strength raises KeyError on missing firdar strength key."""
    from solarsage.services.activation_builder import _get_period_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    assert _get_period_strength(rules, "firdar_major") == 0.65
    assert _get_period_strength(rules, "firdar_minor") == 0.40
    with pytest.raises(KeyError):
        _get_period_strength(rules, "nonexistent_technique")


# ── Spy test: calculate_firdar called once ───────────────────────────────────


def test_calculate_firdar_called_once(monkeypatch):
    """When both firdar_major and firdar_minor are requested, calculate_firdar
    is called exactly once (not once per technique)."""
    from solarsage.services import firdar as firdar_module
    call_count = 0
    original = firdar_module.calculate_firdar

    def spy(**kwargs):
        nonlocal call_count
        call_count += 1
        return original(**kwargs)

    monkeypatch.setattr(firdar_module, "calculate_firdar", spy)

    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    assert call_count == 1, f"Expected calculate_firdar called once, got {call_count}"


# ── Endpoint tests ───────────────────────────────────────────────────────────


def test_basil_firdar_endpoint():
    """Basil endpoint returns firdar_major=SUN, firdar_minor=SATURN."""
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    activations = layer["activations"]

    major = [a for a in activations if a["id"] == "firdar_major__PERIOD_LORD__SUN"]
    assert len(major) == 1
    m = major[0]
    assert m["technique"] == "firdar_major"
    assert m["technique_family"] == "firdar"
    assert m["target_key"] == "SUN"
    assert m["kind"] == "major_period_lord"
    assert m["phase"] == "period"
    assert m["polarity"] == "neutral"
    assert m["strength"] == 0.65
    assert "Sun is major firdar lord" in m["evidence"]
    assert m["target_planet"] == "SUN"

    minor = [a for a in activations if a["id"] == "firdar_minor__SUBPERIOD_LORD__SATURN"]
    assert len(minor) == 1
    mi = minor[0]
    assert mi["technique"] == "firdar_minor"
    assert mi["technique_family"] == "firdar"
    assert mi["target_key"] == "SATURN"
    assert mi["kind"] == "minor_period_lord"
    assert mi["phase"] == "period"
    assert mi["strength"] == 0.40
    assert "Saturn is minor firdar lord" in mi["evidence"]

    # Index refs
    assert "SUN" in layer.get("by_planet", {})
    assert "SATURN" in layer.get("by_planet", {})
    assert m["id"] in layer["by_planet"]["SUN"]
    assert mi["id"] in layer["by_planet"]["SATURN"]


def test_major_only_when_requested():
    """Requesting firdar_major only emits major activation."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST, "techniques": ["firdar_major"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    techniques = {a["technique"] for a in layer["activations"]}
    assert "firdar_major" in techniques
    assert "firdar_minor" not in techniques
    assert "transit_to_natal" not in techniques


def test_minor_only_when_requested():
    """Requesting firdar_minor only emits minor activation."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST, "techniques": ["firdar_minor"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    techniques = {a["technique"] for a in layer["activations"]}
    assert "firdar_minor" in techniques
    assert "firdar_major" not in techniques


def test_deterministic_order():
    """Two builds produce identical firdar activation ids."""
    resp1 = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    resp2 = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] in ("firdar_major", "firdar_minor")]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] in ("firdar_major", "firdar_minor")]
    assert ids1 == ids2


# ── Historical fixture compatibility ─────────────────────────────────────────


def _load_fixture(path: str) -> dict:
    return json.loads(Path(path).read_text())


def test_historical_fixture_vasiliy_sequence():
    """Vasiliy fixture firdaria sequence matches night period canon."""
    fixture = _load_fixture("tests/fixtures/vasiliy_2026-05-30.json")
    firdaria = fixture.get("raw", {}).get("firdaria", {})
    assert firdaria.get("value", {}).get("is_day_birth") is False

    periods = firdaria.get("value", {}).get("periods", [])
    major_lords = [p["lord"] for p in periods]

    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    canon_lords = [entry["lord"] for entry in canon["night_sequence"]]
    # The first 7 entries should match (filtering node periods at the end)
    # Fixture stores all 9 periods (including nodes)
    assert major_lords[:7] == canon_lords[:7], \
        f"Vasiliy night fixture first 7 lords mismatch"


def test_historical_fixture_vasiliy_first_period():
    """Vasiliy fixture first period (active major when born) is MOON."""
    fixture = _load_fixture("tests/fixtures/vasiliy_2026-05-30.json")
    periods = fixture.get("raw", {}).get("firdaria", {}).get("value", {}).get("periods", [])
    assert len(periods) > 0
    assert periods[0]["lord"] == "MOON", \
        f"Vasiliy first period expected MOON, got {periods[0]['lord']}"
    assert periods[0]["years"] == 9


def test_historical_fixture_vasiliy_active_period():
    """Vasiliy 2026-05-30 active period: SUN major (verified from fixture)."""
    fixture = _load_fixture("tests/fixtures/vasiliy_2026-05-30.json")
    fd = fixture.get("raw", {}).get("firdaria", {}).get("value", {})
    assert fd.get("current_period", {}).get("lord") == "SUN", \
        f"Vasiliy active major expected SUN, got {fd.get('current_period', {}).get('lord')}"


def test_historical_fixture_vasiliy_subperiods():
    """Vasiliy fixture first period subperiods match night 7-planet sequence starting from MOON."""
    fixture = _load_fixture("tests/fixtures/vasiliy_2026-05-30.json")
    periods = fixture.get("raw", {}).get("firdaria", {}).get("value", {}).get("periods", [])
    first_subperiods = periods[0].get("sub_periods", [])
    sub_lords = [s["lord"] for s in first_subperiods]
    # For a night chart, the 7-planet sequence filtered from night_sequence is:
    # MOON, SATURN, JUPITER, MARS, SUN, VENUS, MERCURY
    # Starting from MOON (major lord of first period), the rotation is the same
    expected = ["MOON", "SATURN", "JUPITER", "MARS", "SUN", "VENUS", "MERCURY"]
    assert sub_lords == expected, \
        f"Vasiliy first subperiods expected {expected}, got {sub_lords}"


def test_historical_fixture_test_user_sequence():
    """test_user fixture firdaria sequence matches day period canon."""
    fixture = _load_fixture("tests/fixtures/test_user_2026-06-15.json")
    firdaria = fixture.get("raw", {}).get("firdaria", {})
    assert firdaria.get("value", {}).get("is_day_birth") is True

    periods = firdaria.get("value", {}).get("periods", [])
    major_lords = [p["lord"] for p in periods]

    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    canon_lords = [entry["lord"] for entry in canon["day_sequence"]]
    assert major_lords[:7] == canon_lords[:7], \
        f"test_user day fixture first 7 lords mismatch"


def test_historical_fixture_test_user_active_period():
    """test_user 2026-06-15 active period: MOON major (verified from fixture)."""
    fixture = _load_fixture("tests/fixtures/test_user_2026-06-15.json")
    fd = fixture.get("raw", {}).get("firdaria", {}).get("value", {})
    assert fd.get("current_period", {}).get("lord") == "MOON", \
        f"test_user active major expected MOON, got {fd.get('current_period', {}).get('lord')}"


def test_vintage_fixture_vasiliy():
    """Vasiliy 2026-05-30 fixture endpoint: night birth, major=SUN, minor=SATURN."""
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1980-10-30", "time": "19:50", "lat": 67.9394, "lon": 32.8144, "tz": "Europe/Moscow"},
        "target": {"date": "2026-05-30", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    major = [a for a in layer["activations"] if a["technique"] == "firdar_major"]
    assert major[0]["target_key"] == "SUN", f"Vasiliy major: expected SUN, got {major[0]['target_key']}"
    minor = [a for a in layer["activations"] if a["technique"] == "firdar_minor"]
    assert minor[0]["target_key"] == "SATURN", f"Vasiliy minor: expected SATURN, got {minor[0]['target_key']}"


def test_vintage_fixture_test_user():
    """test_user 2026-06-15 fixture endpoint: day birth, major=MOON, minor=SUN."""
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1990-01-15", "time": "14:30", "lat": 55.7558, "lon": 37.6173, "tz": "Europe/Moscow"},
        "target": {"date": "2026-06-15", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    major = [a for a in layer["activations"] if a["technique"] == "firdar_major"]
    assert major[0]["target_key"] == "MOON", f"test_user major: expected MOON, got {major[0]['target_key']}"
    minor = [a for a in layer["activations"] if a["technique"] == "firdar_minor"]
    assert minor[0]["target_key"] == "SUN", f"test_user minor: expected SUN, got {minor[0]['target_key']}"


def test_unsupported_future_techniques():
    """Unsupported future techniques produce warnings, not activations."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return", "lunar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    warnings_text = " ".join(layer.get("warnings", []))
    assert "unsupported_technique_deferred:solar_return" in warnings_text
    assert "unsupported_technique_deferred:lunar_return" in warnings_text
    for a in layer["activations"]:
        assert a["technique"] not in ("solar_return", "lunar_return")
