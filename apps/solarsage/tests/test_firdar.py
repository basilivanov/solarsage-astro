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


# ── Canon validation ────────────────────────────────────────────────────────


def test_canon_validation_zero_minor_divisions():
    """minor_divisions = 0 raises ValueError through calculate_firdar(canon=bad)."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    import copy
    bad = copy.deepcopy(canon)
    bad["minor_divisions"] = 0
    with pytest.raises(ValueError, match="minor_divisions"):
        calculate_firdar(
            birth_local=date(1990, 1, 1),
            target_local=date(2000, 1, 1),
            is_day_birth=True,
            sun_house=9,
            canon=bad,
        )


def test_canon_validation_day_sequence_sum_mismatch():
    """Day sequence sum mismatch raises ValueError through calculate_firdar(canon=bad)."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    import copy
    bad = copy.deepcopy(canon)
    bad["day_sequence"] = [{"lord": "SUN", "years": 10}]  # sum=10, cycle=75
    with pytest.raises(ValueError, match="cycle_years"):
        calculate_firdar(
            birth_local=date(1990, 1, 1),
            target_local=date(2000, 1, 1),
            is_day_birth=True,
            sun_house=9,
            canon=bad,
        )


def test_canon_validation_night_sequence_sum_mismatch():
    """Night sequence sum mismatch raises ValueError through calculate_firdar(canon=bad)."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    import copy
    bad = copy.deepcopy(canon)
    bad["night_sequence"] = [{"lord": "MOON", "years": 9}]  # sum=9, cycle=75
    with pytest.raises(ValueError, match="cycle_years"):
        calculate_firdar(
            birth_local=date(1980, 10, 30),
            target_local=date(2026, 7, 8),
            is_day_birth=False,
            sun_house=5,
            canon=bad,
        )


def test_canon_validation_node_sequence_length():
    """node_minor_sequence length mismatch raises ValueError through calculate_firdar(canon=bad)."""
    from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
    from datetime import date
    canon = _load_firdar_canon()
    import copy
    bad = copy.deepcopy(canon)
    bad["node_minor_sequence"] = bad["node_minor_sequence"][:3]  # 3 != 7
    with pytest.raises(ValueError, match="minor_divisions"):
        calculate_firdar(
            birth_local=date(1990, 1, 1),
            target_local=date(2000, 1, 1),
            is_day_birth=True,
            sun_house=9,
            canon=bad,
        )


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


def test_strength_missing_firdar_major_key():
    """Missing period_strength.firdar_major raises KeyError."""
    from solarsage.services.activation_builder import _get_period_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    # Remove firdar_major from period_base
    period_base = rules.get("activation_strength", {}).get("period_base", {})
    del period_base["firdar_major"]
    with pytest.raises(KeyError, match="firdar_major"):
        _get_period_strength(rules, "firdar_major")


def test_strength_missing_firdar_minor_key():
    """Missing period_strength.firdar_minor raises KeyError."""
    from solarsage.services.activation_builder import _get_period_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    period_base = rules.get("activation_strength", {}).get("period_base", {})
    del period_base["firdar_minor"]
    with pytest.raises(KeyError, match="firdar_minor"):
        _get_period_strength(rules, "firdar_minor")


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


def _night_7_planets():
    """Night 7-planet sequence filtered from canon night_sequence."""
    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    return [entry["lord"] for entry in canon["night_sequence"]
            if entry["lord"] not in ("NORTH_NODE_TRUE", "SOUTH_NODE")]


def _day_7_planets():
    """Day 7-planet sequence filtered from canon day_sequence."""
    from solarsage.services.firdar import _load_firdar_canon
    canon = _load_firdar_canon()
    return [entry["lord"] for entry in canon["day_sequence"]
            if entry["lord"] not in ("NORTH_NODE_TRUE", "SOUTH_NODE")]


def _compare_fixture_periods(fixture_path: str, canon_sequence_key: str, tol: float = 1e-10):
    """Compare all fixture periods against canon sequence: lords, years,
    start/end ages, and all subperiod rotations."""
    from solarsage.services.firdar import _load_firdar_canon
    fixture = _load_fixture(fixture_path)
    periods = fixture.get("raw", {}).get("firdaria", {}).get("value", {}).get("periods", [])
    canon = _load_firdar_canon()
    canon_seq = canon[canon_sequence_key]

    assert len(periods) == len(canon_seq), \
        f"Period count mismatch: fixture={len(periods)} canon={len(canon_seq)}"

    all_7_planets = _day_7_planets() if "day" in canon_sequence_key else _night_7_planets()
    node_minor = canon["node_minor_sequence"]
    total_years = 0.0

    for i, (fp, cp) in enumerate(zip(periods, canon_seq)):
        lord = cp["lord"]
        years = float(cp["years"])

        # Lord
        assert fp["lord"] == lord, f"Period {i}: expected lord {lord}, got {fp['lord']}"
        # Years
        assert abs(fp["years"] - years) < tol, \
            f"Period {i} {lord}: expected years {years}, got {fp['years']}"
        # Start age
        assert abs(fp["start_age"] - total_years) < tol, \
            f"Period {i} {lord}: expected start_age {total_years}, got {fp['start_age']}"
        # End age
        assert abs(fp["end_age"] - (total_years + years)) < tol, \
            f"Period {i} {lord}: expected end_age {total_years + years}, got {fp['end_age']}"

        # Subperiod rotation
        if lord in ("NORTH_NODE_TRUE", "SOUTH_NODE"):
            expected_sub = node_minor
        else:
            idx = all_7_planets.index(lord)
            expected_sub = all_7_planets[idx:] + all_7_planets[:idx]

        sub_lords = [s["lord"] for s in fp.get("sub_periods", [])]
        assert sub_lords == expected_sub, \
            f"Period {i} {lord}: subperiod lords {sub_lords} != expected {expected_sub}"
        assert len(fp["sub_periods"]) == 7, \
            f"Period {i} {lord}: expected 7 subperiods, got {len(fp['sub_periods'])}"

        total_years += years

    assert abs(total_years - float(canon["cycle_years"])) < tol, \
        f"Total years {total_years} != cycle_years {canon['cycle_years']}"


def test_historical_fixture_vasiliy_is_day():
    """Vasiliy fixture: is_day_birth=False (night)."""
    fixture = _load_fixture("tests/fixtures/vasiliy_2026-05-30.json")
    assert fixture.get("raw", {}).get("firdaria", {}).get("value", {}).get("is_day_birth") is False


def test_historical_fixture_vasiliy_full_periods():
    """Vasiliy fixture: all night sequence periods compared (lords, years, ages, subperiods)."""
    _compare_fixture_periods("tests/fixtures/vasiliy_2026-05-30.json", "night_sequence")


def test_historical_fixture_vasiliy_active_major():
    """Vasiliy 2026-05-30 active period: SUN major (verified from fixture)."""
    fixture = _load_fixture("tests/fixtures/vasiliy_2026-05-30.json")
    fd = fixture.get("raw", {}).get("firdaria", {}).get("value", {})
    assert fd.get("current_period", {}).get("lord") == "SUN", \
        f"Vasiliy active major expected SUN, got {fd.get('current_period', {}).get('lord')}"


def test_historical_fixture_test_user_is_day():
    """test_user fixture: is_day_birth=True (day)."""
    fixture = _load_fixture("tests/fixtures/test_user_2026-06-15.json")
    assert fixture.get("raw", {}).get("firdaria", {}).get("value", {}).get("is_day_birth") is True


def test_historical_fixture_test_user_full_periods():
    """test_user fixture: all day sequence periods compared (lords, years, ages, subperiods)."""
    _compare_fixture_periods("tests/fixtures/test_user_2026-06-15.json", "day_sequence")


def test_historical_fixture_test_user_active_major():
    """test_user 2026-06-15 active period: MOON major (verified from fixture).
    NOTE: The fixture's current_sub_period = MARS was computed with integer age 36
    by the legacy collector. The W3.3 date-precise calculation gives minor = SUN for
    age_years ~= 36.4137. The fixture period table itself correctly shows the SUN
    subperiod at the date-precise position (ages 36.143-37.429). The active minor
    is verified from the period table, NOT from the legacy current_sub_period field."""
    fixture = _load_fixture("tests/fixtures/test_user_2026-06-15.json")
    fd = fixture.get("raw", {}).get("firdaria", {}).get("value", {})
    assert fd.get("current_period", {}).get("lord") == "MOON", \
        f"test_user active major expected MOON, got {fd.get('current_period', {}).get('lord')}"

    # Verify from the period table itself: age 36.4137 falls in SUN subperiod (ages 36.143-37.429)
    moon_period = [p for p in fd.get("periods", []) if p["lord"] == "MOON"][0]
    sun_sub = [s for s in moon_period["sub_periods"] if s["lord"] == "SUN"]
    assert len(sun_sub) == 1
    assert sun_sub[0]["start_age"] <= 36.4137 <= sun_sub[0]["end_age"], \
        f"SUN subperiod {sun_sub[0]} should contain age 36.4137"


# ── Strong node endpoint assertions ─────────────────────────────────────────


def test_node_north_node_true_exact():
    """Date at exact age 70.0: NORTH_NODE_TRUE major, stable id, readable evidence."""
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1990-01-01", "time": "12:00", "lat": 55.0, "lon": 37.0, "tz": "Europe/Moscow"},
        "target": {"date": "2060-01-01", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]

    major = [a for a in layer["activations"] if a["id"] == "firdar_major__PERIOD_LORD__NORTH_NODE_TRUE"]
    assert len(major) == 1, "Expected firdar_major__PERIOD_LORD__NORTH_NODE_TRUE"
    m = major[0]
    assert m["target_key"] == "NORTH_NODE_TRUE"
    assert m["target_planet"] == "NORTH_NODE_TRUE"
    assert m["evidence"].startswith("North Node is major firdar lord")
    assert "NORTH_NODE_TRUE" not in m["evidence"]
    assert "NORTH_NODE_TRUE" in layer.get("by_planet", {})
    assert m["id"] in layer["by_planet"]["NORTH_NODE_TRUE"]

    minor = [a for a in layer["activations"] if a["id"] == "firdar_minor__SUBPERIOD_LORD__SATURN"]
    assert len(minor) == 1, "Expected firdar_minor__SUBPERIOD_LORD__SATURN"
    mi = minor[0]
    assert mi["target_key"] == "SATURN"
    assert mi["evidence"].startswith("Saturn is minor firdar lord")


def test_node_south_node_exact():
    """Date at exact age 73.0: SOUTH_NODE major, stable id, readable evidence."""
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1990-01-01", "time": "12:00", "lat": 55.0, "lon": 37.0, "tz": "Europe/Moscow"},
        "target": {"date": "2063-01-01", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]

    major = [a for a in layer["activations"] if a["id"] == "firdar_major__PERIOD_LORD__SOUTH_NODE"]
    assert len(major) == 1, "Expected firdar_major__PERIOD_LORD__SOUTH_NODE"
    m = major[0]
    assert m["target_key"] == "SOUTH_NODE"
    assert m["target_planet"] == "SOUTH_NODE"
    assert m["evidence"].startswith("South Node is major firdar lord")
    assert "SOUTH_NODE" in layer.get("by_planet", {})
    assert m["id"] in layer["by_planet"]["SOUTH_NODE"]

    minor = [a for a in layer["activations"] if a["id"] == "firdar_minor__SUBPERIOD_LORD__SATURN"]
    assert len(minor) == 1, "Expected firdar_minor__SUBPERIOD_LORD__SATURN (node minor starts with SATURN)"
    assert minor[0]["target_key"] == "SATURN"


# ── Single activation-rules load test ───────────────────────────────────────


def test_activation_rules_loaded_once_firdar(monkeypatch):
    """When only firdar_major and firdar_minor requested, activation rules are
    loaded exactly once."""
    from solarsage.services import activation_builder as ab
    original_load = ab._load_activation_rules
    load_count = 0

    def spy():
        nonlocal load_count
        load_count += 1
        return original_load()

    monkeypatch.setattr(ab, "_load_activation_rules", spy)

    # Single focused request with only firdar techniques
    resp = client.post("/v1/activation-layer", json={
        "birth": {"date": "1980-10-30", "time": "19:50", "lat": 67.9394, "lon": 32.8144, "tz": "Europe/Moscow"},
        "target": {"date": "2026-07-08", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["firdar_major", "firdar_minor"],
    })
    assert resp.status_code == 200
    assert load_count == 1, f"Expected exactly 1 activation-rules load, got {load_count}"


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
        "techniques": ["eclipse_window"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    warnings_text = " ".join(layer.get("warnings", []))
    assert "unsupported_technique_deferred:eclipse_window" in warnings_text
    for a in layer["activations"]:
        assert a["technique"] not in ("eclipse_window",)
