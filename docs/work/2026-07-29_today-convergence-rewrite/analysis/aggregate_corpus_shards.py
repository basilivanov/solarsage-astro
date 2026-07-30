#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: CORPUS_SHARD_AGGREGATOR — merge replay checkpoints and audit them.
# ROLE: Combines independently calculated local/remote corpus shards without
#       rerunning ephemeris calculations or importing the calculation runtime.
# ############################################################################

# START_MODULE_CONTRACT: M-CORPUS-SHARD-AGGREGATOR
# purpose: Validate and aggregate Today convergence corpus replay checkpoints.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/aggregate_corpus_shards.py
# inputs: one or more replay output/checkpoint directories containing v2 JSON.
# outputs: compact combined JSON and Markdown reports.
# dependencies: Python standard library only.
# side_effects: reads checkpoint JSON; atomically writes requested report files.
# emitted_logs: none.
# invariants:
#   - every chart_id is unique across shards;
#   - successful checkpoints share one source fingerprint and date range;
#   - state frequency is reported as observation, never used as a quota gate;
#   - tense streaks are derived only from the checkpoint's selected public state.
# failure_policy: raises ValueError on incompatible/duplicate/incomplete inputs;
#   CLI exits non-zero and does not write a misleading successful report.
# END_MODULE_CONTRACT: M-CORPUS-SHARD-AGGREGATOR

# START_MODULE_MAP: M-CORPUS-SHARD-AGGREGATOR
# public_entrypoints:
#   - aggregate_shards
#   - write_reports
#   - main
# semantic_blocks:
#   - INPUTS: resolve and validate checkpoint files.
#   - STATISTICS: histogram quantiles and contiguous tense streaks.
#   - AGGREGATION: streaming cross-shard metrics and invariant checks.
#   - OUTPUT: atomic JSON/Markdown report writers.
#   - CLI: command-line entrypoint.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_aggregate_corpus_shards.py
# END_MODULE_MAP: M-CORPUS-SHARD-AGGREGATOR

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
from collections import Counter
from datetime import date as Date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMAS = frozenset({
    "today-convergence-corpus-chart.v2",  # diagnostic baseline
    "today-convergence-corpus-chart.v3",  # tone-aware final candidate
})
PUBLIC_STATES = frozenset({"convergence_today", "quiet_day"})


# START_BLOCK: INPUTS
def _checkpoint_paths(inputs: Sequence[Path]) -> list[Path]:
    paths: set[Path] = set()
    for raw in inputs:
        path = raw.resolve()
        if path.is_file():
            paths.add(path)
            continue
        checkpoint_dir = path / "checkpoints" if (path / "checkpoints").is_dir() else path
        if not checkpoint_dir.is_dir():
            raise ValueError(f"checkpoint input does not exist: {raw}")
        paths.update(item.resolve() for item in checkpoint_dir.glob("*.json"))
    if not paths:
        raise ValueError("no checkpoint JSON files found")
    return sorted(paths)


def _load_checkpoint(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid checkpoint {path}: {exc}") from exc
    if payload.get("schema_version") not in SCHEMAS:
        raise ValueError(
            f"unsupported checkpoint schema in {path}: {payload.get('schema_version')!r}"
        )
    return payload, hashlib.sha256(raw).hexdigest()
# END_BLOCK: INPUTS


# START_BLOCK: STATISTICS
def _histogram_quantile(histogram: Mapping[int, int], quantile: float) -> float | None:
    count = sum(histogram.values())
    if not count:
        return None
    rank = max(0, min(count - 1, round((count - 1) * quantile)))
    seen = 0
    for value in sorted(histogram):
        seen += histogram[value]
        if seen > rank:
            return float(value)
    raise AssertionError("histogram rank was not resolved")


def _longest_tense_streak(daily: Iterable[Mapping[str, Any]]) -> int:
    longest = current = 0
    previous: Date | None = None
    for row in sorted(daily, key=lambda item: str(item.get("date") or "")):
        current_date = Date.fromisoformat(str(row["date"]))
        contiguous = previous is not None and current_date == previous + timedelta(days=1)
        is_tense = (
            str(row.get("day_tone") or "") == "tense"
            if "day_tone" in row
            else bool(row.get("tense"))
        )
        if is_tense:
            current = current + 1 if contiguous else 1
            longest = max(longest, current)
        else:
            current = 0
        previous = current_date
    return longest


def _new_mode_accumulator() -> dict[str, Any]:
    return {
        "charts": 0,
        "days": 0,
        "state_distribution": Counter(),
        "diagnostic_state_distribution": Counter(),
        "hero_days": 0,
        "hero_rates": [],
        "significant_histogram": Counter(),
        "independent_histogram": Counter(),
        "group_histogram": Counter(),
        "public_histogram": Counter(),
        "selected_public_histogram": Counter(),
        "excluded_reasons": Counter(),
        "tense_days": 0,
        "day_tones": Counter(),
        "legacy_tense_days": 0,
        "tone_triggers": 0,
        "tense_streaks": [],
        "hero_sphere_span_gt2_days": 0,
        "zero_public_days": 0,
        "zero_selected_public_days": 0,
        "raw_activations": 0,
        "raw_ledger": 0,
        "invalid_ledger": 0,
        "duplicate_ledger": 0,
        "timing_deferred": 0,
    }
# END_BLOCK: STATISTICS


# START_BLOCK: AGGREGATION
def aggregate_shards(
    inputs: Sequence[Path],
    *,
    expected_charts: int | None = None,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-CORPUS-SHARD-AGGREGATOR.aggregate_shards
    # purpose: Stream compatible replay checkpoints into one audit summary.
    # inputs: checkpoint paths/directories and optional expected chart count.
    # returns: JSON-safe combined metrics and invariant statuses.
    # side_effects: reads checkpoint files only.
    # emitted_logs: none.
    # error_behavior: raises ValueError for duplicates, drift, errors, or count mismatch.
    # END_FUNCTION_CONTRACT: F-M-CORPUS-SHARD-AGGREGATOR.aggregate_shards
    paths = _checkpoint_paths(inputs)
    chart_ids: set[str] = set()
    fingerprints: set[str] = set()
    date_ranges: set[tuple[str, str]] = set()
    modes: dict[str, dict[str, Any]] = {}
    elapsed: list[float] = []
    failures: list[dict[str, Any]] = []
    checkpoint_hashes: list[tuple[str, str]] = []

    for path in paths:
        checkpoint, checkpoint_hash = _load_checkpoint(path)
        chart_id = str(checkpoint.get("chart", {}).get("chart_id") or "")
        if not chart_id:
            raise ValueError(f"checkpoint has no chart_id: {path}")
        if chart_id in chart_ids:
            raise ValueError(f"duplicate chart_id across shards: {chart_id}")
        chart_ids.add(chart_id)
        checkpoint_hashes.append((chart_id, checkpoint_hash))
        if checkpoint.get("status") != "ok":
            failures.append({"chart_id": chart_id, "errors": checkpoint.get("errors", [])})
            continue

        fingerprint = str(checkpoint.get("source_fingerprint_sha256") or "")
        if not fingerprint:
            raise ValueError(f"checkpoint has no source fingerprint: {chart_id}")
        fingerprints.add(fingerprint)
        raw_range = checkpoint.get("date_range") or ()
        if len(raw_range) != 2:
            raise ValueError(f"checkpoint has invalid date range: {chart_id}")
        date_ranges.add((str(raw_range[0]), str(raw_range[1])))
        elapsed.append(float(checkpoint.get("elapsed_s", 0.0)))

        for mode, row in checkpoint.get("modes", {}).items():
            accumulator = modes.setdefault(str(mode), _new_mode_accumulator())
            daily = list(row.get("daily", []))
            accumulator["charts"] += 1
            accumulator["days"] += int(row.get("n_days", len(daily)))
            accumulator["state_distribution"].update(row.get("state_distribution", {}))
            accumulator["diagnostic_state_distribution"].update(
                row.get("diagnostic_state_distribution", {})
            )
            hero_days = int(row.get("hero_days_n", 0))
            n_days = int(row.get("n_days", len(daily)))
            accumulator["hero_days"] += hero_days
            accumulator["hero_rates"].append(hero_days / n_days if n_days else 0.0)
            accumulator["excluded_reasons"].update(row.get("excluded_reasons", {}))
            accumulator["tense_days"] += int(row.get("tense_days", 0))
            accumulator["day_tones"].update(row.get("day_tone_distribution", {}))
            accumulator["legacy_tense_days"] += int(
                row.get("legacy_tense_days", row.get("tense_days", 0))
            )
            accumulator["tone_triggers"] += int(row.get("tone_triggers", 0))
            accumulator["tense_streaks"].append(_longest_tense_streak(daily))
            accumulator["zero_public_days"] += int(row.get("zero_public_days", 0))
            for key in (
                "raw_activations",
                "raw_ledger",
                "invalid_ledger",
                "duplicate_ledger",
                "timing_deferred",
            ):
                accumulator[key] += int(row.get(key, 0))

            for day in daily:
                state = str(day.get("state") or "")
                if state not in PUBLIC_STATES:
                    raise ValueError(f"unknown public state {state!r}: {chart_id}/{mode}")
                accumulator["significant_histogram"][int(day.get("n_significant", 0))] += 1
                accumulator["independent_histogram"][int(day.get("n_independent_units", 0))] += 1
                accumulator["group_histogram"][int(day.get("n_groups", 0))] += 1
                accumulator["public_histogram"][int(day.get("n_public", 0))] += 1
                selected = int(day.get("n_selected_public_units", 0))
                accumulator["selected_public_histogram"][selected] += 1
                accumulator["zero_selected_public_days"] += int(selected == 0)
                accumulator["hero_sphere_span_gt2_days"] += int(
                    state == "convergence_today" and len(day.get("hero_spheres", ())) > 2
                )

    if failures:
        raise ValueError(f"{len(failures)} replay checkpoints failed: {failures[:3]}")
    if len(fingerprints) != 1:
        raise ValueError(f"source fingerprint drift across shards: {sorted(fingerprints)}")
    if len(date_ranges) != 1:
        raise ValueError(f"date range drift across shards: {sorted(date_ranges)}")
    if expected_charts is not None and len(chart_ids) != expected_charts:
        raise ValueError(f"expected {expected_charts} charts, found {len(chart_ids)}")

    mode_results: dict[str, Any] = {}
    for mode, accumulator in sorted(modes.items()):
        days = accumulator["days"]
        hero_rates = accumulator["hero_rates"]
        streaks = accumulator["tense_streaks"]
        mode_results[mode] = {
            "charts": accumulator["charts"],
            "days": days,
            "state_distribution": dict(accumulator["state_distribution"]),
            "diagnostic_state_distribution": dict(
                accumulator["diagnostic_state_distribution"]
            ),
            "hero_days": accumulator["hero_days"],
            "hero_rate": round(accumulator["hero_days"] / days, 6) if days else None,
            "chart_hero_rate_median": round(statistics.median(hero_rates), 6),
            "chart_hero_rate_min": round(min(hero_rates), 6),
            "chart_hero_rate_max": round(max(hero_rates), 6),
            "significant_median": _histogram_quantile(
                accumulator["significant_histogram"], 0.5
            ),
            "independent_units_median": _histogram_quantile(
                accumulator["independent_histogram"], 0.5
            ),
            "groups_median": _histogram_quantile(accumulator["group_histogram"], 0.5),
            "public_units_median": _histogram_quantile(
                accumulator["public_histogram"], 0.5
            ),
            "selected_public_units_median": _histogram_quantile(
                accumulator["selected_public_histogram"], 0.5
            ),
            "zero_public_days": accumulator["zero_public_days"],
            "zero_selected_public_days": accumulator["zero_selected_public_days"],
            "tense_days": accumulator["tense_days"],
            "tense_rate": round(accumulator["tense_days"] / days, 6) if days else None,
            "day_tone_distribution": dict(accumulator["day_tones"]),
            "legacy_tense_days": accumulator["legacy_tense_days"],
            "legacy_tense_rate": round(accumulator["legacy_tense_days"] / days, 6) if days else None,
            "tone_triggers": accumulator["tone_triggers"],
            "tense_streak_chart_median": statistics.median(streaks) if streaks else None,
            "tense_streak_chart_p95": (
                _histogram_quantile(Counter(streaks), 0.95) if streaks else None
            ),
            "tense_streak_max": max(streaks) if streaks else None,
            "hero_sphere_span_gt2_days": accumulator["hero_sphere_span_gt2_days"],
            "excluded_reasons": dict(accumulator["excluded_reasons"]),
            "raw_activations": accumulator["raw_activations"],
            "raw_ledger": accumulator["raw_ledger"],
            "invalid_ledger": accumulator["invalid_ledger"],
            "duplicate_ledger": accumulator["duplicate_ledger"],
            "timing_deferred": accumulator["timing_deferred"],
        }

    checkpoint_set_digest = hashlib.sha256()
    for chart_id, checkpoint_hash in sorted(checkpoint_hashes):
        checkpoint_set_digest.update(chart_id.encode("utf-8"))
        checkpoint_set_digest.update(b"\0")
        checkpoint_set_digest.update(checkpoint_hash.encode("ascii"))
        checkpoint_set_digest.update(b"\0")

    return {
        "schema_version": "today-convergence-corpus-combined.v2",
        "source_fingerprint_sha256": next(iter(fingerprints)),
        "checkpoint_set_sha256": checkpoint_set_digest.hexdigest(),
        "date_range": list(next(iter(date_ranges))),
        "charts": len(chart_ids),
        "checkpoint_files": len(paths),
        "chart_ids": sorted(chart_ids),
        "latency": {
            "chart_elapsed_s_median": round(statistics.median(elapsed), 3),
            "chart_elapsed_s_p95": _histogram_quantile(
                Counter(round(value) for value in elapsed), 0.95
            ),
            "chart_elapsed_s_max": round(max(elapsed), 3),
            "sum_chart_cpu_s": round(sum(elapsed), 3),
        },
        "invariants": {
            "all_checkpoints_ok": True,
            "unique_chart_ids": True,
            "single_source_fingerprint": True,
            "single_date_range": True,
            "expected_chart_count": expected_charts is None or len(chart_ids) == expected_charts,
        },
        "modes": mode_results,
        "interpretation_policy": (
            "Observed frequencies are monitoring diagnostics, not quotas or acceptance gates."
        ),
    }
# END_BLOCK: AGGREGATION


# START_BLOCK: OUTPUT
def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_reports(payload: Mapping[str, Any], *, json_path: Path, markdown_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-CORPUS-SHARD-AGGREGATOR.write_reports
    # purpose: Persist one combined replay result in machine/human-readable forms.
    # inputs: aggregate payload and destination JSON/Markdown paths.
    # returns: None.
    # side_effects: atomic local file writes.
    # emitted_logs: none.
    # error_behavior: propagates filesystem failures; never leaves partial target files.
    # END_FUNCTION_CONTRACT: F-M-CORPUS-SHARD-AGGREGATOR.write_reports
    _atomic_write(
        json_path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    lines = [
        "# Today convergence — combined corpus replay",
        "",
        f"- charts: {payload['charts']}",
        f"- date range: {payload['date_range'][0]} .. {payload['date_range'][1]}",
        f"- source fingerprint: `{payload['source_fingerprint_sha256']}`",
        f"- checkpoint set checksum: `{payload['checkpoint_set_sha256']}`",
        f"- median chart latency: {payload['latency']['chart_elapsed_s_median']} s",
        "",
        "| mode | days | hero | hero rate | day tone | legacy tense | tone tense | significant p50 | independent p50 | max tone streak |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for mode, row in payload["modes"].items():
        lines.append(
            f"| {mode} | {row['days']} | {row['hero_days']} | {row['hero_rate']} | "
            f"{row.get('day_tone_distribution', {})} | {row.get('legacy_tense_rate')} | "
            f"{row['tense_rate']} | {row['significant_median']} | "
            f"{row['independent_units_median']} | {row['tense_streak_max']} |"
        )
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- invariants: `{json.dumps(payload['invariants'], sort_keys=True)}`",
            "- frequencies above are monitoring diagnostics, not a quota or acceptance gate.",
            "- `hero_sphere_span_gt2_days` is a diagnostic span across all hero groups on a day; it is not by itself proof of per-group fan-out.",
        ]
    )
    _atomic_write(markdown_path, "\n".join(lines) + "\n")
# END_BLOCK: OUTPUT


# START_BLOCK: CLI
def main(argv: Sequence[str] | None = None) -> int:
    # START_FUNCTION_CONTRACT: F-M-CORPUS-SHARD-AGGREGATOR.main
    # purpose: Parse CLI inputs, aggregate shards, and write both report formats.
    # inputs: optional argv sequence.
    # returns: process exit code 0 on a fully validated report.
    # side_effects: checkpoint reads and report writes.
    # emitted_logs: none.
    # error_behavior: argparse/ValueError terminates non-zero before success output.
    # END_FUNCTION_CONTRACT: F-M-CORPUS-SHARD-AGGREGATOR.main
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--expected-charts", type=int, default=None)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = aggregate_shards(args.inputs, expected_charts=args.expected_charts)
    write_reports(payload, json_path=args.json_output, markdown_path=args.markdown_output)
    print(
        json.dumps(
            {
                "charts": payload["charts"],
                "fingerprint": payload["source_fingerprint_sha256"],
                "json": str(args.json_output.resolve()),
                "markdown": str(args.markdown_output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK: CLI
