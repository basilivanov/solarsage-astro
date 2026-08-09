#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: NARRATIVE_MODEL_EVAL — safe two-arm OpenRouter model evaluation
# ROLE: Collect real Today inputs read-only, validate the paid-run plan, score
#       raw narrative responses, and keep committed artifacts PII-safe.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-MODEL-EVAL
# purpose: Build and score a reproducible Today narrative v5 model comparison
#   without allowing selftest or validate to make paid provider calls.
# owns:
#   - scripts/narrative_model_eval.py
# inputs: immutable task artifacts, dev profile read-only, deterministic Today
#   pipeline, prompt builder, sanitizer, and optional OpenRouter responses.
# outputs: task inputs, ignored raw run traces, compact metrics, and CLI plans.
# dependencies: Python stdlib, SQLAlchemy, and read-only SolarSage app imports.
# side_effects: validate reads the dev DB and sidecar but never writes them;
#   run writes only .eval-runs raw traces and evals/results compact artifacts.
# emitted_logs: none; stdout contains counts, hashes, prices, and error classes only.
# invariants: five pinned models, two response arms, two repeats, concurrency two,
#   hard budget guard $0.90, full provider usage in ignored raw files, no credentials in artifacts, and no OpenRouter call
#   from --selftest or validate.
# failure_policy: invalid task/input/config exits non-zero; provider failures are
#   recorded by class; strict 400/404 is strict_unsupported without retry.
# END_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-MODEL-EVAL

# START_MODULE_MAP: M-SCRIPTS-NARRATIVE-MODEL-EVAL
# public_entrypoints:
#   - main
#   - run_selftest
#   - validate_task
#   - score_run
# semantic_blocks:
#   - TASK: immutable TOML/Markdown/JSON task loading and validation.
#   - INPUTS: read-only profile collection and in-memory deterministic snapshots.
#   - PROMPTS: production JSON-object body and strict array/schema arm.
#   - SCORING: response normalization, sanitizer metrics, repeatability, and cost.
#   - RUN: explicit paid OpenRouter execution with retry and budget guard.
#   - CLI: selftest, validate, run, and score commands.
# owned_tests: --selftest and validate command gates.
# END_MODULE_MAP: M-SCRIPTS-NARRATIVE-MODEL-EVAL

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
import tomllib
from types import SimpleNamespace
from typing import Any, Iterable, Mapping
from uuid import UUID


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "apps" / "api"
DEFAULT_TASK_DIR = REPO_ROOT / "evals" / "tasks" / "today-narrative-v5-models"
RAW_ROOT = REPO_ROOT / ".eval-runs" / "narrative-model-eval-v1"
RESULTS_ROOT = REPO_ROOT / "evals" / "results"
TASK_ID = "narrative-model-eval-v1"
PROMPT_VERSION = "today-narrative-v5"
OWNER_USER_ID = UUID("eb3876be-e1b4-43d6-b887-1f8554e33150")
CANDIDATE_START = date(2026, 8, 9)
CANDIDATE_END = date(2026, 9, 25)
MAX_INPUTS = 14
MAX_MODELS = 5
REPEATS = 2
CONCURRENCY = 2
TIMEOUT_SECONDS = 60.0
MAX_BUDGET_USD = 1.60
EXPECTED_COMPLETION_TOKENS = 400
MONTHLY_NARRATIVE_CALLS = 3000
NAME_MASK = "ИМЯ"
ARMS = ("json_object", "strict_json_schema")
CLAIMS = ("summary", "meaning", "action")
STAMP_TERMS = (
    "в сфере",
    "может усилиться",
    "наблюдается",
    "играет важную роль",
    "указывает на важность",
    "возможна активность",
    "междуличностные связи",
    "жизненные выборы",
    "позитивные перемены",
)
TIME_PATTERNS = (
    re.compile(r"(?<!\d)(?:[01]\d|2[0-3]):[0-5]\d(?!\d)"),
    re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)"),
    re.compile(r"(?<!\d)\d{1,2}[./-]\d{1,2}[./-]\d{2,4}(?!\d)"),
    re.compile(r"\bс\s+(?:\d{1,2}:\d{2}|\d{1,2}[./-]\d{1,2})\s+по\s+", re.IGNORECASE),
)
TOKEN_PATTERN = re.compile(r"[\wёа-яА-ЯЁ-]+", re.UNICODE)


class EvalError(RuntimeError):
    """A repository-owned eval contract or input error."""


def _ensure_app_paths() -> None:
    for path in (APP_ROOT, REPO_ROOT / "packages" / "py-contracts"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


@dataclass(frozen=True)
class ModelConfig:
    key: str
    label: str
    model: str
    pricing_key: str
    max_tokens: int = 2000
    extra_body: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceConfig:
    key: str
    model: str
    input_per_million: float
    output_per_million: float


@dataclass(frozen=True)
class TaskBundle:
    directory: Path
    models: tuple[ModelConfig, ...]
    prices: dict[str, PriceConfig]
    inputs: dict[str, Any] | None
    all_models: tuple[ModelConfig, ...]


@dataclass(frozen=True)
class ResponseEnvelope:
    model_key: str
    arm: str
    input_id: str
    repeat: int
    raw: str
    usage: dict[str, Any]
    latency_ms: int
    retries: int
    error_class: str | None = None
    max_tokens: int = 2000
    truncated: bool | None = None


def _fail(message: str) -> None:
    raise EvalError(message)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise EvalError(f"missing task artifact: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise EvalError(f"invalid TOML: {path}: {exc}") from exc
    if not isinstance(value, dict):
        _fail(f"TOML root must be a table: {path}")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvalError(f"missing JSON artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvalError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        _fail(f"JSON root must be an object: {path}")
    return value


def _resolve_task_dir(value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(REPO_ROOT / "evals" / "tasks")
    except ValueError as exc:
        raise EvalError("task must live under evals/tasks") from exc
    if not candidate.is_dir():
        _fail(f"task directory not found: {candidate}")
    return candidate


# START_BLOCK: TASK
def _parse_model_filter(value: str | None) -> tuple[str, ...] | None:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._parse_model_filter
    # purpose: Parse the comma-separated CLI model selection without accepting an empty or duplicate key.
    # inputs: value — optional `--models key1,key2` string.
    # returns: ordered unique model keys, or None when no filter was requested.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed values raise EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._parse_model_filter
    if value is None:
        return None
    keys = tuple(part.strip() for part in value.split(",") if part.strip())
    if not keys or len(keys) != len(set(keys)):
        _fail("--models must contain unique comma-separated model keys")
    return keys


def _load_bundle(
    task_dir: str | Path,
    *,
    require_inputs: bool = False,
    model_filter: str | None = None,
) -> TaskBundle:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._load_bundle
    # purpose: Load and validate the immutable narrative task artifacts.
    # inputs: task directory containing task.md, models.toml, pricing snapshot, optional inputs.json, and model filter.
    # returns: validated TaskBundle with all five pinned models plus the selected CLI subset.
    # side_effects: filesystem reads only.
    # emitted_logs: none.
    # error_behavior: raises EvalError for missing, malformed, mutable, or mismatched artifacts.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._load_bundle
    directory = _resolve_task_dir(task_dir)
    required = ("task.md", "models.toml", "pricing-2026-08-09.toml", "rubric.md")
    for filename in required:
        if not (directory / filename).is_file():
            _fail(f"missing task artifact: {directory / filename}")
    model_doc = _read_toml(directory / "models.toml")
    price_doc = _read_toml(directory / "pricing-2026-08-09.toml")
    if model_doc.get("schema_version") != 1 or model_doc.get("task_id") != TASK_ID:
        _fail("models.toml schema/task mismatch")
    for field in ("base_sha", "tree_sha"):
        if not isinstance(model_doc.get(field), str) or not re.fullmatch(r"[0-9a-f]{40}", model_doc[field]):
            _fail(f"models.toml must pin a 40-character {field}")
    raw_models = model_doc.get("models")
    raw_prices = price_doc.get("prices")
    if not isinstance(raw_models, dict) or not isinstance(raw_prices, dict):
        _fail("models.toml must contain [models.*] and pricing must contain [prices.*]")
    models: list[ModelConfig] = []
    for key, raw in raw_models.items():
        if not isinstance(key, str) or not isinstance(raw, dict):
            _fail("invalid model table")
        fields = (raw.get("label"), raw.get("model"), raw.get("pricing_key"))
        if not all(isinstance(field, str) and field.strip() for field in fields):
            _fail(f"invalid model entry: {key}")
        max_tokens = raw.get("max_tokens", 2000)
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            _fail(f"invalid max_tokens for model: {key}")
        extra_body = raw.get("extra_body", {})
        if extra_body is None:
            extra_body = {}
        if not isinstance(extra_body, dict) or any(not isinstance(name, str) for name in extra_body):
            _fail(f"invalid extra_body for model: {key}")
        reserved = {"model", "messages", "max_tokens", "response_format", "provider"}
        if reserved & set(extra_body):
            _fail(f"extra_body overrides reserved request fields for model: {key}")
        try:
            json.dumps(extra_body)
        except (TypeError, ValueError) as exc:
            raise EvalError(f"extra_body is not JSON-compatible for model: {key}") from exc
        models.append(ModelConfig(key, fields[0], fields[1], fields[2], max_tokens, dict(extra_body)))
    models.sort(key=lambda item: item.key)
    if len(models) != MAX_MODELS:
        _fail(f"expected exactly {MAX_MODELS} models, got {len(models)}")
    prices: dict[str, PriceConfig] = {}
    for key, raw in raw_prices.items():
        if not isinstance(key, str) or not isinstance(raw, dict):
            _fail("invalid pricing table")
        model = raw.get("model")
        input_rate = raw.get("input_per_million")
        output_rate = raw.get("output_per_million")
        if (
            not isinstance(model, str)
            or isinstance(input_rate, bool)
            or not isinstance(input_rate, (int, float))
            or isinstance(output_rate, bool)
            or not isinstance(output_rate, (int, float))
            or input_rate < 0
            or output_rate < 0
        ):
            _fail(f"invalid price entry: {key}")
        prices[key] = PriceConfig(key, model, float(input_rate), float(output_rate))
    for model in models:
        price = prices.get(model.pricing_key)
        if price is None or price.model != model.model:
            _fail(f"pricing mismatch for model {model.key}")
    all_models = tuple(models)
    selected_keys = _parse_model_filter(model_filter)
    if selected_keys is not None:
        available = {model.key: model for model in models}
        unknown = [key for key in selected_keys if key not in available]
        if unknown:
            _fail("unknown model key(s): " + ", ".join(unknown))
        models = [available[key] for key in selected_keys]
    inputs_path = directory / "inputs.json"
    inputs = _read_json(inputs_path) if inputs_path.exists() else None
    if require_inputs and inputs is None:
        _fail(f"inputs.json is required: {inputs_path}")
    if inputs is not None:
        _validate_inputs_document(inputs)
    return TaskBundle(directory, tuple(models), prices, inputs, all_models)


def _validate_inputs_document(document: Mapping[str, Any]) -> None:
    if document.get("schema_version") != 1 or document.get("task_id") != TASK_ID:
        _fail("inputs.json schema/task mismatch")
    if document.get("prompt_version") != PROMPT_VERSION:
        _fail("inputs.json prompt version mismatch")
    profile = document.get("profile")
    if (
        not isinstance(profile, dict)
        or profile.get("user_id") != str(OWNER_USER_ID)
        or profile.get("first_name") != NAME_MASK
    ):
        _fail("inputs.json profile name must be masked as ИМЯ")
    window = document.get("candidate_window")
    if (
        not isinstance(window, dict)
        or window.get("start") != CANDIDATE_START.isoformat()
        or window.get("end") != CANDIDATE_END.isoformat()
    ):
        _fail("inputs.json candidate window mismatch")
    records = document.get("inputs")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_INPUTS:
        _fail(f"inputs.json must contain 1..{MAX_INPUTS} inputs")
    coverage = document.get("coverage")
    if not isinstance(coverage, dict):
        _fail("inputs.json coverage must be an object")
    input_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _fail(f"inputs[{index}] must be an object")
        input_id = record.get("input_id")
        prompt = record.get("prompt")
        expected = record.get("expected")
        if not isinstance(input_id, str) or input_id in input_ids:
            _fail(f"inputs[{index}].input_id must be unique")
        if not isinstance(prompt, str) or not prompt:
            _fail(f"inputs[{index}].prompt is required")
        if not isinstance(expected, dict):
            _fail(f"inputs[{index}].expected is required")
        if "canonical_input_json" in record or "profile_payload" in record:
            _fail("inputs.json must not contain raw canonical/profile payloads")
        input_ids.add(input_id)


# END_BLOCK: TASK


# START_BLOCK: SCHEMA
def strict_response_schema() -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.strict_response_schema
    # purpose: Return the immutable array-based Structured Outputs schema for arm B.
    # inputs: none.
    # returns: a fresh JSON-schema dictionary with no dynamic property names.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.strict_response_schema
    claim = {
        "anyOf": [
            {"type": "null"},
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "sourceEventIds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "sourceEventIds"],
            },
        ]
    }
    claim_ref = {"$ref": "#/$defs/claim"}
    block = {
        "type": "object",
        "additionalProperties": False,
        "properties": {name: claim_ref for name in CLAIMS},
        "required": list(CLAIMS),
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "convergences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "groupId": {"type": "string"},
                        **{name: claim_ref for name in CLAIMS},
                    },
                    "required": ["groupId", *CLAIMS],
                },
            },
            "main_event": {"anyOf": [{"$ref": "#/$defs/block"}, {"type": "null"}]},
            "impulses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "eventId": {"type": "string"},
                        **{name: claim_ref for name in CLAIMS},
                    },
                    "required": ["eventId", *CLAIMS],
                },
            },
        },
        "required": ["convergences", "main_event", "impulses"],
        "$defs": {"claim": claim, "block": block},
    }


def _strict_prompt(prompt: str, expected: Mapping[str, Any]) -> str:
    marker = "\nТочный JSON-шаблон ответа для этого snapshot:\n"
    suffix_marker = "\nЗамени только пустые значения text на текст"
    if marker not in prompt or suffix_marker not in prompt:
        _fail("production prompt template markers are missing")
    prefix, rest = prompt.split(marker, 1)
    _, suffix = rest.split(suffix_marker, 1)
    template = {
        "convergences": [
            {
                "groupId": group["groupId"],
                **{name: {"text": "", "sourceEventIds": list(group["sourceEventIds"])} for name in CLAIMS},
            }
            for group in expected.get("convergences", [])
        ],
        "main_event": (
            None
            if expected.get("main_event") is None
            else {
                name: {"text": "", "sourceEventIds": list(expected["main_event"]["sourceEventIds"])}
                for name in CLAIMS
            }
        ),
        "impulses": [
            {
                "eventId": impulse["eventId"],
                **{name: {"text": "", "sourceEventIds": list(impulse["sourceEventIds"])} for name in CLAIMS},
            }
            for impulse in expected.get("impulses", [])
        ],
    }
    strict_tail = (
        "\nДля плеча strict json_schema сохрани массивы: в convergences используй "
        "groupId, в impulses — eventId. Не превращай массивы в словари. "
        "Замени только пустые значения text на текст и верни этот JSON. "
        "Сохрани все ключи, идентификаторы и массивы sourceEventIds; не добавляй и не удаляй поля."
        + suffix
    )
    return prefix + marker + json.dumps(template, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + strict_tail


# END_BLOCK: SCHEMA


# START_BLOCK: INPUTS
def _safe_json(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _age_at(birthday: date, target_date: date) -> int:
    return target_date.year - birthday.year - ((target_date.month, target_date.day) < (birthday.month, birthday.day))


def _profile_namespace(row: object) -> SimpleNamespace:
    fields = (
        "birthday",
        "birth_time",
        "birth_time_mode",
        "birth_time_bucket",
        "birth_lat",
        "birth_lon",
        "birth_tz",
        "current_lat",
        "current_lon",
        "current_tz",
        "first_name",
    )
    return SimpleNamespace(**{field: getattr(row, field, None) for field in fields})


async def _load_owner_profile() -> SimpleNamespace:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._load_owner_profile
    # purpose: Read the owner's direct profile fields from the dev DB without mutation.
    # inputs: fixed owner UUID and DATABASE_URL-backed app SessionLocal.
    # returns: detached namespace with only fields consumed by the deterministic runtime.
    # side_effects: one SELECT transaction; no commit, flush, update, or delete.
    # emitted_logs: none.
    # error_behavior: missing/incomplete profile raises EvalError without printing row values.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._load_owner_profile
    _ensure_app_paths()
    from sqlalchemy import select
    from app.db.models import UserProfile
    from app.db.session import SessionLocal

    async with SessionLocal() as session:
        result = await session.execute(select(UserProfile).where(UserProfile.user_id == OWNER_USER_ID))
        row = result.scalar_one_or_none()
        if row is None:
            _fail("owner profile not found in dev DB")
        profile = _profile_namespace(row)
    required = ("birthday", "birth_lat", "birth_lon", "birth_tz", "birth_time_mode")
    if any(getattr(profile, field, None) is None for field in required):
        _fail("owner profile is incomplete for Today calculation")
    return profile


def _prompt_input(prompt: str) -> dict[str, Any]:
    start_marker = "\nВход:\n"
    end_marker = "\nТочный JSON-шаблон ответа для этого snapshot:\n"
    if start_marker not in prompt or end_marker not in prompt:
        _fail("prompt input markers are missing")
    raw = prompt.split(start_marker, 1)[1].split(end_marker, 1)[0]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EvalError("production prompt input is not JSON") from exc
    if not isinstance(value, dict):
        _fail("production prompt input must be an object")
    return value


def _lexicon(event_or_events: Iterable[Mapping[str, Any]]) -> list[str]:
    return sorted({word for event in event_or_events for word in event.get("lexicon", []) if isinstance(word, str)})


def _expected_from_prompt(prompt: str, document: object) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._expected_from_prompt
    # purpose: Project the deterministic snapshot into safe response IDs and grounding metadata.
    # inputs: v5 prompt and in-memory snapshot document.
    # returns: expected keyed blocks, source IDs, facets, polarities, and lexicons.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed deterministic result raises EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._expected_from_prompt
    prompt_input = _prompt_input(prompt)
    result_json = getattr(document, "deterministic_result_json", None)
    if not isinstance(result_json, dict) or not isinstance(result_json.get("selected"), dict):
        _fail("snapshot deterministic result is malformed")
    selected = result_json["selected"]
    prompt_groups = {item.get("groupId"): item for item in prompt_input.get("convergences", []) if isinstance(item, dict)}
    groups: list[dict[str, Any]] = []
    for group in selected.get("convergences", []):
        if not isinstance(group, dict):
            _fail("selected convergence is malformed")
        group_id = group.get("group_id")
        prompt_group = prompt_groups.get(group_id, {})
        groups.append(
            {
                "groupId": group_id,
                "sourceEventIds": list(group.get("evidence_event_ids", [])),
                "sphere": group.get("sphere"),
                "facet": group.get("facet"),
                "polarity": group.get("polarity"),
                "lexicon": _lexicon(prompt_group.get("evidence", [])),
                "evidence_level": group.get("evidence_level"),
            }
        )
    main = selected.get("main_event")
    prompt_main = prompt_input.get("mainEvent")
    main_expected = None
    if isinstance(main, dict):
        main_expected = {
            "eventId": main.get("event_id"),
            "sourceEventIds": [main.get("event_id")],
            "sphere": main.get("sphere"),
            "facet": main.get("facet"),
            "polarity": main.get("polarity"),
            "lexicon": _lexicon([prompt_main]) if isinstance(prompt_main, dict) else [],
        }
    impulses: list[dict[str, Any]] = []
    prompt_impulses = {
        item.get("eventId"): item
        for item in prompt_input.get("impulses", [])
        if isinstance(item, dict)
    }
    for event in selected.get("impulses", []):
        if not isinstance(event, dict):
            _fail("selected impulse is malformed")
        event_id = event.get("event_id")
        prompt_event = prompt_impulses.get(event_id, {})
        impulses.append(
            {
                "eventId": event_id,
                "sourceEventIds": [event_id],
                "sphere": event.get("sphere"),
                "facet": event.get("facet"),
                "polarity": event.get("polarity"),
                "lexicon": _lexicon([prompt_event]),
            }
        )
    return {"convergences": groups, "main_event": main_expected, "impulses": impulses}


def _mask_prompt(prompt: str, first_name: str | None) -> str:
    if not first_name or not first_name.strip() or first_name.strip() == NAME_MASK:
        return prompt
    return prompt.replace(first_name.strip(), NAME_MASK)


def _coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    states: defaultdict[str, int] = defaultdict(int)
    polarities: set[str] = set()
    facets: set[str] = set()
    evidence_levels: set[str] = set()
    for record in records:
        states[str(record["state"])] += 1
        polarities.update(record.get("polarities", []))
        facets.update(facet for facet in record.get("facets", []) if facet)
        evidence_levels.update(record.get("evidence_levels", []))
    return {
        "state_counts": dict(sorted(states.items())),
        "polarities": sorted(polarities),
        "facets": sorted(facets),
        "facet_count": len(facets),
        "evidence_levels": sorted(evidence_levels),
        "has_hero": "high" in evidence_levels,
        "has_medium": "medium" in evidence_levels,
    }


def _coverage_gaps(coverage: Mapping[str, Any]) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._coverage_gaps
    # purpose: Report unmet hard input-coverage targets without fabricating records.
    # inputs: coverage — safe aggregate metadata from inputs.json.
    # returns: stable human-readable gap labels.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed aggregate fields are reported as gaps.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._coverage_gaps
    state_counts = coverage.get("state_counts", {})
    polarities = set(coverage.get("polarities", []))
    gaps: list[str] = []
    if not isinstance(state_counts, dict) or state_counts.get("convergence_today", 0) < 3:
        gaps.append("convergence_today>=3")
    if not isinstance(state_counts, dict) or state_counts.get("quiet_day", 0) < 3:
        gaps.append("quiet_day>=3")
    missing_polarities = {"supportive", "tense", "mixed"} - polarities
    if missing_polarities:
        gaps.append("polarities=" + ",".join(sorted(missing_polarities)))
    if coverage.get("facet_count", 0) < 8:
        gaps.append("facet_count>=8")
    if not coverage.get("has_hero"):
        gaps.append("hero_group")
    if not coverage.get("has_medium"):
        gaps.append("medium_group")
    return gaps


def _select_coverage_records(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    remaining = list(candidates)
    while remaining and len(selected) < MAX_INPUTS:
        current = _coverage(selected)

        def gain(record: dict[str, Any]) -> tuple[int, str]:
            score = 0
            state = record["state"]
            if state == "convergence_today" and current["state_counts"].get(state, 0) < 3:
                score += 20
            if state == "quiet_day" and current["state_counts"].get(state, 0) < 3:
                score += 20
            score += 8 * len(set(record.get("polarities", [])) - set(current["polarities"]))
            score += 4 * len(set(record.get("facets", [])) - set(current["facets"]))
            if "high" in record.get("evidence_levels", []) and not current["has_hero"]:
                score += 8
            if "medium" in record.get("evidence_levels", []) and not current["has_medium"]:
                score += 8
            return score, str(record["target_date"])

        best = max(remaining, key=gain)
        selected.append(best)
        remaining.remove(best)
    return sorted(selected, key=lambda record: record["target_date"])


async def _collect_inputs(task_dir: Path) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._collect_inputs
    # purpose: Collect candidate Today dates and write a masked immutable inputs.json.
    # inputs: task directory; fixed owner UUID; dev DATABASE_URL and sidecar settings.
    # returns: safe inputs document with coverage and input hashes.
    # side_effects: read-only DB SELECTs and in-memory sidecar calculations; writes only the new task inputs.json.
    # emitted_logs: none; failures expose dates and exception classes, never profile values.
    # error_behavior: unavailable dates are skipped; no usable coverage raises EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._collect_inputs
    _ensure_app_paths()
    from app.services.today_convergence_runtime import TodayConvergenceCalculationBuilt, calculate_today_convergence
    from app.services.today_convergence_snapshot import build_today_convergence_snapshot_document
    from app.services.today_narrative_service import TodayNarrativePerson, build_today_narrative_prompt

    profile = await _load_owner_profile()
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    current = CANDIDATE_START
    while current <= CANDIDATE_END:
        try:
            calculation = await calculate_today_convergence(profile, current)
            if not isinstance(calculation, TodayConvergenceCalculationBuilt):
                skipped.append({"target_date": current.isoformat(), "reason": "calculation_unavailable"})
                current += timedelta(days=1)
                continue
            document = build_today_convergence_snapshot_document(profile, calculation)
            age = _age_at(profile.birthday, current)
            person = TodayNarrativePerson(first_name=getattr(profile, "first_name", None), age=age)
            prompt = build_today_narrative_prompt(document, prompt_version=PROMPT_VERSION, person=person)
            expected = _expected_from_prompt(prompt, document)
            facets = sorted(
                {
                    item.get("facet")
                    for item in [*expected["convergences"], *( [expected["main_event"]] if expected["main_event"] else []), *expected["impulses"]]
                    if isinstance(item, dict) and item.get("facet")
                }
            )
            polarities = sorted(
                {
                    item.get("polarity")
                    for item in [*expected["convergences"], *( [expected["main_event"]] if expected["main_event"] else []), *expected["impulses"]]
                    if isinstance(item, dict) and item.get("polarity")
                }
            )
            evidence_levels = sorted(
                {item.get("evidence_level") for item in expected["convergences"] if item.get("evidence_level")}
            )
            safe_prompt = _mask_prompt(prompt, getattr(profile, "first_name", None))
            candidates.append(
                {
                    "input_id": f"narrative-{current.strftime('%Y%m%d')}",
                    "target_date": current.isoformat(),
                    "input_hash": document.input_hash,
                    "prompt_sha256": hashlib.sha256(safe_prompt.encode("utf-8")).hexdigest(),
                    "state": calculation.state,
                    "day_tone": calculation.pipeline.tone.day_tone,
                    "facets": facets,
                    "polarities": polarities,
                    "evidence_levels": evidence_levels,
                    "prompt": safe_prompt,
                    "name_token": NAME_MASK,
                    "expected": expected,
                }
            )
        except Exception as exc:  # collection should report a safe class and continue to the next date
            skipped.append({"target_date": current.isoformat(), "reason": type(exc).__name__})
        current += timedelta(days=1)
    selected = _select_coverage_records(candidates)
    if not selected:
        _fail("no usable Today inputs collected; check dev DB and sidecar availability")
    for index, record in enumerate(selected, start=1):
        record["ordinal"] = index
    coverage = _coverage(selected)
    document = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "prompt_version": PROMPT_VERSION,
        "profile": {"user_id": str(OWNER_USER_ID), "first_name": NAME_MASK},
        "candidate_window": {"start": CANDIDATE_START.isoformat(), "end": CANDIDATE_END.isoformat()},
        "collection": {"candidate_count": len(candidates), "skipped": skipped},
        "coverage": coverage,
        "inputs": selected,
    }
    inputs_path = task_dir / "inputs.json"
    inputs_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def _load_or_collect(task: TaskBundle) -> dict[str, Any]:
    if task.inputs is not None:
        return task.inputs
    return asyncio.run(_collect_inputs(task.directory))


# END_BLOCK: INPUTS


# START_BLOCK: SCORING
def _expected_ids(expected: Mapping[str, Any]) -> tuple[set[str], str | None, set[str]]:
    groups = {item["groupId"] for item in expected.get("convergences", [])}
    main = expected.get("main_event")
    main_id = main.get("eventId") if isinstance(main, dict) else None
    impulses = {item["eventId"] for item in expected.get("impulses", [])}
    return groups, main_id, impulses


def _claim_shape(value: Any) -> bool:
    if value is None:
        return True
    return (
        isinstance(value, dict)
        and set(value) == {"text", "sourceEventIds"}
        and isinstance(value["text"], str)
        and isinstance(value["sourceEventIds"], list)
        and all(isinstance(item, str) for item in value["sourceEventIds"])
    )


def _block_shape(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == set(CLAIMS) and all(_claim_shape(value[name]) for name in CLAIMS)


def _normalize_response(raw: str, arm: str, expected: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "empty_response"
    stripped = raw.strip()
    if stripped.startswith("```") or stripped.endswith("```"):
        return None, "markdown_fence"
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        return None, "json_parse_error"
    if not isinstance(value, dict):
        return None, "root_not_object"
    group_ids, main_id, impulse_ids = _expected_ids(expected)
    if arm == "json_object":
        if set(value) != {"convergences", "main_event", "impulses"}:
            return None, "root_shape"
        convergence_value = value.get("convergences")
        impulse_value = value.get("impulses")
        if not isinstance(convergence_value, dict) or not isinstance(impulse_value, dict):
            return None, "keyed_shape"
        if set(convergence_value) != group_ids or set(impulse_value) != impulse_ids:
            return None, "block_ids"
        if (main_id is None) != (value.get("main_event") is None):
            return None, "main_event_shape"
        normalized = {
            "convergences": convergence_value,
            "main_event": value.get("main_event"),
            "impulses": impulse_value,
        }
    elif arm == "strict_json_schema":
        if set(value) != {"convergences", "main_event", "impulses"}:
            return None, "root_shape"
        convergence_value = value.get("convergences")
        impulse_value = value.get("impulses")
        if not isinstance(convergence_value, list) or not isinstance(impulse_value, list):
            return None, "array_shape"
        seen_groups: list[str] = []
        convergence_map: dict[str, Any] = {}
        for item in convergence_value:
            if not isinstance(item, dict) or set(item) != {"groupId", *CLAIMS} or not isinstance(item.get("groupId"), str):
                return None, "convergence_item_shape"
            group_id = item["groupId"]
            if group_id in seen_groups:
                return None, "duplicate_group_id"
            seen_groups.append(group_id)
            convergence_map[group_id] = {name: item[name] for name in CLAIMS}
        seen_impulses: list[str] = []
        impulse_map: dict[str, Any] = {}
        for item in impulse_value:
            if not isinstance(item, dict) or set(item) != {"eventId", *CLAIMS} or not isinstance(item.get("eventId"), str):
                return None, "impulse_item_shape"
            event_id = item["eventId"]
            if event_id in seen_impulses:
                return None, "duplicate_event_id"
            seen_impulses.append(event_id)
            impulse_map[event_id] = {name: item[name] for name in CLAIMS}
        if set(convergence_map) != group_ids or set(impulse_map) != impulse_ids:
            return None, "block_ids"
        if (main_id is None) != (value.get("main_event") is None):
            return None, "main_event_shape"
        normalized = {"convergences": convergence_map, "main_event": value.get("main_event"), "impulses": impulse_map}
    else:
        return None, "unknown_arm"
    if not all(_block_shape(block) for block in normalized["convergences"].values()):
        return None, "convergence_block_shape"
    if normalized["main_event"] is not None and not _block_shape(normalized["main_event"]):
        return None, "main_block_shape"
    if not all(_block_shape(block) for block in normalized["impulses"].values()):
        return None, "impulse_block_shape"
    return normalized, None


def _block_metadata(expected: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    for item in expected.get("convergences", []):
        blocks[str(item["groupId"])] = item
    if isinstance(expected.get("main_event"), dict):
        main = expected["main_event"]
        blocks[str(main["eventId"])] = main
    for item in expected.get("impulses", []):
        blocks[str(item["eventId"])] = item
    return blocks


def _text_tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(text)}


def _usage_int(usage: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = usage.get(key, default)
    if isinstance(value, bool):
        return default
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _reasoning_tokens(usage: Mapping[str, Any]) -> int | None:
    details = usage.get("completion_tokens_details")
    if isinstance(details, Mapping) and "reasoning_tokens" in details:
        value = details.get("reasoning_tokens")
        if value is None:
            return None
        return _usage_int(details, "reasoning_tokens")
    if "reasoning_tokens" in usage:
        value = usage.get("reasoning_tokens")
        if value is None:
            return None
        return _usage_int(usage, "reasoning_tokens")
    return None


def _visible_completion_tokens(usage: Mapping[str, Any]) -> int | None:
    reasoning = _reasoning_tokens(usage)
    if reasoning is None:
        return None
    return max(0, _usage_int(usage, "completion_tokens") - reasoning)


def _repeatability(first: Mapping[str, Any] | None, second: Mapping[str, Any] | None, expected: Mapping[str, Any]) -> float | None:
    if first is None or second is None:
        return None
    texts: list[float] = []
    first_blocks = {**first.get("convergences", {}), **first.get("impulses", {})}
    second_blocks = {**second.get("convergences", {}), **second.get("impulses", {})}
    if expected.get("main_event") is not None:
        first_blocks[expected["main_event"]["eventId"]] = first.get("main_event")
        second_blocks[expected["main_event"]["eventId"]] = second.get("main_event")
    for block_id in first_blocks.keys() & second_blocks.keys():
        for claim_name in CLAIMS:
            first_claim = first_blocks[block_id].get(claim_name)
            second_claim = second_blocks[block_id].get(claim_name)
            if not isinstance(first_claim, dict) or not isinstance(second_claim, dict):
                continue
            left = _text_tokens(first_claim["text"])
            right = _text_tokens(second_claim["text"])
            if left or right:
                texts.append(len(left & right) / len(left | right) if left | right else 1.0)
    return statistics.mean(texts) if texts else None


def _score_response(
    envelope: ResponseEnvelope,
    expected: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._score_response
    # purpose: Normalize one arm and calculate deterministic narrative quality, usage-split, and truncation metrics.
    # inputs: raw response envelope and safe expected block metadata.
    # returns: compact metric row and normalized response for repeatability only.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed responses become json_valid=0 with a classified error.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._score_response
    prompt_tokens = _usage_int(envelope.usage, "prompt_tokens")
    completion_tokens = _usage_int(envelope.usage, "completion_tokens")
    reasoning_tokens = _reasoning_tokens(envelope.usage)
    visible_completion_tokens = _visible_completion_tokens(envelope.usage)
    truncated = envelope.truncated if envelope.truncated is not None else completion_tokens >= envelope.max_tokens
    base: dict[str, Any] = {
        "model_key": envelope.model_key,
        "arm": envelope.arm,
        "input_id": envelope.input_id,
        "repeat": envelope.repeat,
        "error_class": envelope.error_class,
        "strict_support": 0.0 if envelope.error_class == "strict_unsupported" else 1.0,
        "json_valid": 0.0,
        "fill_rate": 0.0,
        "claim_binding": 0.0,
        "sanitizer_pass": 0.0,
        "length_ok": 0.0,
        "stamp_hits": 0,
        "stamp_clean": 0.0,
        "datetime_leak": 0,
        "datetime_clean": 0.0,
        "name_rule": 0.0,
        "lexicon_cover": 0.0,
        "auto_score": 0.0,
        "latency_ms": envelope.latency_ms,
        "retries": envelope.retries,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
        "visible_completion_tokens": visible_completion_tokens,
        "truncated": truncated,
        "truncated_rate": 1.0 if truncated else 0.0,
    }
    if envelope.error_class is not None:
        return base, None
    normalized, error = _normalize_response(envelope.raw, envelope.arm, expected)
    if normalized is None:
        base["error_class"] = error or "invalid_response"
        return base, None
    base["json_valid"] = 1.0
    if truncated:
        return base, None
    metadata = _block_metadata(expected)
    blocks: list[tuple[str, Mapping[str, Any], Any]] = []
    for block_id, block in normalized["convergences"].items():
        blocks.append((block_id, metadata[block_id], block))
    if normalized["main_event"] is not None and isinstance(expected.get("main_event"), dict):
        event_id = expected["main_event"]["eventId"]
        blocks.append((event_id, metadata[event_id], normalized["main_event"]))
    for block_id, block in normalized["impulses"].items():
        blocks.append((block_id, metadata[block_id], block))
    required_claims = len(blocks) * len(CLAIMS)
    filled = 0
    bound = 0
    provided_claims = 0
    safe = 0
    length_ok = 0
    lexicon_total = 0
    lexicon_ok = 0
    stamps = 0
    leaks = 0
    all_text: list[str] = []
    for _, block_meta, block in blocks:
        allowed_ids = set(block_meta.get("sourceEventIds", []))
        for claim_name in CLAIMS:
            claim = block[claim_name]
            if claim is None:
                continue
            provided_claims += 1
            text = claim["text"].strip()
            source_ids = claim["sourceEventIds"]
            if text:
                filled += 1
                all_text.append(text)
            if source_ids and set(source_ids).issubset(allowed_ids):
                bound += 1
            if text:
                facet = block_meta.get("facet")
                allowed_spheres = (block_meta.get("sphere"),)
                allowed_facets = (facet,) if facet else ()
                _ensure_app_paths()
                from app.services.narrative_sanitizer import has_forbidden_narrative_tokens, has_narrative_grounding_violation

                if not has_forbidden_narrative_tokens(text) and not has_narrative_grounding_violation(
                    text,
                    allowed_spheres=allowed_spheres,
                    allowed_facets=allowed_facets,
                    polarity=str(block_meta.get("polarity")),
                ):
                    safe += 1
                if len(text) <= {"summary": 220, "meaning": 260, "action": 180}[claim_name]:
                    length_ok += 1
                lexicon = [word.lower() for word in block_meta.get("lexicon", []) if isinstance(word, str)]
                if facet and lexicon:
                    lexicon_total += 1
                    if any(word in text.lower() for word in lexicon):
                        lexicon_ok += 1
                for term in STAMP_TERMS:
                    stamps += text.lower().count(term)
                leaks += sum(len(pattern.findall(text)) for pattern in TIME_PATTERNS)
    filled_denominator = filled or 1
    lexicon_denominator = lexicon_total or 1
    name_token = NAME_MASK
    name_occurrences = " ".join(all_text).lower().count(name_token.lower())
    base.update(
        {
            "fill_rate": filled / (required_claims or 1),
            "claim_binding": bound / (provided_claims or 1),
            "sanitizer_pass": safe / filled_denominator,
            "length_ok": length_ok / filled_denominator,
            "stamp_hits": stamps,
            "stamp_clean": 1.0 if stamps == 0 else max(0.0, 1.0 - stamps / filled_denominator),
            "datetime_leak": leaks,
            "datetime_clean": 1.0 if leaks == 0 else max(0.0, 1.0 - leaks / filled_denominator),
            "name_rule": 1.0 if name_occurrences <= 1 else 0.0,
            "lexicon_cover": lexicon_ok / lexicon_denominator,
            "required_claims": required_claims,
            "filled_claims": filled,
        }
    )
    base["auto_score"] = round(
        base["sanitizer_pass"] * 30
        + base["fill_rate"] * 15
        + base["claim_binding"] * 10
        + base["length_ok"] * 10
        + base["lexicon_cover"] * 10
        + base["stamp_clean"] * 10
        + base["datetime_clean"] * 10
        + base["name_rule"] * 5,
        3,
    )
    return base, normalized


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _cost(usage: Mapping[str, Any], price: PriceConfig) -> float:
    return (
        _usage_int(usage, "prompt_tokens") * price.input_per_million
        + _usage_int(usage, "completion_tokens") * price.output_per_million
    ) / 1_000_000.0


def _aggregate(
    rows: list[dict[str, Any]],
    bundle: TaskBundle,
    *,
    model_configs: Iterable[ModelConfig] | None = None,
) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["model_key"], row["arm"])].append(row)
    output: list[dict[str, Any]] = []
    for model in model_configs or bundle.models:
        price = bundle.prices[model.pricing_key]
        for arm in ARMS:
            members = groups.get((model.key, arm), [])
            if not members:
                continue
            metric_names = (
                "strict_support",
                "json_valid",
                "truncated_rate",
                "fill_rate",
                "claim_binding",
                "sanitizer_pass",
                "length_ok",
                "stamp_clean",
                "datetime_clean",
                "name_rule",
                "lexicon_cover",
                "auto_score",
            )
            averages = {name: round(statistics.mean(float(row[name]) for row in members), 4) for name in metric_names}
            total_cost = sum(_cost({"prompt_tokens": row["input_tokens"], "completion_tokens": row["output_tokens"]}, price) for row in members)
            latencies = [float(row["latency_ms"]) for row in members]
            prompt_tokens = sum(int(row["input_tokens"]) for row in members)
            completion_tokens = sum(int(row["output_tokens"]) for row in members)
            reasoning_values = [int(row["reasoning_tokens"]) for row in members if row.get("reasoning_tokens") is not None]
            visible_values = [int(row["visible_completion_tokens"]) for row in members if row.get("visible_completion_tokens") is not None]
            repeatability_values: list[float] = []
            by_input: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
            for row in members:
                if row.get("normalized") is not None:
                    by_input[row["input_id"]][int(row["repeat"])] = row["normalized"]
            inputs_by_id = {record["input_id"]: record for record in (bundle.inputs or {}).get("inputs", [])}
            for input_id, repeats in by_input.items():
                if 0 in repeats and 1 in repeats and input_id in inputs_by_id:
                    value = _repeatability(repeats[0], repeats[1], inputs_by_id[input_id]["expected"])
                    if value is not None:
                        repeatability_values.append(value)
            calls = len(members)
            output.append(
                {
                    "model_key": model.key,
                    "label": model.label,
                    "model": model.model,
                    "max_tokens": model.max_tokens,
                    "arm": arm,
                    "calls": calls,
                    "retries": sum(int(row["retries"]) for row in members),
                    "strict_unsupported": sum(row.get("error_class") == "strict_unsupported" for row in members),
                    "latency_ms": {"p50": round(_percentile(latencies, 0.50), 1), "p95": round(_percentile(latencies, 0.95), 1)},
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "reasoning_tokens": sum(reasoning_values) if reasoning_values else None,
                        "visible_completion_tokens": sum(visible_values) if visible_values else None,
                        "reasoning_token_calls": len(reasoning_values),
                        "mean_prompt_tokens": round(prompt_tokens / calls, 2) if calls else 0.0,
                        "mean_completion_tokens": round(completion_tokens / calls, 2) if calls else 0.0,
                        "mean_reasoning_tokens": round(statistics.mean(reasoning_values), 2) if reasoning_values else None,
                        "mean_visible_completion_tokens": round(statistics.mean(visible_values), 2) if visible_values else None,
                    },
                    "cost_usd": round(total_cost, 6),
                    "mean_cost_per_call_usd": round(total_cost / calls if calls else 0.0, 6),
                    "cost_per_1k_narratives_usd": round(total_cost / calls * 1000 if calls else 0.0, 4),
                    "monthly_estimate_usd": round(total_cost / calls * 500 * 30 if calls else 0.0, 4),
                    "monthly_3000_estimate_usd": round(total_cost / calls * MONTHLY_NARRATIVE_CALLS if calls else 0.0, 4),
                    "repeatability": round(statistics.mean(repeatability_values), 4) if repeatability_values else None,
                    "metrics": averages,
                    "stamp_hits": sum(int(row["stamp_hits"]) for row in members),
                    "datetime_leak": sum(int(row["datetime_leak"]) for row in members),
                }
            )
    return {"arms": output}


# END_BLOCK: SCORING


# START_BLOCK: RUN
class BudgetGuard:
    def __init__(self, limit: float = MAX_BUDGET_USD, initial_spent: float = 0.0) -> None:
        self.limit = limit
        self.spent = max(0.0, initial_spent)
        self._lock = asyncio.Lock()

    async def before_call(self) -> None:
        async with self._lock:
            if self.spent >= self.limit:
                raise EvalError(f"budget guard stopped before call at ${self.spent:.4f}")

    async def record(self, amount: float) -> None:
        async with self._lock:
            self.spent += amount
            if self.spent > self.limit:
                raise EvalError(f"budget guard exceeded ${self.spent:.4f} > ${self.limit:.2f}")


def _request_body(model: ModelConfig, arm: str, prompt: str, expected: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": model.max_tokens,
    }
    if arm == "json_object":
        body["response_format"] = {"type": "json_object"}
    else:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "today_narrative", "strict": True, "schema": strict_response_schema()},
        }
        body["provider"] = {"require_parameters": True}
    body.update(model.extra_body)
    return body


def _resolve_raw_out_dir(value: str | Path) -> Path:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._resolve_raw_out_dir
    # purpose: Resolve an existing raw run directory for an idempotent model merge.
    # inputs: value — path supplied to `run --out-dir`.
    # returns: existing directory under the ignored narrative eval root.
    # side_effects: filesystem reads only.
    # emitted_logs: none.
    # error_behavior: paths outside `.eval-runs/narrative-model-eval-v1` or missing directories raise EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._resolve_raw_out_dir
    path = Path(value)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    root = RAW_ROOT.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise EvalError("--out-dir must be under .eval-runs/narrative-model-eval-v1") from exc
    if not path.is_dir():
        _fail(f"existing --out-dir not found: {path}")
    return path


def _api_environment() -> tuple[str, str]:
    # app Settings reads the repository .env; this helper keeps the key out of
    # output and lets the runner fail closed before any paid request.
    _ensure_app_paths()
    from app.core.config import settings

    key = settings.openrouter_api_key
    base_url = settings.openrouter_base_url.rstrip("/")
    if not isinstance(key, str) or not key.strip():
        _fail("OPENROUTER_API_KEY is missing; paid run not started")
    return key, base_url


async def _openrouter_call(
    body: Mapping[str, Any],
    *,
    api_key: str,
    base_url: str,
    arm: str,
) -> tuple[str, dict[str, Any], int, int, str | None]:
    import httpx

    retries = 0
    async with httpx.AsyncClient() as client:
        while True:
            started = time.perf_counter()
            try:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=body,
                    timeout=TIMEOUT_SECONDS,
                )
            except (httpx.TimeoutException, httpx.TransportError):
                if retries < 1:
                    retries += 1
                    continue
                return "", {}, round((time.perf_counter() - started) * 1000), retries, "transport_error"
            latency_ms = round((time.perf_counter() - started) * 1000)
            if arm == "strict_json_schema" and response.status_code in {400, 404}:
                return "", {}, latency_ms, retries, "strict_unsupported"
            if response.status_code >= 500 and retries < 1:
                retries += 1
                continue
            if response.status_code >= 400:
                return "", {}, latency_ms, retries, f"http_{response.status_code}"
            try:
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                usage_raw = payload.get("usage") or {}
                if not isinstance(usage_raw, dict):
                    return "", {}, latency_ms, retries, "provider_shape"
                usage = dict(usage_raw)
                usage["prompt_tokens"] = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
                usage["completion_tokens"] = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
            except (ValueError, KeyError, TypeError, IndexError):
                return "", {}, latency_ms, retries, "provider_shape"
            return content if isinstance(content, str) else "", usage, latency_ms, retries, None


async def _run_paid(
    task: TaskBundle,
    inputs: Mapping[str, Any],
    run_id: str | None,
    out_dir: str | Path | None = None,
) -> Path:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._run_paid
    # purpose: Execute the explicitly confirmed provider run, optionally merging selected models into an existing raw run.
    # inputs: filtered task bundle, safe inputs, optional run id, and optional existing raw out directory.
    # returns: compact result directory with all available raw responses scored.
    # side_effects: paid OpenRouter calls only after explicit CLI confirmation; writes selected raw files, manifest, and compact metrics.
    # emitted_logs: none; manifests contain counts/costs/model keys, never credentials.
    # error_behavior: transport/5xx retry once, strict 400/404 becomes strict_unsupported, budget stops fail closed.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._run_paid
    if not inputs.get("inputs"):
        _fail("paid run requires inputs.json")
    if out_dir is not None:
        raw_dir = _resolve_raw_out_dir(out_dir)
        manifest_path = raw_dir / "manifest.json"
        manifest = _read_json(manifest_path) if manifest_path.exists() else {}
        stored_run_id = manifest.get("run_id")
        if run_id and stored_run_id and str(run_id) != str(stored_run_id):
            _fail("--run-id does not match existing --out-dir manifest")
        effective_run_id = str(stored_run_id or run_id or raw_dir.name)
    else:
        effective_run_id = str(run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
        raw_dir = RAW_ROOT / effective_run_id
        raw_dir.mkdir(parents=True, exist_ok=False)
        manifest = {}
    api_key, base_url = _api_environment()
    model_by_key = {model.key: model for model in task.all_models}
    existing_envelopes = _load_raw_envelopes(raw_dir, model_by_key)
    existing_raw_cost = sum(
        _cost(envelope.usage, task.prices[model_by_key[envelope.model_key].pricing_key])
        for envelope in existing_envelopes
        if envelope.model_key in model_by_key
    )
    try:
        previous_spent = float(manifest.get("spent_usd", existing_raw_cost) or 0.0)
    except (TypeError, ValueError):
        previous_spent = existing_raw_cost
    initial_spent = max(0.0, previous_spent, existing_raw_cost)
    existing_model_keys = {envelope.model_key for envelope in existing_envelopes}
    manifest.setdefault("schema_version", 1)
    manifest.setdefault("task_id", TASK_ID)
    if manifest["task_id"] != TASK_ID:
        _fail("existing --out-dir manifest task mismatch")
    manifest.setdefault("created_at", datetime.now(UTC).isoformat())
    manifest.update(
        {
            "run_id": effective_run_id,
            "models": sorted({str(value) for value in manifest.get("models", [])} | {model.model for model in task.models}),
            "model_keys": sorted(
                {str(value) for value in manifest.get("model_keys", [])}
                | existing_model_keys
                | {model.key for model in task.models}
            ),
            "arms": list(ARMS),
            "inputs": len(inputs["inputs"]),
            "repeats": REPEATS,
            "concurrency": CONCURRENCY,
            "timeout_seconds": TIMEOUT_SECONDS,
            "budget_usd": MAX_BUDGET_USD,
            "paid_provider": "openrouter",
            "last_run_models": [model.key for model in task.models],
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    guard = BudgetGuard(initial_spent=initial_spent)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    rows: list[dict[str, Any]] = []
    rows_lock = asyncio.Lock()

    async def one(model: ModelConfig, arm: str, record: Mapping[str, Any], repeat: int) -> None:
        async with semaphore:
            await guard.before_call()
            prompt = str(record["prompt"])
            request_prompt = prompt if arm == "json_object" else _strict_prompt(prompt, record["expected"])
            body = _request_body(model, arm, request_prompt, record["expected"])
            raw, usage, latency_ms, retries, error_class = await _openrouter_call(
                body, api_key=api_key, base_url=base_url, arm=arm
            )
            amount = _cost(usage, task.prices[model.pricing_key])
            await guard.record(amount)
            envelope = ResponseEnvelope(
                model.key,
                arm,
                str(record["input_id"]),
                repeat,
                raw,
                usage,
                latency_ms,
                retries,
                error_class,
                model.max_tokens,
            )
            metric, normalized = _score_response(envelope, record["expected"])
            metric["normalized"] = normalized
            filename = f"{model.key}__{arm}__{record['input_id']}__r{repeat}.json"
            payload = {
                "model_key": model.key,
                "model": model.model,
                "arm": arm,
                "input_id": record["input_id"],
                "repeat": repeat,
                "request": body,
                "response": raw,
                "usage": usage,
                "max_tokens": model.max_tokens,
                "truncated": bool(metric["truncated"]),
                "latency_ms": latency_ms,
                "retries": retries,
                "error_class": error_class,
            }
            (raw_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            async with rows_lock:
                rows.append(metric)

    jobs = [
        one(model, arm, record, repeat)
        for model in task.models
        for arm in ARMS
        for record in inputs["inputs"]
        for repeat in range(REPEATS)
    ]
    try:
        await asyncio.gather(*jobs)
    except Exception:
        manifest.update(
            {
                "stopped_spent_usd": round(guard.spent, 6),
                "spent_usd": round(guard.spent, 6),
                "last_run_spent_usd": round(max(0.0, guard.spent - initial_spent), 6),
                "last_run_call_count": len(rows),
                "call_count": int(manifest.get("call_count", len(existing_envelopes))) + len(rows),
                "retries": int(manifest.get("retries", 0) or 0) + sum(int(row["retries"]) for row in rows),
                "stopped": True,
            }
        )
        (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        raise
    all_envelopes = _load_raw_envelopes(raw_dir, model_by_key)
    all_rows = _score_envelopes(task, inputs, all_envelopes)
    current_raw_cost = sum(
        _cost(envelope.usage, task.prices[model_by_key[envelope.model_key].pricing_key])
        for envelope in all_envelopes
        if envelope.model_key in model_by_key
    )
    previous_call_count = int(manifest.get("call_count", len(existing_envelopes)) or 0)
    previous_retries = int(manifest.get("retries", 0) or 0)
    manifest.update(
        {
            "spent_usd": round(guard.spent, 6),
            "last_run_spent_usd": round(max(0.0, guard.spent - initial_spent), 6),
            "call_count": previous_call_count + len(rows),
            "last_run_call_count": len(rows),
            "retries": previous_retries + sum(int(row["retries"]) for row in rows),
            "raw_response_count": len(all_envelopes),
            "current_raw_cost_usd": round(current_raw_cost, 6),
            "stopped": False,
        }
    )
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    compact = _aggregate(all_rows, task, model_configs=task.all_models)
    compact.update(
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "run_id": effective_run_id,
            "created_at": manifest["created_at"],
            "spent_usd": round(guard.spent, 6),
            "call_count": manifest["call_count"],
            "raw_response_count": len(all_envelopes),
            "coverage": inputs.get("coverage", {}),
        }
    )
    result_dir = RESULTS_ROOT / effective_run_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (result_dir / "metrics.json").write_text(json.dumps(compact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result_dir


def _load_raw_envelopes(
    raw_dir: Path,
    model_by_key: Mapping[str, ModelConfig] | None = None,
) -> list[ResponseEnvelope]:
    envelopes: list[ResponseEnvelope] = []
    for path in sorted(raw_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        value = _read_json(path)
        model_key = str(value.get("model_key"))
        request = value.get("request") if isinstance(value.get("request"), dict) else {}
        max_tokens = value.get("max_tokens", request.get("max_tokens"))
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            max_tokens = model_by_key.get(model_key, ModelConfig("", "", "", "")).max_tokens if model_by_key else 2000
        envelopes.append(
            ResponseEnvelope(
                model_key=model_key,
                arm=str(value.get("arm")),
                input_id=str(value.get("input_id")),
                repeat=int(value.get("repeat", 0)),
                raw=str(value.get("response", "")),
                usage=dict(value.get("usage")) if isinstance(value.get("usage"), dict) else {},
                latency_ms=int(value.get("latency_ms", 0)),
                retries=int(value.get("retries", 0)),
                error_class=value.get("error_class") if isinstance(value.get("error_class"), str) else None,
                max_tokens=max_tokens,
                truncated=value.get("truncated") if isinstance(value.get("truncated"), bool) else None,
            )
        )
    return envelopes


def _score_envelopes(
    task: TaskBundle,
    inputs: Mapping[str, Any],
    envelopes: Iterable[ResponseEnvelope],
) -> list[dict[str, Any]]:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._score_envelopes
    # purpose: Score a complete raw run, including preserved models during an out-dir merge.
    # inputs: task, safe inputs, and raw response envelopes.
    # returns: compact metric rows with normalized responses attached only in memory.
    # side_effects: none; no provider or filesystem writes.
    # emitted_logs: none.
    # error_behavior: unknown input IDs raise EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL._score_envelopes
    inputs_by_id = {record["input_id"]: record for record in inputs.get("inputs", [])}
    known_model_keys = {model.key for model in task.all_models}
    rows: list[dict[str, Any]] = []
    for envelope in envelopes:
        if envelope.model_key not in known_model_keys:
            _fail(f"raw response references unknown model: {envelope.model_key}")
        record = inputs_by_id.get(envelope.input_id)
        if record is None:
            _fail(f"raw response references unknown input: {envelope.input_id}")
        metric, normalized = _score_response(envelope, record["expected"])
        metric["normalized"] = normalized
        rows.append(metric)
    return rows


def score_run(task_dir: str | Path, run_dir: str | Path, model_filter: str | None = None) -> Path:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.score_run
    # purpose: Recalculate compact metrics from ignored raw responses without provider calls.
    # inputs: immutable task directory and .eval-runs run directory.
    # returns: evals/results/<run-id> directory containing manifest and metrics JSON.
    # side_effects: reads raw traces and writes compact result artifacts only.
    # emitted_logs: none.
    # error_behavior: malformed raw/task data raises EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.score_run
    task = _load_bundle(task_dir, require_inputs=True, model_filter=model_filter)
    raw_path = Path(run_dir)
    if not raw_path.is_absolute():
        raw_path = (REPO_ROOT / raw_path).resolve()
    inputs = task.inputs
    assert inputs is not None
    model_by_key = {model.key: model for model in task.all_models}
    envelopes = _load_raw_envelopes(raw_path, model_by_key)
    if model_filter is not None:
        selected_keys = {model.key for model in task.models}
        envelopes = [envelope for envelope in envelopes if envelope.model_key in selected_keys]
    rows = _score_envelopes(task, inputs, envelopes)
    compact = _aggregate(rows, task, model_configs=task.models if model_filter is not None else task.all_models)
    manifest = _read_json(raw_path / "manifest.json")
    compact.update(
        {
            "schema_version": 1,
            "task_id": TASK_ID,
            "run_id": manifest.get("run_id", raw_path.name),
            "created_at": manifest.get("created_at"),
            "spent_usd": round(
                sum(
                    _cost(envelope.usage, task.prices[model_by_key[envelope.model_key].pricing_key])
                    for envelope in envelopes
                    if envelope.model_key in model_by_key
                ),
                6,
            ),
            "call_count": len(rows),
            "raw_response_count": len(envelopes),
            "coverage": inputs.get("coverage", {}),
        }
    )
    result_dir = RESULTS_ROOT / str(compact["run_id"])
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (result_dir / "metrics.json").write_text(json.dumps(compact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result_dir


# END_BLOCK: RUN


# START_BLOCK: CLI
def _estimate_plan(task: TaskBundle, inputs: Mapping[str, Any]) -> dict[str, Any]:
    records = inputs.get("inputs", [])
    total = 0.0
    max_cap_total = 0.0
    by_model: dict[str, float] = {}
    max_cap_by_model: dict[str, float] = {}
    for model in task.models:
        price = task.prices[model.pricing_key]
        model_total = 0.0
        model_cap_total = 0.0
        for record in records:
            prompt_a = str(record["prompt"])
            prompt_b = _strict_prompt(prompt_a, record["expected"])
            for prompt in (prompt_a, prompt_b):
                prompt_tokens = max(1, math.ceil(len(prompt.encode("utf-8")) / 4))
                model_total += (prompt_tokens * price.input_per_million + EXPECTED_COMPLETION_TOKENS * price.output_per_million) / 1_000_000
                model_cap_total += (prompt_tokens * price.input_per_million + model.max_tokens * price.output_per_million) / 1_000_000
        model_total *= REPEATS
        model_cap_total *= REPEATS
        by_model[model.key] = round(model_total, 6)
        max_cap_by_model[model.key] = round(model_cap_total, 6)
        total += model_total
        max_cap_total += model_cap_total
    return {
        "inputs": len(records),
        "models": len(task.models),
        "arms": len(ARMS),
        "repeats": REPEATS,
        "concurrency": CONCURRENCY,
        "calls": len(records) * len(task.models) * len(ARMS) * REPEATS,
        "expected_completion_tokens_per_call": EXPECTED_COMPLETION_TOKENS,
        "estimated_cost_usd": round(total, 4),
        "estimated_cost_by_model_usd": by_model,
        "max_cap_estimated_cost_usd": round(max_cap_total, 4),
        "max_cap_estimated_cost_by_model_usd": max_cap_by_model,
        "hard_budget_usd": MAX_BUDGET_USD,
    }


def validate_task(task_dir: str | Path, model_filter: str | None = None) -> int:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.validate_task
    # purpose: Free-check task artifacts, collect missing inputs read-only, and print the paid-run estimate.
    # inputs: task directory, optional model filter; no provider credentials are used.
    # returns: process-style zero on success.
    # side_effects: may read dev DB/sidecar and create inputs.json; never calls OpenRouter.
    # emitted_logs: stdout plan only, with no names, credentials, or raw narrative.
    # error_behavior: coverage gaps return process code 2; malformed task or over-budget max-cap estimate raises EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.validate_task
    task = _load_bundle(task_dir, model_filter=model_filter)
    inputs = _load_or_collect(task)
    _validate_inputs_document(inputs)
    plan = _estimate_plan(task, inputs)
    if plan["max_cap_estimated_cost_usd"] > MAX_BUDGET_USD:
        _fail(f"validation max-cap estimate exceeds hard budget: ${plan['max_cap_estimated_cost_usd']:.4f}")
    coverage_gaps = _coverage_gaps(inputs.get("coverage", {}))
    if coverage_gaps:
        print("narrative_model_eval validate: INCOMPLETE (no OpenRouter calls)")
    else:
        print("narrative_model_eval validate: PASS (no OpenRouter calls)")
    print(f"task={TASK_ID} prompt_version={PROMPT_VERSION}")
    print(f"inputs={plan['inputs']} models={plan['models']} model_keys={','.join(model.key for model in task.models)} arms={plan['arms']} repeats={plan['repeats']} concurrency={plan['concurrency']}")
    print(f"calls={plan['calls']} estimated_cost_usd=${plan['estimated_cost_usd']:.4f} hard_budget_usd=${MAX_BUDGET_USD:.2f}")
    print(f"max_cap_estimated_cost_usd=${plan['max_cap_estimated_cost_usd']:.4f}")
    print(f"coverage={json.dumps(inputs.get('coverage', {}), ensure_ascii=False, sort_keys=True)}")
    print(f"coverage_gaps={json.dumps(coverage_gaps, ensure_ascii=False)}")
    print(f"estimated_cost_by_model_usd={json.dumps(plan['estimated_cost_by_model_usd'], sort_keys=True)}")
    print(f"max_cap_estimated_cost_by_model_usd={json.dumps(plan['max_cap_estimated_cost_by_model_usd'], sort_keys=True)}")
    print("paid_run_requires=run --confirm-paid-run")
    return 2 if coverage_gaps else 0


def run_selftest() -> int:
    # START_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.run_selftest
    # purpose: Exercise A/B normalization, deterministic scoring, cost math, and the nano cross-facet sanity control without network.
    # inputs: synthetic masked prompt metadata only.
    # returns: process-style zero when all harness controls pass.
    # side_effects: none; this function never imports the DB/session or HTTP client.
    # emitted_logs: one safe PASS line.
    # error_behavior: assertion failure raises EvalError.
    # END_FUNCTION_CONTRACT: F-M-SCRIPTS-NARRATIVE-MODEL-EVAL.run_selftest
    expected = {
        "convergences": [
            {
                "groupId": "cvg-test",
                "sourceEventIds": ["evt-test-1", "evt-test-2"],
                "sphere": "relationships",
                "facet": "romance",
                "polarity": "supportive",
                "lexicon": ["романтика", "свидание", "симпатия"],
            }
        ],
        "main_event": None,
        "impulses": [],
    }
    valid_claim = {"text": "Сегодня романтика требует тёплого разговора о симпатии.", "sourceEventIds": ["evt-test-1"]}
    valid_block = {name: valid_claim for name in CLAIMS}
    keyed = {"convergences": {"cvg-test": valid_block}, "main_event": None, "impulses": {}}
    array = {"convergences": [{"groupId": "cvg-test", **valid_block}], "main_event": None, "impulses": []}
    envelope_a = ResponseEnvelope("baseline-nano", "json_object", "synthetic", 0, json.dumps(keyed, ensure_ascii=False), {"prompt_tokens": 100, "completion_tokens": 50}, 10, 0)
    envelope_b = ResponseEnvelope("baseline-nano", "strict_json_schema", "synthetic", 0, json.dumps(array, ensure_ascii=False), {"prompt_tokens": 100, "completion_tokens": 50}, 10, 0)
    model = ModelConfig("baseline-nano", "baseline", "openai/gpt-4.1-nano", "price")
    body_a = _request_body(model, "json_object", "prompt", expected)
    body_b = _request_body(model, "strict_json_schema", "strict prompt", expected)
    if body_a.get("response_format") != {"type": "json_object"} or "temperature" in body_a:
        _fail("selftest production request body mismatch")
    schema = body_b.get("response_format", {}).get("json_schema", {})
    if (
        body_b.get("provider") != {"require_parameters": True}
        or schema.get("name") != "today_narrative"
        or schema.get("strict") is not True
        or schema.get("schema", {}).get("properties", {}).get("convergences", {}).get("type") != "array"
    ):
        _fail("selftest strict request body mismatch")
    override_model = ModelConfig("deepseek-v4-flash", "flash", "deepseek/deepseek-v4-flash", "price", 6000, {"reasoning": {"effort": "low"}})
    override_body = _request_body(override_model, "json_object", "prompt", expected)
    if override_body.get("max_tokens") != 6000 or override_body.get("reasoning") != {"effort": "low"}:
        _fail("selftest model override body mismatch")
    if _parse_model_filter("deepseek-v4-flash,deepseek-v4-pro") != ("deepseek-v4-flash", "deepseek-v4-pro"):
        _fail("selftest model filter parsing failed")
    score_a, normalized_a = _score_response(envelope_a, expected)
    score_b, normalized_b = _score_response(envelope_b, expected)
    if score_a["json_valid"] != 1.0 or score_b["json_valid"] != 1.0 or normalized_a != normalized_b:
        _fail("selftest A/B normalization failed")
    unsupported_score, _ = _score_response(
        ResponseEnvelope(
            "baseline-nano",
            "strict_json_schema",
            "synthetic",
            0,
            "",
            {},
            0,
            0,
            "strict_unsupported",
        ),
        expected,
    )
    if unsupported_score["strict_support"] != 0.0 or unsupported_score["json_valid"] != 0.0:
        _fail("selftest strict_unsupported classification failed")
    truncated_score, _ = _score_response(
        ResponseEnvelope(
            "deepseek-v4-flash",
            "json_object",
            "synthetic",
            0,
            json.dumps(keyed, ensure_ascii=False),
            {"prompt_tokens": 100, "completion_tokens": 6000, "completion_tokens_details": {"reasoning_tokens": 5000}},
            10,
            0,
            None,
            6000,
        ),
        expected,
    )
    if (
        truncated_score["truncated"] is not True
        or truncated_score["truncated_rate"] != 1.0
        or truncated_score["json_valid"] != 1.0
        or truncated_score["fill_rate"] != 0.0
        or truncated_score["reasoning_tokens"] != 5000
        or truncated_score["visible_completion_tokens"] != 1000
    ):
        _fail("selftest usage/truncation accounting failed")
    bad_claim = {"text": "Проверь доходы и расходы в романтике.", "sourceEventIds": ["evt-test-1"]}
    bad = {"convergences": {"cvg-test": {name: bad_claim for name in CLAIMS}}, "main_event": None, "impulses": {}}
    bad_score, _ = _score_response(ResponseEnvelope("baseline-nano", "json_object", "synthetic", 0, json.dumps(bad, ensure_ascii=False), {}, 0, 0), expected)
    if bad_score["sanitizer_pass"] >= 1.0:
        _fail("nano cross-facet sanity control did not fail")
    if _cost({"prompt_tokens": 100, "completion_tokens": 50}, PriceConfig("p", "m", 0.10, 0.40)) <= 0:
        _fail("selftest cost math failed")
    print("narrative_model_eval selftest: PASS (A/B normalization, scorer, nano cross-facet sanity, no network)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe two-arm Today narrative v5 model evaluation")
    parser.add_argument("--selftest", action="store_true", help="run synthetic scorer controls without DB or network")
    subparsers = parser.add_subparsers(dest="command")
    validate_parser = subparsers.add_parser("validate", help="collect inputs and print a free cost estimate")
    validate_parser.add_argument("--task", required=True)
    validate_parser.add_argument("--models", default=None, help="comma-separated model keys to include")
    run_parser = subparsers.add_parser("run", help="paid OpenRouter run; explicit confirmation required")
    run_parser.add_argument("--task", required=True)
    run_parser.add_argument("--models", default=None, help="comma-separated model keys to run")
    run_parser.add_argument("--confirm-paid-run", action="store_true")
    run_parser.add_argument("--run-id", default=None)
    run_parser.add_argument("--out-dir", default=None, help="existing raw run directory for an idempotent merge")
    score_parser = subparsers.add_parser("score", help="score raw traces without provider calls")
    score_parser.add_argument("--task", required=True)
    score_parser.add_argument("--run", required=True)
    score_parser.add_argument("--models", default=None, help="comma-separated model keys to score")
    args = parser.parse_args(argv)
    try:
        if args.selftest:
            return run_selftest()
        if args.command == "validate":
            return validate_task(args.task, args.models)
        if args.command == "run":
            if not args.confirm_paid_run:
                _fail("paid run blocked: pass --confirm-paid-run")
            task = _load_bundle(args.task, require_inputs=True, model_filter=args.models)
            inputs = task.inputs
            assert inputs is not None
            coverage_gaps = _coverage_gaps(inputs.get("coverage", {}))
            if coverage_gaps:
                _fail("paid run blocked by incomplete input coverage: " + ", ".join(coverage_gaps))
            result_dir = asyncio.run(_run_paid(task, inputs, args.run_id, args.out_dir))
            print(f"narrative_model_eval run: PASS run_id={result_dir.name} result={result_dir.relative_to(REPO_ROOT)}")
            return 0
        if args.command == "score":
            result_dir = score_run(args.task, args.run, args.models)
            print(f"narrative_model_eval score: PASS result={result_dir.relative_to(REPO_ROOT)}")
            return 0
        parser.error("choose --selftest, validate, run, or score")
    except EvalError as exc:
        print(f"narrative_model_eval: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


# END_BLOCK: CLI
