# ############################################################################
# AI_HEADER: MODULE_CONTRACTS_TODAY_HORIZONS — additive Today V2 horizon wire contract.
# ROLE: Defines the public TodayV2 horizons block and pure validators used by
#       TodayV2Block to validate cross-reference and timing integrity.
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS-TODAY-HORIZONS
# purpose: Own the public horizon wire models, literal aliases, and pure
#          validation helpers for the additive Today V2 horizons contract.
# owns:
#   - apps/api/app/schemas/today_horizons.py
# inputs: Pydantic model input payloads and activation evidence collections.
# outputs: TodayV2 horizon models plus validate_horizons_against_evidence helper.
# dependencies: datetime/re stdlib, pydantic, app.schemas._base.CamelModel.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Validation errors identify structural path/id/reason and do not include raw human claim text.
#   - Wire strings are preserved exactly; normalized values are used only for validation/comparison.
#   - This module does not import services, settings, DB, sidecar, or frontend code.
# failure_policy: raises Pydantic ValidationError/ValueError on invalid wire input.
# END_MODULE_CONTRACT: M-CONTRACTS-TODAY-HORIZONS

# START_MODULE_MAP: M-CONTRACTS-TODAY-HORIZONS
# public_entrypoints:
#   - TodayV2HorizonId
#   - TodayV2HorizonTone
#   - TodayV2TimingState
#   - TodayV2TimingPrecision
#   - TodayV2ClaimKind
#   - TodayV2GuidanceMode
#   - TodayV2ProductSphereKey
#   - TodayV2Provenance
#   - TodayV2GroundedItem
#   - TodayV2HorizonTiming
#   - TodayV2TechniqueExplanation
#   - TodayV2Manifestation
#   - TodayV2HorizonActions
#   - TodayV2Horizon
#   - TodayV2HorizonIntro
#   - TodayV2HorizonsBlock
#   - validate_horizons_against_evidence
# semantic_blocks:
#   - HORIZON_TYPE_ALIASES: public literals and constrained scalar aliases.
#   - HORIZON_VALIDATION_HELPERS: pure parsers, normalizers, and uniqueness helpers.
#   - HORIZON_WIRE_MODELS: public horizon block models and per-model validators.
#   - CROSS_REFERENCE_VALIDATION: evidence-backed integrity checks used from TodayV2Block.
# owned_tests:
#   - apps/api/tests/test_today_horizons_contract.py
#   - apps/api/tests/test_contract_registry.py
# END_MODULE_MAP: M-CONTRACTS-TODAY-HORIZONS

# START_BLOCK: HORIZON_TYPE_ALIASES
from __future__ import annotations

from datetime import date, datetime
import re
from typing import TYPE_CHECKING, AbstractSet, Annotated, Any, Literal, Sequence

from pydantic import Field, field_validator, model_validator

from ._base import CamelModel

if TYPE_CHECKING:
    from .activation import ActivationEvidence


TodayV2HorizonId = Literal["long", "medium", "fast"]

TodayV2HorizonTone = Literal[
    "supportive",
    "neutral",
    "tense",
    "mixed",
]

TodayV2TimingState = Literal[
    "upcoming",
    "building",
    "active",
    "exact",
    "peaked",
    "fading",
    "background",
]

TodayV2TimingPrecision = Literal["date", "instant"]

TodayV2ClaimKind = Literal[
    "explanation",
    "strength",
    "risk",
    "manifestation",
    "action",
    "avoid",
    "technique_definition",
]

TodayV2GuidanceMode = Literal["deterministic", "llm_refined"]

TodayV2ProductSphereKey = Literal[
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

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
OPAQUE_FACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
TERMINAL_ACTION_PUNCTUATION_RE = re.compile(r"[.,!?:;—-]+$")
WHITESPACE_RE = re.compile(r"\s+")

IdStr = Annotated[str, Field(min_length=1, max_length=160)]
LabelStr = Annotated[str, Field(min_length=1, max_length=160)]
TitleStr = Annotated[str, Field(min_length=1, max_length=240)]
BodyStr = Annotated[str, Field(min_length=1, max_length=1200)]
TimezoneStr = Annotated[str, Field(min_length=1, max_length=80)]
OpaqueFactId = Annotated[
    str,
    Field(min_length=2, max_length=128, pattern=OPAQUE_FACT_ID_RE.pattern),
]
# END_BLOCK: HORIZON_TYPE_ALIASES


# START_BLOCK: HORIZON_VALIDATION_HELPERS
def _raise_contract_error(path: str, reason: str, *, item_id: str | None = None) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._raise_contract_error
    # purpose: Raise a deterministic structural validation error without leaking human body text.
    # inputs: path - structural path; reason - concise machine-readable reason; item_id - optional stable id.
    # returns: never; raises ValueError.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: always raises ValueError.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._raise_contract_error
    parts = [path, reason]
    if item_id:
        parts.append(f"id={item_id}")
    raise ValueError(" | ".join(parts))


def _ensure_unique(values: Sequence[str], path: str, *, item_id: str | None = None) -> Sequence[str]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._ensure_unique
    # purpose: Reject duplicates while preserving caller-owned order and data.
    # inputs: values - ordered scalar ids/strings; path - structural error path; item_id - optional parent id.
    # returns: the original input sequence unchanged when unique.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError on first duplicate.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._ensure_unique
    seen: set[str] = set()
    for value in values:
        if value in seen:
            _raise_contract_error(path, f"duplicate:{value}", item_id=item_id)
        seen.add(value)
    return values


def _ensure_non_empty_after_strip(value: str, path: str, *, item_id: str | None = None) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._ensure_non_empty_after_strip
    # purpose: Reject strings that become empty after trimming without mutating wire values.
    # inputs: value - wire string; path - structural path; item_id - optional parent id.
    # returns: original string unchanged.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError when stripped string is empty.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._ensure_non_empty_after_strip
    if not value.strip():
        _raise_contract_error(path, "blank-after-strip", item_id=item_id)
    return value


def _normalize_action_text(value: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._normalize_action_text
    # purpose: Build the duplicate-detection key for action/avoid text without mutating wire text.
    # inputs: value - original action text.
    # returns: normalized comparison key.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._normalize_action_text
    normalized = value.strip().casefold()
    normalized = WHITESPACE_RE.sub(" ", normalized)
    normalized = TERMINAL_ACTION_PUNCTUATION_RE.sub("", normalized)
    return normalized.strip()


def _parse_date_value(value: str, path: str, *, item_id: str | None = None) -> date:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._parse_date_value
    # purpose: Validate exact YYYY-MM-DD timing strings and parse them for comparison.
    # inputs: value - wire date string; path - structural path; item_id - optional parent id.
    # returns: parsed date.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError on malformed or non-date input.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._parse_date_value
    if not DATE_RE.fullmatch(value):
        _raise_contract_error(path, "expected-date-precision", item_id=item_id)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{path} | invalid-date" + (f" | id={item_id}" if item_id else "")) from exc


def _parse_instant_value(value: str, path: str, *, item_id: str | None = None) -> datetime:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._parse_instant_value
    # purpose: Validate RFC3339/ISO datetimes with explicit offset and parse them for comparison.
    # inputs: value - wire instant string; path - structural path; item_id - optional parent id.
    # returns: timezone-aware datetime preserving original wire string outside this helper.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError on malformed or naive datetimes.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._parse_instant_value
    if not INSTANT_RE.fullmatch(value):
        _raise_contract_error(path, "expected-instant-precision", item_id=item_id)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path} | invalid-instant" + (f" | id={item_id}" if item_id else "")) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _raise_contract_error(path, "naive-datetime", item_id=item_id)
    return parsed


def _parse_timing_value(value: str, precision: TodayV2TimingPrecision, path: str, *, item_id: str | None = None) -> date | datetime:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._parse_timing_value
    # purpose: Parse a timing boundary according to the declared precision while preserving wire strings elsewhere.
    # inputs: value - wire timing string; precision - date|instant; path - structural path; item_id - optional parent id.
    # returns: comparable date/datetime value.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError on precision mismatch.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._parse_timing_value
    return _parse_date_value(value, path, item_id=item_id) if precision == "date" else _parse_instant_value(value, path, item_id=item_id)


def _evidence_attr(item: Any, name: str) -> Any:
    return getattr(item, name, None)


def _collect_provenance_activation_ids(horizon: "TodayV2Horizon") -> list[tuple[str, str]]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._collect_provenance_activation_ids
    # purpose: Enumerate every nested provenance activation reference for subset validation.
    # inputs: horizon - validated horizon model.
    # returns: ordered list of (path, activation_id) tuples.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._collect_provenance_activation_ids
    references: list[tuple[str, str]] = []

    def extend_from_provenance(path: str, provenance: TodayV2Provenance) -> None:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._collect_provenance_activation_ids.extend_from_provenance
        # purpose: Append every activation id from one provenance object with its structural path to the enclosing references accumulator.
        # inputs: path - already-built structural path; provenance - typed provenance.
        # returns: none.
        # side_effects: mutates only the enclosing local references list.
        # emitted_logs: none.
        # error_behavior: none; iterates the validated activation_ids list.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._collect_provenance_activation_ids.extend_from_provenance
        for activation_id in provenance.activation_ids:
            references.append((path, activation_id))

    if horizon.strength is not None:
        extend_from_provenance(f"horizon[{horizon.id}].strength.provenance", horizon.strength.provenance)
    if horizon.risk is not None:
        extend_from_provenance(f"horizon[{horizon.id}].risk.provenance", horizon.risk.provenance)
    for manifestation in horizon.manifestations:
        extend_from_provenance(
            f"horizon[{horizon.id}].manifestation[{manifestation.id}].provenance",
            manifestation.provenance,
        )
    for item in horizon.actions.do:
        extend_from_provenance(f"horizon[{horizon.id}].actions.do[{item.id}].provenance", item.provenance)
    for item in horizon.actions.avoid:
        extend_from_provenance(f"horizon[{horizon.id}].actions.avoid[{item.id}].provenance", item.provenance)
    return references


def _has_non_null_timing_fields(item: Any) -> bool:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._has_non_null_timing_fields
    # purpose: Decide whether an activation evidence item carries any explicit timing support.
    # inputs: item - activation evidence model or dict-like object.
    # returns: true when active_from, active_until, or exact_at is non-null.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._has_non_null_timing_fields
    return any(
        _evidence_attr(item, field_name) is not None
        for field_name in ("active_from", "active_until", "exact_at")
    )


def _validate_provenance_sphere_subset(
    provenance: "TodayV2Provenance",
    *,
    path: str,
    item_id: str,
    likely_spheres: AbstractSet[str],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._validate_provenance_sphere_subset
    # purpose: Reject provenance sphere keys that escape the horizon likely_spheres contract.
    # inputs: provenance - nested provenance model; path - structural path; item_id - stable nested item id; likely_spheres - read-only allowed sphere key set.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError with structural reason when provenance sphere keys are outside likely_spheres.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._validate_provenance_sphere_subset
    if not set(provenance.sphere_keys).issubset(likely_spheres):
        _raise_contract_error(path, "provenance-spheres-outside-likely-spheres", item_id=item_id)


def _validate_technique_explanation_timing_support(
    *,
    horizon_id: str,
    explanation: "TodayV2TechniqueExplanation",
    referenced_items: Sequence[Any],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._validate_technique_explanation_timing_support
    # purpose: Ensure explanation timing is backed by at least one timed evidence item of the same technique.
    # inputs: horizon_id - parent horizon id; explanation - technique explanation model; referenced_items - evidence resolved from explanation.activation_ids.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError when explanation.timing is set but every matching referenced evidence is untimed.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS._validate_technique_explanation_timing_support
    if explanation.timing is None:
        return
    matching_timed_evidence = [
        item
        for item in referenced_items
        if _evidence_attr(item, "technique") == explanation.technique and _has_non_null_timing_fields(item)
    ]
    if not matching_timed_evidence:
        _raise_contract_error(
            f"todayV2HorizonsBlock.items[{horizon_id}].techniqueExplanations",
            "technique-timing-without-timed-evidence",
            item_id=explanation.technique,
        )
# END_BLOCK: HORIZON_VALIDATION_HELPERS


# START_BLOCK: HORIZON_WIRE_MODELS
class TodayV2Provenance(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    activation_ids: list[IdStr] = Field(default_factory=list)
    natal_fact_ids: list[OpaqueFactId] = Field(default_factory=list)
    profile_fact_ids: list[OpaqueFactId] = Field(default_factory=list)
    sphere_keys: list[TodayV2ProductSphereKey] = Field(default_factory=list)

    @field_validator("activation_ids", "natal_fact_ids", "profile_fact_ids", "sphere_keys", mode="after")
    @classmethod
    def validate_unique_lists(cls, values: list[str]) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Provenance.validate_unique_lists
        # purpose: Enforce uniqueness for each provenance scalar list.
        # inputs: values - validated field list selected by the Pydantic field validator.
        # returns: the same list unchanged when unique.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError through _ensure_unique on duplicates.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Provenance.validate_unique_lists
        _ensure_unique(values, "todayV2Provenance.list")
        return values
    @model_validator(mode="after")
    def validate_non_empty_sources(self) -> "TodayV2Provenance":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Provenance.validate_non_empty_sources
        # purpose: Require at least one non-empty provenance source list.
        # inputs: self - validated provenance candidate.
        # returns: the same model when at least one source list is populated.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError when all four source lists are empty.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Provenance.validate_non_empty_sources
        if not any((self.activation_ids, self.natal_fact_ids, self.profile_fact_ids, self.sphere_keys)):
            _raise_contract_error("todayV2Provenance", "at-least-one-source-list-required")
        return self


class TodayV2GroundedItem(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    id: IdStr
    kind: TodayV2ClaimKind
    text: BodyStr
    conditional: bool = False
    provenance: TodayV2Provenance


class TodayV2HorizonTiming(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    active_from: str
    exact_at: str | None = None
    active_until: str
    precision: TodayV2TimingPrecision
    state: TodayV2TimingState
    range_label: LabelStr
    peak_label: LabelStr | None = None
    state_label: LabelStr
    timezone: TimezoneStr

    @field_validator("range_label", "state_label", "timezone", mode="after")
    @classmethod
    def validate_non_blank_labels(cls, value: str, info: Any) -> str:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_non_blank_labels
        # purpose: Reject blank range/state/timezone label fields.
        # inputs: value - field string; info - Pydantic field metadata.
        # returns: the original value when non-blank after stripping for validation.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError through _ensure_non_empty_after_strip.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_non_blank_labels
        return _ensure_non_empty_after_strip(value, f"todayV2HorizonTiming.{info.field_name}")
    @field_validator("peak_label", mode="after")
    @classmethod
    def validate_peak_label(cls, value: str | None) -> str | None:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_peak_label
        # purpose: Permit a null peak label or reject a present blank peak label.
        # inputs: value - optional peak label.
        # returns: None unchanged or the original validated non-blank string.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for a present blank label.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_peak_label
        if value is None:
            return value
        return _ensure_non_empty_after_strip(value, "todayV2HorizonTiming.peakLabel")

    @model_validator(mode="after")
    def validate_timing(self) -> "TodayV2HorizonTiming":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_timing
        # purpose: Enforce precision-aware timing boundaries, exact/peak coupling, and exact-state requirements.
        # inputs: self - validated timing model candidate.
        # returns: the same timing model when contract invariants hold.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on malformed ranges, mismatched precision, or missing exact/peak companions.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonTiming.validate_timing
        active_from = _parse_timing_value(self.active_from, self.precision, "todayV2HorizonTiming.activeFrom")
        active_until = _parse_timing_value(self.active_until, self.precision, "todayV2HorizonTiming.activeUntil")
        if active_from > active_until:
            _raise_contract_error("todayV2HorizonTiming", "active-from-after-active-until")

        if self.exact_at is not None:
            exact_at = _parse_timing_value(self.exact_at, self.precision, "todayV2HorizonTiming.exactAt")
            if exact_at < active_from or exact_at > active_until:
                _raise_contract_error("todayV2HorizonTiming", "exact-at-outside-range")
            if self.peak_label is None:
                _raise_contract_error("todayV2HorizonTiming", "exact-at-requires-peak-label")
        else:
            if self.peak_label is not None:
                _raise_contract_error("todayV2HorizonTiming", "peak-label-requires-exact-at")
            exact_at = None

        if self.state == "exact" and exact_at is None:
            _raise_contract_error("todayV2HorizonTiming", "exact-state-requires-exact-at")
        return self


class TodayV2TechniqueExplanation(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    technique: LabelStr
    label: LabelStr
    what_it_is: BodyStr
    why_it_matters_now: BodyStr
    timing: TodayV2HorizonTiming | None = None
    activation_ids: list[IdStr] = Field(min_length=1)

    @field_validator("technique", "label", "what_it_is", "why_it_matters_now", mode="after")
    @classmethod
    def validate_non_blank_fields(cls, value: str, info: Any) -> str:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2TechniqueExplanation.validate_non_blank_fields
        # purpose: Reject blank technique, label, definition and relevance copy.
        # inputs: value - field string; info - Pydantic field metadata.
        # returns: the original non-blank value.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for blank copy.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2TechniqueExplanation.validate_non_blank_fields
        return _ensure_non_empty_after_strip(value, f"todayV2TechniqueExplanation.{info.field_name}")
    @field_validator("activation_ids", mode="after")
    @classmethod
    def validate_activation_ids_unique(cls, values: list[str]) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2TechniqueExplanation.validate_activation_ids_unique
        # purpose: Enforce unique activation references in one technique explanation.
        # inputs: values - activation id list.
        # returns: the same list unchanged when unique.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError on duplicate ids.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2TechniqueExplanation.validate_activation_ids_unique
        _ensure_unique(values, "todayV2TechniqueExplanation.activationIds")
        return values


class TodayV2Manifestation(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    id: IdStr
    title: TitleStr
    body: BodyStr
    condition: BodyStr | None = None
    sphere_keys: list[TodayV2ProductSphereKey] = Field(min_length=1, max_length=3)
    provenance: TodayV2Provenance

    @field_validator("title", "body", mode="after")
    @classmethod
    def validate_non_blank_fields(cls, value: str, info: Any) -> str:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_non_blank_fields
        # purpose: Reject blank manifestation title/body copy.
        # inputs: value - field string; info - Pydantic field metadata.
        # returns: the original non-blank value.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for blank copy.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_non_blank_fields
        return _ensure_non_empty_after_strip(value, f"todayV2Manifestation.{info.field_name}")
    @field_validator("condition", mode="after")
    @classmethod
    def validate_condition(cls, value: str | None) -> str | None:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_condition
        # purpose: Permit a null condition or reject a present blank condition.
        # inputs: value - optional condition copy.
        # returns: None unchanged or the original validated non-blank string.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for a present blank condition.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_condition
        if value is None:
            return value
        return _ensure_non_empty_after_strip(value, "todayV2Manifestation.condition")
    @field_validator("sphere_keys", mode="after")
    @classmethod
    def validate_sphere_keys_unique(cls, values: list[str]) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_sphere_keys_unique
        # purpose: Enforce unique sphere references in one manifestation.
        # inputs: values - sphere key list.
        # returns: the same list unchanged when unique.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError on duplicate keys.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Manifestation.validate_sphere_keys_unique
        _ensure_unique(values, "todayV2Manifestation.sphereKeys")
        return values


class TodayV2HorizonActions(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    heading: LabelStr
    valid_until: str
    valid_until_label: LabelStr
    do: list[TodayV2GroundedItem] = Field(min_length=1)
    avoid: list[TodayV2GroundedItem] = Field(min_length=1)

    @field_validator("heading", "valid_until_label", mode="after")
    @classmethod
    def validate_non_blank_fields(cls, value: str, info: Any) -> str:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonActions.validate_non_blank_fields
        # purpose: Reject blank action heading and valid-until label.
        # inputs: value - field string; info - Pydantic field metadata.
        # returns: the original non-blank value.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for blank copy.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonActions.validate_non_blank_fields
        return _ensure_non_empty_after_strip(value, f"todayV2HorizonActions.{info.field_name}")

    @model_validator(mode="after")
    def validate_actions(self) -> "TodayV2HorizonActions":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonActions.validate_actions
        # purpose: Enforce action/avoid kind integrity, unique ids, and normalized human-text uniqueness inside one horizon action block.
        # inputs: self - validated horizon actions candidate.
        # returns: the same actions model when list semantics are valid.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on kind mismatches, duplicate ids, or duplicate normalized text.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonActions.validate_actions
        ids_seen: set[str] = set()
        normalized_texts: set[str] = set()
        for list_name, expected_kind, items in (("do", "action", self.do), ("avoid", "avoid", self.avoid)):
            for item in items:
                if item.kind != expected_kind:
                    _raise_contract_error(
                        f"todayV2HorizonActions.{list_name}",
                        f"kind-mismatch:{item.kind}",
                        item_id=item.id,
                    )
                if item.id in ids_seen:
                    _raise_contract_error(
                        f"todayV2HorizonActions.{list_name}",
                        "duplicate-item-id",
                        item_id=item.id,
                    )
                ids_seen.add(item.id)
                normalized = _normalize_action_text(item.text)
                if normalized in normalized_texts:
                    _raise_contract_error(
                        f"todayV2HorizonActions.{list_name}",
                        "duplicate-normalized-action-text",
                        item_id=item.id,
                    )
                normalized_texts.add(normalized)
        return self


class TodayV2Horizon(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    id: IdStr
    horizon: TodayV2HorizonId
    tone: TodayV2HorizonTone
    eyebrow: LabelStr
    title: TitleStr
    summary: BodyStr
    plain_explanation: BodyStr
    timing: TodayV2HorizonTiming
    likely_spheres: list[TodayV2ProductSphereKey] = Field(min_length=1, max_length=3)
    manifestations: list[TodayV2Manifestation] = Field(min_length=1, max_length=3)
    strength: TodayV2GroundedItem | None = None
    risk: TodayV2GroundedItem | None = None
    actions: TodayV2HorizonActions
    technique_explanations: list[TodayV2TechniqueExplanation] = Field(min_length=1)
    activation_ids: list[IdStr] = Field(min_length=1)

    @field_validator("eyebrow", "title", "summary", "plain_explanation", mode="after")
    @classmethod
    def validate_non_blank_text_fields(cls, value: str, info: Any) -> str:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_non_blank_text_fields
        # purpose: Reject blank eyebrow/title/summary/plain-explanation copy.
        # inputs: value - field string; info - Pydantic field metadata.
        # returns: the original non-blank value.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for blank copy.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_non_blank_text_fields
        return _ensure_non_empty_after_strip(value, f"todayV2Horizon.{info.field_name}")

    @field_validator("likely_spheres", "activation_ids", mode="after")
    @classmethod
    def validate_unique_scalar_lists(cls, values: list[str], info: Any) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_unique_scalar_lists
        # purpose: Enforce uniqueness for likely_spheres and activation_ids.
        # inputs: values - selected list; info - Pydantic field metadata.
        # returns: the same list unchanged when unique.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError on duplicates.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_unique_scalar_lists
        _ensure_unique(values, f"todayV2Horizon.{info.field_name}")
        return values

    @model_validator(mode="after")
    def validate_horizon(self) -> "TodayV2Horizon":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_horizon
        # purpose: Enforce per-horizon nested kind, sphere-subset, activation-subset, timing, and action-count invariants.
        # inputs: self - validated horizon model candidate.
        # returns: the same horizon model when nested contract rules pass.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError with structural path/id/reason on any horizon contract violation.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2Horizon.validate_horizon
        if self.strength is not None and self.strength.kind != "strength":
            _raise_contract_error("todayV2Horizon.strength", f"kind-mismatch:{self.strength.kind}", item_id=self.strength.id)
        if self.risk is not None and self.risk.kind != "risk":
            _raise_contract_error("todayV2Horizon.risk", f"kind-mismatch:{self.risk.kind}", item_id=self.risk.id)

        likely_spheres = set(self.likely_spheres)
        horizon_activation_ids = set(self.activation_ids)

        for manifestation in self.manifestations:
            if not set(manifestation.sphere_keys).issubset(likely_spheres):
                _raise_contract_error(
                    f"todayV2Horizon.manifestations[{manifestation.id}]",
                    "manifestation-spheres-outside-likely-spheres",
                    item_id=manifestation.id,
                )
            _validate_provenance_sphere_subset(
                manifestation.provenance,
                path=f"todayV2Horizon.manifestations[{manifestation.id}].provenance",
                item_id=manifestation.id,
                likely_spheres=likely_spheres,
            )

        if self.strength is not None:
            _validate_provenance_sphere_subset(
                self.strength.provenance,
                path="todayV2Horizon.strength.provenance",
                item_id=self.strength.id,
                likely_spheres=likely_spheres,
            )
        if self.risk is not None:
            _validate_provenance_sphere_subset(
                self.risk.provenance,
                path="todayV2Horizon.risk.provenance",
                item_id=self.risk.id,
                likely_spheres=likely_spheres,
            )
        for item in self.actions.do:
            _validate_provenance_sphere_subset(
                item.provenance,
                path=f"todayV2Horizon.actions.do[{item.id}].provenance",
                item_id=item.id,
                likely_spheres=likely_spheres,
            )
        for item in self.actions.avoid:
            _validate_provenance_sphere_subset(
                item.provenance,
                path=f"todayV2Horizon.actions.avoid[{item.id}].provenance",
                item_id=item.id,
                likely_spheres=likely_spheres,
            )

        for path, activation_id in _collect_provenance_activation_ids(self):
            if activation_id not in horizon_activation_ids:
                _raise_contract_error(path, "activation-id-outside-horizon", item_id=activation_id)

        if self.actions.valid_until != self.timing.active_until:
            _raise_contract_error(f"todayV2Horizon[{self.id}].actions.validUntil", "must-match-horizon-active-until", item_id=self.id)

        for explanation in self.technique_explanations:
            if not set(explanation.activation_ids).issubset(horizon_activation_ids):
                _raise_contract_error(
                    f"todayV2Horizon[{self.id}].techniqueExplanations",
                    "technique-activation-id-outside-horizon",
                    item_id=explanation.technique,
                )
            if explanation.timing is not None and explanation.timing.model_dump() != self.timing.model_dump():
                _raise_contract_error(
                    f"todayV2Horizon[{self.id}].techniqueExplanations",
                    "technique-timing-must-equal-horizon-timing",
                    item_id=explanation.technique,
                )

        if self.horizon in {"medium", "fast"} and (self.timing.exact_at is None or self.timing.peak_label is None):
            _raise_contract_error(f"todayV2Horizon[{self.id}].timing", "medium-fast-requires-peak", item_id=self.id)

        expected_counts = {
            "long": ((1, 2), (1, 2)),
            "medium": ((2, 3), (1, 3)),
            "fast": ((1, 1), (1, 2)),
        }[self.horizon]
        do_range, avoid_range = expected_counts
        if not (do_range[0] <= len(self.actions.do) <= do_range[1]):
            _raise_contract_error(f"todayV2Horizon[{self.id}].actions.do", "count-out-of-range", item_id=self.id)
        if not (avoid_range[0] <= len(self.actions.avoid) <= avoid_range[1]):
            _raise_contract_error(f"todayV2Horizon[{self.id}].actions.avoid", "count-out-of-range", item_id=self.id)
        return self


class TodayV2HorizonIntro(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    eyebrow: LabelStr
    headline: TitleStr
    body: BodyStr
    theme_key: IdStr
    activation_ids: list[IdStr] = Field(min_length=1)

    @field_validator("eyebrow", "headline", "body", "theme_key", mode="after")
    @classmethod
    def validate_non_blank_text_fields(cls, value: str, info: Any) -> str:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonIntro.validate_non_blank_text_fields
        # purpose: Reject blank intro eyebrow/headline/body/theme key.
        # inputs: value - field string; info - Pydantic field metadata.
        # returns: the original non-blank value.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError for blank text/id.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonIntro.validate_non_blank_text_fields
        return _ensure_non_empty_after_strip(value, f"todayV2HorizonIntro.{info.field_name}")

    @field_validator("activation_ids", mode="after")
    @classmethod
    def validate_activation_ids_unique(cls, values: list[str]) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonIntro.validate_activation_ids_unique
        # purpose: Enforce unique activation references in the intro.
        # inputs: values - activation id list.
        # returns: the same list unchanged when unique.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError on duplicate ids.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonIntro.validate_activation_ids_unique
        _ensure_unique(values, "todayV2HorizonIntro.activationIds")
        return values


class TodayV2HorizonsBlock(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    schema_version: Literal["today-horizons.v1"]
    guidance_mode: TodayV2GuidanceMode
    intro: TodayV2HorizonIntro
    items: list[TodayV2Horizon] = Field(min_length=3, max_length=3)
    warnings: list[LabelStr] = Field(default_factory=list)

    @field_validator("warnings", mode="after")
    @classmethod
    def validate_warnings(cls, values: list[str]) -> list[str]:
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonsBlock.validate_warnings
        # purpose: Enforce ordered unique non-blank warning strings.
        # inputs: values - warning list.
        # returns: the same list in original order when valid.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises structural ValueError on duplicate or blank warnings.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonsBlock.validate_warnings
        seen: set[str] = set()
        for index, value in enumerate(values):
            if value in seen:
                _raise_contract_error(
                    f"todayV2HorizonsBlock.warnings[{index}]",
                    "duplicate-warning",
                )
            seen.add(value)
        for value in values:
            _ensure_non_empty_after_strip(value, "todayV2HorizonsBlock.warnings")
        return values

    @model_validator(mode="after")
    def validate_block(self) -> "TodayV2HorizonsBlock":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonsBlock.validate_block
        # purpose: Enforce ordered horizon coverage, intro activation subset, and block-wide uniqueness for ids and normalized action text.
        # inputs: self - validated horizons block candidate.
        # returns: the same block when aggregate invariants hold.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError on ordering, subset, or uniqueness violations.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.TodayV2HorizonsBlock.validate_block
        ordered_horizons = [item.horizon for item in self.items]
        if ordered_horizons != ["long", "medium", "fast"]:
            _raise_contract_error("todayV2HorizonsBlock.items", "horizons-must-be-long-medium-fast")

        horizon_ids = [item.id for item in self.items]
        _ensure_unique(horizon_ids, "todayV2HorizonsBlock.items.ids")

        intro_activation_ids = set(self.intro.activation_ids)
        item_activation_ids = set().union(*(set(item.activation_ids) for item in self.items))
        if not intro_activation_ids.issubset(item_activation_ids):
            _raise_contract_error("todayV2HorizonsBlock.intro.activationIds", "intro-ids-outside-item-union")

        entity_ids: set[str] = set()
        normalized_action_texts: set[str] = set()
        for item in self.items:
            for grounded in [candidate for candidate in [item.strength, item.risk] if candidate is not None] + item.actions.do + item.actions.avoid:
                if grounded.id in entity_ids:
                    _raise_contract_error("todayV2HorizonsBlock.items", "duplicate-grounded-id", item_id=grounded.id)
                entity_ids.add(grounded.id)
                normalized = _normalize_action_text(grounded.text) if grounded.kind in {"action", "avoid"} else None
                if normalized is not None:
                    if normalized in normalized_action_texts:
                        _raise_contract_error("todayV2HorizonsBlock.items", "duplicate-normalized-action-text", item_id=grounded.id)
                    normalized_action_texts.add(normalized)
            for manifestation in item.manifestations:
                if manifestation.id in entity_ids:
                    _raise_contract_error("todayV2HorizonsBlock.items", "duplicate-manifestation-id", item_id=manifestation.id)
                entity_ids.add(manifestation.id)
        return self
# END_BLOCK: HORIZON_WIRE_MODELS


# START_BLOCK: CROSS_REFERENCE_VALIDATION
def validate_horizons_against_evidence(
    horizons: TodayV2HorizonsBlock,
    activation_evidence: Sequence["ActivationEvidence"] | Sequence[Any],
) -> TodayV2HorizonsBlock:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.validate_horizons_against_evidence
    # purpose: Validate a TodayV2 horizons block against TodayV2 activation evidence references and aggregate timing policy.
    # inputs: horizons - validated horizon block; activation_evidence - validated TodayV2 activation evidence collection.
    # returns: the original horizons block when every cross-reference and timing rule passes.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError with structural path/id/reason.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-TODAY-HORIZONS.validate_horizons_against_evidence
    evidence_by_id: dict[str, Any] = {}
    for item in activation_evidence:
        item_id = _evidence_attr(item, "id")
        if not isinstance(item_id, str) or not item_id:
            _raise_contract_error("activationEvidence", "missing-id")
        evidence_by_id[item_id] = item

    for activation_id in horizons.intro.activation_ids:
        if activation_id not in evidence_by_id:
            _raise_contract_error("todayV2HorizonsBlock.intro.activationIds", "unknown-activation-id", item_id=activation_id)

    for horizon in horizons.items:
        for activation_id in horizon.activation_ids:
            if activation_id not in evidence_by_id:
                _raise_contract_error(f"todayV2HorizonsBlock.items[{horizon.id}].activationIds", "unknown-activation-id", item_id=activation_id)

        for path, activation_id in _collect_provenance_activation_ids(horizon):
            if activation_id not in evidence_by_id:
                _raise_contract_error(path, "unknown-activation-id", item_id=activation_id)

        for explanation in horizon.technique_explanations:
            referenced_items: list[Any] = []
            for activation_id in explanation.activation_ids:
                if activation_id not in evidence_by_id:
                    _raise_contract_error(
                        f"todayV2HorizonsBlock.items[{horizon.id}].techniqueExplanations",
                        "unknown-activation-id",
                        item_id=activation_id,
                    )
                if activation_id not in horizon.activation_ids:
                    _raise_contract_error(
                        f"todayV2HorizonsBlock.items[{horizon.id}].techniqueExplanations",
                        "technique-activation-id-outside-horizon",
                        item_id=activation_id,
                    )
                referenced_items.append(evidence_by_id[activation_id])
            if not any(_evidence_attr(item, "technique") == explanation.technique for item in referenced_items):
                _raise_contract_error(
                    f"todayV2HorizonsBlock.items[{horizon.id}].techniqueExplanations",
                    "technique-mismatch-with-evidence",
                    item_id=explanation.technique,
                )
            _validate_technique_explanation_timing_support(
                horizon_id=horizon.id,
                explanation=explanation,
                referenced_items=referenced_items,
            )

        referenced_evidence = [evidence_by_id[activation_id] for activation_id in horizon.activation_ids]
        timed_support = []
        active_from_candidates: list[tuple[date | datetime, str]] = []
        active_until_candidates: list[tuple[date | datetime, str]] = []
        exact_candidates: list[str] = []

        for evidence in referenced_evidence:
            active_from = _evidence_attr(evidence, "active_from")
            active_until = _evidence_attr(evidence, "active_until")
            exact_at = _evidence_attr(evidence, "exact_at")
            non_null_values = [("activeFrom", active_from), ("activeUntil", active_until), ("exactAt", exact_at)]
            if all(value is None for _, value in non_null_values):
                continue
            timed_support.append(evidence)
            for field_name, value in non_null_values:
                if value is None:
                    continue
                parsed = _parse_timing_value(
                    value,
                    horizon.timing.precision,
                    f"todayV2HorizonsBlock.items[{horizon.id}].evidence[{_evidence_attr(evidence, 'id')}].{field_name}",
                    item_id=_evidence_attr(evidence, "id"),
                )
                if field_name == "activeFrom":
                    active_from_candidates.append((parsed, value))
                elif field_name == "activeUntil":
                    active_until_candidates.append((parsed, value))
                else:
                    exact_candidates.append(value)

        if not timed_support:
            _raise_contract_error(f"todayV2HorizonsBlock.items[{horizon.id}].timing", "only-untimed-evidence")
        if not active_from_candidates or not active_until_candidates:
            _raise_contract_error(f"todayV2HorizonsBlock.items[{horizon.id}].timing", "missing-aggregate-boundaries")

        expected_active_from = min(active_from_candidates, key=lambda item: item[0])[1]
        expected_active_until = max(active_until_candidates, key=lambda item: item[0])[1]
        if horizon.timing.active_from != expected_active_from:
            _raise_contract_error(f"todayV2HorizonsBlock.items[{horizon.id}].timing.activeFrom", "aggregate-min-mismatch", item_id=horizon.id)
        if horizon.timing.active_until != expected_active_until:
            _raise_contract_error(f"todayV2HorizonsBlock.items[{horizon.id}].timing.activeUntil", "aggregate-max-mismatch", item_id=horizon.id)
        if horizon.timing.exact_at is not None and horizon.timing.exact_at not in exact_candidates:
            _raise_contract_error(f"todayV2HorizonsBlock.items[{horizon.id}].timing.exactAt", "not-backed-by-evidence", item_id=horizon.id)

    return horizons
# END_BLOCK: CROSS_REFERENCE_VALIDATION


__all__ = [
    "TodayV2HorizonId",
    "TodayV2HorizonTone",
    "TodayV2TimingState",
    "TodayV2TimingPrecision",
    "TodayV2ClaimKind",
    "TodayV2GuidanceMode",
    "TodayV2ProductSphereKey",
    "TodayV2Provenance",
    "TodayV2GroundedItem",
    "TodayV2HorizonTiming",
    "TodayV2TechniqueExplanation",
    "TodayV2Manifestation",
    "TodayV2HorizonActions",
    "TodayV2Horizon",
    "TodayV2HorizonIntro",
    "TodayV2HorizonsBlock",
    "validate_horizons_against_evidence",
]
