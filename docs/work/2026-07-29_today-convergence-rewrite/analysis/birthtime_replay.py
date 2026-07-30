#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: BIRTHTIME_REPLAY — deterministic merge and publication rules.
# ROLE: Applies the W1 birth-time robustness contract to FactorDay records
#       produced by the direct replay pipeline.
# ############################################################################

# START_MODULE_CONTRACT: M-BIRTHTIME-REPLAY
# purpose: Merge factor observations from canonical control times and resolve
#   only evidence that is present, polarity/sphere-stable, geometrically
#   sect-stable, and inside the canonical orb-margin.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/birthtime_replay.py
# inputs: FactorDay-like records and a named birth-time stratum/grid.
# outputs: merged audit records, public factor records, and exclusions.
# dependencies: direct_replay_pipeline record shape; W1 canon constants.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - A control-point observation is one evidence unit, never a duplicate unit.
#   - Background is never admitted to grouping or independence.
#   - Missing canon orb data fails closed.
#   - Bucket/unknown publication excludes house/angle/lot targets.
# failure_policy: malformed records are rejected with ValueError; unstable or
#   non-canonical facts are returned in excluded_noise with an explicit reason.
# END_MODULE_CONTRACT: M-BIRTHTIME-REPLAY

# START_MODULE_MAP: M-BIRTHTIME-REPLAY
# public_entrypoints:
#   - merge_factor_days
#   - resolve_merged_day
#   - resolve_exact_day
#   - published_ids
# semantic_blocks:
#   - CANONICAL_GRIDS: fixed control-time and orb-margin constants.
#   - MERGE: identity-preserving cross-time aggregation.
#   - PUBLICATION: fail-closed robustness and role resolution.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_birthtime_replay.py
# END_MODULE_MAP: M-BIRTHTIME-REPLAY

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Sequence


# START_BLOCK: CANONICAL_GRIDS
ROLE_ORDER = {"anchor_today": 0, "supporting": 1, "background": 2, "unrelated": 3}
NON_PUBLIC_TARGETS = {"house", "angle", "lot"}
BUCKETS = ("night", "morning", "day", "evening")
CONTROL_GRIDS: dict[str, tuple[str, ...]] = {
    "night": ("00:00", "03:00", "05:59"),
    "morning": ("06:00", "09:00", "11:59"),
    "day": ("12:00", "15:00", "17:59"),
    "evening": ("18:00", "21:00", "23:59"),
    "unknown": ("00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59"),
}
SHIFTED_GRIDS: dict[str, tuple[str, ...]] = {
    "night": ("01:00", "03:00", "05:00"),
    "morning": ("07:00", "09:00", "11:00"),
    "day": ("13:00", "15:00", "17:00"),
    "evening": ("19:00", "21:00", "23:00"),
}
CANONICAL_GAP_HOURS = {**{name: 3.0 for name in BUCKETS}, "unknown": 4.0}
THETA_W = 0.55
THETA_O = 0.5

# Mean geocentric target speeds, deg/hour.  The target is the natal object
# whose longitude changes when a birth-time control point changes.  This is
# the same object-speed interpretation used by the frozen W1 oracle harness.
TARGET_SPEED_DEG_H = {
    "MOON": 0.55,
    "MERCURY": 0.059,
    "VENUS": 0.049,
    "SUN": 0.041,
    "MARS": 0.026,
    "JUPITER": 0.010,
    "SATURN": 0.0050,
    "URANUS": 0.0017,
    "NEPTUNE": 0.0014,
    "PLUTO": 0.0010,
}
# END_BLOCK: CANONICAL_GRIDS


# START_BLOCK: MERGE
def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _identity(factor: Mapping[str, Any]) -> tuple[Any, ...]:
    semantic = factor.get("semantic_key")
    if not semantic:
        raise ValueError("factor is missing semantic_key")
    polarity = factor.get("polarity")
    spheres = tuple(sorted(str(s) for s in (factor.get("spheres") or ())))
    return semantic, polarity, spheres


def _factor_at_time(factor: Mapping[str, Any]) -> dict[str, Any]:
    """Copy one one-time factor, dropping internal cross-time vector fields."""
    return {
        key: value
        for key, value in factor.items()
        if key not in {"presence", "roles", "orbs", "strengths"}
    }


def merge_factor_days(days: Sequence[Any], times: Sequence[str]) -> dict[str, Any]:
    """Merge one FactorDay per control time into evidence vectors.

    A factor is keyed by semantic identity + polarity + product spheres.  A
    changed polarity or sphere therefore cannot silently survive aggregation:
    it becomes a different identity and fails the all-points presence check.
    """
    if len(days) != len(times):
        raise ValueError(f"days/times length mismatch: {len(days)} != {len(times)}")
    if not days:
        raise ValueError("at least one control point is required")
    target_date = str(_value(days[0], "target_date"))
    for day in days:
        if str(_value(day, "target_date")) != target_date:
            raise ValueError("control points must refer to one target date")

    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    order: list[tuple[Any, ...]] = []
    trigger_keys_per_time: list[list[str]] = []
    sect_per_time: list[bool | None] = []
    per_time_counts: list[dict[str, int]] = []
    for day in days:
        trigger_keys_per_time.append(sorted(str(k) for k in (_value(day, "trigger_keys", ()) or ())))
        sect_per_time.append(_value(day, "sect_is_day"))
        factors = tuple(_value(day, "factors", ()) or ())
        per_time_counts.append({
            "factors": len(factors),
            "raw_activations": int(_value(day, "raw_activation_count", 0) or 0),
            "raw_ledger": int(_value(day, "raw_ledger_count", 0) or 0),
            "invalid_ledger": int(_value(day, "invalid_ledger_count", 0) or 0),
            "duplicate_ledger": int(_value(day, "duplicate_ledger_count", 0) or 0),
            "timing_deferred": int(_value(day, "timing_deferred_count", 0) or 0),
        })
        for raw in factors:
            factor = _factor_at_time(raw)
            ident = _identity(factor)
            if ident not in merged:
                base = {
                    key: value
                    for key, value in factor.items()
                    if key not in {"temporal_role", "orb", "strength"}
                }
                base["presence"] = [False] * len(times)
                base["roles"] = [None] * len(times)
                base["orbs"] = [None] * len(times)
                base["strengths"] = [None] * len(times)
                merged[ident] = base
                order.append(ident)
            entry = merged[ident]
            index = len(trigger_keys_per_time) - 1
            entry["presence"][index] = True
            entry["roles"][index] = factor.get("temporal_role")
            entry["orbs"][index] = factor.get("orb")
            entry["strengths"][index] = factor.get("strength")

    return {
        "date": target_date,
        "times": list(times),
        "factors": [merged[key] for key in order],
        "trigger_keys_per_time": trigger_keys_per_time,
        "sect_is_day_per_time": sect_per_time,
        "per_time_counts": per_time_counts,
    }
# END_BLOCK: MERGE


# START_BLOCK: PUBLICATION
def _target_speed(target_key: Any) -> float:
    key = str(target_key or "").strip().upper()
    # Factor records use bare natal names; tolerate canonical qualified keys.
    key = key.rsplit(":", 1)[-1]
    return TARGET_SPEED_DEG_H.get(key, 0.55)


def _max_orb(source_planet: Any, orb_profile: Mapping[str, Any]) -> float | None:
    source = str(source_planet or "").replace("TRANSIT_", "").strip().upper()
    value = orb_profile.get(source)
    if value is None:
        return None
    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return None
    return value_f if value_f > 0.0 else None


def _resolved_role(entry: Mapping[str, Any], trigger_keys_per_time: Sequence[Iterable[str]]) -> str:
    roles: list[str] = []
    semantic = entry["semantic_key"]
    for raw_role, triggers in zip(entry["roles"], trigger_keys_per_time):
        role = str(raw_role or "unrelated")
        if semantic in set(triggers):
            role = "anchor_today"
        roles.append(role)
    if roles and all(role == "anchor_today" for role in roles):
        return "anchor_today"
    return max(roles or ["unrelated"], key=lambda role: ROLE_ORDER.get(role, 3))


def resolve_merged_day(
    merged: Mapping[str, Any],
    *,
    stratum: str,
    orb_profile: Mapping[str, Any],
    theta_o: float = THETA_O,
    hard_exclude: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve a merged bucket/unknown day using the fixed W1 publication rule."""
    times = tuple(str(t) for t in merged["times"])
    triggers = merged["trigger_keys_per_time"]
    sect_values = tuple(merged.get("sect_is_day_per_time") or ())
    sect_stable = not sect_values or any(value is None for value in sect_values) or all(
        value == sect_values[0] for value in sect_values
    )
    gap_hours = float(CANONICAL_GAP_HOURS[stratum])
    public: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for raw in merged["factors"]:
        # Vectors are treated as immutable below; a shallow copy is sufficient
        # and avoids copying thousands of nested audit values per control set.
        entry = dict(raw)
        if not all(bool(value) for value in entry["presence"]):
            entry["exclusion_reason"] = "not_present_at_all_control_points"
            excluded.append(entry)
            continue
        family = str(entry.get("technique_family") or "").lower()
        if not sect_stable and family == "firdar":
            entry["exclusion_reason"] = "time_sensitive_sect"
            excluded.append(entry)
            continue
        aspect = str(entry.get("aspect_type") or "").strip().lower()
        if aspect:
            denom = _max_orb(entry.get("source_planet"), orb_profile)
            if denom is None:
                entry["exclusion_reason"] = "orb_profile_missing"
                excluded.append(entry)
                continue
            margin = _target_speed(entry.get("target_key")) * gap_hours / denom
            ratios = [
                (float(orb) / denom) if orb is not None else None
                for orb in entry["orbs"]
            ]
            if any(ratio is None or ratio + margin > theta_o for ratio in ratios):
                entry["exclusion_reason"] = "orb_margin"
                entry["orb_margin"] = margin
                excluded.append(entry)
                continue
        role = _resolved_role(entry, triggers)
        entry["temporal_role"] = role
        present_orbs = [float(value) for value in entry["orbs"] if value is not None]
        present_strengths = [float(value) for value in entry["strengths"] if value is not None]
        entry["orb"] = max(present_orbs) if present_orbs else None
        entry["strength"] = max(present_strengths) if present_strengths else 0.0
        if hard_exclude and str(entry.get("target_type") or "").lower() in NON_PUBLIC_TARGETS:
            entry["exclusion_reason"] = "birth_time_sensitive_target"
            excluded.append(entry)
            continue
        public.append(entry)
    return public, excluded


def resolve_exact_day(day: Any) -> list[dict[str, Any]]:
    """Resolve exact-time factors; no cross-time stability filtering applies."""
    triggers = set(str(key) for key in (_value(day, "trigger_keys", ()) or ()))
    result: list[dict[str, Any]] = []
    for raw in _value(day, "factors", ()) or ():
        factor = dict(raw)
        if factor.get("semantic_key") in triggers:
            factor["temporal_role"] = "anchor_today"
        result.append(factor)
    return result


def published_ids(factors: Sequence[Mapping[str, Any]]) -> set[str]:
    """Stable public identity set used by parity and shifted-grid fixtures."""
    return {
        json.dumps(
            [factor.get("semantic_key"), factor.get("polarity"), factor.get("spheres")],
            ensure_ascii=False,
            sort_keys=False,
        )
        for factor in factors
    }
# END_BLOCK: PUBLICATION
