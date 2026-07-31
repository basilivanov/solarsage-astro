# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_TODAY_CONVERGENCE — strict P1-F Today wire root.
# ROLE: Owns the isolated Today Convergence envelope and all feature-prefixed nested models.
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-TODAY-CONVERGENCE
# purpose: Define the strict TodayConvergencePayload wire contract for W2/W3.
# owns:
#   - apps/api/app/schemas/today_convergence.py
# inputs: JSON-compatible API payloads.
# outputs: validated CamelModel payloads and nested feature-prefixed models.
# dependencies: Pydantic v2, schemas._base.CamelModel, schemas.access.ContentAccessState.
# side_effects: none.
# emitted_logs: none.
# invariants: extra fields, legacy Today fields, invalid state projections, and dangling IDs are rejected.
# failure_policy: deterministic ValidationError reason tokens; no compatibility projection.
# END_MODULE_CONTRACT: M-SCHEMAS-TODAY-CONVERGENCE

# START_MODULE_MAP: M-SCHEMAS-TODAY-CONVERGENCE
# public_entrypoints:
#   - TodayConvergencePayload
#   - TodayConvergenceBirthCapabilities
#   - TodayConvergenceBirthTime
#   - TodayConvergencePreviewTeaser
#   - TodayConvergenceNarrativeClaim
#   - TodayConvergenceSummary
#   - TodayConvergenceEventTime
#   - TodayConvergenceEvent
#   - TodayConvergenceGroup
#   - TodayConvergenceMainEvent
#   - TodayConvergenceImpulse
#   - TodayConvergencePeriodContext
#   - TodayConvergenceLookahead
# semantic_blocks:
#   - BIRTH_TIME: birth mode, range, and calculation capabilities.
#   - EVENT_PRESENTATION: event ledger and presentation precision.
#   - CONTENT_BLOCKS: convergence, quiet-day, period, and narrative shapes.
#   - ROOT_VALIDATION: access/state/content matrix and reference integrity.
# owned_tests:
#   - apps/api/tests/test_today_convergence_contract.py
# END_MODULE_MAP: M-SCHEMAS-TODAY-CONVERGENCE

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, ClassVar, Literal
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator

from ._base import CamelModel
from .access import ContentAccessState


CanonicalSphere = Literal[
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
]
ConvergenceState = Literal["convergence_today", "quiet_day", "unavailable"]
DayTone = Literal["steady", "supportive", "mixed", "tense"]
ContentState = Literal["ready", "pending", "unavailable", "not_needed"]
Polarity = Literal["supportive", "tense", "mixed"]
EvidenceLevel = Literal["high", "medium"]
BirthMode = Literal["exact", "bucket", "unknown"]
BirthBucket = Literal["night", "morning", "day", "evening"]
EventTimeMode = Literal["exact", "partofday", "date"]
PartOfDay = Literal["night", "morning", "day", "evening"]
PeriodKind = Literal["active_period", "no_strong_accent"]

_CLOCK_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_CLOCK_OR_END_RE = re.compile(r"^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$")


def _fail(token: str) -> None:
    raise ValueError(f"today_convergence:{token}")


def _non_empty(value: str, token: str) -> None:
    if not value.strip():
        _fail(token)


def _unique(values: list[str], token: str = "duplicate_id") -> None:
    if len(values) != len(set(values)):
        _fail(token)


def _validate_id_list(values: list[str], token: str = "empty_id") -> None:
    for value in values:
        _non_empty(value, token)
    _unique(values)


def _valid_clock(value: str, token: str = "event_time_clock_format") -> None:
    if not _CLOCK_RE.fullmatch(value):
        _fail(token)


def _valid_clock_or_end(value: str, token: str) -> None:
    if not _CLOCK_OR_END_RE.fullmatch(value):
        _fail(token)


# START_BLOCK: BIRTH_TIME
class TodayConvergenceBirthCapabilities(CamelModel):
    houses: bool
    angles: bool
    lots: bool
    exact_timing: bool


class TodayConvergenceBirthTime(CamelModel):
    mode: BirthMode
    bucket: BirthBucket | None
    range_start: str
    range_end: str
    capabilities: TodayConvergenceBirthCapabilities

    @model_validator(mode="after")
    def validate_birth_time(self) -> TodayConvergenceBirthTime:
        if self.mode == "exact":
            _valid_clock(self.range_start, "birth_exact_range")
            _valid_clock(self.range_end, "birth_exact_range")
            if self.bucket is not None or self.range_start != self.range_end:
                _fail("birth_exact_range")
            if not all(vars(self.capabilities).values()):
                _fail("birth_exact_capabilities")
        elif self.mode == "bucket":
            ranges = {
                "night": ("00:00", "06:00"),
                "morning": ("06:00", "12:00"),
                "day": ("12:00", "18:00"),
                "evening": ("18:00", "24:00"),
            }
            if self.bucket is None or (self.range_start, self.range_end) != ranges[self.bucket]:
                _fail("birth_bucket_range")
            if any(vars(self.capabilities).values()):
                _fail("birth_bucket_capabilities")
        else:
            if self.bucket is not None or (self.range_start, self.range_end) != ("00:00", "24:00"):
                _fail("birth_unknown_range")
            if any(vars(self.capabilities).values()):
                _fail("birth_unknown_capabilities")
        return self


# END_BLOCK: BIRTH_TIME


# START_BLOCK: CONTENT_BLOCKS
class TodayConvergencePreviewTeaser(CamelModel):
    spheres: list[CanonicalSphere] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def validate_spheres(self) -> TodayConvergencePreviewTeaser:
        _unique(self.spheres)
        return self


class TodayConvergenceNarrativeClaim(CamelModel):
    text: str = Field(..., min_length=1)
    source_event_ids: list[str] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_sources(self) -> TodayConvergenceNarrativeClaim:
        _validate_id_list(self.source_event_ids)
        return self


class TodayConvergenceSummary(TodayConvergenceNarrativeClaim):
    text: str = Field(..., min_length=1, max_length=220)

    @model_validator(mode="before")
    @classmethod
    def validate_summary_length(cls, value: Any) -> Any:
        if isinstance(value, dict) and isinstance(value.get("text"), str) and len(value["text"]) > 220:
            _fail("summary_text_too_long")
        return value


# START_BLOCK: EVENT_PRESENTATION
class TodayConvergenceEventTime(CamelModel):
    mode: EventTimeMode
    peak: str | None = None
    start: str | None = None
    end: str | None = None
    part_of_day: PartOfDay | None = None

    @model_validator(mode="after")
    def validate_event_time(self) -> TodayConvergenceEventTime:
        clocks = (self.peak, self.start, self.end)
        if self.mode == "exact":
            if self.part_of_day is not None:
                _fail("event_time_exact_part_of_day")
            for value in clocks:
                if value is not None:
                    _valid_clock(value)
        elif self.mode == "partofday":
            if self.part_of_day is None:
                _fail("event_time_partofday_missing")
            if any(value is not None for value in clocks):
                _fail("event_time_partofday_clock")
        else:
            if any(value is not None for value in clocks) or self.part_of_day is not None:
                _fail("event_time_date_fields")
        return self


class TodayConvergenceEvent(CamelModel):
    id: str
    kind: str
    sphere: CanonicalSphere
    polarity: Polarity
    evidence_level: EvidenceLevel
    time: TodayConvergenceEventTime
    source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_event(self) -> TodayConvergenceEvent:
        _non_empty(self.id, "empty_id")
        _unique(self.source_ids)
        for value in self.source_ids:
            _non_empty(value, "empty_id")
        return self


# END_BLOCK: EVENT_PRESENTATION


class TodayConvergenceGroup(CamelModel):
    id: str
    primary_sphere: CanonicalSphere
    secondary_sphere: CanonicalSphere | None = None
    polarity: Polarity
    evidence_level: EvidenceLevel
    event_ids: list[str] = Field(..., min_length=2)
    summary: TodayConvergenceSummary | None = None
    meaning: TodayConvergenceNarrativeClaim | None = None
    action: TodayConvergenceNarrativeClaim | None = None

    @model_validator(mode="after")
    def validate_group(self) -> TodayConvergenceGroup:
        _non_empty(self.id, "empty_id")
        _validate_id_list(self.event_ids)
        if len(self.event_ids) < 2:
            _fail("group_event_count")
        if self.primary_sphere == self.secondary_sphere:
            _fail("group_sphere_distinct")
        return self


class TodayConvergenceMainEvent(CamelModel):
    id: str
    event_id: str
    sphere: CanonicalSphere
    polarity: Polarity
    evidence_level: EvidenceLevel
    time: TodayConvergenceEventTime
    summary: TodayConvergenceSummary | None = None
    meaning: TodayConvergenceNarrativeClaim | None = None
    action: TodayConvergenceNarrativeClaim | None = None

    @model_validator(mode="after")
    def validate_main_event(self) -> TodayConvergenceMainEvent:
        _non_empty(self.id, "empty_id")
        _non_empty(self.event_id, "empty_id")
        return self


class TodayConvergenceImpulse(CamelModel):
    event_id: str
    sphere: CanonicalSphere
    polarity: Polarity
    evidence_level: EvidenceLevel
    time: TodayConvergenceEventTime
    summary: TodayConvergenceSummary | None = None
    meaning: TodayConvergenceNarrativeClaim | None = None
    action: TodayConvergenceNarrativeClaim | None = None

    @model_validator(mode="after")
    def validate_impulse(self) -> TodayConvergenceImpulse:
        _non_empty(self.event_id, "empty_id")
        return self


class TodayConvergencePeriodContext(CamelModel):
    id: str
    kind: PeriodKind
    sphere: CanonicalSphere | None
    title: str | None
    active_from: date | None
    active_until: date | None
    event_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_period(self) -> TodayConvergencePeriodContext:
        _non_empty(self.id, "empty_id")
        _validate_id_list(self.event_ids)
        if self.kind == "no_strong_accent":
            if self.sphere is not None or self.active_from is not None or self.active_until is not None or self.event_ids:
                _fail("no_strong_accent_fields")
            if not self.title:
                _fail("period_title_required")
        else:
            if self.sphere is None or not self.title or self.active_from is None or self.active_until is None:
                _fail("active_period_fields")
            if self.active_until < self.active_from:
                _fail("active_period_date_order")
        return self


class TodayConvergenceLookahead(CamelModel):
    target_date: date
    sphere: CanonicalSphere
    snapshot_id: str

    @model_validator(mode="after")
    def validate_lookahead(self) -> TodayConvergenceLookahead:
        _non_empty(self.snapshot_id, "empty_id")
        return self


# END_BLOCK: CONTENT_BLOCKS


# START_BLOCK: ROOT_VALIDATION
class TodayConvergencePayload(CamelModel):
    schema_version: Literal[1]
    snapshot_id: str | None
    target_date: date
    timezone: str
    published_at: datetime | None
    access: ContentAccessState
    birth_time: TodayConvergenceBirthTime
    state: ConvergenceState | None
    day_tone: DayTone | None
    personal: bool | None
    preview_teaser: TodayConvergencePreviewTeaser | None
    convergences: list[TodayConvergenceGroup] = Field(..., max_length=3)
    main_event: TodayConvergenceMainEvent | None
    impulses: list[TodayConvergenceImpulse] = Field(..., max_length=3)
    period_context: TodayConvergencePeriodContext | None
    lookahead: TodayConvergenceLookahead | None
    events: list[TodayConvergenceEvent]
    content_state: ContentState
    formula_version: Literal["today-convergence-2"]
    calculation_version: str = Field(..., min_length=1)

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset({
        "schema_version", "schemaVersion", "snapshot_id", "snapshotId", "target_date", "targetDate",
        "timezone", "published_at", "publishedAt", "access", "birth_time", "birthTime", "state",
        "day_tone", "dayTone", "personal", "preview_teaser", "previewTeaser", "convergences",
        "main_event", "mainEvent", "impulses", "period_context", "periodContext", "lookahead",
        "events", "content_state", "contentState", "formula_version", "formulaVersion",
        "calculation_version", "calculationVersion",
    })

    @model_validator(mode="before")
    @classmethod
    def reject_unknown_and_legacy_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            legacy = {"dayStatus", "day_status", "relativeStatus", "relative_status", "v2", "focus"}
            if legacy.intersection(value):
                _fail("legacy_field_rejected")
            unknown = set(value) - cls._ROOT_KEYS
            if unknown:
                _fail("extra_field_rejected")
        return value

    @model_validator(mode="after")
    def validate_root(self) -> TodayConvergencePayload:
        try:
            ZoneInfo(self.timezone)
        except Exception:
            _fail("timezone_invalid")

        if len(self.convergences) > 3 or len(self.impulses) > 3:
            _fail("root_cap")

        event_ids = [event.id for event in self.events]
        convergence_ids = [group.id for group in self.convergences]
        _validate_id_list(event_ids)
        _validate_id_list(convergence_ids)

        if self.state is None and self.access.state != "locked":
            _fail("state_required")
        if self.access.state == "locked":
            if any(value is not None for value in (self.state, self.day_tone, self.personal, self.snapshot_id, self.published_at)):
                _fail("locked_state_null")
            if self.content_state != "not_needed":
                _fail("locked_content_state")
            if any((self.preview_teaser, self.convergences, self.main_event, self.impulses, self.period_context, self.lookahead, self.events)):
                _fail("locked_projection_empty")
        elif self.state == "unavailable":
            if self.snapshot_id is not None or self.published_at is not None:
                _fail("unavailable_snapshot_null")
            if self.day_tone is not None or self.personal is not None or self.preview_teaser is not None:
                _fail("unavailable_projection_empty")
            if self.convergences or self.main_event or self.impulses or self.period_context or self.lookahead or self.events:
                _fail("unavailable_projection_empty")
            if self.content_state != "unavailable":
                _fail("unavailable_content_state")
        elif self.access.state == "preview":
            if self.snapshot_id is None or self.published_at is None or self.day_tone is None or self.personal is None:
                _fail("preview_snapshot_required")
            if self.preview_teaser is None:
                _fail("preview_teaser_required")
            if self.content_state != "not_needed":
                _fail("preview_content_state")
            if self.convergences or self.main_event or self.impulses or self.period_context or self.lookahead or self.events:
                _fail("preview_hidden_events")
        elif self.state in {"convergence_today", "quiet_day"}:
            if self.snapshot_id is None or self.published_at is None or self.day_tone is None or self.personal is None:
                _fail("calculated_snapshot_required")
            if self.preview_teaser is not None:
                _fail("full_preview_forbidden")

        if self.state in {"convergence_today", "quiet_day"}:
            allowed = {"ready", "pending", "unavailable"}
            if self.state == "quiet_day":
                allowed.add("not_needed")
            if self.access.state == "preview":
                allowed = {"not_needed"}
            if self.content_state not in allowed:
                _fail("state_content_state")
        elif self.state == "unavailable" and self.content_state != "unavailable":
            _fail("state_content_state")

        if self.state == "convergence_today":
            if self.access.state == "full" and not 1 <= len(self.convergences) <= 3:
                _fail("convergence_group_count")
            if self.main_event is not None:
                _fail("convergence_main_event_forbidden")
            if self.impulses:
                _fail("convergence_impulses_forbidden")
            if self.lookahead is not None:
                _fail("convergence_lookahead_forbidden")
        elif self.state == "quiet_day":
            if self.convergences:
                _fail("quiet_convergences_forbidden")
            if self.main_event is None and not self.impulses and self.period_context is None:
                _fail("quiet_content_required")
        elif self.lookahead is not None:
            _fail("lookahead_state_forbidden")

        selected_event_ids: set[str] = set()
        for group in self.convergences:
            selected_event_ids.update(group.event_ids)
        if self.main_event is not None:
            selected_event_ids.add(self.main_event.event_id)
        for impulse in self.impulses:
            selected_event_ids.add(impulse.event_id)
        if self.period_context is not None:
            selected_event_ids.update(self.period_context.event_ids)
        actual_event_ids = set(event_ids)
        if not selected_event_ids.issubset(actual_event_ids):
            _fail("event_reference_missing")
        if actual_event_ids != selected_event_ids:
            _fail("event_ledger_mismatch")

        presentation_spheres: set[str] = set()
        for group in self.convergences:
            presentation_spheres.add(group.primary_sphere)
            if group.secondary_sphere is not None:
                presentation_spheres.add(group.secondary_sphere)
            for narrative in (group.summary, group.meaning, group.action):
                self._validate_narrative(narrative, selected_event_ids)
        for block in (self.main_event, *self.impulses):
            if block is None:
                continue
            presentation_spheres.add(block.sphere)
            for narrative in (block.summary, block.meaning, block.action):
                self._validate_narrative(narrative, selected_event_ids)
        if len(presentation_spheres) > 3:
            _fail("sphere_union_cap")

        presented_times = [event.time for event in self.events]
        if self.main_event is not None:
            presented_times.append(self.main_event.time)
        presented_times.extend(impulse.time for impulse in self.impulses)
        if self.birth_time.mode == "bucket" and any(item.mode != "partofday" for item in presented_times):
            _fail("birth_event_time_precision")
        if self.birth_time.mode == "unknown" and any(item.mode not in {"partofday", "date"} for item in presented_times):
            _fail("birth_event_time_precision")
        for event in self.events:
            _unique(event.source_ids)
        return self

    def _validate_narrative(
        self,
        narrative: TodayConvergenceNarrativeClaim | None,
        selected_event_ids: set[str],
    ) -> None:
        if narrative is None:
            return
        if self.content_state != "ready":
            _fail("narrative_content_state")
        if not set(narrative.source_event_ids).issubset(selected_event_ids):
            _fail("narrative_source_event_unknown")


# END_BLOCK: ROOT_VALIDATION


__all__ = [
    "CanonicalSphere",
    "TodayConvergenceBirthCapabilities",
    "TodayConvergenceBirthTime",
    "TodayConvergencePreviewTeaser",
    "TodayConvergenceNarrativeClaim",
    "TodayConvergenceSummary",
    "TodayConvergenceEventTime",
    "TodayConvergenceEvent",
    "TodayConvergenceGroup",
    "TodayConvergenceMainEvent",
    "TodayConvergenceImpulse",
    "TodayConvergencePeriodContext",
    "TodayConvergenceLookahead",
    "TodayConvergencePayload",
]
