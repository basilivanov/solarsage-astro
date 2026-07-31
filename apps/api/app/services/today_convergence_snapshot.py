# ############################################################################
# AI_HEADER: MODULE_TODAY-CONVERGENCE-SNAPSHOT — pure deterministic snapshot document.
# ROLE: Converts one validated runtime calculation into privacy-safe,
#       content-addressed input/result records for future persistence.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT
# purpose: Build a pure deterministic W3 snapshot document between the accepted
#   runtime calculation and a future persistence transaction.
# owns:
#   - apps/api/app/services/today_convergence_snapshot.py
# inputs: direct profile, TodayConvergenceCalculationBuilt, and optional strict canon directory.
# outputs: frozen TodayConvergenceSnapshotDocument with profile/input/canon hashes,
#   normalized factor pack, and deterministic presentation/audit result.
# dependencies: today_convergence_canon, today_birth_time, runtime records, and
#   accepted immutable ledger/group/tone/selection records; standard library only otherwise.
# side_effects: reads frozen canon files; never writes, logs, calls HTTP/DB/LLM, or persists.
# emitted_logs: none.
# invariants: profile identity is mode-aware and privacy-safe; each CanonicalUnit
#   appears once in canonical_input_json; result references are ledger-owned and bounded.
# failure_policy: TodayConvergenceSnapshotError with stable prefixed reasons; no fallback.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT

# START_MODULE_MAP: M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT
# public_entrypoints:
#   - TodayConvergenceSnapshotDocument
#   - TodayConvergenceSnapshotError
#   - build_today_convergence_snapshot_document
# semantic_blocks:
#   - PROFILE_IDENTITY: strict mode-aware profile hash and resolution parity.
#   - CANONICAL_INPUT: canon fingerprint and normalized factor pack.
#   - DETERMINISTIC_RESULT: selected references and audit-only records.
#   - VALIDATION: typed reference, version, state, serialization, and privacy guards.
# owned_tests:
#   - apps/api/tests/test_today_convergence_snapshot.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from math import isfinite
from numbers import Real
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.today_birth_time import BirthTimeResolution, TodayBirthTimeError, resolve_profile_birth_time
from app.services.today_convergence_canon import (
    TodayConvergenceCanon,
    TodayConvergenceCanonError,
    compute_today_convergence_canon_hash,
    load_today_convergence_canon,
)
from app.services.today_convergence_groups import (
    CanonicalConvergenceGroup,
    CanonicalGroupingResult,
)
from app.services.today_convergence_ledger import CanonicalLedger
from app.services.today_convergence_pipeline import CanonicalPipelineBuilt
from app.services.today_convergence_runtime import TodayConvergenceCalculationBuilt
from app.services.today_convergence_selection import (
    CanonicalSelectedConvergence,
    CanonicalSelectedEvent,
    CanonicalSelectionResult,
)
from app.services.today_convergence_units import CanonicalUnit


class TodayConvergenceSnapshotError(ValueError):
    """Raised when a deterministic snapshot document cannot be trusted."""


@dataclass(frozen=True)
class TodayConvergenceSnapshotDocument:
    """Immutable deterministic snapshot document without persistence metadata."""

    profile_hash: str
    input_hash: str
    canon_hash: str
    formula_version: str
    calculation_version: str
    ephemeris_artifact_id: str
    birth_time_mode: str
    birth_time_range: dict[str, str]
    canonical_input_json: dict[str, object]
    deterministic_result_json: dict[str, object]


def _fail(reason: str) -> None:
    raise TodayConvergenceSnapshotError(f"today_convergence_snapshot:{reason}")


def _bounded_text(value: object, reason: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _fail(reason)
    return value


def _finite_coordinate(value: object, reason: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        _fail(reason)
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        _fail(reason)
    if not isfinite(number) or not minimum <= number <= maximum:
        _fail(reason)
    return 0.0 if number == 0.0 else number


def _safe_json_value(value: object) -> object:
    if isinstance(value, Enum):
        return _safe_json_value(value.value)
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            _fail("non_finite_value")
        return 0.0 if value == 0.0 else value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return {field.name: _safe_json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                _fail("mapping_key")
            normalized[key] = _safe_json_value(item)
        return normalized
    if isinstance(value, (tuple, list)):
        return [_safe_json_value(item) for item in value]
    _fail("unknown_value")


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    try:
        return json_dumps(value).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise TodayConvergenceSnapshotError("today_convergence_snapshot:json_encoding") from exc


def json_dumps(value: object) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _profile_payload(profile: object, resolution: BirthTimeResolution) -> dict[str, object]:
    try:
        birthday = getattr(profile, "birthday")
        birth_tz = getattr(profile, "birth_tz")
        birth_lat = getattr(profile, "birth_lat")
        birth_lon = getattr(profile, "birth_lon")
    except AttributeError as exc:
        raise TodayConvergenceSnapshotError("today_convergence_snapshot:profile_identity") from exc
    if type(birthday) is not date:
        _fail("profile_identity")
    latitude = _finite_coordinate(birth_lat, "profile_identity", -90.0, 90.0)
    longitude = _finite_coordinate(birth_lon, "profile_identity", -180.0, 180.0)
    if not isinstance(birth_tz, str) or not birth_tz:
        _fail("profile_identity")
    try:
        ZoneInfo(birth_tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TodayConvergenceSnapshotError("today_convergence_snapshot:profile_identity") from exc
    return {
        "schema": "today-profile-identity.v1",
        "birthday": birthday.isoformat(),
        "birth_latitude": latitude,
        "birth_longitude": longitude,
        "birth_timezone": birth_tz,
        "house_system": "PLACIDUS",
        "birth_time": {
            "mode": resolution.mode,
            "bucket": resolution.bucket,
            "exact": resolution.birth_time,
            "range": {"start": resolution.range_start, "end": resolution.range_end},
        },
    }


def _resolution_for_profile(profile: object, canon: TodayConvergenceCanon) -> BirthTimeResolution:
    try:
        return resolve_profile_birth_time(profile, canon)
    except (AttributeError, TypeError, TodayBirthTimeError, ValueError) as exc:
        raise TodayConvergenceSnapshotError("today_convergence_snapshot:profile_resolution") from exc


def _unit_payload(unit: CanonicalUnit) -> dict[str, object]:
    if not isinstance(unit, CanonicalUnit):
        _fail("factor_unit_type")
    return _safe_json_value(unit)  # type: ignore[return-value]


def _validated_units(pipeline: CanonicalPipelineBuilt) -> tuple[CanonicalUnit, ...]:
    ledger = pipeline.ledger
    if not isinstance(ledger, CanonicalLedger) or not isinstance(ledger.units, tuple):
        _fail("ledger")
    if any(not isinstance(unit, CanonicalUnit) for unit in ledger.units):
        _fail("factor_unit_type")
    units = tuple(sorted(ledger.units, key=lambda unit: unit.canonical_event_id))
    ids = [unit.canonical_event_id for unit in units]
    if any(not isinstance(unit_id, str) or not unit_id for unit_id in ids) or len(ids) != len(set(ids)):
        _fail("factor_unit_id")
    return units


def _validate_event(event: CanonicalSelectedEvent, unit_by_id: dict[str, CanonicalUnit], canon: TodayConvergenceCanon) -> None:
    if not isinstance(event, CanonicalSelectedEvent):
        _fail("foreign_event_reference")
    unit_id = event.unit.canonical_event_id
    if unit_id not in unit_by_id or unit_by_id[unit_id] is not event.unit:
        _fail("foreign_event_reference")
    if event.product_sphere not in canon.canonical_spheres:
        _fail("unknown_selected_sphere")
    if event.polarity not in {"supportive", "tense", "mixed"}:
        _fail("selected_polarity")
    if event.evidence_level not in {"high", "medium"}:
        _fail("selected_evidence_level")


def _validate_selection(
    pipeline: CanonicalPipelineBuilt,
    units: tuple[CanonicalUnit, ...],
    canon: TodayConvergenceCanon,
) -> CanonicalSelectionResult:
    grouping = pipeline.grouping
    selection = pipeline.selection
    if not isinstance(grouping, CanonicalGroupingResult) or not isinstance(selection, CanonicalSelectionResult):
        _fail("selection_records")
    unit_by_id = {unit.canonical_event_id: unit for unit in units}
    if not isinstance(grouping.groups, tuple):
        _fail("grouping_caps")
    group_by_id: dict[str, CanonicalConvergenceGroup] = {}
    for group in grouping.groups:
        if not isinstance(group, CanonicalConvergenceGroup) or not group.group_id or group.group_id in group_by_id:
            _fail("foreign_group_reference")
        group_by_id[group.group_id] = group
        if not isinstance(group.member_units, tuple) or not group.member_units:
            _fail("foreign_group_reference")
        member_ids = [member.canonical_event_id for member in group.member_units]
        if any(unit_by_id.get(unit_id) is not member for unit_id, member in zip(member_ids, group.member_units, strict=True)):
            _fail("foreign_group_reference")
        if group.anchor_unit_id not in member_ids or group.primary_sphere not in canon.canonical_spheres:
            _fail("foreign_group_reference")
        if group.secondary_sphere is not None and group.secondary_sphere not in canon.canonical_spheres:
            _fail("unknown_selected_sphere")

    selected_ids = selection.selected_unit_ids
    if not isinstance(selected_ids, tuple) or len(selected_ids) != len(set(selected_ids)):
        _fail("selected_unit_ids")
    if any(unit_id not in unit_by_id for unit_id in selected_ids):
        _fail("foreign_event_reference")
    selected_spheres = selection.selected_spheres
    if (
        not isinstance(selected_spheres, tuple)
        or len(selected_spheres) != len(set(selected_spheres))
        or len(selected_spheres) > 3
        or any(sphere not in canon.canonical_spheres for sphere in selected_spheres)
    ):
        _fail("selected_spheres")

    expected_ids: set[str] = set()
    if selection.state == "convergence_today":
        if selection.main_event is not None or selection.impulses or len(selection.convergences) > 3:
            _fail("selection_caps")
        for selected in selection.convergences:
            if not isinstance(selected, CanonicalSelectedConvergence):
                _fail("foreign_group_reference")
            group = group_by_id.get(selected.group.group_id)
            if group is None or group is not selected.group:
                _fail("foreign_group_reference")
            if selected.polarity not in {"supportive", "tense", "mixed"}:
                _fail("selected_polarity")
            if group.evidence_level not in {"high", "medium"}:
                _fail("selected_evidence_level")
            if len(selected.evidence_event_ids) != 2 or len(set(selected.evidence_event_ids)) != 2:
                _fail("evidence_pair")
            member_ids = {member.canonical_event_id for member in group.member_units}
            if any(event_id not in member_ids for event_id in selected.evidence_event_ids):
                _fail("foreign_event_reference")
            expected_ids.update(selected.evidence_event_ids)
    elif selection.state == "quiet_day":
        if selection.convergences or len(selection.impulses) > 3:
            _fail("selection_caps")
        if selection.main_event is not None:
            _validate_event(selection.main_event, unit_by_id, canon)
            expected_ids.add(selection.main_event.unit.canonical_event_id)
        for event in selection.impulses:
            _validate_event(event, unit_by_id, canon)
            expected_ids.add(event.unit.canonical_event_id)
    else:
        _fail("selection_state")
    if set(selected_ids) != expected_ids:
        _fail("selected_unit_ids")
    return selection


def _factor_pack(
    profile: object,
    calculation: TodayConvergenceCalculationBuilt,
    resolution: BirthTimeResolution,
    canon_hash: str,
    units: tuple[CanonicalUnit, ...],
) -> dict[str, object]:
    return {
        "schema_version": "today-canonical-input.v1",
        "profile_hash": _profile_hash(profile, resolution),
        "target": {
            "date": calculation.target_date.isoformat(),
            "time": calculation.target_time,
            "timezone": calculation.target_timezone,
        },
        "birth_time": {
            "mode": resolution.mode,
            "bucket": resolution.bucket,
            "range": {"start": resolution.range_start, "end": resolution.range_end},
            "controls": list(resolution.control_times),
            "canonical_gap_hours": resolution.canonical_gap_hours,
            "capabilities": _safe_json_value(resolution.capabilities),
        },
        "versions": {
            "formula": calculation.pipeline.formula_version,
            "calculation": calculation.calculation_version,
            "activation_layer": calculation.activation_layer_version,
            "ephemeris_artifact": calculation.ephemeris_artifact_id,
            "canon_hash": canon_hash,
        },
        "factor_units": [_unit_payload(unit) for unit in units],
    }


def _profile_hash(profile: object, resolution: BirthTimeResolution) -> str:
    return sha256(_canonical_bytes(_profile_payload(profile, resolution))).hexdigest()


def _selected_event_payload(event: CanonicalSelectedEvent) -> dict[str, object]:
    return {
        "event_id": event.unit.canonical_event_id,
        "sphere": event.product_sphere,
        "polarity": event.polarity,
        "evidence_level": event.evidence_level,
    }


def _result_pack(
    calculation: TodayConvergenceCalculationBuilt,
    selection: CanonicalSelectionResult,
) -> dict[str, object]:
    selected_convergences = []
    for selected in selection.convergences:
        group = selected.group
        selected_convergences.append(
            {
                "group_id": group.group_id,
                "anchor_event_id": group.anchor_unit_id,
                "member_event_ids": [unit.canonical_event_id for unit in group.member_units],
                "evidence_event_ids": list(selected.evidence_event_ids),
                "primary_sphere": group.primary_sphere,
                "secondary_sphere": group.secondary_sphere,
                "polarity": selected.polarity,
                "evidence_level": group.evidence_level,
            }
        )
    return {
        "schema_version": "today-deterministic-result.v1",
        "state": calculation.pipeline.state,
        "day_tone": calculation.pipeline.tone.day_tone,
        "selected": {
            "convergences": selected_convergences,
            "main_event": None if selection.main_event is None else _selected_event_payload(selection.main_event),
            "impulses": [_selected_event_payload(event) for event in selection.impulses],
            "selected_unit_ids": list(selection.selected_unit_ids),
            "selected_spheres": list(selection.selected_spheres),
        },
        "audit": {
            "birth_time_facts": _safe_json_value(calculation.facts_audit),
            "ledger": _safe_json_value(calculation.pipeline.ledger.audit),
            "grouping": _safe_json_value(calculation.pipeline.grouping.audit),
            "tone": _safe_json_value(calculation.pipeline.tone.audit),
            "selection": _safe_json_value(selection.audit),
        },
    }


def build_today_convergence_snapshot_document(
    profile: object,
    calculation: TodayConvergenceCalculationBuilt,
    canon_dir: Path | None = None,
) -> TodayConvergenceSnapshotDocument:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT.build
    # purpose: Build one immutable, privacy-safe, content-addressed deterministic snapshot document.
    # inputs: direct profile, successful runtime calculation, and optional canon directory.
    # returns: TodayConvergenceSnapshotDocument without ID/timestamps/narrative/persistence.
    # side_effects: reads strict canon files only.
    # emitted_logs: none.
    # error_behavior: raises TodayConvergenceSnapshotError for foreign records,
    #   mismatch, malformed serialization, references, versions, or bounds.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT.build
    if not isinstance(calculation, TodayConvergenceCalculationBuilt):
        _fail("runtime_calculation")
    if not isinstance(calculation.pipeline, CanonicalPipelineBuilt):
        _fail("pipeline")
    try:
        canon = load_today_convergence_canon(canon_dir)
        canon_hash = compute_today_convergence_canon_hash(canon_dir)
    except TodayConvergenceCanonError as exc:
        raise TodayConvergenceSnapshotError("today_convergence_snapshot:canon") from exc
    if not isinstance(canon, TodayConvergenceCanon):
        _fail("canon")
    if not isinstance(calculation.birth_time, BirthTimeResolution):
        _fail("birth_resolution")
    profile_resolution = _resolution_for_profile(profile, canon)
    if profile_resolution != calculation.birth_time:
        _fail("profile_resolution")
    if calculation.pipeline.formula_version != canon.formula_version:
        _fail("formula_version")
    if calculation.state != calculation.pipeline.state or calculation.pipeline.state != calculation.pipeline.selection.state:
        _fail("state_disagreement")
    if type(calculation.target_date) is not date:
        _fail("target_date")
    target_timezone = _bounded_text(calculation.target_timezone, "target_timezone", 64)
    try:
        ZoneInfo(target_timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TodayConvergenceSnapshotError("today_convergence_snapshot:target_timezone") from exc
    _bounded_text(calculation.target_time, "target_time", 16)
    calculation_version = _bounded_text(calculation.calculation_version, "calculation_version", 64)
    _bounded_text(calculation.activation_layer_version, "activation_layer_version", 64)
    artifact_id = _bounded_text(calculation.ephemeris_artifact_id, "artifact_id", 128)
    units = _validated_units(calculation.pipeline)
    selection = _validate_selection(calculation.pipeline, units, canon)
    profile_hash = _profile_hash(profile, calculation.birth_time)
    canonical_input_json = _factor_pack(profile, calculation, calculation.birth_time, canon_hash, units)
    canonical_input_json["profile_hash"] = profile_hash
    canonical_input_bytes = _canonical_bytes(canonical_input_json)
    deterministic_result_json = _result_pack(calculation, selection)
    return TodayConvergenceSnapshotDocument(
        profile_hash=profile_hash,
        input_hash=sha256(canonical_input_bytes).hexdigest(),
        canon_hash=canon_hash,
        formula_version=calculation.pipeline.formula_version,
        calculation_version=calculation_version,
        ephemeris_artifact_id=artifact_id,
        birth_time_mode=calculation.birth_time.mode,
        birth_time_range={
            "start": calculation.birth_time.range_start,
            "end": calculation.birth_time.range_end,
        },
        canonical_input_json=canonical_input_json,
        deterministic_result_json=deterministic_result_json,
    )


__all__ = [
    "TodayConvergenceSnapshotDocument",
    "TodayConvergenceSnapshotError",
    "build_today_convergence_snapshot_document",
]
