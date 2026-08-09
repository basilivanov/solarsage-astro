#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: NARRATIVE_EVAL_REVIEW_PACK — blind review artifacts for narrative eval
# ROLE: Build an anonymous, deterministic text-review pack from local raw
#       responses and reveal reviewer scores only through the private key.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK
# purpose: Render a blind review pack for the fixed three-candidate narrative
#   evaluation without making network calls or exposing candidate identities.
# owns:
#   - scripts/narrative_eval_review_pack.py
# inputs: local raw response files and the committed inputs.json artifact.
# outputs: review.html, scorecard.md, review-key.json, review.json, and an
#   optional review-revealed.json after the owner submits scores.
# dependencies: Python standard library only.
# side_effects: reads local artifacts and writes only the requested result
#   directory; never reads a database, calls a provider, or changes app code.
# emitted_logs: safe stdout status lines only; raw narrative text is not logged.
# invariants: exactly three fixed candidates, ten deterministic input days,
#   thirty blocks, candidate/day shuffling from run_id, and no model mapping in
#   the blind HTML or scorecard.
# failure_policy: malformed or truncated responses are listed and stop the
#   pack before artifacts are written; reveal validates scores and key shape.
# END_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK

# START_MODULE_MAP: M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK
# public_entrypoints:
#   - main
#   - generate_review_pack
#   - reveal_review
# semantic_blocks:
#   - LOAD: local input, raw response, and review-key loading.
#   - SELECT: deterministic maximum facet/polarity coverage selection.
#   - NORMALIZE: fail-closed raw JSON parsing and product-text extraction.
#   - RENDER: anonymous HTML, scorecard, and empty review template.
#   - REVEAL: score join, means, per-block details, and final table.
#   - CLI: generator and --reveal command line entry point.
# owned_tests: manual generator run plus py_compile and grace_lint gates.
# END_MODULE_MAP: M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from html import escape
import itertools
import json
from pathlib import Path
import random
import sys
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "20260809T082931Z"
DEFAULT_RAW_DIR = REPO_ROOT / ".eval-runs" / "narrative-model-eval-v1" / DEFAULT_RUN_ID
DEFAULT_INPUTS = REPO_ROOT / "evals" / "tasks" / "today-narrative-v5-models" / "inputs.json"
DEFAULT_OUT_DIR = REPO_ROOT / "evals" / "results" / DEFAULT_RUN_ID
NAME_MASK = "ИМЯ"
CLAIMS = ("summary", "meaning", "action")
FORBIDDEN_BLIND_TERMS = ("gemma", "deepseek", "nano", "openai", "qwen")
CLAIM_LABELS = {
    "summary": "Кратко",
    "meaning": "Значение",
    "action": "Действие",
}
SECTION_LABELS = {
    "convergences": "Конвергенции",
    "impulses": "Импульсы",
}


@dataclass(frozen=True)
class Candidate:
    candidate: str
    model_key: str
    arm: str
    label: str


@dataclass(frozen=True)
class ReviewBlock:
    block_id: str
    candidate: Candidate
    record: dict[str, Any]
    response: dict[str, Any]


class ReviewPackError(ValueError):
    """A review-pack contract, privacy, or local-artifact error."""


FIXED_CANDIDATES = (
    Candidate("candidate-a", "baseline-nano", "json_object", "GPT-4.1 nano (baseline)"),
    Candidate("candidate-b", "gemma-4-31b", "strict_json_schema", "Gemma 4 31B IT"),
    Candidate("candidate-c", "deepseek-v4-flash", "strict_json_schema", "DeepSeek V4 Flash"),
)


class ResponseShapeError(ValueError):
    """A parsed response cannot provide the product text contract."""


def _fail(message: str) -> None:
    raise ReviewPackError(message)


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _load_json(path: Path, *, root_name: str) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewPackError(f"missing {root_name}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewPackError(f"invalid JSON in {root_name}: {path}: {exc}") from exc
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# START_BLOCK: LOAD
def _load_input_records(path: Path) -> list[dict[str, Any]]:
    """Load and minimally validate the committed input collection."""
    value = _load_json(path, root_name="inputs")
    if not isinstance(value, dict) or not isinstance(value.get("inputs"), list):
        _fail(f"inputs root must contain an inputs array: {path}")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ordinal, item in enumerate(value["inputs"]):
        if not isinstance(item, dict):
            _fail(f"inputs[{ordinal}] must be an object")
        input_id = item.get("input_id")
        if not isinstance(input_id, str) or not input_id:
            _fail(f"inputs[{ordinal}] has no input_id")
        if input_id in seen:
            _fail(f"duplicate input_id: {input_id}")
        for field in ("target_date", "state", "day_tone", "facets", "polarities", "expected", "prompt"):
            if field not in item:
                _fail(f"input {input_id} misses {field}")
        if not isinstance(item["facets"], list) or not isinstance(item["polarities"], list):
            _fail(f"input {input_id} facets/polarities must be arrays")
        if not isinstance(item["expected"], dict):
            _fail(f"input {input_id} expected must be an object")
        seen.add(input_id)
        records.append(item)
    if not records:
        _fail("inputs collection is empty")
    return records


def _candidate_file(raw_dir: Path, candidate: Candidate, input_id: str) -> Path:
    return raw_dir / f"{candidate.model_key}__{candidate.arm}__{input_id}__r0.json"


def _person_first_name(prompt: Any) -> str | None:
    """Read firstName from the embedded prompt input when one is present."""
    if not isinstance(prompt, str):
        return None
    marker = "Вход:\n"
    start = prompt.find(marker)
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(prompt[start + len(marker) :])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("person"), dict):
        return None
    first_name = payload["person"].get("firstName")
    return first_name.strip() if isinstance(first_name, str) and first_name.strip() else None


# END_BLOCK: LOAD


# START_BLOCK: SELECT
def _record_sort_key(record: Mapping[str, Any]) -> tuple[str, str]:
    return (str(record.get("target_date", "")), str(record.get("input_id", "")))


def _coverage(record_group: Iterable[Mapping[str, Any]]) -> tuple[set[str], set[str]]:
    facets: set[str] = set()
    polarities: set[str] = set()
    for record in record_group:
        facets.update(str(value) for value in record.get("facets", []))
        polarities.update(str(value) for value in record.get("polarities", []))
    return facets, polarities


def _select_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select all convergence days and the lexicographically earliest max cover."""
    convergence = sorted(
        (record for record in records if record.get("state") == "convergence_today"),
        key=_record_sort_key,
    )
    quiet = sorted(
        (record for record in records if record.get("state") == "quiet_day"),
        key=_record_sort_key,
    )
    if len(convergence) != 3:
        _fail(f"expected exactly 3 convergence_today inputs, found {len(convergence)}")
    if len(quiet) < 7:
        _fail(f"need at least 7 quiet_day inputs, found {len(quiet)}")

    base_facets, base_polarities = _coverage(convergence)
    scored: list[tuple[int, int, tuple[str, ...], tuple[dict[str, Any], ...]]] = []
    for combination in itertools.combinations(quiet, 7):
        facets, polarities = _coverage(combination)
        scored.append(
            (
                len(base_facets | facets),
                len(base_polarities | polarities),
                tuple(str(record["input_id"]) for record in combination),
                combination,
            )
        )
    max_counts = max((item[0], item[1]) for item in scored)
    best = min(
        (item for item in scored if (item[0], item[1]) == max_counts),
        key=lambda item: item[2],
    )
    selected_quiet = list(best[3])
    selected = convergence + selected_quiet
    if len(selected) != 10:
        _fail(f"selection must contain 10 days, found {len(selected)}")
    return selected


def _shuffle_blocks(
    records: list[dict[str, Any]],
    *,
    run_id: str,
) -> list[tuple[dict[str, Any], Candidate]]:
    """Keep candidates adjacent per day while shuffling both axes."""
    seed = int.from_bytes(sha256(run_id.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    days = list(records)
    rng.shuffle(days)
    grouped: list[tuple[dict[str, Any], Candidate]] = []
    for record in days:
        candidates = list(FIXED_CANDIDATES)
        rng.shuffle(candidates)
        grouped.extend((record, candidate) for candidate in candidates)
    return grouped


# END_BLOCK: SELECT


# START_BLOCK: NORMALIZE
def _claim_texts(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ResponseShapeError("event claim must be an object")
    result: dict[str, str] = {}
    for claim in CLAIMS:
        field = value.get(claim)
        if not isinstance(field, dict) or not isinstance(field.get("text"), str):
            raise ResponseShapeError(f"missing text for {claim}")
        result[claim] = field["text"]
    return result


def _normalise_section(value: Any, section: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    result: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for event_id, item in value.items():
            # Some otherwise usable JSON responses put a null main_event
            # sentinel inside impulses; it carries no product text.
            if item is None:
                continue
            if not isinstance(event_id, str):
                raise ResponseShapeError(f"{section} id must be a string")
            result.append({"event_id": event_id, "claims": _claim_texts(item)})
        return result
    if isinstance(value, list):
        id_field = "groupId" if section == "convergences" else "eventId"
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get(id_field), str):
                raise ResponseShapeError(f"{section} array item misses {id_field}")
            result.append(
                {
                    "event_id": item[id_field],
                    "claims": _claim_texts(item),
                }
            )
        return result
    raise ResponseShapeError(f"{section} must be an object or array")


def _normalise_response(root: Any) -> dict[str, Any]:
    if not isinstance(root, dict):
        raise ResponseShapeError("response root must be an object")
    convergences = _normalise_section(root.get("convergences", {}), "convergences")
    impulses = _normalise_section(root.get("impulses", {}), "impulses")

    # Preserve useful event-shaped payloads from a valid JSON object even when
    # a model accidentally placed one at root; do not expose arbitrary fields.
    for event_id, item in root.items():
        if event_id in {"convergences", "impulses", "main_event"}:
            continue
        if isinstance(event_id, str) and event_id.startswith("evt_") and isinstance(item, dict):
            impulses.append({"event_id": event_id, "claims": _claim_texts(item)})
        elif isinstance(event_id, str) and event_id.startswith("cvg_") and isinstance(item, dict):
            convergences.append({"event_id": event_id, "claims": _claim_texts(item)})

    main_event = root.get("main_event")
    normalised_main = _claim_texts(main_event) if isinstance(main_event, dict) else None
    return {
        "convergences": convergences,
        "impulses": impulses,
        "main_event": normalised_main,
    }


def _read_response(
    raw_dir: Path,
    candidate: Candidate,
    record: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    path = _candidate_file(raw_dir, candidate, str(record["input_id"]))
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"missing: {path.name}"
    except json.JSONDecodeError:
        return None, f"invalid envelope JSON: {path.name}"
    if not isinstance(envelope, dict):
        return None, f"invalid envelope shape: {path.name}"
    if envelope.get("truncated") is True:
        return None, f"truncated=true: {path.name}"
    raw_response = envelope.get("response")
    try:
        parsed = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
    except json.JSONDecodeError:
        return None, f"invalid response JSON: {path.name}"
    try:
        return _normalise_response(parsed), None
    except ResponseShapeError as exc:
        return None, f"invalid response shape ({exc}): {path.name}"


def _iter_response_texts(response: Mapping[str, Any]) -> Iterable[str]:
    for section in ("convergences", "impulses"):
        for item in response.get(section, []):
            for claim in CLAIMS:
                yield str(item["claims"][claim])
    main_event = response.get("main_event")
    if isinstance(main_event, dict):
        for claim in CLAIMS:
            yield str(main_event[claim])


def _check_owner_name(record: Mapping[str, Any], response: Mapping[str, Any]) -> None:
    # firstName is currently absent from the committed inputs; keep this
    # future-facing check fail-closed before any text reaches review.html.
    first_name = _person_first_name(record.get("prompt"))
    if not first_name or first_name == NAME_MASK:
        return
    needle = first_name.casefold()
    for text in _iter_response_texts(response):
        if needle in text.casefold():
            _fail(f"owner firstName detected in block {record.get('input_id')}")


# END_BLOCK: NORMALIZE


# START_BLOCK: RENDER
def _expected_events(record: Mapping[str, Any]) -> list[dict[str, str]]:
    expected = record.get("expected")
    if not isinstance(expected, dict):
        return []
    events: list[dict[str, str]] = []
    for item in expected.get("convergences", []):
        if not isinstance(item, dict):
            continue
        event_id = item.get("eventId") or item.get("groupId") or "—"
        events.append(
            {
                "kind": "Конвергенция",
                "facet": str(item.get("facet", "—")),
                "polarity": str(item.get("polarity", "—")),
                "event_id": str(event_id),
            }
        )
    main_event = expected.get("main_event")
    if isinstance(main_event, dict):
        events.append(
            {
                "kind": "Главное событие",
                "facet": str(main_event.get("facet", "—")),
                "polarity": str(main_event.get("polarity", "—")),
                "event_id": str(main_event.get("eventId", "—")),
            }
        )
    for item in expected.get("impulses", []):
        if not isinstance(item, dict):
            continue
        events.append(
            {
                "kind": "Импульс",
                "facet": str(item.get("facet", "—")),
                "polarity": str(item.get("polarity", "—")),
                "event_id": str(item.get("eventId", "—")),
            }
        )
    return events


def _render_claims(claims: Mapping[str, str]) -> str:
    return "".join(
        "<div class=\"claim\"><strong>"
        + escape(CLAIM_LABELS[claim])
        + "</strong><p>"
        + escape(str(claims.get(claim, "")))
        + "</p></div>"
        for claim in CLAIMS
    )


def _render_section(section: str, items: list[Mapping[str, Any]]) -> str:
    body = []
    for item in items:
        event_id = escape(str(item.get("event_id", "—")))
        body.append(
            f'<article class="event" data-event-id="{event_id}">'
            f"<h4>{event_id}</h4>"
            f"{_render_claims(item.get('claims', {}))}</article>"
        )
    if not body:
        body.append('<p class="empty">Нет текстов</p>')
    return (
        f'<section class="narrative-section {escape(section)}">'
        f"<h3>{escape(SECTION_LABELS[section])}</h3>"
        + "".join(body)
        + "</section>"
    )


def _render_block(block: ReviewBlock) -> str:
    record = block.record
    facts = _expected_events(record)
    fact_rows = "".join(
        "<li><span>"
        + escape(item["kind"])
        + "</span> · facet="
        + escape(item["facet"])
        + " · polarity="
        + escape(item["polarity"])
        + " · eventId="
        + escape(item["event_id"])
        + "</li>"
        for item in facts
    )
    if not fact_rows:
        fact_rows = "<li>Нет expected events</li>"
    response = block.response
    title = f"{block.block_id} · {block.candidate.candidate}"
    return (
        f'<section class="block" id="{escape(block.block_id)}" '
        f'data-block-id="{escape(block.block_id)}" '
        f'data-candidate="{escape(block.candidate.candidate)}">'
        f"<h2>{escape(title)}</h2>"
        '<div class="facts"><h3>Факты дня</h3><dl>'
        f"<dt>Дата</dt><dd>{escape(str(record.get('target_date', '—')))}</dd>"
        f"<dt>Состояние</dt><dd>{escape(str(record.get('state', '—')))}</dd>"
        f"<dt>Тон дня</dt><dd>{escape(str(record.get('day_tone', '—')))}</dd>"
        f"<dt>Фасеты</dt><dd>{escape(', '.join(str(value) for value in record.get('facets', [])))}</dd>"
        f"<dt>Полярности</dt><dd>{escape(', '.join(str(value) for value in record.get('polarities', [])))}</dd>"
        "</dl><h4>Ожидаемые события</h4><ul>"
        + fact_rows
        + "</ul></div>"
        + _render_section("convergences", response.get("convergences", []))
        + _render_section("impulses", response.get("impulses", []))
        + (
            '<section class="narrative-section main-event"><h3>Главное событие</h3>'
            + _render_claims(response["main_event"])
            + "</section>"
            if isinstance(response.get("main_event"), dict)
            else ""
        )
        + "</section>"
    )


def _render_html(blocks: list[ReviewBlock], run_id: str) -> str:
    rendered = "\n".join(_render_block(block) for block in blocks)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Слепой review-пак · {escape(run_id)}</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, -apple-system, sans-serif; background: #f5f6f8; color: #1b1d22; }}
    body {{ margin: 0; padding: 24px; }}
    main {{ max-width: 1050px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; }}
    .intro {{ color: #555b66; margin-bottom: 24px; }}
    .block {{ background: #fff; border: 1px solid #dfe2e8; border-radius: 12px; padding: 20px; margin: 0 0 24px; box-shadow: 0 2px 8px #1b1d220d; }}
    .block h2 {{ margin: 0 0 16px; font-size: 1.15rem; }}
    .facts {{ background: #f7f8fa; border-radius: 8px; padding: 14px 16px; margin-bottom: 18px; }}
    .facts h3, .facts h4 {{ margin: 0 0 10px; }}
    .facts dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0 0 12px; }}
    .facts dt {{ font-weight: 650; }}
    .facts dd {{ margin: 0; }}
    .facts ul {{ margin: 0; padding-left: 22px; }}
    .narrative-section {{ border-top: 1px solid #e8eaf0; padding-top: 14px; margin-top: 14px; }}
    .narrative-section h3 {{ margin: 0 0 12px; font-size: 1rem; }}
    .event {{ border-left: 3px solid #b6c7ed; padding: 8px 0 8px 14px; margin: 0 0 14px; }}
    .event h4 {{ margin: 0 0 8px; font-size: .9rem; font-family: ui-monospace, monospace; overflow-wrap: anywhere; }}
    .claim {{ margin: 8px 0; }}
    .claim strong {{ display: block; color: #4c5566; font-size: .85rem; }}
    .claim p {{ white-space: pre-wrap; margin: 2px 0 0; line-height: 1.5; }}
    .empty {{ color: #777f8c; font-style: italic; }}
  </style>
</head>
<body>
<main>
  <h1>Слепой review-пак</h1>
  <p class="intro">{escape(run_id)} · 10 дней · 30 блоков. Метки кандидатов перемешаны внутри каждого дня.</p>
  {rendered}
</main>
</body>
</html>
"""


def _render_scorecard(blocks: list[ReviewBlock]) -> str:
    rows = "\n".join(
        f"| {block.block_id} | {block.candidate.candidate} |  |  |  |" for block in blocks
    )
    return """# Blind review scorecard

Оцени каждый блок независимо по красоте текста и соответствию фактам дня.

| block_id | candidate | beauty 1–5 | accuracy 1–5 | заметка |
|---|---|---:|---:|---|
""" + rows + "\n"


def _review_template(blocks: list[ReviewBlock], run_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "blocks": [
            {
                "block_id": block.block_id,
                "candidate": block.candidate.candidate,
                "beauty": None,
                "accuracy": None,
                "note": "",
            }
            for block in blocks
        ],
    }


def _review_key(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "candidates": {
            candidate.candidate: {
                "model_key": candidate.model_key,
                "arm": candidate.arm,
                "label": candidate.label,
            }
            for candidate in FIXED_CANDIDATES
        },
    }


def _forbidden_hits(value: str) -> list[str]:
    lowered = value.casefold()
    return [term for term in FORBIDDEN_BLIND_TERMS if term in lowered]


# END_BLOCK: RENDER


# START_BLOCK: REVEAL
def _score(value: Any, field: str, block_id: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 5:
        _fail(f"{field} for {block_id} must be null or a number from 1 to 5")
    return float(value)


def reveal_review(
    filled_review_path: Path,
    *,
    out_dir: Path,
) -> Path:
    """Join owner scores with the private key and write the revealed result."""
    review = _load_json(filled_review_path, root_name="filled review")
    key = _load_json(out_dir / "review-key.json", root_name="review key")
    if not isinstance(review, dict) or not isinstance(review.get("blocks"), list):
        _fail("filled review must contain a blocks array")
    if not isinstance(key, dict) or not isinstance(key.get("candidates"), dict):
        _fail("review-key.json must contain candidates")
    candidates = key["candidates"]
    details: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in review["blocks"]:
        if not isinstance(item, dict):
            _fail("filled review block must be an object")
        block_id = item.get("block_id")
        candidate_id = item.get("candidate")
        if not isinstance(block_id, str) or not isinstance(candidate_id, str):
            _fail("filled review block misses block_id or candidate")
        if block_id in seen:
            _fail(f"duplicate review block: {block_id}")
        mapping = candidates.get(candidate_id)
        if not isinstance(mapping, dict):
            _fail(f"unknown candidate in filled review: {candidate_id}")
        note = item.get("note", "")
        if not isinstance(note, str):
            _fail(f"note for {block_id} must be a string")
        details.append(
            {
                "block_id": block_id,
                "candidate": candidate_id,
                "model_key": mapping.get("model_key"),
                "arm": mapping.get("arm"),
                "label": mapping.get("label"),
                "beauty": _score(item.get("beauty"), "beauty", block_id),
                "accuracy": _score(item.get("accuracy"), "accuracy", block_id),
                "note": note,
            }
        )
        seen.add(block_id)

    final_table: list[dict[str, Any]] = []
    for candidate_id, mapping in candidates.items():
        model_key = mapping.get("model_key")
        own = [item for item in details if item["candidate"] == candidate_id]
        beauty = [item["beauty"] for item in own if item["beauty"] is not None]
        accuracy = [item["accuracy"] for item in own if item["accuracy"] is not None]
        final_table.append(
            {
                "candidate": candidate_id,
                "model_key": model_key,
                "arm": mapping.get("arm"),
                "label": mapping.get("label"),
                "beauty_count": len(beauty),
                "accuracy_count": len(accuracy),
                "mean_beauty": sum(beauty) / len(beauty) if beauty else None,
                "mean_accuracy": sum(accuracy) / len(accuracy) if accuracy else None,
            }
        )
    result = {
        "schema_version": 1,
        "run_id": review.get("run_id", key.get("run_id")),
        "means_by_model": final_table,
        "blocks": details,
        "final_table": final_table,
    }
    output = out_dir / "review-revealed.json"
    _write_json(output, result)
    print(f"review_revealed: wrote={output}")
    for row in final_table:
        print(
            "model="
            + str(row["model_key"])
            + " mean_beauty="
            + ("—" if row["mean_beauty"] is None else f"{row['mean_beauty']:.3f}")
            + " mean_accuracy="
            + ("—" if row["mean_accuracy"] is None else f"{row['mean_accuracy']:.3f}")
        )
    return output


# END_BLOCK: REVEAL


# START_BLOCK: CLI
def generate_review_pack(
    *,
    raw_dir: Path,
    inputs_path: Path,
    out_dir: Path,
    run_id: str,
) -> list[Path]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK.generate_review_pack
    # purpose: Build the deterministic anonymous pack from local r0 responses.
    # inputs: raw_dir, inputs_path, out_dir, and run_id; all are local paths/IDs.
    # returns: Four generated artifact paths in the result directory.
    # side_effects: Reads raw/input files and writes review HTML/Markdown/JSON;
    #   no database, network, or production-code side effects.
    # emitted_logs: block/skip/output/anonymity status lines without raw text.
    # error_behavior: Raises ReviewPackError on missing, malformed, truncated,
    #   or privacy-unsafe inputs before writing the pack.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK.generate_review_pack
    records = _select_records(_load_input_records(inputs_path))
    grouped = _shuffle_blocks(records, run_id=run_id)
    blocks: list[ReviewBlock] = []
    skips: list[str] = []
    for ordinal, (record, candidate) in enumerate(grouped, start=1):
        response, reason = _read_response(raw_dir, candidate, record)
        if reason is not None or response is None:
            skips.append(f"{candidate.candidate}/{record['input_id']}: {reason}")
            continue
        _check_owner_name(record, response)
        blocks.append(
            ReviewBlock(
                block_id=f"blk-{ordinal:02d}",
                candidate=candidate,
                record=record,
                response=response,
            )
        )
    print(f"review_pack: blocks={len(blocks)} skipped={len(skips)}")
    for item in skips:
        print(f"skip: {item}")
    if skips:
        _fail("review pack stopped because one or more response files were skipped")
    if len(blocks) != 30:
        _fail(f"review pack must contain 30 blocks, found {len(blocks)}")

    html = _render_html(blocks, run_id)
    hits = _forbidden_hits(html)
    if hits:
        _fail("review.html anonymity check failed: " + ", ".join(hits))
    output_paths = [
        out_dir / "review.html",
        out_dir / "scorecard.md",
        out_dir / "review-key.json",
        out_dir / "review.json",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    output_paths[0].write_text(html, encoding="utf-8")
    output_paths[1].write_text(_render_scorecard(blocks), encoding="utf-8")
    _write_json(output_paths[2], _review_key(run_id))
    _write_json(output_paths[3], _review_template(blocks, run_id))
    print("anonymity_grep: PASS forbidden=gemma,deepseek,nano,openai,qwen")
    print(f"review_pack: PASS blocks={len(blocks)} skipped=0")
    for path in output_paths:
        print(f"output: {path}")
    return output_paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or reveal a local narrative blind review pack")
    parser.add_argument("--run-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--inputs", default=str(DEFAULT_INPUTS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--reveal", default=None, help="filled review.json to reveal through review-key.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK.main
    # purpose: Dispatch local generation or score reveal without network calls.
    # inputs: CLI arguments for raw/input/result paths and optional --reveal.
    # returns: 0 on a complete local operation, 1 on a contract/privacy error.
    # side_effects: Delegates only to local artifact reads/writes.
    # emitted_logs: Safe status and artifact path lines.
    # error_behavior: Prints a concise error and returns non-zero.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-EVAL-REVIEW-PACK.main
    args = _build_parser().parse_args(argv)
    out_dir = _resolve_path(args.out_dir)
    run_id = str(args.run_id or out_dir.name or DEFAULT_RUN_ID)
    try:
        if args.reveal:
            reveal_review(_resolve_path(args.reveal), out_dir=out_dir)
        else:
            generate_review_pack(
                raw_dir=_resolve_path(args.run_dir),
                inputs_path=_resolve_path(args.inputs),
                out_dir=out_dir,
                run_id=run_id,
            )
    except ReviewPackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


# END_BLOCK: CLI


if __name__ == "__main__":
    raise SystemExit(main())
