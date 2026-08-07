#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: CORPUS-REPLAY — parallel synthetic W1 replay runner.
# ROLE: Runs the direct in-process calculation core over deterministic charts,
#       then applies the canonical exact/bucket/unknown publication rules.
# ############################################################################

# START_MODULE_CONTRACT: M-CORPUS-REPLAY
# purpose: Execute a resumable, privacy-safe 100–200-chart replay corpus using
#   the same calculation core as the HTTP sidecar, with one task per chart.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py
#   - per-chart checkpoint and aggregate report files under a run directory.
# inputs: corpus_manifest.v1.json, date range, shard residues, worker count.
# outputs: atomic per-chart JSON checkpoints, aggregate JSON/Markdown, and
#   deterministic per-day physical-signature JSONL.
# dependencies: direct_replay_pipeline, birthtime_replay, fixed ablation
#   classifier, Swiss Ephemeris and canon files.
# side_effects: Swiss Ephemeris reads; writes only the requested output dir.
# emitted_logs: progress lines to stdout; no product logs.
# invariants:
#   - Source fingerprint must match the manifest unless explicitly overridden.
#   - A failed chart is never counted as a successful chart.
#   - Control streams are sequential per chart (DayDelta correctness); charts
#     are the unit of process-level parallelism.
#   - No HTTP, DB, LLM, production container, or user data is touched.
# failure_policy: chart exceptions produce status=error checkpoints and a
#   non-zero aggregate exit status after all independent charts finish.
# END_MODULE_CONTRACT: M-CORPUS-REPLAY

# START_MODULE_MAP: M-CORPUS-REPLAY
# public_entrypoints:
#   - run_chart
#   - aggregate_checkpoints
#   - write_physical_signatures
#   - main
# semantic_blocks:
#   - PATH_BOOTSTRAP: analysis/repository imports.
#   - CHART_REPLAY: sequential per-chart control streams.
#   - METRICS: compact daily and chart summaries.
#   - PHYSICAL_SIGNATURES: baseline identity and projection evidence.
#   - CLI: resumable shard execution.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_corpus_replay.py
# END_MODULE_MAP: M-CORPUS-REPLAY

from __future__ import annotations

# START_BLOCK: PATH_BOOTSTRAP
import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date as Date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

ANALYSIS = Path(__file__).resolve().parent
REPO = ANALYSIS.parents[4]
for import_root in (ANALYSIS, REPO / "apps/solarsage", REPO / "apps/api"):
    text_root = str(import_root)
    if text_root not in sys.path:
        sys.path.insert(0, text_root)
# END_BLOCK: PATH_BOOTSTRAP

from ablation_harness import FIXES, ORB_PROFILE, classify_day_v2, driver_of  # noqa: E402
from birthtime_replay import (  # noqa: E402
    BUCKETS,
    CONTROL_GRIDS,
    SHIFTED_GRIDS,
    THETA_O,
    THETA_W,
    merge_factor_days,
    published_ids,
    resolve_exact_day,
    resolve_merged_day,
)
from direct_replay_pipeline import ChartInput, DirectReplayPipeline  # noqa: E402
from generate_corpus_manifest import source_fingerprint  # noqa: E402
from solarsage.services.transit_timing import TransitTimingSolver  # noqa: E402
from tone_policy_candidate import TONE_POLICY_VERSION, compute_tone_policy  # noqa: E402


# START_BLOCK: METRICS
MODE_ORDER = ("exact", *BUCKETS, "unknown")
SHIFTED_MODE_ORDER = tuple(f"shifted_{name}" for name in BUCKETS)


def _parse_date(value: str) -> Date:
    try:
        return Date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def _date_range(start: Date, end: Date) -> list[Date]:
    if end < start:
        raise ValueError(f"end date precedes start date: {start} > {end}")
    return [start + timedelta(days=index) for index in range((end - start).days + 1)]


LEGACY_SPHERE_KEYS = frozenset({"decisions", "shopping"})


def _field(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _iter_values(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)


def _sphere_values(item: Any) -> tuple[str, ...]:
    raw = _field(item, "spheres", None)
    if raw is None:
        raw = _field(item, "sphere", None)
    return tuple(sorted({str(value).strip() for value in _iter_values(raw) if str(value).strip()}))


def _facet_value(item: Any) -> Any:
    value = _field(item, "facet", None)
    if value is None:
        value = _field(item, "facet_key", None)
    return value


def _event_id(item: Any) -> str | None:
    for key in ("canonical_event_id", "canonicalEventId", "factor_id", "factorId", "semantic_key"):
        value = _field(item, key, None)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _driver_key(item: Mapping[str, Any]) -> str:
    try:
        return str(driver_of(dict(item)))
    except (KeyError, TypeError, AttributeError):
        return f"src:{str(_field(item, 'source_planet', None) or 'UNKNOWN')}"


def _group_id(group: Mapping[str, Any], member_event_ids: Sequence[str]) -> str:
    explicit = _field(group, "group_id", None) or _field(group, "groupId", None)
    if explicit is not None and str(explicit).strip():
        return str(explicit)
    payload = json.dumps(sorted(member_event_ids), ensure_ascii=False, separators=(",", ":"))
    return f"group:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _legacy_key_counts(items: Sequence[Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in items:
        for key in ("spheres", "sphere", "facet", "facet_key", "theme_keys", "technical_spheres"):
            for value in _iter_values(_field(item, key, None)):
                normalized = str(value).strip().lower()
                if normalized in LEGACY_SPHERE_KEYS:
                    counts[normalized] += 1
    return counts


def _facet_stats(items: Sequence[Any]) -> tuple[Counter[str], int, int]:
    counts: Counter[str] = Counter()
    null_count = 0
    invalid_count = 0
    for item in items:
        facet = _facet_value(item)
        if facet is None:
            null_count += 1
        elif isinstance(facet, str) and facet.strip():
            counts[facet.strip()] += 1
        else:
            invalid_count += 1
    return counts, null_count, invalid_count


def _physical_signature(
    public: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    tone: Mapping[str, Any],
    *,
    state: str,
    day_tone: str,
    target_date: str | None,
) -> dict[str, Any]:
    """Build the deterministic physical/projection identity for one day."""
    significant = [dict(unit) for unit in result.get("sig_units", ()) or ()]
    selected = [dict(unit) for unit in result.get("selected_public_units", ()) or ()]
    public_units = [dict(unit) for unit in public]

    event_driver_keys = {
        event_id: _driver_key(unit)
        for unit in significant
        if (event_id := _event_id(unit)) is not None
    }
    selected_event_ids = sorted(
        {event_id for unit in selected if (event_id := _event_id(unit)) is not None}
    )
    selected_sphere_counts: Counter[str] = Counter()
    all_sphere_counts: Counter[str] = Counter()
    for unit in public_units:
        all_sphere_counts.update(_sphere_values(unit))
    for unit in selected:
        selected_sphere_counts.update(_sphere_values(unit))

    selected_facet_counts, selected_facet_null_count, selected_invalid_facet_count = _facet_stats(selected)
    facet_counts, facet_null_count, invalid_facet_count = _facet_stats(public_units)

    tone_groups = tuple(tone.get("groups", ()) or ())
    group_signatures: list[dict[str, Any]] = []
    for index, raw_group in enumerate(result.get("groups", ()) or ()):
        group = dict(raw_group)
        members = [dict(member) for member in group.get("members", ()) or ()]
        member_event_ids = sorted(
            {event_id for member in members if (event_id := _event_id(member)) is not None}
        )
        group_id = _group_id(group, member_event_ids)
        tone_group = tone_groups[index] if index < len(tone_groups) else {}
        tone_group = dict(tone_group) if isinstance(tone_group, Mapping) else {}
        hero_anchor = group.get("hero_anchor") or {}
        hero_confirmation = group.get("hero_confirmation") or {}
        hero_anchor_id = _event_id(hero_anchor)
        hero_confirmation_id = _event_id(hero_confirmation)
        is_hero = bool(group.get("hero"))
        evidence_level = None
        if is_hero:
            evidence_level = "high" if hero_anchor_id and hero_confirmation_id else "medium"
        driver_keys = sorted(
            {str(value) for value in (tone_group.get("driver_keys") or ())}
            or {_driver_key(member) for member in members}
        )
        group_signatures.append(
            {
                "group_id": group_id,
                "member_event_ids": member_event_ids,
                "driver_keys": driver_keys,
                "independence_keys": driver_keys,
                "n_independent": int(group.get("n_independent", len(driver_keys))),
                "spheres": list(_sphere_values(group)),
                "hero": is_hero,
                "hero_anchor_id": hero_anchor_id,
                "hero_confirmation_id": hero_confirmation_id,
                "hero_evidence_level": evidence_level,
                "polarity": str(tone_group.get("polarity") or "steady"),
            }
        )

    group_signatures.sort(key=lambda record: record["group_id"])
    # House-only rows with no technical/context evidence remain in the
    # physical classifier/audit, but are not canonical event identities: the
    # pre-projection baseline treated them as control metadata. Keep their
    # IDs in the explicit audit field so product projection cannot change the
    # parity universe or erase the physical row.
    significant_event_ids = sorted(
        {
            event_id
            for unit in significant
            if (event_id := _event_id(unit)) is not None
            and not (
                str(unit.get("target_type") or "").lower() == "house"
                and not unit.get("technical_spheres")
                and not unit.get("theme_keys")
            )
        }
    )
    audit_only_event_ids = sorted(
        {
            event_id
            for unit in significant
            if (event_id := _event_id(unit)) is not None
            and str(unit.get("target_type") or "").lower() == "house"
            and not unit.get("technical_spheres")
            and not unit.get("theme_keys")
        }
    )
    unmapped_event_ids = sorted(
        {
            event_id
            for unit in significant
            if (event_id := _event_id(unit)) is not None and not _sphere_values(unit)
        }
    )
    group_ids = [record["group_id"] for record in group_signatures]
    selected_group_ids = sorted(
        record["group_id"]
        for record in group_signatures
        if set(record["member_event_ids"]) & set(selected_event_ids)
    )
    hero_records = [record for record in group_signatures if record["hero"]]
    hero_levels = sorted({record["hero_evidence_level"] for record in hero_records if record["hero_evidence_level"]})
    repeated_spheres = sorted(
        sphere for sphere, count in selected_sphere_counts.items() if count >= 2
    )
    return {
        "schema_version": "today-convergence-physical-signature.v1",
        "target_date": target_date,
        "state": state,
        "dayTone": day_tone,
        "canonical_event_ids": significant_event_ids,
        "audit_only_event_ids": audit_only_event_ids,
        "unmapped_event_ids": unmapped_event_ids,
        "group_ids": group_ids,
        "groups": group_signatures,
        "driver_keys": sorted(set(event_driver_keys.values())),
        "independence_keys": sorted(
            {key for record in group_signatures for key in record["independence_keys"]}
        ),
        "hero_anchor_ids": [record["hero_anchor_id"] for record in hero_records if record["hero_anchor_id"]],
        "hero_confirmation_ids": [
            record["hero_confirmation_id"]
            for record in hero_records
            if record["hero_confirmation_id"]
        ],
        "hero_evidence_level": hero_levels[0] if len(hero_levels) == 1 else hero_levels or None,
        "group_polarity": {
            record["group_id"]: record["polarity"] for record in group_signatures
        },
        "selected_group_ids": selected_group_ids,
        "selected_event_ids": selected_event_ids,
        "selected_sphere_counts": dict(selected_sphere_counts),
        "sphere_counts": dict(all_sphere_counts),
        "repeated_spheres": repeated_spheres,
        "repeated_sphere_selected_count": sum(selected_sphere_counts[sphere] for sphere in repeated_spheres),
        "facet_counts": dict(facet_counts),
        "facet_null_count": facet_null_count,
        "invalid_facet_count": invalid_facet_count,
        "selected_facet_counts": dict(selected_facet_counts),
        "selected_facet_null_count": selected_facet_null_count,
        "selected_invalid_facet_count": selected_invalid_facet_count,
        "group_without_sphere_count": sum(
            not _sphere_values(group) for group in (result.get("groups", ()) or ())
        ),
        "unmapped_count": sum(not _sphere_values(unit) for unit in public_units),
        "legacy_key_occurrences": dict(_legacy_key_counts(public_units)),
    }


def _chart_input(raw: Mapping[str, Any]) -> ChartInput:
    return ChartInput(
        chart_id=str(raw["chart_id"]),
        birth_date=str(raw["birth_date"]),
        birth_time=str(raw["birth_time"]),
        birth_lat=float(raw["birth_lat"]),
        birth_lon=float(raw["birth_lon"]),
        birth_tz=str(raw["birth_tz"]),
        target_tz=str(raw["target_tz"]),
        house_system=str(raw.get("house_system") or "PLACIDUS"),
        current_lat=raw.get("current_lat"),
        current_lon=raw.get("current_lon"),
        current_tz=raw.get("current_tz"),
    )


def _state_result(
    public: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    *,
    trigger_keys=None,
    target_date: str | None = None,
) -> dict[str, Any]:
    result = classify_day_v2(
        public,
        THETA_W,
        THETA_O,
        "B",
        fixes=FIXES,
        trigger_keys=set(trigger_keys or ()),
    )
    tone = compute_tone_policy(result, target_date=target_date)
    diagnostic_state = result["state"]
    # Product terminology distinguishes a day with only non-anchor impulses
    # from a day where a fresh impulse was found.
    if diagnostic_state == "single_impulse" and result.get("n_anchors", 0) == 0:
        diagnostic_state = "quiet_impulses"
    public_state = "convergence_today" if diagnostic_state == "hero" else "quiet_day"
    significant_units = [
        unit for unit in result.get("sig_units", [])
        if unit.get("temporal_role") != "background"
    ]
    independent_units = len({driver_of(unit) for unit in significant_units})
    hero_keys = sorted(
        str(group["hero_anchor"]["semantic_key"])
        for group in result.get("hero_groups", [])
        if group.get("hero_anchor")
    )
    hero_spheres = sorted(
        {
            sphere
            for group in result.get("hero_groups", [])
            for sphere in _sphere_values(group)
        }
    )
    physical_signature = _physical_signature(
        public,
        result,
        tone,
        state=public_state,
        day_tone=tone["day_tone"],
        target_date=target_date,
    )
    return {
        "state": public_state,
        "diagnostic_state": diagnostic_state,
        "n_public": len(public),
        "n_excluded": len(excluded),
        "n_significant": int(result.get("n_significant", 0)),
        "n_anchors": int(result.get("n_anchors", 0)),
        "n_independent_units": independent_units,
        # `groups` is the physical ledger (including unresolved groups for
        # parity/audit); publication metrics count only resolver-backed
        # groups, mirroring production fail-closed selection.
        "n_groups": int(
            result.get(
                "n_groups",
                len(result.get("published_groups", result.get("groups", []))),
            )
        ),
        "n_hero_groups": len(result.get("hero_groups", [])),
        "n_selected_public_units": len(result.get("selected_public_units", [])),
        "excluded_orb_fail_closed": int(result.get("excluded_orb_fail_closed", 0)),
        # `tense` is now the public day-tone boolean.  The old any-selected
        # diagnostic remains explicitly named for before/after comparisons.
        "tense": tone["day_tone"] == "tense",
        "day_tone": tone["day_tone"],
        "legacy_any_selected_tense": tone["legacy_any_selected_tense"],
        "unit_polarity_counts": tone["unit_polarity_counts"],
        "context_polarity_counts": tone["context_polarity_counts"],
        "group_polarity_counts": tone["group_polarity_counts"],
        "tone_scores": tone["tone_scores"],
        "tone_trigger_keys": tone["tone_trigger_keys"],
        "tone_policy_version": tone["tone_policy_version"],
        "target_date": target_date,
        "hero_keys": hero_keys,
        "hero_spheres": hero_spheres,
        "public_ids": sorted(published_ids(public)),
        "excluded_reasons": dict(Counter(str(item.get("exclusion_reason") or "unspecified") for item in excluded)),
        "physical_signature": physical_signature,
    }


def _stream_times(chart: ChartInput, *, include_shifted: bool) -> dict[str, tuple[str, ...]]:
    modes: dict[str, tuple[str, ...]] = {"exact": (chart.birth_time,)}
    modes.update(CONTROL_GRIDS)
    if include_shifted:
        modes.update({f"shifted_{name}": grid for name, grid in SHIFTED_GRIDS.items()})
    return modes


def _compact_day(day: Any) -> dict[str, Any]:
    """Drop current_signals while retaining audit fields needed by merge."""
    return {
        "target_date": str(day.target_date),
        "factors": [dict(factor) for factor in day.factors],
        "trigger_keys": sorted(day.trigger_keys),
        "raw_activation_count": int(day.raw_activation_count),
        "raw_ledger_count": int(day.raw_ledger_count),
        "invalid_ledger_count": int(day.invalid_ledger_count),
        "duplicate_ledger_count": int(day.duplicate_ledger_count),
        "timing_deferred_count": int(day.timing_deferred_count),
        "sect_is_day": day.sect_is_day,
    }


def _classify_mode(mode: str, days_by_time: Mapping[str, Any], times: Sequence[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    if mode == "exact":
        day = days_by_time[times[0]]
        public = resolve_exact_day(day)
        excluded: list[dict[str, Any]] = []
        return _state_result(
            public,
            excluded,
            trigger_keys=day["trigger_keys"],
            target_date=str(day["target_date"]),
        ), {
            "public": public,
            "excluded": excluded,
        }
    merged = merge_factor_days([days_by_time[time] for time in times], times)
    stratum = "unknown" if mode == "unknown" else mode.removeprefix("shifted_")
    public, excluded = resolve_merged_day(
        merged,
        stratum=stratum,
        orb_profile=ORB_PROFILE,
        theta_o=THETA_O,
        hard_exclude=True,
    )
    return _state_result(
        public,
        excluded,
        target_date=str(merged["date"]),
    ), {"public": public, "excluded": excluded}


def _empty_mode_metrics() -> dict[str, Any]:
    return {
        "n_days": 0,
        "state_distribution": Counter(),
        "diagnostic_state_distribution": Counter(),
        "hero_days": [],
        "hero_keys": Counter(),
        "hero_spheres": Counter(),
        "significant": [],
        "independent_units": [],
        "groups": [],
        "public": [],
        "excluded": Counter(),
        "tense_days": 0,
        "day_tones": Counter(),
        "legacy_tense_days": 0,
        "tone_triggers": 0,
        "raw_activations": 0,
        "raw_ledger": 0,
        "invalid_ledger": 0,
        "duplicate_ledger": 0,
        "timing_deferred": 0,
        "selected_sphere_counts": Counter(),
        "sphere_counts": Counter(),
        "facet_counts": Counter(),
        "selected_facet_counts": Counter(),
        "facet_null_count": 0,
        "selected_facet_null_count": 0,
        "invalid_facet_count": 0,
        "selected_invalid_facet_count": 0,
        "repeated_sphere_days": 0,
        "repeated_sphere_selected_count": 0,
        "repeated_spheres": Counter(),
        "group_without_sphere_count": 0,
        "unmapped_count": 0,
        "legacy_key_occurrences": Counter(),
        "physical_signatures": [],
        "daily": [],
    }


def _add_mode_metrics(
    metrics: dict[str, Any],
    date_text: str,
    state: dict[str, Any],
    days: Sequence[Mapping[str, Any]],
    *,
    chart_id: str | None = None,
    birth_mode: str | None = None,
) -> None:
    metrics["n_days"] += 1
    metrics["state_distribution"][state["state"]] += 1
    metrics["diagnostic_state_distribution"][state["diagnostic_state"]] += 1
    if state["state"] == "convergence_today":
        metrics["hero_days"].append(date_text)
        metrics["hero_keys"].update(state["hero_keys"])
        metrics["hero_spheres"].update(state["hero_spheres"])
    metrics["significant"].append(state["n_significant"])
    metrics["independent_units"].append(state["n_independent_units"])
    metrics["groups"].append(state["n_groups"])
    metrics["public"].append(state["n_public"])
    metrics["excluded"].update(state["excluded_reasons"])
    metrics["tense_days"] += int(state["tense"])
    metrics["day_tones"][state["day_tone"]] += 1
    metrics["legacy_tense_days"] += int(state["legacy_any_selected_tense"])
    metrics["tone_triggers"] += len(state["tone_trigger_keys"])
    for day in days:
        metrics["raw_activations"] += int(day["raw_activation_count"])
        metrics["raw_ledger"] += int(day["raw_ledger_count"])
        metrics["invalid_ledger"] += int(day["invalid_ledger_count"])
        metrics["duplicate_ledger"] += int(day["duplicate_ledger_count"])
        metrics["timing_deferred"] += int(day["timing_deferred_count"])
    signature = dict(state["physical_signature"])
    signature["chart_id"] = chart_id
    signature["birth_mode"] = birth_mode
    signature["mode"] = birth_mode
    signature["date"] = date_text
    metrics["selected_sphere_counts"].update(signature.get("selected_sphere_counts") or {})
    metrics["sphere_counts"].update(signature.get("sphere_counts") or {})
    metrics["facet_counts"].update(signature.get("facet_counts") or {})
    metrics["selected_facet_counts"].update(signature.get("selected_facet_counts") or {})
    metrics["facet_null_count"] += int(signature.get("facet_null_count", 0))
    metrics["selected_facet_null_count"] += int(signature.get("selected_facet_null_count", 0))
    metrics["invalid_facet_count"] += int(signature.get("invalid_facet_count", 0))
    metrics["selected_invalid_facet_count"] += int(signature.get("selected_invalid_facet_count", 0))
    repeated_spheres = signature.get("repeated_spheres") or []
    metrics["repeated_sphere_days"] += int(bool(repeated_spheres))
    metrics["repeated_sphere_selected_count"] += int(
        signature.get("repeated_sphere_selected_count", 0)
    )
    metrics["repeated_spheres"].update(repeated_spheres)
    metrics["group_without_sphere_count"] += int(signature.get("group_without_sphere_count", 0))
    metrics["unmapped_count"] += int(signature.get("unmapped_count", 0))
    metrics["legacy_key_occurrences"].update(signature.get("legacy_key_occurrences") or {})
    # Per-day JSONL is the baseline identity artifact.  Aggregate-only audit
    # counters stay in the mode report and are deliberately omitted here to
    # keep the full 120-chart replay compact.
    metrics["physical_signatures"].append(
        {
            key: value
            for key, value in signature.items()
            if key
            not in {
                "sphere_counts",
                "facet_counts",
                "facet_null_count",
                "invalid_facet_count",
                "selected_facet_counts",
                "selected_facet_null_count",
                "selected_invalid_facet_count",
                "group_without_sphere_count",
                "unmapped_count",
                "legacy_key_occurrences",
            }
        }
    )
    metrics["daily"].append({
        "date": date_text,
        "state": state["state"],
        "diagnostic_state": state["diagnostic_state"],
        "n_public": state["n_public"],
        "n_excluded": state["n_excluded"],
        "n_significant": state["n_significant"],
        "n_anchors": state["n_anchors"],
        "n_independent_units": state["n_independent_units"],
        "n_groups": state["n_groups"],
        "n_hero_groups": state["n_hero_groups"],
        "n_selected_public_units": state["n_selected_public_units"],
        "excluded_orb_fail_closed": state["excluded_orb_fail_closed"],
        "tense": state["tense"],
        "day_tone": state["day_tone"],
        "legacy_any_selected_tense": state["legacy_any_selected_tense"],
        "unit_polarity_counts": state["unit_polarity_counts"],
        "context_polarity_counts": state["context_polarity_counts"],
        "group_polarity_counts": state["group_polarity_counts"],
        "tone_scores": state["tone_scores"],
        "tone_trigger_keys": state["tone_trigger_keys"],
        "hero_keys": state["hero_keys"],
        "hero_spheres": state["hero_spheres"],
        "excluded_reasons": state["excluded_reasons"],
    })


def _finalize_mode(metrics: dict[str, Any]) -> dict[str, Any]:
    significant = metrics["significant"]
    public = metrics["public"]
    n_days = max(metrics["n_days"], 1)
    return {
        "n_days": metrics["n_days"],
        "state_distribution": dict(metrics["state_distribution"]),
        "diagnostic_state_distribution": dict(metrics["diagnostic_state_distribution"]),
        "hero_days_n": len(metrics["hero_days"]),
        "hero_days": metrics["hero_days"],
        "hero_keys": dict(metrics["hero_keys"].most_common()),
        "hero_spheres": dict(metrics["hero_spheres"].most_common()),
        "median_significant": statistics.median(significant) if significant else None,
        "mean_significant": round(statistics.mean(significant), 3) if significant else None,
        "median_independent_units": (
            statistics.median(metrics["independent_units"])
            if metrics["independent_units"] else None
        ),
        "mean_independent_units": (
            round(statistics.mean(metrics["independent_units"]), 3)
            if metrics["independent_units"] else None
        ),
        "median_groups": statistics.median(metrics["groups"]) if metrics["groups"] else None,
        "mean_public_per_day": round(statistics.mean(public), 3) if public else 0.0,
        "zero_public_days": sum(value == 0 for value in public),
        "tense_days": metrics["tense_days"],
        "tense_rate": round(metrics["tense_days"] / n_days, 4),
        "day_tone_distribution": dict(metrics["day_tones"]),
        "legacy_tense_days": metrics["legacy_tense_days"],
        "legacy_tense_rate": round(metrics["legacy_tense_days"] / n_days, 4),
        "tone_triggers": metrics["tone_triggers"],
        "excluded_reasons": dict(metrics["excluded"]),
        "raw_activations": metrics["raw_activations"],
        "raw_ledger": metrics["raw_ledger"],
        "invalid_ledger": metrics["invalid_ledger"],
        "duplicate_ledger": metrics["duplicate_ledger"],
        "timing_deferred": metrics["timing_deferred"],
        "selected_sphere_counts": dict(metrics["selected_sphere_counts"].most_common()),
        "sphere_counts": dict(metrics["sphere_counts"].most_common()),
        "facet_counts": dict(metrics["facet_counts"].most_common()),
        "selected_facet_counts": dict(metrics["selected_facet_counts"].most_common()),
        "facet_null_count": metrics["facet_null_count"],
        "selected_facet_null_count": metrics["selected_facet_null_count"],
        "invalid_facet_count": metrics["invalid_facet_count"],
        "selected_invalid_facet_count": metrics["selected_invalid_facet_count"],
        "repeated_sphere_days": metrics["repeated_sphere_days"],
        "repeated_sphere_selected_count": metrics["repeated_sphere_selected_count"],
        "repeated_spheres": dict(metrics["repeated_spheres"].most_common()),
        "group_without_sphere_count": metrics["group_without_sphere_count"],
        "unmapped_count": metrics["unmapped_count"],
        "unmapped_factor_count": metrics["unmapped_count"],
        "legacy_key_occurrences": dict(metrics["legacy_key_occurrences"].most_common()),
        "old_key_occurrences": dict(metrics["legacy_key_occurrences"].most_common()),
        "physical_signatures": metrics["physical_signatures"],
        "daily": metrics["daily"],
    }
# END_BLOCK: METRICS


# START_BLOCK: CHART_REPLAY
def run_chart(config: Mapping[str, Any]) -> dict[str, Any]:
    """Run one chart sequentially and return a JSON-safe checkpoint."""
    started = time.perf_counter()
    raw_chart = config["chart"]
    chart = _chart_input(raw_chart)
    start = Date.fromisoformat(str(config["from_date"]))
    end = Date.fromisoformat(str(config["to_date"]))
    dates = _date_range(start, end)
    include_shifted = bool(config.get("include_shifted", False))
    timing_scope = str(config.get("timing_scope", "convergence_eligible"))
    modes = _stream_times(chart, include_shifted=include_shifted)
    # Build each natal control context once.  DayDelta state is kept separately
    # for each stream, because a different birth-time probe has different facts.
    pipeline = DirectReplayPipeline(timing_scope=timing_scope)
    prepared = {time_text: pipeline.prepare_chart(chart, control_time=time_text) for time_text in sorted({t for grid in modes.values() for t in grid})}
    target_cache: dict[str, Any] = {}
    previous: dict[str, list[Any]] = {}
    previous_date = (start - timedelta(days=1)).isoformat()
    for time_text, context in prepared.items():
        previous_key = f"{previous_date}|{chart.target_tz}|12:00"
        target = target_cache.get(previous_key)
        if target is None:
            target = pipeline.prepare_target(target_date=previous_date, target_tz=chart.target_tz)
            target_cache[previous_key] = target
        previous[time_text] = pipeline.normalize_signals(context, target)

    metrics = {mode: _empty_mode_metrics() for mode in modes}
    shifted_diagnostic = {
        name: {"identical_days": 0, "differing_days": 0, "samples": []}
        for name in BUCKETS
    }
    errors: list[dict[str, str]] = []
    for target_date in dates:
        date_text = target_date.isoformat()
        day_by_time: dict[str, dict[str, Any]] = {}
        cache_key = f"{date_text}|{chart.target_tz}|12:00"
        target = target_cache.get(cache_key)
        if target is None:
            target = pipeline.prepare_target(target_date=date_text, target_tz=chart.target_tz)
            target_cache[cache_key] = target
        timing_solver = TransitTimingSolver(target_jd=target.context.target_jd)
        for time_text, context in prepared.items():
            try:
                day = pipeline.calculate_factor_day(
                    prepared=context,
                    target=target,
                    previous_signals=previous[time_text],
                    timing_solver=timing_solver,
                )
                previous[time_text] = list(day.current_signals)
                day_by_time[time_text] = _compact_day(day)
            except Exception as exc:  # noqa: BLE001 - checkpoint must record chart failure
                errors.append({"date": date_text, "control_time": time_text, "error": repr(exc)})
        if len(day_by_time) != len(prepared):
            # Do not classify a partial date.  Continue to collect independent
            # failures, but never turn a partial result into a successful day.
            continue
        states_by_mode: dict[str, dict[str, Any]] = {}
        for mode, times in modes.items():
            try:
                state, _audit = _classify_mode(mode, day_by_time, times)
                states_by_mode[mode] = state
                _add_mode_metrics(
                    metrics[mode],
                    date_text,
                    state,
                    [day_by_time[t] for t in set(times)],
                    chart_id=chart.chart_id,
                    birth_mode=mode,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"date": date_text, "mode": mode, "error": repr(exc)})
        if include_shifted:
            for name in BUCKETS:
                main_state = states_by_mode.get(name)
                shifted_state = states_by_mode.get(f"shifted_{name}")
                if main_state is None or shifted_state is None:
                    continue
                if main_state["public_ids"] == shifted_state["public_ids"]:
                    shifted_diagnostic[name]["identical_days"] += 1
                else:
                    shifted_diagnostic[name]["differing_days"] += 1
                    if len(shifted_diagnostic[name]["samples"]) < 10:
                        shifted_diagnostic[name]["samples"].append({
                            "date": date_text,
                            "main_only": sorted(set(main_state["public_ids"]) - set(shifted_state["public_ids"]))[:10],
                            "shifted_only": sorted(set(shifted_state["public_ids"]) - set(main_state["public_ids"]))[:10],
                        })

    mode_results = {mode: _finalize_mode(value) for mode, value in metrics.items()}
    return {
        "schema_version": "today-convergence-corpus-chart.v3",
        "status": "error" if errors else "ok",
        "source_fingerprint_sha256": config.get("source_fingerprint_sha256"),
        "chart": dict(raw_chart),
        "calculation": {
        "timing_scope": timing_scope,
        "tone_policy_version": TONE_POLICY_VERSION,
            "theta_w": THETA_W,
            "theta_o": THETA_O,
            "fixes": dict(FIXES),
            "include_shifted": include_shifted,
        },
        "date_range": [start.isoformat(), end.isoformat()],
        "elapsed_s": round(time.perf_counter() - started, 3),
        "errors": errors[:100],
        "modes": mode_results,
        "fixtures": {
            "diagnostic_shifted_grid_sensitivity": shifted_diagnostic if include_shifted else None,
        },
    }
# END_BLOCK: CHART_REPLAY


# START_BLOCK: CLI
def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_manifest(path: Path, *, allow_source_drift: bool) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = str(manifest.get("source_fingerprint_sha256") or "")
    actual = source_fingerprint()
    if expected != actual and not allow_source_drift:
        raise RuntimeError(
            "manifest source fingerprint mismatch; regenerate corpus_manifest.v1.json "
            f"(manifest={expected}, current={actual})"
        )
    manifest["current_source_fingerprint_sha256"] = actual
    return manifest


def _parse_residues(value: str) -> set[int]:
    residues = {int(part.strip()) for part in value.split(",") if part.strip()}
    if not residues or any(item < 0 or item > 4 for item in residues):
        raise argparse.ArgumentTypeError("residues must be comma-separated values 0..4")
    return residues


def aggregate_checkpoints(paths: Sequence[Path]) -> dict[str, Any]:
    charts = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    ok = [chart for chart in charts if chart.get("status") == "ok"]
    errors = [chart for chart in charts if chart.get("status") != "ok"]
    aggregate_modes: dict[str, Any] = {}
    all_modes = sorted({mode for chart in charts for mode in chart.get("modes", {})})
    for mode in all_modes:
        rows = [chart["modes"][mode] for chart in ok if mode in chart.get("modes", {})]
        states: Counter[str] = Counter()
        diagnostic_states: Counter[str] = Counter()
        heroes: list[str] = []
        hero_spheres: Counter[str] = Counter()
        excluded: Counter[str] = Counter()
        n_days = 0
        zero_public = 0
        significant: list[float] = []
        independent: list[float] = []
        groups: list[float] = []
        public: list[float] = []
        tense = 0
        legacy_tense = 0
        day_tones: Counter[str] = Counter()
        tone_triggers = 0
        raw_activations = raw_ledger = invalid = duplicate = deferred = 0
        selected_sphere_counts: Counter[str] = Counter()
        sphere_counts: Counter[str] = Counter()
        facet_counts: Counter[str] = Counter()
        selected_facet_counts: Counter[str] = Counter()
        facet_null_count = selected_facet_null_count = 0
        invalid_facet_count = selected_invalid_facet_count = 0
        repeated_sphere_days = repeated_sphere_selected_count = 0
        repeated_spheres: Counter[str] = Counter()
        group_without_sphere_count = unmapped_count = 0
        legacy_key_occurrences: Counter[str] = Counter()
        physical_signatures_count = 0
        for row in rows:
            n_days += int(row.get("n_days", 0))
            states.update(row.get("state_distribution", {}))
            diagnostic_states.update(row.get("diagnostic_state_distribution", {}))
            heroes.extend(row.get("hero_days", []))
            hero_spheres.update(row.get("hero_spheres", {}))
            excluded.update(row.get("excluded_reasons", {}))
            zero_public += int(row.get("zero_public_days", 0))
            if row.get("median_significant") is not None:
                significant.append(float(row["median_significant"]))
            if row.get("median_independent_units") is not None:
                independent.append(float(row["median_independent_units"]))
            if row.get("median_groups") is not None:
                groups.append(float(row["median_groups"]))
            public.append(float(row.get("mean_public_per_day", 0.0)))
            tense += int(row.get("tense_days", 0))
            legacy_tense += int(row.get("legacy_tense_days", row.get("tense_days", 0)))
            day_tones.update(row.get("day_tone_distribution", {}))
            tone_triggers += int(row.get("tone_triggers", 0))
            raw_activations += int(row.get("raw_activations", 0))
            raw_ledger += int(row.get("raw_ledger", 0))
            invalid += int(row.get("invalid_ledger", 0))
            duplicate += int(row.get("duplicate_ledger", 0))
            deferred += int(row.get("timing_deferred", 0))
            selected_sphere_counts.update(row.get("selected_sphere_counts") or {})
            sphere_counts.update(row.get("sphere_counts") or {})
            facet_counts.update(row.get("facet_counts") or {})
            selected_facet_counts.update(row.get("selected_facet_counts") or {})
            facet_null_count += int(row.get("facet_null_count", 0))
            selected_facet_null_count += int(row.get("selected_facet_null_count", 0))
            invalid_facet_count += int(row.get("invalid_facet_count", 0))
            selected_invalid_facet_count += int(row.get("selected_invalid_facet_count", 0))
            repeated_sphere_days += int(row.get("repeated_sphere_days", 0))
            repeated_sphere_selected_count += int(row.get("repeated_sphere_selected_count", 0))
            repeated_spheres.update(row.get("repeated_spheres") or {})
            group_without_sphere_count += int(row.get("group_without_sphere_count", 0))
            unmapped_count += int(row.get("unmapped_count", row.get("unmapped_factor_count", 0)))
            legacy_key_occurrences.update(
                row.get("legacy_key_occurrences", row.get("old_key_occurrences", {})) or {}
            )
            physical_signatures_count += len(row.get("physical_signatures") or ())
        aggregate_modes[mode] = {
            "charts_ok": len(rows),
            "charts_error": len(errors),
            "n_days": n_days,
            "state_distribution": dict(states),
            "diagnostic_state_distribution": dict(diagnostic_states),
            "hero_days_n": len(heroes),
            "hero_rate": round(len(heroes) / n_days, 6) if n_days else None,
            "hero_spheres": dict(hero_spheres),
            "median_of_chart_medians": statistics.median(significant) if significant else None,
            "median_of_chart_independent_medians": statistics.median(independent) if independent else None,
            "median_of_chart_group_medians": statistics.median(groups) if groups else None,
            "mean_chart_public_per_day": round(statistics.mean(public), 3) if public else None,
            "zero_public_days": zero_public,
            "tense_days": tense,
            "tense_rate": round(tense / n_days, 6) if n_days else None,
            "day_tone_distribution": dict(day_tones),
            "legacy_tense_days": legacy_tense,
            "legacy_tense_rate": round(legacy_tense / n_days, 6) if n_days else None,
            "tone_triggers": tone_triggers,
            "excluded_reasons": dict(excluded),
            "raw_activations": raw_activations,
            "raw_ledger": raw_ledger,
            "invalid_ledger": invalid,
            "duplicate_ledger": duplicate,
            "timing_deferred": deferred,
            "selected_sphere_counts": dict(selected_sphere_counts.most_common()),
            "sphere_counts": dict(sphere_counts.most_common()),
            "facet_counts": dict(facet_counts.most_common()),
            "selected_facet_counts": dict(selected_facet_counts.most_common()),
            "facet_null_count": facet_null_count,
            "selected_facet_null_count": selected_facet_null_count,
            "invalid_facet_count": invalid_facet_count,
            "selected_invalid_facet_count": selected_invalid_facet_count,
            "repeated_sphere_days": repeated_sphere_days,
            "repeated_sphere_selected_count": repeated_sphere_selected_count,
            "repeated_spheres": dict(repeated_spheres.most_common()),
            "group_without_sphere_count": group_without_sphere_count,
            "unmapped_count": unmapped_count,
            "unmapped_factor_count": unmapped_count,
            "legacy_key_occurrences": dict(legacy_key_occurrences.most_common()),
            "old_key_occurrences": dict(legacy_key_occurrences.most_common()),
            "physical_signatures_count": physical_signatures_count,
        }
    shifted_aggregate: dict[str, Any] = {}
    for name in BUCKETS:
        identical = differing = 0
        samples: list[dict[str, Any]] = []
        for chart in ok:
            fixture = (
                chart.get("fixtures", {})
                .get("diagnostic_shifted_grid_sensitivity")
            )
            if not fixture or name not in fixture:
                continue
            identical += int(fixture[name].get("identical_days", 0))
            differing += int(fixture[name].get("differing_days", 0))
            samples.extend(fixture[name].get("samples", [])[: max(0, 10 - len(samples))])
        shifted_aggregate[name] = {
            "identical_days": identical,
            "differing_days": differing,
            "status": "observed" if identical or differing else "not_run",
            "samples": samples[:10],
        }
    return {
        "schema_version": "today-convergence-corpus-run.v3",
        "charts_total": len(charts),
        "charts_ok": len(ok),
        "charts_error": len(errors),
        "error_chart_ids": [str(chart.get("chart", {}).get("chart_id")) for chart in errors],
        "modes": aggregate_modes,
        "fixtures": {"diagnostic_shifted_grid_sensitivity": shifted_aggregate},
        "physical_signatures_count": sum(
            int(row.get("physical_signatures_count", 0))
            for row in aggregate_modes.values()
        ),
        "chart_elapsed_s": round(sum(float(chart.get("elapsed_s", 0.0)) for chart in charts), 3),
        "wall_clock_note": "sum of chart times is not wall-clock time when workers > 1",
    }


def write_physical_signatures(path: Path, paths: Sequence[Path]) -> int:
    """Write stable one-record-per-chart/day/birth-mode baseline signatures."""
    rows: list[dict[str, Any]] = []
    for checkpoint_path in paths:
        chart = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if chart.get("status") != "ok":
            continue
        chart_id = str(chart.get("chart", {}).get("chart_id") or "")
        for mode, mode_result in chart.get("modes", {}).items():
            for raw_signature in mode_result.get("physical_signatures", ()) or ():
                signature = dict(raw_signature)
                signature["chart_id"] = signature.get("chart_id") or chart_id
                signature["birth_mode"] = signature.get("birth_mode") or mode
                signature["mode"] = signature.get("mode") or mode
                signature["target_date"] = signature.get("target_date") or signature.get("date")
                rows.append(signature)
    rows.sort(
        key=lambda row: (
            str(row.get("chart_id") or ""),
            str(row.get("birth_mode") or ""),
            str(row.get("target_date") or ""),
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)
    return len(rows)


def write_markdown(path: Path, run_meta: Mapping[str, Any], aggregate: Mapping[str, Any]) -> None:
    lines = [
        "# Today convergence corpus replay",
        "",
        f"- charts: {aggregate['charts_ok']}/{aggregate['charts_total']} successful",
        f"- date range: {run_meta['date_range'][0]} .. {run_meta['date_range'][1]}",
        f"- residues: {run_meta['residues']}",
        f"- workers: {run_meta['workers']}",
        f"- timing scope: `{run_meta['timing_scope']}`",
        f"- source fingerprint: `{run_meta['source_fingerprint_sha256']}`",
        "",
        "| mode | days | hero | hero rate | day tone | legacy tense | tone tense | median significant | median independent |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for mode, row in aggregate["modes"].items():
        lines.append(
            f"| {mode} | {row['n_days']} | {row['hero_days_n']} | "
            f"{row['hero_rate']} | {row.get('day_tone_distribution', {})} | "
            f"{row.get('legacy_tense_rate')} | {row.get('tense_rate')} | "
            f"{row['median_of_chart_medians']} | "
            f"{row['median_of_chart_independent_medians']} |"
        )
    lines.extend(["", "## Replay instrumentation", ""])
    for mode, row in aggregate["modes"].items():
        lines.append(
            f"- {mode}: selected spheres {row.get('selected_sphere_counts', {})}; "
            f"repeated-sphere days {row.get('repeated_sphere_days', 0)}; "
            f"legacy keys {row.get('old_key_occurrences', {})}; "
            f"unmapped {row.get('unmapped_count', 0)}; "
            f"group-without-sphere {row.get('group_without_sphere_count', 0)}; "
            f"facet/null/invalid {row.get('facet_counts', {})}/"
            f"{row.get('facet_null_count', 0)}/"
            f"{row.get('invalid_facet_count', 0)}."
        )
    lines.extend([
        "",
        "This is a diagnostic/replay artifact. State frequencies are monitoring, not a quota or acceptance gate.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ANALYSIS / "corpus_manifest.v1.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--residues", type=_parse_residues, default={0})
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit-charts", type=int, default=None)
    parser.add_argument("--from-date", type=_parse_date, default=None)
    parser.add_argument("--to-date", type=_parse_date, default=None)
    parser.add_argument("--include-shifted", action="store_true")
    parser.add_argument("--timing-scope", choices=("all", "convergence_eligible"), default="convergence_eligible")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-source-drift", action="store_true")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    manifest = _load_manifest(args.manifest, allow_source_drift=args.allow_source_drift)
    manifest_start, manifest_end = map(Date.fromisoformat, manifest["date_range"])
    start = max(manifest_start, args.from_date or manifest_start)
    end = min(manifest_end, args.to_date or manifest_end)
    if end < start:
        parser.error("requested date range is outside manifest")
    charts = [
        chart for chart in manifest["charts"]
        if int(chart["shard_residue_mod5"]) in args.residues
    ]
    if args.limit_charts is not None:
        charts = charts[: max(0, args.limit_charts)]
    if not charts:
        parser.error("no charts selected")

    output_dir = args.output_dir.resolve()
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    run_meta = {
        "schema_version": "today-convergence-corpus-run.v3",
        "manifest": str(args.manifest.resolve()),
        "manifest_source_fingerprint_sha256": manifest.get("source_fingerprint_sha256"),
        "source_fingerprint_sha256": manifest.get("current_source_fingerprint_sha256"),
        "date_range": [start.isoformat(), end.isoformat()],
        "residues": sorted(args.residues),
        "workers": args.workers,
        "timing_scope": args.timing_scope,
        "include_shifted": args.include_shifted,
        "chart_ids": [chart["chart_id"] for chart in charts],
        "physical_signatures_file": "physical_signatures.jsonl",
        "started_at_epoch": time.time(),
    }
    _atomic_write(output_dir / "run_meta.json", run_meta)

    tasks: list[dict[str, Any]] = []
    checkpoint_paths: list[Path] = []
    for chart in charts:
        path = checkpoint_dir / f"{chart['chart_id']}.json"
        checkpoint_paths.append(path)
        if args.resume and path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                if (
                    cached.get("schema_version") == "today-convergence-corpus-chart.v3"
                    and cached.get("status") == "ok"
                    and cached.get("date_range") == [start.isoformat(), end.isoformat()]
                    and cached.get("source_fingerprint_sha256")
                    == manifest.get("current_source_fingerprint_sha256")
                    and all(
                        "physical_signatures" in mode_result
                        for mode_result in (cached.get("modes") or {}).values()
                    )
                ):
                    continue
            except (OSError, json.JSONDecodeError):
                pass
        tasks.append({
            "chart": chart,
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
            "include_shifted": args.include_shifted,
            "timing_scope": args.timing_scope,
            "source_fingerprint_sha256": manifest.get("current_source_fingerprint_sha256"),
        })

    print(f"corpus: {len(charts)} charts, {len(tasks)} pending, {args.workers} workers, {start}..{end}", flush=True)
    failures = 0
    if tasks:
        # spawn avoids inheriting a configured Swiss Ephemeris thread/runtime
        # state from the parent and makes local/remote behavior identical.
        import multiprocessing as mp

        context = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=context) as pool:
            futures = {pool.submit(run_chart, task): task["chart"]["chart_id"] for task in tasks}
            for index, future in enumerate(as_completed(futures), start=1):
                chart_id = futures[future]
                path = checkpoint_dir / f"{chart_id}.json"
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    result = {
                        "schema_version": "today-convergence-corpus-chart.v3",
                        "status": "error",
                        "source_fingerprint_sha256": manifest.get("current_source_fingerprint_sha256"),
                        "chart": {"chart_id": chart_id},
                        "errors": [{"error": repr(exc)}],
                    }
                if result.get("status") != "ok":
                    failures += 1
                _atomic_write(path, result)
                print(
                    f"[{index}/{len(tasks)}] {chart_id}: {result.get('status')} "
                    f"{result.get('elapsed_s', '?')}s",
                    flush=True,
                )

    # Only aggregate selected chart paths.  A resumed run may have no tasks.
    existing = [path for path in checkpoint_paths if path.exists()]
    aggregate = aggregate_checkpoints(existing)
    aggregate["run_meta"] = run_meta
    signature_path = output_dir / "physical_signatures.jsonl"
    aggregate["physical_signatures_file"] = signature_path.name
    aggregate["physical_signatures_count"] = write_physical_signatures(
        signature_path,
        existing,
    )
    _atomic_write(output_dir / "aggregate.json", aggregate)
    write_markdown(output_dir / "report.md", run_meta, aggregate)
    print(json.dumps({"aggregate": aggregate, "failures": failures}, ensure_ascii=False, indent=2))
    return 1 if aggregate["charts_error"] else 0
# END_BLOCK: CLI


if __name__ == "__main__":
    raise SystemExit(main())
