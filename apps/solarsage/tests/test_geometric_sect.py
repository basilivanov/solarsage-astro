# ############################################################################
# AI_HEADER: TEST_GEOMETRIC_SECT — geometric day/night chart regression tests.
# ROLE: Proves sect follows true solar altitude at the birth event and is
#       independent of the requested house system.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-GEOMETRIC-SECT
# purpose: Guard the convergence rewrite's geometric sect rule.
# owns:
#   - apps/solarsage/tests/test_geometric_sect.py
# inputs: Swiss Ephemeris calculations and activation-layer builder.
# outputs: pytest assertions for altitude sign, coordinate validation, and
#   firdar audit provenance.
# dependencies: solarsage.utils.ephemeris; activation_builder.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Positive true altitude means day; non-positive means night.
#   - House-system selection cannot change sect or firdar lords.
# failure_policy: tests fail on any contract drift.
# END_MODULE_CONTRACT: M-TEST-GEOMETRIC-SECT

# START_MODULE_MAP: M-TEST-GEOMETRIC-SECT
# public_entrypoints: none
# semantic_blocks:
#   - SOLAR_ALTITUDE: true-altitude and validation proof.
#   - FIRDAR_PROVENANCE: house-independent sect integration proof.
# owned_tests:
#   - apps/solarsage/tests/test_geometric_sect.py
# END_MODULE_MAP: M-TEST-GEOMETRIC-SECT

from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("moshier_mode")

from solarsage.services.activation_builder import build_activation_layer
from solarsage.utils.ephemeris import (
    calculate_julian_day,
    calculate_solar_altitude,
)


# START_BLOCK: SOLAR_ALTITUDE
def test_true_solar_altitude_separates_day_and_night() -> None:
    noon_jd = calculate_julian_day("2026-06-21", "12:00", "Europe/Moscow")
    midnight_jd = calculate_julian_day("2026-06-21", "00:00", "Europe/Moscow")

    noon = calculate_solar_altitude(noon_jd, 55.7558, 37.6173)
    midnight = calculate_solar_altitude(midnight_jd, 55.7558, 37.6173)

    assert noon > 0.0
    assert midnight < 0.0


@pytest.mark.parametrize(
    ("lat", "lon", "message"),
    [
        (90.1, 37.6173, "Latitude"),
        (55.7558, 180.1, "Longitude"),
    ],
)
def test_solar_altitude_rejects_invalid_coordinates(
    lat: float,
    lon: float,
    message: str,
) -> None:
    jd = calculate_julian_day("2026-06-21", "12:00", "UTC")
    with pytest.raises(ValueError, match=message):
        calculate_solar_altitude(jd, lat, lon)
# END_BLOCK: SOLAR_ALTITUDE


# START_BLOCK: FIRDAR_PROVENANCE
def _firdar_major_debug(house_system: str) -> tuple[str, dict]:
    layer = build_activation_layer(
        birth_date="1990-01-15",
        birth_time="14:30",
        birth_lat=55.7558,
        birth_lon=37.6173,
        birth_tz="Europe/Moscow",
        target_date="2026-06-15",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system=house_system,
        techniques=["firdar_major"],
    )
    event = next(item for item in layer.activations if item.technique == "firdar_major")
    return event.target_key, event.debug


def test_firdar_sect_is_geometric_and_house_system_independent() -> None:
    placidus_lord, placidus_debug = _firdar_major_debug("PLACIDUS")
    whole_sign_lord, whole_sign_debug = _firdar_major_debug("WHOLE_SIGN")

    assert placidus_lord == whole_sign_lord == "MOON"
    assert placidus_debug["is_day_birth"] is True
    assert whole_sign_debug["is_day_birth"] is True
    assert placidus_debug["sect_basis"] == "geometric_sun_altitude"
    assert whole_sign_debug["sect_basis"] == "geometric_sun_altitude"
    assert placidus_debug["sun_altitude_deg"] == whole_sign_debug["sun_altitude_deg"]
    assert placidus_debug["sun_altitude_deg"] > 0.0
    assert placidus_debug["sun_house_role"] == "audit_only"
# END_BLOCK: FIRDAR_PROVENANCE


# START_BLOCK: HIGH_LAT_WINTER_STABILITY
def _firdar_is_day(birth_date: str, birth_time: str, lat: float, lon: float, tz: str) -> tuple[bool, str, dict]:
    layer = build_activation_layer(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_lat=lat,
        birth_lon=lon,
        birth_tz=tz,
        target_date="2026-06-15",
        target_time="12:00",
        target_tz=tz,
        house_system="PLACIDUS",
        techniques=["firdar_major"],
    )
    event = next(item for item in layer.activations if item.technique == "firdar_major")
    return event.debug["is_day_birth"], event.target_key, event.debug


# Owner-like synthetic: high-latitude winter with ~9h of daylight. The old
# Whole-Sign-house rule flipped sect at 13:00/16:00/17:00 here; the geometric
# rule must stay constant across the daylight window 12:00-16:00.
def test_high_latitude_winter_no_spurious_flips_12_to_16() -> None:
    results = [
        _firdar_is_day("1991-03-10", f"{h:02d}:00", 64.0, 25.0, "Europe/Helsinki")
        for h in range(12, 17)
    ]
    # self-check: geometric daylight really covers the whole window
    for h in range(12, 17):
        jd = calculate_julian_day("1991-03-10", f"{h:02d}:00", "Europe/Helsinki")
        assert calculate_solar_altitude(jd, 64.0, 25.0) > 0.0
    sects = {is_day for is_day, _lord, _dbg in results}
    lords = {lord for _is_day, lord, _dbg in results}
    assert sects == {True}
    assert len(lords) == 1
# END_BLOCK: HIGH_LAT_WINTER_STABILITY


# START_BLOCK: RISE_SET_BOUNDARY
def _rise_set_jd(jd_start: float, lat: float, lon: float, rsmi: int) -> float:
    import swisseph as swe

    # Disc-centre, no refraction: matches the sect rule's true-altitude-0
    # convention (apparent rise/set would be ~50 arcmin earlier/later).
    flags = rsmi | swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION
    _ret, tret = swe.rise_trans(jd_start, swe.SUN, flags, (lon, lat, 0.0), 0.0, 0.0, swe.FLG_SWIEPH)
    return float(tret[0])


def test_sect_flips_exactly_at_geometric_rise_and_set() -> None:
    import swisseph as swe

    lat, lon, tz = 64.0, 25.0, "Europe/Helsinki"
    # Anchor: local birth-date midnight, then the first rise and the first
    # set after it — both belong to the same local birth date.
    jd_midnight = calculate_julian_day("1991-03-10", "00:00", tz) - 0.5
    rise_jd = _rise_set_jd(jd_midnight, lat, lon, swe.CALC_RISE)
    set_jd = _rise_set_jd(rise_jd + 1e-4, lat, lon, swe.CALC_SET)
    assert rise_jd < set_jd

    for event_jd, before_expect, after_expect in (
        (rise_jd, False, True),
        (set_jd, True, False),
    ):
        assert (calculate_solar_altitude(event_jd - 2.0 / 1440.0, lat, lon) > 0.0) == before_expect
        assert (calculate_solar_altitude(event_jd + 2.0 / 1440.0, lat, lon) > 0.0) == after_expect
# END_BLOCK: RISE_SET_BOUNDARY


# START_BLOCK: POLAR_CONDITION
def test_polar_day_and_polar_night_are_explicit() -> None:
    _is_day_s, _lord_s, debug_summer = _firdar_is_day("2026-06-21", "12:00", 70.0, 25.7, "Europe/Helsinki")
    assert _is_day_s is True
    assert debug_summer["sect_polar_condition"] == "polar_day"
    assert debug_summer["sect_basis"] == "geometric_sun_altitude"

    _is_day_w, _lord_w, debug_winter = _firdar_is_day("2026-01-15", "12:00", 70.0, 25.7, "Europe/Helsinki")
    assert _is_day_w is False
    assert debug_winter["sect_polar_condition"] == "polar_night"

    _is_day_m, _lord_m, debug_normal = _firdar_is_day("2026-03-21", "12:00", 55.7558, 37.6173, "Europe/Moscow")
    assert debug_normal["sect_polar_condition"] is None
# END_BLOCK: POLAR_CONDITION


# START_BLOCK: NORMAL_LATITUDE_REGRESSION
def test_normal_latitude_matches_plain_horizon_rule() -> None:
    # Clear-cut hours at normal latitude: geometric sect must agree with the
    # naive "Sun above/below horizon" expectation and with Placidus house>=7.
    from solarsage.services.activation_builder import prepare_natal_context

    noon = prepare_natal_context(
        birth_date="2026-06-21", birth_time="12:00",
        birth_lat=55.7558, birth_lon=37.6173, birth_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    midnight = prepare_natal_context(
        birth_date="2026-06-21", birth_time="00:00",
        birth_lat=55.7558, birth_lon=37.6173, birth_tz="Europe/Moscow",
        house_system="PLACIDUS",
    )
    assert noon.is_day is True and noon.sun_altitude_deg > 0.0
    assert midnight.is_day is False and midnight.sun_altitude_deg <= 0.0
    # regression vs the retired rule at non-boundary hours
    assert (noon.natal_sun_house is not None and noon.natal_sun_house >= 7) == noon.is_day
    assert (midnight.natal_sun_house is not None and midnight.natal_sun_house >= 7) == midnight.is_day
# END_BLOCK: NORMAL_LATITUDE_REGRESSION
