# ############################################################################
# AI_HEADER: MODULE_SIDECAR_TRANSIT_TIMING — transit timing window/exact crossing solver.
# ROLE: Solves active_from, exact_at, and active_until timestamps for transit aspects.
# DEPENDENCIES: swisseph, dataclasses, typing, solarsage.utils.ephemeris
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-TRANSIT-TIMING
# purpose: Solve exact timing and active window boundaries for planetary transits.
# owns:
#   - apps/solarsage/solarsage/services/transit_timing.py
# inputs: source planet name, target longitude, aspect angle, max orb.
# outputs: TransitTimingResult containing ISO UTC timestamps and warnings.
# dependencies: swisseph, solarsage/utils/ephemeris.
# side_effects: Calls Swiss Ephemeris single-planet calculations through an
#   injectable/cacheable provider; mutates request-scoped in-memory caches.
# emitted_logs: none.
# invariants:
#   - active_from <= target_jd <= active_until
#   - active_from <= exact_at <= active_until (if exact_at is not None)
#   - Uses position and coarse search caching for performance.
# failure_policy: Raises TransitTimingError on unsupported planets, bracketing, or
#   coarse search failures; mathematical near-miss returns a successful result with
#   warning_code="no_exact_hit_in_window".
# END_MODULE_CONTRACT: M-SIDECAR-TRANSIT-TIMING

# START_MODULE_MAP: M-SIDECAR-TRANSIT-TIMING
# public_entrypoints:
#   - TransitTimingResult
#   - TransitTimingError
#   - TransitTimingSolver
#   - TransitPositionCache
#   - TransitPosition
#   - signed_delta
# semantic_blocks:
#   - MATH_HELPERS: signed delta calculations.
#   - CACHING: caching of planetary positions and search grids.
#   - SOLVER_LOGIC: coarse walking, boundary refinement, exact root finding, and occurrence selection.
# owned_tests:
#   - apps/solarsage/tests/test_transit_timing.py
# END_MODULE_MAP: M-SIDECAR-TRANSIT-TIMING

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import swisseph as swe

from solarsage.utils.ephemeris import PLANETS, julian_day_to_utc_iso

TransitPhase = Literal["applying", "exact", "separating"]

# START_BLOCK: MATH_HELPERS
def signed_delta(lon: float, exact_lon: float) -> float:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.signed_delta
    # purpose: Calculate the signed shortest distance from exact_lon to lon in degrees.
    # inputs: lon - current longitude; exact_lon - target longitude.
    # returns: float in [-180, 180).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.signed_delta
    return ((lon - exact_lon + 180.0) % 360.0) - 180.0
# END_BLOCK: MATH_HELPERS

class TransitTimingError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        # START_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitTimingError.__init__
        # purpose: Construct a typed transit timing failure with a stable code.
        # inputs: code - stable machine-readable failure code; message - human-readable detail.
        # returns: None.
        # side_effects: initializes RuntimeError state.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitTimingError.__init__
        super().__init__(message)
        self.code = code

@dataclass(frozen=True)
class TransitTimingResult:
    active_from_utc: str
    exact_at_utc: str | None
    active_until_utc: str
    occurrence_index: int | None
    exact_hits_in_window: tuple[str, ...]
    phase: TransitPhase
    applying: bool
    selected_branch: Literal["plus", "minus"]
    selected_exact_longitude: float
    warning_code: str | None = None

@dataclass(frozen=True)
class TransitPosition:
    jd: float
    longitude: float
    speed_longitude: float

# START_BLOCK: CACHING
class TransitPositionCache:
    def __init__(self, calc_func: Callable[[float, int], tuple[float, float]] | None = None) -> None:
        # START_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitPositionCache.__init__
        # purpose: Create a single-planet position cache for a request-scoped solver.
        # inputs: calc_func - optional injectable provider returning longitude and speed.
        # returns: None.
        # side_effects: initializes mutable in-memory cache/counters.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitPositionCache.__init__
        self.cache: dict[tuple[int, float], TransitPosition] = {}
        self.hits = 0
        self.misses = 0
        self._calc_func = calc_func or self._default_calc

    @property
    def cache_hits(self) -> int:
        return self.hits

    @property
    def cache_misses(self) -> int:
        return self.misses

    def _default_calc(self, jd: float, planet_id: int) -> tuple[float, float]:
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        res = swe.calc_ut(jd, planet_id, flags)
        lon, _, _, speed_lon, _, _ = res[0]
        return lon, speed_lon

    def get(self, planet_id: int, jd: float) -> TransitPosition:
        # START_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitPositionCache.get
        # purpose: Return one canonicalized planetary position for a planet/JD pair.
        # inputs: planet_id - Swiss Ephemeris planet id; jd - Julian Day.
        # returns: TransitPosition with longitude normalized to [0, 360).
        # side_effects: may call provider and update cache/counters on cache miss.
        # emitted_logs: none.
        # error_behavior: propagates provider errors.
        # END_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitPositionCache.get
        key = (planet_id, round(jd, 10))
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        lon, speed_lon = self._calc_func(jd, planet_id)
        pos = TransitPosition(jd=jd, longitude=lon % 360.0, speed_longitude=speed_lon)
        self.cache[key] = pos
        return pos
# END_BLOCK: CACHING

# Policy parameters for adaptive grid search per planet
PLANET_POLICIES = {
    # Name: (max_horizon_days, desired_angular_step, min_step_days, max_step_days)
    "MOON": (5.0, 0.50, 5.0 / 1440.0, 1.0 / 24.0),
    "SUN": (30.0, 0.50, 30.0 / 1440.0, 6.0 / 24.0),
    "MERCURY": (180.0, 0.40, 15.0 / 1440.0, 6.0 / 24.0),
    "VENUS": (300.0, 0.40, 30.0 / 1440.0, 12.0 / 24.0),
    "MARS": (800.0, 0.35, 1.0 / 24.0, 1.0),
    "JUPITER": (1800.0, 0.30, 2.0 / 24.0, 2.0),
    "SATURN": (4000.0, 0.25, 4.0 / 24.0, 4.0),
    "URANUS": (8000.0, 0.20, 6.0 / 24.0, 7.0),
    "NEPTUNE": (12000.0, 0.15, 8.0 / 24.0, 10.0),
    "PLUTO": (20000.0, 0.12, 8.0 / 24.0, 14.0),
}
COARSE_SAMPLES_CAP = 25000

# START_BLOCK: SOLVER_LOGIC
class TransitTimingSolver:
    def __init__(
        self,
        *,
        target_jd: float,
        position_cache: TransitPositionCache | None = None,
    ) -> None:
        # START_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitTimingSolver.__init__
        # purpose: Create a request-scoped transit timing solver and shared outward grids.
        # inputs: target_jd - request target Julian Day; position_cache - optional shared cache.
        # returns: None.
        # side_effects: initializes mutable in-memory cache/grid references only.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitTimingSolver.__init__
        self.target_jd = target_jd
        self.cache = position_cache or TransitPositionCache()
        # Memoized grids to avoid scanning the same planet multiple times in a request
        # key: (planet_id, direction: Literal[1, -1]) -> list[TransitPosition]
        self.grids: dict[tuple[int, int], list[TransitPosition]] = {}

    def _get_planet_id(self, name: str) -> int:
        norm = name.strip().upper()
        # strip Transit_/Natal_ prefix
        for prefix in ("TRANSIT_", "NATAL_"):
            if norm.startswith(prefix):
                norm = norm[len(prefix):]
        # title case mapping
        title_name = norm.title()
        if title_name not in PLANETS:
            raise TransitTimingError("unsupported_planet", f"Planet '{name}' is not supported")
        return PLANETS[title_name]

    def _get_policy(self, name: str) -> tuple[float, float, float, float]:
        norm = name.strip().upper()
        for prefix in ("TRANSIT_", "NATAL_"):
            if norm.startswith(prefix):
                norm = norm[len(prefix):]
        if norm not in PLANET_POLICIES:
            raise TransitTimingError("unsupported_planet", f"Planet '{name}' has no search policy")
        return PLANET_POLICIES[norm]

    def _get_grid(self, planet_id: int, planet_name: str, direction: int) -> list[TransitPosition]:
        key = (planet_id, direction)
        if key in self.grids:
            return self.grids[key]

        grid = [self.cache.get(planet_id, self.target_jd)]
        self.grids[key] = grid
        return grid

    def _append_grid_sample(
        self,
        *,
        planet_id: int,
        planet_name: str,
        direction: int,
    ) -> TransitPosition | None:
        grid = self._get_grid(planet_id, planet_name, direction)
        if len(grid) - 1 >= COARSE_SAMPLES_CAP:
            raise TransitTimingError("coarse_sample_budget_exhausted", "Coarse search sample cap exceeded")

        max_horizon, desired_step, min_step, max_step = self._get_policy(planet_name)
        last_pos = grid[-1]
        horizon_limit = self.target_jd + direction * max_horizon
        if direction * (horizon_limit - last_pos.jd) <= 0:
            return None

        speed_floor = desired_step / max_step
        raw_days = desired_step / max(abs(last_pos.speed_longitude), speed_floor)
        step = max(min_step, min(raw_days, max_step))
        next_jd = last_pos.jd + direction * step

        if direction * (horizon_limit - next_jd) < 0:
            next_jd = horizon_limit
        if direction * (next_jd - last_pos.jd) <= 0:
            return None

        next_pos = self.cache.get(planet_id, next_jd)
        grid.append(next_pos)
        return next_pos

    def _find_first_outside_index(
        self,
        *,
        planet_id: int,
        planet_name: str,
        direction: int,
        selected_lon: float,
        max_orb: float,
    ) -> int:
        grid = self._get_grid(planet_id, planet_name, direction)

        def is_outside(pos: TransitPosition) -> bool:
            return abs(signed_delta(pos.longitude, selected_lon)) > max_orb + 1e-9

        for idx, pos in enumerate(grid):
            if is_outside(pos):
                if idx == 0:
                    raise TransitTimingError("target_outside_orb", "Target julian day is outside of aspect orb")
                return idx

        while True:
            new_pos = self._append_grid_sample(
                planet_id=planet_id,
                planet_name=planet_name,
                direction=direction,
            )
            if new_pos is None:
                direction_name = "forward" if direction == 1 else "backward"
                raise TransitTimingError(
                    f"boundary_not_bracketed_{direction_name}",
                    f"{direction_name.title()} orb boundary not bracketed",
                )
            if is_outside(new_pos):
                return len(grid) - 1

    def solve(
        self,
        *,
        source_planet: str,
        target_longitude: float,
        aspect_angle: float,
        max_orb: float,
    ) -> TransitTimingResult:
        # START_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitTimingSolver.solve
        # purpose: Find the active window boundaries and exact return moment for a transit.
        # inputs: source_planet - name; target_longitude - float; aspect_angle - float; max_orb - float.
        # returns: TransitTimingResult.
        # side_effects: mutates request-scoped position cache/coarse grids and may
        #   call Swiss Ephemeris on cache misses.
        # emitted_logs: none.
        # error_behavior: raises TransitTimingError on bracket or search failures.
        # END_FUNCTION_CONTRACT: F-M-SIDECAR-TRANSIT-TIMING.TransitTimingSolver.solve
        planet_id = self._get_planet_id(source_planet)

        # 1. Select exact target branch (plus or minus)
        target_plus = (target_longitude + aspect_angle) % 360.0
        target_minus = (target_longitude - aspect_angle) % 360.0

        current_pos = self.cache.get(planet_id, self.target_jd)
        diff_plus = abs(signed_delta(current_pos.longitude, target_plus))
        diff_minus = abs(signed_delta(current_pos.longitude, target_minus))

        if diff_plus <= diff_minus:
            selected_lon = target_plus
            selected_branch = "plus"
        else:
            selected_lon = target_minus
            selected_branch = "minus"

        # Check if currently inside orb
        current_residual = signed_delta(current_pos.longitude, selected_lon)
        if abs(current_residual) > max_orb + 1e-9:
            raise TransitTimingError("target_outside_orb", "Target julian day is outside of aspect orb")

        # Helpers for solver boundary
        def inside(jd: float) -> bool:
            pos = self.cache.get(planet_id, jd)
            return abs(signed_delta(pos.longitude, selected_lon)) <= max_orb + 1e-9

        def residual(jd: float) -> float:
            pos = self.cache.get(planet_id, jd)
            return signed_delta(pos.longitude, selected_lon)

        # 2. Scan boundaries (backward and forward)
        # Backward boundary
        backward_grid = self._get_grid(planet_id, source_planet, -1)
        first_outside_idx = self._find_first_outside_index(
            planet_id=planet_id,
            planet_name=source_planet,
            direction=-1,
            selected_lon=selected_lon,
            max_orb=max_orb,
        )

        # Refine backward boundary
        left_jd = backward_grid[first_outside_idx].jd
        right_jd = backward_grid[first_outside_idx - 1].jd  # inside

        # Bounded bisection to find crossing where abs(res) == max_orb
        for _ in range(64):
            if abs(right_jd - left_jd) * 86400.0 <= 300.0:
                break
            mid_jd = 0.5 * (left_jd + right_jd)
            if inside(mid_jd):
                right_jd = mid_jd
            else:
                left_jd = mid_jd
        # We return the inside-side endpoint (right_jd)
        active_from_jd = right_jd

        # Forward boundary
        forward_grid = self._get_grid(planet_id, source_planet, 1)
        first_outside_idx_f = self._find_first_outside_index(
            planet_id=planet_id,
            planet_name=source_planet,
            direction=1,
            selected_lon=selected_lon,
            max_orb=max_orb,
        )

        left_jd_f = forward_grid[first_outside_idx_f - 1].jd  # inside
        right_jd_f = forward_grid[first_outside_idx_f].jd

        for _ in range(64):
            if abs(right_jd_f - left_jd_f) * 86400.0 <= 300.0:
                break
            mid_jd = 0.5 * (left_jd_f + right_jd_f)
            if inside(mid_jd):
                left_jd_f = mid_jd
            else:
                right_jd_f = mid_jd
        active_until_jd = left_jd_f

        # 3. Exact-hit enumeration inside [active_from_jd, active_until_jd]
        # Gather unique samples in window
        samples_in_window_set = {active_from_jd, active_until_jd}
        for pos in backward_grid[:first_outside_idx]:
            if active_from_jd <= pos.jd <= active_until_jd:
                samples_in_window_set.add(pos.jd)
        for pos in forward_grid[:first_outside_idx_f]:
            if active_from_jd <= pos.jd <= active_until_jd:
                samples_in_window_set.add(pos.jd)

        samples_in_window = sorted(list(samples_in_window_set))
        roots_jd: list[float] = []

        # Find exact zeros directly on the sample grid points
        for jd in samples_in_window:
            if abs(residual(jd)) <= 1e-5:
                roots_jd.append(jd)

        # Find roots between sample points
        for idx in range(len(samples_in_window) - 1):
            jd1 = samples_in_window[idx]
            jd2 = samples_in_window[idx + 1]
            res1 = residual(jd1)
            res2 = residual(jd2)

            # 1. residual sign change
            if res1 * res2 < 0:
                left, right = jd1, jd2
                for _ in range(64):
                    if abs(right - left) * 86400.0 <= 1.0:
                        break
                    mid = 0.5 * (left + right)
                    if residual(mid) * res1 < 0:
                        right = mid
                    else:
                        left = mid
                roots_jd.append(0.5 * (left + right))
            else:
                # check for speed sign change (station / tangent point)
                pos1 = self.cache.get(planet_id, jd1)
                pos2 = self.cache.get(planet_id, jd2)
                if pos1.speed_longitude * pos2.speed_longitude < 0:
                    # Find station time
                    left, right = jd1, jd2
                    for _ in range(64):
                        if abs(right - left) * 86400.0 <= 1.0:
                            break
                        mid = 0.5 * (left + right)
                        pm = self.cache.get(planet_id, mid)
                        if pm.speed_longitude * pos1.speed_longitude < 0:
                            right = mid
                        else:
                            left = mid
                    station_jd = 0.5 * (left + right)
                    if abs(residual(station_jd)) <= 1e-5:
                        roots_jd.append(station_jd)

        # Sort and deduplicate roots (<= 120 seconds)
        roots_jd.sort()
        deduped_roots: list[float] = []
        for r in roots_jd:
            if not deduped_roots or (r - deduped_roots[-1]) * 86400.0 > 120.0:
                deduped_roots.append(r)

        exact_hits_in_window = tuple(julian_day_to_utc_iso(r) for r in deduped_roots)

        # 4. Occurrence selection
        exact_at_utc: str | None = None
        occurrence_index: int | None = None
        warning_code: str | None = None

        if deduped_roots:
            # Find closest root to target_jd
            closest_root_idx = min(range(len(deduped_roots)), key=lambda i: abs(deduped_roots[i] - self.target_jd))
            # Tie breaker: future root chosen
            if closest_root_idx < len(deduped_roots) - 1:
                curr_dist = abs(deduped_roots[closest_root_idx] - self.target_jd)
                next_dist = abs(deduped_roots[closest_root_idx + 1] - self.target_jd)
                if abs(curr_dist - next_dist) * 86400.0 <= 1.0:
                    closest_root_idx += 1

            selected_root_jd = deduped_roots[closest_root_idx]
            exact_at_utc = exact_hits_in_window[closest_root_idx]
            occurrence_index = closest_root_idx

            diff_sec = (selected_root_jd - self.target_jd) * 86400.0
            if abs(diff_sec) <= 60.0:
                phase = "exact"
                applying = False
            elif diff_sec > 60.0:
                phase = "applying"
                applying = True
            else:
                phase = "separating"
                applying = False
        else:
            # Near miss
            exact_at_utc = None
            occurrence_index = None
            warning_code = "no_exact_hit_in_window"

            # Determine local direction using the shared forward grid, not a new +0.1 day probe.
            probe_pos = forward_grid[1] if len(forward_grid) > 1 else current_pos
            probe_res = signed_delta(probe_pos.longitude, selected_lon)
            if abs(probe_res) < abs(current_residual):
                phase = "applying"
                applying = True
            else:
                phase = "separating"
                applying = False

        # Invariant checks
        if exact_at_utc:
            sel_jd = deduped_roots[occurrence_index]
            if phase == "applying" and sel_jd < self.target_jd - 60.0 / 86400.0:
                raise RuntimeError("Phase invariant violated: applying exact_at is before target")
            if phase == "separating" and sel_jd > self.target_jd + 60.0 / 86400.0:
                raise RuntimeError("Phase invariant violated: separating exact_at is after target")
            if phase == "exact" and abs(sel_jd - self.target_jd) > 60.0 / 86400.0:
                raise RuntimeError("Phase invariant violated: exact phase mismatch")

        # Format result boundaries
        active_from_utc = julian_day_to_utc_iso(active_from_jd)
        active_until_utc = julian_day_to_utc_iso(active_until_jd)

        return TransitTimingResult(
            active_from_utc=active_from_utc,
            exact_at_utc=exact_at_utc,
            active_until_utc=active_until_utc,
            occurrence_index=occurrence_index,
            exact_hits_in_window=exact_hits_in_window,
            phase=phase,
            applying=applying,
            selected_branch=selected_branch,
            selected_exact_longitude=selected_lon,
            warning_code=warning_code,
        )
# END_BLOCK: SOLVER_LOGIC
