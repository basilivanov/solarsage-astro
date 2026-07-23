# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ELECTION_ENGINE
# ROLE: Unit tests for election_engine scoring
# DEPENDENCIES: pytest, app.services.election_engine
# GRACE_ANCHORS: []
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for election_engine scan logic.
# owns:
#   - apps/api/tests/test_election_engine.py
# inputs: stubbed lunar_days
# outputs: assertions on best_days, avoid_days, score calculations
# END_MODULE_CONTRACT

from datetime import date
import pytest

from app.services.election_engine import scan


@pytest.mark.asyncio
async def test_election_engine_scoring_and_clamping() -> None:
    # Event: wedding (preferred: taurus, libra, cancer; disfavored: scorpio, capricorn; mercury_sensitive: true)
    lunar_days = [
        # Day 1: Preferred sign (taurus), waxing (+10), no VOC, no retro -> 50 + 25 + 10 = 85 (great)
        {
            "date": "2026-08-01",
            "moon_sign": "taurus",
            "moon_sign_ru": "Телец",
            "waxing": True,
            "voc_fraction": 0.0,
            "mercury_retro": False,
        },
        # Day 2: Disfavored sign (scorpio), waning, high VOC (0.5 > 0.25 penalty -40), retro (-20) -> 50 - 15 - 40 - 20 = -25 -> clamp 0 (avoid)
        {
            "date": "2026-08-02",
            "moon_sign": "scorpio",
            "moon_sign_ru": "Скорпион",
            "waxing": False,
            "voc_fraction": 0.5,
            "mercury_retro": True,
        },
    ]

    from_date = date(2026, 8, 1)
    to_date = date(2026, 8, 2)

    res = await scan("wedding", from_date, to_date, lunar_days)

    assert res["event"] == "wedding"
    assert len(res["best_days"]) == 1
    assert res["best_days"][0]["date"] == "2026-08-01"
    assert res["best_days"][0]["score"] == 85
    assert res["best_days"][0]["label"] == "great"
    assert len(res["best_days"][0]["reasons"]) > 0

    assert len(res["avoid_days"]) == 1
    assert res["avoid_days"][0]["date"] == "2026-08-02"
    assert res["avoid_days"][0]["score"] == 0
    assert res["avoid_days"][0]["label"] == "avoid"
    assert len(res["avoid_days"][0]["reasons"]) == 3  # disfavored, voc, retro


@pytest.mark.asyncio
async def test_election_engine_invalid_event_type() -> None:
    with pytest.raises(ValueError):
        await scan("invalid_event", date(2026, 8, 1), date(2026, 8, 2), [])
