# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_GROUPS — deterministic direct-star groups.
# ROLE: Builds immutable physical groups, C1 hero evidence, independence, and one group-level sphere/facet projection.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-GROUPS
# purpose: Group accepted canonical ledger units by direct target/theme relation without transitive bridges.
# owns:
#   - apps/api/app/services/today_convergence_groups.py
# inputs: CanonicalLedger and optional validated TodayConvergenceCanon.
# outputs: CanonicalGroupingResult with immutable groups and deterministic audit.
# dependencies: today_convergence_canon, today_convergence_ledger, today_convergence_units, and Python standard library only.
# side_effects: none; this module is pure and emits no runtime logs.
# emitted_logs: none.
# invariants: public pool is evidence-eligible/non-background; group identity uses only canonical member IDs; sphere/facet are group-level.
# failure_policy: malformed API input and ledger invariant violations raise TodayConvergenceGroupingError; data already rejected by ledger stays out of groups.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-GROUPS

# START_MODULE_MAP: M-TODAY-CONVERGENCE-GROUPS
# public_entrypoints:
#   - CanonicalConvergenceGroup
#   - CanonicalGroupingAudit
#   - CanonicalGroupingResult
#   - TodayConvergenceGroupingError
#   - build_canonical_groups
# semantic_blocks:
#   - INPUT_VALIDATION: accept only immutable validated ledger/canon records.
#   - DIRECT_STARS: seed anchors and link only direct target/theme neighbors.
#   - INDEPENDENCE: distinct driver validity and deterministic selected anchor.
#   - HERO_C1: rare anchor plus direct independent confirmation.
#   - SPHERE_PROJECTION: one deterministic group-level sphere/facet resolver call.
#   - AUDIT: immutable deterministic counters and sorted output.
# owned_tests:
#   - apps/api/tests/test_today_convergence_groups.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-GROUPS

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, Sequence

from app.services.today_convergence_canon import (
    TodayConvergenceCanon,
    load_today_convergence_canon,
    resolve_product_sphere,
)
from app.services.today_convergence_ledger import CanonicalLedger
from app.services.today_convergence_units import CanonicalUnit


class TodayConvergenceGroupingError(ValueError):
    """Programming misuse or violation of a previously guaranteed ledger invariant."""


@dataclass(frozen=True)
class CanonicalConvergenceGroup:
    """Immutable direct-star group with optional C1 hero pair and one projection."""

    group_id: str
    anchor_unit_id: str
    member_units: tuple[CanonicalUnit, ...]
    independent_driver_keys: tuple[str, ...]
    hero_anchor_id: str | None
    hero_confirmation_id: str | None
    hero_eligible: bool
    evidence_level: Literal["high", "medium"]
    sphere: str
    facet: str | None

    @property
    def selected_anchor_id(self) -> str:
        return self.anchor_unit_id

    @property
    def members(self) -> tuple[CanonicalUnit, ...]:
        return self.member_units


@dataclass(frozen=True)
class CanonicalGroupingAudit:
    """Immutable counters for public-pool filtering, star candidates, and groups."""

    ledger_unit_count: int
    public_evidence_pool_count: int
    today_anchor_count: int
    candidate_star_count: int
    duplicate_star_count: int
    group_count: int
    hero_count: int
    medium_count: int
    background_exclusion_count: int
    ineligible_exclusion_count: int
    insufficient_independence_count: int
    group_without_sphere_count: int

    @property
    def background_exclusions(self) -> int:
        return self.background_exclusion_count

    @property
    def ineligible_exclusions(self) -> int:
        return self.ineligible_exclusion_count


@dataclass(frozen=True)
class CanonicalGroupingResult:
    """Immutable sorted direct-star groups and their audit."""

    groups: tuple[CanonicalConvergenceGroup, ...]
    audit: CanonicalGroupingAudit


def _validate_inputs(ledger: CanonicalLedger, canon: TodayConvergenceCanon) -> tuple[CanonicalUnit, ...]:
    if not isinstance(ledger, CanonicalLedger):
        raise TodayConvergenceGroupingError("ledger must be CanonicalLedger")
    if not isinstance(canon, TodayConvergenceCanon):
        raise TodayConvergenceGroupingError("canon must be TodayConvergenceCanon")
    if not isinstance(ledger.units, tuple):
        raise TodayConvergenceGroupingError("ledger units must be an immutable tuple")
    units = ledger.units
    if any(not isinstance(unit, CanonicalUnit) for unit in units):
        raise TodayConvergenceGroupingError("ledger contains non-CanonicalUnit")
    ids = [unit.canonical_event_id for unit in units]
    if any(not isinstance(unit_id, str) or not unit_id for unit_id in ids):
        raise TodayConvergenceGroupingError("ledger contains invalid canonical_event_id")
    if len(ids) != len(set(ids)):
        raise TodayConvergenceGroupingError("duplicate canonical_event_id in ledger")
    return units


# START_BLOCK: DIRECT_STARS
def _directly_related(left: CanonicalUnit, right: CanonicalUnit) -> bool:
    same_target = bool(left.target_key and right.target_key and left.target_key == right.target_key)
    shared_theme = bool(set(left.theme_keys).intersection(right.theme_keys))
    return same_target or shared_theme


def _public_pool(units: Sequence[CanonicalUnit]) -> tuple[tuple[CanonicalUnit, ...], int, int]:
    pool: list[CanonicalUnit] = []
    background_exclusions = 0
    ineligible_exclusions = 0
    for unit in units:
        if unit.temporal_role == "background":
            background_exclusions += 1
        elif not unit.evidence_eligible or unit.exclusion_reason is not None:
            ineligible_exclusions += 1
        else:
            pool.append(unit)
    return tuple(sorted(pool, key=lambda unit: unit.canonical_event_id)), background_exclusions, ineligible_exclusions


def _star_candidates(
    pool: Sequence[CanonicalUnit],
) -> tuple[tuple[tuple[tuple[str, ...], tuple[CanonicalUnit, ...]], ...], int, int]:
    anchors = [unit for unit in pool if unit.temporal_role == "anchor_today"]
    stars: dict[tuple[str, ...], tuple[CanonicalUnit, ...]] = {}
    for anchor in sorted(anchors, key=lambda unit: unit.canonical_event_id):
        members = tuple(
            sorted(
                (unit for unit in pool if unit.canonical_event_id == anchor.canonical_event_id or _directly_related(anchor, unit)),
                key=lambda unit: unit.canonical_event_id,
            )
        )
        key = tuple(unit.canonical_event_id for unit in members)
        stars.setdefault(key, members)
    return tuple(sorted(stars.items())), len(anchors), len(anchors) - len(stars)


# END_BLOCK: DIRECT_STARS


# START_BLOCK: INDEPENDENCE
def _driver_keys(members: Sequence[CanonicalUnit]) -> tuple[str, ...]:
    return tuple(sorted({unit.driver_key.strip() for unit in members if isinstance(unit.driver_key, str) and unit.driver_key.strip()}))


def _anchor_sort_key(unit: CanonicalUnit) -> tuple[float, float, str]:
    return (-unit.strength, -unit.target_salience, unit.canonical_event_id)


def _select_anchor(members: Sequence[CanonicalUnit]) -> CanonicalUnit:
    anchors = [unit for unit in members if unit.temporal_role == "anchor_today"]
    if not anchors:  # pragma: no cover - guarded by star construction
        raise TodayConvergenceGroupingError("star has no anchor_today unit")
    return min(anchors, key=_anchor_sort_key)


# END_BLOCK: INDEPENDENCE


# START_BLOCK: HERO_C1
def _hero_pair(
    members: Sequence[CanonicalUnit],
    canon: TodayConvergenceCanon,
) -> tuple[CanonicalUnit | None, CanonicalUnit | None]:
    rare_anchors = sorted(
        (
            unit
            for unit in members
            if unit.temporal_role == "anchor_today"
            and unit.rare_anchor_eligible
            and unit.target_type in canon.hero_target_types
        ),
        key=_anchor_sort_key,
    )
    for rare in rare_anchors:
        if not rare.driver_key.strip():
            continue
        confirmations = sorted(
            (
                unit
                for unit in members
                if unit.canonical_event_id != rare.canonical_event_id
                and unit.temporal_role != "background"
                and unit.hero_confirmation_eligible
                and unit.driver_key.strip()
                and unit.driver_key != rare.driver_key
                and _directly_related(rare, unit)
            ),
            key=_anchor_sort_key,
        )
        if confirmations:
            return rare, confirmations[0]
    return None, None


# END_BLOCK: HERO_C1


# START_BLOCK: SPHERE_PROJECTION
def _group_house(members: Sequence[CanonicalUnit]) -> int | None:
    houses = {unit.house for unit in members if unit.house is not None}
    return next(iter(houses)) if len(houses) == 1 else None


def _project_sphere_facet(
    members: Sequence[CanonicalUnit],
    canon: TodayConvergenceCanon,
) -> tuple[str, str | None] | None:
    technical_spheres = tuple(sorted({
        technical_sphere
        for member in members
        for technical_sphere in member.technical_spheres
    }))
    theme_keys = tuple(sorted({
        theme_key
        for member in members
        for theme_key in member.theme_keys
    }))
    return resolve_product_sphere(
        canon,
        house=_group_house(members),
        technical_spheres=technical_spheres,
        theme_keys=theme_keys,
    )


# END_BLOCK: SPHERE_PROJECTION


# START_BLOCK: AUDIT
def _group_id(member_ids: Sequence[str]) -> str:
    payload = {"identity_version": "cvg_v1", "member_ids": sorted(set(member_ids))}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "cvg_v1_" + hashlib.sha256(encoded).hexdigest()[:32]


# END_BLOCK: AUDIT


# START_BLOCK: GROUP_BUILD
def build_canonical_groups(
    ledger: CanonicalLedger,
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalGroupingResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-GROUPS.build_canonical_groups
    # purpose: Build direct-star medium/hero groups from one canonical ledger.
    # inputs: ledger — immutable deduplicated CanonicalLedger; canon — validated frozen canon or strict-loader default.
    # returns: CanonicalGroupingResult — sorted immutable groups and audit; no tone, presentation, or adapter output.
    # side_effects: reads frozen canon when omitted; no writes, network, database, or logs.
    # emitted_logs: none.
    # error_behavior: malformed API input or duplicate ledger IDs raises TodayConvergenceGroupingError; excluded units remain audit-only.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-GROUPS.build_canonical_groups
    resolved_canon = load_today_convergence_canon() if canon is None else canon
    units = _validate_inputs(ledger, resolved_canon)
    pool, background_exclusions, ineligible_exclusions = _public_pool(units)
    stars, candidate_star_count, duplicate_star_count = _star_candidates(pool)
    groups: list[CanonicalConvergenceGroup] = []
    insufficient_independence_count = 0
    group_without_sphere_count = 0

    for _, members in stars:
        independent_driver_keys = _driver_keys(members)
        if len(independent_driver_keys) < 2:
            insufficient_independence_count += 1
            continue
        hero_anchor, hero_confirmation = _hero_pair(members, resolved_canon)
        anchor = hero_anchor or _select_anchor(members)
        sphere_facet = _project_sphere_facet(members, resolved_canon)
        if sphere_facet is None:
            group_without_sphere_count += 1
            continue
        sphere, facet = sphere_facet
        groups.append(
            CanonicalConvergenceGroup(
                group_id=_group_id([unit.canonical_event_id for unit in members]),
                anchor_unit_id=anchor.canonical_event_id,
                member_units=tuple(sorted(members, key=lambda unit: unit.canonical_event_id)),
                independent_driver_keys=independent_driver_keys,
                hero_anchor_id=hero_anchor.canonical_event_id if hero_anchor is not None else None,
                hero_confirmation_id=hero_confirmation.canonical_event_id if hero_confirmation is not None else None,
                hero_eligible=hero_anchor is not None and hero_confirmation is not None,
                evidence_level="high" if hero_anchor is not None and hero_confirmation is not None else "medium",
                sphere=sphere,
                facet=facet,
            )
        )

    ordered_groups = tuple(sorted(groups, key=lambda group: group.group_id))
    hero_count = sum(group.hero_eligible for group in ordered_groups)
    audit = CanonicalGroupingAudit(
        ledger_unit_count=len(units),
        public_evidence_pool_count=len(pool),
        today_anchor_count=sum(unit.temporal_role == "anchor_today" for unit in pool),
        candidate_star_count=candidate_star_count,
        duplicate_star_count=duplicate_star_count,
        group_count=len(ordered_groups),
        hero_count=hero_count,
        medium_count=len(ordered_groups) - hero_count,
        background_exclusion_count=background_exclusions,
        ineligible_exclusion_count=ineligible_exclusions,
        insufficient_independence_count=insufficient_independence_count,
        group_without_sphere_count=group_without_sphere_count,
    )
    return CanonicalGroupingResult(groups=ordered_groups, audit=audit)


# END_BLOCK: GROUP_BUILD


__all__ = [
    "CanonicalConvergenceGroup",
    "CanonicalGroupingAudit",
    "CanonicalGroupingResult",
    "TodayConvergenceGroupingError",
    "build_canonical_groups",
]
