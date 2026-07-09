"""Tests for sidecar W3.3 firdar activations.

Tests canon loading, Basil golden values, day/night fixture compatibility,
exact boundary behavior, and technique filtering."""
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


# ── Boundary ─────────────────────────────────────────────────────────────────


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


def test_vintage_fixture_vasiliy():
    """Vasiliy 2026-05-30 fixture: night birth, major=SUN, minor=SATURN."""
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
    """test_user 2026-06-15 fixture: day birth, major=MOON, minor=SUN."""
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
