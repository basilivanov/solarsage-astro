# ############################################################################
# AI_HEADER: MODULE_TODAY-CONVERGENCE-RUNTIME — deterministic runtime calculation boundary.
# ROLE: Validates one direct profile, requests one activation grid, preserves its
#       verified ephemeris lineage, builds robust facts, and composes the accepted
#       canonical convergence pipeline.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-RUNTIME
# purpose: Orchestrate the W2 calculation path from a validated profile and
#   target local date without persistence, wire, logging, or legacy adapters.
# owns:
#   - apps/api/app/services/today_convergence_runtime.py
# inputs: Direct profile fields, target local date, optional canonical DayDelta
#   semantic keys, and an injectable SolarSage grid client.
# outputs: Immutable built or unavailable runtime calculation records; built
#   records preserve the activation-grid ephemeris artifact identity.
# dependencies: today_birth_time, solarsage_client, today_birth_time_facts,
#   and today_convergence_pipeline only.
# side_effects: one activation-grid HTTP request through the accepted client;
#   no writes, retries, cache, logs, or fallback calculation.
# emitted_logs: none.
# invariants: canonical target time is 12:00; profile and target boundaries fail
#   closed; successful stages are preserved in unavailable results; built records
#   carry the batch artifact without fallback.
# failure_policy: typed profile, transport, facts, and pipeline failures become
#   safe today_convergence_runtime-prefixed unavailable tokens; programming errors propagate.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-RUNTIME

# START_MODULE_MAP: M-TODAY-CONVERGENCE-RUNTIME
# public_entrypoints:
#   - CANONICAL_TARGET_TIME
#   - TodayConvergenceProfileLike
#   - TodayConvergenceRuntimeError
#   - TodayConvergenceCalculationBuilt
#   - TodayConvergenceCalculationUnavailable
#   - TodayConvergenceCalculationResult
#   - calculate_today_convergence
# semantic_blocks:
#   - PROFILE_BOUNDARY: direct profile/date/coordinate/timezone validation.
#   - ACTIVATION_GRID: one canonical target-moment sidecar request.
#   - STAGE_COMPOSITION: robust facts and canonical pipeline composition.
#   - IMMUTABLE_RESULTS: frozen built/unavailable records and safe failure tokens.
# owned_tests:
#   - apps/api/tests/test_today_convergence_runtime.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-RUNTIME

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Number
from typing import Literal, Protocol, TypeAlias
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.clients.solarsage_client import (
    ActivationGridBatch,
    SolarSageClient,
    SolarSageClientError,
    get_solarsage_client,
)
from app.services.today_birth_time import (
    BirthTimeResolution,
    TodayBirthTimeError,
    resolve_profile_birth_time,
)
from app.services.today_birth_time_facts import (
    BirthTimeFactsAudit,
    TodayBirthTimeFactsError,
    build_birth_time_facts,
)
from app.services.today_convergence_pipeline import (
    CanonicalPipelineBuilt,
    CanonicalPipelineUnavailable,
    run_canonical_today_pipeline,
)


CANONICAL_TARGET_TIME = "12:00"


class TodayConvergenceProfileLike(Protocol):
    """The exact direct profile shape consumed by the runtime boundary."""

    birthday: object
    birth_time: object
    birth_time_mode: object
    birth_time_bucket: object
    birth_lat: object
    birth_lon: object
    birth_tz: object
    current_lat: object
    current_lon: object
    current_tz: object


class TodayConvergenceRuntimeError(ValueError):
    """Programming misuse of the runtime result boundary."""


@dataclass(frozen=True)
class TodayConvergenceCalculationBuilt:
    """Immutable successful deterministic calculation."""

    state: Literal["convergence_today", "quiet_day"]
    target_date: date
    target_timezone: str
    target_time: str
    birth_time: BirthTimeResolution
    calculation_version: str
    activation_layer_version: str
    ephemeris_artifact_id: str
    facts_audit: BirthTimeFactsAudit
    pipeline: CanonicalPipelineBuilt


@dataclass(frozen=True)
class TodayConvergenceCalculationUnavailable:
    """Immutable typed failure preserving only completed safe stages."""

    state: Literal["unavailable"]
    target_date: date
    failure_stage: Literal["profile", "activation_grid", "facts", "pipeline"]
    failure_reason: str
    target_timezone: str | None
    target_time: str
    birth_time: BirthTimeResolution | None
    facts_audit: BirthTimeFactsAudit | None
    pipeline: CanonicalPipelineUnavailable | None


TodayConvergenceCalculationResult: TypeAlias = (
    TodayConvergenceCalculationBuilt | TodayConvergenceCalculationUnavailable
)


_MISSING = object()
_RUNTIME_PREFIX = "today_convergence_runtime:"


# START_BLOCK: PROFILE_BOUNDARY
def _safe_target_date(value: object) -> date:
    return value if type(value) is date else date.min


def _unavailable(
    *,
    target_date: object,
    stage: Literal["profile", "activation_grid", "facts", "pipeline"],
    reason: str,
    target_timezone: str | None = None,
    birth_time: BirthTimeResolution | None = None,
    facts_audit: BirthTimeFactsAudit | None = None,
    pipeline: CanonicalPipelineUnavailable | None = None,
) -> TodayConvergenceCalculationUnavailable:
    return TodayConvergenceCalculationUnavailable(
        state="unavailable",
        target_date=_safe_target_date(target_date),
        failure_stage=stage,
        failure_reason=f"{_RUNTIME_PREFIX}{reason}",
        target_timezone=target_timezone,
        target_time=CANONICAL_TARGET_TIME,
        birth_time=birth_time,
        facts_audit=facts_audit,
        pipeline=pipeline,
    )


def _profile_values(profile: object) -> dict[str, object]:
    fields = (
        "birthday",
        "birth_time",
        "birth_time_mode",
        "birth_time_bucket",
        "birth_lat",
        "birth_lon",
        "birth_tz",
        "current_lat",
        "current_lon",
        "current_tz",
    )
    values = {field: getattr(profile, field, _MISSING) for field in fields}
    if any(value is _MISSING for value in values.values()):
        raise TodayConvergenceRuntimeError("profile_attribute")
    return values


def _finite_coordinate(value: object, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Number):
        raise TodayConvergenceRuntimeError("coordinate_type")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TodayConvergenceRuntimeError("coordinate_type") from exc
    if not isfinite(result) or not minimum <= result <= maximum:
        raise TodayConvergenceRuntimeError("coordinate_range")
    return result


def _valid_timezone(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise TodayConvergenceRuntimeError("timezone")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TodayConvergenceRuntimeError("timezone") from exc
    return value


def _validate_profile(
    values: dict[str, object],
) -> tuple[str, dict[str, float | str] | None]:
    if type(values["birthday"]) is not date:
        raise TodayConvergenceRuntimeError("birthday")
    _finite_coordinate(values["birth_lat"], -90.0, 90.0)
    _finite_coordinate(values["birth_lon"], -180.0, 180.0)
    birth_tz = _valid_timezone(values["birth_tz"])

    selected_timezone = values["current_tz"] if values["current_tz"] is not None else birth_tz
    target_timezone = _valid_timezone(selected_timezone)

    current_values = (values["current_lat"], values["current_lon"], values["current_tz"])
    if all(value is None for value in current_values):
        current_location = None
    elif all(value is not None for value in current_values):
        current_location = {
            "lat": _finite_coordinate(values["current_lat"], -90.0, 90.0),
            "lon": _finite_coordinate(values["current_lon"], -180.0, 180.0),
            "tz": _valid_timezone(values["current_tz"]),
        }
    else:
        current_location = None
    return target_timezone, current_location


# END_BLOCK: PROFILE_BOUNDARY


# START_BLOCK: ACTIVATION_GRID
async def _request_activation_grid(
    *,
    profile_values: dict[str, object],
    resolution: BirthTimeResolution,
    target_date: date,
    target_timezone: str,
    current_location: dict[str, float | str] | None,
    client: SolarSageClient | object | None,
) -> ActivationGridBatch:
    selected_client = get_solarsage_client() if client is None else client
    return await selected_client.get_activation_layer_grid(
        birth_date=profile_values["birthday"].isoformat(),  # type: ignore[union-attr]
        birth_times=resolution.control_times,
        birth_lat=_finite_coordinate(profile_values["birth_lat"], -90.0, 90.0),
        birth_lon=_finite_coordinate(profile_values["birth_lon"], -180.0, 180.0),
        birth_tz=profile_values["birth_tz"],
        target_date=target_date.isoformat(),
        target_time=CANONICAL_TARGET_TIME,
        target_tz=target_timezone,
        house_system="PLACIDUS",
        techniques=None,
        current_location=current_location,
    )


# END_BLOCK: ACTIVATION_GRID


# START_BLOCK: STAGE_COMPOSITION
async def calculate_today_convergence(
    profile: TodayConvergenceProfileLike,
    target_date: date,
    *,
    delta_trigger_semantic_keys: Sequence[str] | None = None,
    client: SolarSageClient | None = None,
) -> TodayConvergenceCalculationResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-RUNTIME.calculate_today_convergence
    # purpose: Build one deterministic target-day calculation from profile to canonical pipeline.
    # inputs: direct profile shape, strict local target date, semantic DayDelta keys, optional injected client.
    # returns: frozen built or unavailable calculation result.
    # side_effects: exactly one activation-grid request when profile validation succeeds; no logs or writes.
    # emitted_logs: none.
    # error_behavior: expected typed boundaries return unavailable; unexpected programming errors propagate.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-RUNTIME.calculate_today_convergence
    if type(target_date) is not date:
        return _unavailable(target_date=target_date, stage="profile", reason="profile:target_date")

    try:
        values = _profile_values(profile)
        target_timezone, current_location = _validate_profile(values)
        resolution = resolve_profile_birth_time(profile)
    except TodayBirthTimeError:
        return _unavailable(target_date=target_date, stage="profile", reason="profile:birth_time")
    except TodayConvergenceRuntimeError:
        return _unavailable(target_date=target_date, stage="profile", reason="profile:invalid")

    try:
        batch = await _request_activation_grid(
            profile_values=values,
            resolution=resolution,
            target_date=target_date,
            target_timezone=target_timezone,
            current_location=current_location,
            client=client,
        )
    except SolarSageClientError:
        return _unavailable(
            target_date=target_date,
            stage="activation_grid",
            reason="activation_grid:client_contract",
            target_timezone=target_timezone,
            birth_time=resolution,
        )
    except httpx.HTTPError:
        return _unavailable(
            target_date=target_date,
            stage="activation_grid",
            reason="activation_grid:http_error",
            target_timezone=target_timezone,
            birth_time=resolution,
        )

    try:
        facts = build_birth_time_facts(resolution, batch.samples)
    except TodayBirthTimeFactsError:
        return _unavailable(
            target_date=target_date,
            stage="facts",
            reason="facts:invalid_boundary",
            target_timezone=target_timezone,
            birth_time=resolution,
        )

    pipeline = run_canonical_today_pipeline(
        facts.facts,
        target_date,
        target_timezone,
        delta_trigger_semantic_keys,
    )
    if isinstance(pipeline, CanonicalPipelineUnavailable):
        return _unavailable(
            target_date=target_date,
            stage="pipeline",
            reason=f"pipeline:{pipeline.failure_stage}",
            target_timezone=target_timezone,
            birth_time=resolution,
            facts_audit=facts.audit,
            pipeline=pipeline,
        )
    if not isinstance(pipeline, CanonicalPipelineBuilt):
        raise TodayConvergenceRuntimeError("invalid_pipeline_result")

    return TodayConvergenceCalculationBuilt(
        state=pipeline.state,
        target_date=target_date,
        target_timezone=target_timezone,
        target_time=CANONICAL_TARGET_TIME,
        birth_time=resolution,
        calculation_version=batch.calculation_version,
        activation_layer_version=batch.activation_layer_version,
        ephemeris_artifact_id=batch.ephemeris_artifact_id,
        facts_audit=facts.audit,
        pipeline=pipeline,
    )


# END_BLOCK: STAGE_COMPOSITION


__all__ = [
    "CANONICAL_TARGET_TIME",
    "TodayConvergenceProfileLike",
    "TodayConvergenceRuntimeError",
    "TodayConvergenceCalculationBuilt",
    "TodayConvergenceCalculationUnavailable",
    "TodayConvergenceCalculationResult",
    "calculate_today_convergence",
]
