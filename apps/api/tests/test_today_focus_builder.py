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
    build_today_focus,
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
        semantic_key="aspect:MARS:opposition:natal_planet:NEPTUNE",
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


# ── B2 Focus Assembly Tests (§12.1 cases 1–9, 13) ─────────────────────────────

def test_b2_single_firdar_yields_background_only_not_convergence():
    """1. Single annual firdar factor -> background_only state, NOT convergence_today."""
    target_date = date(2026, 7, 28)
    tf_firdar = TodayFactor(
        factor_id="act:firdar:sun",
        activation_ids=("act-firdar-sun",),
        technique="firdar",
        technique_family="firdar",
        source_key="SUN",
        target_key="SUN",
        theme_keys=("identity",),
        product_spheres=("work", "decisions"),
        polarity="supportive",
        strength=0.8,
        salience=0.8,
        active_from=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        exact_at=None,
        active_until=datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        phase=None,
        temporal_role="background",
    )

    focus = build_today_focus([tf_firdar], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "background_only"
    assert focus.convergence is None
    assert focus.events == ()
    assert focus.featured_spheres == ()


def test_b2_single_exact_factor_yields_single_impulses():
    """2. Single exact factor today -> single_impulses state, convergence is None, featured_spheres empty."""
    target_date = date(2026, 7, 28)
    exact_dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
    tf_exact = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "decisions"),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=exact_dt - timedelta(hours=6),
        exact_at=exact_dt,
        active_until=exact_dt + timedelta(hours=6),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf_exact], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "single_impulses"
    assert focus.convergence is None
    assert len(focus.events) == 1
    assert focus.events[0].id == "ev:sig:aspect:MARS:OPPOSITION:NEPTUNE"
    assert focus.featured_spheres == ()


def test_b2_two_related_factors_plus_exact_yields_convergence_today():
    """3. Two related factors + exact today -> convergence_today state."""
    target_date = date(2026, 7, 28)
    exact_dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
    
    tf1 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "decisions"),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=exact_dt - timedelta(hours=6),
        exact_at=exact_dt,
        active_until=exact_dt + timedelta(hours=6),
        phase="exact",
        temporal_role="anchor_today",
    )
    
    # Related by same target_key "NEPTUNE"
    tf2 = TodayFactor(
        factor_id="sig:aspect:MOON:OPPOSITION:NEPTUNE",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="NEPTUNE",
        theme_keys=("emotion",),
        product_spheres=("relationships", "health"),
        polarity="tense",
        strength=0.75,
        salience=0.75,
        active_from=exact_dt - timedelta(hours=2),
        exact_at=exact_dt + timedelta(hours=1),
        active_until=exact_dt + timedelta(hours=4),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf1, tf2], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "convergence_today"
    assert focus.convergence is not None
    assert focus.convergence.independent_factor_count == 2
    assert len(focus.events) == 2
    assert len(focus.featured_spheres) >= 1


def test_b2_two_unrelated_exact_factors_yields_two_events_single_impulses():
    """4. Two simultaneous but unrelated exact factors -> 2 events, state is single_impulses (no convergence)."""
    target_date = date(2026, 7, 28)
    exact_dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
    
    tf1 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=exact_dt - timedelta(hours=6),
        exact_at=exact_dt,
        active_until=exact_dt + timedelta(hours=6),
        phase="exact",
        temporal_role="anchor_today",
    )
    
    # Unrelated: different target_key "JUPITER", no common theme or sphere
    tf2 = TodayFactor(
        factor_id="sig:aspect:VENUS:TRINE:JUPITER",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="VENUS",
        target_key="JUPITER",
        theme_keys=("finance",),
        product_spheres=("money", "shopping"),
        polarity="supportive",
        strength=0.80,
        salience=0.80,
        active_from=exact_dt - timedelta(hours=2),
        exact_at=exact_dt + timedelta(hours=2),
        active_until=exact_dt + timedelta(hours=4),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf1, tf2], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "single_impulses"
    assert focus.convergence is None
    assert len(focus.events) == 2
    assert focus.featured_spheres == ()


def test_b2_signal_plus_activation_counts_as_one_independent_factor():
    """5. Signal + activation of same aspect merges into 1 TodayFactor -> count is 1."""
    target_date = date(2026, 7, 28)
    tf1 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1", "act-2"),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 16, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf1], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "single_impulses"
    assert len(focus.events) == 1


def test_b2_single_factor_in_three_spheres_count_remains_one():
    """6. Single factor mapped to 3 product spheres maintains independent_factor_count == 1."""
    target_date = date(2026, 7, 28)
    tf1 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "decisions", "health"),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 16, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf1], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "single_impulses"
    assert focus.convergence is None


def test_b2_background_joins_existing_convergence_does_not_create_one():
    """7. Background factor joins an existing convergence group, but cannot create one alone."""
    target_date = date(2026, 7, 28)
    exact_dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
    
    tf_anchor = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "decisions"),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=exact_dt - timedelta(hours=6),
        exact_at=exact_dt,
        active_until=exact_dt + timedelta(hours=6),
        phase="exact",
        temporal_role="anchor_today",
    )

    tf_bg = TodayFactor(
        factor_id="act:firdar:neptune",
        activation_ids=("act-firdar-neptune",),
        technique="firdar",
        technique_family="firdar",
        source_key="NEPTUNE",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "decisions"),
        polarity="tense",
        strength=0.70,
        salience=0.70,
        active_from=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        exact_at=None,
        active_until=datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        phase=None,
        temporal_role="background",
    )

    # Solo background + solo anchor -> cannot form convergence (background cannot create convergence alone)
    focus_solo = build_today_focus([tf_anchor, tf_bg], tz_name="Europe/Moscow", target_date=target_date)
    assert focus_solo.state == "single_impulses"
    assert focus_solo.convergence is None

    # 2 related anchors + 1 background -> convergence formed, background joins technique_families
    tf_anchor2 = TodayFactor(
        factor_id="sig:aspect:MOON:OPPOSITION:NEPTUNE",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("relationships", "health"),
        polarity="tense",
        strength=0.75,
        salience=0.75,
        active_from=exact_dt - timedelta(hours=2),
        exact_at=exact_dt + timedelta(hours=1),
        active_until=exact_dt + timedelta(hours=4),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus_conv = build_today_focus([tf_anchor, tf_anchor2, tf_bg], tz_name="Europe/Moscow", target_date=target_date)
    assert focus_conv.state == "convergence_today"
    assert focus_conv.convergence is not None
    assert focus_conv.convergence.independent_factor_count == 2
    assert "firdar" in focus_conv.convergence.technique_families


def test_b2_permutation_of_factors_preserves_focus_state_and_ids():
    """8. Permutation of input factors list preserves state, ranking, and output IDs."""
    target_date = date(2026, 7, 28)
    exact_dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
    
    tf1 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "decisions"),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=exact_dt - timedelta(hours=6),
        exact_at=exact_dt,
        active_until=exact_dt + timedelta(hours=6),
        phase="exact",
        temporal_role="anchor_today",
    )
    
    tf2 = TodayFactor(
        factor_id="sig:aspect:MOON:OPPOSITION:NEPTUNE",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="NEPTUNE",
        theme_keys=("emotion",),
        product_spheres=("relationships", "health"),
        polarity="tense",
        strength=0.75,
        salience=0.75,
        active_from=exact_dt - timedelta(hours=2),
        exact_at=exact_dt + timedelta(hours=1),
        active_until=exact_dt + timedelta(hours=4),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus1 = build_today_focus([tf1, tf2], tz_name="Europe/Moscow", target_date=target_date)
    focus2 = build_today_focus([tf2, tf1], tz_name="Europe/Moscow", target_date=target_date)

    assert focus1.state == focus2.state
    assert focus1.convergence.id == focus2.convergence.id
    assert [e.id for e in focus1.events] == [e.id for e in focus2.events]
    assert [s.key for s in focus1.featured_spheres] == [s.key for s in focus2.featured_spheres]


def test_b2_featured_spheres_capped_at_three():
    """9. Featured spheres are capped at 3 (0..3). 4th sphere does not pass cap."""
    target_date = date(2026, 7, 28)
    exact_dt = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)
    
    tf1 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "money", "documents", "relationships", "sport"),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=exact_dt - timedelta(hours=6),
        exact_at=exact_dt,
        active_until=exact_dt + timedelta(hours=6),
        phase="exact",
        temporal_role="anchor_today",
    )
    
    tf2 = TodayFactor(
        factor_id="sig:aspect:MOON:OPPOSITION:NEPTUNE",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work", "money", "documents", "relationships"),
        polarity="tense",
        strength=0.75,
        salience=0.75,
        active_from=exact_dt - timedelta(hours=2),
        exact_at=exact_dt + timedelta(hours=1),
        active_until=exact_dt + timedelta(hours=4),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf1, tf2], tz_name="Europe/Moscow", target_date=target_date)
    assert focus.state == "convergence_today"
    assert len(focus.featured_spheres) <= 3
    assert len(focus.featured_spheres) == 3


def test_b2_malformed_or_none_input_returns_unavailable():
    """13. None or malformed input returns state='unavailable'."""
    focus = build_today_focus(None)
    assert focus.state == "unavailable"
    assert focus.content_state == "unavailable"
    assert focus.convergence is None
    assert focus.events == ()
    assert focus.featured_spheres == ()

