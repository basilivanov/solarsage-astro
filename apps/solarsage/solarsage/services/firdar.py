# ############################################################################
# AI_HEADER: MODULE_SIDECAR_FIRDAR — Firdar period calculation.
# ROLE: Calculates firdar_major and firdar_minor period lords for a birth +
#       target context. Loads period sequences from grace/canon/firdar.v1.yml.
# ############################################################################

from __future__ import annotations

import os
import pathlib
from datetime import date as Date
from typing import Any

import yaml

# ── Canon loading ────────────────────────────────────────────────────────────


def _resolve_canon_path(relative: str) -> str:
    """Resolve a path relative to the project root (grace/canon/…)."""
    here = pathlib.Path(__file__).resolve().parent  # services/
    root = here.parent.parent.parent.parent  # 4 levels up to project root
    return os.path.join(root, relative)


def _load_firdar_canon() -> dict[str, Any]:
    path = _resolve_canon_path("grace/canon/firdar.v1.yml")
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("firdar.v1.yml must be a mapping")
    required_keys = ["cycle_years", "minor_divisions", "day_sequence", "night_sequence", "node_minor_sequence"]
    for key in required_keys:
        if key not in data:
            raise KeyError(f"firdar.v1.yml missing required key: {key}")
    return data


# ── Date helpers ─────────────────────────────────────────────────────────────


def _completed_years(birth_local: Date, target_local: Date) -> int:
    """Completed full years between two local dates."""
    age = target_local.year - birth_local.year
    if (target_local.month, target_local.day) < (birth_local.month, birth_local.day):
        age -= 1
    return max(0, age)


def _days_in_year(year: int) -> int:
    """Days in a given year (365 or 366 for leap years)."""
    import calendar
    return 366 if calendar.isleap(year) else 365


def _age_years_decimal(birth_local: Date, target_local: Date) -> float:
    """Age in years as a decimal, from local dates."""
    completed = _completed_years(birth_local, target_local)
    # Elapsed days since last birthday
    birthday_this_year = Date(target_local.year, birth_local.month, birth_local.day)
    if birthday_this_year > target_local:
        birthday_this_year = Date(target_local.year - 1, birth_local.month, birth_local.day)
    elapsed_days = (target_local - birthday_this_year).days
    days_in_birth_year = _days_in_year(birthday_this_year.year)
    return completed + elapsed_days / days_in_birth_year


# ── Firdar calculation ───────────────────────────────────────────────────────


class FirdarContext:
    """Holds the full firdar calculation result."""

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
        # Edge case: exact boundary (age == end of a period)
        # Boundary rule: at exact boundary, the NEXT period starts
        # So if cycle_age == end, choose the next period
        # But we need to handle this for the last period wrapping to first
        cumulative = end

    # If we reached the end, wrap around (shouldn't happen if sequences cover cycle_years)
    if major_lord is None:
        major_lord = sequence[0]["lord"]
        major_start_age = 0.0
        major_end_age = float(sequence[0]["years"])
        major_years = major_end_age

    # Minor subperiod
    # Determine minor sequence base
    if major_lord in ("NORTH_NODE_TRUE", "SOUTH_NODE"):
        minor_seq = list(canon["node_minor_sequence"])
    else:
        # Build the 7-planet sequence from the day/night sequence (filtering node entries)
        all_planets: list[str] = []
        for entry in sequence:
            if entry["lord"] not in ("NORTH_NODE_TRUE", "SOUTH_NODE"):
                all_planets.append(entry["lord"])
        # Rotate so major lord is first
        try:
            idx = all_planets.index(major_lord)
        except ValueError:
            idx = 0
        minor_seq = all_planets[idx:] + all_planets[:idx]

    minor_division_years = major_years / minor_divisions
    minor_offset = cycle_age - major_start_age
    minor_index = int(minor_offset // minor_division_years)
    # Clamp to valid range
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
