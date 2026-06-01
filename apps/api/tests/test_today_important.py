# AI_HEADER
# module: M-TEST-TODAY-IMPORTANT
# wave: W-PHASE-2
# purpose: Tests for TodayImportantService and schema additions

from datetime import date

import pytest

from app.schemas.normalization import AstroSignal
from app.schemas.today import ImportantTodayItem, ImportantTodayDetails, ImportantTodayType, ImportantTodaySeverity, TodayPayload
from app.services.today_important_service import TodayImportantService


# ── Schema tests ──────────────────────────────────────────────────────

def test_today_payload_has_important_today_default_empty():
    from app.schemas.today import TodayMeta, ContentAccessState, ReadingBody, WhyThisHappens
    import datetime as dt
    p = TodayPayload(
        meta=TodayMeta(
            schema_version="today/v1",
            contract_version=2,
            calculation_version=1,
            normalization_version=1,
            scoring_version=1,
            prompt_version=1,
            content_version=1,
            generated_at=dt.datetime.now(dt.UTC).isoformat(),
            cached=False,
        ),
        date="2026-01-01",
        title="Test",
        headline="Headline",
        access=ContentAccessState(state="full"),
        day_status="steady",
        top_flags=[],
        reading=ReadingBody(paragraphs=["ok"]),
        why_this_happens=WhyThisHappens(sections=[]),
        week_strip=[],
        microcopy=[],
    )
    assert p.important_today == []
    assert p.meta.contract_version == 2


def test_astrosignal_accepts_delta_fields():
    s = AstroSignal(
        type="aspect",
        planet="Moon",
        target_planet="Sun",
        aspect_type="conjunction",
        orb=1.0,
        strength=0.9,
        delta_kind="new_today",
        phase="applying",
        daily_salience=1.17,
    )
    assert s.delta_kind == "new_today"
    assert s.phase == "applying"
    assert s.daily_salience == 1.17


def test_important_today_item_fallback_details():
    item = ImportantTodayItem(
        id="test",
        type="moon_void",
        title="Test",
        subtitle="Sub",
        severity="soft_warning",
    )
    assert item.type == "moon_void"
    assert item.severity == "soft_warning"
    assert item.details is None


def test_important_today_details_model():
    details = ImportantTodayDetails(
        meaning="Test meaning",
        why_important="Test why",
        personal_context="Test context",
    )
    assert details.meaning == "Test meaning"
    assert details.why_important == "Test why"
    assert details.personal_context == "Test context"


# ── Service tests ─────────────────────────────────────────────────────

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


def test_active_house_item_created_from_top_signal():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 60.0),
    ])
    top_sig = AstroSignal(
        type="planet_in_house", planet="Mars", house=10, strength=0.9,
    )
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[top_sig],
        scoring_result=_make_scoring(top_signals=[top_sig]),
    )
    house_items = [it for it in items if it.type == "active_house"]
    assert len(house_items) == 1
    assert house_items[0].house == 10
    assert "Активен 10 дом" == house_items[0].title


def test_important_today_limited_to_three_items():
    svc = TodayImportantService()
    # Create many signals to trigger multiple items
    planets = [
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 120.0),  # same as Sun → new moon
        _transit_planet("Mercury", 130.0, speed=-0.3),  # retrograde
        _transit_planet("Venus", 200.0, speed=-0.1),  # retrograde
        _transit_planet("Saturn", 300.0, speed=0.001),  # station
    ]
    transits = _make_transits(planets)
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[],
        scoring_result=_make_scoring(),
    )
    assert len(items) <= 3


def test_important_today_sorted_by_priority():
    svc = TodayImportantService()
    planets = [
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 120.0),
        _transit_planet("Mercury", 130.0, speed=-0.3),
        _transit_planet("Venus", 200.0, speed=-0.1),
        _transit_planet("Saturn", 300.0, speed=0.001),
    ]
    transits = _make_transits(planets)
    # Moon needs an aspect to avoid VOC (which has priority 85, higher than Mercury retrograde 80)
    moon_signal = AstroSignal(
        type="aspect", planet="Moon", target_planet="Sun",
        aspect_type="conjunction", orb=0.5, strength=0.8,
    )
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[moon_signal],
        scoring_result=_make_scoring(top_signals=[moon_signal]),
    )
    # New moon = 90, Mercury retro = 80, station = 70
    # Should be: new_moon, retro_mercury, station_saturn
    assert items[0].type == "new_moon"
    assert items[1].type == "retrograde"
    assert items[1].planet == "Меркурий"
    assert items[2].priority <= items[1].priority <= items[0].priority


def test_new_moon_item_created_from_sun_moon_angle():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 122.0),  # 2° diff → new moon
    ])
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[],
        scoring_result=_make_scoring(),
    )
    moon_items = [it for it in items if it.type == "new_moon"]
    assert len(moon_items) == 1
    assert moon_items[0].title == "Новолуние сегодня"


def test_full_moon_item_created_from_sun_moon_angle():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 300.0),  # 180° diff → full moon
    ])
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[],
        scoring_result=_make_scoring(),
    )
    moon_items = [it for it in items if it.type == "full_moon"]
    assert len(moon_items) == 1


def test_mercury_retrograde_item_created_when_flag_present():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
        _transit_planet("Mercury", 150.0, speed=-0.3),
    ])
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[],
        scoring_result=_make_scoring(),
    )
    retro_items = [it for it in items if it.type == "retrograde"]
    assert len(retro_items) >= 1
    assert any(it.planet == "Меркурий" for it in retro_items)


def test_important_details_fallback_present_without_llm():
    svc = TodayImportantService()
    planets = [
        _transit_planet("Sun", 120.0),
        _transit_planet("Moon", 122.0),
    ]
    transits = _make_transits(planets)
    top_sig = AstroSignal(
        type="planet_in_house", planet="Mars", house=10, strength=0.9,
    )
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[top_sig],
        scoring_result=_make_scoring(top_signals=[top_sig]),
    )
    for it in items:
        assert it.details is not None, f"Item {it.id} missing fallback details"
        assert it.details.meaning is not None


def test_empty_when_no_data():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0, speed=1),
        _transit_planet("Moon", 200.0, speed=13),
    ])
    # Add a Moon aspect to avoid VOC from empty signals list
    moon_sig = AstroSignal(
        type="aspect", planet="Moon", target_planet="Mars",
        aspect_type="trine", orb=2.0, strength=0.5,
    )
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[moon_sig],
        scoring_result=_make_scoring(),
    )
    # No special conditions → only active_house might appear from Moon position
    assert all(it.type == "active_house" for it in items) if items else True


def test_ingress_detected_near_sign_boundary():
    svc = TodayImportantService()
    transits = _make_transits([
        _transit_planet("Sun", 100.0),
        _transit_planet("Moon", 200.0),
        _transit_planet("Venus", 60.5, speed=0.5),  # Just past 60° — ingress into Gemini
    ])
    items = svc.build_items(
        target_date=date.today(),
        timezone="UTC",
        natal={},
        transits=transits,
        signals=[],
        scoring_result=_make_scoring(),
    )
    ingress_items = [it for it in items if it.type == "ingress"]
    assert len(ingress_items) == 1
    assert ingress_items[0].planet == "Венера"
