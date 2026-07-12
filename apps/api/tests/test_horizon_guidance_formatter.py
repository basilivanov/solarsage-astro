# ############################################################################
# AI_HEADER: TEST_HORIZON_GUIDANCE_FORMATTER — B2B2 deterministic formatter tests.
# ROLE: Proves timing formatting (validate first, human labels, entities,
#       technique templates) and manifestation splitting.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-GUIDANCE-FORMATTER
# purpose: Test pure formatting helpers: validate first, human labels,
#          entity mappings, and manifestation splits.
# owns:
#   - apps/api/tests/test_horizon_guidance_formatter.py
# inputs: Synthetic raw timing strings and entity keys.
# outputs: Assertions over formatted labels, display invariants, and error
#          codes.
# dependencies: pytest, guidance formatter, content canon service.
# side_effects: reads cached content canon.
# emitted_logs: none.
# invariants:
#   - No server-local timezone, network, DB, or clock involved.
# failure_policy: test failures identify formatting regression.
# END_MODULE_CONTRACT: M-TEST-HORIZON-GUIDANCE-FORMATTER

# START_MODULE_MAP: M-TEST-HORIZON-GUIDANCE-FORMATTER
# public_entrypoints:
#   - test_date_russian_genitive
#   - test_instant_utc
#   - test_moscow_conversion
#   - test_new_york_dst
#   - test_berlin_dst
#   - test_leap_day_2028
#   - test_invalid_timezone_rejects
#   - test_invalid_calendar_date_rejects
#   - test_state_label_exact
#   - test_long_valid_until_human
#   - test_medium_valid_until_human
#   - test_fast_valid_until_human
#   - test_long_instant_suffix
#   - test_peak_null_only_long
#   - test_house_boundaries
#   - test_missing_transit_source_fails
#   - test_no_raw_fallback_entity
#   - test_manifestation_split_valid
#   - test_manifestation_split_missing_comma
#   - test_manifestation_split_bad_prefix
#   - test_r5_raw_enum_values_sanitized
# semantic_blocks:
#   - FORMATTER_TIMING_TESTS
#   - FORMATTER_ENTITY_TESTS
#   - FORMATTER_MANIFESTATION_TESTS
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_formatter.py
# END_MODULE_MAP: M-TEST-HORIZON-GUIDANCE-FORMATTER

# START_BLOCK: FORMATTER_TIMING_TESTS
from __future__ import annotations

import pytest

from app.schemas.horizon_guidance import HorizonGuidanceError
from app.schemas.horizon_selection import HorizonTimingAssessment
from app.services.horizon_guidance_formatter import HorizonGuidanceFormatter


def _make_timing(
    precision: str = "date",
    state: str = "active",
    active_from: str = "2026-01-01",
    exact_at: str | None = "2026-07-15",
    active_until: str = "2026-12-31",
    timezone: str = "Europe/Moscow",
) -> HorizonTimingAssessment:
    return HorizonTimingAssessment(
        activation_id="test",
        precision=precision,  # type: ignore
        active_from=active_from,
        exact_at=exact_at,
        active_until=active_until,
        timezone=timezone,
        target_local="2026-07-12T12:00:00",
        target_utc="2026-07-12T09:00:00Z",
        duration_seconds=3600.0,
        duration_days=1.0,
        relative_position="inside",
        timing_state=state,  # type: ignore
        timing_completeness=1.0,
        eligible_horizons=["long", "medium", "fast"],
        preferred_horizons=["medium", "fast"],
        is_anchor_eligible=True,
    )


def test_date_russian_genitive() -> None:
    """Prove date precision renders Russian genitive month names."""
    # START_FUNCTION_CONTRACT: F-TEST.test_date_russian_genitive
    # purpose: test date russian genitive.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_date_russian_genitive
    f = HorizonGuidanceFormatter()
    tests = [
        ("2026-01-08", "8 января 2026"),
        ("2026-05-01", "1 мая 2026"),
        ("2026-07-12", "12 июля 2026"),
        ("2026-12-31", "31 декабря 2026"),
    ]
    for raw, expected in tests:
        result = f._validate_date_label(raw)
        assert result == expected, f"{raw} -> {result} != {expected}"


def test_instant_utc() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_instant_utc
    # purpose: test instant utc.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_instant_utc
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-01-01T00:00:00Z",
        exact_at="2026-07-12T12:00:00Z",
        active_until="2026-12-31T23:59:00Z",
        timezone="UTC",
    )
    pres = f.format_timing(horizon="medium", timing=t)
    assert "12 июля 2026, 12:00" in pres.exact_at_label or ""
    assert "UTC" in pres.timezone_suffix


def test_moscow_conversion() -> None:
    """09:00 UTC -> 12:00 MSK with 'по Москве' suffix."""
    # START_FUNCTION_CONTRACT: F-TEST.test_moscow_conversion
    # purpose: test moscow conversion.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_moscow_conversion
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-07-01T00:00:00Z",
        exact_at="2026-07-12T09:00:00Z",
        active_until="2026-07-20T00:00:00Z",
        timezone="Europe/Moscow",
    )
    pres = f.format_timing(horizon="fast", timing=t)
    assert "по Москве" in pres.timezone_suffix
    assert "12:00" in (pres.exact_at_label or "")


def test_new_york_dst() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_new_york_dst
    # purpose: test new york dst.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_new_york_dst
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-03-01T00:00:00Z",
        exact_at="2026-07-12T16:00:00Z",
        active_until="2026-09-01T00:00:00Z",
        timezone="America/New_York",
    )
    pres = f.format_timing(horizon="medium", timing=t)
    assert "(America/New_York)" in pres.timezone_suffix


def test_berlin_dst() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_berlin_dst
    # purpose: test berlin dst.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_berlin_dst
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-10-01T00:00:00Z",
        exact_at="2026-10-25T10:00:00Z",
        active_until="2026-11-01T00:00:00Z",
        timezone="Europe/Berlin",
    )
    pres = f.format_timing(horizon="medium", timing=t)
    assert "(Europe/Berlin)" in pres.timezone_suffix


def test_leap_day_2028() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_leap_day_2028
    # purpose: test leap day 2028.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_leap_day_2028
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        active_from="2028-01-01",
        exact_at="2028-02-29",
        active_until="2028-12-31",
    )
    pres = f.format_timing(horizon="medium", timing=t)
    assert pres.public_timing.peak_label is not None
    assert "29 февраля 2028" in pres.public_timing.peak_label


def test_invalid_timezone_rejects() -> None:
    """Unknown timezone raises invalid_timezone."""
    # START_FUNCTION_CONTRACT: F-TEST.test_invalid_timezone_rejects
    # purpose: test invalid timezone rejects.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_invalid_timezone_rejects
    f = HorizonGuidanceFormatter()
    t = _make_timing(timezone="Not/A_Zone")
    with pytest.raises(HorizonGuidanceError, match="invalid_timezone"):
        f.format_timing(horizon="medium", timing=t)


def test_invalid_calendar_date_rejects() -> None:
    """Bogus date raises invalid_timing_value."""
    # START_FUNCTION_CONTRACT: F-TEST.test_invalid_calendar_date_rejects
    # purpose: test invalid calendar date rejects.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_invalid_calendar_date_rejects
    f = HorizonGuidanceFormatter()
    t = _make_timing(active_from="2026-13-01")
    with pytest.raises(HorizonGuidanceError, match="invalid_timing_value"):
        f.format_timing(horizon="medium", timing=t)


def test_state_label_exact() -> None:
    """State label is a non-empty canon key."""
    # START_FUNCTION_CONTRACT: F-TEST.test_state_label_exact
    # purpose: test state label exact.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_state_label_exact
    f = HorizonGuidanceFormatter()
    t = _make_timing(state="exact")
    pres = f.format_timing(horizon="medium", timing=t)
    assert pres.public_timing.state_label


def test_long_valid_until_human() -> None:
    """Long valid_until is a human label, not raw machine."""
    # START_FUNCTION_CONTRACT: F-TEST.test_long_valid_until_human
    # purpose: test long valid until human.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_long_valid_until_human
    f = HorizonGuidanceFormatter()
    t = _make_timing(exact_at=None)
    pres = f.format_timing(horizon="long", timing=t)
    label = pres.valid_until_label
    assert label
    assert "2026" in label
    assert "T" not in label


def test_medium_valid_until_human() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_medium_valid_until_human
    # purpose: test medium valid until human.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_medium_valid_until_human
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-01-01T00:00:00Z",
        exact_at="2026-07-15T00:00:00Z",
        active_until="2026-10-01T00:00:00Z",
    )
    pres = f.format_timing(horizon="medium", timing=t)
    label = pres.valid_until_label
    assert label
    assert "T" not in label


def test_fast_valid_until_human() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_fast_valid_until_human
    # purpose: test fast valid until human.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_fast_valid_until_human
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-07-01T00:00:00Z",
        exact_at="2026-07-10T00:00:00Z",
        active_until="2026-07-12T00:00:00Z",
    )
    pres = f.format_timing(horizon="fast", timing=t)
    label = pres.valid_until_label
    assert label
    assert "T" not in label


def test_long_instant_suffix() -> None:
    """Long instant range carries timezone suffix."""
    # START_FUNCTION_CONTRACT: F-TEST.test_long_instant_suffix
    # purpose: test long instant suffix.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_long_instant_suffix
    f = HorizonGuidanceFormatter()
    t = _make_timing(
        precision="instant",
        active_from="2026-01-01T00:00:00Z",
        exact_at=None,
        active_until="2026-12-31T00:00:00Z",
    )
    pres = f.format_timing(horizon="long", timing=t)
    assert pres.timezone_suffix


def test_peak_null_only_long() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_peak_null_only_long
    # purpose: test peak null only long.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_peak_null_only_long
    f = HorizonGuidanceFormatter()
    t = _make_timing(exact_at=None)
    pres = f.format_timing(horizon="long", timing=t)
    assert pres.public_timing.peak_label is None
    assert pres.exact_at_label is None


def test_house_boundaries() -> None:
    """House 1-12 valid; 0, 13, raw reject."""
    # START_FUNCTION_CONTRACT: F-TEST.test_house_boundaries
    # purpose: test house boundaries.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_house_boundaries
    f = HorizonGuidanceFormatter()
    # Valid houses
    f.target_label("house", "1")
    f.target_label("house", "12")
    # Invalid
    with pytest.raises(HorizonGuidanceError, match="unsupported_entity_label"):
        f.target_label("house", "0")
    with pytest.raises(HorizonGuidanceError, match="unsupported_entity_label"):
        f.target_label("house", "13")
    with pytest.raises(HorizonGuidanceError, match="unsupported_entity_label"):
        f.target_label("house", "abc")


def test_missing_transit_source_fails() -> None:
    """Missing transit source raises unsupported_entity_label, not generic."""
    # START_FUNCTION_CONTRACT: F-TEST.test_missing_transit_source_fails
    # purpose: test missing transit source fails.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_missing_transit_source_fails
    f = HorizonGuidanceFormatter()
    with pytest.raises(HorizonGuidanceError, match="unsupported_entity_label"):
        f.source_label(None)


def test_no_raw_fallback_entity() -> None:
    """Unknown entity key raises, not raw fallback."""
    # START_FUNCTION_CONTRACT: F-TEST.test_no_raw_fallback_entity
    # purpose: test no raw fallback entity.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_no_raw_fallback_entity
    f = HorizonGuidanceFormatter()
    with pytest.raises(HorizonGuidanceError, match="unsupported_entity_label"):
        f.entity_display("UNKNOWN_ENTITY")


# END_BLOCK: FORMATTER_TIMING_TESTS

# START_BLOCK: FORMATTER_MANIFESTATION_TESTS
def test_manifestation_split_valid() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_manifestation_split_valid
    # purpose: test manifestation split valid.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_manifestation_split_valid
    f = HorizonGuidanceFormatter()
    prefixes = ("Если",)
    body = "Если вы заняты работой, сосредоточьтесь на главном."
    cond, tail = f.split_manifestation(body, prefixes)
    assert cond == "Если вы заняты работой"
    assert tail == "Сосредоточьтесь на главном."


def test_manifestation_split_missing_comma() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_manifestation_split_missing_comma
    # purpose: test manifestation split missing comma.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_manifestation_split_missing_comma
    f = HorizonGuidanceFormatter()
    with pytest.raises(HorizonGuidanceError, match="invalid_manifestation_copy"):
        f.split_manifestation("Если нет запятой", ("Если",))


def test_manifestation_split_bad_prefix() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_manifestation_split_bad_prefix
    # purpose: test manifestation split bad prefix.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_manifestation_split_bad_prefix
    f = HorizonGuidanceFormatter()
    with pytest.raises(HorizonGuidanceError, match="invalid_manifestation_copy"):
        f.split_manifestation("При условии, что сделано.", ("Если",))


def test_formatter_sanitized_exceptions() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_formatter_sanitized_exceptions
    # purpose: Assert formatter exceptions contain no raw input or sentinels.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on sentinel or raw input leak.
    # END_FUNCTION_CONTRACT: F-TEST.test_formatter_sanitized_exceptions
    f = HorizonGuidanceFormatter()
    sentinels = [
        "RAW_EVIDENCE_SENTINEL",
        "RAW_DEBUG_SENTINEL",
        "PROFILE_NAME_SENTINEL",
        "PROFILE_CITY_SENTINEL",
        "COORDINATE_SENTINEL",
        "SESSION_SENTINEL",
    ]
    for s in sentinels:
        try:
            f.target_label("planet", s)
            pytest.fail("expected error")
        except HorizonGuidanceError as exc:
            msg = str(exc)
            assert exc.code == "unsupported_entity_label"
            assert s not in msg
        try:
            f.target_label("angle", s)
            pytest.fail("expected error")
        except HorizonGuidanceError as exc:
            msg = str(exc)
            assert exc.code == "unsupported_entity_label"
            assert s not in msg
        try:
            f.target_label("sphere", s)
            pytest.fail("expected error")
        except HorizonGuidanceError as exc:
            msg = str(exc)
            assert exc.code == "unsupported_entity_label"
            assert s not in msg
        try:
            f.source_label(s)
            pytest.fail("expected error")
        except HorizonGuidanceError as exc:
            msg = str(exc)
            assert exc.code == "unsupported_entity_label"
            assert s not in msg
        try:
            f.entity_display(s)
            pytest.fail("expected error")
        except HorizonGuidanceError as exc:
            msg = str(exc)
            assert exc.code == "unsupported_entity_label"
            assert s not in msg


def test_r5_raw_enum_values_sanitized() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.test_r5_raw_enum_values_sanitized
    # purpose: Prove invalid precision and target type are replaced by stable structural paths.
    # inputs: unique enum-like sentinels.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on wrong code or raw-value leakage.
    # END_FUNCTION_CONTRACT: F-TEST.test_r5_raw_enum_values_sanitized
    formatter = HorizonGuidanceFormatter()
    timing = _make_timing().model_copy(update={"precision": "R5_PRECISION_SENTINEL"})
    with pytest.raises(HorizonGuidanceError) as precision_exc:
        formatter.format_timing(horizon="long", timing=timing)
    assert precision_exc.value.code == "invalid_timing_value"
    assert str(precision_exc.value) == "invalid_timing_value | timing.precision"
    with pytest.raises(HorizonGuidanceError) as target_exc:
        formatter.target_label("R5_TARGET_TYPE_SENTINEL", "SUN")
    assert target_exc.value.code == "unknown_entity_label"
    assert str(target_exc.value) == "unknown_entity_label | target_type"


# END_BLOCK: FORMATTER_MANIFESTATION_TESTS
