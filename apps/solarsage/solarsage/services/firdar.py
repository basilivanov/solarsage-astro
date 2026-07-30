# ############################################################################
# AI_HEADER: MODULE_SIDECAR_FIRDAR — Firdar period calculation.
# ROLE: Calculates firdar_major and firdar_minor period lords for a birth +
#       target context. Loads period sequences from grace/canon/firdar.v1.yml.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-FIRDAR
# purpose: Firdar period calculation. Determines active firdar_major and
#          firdar_minor lords for a birth+target local date pair using
#          day/night canon sequences from grace/canon/firdar.v1.yml.
# owns:
#   - apps/solarsage/solarsage/services/firdar.py
# inputs: birth_local (Date), target_local (Date), is_day_birth (bool),
#         sun_house (int|None), canon (dict|None)
# outputs: FirdarContext with major/minor lord info, debug payloads
# dependencies: grace/canon/firdar.v1.yml, yaml, datetime
# side_effects: Reads firdar.v1.yml canon file on first load if canon=None
# emitted_logs: none
# invariants:
#   - age_years uses actual birthday interval, not calendar year
#   - Feb 29 births clamp to Feb 28 in non-leap years
#   - canon is validated: cycle_years >0, minor_divisions >0, sequences non-empty,
#     each entry has lord and positive years, year sum == cycle_years,
#     node_minor_sequence length == minor_divisions
# failure_policy: Raises ValueError on malformed canon values (bad sums, zero divisions,
#   empty sequences); KeyError on missing required canon keys; zero-division guard
#   returns 0 if interval_days <= 0 in age calculation
# END_MODULE_CONTRACT: M-SIDECAR-FIRDAR

# START_MODULE_MAP: M-SIDECAR-FIRDAR
# public_entrypoints:
#   - calculate_firdar
#   - _load_firdar_canon
#   - FirdarPeriodBounds
#   - calculate_firdar_period_bounds
# semantic_blocks:
#   - CANON_LOADING: canon file loading
#   - DATE_HELPERS: birthday clamping, age decimal calculation
#   - FIRDAR_CALCULATION: main period/superiod logic
# owned_tests:
#   - tests/test_firdar.py
# END_MODULE_MAP: M-SIDECAR-FIRDAR

from __future__ import annotations

import calendar
import os
import pathlib
from copy import deepcopy
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from functools import lru_cache
from math import ceil, floor
from typing import Any

import yaml

# ── Display names for node-period evidence ───────────────────────────────────
# target_key remains uppercase; evidence uses readable names.

_DISPLAY_NAMES: dict[str, str] = {
    "NORTH_NODE_TRUE": "North Node",
    "SOUTH_NODE": "South Node",
}


def _display_name(key: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._display_name
    # purpose: Return human-readable name for a firdar lord key (North Node/South Node).
    # inputs: key — uppercase lord key (e.g. NORTH_NODE_TRUE)
    # returns: display string; falls back to key if not found
    # side_effects: none
    # error_behavior: Returns key unchanged if not in display map
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._display_name
    return _DISPLAY_NAMES.get(key.upper(), key)


# START_BLOCK: CANON_LOADING


def _resolve_canon_path(relative: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._resolve_canon_path
    # purpose: Resolve a path relative to the project root (grace/canon/…).
    # inputs: relative — relative path from project root
    # returns: absolute path string
    # side_effects: none
    # error_behavior: Returns path regardless of existence
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._resolve_canon_path
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent.parent.parent
    return os.path.join(root, relative)


@lru_cache(maxsize=8)
def _read_firdar_canon_cached(path: str, mtime_ns: int, size: int) -> dict[str, Any]:
    """Read one firdar canon revision once per worker process."""
    del mtime_ns, size
    with open(path) as f:
        return yaml.safe_load(f)


def _load_firdar_canon() -> dict[str, Any]:
    """Load and validate firdar canon, reusing an immutable parsed revision."""
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._load_firdar_canon
    # purpose: Load firdar period sequences from grace/canon/firdar.v1.yml.
    # inputs: none
    # returns: dict with cycle_years, minor_divisions, day_sequence,
    #          night_sequence, node_minor_sequence
    # side_effects: reads file
    # error_behavior: Raises ValueError on non-mapping; KeyError on missing keys;
    #   ValueError on malformed canon values (zero cycle, empty sequences, sum mismatch)
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._load_firdar_canon
    path = _resolve_canon_path("grace/canon/firdar.v1.yml")
    stat = os.stat(path)
    data = deepcopy(_read_firdar_canon_cached(path, stat.st_mtime_ns, stat.st_size))
    if not isinstance(data, dict):
        raise ValueError("firdar.v1.yml must be a mapping")
    required_keys = ["cycle_years", "minor_divisions", "day_sequence", "night_sequence", "node_minor_sequence"]
    for key in required_keys:
        if key not in data:
            raise KeyError(f"firdar.v1.yml missing required key: {key}")

    # ── Canon value validation ────────────────────────────────────
    _validate_firdar_canon(data)
    return data


def _validate_firdar_canon(data: dict) -> None:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._validate_firdar_canon
    # purpose: Validate firdar canon values: cycle_years, minor_divisions,
    #          sequence sums, node_minor_sequence length.
    # inputs: data — loaded canon dict with all required keys
    # returns: None; raises on invalid values
    # side_effects: none
    # error_behavior: ValueError on zero/negative values, empty sequences,
    #   sum mismatch, node sequence length mismatch
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._validate_firdar_canon
    """Validate firdar canon values. Raises ValueError on malformed data."""
    cycle_years = int(data["cycle_years"])
    if cycle_years <= 0:
        raise ValueError(f"cycle_years must be > 0, got {cycle_years}")
    minor_divisions = int(data["minor_divisions"])
    if minor_divisions <= 0:
        raise ValueError(f"minor_divisions must be > 0, got {minor_divisions}")

    for seq_key in ("day_sequence", "night_sequence"):
        seq = data[seq_key]
        if not isinstance(seq, list) or len(seq) == 0:
            raise ValueError(f"{seq_key} must be a non-empty list")
        total = 0.0
        for entry in seq:
            lord = entry.get("lord")
            years = entry.get("years")
            if not lord:
                raise ValueError(f"{seq_key} entry missing 'lord': {entry}")
            if not years or float(years) <= 0:
                raise ValueError(f"{seq_key} entry {lord} has invalid years: {years}")
            total += float(years)
        if abs(total - cycle_years) > 1e-6:
            raise ValueError(
                f"{seq_key} years sum {total} != cycle_years {cycle_years}"
            )

    node_seq = data["node_minor_sequence"]
    if not isinstance(node_seq, list) or len(node_seq) == 0:
        raise ValueError("node_minor_sequence must be a non-empty list")
    if len(node_seq) != minor_divisions:
        raise ValueError(
            f"node_minor_sequence length {len(node_seq)} != minor_divisions {minor_divisions}"
        )


# END_BLOCK: CANON_LOADING

# START_BLOCK: DATE_HELPERS

@dataclass(frozen=True)
class FirdarPeriodBounds:
    major_active_from: Date
    major_active_until: Date
    minor_active_from: Date
    minor_active_until: Date

def calculate_firdar_period_bounds(
    *,
    birth_local: Date,
    context: FirdarContext,
) -> FirdarPeriodBounds:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR.calculate_firdar_period_bounds
    # purpose: Calculate firdar period active_from and active_until bounds.
    # inputs: birth_local - Date; context - FirdarContext.
    # returns: FirdarPeriodBounds object with inclusive local-date boundaries.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: propagates date arithmetic errors for invalid dates.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR.calculate_firdar_period_bounds
    def age_boundary_to_date(age: float) -> Date:
        whole = floor(age + 1e-12)
        fraction = age - whole
        interval_start = _clamp_birthday(birth_local, birth_local.year + whole)
        interval_end = _clamp_birthday(birth_local, birth_local.year + whole + 1)
        interval_days = (interval_end - interval_start).days
        offset_days = ceil(fraction * interval_days - 1e-12)
        return interval_start + timedelta(days=offset_days)

    cycle_base = context.cycle_index * context.cycle_years
    major_start_abs = cycle_base + context.major_start_age
    major_end_abs   = cycle_base + context.major_end_age
    minor_start_abs = cycle_base + context.minor_start_age
    minor_end_abs   = cycle_base + context.minor_end_age

    major_active_from = age_boundary_to_date(major_start_abs)
    major_active_until = age_boundary_to_date(major_end_abs) - timedelta(days=1)
    minor_active_from = age_boundary_to_date(minor_start_abs)
    minor_active_until = age_boundary_to_date(minor_end_abs) - timedelta(days=1)

    return FirdarPeriodBounds(
        major_active_from=major_active_from,
        major_active_until=major_active_until,
        minor_active_from=minor_active_from,
        minor_active_until=minor_active_until,
    )


def _clamp_birthday(birth_local: Date, year: int) -> Date:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._clamp_birthday
    # purpose: Return birthday in a given year, clamping Feb 29 to Feb 28
    #          in non-leap years.
    # inputs: birth_local — birth date; year — target year
    # returns: Date in given year, safe for Feb 29 births
    # side_effects: none
    # error_behavior: ValueError on invalid date components (calendar range)
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._clamp_birthday
    """Return birthday in a given year, clamping Feb 29 to Feb 28 in non-leap years."""
    if birth_local.month == 2 and birth_local.day == 29 and not calendar.isleap(year):
        return Date(year, 2, 28)
    return Date(year, birth_local.month, birth_local.day)


def _completed_years(birth_local: Date, target_local: Date) -> int:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._completed_years
    # purpose: Completed full years between two local dates.
    # inputs: birth_local, target_local — dates
    # returns: integer completed years (>= 0)
    # side_effects: none
    # error_behavior: Returns 0 if target before birth
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._completed_years
    """Completed full years between two local dates.

    Uses clamped birthday (Feb 29→Feb 28 in non-leap years) for comparison
    so that the clamped anniversary is treated as the actual birthday.
    """
    age = target_local.year - birth_local.year
    # Compare with clamped birthday for the target year
    birthday_this_year = _clamp_birthday(birth_local, target_local.year)
    if target_local < birthday_this_year:
        age -= 1
    return max(0, age)


def _last_birthday(birth_local: Date, target_local: Date) -> Date:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._last_birthday
    # purpose: Return the most recent birthday on or before target_local.
    #          Clamps Feb 29 to Feb 28 in non-leap years.
    # inputs: birth_local, target_local — dates
    # returns: Date of last birthday
    # side_effects: none
    # error_behavior: May return date after target for edge cases
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._last_birthday
    """Return the most recent birthday on or before target_local.
    Clamps Feb 29 to Feb 28 in non-leap years."""
    candidate = _clamp_birthday(birth_local, target_local.year)
    if candidate <= target_local:
        return candidate
    return _clamp_birthday(birth_local, target_local.year - 1)


def _next_birthday(birth_local: Date, last_bday: Date) -> Date:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._next_birthday
    # purpose: Return the next birthday after last_bday.
    #          For Feb 29 births, returns Feb 28 in non-leap years, Feb 29 in leap.
    # inputs: birth_local — original birth date; last_bday — most recent birthday
    # returns: Date of next birthday
    # side_effects: none
    # error_behavior: ValueError on invalid date components
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._next_birthday
    """Return the next birthday after last_bday.
    For Feb 29 births, returns Feb 28 in non-leap years, Feb 29 in leap years."""
    return _clamp_birthday(birth_local, last_bday.year + 1)


def _age_years_decimal(birth_local: Date, target_local: Date) -> float:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._age_years_decimal
    # purpose: Age in years as a decimal, using actual birthday interval denominator.
    #          Uses exact interval between last and next birthday as denominator.
    #          Clamps Feb 29 to Feb 28 in non-leap years.
    # inputs: birth_local, target_local — dates
    # returns: float age_years (>= 0.0)
    # side_effects: none
    # error_behavior: ZeroDivisionError if interval_days <= 0 (malformed dates)
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR._age_years_decimal
    """Age in years as a decimal, using actual birthday interval denominator.

    Uses the exact interval between last and next birthday as denominator.
    This ensures age_years == 10.0 precisely on the 10th birthday,
    and age_years < 10.0 one day before.

    Feb 29 births clamp to Feb 28 in non-leap years for both last/next birthdays.
    """
    completed = _completed_years(birth_local, target_local)
    last_bday = _last_birthday(birth_local, target_local)
    next_bday = _next_birthday(birth_local, last_bday)
    elapsed_days = (target_local - last_bday).days
    interval_days = (next_bday - last_bday).days
    if interval_days <= 0:
        return float(completed)
    return completed + elapsed_days / interval_days


# END_BLOCK: DATE_HELPERS

# START_BLOCK: FIRDAR_CALCULATION


class FirdarContext:
    """Holds the full firdar calculation result."""

    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR.FirdarContext.__init__
    # purpose: Hold the full firdar calculation result (major/minor lords, ages,
    #          cycle info, subperiod data).
    # inputs: All keyword-only parameters defining period state
    # returns: None
    # side_effects: none
    # error_behavior: None (pure data storage)
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR.FirdarContext.__init__
    def __init__(
        self,
        *,
        is_day_birth: bool,
        sun_house: int | None,
        age_years: float,
        cycle_age: float,
        cycle_index: int,
        major_lord: str,
        major_start_age: float,
        major_end_age: float,
        major_years: float,
        minor_lord: str,
        minor_index: int,
        minor_start_age: float,
        minor_end_age: float,
        minor_sequence: list[str],
        cycle_years: int,
        schema_version: str,
    ) -> None:
        self.is_day_birth = is_day_birth
        self.sun_house = sun_house
        self.age_years = age_years
        self.cycle_age = cycle_age
        self.cycle_index = cycle_index
        self.major_lord = major_lord
        self.major_start_age = major_start_age
        self.major_end_age = major_end_age
        self.major_years = major_years
        self.minor_lord = minor_lord
        self.minor_index = minor_index
        self.minor_start_age = minor_start_age
        self.minor_end_age = minor_end_age
        self.minor_sequence = minor_sequence
        self.cycle_years = cycle_years
        self.schema_version = schema_version


def calculate_firdar(
    *,
    birth_local: Date,
    target_local: Date,
    is_day_birth: bool,
    sun_house: int | None,
    canon: dict[str, Any] | None = None,
) -> FirdarContext:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR.calculate_firdar
    # purpose: Calculate firdar context for a birth+target local date pair.
    # inputs:
    #   birth_local — birth local date
    #   target_local — target local date
    #   is_day_birth — True if Sun in houses 7-12 (day chart)
    #   sun_house — natal Sun house (for debug)
    #   canon — optional pre-loaded canon dict; loaded from file if None;
    #           validated for correct values before use
    # returns: FirdarContext with major/minor lord, ages, debug payloads
    # side_effects: loads canon file if canon=None
    # error_behavior: KeyError on missing required canon keys;
    #   ValueError on malformed canon values (zero cycle, empty sequences, sum mismatch)
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-FIRDAR.calculate_firdar
    """Calculate firdar context for a birth+target local date pair.

    Args:
        birth_local: Birth local date.
        target_local: Target local date.
        is_day_birth: Whether birth is a day chart (Sun in houses 7-12).
        sun_house: Natal Sun house number (for debug).
        canon: Optional pre-loaded canon dict; loaded from file if None.

    Returns:
        FirdarContext with major and minor period information.
    """
    if canon is None:
        canon = _load_firdar_canon()
    else:
        _validate_firdar_canon(canon)

    cycle_years = int(canon["cycle_years"])
    minor_divisions = int(canon["minor_divisions"])

    # Age
    age_years = _age_years_decimal(birth_local, target_local)
    cycle_age = age_years % cycle_years
    cycle_index = int(age_years // cycle_years)

    # Select sequence
    sequence_key = "day_sequence" if is_day_birth else "night_sequence"
    sequence = canon[sequence_key]

    # Find active major period
    major_lord: str | None = None
    major_start_age: float = 0.0
    major_end_age: float = 0.0
    major_years: float = 0.0

    cumulative = 0.0
    for entry in sequence:
        lord = entry["lord"]
        years = float(entry["years"])
        start = cumulative
        end = cumulative + years
        if start <= cycle_age < end:
            major_lord = lord
            major_start_age = start
            major_end_age = end
            major_years = years
            break
        cumulative = end

    # Fallback for edge cases
    if major_lord is None:
        major_lord = sequence[0]["lord"]
        major_start_age = 0.0
        major_end_age = float(sequence[0]["years"])
        major_years = major_end_age

    # Minor subperiod
    if major_lord in ("NORTH_NODE_TRUE", "SOUTH_NODE"):
        minor_seq = list(canon["node_minor_sequence"])
    else:
        all_planets: list[str] = []
        for entry in sequence:
            if entry["lord"] not in ("NORTH_NODE_TRUE", "SOUTH_NODE"):
                all_planets.append(entry["lord"])
        try:
            idx = all_planets.index(major_lord)
        except ValueError:
            idx = 0
        minor_seq = all_planets[idx:] + all_planets[:idx]

    minor_division_years = major_years / minor_divisions
    minor_offset = cycle_age - major_start_age
    minor_index = int(minor_offset // minor_division_years)
    minor_index = min(max(minor_index, 0), len(minor_seq) - 1)

    minor_lord = minor_seq[minor_index]
    minor_start_age = major_start_age + minor_index * minor_division_years
    minor_end_age = minor_start_age + minor_division_years

    return FirdarContext(
        is_day_birth=is_day_birth,
        sun_house=sun_house,
        age_years=age_years,
        cycle_age=cycle_age,
        cycle_index=cycle_index,
        major_lord=major_lord,
        major_start_age=major_start_age,
        major_end_age=major_end_age,
        major_years=major_years,
        minor_lord=minor_lord,
        minor_index=minor_index,
        minor_start_age=minor_start_age,
        minor_end_age=minor_end_age,
        minor_sequence=minor_seq,
        cycle_years=cycle_years,
        schema_version=canon.get("schema_version", "firdar.v1"),
    )


# END_BLOCK: FIRDAR_CALCULATION
