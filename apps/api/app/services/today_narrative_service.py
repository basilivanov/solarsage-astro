# ############################################################################
# AI_HEADER: TODAY_NARRATIVE_SERVICE — bounded, claim-bound Today narrative generation.
# ROLE: Builds a small public evidence prompt, performs one deadline-bounded
#       strict-JSON provider call, and accepts the response only atomically.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-NARRATIVE
# purpose: Generate bounded Russian narrative content for one published
#   TodaySnapshot without touching persistence, leases, projections, or HTTP.
# owns:
#   - apps/api/app/services/today_narrative_service.py
# inputs: TodaySnapshot-like row, prompt version, injectable LLM client, and
#   optional correlation/timeout controls.
# outputs: TodayNarrativeSuccess with canonical content_json, or typed
#   TodayNarrativeFailure with a stable error code and latency.
# dependencies: TodaySnapshot JSON shape, Settings, existing LLM provider layer,
#   and structured backend logging.
# side_effects: one bounded provider call and three guarded generation-boundary
#   log events; no database writes, lease transitions, or template fallback.
# emitted_logs: day.narrative_generation_started,
#   day.narrative_generation_completed, day.narrative_generation_failed.
# invariants: only selected public units enter the prompt; date-aware EventTime
#   instants use the same local timezone semantics as the public projection;
#   content is accepted atomically; claims bind to selected event IDs;
#   unavailable is honest on any provider, schema, claim, capability, or
#   deadline failure.
# failure_policy: return TodayNarrativeFailure; never return partial content or
#   generated template text; cancellation is propagated to the caller.
# END_MODULE_CONTRACT: M-TODAY-NARRATIVE

# START_MODULE_MAP: M-TODAY-NARRATIVE
# public_entrypoints:
#   - TodayNarrativeErrorCode
#   - TodayNarrativeSuccess
#   - TodayNarrativeFailure
#   - build_today_narrative_prompt
#   - generate_today_narrative
# semantic_blocks:
#   - PROMPT: selected-unit and capability-bounded prompt construction.
#   - EVENT_TIME: clock and absolute instant projection for prompt evidence.
#   - CALL: injectable provider invocation and existing provider adapter.
#   - VALIDATE: exact response shape and claim binding.
#   - CAPABILITY: deterministic text restrictions by birth-time capability.
#   - LOGGING: guarded generation lifecycle events without narrative text.
# owned_tests:
#   - apps/api/tests/test_today_narrative_service.py
# END_MODULE_MAP: M-TODAY-NARRATIVE

from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone as dt_timezone
from enum import StrEnum
from typing import Any, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.core.logging import (
    bind_log_context,
    correlation_id_var,
    log_block,
    log_event,
)
from app.services.llm_service import LLMService
from app.services.narrative_sanitizer import sanitize_narrative_text


_MISSING = object()
_BIRTH_MODES = frozenset({"exact", "bucket", "unknown"})
_POLARITIES = frozenset({"supportive", "tense", "mixed"})
_DAY_STATES = frozenset({"convergence_today", "quiet_day"})
_DAY_TONES = frozenset({"steady", "supportive", "mixed", "tense"})
_NARRATIVE_FIELDS = ("summary", "meaning", "action")
_CAPABILITY_KEYS = ("houses", "angles", "lots", "exact_timing")


class TodayNarrativeErrorCode(StrEnum):
    """Stable failure values handed to the narrative lease consumer."""

    TIMEOUT = "timeout"
    SCHEMA_INVALID = "schema_invalid"
    CLAIM_BINDING = "claim_binding"
    CAPABILITY_VIOLATION = "capability_violation"
    PROVIDER_ERROR = "provider_error"
    INTERNAL_ERROR = "internal_error"


# A short alias is useful to callers that name the enum by its domain rather
# than by the Today prefix.  The returned public value is always a string.
NarrativeErrorCode = TodayNarrativeErrorCode


@dataclass(frozen=True)
class TodayNarrativeSuccess:
    """Atomically validated narrative content."""

    content_json: dict[str, Any]
    output_tokens: int | None
    latency_ms: int


@dataclass(frozen=True)
class TodayNarrativeFailure:
    """Typed unavailable outcome; no partial narrative is carried."""

    error_code: str
    latency_ms: int


class TodayNarrativeLLM(Protocol):
    """Minimal injectable provider surface used by tests and future callers."""

    async def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> object:
        """Return a JSON string or a provider response carrying one."""


class _NarrativeInputError(ValueError):
    """Internal fail-closed error while reading a published snapshot."""


class _NarrativeValidationError(ValueError):
    """Internal validation error with a public typed failure code."""

    def __init__(self, code: TodayNarrativeErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True)
class _PromptEvent:
    event_id: str
    kind: str
    sphere: str
    polarity: str
    event_time: dict[str, Any]


@dataclass(frozen=True)
class _NarrativeBlock:
    block_id: str
    event_ids: tuple[str, ...]
    events: tuple[_PromptEvent, ...]
    primary_sphere: str | None = None
    secondary_sphere: str | None = None
    polarity: str | None = None


@dataclass(frozen=True)
class _SnapshotContext:
    snapshot_id: str
    state: str
    day_tone: str
    birth_mode: str
    capabilities: dict[str, bool]
    convergences: tuple[_NarrativeBlock, ...]
    main_event: _NarrativeBlock | None
    impulses: tuple[_NarrativeBlock, ...]


@dataclass(frozen=True)
class _ProviderText:
    text: str
    output_tokens: int | None


_CLOCK_TEXT_RE = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)")
_HOUSE_TEXT_RE = re.compile(r"(?<!\w)(?:дом\w*|house\w*)", re.IGNORECASE)
_ANGLE_TEXT_RE = re.compile(
    r"(?<!\w)(?:асцендент\w*|ascendant\w*|asc|mc)(?!\w)",
    re.IGNORECASE,
)
_LOT_TEXT_RE = re.compile(r"(?<!\w)(?:лот\w*|жреб\w*|lot\w*)", re.IGNORECASE)


def _mapping(value: object, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise _NarrativeInputError(reason)
    return value


def _sequence(value: object, reason: str) -> list[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise _NarrativeInputError(reason)
    return list(value)


def _value(mapping: Mapping[str, Any], *keys: str, default: object = _MISSING) -> object:
    for key in keys:
        if key in mapping:
            return mapping[key]
    if default is not _MISSING:
        return default
    raise _NarrativeInputError(f"missing_{keys[0]}")


def _text(value: object, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _NarrativeInputError(reason)
    return value


def _optional_text(value: object, reason: str) -> str | None:
    if value is None:
        return None
    return _text(value, reason)


def _enum_text(value: object, allowed: frozenset[str], reason: str) -> str:
    result = _text(value, reason)
    if result not in allowed:
        raise _NarrativeInputError(reason)
    return result


def _id_list(value: object, reason: str) -> tuple[str, ...]:
    values = _sequence(value, reason)
    result = tuple(_text(item, reason) for item in values)
    if len(result) != len(set(result)):
        raise _NarrativeInputError(f"duplicate_{reason}")
    if not result:
        raise _NarrativeInputError(reason)
    return result


def _parse_source_time(value: object, reason: str) -> date | datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise _NarrativeInputError(reason)
        return value
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise _NarrativeInputError(reason)
    try:
        normalized = value.replace("Z", "+00:00")
        if "T" in normalized or " " in normalized:
            parsed_datetime = datetime.fromisoformat(normalized)
            if parsed_datetime.tzinfo is None or parsed_datetime.utcoffset() is None:
                raise _NarrativeInputError(reason)
            return parsed_datetime
        return date.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        raise _NarrativeInputError(reason) from exc


def _local_time(value: date | datetime, timezone: ZoneInfo, reason: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise _NarrativeInputError(reason)
    return value.astimezone(timezone)


def _part_of_day(hour: int) -> str:
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 18:
        return "day"
    return "evening"


def _midpoint(first: datetime, second: datetime) -> datetime:
    """Return the absolute-window midpoint in the first instant's timezone."""

    first_utc = first.astimezone(dt_timezone.utc)
    second_utc = second.astimezone(dt_timezone.utc)
    return (first_utc + (second_utc - first_utc) / 2).astimezone(first.tzinfo)


# START_BLOCK: EVENT_TIME
def _event_time(unit: Mapping[str, Any], birth_mode: str, timezone: ZoneInfo) -> dict[str, Any]:
    """Project one factor window into the deterministic public EventTime shape."""

    exact_at = _parse_source_time(unit.get("exact_at", unit.get("exactAt")), "factor_exact_at")
    active_from = _parse_source_time(
        unit.get("active_from", unit.get("activeFrom")),
        "factor_active_from",
    )
    active_until = _parse_source_time(
        unit.get("active_until", unit.get("activeUntil")),
        "factor_active_until",
    )

    if birth_mode == "exact":
        peak = _local_time(exact_at, timezone, "event_time_exact_missing") if isinstance(exact_at, datetime) else None
        if peak is None and isinstance(active_from, datetime) and isinstance(active_until, datetime):
            peak = _midpoint(
                _local_time(active_from, timezone, "event_time_exact_window"),
                _local_time(active_until, timezone, "event_time_exact_window"),
            )
        if peak is None:
            raise _NarrativeInputError("event_time_exact_missing")
        local_start = _local_time(active_from, timezone, "event_time_exact_window") if isinstance(active_from, datetime) else None
        local_end = _local_time(active_until, timezone, "event_time_exact_window") if isinstance(active_until, datetime) else None
        return {
            "mode": "exact",
            "peak": peak.strftime("%H:%M"),
            "start": None if local_start is None else local_start.strftime("%H:%M"),
            "end": None if local_end is None else local_end.strftime("%H:%M"),
            "peakAt": peak.isoformat(),
            "startAt": None if local_start is None else local_start.isoformat(),
            "endAt": None if local_end is None else local_end.isoformat(),
            "partOfDay": None,
        }

    if birth_mode == "bucket":
        peak = _local_time(exact_at, timezone, "event_time_bucket_missing") if isinstance(exact_at, datetime) else None
        if peak is None and isinstance(active_from, datetime) and isinstance(active_until, datetime):
            peak = _midpoint(
                _local_time(active_from, timezone, "event_time_bucket_window"),
                _local_time(active_until, timezone, "event_time_bucket_window"),
            )
        if peak is None:
            raise _NarrativeInputError("event_time_bucket_missing")
        return {
            "mode": "partofday",
            "peak": None,
            "start": None,
            "end": None,
            "peakAt": None,
            "startAt": None,
            "endAt": None,
            "partOfDay": _part_of_day(peak.hour),
        }

    if isinstance(exact_at, datetime):
        local_exact = _local_time(exact_at, timezone, "event_time_unknown")
        return {
            "mode": "partofday",
            "peak": None,
            "start": None,
            "end": None,
            "peakAt": None,
            "startAt": None,
            "endAt": None,
            "partOfDay": _part_of_day(local_exact.hour),
        }
    if isinstance(exact_at, date):
        return {
            "mode": "date",
            "peak": None,
            "start": None,
            "end": None,
            "peakAt": None,
            "startAt": None,
            "endAt": None,
            "partOfDay": None,
        }
    if isinstance(active_from, datetime) and isinstance(active_until, datetime):
        midpoint = _midpoint(
            _local_time(active_from, timezone, "event_time_unknown_window"),
            _local_time(active_until, timezone, "event_time_unknown_window"),
        )
        return {
            "mode": "partofday",
            "peak": None,
            "start": None,
            "end": None,
            "peakAt": None,
            "startAt": None,
            "endAt": None,
            "partOfDay": _part_of_day(midpoint.hour),
        }
    if isinstance(active_from, date) or isinstance(active_until, date):
        return {
            "mode": "date",
            "peak": None,
            "start": None,
            "end": None,
            "peakAt": None,
            "startAt": None,
            "endAt": None,
            "partOfDay": None,
        }
    raise _NarrativeInputError("event_time_unknown_missing")


# END_BLOCK: EVENT_TIME


def _snapshot_id(snapshot: object) -> str:
    value = getattr(snapshot, "id", None)
    if value is None:
        return "unknown"
    return str(value)


def _factor_units(snapshot: object) -> tuple[dict[str, Mapping[str, Any]], ZoneInfo]:
    canonical_input = _mapping(getattr(snapshot, "canonical_input_json", None), "canonical_input")
    raw_units = _sequence(_value(canonical_input, "factor_units", "factorUnits"), "factor_units")
    units: dict[str, Mapping[str, Any]] = {}
    for raw_unit in raw_units:
        unit = _mapping(raw_unit, "factor_unit")
        event_id = _text(_value(unit, "canonical_event_id", "canonicalEventId"), "factor_event_id")
        if event_id in units:
            raise _NarrativeInputError("duplicate_factor_event_id")
        units[event_id] = unit

    timezone_name = _text(getattr(snapshot, "timezone", None), "timezone")
    try:
        timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise _NarrativeInputError("timezone") from exc
    return units, timezone


def _event_for_selection(
    event_id: str,
    selection: Mapping[str, Any],
    units: Mapping[str, Mapping[str, Any]],
    birth_mode: str,
    timezone: ZoneInfo,
    *,
    polarity: str | None = None,
) -> _PromptEvent:
    if event_id not in units:
        raise _NarrativeInputError("foreign_event_reference")
    unit = units[event_id]
    kind = _optional_text(unit.get("event_class", unit.get("eventClass")), "factor_event_kind")
    if kind is None:
        kind = _text(unit.get("technique_horizon", unit.get("techniqueHorizon")), "factor_event_kind")
    selected_sphere = _text(_value(selection, "sphere"), "selected_sphere")
    selected_polarity = polarity or _text(_value(selection, "polarity"), "selected_polarity")
    if selected_polarity not in _POLARITIES:
        raise _NarrativeInputError("selected_polarity")
    return _PromptEvent(
        event_id=event_id,
        kind=kind,
        sphere=selected_sphere,
        polarity=selected_polarity,
        event_time=_event_time(unit, birth_mode, timezone),
    )


def _group_events(
    group: Mapping[str, Any],
    units: Mapping[str, Mapping[str, Any]],
    birth_mode: str,
    timezone: ZoneInfo,
) -> _NarrativeBlock:
    group_id = _text(_value(group, "group_id", "groupId"), "group_id")
    event_ids = _id_list(_value(group, "evidence_event_ids", "evidenceEventIds"), "evidence_event_ids")
    primary_sphere = _text(_value(group, "primary_sphere", "primarySphere"), "selected_sphere")
    secondary_sphere = _optional_text(
        _value(group, "secondary_sphere", "secondarySphere", default=None),
        "selected_sphere",
    )
    group_polarity = _enum_text(_value(group, "polarity"), _POLARITIES, "selected_polarity")
    raw_anchor = _value(group, "anchor_event_id", "anchorEventId", default=None)
    anchor = event_ids[0] if raw_anchor is None else _text(raw_anchor, "anchor_event_id")
    if anchor not in event_ids:
        raise _NarrativeInputError("foreign_event_reference")

    events: list[_PromptEvent] = []
    for event_id in event_ids:
        is_anchor = event_id == anchor
        sphere = primary_sphere if is_anchor or secondary_sphere is None else secondary_sphere
        unit_polarity = units[event_id].get("polarity") if event_id in units else None
        event_polarity = group_polarity
        if not is_anchor and isinstance(unit_polarity, str) and unit_polarity in _POLARITIES:
            event_polarity = unit_polarity
        selection = {"sphere": sphere, "polarity": event_polarity}
        events.append(_event_for_selection(event_id, selection, units, birth_mode, timezone, polarity=event_polarity))
    return _NarrativeBlock(
        block_id=group_id,
        event_ids=event_ids,
        events=tuple(events),
        primary_sphere=primary_sphere,
        secondary_sphere=secondary_sphere,
        polarity=group_polarity,
    )


def _single_event_block(
    value: Mapping[str, Any],
    units: Mapping[str, Mapping[str, Any]],
    birth_mode: str,
    timezone: ZoneInfo,
) -> _NarrativeBlock:
    event_id = _text(_value(value, "event_id", "eventId"), "selected_event_id")
    event = _event_for_selection(event_id, value, units, birth_mode, timezone)
    return _NarrativeBlock(block_id=event_id, event_ids=(event_id,), events=(event,))


def _birth_context(snapshot: object, canonical_input: Mapping[str, Any]) -> tuple[str, dict[str, bool]]:
    raw_birth = _mapping(_value(canonical_input, "birth_time", "birthTime"), "birth_time")
    raw_mode = getattr(snapshot, "birth_time_mode", None)
    mode = _enum_text(raw_mode if raw_mode is not None else _value(raw_birth, "mode"), _BIRTH_MODES, "birth_mode")
    canonical_mode = _value(raw_birth, "mode", default=mode)
    if canonical_mode != mode:
        raise _NarrativeInputError("birth_mode")
    raw_capabilities = _mapping(_value(raw_birth, "capabilities"), "birth_capabilities")
    capabilities: dict[str, bool] = {}
    for key in _CAPABILITY_KEYS:
        aliases = (key, "exactTiming") if key == "exact_timing" else (key,)
        value = _value(raw_capabilities, *aliases)
        if type(value) is not bool:
            raise _NarrativeInputError("birth_capabilities")
        capabilities[key] = value
    return mode, capabilities


def _snapshot_context(snapshot: object) -> _SnapshotContext:
    deterministic_result = _mapping(getattr(snapshot, "deterministic_result_json", None), "deterministic_result")
    state = _enum_text(_value(deterministic_result, "state"), _DAY_STATES, "state")
    day_tone = _enum_text(
        _value(deterministic_result, "day_tone", "dayTone"),
        _DAY_TONES,
        "day_tone",
    )
    selected = _mapping(_value(deterministic_result, "selected"), "selected")
    raw_convergences = _sequence(_value(selected, "convergences"), "convergences")
    raw_impulses = _sequence(_value(selected, "impulses"), "impulses")
    if len(raw_convergences) > 3 or len(raw_impulses) > 3:
        raise _NarrativeInputError("selection_cap")

    units, timezone = _factor_units(snapshot)
    canonical_input = _mapping(getattr(snapshot, "canonical_input_json", None), "canonical_input")
    birth_mode, capabilities = _birth_context(snapshot, canonical_input)
    groups = tuple(
        _group_events(_mapping(value, "convergence"), units, birth_mode, timezone)
        for value in raw_convergences
    )
    if len({group.block_id for group in groups}) != len(groups):
        raise _NarrativeInputError("duplicate_group_id")

    raw_main = _value(selected, "main_event", "mainEvent", default=None)
    main_event = None if raw_main is None else _single_event_block(
        _mapping(raw_main, "main_event"), units, birth_mode, timezone
    )
    impulses = tuple(
        _single_event_block(_mapping(value, "impulse"), units, birth_mode, timezone)
        for value in raw_impulses
    )
    all_event_ids = [event_id for group in groups for event_id in group.event_ids]
    if main_event is not None:
        all_event_ids.extend(main_event.event_ids)
    all_event_ids.extend(event_id for impulse in impulses for event_id in impulse.event_ids)
    if len(all_event_ids) != len(set(all_event_ids)):
        raise _NarrativeInputError("duplicate_selected_event_id")
    selected_ids = _id_list(_value(selected, "selected_unit_ids", "selectedUnitIds"), "selected_unit_ids")
    if set(selected_ids) != set(all_event_ids):
        raise _NarrativeInputError("selected_unit_ids")
    return _SnapshotContext(
        snapshot_id=_snapshot_id(snapshot),
        state=state,
        day_tone=day_tone,
        birth_mode=birth_mode,
        capabilities=capabilities,
        convergences=groups,
        main_event=main_event,
        impulses=impulses,
    )


# START_BLOCK: PROMPT
def _build_prompt(context: _SnapshotContext, prompt_version: str) -> str:
    prompt_input: dict[str, Any] = {
        "promptVersion": prompt_version,
        "state": context.state,
        "dayTone": context.day_tone,
        "convergences": [
            {
                "groupId": group.block_id,
                "primarySphere": group.primary_sphere,
                "secondarySphere": group.secondary_sphere,
                "polarity": group.polarity,
                "evidenceEventIds": list(group.event_ids),
                "evidence": [
                    {
                        "kind": event.kind,
                        "sphere": event.sphere,
                        "polarity": event.polarity,
                        "eventTime": event.event_time,
                    }
                    for event in group.events
                ],
            }
            for group in context.convergences
        ],
        "mainEvent": (
            None
            if context.main_event is None
            else {
                "eventId": context.main_event.block_id,
                "kind": context.main_event.events[0].kind,
                "sphere": context.main_event.events[0].sphere,
                "polarity": context.main_event.events[0].polarity,
                "eventTime": context.main_event.events[0].event_time,
            }
        ),
        "impulses": [
            {
                "eventId": impulse.block_id,
                "kind": impulse.events[0].kind,
                "sphere": impulse.events[0].sphere,
                "polarity": impulse.events[0].polarity,
                "eventTime": impulse.events[0].event_time,
            }
            for impulse in context.impulses
        ],
        "birthTime": {
            "mode": context.birth_mode,
            "capabilities": context.capabilities,
        },
    }
    serialized_input = json.dumps(
        prompt_input,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    def _template_block(event_ids: Sequence[str]) -> dict[str, Any]:
        return {
            "summary": {"text": "", "sourceEventIds": list(event_ids)},
            "meaning": None,
            "action": None,
        }

    response_template = {
        "convergences": {
            group.block_id: _template_block(group.event_ids) for group in context.convergences
        },
        "main_event": (
            None
            if context.main_event is None
            else _template_block(context.main_event.event_ids)
        ),
        "impulses": {
            impulse.block_id: _template_block(impulse.event_ids) for impulse in context.impulses
        },
    }
    serialized_template = json.dumps(
        response_template,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"""Ты пишешь короткий персональный текст для экрана Today на русском языке.

Правила источников:
- Используй только факты из входа ниже; ничего не вычисляй и не добавляй.
- Не изменяй state, dayTone, сферы, polarity, event IDs или EventTime.
- В каждом ненулевом claim укажи один или несколько sourceEventIds только из
  соответствующего блока. Не выдумывай IDs и не оставляй список пустым.
- Текст claim никогда не должен содержать часы, даты, окна или длительности:
  EventTime — только display-only данные для интерфейса. Формулируй текст claim
  только общими словами по kind, sphere и polarity; не упоминай house, angle или
  lot, если соответствующая capability не равна true.
- Эти правила относятся к summary.text: только русский язык, не более 220
  символов, практичный короткий текст без категоричных предсказаний. Не
  выдумывай реальные события, чувства, исходы или неподтверждённые детали.
- Учитывай mode и capabilities: не упоминай недоступные детали расчёта.
- Никогда не пиши служебные имена или шаблоны: Transit_, Natal_, Planet,
  «M, Mars» и любые перечисления вида «M, <Planet>». Если факт нельзя
  назвать обычными русскими словами, не используй этот факт; summary всё
  равно должен опираться на остальные разрешённые evidence.

Верни строго один JSON-объект без markdown и без дополнительных ключей.
Для каждого присутствующего блока summary — JSON-объект с ключами text и
sourceEventIds; не возвращай строку вместо объекта. Не меняй ключи блоков,
sourceEventIds, meaning или action. Если mainEvent во входе равен null, оставь
main_event равным null.

Вход:
{serialized_input}

Точный JSON-шаблон ответа для этого snapshot:
{serialized_template}
Замени только пустые значения summary.text на текст и верни этот JSON. Сохрани
все ключи, идентификаторы и массивы sourceEventIds; не добавляй и не удаляй
поля. В каждом присутствующем блоке summary.text обязателен.
"""


def build_today_narrative_prompt(snapshot: object, *, prompt_version: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.build_today_narrative_prompt
    # purpose: Build the bounded prompt from selected public snapshot units.
    # inputs: snapshot — published TodaySnapshot-like row; prompt_version — lease identity.
    # returns: str — Russian strict-JSON provider prompt with no full ledger.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for malformed snapshot or prompt version.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.build_today_narrative_prompt
    if not isinstance(prompt_version, str) or not prompt_version.strip() or len(prompt_version) > 64:
        raise ValueError("today_narrative:prompt_version")
    try:
        context = _snapshot_context(snapshot)
    except _NarrativeInputError as exc:
        raise ValueError(f"today_narrative:{exc}") from exc
    return _build_prompt(context, prompt_version)


# END_BLOCK: PROMPT


# START_BLOCK: CALL
def _provider_method(llm: object) -> tuple[Callable[..., object], str]:
    for name in ("generate_json", "generate", "complete", "_generate_text"):
        candidate = getattr(llm, name, None)
        if callable(candidate):
            return candidate, name
    if callable(llm):
        return llm, "__call__"
    raise TypeError("llm client has no supported call method")


def _call_kwargs(
    method: Callable[..., object],
    method_name: str,
    max_output_tokens: int,
    timeout_seconds: float,
    deadline_at: float,
) -> dict[str, Any]:
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        parameters = {}
    accepts_kwargs = any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values())

    def supports(name: str) -> bool:
        return accepts_kwargs or name in parameters

    kwargs: dict[str, Any] = {}
    if method_name == "_generate_text":
        if supports("max_tokens"):
            kwargs["max_tokens"] = max_output_tokens
        if supports("json_object"):
            kwargs["json_object"] = True
        if supports("deadline_at"):
            kwargs["deadline_at"] = deadline_at
        return kwargs
    if supports("max_output_tokens"):
        kwargs["max_output_tokens"] = max_output_tokens
    elif supports("max_tokens"):
        kwargs["max_tokens"] = max_output_tokens
    if supports("timeout_seconds"):
        kwargs["timeout_seconds"] = timeout_seconds
    elif supports("timeout"):
        kwargs["timeout"] = timeout_seconds
    if supports("deadline_at"):
        kwargs["deadline_at"] = deadline_at
    if supports("json_object"):
        kwargs["json_object"] = True
    return kwargs


async def _invoke_provider(
    llm: object | None,
    prompt: str,
    *,
    max_output_tokens: int,
    timeout_seconds: float,
) -> object:
    client = LLMService() if llm is None else llm
    method, method_name = _provider_method(client)
    deadline_at = time.monotonic() + timeout_seconds
    kwargs = _call_kwargs(method, method_name, max_output_tokens, timeout_seconds, deadline_at)
    result = method(prompt, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _output_tokens(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _provider_text(value: object) -> _ProviderText | None:
    if value is None:
        return None
    if isinstance(value, str):
        return _ProviderText(value, None)
    if isinstance(value, bytes):
        return _ProviderText(value.decode("utf-8"), None)
    if isinstance(value, Mapping):
        raw_text: object = _MISSING
        for key in ("text", "content", "output", "response"):
            if key in value:
                raw_text = value[key]
                break
        raw_tokens = value.get("output_tokens", value.get("outputTokens"))
        usage = value.get("usage")
        if raw_tokens is None and isinstance(usage, Mapping):
            raw_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
        if isinstance(raw_text, str):
            return _ProviderText(raw_text, _output_tokens(raw_tokens))
        return None
    raw_text = getattr(value, "text", getattr(value, "content", None))
    if isinstance(raw_text, str):
        return _ProviderText(raw_text, _output_tokens(getattr(value, "output_tokens", None)))
    return None


# END_BLOCK: CALL


# START_BLOCK: VALIDATE
def _claim(value: object, allowed_event_ids: frozenset[str]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"text", "sourceEventIds"}:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    text = value["text"]
    source_ids = value["sourceEventIds"]
    if not isinstance(text, str) or not text.strip():
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    clean_text = sanitize_narrative_text(text)
    if clean_text is None:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    if not isinstance(source_ids, list) or not source_ids:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.CLAIM_BINDING)
    if any(not isinstance(event_id, str) or not event_id.strip() for event_id in source_ids):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.CLAIM_BINDING)
    if len(source_ids) != len(set(source_ids)) or not set(source_ids).issubset(allowed_event_ids):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.CLAIM_BINDING)
    return {"text": clean_text, "sourceEventIds": list(source_ids)}


def _block_content(
    value: object,
    expected_ids: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_NARRATIVE_FIELDS):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    allowed_event_ids = frozenset(expected_ids)
    result = {
        field: _claim(value[field], allowed_event_ids)
        for field in _NARRATIVE_FIELDS
    }
    summary = result["summary"]
    if summary is not None and len(summary["text"]) > 220:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    return result


def _validate_response(raw_text: str, context: _SnapshotContext) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_text)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID) from exc
    if not isinstance(parsed, dict) or set(parsed) != {"convergences", "main_event", "impulses"}:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)

    raw_convergences = parsed["convergences"]
    raw_impulses = parsed["impulses"]
    if not isinstance(raw_convergences, dict) or not isinstance(raw_impulses, dict):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    expected_groups = {group.block_id: group for group in context.convergences}
    if set(raw_convergences) != set(expected_groups):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    expected_impulses = {impulse.block_id: impulse for impulse in context.impulses}
    if set(raw_impulses) != set(expected_impulses):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)

    main_value = parsed["main_event"]
    if context.main_event is None:
        if main_value is not None:
            raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
        main_content = None
    else:
        if main_value is None:
            raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
        main_content = _block_content(main_value, context.main_event.event_ids)

    content = {
        "convergences": {
            group_id: _block_content(raw_convergences[group_id], group.event_ids)
            for group_id, group in expected_groups.items()
        },
        "main_event": main_content,
        "impulses": {
            event_id: _block_content(raw_impulses[event_id], impulse.event_ids)
            for event_id, impulse in expected_impulses.items()
        },
    }
    return content


# END_BLOCK: VALIDATE


# START_BLOCK: CAPABILITY
def _claim_texts(content: Mapping[str, Any]) -> list[str]:
    texts: list[str] = []
    for group in content["convergences"].values():
        texts.extend(claim["text"] for claim in group.values() if claim is not None)
    main_event = content["main_event"]
    if main_event is not None:
        texts.extend(claim["text"] for claim in main_event.values() if claim is not None)
    for impulse in content["impulses"].values():
        texts.extend(claim["text"] for claim in impulse.values() if claim is not None)
    return texts


def _validate_capabilities(content: Mapping[str, Any], context: _SnapshotContext) -> None:
    banned: list[re.Pattern[str]] = [_CLOCK_TEXT_RE]
    if context.birth_mode != "exact" or not context.capabilities["houses"]:
        banned.append(_HOUSE_TEXT_RE)
    if context.birth_mode != "exact" or not context.capabilities["angles"]:
        banned.append(_ANGLE_TEXT_RE)
    if context.birth_mode != "exact" or not context.capabilities["lots"]:
        banned.append(_LOT_TEXT_RE)
    for text in _claim_texts(content):
        if any(pattern.search(text) is not None for pattern in banned):
            raise _NarrativeValidationError(TodayNarrativeErrorCode.CAPABILITY_VIOLATION)


# END_BLOCK: CAPABILITY


def _latency_ms(clock: Callable[[], float], started_at: float) -> int:
    return max(0, int(round((clock() - started_at) * 1000)))


# START_BLOCK: LOGGING
@contextmanager
def _correlation_scope(correlation_id: str | None):
    previous = correlation_id_var.get()
    if correlation_id:
        try:
            bind_log_context(correlation_id=correlation_id)
        except Exception:
            pass
    try:
        yield
    finally:
        try:
            correlation_id_var.set(previous)
        except Exception:
            pass


def _safe_log(event: str, *, payload: dict[str, Any], duration_ms: int | None = None) -> None:
    try:
        with log_block(slice="W-TODAY-CONVERGENCE-REWRITE", module="M-TODAY-NARRATIVE", block="GENERATION"):
            log_event(event, payload=payload, duration_ms=duration_ms)
    except Exception:
        pass


def _log_started(context: _SnapshotContext | None, snapshot_identifier: str, prompt_version: str) -> None:
    _safe_log(
        "day.narrative_generation_started",
        payload={
            "snapshot_id": snapshot_identifier,
            "prompt_version": prompt_version,
            "convergence_count": 0 if context is None else len(context.convergences),
            "main_event_present": 0 if context is None or context.main_event is None else 1,
            "impulse_count": 0 if context is None else len(context.impulses),
        },
    )


def _log_completed(
    context: _SnapshotContext,
    snapshot_identifier: str,
    prompt_version: str,
    latency_ms: int,
    output_tokens: int | None,
    claims_count: int,
) -> None:
    _safe_log(
        "day.narrative_generation_completed",
        payload={
            "snapshot_id": snapshot_identifier,
            "prompt_version": prompt_version,
            "latency_ms": latency_ms,
            "claims_count": claims_count,
            "output_tokens": output_tokens,
        },
        duration_ms=latency_ms,
    )


def _log_failed(snapshot_identifier: str, prompt_version: str, error_code: str, latency_ms: int) -> None:
    _safe_log(
        "day.narrative_generation_failed",
        payload={
            "snapshot_id": snapshot_identifier,
            "prompt_version": prompt_version,
            "error_code": error_code,
            "latency_ms": latency_ms,
        },
        duration_ms=latency_ms,
    )


# END_BLOCK: LOGGING


def _count_claims(content: Mapping[str, Any]) -> int:
    return len(_claim_texts(content))


def _provider_error_code(exc: BaseException) -> TodayNarrativeErrorCode:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return TodayNarrativeErrorCode.TIMEOUT
    if "timeout" in type(exc).__name__.lower():
        return TodayNarrativeErrorCode.TIMEOUT
    return TodayNarrativeErrorCode.PROVIDER_ERROR


async def generate_today_narrative(
    snapshot: object,
    *,
    prompt_version: str,
    llm: object | None = None,
    correlation_id: str | None = None,
    timeout_seconds: float | None = None,
    clock: Callable[[], float] | None = None,
) -> TodayNarrativeSuccess | TodayNarrativeFailure:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.generate_today_narrative
    # purpose: Generate and atomically validate one bounded Today narrative.
    # inputs: snapshot — published TodaySnapshot-like row; prompt_version — lease
    #   identity; llm — injectable provider; correlation_id — caller context;
    #   timeout_seconds/clock — optional test and deadline controls.
    # returns: TodayNarrativeSuccess with canonical content_json, or
    #   TodayNarrativeFailure with timeout/provider/schema/claim/capability code.
    # side_effects: at most one bounded provider call and guarded lifecycle logs.
    # emitted_logs: day.narrative_generation_started,
    #   day.narrative_generation_completed, day.narrative_generation_failed.
    # error_behavior: returns typed failure for all expected generation errors;
    #   propagates asyncio cancellation and never emits template fallback text.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.generate_today_narrative
    active_clock = time.monotonic if clock is None else clock
    started_at = active_clock()
    snapshot_identifier = _snapshot_id(snapshot)
    context: _SnapshotContext | None = None
    context_error: _NarrativeInputError | None = None
    try:
        context = _snapshot_context(snapshot)
    except _NarrativeInputError as exc:
        context_error = exc

    with _correlation_scope(correlation_id):
        _log_started(context, snapshot_identifier, prompt_version)
        if not isinstance(prompt_version, str) or not prompt_version.strip() or len(prompt_version) > 64:
            error_code = TodayNarrativeErrorCode.SCHEMA_INVALID.value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)
        if context_error is not None or context is None:
            error_code = TodayNarrativeErrorCode.SCHEMA_INVALID.value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)

        configured_timeout = settings.today_narrative_timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            bounded_timeout = float(configured_timeout)
        except (TypeError, ValueError):
            bounded_timeout = 0.0
        if bounded_timeout <= 0:
            error_code = TodayNarrativeErrorCode.TIMEOUT.value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)

        prompt = _build_prompt(context, prompt_version)
        max_output_tokens = settings.today_narrative_max_output_tokens
        try:
            raw_response = await asyncio.wait_for(
                _invoke_provider(
                    llm,
                    prompt,
                    max_output_tokens=max_output_tokens,
                    timeout_seconds=bounded_timeout,
                ),
                timeout=bounded_timeout,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error_code = _provider_error_code(exc).value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)

        provider_text = _provider_text(raw_response)
        if provider_text is None:
            error_code = TodayNarrativeErrorCode.PROVIDER_ERROR.value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)
        try:
            content = _validate_response(provider_text.text, context)
            _validate_capabilities(content, context)
        except _NarrativeValidationError as exc:
            error_code = exc.code.value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)
        except Exception:
            error_code = TodayNarrativeErrorCode.SCHEMA_INVALID.value
            latency_ms = _latency_ms(active_clock, started_at)
            _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
            return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)

        latency_ms = _latency_ms(active_clock, started_at)
        _log_completed(
            context,
            snapshot_identifier,
            prompt_version,
            latency_ms,
            provider_text.output_tokens,
            _count_claims(content),
        )
        return TodayNarrativeSuccess(
            content_json=content,
            output_tokens=provider_text.output_tokens,
            latency_ms=latency_ms,
        )


__all__ = [
    "NarrativeErrorCode",
    "TodayNarrativeErrorCode",
    "TodayNarrativeFailure",
    "TodayNarrativeLLM",
    "TodayNarrativeSuccess",
    "build_today_narrative_prompt",
    "generate_today_narrative",
]
