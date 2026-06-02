# AI_HEADER
# module: M-TEST-TODAY-IMPORTANT
# wave: W-PHASE-3
# purpose: Tests for TodayImportantService — whitelist-only events, window logic, dedup

from datetime import date

import pytest

from app.schemas.normalization import AstroSignal
from app.schemas.today import ImportantTodayItem, ImportantTodayDetails
from app.services.today_important_service import TodayImportantService


def _make_transits(planets_data):
    return {"planets": planets_data}


def _make_scoring(day_status="steady", top_signals=None, sphere_scores=None):
    return {
        "day_status": day_status,
        "top_signals": top_signals or [],
        "sphere_scores": sphere_scores or {},
    }


def _transit_planet(name, longitude, speed=0.5, extra=None):
    d = {"name": name, "longitude": longitude, "speed": speed}
    if extra:
        d.update(extra)
    return d


# ── Outer planet retrogrades are NOT rendered ──────────────────────

def test_outer_planet_retrogrades_are_not_rendered():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
        _transit_planet("Neptune", 350.0, speed=-0.01),
        _transit_planet("Pluto", 290.0, speed=-0.02),
        _transit_planet("Uranus", 50.0, speed=-0.01),
        _transit_planet("Saturn", 30.0, speed=-0.005),
        _transit_planet("Jupiter", 120.0, speed=-0.03),
    ])
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[],
        scoring_result=_make_scoring(),
    )
    retro_items = [it for it in items if it.type == "mercury_retrograde"]
    assert len(retro_items) == 0
    station_items = [it for it in items if it.type == "mercury_station"]
    assert len(station_items) == 0


def test_only_mercury_retrograde_is_allowed():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
        _transit_planet("Mercury", 150.0, speed=-0.3),
    ])
    # Add Moon aspect to prevent VOC
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Sun", aspect_type="trine", orb=2, strength=0.5)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[msig],
        scoring_result=_make_scoring(),
    )
    retro = [it for it in items if it.type == "mercury_retrograde"]
    assert len(retro) == 1
    assert retro[0].planet == "Меркурий"


def test_mercury_station_suppresses_mercury_retrograde():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
        _transit_planet("Mercury", 150.0, speed=-0.01),  # retrograde AND station
    ])
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Sun", aspect_type="trine", orb=2, strength=0.5)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[msig],
        scoring_result=_make_scoring(),
    )
    stations = [it for it in items if it.type == "mercury_station"]
    retros = [it for it in items if it.type == "mercury_retrograde"]
    assert len(stations) == 1
    assert len(retros) == 0  # Station suppresses retrograde


# ── Lunation window (±3 days) ───────────────────────────────────

def test_new_moon_window_three_days_before_and_after():
    svc = TodayImportantService()
    for offset, expected in [(-3, True), (-1, True), (0, True), (1, True), (3, True), (5, False)]:
        moon_lon = 120.0 + offset * 12
        transits = _make_transits([
            _transit_planet("Sun", 120.0),
            _transit_planet("Moon", moon_lon),
        ])
        items = svc.build_items(
            target_date=date.today(),
            timezone="UTC", natal={}, transits=transits, signals=[],
            scoring_result=_make_scoring(),
        )
        found = any(it.type == "new_moon_window" for it in items)
        assert found == expected, f"offset={offset}: expected new_moon_window={expected}"


def test_full_moon_window_three_days_before_and_after():
    svc = TodayImportantService()
    for offset in [-3, -1, 0, 1, 3]:
        moon_lon = 120.0 + 180 + offset * 12
        diff = abs(moon_lon - 120.0) % 360
        diff = min(diff, 360 - diff)
        transits = _make_transits([
            _transit_planet("Sun", 120.0),
            _transit_planet("Moon", moon_lon),
        ])
        items = svc.build_items(
            target_date=date.today(),
            timezone="UTC", natal={}, transits=transits, signals=[],
            scoring_result=_make_scoring(),
        )
        found = any(it.type == "full_moon_window" for it in items)
        assert found, f"offset={offset}: expected full_moon_window=True, diff={diff}"


def test_eclipse_suppresses_lunation_item():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 120.0, speed=13),  # New moon
        _transit_planet("NORTH_NODE_TRUE", 122.0),
    ])
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[],
        scoring_result=_make_scoring(),
    )
    ecl = [it for it in items if it.type == "eclipse_window"]
    new = [it for it in items if it.type == "new_moon_window"]
    assert len(ecl) == 1  # Eclipse detected (sun & moon near node)
    assert len(new) == 0   # New moon suppressed by eclipse


def test_empty_important_today_when_no_whitelisted_events():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0, speed=1),
        _transit_planet("Moon", 200.0, speed=13),
        _transit_planet("Venus", 50.0, speed=0.5),
    ])
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Mars", aspect_type="trine", orb=3, strength=0.4)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[msig],
        scoring_result=_make_scoring(),
    )
    # Only active_house might appear (from Moon position), which is fine.
    # No retrograde, no station, no eclipse, no lunation, no exact aspect.
    forbidden = ["mercury_retrograde", "mercury_station", "eclipse_window",
                 "new_moon_window", "full_moon_window", "exact_daily_aspect"]
    for it in items:
        assert it.type not in forbidden, f"Unexpected item type: {it.type}"


def test_active_house_can_be_single_item_if_computed():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0, speed=1),
        _transit_planet("Moon", 200.0, speed=13),
    ])
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Mars", aspect_type="trine", orb=2, strength=0.5)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[msig],
        scoring_result=_make_scoring(),
    )
    house = [it for it in items if it.type == "active_house"]
    assert len(house) <= 1
    if house:
        assert house[0].house is not None


def test_important_today_limited_to_three_items():
    svc = TodayImportantService()
    planets = [
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 120.0 + 180),  # Full moon
        _transit_planet("Mercury", 130.0, speed=-0.3),  # Retrograde
    ]
    transits = _make_transits(planets)
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Sun",
                       aspect_type="opposition", orb=3, strength=0.8,
                       delta_kind="peak_today", daily_salience=0.9)
    top_sig = AstroSignal(type="planet_in_house", planet="Mars", house=10, strength=0.9)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits,
        signals=[msig, top_sig],
        scoring_result=_make_scoring(top_signals=[top_sig]),
    )
    assert len(items) <= 3


def test_sorted_by_priority():
    svc = TodayImportantService()
    planets = [
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 120.0),  # New moon
        _transit_planet("Mercury", 130.0, speed=-0.3),
    ]
    transits = _make_transits(planets)
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Sun",
                       aspect_type="conjunction", orb=1, strength=0.8)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[msig],
        scoring_result=_make_scoring(),
    )
    for i in range(len(items) - 1):
        assert items[i].priority >= items[i+1].priority


def test_exact_daily_aspect_requires_delta_kind():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
    ])
    # Aspect with background delta — should NOT be shown
    bg_sig = AstroSignal(type="aspect", planet="Moon", target_planet="Saturn",
                         aspect_type="square", orb=1, strength=0.9,
                         delta_kind="background", daily_salience=0.5)
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Mars",
                       aspect_type="trine", orb=2, strength=0.5)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[bg_sig, msig],
        scoring_result=_make_scoring(),
    )
    exact = [it for it in items if it.type == "exact_daily_aspect"]
    assert len(exact) == 0


def test_exact_daily_aspect_shows_with_peak_delta():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
    ])
    peak_sig = AstroSignal(type="aspect", planet="Moon", target_planet="Saturn",
                           aspect_type="square", orb=1, strength=0.9,
                           delta_kind="peak_today", daily_salience=1.17)
    msig = AstroSignal(type="aspect", planet="Moon", target_planet="Mars",
                       aspect_type="trine", orb=2, strength=0.5)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC", natal={}, transits=transits, signals=[peak_sig, msig],
        scoring_result=_make_scoring(),
    )
    exact = [it for it in items if it.type == "exact_daily_aspect"]
    assert len(exact) == 1
    assert "Луна" in exact[0].title and "Сатурн" in exact[0].title
