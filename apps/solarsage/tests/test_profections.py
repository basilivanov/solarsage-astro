"""Tests for sidecar W3.2 profection activations.

Tests that the sidecar builder produces deterministic annual_profection
and monthly_profection activations with correct golden values for Basil
audit profile."""
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


def test_basil_annual_profection_golden_values():
    """Basil audit profile produces expected annual profection golden values:
    age=45, annual_house=10, lord_of_year=MARS, strength=0.75,
    house_cusp_longitude=0.0, house_cusp_sign=Aries."""
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    activations = layer["activations"]

    # Find annual profection house activation
    ann_house = [a for a in activations if a["id"] == "annual_profection__HOUSE__10"]
    assert len(ann_house) >= 1, "Expected annual_profection house 10"
    ah = ann_house[0]
    assert ah["technique"] == "annual_profection"
    assert ah["technique_family"] == "profection"
    assert ah["target_type"] == "house"
    assert ah["target_key"] == "10"
    assert ah["kind"] == "profected_house"
    assert ah["phase"] == "period"
    assert ah["polarity"] == "neutral"
    assert ah["house"] == 10
    assert ah["strength"] == 0.75
    assert ah["evidence"] == "Annual profection activates house 10"

    # Debug fields
    assert ah["debug"]["age"] == 45
    assert ah["debug"]["house_cusp_longitude"] == 0.0
    assert ah["debug"]["house_cusp_sign"] == "Aries"
    assert ah["debug"]["ruler"] == "MARS"
    assert ah["debug"]["ruler_system"] == "traditional"

    # Find lord of year activation
    ann_lord = [a for a in activations if a["id"] == "annual_profection__LORD_OF_YEAR__MARS"]
    assert len(ann_lord) >= 1, "Expected annual_profection lord MARS"
    al = ann_lord[0]
    assert al["technique"] == "annual_profection"
    assert al["technique_family"] == "profection"
    assert al["target_type"] == "planet"
    assert al["target_key"] == "MARS"
    assert al["kind"] == "lord_of_year"
    assert al["phase"] == "period"
    assert al["strength"] == 0.75
    assert al["target_planet"] == "MARS"
    assert "Mars is lord of year" in al["evidence"]
    assert "house 10" in al["evidence"]
    # Lord debug also includes house_cusp_longitude
    assert al["debug"]["house_cusp_longitude"] == 0.0

    # Index references
    assert "10" in layer.get("by_house", {})
    assert ah["id"] in layer["by_house"]["10"]
    assert "MARS" in layer.get("by_planet", {})
    assert al["id"] in layer["by_planet"]["MARS"]


def test_basil_monthly_profection_golden_values():
    """Basil audit profile produces expected monthly profection golden values:
    completed_month_steps=8, monthly_house=6, lord_of_month=JUPITER, strength=0.45,
    house_cusp_longitude=240.0, house_cusp_sign=Sagittarius."""
    resp = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    activations = layer["activations"]

    # Find monthly profection house activation
    mon_house = [a for a in activations if a["id"] == "monthly_profection__HOUSE__6"]
    assert len(mon_house) >= 1, "Expected monthly_profection house 6"
    mh = mon_house[0]
    assert mh["technique"] == "monthly_profection"
    assert mh["technique_family"] == "profection"
    assert mh["target_type"] == "house"
    assert mh["target_key"] == "6"
    assert mh["kind"] == "monthly_profected_house"
    assert mh["phase"] == "period"
    assert mh["polarity"] == "neutral"
    assert mh["house"] == 6
    assert mh["strength"] == 0.45
    assert mh["evidence"] == "Monthly profection activates house 6"

    # Debug fields
    assert mh["debug"]["completed_month_steps"] == 8
    assert mh["debug"]["age"] == 45
    assert mh["debug"]["house_cusp_longitude"] == 240.0
    assert mh["debug"]["house_cusp_sign"] == "Sagittarius"
    assert mh["debug"]["ruler"] == "JUPITER"

    # Find lord of month activation
    mon_lord = [a for a in activations if a["id"] == "monthly_profection__LORD_OF_MONTH__JUPITER"]
    assert len(mon_lord) >= 1, "Expected monthly_profection lord JUPITER"
    ml = mon_lord[0]
    assert ml["technique"] == "monthly_profection"
    assert ml["technique_family"] == "profection"
    assert ml["target_type"] == "planet"
    assert ml["target_key"] == "JUPITER"
    assert ml["kind"] == "lord_of_month"
    assert ml["phase"] == "period"
    assert ml["strength"] == 0.45
    assert ml["target_planet"] == "JUPITER"
    assert "Jupiter is lord of month" in ml["evidence"]
    assert "house 6" in ml["evidence"]
    # Lord debug also includes house_cusp_longitude
    assert ml["debug"]["house_cusp_longitude"] == 240.0

    # Index references
    assert "6" in layer.get("by_house", {})
    assert mh["id"] in layer["by_house"]["6"]
    assert "JUPITER" in layer.get("by_planet", {})
    assert ml["id"] in layer["by_planet"]["JUPITER"]


def test_birthday_boundary_age_45_house_10():
    """On 2026-10-29 (day before birthday), age=45, house=10 still."""
    req = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-10-29", "time": "12:00", "tz": "Europe/Moscow"}}
    resp = client.post("/v1/activation-layer", json=req)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ann_houses = [a for a in layer["activations"] if a["technique"] == "annual_profection" and a["target_type"] == "house"]
    assert len(ann_houses) >= 1
    assert ann_houses[0]["debug"]["age"] == 45
    assert ann_houses[0]["debug"]["house"] == 10


def test_birthday_boundary_age_46_house_11():
    """On 2026-10-30 (birthday), age=46, house=11."""
    req = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-10-30", "time": "12:00", "tz": "Europe/Moscow"}}
    resp = client.post("/v1/activation-layer", json=req)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    ann_houses = [a for a in layer["activations"] if a["technique"] == "annual_profection" and a["target_type"] == "house"]
    assert len(ann_houses) >= 1
    assert ann_houses[0]["debug"]["age"] == 46, f"Expected age 46 for birthday, got {ann_houses[0]['debug']['age']}"
    assert ann_houses[0]["debug"]["house"] == 11


def test_monthly_drift_non_drifting_anniversaries():
    """Monthly anniversaries are counted from annual_year_start without drift.
    With annual_year_start=2025-10-30:
      target 2026-03-29 => step 4 (Mar 30 not yet reached)
      target 2026-03-30 => step 5 (Mar 30 is exactly the 5th anniversary)
      target 2026-07-29 => step 8 (Jun 30 is the 8th, Jul 30 not yet)
      target 2026-07-30 => step 9 (Jul 30 is exactly the 9th)"""
    cases = [
        ("2026-03-29", 4, 2),
        ("2026-03-30", 5, 3),
        ("2026-07-29", 8, 6),
        ("2026-07-30", 9, 7),
    ]
    for target_date, expected_steps, expected_house in cases:
        req = {**BASIL_AUDIT_REQUEST, "target": {"date": target_date, "time": "12:00", "tz": "Europe/Moscow"}}
        resp = client.post("/v1/activation-layer", json=req)
        assert resp.status_code == 200, f"Failed for {target_date}"
        layer = resp.json()["activation_layer"]
        mon_houses = [a for a in layer["activations"]
                      if a["technique"] == "monthly_profection" and a["target_type"] == "house"]
        assert len(mon_houses) >= 1, f"No monthly house for {target_date}"
        assert mon_houses[0]["debug"]["completed_month_steps"] == expected_steps, \
            f"{target_date}: expected steps={expected_steps}, got {mon_houses[0]['debug']['completed_month_steps']}"
        assert mon_houses[0]["debug"]["house"] == expected_house, \
            f"{target_date}: expected house={expected_house}, got {mon_houses[0]['debug']['house']}"


def test_monthly_boundary_before_month_anniversary():
    """Monthly boundary: 2026-05-29 is before the 7th monthly anniversary at 2026-05-30,
    so completed_month_steps should be 6, monthly_house=4."""
    req = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-05-29", "time": "12:00", "tz": "Europe/Moscow"}}
    resp = client.post("/v1/activation-layer", json=req)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    mon_houses = [a for a in layer["activations"] if a["technique"] == "monthly_profection" and a["target_type"] == "house"]
    assert len(mon_houses) >= 1
    assert mon_houses[0]["debug"]["completed_month_steps"] == 6, \
        f"Expected 6 month steps on May 29, got {mon_houses[0]['debug']['completed_month_steps']}"


def test_monthly_boundary_after_month_anniversary():
    """Monthly boundary: 2026-06-30 is after the 8th monthly anniversary (exact match),
    so completed_month_steps=8, monthly_house=6."""
    req = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-06-30", "time": "12:00", "tz": "Europe/Moscow"}}
    resp = client.post("/v1/activation-layer", json=req)
    assert resp.status_code == 200
    layer = resp.json()["activation_layer"]
    mon_houses = [a for a in layer["activations"] if a["technique"] == "monthly_profection" and a["target_type"] == "house"]
    assert len(mon_houses) >= 1
    assert mon_houses[0]["debug"]["completed_month_steps"] == 8, \
        f"Expected 8 month steps on Jun 30, got {mon_houses[0]['debug']['completed_month_steps']}"


def test_sign_ruler_mapping():
    """Traditional sign ruler mapping produces correct rulers."""
    from solarsage.services.activation_builder import _ruler_of_sign

    assert _ruler_of_sign("Aries") == "MARS"
    assert _ruler_of_sign("Taurus") == "VENUS"
    assert _ruler_of_sign("Gemini") == "MERCURY"
    assert _ruler_of_sign("Cancer") == "MOON"
    assert _ruler_of_sign("Leo") == "SUN"
    assert _ruler_of_sign("Virgo") == "MERCURY"
    assert _ruler_of_sign("Libra") == "VENUS"
    assert _ruler_of_sign("Scorpio") == "MARS"
    assert _ruler_of_sign("Sagittarius") == "JUPITER"
    assert _ruler_of_sign("Capricorn") == "SATURN"
    assert _ruler_of_sign("Aquarius") == "SATURN"
    assert _ruler_of_sign("Pisces") == "JUPITER"


def test_unknown_sign_raises():
    """Unknown sign raises ValueError, not silent Saturn fallback."""
    from solarsage.services.activation_builder import _ruler_of_sign
    with pytest.raises(ValueError, match="Unknown sign"):
        _ruler_of_sign("NotASign")


def test_deterministic_activation_order():
    """Two builds produce identical profection activations."""
    resp1 = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    resp2 = client.post("/v1/activation-layer", json=BASIL_AUDIT_REQUEST)
    ids1 = [a["id"] for a in resp1.json()["activation_layer"]["activations"]
            if a["technique"] in ("annual_profection", "monthly_profection")]
    ids2 = [a["id"] for a in resp2.json()["activation_layer"]["activations"]
            if a["technique"] in ("annual_profection", "monthly_profection")]
    assert ids1 == ids2, "Profection activation order must be deterministic"


def test_timezone_boundary_local_date():
    """Target date is treated as the local date for profection boundaries,
    independent of host timezone. Two requests with the same local date
    but different timezones produce same profection results."""
    # Same local date Oct 29 (age 45) in different timezones
    req_east = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-10-29", "time": "23:30", "tz": "Pacific/Kiritimati"}}
    req_west = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-10-29", "time": "00:30", "tz": "America/Anchorage"}}
    resp_east = client.post("/v1/activation-layer", json=req_east)
    resp_west = client.post("/v1/activation-layer", json=req_west)
    assert resp_east.status_code == 200
    assert resp_west.status_code == 200
    ann_east = [a for a in resp_east.json()["activation_layer"]["activations"]
                if a["technique"] == "annual_profection" and a["target_type"] == "house"]
    ann_west = [a for a in resp_west.json()["activation_layer"]["activations"]
                if a["technique"] == "annual_profection" and a["target_type"] == "house"]
    assert ann_east[0]["debug"]["age"] == 45
    assert ann_west[0]["debug"]["age"] == 45
    assert ann_east[0]["debug"]["house"] == 10
    assert ann_west[0]["debug"]["house"] == 10

    # Next day Oct 30 (birthday, age 46) in different timezones
    req_east_bday = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-10-30", "time": "00:30", "tz": "Pacific/Kiritimati"}}
    req_west_bday = {**BASIL_AUDIT_REQUEST, "target": {"date": "2026-10-30", "time": "23:30", "tz": "America/Anchorage"}}
    resp_east_bday = client.post("/v1/activation-layer", json=req_east_bday)
    resp_west_bday = client.post("/v1/activation-layer", json=req_west_bday)
    assert resp_east_bday.status_code == 200
    assert resp_west_bday.status_code == 200
    ann_east_bday = [a for a in resp_east_bday.json()["activation_layer"]["activations"]
                     if a["technique"] == "annual_profection" and a["target_type"] == "house"]
    ann_west_bday = [a for a in resp_west_bday.json()["activation_layer"]["activations"]
                     if a["technique"] == "annual_profection" and a["target_type"] == "house"]
    assert ann_east_bday[0]["debug"]["age"] == 46, f"East Kiritimati birthday: {ann_east_bday[0]['debug']}"
    assert ann_west_bday[0]["debug"]["age"] == 46, f"West Anchorage birthday: {ann_west_bday[0]['debug']}"
    assert ann_east_bday[0]["debug"]["house"] == 11
    assert ann_west_bday[0]["debug"]["house"] == 11
