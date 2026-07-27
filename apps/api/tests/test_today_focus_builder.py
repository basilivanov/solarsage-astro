# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_FOCUS_BUILDER
# ROLE: Directed unit tests for M-TODAY-FOCUS-BUILDER (Slice B1).
# DEPENDENCIES: pytest, app.services.today_focus_builder, app.schemas.day_valence
# ############################################################################

from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pytest

from app.schemas.day_valence import DayValenceFactor, FactorLedger
from app.services.today_focus_builder import (
    TodayFactor,
    classify_temporal_role,
    local_day_bounds,
    normalize_factors,
)


def test_local_day_bounds_moscow_and_new_york():
    """Verify local day bounds in UTC for different IANA timezones."""
    target_date = date(2026, 7, 28)

    # Europe/Moscow is UTC+3 in July
    start_mow, end_mow = local_day_bounds(target_date, "Europe/Moscow")
    assert start_mow == datetime(2026, 7, 27, 21, 0, 0, tzinfo=timezone.utc)
    assert end_mow == datetime(2026, 7, 28, 21, 0, 0, tzinfo=timezone.utc)

    # America/New_York is EDT (UTC-4) in July
    start_ny, end_ny = local_day_bounds(target_date, "America/New_York")
    assert start_ny == datetime(2026, 7, 28, 4, 0, 0, tzinfo=timezone.utc)
    assert end_ny == datetime(2026, 7, 29, 4, 0, 0, tzinfo=timezone.utc)


def test_exact_at_midnight_timezone_boundary():
    """Verify exact_at before/after midnight UTC maps to correct local date."""
    target_date = date(2026, 7, 28)
    start_mow, end_mow = local_day_bounds(target_date, "Europe/Moscow")

    # 2026-07-27 20:59 UTC is 23:59 July 27 in Moscow (NOT July 28)
    dt_before = datetime(2026, 7, 27, 20, 59, 0, tzinfo=timezone.utc)
    factor_before = {
        "factor_id": "test:1",
        "exact_at": dt_before,
        "technique_family": "transit",
        "technique": "transit_to_natal",
    }
    assert classify_temporal_role(factor_before, start_mow, end_mow) != "anchor_today"

    # 2026-07-27 21:01 UTC is 00:01 July 28 in Moscow (IS July 28 anchor)
    dt_after = datetime(2026, 7, 27, 21, 1, 0, tzinfo=timezone.utc)
    factor_after = {
        "factor_id": "test:2",
        "exact_at": dt_after,
        "technique_family": "transit",
        "technique": "transit_to_natal",
    }
    assert classify_temporal_role(factor_after, start_mow, end_mow) == "anchor_today"


def test_signal_plus_activation_merge_one_today_factor():
    """Signal + activation of the same physical aspect merges into one TodayFactor with activation_ids."""
    factor_sig = DayValenceFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        semantic_key="aspect:MARS:opposition:NEPTUNE",
        source="day_signal",
        technique="transit_to_natal",
        technique_family="transit",
        polarity="tense",
        strength=0.9,
        technical_spheres=["career"],
        source_planet="MARS",
        target_type="natal_planet",
        target_key="NEPTUNE",
        aspect_type="opposition",
    )
    ledger = FactorLedger(factors=[factor_sig], duplicate_count=0, invalid_count=0)

    activation_layer = [
        {
            "id": "act-mars-opp-neptune",
            "planet": "Transit_Mars",
            "target_planet": "Neptune",
            "aspect_type": "opposition",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "exact_at": "2026-07-28T16:52:00Z",
        }
    ]

    result = normalize_factors(
        ledger=ledger,
        activation_layer=activation_layer,
        target_date=date(2026, 7, 28),
        tz_info="Europe/Moscow",
    )

    assert len(result) == 1
    tf = result[0]
    assert tf.factor_id == "sig:aspect:MARS:OPPOSITION:NEPTUNE"
    assert tf.activation_ids == ("act-mars-opp-neptune",)
    assert tf.temporal_role == "anchor_today"
    assert tf.exact_at == datetime(2026, 7, 28, 16, 52, 0, tzinfo=timezone.utc)


def test_strong_factor_without_timing_not_anchor():
    """High strength/small orb factor without daily timing is NOT anchor_today (§2.2)."""
    target_date = date(2026, 7, 28)
    start_mow, end_mow = local_day_bounds(target_date, "Europe/Moscow")

    factor_strong = {
        "factor_id": "sig:aspect:PLUTO:TRINE:SATURN",
        "strength": 0.99,
        "exact_at": None,
        "active_from": datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc),
        "active_until": datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc),
        "technique_family": "transit",
        "technique": "transit_to_natal",
    }

    role = classify_temporal_role(factor_strong, start_mow, end_mow)
    assert role == "supporting"
    assert role != "anchor_today"


def test_exact_at_none_manufactures_no_hours():
    """Factor with exact_at=None leaves exact_at as None and manufactures no fake hours."""
    factor_no_time = DayValenceFactor(
        factor_id="sig:house:VENUS:10",
        semantic_key="house:VENUS:10",
        source="day_signal",
        technique="transit_planet_in_house",
        technique_family="transit",
        polarity="neutral",
        strength=0.7,
        technical_spheres=["career"],
        source_planet="VENUS",
        target_type="house",
        target_key="10",
        aspect_type=None,
    )
    ledger = FactorLedger(factors=[factor_no_time], duplicate_count=0, invalid_count=0)

    result = normalize_factors(ledger, None, target_date=date(2026, 7, 28), tz_info="Europe/Moscow")
    assert len(result) == 1
    assert result[0].exact_at is None
    assert result[0].temporal_role != "anchor_today"


def test_firdar_and_profection_classified_as_background():
    """Annual firdar and profection factors classify as background."""
    target_date = date(2026, 7, 28)
    start_mow, end_mow = local_day_bounds(target_date, "Europe/Moscow")

    firdar_factor = {
        "factor_id": "act:firdar:sun",
        "technique_family": "firdar",
        "technique": "firdar",
        "active_from": datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        "active_until": datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    }

    role = classify_temporal_role(firdar_factor, start_mow, end_mow)
    assert role == "background"


def test_permutation_invariance():
    """Shuffling inputs produces the exact same deterministic list of TodayFactor."""
    f1 = DayValenceFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        semantic_key="aspect:MARS:opposition:NEPTUNE",
        source="day_signal",
        technique="transit_to_natal",
        technique_family="transit",
        polarity="tense",
        strength=0.9,
        technical_spheres=["career"],
        source_planet="MARS",
        target_type="natal_planet",
        target_key="NEPTUNE",
        aspect_type="opposition",
    )
    f2 = DayValenceFactor(
        factor_id="sig:aspect:VENUS:TRINE:JUPITER",
        semantic_key="aspect:VENUS:trine:JUPITER",
        source="day_signal",
        technique="transit_to_natal",
        technique_family="transit",
        polarity="supportive",
        strength=0.8,
        technical_spheres=["finance"],
        source_planet="VENUS",
        target_type="natal_planet",
        target_key="JUPITER",
        aspect_type="trine",
    )

    ledger1 = FactorLedger(factors=[f1, f2], duplicate_count=0, invalid_count=0)
    ledger2 = FactorLedger(factors=[f2, f1], duplicate_count=0, invalid_count=0)

    res1 = normalize_factors(ledger1, target_date=date(2026, 7, 28), tz_info="Europe/Moscow")
    res2 = normalize_factors(ledger2, target_date=date(2026, 7, 28), tz_info="Europe/Moscow")

    assert [f.factor_id for f in res1] == [f.factor_id for f in res2]
