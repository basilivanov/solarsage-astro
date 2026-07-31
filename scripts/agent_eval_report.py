#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: MODULE_AGENT_EVAL_REPORT — self-contained HTML report for agent eval runs
# ROLE: Merge controller metrics (a scripts/agent_eval.py run directory) with a
#       small human review JSON into a single Russian HTML report (SVG radar
#       included) for 2-4 model candidates. Replaces hand-written report.html.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-AGENT-EVAL-REPORT
# purpose: Generate a self-contained HTML comparison report from one agent-eval
#   run directory (metrics.json + optional manifest.json) plus a human review
#   file (blind scores, verdict, findings). Reproduces the visual language of
#   the hand-written evals/results/*/report.html reports for 2-4 candidates.
# owns:
#   - scripts/agent_eval_report.py
# inputs: --run dir (metrics.json required, manifest.json optional),
#   --review JSON (schema documented in the module docstring), --out path.
# outputs: one self-contained HTML file (RU, inline CSS/SVG, no external assets)
#   and a one-line stdout summary.
# dependencies: Python 3 stdlib only (argparse, html, json, math, pathlib, sys,
#   dataclasses, typing).
# side_effects: reads run/review files, writes --out (creating parent dirs);
#   no network, no git, no model invocation.
# emitted_logs: none.
# invariants:
#   - 2..4 candidates (palette bound), matched metrics<->review by modelKey;
#   - every metrics candidate must have a review entry and vice versa;
#   - radar speed/price axes are normalized best=100 (speed rounded to 0.1,
#     price to 0.01); acceptance = passed verification gates / total gates;
#   - the price axis (and cost metric block) is dropped unless every candidate
#     has a positive cost.normalizedCostUsd;
#   - all review strings are HTML-escaped except footerNotes (trusted HTML,
#     "**bold**" markdown converted to <strong>).
# failure_policy: missing or invalid input -> message on stderr, non-zero exit.
# END_MODULE_CONTRACT: M-SCRIPTS-AGENT-EVAL-REPORT

# START_MODULE_MAP: M-SCRIPTS-AGENT-EVAL-REPORT
# public_entrypoints:
#   - main
# semantic_blocks:
#   - LOAD: read and validate metrics/manifest/review JSON inputs.
#   - MODEL: Candidate dataclass and normalized axis score computation.
#   - RADAR: SVG grid/axes/labels/polygons/dots generation.
#   - HTML: CSS plus report section assembly.
#   - CLI: argparse entry point.
# owned_tests: none (validated via golden-run regeneration)
# END_MODULE_MAP: M-SCRIPTS-AGENT-EVAL-REPORT

"""
agent_eval_report.py — generate a self-contained HTML report for one local
coding-agent eval run (see scripts/agent_eval.py and evals/README.md).

Usage:
    python3 scripts/agent_eval_report.py \\
        --run evals/results/<run-id> \\
        --review evals/results/<run-id>/review.json \\
        --out evals/results/<run-id>/report.html

--run must contain metrics.json (required) and may contain manifest.json
(optional fallback for taskId / baseSha / baseTree / createdAt).

Review JSON schema (full example: evals/review.example.json):

    {
      "title": "Luna high vs Gemini 3.6 high",  # optional; default "<A> vs <B> [vs ...]"
      "subtitle": "lede paragraph under the H1", # required
      "dateLabel": "30 июля 2026",               # optional; default manifest.createdAt date
      "taskId": "checkin-mood-trend-v1",         # optional; default manifest.task.id
      "baseSha": "ec2331614b48…",                # optional; default manifest.base.baseSha
      "verdict": {                               # required
        "winnerModelKey": "luna-high",           # required, must exist in metrics.json
        "headline": "Luna — основной кодер …",    # required, verdict panel H2
        "text": "…",                              # required, verdict panel paragraph
        "scoreLabel": "Luna · final score",      # optional; default "<winner label> · final score"
        "scoreCaption": "5/5 gates · ≈ $0.095 за запуск"
                                                 # optional; default "<gates> gates · ≈ $<cost> за запуск"
      },
      "candidates": [              # required, one entry per metrics candidate;
                                   # list order = report display order
        {
          "modelKey": "luna-high",               # required, key from metrics.json
          "label": "Luna high",                  # required, display name
          "runnerLabel": "Codex · high effort",  # optional pill under the name
          "completion": 90,                      # required, 0-100, acceptance-adjusted
          "accuracy": 87.5,                      # required, 0-100, business-rule cases
          "accuracyDetail": "7/8",               # optional raw fraction next to accuracy
          "blind": 85,                           # required, 0-100 blind patch review score
          "status": "Готово к поставке",          # required status text
          "statusOk": true,                      # required, green/red status dot
          "note": "short reviewer note"          # optional, shown under the model name
        }
      ],
      "findings": [                              # optional, 2-4 recommended
        {"title": "…", "text": "…", "modelKey": "luna-high"},  # modelKey may be null
        {"title": "…", "text": "…", "modelKey": null}
      ],
      "findingsTitle": "Три вывода без лишней теории",  # optional; default from count
      "footerNotes": [                           # optional, methodology lines;
        "<strong>Метод:</strong> …"              # TRUSTED HTML — not escaped
      ]
    }

Radar axes (0-100): Приёмка (verification gates), Выполнение (completion),
Точность (accuracy), Скорость (fastest=100), Цена (cheapest=100, hidden unless
all candidates have a positive normalizedCostUsd), Blind review (blind).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape as esc
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Sequence


PALETTE = ("#6850b7", "#d16b42", "#26765c", "#2262a8")
MAX_CANDIDATES = len(PALETTE)

# Radar geometry inside viewBox "0 0 520 430".
CX, CY = 260.0, 220.0
RADIUS = 150.0
LABEL_RADIUS = 178.0
GRID_FRACTIONS = (0.25, 0.5, 0.75, 1.0)

FINDINGS_TITLES = {
    2: "Два вывода без лишней теории",
    3: "Три вывода без лишней теории",
    4: "Четыре вывода без лишней теории",
}


# START_BLOCK: LOAD


def fail(message: str) -> None:
    raise SystemExit(f"agent_eval_report: error: {message}")


def load_json(path: Path, what: str) -> Any:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.load_json
    # purpose: Read and parse a JSON input file with uniform error reporting.
    # inputs: path — file to read; what — human label for error messages.
    # returns: parsed JSON value.
    # side_effects: filesystem read.
    # emitted_logs: none.
    # error_behavior: raises SystemExit(1) on missing file or invalid JSON.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.load_json
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"{what} not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"{what} is not valid JSON: {path}: {exc}")


def req_str(mapping: dict[str, Any], name: str, where: str) -> str:
    value = mapping.get(name)
    if not isinstance(value, str) or not value.strip():
        fail(f"{where}.{name} is required and must be a non-empty string")
    return value


def req_score(mapping: dict[str, Any], name: str, where: str) -> float:
    value = mapping.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{where}.{name} is required and must be a number")
    if not 0.0 <= float(value) <= 100.0:
        fail(f"{where}.{name} must be within 0-100, got {value}")
    return float(value)


# END_BLOCK: LOAD


# START_BLOCK: MODEL


@dataclass
class Candidate:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.Candidate
    # purpose: Merged per-candidate view of metrics.json data (measured) and
    #   review data (human scores), plus normalized radar axis scores.
    # inputs: built by build_candidates + compute_scores.
    # returns: n/a (dataclass).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: n/a.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.Candidate
    index: int
    model_key: str
    label: str
    runner_label: str
    completion: float
    accuracy: float
    accuracy_detail: str | None
    blind: float
    status: str
    status_ok: bool
    note: str | None
    color: str
    color_soft: str
    runner: str
    model: str
    wall_seconds: float | None
    gates_passed: int
    gates_total: int
    cost_usd: float | None
    pricing_source: str | None
    usage: dict[str, Any]
    accept_pct: float = 0.0
    speed_score: float | None = None
    price_score: float | None = None
    # Optional controller note about a re-run (metrics.json "rerunNote");
    # consumed by scripts/agent_eval_summary.py footnotes, not by this report.
    rerun_note: str | None = None


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_candidates(metrics: dict[str, Any], review: dict[str, Any]) -> list[Candidate]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.build_candidates
    # purpose: Pair every review.candidates entry with its metrics.json entry by
    #   modelKey (review order = display order) and validate required fields.
    # inputs: metrics — parsed metrics.json; review — parsed review JSON.
    # returns: list of Candidate, 2..MAX_CANDIDATES items, palette colors assigned.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: SystemExit on count mismatch, unknown/duplicate modelKey,
    #   missing review entry for a metrics candidate, or invalid fields.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.build_candidates
    metrics_by_key: dict[str, dict[str, Any]] = {}
    for entry in metrics.get("candidates") or []:
        key = entry.get("modelKey")
        if isinstance(key, str) and key:
            metrics_by_key[key] = entry
    if not metrics_by_key:
        fail("metrics.json has no candidates")

    review_entries = review.get("candidates")
    if not isinstance(review_entries, list) or not review_entries:
        fail("review.candidates is required and must be a non-empty list")
    if not 2 <= len(review_entries) <= MAX_CANDIDATES:
        fail(f"review.candidates must contain 2-{MAX_CANDIDATES} entries, got {len(review_entries)}")

    candidates: list[Candidate] = []
    seen: set[str] = set()
    for index, rc in enumerate(review_entries):
        where = f"review.candidates[{index}]"
        if not isinstance(rc, dict):
            fail(f"{where} must be an object")
        key = req_str(rc, "modelKey", where)
        if key in seen:
            fail(f"duplicate review entry for modelKey '{key}'")
        seen.add(key)
        m = metrics_by_key.get(key)
        if m is None:
            fail(f"review candidate '{key}' has no entry in metrics.json")

        verification = m.get("verification") or []
        gates_total = len(verification)
        gates_passed = sum(1 for gate in verification if gate.get("passed"))
        agent = m.get("agent") or {}
        wall = agent.get("wallSeconds")
        cost = m.get("cost") or {}
        cost_usd = cost.get("normalizedCostUsd")
        status_ok = rc.get("statusOk")
        if not isinstance(status_ok, bool):
            fail(f"{where}.statusOk is required and must be a boolean")
        note = rc.get("note")
        accuracy_detail = rc.get("accuracyDetail")
        runner_label = rc.get("runnerLabel") or m.get("runner") or ""

        candidates.append(
            Candidate(
                index=index,
                model_key=key,
                label=req_str(rc, "label", where),
                runner_label=runner_label,
                completion=req_score(rc, "completion", where),
                accuracy=req_score(rc, "accuracy", where),
                accuracy_detail=accuracy_detail if isinstance(accuracy_detail, str) else None,
                blind=req_score(rc, "blind", where),
                status=req_str(rc, "status", where),
                status_ok=status_ok,
                note=note if isinstance(note, str) and note.strip() else None,
                color=PALETTE[index],
                color_soft=hex_to_rgba(PALETTE[index], 0.14),
                runner=m.get("runner") or "",
                model=m.get("model") or "",
                wall_seconds=float(wall) if isinstance(wall, (int, float)) else None,
                gates_passed=gates_passed,
                gates_total=gates_total,
                cost_usd=float(cost_usd) if isinstance(cost_usd, (int, float)) else None,
                pricing_source=cost.get("pricingSource"),
                usage=m.get("usage") or {},
                rerun_note=m.get("rerunNote") if isinstance(m.get("rerunNote"), str) else None,
            )
        )

    extra = sorted(set(metrics_by_key) - seen)
    if extra:
        fail(f"metrics.json candidates missing from review.candidates: {', '.join(extra)}")
    return candidates


def compute_scores(candidates: list[Candidate]) -> None:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.compute_scores
    # purpose: Fill normalized radar/metric scores in place: acceptance from
    #   verification gates, speed (fastest=100, rounded to 0.1) and price
    #   (cheapest=100, rounded to 0.01, only when every candidate has cost > 0).
    # inputs: candidates — list from build_candidates.
    # returns: None (mutates candidates).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: missing wall time leaves speed_score=None (axis hidden).
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.compute_scores
    for cand in candidates:
        cand.accept_pct = 100.0 * cand.gates_passed / cand.gates_total if cand.gates_total else 0.0

    if all(cand.wall_seconds and cand.wall_seconds > 0 for cand in candidates):
        fastest = min(cand.wall_seconds for cand in candidates if cand.wall_seconds)
        for cand in candidates:
            if cand.wall_seconds:
                cand.speed_score = round(100.0 * fastest / cand.wall_seconds, 1)

    if all(cand.cost_usd and cand.cost_usd > 0 for cand in candidates):
        cheapest = min(cand.cost_usd for cand in candidates if cand.cost_usd)
        for cand in candidates:
            if cand.cost_usd:
                cand.price_score = round(100.0 * cheapest / cand.cost_usd, 2)


def build_axes(candidates: list[Candidate]) -> list[tuple[str, list[float]]]:
    # Ordered axis list for the radar; optional axes drop out when data is missing.
    axes: list[tuple[str, list[float]]] = [
        ("Приёмка", [cand.accept_pct for cand in candidates]),
        ("Выполнение", [cand.completion for cand in candidates]),
        ("Точность", [cand.accuracy for cand in candidates]),
    ]
    if all(cand.speed_score is not None for cand in candidates):
        axes.append(("Скорость", [cand.speed_score or 0.0 for cand in candidates]))
    if all(cand.price_score is not None for cand in candidates):
        axes.append(("Цена", [cand.price_score or 0.0 for cand in candidates]))
    axes.append(("Blind review", [cand.blind for cand in candidates]))
    return axes


def find_winner(candidates: list[Candidate], review: dict[str, Any]) -> Candidate:
    verdict = review.get("verdict")
    if not isinstance(verdict, dict):
        fail("review.verdict is required and must be an object")
    winner_key = req_str(verdict, "winnerModelKey", "review.verdict")
    req_str(verdict, "headline", "review.verdict")
    req_str(verdict, "text", "review.verdict")
    for cand in candidates:
        if cand.model_key == winner_key:
            return cand
    fail(f"review.verdict.winnerModelKey '{winner_key}' is not among the candidates")


# END_BLOCK: MODEL


# START_BLOCK: RADAR


def svg_num(value: float) -> str:
    # Compact SVG coordinate: 2 decimals max, trailing zeros stripped.
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def polar(axis_index: int, axis_count: int, value: float) -> tuple[float, float]:
    # Axis 0 points up (-90°), subsequent axes advance clockwise.
    angle = -math.pi / 2 + 2 * math.pi * axis_index / axis_count
    radius = RADIUS * max(0.0, min(100.0, value)) / 100.0
    return CX + radius * math.cos(angle), CY + radius * math.sin(angle)


def radar_svg(candidates: list[Candidate], axes: list[tuple[str, list[float]]]) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.radar_svg
    # purpose: Render the radar chart SVG: 4 grid rings (25/50/75/100%), axis
    #   lines and labels, one value polygon per candidate (first candidate drawn
    #   last, on top), vertex dots and a11y title/desc with per-axis leaders.
    # inputs: candidates — scored candidates; axes — ordered (name, values) list.
    # returns: SVG markup string (without the legend, rendered by caller).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: values are clamped to 0-100; assumes 3..8 axes.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.radar_svg
    count = len(axes)
    parts: list[str] = []

    for fraction in GRID_FRACTIONS:
        points = " ".join(
            f"{svg_num(x)},{svg_num(y)}"
            for x, y in (polar(i, count, fraction * 100.0) for i in range(count))
        )
        parts.append(f'          <polygon class="grid" points="{points}" />')

    for i in range(count):
        x, y = polar(i, count, 100.0)
        parts.append(
            f'          <line class="axis" x1="{svg_num(CX)}" y1="{svg_num(CY)}" '
            f'x2="{svg_num(x)}" y2="{svg_num(y)}" />'
        )

    for i, (name, _values) in enumerate(axes):
        angle = -math.pi / 2 + 2 * math.pi * i / count
        lx = CX + LABEL_RADIUS * math.cos(angle)
        ly = CY + LABEL_RADIUS * math.sin(angle)
        cos_a = math.cos(angle)
        anchor = "start" if cos_a > 0.3 else "end" if cos_a < -0.3 else "middle"
        parts.append(
            f'          <text class="axis-label" x="{svg_num(lx)}" y="{svg_num(ly)}" '
            f'text-anchor="{anchor}">{esc(name)}</text>'
        )

    for cand in reversed(candidates):
        points = " ".join(
            f"{svg_num(x)},{svg_num(y)}"
            for x, y in (polar(i, count, values[cand.index]) for i, (_n, values) in enumerate(axes))
        )
        parts.append(f'          <polygon class="radar-c{cand.index}" points="{points}" />')

    parts.append('          <g aria-hidden="true">')
    for cand in reversed(candidates):
        for i, (_name, values) in enumerate(axes):
            x, y = polar(i, count, values[cand.index])
            parts.append(
                f'            <circle class="dot-c{cand.index}" cx="{svg_num(x)}" cy="{svg_num(y)}" r="4" />'
            )
    parts.append('          </g>')

    leaders: dict[str, list[str]] = {}
    for name, values in axes:
        best = max(values)
        for cand in candidates:
            if values[cand.index] == best:
                leaders.setdefault(cand.label, []).append(name.lower())
    desc = " ".join(
        f"{label} лидирует по осям: {', '.join(names)}." for label, names in leaders.items()
    )
    title = "Радарное сравнение: " + ", ".join(cand.label for cand in candidates)

    svg = [
        f'        <svg class="chart" viewBox="0 0 520 430" role="img" aria-labelledby="radar-svg-title radar-svg-desc">',
        f'          <title id="radar-svg-title">{esc(title)}</title>',
        f'          <desc id="radar-svg-desc">{esc(desc)}</desc>',
        *parts,
        "        </svg>",
    ]
    return "\n".join(svg)


# END_BLOCK: RADAR


# START_BLOCK: HTML


def fmt_pct(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def fmt_mmss(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def fmt_grouped(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "n/a"
    return f"{int(value):,}".replace(",", " ")


def fmt_money(value: float | None, digits: int) -> str:
    if value is None:
        return "n/a"
    return f"${value:.{digits}f}"


BASE_CSS = """
    :root {
      --ink: #201a24;
      --muted: #716977;
      --paper: #fbf9f7;
      --surface: rgba(255, 255, 255, 0.82);
      --line: rgba(63, 47, 68, 0.13);
      --success: #26765c;
      --success-soft: rgba(38, 118, 92, 0.11);
      --danger: #a24b47;
      --shadow: 0 24px 70px rgba(44, 29, 50, 0.10);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 5%, rgba(104, 80, 183, 0.11), transparent 28rem),
        radial-gradient(circle at 92% 16%, rgba(209, 107, 66, 0.10), transparent 26rem),
        var(--paper);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.5;
    }

    .page {
      width: min(1160px, calc(100% - 40px));
      margin: 0 auto;
      padding: 56px 0 64px;
    }

    .eyebrow {
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    h1, h2, h3, p { margin-top: 0; }

    h1 {
      max-width: 850px;
      margin-bottom: 18px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(42px, 7vw, 78px);
      font-weight: 500;
      letter-spacing: -0.055em;
      line-height: 0.98;
    }

    h2 {
      margin-bottom: 22px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(27px, 4vw, 40px);
      font-weight: 500;
      letter-spacing: -0.035em;
      line-height: 1.08;
    }

    h3 {
      margin-bottom: 10px;
      font-size: 16px;
      font-weight: 700;
    }

    .lede {
      max-width: 790px;
      margin-bottom: 30px;
      color: var(--muted);
      font-size: clamp(17px, 2vw, 21px);
    }

    .hero-meta,
    .legend,
    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.52);
      color: var(--muted);
      font-size: 13px;
    }

    .pill strong { color: var(--ink); }

    .pill--winner {
      border-color: rgba(38, 118, 92, 0.22);
      background: var(--success-soft);
      color: var(--success);
      font-weight: 700;
    }

    .verdict {
      display: grid;
      grid-template-columns: 1.5fr 0.7fr;
      gap: 22px;
      margin: 46px 0 64px;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: 28px;
      background: var(--surface);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }

    .verdict-main {
      padding: clamp(28px, 5vw, 46px);
      background:
        linear-gradient(135deg, rgba(104, 80, 183, 0.11), transparent 48%),
        var(--surface);
    }

    .verdict-main p {
      max-width: 700px;
      margin-bottom: 0;
      color: var(--muted);
      font-size: 18px;
    }

    .verdict-score {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 220px;
      padding: 30px;
      color: white;
      background: linear-gradient(150deg, #7561c2, #4d3a90);
    }

    .verdict-score .label {
      color: rgba(255, 255, 255, 0.72);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .verdict-score .value {
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(58px, 8vw, 90px);
      line-height: 0.9;
    }

    .verdict-score .caption {
      color: rgba(255, 255, 255, 0.82);
      font-size: 14px;
    }

    .comparison {
      display: grid;
      grid-template-columns: 1.08fr 0.92fr;
      gap: 42px;
      align-items: center;
      margin-bottom: 70px;
    }

    .chart-wrap {
      min-width: 0;
    }

    .chart {
      display: block;
      width: 100%;
      height: auto;
      overflow: visible;
    }

    .chart .grid {
      fill: none;
      stroke: rgba(63, 47, 68, 0.14);
      stroke-width: 1;
    }

    .chart .axis {
      stroke: rgba(63, 47, 68, 0.12);
      stroke-width: 1;
    }

    .chart .axis-label {
      fill: var(--muted);
      font-size: 12px;
      font-weight: 650;
      letter-spacing: 0.01em;
    }

    .legend {
      justify-content: center;
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }

    .legend-item {
      display: inline-flex;
      gap: 8px;
      align-items: center;
    }

    .swatch {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }

    .chart-note {
      margin: 12px auto 0;
      max-width: 560px;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }

    .metrics {
      display: grid;
      gap: 18px;
    }

    .metric {
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }

    .metric:last-child {
      padding-bottom: 0;
      border-bottom: 0;
    }

    .metric-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 9px;
      font-size: 14px;
    }

    .metric-head span:first-child { color: var(--muted); }
    .metric-head strong { font-variant-numeric: tabular-nums; }

    .bar {
      height: 9px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(63, 47, 68, 0.08);
    }

    .bar + .metric-head { margin-top: 10px; }

    .bar-fill {
      height: 100%;
      border-radius: inherit;
    }

    .section { margin-bottom: 70px; }

    .table-wrap {
      overflow-x: auto;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }

    th,
    td {
      padding: 18px 16px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
    }

    tr:last-child td { border-bottom: 0; }

    th {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    td { font-size: 14px; }
    td strong { font-size: 15px; }
    .num { font-variant-numeric: tabular-nums; }

    .cand-note {
      margin-top: 8px;
      max-width: 280px;
      color: var(--muted);
      font-size: 12px;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-weight: 700;
    }

    .status::before {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      content: "";
    }

    .status--pass { color: var(--success); }
    .status--pass::before { background: var(--success); }
    .status--fail { color: var(--danger); }
    .status--fail::before { background: var(--danger); }

    .findings {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 18px;
    }

    .usage-note {
      max-width: 820px;
      margin: -10px 0 24px;
      color: var(--muted);
      font-size: 14px;
    }

    .finding {
      padding: 24px 0 0;
      border-top: 3px solid var(--line);
    }

    .finding p {
      margin-bottom: 0;
      color: var(--muted);
      font-size: 14px;
    }

    .footer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 28px;
      padding-top: 28px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
    }

    .footer p { margin-bottom: 7px; }

    a {
      color: inherit;
      text-decoration-color: rgba(63, 47, 68, 0.35);
      text-underline-offset: 3px;
    }

    a:hover { color: var(--ink); }

    code {
      color: var(--ink);
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 0.92em;
    }

    @media (max-width: 850px) {
      .page { width: min(100% - 28px, 720px); padding-top: 34px; }
      .verdict,
      .comparison { grid-template-columns: 1fr; }
      .verdict-score { min-height: 190px; }
      .comparison { gap: 30px; }
      .findings { grid-template-columns: 1fr; }
      .footer { grid-template-columns: 1fr; }
    }

    @media (max-width: 520px) {
      h1 { font-size: 43px; }
      .page { width: min(100% - 22px, 480px); }
      .panel { border-radius: 22px; }
      .verdict-main, .verdict-score { padding: 24px; }
      .chart .axis-label { font-size: 10px; }
      .hero-meta { align-items: flex-start; }

      .table-wrap {
        overflow-x: visible;
        border: 0;
      }

      table,
      tbody,
      tr,
      td {
        display: block;
        width: 100%;
      }

      table { min-width: 0; }
      thead { display: none; }

      tbody {
        display: grid;
        gap: 16px;
      }

      tr {
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--surface);
      }

      tr:last-child td { border-bottom: 1px solid var(--line); }

      td,
      tr:last-child td:last-child {
        display: grid;
        grid-template-columns: minmax(98px, 0.75fr) minmax(0, 1.25fr);
        gap: 12px;
        align-items: center;
        padding: 12px 14px;
        border-bottom: 1px solid var(--line);
        text-align: right;
      }

      td:last-child { border-bottom: 0; }

      td::before {
        content: attr(data-label);
        color: var(--muted);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-align: left;
        text-transform: uppercase;
      }

      td:first-child {
        grid-template-columns: 1fr;
        gap: 8px;
        text-align: left;
      }

      td:first-child::before { display: none; }
      td .pill, td .status { justify-self: end; }
      td:first-child .pill { justify-self: start; }
    }

    @media print {
      body { background: white; }
      .page { width: 100%; padding: 0; }
      .panel { box-shadow: none; backdrop-filter: none; }
      .section, .comparison, .verdict { break-inside: avoid; }
      a { text-decoration: none; }
    }
"""


def candidate_css(candidates: list[Candidate]) -> str:
    rules: list[str] = []
    for cand in candidates:
        i = cand.index
        rules.append(
            f"    .chart .radar-c{i} {{ fill: {cand.color_soft}; stroke: {cand.color}; "
            f"stroke-width: 3; stroke-linejoin: round; }}"
        )
        rules.append(f"    .chart .dot-c{i} {{ fill: {cand.color}; }}")
        rules.append(f"    .swatch--c{i} {{ background: {cand.color}; }}")
        rules.append(f"    .bar-fill--c{i} {{ background: {cand.color}; }}")
        rules.append(f"    .finding--c{i} {{ border-color: {cand.color}; }}")
    return "\n".join(rules)


def render_metric_block(title: str, rows: list[tuple[str, str, float, int]]) -> str:
    # rows: (label, value_html, bar_width_pct, candidate_index)
    parts = [f'        <div class="metric">', f"          <h3>{esc(title)}</h3>"]
    for label, value_html, width, index in rows:
        parts.append(
            f'          <div class="metric-head"><span>{esc(label)}</span><strong>{value_html}</strong></div>'
        )
        parts.append(
            f'          <div class="bar"><div class="bar-fill bar-fill--c{index}" '
            f'style="width:{fmt_pct(width)}%"></div></div>'
        )
    parts.append("        </div>")
    return "\n".join(parts)


def render_metrics_column(candidates: list[Candidate]) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.render_metrics_column
    # purpose: Render the right-hand metric blocks next to the radar: working
    #   time (bar = speed score), controller acceptance, normalized cost
    #   (bar = share of max cost, only when all costs known) and business rules.
    # inputs: candidates — scored candidates.
    # returns: HTML markup string for the .metrics container.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: blocks whose inputs are missing are omitted.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.render_metrics_column
    blocks: list[str] = []

    if all(cand.speed_score is not None and cand.wall_seconds for cand in candidates):
        walls = [cand.wall_seconds or 0.0 for cand in candidates]
        fastest = min(walls)
        slowest = max(walls)
        rows = []
        for cand in candidates:
            suffix = ""
            if cand.wall_seconds == fastest and slowest > fastest:
                suffix = f" · в {slowest / fastest:.2f}× быстрее"
            rows.append((cand.label, f"{fmt_mmss(cand.wall_seconds or 0.0)}{suffix}", cand.speed_score or 0.0, cand.index))
        blocks.append(render_metric_block("Время работы", rows))

    rows = [
        (
            cand.label,
            f"{cand.gates_passed}/{cand.gates_total} · {fmt_pct(cand.accept_pct)}%",
            cand.accept_pct,
            cand.index,
        )
        for cand in candidates
    ]
    blocks.append(render_metric_block("Контроллерная приёмка", rows))

    if all(cand.cost_usd and cand.cost_usd > 0 for cand in candidates):
        costs = [cand.cost_usd or 0.0 for cand in candidates]
        cheapest = min(costs)
        priciest = max(costs)
        rows = []
        for cand in candidates:
            suffix = ""
            if cand.cost_usd == priciest and priciest > cheapest:
                suffix = f" · в {priciest / cheapest:.2f}× дороже"
            width = 100.0 * (cand.cost_usd or 0.0) / priciest
            rows.append((cand.label, f"{fmt_money(cand.cost_usd, 3)}{suffix}", width, cand.index))
        blocks.append(render_metric_block("Нормализованная стоимость", rows))

    rows = []
    for cand in candidates:
        detail = f"{cand.accuracy_detail} · " if cand.accuracy_detail else ""
        rows.append((cand.label, f"{detail}{fmt_pct(cand.accuracy)}%", cand.accuracy, cand.index))
    blocks.append(render_metric_block("Бизнес-правила", rows))

    return "\n\n".join(blocks)


def render_numbers_table(candidates: list[Candidate]) -> str:
    rows: list[str] = []
    for cand in candidates:
        runner_pill = (
            f'<br><span class="pill">{esc(cand.runner_label)}</span>' if cand.runner_label else ""
        )
        note = f'<div class="cand-note">{esc(cand.note)}</div>' if cand.note else ""
        wall = cand.wall_seconds
        time_cell = "n/a" if wall is None else f"{wall:.1f} сек<br><strong>{fmt_mmss(wall)}</strong>"
        accuracy_cell = (
            f"{esc(cand.accuracy_detail)}<br>{fmt_pct(cand.accuracy)}%"
            if cand.accuracy_detail
            else f"{fmt_pct(cand.accuracy)}%"
        )
        status_class = "status--pass" if cand.status_ok else "status--fail"
        rows.append(
            "            <tr>\n"
            f'              <td data-label="Модель"><strong>{esc(cand.label)}</strong>{runner_pill}{note}</td>\n'
            f'              <td class="num" data-label="Время">{time_cell}</td>\n'
            f'              <td class="num" data-label="Gates"><strong>{cand.gates_passed}/{cand.gates_total}</strong>'
            f"<br>{fmt_pct(cand.accept_pct)}%</td>\n"
            f'              <td class="num" data-label="Выполнение"><strong>{fmt_pct(cand.completion)}/100</strong></td>\n'
            f'              <td class="num" data-label="Точность">{accuracy_cell}</td>\n'
            f'              <td class="num" data-label="Стоимость"><strong>{fmt_money(cand.cost_usd, 4)}</strong></td>\n'
            f'              <td data-label="Статус"><span class="status {status_class}">{esc(cand.status)}</span></td>\n'
            "            </tr>"
        )
    body = "\n".join(rows)
    return f"""      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Модель</th>
              <th>Время</th>
              <th>Gates</th>
              <th>Выполнение</th>
              <th>Точность</th>
              <th>Стоимость</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
{body}
          </tbody>
        </table>
      </div>"""


def render_tokens_table(candidates: list[Candidate]) -> str:
    rows: list[str] = []
    for cand in candidates:
        usage = cand.usage
        rows.append(
            "            <tr>\n"
            f'              <td data-label="Модель"><strong>{esc(cand.label)}</strong></td>\n'
            f'              <td class="num" data-label="Input">{fmt_grouped(usage.get("input_tokens"))}</td>\n'
            f'              <td class="num" data-label="Cached input">{fmt_grouped(usage.get("cached_input_tokens"))}</td>\n'
            f'              <td class="num" data-label="Output">{fmt_grouped(usage.get("output_tokens"))}</td>\n'
            f'              <td class="num" data-label="Reasoning">{fmt_grouped(usage.get("reasoning_tokens"))}</td>\n'
            f'              <td class="num" data-label="Официальная цена"><strong>{fmt_money(cand.cost_usd, 4)}</strong></td>\n'
            "            </tr>"
        )
    body = "\n".join(rows)
    return f"""      <div class="table-wrap">
        <table aria-labelledby="usage-title">
          <thead>
            <tr>
              <th>Модель</th>
              <th>Input</th>
              <th>Cached input</th>
              <th>Output</th>
              <th>Reasoning</th>
              <th>Официальная цена</th>
            </tr>
          </thead>
          <tbody>
{body}
          </tbody>
        </table>
      </div>"""


def render_findings(candidates: list[Candidate], review: dict[str, Any]) -> str:
    findings = review.get("findings") or []
    if not isinstance(findings, list):
        fail("review.findings must be a list")
    by_key = {cand.model_key: cand for cand in candidates}
    articles: list[str] = []
    for i, finding in enumerate(findings):
        where = f"review.findings[{i}]"
        if not isinstance(finding, dict):
            fail(f"{where} must be an object")
        title = req_str(finding, "title", where)
        text = req_str(finding, "text", where)
        model_key = finding.get("modelKey")
        css_class = "finding"
        if model_key is not None:
            cand = by_key.get(model_key)
            if cand is None:
                fail(f"{where}.modelKey '{model_key}' is not among the candidates")
            css_class = f"finding finding--c{cand.index}"
        articles.append(
            f'        <article class="{css_class}">\n'
            f"          <h3>{esc(title)}</h3>\n"
            f"          <p>{esc(text)}</p>\n"
            "        </article>"
        )
    title = review.get("findingsTitle") or FINDINGS_TITLES.get(len(findings), "Выводы без лишней теории")
    return f"""    <section class="section" aria-labelledby="meaning-title">
      <p class="eyebrow">Что это означает</p>
      <h2 id="meaning-title">{esc(title)}</h2>
      <div class="findings">
{chr(10).join(articles)}
      </div>
    </section>"""


def render_footer_note(note: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.render_footer_note
    # purpose: Render one footerNotes entry: input is trusted human-authored
    #   HTML (not escaped); additionally `**bold**` markdown is converted to
    #   <strong> because review authors use it (see evals/results/*/review.json).
    # inputs: note — raw footerNotes string.
    # returns: HTML fragment safe to embed.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: non-string input is stringified by caller contract; no raise.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.render_footer_note
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", note)


def render_footer(candidates: list[Candidate], review: dict[str, Any], base_sha: str | None, base_tree: str | None) -> str:
    notes = review.get("footerNotes") or []
    if not isinstance(notes, list):
        fail("review.footerNotes must be a list of strings")
    # footerNotes are trusted human-authored HTML and intentionally not escaped;
    # **bold** markdown is converted (see render_footer_note).
    left = "\n        ".join(f"<p>{render_footer_note(note)}</p>" for note in notes) or "<p>—</p>"

    right: list[str] = []
    seen_sources: set[str] = set()
    for cand in candidates:
        source = cand.pricing_source
        if isinstance(source, str) and source and source not in seen_sources:
            seen_sources.add(source)
            right.append(f'<p><a href="{esc(source, quote=True)}">Тариф {esc(cand.label)}</a></p>')
    if base_sha:
        code = f"base {base_sha[:8]}"
        if base_tree:
            code += f" · tree {base_tree[:8]}"
        right.append(f"<p><code>{esc(code)}</code></p>")
    right_html = "\n        ".join(right)
    return f"""    <footer class="footer">
      <div>
        {left}
      </div>
      <div>
        {right_html}
      </div>
    </footer>"""


def render_report(
    candidates: list[Candidate],
    axes: list[tuple[str, list[float]]],
    review: dict[str, Any],
    winner: Candidate,
    meta: dict[str, Any],
) -> str:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.render_report
    # purpose: Assemble the full self-contained HTML document: hero with pills,
    #   verdict panels, radar + metrics column, numbers/tokens tables, findings
    #   and footer, in the visual language of the hand-written sample report.
    # inputs: candidates — scored candidates (display order); axes — radar axes;
    #   review — parsed review JSON; winner — verdict winner; meta — resolved
    #   taskId/baseSha/baseTree/dateLabel/gatesTotal.
    # returns: complete HTML document as a string.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: SystemExit on missing required review fields.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.render_report
    verdict = review["verdict"]
    subtitle = req_str(review, "subtitle", "review")
    labels = [cand.label for cand in candidates]
    title_text = review.get("title") or " vs ".join(labels)
    if review.get("title"):
        title_html = esc(title_text)
    elif len(labels) == 2:
        title_html = f"{esc(labels[0])}<br>vs {esc(labels[1])}"
    else:
        title_html = esc(" vs ".join(labels))

    gates_total = meta["gates_total"]
    gates_label = "1 независимый gate" if gates_total == 1 else f"{gates_total} независимых gates"
    score_label = verdict.get("scoreLabel") or f"{winner.label} · final score"
    score_caption = verdict.get("scoreCaption")
    if not score_caption:
        score_caption = f"{winner.gates_passed}/{winner.gates_total} gates"
        if winner.cost_usd:
            score_caption += f" · ≈ {fmt_money(winner.cost_usd, 3)} за запуск"

    legend = "\n          ".join(
        f'<span class="legend-item"><span class="swatch swatch--c{cand.index}"></span>{esc(cand.label)}</span>'
        for cand in candidates
    )
    note_parts = [
        "Скорость и ценовая эффективность нормализованы относительно лучшего результата среди кандидатов. "
        "«Точность» — прохождение бизнес-кейсов, blind review — оценка патча до раскрытия модели."
    ]
    if not all(cand.price_score is not None for cand in candidates):
        note_parts.append("Нормализованная цена известна не для всех кандидатов — ось «Цена» скрыта (n/a).")
    if not all(cand.speed_score is not None for cand in candidates):
        note_parts.append("Время работы известно не для всех кандидатов — ось «Скорость» скрыта (n/a).")
    chart_note = " ".join(note_parts)

    findings_html = render_findings(candidates, review) if review.get("findings") else ""
    footer_html = render_footer(candidates, review, meta.get("base_sha"), meta.get("base_tree"))
    css = BASE_CSS + "\n" + candidate_css(candidates) + "\n"

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <!-- generated by scripts/agent_eval_report.py -->
  <title>{esc(title_text)} — SolarSage Agent Eval</title>
  <style>{css}  </style>
</head>
<body>
  <main class="page">
    <header>
      <p class="eyebrow">SolarSage · Coding agent benchmark · {esc(meta["date_label"])}</p>
      <h1>{title_html}</h1>
      <p class="lede">{esc(subtitle)}</p>
      <div class="hero-meta" aria-label="Параметры эксперимента">
        <span class="pill"><strong>Задача:</strong>&nbsp; {esc(meta["task_id"])}</span>
        <span class="pill"><strong>Snapshot:</strong>&nbsp; {esc(meta["sha8"])}</span>
        <span class="pill"><strong>Контроль:</strong>&nbsp; {esc(gates_label)}</span>
        <span class="pill pill--winner">Рекомендация: {esc(winner.label)}</span>
      </div>
    </header>

    <section class="verdict" aria-labelledby="verdict-title">
      <div class="panel verdict-main">
        <p class="eyebrow">Вердикт пилота</p>
        <h2 id="verdict-title">{esc(verdict["headline"])}</h2>
        <p>{esc(verdict["text"])}</p>
      </div>
      <div class="panel verdict-score" aria-label="Итог {esc(winner.label)}: {fmt_pct(winner.completion)} баллов из 100, {winner.gates_passed} проверок из {winner.gates_total}">
        <span class="label">{esc(score_label)}</span>
        <strong class="value">{fmt_pct(winner.completion)}</strong>
        <span class="caption">{esc(score_caption)}</span>
      </div>
    </section>

    <section class="comparison" aria-labelledby="radar-title">
      <div class="chart-wrap">
        <p class="eyebrow">Профиль моделей · шкала 0–100</p>
        <h2 id="radar-title">Где каждая модель сильнее</h2>
{radar_svg(candidates, axes)}
        <div class="legend" aria-hidden="true">
          {legend}
        </div>
        <p class="chart-note">{esc(chart_note)}</p>
      </div>

      <div class="metrics" aria-label="Основные сравнительные показатели">
{render_metrics_column(candidates)}
      </div>
    </section>

    <section class="section" aria-labelledby="numbers-title">
      <p class="eyebrow">Объективные результаты</p>
      <h2 id="numbers-title">Итог в цифрах</h2>
{render_numbers_table(candidates)}
    </section>

    <section class="section" aria-labelledby="usage-title">
      <p class="eyebrow">Токены и экономика</p>
      <h2 id="usage-title">Что было потрачено</h2>
      <p class="usage-note">CLI провайдеров считают контекст по-разному, поэтому токены показаны как прозрачный первичный отчёт, а стоимость пересчитана отдельно по официальным тарифам.</p>
{render_tokens_table(candidates)}
    </section>

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
        description="Generate a self-contained HTML report for one local agent eval run.",
    )
    parser.add_argument("--run", required=True, type=Path, help="run directory with metrics.json (+ optional manifest.json)")
    parser.add_argument("--review", required=True, type=Path, help="human review JSON (see module docstring)")
    parser.add_argument("--out", required=True, type=Path, help="output HTML file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.main
    # purpose: CLI entry: load inputs, score candidates, render and write HTML.
    # inputs: argv — optional argument vector (defaults to sys.argv).
    # returns: process exit code (0 on success).
    # side_effects: reads --run/--review files, writes --out (mkdir -p), stdout summary.
    # emitted_logs: none.
    # error_behavior: invalid input -> SystemExit with non-zero code via fail().
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-AGENT-EVAL-REPORT.main
    args = parse_args(argv)

    metrics = load_json(args.run / "metrics.json", "metrics.json")
    if not isinstance(metrics, dict):
        fail("metrics.json must contain a JSON object")
    manifest_path = args.run / "manifest.json"
    manifest = load_json(manifest_path, "manifest.json") if manifest_path.exists() else {}
    review = load_json(args.review, "review file")
    if not isinstance(review, dict):
        fail("review file must contain a JSON object")

    candidates = build_candidates(metrics, review)
    compute_scores(candidates)
    axes = build_axes(candidates)
    winner = find_winner(candidates, review)

    baseline = metrics.get("baseline") or []
    manifest_task = manifest.get("task") or {}
    manifest_base = manifest.get("base") or {}
    base_sha = review.get("baseSha") or manifest_base.get("baseSha")
    created = str(manifest.get("createdAt") or "")
    meta = {
        "task_id": review.get("taskId") or manifest_task.get("id") or "—",
        "base_sha": base_sha,
        "base_tree": manifest_base.get("baseTree"),
        "sha8": (base_sha or "—")[:8],
        "date_label": review.get("dateLabel") or (created[:10] if created else "—"),
        "gates_total": len(baseline) or (candidates[0].gates_total if candidates else 0),
    }

    html_doc = render_report(candidates, axes, review, winner, meta)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_doc, encoding="utf-8")
    print(f"agent_eval_report: wrote {args.out} ({len(candidates)} candidates, {len(axes)} radar axes)")
    return 0


# END_BLOCK: CLI


if __name__ == "__main__":
    sys.exit(main())
