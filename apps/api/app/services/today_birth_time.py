# ############################################################################
# AI_HEADER: MODULE_TODAY_BIRTH_TIME — strict birth-time calculation resolution.
# ROLE: Converts persisted profile birth-time state into an immutable W1 calculation plan.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-BIRTH-TIME
# purpose: Resolve exact, bucket, and unknown birth-time states from the validated convergence canon.
# owns:
#   - apps/api/app/services/today_birth_time.py
# inputs: Persisted birth_time_mode, birth_time, and birth_time_bucket values plus TodayConvergenceCanon.
# outputs: Immutable BirthTimeResolution calculation input for convergence planning.
# dependencies: Python standard library and the validated TodayConvergenceCanon.
# side_effects: none; no database, HTTP, sidecar, logging, wire, or analysis dependencies.
# emitted_logs: none.
# invariants: persisted mode and bucket values are not normalized; malformed states fail closed.
# failure_policy: TodayBirthTimeError with a stable today_birth_time: reason is raised for every invalid state.
# END_MODULE_CONTRACT: M-TODAY-BIRTH-TIME

# START_MODULE_MAP: M-TODAY-BIRTH-TIME
# public_entrypoints:
#   - BirthTimeResolution
#   - BirthTimeProfileLike
#   - TodayBirthTimeError
#   - resolve_birth_time
#   - resolve_profile_birth_time
# semantic_blocks:
#   - INPUT_VALIDATION: strict persisted mode/time/bucket state validation.
#   - RESOLUTION: deterministic ranges, control grids, gaps, and capabilities.
#   - PROFILE: safe extraction of the direct profile contract.
# owned_tests:
#   - apps/api/tests/test_today_birth_time.py
# END_MODULE_MAP: M-TODAY-BIRTH-TIME

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Literal, Protocol

from app.services.today_convergence_canon import (
    BirthTimeCapabilities,
    TodayConvergenceCanon,
    load_today_convergence_canon,
)


BirthTimeMode = Literal["exact", "bucket", "unknown"]
BirthTimeBucket = Literal["night", "morning", "day", "evening"]


class TodayBirthTimeError(ValueError):
    """Raised when a persisted birth-time state cannot produce a safe plan."""


@dataclass(frozen=True)
class BirthTimeResolution:
    """Immutable calculation range and capability plan for one birth-time mode."""

    mode: BirthTimeMode
    bucket: BirthTimeBucket | None
    birth_time: str | None
    range_start: str
    range_end: str
    control_times: tuple[str, ...]
    canonical_gap_hours: int | None
    capabilities: BirthTimeCapabilities


class BirthTimeProfileLike(Protocol):
    """The direct profile attributes consumed by the pure resolver."""

    birth_time_mode: object
    birth_time: time | None
    birth_time_bucket: object | None


# START_BLOCK: INPUT_VALIDATION
def _fail(reason: str) -> None:
    raise TodayBirthTimeError(f"today_birth_time:{reason}")


def _canon_or_default(canon: TodayConvergenceCanon | None) -> TodayConvergenceCanon:
    if canon is None:
        return load_today_convergence_canon()
    if not isinstance(canon, TodayConvergenceCanon):
        _fail("invalid_canon")
    return canon


def _format_minutes(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def _validate_mode(mode: object, canon: TodayConvergenceCanon) -> BirthTimeMode:
    if not isinstance(mode, str) or mode not in canon.birth_time.modes:
        _fail("invalid_mode")
    return mode  # type: ignore[return-value]


def _validate_bucket(bucket: object, canon: TodayConvergenceCanon) -> BirthTimeBucket:
    if not isinstance(bucket, str) or bucket not in canon.birth_time.buckets_local:
        _fail("invalid_bucket")
    return bucket  # type: ignore[return-value]


def _validate_exact_time(birth_time: object) -> time:
    if not isinstance(birth_time, time):
        _fail("exact_time_required")
    if birth_time.second != 0 or birth_time.microsecond != 0:
        _fail("exact_time_precision")
    return birth_time


# END_BLOCK: INPUT_VALIDATION


# START_BLOCK: RESOLUTION
def resolve_birth_time(
    *,
    mode: object,
    birth_time: time | None,
    bucket: object | None,
    canon: TodayConvergenceCanon | None = None,
) -> BirthTimeResolution:
    # START_FUNCTION_CONTRACT: F-M-TODAY-BIRTH-TIME.resolve_birth_time
    # purpose: Resolve one persisted birth-time state into canonical calculation controls.
    # inputs: mode, birth_time, bucket — direct profile values; canon — validated W1 canon or default.
    # returns: Frozen BirthTimeResolution containing range, controls, gap, and capabilities.
    # side_effects: reads the default canon when canon is omitted; otherwise none.
    # emitted_logs: none.
    # error_behavior: raises TodayBirthTimeError for every malformed or conflicting state.
    # END_FUNCTION_CONTRACT: F-M-TODAY-BIRTH-TIME.resolve_birth_time
    resolved_canon = _canon_or_default(canon)
    resolved_mode = _validate_mode(mode, resolved_canon)
    birth_canon = resolved_canon.birth_time

    if resolved_mode == "exact":
        if bucket is not None:
            _fail("exact_bucket_forbidden")
        resolved_time = _validate_exact_time(birth_time)
        value = f"{resolved_time.hour:02d}:{resolved_time.minute:02d}"
        return BirthTimeResolution(
            mode="exact",
            bucket=None,
            birth_time=value,
            range_start=value,
            range_end=value,
            control_times=(value,),
            canonical_gap_hours=None,
            capabilities=birth_canon.capabilities["exact"],
        )

    if birth_time is not None:
        _fail(f"{resolved_mode}_time_forbidden")

    if resolved_mode == "bucket":
        resolved_bucket = _validate_bucket(bucket, resolved_canon)
        if birth_canon.control_grid.get("bucket") != "edges_plus_middle":
            _fail("control_grid")
        start_hour, end_hour = birth_canon.buckets_local[resolved_bucket]
        start = start_hour * 60
        end = end_hour * 60
        middle = start + ((end - start) // 2)
        controls = (_format_minutes(start), _format_minutes(middle), _format_minutes(end - 1))
        return BirthTimeResolution(
            mode="bucket",
            bucket=resolved_bucket,
            birth_time=None,
            range_start=controls[0],
            range_end=_format_minutes(end),
            control_times=controls,
            canonical_gap_hours=birth_canon.orb_margin.gap_hours["bucket"],
            capabilities=birth_canon.capabilities["bucket"],
        )

    if bucket is not None:
        _fail("unknown_bucket_forbidden")
    if birth_canon.control_grid.get("unknown") != "every_4h_plus_2359":
        _fail("control_grid")
    gap_hours = birth_canon.orb_margin.gap_hours["unknown"]
    gap_minutes = gap_hours * 60
    controls = tuple(_format_minutes(minutes) for minutes in range(0, 24 * 60, gap_minutes)) + (
        _format_minutes(24 * 60 - 1),
    )
    return BirthTimeResolution(
        mode="unknown",
        bucket=None,
        birth_time=None,
        range_start="00:00",
        range_end="24:00",
        control_times=controls,
        canonical_gap_hours=gap_hours,
        capabilities=birth_canon.capabilities["unknown"],
    )


# END_BLOCK: RESOLUTION


# START_BLOCK: PROFILE
def resolve_profile_birth_time(
    profile: BirthTimeProfileLike,
    canon: TodayConvergenceCanon | None = None,
) -> BirthTimeResolution:
    # START_FUNCTION_CONTRACT: F-M-TODAY-BIRTH-TIME.resolve_profile_birth_time
    # purpose: Resolve the three direct persisted profile attributes without inference or fallback.
    # inputs: profile — object exposing birth_time_mode, birth_time, and birth_time_bucket; canon — validated W1 canon.
    # returns: The same BirthTimeResolution produced by resolve_birth_time for those values.
    # side_effects: none except default canon loading when omitted.
    # emitted_logs: none.
    # error_behavior: raises TodayBirthTimeError when profile attributes are absent or invalid.
    # END_FUNCTION_CONTRACT: F-M-TODAY-BIRTH-TIME.resolve_profile_birth_time
    sentinel = object()
    mode = getattr(profile, "birth_time_mode", sentinel)
    birth_time = getattr(profile, "birth_time", sentinel)
    bucket = getattr(profile, "birth_time_bucket", sentinel)
    if any(value is sentinel for value in (mode, birth_time, bucket)):
        _fail("profile_attribute")
    return resolve_birth_time(mode=mode, birth_time=birth_time, bucket=bucket, canon=canon)  # type: ignore[arg-type]


# END_BLOCK: PROFILE


__all__ = [
    "BirthTimeProfileLike",
    "BirthTimeResolution",
    "TodayBirthTimeError",
    "resolve_birth_time",
    "resolve_profile_birth_time",
]
