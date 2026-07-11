# ############################################################################
# AI_HEADER: MODULE_SIDECAR_TEST_TRANSIT_TIMING — tests for TransitTimingSolver.
# ROLE: Verifies that the transit timing solver computes correct boundaries and roots.
# DEPENDENCIES: pytest, solarsage/services/transit_timing, solarsage/schemas/activation
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SIDECAR-TRANSIT-TIMING
# purpose: Test TransitTimingSolver on synthetic planet positions and wraps.
# owns:
#   - apps/solarsage/tests/test_transit_timing.py
# inputs: mock position providers
# outputs: pytest assertion results
# dependencies: solarsage/services/transit_timing.py
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - exact_at is correct within 60s
#   - active_from/active_until correct within 300s
# failure_policy: fail test
# END_MODULE_CONTRACT: M-TEST-SIDECAR-TRANSIT-TIMING

# START_MODULE_MAP: M-TEST-SIDECAR-TRANSIT-TIMING
# public_entrypoints: test functions
# semantic_blocks:
#   - SOLVER_TESTS: direct pass, wrapping, retrograde, tangent, near-miss, cache reuse, determinism.
# owned_tests:
#   - apps/solarsage/tests/test_transit_timing.py
# END_MODULE_MAP: M-TEST-SIDECAR-TRANSIT-TIMING

# START_BLOCK: SOLVER_TESTS
from datetime import datetime, timezone
import pytest
from solarsage.services.transit_timing import (
    TransitTimingSolver,
    TransitPositionCache,
    TransitTimingError,
    signed_delta,
)
from solarsage.utils.ephemeris import julian_day_to_utc_iso


def parse_utc_z(value: str) -> datetime:
    assert value.endswith("Z")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    assert parsed.tzinfo is not None
    return parsed.astimezone(timezone.utc)


def seconds_between(actual: str | None, expected: str) -> float:
    assert actual is not None
    return abs((parse_utc_z(actual) - parse_utc_z(expected)).total_seconds())


def utc_z_to_jd(value: str) -> float:
    parsed = parse_utc_z(value)
    return parsed.timestamp() / 86400.0 + 2440587.5


def test_julian_day_to_utc_iso():
    # test julian_day_to_utc_iso formats correctly and ends with Z
    jd = 2461229.875  # 2026-07-08T09:00:00
    iso = julian_day_to_utc_iso(jd)
    assert iso.endswith("Z")
    assert "2026-07-08T09:00:00" in iso


def test_signed_delta():
    assert signed_delta(10.0, 5.0) == 5.0
    assert signed_delta(5.0, 10.0) == -5.0
    assert signed_delta(359.0, 1.0) == -2.0
    assert signed_delta(1.0, 359.0) == 2.0


def test_direct_linear_pass():
    """1. Direct linear pass of a planet over target longitude."""
    # Planet starts at 9.0 jd=0, exact at 10.0 jd=1, goes to 11.0 jd=2. Target exact=10.0. Max orb=0.5.
    # jd_exact = 1.0 (exact_at = 2026-07-08T12:00:00Z if target_jd=2461230.0)
    # inside from jd=0.5 to jd=1.5.
    target_jd = 2461230.0  # 2026-07-08T12:00:00Z

    def mock_calc(jd: float, planet_id: int):
        # speed = 1.0 degree/day.
        # longitude = 10.0 + (jd - target_jd) * 1.0
        lon = (10.0 + (jd - target_jd) * 1.0) % 360.0
        return lon, 1.0

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    result = solver.solve(
        source_planet="Moon",
        target_longitude=10.0,
        aspect_angle=0.0,
        max_orb=0.5,
    )

    # exact_at is 2026-07-08T12:00:00Z
    assert seconds_between(result.exact_at_utc, "2026-07-08T12:00:00Z") <= 1.0
    assert result.phase == "exact"
    assert result.applying is False
    assert result.occurrence_index == 0
    assert len(result.exact_hits_in_window) == 1
    assert result.selected_branch == "plus"
    assert abs(result.selected_exact_longitude - 10.0) <= 1e-9
    exact_jd = utc_z_to_jd(result.exact_at_utc)
    exact_lon, _ = mock_calc(exact_jd, 0)
    assert abs(signed_delta(exact_lon, result.selected_exact_longitude)) <= 1e-5

    # active_from should be 12 hours before target_jd -> 2026-07-08T00:00:00Z
    assert seconds_between(result.active_from_utc, "2026-07-08T00:00:00Z") <= 300.0
    assert seconds_between(result.active_until_utc, "2026-07-09T00:00:00Z") <= 300.0


def test_controlled_minus_branch_debug_values():
    """Controlled minus branch exposes the exact branch/longitude used by root solving."""
    target_jd = 2461230.0

    def mock_calc(jd: float, planet_id: int):
        lon = (105.0 + (jd - target_jd) * 1.0) % 360.0
        return lon, 1.0

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    result = solver.solve(
        source_planet="Sun",
        target_longitude=225.0,
        aspect_angle=120.0,
        max_orb=0.5,
    )

    assert result.selected_branch == "minus"
    assert abs(result.selected_exact_longitude - 105.0) <= 1e-9
    assert seconds_between(result.exact_at_utc, "2026-07-08T12:00:00Z") <= 1.0
    exact_jd = utc_z_to_jd(result.exact_at_utc)
    exact_lon, _ = mock_calc(exact_jd, 0)
    assert abs(signed_delta(exact_lon, result.selected_exact_longitude)) <= 1e-5


def test_wrap_pass():
    """2. 0°/360° wrap test."""
    target_jd = 2461230.0

    def mock_calc(jd: float, planet_id: int):
        # longitude goes from 359 -> 0 -> 1. Exact at 0.0, jd=target_jd
        lon = ((jd - target_jd) * 1.0) % 360.0
        return lon, 1.0

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    result = solver.solve(
        source_planet="Moon",
        target_longitude=0.0,
        aspect_angle=0.0,
        max_orb=0.5,
    )

    assert seconds_between(result.exact_at_utc, "2026-07-08T12:00:00Z") <= 1.0
    assert result.phase == "exact"
    assert result.occurrence_index == 0


def test_retrograde_triple_pass():
    """3. Retrograde triple pass in one contiguous window."""
    target_jd = 2461230.0

    # We model a cubic residual: g(x) = 0.25 * (x + 2) * x * (x - 2)
    # x = jd - target_jd
    # Roots at x = -2, 0, +2 days.
    # Max speed is at x=0 (g'(0) = -1.0).
    # Let's verify roots:
    # x = -2: g(-2) = 0.0
    # x = 0: g(0) = 0.0
    # x = 2: g(2) = 0.0
    # Let's set max_orb = 2.0 degrees, so all three roots fall inside one contiguous window.
    # At x = -2.5, g(-2.5) = 0.25 * (-0.5) * (-2.5) * (-4.5) = -2.8125 (outside orb).
    # At x = 2.5, g(2.5) = 2.8125 (outside).
    # Let's write the position provider.
    def mock_calc(jd: float, planet_id: int):
        x = jd - target_jd
        lon = (10.0 + 0.25 * (x + 2.0) * x * (x - 2.0)) % 360.0
        speed = 0.25 * (3.0 * x * x - 4.0)
        return lon, speed

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    # Let's solve at target_jd (x=0). This is one of the exact hits.
    result = solver.solve(
        source_planet="Moon",
        target_longitude=10.0,
        aspect_angle=0.0,
        max_orb=2.0,
    )

    assert len(result.exact_hits_in_window) == 3
    # Roots must be sorted: -2 days, 0 days, +2 days
    assert seconds_between(result.exact_hits_in_window[0], "2026-07-06T12:00:00Z") <= 1.0
    assert seconds_between(result.exact_hits_in_window[1], "2026-07-08T12:00:00Z") <= 1.0
    assert seconds_between(result.exact_hits_in_window[2], "2026-07-10T12:00:00Z") <= 1.0

    assert seconds_between(result.exact_at_utc, "2026-07-08T12:00:00Z") <= 1.0
    assert result.occurrence_index == 1
    assert result.phase == "exact"


def test_tangent_exact_at_station():
    """4. Tangent exact at station (speed=0, residual=0)."""
    target_jd = 2461230.0

    # g(x) = (x - 1)^2. Station at x=1.0 (jd = target_jd + 1.0).
    # Residual touches 0.0 at x=1.0.
    def mock_calc(jd: float, planet_id: int):
        x = jd - target_jd
        lon = (10.0 + (x - 1.0) ** 2) % 360.0
        speed = 2.0 * (x - 1.0)
        return lon, speed

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    result = solver.solve(
        source_planet="Moon",
        target_longitude=10.0,
        aspect_angle=0.0,
        max_orb=1.0,
    )

    # exact_at is target_jd + 1.0 -> 2026-07-09T12:00:00Z
    assert seconds_between(result.exact_at_utc, "2026-07-09T12:00:00Z") <= 1.0
    assert result.phase == "applying"
    assert result.applying is True
    assert result.occurrence_index == 0


def test_near_miss_at_station():
    """5. Near-miss at station (touches, but doesn't reach target)."""
    target_jd = 2461230.0

    # g(x) = (x - 0.2)^2 + 0.1. Minimum is at x=0.2 (jd = target_jd + 0.2), value is 0.1.
    # Target is 10.0. Max orb is 0.5.
    # At target_jd (x=0), value is 10.14, which is inside max_orb (0.14 <= 0.5).
    # It enters orb (value <= 0.5), reaches closest point (0.1), and exits orb.
    # No exact hit (value never reaches 0.0).
    def mock_calc(jd: float, planet_id: int):
        x = jd - target_jd
        lon = (10.0 + (x - 0.2) ** 2 + 0.1) % 360.0
        speed = 2.0 * (x - 0.2)
        return lon, speed

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    result = solver.solve(
        source_planet="Moon",
        target_longitude=10.0,
        aspect_angle=0.0,
        max_orb=0.5,
    )

    assert result.exact_at_utc is None
    assert result.occurrence_index is None
    assert result.warning_code == "no_exact_hit_in_window"
    assert result.phase == "applying"
    assert result.applying is True


def test_boundary_not_bracketed():
    """6. Boundary not bracketed throws TransitTimingError."""
    target_jd = 2461230.0

    # Planet stays inside orb forever (constant longitude).
    def mock_calc(jd: float, planet_id: int):
        return 10.0, 0.0

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    with pytest.raises(TransitTimingError) as exc:
        solver.solve(
            source_planet="Moon",
            target_longitude=10.0,
            aspect_angle=0.0,
            max_orb=1.0,
        )
    assert "boundary_not_bracketed" in exc.value.code


def test_cache_and_grid_reuse():
    """7. Cache and grid reuse proof."""
    target_jd = 2461230.0

    call_count = 0

    def mock_calc(jd: float, planet_id: int):
        nonlocal call_count
        call_count += 1
        lon = (10.0 + (jd - target_jd) * 1.0) % 360.0
        return lon, 1.0

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    # Call solve once
    solver.solve(
        source_planet="Moon",
        target_longitude=10.0,
        aspect_angle=0.0,
        max_orb=0.5,
    )
    first_pass_calls = call_count

    # Call solve again with different target/aspect but same planet
    # It should reuse the coarse grids memoized in the solver instance
    solver.solve(
        source_planet="Moon",
        target_longitude=10.1,
        aspect_angle=0.0,
        max_orb=0.5,
    )
    
    extra_calls = call_count - first_pass_calls
    assert 0 < extra_calls < first_pass_calls
    assert cache.hits > 0


def test_lazy_grid_stops_at_first_outside_and_reuses_prefix():
    """Slow-source grid must expand lazily, not precompute the full horizon."""
    target_jd = 2461230.0
    seen_keys: set[tuple[int, float]] = set()
    duplicate_keys: list[tuple[int, float]] = []

    def mock_calc(jd: float, planet_id: int):
        key = (planet_id, round(jd, 10))
        if key in seen_keys:
            duplicate_keys.append(key)
        seen_keys.add(key)
        lon = (100.0 + (jd - target_jd) * 0.01) % 360.0
        return lon, 0.01

    cache = TransitPositionCache(calc_func=mock_calc)
    solver = TransitTimingSolver(target_jd=target_jd, position_cache=cache)

    first = solver.solve(
        source_planet="Pluto",
        target_longitude=100.0,
        aspect_angle=0.0,
        max_orb=0.1,
    )
    first_calls = cache.cache_misses
    forward_grid = solver.grids[(9, 1)]
    backward_grid = solver.grids[(9, -1)]
    first_forward_len = len(forward_grid)
    first_backward_len = len(backward_grid)
    assert first_calls < 80
    assert first_forward_len < 20
    assert first_backward_len < 20
    assert forward_grid[-1].jd < target_jd + 20000.0
    assert backward_grid[-1].jd > target_jd - 20000.0
    assert abs(signed_delta(forward_grid[-1].longitude, first.selected_exact_longitude)) > 0.1
    assert abs(signed_delta(forward_grid[-2].longitude, first.selected_exact_longitude)) <= 0.1 + 1e-9

    second = solver.solve(
        source_planet="Pluto",
        target_longitude=100.02,
        aspect_angle=0.0,
        max_orb=0.1,
    )
    second_extra_calls = cache.cache_misses - first_calls
    assert second_extra_calls > 0
    assert second_extra_calls < 80
    assert len(forward_grid) >= first_forward_len
    assert len(backward_grid) >= first_backward_len
    assert [pos.jd for pos in forward_grid[:first_forward_len]][-1] < target_jd + 20000.0
    assert [pos.jd for pos in backward_grid[:first_backward_len]][-1] > target_jd - 20000.0
    assert duplicate_keys == []
    assert second.active_from_utc <= second.exact_at_utc <= second.active_until_utc


def test_solver_determinism_includes_timing_debug_fields():
    target_jd = 2461230.0

    def mock_calc(jd: float, planet_id: int):
        lon = (10.0 + (jd - target_jd) * 1.0) % 360.0
        return lon, 1.0

    result_1 = TransitTimingSolver(
        target_jd=target_jd,
        position_cache=TransitPositionCache(calc_func=mock_calc),
    ).solve(source_planet="Moon", target_longitude=10.0, aspect_angle=0.0, max_orb=0.5)
    result_2 = TransitTimingSolver(
        target_jd=target_jd,
        position_cache=TransitPositionCache(calc_func=mock_calc),
    ).solve(source_planet="Moon", target_longitude=10.0, aspect_angle=0.0, max_orb=0.5)

    assert result_1 == result_2
# END_BLOCK: SOLVER_TESTS
