# ############################################################################
# AI_HEADER: TODAY_NARRATIVE_SERVICE — grounded, claim-bound Today narrative generation.
# ROLE: Builds a small public evidence prompt from deterministic driver titles
#       and themes, performs bounded strict-JSON provider calls, and publishes
#       only sanitized, sphere/facet/polarity-grounded claims.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-NARRATIVE
# purpose: Generate bounded Russian narrative content for one published
#   TodaySnapshot without touching persistence, leases, projections, or HTTP;
#   ground each claim on deterministic driver evidence before publication.
# owns:
#   - apps/api/app/services/today_narrative_service.py
# inputs: TodaySnapshot-like row, prompt version, injectable LLM client, an
#   ondemand/pregen generation path, and optional correlation/timeout controls.
# outputs: TodayNarrativeSuccess with canonical content_json, or typed
#   TodayNarrativeFailure with a stable error code and latency.
# dependencies: TodaySnapshot JSON shape, Settings, existing LLM provider layer,
#   and structured backend logging.
# side_effects: one bounded provider call, plus one regeneration only after a
#   grounding rejection, and three guarded generation-boundary log events; no
#   database writes, lease transitions, or template fallback.
# emitted_logs: day.narrative_generation_started,
#   day.narrative_generation_completed, day.narrative_generation_failed,
#   day.narrative_claim_nulled.
# invariants: only selected public units enter the prompt; v6 provider calls use
#   the strict array schema and normalize accepted arrays into the existing
#   keyed content shape before the unchanged validators/storage boundary;
#   date-aware EventTime
#   instants use the same local timezone semantics as the public projection;
#   convergence evidence may overlap between groups and remains present in each
#   group; selected IDs validate the union while main/impulse IDs stay disjoint;
#   content is accepted atomically after grounding; claims bind to selected
#   event IDs and unsupported claims become honest nulls after one retry;
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
#   - strict_response_schema
#   - build_today_narrative_prompt
#   - generate_today_narrative
# semantic_blocks:
#   - PROMPT: selected-unit, deterministic-driver, and capability-bounded prompt construction.
#   - STRICT_SCHEMA: provider-enforced array schema and keyed-shape normalization.
#   - EVENT_TIME: clock and absolute instant projection for prompt evidence.
#   - CALL: injectable provider invocation and existing provider adapter.
#   - VALIDATE: exact response shape, claim binding, and grounding retry/nulling.
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
from functools import lru_cache
from typing import Any, Literal, Protocol, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.core.logging import (
    bind_log_context,
    correlation_id_var,
    log_block,
    log_event,
)
from app.services.llm_service import LLMService
from app.services.astro_utils import strip_prefix
from app.services.focus_title_builder import PLANET_NOMINATIVE_RU
from app.services.horizon_content_canon_service import load_horizon_content_canons
from app.services.narrative_sanitizer import (
    explain_narrative_grounding_violation,
    has_narrative_grounding_violation,
    sanitize_narrative_text,
)
from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_titles import build_today_convergence_event_title


_MISSING = object()
_BIRTH_MODES = frozenset({"exact", "bucket", "unknown"})
_POLARITIES = frozenset({"supportive", "tense", "mixed"})
_SPHERES = frozenset({
    "work",
    "finance",
    "documents",
    "relationships",
    "sport",
    "communication",
    "health",
    "home_family",
    "travel",
    "creativity",
    "study",
    "friends_goals",
})
_DAY_STATES = frozenset({"convergence_today", "quiet_day"})
_DAY_TONES = frozenset({"steady", "supportive", "mixed", "tense"})
_NARRATIVE_FIELDS = ("summary", "meaning", "action")
_CAPABILITY_KEYS = ("houses", "angles", "lots", "exact_timing")
_GROUNDING_RETRY_SUFFIX = """
Проверка grounding отклонила предыдущую версию: claim должен оставаться в
разрешённой сфере и соответствовать polarity. Повтори JSON один раз, опираясь
на title и driverThemes. Если честный summary невозможен, поставь его в null;
не заменяй его общей фразой и не показывай неподтверждённую сферу.
"""


# START_BLOCK: STRICT_SCHEMA
def strict_response_schema() -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.strict_response_schema
    # purpose: Return the provider-enforced array schema used by Today narrative.
    # inputs: none.
    # returns: fresh strict JSON Schema without dynamic object property names.
    # side_effects: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.strict_response_schema
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
        "properties": {name: claim_ref for name in _NARRATIVE_FIELDS},
        "required": list(_NARRATIVE_FIELDS),
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
                        **{name: claim_ref for name in _NARRATIVE_FIELDS},
                    },
                    "required": ["groupId", *_NARRATIVE_FIELDS],
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
                        **{name: claim_ref for name in _NARRATIVE_FIELDS},
                    },
                    "required": ["eventId", *_NARRATIVE_FIELDS],
                },
            },
        },
        "required": ["convergences", "main_event", "impulses"],
        "$defs": {"claim": claim, "block": block},
    }


# END_BLOCK: STRICT_SCHEMA

# S16: per-facet safe lexicon handed to the provider. Narrow words of OTHER
# facets trip the grounding sanitizer even when the sentence is fine, so the
# prompt tells the model exactly which concrete words each block owns.
_FACET_LEXICON: Mapping[str, tuple[str, ...]] = {
    "daily_work": ("текущие задачи", "рутина", "служба", "довести дело до конца"),
    "career_status": ("карьера", "статус", "продвижение", "публичная роль"),
    "personal_money": ("личные деньги", "доход", "расход", "накопления"),
    "shared_money": ("общий бюджет", "страховка", "наследство"),
    "purchases_transactions": ("покупка", "продажа", "цена", "сделка"),
    "financial_obligations": ("кредит", "долг", "налог", "возврат долга"),
    "admin_documents": ("заявление", "справка", "переписка", "оформление"),
    "legal_foreign_education_documents": ("юридические документы", "виза", "заграничные документы"),
    "contracts": ("договор", "контракт"),
    "financial_documents": ("счета", "финансовые документы"),
    "property_documents": ("документы на жильё", "недвижимость"),
    "romance": ("симпатия", "свидание", "романтика", "флирт"),
    "partnership": ("пара", "партнёрство", "брак", "отношения один на один"),
    "physical_energy": ("тонус", "энергия тела", "физическая активность"),
    "training_routine": ("тренировка", "режим занятий"),
    "competition_performance": ("соревнование", "выступление"),
    "everyday_contacts": ("разговоры", "переписка", "повседневные контакты"),
    "negotiations": ("переговоры", "договорённости"),
    "groups_audience": ("группа", "аудитория", "сообщество"),
    "public_speech_teaching": ("выступление", "преподавание"),
    "general_condition": ("самочувствие", "тонус", "общее состояние"),
    "symptoms_routine_treatment": ("симптомы", "лечение", "режим дня"),
    "recovery_isolation": ("отдых", "восстановление", "тишина и пауза"),
    "family_roots": ("семья", "родители", "домашняя база"),
    "housing_property": ("жильё", "бытовое пространство"),
    "relocation": ("переезд",),
    "local_travel": ("короткая поездка", "локальный маршрут"),
    "long_distance_foreign_travel": ("дальняя поездка", "заграница"),
    "self_expression": ("самовыражение", "творчество"),
    "creative_work": ("творческий проект", "творческая работа"),
    "private_inner_creativity": ("творчество в уединении",),
    "skills_courses": ("навык", "курс", "обучение"),
    "higher_education_worldview": ("высшее образование", "мировоззрение", "философия"),
    "friends_community": ("друзья", "сообщество", "единомышленники"),
    "collective_projects": ("совместный проект",),
    "long_term_goals": ("долгосрочные планы",),
}


class TodayNarrativeErrorCode(StrEnum):
    """Stable failure values handed to the narrative lease consumer."""

    TIMEOUT = "timeout"
    SCHEMA_INVALID = "schema_invalid"
    CLAIM_BINDING = "claim_binding"
    GROUNDING_VIOLATION = "grounding_violation"
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
class TodayNarrativePerson:
    """Optional person context for prompt personalization (S16); never logged."""

    first_name: str | None = None
    age: int | None = None


@dataclass(frozen=True)
class _PeriodAnchor:
    """One ongoing deterministic period (firdar/profection) as prompt background."""

    kind: str
    lord: str
    active_from: str | None
    active_until: str | None


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
    facet: str | None
    polarity: str
    event_time: dict[str, Any]
    house: int | None = None
    planets: tuple[str, ...] = ()
    title: str | None = None
    driver_themes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _NarrativeBlock:
    block_id: str
    event_ids: tuple[str, ...]
    events: tuple[_PromptEvent, ...]
    sphere: str
    facet: str | None
    polarity: str


@dataclass(frozen=True)
class _BlockGrounding:
    """Claim grounding indexed by the source facts cited by a block."""

    allowed_spheres: frozenset[str]
    allowed_facets: frozenset[str]
    polarity: str
    event_grounding: dict[str, tuple[str, str | None, str]]


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
    person: TodayNarrativePerson | None = None
    period: tuple[_PeriodAnchor, ...] = ()


@dataclass(frozen=True)
class _ProviderText:
    text: str
    output_tokens: int | None


_CLOCK_TEXT_RE = re.compile(r"(?<!\d)\d{1,2}:\d{2}(?!\d)")
_HOUSE_TEXT_RE = re.compile(r"(?<!\w)(?:дом\w*|house\w*)", re.IGNORECASE)
_HOUSE_NUMBER_RE = re.compile(r"(?<!\w)(?:дом\w*|house)\s*(\d{1,2})(?!\d)", re.IGNORECASE)
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


def _evidence_pair(value: object) -> tuple[str, str]:
    values = _sequence(value, "evidence_event_ids")
    result = tuple(_text(item, "evidence_event_id") for item in values)
    if len(result) != 2 or len(set(result)) != 2:
        raise _NarrativeInputError("evidence_pair")
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


# START_BLOCK: PERIOD_BACKGROUND
_PERIOD_KIND_LABELS: Mapping[str, str] = {
    "firdar_major": "Большой фирдар",
    "firdar_minor": "Малый фирдар",
    "annual_profection": "Годовая профекция",
    "monthly_profection": "Месячная профекция",
}


def _unit_technique(unit: Mapping[str, Any]) -> str:
    semantic = unit.get("semantic_key", unit.get("semanticKey"))
    if isinstance(semantic, str) and semantic.strip():
        try:
            parsed = json.loads(semantic)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict) and isinstance(parsed.get("technique"), str):
            return parsed["technique"]
    raw = unit.get("technique", unit.get("technique_horizon", unit.get("techniqueHorizon")))
    return raw if isinstance(raw, str) else ""


def _window_date(value: object) -> str | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    token = value[:10]
    try:
        date.fromisoformat(token)
    except ValueError:
        return None
    return token


def _period_anchors(units: Mapping[str, Mapping[str, Any]]) -> tuple[_PeriodAnchor, ...]:
    """Collect ongoing firdar/profection periods as immutable prompt background."""
    anchors: list[_PeriodAnchor] = []
    seen: set[str] = set()
    for unit in units.values():
        technique = _unit_technique(unit)
        kind = _PERIOD_KIND_LABELS.get(technique)
        if kind is None or kind in seen:
            continue
        lord_key = strip_prefix(str(unit.get("target_key", unit.get("targetKey", ""))).strip()).upper()
        lord = PLANET_NOMINATIVE_RU.get(lord_key)
        if lord is None:
            continue
        seen.add(kind)
        anchors.append(
            _PeriodAnchor(
                kind=kind,
                lord=lord,
                active_from=_window_date(unit.get("active_from", unit.get("activeFrom"))),
                active_until=_window_date(unit.get("active_until", unit.get("activeUntil"))),
            )
        )
    return tuple(anchors)


# END_BLOCK: PERIOD_BACKGROUND


# START_BLOCK: DRIVER_GROUNDING
@lru_cache(maxsize=1)
def _driver_theme_labels() -> Mapping[str, tuple[str, ...]]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._driver_theme_labels
    # purpose: Join the frozen planet-to-theme mapping with the existing human
    #   Russian theme labels used by the horizon language canon.
    # inputs: none; repository canons are resolved by their own strict loaders.
    # returns: uppercase planet key to ordered human theme labels.
    # side_effects: cached filesystem reads through canonical loaders only.
    # emitted_logs: none.
    # error_behavior: canonical loader errors propagate to the snapshot input
    #   boundary, where narrative generation fails closed.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._driver_theme_labels
    convergence_canon = load_today_convergence_canon()
    language_canon = load_horizon_content_canons().language
    labels: dict[str, tuple[str, ...]] = {}
    for planet, theme_keys in convergence_canon.target_planet_themes.items():
        human_labels: list[str] = []
        for theme_key in theme_keys:
            theme = cast(Mapping[str, Any], language_canon.themes).get(theme_key)
            label = getattr(theme, "label", None)
            if not isinstance(label, str) or not label.strip():
                raise ValueError("driver_theme_label")
            human_labels.append(label.strip())
        if not human_labels:
            raise ValueError("driver_theme_labels")
        labels[planet] = tuple(dict.fromkeys(human_labels))
    return labels


def _driver_themes(unit: Mapping[str, Any]) -> tuple[str, ...]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._driver_themes
    # purpose: Project only canonical human themes for the source and named
    # target planets of one deterministic factor unit.
    # inputs: normalized factor-unit mapping.
    # returns: stable, deduplicated human theme labels; empty for non-planetary
    #   or unknown drivers.
    # side_effects: cached canon reads on first use.
    # emitted_logs: none.
    # error_behavior: malformed canon data raises the internal input error;
    #   unknown driver keys simply have no themes.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._driver_themes
    try:
        labels = _driver_theme_labels()
    except Exception as exc:
        raise _NarrativeInputError("driver_themes") from exc

    result: list[str] = []
    for raw_key in (unit.get("source_key"), unit.get("target_key")):
        if raw_key is None:
            continue
        normalized_key = strip_prefix(str(raw_key).strip()).upper()
        for label in labels.get(normalized_key, ()):
            if label not in result:
                result.append(label)
    return tuple(result)


def _block_grounding(block: _NarrativeBlock) -> _BlockGrounding:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._block_grounding
    # purpose: Collect one sphere/facet contract and per-source polarity for
    #   one narrative block.
    # inputs: validated narrative block.
    # returns: immutable sphere/facet/polarity grounding indexed by event ID.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed internal block data raises the validation error.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._block_grounding
    if not block.events or block.sphere not in _SPHERES:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.GROUNDING_VIOLATION)
    if any(event.sphere != block.sphere for event in block.events):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.GROUNDING_VIOLATION)
    event_facets = {event.facet for event in block.events}
    if event_facets != {block.facet}:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.GROUNDING_VIOLATION)
    if block.polarity not in _POLARITIES or any(
        event.polarity not in _POLARITIES for event in block.events
    ):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.GROUNDING_VIOLATION)
    facets = frozenset({block.facet} if block.facet is not None else set())
    if has_narrative_grounding_violation(
        "",
        allowed_spheres={block.sphere},
        allowed_facets=facets,
        polarity=block.polarity,
    ):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.GROUNDING_VIOLATION)
    return _BlockGrounding(
        allowed_spheres=frozenset({block.sphere}),
        allowed_facets=facets,
        polarity=block.polarity,
        event_grounding={
            event.event_id: (event.sphere, event.facet, event.polarity)
            for event in block.events
        },
    )


def _claim_grounding(
    grounding: _BlockGrounding,
    source_ids: Sequence[str],
) -> tuple[frozenset[str], frozenset[str], str]:
    """Narrow a block contract to the facts cited by one claim."""

    source_context = [grounding.event_grounding[event_id] for event_id in source_ids]
    spheres = frozenset(item[0] for item in source_context)
    facets = frozenset(item[1] for item in source_context if item[1] is not None)
    polarities = {item[2] for item in source_context}
    polarity = next(iter(polarities)) if len(polarities) == 1 else "mixed"
    return spheres, facets, polarity


def _prompt_planets(unit: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for key in ("source_key", "sourceKey", "target_key", "targetKey"):
        value = unit.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        normalized = strip_prefix(value.strip()).upper()
        if not normalized or normalized.startswith("ACTIVATION-"):
            continue
        if normalized not in values:
            values.append(normalized)
    return tuple(values)


def _prompt_house(unit: Mapping[str, Any]) -> int | None:
    value = unit.get("house")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 12:
        return None
    return value


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
    selected_facet = _optional_text(
        _value(selection, "facet", default=None),
        "selected_facet",
    )
    selected_polarity = polarity or _text(_value(selection, "polarity"), "selected_polarity")
    if selected_polarity not in _POLARITIES:
        raise _NarrativeInputError("selected_polarity")
    return _PromptEvent(
        event_id=event_id,
        kind=kind,
        sphere=selected_sphere,
        facet=selected_facet,
        polarity=selected_polarity,
        event_time=_event_time(unit, birth_mode, timezone),
        house=_prompt_house(unit),
        planets=_prompt_planets(unit),
        title=build_today_convergence_event_title(unit),
        driver_themes=_driver_themes(unit),
    )


def _group_events(
    group: Mapping[str, Any],
    units: Mapping[str, Mapping[str, Any]],
    birth_mode: str,
    timezone: ZoneInfo,
) -> _NarrativeBlock:
    group_id = _text(_value(group, "group_id", "groupId"), "group_id")
    event_ids = _evidence_pair(_value(group, "evidence_event_ids", "evidenceEventIds"))
    sphere = _text(_value(group, "sphere"), "selected_sphere")
    facet = _optional_text(
        _value(group, "facet", default=None),
        "selected_facet",
    )
    group_polarity = _enum_text(_value(group, "polarity"), _POLARITIES, "selected_polarity")
    raw_anchor = _value(group, "anchor_event_id", "anchorEventId", default=None)
    anchor = event_ids[0] if raw_anchor is None else _text(raw_anchor, "anchor_event_id")
    if anchor not in event_ids:
        raise _NarrativeInputError("foreign_event_reference")

    events: list[_PromptEvent] = []
    for event_id in event_ids:
        is_anchor = event_id == anchor
        unit = units.get(event_id)
        unit_polarity = unit.get("polarity") if unit is not None else None
        event_polarity = group_polarity
        if not is_anchor and isinstance(unit_polarity, str) and unit_polarity in _POLARITIES:
            event_polarity = unit_polarity
        selection = {"sphere": sphere, "facet": facet, "polarity": event_polarity}
        events.append(_event_for_selection(event_id, selection, units, birth_mode, timezone, polarity=event_polarity))
    return _NarrativeBlock(
        block_id=group_id,
        event_ids=event_ids,
        events=tuple(events),
        sphere=sphere,
        facet=facet,
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
    return _NarrativeBlock(
        block_id=event_id,
        event_ids=(event_id,),
        events=(event,),
        sphere=event.sphere,
        facet=event.facet,
        polarity=event.polarity,
    )


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


def _snapshot_context(snapshot: object, person: TodayNarrativePerson | None = None) -> _SnapshotContext:
    if person is not None:
        if not isinstance(person, TodayNarrativePerson):
            raise _NarrativeInputError("person")
        if person.first_name is not None and (
            not isinstance(person.first_name, str) or not person.first_name.strip() or len(person.first_name) > 120
        ):
            raise _NarrativeInputError("person")
        if person.age is not None and (
            isinstance(person.age, bool) or not isinstance(person.age, int) or not 0 <= person.age <= 120
        ):
            raise _NarrativeInputError("person")
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
    convergence_event_ids = {
        event_id
        for group in groups
        for event_id in group.event_ids
    }
    non_convergence_event_ids: list[str] = []
    if main_event is not None:
        non_convergence_event_ids.extend(main_event.event_ids)
    non_convergence_event_ids.extend(
        event_id for impulse in impulses for event_id in impulse.event_ids
    )
    if (
        len(non_convergence_event_ids) != len(set(non_convergence_event_ids))
        or convergence_event_ids.intersection(non_convergence_event_ids)
    ):
        raise _NarrativeInputError("duplicate_selected_event_id")
    selected_ids = _id_list(_value(selected, "selected_unit_ids", "selectedUnitIds"), "selected_unit_ids")
    expected_event_ids = convergence_event_ids.union(non_convergence_event_ids)
    if set(selected_ids) != expected_event_ids:
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
        person=person,
        period=_period_anchors(units),
    )
# END_BLOCK: DRIVER_GROUNDING


# START_BLOCK: PROMPT
def _prompt_event(event: _PromptEvent) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._prompt_event
    # purpose: Project one selected event into the bounded, human-readable
    #   prompt evidence shape.
    # inputs: validated prompt event.
    # returns: prompt-safe mapping with title omitted when unavailable.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none for validated input.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._prompt_event
    result: dict[str, Any] = {
        "kind": event.kind,
        "sphere": event.sphere,
        "facet": event.facet,
        "polarity": event.polarity,
        "sourceFactIds": [event.event_id],
        "eventTime": event.event_time,
        "driverThemes": list(event.driver_themes),
        "grounding": {
            "house": event.house,
            "planets": list(event.planets),
        },
    }
    if event.facet is not None:
        result["lexicon"] = list(_FACET_LEXICON.get(event.facet, ()))
    if event.title is not None:
        result["title"] = event.title
    return result


def _build_prompt(context: _SnapshotContext, prompt_version: str) -> str:
    strict_mode = prompt_version == "today-narrative-v6"
    person_block: dict[str, Any] = {}
    if context.person is not None:
        if context.person.first_name:
            person_block["firstName"] = context.person.first_name.strip()
        if context.person.age is not None:
            person_block["age"] = context.person.age
    period_block = [
        {
            "kind": anchor.kind,
            "lord": anchor.lord,
            "activeFrom": anchor.active_from,
            "activeUntil": anchor.active_until,
        }
        for anchor in context.period
    ]
    prompt_input: dict[str, Any] = {
        "promptVersion": prompt_version,
        "state": context.state,
        "dayTone": context.day_tone,
        "person": person_block,
        "periodBackground": period_block,
        "convergences": [
            {
                "groupId": group.block_id,
                "sphere": group.sphere,
                "facet": group.facet,
                "polarity": group.polarity,
                "sourceFactIds": list(group.event_ids),
                "evidence": [_prompt_event(event) for event in group.events],
            }
            for group in context.convergences
        ],
        "mainEvent": (
            None
            if context.main_event is None
            else _prompt_event(context.main_event.events[0])
        ),
        "impulses": [
            _prompt_event(impulse.events[0])
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
            "meaning": {"text": "", "sourceEventIds": list(event_ids)},
            "action": {"text": "", "sourceEventIds": list(event_ids)},
        }

    if strict_mode:
        response_template = {
            "convergences": [
                {
                    "groupId": group.block_id,
                    **_template_block(group.event_ids),
                }
                for group in context.convergences
            ],
            "main_event": (
                None
                if context.main_event is None
                else _template_block(context.main_event.event_ids)
            ),
            "impulses": [
                {
                    "eventId": impulse.block_id,
                    **_template_block(impulse.event_ids),
                }
                for impulse in context.impulses
            ],
        }
    else:
        response_template = {
            "convergences": {
                group.block_id: _template_block(group.event_ids)
                for group in context.convergences
            },
            "main_event": (
                None
                if context.main_event is None
                else _template_block(context.main_event.event_ids)
            ),
            "impulses": {
                impulse.block_id: _template_block(impulse.event_ids)
                for impulse in context.impulses
            },
        }
    serialized_template = json.dumps(
        response_template,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    strict_tail = (
        "\nДля плеча strict json_schema сохрани массивы: в convergences используй "
        "groupId, в impulses — eventId. Не превращай массивы в словари. "
        "Замени только пустые значения text на текст и верни этот JSON. "
        "Сохрани все ключи, идентификаторы и массивы sourceEventIds; не добавляй и не удаляй поля."
        if strict_mode
        else "\nЗамени только пустые значения text на текст и верни этот JSON. Сохрани\n"
        "все ключи, идентификаторы и массивы sourceEventIds; не добавляй и не удаляй\n"
        "поля. В каждом присутствующем блоке summary.text, meaning.text и action.text\n"
        "обязательны.\n"
    )
    return f"""Ты пишешь короткие персональные тексты для экрана «Сегодня» астрологического приложения, на русском языке. Ты пишешь одному конкретному человеку, на «ты», тепло и по делу — как внимательный друг-астролог, а не как справочник.

О человеке (поле person, если передано):
- firstName — имя человека; используй его не чаще одного раза во всём ответе и только там, где это звучит естественно.
- age — полных лет на дату прогноза; учитывай жизненный контекст молча, цифру возраста в тексте не называй.

Фон периода (periodBackground) — это НЕ факт дня, а долгий контекст жизни человека. Упоминай его только в meaning, когда это честно объясняет, почему тема блока сейчас значима; не пересказывай фон как событие дня и не называй его даты.

Как писать каждый блок:
- summary — 1–2 предложения, не более 220 символов: ЧТО сегодня конкретно (из title события и driverThemes) и КАК это может проявиться в быту строго в рамках facet блока.
- meaning — одно предложение, не более 260 символов: почему это важно человеку сейчас; здесь уместна аккуратная связь с фоном периода.
- action — одно конкретное действие на сегодня, не более 180 символов: начинай с глагола («проверь», «отложи», «напиши»), только в рамках facet блока.
- Конкретика обязательна: используй бытовые детали разрешённого facet (например personal_money → поступления, траты, отложить сумму; romance → симпатия, свидание, разговор по душам; daily_work → текущие задачи, рутина, довести дело до конца).
- Поле lexicon — безопасные слова блока. Опирайся на них для конкретики. Узкие слова ДРУГИХ facet'ов запрещены: для romance не пиши «партнёрский», «брак», «договорённости»; для personal_money не пиши «кредит», «покупка», «бюджет»; для daily_work не пиши «карьера», «статус» — каждое узкое слово принадлежит своему facet.
- Один claim — одна тема блока. Не упоминай другие сферы жизни вообще: ни друзей в блоке отношений, ни документы в блоке денег, ни разговоры/переписку в блоке романтики. Любое слово о другой сфере — брак.
- Тема блока — это facet, а не планета-драйвер. Планета задаёт только характер влияния. Если блок romance, а драйвер Меркурий — пиши о романтике (свидание, симпатия), а не о переговорах и документах: темы планеты не переноси в текст.
- В каждом claim называй тему блока прямо хотя бы одним словом из lexicon; общие обороты «отношения», «финансы», «сфера» без узкого слова facet — брак.
- Не используй слова-антонимы polarity блока даже с отрицанием: для supportive не пиши «напряжение», «конфликт», «тревога»; для tense не пиши «гармония», «поддержка», «легко».
- Если title содержит «жребий Брака», а facet блока — romance, слово «брак» в тексте не используй: заменяй на слова из lexicon («романтика», «свидание», «симпатия»).
- Запрещённые штампы: «в сфере …», «может усилиться», «наблюдается», «играет важную роль», «указывает на важность», «возможна активность», «междуличностные связи», «жизненные выборы», «позитивные перемены», «гармония сферы» и подобная канцелярская вода. Если фраза подошла бы любому человеку в любой день — она запрещена.

Грамматика обязательна:
- Род планет: Солнце — средний («сошлось», «помогло»); Луна и Венера — женский; Меркурий, Марс, Юпитер, Сатурн, Уран, Нептун, Плутон — мужской.
- Следи за падежами после предлогов («сосредоточиться на рутине», не «на рутины»).
- Перед ответом перечитай каждое предложение и исправь согласование.

Примеры (плохо → хорошо):
- Плохо: «В сфере отношений может усилиться напряжение между мыслями и чувствами.»
  Хорошо: «Солнце спорит с твоим Меркурием: в романтике легко зацепиться за слова. Скажи, что чувствуешь, вместо спора о формулировках.»
- Плохо: «В финансовой сфере возможна активность, связанная с оценкой приоритетов.»
  Хорошо: «Личные деньги сегодня послушны: проверь поступления и сразу отложи часть суммы — день этому помогает.»

Правила источников:
- Используй только факты из входа ниже; ничего не вычисляй и не добавляй.
- Не изменяй state, dayTone, сферы, polarity, event IDs или EventTime.
- В каждом ненулевом claim укажи один или несколько sourceEventIds только из
  соответствующего блока. Не выдумывай IDs и не оставляй список пустым.
- Для каждого блока соблюдай ровно переданные sphere, facet (или null),
  polarity и sourceFactIds. Не переноси claim в соседнюю сферу или facet и не
  распространяй polarity узкого facet на всю сферу.
- Каждый claim обязан опираться на title события, если title передан, и на
  driverThemes; не подменяй эту связь общей фразой. При facet=null используй
  только общий язык sphere.
- Текст claim никогда не должен содержать часы, даты, окна или длительности:
  EventTime — только display-only данные для интерфейса. Поля grounding с
  house и planets — внутренние детерминированные источники: называй house
  только при capabilities.houses=true; не раскрывай planets как машинные
  идентификаторы. Не упоминай angle или lot, если соответствующая capability
  не равна true.
- Только русский язык; практичный текст без категоричных предсказаний. Не
  выдумывай реальные события, чувства, исходы или неподтверждённые детали.
- Учитывай mode и capabilities: не упоминай недоступные детали расчёта.
- Никогда не пиши служебные имена или шаблоны: Transit_, Natal_, Planet,
  «M, Mars» и любые перечисления вида «M, <Planet>». Если факт нельзя
  назвать обычными русскими словами, не используй этот факт; claim всё
  равно должен опираться на остальные разрешённые evidence.

Верни строго один JSON-объект без markdown и без дополнительных ключей.
Для каждого присутствующего блока summary, meaning и action — JSON-объекты с
ключами text и sourceEventIds; не возвращай строку вместо объекта. Не меняй
ключи блоков, sourceEventIds и не добавляй полей. Если mainEvent во входе
равен null, оставь main_event равным null.

Вход:
{serialized_input}

Точный JSON-шаблон ответа для этого snapshot:
{serialized_template}
{strict_tail}
"""


def build_today_narrative_prompt(
    snapshot: object,
    *,
    prompt_version: str,
    person: TodayNarrativePerson | None = None,
) -> str:
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
        context = _snapshot_context(snapshot, person)
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
    *,
    json_schema: dict[str, Any] | None,
    system: str | None,
    model: str | None,
    models: list[str] | None,
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
            kwargs["json_object"] = json_schema is None
        if json_schema is not None and supports("json_schema"):
            kwargs["json_schema"] = json_schema
        if system and supports("system"):
            kwargs["system"] = system
        if model is not None and supports("model"):
            kwargs["model"] = model
        if models is not None and supports("models"):
            kwargs["models"] = list(models)
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
        kwargs["json_object"] = json_schema is None
    if json_schema is not None and supports("json_schema"):
        kwargs["json_schema"] = json_schema
    if system and supports("system"):
        kwargs["system"] = system
    if model is not None and supports("model"):
        kwargs["model"] = model
    if models is not None and supports("models"):
        kwargs["models"] = list(models)
    return kwargs


def _split_prompt(prompt: str) -> tuple[str | None, str]:
    """Split a prompt only when its explicit system/user boundary is present."""
    marker = "\nВход:\n"
    index = prompt.find(marker)
    if index < 0:
        return None, prompt
    return prompt[:index], prompt[index + 1 :]


async def _invoke_provider(
    llm: object | None,
    prompt: str,
    *,
    max_output_tokens: int,
    timeout_seconds: float,
    json_schema: dict[str, Any] | None,
    model: str,
    models: list[str],
) -> object:
    client = LLMService() if llm is None else llm
    method, method_name = _provider_method(client)
    deadline_at = time.monotonic() + timeout_seconds
    system_prompt, user_prompt = _split_prompt(prompt)
    kwargs = _call_kwargs(
        method,
        method_name,
        max_output_tokens,
        timeout_seconds,
        deadline_at,
        json_schema=json_schema,
        system=system_prompt,
        model=model,
        models=models,
    )
    try:
        method_parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        method_parameters = {}
    accepts_system = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD or name == "system"
        for name, parameter in method_parameters.items()
    )
    result = method(user_prompt if system_prompt and accepts_system else prompt, **kwargs)
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
def _raw_claim_texts(content: Mapping[str, Any]) -> list[str]:
    texts: list[str] = []
    raw_convergences = content.get("convergences")
    if isinstance(raw_convergences, Mapping):
        blocks: list[object] = list(raw_convergences.values())
    else:
        blocks = []
    if content.get("main_event") is not None:
        blocks.append(content.get("main_event"))
    raw_impulses = content.get("impulses")
    if isinstance(raw_impulses, Mapping):
        blocks.extend(raw_impulses.values())
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        for field in _NARRATIVE_FIELDS:
            claim = block.get(field)
            if isinstance(claim, Mapping) and isinstance(claim.get("text"), str):
                texts.append(claim["text"])
    return texts


def _claim(
    value: object,
    allowed_event_ids: frozenset[str],
    *,
    grounding: _BlockGrounding,
    allow_grounding_nulls: bool,
) -> dict[str, Any] | None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._claim
    # purpose: Sanitize, bind, and ground one provider claim.
    # inputs: raw claim, selected event ids, block grounding context, and the
    #   second-pass nulling policy.
    # returns: canonical claim or None when the provider explicitly omitted it
    #   or the second grounding pass withholds it.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: schema/binding errors raise typed validation errors;
    #   grounding errors retry once at the generation boundary, then null.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._claim
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
    allowed_spheres, allowed_facets, polarity = _claim_grounding(grounding, source_ids)
    if has_narrative_grounding_violation(
        clean_text,
        allowed_spheres=allowed_spheres,
        allowed_facets=allowed_facets,
        polarity=polarity,
    ):
        if allow_grounding_nulls:
            reason = explain_narrative_grounding_violation(
                clean_text,
                allowed_spheres=allowed_spheres,
                allowed_facets=allowed_facets,
                polarity=polarity,
            ) or {
                "reason_class": "sphere_conflict",
                "pattern_id": "grounding_violation",
            }
            _safe_log_claim_nulled(
                reason_class=reason["reason_class"],
                facet=next(iter(allowed_facets), None),
                polarity=polarity,
                pattern_id=reason["pattern_id"],
            )
            return None
        raise _NarrativeValidationError(TodayNarrativeErrorCode.GROUNDING_VIOLATION)
    return {"text": clean_text, "sourceEventIds": list(source_ids)}


def _block_content(
    value: object,
    expected_ids: tuple[str, ...],
    block: _NarrativeBlock,
    *,
    allow_grounding_nulls: bool,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._block_content
    # purpose: Validate one exact narrative block and apply its
    #   sphere/facet/polarity grounding policy to every claim field.
    # inputs: raw provider block, its selected event ids, block evidence, and
    #   whether grounding failures may become null claims.
    # returns: canonical block with only sanitized, bound claims.
    # side_effects: none.
    # error_behavior: raises typed validation errors for all non-grounding
    #   violations; grounding is retried/nullable according to the flag.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._block_content
    if not isinstance(value, Mapping) or set(value) != set(_NARRATIVE_FIELDS):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    allowed_event_ids = frozenset(expected_ids)
    grounding = _block_grounding(block)
    result = {
        field: _claim(
            value[field],
            allowed_event_ids,
            grounding=grounding,
            allow_grounding_nulls=allow_grounding_nulls,
        )
        for field in _NARRATIVE_FIELDS
    }
    summary = result["summary"]
    if summary is not None and len(summary["text"]) > 220:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    return result


def _normalise_array_response(parsed: object) -> object:
    """Convert strict array output into the canonical keyed content shape."""
    if not isinstance(parsed, dict):
        return parsed
    raw_convergences = parsed.get("convergences")
    raw_impulses = parsed.get("impulses")
    if not isinstance(raw_convergences, list) and not isinstance(raw_impulses, list):
        return parsed
    if set(parsed) != {"convergences", "main_event", "impulses"}:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    if not isinstance(raw_convergences, list) or not isinstance(raw_impulses, list):
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)

    convergences: dict[str, Any] = {}
    for item in raw_convergences:
        if (
            not isinstance(item, Mapping)
            or set(item) != {"groupId", *_NARRATIVE_FIELDS}
            or not isinstance(item.get("groupId"), str)
        ):
            raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
        group_id = item["groupId"]
        if group_id in convergences:
            raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
        convergences[group_id] = {field: item.get(field) for field in _NARRATIVE_FIELDS}

    impulses: dict[str, Any] = {}
    for item in raw_impulses:
        if (
            not isinstance(item, Mapping)
            or set(item) != {"eventId", *_NARRATIVE_FIELDS}
            or not isinstance(item.get("eventId"), str)
        ):
            raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
        event_id = item["eventId"]
        if event_id in impulses:
            raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
        impulses[event_id] = {field: item.get(field) for field in _NARRATIVE_FIELDS}

    return {
        "convergences": convergences,
        "main_event": parsed.get("main_event"),
        "impulses": impulses,
    }


def _validate_response(
    raw_text: str,
    context: _SnapshotContext,
    *,
    allow_grounding_nulls: bool = False,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._validate_response
    # purpose: Parse and validate the exact provider envelope, including
    #   grounding-aware claim handling.
    # inputs: raw provider JSON, validated snapshot context, and the second
    #   grounding-pass null policy.
    # returns: canonical narrative content.
    # side_effects: none.
    # error_behavior: raises typed validation errors; only grounding can be
    #   converted to null when explicitly enabled.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE._validate_response
    try:
        parsed = json.loads(raw_text)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID) from exc
    parsed = _normalise_array_response(parsed)
    if not isinstance(parsed, dict) or set(parsed) != {"convergences", "main_event", "impulses"}:
        raise _NarrativeValidationError(TodayNarrativeErrorCode.SCHEMA_INVALID)
    _validate_capability_texts(_raw_claim_texts(parsed), context)

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
        main_content = _block_content(
            main_value,
            context.main_event.event_ids,
            context.main_event,
            allow_grounding_nulls=allow_grounding_nulls,
        )

    content = {
        "convergences": {
            group_id: _block_content(
                raw_convergences[group_id],
                group.event_ids,
                group,
                allow_grounding_nulls=allow_grounding_nulls,
            )
            for group_id, group in expected_groups.items()
        },
        "main_event": main_content,
        "impulses": {
            event_id: _block_content(
                raw_impulses[event_id],
                impulse.event_ids,
                impulse,
                allow_grounding_nulls=allow_grounding_nulls,
            )
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
    _validate_capability_texts(_claim_texts(content), context)


def _validate_capability_texts(texts: Sequence[str], context: _SnapshotContext) -> None:
    banned: list[re.Pattern[str]] = [_CLOCK_TEXT_RE]
    if context.birth_mode != "exact" or not context.capabilities["houses"]:
        banned.append(_HOUSE_TEXT_RE)
    if context.birth_mode != "exact" or not context.capabilities["angles"]:
        banned.append(_ANGLE_TEXT_RE)
    if context.birth_mode != "exact" or not context.capabilities["lots"]:
        banned.append(_LOT_TEXT_RE)
    available_houses = {
        event.house
        for block in (*context.convergences, context.main_event, *context.impulses)
        if block is not None
        for event in block.events
        if event.house is not None
    }
    for text in texts:
        if any(pattern.search(text) is not None for pattern in banned):
            raise _NarrativeValidationError(TodayNarrativeErrorCode.CAPABILITY_VIOLATION)
        if context.birth_mode == "exact" and context.capabilities["houses"]:
            if _HOUSE_TEXT_RE.search(text) is not None:
                if not available_houses:
                    raise _NarrativeValidationError(TodayNarrativeErrorCode.CAPABILITY_VIOLATION)
                referenced_houses = {
                    int(match.group(1)) for match in _HOUSE_NUMBER_RE.finditer(text)
                }
                if referenced_houses and not referenced_houses.issubset(available_houses):
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


def _safe_log(
    event: str,
    *,
    payload: dict[str, Any],
    duration_ms: int | None = None,
    block: str = "GENERATION",
) -> None:
    try:
        with log_block(slice="W-TODAY-CONVERGENCE-REWRITE", module="M-TODAY-NARRATIVE", block=block):
            log_event(event, payload=payload, duration_ms=duration_ms)
    except Exception:
        pass


def _safe_log_claim_nulled(
    *,
    reason_class: str,
    facet: str | None,
    polarity: str,
    pattern_id: str,
) -> None:
    _safe_log(
        "day.narrative_claim_nulled",
        block="CLAIM",
        payload={
            "reason_class": reason_class,
            "facet": facet,
            "polarity": polarity,
            "pattern_id": pattern_id,
        },
    )


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


def _narrative_provider_options(
    generation_path: Literal["ondemand", "pregen"],
) -> tuple[str, list[str], int]:
    if generation_path == "pregen":
        model = settings.today_narrative_model_pregen
        max_output_tokens = settings.today_narrative_pregen_max_output_tokens
    else:
        model = settings.today_narrative_model_ondemand
        max_output_tokens = settings.today_narrative_max_output_tokens
    fallback_models = list(settings.today_narrative_fallback_models)
    return model, [model, *fallback_models], max_output_tokens


async def generate_today_narrative(
    snapshot: object,
    *,
    prompt_version: str,
    llm: object | None = None,
    correlation_id: str | None = None,
    timeout_seconds: float | None = None,
    clock: Callable[[], float] | None = None,
    person: TodayNarrativePerson | None = None,
    generation_path: Literal["ondemand", "pregen"] = "ondemand",
) -> TodayNarrativeSuccess | TodayNarrativeFailure:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.generate_today_narrative
    # purpose: Generate and atomically validate one bounded Today narrative;
    #   grounding failures receive one bounded regeneration before unsafe claims
    #   are withheld as null.
    # inputs: snapshot — published TodaySnapshot-like row; prompt_version — lease
    #   identity; llm — injectable provider; correlation_id — caller context;
    #   timeout_seconds/clock — optional test/deadline controls; generation_path
    #   selects the pregen flash cap or on-demand nano cap.
    # returns: TodayNarrativeSuccess with canonical content_json, or
    #   TodayNarrativeFailure with timeout/provider/schema/claim/capability code.
    # side_effects: at most two bounded provider calls (only for grounding retry)
    #   and guarded lifecycle logs.
    # emitted_logs: day.narrative_generation_started,
    #   day.narrative_generation_completed, day.narrative_generation_failed,
    #   day.narrative_claim_nulled.
    # error_behavior: returns typed failure for all expected generation errors;
    #   propagates asyncio cancellation and never emits template fallback text.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE.generate_today_narrative
    active_clock = time.monotonic if clock is None else clock
    started_at = active_clock()
    snapshot_identifier = _snapshot_id(snapshot)
    context: _SnapshotContext | None = None
    context_error: _NarrativeInputError | None = None
    try:
        context = _snapshot_context(snapshot, person)
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
        if generation_path not in {"ondemand", "pregen"}:
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
        model, models, max_output_tokens = _narrative_provider_options(generation_path)
        provider_text: _ProviderText | None = None
        content: dict[str, Any] | None = None
        for attempt in range(2):
            attempt_prompt = prompt if attempt == 0 else prompt + _GROUNDING_RETRY_SUFFIX
            try:
                raw_response = await asyncio.wait_for(
                    _invoke_provider(
                        llm,
                        attempt_prompt,
                        max_output_tokens=max_output_tokens,
                        timeout_seconds=bounded_timeout,
                        json_schema=(
                            strict_response_schema()
                            if prompt_version == "today-narrative-v6"
                            else None
                        ),
                        model=model,
                        models=models,
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
                content = _validate_response(
                    provider_text.text,
                    context,
                    allow_grounding_nulls=attempt == 1,
                )
                _validate_capabilities(content, context)
            except _NarrativeValidationError as exc:
                if attempt == 0 and exc.code is TodayNarrativeErrorCode.GROUNDING_VIOLATION:
                    continue
                error_code = exc.code.value
                latency_ms = _latency_ms(active_clock, started_at)
                _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
                return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)
            except Exception:
                error_code = TodayNarrativeErrorCode.SCHEMA_INVALID.value
                latency_ms = _latency_ms(active_clock, started_at)
                _log_failed(snapshot_identifier, prompt_version, error_code, latency_ms)
                return TodayNarrativeFailure(error_code=error_code, latency_ms=latency_ms)
            break

        if content is None or provider_text is None:
            error_code = TodayNarrativeErrorCode.GROUNDING_VIOLATION.value
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
    "TodayNarrativePerson",
    "TodayNarrativeSuccess",
    "build_today_narrative_prompt",
    "generate_today_narrative",
    "strict_response_schema",
]
