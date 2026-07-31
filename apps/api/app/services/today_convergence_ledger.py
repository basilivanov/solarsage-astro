# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_LEDGER — deterministic canonical ledger.
# ROLE: Deduplicates normalized physical units, aggregates audit evidence, and applies semantic DayDelta upgrades.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-LEDGER
# purpose: Build a pure immutable ledger between raw physical facts and later grouping.
# owns:
#   - apps/api/app/services/today_convergence_ledger.py
# inputs: A sequence of RawPhysicalFact values, optional frozen canon, and semantic DayDelta keys.
# outputs: CanonicalLedger with unique sorted CanonicalUnit records and immutable audit counts.
# dependencies: today_convergence_canon and today_convergence_units only; no DB, HTTP, logger, or adapter.
# side_effects: none; this module is deterministic and does not write or emit logs.
# emitted_logs: none.
# invariants: canonical IDs are unique; producer/provenance do not alter identity; malformed rows fail closed per row.
# failure_policy: data-row errors aggregate into audit; programming/configuration misuse raises TodayConvergenceLedgerError; canon errors propagate.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-LEDGER

# START_MODULE_MAP: M-TODAY-CONVERGENCE-LEDGER
# public_entrypoints:
#   - CanonicalLedgerAudit
#   - CanonicalLedger
#   - TodayConvergenceLedgerError
#   - build_canonical_ledger
# semantic_blocks:
#   - INPUT_VALIDATION: validate pure API collections and producer domain.
#   - DEDUPLICATION: select deterministic enrichment winners and union provenance.
#   - DELTA_UPGRADE: apply exact semantic-key triggers after deduplication.
#   - AUDIT: materialize sorted immutable row and producer counters.
#   - LEDGER_BUILD: orchestrate normalization, deduplication, upgrade, and audit.
# owned_tests:
#   - apps/api/tests/test_today_convergence_ledger.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-LEDGER

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from datetime import date, datetime
from enum import Enum
from typing import Any

from app.services.today_convergence_canon import (
    TodayConvergenceCanon,
    TodayConvergenceCanonError,
    load_today_convergence_canon,
)
from app.services.today_convergence_units import (
    CanonicalUnit,
    ExclusionReason,
    RawPhysicalFact,
    build_canonical_unit,
)


_PRODUCER_PRECEDENCE = ("activation", "day_signal")
_PUBLIC_DELTA_ROLES = frozenset({"supporting", "unrelated"})


class TodayConvergenceLedgerError(ValueError):
    """Programming/configuration misuse of the pure ledger API."""


@dataclass(frozen=True)
class CanonicalLedgerAudit:
    """Immutable deterministic counters for accepted, excluded, and duplicate rows."""

    raw_fact_count: int
    accepted_fact_count: int
    canonical_unit_count: int
    duplicate_fact_count: int
    duplicate_conflict_count: int
    delta_upgraded_count: int
    unmatched_delta_trigger_count: int
    producer_counts: tuple[tuple[str, int], ...]
    excluded_by_reason: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class CanonicalLedger:
    """Immutable sorted canonical units plus their audit-only accounting."""

    units: tuple[CanonicalUnit, ...]
    audit: CanonicalLedgerAudit


@dataclass(frozen=True)
class _LedgerRow:
    unit: CanonicalUnit
    producer: str


# START_BLOCK: INPUT_VALIDATION
def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TodayConvergenceLedgerError(f"{name} must be a sequence")
    return value


def _trigger_keys(value: Sequence[str] | None) -> frozenset[str]:
    if value is None:
        return frozenset()
    sequence = _require_sequence(value, "delta_trigger_semantic_keys")
    if any(not isinstance(item, str) for item in sequence):
        raise TodayConvergenceLedgerError("delta_trigger_semantic_keys must contain only strings")
    return frozenset(sequence)


def _producer(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, "empty_producer"
    if not isinstance(value, str):
        return None, "unknown_producer"
    normalized = value.strip().lower()
    if not normalized:
        return None, "empty_producer"
    if normalized not in _PRODUCER_PRECEDENCE:
        return None, "unknown_producer"
    return normalized, None


# END_BLOCK: INPUT_VALIDATION


# START_BLOCK: DEDUPLICATION
def _reason_token(reason: ExclusionReason | str | None) -> str:
    if isinstance(reason, Enum):
        return str(reason.value)
    if isinstance(reason, str) and reason:
        return reason
    return "malformed_raw_fact"


def _stable_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_stable_value(item) for item in value]
    if isinstance(value, list):
        return [_stable_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _stable_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    return value


def _enrichment_key(unit: CanonicalUnit) -> str:
    excluded = {"canonical_event_id", "semantic_key", "provenance_ids"}
    payload = {
        field.name: _stable_value(getattr(unit, field.name))
        for field in fields(unit)
        if field.name not in excluded
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _provenance_key(unit: CanonicalUnit) -> str:
    return json.dumps(unit.provenance_ids, ensure_ascii=False, separators=(",", ":"))


def _producer_rank(canon: TodayConvergenceCanon, producer: str) -> int:
    configured = getattr(canon, "producer_precedence", _PRODUCER_PRECEDENCE)
    try:
        precedence = tuple(configured)
    except TypeError as exc:  # pragma: no cover - defensive programming misuse
        raise TodayConvergenceLedgerError("canon producer precedence must be a sequence") from exc
    if precedence != _PRODUCER_PRECEDENCE:
        raise TodayConvergenceLedgerError("canon producer precedence is not the frozen activation/day_signal order")
    return precedence.index(producer)


def _winner(rows: Sequence[_LedgerRow], canon: TodayConvergenceCanon) -> tuple[_LedgerRow, int]:
    enrichment_keys = {_enrichment_key(row.unit) for row in rows}
    conflicts = max(0, len(enrichment_keys) - 1)
    selected = min(
        rows,
        key=lambda row: (
            _producer_rank(canon, row.producer),
            _enrichment_key(row.unit),
            _provenance_key(row.unit),
        ),
    )
    return selected, conflicts


# END_BLOCK: DEDUPLICATION


# START_BLOCK: DELTA_UPGRADE
def _is_delta_upgrade_candidate(unit: CanonicalUnit, trigger_keys: frozenset[str]) -> bool:
    return (
        unit.semantic_key in trigger_keys
        and unit.temporal_role in _PUBLIC_DELTA_ROLES
        and unit.exclusion_reason is None
    )


# END_BLOCK: DELTA_UPGRADE


# START_BLOCK: AUDIT
def _sorted_counts(counts: dict[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((key, value) for key, value in counts.items()))


# END_BLOCK: AUDIT


# START_BLOCK: LEDGER_BUILD
def build_canonical_ledger(
    raw_facts: Sequence[RawPhysicalFact],
    canon: TodayConvergenceCanon | None = None,
    delta_trigger_semantic_keys: Sequence[str] | None = None,
) -> CanonicalLedger:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-LEDGER.build_canonical_ledger
    # purpose: Normalize, deduplicate, audit, and semantically upgrade raw physical facts.
    # inputs: raw_facts — sequence whose valid items are RawPhysicalFact; canon — frozen canon or loaded default; delta_trigger_semantic_keys — exact semantic keys only.
    # returns: CanonicalLedger — unique units sorted by canonical_event_id plus immutable audit.
    # side_effects: reads frozen canon when omitted; no writes, network, database, or logs.
    # emitted_logs: none.
    # error_behavior: row failures are counted and skipped; invalid API collections raise TodayConvergenceLedgerError; canon errors propagate.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-LEDGER.build_canonical_ledger
    raw_sequence = _require_sequence(raw_facts, "raw_facts")
    resolved_canon = load_today_convergence_canon() if canon is None else canon
    if not isinstance(resolved_canon, TodayConvergenceCanon):
        raise TodayConvergenceLedgerError("canon must be TodayConvergenceCanon")
    trigger_keys = _trigger_keys(delta_trigger_semantic_keys)

    producer_counts: dict[str, int] = {}
    excluded_by_reason: dict[str, int] = {}
    grouped: dict[str, list[_LedgerRow]] = {}
    accepted_fact_count = 0

    def exclude(reason: ExclusionReason | str | None) -> None:
        token = _reason_token(reason)
        excluded_by_reason[token] = excluded_by_reason.get(token, 0) + 1

    for item in raw_sequence:
        if not isinstance(item, RawPhysicalFact):
            exclude("non_raw_fact")
            continue
        producer, producer_reason = _producer(item.producer)
        if producer_reason is not None or producer is None:
            exclude(producer_reason)
            continue
        producer_counts[producer] = producer_counts.get(producer, 0) + 1
        try:
            result = build_canonical_unit(item, resolved_canon)
        except TodayConvergenceCanonError:
            raise
        except Exception:
            exclude("malformed_raw_fact")
            continue
        if not result.accepted or result.unit is None:
            exclude(result.exclusion_reason)
            continue
        accepted_fact_count += 1
        if result.exclusion_reason is not None:
            exclude(result.exclusion_reason)
        grouped.setdefault(result.unit.canonical_event_id, []).append(_LedgerRow(result.unit, producer))

    duplicate_fact_count = sum(max(0, len(rows) - 1) for rows in grouped.values())
    duplicate_conflict_count = 0
    units: list[CanonicalUnit] = []
    for canonical_event_id in sorted(grouped):
        rows = grouped[canonical_event_id]
        selected, conflicts = _winner(rows, resolved_canon)
        duplicate_conflict_count += conflicts
        provenance = tuple(sorted({item for row in rows for item in row.unit.provenance_ids}))
        units.append(replace(selected.unit, provenance_ids=provenance))

    unmatched_delta_trigger_count = len(trigger_keys - {unit.semantic_key for unit in units})
    delta_upgraded_count = 0
    upgraded_units: list[CanonicalUnit] = []
    for unit in units:
        if _is_delta_upgrade_candidate(unit, trigger_keys):
            upgraded_units.append(replace(unit, temporal_role="anchor_today"))
            delta_upgraded_count += 1
        else:
            upgraded_units.append(unit)

    audit = CanonicalLedgerAudit(
        raw_fact_count=len(raw_sequence),
        accepted_fact_count=accepted_fact_count,
        canonical_unit_count=len(upgraded_units),
        duplicate_fact_count=duplicate_fact_count,
        duplicate_conflict_count=duplicate_conflict_count,
        delta_upgraded_count=delta_upgraded_count,
        unmatched_delta_trigger_count=unmatched_delta_trigger_count,
        producer_counts=_sorted_counts(producer_counts),
        excluded_by_reason=_sorted_counts(excluded_by_reason),
    )
    return CanonicalLedger(units=tuple(upgraded_units), audit=audit)


# END_BLOCK: LEDGER_BUILD


__all__ = [
    "CanonicalLedgerAudit",
    "CanonicalLedger",
    "TodayConvergenceLedgerError",
    "build_canonical_ledger",
]
