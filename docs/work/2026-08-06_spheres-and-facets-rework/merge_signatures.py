#!/usr/bin/env python3
"""Streaming merge of replay checkpoints into physical_signatures.jsonl + gate counters.

The stock corpus_replay merge loads all 120 checkpoints (~25 MB each) into memory
and gets OOM-killed on this 7 GB host. This merger processes one checkpoint at a
time: chart-major sort order means per-chart in-memory sort yields a globally
sorted JSONL without holding the corpus.

Usage: python3 docs/work/2026-08-06_spheres-and-facets-rework/merge_signatures.py <run-dir>
Writes <run-dir>/physical_signatures.jsonl and prints gate counters as JSON.
"""
import json
import sys
from pathlib import Path

GATE_MODE_COUNTERS = (
    "group_without_sphere_count",
    "old_key_occurrences",
    "legacy_key_occurrences",
    "invalid_facet_count",
    "selected_invalid_facet_count",
    "unmapped_count",
    "facet_null_count",
    "selected_facet_null_count",
)


def main() -> None:
    run_dir = Path(sys.argv[1])
    ck_dir = run_dir / "checkpoints"
    out_path = run_dir / "physical_signatures.jsonl"
    chart_paths = sorted(ck_dir.glob("*.json"))

    total_rows = 0
    charts_ok = 0
    charts_error = 0
    error_charts: list[str] = []
    gate_totals = {name: 0 for name in GATE_MODE_COUNTERS}
    status_by_chart: dict[str, str] = {}

    with out_path.open("w", encoding="utf-8") as out:
        for path in chart_paths:
            chart = json.loads(path.read_text(encoding="utf-8"))
            chart_id = str(chart.get("chart", {}).get("chart_id") or path.stem)
            status = str(chart.get("status") or "")
            status_by_chart[chart_id] = status
            if status != "ok":
                charts_error += 1
                error_charts.append(chart_id)
                continue
            charts_ok += 1
            rows: list[dict] = []
            for mode, mode_result in (chart.get("modes") or {}).items():
                for name in GATE_MODE_COUNTERS:
                    value = mode_result.get(name)
                    if isinstance(value, dict):
                        gate_totals[name] += sum(int(v) for v in value.values())
                    else:
                        gate_totals[name] += int(value or 0)
                for raw in mode_result.get("physical_signatures") or ():
                    signature = dict(raw)
                    signature["chart_id"] = signature.get("chart_id") or chart_id
                    signature["birth_mode"] = signature.get("birth_mode") or mode
                    signature["mode"] = signature.get("mode") or mode
                    signature["target_date"] = signature.get("target_date") or signature.get("date")
                    rows.append(signature)
            rows.sort(key=lambda r: (str(r.get("birth_mode") or ""), str(r.get("target_date") or "")))
            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            total_rows += len(rows)

    print(json.dumps({
        "rows": total_rows,
        "charts_ok": charts_ok,
        "charts_error": charts_error,
        "error_charts": error_charts,
        "gate_totals": gate_totals,
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
