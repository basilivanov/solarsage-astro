# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ELECTION_ENGINE
# ROLE: Unit tests for election_engine scoring (v2 categories & facts)
# DEPENDENCIES: pytest, app.services.election_engine
# ############################################################################

from datetime import date
import pytest

from app.services.election_engine import scan, resolve_event


@pytest.mark.asyncio
async def test_election_engine_category_resolution() -> None:
    # Test category:sub resolution
    cat, sub, rule = resolve_event("relations:wedding")
    assert cat == "relations"
    assert sub == "wedding"
    assert rule["label"] == "Свадьба/помолвка"

    # Test plain sub resolution
    cat2, sub2, rule2 = resolve_event("wedding")
    assert cat2 == "relations"
    assert sub2 == "wedding"

    # Test invalid event
    with pytest.raises(ValueError):
        resolve_event("invalid_category:invalid_sub")


@pytest.mark.asyncio
async def test_election_engine_scoring_and_facts() -> None:
    lunar_days = [
        {
            "date": "2026-08-01",
            "moon_sign": "taurus",
            "moon_sign_ru": "Телец",
            "phase_angle": 120.0,
            "waxing": True,
            "voc_fraction": 0.0,
            "voc_intervals": [],
            "mercury_retro": False,
        },
        {
            "date": "2026-08-02",
            "moon_sign": "scorpio",
            "moon_sign_ru": "Скорпион",
            "phase_angle": 200.0,
            "waxing": False,
            "voc_fraction": 0.5,
            "voc_intervals": [{"start": "2026-08-02T10:00:00Z", "end": "2026-08-02T14:00:00Z"}],
            "mercury_retro": True,
        },
    ]

    from_date = date(2026, 8, 1)
    to_date = date(2026, 8, 2)

    res = await scan("relations:wedding", from_date, to_date, lunar_days, natal_moon_sign="taurus")

    assert res["event"] == "relations:wedding"
    assert len(res["best_days"]) == 1
    assert res["best_days"][0]["date"] == "2026-08-01"
    assert res["best_days"][0]["score"] == 85
    assert res["best_days"][0]["label"] == "great"

    assert "facts" in res
    assert res["facts"]["event"]["category"] == "relations"
    assert res["facts"]["event"]["sub"] == "wedding"
    assert res["facts"]["personal"]["natal_moon_sign"] == "taurus"
    assert res["facts"]["personal"]["resonates"] is True

    assert "days" in res
    assert len(res["days"]) == 2
