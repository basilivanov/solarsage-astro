#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: TONE_POLICY_CANDIDATE — separate unit, group, and day tone.
# ROLE: Experimental W1 policy for polarity aggregation; never mutates factors.
# ############################################################################

# START_MODULE_CONTRACT: M-TONE-POLICY-CANDIDATE
# purpose: Turn classified evidence units/groups into auditable polarity layers.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/tone_policy_candidate.py
# inputs: classify_day_v2 result containing significant units, groups, and hero groups.
# outputs: unit polarity counts, group polarity records, day_tone, score/audit fields.
# dependencies: Python standard library only.
# side_effects: none; all returned records are new dictionaries.
# emitted_logs: none.
# invariants:
#   - background units never influence group/day tone;
#   - fast sources cannot create day tone alone;
#   - supporting/ongoing units are context for day tone, not fresh threats;
#   - independent counts use distinct driver keys, never raw duplicate rows.
# failure_policy: malformed/unknown polarity is mapped to steady and recorded.
# status: candidate; thresholds require replay calibration before canon freeze.
# END_MODULE_CONTRACT: M-TONE-POLICY-CANDIDATE

# START_MODULE_MAP: M-TONE-POLICY-CANDIDATE
# public_entrypoints:
#   - compute_tone_policy
#   - group_polarity
# semantic_blocks:
#   - CONSTANTS: candidate thresholds and source/role rules.
#   - NORMALIZATION: polarity, driver, and weight helpers.
#   - GROUP_TONE: independent weighted group balance.
#   - DAY_TONE: fresh-event gate and mixed/supportive/tense/steady decision.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_tone_policy_candidate.py
# END_MODULE_MAP: M-TONE-POLICY-CANDIDATE

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping


TONE_POLICY_VERSION = "tone-candidate-0.1"
FAST_SOURCES = frozenset({"MOON", "MERCURY", "VENUS"})
BACKGROUND_ROLE = "background"
FRESH_ROLE = "anchor_today"
ROLE_WEIGHT = {FRESH_ROLE: 1.0, "supporting": 0.5, BACKGROUND_ROLE: 0.0}

# These are explicit candidate constants, not a frequency target. They are
# intentionally kept here until a replay/ablation promotes them into canon.
HIGH_CONFIDENCE_STRENGTH = 0.75
MIN_INDEPENDENT_POLARITY_UNITS = 2
MIN_GROUP_SIDE_WEIGHT = 0.25
GROUP_MIX_MARGIN = 0.25

POLARITIES = frozenset({"supportive", "tense", "mixed", "steady"})


# START_BLOCK: NORMALIZATION
def _source(unit: Mapping[str, Any]) -> str:
    return str(unit.get("source_planet") or "").replace("TRANSIT_", "").upper()


def _technique_family(unit: Mapping[str, Any]) -> str:
    return str(unit.get("technique_family") or "").lower()


def driver_key(unit: Mapping[str, Any]) -> str:
    """Return the rule-B independent driver identity."""
    family = _technique_family(unit)
    if family in {
        "firdar",
        "profection",
        "solar_return",
        "lunar_return",
        "return",
        "progression",
        "progressive",
    }:
        return f"fam:{family}"
    return f"src:{_source(unit) or 'UNKNOWN'}"


def normalize_polarity(value: Any) -> str:
    value_text = str(value or "").strip().lower()
    if value_text in {"supportive", "tense", "mixed"}:
        return value_text
    return "steady"


def _is_fresh(unit: Mapping[str, Any], target_date: str | None) -> bool:
    """Treat a same-day exact peak as fresh even when DayDelta calls it supporting."""
    if str(unit.get("temporal_role") or "") == FRESH_ROLE:
        return True
    if not target_date:
        return False
    exact_at = str(unit.get("exact_at") or "")
    return bool(exact_at[:10] == str(target_date))


def unit_weight(
    unit: Mapping[str, Any],
    *,
    fresh_only: bool = False,
    target_date: str | None = None,
) -> float:
    """Return deterministic evidence weight for balance, never for eligibility."""
    role = str(unit.get("temporal_role") or "supporting")
    if role == BACKGROUND_ROLE or (fresh_only and not _is_fresh(unit, target_date)):
        return 0.0
    try:
        strength = max(0.0, min(1.0, float(unit.get("strength") or 0.0)))
    except (TypeError, ValueError):
        strength = 0.0
    return strength * ROLE_WEIGHT.get(role, 0.5)


def _dedupe_by_driver(
    units: Iterable[Mapping[str, Any]],
    *,
    fresh_only: bool,
    target_date: str | None = None,
) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for raw in units:
        if str(raw.get("temporal_role") or "") == BACKGROUND_ROLE:
            continue
        if fresh_only and not _is_fresh(raw, target_date):
            continue
        weight = unit_weight(raw, fresh_only=fresh_only, target_date=target_date)
        if weight <= 0.0:
            continue
        unit = dict(raw)
        unit["unit_polarity"] = normalize_polarity(unit.get("polarity"))
        unit["driver_key"] = driver_key(unit)
        unit["tone_weight"] = round(weight, 6)
        key = str(unit["driver_key"])
        if key not in best or weight > float(best[key].get("tone_weight") or 0.0):
            best[key] = unit
    return list(best.values())
# END_BLOCK: NORMALIZATION


# START_BLOCK: GROUP_TONE
def group_polarity(members: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-TONE-POLICY-CANDIDATE.group_polarity
    # purpose: Aggregate independent group members into a polarity and balance.
    # inputs: group members from classify_day_v2.
    # returns: polarity, weighted supportive/tense scores, and independent counts.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown/neutral units contribute to steady only.
    # END_FUNCTION_CONTRACT: F-M-TONE-POLICY-CANDIDATE.group_polarity
    units = _dedupe_by_driver(members, fresh_only=False)
    supportive = tense = 0.0
    counts: Counter[str] = Counter()
    for unit in units:
        polarity = str(unit["unit_polarity"])
        weight = float(unit["tone_weight"])
        counts[polarity] += 1
        if polarity == "supportive":
            supportive += weight
        elif polarity == "tense":
            tense += weight
        elif polarity == "mixed":
            supportive += weight * 0.5
            tense += weight * 0.5

    if supportive < MIN_GROUP_SIDE_WEIGHT and tense < MIN_GROUP_SIDE_WEIGHT:
        polarity = "steady"
    elif supportive >= MIN_GROUP_SIDE_WEIGHT and tense >= MIN_GROUP_SIDE_WEIGHT:
        total = supportive + tense
        polarity = (
            "mixed"
            if abs(supportive - tense) <= max(GROUP_MIX_MARGIN, total * GROUP_MIX_MARGIN)
            else ("supportive" if supportive > tense else "tense")
        )
    else:
        polarity = "supportive" if supportive > tense else "tense"

    return {
        "polarity": polarity,
        "supportive_score": round(supportive, 6),
        "tense_score": round(tense, 6),
        "independent_units": len(units),
        "unit_polarity_counts": dict(counts),
        "driver_keys": sorted(str(unit["driver_key"]) for unit in units),
    }
# END_BLOCK: GROUP_TONE


# START_BLOCK: DAY_TONE
def _hero_anchor_units(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for group in result.get("hero_groups", ()) or ():
        anchor = group.get("hero_anchor") or group.get("anchor")
        if isinstance(anchor, Mapping):
            anchors.append(dict(anchor))
    return anchors


def compute_tone_policy(
    result: Mapping[str, Any],
    *,
    target_date: str | None = None,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-TONE-POLICY-CANDIDATE.compute_tone_policy
    # purpose: Separate unit polarity, group polarity, and day_tone.
    # inputs: classify_day_v2 result with sig_units/groups/hero_groups/selected_public_units.
    # returns: auditable tone payload; no factor mutation.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: absent lists produce steady; malformed units are steady.
    # END_FUNCTION_CONTRACT: F-M-TONE-POLICY-CANDIDATE.compute_tone_policy
    significant = [
        dict(unit)
        for unit in (result.get("sig_units", ()) or ())
        if str(unit.get("temporal_role") or "") != BACKGROUND_ROLE
    ]
    selected = [
        dict(unit)
        for unit in (result.get("selected_public_units", ()) or ())
        if str(unit.get("temporal_role") or "") != BACKGROUND_ROLE
    ]
    unit_counts = Counter(normalize_polarity(unit.get("polarity")) for unit in selected)
    context_counts = Counter(
        normalize_polarity(unit.get("polarity"))
        for unit in significant
        if not _is_fresh(unit, target_date)
    )

    group_records: list[dict[str, Any]] = []
    for group in result.get("groups", ()) or ():
        balance = group_polarity(group.get("members", ()))
        anchor = group.get("hero_anchor") or group.get("anchor") or {}
        group_records.append(
            {
                "polarity": balance["polarity"],
                "is_hero": bool(group.get("hero")),
                "anchor_key": anchor.get("semantic_key"),
                **balance,
            }
        )

    # Only fresh, non-fast units can create a general day tone. Ongoing
    # transits remain visible in group/context details but do not re-trigger
    # a threat every day. Distinct drivers prevent duplicate rows counting twice.
    fresh_units = _dedupe_by_driver(
        significant,
        fresh_only=True,
        target_date=target_date,
    )
    day_units = [unit for unit in fresh_units if _source(unit) not in FAST_SOURCES]
    fresh_supportive = [u for u in day_units if u["unit_polarity"] == "supportive"]
    fresh_tense = [u for u in day_units if u["unit_polarity"] == "tense"]
    fresh_mixed = [u for u in day_units if u["unit_polarity"] == "mixed"]
    anchors = _hero_anchor_units(result)
    high_conf_tense_anchor = any(
        normalize_polarity(anchor.get("polarity")) == "tense"
        and float(anchor.get("strength") or 0.0) >= HIGH_CONFIDENCE_STRENGTH
        for anchor in anchors
    )
    high_conf_supportive_anchor = any(
        normalize_polarity(anchor.get("polarity")) == "supportive"
        and float(anchor.get("strength") or 0.0) >= HIGH_CONFIDENCE_STRENGTH
        for anchor in anchors
    )
    tense_independent = len(fresh_tense)
    supportive_independent = len(fresh_supportive)
    # A mixed fresh unit contributes to both sides only when another
    # independent non-fast unit exists; it cannot create a tone alone.
    if fresh_mixed and day_units:
        tense_independent += int(len(day_units) > 1)
        supportive_independent += int(len(day_units) > 1)

    meaningful_tense = (
        high_conf_tense_anchor or tense_independent >= MIN_INDEPENDENT_POLARITY_UNITS
    )
    meaningful_supportive = (
        high_conf_supportive_anchor
        or supportive_independent >= MIN_INDEPENDENT_POLARITY_UNITS
    )
    # A fresh supportive + fresh tense pair is explicitly mixed, even when
    # the tense side is below the standalone two-driver tense threshold. This
    # prevents one difficult unit from turning a balanced day into "heavy".
    fresh_support_weight = sum(float(unit["tone_weight"]) for unit in fresh_supportive)
    fresh_tense_weight = sum(float(unit["tone_weight"]) for unit in fresh_tense)
    fresh_pair_is_mixed = (
        fresh_support_weight >= MIN_GROUP_SIDE_WEIGHT
        and fresh_tense_weight >= MIN_GROUP_SIDE_WEIGHT
    )
    if fresh_pair_is_mixed:
        day_tone = "mixed"
    elif meaningful_tense:
        day_tone = "tense"
    elif meaningful_supportive:
        day_tone = "supportive"
    else:
        day_tone = "steady"

    legacy_any_selected_tense = any(
        normalize_polarity(unit.get("polarity")) == "tense" for unit in selected
    )
    return {
        "tone_policy_version": TONE_POLICY_VERSION,
        "day_tone": day_tone,
        "legacy_any_selected_tense": legacy_any_selected_tense,
        "unit_polarity_counts": dict(unit_counts),
        "context_polarity_counts": dict(context_counts),
        "group_polarity_counts": dict(Counter(row["polarity"] for row in group_records)),
        "groups": group_records,
        "tone_scores": {
            "fresh_supportive_units": supportive_independent,
            "fresh_tense_units": tense_independent,
            "high_confidence_supportive_anchor": high_conf_supportive_anchor,
            "high_confidence_tense_anchor": high_conf_tense_anchor,
            "context_supportive_units": context_counts.get("supportive", 0),
            "context_tense_units": context_counts.get("tense", 0),
        },
        "tone_trigger_keys": sorted(
            str(unit.get("semantic_key"))
            for unit in day_units
            if unit.get("semantic_key")
        ),
    }
# END_BLOCK: DAY_TONE
