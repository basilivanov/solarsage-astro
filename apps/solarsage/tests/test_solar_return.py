"""Tests for sidecar W3.4 solar return activations."""
import pytest
from datetime import datetime, timezone, timedelta
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


def _parse_utc_z(value: str) -> datetime:
    assert value.endswith("Z")
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(timezone.utc)


def test_solar_return_service_precision():
    """Solar return longitude residual <= 0.001°."""
    from solarsage.services.returns import calculate_solar_return
    sr = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    residual = abs(sr.return_sun_lon - sr.natal_sun_lon) % 360.0
    if residual > 180.0:
        residual = 360.0 - residual
    assert residual <= 0.001, f"Solar return longitude residual {residual} > 0.001°"


def test_solar_return_basil_jd():
    """Basil 2026 solar return JD matches historical fixture within tolerance."""
    from solarsage.services.returns import calculate_solar_return
    sr = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    expected_jd = 2461344.3452186584
    assert abs(sr.return_jd - expected_jd) < 0.001, \
        f"SR JD {sr.return_jd} differs from expected {expected_jd}"


def test_solar_return_timestamp_stable():
    """Solar return UTC timestamp is stable across calls."""
    from solarsage.services.returns import calculate_solar_return
    sr1 = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    sr2 = calculate_solar_return(
        birth_date="1980-10-30", birth_time="19:50", birth_tz="Europe/Moscow",
        birth_lat=67.9394, birth_lon=32.8144,
        target_year=2026, house_system="PLACIDUS",
    )
    assert sr1.return_utc_iso == sr2.return_utc_iso


def test_solar_return_endpoint_activations():
    """Solar return endpoint returns expected activations for Basil."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    assert len(sr_acts) >= 3, f"Expected at least 3 solar return activations, got {len(sr_acts)}"

    # Check kinds
    kinds = {a["kind"] for a in sr_acts}
    assert "return_angle_in_natal_house" in kinds
    assert "return_chart_ruler" in kinds

    # IDs stable
    ids = [a["id"] for a in sr_acts]
    for aid in ids:
        assert aid.startswith("solar_return__"), f"Unexpected ID: {aid}"
    timings = {(a["active_from"], a["exact_at"], a["active_until"]) for a in sr_acts}
    assert len(timings) == 1
    active_from, exact_at, active_until = timings.pop()
    assert active_from == exact_at
    assert _parse_utc_z(active_from) <= _parse_utc_z("2026-07-08T09:00:00Z") < _parse_utc_z(sr_acts[0]["debug"]["next_return_utc_iso"])
    assert _parse_utc_z(active_until) == _parse_utc_z(sr_acts[0]["debug"]["next_return_utc_iso"]) - timedelta(seconds=1)


def test_solar_return_debug_fields():
    """Solar return activations include all required debug fields."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    for a in sr_acts:
        d = a.get("debug", {})
        assert d.get("return_type") == "solar"
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
        assert d.get("next_return_jd", 0) > d.get("return_jd", 0)
        assert d.get("next_return_utc_iso", "").endswith("Z")
        assert d.get("active_until_utc") == a["active_until"]


def test_solar_return_indexes():
    """Every solar return activation is referenced in appropriate index."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    valid_ids = {a["id"] for a in sr_acts}

    # Every SR activation must have its ID in the appropriate index
    for a in sr_acts:
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


def test_solar_return_location_source():
    """Solar return with explicit current_location changes location_source
    and actually changes return chart houses/ASC/MC."""
    # Baseline with birth location
    base_resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    base_ids = [a["id"] for a in base_resp.json()["activation_layer"]["activations"]
                if a["technique"] == "solar_return"]

    # Relocated to equator
    reloc_resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
        "current_location": {"lat": 0.0, "lon": 0.0, "tz": "UTC"},
    })
    assert reloc_resp.status_code == 200
    layer = reloc_resp.json()["activation_layer"]
    sr_acts = [a for a in layer["activations"] if a["technique"] == "solar_return"]
    for a in sr_acts:
        assert a["debug"]["return_location_source"] == "current_location"

    # Activation IDs must differ (chart changed with location)
    reloc_ids = [a["id"] for a in reloc_resp.json()["activation_layer"]["activations"]
                  if a["technique"] == "solar_return"]
    assert base_ids != reloc_ids, "Relocated solar return must produce different activation IDs"

    # Resolved house system for equator should be PLACIDUS (low latitude)
    for a in sr_acts:
        assert a["debug"]["resolved_house_system"] == "PLACIDUS", \
            f"Expected PLACIDUS for equator, got {a['debug']['resolved_house_system']}"


def test_solar_return_no_fallback_warning_with_current_location():
    """When current_location supplied, no fallback warning emitted."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
        "current_location": {"lat": 43.5, "lon": 39.5, "tz": "Europe/Moscow"},
    })
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    # No fallback warning should appear
    for w in layer.get("warnings", []):
        assert "return_location_fallback" not in w, f"Unexpected fallback warning: {w}"


def test_solar_return_only_when_requested():
    """Only solar_return emitted when specifically requested."""
    resp = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    assert resp.status_code == 200
    techniques = {a["technique"] for a in resp.json()["activation_layer"]["activations"]}
    assert "solar_return" in techniques
    assert "lunar_return" not in techniques
    assert "firdar_major" not in techniques


def test_solar_return_deterministic():
    """Two builds produce identical solar return activation ids."""
    resp1 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    resp2 = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "techniques": ["solar_return"],
    })
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] == "solar_return"]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] == "solar_return"]
    assert ids1 == ids2


def test_solar_return_current_previous_before_birthday_and_same_year_after():
    from solarsage.utils.ephemeris import calculate_julian_day

    before = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "target": {"date": "2026-07-08", "time": "12:00", "tz": "Europe/Moscow"},
        "techniques": ["solar_return"],
    })
    after = client.post("/v1/activation-layer", json={
        **BASIL_AUDIT_REQUEST,
        "target": {"date": "2026-11-01", "time": "12:00", "tz": "Europe/Moscow"},
        "techniques": ["solar_return"],
    })
    assert before.status_code == 200
    assert after.status_code == 200
    before_act = next(a for a in before.json()["activation_layer"]["activations"] if a["technique"] == "solar_return")
    after_act = next(a for a in after.json()["activation_layer"]["activations"] if a["technique"] == "solar_return")
    assert before_act["active_from"] == "2025-10-30T14:24:27Z"
    assert before_act["exact_at"] == "2025-10-30T14:24:27Z"
    assert before_act["debug"]["next_return_utc_iso"] == "2026-10-30T20:17:07Z"
    assert before_act["active_until"] == "2026-10-30T20:17:06Z"
    before_target_jd = calculate_julian_day("2026-07-08", "12:00", "Europe/Moscow")
    assert before_act["debug"]["return_jd"] <= before_target_jd < before_act["debug"]["next_return_jd"]

    assert after_act["active_from"] == "2026-10-30T20:17:07Z"
    assert after_act["exact_at"] == "2026-10-30T20:17:07Z"
    assert after_act["debug"]["next_return_utc_iso"] == "2027-10-31T02:04:52Z"
    assert after_act["active_until"] == "2027-10-31T02:04:51Z"
    after_target_jd = calculate_julian_day("2026-11-01", "12:00", "Europe/Moscow")
    assert after_act["debug"]["return_jd"] <= after_target_jd < after_act["debug"]["next_return_jd"]


def test_feb29_solar_return_current_next_pair_matches_helpers(monkeypatch):
    from solarsage.services import returns as returns_module
    from solarsage.services.returns import find_solar_return_jd
    from solarsage.utils.ephemeris import calculate_julian_day, calculate_positions

    calls = {"positions": 0, "houses": 0}
    original_positions = returns_module.calculate_positions
    original_houses = returns_module.calculate_houses_cusps

    def spy_positions(*args, **kwargs):
        calls["positions"] += 1
        return original_positions(*args, **kwargs)

    def spy_houses(*args, **kwargs):
        calls["houses"] += 1
        return original_houses(*args, **kwargs)

    monkeypatch.setattr(returns_module, "calculate_positions", spy_positions)
    monkeypatch.setattr(returns_module, "calculate_houses_cusps", spy_houses)

    req = {
        "birth": {"date": "2000-02-29", "time": "12:00", "lat": 55.7558, "lon": 37.6173, "tz": "Europe/Moscow"},
        "target": {"date": "2026-03-01", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["solar_return"],
    }
    resp = client.post("/v1/activation-layer", json=req)
    assert resp.status_code == 200
    act = next(a for a in resp.json()["activation_layer"]["activations"] if a["technique"] == "solar_return")
    assert act["active_from"].endswith("Z")
    assert act["exact_at"] == act["active_from"]
    assert act["active_until"].endswith("Z")

    target_jd = calculate_julian_day("2026-03-01", "12:00", "Europe/Moscow")
    natal_jd = calculate_julian_day("2000-02-29", "12:00", "Europe/Moscow")
    natal_sun_lon = next(p["longitude"] for p in calculate_positions(natal_jd) if p["name"] == "Sun")
    candidate_2026 = find_solar_return_jd(
        natal_sun_longitude=natal_sun_lon,
        birth_month=2,
        birth_day=29,
        target_year=2026,
    )
    current_year = 2025 if candidate_2026 > target_jd else 2026
    expected_current = find_solar_return_jd(
        natal_sun_longitude=natal_sun_lon,
        birth_month=2,
        birth_day=29,
        target_year=current_year,
    )
    expected_next = find_solar_return_jd(
        natal_sun_longitude=natal_sun_lon,
        birth_month=2,
        birth_day=29,
        target_year=current_year + 1,
    )
    assert abs(act["debug"]["return_jd"] - round(expected_current, 8)) < 1e-7
    assert abs(act["debug"]["next_return_jd"] - round(expected_next, 8)) < 1e-7
    assert expected_current <= target_jd < expected_next
    assert calls["positions"] == 1
    assert calls["houses"] == 1


def test_solar_return_builder_rejects_false_current_next_window(monkeypatch):
    from solarsage.services import activation_builder as ab
    from solarsage.utils.ephemeris import calculate_julian_day

    target_jd = calculate_julian_day("2026-11-01", "12:00", "Europe/Moscow")

    def fake_find_solar_return_jd(*, natal_sun_longitude, birth_month, birth_day, target_year):
        if target_year == 2026:
            return target_jd - 1.0
        if target_year == 2027:
            return target_jd
        raise AssertionError(f"unexpected target_year {target_year}")

    monkeypatch.setattr(ab, "find_solar_return_jd", fake_find_solar_return_jd)
    with pytest.raises(ValueError, match="Solar return window invariant violated"):
        ab.build_activation_layer(
            birth_date="1980-10-30", birth_time="19:50", birth_lat=67.9394, birth_lon=32.8144,
            birth_tz="Europe/Moscow", target_date="2026-11-01", target_time="12:00",
            target_tz="Europe/Moscow", house_system="PLACIDUS", techniques=["solar_return"],
        )


def test_solar_next_boundary_helper_avoids_second_full_chart(monkeypatch):
    from solarsage.services import returns as returns_module
    calls = {"positions": 0, "houses": 0}
    original_positions = returns_module.calculate_positions
    original_houses = returns_module.calculate_houses_cusps

    def spy_positions(*args, **kwargs):
        calls["positions"] += 1
        return original_positions(*args, **kwargs)

    def spy_houses(*args, **kwargs):
        calls["houses"] += 1
        return original_houses(*args, **kwargs)

    monkeypatch.setattr(returns_module, "calculate_positions", spy_positions)
    monkeypatch.setattr(returns_module, "calculate_houses_cusps", spy_houses)
    resp = client.post("/v1/activation-layer", json={**BASIL_AUDIT_REQUEST, "techniques": ["solar_return"]})
    assert resp.status_code == 200
    assert calls["positions"] == 1  # one current return chart, no natal/next full chart
    assert calls["houses"] == 1  # one current return chart, no next full chart


# ── Strength strictness ─────────────────────────────────────────────────


def test_strength_missing_solar_return_key():
    """Missing solar_return_angle_in_natal_house raises KeyError."""
    from solarsage.services.activation_builder import _get_return_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    period_base = rules.get("activation_strength", {}).get("return_base", {})
    del period_base["solar_return_angle_in_natal_house"]
    with pytest.raises(KeyError, match="solar_return_angle_in_natal_house"):
        _get_return_strength(rules, "solar_return_angle_in_natal_house")


def test_strength_missing_lunar_return_key():
    """Missing lunar_return_moon_house raises KeyError."""
    from solarsage.services.activation_builder import _get_return_strength
    from solarsage.services.activation_builder import _load_activation_rules
    rules = _load_activation_rules()
    period_base = rules.get("activation_strength", {}).get("return_base", {})
    del period_base["lunar_return_moon_house"]
    with pytest.raises(KeyError, match="lunar_return_moon_house"):
        _get_return_strength(rules, "lunar_return_moon_house")
