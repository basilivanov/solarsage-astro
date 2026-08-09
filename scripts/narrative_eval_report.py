#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: NARRATIVE_EVAL_REPORT — compact HTML report for narrative model eval
# ROLE: Render immutable compact metrics, arm comparison, budget, and next-step
#       recommendations without reading raw responses or making network calls.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-EVAL-REPORT
# purpose: Build a self-contained HTML report from narrative-model-eval metrics,
#   including measured reasoning-token splits and a 3000-call monthly projection.
# owns:
#   - scripts/narrative_eval_report.py
# inputs: evals/results/<run-id>/metrics.json and optional manifest.json.
# outputs: one escaped, self-contained report.html.
# dependencies: Python standard library only.
# side_effects: reads compact artifacts and writes one HTML file; no network,
#   provider calls, raw response reads, or database access.
# emitted_logs: one safe output path line.
# invariants: no raw narrative or credentials enter the report; model/arm rows
#   remain comparable and recommendation rules are deterministic.
# failure_policy: missing or malformed compact metrics exits non-zero.
# END_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-EVAL-REPORT

# START_MODULE_MAP: M-SCRIPTS-NARRATIVE-EVAL-REPORT
# public_entrypoints:
#   - main
# semantic_blocks:
#   - LOAD: compact metric and manifest loading.
#   - RECOMMEND: cheapest-qualified and strict-schema verdicts.
#   - HTML: escaped self-contained report assembly.
#   - CLI: --run/--out entry point.
# owned_tests: narrative_model_eval --selftest and validate gates.
# END_MODULE_MAP: M-SCRIPTS-NARRATIVE-EVAL-REPORT

from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import statistics
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReportError(ValueError):
    """Invalid compact narrative eval artifact."""


def _fail(message: str) -> None:
    raise ReportError(message)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReportError(f"missing artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        _fail(f"artifact root must be an object: {path}")
    return value


def _resolve_run(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    path = path.resolve()
    try:
        path.relative_to(REPO_ROOT / "evals" / "results")
    except ValueError as exc:
        raise ReportError("run must live under evals/results") from exc
    return path


# START_BLOCK: RECOMMEND
def _recommendations(rows: list[dict[str, Any]]) -> tuple[str, str]:
    arm_a = {row["model_key"]: row for row in rows if row.get("arm") == "json_object"}
    arm_b = {row["model_key"]: row for row in rows if row.get("arm") == "strict_json_schema"}
    baseline = arm_a.get("baseline-nano")
    if baseline is None:
        return "baseline nano отсутствует", "нет baseline для strict-сравнения"
    baseline_metrics = baseline.get("metrics", {})
    qualified = [
        row
        for row in arm_a.values()
        if float(row.get("metrics", {}).get("auto_score", 0)) >= float(baseline_metrics.get("auto_score", 0))
        and float(row.get("metrics", {}).get("sanitizer_pass", 0)) >= float(baseline_metrics.get("sanitizer_pass", 0))
    ]
    if qualified:
        winner = min(qualified, key=lambda row: float(row.get("cost_per_1k_narratives_usd", float("inf"))))
        production = f"рекомендация: {winner.get('label', winner['model_key'])} — самая дешёвая модель выше порога baseline"
    else:
        production = "рекомендация: ни одна модель не превысила baseline nano по обоим порогам"
    strict_candidates = []
    for key, row_a in arm_a.items():
        row_b = arm_b.get(key)
        if row_b is None:
            continue
        metrics_a = row_a.get("metrics", {})
        metrics_b = row_b.get("metrics", {})
        support = float(metrics_b.get("strict_support", 0))
        valid = float(metrics_b.get("json_valid", 0))
        valid_a = float(metrics_a.get("json_valid", 0))
        score = float(metrics_b.get("auto_score", 0))
        score_a = float(metrics_a.get("auto_score", 0))
        if support >= 0.8 and valid >= valid_a - 0.05 and score >= score_a - 5.0:
            strict_candidates.append(row_b)
    if strict_candidates:
        strict = min(strict_candidates, key=lambda row: float(row.get("cost_per_1k_narratives_usd", float("inf"))))
        strict_text = f"strict json_schema: мигрировать да, кандидат {strict.get('label', strict['model_key'])}"
    else:
        strict_text = "strict json_schema: миграция пока нет — support/validity/quality деградируют или не подтверждены"
    return production, strict_text


# END_BLOCK: RECOMMEND


# START_BLOCK: HTML
def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return escape(str(value))


def _metric_cell(row: dict[str, Any], name: str) -> str:
    return _fmt(row.get("metrics", {}).get(name), 3)


def _human_scores(review: dict[str, Any] | None) -> dict[str, float]:
    if not isinstance(review, dict):
        return {}
    source = review.get("models") or review.get("scores")
    entries: list[dict[str, Any]] = []
    if isinstance(source, dict):
        entries = [{"model_key": key, **value} for key, value in source.items() if isinstance(value, dict)]
    elif isinstance(review.get("candidates"), list):
        entries = [value for value in review["candidates"] if isinstance(value, dict)]
    output: dict[str, float] = {}
    for entry in entries:
        model_key = entry.get("model_key", entry.get("modelKey"))
        if not isinstance(model_key, str):
            continue
        values = [entry.get(name) for name in ("beauty", "accuracy")]
        numeric = [float(value) for value in values if isinstance(value, (int, float)) and 1 <= value <= 5]
        if not numeric and isinstance(entry.get("human_score"), (int, float)):
            value = float(entry["human_score"])
            if 1 <= value <= 5:
                numeric = [value]
        if numeric:
            output[model_key] = round(statistics.mean(numeric), 3)
    return output


def _monthly_projection_table(rows: list[dict[str, Any]]) -> tuple[str, str]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REPORT._monthly_projection_table
    # purpose: Render measured token/cost averages and the 3000-call monthly projection for each model arm.
    # inputs: compact model/arm rows from metrics.json.
    # returns: escaped header HTML and row HTML for the monthly projection table.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: missing optional reasoning details render as an em dash.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REPORT._monthly_projection_table
    headers = (
        "Модель",
        "Плечо",
        "Mean prompt tokens",
        "Mean completion tokens",
        "Mean reasoning tokens",
        "Mean visible tokens",
        "Mean $ / call",
        "$ / month (3000)",
        "p50/p95, сек",
    )
    rows_html: list[str] = []
    for row in rows:
        usage = row.get("usage", {}) if isinstance(row.get("usage"), dict) else {}
        latency = row.get("latency_ms", {}) if isinstance(row.get("latency_ms"), dict) else {}
        rows_html.append(
            "<tr>"
            + f"<td>{escape(str(row.get('label', row.get('model_key', '—'))))}</td>"
            + f"<td><code>{escape(str(row.get('arm', '—')))}</code></td>"
            + f"<td>{_fmt(usage.get('mean_prompt_tokens'), 2)}</td>"
            + f"<td>{_fmt(usage.get('mean_completion_tokens'), 2)}</td>"
            + f"<td>{_fmt(usage.get('mean_reasoning_tokens'), 2)}</td>"
            + f"<td>{_fmt(usage.get('mean_visible_completion_tokens'), 2)}</td>"
            + f"<td>{_fmt(row.get('mean_cost_per_call_usd'), 6)}</td>"
            + f"<td>{_fmt(row.get('monthly_3000_estimate_usd'), 2)}</td>"
            + f"<td>{_fmt((latency.get('p50') or 0) / 1000, 1)} / {_fmt((latency.get('p95') or 0) / 1000, 1)}</td>"
            + "</tr>"
        )
    return "".join(f"<th>{escape(header)}</th>" for header in headers), "".join(rows_html)


def build_report(
    metrics: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REPORT.build_report
    # purpose: Render compact model/arm metrics, measured monthly projection, and deterministic recommendations into standalone HTML.
    # inputs: validated compact metrics, optional safe run manifest, and optional safe human review.
    # returns: complete HTML document.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed arm rows raise ReportError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REPORT.build_report
    rows = metrics.get("arms")
    if not isinstance(rows, list) or not rows:
        _fail("metrics.arms must be a non-empty list")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("model_key"), str) or row.get("arm") not in {"json_object", "strict_json_schema"}:
            _fail("invalid model/arm row")
    production, strict = _recommendations(rows)
    human_scores = _human_scores(review)
    coverage = metrics.get("coverage", {})
    title = "Today narrative v5 — model eval"
    subtitle = f"{escape(str(metrics.get('task_id', 'narrative-model-eval-v1')))} · run {escape(str(metrics.get('run_id', 'unknown')))}"
    headers = (
        "Модель",
        "Плечо",
        "Вызовы",
        "Human",
        "Strict",
        "JSON",
        "Truncated",
        "Fill",
        "Binding",
        "Sanitizer",
        "Length",
        "Lexicon",
        "Stamps (hits/clean)",
        "Datetime (hits/clean)",
        "Name",
        "Repeat",
        "Auto score",
        "p50/p95, сек",
        "$ / 1k",
        "$ / мес (3000)",
    )
    table_rows: list[str] = []
    for row in rows:
        latency = row.get("latency_ms", {})
        table_rows.append(
            "<tr>"
            + f"<td>{escape(str(row.get('label', row['model_key'])))}</td>"
            + f"<td><code>{escape(str(row['arm']))}</code></td>"
            + f"<td>{_fmt(row.get('calls'), 0)}</td>"
            + f"<td>{_fmt(human_scores.get(str(row['model_key'])), 3)}</td>"
            + f"<td>{_metric_cell(row, 'strict_support')}</td>"
            + f"<td>{_metric_cell(row, 'json_valid')}</td>"
            + f"<td>{_metric_cell(row, 'truncated_rate')}</td>"
            + f"<td>{_metric_cell(row, 'fill_rate')}</td>"
            + f"<td>{_metric_cell(row, 'claim_binding')}</td>"
            + f"<td>{_metric_cell(row, 'sanitizer_pass')}</td>"
            + f"<td>{_metric_cell(row, 'length_ok')}</td>"
            + f"<td>{_metric_cell(row, 'lexicon_cover')}</td>"
            + f"<td>{_fmt(row.get('stamp_hits'), 0)} / {_metric_cell(row, 'stamp_clean')}</td>"
            + f"<td>{_fmt(row.get('datetime_leak'), 0)} / {_metric_cell(row, 'datetime_clean')}</td>"
            + f"<td>{_metric_cell(row, 'name_rule')}</td>"
            + f"<td>{_fmt(row.get('repeatability'), 3)}</td>"
            + f"<td>{_metric_cell(row, 'auto_score')}</td>"
            + f"<td>{_fmt((latency.get('p50') or 0) / 1000, 1)} / {_fmt((latency.get('p95') or 0) / 1000, 1)}</td>"
            + f"<td>{_fmt(row.get('cost_per_1k_narratives_usd'), 4)}</td>"
            + f"<td>{_fmt(row.get('monthly_3000_estimate_usd'), 2)}</td>"
            + "</tr>"
        )
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    coverage_html = escape(json.dumps(coverage, ensure_ascii=False, sort_keys=True))
    spent = escape(str(metrics.get("spent_usd", "—")))
    call_count = escape(str(metrics.get("call_count", "—")))
    monthly_header_html, monthly_rows_html = _monthly_projection_table(rows)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ margin: 0; background: #f5f1e9; color: #24221e; font: 15px/1.5 system-ui, sans-serif; }}
main {{ max-width: 1500px; margin: 0 auto; padding: 32px; }}
h1 {{ margin-bottom: 4px; }} .muted {{ color: #706a61; }}
.callout {{ background: #fff; border-left: 5px solid #6850b7; padding: 16px 20px; margin: 20px 0; }}
.callout.strict {{ border-color: #26765c; }}
.table-wrap {{ overflow-x: auto; background: #fff; }}
table {{ border-collapse: collapse; min-width: 1200px; width: 100%; }}
th, td {{ border-bottom: 1px solid #e5dfd5; padding: 9px 10px; text-align: right; white-space: nowrap; }}
th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
th {{ background: #eee8de; position: sticky; top: 0; }}
code {{ font-size: 12px; }} .meta {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px; }}
.meta div {{ background: #fff; padding: 12px 16px; }}
</style>
</head>
<body><main>
<h1>{title}</h1><div class="muted">{subtitle}</div>
<div class="callout"><strong>{escape(production)}</strong></div>
<div class="callout strict"><strong>{escape(strict)}</strong></div>
<div class="meta">
<div><strong>Вызовы:</strong> {call_count}</div>
<div><strong>Фактическая стоимость:</strong> ${spent}</div>
<div><strong>Coverage:</strong> <code>{coverage_html}</code></div>
</div>
<h2>Модели × плечи</h2>
<div class="table-wrap"><table><thead><tr>{header_html}</tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<h2>Месячная проекция стоимости</h2>
<p>Допущения: 100 DAU; каждый пользователь ежедневно открывает день; 1 narrative-генерация на пользователь-день; итого <strong>3000 вызовов в месяц</strong>. Цены взяты из immutable pricing TOML, as_of 2026-08-09. Токены и стоимость на вызов — измеренные средние по прогону, не оценка.</p>
<p>Day-pregen выполняется офлайн-батчем в 04:07, поэтому latency до ~60 секунд приемлема. Интерактивный on-demand путь используется только при cache-miss и относится к minority-трафику.</p>
<div class="table-wrap"><table><thead><tr>{monthly_header_html}</tr></thead><tbody>{monthly_rows_html}</tbody></table></div>
<h2>Следующие шаги</h2>
<ol>
<li>Для выбранной модели отдельно проверить миграцию на <code>json_schema</code> с array-шаблоном.</li>
<li>После выбора модели сравнить system/user split на том же immutable inputs.json.</li>
<li>Зафиксировать fallback-модель и повторить проверку бюджета перед production rollout.</li>
</ol>
</main></body></html>"""


# END_BLOCK: HTML


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Today narrative model evaluation HTML")
    parser.add_argument("--run", required=True, help="evals/results/<run-id>")
    parser.add_argument("--out", default=None, help="output HTML path; defaults to <run>/report.html")
    args = parser.parse_args(argv)
    try:
        run_dir = _resolve_run(args.run)
        metrics = _load_json(run_dir / "metrics.json")
        manifest_path = run_dir / "manifest.json"
        manifest = _load_json(manifest_path) if manifest_path.exists() else None
        review_path = run_dir / "review.json"
        review = _load_json(review_path) if review_path.exists() else None
        output = Path(args.out) if args.out else run_dir / "report.html"
        if not output.is_absolute():
            output = REPO_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_report(metrics, manifest, review), encoding="utf-8")
        print(f"narrative_eval_report: PASS {output.relative_to(REPO_ROOT)}")
        return 0
    except ReportError as exc:
        print(f"narrative_eval_report: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
