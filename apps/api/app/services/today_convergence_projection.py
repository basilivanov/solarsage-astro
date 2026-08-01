# ############################################################################
# AI_HEADER: TODAY_CONVERGENCE_PROJECTION — pure snapshot-to-wire projection.
# ROLE: Projects published deterministic Today rows into the validated
#       TodayConvergencePayload without HTTP, DB, sidecar, LLM, or logging.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-PROJECTION
# purpose: Convert a published TodaySnapshot, optional narrative row, and
#   ContentAccessState into the strict Today convergence wire root.
# owns:
#   - apps/api/app/services/today_convergence_projection.py
# inputs: TodaySnapshot JSON rows, optional TodaySnapshotNarrative, and access state.
# outputs: Validated TodayConvergencePayload or a typed fail-closed error.
# dependencies: Today snapshot DB row types, access schema, Today wire schemas.
# side_effects: none; no HTTP/DB/sidecar/LLM calls and no logs.
# emitted_logs: none.
# invariants: Deterministic fields are copied from published JSON, narrative is
#   accepted atomically, event references resolve to the snapshot factor ledger,
#   and input rows are never mutated.
# failure_policy: TodayConvergenceProjectionError with a stable prefixed reason;
#   invalid narrative content falls back atomically to unavailable LLM content.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-PROJECTION

# START_MODULE_MAP: M-TODAY-CONVERGENCE-PROJECTION
# public_entrypoints:
#   - TodayConvergenceProjectionError
#   - project_snapshot_payload
#   - project_empty_payload
# semantic_blocks:
#   - MATRIX: access validation, birth-time wire, and selection parsing.
#   - LEDGER: deterministic selected blocks and factor-unit event union.
#   - EVENT_TIME: timezone-aware exact, bucket, and unknown precision mapping.
#   - NARRATIVE: atomic claim validation and content-state projection.
#   - ASSEMBLY: wire root assembly and final schema validation.
#   - ENTRYPOINTS: public projection facades.
# owned_tests:
#   - apps/api/tests/test_today_convergence_projection.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-PROJECTION

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, NoReturn, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError

from app.core.versions import CALCULATION_VERSION
from app.db.models import TodaySnapshot, TodaySnapshotNarrative
from app.schemas.access import ContentAccessState
from app.schemas.today_convergence import (
    TodayConvergenceBirthTime,
    TodayConvergencePayload,
)
from app.services.narrative_sanitizer import sanitize_narrative_text
from app.services.today_convergence_titles import build_today_convergence_event_title


_FORMULA_VERSION = "today-convergence-2"
# Versioned registry title for the honest quiet-day no_strong_accent context
# (04 §3.3: deterministic registry text, never an LLM placeholder).
_NO_STRONG_ACCENT_TITLE = "Ровный фон без сильного акцента"
_MISSING = object()
_SPHERES = frozenset({
    "work",
    "money",
    "documents",
    "relationships",
    "sport",
    "communication",
    "health",
    "decisions",
    "travel",
    "creativity",
    "study",
    "shopping",
})
_POLARITIES = frozenset({"supportive", "tense", "mixed"})
_EVIDENCE_LEVELS = frozenset({"high", "medium"})
_BIRTH_MODES = frozenset({"exact", "bucket", "unknown"})
_BIRTH_BUCKETS = frozenset({"night", "morning", "day", "evening"})
_NARRATIVE_FIELDS = ("summary", "meaning", "action")


class TodayConvergenceProjectionError(ValueError):
    """Raised when a Today snapshot cannot be projected safely."""


def _fail(reason: str, cause: BaseException | None = None) -> NoReturn:
    error = TodayConvergenceProjectionError(f"today_convergence_projection:{reason}")
    if cause is None:
        raise error
    raise error from cause


def _mapping(value: object, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(reason)
    if any(not isinstance(key, str) for key in value):
        _fail(reason)
    return cast(Mapping[str, Any], value)


def _sequence(value: object, reason: str) -> list[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        _fail(reason)
    return list(value)


def _value(mapping: Mapping[str, Any], *keys: str, default: object = _MISSING) -> object:
    for key in keys:
        if key in mapping:
            return mapping[key]
    if default is not _MISSING:
        return default
    _fail(f"missing_{keys[0]}")


def _text(value: object, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(reason)
    return value


def _optional_text(value: object, reason: str) -> str | None:
    if value is None:
        return None
    return _text(value, reason)


def _enum_text(value: object, allowed: frozenset[str], reason: str) -> str:
    text = _text(value, reason)
    if text not in allowed:
        _fail(reason)
    return text


def _text_list(value: object, reason: str) -> list[str]:
    values = _sequence(value, reason)
    result: list[str] = []
    for item in values:
        result.append(_text(item, reason))
    if len(result) != len(set(result)):
        _fail("duplicate_id")
    return result


def _zone(timezone_name: object) -> ZoneInfo:
    timezone_text = _text(timezone_name, "timezone")
    try:
        return ZoneInfo(timezone_text)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        _fail("timezone_invalid", exc)


def _iso_value(value: object, reason: str) -> date | datetime:
    raw = _text(value, reason)
    try:
        if "T" in raw or " " in raw:
            parsed_datetime = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed_datetime.tzinfo is None or parsed_datetime.utcoffset() is None:
                _fail(f"{reason}_timezone")
            return parsed_datetime
        return date.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        _fail(reason, exc)


def _local_datetime(value: date | datetime, timezone: ZoneInfo, reason: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        _fail(reason)
    return value.astimezone(timezone)


def _clock(value: datetime) -> str:
    return value.strftime("%H:%M")


def _part_of_day(hour: int) -> str:
    if 0 <= hour < 6:
        return "night"
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "day"
    return "evening"


def _midpoint(first: datetime, second: datetime) -> datetime:
    return first + (second - first) / 2


def _source_datetime(
    unit: Mapping[str, Any],
    field: str,
    timezone: ZoneInfo,
) -> date | datetime | None:
    raw = unit.get(field)
    if raw is None:
        return None
    parsed = _iso_value(raw, f"factor_{field}")
    if isinstance(parsed, datetime):
        return parsed.astimezone(timezone)
    return parsed


@dataclass(frozen=True)
class _EventPresentation:
    sphere: str
    polarity: str
    evidence_level: str


@dataclass(frozen=True)
class _Selection:
    state: str
    day_tone: str
    selected_spheres: list[str]
    convergences: list[Mapping[str, Any]]
    main_event: Mapping[str, Any] | None
    impulses: list[Mapping[str, Any]]
    selected_unit_ids: list[str]


# START_BLOCK: MATRIX
def _validate_access(access_state: object) -> ContentAccessState:
    if not isinstance(access_state, ContentAccessState):
        _fail("access_type")
    return access_state


def _birth_time_from_snapshot(snapshot: TodaySnapshot) -> TodayConvergenceBirthTime:
    mode = _enum_text(snapshot.birth_time_mode, _BIRTH_MODES, "birth_mode")
    birth_range = _mapping(snapshot.birth_time_range, "birth_range")
    range_start = _text(_value(birth_range, "start", "range_start"), "birth_range")
    range_end = _text(_value(birth_range, "end", "range_end"), "birth_range")

    canonical_input = _mapping(snapshot.canonical_input_json, "canonical_input")
    birth_input = _mapping(_value(canonical_input, "birth_time"), "birth_input")
    capabilities_input = _mapping(_value(birth_input, "capabilities"), "birth_capabilities")
    capabilities = {
        "houses": capabilities_input.get("houses"),
        "angles": capabilities_input.get("angles"),
        "lots": capabilities_input.get("lots"),
        "exact_timing": capabilities_input.get("exact_timing", capabilities_input.get("exactTiming")),
    }
    if any(type(value) is not bool for value in capabilities.values()):
        _fail("birth_capabilities")

    raw_bucket = _value(birth_input, "bucket", default=None)
    bucket = None if raw_bucket is None else _enum_text(raw_bucket, _BIRTH_BUCKETS, "birth_bucket")
    if mode == "exact":
        bucket = None
    elif mode == "unknown":
        bucket = None
    elif bucket is None:
        ranges = {
            "night": ("00:00", "06:00"),
            "morning": ("06:00", "12:00"),
            "day": ("12:00", "18:00"),
            "evening": ("18:00", "24:00"),
        }
        bucket = next(
            (candidate for candidate, bounds in ranges.items() if bounds == (range_start, range_end)),
            None,
        )
        if bucket is None:
            _fail("birth_bucket")

    try:
        return TodayConvergenceBirthTime.model_validate({
            "mode": mode,
            "bucket": bucket,
            "range_start": range_start,
            "range_end": range_end,
            "capabilities": capabilities,
        })
    except ValidationError as exc:
        _fail("birth_time", exc)


def _snapshot_selection(snapshot: TodaySnapshot) -> tuple[Mapping[str, Any], _Selection]:
    result = _mapping(snapshot.deterministic_result_json, "deterministic_result")
    state = _enum_text(
        _value(result, "state"),
        frozenset({"convergence_today", "quiet_day"}),
        "state",
    )
    day_tone = _enum_text(
        _value(result, "day_tone", "dayTone"),
        frozenset({"steady", "supportive", "mixed", "tense"}),
        "day_tone",
    )
    selected = _mapping(_value(result, "selected"), "selected")
    convergence_values = _sequence(_value(selected, "convergences"), "convergences")
    convergences = [_mapping(value, "convergence") for value in convergence_values]
    raw_main = _value(selected, "main_event", "mainEvent", default=None)
    main_event = None if raw_main is None else _mapping(raw_main, "main_event")
    impulse_values = _sequence(_value(selected, "impulses"), "impulses")
    impulses = [_mapping(value, "impulse") for value in impulse_values]
    selected_spheres = _text_list(_value(selected, "selected_spheres", "selectedSpheres"), "selected_spheres")
    if any(sphere not in _SPHERES for sphere in selected_spheres) or len(selected_spheres) > 3:
        _fail("selected_spheres")
    selected_unit_ids = _text_list(_value(selected, "selected_unit_ids", "selectedUnitIds"), "selected_unit_ids")
    return result, _Selection(
        state=state,
        day_tone=day_tone,
        selected_spheres=selected_spheres,
        convergences=convergences,
        main_event=main_event,
        impulses=impulses,
        selected_unit_ids=selected_unit_ids,
    )


def _factor_ledger(snapshot: TodaySnapshot) -> dict[str, Mapping[str, Any]]:
    canonical_input = _mapping(snapshot.canonical_input_json, "canonical_input")
    raw_units = _sequence(_value(canonical_input, "factor_units", "factorUnits"), "factor_units")
    units: dict[str, Mapping[str, Any]] = {}
    for raw_unit in raw_units:
        unit = _mapping(raw_unit, "factor_unit")
        event_id = _text(_value(unit, "canonical_event_id", "canonicalEventId"), "factor_event_id")
        if event_id in units:
            _fail("duplicate_factor_event_id")
        units[event_id] = unit
    return units


def _presentation(
    value: Mapping[str, Any],
    *,
    event_id_key: str = "event_id",
) -> tuple[str, str, str, str]:
    event_id = _text(_value(value, event_id_key, "eventId"), "selected_event_id")
    sphere = _enum_text(_value(value, "sphere"), _SPHERES, "selected_sphere")
    polarity = _enum_text(_value(value, "polarity"), _POLARITIES, "selected_polarity")
    evidence_level = _enum_text(
        _value(value, "evidence_level", "evidenceLevel"),
        _EVIDENCE_LEVELS,
        "selected_evidence_level",
    )
    return event_id, sphere, polarity, evidence_level


def _register_presentation(
    event_id: str,
    presentation: _EventPresentation,
    factor_units: Mapping[str, Mapping[str, Any]],
    presentations: dict[str, _EventPresentation],
    ordered_ids: list[str],
) -> None:
    if event_id not in factor_units:
        _fail("foreign_event_reference")
    previous = presentations.get(event_id)
    if previous is not None and previous != presentation:
        _fail("event_presentation_conflict")
    if previous is None:
        presentations[event_id] = presentation
        ordered_ids.append(event_id)


def _selected_event_ids(selection: _Selection) -> set[str]:
    selected_ids: set[str] = set()
    for group in selection.convergences:
        selected_ids.update(
            _text_list(
                _value(group, "evidence_event_ids", "evidenceEventIds"),
                "evidence_event_ids",
            )
        )
    if selection.main_event is not None:
        selected_ids.add(_text(_value(selection.main_event, "event_id", "eventId"), "selected_event_id"))
    for impulse in selection.impulses:
        selected_ids.add(_text(_value(impulse, "event_id", "eventId"), "selected_event_id"))
    return selected_ids


# END_BLOCK: MATRIX


# START_BLOCK: LEDGER
def _build_deterministic_blocks(
    snapshot: TodaySnapshot,
    selection: _Selection,
    factor_units: Mapping[str, Mapping[str, Any]],
    timezone: ZoneInfo,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    presentations: dict[str, _EventPresentation] = {}
    ordered_ids: list[str] = []
    groups: list[dict[str, Any]] = []

    for group in selection.convergences:
        group_id = _text(_value(group, "group_id", "groupId"), "group_id")
        event_ids = _text_list(_value(group, "evidence_event_ids", "evidenceEventIds"), "evidence_event_ids")
        if len(event_ids) != 2:
            _fail("evidence_pair")
        primary = _enum_text(_value(group, "primary_sphere", "primarySphere"), _SPHERES, "selected_sphere")
        raw_secondary = _value(group, "secondary_sphere", "secondarySphere", default=None)
        secondary = None if raw_secondary is None else _enum_text(raw_secondary, _SPHERES, "selected_sphere")
        polarity = _enum_text(_value(group, "polarity"), _POLARITIES, "selected_polarity")
        evidence = _enum_text(
            _value(group, "evidence_level", "evidenceLevel"),
            _EVIDENCE_LEVELS,
            "selected_evidence_level",
        )
        member_ids = _text_list(_value(group, "member_event_ids", "memberEventIds"), "member_event_ids")
        if any(event_id not in member_ids for event_id in event_ids):
            _fail("foreign_event_reference")
        raw_anchor = _value(group, "anchor_event_id", "anchorEventId", default=None)
        anchor_event_id = None if raw_anchor is None else _text(raw_anchor, "anchor_event_id")
        if anchor_event_id is not None and anchor_event_id not in event_ids:
            _fail("foreign_event_reference")
        for index, event_id in enumerate(event_ids):
            is_anchor = anchor_event_id == event_id or (anchor_event_id is None and index == 0)
            sphere = primary if is_anchor or secondary is None else secondary
            unit_polarity = factor_units[event_id].get("polarity")
            event_polarity = (
                polarity
                if is_anchor or not isinstance(unit_polarity, str) or unit_polarity not in _POLARITIES
                else unit_polarity
            )
            unit_evidence = factor_units[event_id].get(
                "evidence_level", factor_units[event_id].get("evidenceLevel")
            )
            event_evidence = (
                evidence
                if is_anchor or not isinstance(unit_evidence, str) or unit_evidence not in _EVIDENCE_LEVELS
                else unit_evidence
            )
            if not is_anchor and event_evidence == evidence:
                event_evidence = "medium"
            _register_presentation(
                event_id,
                _EventPresentation(sphere=sphere, polarity=event_polarity, evidence_level=event_evidence),
                factor_units,
                presentations,
                ordered_ids,
            )
        groups.append({
            "id": group_id,
            "primary_sphere": primary,
            "secondary_sphere": secondary,
            "polarity": polarity,
            "evidence_level": evidence,
            "event_ids": event_ids,
            "summary": None,
            "meaning": None,
            "action": None,
        })

    main_wire: dict[str, Any] | None = None
    if selection.main_event is not None:
        event_id, sphere, polarity, evidence = _presentation(selection.main_event)
        _register_presentation(
            event_id,
            _EventPresentation(sphere=sphere, polarity=polarity, evidence_level=evidence),
            factor_units,
            presentations,
            ordered_ids,
        )
        main_wire = {
            "id": f"mev_v1_{event_id}",
            "event_id": event_id,
            "sphere": sphere,
            "polarity": polarity,
            "evidence_level": evidence,
            "time": _event_time(factor_units[event_id], snapshot.birth_time_mode, timezone),
            "summary": None,
            "meaning": None,
            "action": None,
        }

    impulses_wire: list[dict[str, Any]] = []
    if len(selection.impulses) > 3:
        _fail("impulse_cap")
    for impulse in selection.impulses:
        event_id, sphere, polarity, evidence = _presentation(impulse)
        _register_presentation(
            event_id,
            _EventPresentation(sphere=sphere, polarity=polarity, evidence_level=evidence),
            factor_units,
            presentations,
            ordered_ids,
        )
        impulses_wire.append({
            "event_id": event_id,
            "sphere": sphere,
            "polarity": polarity,
            "evidence_level": evidence,
            "time": _event_time(factor_units[event_id], snapshot.birth_time_mode, timezone),
            "summary": None,
            "meaning": None,
            "action": None,
        })

    expected_selected_ids = _selected_event_ids(selection)
    if set(ordered_ids) != expected_selected_ids or set(selection.selected_unit_ids) != expected_selected_ids:
        _fail("selected_unit_ids")

    events: list[dict[str, Any]] = []
    for event_id in ordered_ids:
        unit = factor_units[event_id]
        presentation = presentations[event_id]
        kind = _optional_text(unit.get("event_class"), "factor_event_kind")
        if kind is None:
            kind = _text(unit.get("technique_horizon"), "factor_event_kind")
        source: str | None = None
        for source_key in ("source_key", "semantic_key", "driver_key"):
            candidate = unit.get(source_key)
            if isinstance(candidate, str) and candidate.strip():
                source = _text(candidate, "factor_source")
                break
        if source is None:
            _fail("factor_source")
        events.append({
            "id": event_id,
            "kind": kind,
            "title": build_today_convergence_event_title(unit),
            "sphere": presentation.sphere,
            "polarity": presentation.polarity,
            "evidence_level": presentation.evidence_level,
            "time": _event_time(unit, snapshot.birth_time_mode, timezone),
            "source_ids": [source],
        })
    return groups, main_wire, impulses_wire, events


# END_BLOCK: LEDGER


# START_BLOCK: EVENT_TIME
def _event_time(unit: Mapping[str, Any], birth_mode: object, timezone: ZoneInfo) -> dict[str, Any]:
    mode = _enum_text(birth_mode, _BIRTH_MODES, "birth_mode")
    exact_at = _source_datetime(unit, "exact_at", timezone)
    active_from = _source_datetime(unit, "active_from", timezone)
    active_until = _source_datetime(unit, "active_until", timezone)

    if mode == "exact":
        exact_peak: datetime | None
        if isinstance(exact_at, datetime):
            exact_peak = exact_at
        elif isinstance(active_from, datetime) and isinstance(active_until, datetime):
            exact_peak = _midpoint(active_from, active_until)
        else:
            _fail("event_time_exact_missing")
        return {
            "mode": "exact",
            "peak": _clock(exact_peak),
            "start": _clock(active_from) if isinstance(active_from, datetime) else None,
            "end": _clock(active_until) if isinstance(active_until, datetime) else None,
            "part_of_day": None,
        }

    if mode == "bucket":
        bucket_peak: datetime | None = exact_at if isinstance(exact_at, datetime) else None
        if bucket_peak is None and isinstance(active_from, datetime) and isinstance(active_until, datetime):
            bucket_peak = _midpoint(active_from, active_until)
        if bucket_peak is None:
            _fail("event_time_bucket_missing")
        return {
            "mode": "partofday",
            "peak": None,
            "start": None,
            "end": None,
            "part_of_day": _part_of_day(bucket_peak.hour),
        }

    date_only = exact_at
    if isinstance(date_only, datetime):
        return {
            "mode": "partofday",
            "peak": None,
            "start": None,
            "end": None,
            "part_of_day": _part_of_day(date_only.hour),
        }
    if isinstance(date_only, date):
        return {"mode": "date", "peak": None, "start": None, "end": None, "part_of_day": None}
    midpoint = (
        _midpoint(active_from, active_until)
        if isinstance(active_from, datetime) and isinstance(active_until, datetime)
        else None
    )
    if midpoint is not None:
        return {
            "mode": "partofday",
            "peak": None,
            "start": None,
            "end": None,
            "part_of_day": _part_of_day(midpoint.hour),
        }
    if isinstance(active_from, date) or isinstance(active_until, date):
        return {"mode": "date", "peak": None, "start": None, "end": None, "part_of_day": None}
    _fail("event_time_unknown_missing")


# END_BLOCK: EVENT_TIME


# START_BLOCK: NARRATIVE
def _content_state_and_narrative(
    narrative: TodaySnapshotNarrative | None,
    snapshot: TodaySnapshot,
    groups: list[dict[str, Any]],
    main_event: dict[str, Any] | None,
    impulses: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]]]:
    if narrative is None:
        # Quiet day without any selected blocks carries only the honest
        # no_strong_accent context — there is nothing for the LLM to write
        # (04 §3.2 full + quiet + not_needed).
        if not groups and main_event is None and not impulses:
            return "not_needed", groups, main_event, impulses
        return "pending", groups, main_event, impulses
    narrative_snapshot_id = getattr(narrative, "snapshot_id", _MISSING)
    if narrative_snapshot_id is _MISSING or str(narrative_snapshot_id) != str(snapshot.id):
        _fail("narrative_snapshot_mismatch")
    status = _text(getattr(narrative, "status", None), "narrative_status")
    if status == "pending":
        return "pending", groups, main_event, impulses
    if status == "unavailable":
        return "unavailable", groups, main_event, impulses
    if status != "ready":
        _fail("narrative_status")
    content = getattr(narrative, "content_json", None)
    try:
        return "ready", *_apply_narrative(content, groups, main_event, impulses)
    except _InvalidNarrative:
        return "unavailable", groups, main_event, impulses


class _InvalidNarrative(Exception):
    pass


def _narrative_block(container: object, block_id: str, reason: str) -> Mapping[str, Any] | None:
    if container is None:
        return None
    if isinstance(container, Mapping):
        value = container.get(block_id, _MISSING)
        if value is _MISSING:
            return None
        if not isinstance(value, Mapping):
            raise _InvalidNarrative(reason)
        return cast(Mapping[str, Any], value)
    if isinstance(container, Sequence) and not isinstance(container, (str, bytes, bytearray)):
        for raw in container:
            item = raw if isinstance(raw, Mapping) else None
            if item is None:
                raise _InvalidNarrative(reason)
            item_id = item.get("id", item.get("group_id", item.get("groupId", item.get("event_id", item.get("eventId")))))
            if item_id == block_id:
                return item
        return None
    raise _InvalidNarrative(reason)


def _claim(value: object, allowed_ids: set[str], *, summary: bool) -> dict[str, Any] | None:
    if value is None or value is _MISSING:
        return None
    if not isinstance(value, Mapping):
        raise _InvalidNarrative("claim_shape")
    text = value.get("text")
    source_ids = value.get("source_event_ids", value.get("sourceEventIds"))
    if not isinstance(text, str) or not text:
        raise _InvalidNarrative("claim_text")
    clean_text = sanitize_narrative_text(text)
    if clean_text is None:
        raise _InvalidNarrative("claim_text")
    if summary and len(clean_text) > 220:
        raise _InvalidNarrative("summary_text")
    if not isinstance(source_ids, Sequence) or isinstance(source_ids, (str, bytes, bytearray)):
        raise _InvalidNarrative("claim_sources")
    ids = list(source_ids)
    if not ids or any(not isinstance(source_id, str) or not source_id.strip() for source_id in ids):
        raise _InvalidNarrative("claim_sources")
    if len(ids) != len(set(ids)) or not set(ids).issubset(allowed_ids):
        raise _InvalidNarrative("claim_sources")
    return {"text": clean_text, "source_event_ids": ids}


def _claims_for_block(block: Mapping[str, Any], allowed_ids: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in _NARRATIVE_FIELDS:
        value = block.get(field, _MISSING)
        result[field] = _claim(value, allowed_ids, summary=field == "summary")
    return result


def _apply_narrative(
    content: object,
    groups: list[dict[str, Any]],
    main_event: dict[str, Any] | None,
    impulses: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(content, Mapping) or any(not isinstance(key, str) for key in content):
        raise _InvalidNarrative("narrative_content")
    root = cast(Mapping[str, Any], content)
    raw_convergences = _value(root, "convergences", default=None)
    raw_main = _value(root, "main_event", "mainEvent", default=None)
    raw_impulses = _value(root, "impulses", default=None)

    projected_groups: list[dict[str, Any]] = []
    for group in groups:
        narrative_block = _narrative_block(raw_convergences, str(group["id"]), "convergence_claims")
        claims = {} if narrative_block is None else _claims_for_block(narrative_block, set(group["event_ids"]))
        projected_groups.append({**group, **claims})

    projected_main = main_event
    if main_event is not None:
        if raw_main is None:
            main_claims: dict[str, Any] = {}
        elif not isinstance(raw_main, Mapping):
            raise _InvalidNarrative("main_claims")
        else:
            main_claims = _claims_for_block(raw_main, {str(main_event["event_id"])})
        projected_main = {**main_event, **main_claims}

    projected_impulses: list[dict[str, Any]] = []
    for impulse in impulses:
        narrative_block = _narrative_block(raw_impulses, str(impulse["event_id"]), "impulse_claims")
        claims = {} if narrative_block is None else _claims_for_block(narrative_block, {str(impulse["event_id"])})
        projected_impulses.append({**impulse, **claims})
    return projected_groups, projected_main, projected_impulses


# END_BLOCK: NARRATIVE


# START_BLOCK: ASSEMBLY
def _validate_payload(wire: Mapping[str, Any]) -> TodayConvergencePayload:
    try:
        return TodayConvergencePayload.model_validate(wire)
    except ValidationError as exc:
        _fail("payload_validation", exc)


def _snapshot_payload(
    snapshot: TodaySnapshot,
    narrative: TodaySnapshotNarrative | None,
    access_state: ContentAccessState,
) -> TodayConvergencePayload:
    if access_state.state == "locked":
        _fail("locked_snapshot_forbidden")
    if not isinstance(snapshot, TodaySnapshot):
        _fail("snapshot_type")
    if type(snapshot.target_date) is not date:
        _fail("target_date")
    timezone = _zone(snapshot.timezone)
    if snapshot.id is None:
        _fail("snapshot_id")
    if not isinstance(snapshot.published_at, datetime):
        _fail("published_at")
    if snapshot.formula_version != _FORMULA_VERSION:
        _fail("formula_version")
    calculation_version = _text(snapshot.calculation_version, "calculation_version")
    birth_time = _birth_time_from_snapshot(snapshot)
    _result, selection = _snapshot_selection(snapshot)
    factor_units = _factor_ledger(snapshot)
    groups, main_event, impulses, events = _build_deterministic_blocks(
        snapshot,
        selection,
        factor_units,
        timezone,
    )

    period_context: dict[str, Any] | None = None
    if selection.state == "quiet_day" and main_event is None and not impulses:
        # 04 §3.3: quiet without mainEvent/impulses must carry the honest
        # no_strong_accent period context from the versioned registry —
        # never an LLM placeholder and never a projection failure.
        period_context = {
            "id": "pcx_v1_no_strong_accent",
            "kind": "no_strong_accent",
            "sphere": None,
            "title": _NO_STRONG_ACCENT_TITLE,
            "active_from": None,
            "active_until": None,
            "event_ids": [],
        }

    if access_state.state == "preview":
        wire: dict[str, Any] = {
            "schema_version": 1,
            "snapshot_id": str(snapshot.id),
            "target_date": snapshot.target_date,
            "timezone": snapshot.timezone,
            "published_at": snapshot.published_at,
            "access": access_state,
            "birth_time": birth_time,
            "state": selection.state,
            "day_tone": selection.day_tone,
            "personal": True,
            "preview_teaser": {"spheres": selection.selected_spheres},
            "convergences": [],
            "main_event": None,
            "impulses": [],
            "period_context": None,
            "lookahead": None,
            "events": [],
            "content_state": "not_needed",
            "formula_version": _FORMULA_VERSION,
            "calculation_version": calculation_version,
        }
        return _validate_payload(wire)

    content_state, groups, main_event, impulses = _content_state_and_narrative(
        narrative,
        snapshot,
        groups,
        main_event,
        impulses,
    )
    wire = {
        "schema_version": 1,
        "snapshot_id": str(snapshot.id),
        "target_date": snapshot.target_date,
        "timezone": snapshot.timezone,
        "published_at": snapshot.published_at,
        "access": access_state,
        "birth_time": birth_time,
        "state": selection.state,
        "day_tone": selection.day_tone,
        "personal": True,
        "preview_teaser": None,
        "convergences": groups,
        "main_event": main_event,
        "impulses": impulses,
        "period_context": period_context,
        "lookahead": None,
        "events": events,
        "content_state": content_state,
        "formula_version": _FORMULA_VERSION,
        "calculation_version": calculation_version,
    }
    return _validate_payload(wire)


# END_BLOCK: ASSEMBLY


# START_BLOCK: ENTRYPOINTS
def project_snapshot_payload(
    snapshot: TodaySnapshot,
    narrative: TodaySnapshotNarrative | None,
    access_state: ContentAccessState,
) -> TodayConvergencePayload:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PROJECTION.project_snapshot_payload
    # purpose: Project one published deterministic snapshot into the strict wire root.
    # inputs: snapshot row, optional same-snapshot narrative row, and full/preview/locked access.
    # returns: Validated TodayConvergencePayload with deterministic fields preserved.
    # side_effects: none; does not mutate rows or call external services.
    # emitted_logs: none.
    # error_behavior: Raises TodayConvergenceProjectionError for malformed snapshot,
    #   references, timing, or root invariants; invalid ready narrative becomes unavailable.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PROJECTION.project_snapshot_payload
    access = _validate_access(access_state)
    if not isinstance(snapshot, TodaySnapshot):
        _fail("snapshot_type")
    if narrative is not None and not isinstance(narrative, TodaySnapshotNarrative):
        _fail("narrative_type")
    return _snapshot_payload(snapshot, narrative, access)


def project_empty_payload(
    *,
    target_date: date,
    timezone_name: str,
    birth_time: TodayConvergenceBirthTime,
    access_state: ContentAccessState,
    unavailable: bool,
) -> TodayConvergencePayload:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PROJECTION.project_empty_payload
    # purpose: Build the locked or unavailable wire root when no snapshot is publishable.
    # inputs: target date, IANA timezone, validated birth time, access state, and empty mode.
    # returns: Validated empty TodayConvergencePayload with no deterministic blocks.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Raises TodayConvergenceProjectionError for invalid arguments or
    #   for an unavailable request combined with locked access.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PROJECTION.project_empty_payload
    access = _validate_access(access_state)
    if type(target_date) is not date:
        _fail("target_date")
    _zone(timezone_name)
    if not isinstance(birth_time, TodayConvergenceBirthTime):
        _fail("birth_time_type")
    if not isinstance(unavailable, bool):
        _fail("unavailable_type")
    if access.state == "locked" and unavailable:
        _fail("locked_unavailable_conflict")
    state = "unavailable" if unavailable else None
    wire: dict[str, Any] = {
        "schema_version": 1,
        "snapshot_id": None,
        "target_date": target_date,
        "timezone": timezone_name,
        "published_at": None,
        "access": access,
        "birth_time": birth_time,
        "state": state,
        "day_tone": None,
        "personal": None,
        "preview_teaser": None,
        "convergences": [],
        "main_event": None,
        "impulses": [],
        "period_context": None,
        "lookahead": None,
        "events": [],
        "content_state": "unavailable" if unavailable else "not_needed",
        "formula_version": _FORMULA_VERSION,
        "calculation_version": CALCULATION_VERSION,
    }
    return _validate_payload(wire)


# END_BLOCK: ENTRYPOINTS


__all__ = [
    "TodayConvergenceProjectionError",
    "project_empty_payload",
    "project_snapshot_payload",
]
