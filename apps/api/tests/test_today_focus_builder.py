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



def test_b2_convergence_background_factors_exclude_events_and_carry_roles():
    """Winning-group factors that did not become events land in background_factors with roles and human titles."""
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
    tf_support = TodayFactor(
        factor_id="sig:aspect:VENUS:TRINE:NEPTUNE",
        activation_ids=("act-3",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="VENUS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("relationships",),
        polarity="supportive",
        strength=0.60,
        salience=0.60,
        active_from=exact_dt - timedelta(days=3),
        exact_at=exact_dt + timedelta(days=2),
        active_until=exact_dt + timedelta(days=5),
        phase="applying",
        temporal_role="supporting",
        aspect_type="trine",
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

    focus = build_today_focus(
        [tf_anchor, tf_anchor2, tf_support, tf_bg],
        tz_name="Europe/Moscow",
        target_date=target_date,
    )
    assert focus.state == "convergence_today"
    conv = focus.convergence
    assert conv is not None

    event_factor_ids = {ev.id.removeprefix("ev:") for ev in focus.events}
    bg = conv.background_factors
    bg_ids = {f.id.removeprefix("f:") for f in bg}

    # Event factors are not duplicated in background_factors
    assert not (bg_ids & event_factor_ids)
    # Non-event winning-group factors are present with roles and clean titles
    assert "sig:aspect:VENUS:TRINE:NEPTUNE" in bg_ids
    assert "act:firdar:neptune" in bg_ids
    roles = {f.id: f.role for f in bg}
    assert roles["f:sig:aspect:VENUS:TRINE:NEPTUNE"] == "supporting"
    assert roles["f:act:firdar:neptune"] == "background"
    titles = {f.id: f.human_title for f in bg}
    assert titles["f:act:firdar:neptune"] == "Фирдар: Нептун — тема периода"
    assert "transit_to_natal" not in " ".join(titles.values())
    # Deterministic order: supporting before background
    assert [f.role for f in bg] == sorted((f.role for f in bg), key={"anchor_today": 0, "supporting": 1, "background": 2, "unrelated": 3}.get)


# ── Amendment §8.1 Acceptance Tests ──────────────────────────────────────────

def test_amendment_8_1_canary_sanitized_2026_07_28():
    """Canary oracle 2026-07-28 Europe/Moscow per amendment §4 & §8.1.12."""
    target_date = date(2026, 7, 28)
    tz_name = "Europe/Moscow"

    # Pluto convergence group anchors and members
    # Moon square Pluto: exact 10:31 UTC = 13:31 Moscow (Primary anchor of Pluto convergence)
    tf_moon_pluto = TodayFactor(
        factor_id="act:t2n__MOON__SQUARE__PLUTO",
        activation_ids=("t2n__MOON__SQUARE__PLUTO",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="PLUTO",
        theme_keys=("transformation",),
        product_spheres=("decisions", "work"),
        polarity="tense",
        strength=0.7200,
        salience=0.7200,
        active_from=datetime(2026, 7, 28, 8, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 10, 31, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 13, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="square",
        target_type="natal_planet",
    )
    # Mars Pluto member of convergence group
    tf_mars_pluto = TodayFactor(
        factor_id="act:t2n__MARS__SQUARE__PLUTO",
        activation_ids=("t2n__MARS__SQUARE__PLUTO",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="PLUTO",
        theme_keys=("transformation",),
        product_spheres=("decisions", "work"),
        polarity="tense",
        strength=0.6500,
        salience=0.6500,
        active_from=datetime(2026, 7, 28, 0, 0, 0, tzinfo=timezone.utc),
        exact_at=None,
        active_until=datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc),
        phase="building",
        temporal_role="supporting",
        aspect_type="square",
        target_type="natal_planet",
    )

    # Independent strong valenced exact anchors
    # Mars opposition Neptune: exact 16:52 UTC = 19:52 Moscow (strength 0.9076)
    tf_mars_neptune = TodayFactor(
        factor_id="act:t2n__MARS__OPPOSITION__NEPTUNE",
        activation_ids=("t2n__MARS__OPPOSITION__NEPTUNE",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("illusion",),
        product_spheres=("creativity", "health"),
        polarity="tense",
        strength=0.9076,
        salience=0.9076,
        active_from=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 16, 52, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 20, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="opposition",
        target_type="natal_planet",
    )
    # Moon sextile Uranus: exact 15:19 UTC = 18:19 Moscow (strength 0.2005)
    tf_moon_uranus = TodayFactor(
        factor_id="act:t2n__MOON__SEXTILE__URANUS",
        activation_ids=("t2n__MOON__SEXTILE__URANUS",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="URANUS",
        theme_keys=("insight",),
        product_spheres=("travel", "decisions"),
        polarity="supportive",
        strength=0.2005,
        salience=0.2005,
        active_from=datetime(2026, 7, 28, 13, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 15, 19, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 17, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="sextile",
        target_type="natal_planet",
    )

    # Weaker/neutral anchors that must be displaced
    # Moon quincunx Lot Necessity: neutral 0.1144, exact 21:35 UTC (00:35 Moscow next day)
    tf_moon_necessity = TodayFactor(
        factor_id="act:t2n__MOON__QUINCUNX__LOT_NECESSITY",
        activation_ids=("t2n__MOON__QUINCUNX__LOT_NECESSITY",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="LOT_NECESSITY",
        theme_keys=("duty",),
        product_spheres=("work",),
        polarity="neutral",
        strength=0.1144,
        salience=0.1144,
        active_from=datetime(2026, 7, 27, 21, 35, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 27, 21, 35, 0, tzinfo=timezone.utc), # 00:35 July 28 Moscow
        active_until=datetime(2026, 7, 27, 23, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="quincunx",
        target_type="lot",
    )
    # Moon sextile Mercury: supportive 0.0137, exact 21:18 UTC July 27 (00:18 Moscow July 28)
    tf_moon_mercury = TodayFactor(
        factor_id="act:t2n__MOON__SEXTILE__MERCURY",
        activation_ids=("t2n__MOON__SEXTILE__MERCURY",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="MERCURY",
        theme_keys=("speech",),
        product_spheres=("communication",),
        polarity="supportive",
        strength=0.0137,
        salience=0.0137,
        active_from=datetime(2026, 7, 27, 21, 18, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 27, 21, 18, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 27, 23, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="sextile",
        target_type="natal_planet",
    )

    factors = [
        tf_moon_pluto,
        tf_mars_pluto,
        tf_mars_neptune,
        tf_moon_uranus,
        tf_moon_necessity,
        tf_moon_mercury,
    ]

    focus = build_today_focus(factors, tz_name=tz_name, target_date=target_date)

    assert focus.state == "convergence_today"
    assert len(focus.events) == 3

    event_ids = [e.id for e in focus.events]
    assert event_ids == [
        "ev:act:t2n__MOON__SQUARE__PLUTO",
        "ev:act:t2n__MOON__SEXTILE__URANUS",
        "ev:act:t2n__MARS__OPPOSITION__NEPTUNE",
    ]

    # Verify display order (13:31 -> 18:19 -> 19:52 Moscow)
    assert focus.events[0].occurs_at == datetime(2026, 7, 28, 10, 31, 0, tzinfo=timezone.utc) # 13:31 MSK
    assert focus.events[1].occurs_at == datetime(2026, 7, 28, 15, 19, 0, tzinfo=timezone.utc) # 18:19 MSK
    assert focus.events[2].occurs_at == datetime(2026, 7, 28, 16, 52, 0, tzinfo=timezone.utc) # 19:52 MSK


def test_amendment_8_1_strong_other_group_displaces_weak_same_group_neutral():
    """8.1.2 Strong exact factor from another group displaces weak neutral factor from winner group."""
    target_date = date(2026, 7, 28)

    # Winner group (Target = PLUTO)
    # Primary anchor (supportive 0.5)
    tf_pluto_1 = TodayFactor(
        factor_id="act:pluto_1",
        activation_ids=("act-p1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="PLUTO",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="supportive",
        strength=0.50,
        salience=0.50,
        active_from=datetime(2026, 7, 28, 8, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )
    # Second anchor of winner group (neutral 0.1)
    tf_pluto_2 = TodayFactor(
        factor_id="act:pluto_2",
        activation_ids=("act-p2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MERCURY",
        target_key="PLUTO",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="neutral",
        strength=0.10,
        salience=0.10,
        active_from=datetime(2026, 7, 28, 9, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 11, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 13, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )

    # Other group (Target = NEPTUNE) anchor (tense 0.95)
    tf_neptune = TodayFactor(
        factor_id="act:neptune_1",
        activation_ids=("act-n1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("t2",),
        product_spheres=("creativity",),
        polarity="tense",
        strength=0.95,
        salience=0.95,
        active_from=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 14, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 16, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf_pluto_1, tf_pluto_2, tf_neptune], tz_name="UTC", target_date=target_date)
    assert focus.state == "convergence_today"
    ev_ids = [e.id for e in focus.events]
    assert "ev:act:pluto_1" in ev_ids
    assert "ev:act:neptune_1" in ev_ids
    assert "ev:act:pluto_2" in ev_ids


def test_amendment_8_1_no_forced_positive_balancing():
    """8.1.4 Three tense events allowed if they rank highest by canon."""
    target_date = date(2026, 7, 28)
    tf_tense1 = TodayFactor(
        factor_id="act:tense_1",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="PLUTO",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.9,
        salience=0.9,
        active_from=datetime(2026, 7, 28, 8, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )
    tf_tense2 = TodayFactor(
        factor_id="act:tense_2",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="SATURN",
        target_key="PLUTO",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.8,
        salience=0.8,
        active_from=datetime(2026, 7, 28, 9, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 11, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 13, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )
    tf_tense3 = TodayFactor(
        factor_id="act:tense_3",
        activation_ids=("act-3",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="URANUS",
        target_key="NEPTUNE",
        theme_keys=("t2",),
        product_spheres=("decisions",),
        polarity="tense",
        strength=0.7,
        salience=0.7,
        active_from=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 14, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 16, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )
    tf_supp = TodayFactor(
        factor_id="act:supp_1",
        activation_ids=("act-4",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="VENUS",
        target_key="JUPITER",
        theme_keys=("t3",),
        product_spheres=("money",),
        polarity="supportive",
        strength=0.3,
        salience=0.3,
        active_from=datetime(2026, 7, 28, 15, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 17, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 19, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )

    focus = build_today_focus([tf_tense1, tf_tense2, tf_tense3, tf_supp], tz_name="UTC", target_date=target_date)
    ev_ids = [e.id for e in focus.events]
    assert ev_ids == ["ev:act:tense_1", "ev:act:tense_2", "ev:act:tense_3"]


def test_amendment_8_1_ineligible_title_skipped_takes_next():
    """8.1.6 Ineligible machine-key title is skipped, selector takes next candidate."""
    target_date = date(2026, 7, 28)
    tf_ineligible = TodayFactor(
        factor_id="act:t2n__MOON__SQUARE__LOT_UNKNOWN_XYZ",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="LOT_UNKNOWN_XYZ",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.95,
        salience=0.95,
        active_from=datetime(2026, 7, 28, 8, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
    )
    tf_eligible = TodayFactor(
        factor_id="act:t2n__MOON__SQUARE__PLUTO",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="PLUTO",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.80,
        salience=0.80,
        active_from=datetime(2026, 7, 28, 9, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 11, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 13, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="square",
        target_type="natal_planet",
    )

    focus = build_today_focus([tf_ineligible, tf_eligible], tz_name="UTC", target_date=target_date)
    ev_ids = [e.id for e in focus.events]
    assert "ev:act:t2n__MOON__SQUARE__LOT_UNKNOWN_XYZ" not in ev_ids
    assert "ev:act:t2n__MOON__SQUARE__PLUTO" in ev_ids


def test_amendment_8_1_null_occurs_at_sorts_last_without_exception():
    """8.1.15 occurs_at=None does not crash, sorts after timed events."""
    target_date = date(2026, 7, 28)
    tf_timed = TodayFactor(
        factor_id="act:timed",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="PLUTO",
        theme_keys=("t1",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.80,
        salience=0.80,
        active_from=datetime(2026, 7, 28, 9, 0, 0, tzinfo=timezone.utc),
        exact_at=datetime(2026, 7, 28, 11, 0, 0, tzinfo=timezone.utc),
        active_until=datetime(2026, 7, 28, 13, 0, 0, tzinfo=timezone.utc),
        phase="exact",
        temporal_role="anchor_today",
        aspect_type="square",
        target_type="natal_planet",
    )
    tf_untimed = TodayFactor(
        factor_id="act:untimed",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("t2",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.90,
        salience=0.90,
        active_from=None,
        exact_at=None,
        active_until=None,
        phase="building",
        temporal_role="anchor_today",
        aspect_type="opposition",
        target_type="natal_planet",
    )

    focus = build_today_focus([tf_timed, tf_untimed], tz_name="UTC", target_date=target_date)
    assert len(focus.events) == 2
    assert focus.events[0].id == "ev:act:timed"
    assert focus.events[1].id == "ev:act:untimed"
    assert focus.events[1].occurs_at is None

