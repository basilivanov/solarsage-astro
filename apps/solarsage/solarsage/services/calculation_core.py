# ############################################################################
# AI_HEADER: SIDECAR_CALCULATION_CORE — shared in-process calculation facade.
# ROLE: Owns the single calculation entrypoints used by HTTP routes and by
#       deterministic offline replay workers.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-CALCULATION-CORE
# purpose: Expose natal, transit, and activation-layer calculations without
#   requiring an HTTP hop while preserving the exact sidecar response models.
# owns:
#   - apps/solarsage/solarsage/services/calculation_core.py
# inputs: validated birth, target, location, house-system, and technique data.
# outputs: NatalResponse, TransitsResponse, or ActivationLayer models with
#   physical natal-target speed debug on transit-to-natal planet evidence.
# dependencies: NatalService; ephemeris utilities; activation_builder; sidecar
#   response schemas.
# side_effects: Swiss Ephemeris artifact reads and process-local canon caches.
# emitted_logs: none.
# invariants:
#   - HTTP routes and offline replay call these same functions.
#   - Returned models serialize identically for identical inputs.
#   - Target-speed debug uses only finite speed from the exact natal context;
#     angle, lot, missing, and invalid speeds never receive a fallback.
# failure_policy: propagates validation and calculation errors fail-closed.
# END_MODULE_CONTRACT: M-SIDECAR-CALCULATION-CORE

# START_MODULE_MAP: M-SIDECAR-CALCULATION-CORE
# public_entrypoints:
#   - calculate_natal_response
#   - calculate_transits_response
#   - calculate_activation_layer
#   - calculate_activation_grid
#   - validate_birth_time_grid
#   - prepare_natal_context
#   - prepare_target_context
# semantic_blocks:
#   - NATAL: natal chart response construction.
#   - TRANSITS: target-moment transit response construction.
#   - ACTIVATION_LAYER: activation evidence calculation and target-speed enrichment.
#   - ACTIVATION_GRID: shared target-context and timing-solver orchestration.
# owned_tests:
#   - apps/solarsage/tests/test_calculation_core.py
#   - apps/solarsage/tests/test_activation_grid.py
#   - apps/solarsage/tests/test_activation_target_speed.py
# END_MODULE_MAP: M-SIDECAR-CALCULATION-CORE

from __future__ import annotations

import re
from collections.abc import Sequence
from math import isfinite
from typing import Any, Literal

from solarsage.schemas.activation import ActivationLayer
from solarsage.schemas.natal import House, NatalResponse, Planet, SpecialPoint
from solarsage.schemas.transits import TransitsResponse
from solarsage.services.activation_builder import (
    ALL_TECHNIQUES,
    NatalCalculationContext,
    TargetCalculationContext,
    build_activation_layer,
    prepare_natal_context,
    prepare_target_context,
)
from solarsage.services.natal import NatalService
from solarsage.services.transit_timing import TransitTimingSolver
from solarsage.utils.ephemeris import calculate_julian_day, calculate_positions


# START_BLOCK: NATAL
def calculate_natal_response(
    *,
    birth_date: str,
    birth_time: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    house_system: str = "PLACIDUS",
) -> NatalResponse:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_natal_response
    # purpose: Calculate and validate one natal response in process.
    # inputs: exact birth event and requested house system.
    # returns: NatalResponse matching POST /v1/natal output.
    # side_effects: Swiss Ephemeris calculations.
    # emitted_logs: none.
    # error_behavior: propagates calculation or schema errors.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_natal_response
    chart = NatalService().calculate_natal_chart(
        date_str=birth_date,
        time_str=birth_time,
        tz_str=birth_tz,
        latitude=birth_lat,
        longitude=birth_lon,
        house_system=house_system,
    )
    return NatalResponse(
        planets=[Planet(**item) for item in chart.positions],
        houses=[House(**item) for item in chart.houses],
        special_points=[SpecialPoint(**item) for item in chart.special_points],
        house_system=chart.house_system,
    )
# END_BLOCK: NATAL


# START_BLOCK: TRANSITS
def calculate_transits_response(
    *,
    target_date: str,
    target_time: str,
    target_tz: str,
) -> TransitsResponse:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_transits_response
    # purpose: Calculate and validate one target-moment transit response.
    # inputs: target local date, time, and timezone.
    # returns: TransitsResponse matching POST /v1/transits output.
    # side_effects: Swiss Ephemeris calculations.
    # emitted_logs: none.
    # error_behavior: propagates calculation or schema errors.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_transits_response
    target_jd = calculate_julian_day(target_date, target_time, target_tz)
    return TransitsResponse(
        planets=[Planet(**item) for item in calculate_positions(target_jd)],
        target_jd=target_jd,
    )
# END_BLOCK: TRANSITS


# START_BLOCK: ACTIVATION_LAYER
def _enrich_target_speed(layer: ActivationLayer, natal_context: NatalCalculationContext) -> ActivationLayer:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE._enrich_target_speed
    # purpose: Add physical natal-target speed to transit-to-natal planet debug only.
    # inputs: builder-produced ActivationLayer and the exact NatalCalculationContext used to build it.
    # returns: Equivalent ActivationLayer with finite target-speed debug enrichment.
    # side_effects: none; returns a model copy when enrichment changes an activation.
    # emitted_logs: none.
    # error_behavior: missing or non-finite natal speed omits the debug key without fallback.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE._enrich_target_speed
    speed_by_target = {
        str(name).strip().upper(): value.get("speed")
        for name, value in natal_context.natal_by_name.items()
    }
    enriched = []
    changed = False
    for activation in layer.activations:
        if activation.technique != "transit_to_natal" or activation.target_type != "planet":
            enriched.append(activation)
            continue
        debug = dict(activation.debug)
        speed = speed_by_target.get(activation.target_key.strip().upper())
        if not isinstance(speed, bool) and isinstance(speed, (int, float)) and isfinite(float(speed)):
            debug["target_speed_deg_per_hour"] = abs(float(speed)) / 24.0
        else:
            debug.pop("target_speed_deg_per_hour", None)
        if debug != activation.debug:
            activation = activation.model_copy(update={"debug": debug})
            changed = True
        enriched.append(activation)
    return layer.model_copy(update={"activations": enriched}) if changed else layer


def calculate_activation_layer(
    *,
    birth_date: str,
    birth_time: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    target_date: str,
    target_time: str,
    target_tz: str,
    house_system: str = "PLACIDUS",
    techniques: list[str] | None = None,
    current_location: dict[str, Any] | None = None,
    timing_scope: Literal["all", "convergence_eligible"] = "all",
    natal_context: NatalCalculationContext | None = None,
    target_context: TargetCalculationContext | None = None,
    timing_solver: TransitTimingSolver | None = None,
) -> ActivationLayer:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_activation_layer
    # purpose: Calculate one activation layer through the shared builder.
    # inputs: birth/target context, house system, techniques, current location.
    # returns: ActivationLayer matching the nested HTTP response model.
    # side_effects: Swiss Ephemeris calculations and process-local canon caches.
    # emitted_logs: none.
    # error_behavior: propagates calculation or schema errors.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_activation_layer
    resolved_natal_context = natal_context or prepare_natal_context(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_tz=birth_tz,
        house_system=house_system,
    )
    layer = build_activation_layer(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_tz=birth_tz,
        target_date=target_date,
        target_time=target_time,
        target_tz=target_tz,
        house_system=house_system,
        techniques=techniques,
        current_location=current_location,
        timing_scope=timing_scope,
        natal_context=resolved_natal_context,
        target_context=target_context,
        timing_solver=timing_solver,
    )
    return _enrich_target_speed(layer, resolved_natal_context)
# END_BLOCK: ACTIVATION_LAYER


# START_BLOCK: ACTIVATION_GRID
_BIRTH_TIME_PATTERN = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")
_TIMING_TECHNIQUES = frozenset({"transit_to_natal", "transit_to_angle", "transit_to_lot"})


def validate_birth_time_grid(birth_times: Sequence[str]) -> tuple[str, ...]:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.validate_birth_time_grid
    # purpose: Validate and return the ordered minute-precision birth-time grid used by core and HTTP callers.
    # inputs: Sequence of strict HH:MM strings, one through seven values.
    # returns: The same ordered tuple after strict uniqueness and range validation.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for non-sequences, malformed values, or non-increasing grids.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.validate_birth_time_grid
    if isinstance(birth_times, (str, bytes)) or not isinstance(birth_times, Sequence):
        raise ValueError("birth_times must be a sequence")
    values = tuple(birth_times)
    if not 1 <= len(values) <= 7:
        raise ValueError("birth_times must contain between 1 and 7 values")

    previous_minutes = -1
    for value in values:
        if not isinstance(value, str) or _BIRTH_TIME_PATTERN.fullmatch(value) is None:
            raise ValueError("birth_times must contain minute-precision HH:MM values")
        hours, minutes = (int(part) for part in value.split(":"))
        total_minutes = hours * 60 + minutes
        if total_minutes <= previous_minutes:
            raise ValueError("birth_times must be strictly increasing and unique")
        previous_minutes = total_minutes
    return values


def calculate_activation_grid(
    *,
    birth_date: str,
    birth_times: Sequence[str],
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    target_date: str,
    target_time: str,
    target_tz: str,
    house_system: str = "PLACIDUS",
    techniques: list[str] | None = None,
    current_location: dict[str, Any] | None = None,
) -> tuple[ActivationLayer, ...]:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_activation_grid
    # purpose: Calculate ordered birth-time control layers with one shared target context and optional timing solver.
    # inputs: birth date/times, target moment, location, house system, and requested activation techniques.
    # returns: ActivationLayer tuple in exact validated birth-time request order.
    # side_effects: Swiss Ephemeris calculations; no parallelism or hidden cache.
    # emitted_logs: none.
    # error_behavior: invalid grids raise ValueError; calculation errors propagate unchanged.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-CALCULATION-CORE.calculate_activation_grid
    validated_times = validate_birth_time_grid(birth_times)
    target_context = prepare_target_context(
        target_date=target_date,
        target_time=target_time,
        target_tz=target_tz,
    )
    requested_techniques = list(ALL_TECHNIQUES) if not techniques else list(techniques)
    timing_solver = None
    if _TIMING_TECHNIQUES.intersection(requested_techniques):
        timing_solver = TransitTimingSolver(target_jd=target_context.target_jd)

    layers: list[ActivationLayer] = []
    for birth_time in validated_times:
        natal_context = prepare_natal_context(
            birth_date=birth_date,
            birth_time=birth_time,
            birth_lat=birth_lat,
            birth_lon=birth_lon,
            birth_tz=birth_tz,
            house_system=house_system,
        )
        layers.append(
            calculate_activation_layer(
                birth_date=birth_date,
                birth_time=birth_time,
                birth_lat=birth_lat,
                birth_lon=birth_lon,
                birth_tz=birth_tz,
                target_date=target_date,
                target_time=target_time,
                target_tz=target_tz,
                house_system=house_system,
                techniques=list(techniques) if techniques else None,
                current_location=current_location,
                timing_scope="convergence_eligible",
                natal_context=natal_context,
                target_context=target_context,
                timing_solver=timing_solver,
            )
        )
    return tuple(layers)
# END_BLOCK: ACTIVATION_GRID
