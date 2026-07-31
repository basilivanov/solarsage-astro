#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: MODULE_AGENT_EVAL_SUMMARY — aggregate HTML report across eval tasks
# ROLE: Merge several agent-eval run directories (metrics.json + review.json
#       each) into one self-contained Russian HTML summary: task x model
#       matrix, aggregated radar, per-model totals, verdict and findings.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-AGENT-EVAL-SUMMARY
# purpose: Generate a self-contained HTML summary report over multiple
#   agent-eval tasks (see scripts/agent_eval_report.py for per-task reports).
# owns:
#   - scripts/agent_eval_summary.py
# inputs: --runs <dir...> (each with metrics.json + review.json),
#   --review summary JSON (optional; schema in module docstring), --out path.
# outputs: one self-contained HTML file (RU, inline CSS/SVG, no external assets)
#   and a one-line stdout summary.
# dependencies: Python 3 stdlib only; imports sibling scripts/agent_eval_report.py
#   for candidate loading, axis scoring, radar SVG and the shared CSS base.
# side_effects: reads run/review files, writes --out (creating parent dirs);
#   no network, no git, no model invocation.
# emitted_logs: none.
# invariants:
#   - models are matched across tasks by modelKey; a model missing from a task
#     renders as "-" in the matrix and is aggregated over its present tasks;
#   - speed/price radar axes: per-task normalized (best=100) values averaged
#     per model (speed rounded to 0.1, price to 0.01, as in per-task reports);
#   - matrix cell color: green >= 90, yellow 70-89, red < 70 or statusOk=false;
#   - candidates with metrics.json "rerunNote" get a numbered footnote marker;
#   - at most 4 distinct models (shared palette bound);
#   - all review strings are HTML-escaped except footerNotes (trusted HTML,
#     "**bold**" markdown converted to <strong>).
# failure_policy: missing or invalid input -> message on stderr, non-zero exit;
#   a missing --review file is NOT an error (verdict/findings sections skipped).
# END_MODULE_CONTRACT: M-SCRIPTS-AGENT-EVAL-SUMMARY

# START_MODULE_MAP: M-SCRIPTS-AGENT-EVAL-SUMMARY
# public_entrypoints:
#   - main
# semantic_blocks:
#   - LOAD: read run directories and the optional summary review.
#   - MODEL: per-model aggregates across tasks (means, totals, footnotes).
#   - MATRIX: task x model matrix with color-coded cells and averages.
#   - HTML: page assembly reusing the per-task visual language.
#   - CLI: argparse entry point.
# owned_tests: none (validated via golden-run regeneration)
# END_MODULE_MAP: M-SCRIPTS-AGENT-EVAL-SUMMARY

"""
agent_eval_summary.py — generate a self-contained HTML summary over several
local coding-agent eval runs (per-task reports: scripts/agent_eval_report.py).

Usage:
    python3 scripts/agent_eval_summary.py \\
        --runs evals/results/<run-1> evals/results/<run-2> [...] \\
        --review evals/results/summary-review.json \\
        --out evals/results/summary.html

Each run directory must contain metrics.json and review.json (the per-task
review schema from agent_eval_report.py). --review is optional; without it the
verdict/findings sections are skipped (not an error).

Summary review JSON schema (example: evals/results/summary-review.json):

    {
      "title": "…",                    # optional; default "SolarSage Agent Eval — итоги набора задач"
      "subtitle": "lede under the H1", # optional
      "dateLabel": "31 июля 2026",     # optional; default: per-task dateLabels joined
      "candidates": [                  # optional display order + per-model summary verdicts
        {                              #   (mirrors the per-task review shape;
          "modelKey": "luna-max",      #    review.models [{modelKey, label}] is a minimal alias)
          "label": "Luna max",         # optional display-name override
          "runnerLabel": "Codex · max effort",  # optional pill override
          "status": "Рекомендован: основной кодер",  # optional, shown in the totals table
          "statusOk": true,            # optional, green/red status dot
          "note": "…"                  # optional, shown under the model name
        }
      ],
      "verdict": {                     # optional; whole verdict panel skipped when absent
        "winnerModelKey": "luna-max",  # required if verdict present, must exist in runs
        "headline": "…",               # required if verdict present
        "text": "…",                   # required if verdict present
        "scoreLabel": "Luna · средний score",   # optional; default "<label> · средний score"
        "scoreCaption": "среднее по 2 задачам · Σ $0.133 за запуски"
                                                 # optional; default computed
      },
      "findings": [                    # optional
        {"title": "…", "text": "…", "modelKey": "luna-max"},  # modelKey may be null
        {"title": "…", "text": "…", "modelKey": null}
      ],
      "findingsTitle": "…",            # optional; default from count
      "footerNotes": [                 # optional, TRUSTED HTML — not escaped;
        "<strong>Метод:</strong> …"    #   "**bold**" markdown is converted to <strong>
      ]
    }

Aggregates per model (over tasks where the model is present): mean completion,
mean accuracy, mean blind, mean acceptance %, mean per-task speed/price scores,
total gates, count of statusOk=false cells, total wall time, total normalized
cost and cost per mean completion point (total cost / mean completion).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from html import escape as esc
from pathlib import Path
import sys
from typing import Any, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import agent_eval_report as per  # noqa: E402  (sibling script, shared code)


DEFAULT_TITLE = "SolarSage Agent Eval — итоги набора задач"
DEFAULT_FOOTER_NOTE = (
    "<strong>Метод:</strong> агрегаты считаются по задачам, где модель присутствует; "
    "скорость и цена сначала нормализованы внутри каждой задачи (лучший = 100), затем усреднены."
)


# START_BLOCK: LOAD


@dataclass
class TaskRun:
    # One run directory: task id plus its scored candidates (per-task view).
    dirname: str
    task_id: str
    date_label: str | None
    candidates: list  # list[per.Candidate], already scored


def load_runs(run_dirs: list[Path]) -> list[TaskRun]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.load_runs
    # purpose: Load every run directory (metrics.json + review.json) through the
    #   per-task loader so per-candidate axis scores match per-task reports.
    # inputs: run_dirs — directories, each with metrics.json and review.json.
    # returns: list of TaskRun in CLI order.
    # side_effects: filesystem reads.
    # emitted_logs: none.
    # error_behavior: SystemExit via per.fail on missing/invalid files or
    #   metrics<->review modelKey mismatch inside a task.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.load_runs
    runs: list[TaskRun] = []
    for directory in run_dirs:
        metrics = per.load_json(directory / "metrics.json", "metrics.json")
        review = per.load_json(directory / "review.json", "review.json")
        if not isinstance(metrics, dict) or not isinstance(review, dict):
            per.fail(f"{directory}: metrics.json and review.json must contain JSON objects")
        candidates = per.build_candidates(metrics, review)
        per.compute_scores(candidates)
        task_id = review.get("taskId") if isinstance(review.get("taskId"), str) else directory.name
        date_label = review.get("dateLabel") if isinstance(review.get("dateLabel"), str) else None
        runs.append(TaskRun(directory.name, task_id, date_label, candidates))
    return runs


# END_BLOCK: LOAD


# START_BLOCK: MODEL


@dataclass
class SummaryModel:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.SummaryModel
    # purpose: One model aggregated across tasks: display identity, per-task
    #   cells (task index -> per-task scored Candidate) and computed aggregates.
    # inputs: built by build_models + compute_aggregates.
    # returns: n/a (dataclass).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: n/a.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.SummaryModel
    index: int
    model_key: str
    label: str
    runner_label: str
    color: str
    color_soft: str
    cells: dict = field(default_factory=dict)  # task index -> per.Candidate
    # optional human summary verdict per model (review.candidates entry)
    status: str | None = None
    status_ok: bool | None = None
    note: str | None = None
    mean_completion: float = 0.0
    mean_accuracy: float = 0.0
    mean_blind: float = 0.0
    mean_accept: float = 0.0
    mean_speed: float | None = None
    mean_price: float | None = None
    gates_passed: int = 0
    gates_total: int = 0
    critical_failures: int = 0
    total_wall: float | None = None
    total_cost: float | None = None


def build_models(runs: list[TaskRun], review: dict[str, Any] | None) -> list[SummaryModel]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.build_models
    # purpose: Union models across tasks by modelKey; display order = optional
    #   review.models order first, then first appearance across runs; palette
    #   colors assigned in display order.
    # inputs: runs — loaded tasks; review — optional summary review.
    # returns: list of SummaryModel with cells mapped, aggregates empty.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: SystemExit on > len(per.PALETTE) distinct models or on an
    #   unknown modelKey in review.models.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.build_models
    known_keys = {cand.model_key for run in runs for cand in run.candidates}
    order: list[str] = []
    labels: dict[str, str] = {}
    runner_labels: dict[str, str] = {}
    review_entries: dict[str, dict[str, Any]] = {}

    # review.candidates is the preferred display-order/label/status source
    # (mirrors the per-task review shape); review.models is a minimal alias.
    entries = (review or {}).get("candidates") or (review or {}).get("models") or []
    if entries:
        if not isinstance(entries, list):
            per.fail("review.candidates/models must be a list of objects")
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                per.fail(f"review.candidates[{i}] must be an object")
            key = per.req_str(entry, "modelKey", f"review.candidates[{i}]")
            if key not in known_keys:
                per.fail(f"review.candidates[{i}].modelKey '{key}' is not present in any run")
            if key not in order:
                order.append(key)
            review_entries[key] = entry
            label = entry.get("label")
            if isinstance(label, str) and label.strip():
                labels[key] = label
            runner_label = entry.get("runnerLabel")
            if isinstance(runner_label, str) and runner_label.strip():
                runner_labels[key] = runner_label
            status_ok = entry.get("statusOk")
            if status_ok is not None and not isinstance(status_ok, bool):
                per.fail(f"review.candidates[{i}].statusOk must be a boolean")

    for run in runs:
        for cand in run.candidates:
            if cand.model_key not in order:
                order.append(cand.model_key)
            labels.setdefault(cand.model_key, cand.label)
            runner_labels.setdefault(cand.model_key, cand.runner_label)

    if len(order) > len(per.PALETTE):
        per.fail(f"summary supports at most {len(per.PALETTE)} distinct models, got {len(order)}")

    models: list[SummaryModel] = []
    for index, key in enumerate(order):
        entry = review_entries.get(key) or {}
        status = entry.get("status")
        note = entry.get("note")
        model = SummaryModel(
            index=index,
            model_key=key,
            label=labels.get(key) or key,
            runner_label=runner_labels.get(key) or "",
            color=per.PALETTE[index],
            color_soft=per.hex_to_rgba(per.PALETTE[index], 0.14),
            status=status if isinstance(status, str) and status.strip() else None,
            status_ok=entry.get("statusOk"),
            note=note if isinstance(note, str) and note.strip() else None,
        )
        for task_index, run in enumerate(runs):
            for cand in run.candidates:
                if cand.model_key == key:
                    model.cells[task_index] = cand
        models.append(model)
    return models


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_aggregates(models: list[SummaryModel]) -> None:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.compute_aggregates
    # purpose: Fill per-model aggregates in place over tasks where the model is
    #   present: means (completion/accuracy/blind/acceptance/speed/price), gate
    #   totals, statusOk=false count, total wall time and total normalized cost.
    # inputs: models — from build_models.
    # returns: None (mutates models).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: models without any speed/price data keep mean None (the
    #   axis is then hidden for everyone, as in per-task reports).
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.compute_aggregates
    for model in models:
        cells = list(model.cells.values())
        model.mean_completion = _mean([c.completion for c in cells])
        model.mean_accuracy = _mean([c.accuracy for c in cells])
        model.mean_blind = _mean([c.blind for c in cells])
        model.mean_accept = _mean([c.accept_pct for c in cells])
        speeds = [c.speed_score for c in cells if c.speed_score is not None]
        prices = [c.price_score for c in cells if c.price_score is not None]
        model.mean_speed = round(_mean(speeds), 1) if speeds else None
        model.mean_price = round(_mean(prices), 2) if prices else None
        model.gates_passed = sum(c.gates_passed for c in cells)
        model.gates_total = sum(c.gates_total for c in cells)
        model.critical_failures = sum(1 for c in cells if not c.status_ok)
        walls = [c.wall_seconds for c in cells if c.wall_seconds is not None]
        costs = [c.cost_usd for c in cells if c.cost_usd is not None]
        model.total_wall = sum(walls) if walls else None
        model.total_cost = sum(costs) if costs else None


def build_axes(models: list[SummaryModel]) -> list[tuple[str, list[float]]]:
    # Ordered radar axes over per-model means; optional axes drop out when data is missing.
    axes: list[tuple[str, list[float]]] = [
        ("Приёмка", [m.mean_accept for m in models]),
        ("Выполнение", [m.mean_completion for m in models]),
        ("Точность", [m.mean_accuracy for m in models]),
    ]
    if all(m.mean_speed is not None for m in models):
        axes.append(("Скорость", [m.mean_speed or 0.0 for m in models]))
    if all(m.mean_price is not None for m in models):
        axes.append(("Цена", [m.mean_price or 0.0 for m in models]))
    axes.append(("Blind review", [m.mean_blind for m in models]))
    return axes


def find_winner(models: list[SummaryModel], review: dict[str, Any]) -> SummaryModel:
    verdict = review.get("verdict")
    if not isinstance(verdict, dict):
        per.fail("review.verdict must be an object when present")
    winner_key = per.req_str(verdict, "winnerModelKey", "review.verdict")
    per.req_str(verdict, "headline", "review.verdict")
    per.req_str(verdict, "text", "review.verdict")
    for model in models:
        if model.model_key == winner_key:
            return model
    per.fail(f"review.verdict.winnerModelKey '{winner_key}' is not present in any run")


# END_BLOCK: MODEL


# START_BLOCK: MATRIX


SUMMARY_CSS = """
    .cell { min-width: 118px; }
    .cell-completion { font-size: 18px; }
    .cell-sub { display: block; margin-top: 2px; color: var(--muted); font-size: 12px; }
    .cell--good { background: var(--success-soft); }
    .cell--good .cell-completion { color: var(--success); }
    .cell--mid { background: rgba(168, 121, 31, 0.10); }
    .cell--mid .cell-completion { color: #8a6d1f; }
    .cell--bad { background: rgba(162, 75, 71, 0.10); }
    .cell--bad .cell-completion { color: var(--danger); }
    .cell--empty { color: var(--muted); text-align: center; }
    .mean-cell { background: rgba(63, 47, 68, 0.045); }
    .footnotes { margin: 14px 0 0; padding-left: 18px; color: var(--muted); font-size: 13px; }
    .footnotes li { margin-bottom: 4px; }
    .task-link { font-weight: 700; }
    .model-scope { display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }
    .model-status { margin-top: 6px; font-size: 13px; }
"""


def cell_class(cand: Any) -> str:
    if not cand.status_ok or cand.completion < 70:
        return "cell--bad"
    if cand.completion >= 90:
        return "cell--good"
    return "cell--mid"


def render_matrix(models: list[SummaryModel], runs: list[TaskRun]) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.render_matrix
    # purpose: Render the task x model matrix: rows are tasks (taskId linking to
    #   ./<dirname>/report.html), columns are models; a cell shows completion
    #   (bold) and accuracy (small) with green/yellow/red coloring; missing
    #   combinations render "-"; rerunNote cells get numbered footnotes; adds
    #   "Среднее по задаче" column and "Среднее по модели" row.
    # inputs: models — aggregated models; runs — loaded tasks.
    # returns: HTML markup string for the matrix section.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none (data already validated upstream).
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.render_matrix
    footnotes: list[str] = []
    footnote_ids: dict[tuple[int, str], int] = {}
    for task_index, run in enumerate(runs):
        for cand in run.candidates:
            if cand.rerun_note:
                footnote_ids[(task_index, cand.model_key)] = len(footnotes) + 1
                footnotes.append(f"{run.task_id} · {cand.label}: {cand.rerun_note}")

    header_cells = "".join(f"\n              <th>{esc(m.label)}</th>" for m in models)
    rows: list[str] = []
    for task_index, run in enumerate(runs):
        cells: list[str] = []
        present: list[float] = []
        for model in models:
            cand = model.cells.get(task_index)
            if cand is None:
                cells.append(
                    f'              <td class="cell cell--empty" data-label="{esc(model.label)}">—</td>'
                )
                continue
            present.append(cand.completion)
            sup = ""
            marker = footnote_ids.get((task_index, cand.model_key))
            if marker:
                sup = f"<sup>{marker}</sup>"
            cells.append(
                f'              <td class="cell {cell_class(cand)}" data-label="{esc(model.label)}">'
                f'<strong class="cell-completion">{per.fmt_pct(cand.completion)}</strong>{sup}'
                f'<span class="cell-sub">точность {per.fmt_pct(cand.accuracy)}%</span></td>'
            )
        task_mean = _mean(present)
        rows.append(
            "            <tr>\n"
            f'              <td data-label="Задача"><a class="task-link" href="./{esc(run.dirname, quote=True)}/report.html">'
            f"{esc(run.task_id)}</a></td>\n" + "\n".join(cells) + "\n"
            f'              <td class="mean-cell" data-label="Среднее по задаче"><strong>{per.fmt_pct(task_mean)}</strong></td>\n'
            "            </tr>"
        )

    mean_cells = "".join(
        f'\n              <td class="mean-cell" data-label="{esc(m.label)}"><strong>{per.fmt_pct(m.mean_completion)}</strong></td>'
        for m in models
    )
    grand = _mean([cand.completion for run in runs for cand in run.candidates])
    rows.append(
        "            <tr>\n"
        '              <td data-label="Задача"><strong>Среднее по модели</strong></td>'
        f"{mean_cells}\n"
        f'              <td class="mean-cell" data-label="Среднее по задаче"><strong>{per.fmt_pct(grand)}</strong></td>\n'
        "            </tr>"
    )

    footnotes_html = ""
    if footnotes:
        items = "\n".join(f"          <li>{esc(text)}</li>" for text in footnotes)
        footnotes_html = f'\n      <ol class="footnotes">\n{items}\n      </ol>'

    return f"""    <section class="section" aria-labelledby="matrix-title">
      <p class="eyebrow">Матрица результатов</p>
      <h2 id="matrix-title">Задачи × модели</h2>
      <div class="table-wrap">
        <table class="matrix">
          <thead>
            <tr>
              <th>Задача</th>{header_cells}
              <th>Среднее по задаче</th>
            </tr>
          </thead>
          <tbody>
{chr(10).join(rows)}
          </tbody>
        </table>
      </div>{footnotes_html}
    </section>"""


# END_BLOCK: MATRIX


# START_BLOCK: HTML


def render_totals_table(models: list[SummaryModel], n_tasks: int) -> str:
    rows: list[str] = []
    for m in models:
        scope = (
            f'<span class="model-scope">по {len(m.cells)} из {n_tasks} задачам</span>'
            if len(m.cells) < n_tasks
            else ""
        )
        runner_pill = f'<br><span class="pill">{esc(m.runner_label)}</span>' if m.runner_label else ""
        status_html = ""
        if m.status:
            status_cls = "status--pass" if m.status_ok else "status--fail"
            status_html = f'<div class="model-status"><span class="status {status_cls}">{esc(m.status)}</span></div>'
        note_html = f'<div class="cand-note">{esc(m.note)}</div>' if m.note else ""
        gates_pct = per.fmt_pct(100.0 * m.gates_passed / m.gates_total) if m.gates_total else "n/a"
        crit = (
            f'<span class="status status--fail">{m.critical_failures}</span>'
            if m.critical_failures
            else "0"
        )
        wall = (
            "n/a"
            if m.total_wall is None
            else f"{m.total_wall:.1f} сек<br><strong>{per.fmt_mmss(m.total_wall)}</strong>"
        )
        cost_per_point = (
            per.fmt_money(m.total_cost / m.mean_completion, 4)
            if m.total_cost is not None and m.mean_completion > 0
            else "n/a"
        )
        rows.append(
            "            <tr>\n"
            f'              <td data-label="Модель"><strong>{esc(m.label)}</strong>{runner_pill}{scope}{status_html}{note_html}</td>\n'
            f'              <td class="num" data-label="Ср. выполнение"><strong>{per.fmt_pct(m.mean_completion)}/100</strong></td>\n'
            f'              <td class="num" data-label="Ср. точность">{per.fmt_pct(m.mean_accuracy)}%</td>\n'
            f'              <td class="num" data-label="Gates"><strong>{m.gates_passed}/{m.gates_total}</strong><br>{gates_pct}%</td>\n'
            f'              <td class="num" data-label="Critical">{crit}</td>\n'
            f'              <td class="num" data-label="Σ время">{wall}</td>\n'
            f'              <td class="num" data-label="Σ стоимость"><strong>{per.fmt_money(m.total_cost, 4)}</strong></td>\n'
            f'              <td class="num" data-label="$ за балл">{cost_per_point}</td>\n'
            "            </tr>"
        )
    body = "\n".join(rows)
    return f"""    <section class="section" aria-labelledby="totals-title">
      <p class="eyebrow">Сводка по моделям</p>
      <h2 id="totals-title">Итоги набора в цифрах</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Модель</th>
              <th>Ср. выполнение</th>
              <th>Ср. точность</th>
              <th>Gates</th>
              <th>Critical</th>
              <th>Σ время</th>
              <th>Σ стоимость</th>
              <th>$ за балл</th>
            </tr>
          </thead>
          <tbody>
{body}
          </tbody>
        </table>
      </div>
    </section>"""


def render_metrics_column(models: list[SummaryModel]) -> str:
    blocks: list[str] = []
    blocks.append(
        per.render_metric_block(
            "Среднее выполнение",
            [(m.label, per.fmt_pct(m.mean_completion), m.mean_completion, m.index) for m in models],
        )
    )
    blocks.append(
        per.render_metric_block(
            "Приёмка гейтов (всего)",
            [
                (
                    m.label,
                    f"{m.gates_passed}/{m.gates_total} · {per.fmt_pct(100.0 * m.gates_passed / m.gates_total) if m.gates_total else 'n/a'}%",
                    100.0 * m.gates_passed / m.gates_total if m.gates_total else 0.0,
                    m.index,
                )
                for m in models
            ],
        )
    )
    if all(m.total_cost is not None for m in models):
        priciest = max(m.total_cost or 0.0 for m in models)
        cheapest = min(m.total_cost or 0.0 for m in models)
        rows = []
        for m in models:
            suffix = ""
            if m.total_cost == priciest and priciest > cheapest:
                suffix = f" · в {priciest / cheapest:.2f}× дороже"
            width = 100.0 * (m.total_cost or 0.0) / priciest if priciest else 0.0
            rows.append((m.label, f"{per.fmt_money(m.total_cost, 3)}{suffix}", width, m.index))
        blocks.append(per.render_metric_block("Суммарная стоимость", rows))
    return "\n\n".join(blocks)


def render_verdict(review: dict[str, Any], winner: SummaryModel) -> str:
    verdict = review["verdict"]
    score_label = verdict.get("scoreLabel") or f"{winner.label} · средний score"
    score_caption = verdict.get("scoreCaption")
    if not score_caption:
        score_caption = f"среднее по {len(winner.cells)} задачам"
        if winner.total_cost is not None:
            score_caption += f" · Σ {per.fmt_money(winner.total_cost, 3)} за запуски"
    return f"""    <section class="verdict" aria-labelledby="verdict-title">
      <div class="panel verdict-main">
        <p class="eyebrow">Вердикт набора</p>
        <h2 id="verdict-title">{esc(verdict["headline"])}</h2>
        <p>{esc(verdict["text"])}</p>
      </div>
      <div class="panel verdict-score" aria-label="Итог {esc(winner.label)}: среднее {per.fmt_pct(winner.mean_completion)} баллов из 100 по {len(winner.cells)} задачам">
        <span class="label">{esc(score_label)}</span>
        <strong class="value">{per.fmt_pct(winner.mean_completion)}</strong>
        <span class="caption">{esc(score_caption)}</span>
      </div>
    </section>"""


def render_footer(models: list[SummaryModel], runs: list[TaskRun], review: dict[str, Any] | None) -> str:
    notes = (review or {}).get("footerNotes") or [DEFAULT_FOOTER_NOTE]
    if not isinstance(notes, list):
        per.fail("review.footerNotes must be a list of strings")
    # footerNotes are trusted human-authored HTML and intentionally not escaped;
    # **bold** markdown is converted (see agent_eval_report.render_footer_note).
    left = "\n        ".join(f"<p>{per.render_footer_note(note)}</p>" for note in notes)

    label_by_key = {m.model_key: m.label for m in models}
    seen: set[str] = set()
    links: list[str] = []
    for run in runs:
        for cand in run.candidates:
            source = cand.pricing_source
            if isinstance(source, str) and source and source not in seen:
                seen.add(source)
                label = label_by_key.get(cand.model_key, cand.label)
                links.append(f'<p><a href="{esc(source, quote=True)}">Тариф {esc(label)}</a></p>')
    right = "\n        ".join(links) or "<p>—</p>"
    return f"""    <footer class="footer">
      <div>
        {left}
      </div>
      <div>
        {right}
      </div>
    </footer>"""


def render_report(
    models: list[SummaryModel],
    runs: list[TaskRun],
    axes: list[tuple[str, list[float]]],
    review: dict[str, Any] | None,
) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.render_report
    # purpose: Assemble the full self-contained HTML summary: hero with pills,
    #   optional verdict, task x model matrix, aggregated radar + metric blocks,
    #   per-model totals table, optional findings and footer.
    # inputs: models — aggregated models; runs — loaded tasks; axes — radar axes
    #   over per-model means; review — optional summary review.
    # returns: complete HTML document as a string.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: SystemExit on invalid verdict/findings fields.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.render_report
    review = review or {}
    title_text = review.get("title") or DEFAULT_TITLE
    subtitle = review.get("subtitle") or (
        "Сводка по нескольким закреплённым задачам: объективные метрики контроллера "
        "плюс человеческое слепое ревью, агрегированные по моделям."
    )
    date_label = review.get("dateLabel") or ", ".join(
        dict.fromkeys(r.date_label for r in runs if r.date_label)
    ) or "—"

    pill_texts = [
        f"<strong>Задачи:</strong>&nbsp; {len(runs)}",
        f"<strong>Модели:</strong>&nbsp; {len(models)}",
        f"<strong>Состав:</strong>&nbsp; {esc(' · '.join(m.label for m in models))}",
    ]
    winner = find_winner(models, review) if review.get("verdict") else None
    pill_html = "\n        ".join(f'<span class="pill">{p}</span>' for p in pill_texts)
    if winner is not None:
        pill_html += f'\n        <span class="pill pill--winner">Рекомендация: {esc(winner.label)}</span>'
    verdict_html = render_verdict(review, winner) if winner is not None else ""

    legend = "\n          ".join(
        f'<span class="legend-item"><span class="swatch swatch--c{m.index}"></span>{esc(m.label)}</span>'
        for m in models
    )
    note_parts = [
        "Скорость и ценовая эффективность сначала нормализованы внутри каждой задачи (лучший = 100), "
        "затем усреднены по задачам модели. «Точность» — прохождение бизнес-кейсов, "
        "blind review — оценка патча до раскрытия модели."
    ]
    if not all(m.mean_price is not None for m in models):
        note_parts.append("Нормализованная цена известна не для всех моделей — ось «Цена» скрыта (n/a).")
    if not all(m.mean_speed is not None for m in models):
        note_parts.append("Время работы известно не для всех моделей — ось «Скорость» скрыта (n/a).")
    chart_note = " ".join(note_parts)

    findings_html = per.render_findings(models, review) if review.get("findings") else ""
    footer_html = render_footer(models, runs, review if review else None)
    css = per.BASE_CSS + "\n" + per.candidate_css(models) + "\n" + SUMMARY_CSS

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <!-- generated by scripts/agent_eval_summary.py -->
  <title>{esc(title_text)}</title>
  <style>{css}  </style>
</head>
<body>
  <main class="page">
    <header>
      <p class="eyebrow">SolarSage · Coding agent benchmark · {esc(date_label)}</p>
      <h1>{esc(title_text)}</h1>
      <p class="lede">{esc(subtitle)}</p>
      <div class="hero-meta" aria-label="Параметры набора">
        {pill_html}
      </div>
    </header>

{verdict_html}

    <section class="comparison" aria-labelledby="radar-title">
      <div class="chart-wrap">
        <p class="eyebrow">Средний профиль моделей · шкала 0–100</p>
        <h2 id="radar-title">Где каждая модель сильнее в среднем</h2>
{per.radar_svg(models, axes)}
        <div class="legend" aria-hidden="true">
          {legend}
        </div>
        <p class="chart-note">{esc(chart_note)}</p>
      </div>

      <div class="metrics" aria-label="Средние сравнительные показатели">
{render_metrics_column(models)}
      </div>
    </section>

{render_matrix(models, runs)}

{render_totals_table(models, len(runs))}

{findings_html}

{footer_html}
  </main>
</body>
</html>
"""


# END_BLOCK: HTML


# START_BLOCK: CLI


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained HTML summary over several agent eval runs.",
    )
    parser.add_argument("--runs", required=True, nargs="+", type=Path, help="run directories with metrics.json + review.json")
    parser.add_argument("--review", type=Path, default=None, help="optional summary review JSON (see module docstring)")
    parser.add_argument("--out", required=True, type=Path, help="output HTML file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.main
    # purpose: CLI entry: load runs and optional summary review, aggregate,
    #   render and write the summary HTML.
    # inputs: argv — optional argument vector (defaults to sys.argv).
    # returns: process exit code (0 on success).
    # side_effects: reads run/review files, writes --out (mkdir -p), stdout summary.
    # emitted_logs: none.
    # error_behavior: invalid input -> SystemExit non-zero via per.fail();
    #   missing --review is allowed and skips verdict/findings.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-SUMMARY.main
    args = parse_args(argv)

    if not args.runs:
        per.fail("--runs must list at least one run directory")
    runs = load_runs(args.runs)
    review = per.load_json(args.review, "summary review") if args.review else None
    if review is not None and not isinstance(review, dict):
        per.fail("summary review must contain a JSON object")

    models = build_models(runs, review)
    compute_aggregates(models)
    axes = build_axes(models)

    html_doc = render_report(models, runs, axes, review)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_doc, encoding="utf-8")
    print(
        f"agent_eval_summary: wrote {args.out} "
        f"({len(runs)} tasks, {len(models)} models, {len(axes)} radar axes)"
    )
    return 0


# END_BLOCK: CLI


if __name__ == "__main__":
    sys.exit(main())
