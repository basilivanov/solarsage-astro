# ############################################################################
# AI_HEADER: MODULE_API_SCORING_V2_SERVICE — Scoring V2 pure service.
# ROLE: Computes V2 sphere scores with activation contributions, convergence,
#       anti-dominance, and transparent day status. Does not wire into
#       TodayService/CalendarService until W5.
# ############################################################################

# START_MODULE_CONTRACT: M-API-SCORING-V2-SERVICE
# purpose: Pure Scoring V2 calculation. Takes day_signals + optional
#          activation_layer, returns ScoringV2Result.
# owns:
#   - apps/api/app/services/scoring_v2_service.py
# inputs: day_signals (list[AstroSignal]), activation_layer (ActivationLayer|dict|None)
# outputs: ScoringV2Result
# dependencies: canons (scoring_v2.v1.yml, spheres.v1.yml, activation_rules.v1.yml)
# side_effects: none (pure computation)
# emitted_logs: none
# invariants:
#   - Base score reuses ScoringService._calculate_sphere_scores (V1 pre-cap formula)
#   - Every active activation-sphere match contributes
#   - Convergence deduplicates by technique family
#   - Anti-dominance caps at 65% of sum_all_positive_scores
# failure_policy: KeyError on missing canon keys; ValueError on invalid inputs
# END_MODULE_CONTRACT: M-API-SCORING-V2-SERVICE

# START_MODULE_MAP: M-API-SCORING-V2-SERVICE
# public_entrypoints:
#   - ScoringV2Service.score_day
# semantic_blocks:
#   - INIT: canon loading + strict helpers
#   - BASE_SCORE: V1 sphere score via ScoringService._calculate_sphere_scores
#   - ACTIVATION_CONTRIBUTION: map active activations to spheres
#   - CONVERGENCE: family-based bonus
#   - ANTI_DOMINANCE: cap logic
#   - DAY_STATUS: transparent breakdown with V1 aspect thresholds
# owned_tests:
#   - tests/test_scoring_v2_contracts.py
#   - tests/test_scoring_v2_convergence.py
#   - tests/test_scoring_v2_antidominance.py
#   - tests/test_scoring_v2_thresholds.py
#   - tests/test_scoring_v2_family_dedup.py
#   - tests/test_scoring_v2_breakdown_contract.py
#   - tests/test_basil_2026_07_08_v2_golden.py
# END_MODULE_MAP: M-API-SCORING-V2-SERVICE

from __future__ import annotations

import os
import pathlib
from typing import Any

import yaml

from app.core.versions import CALCULATION_VERSION, SCORING_V2_VERSION
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.schemas.normalization import AstroSignal
from app.schemas.scoring_v2 import (
    ScoringV2Result,
    SphereContribution,
    SphereScoreV2,
)
from app.services.canon_service import get_canon_versions
from app.services.scoring_service import (
    _aspect_threshold,
    _aspect_weight,
    _is_major,
    _POSITIVE,
    _NEGATIVE,
    ScoringService,
)

# ── Strict canon helpers ─────────────────────────────────────────────────────


def _required_float(data: dict, *keys: str) -> float:
    """Strict canon float lookup. Raises KeyError if missing or non-numeric."""
    d = data
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            raise KeyError(f"Missing required canon key: {'.'.join(keys)}")
        d = d[k]
    try:
        return float(d)
    except (ValueError, TypeError):
        raise KeyError(f"Non-numeric canon value for: {'.'.join(keys)}")


def _required_mapping(data: dict, *keys: str) -> dict:
    """Strict canon mapping lookup. Raises KeyError if missing."""
    d = data
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            raise KeyError(f"Missing required canon mapping: {'.'.join(keys)}")
        d = d[k]
    if not isinstance(d, dict):
        raise KeyError(f"Expected mapping for: {'.'.join(keys)}")
    return d


# ── Canon loading ────────────────────────────────────────────────────────────

_SPHERES: dict | None = None
_SCORING_V2: dict | None = None
_ACTIVATION_RULES: dict | None = None


def _resolve_canon_path(relative: str) -> str:
    here = pathlib.Path(__file__).resolve().parent
    root = here.parent.parent.parent.parent
    return os.path.join(root, relative)


def _load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _get_spheres() -> dict:
    global _SPHERES
    if _SPHERES is None:
        path = _resolve_canon_path("grace/canon/spheres.v1.yml")
        _SPHERES = _load_yaml(path)
    return _SPHERES


def _get_scoring_v2() -> dict:
    global _SCORING_V2
    if _SCORING_V2 is None:
        path = _resolve_canon_path("grace/canon/scoring_v2.v1.yml")
        _SCORING_V2 = _load_yaml(path)
    return _SCORING_V2


def _get_activation_rules() -> dict:
    global _ACTIVATION_RULES
    if _ACTIVATION_RULES is None:
        path = _resolve_canon_path("grace/canon/activation_rules.v1.yml")
        _ACTIVATION_RULES = _load_yaml(path)
    return _ACTIVATION_RULES


def _get_family_independence_weight(technique_family: str) -> float:
    """Strict family weight lookup. Raises KeyError for unknown families."""
    rules = _get_activation_rules()
    families = _required_mapping(rules, "technique_families")
    if technique_family not in families:
        raise KeyError(f"Unknown technique_family: '{technique_family}'")
    info = families[technique_family]
    return _required_float(info, "independence_weight")


def _family_for_technique(technique: str) -> str:
    """Determine the technique family for a given technique name. Raises KeyError if unknown."""
    families = _required_mapping(_get_activation_rules(), "technique_families")
    for family, info in families.items():
        members = info.get("members", [])
        if technique in members:
            return family
    raise KeyError(f"Unknown technique: '{technique}'")


# START_BLOCK: ACTIVATION_CONTRIBUTION


def _map_activation_to_spheres(
    activation: ActivationEvidence,
    spheres_data: dict,
    scoring_v2: dict,
) -> list[tuple[str, float]]:
    """Map an activation to zero or more spheres. Returns [(sphere_key, target_weight), ...]."""
    results: list[tuple[str, float]] = []
    target_type = activation.target_type
    target_key = (activation.target_key or "").upper()
    angle = (activation.angle or target_key).upper() if target_type == "angle" else ""

    twd = _required_mapping(scoring_v2, "target_weight_defaults")
    angle_map = _required_mapping(scoring_v2, "angle_sphere_map")

    for skey, sphere in spheres_data.items():
        weight = 0.0

        if target_type == "planet":
            pw = sphere.get("planets", {}).get(target_key)
            if pw is not None:
                weight = float(pw)

        elif target_type == "house":
            h = activation.house or int(activation.target_key) if activation.target_key else None
            if h and h in sphere.get("houses", []):
                weight = _required_float(twd, "house")

        elif target_type == "lot":
            if target_key in sphere.get("lots", []):
                weight = _required_float(twd, "lot")

        elif target_type == "angle":
            if angle in angle_map:
                mapped_spheres = angle_map[angle]
                if skey in mapped_spheres:
                    weight = _required_float(twd, "angle")

        elif target_type == "sphere":
            if target_key == skey.upper():
                weight = _required_float(twd, "sphere")

        if weight > 0:
            results.append((skey, weight))

    return results


# END_BLOCK: ACTIVATION_CONTRIBUTION

# START_BLOCK: CONVERGENCE


def _compute_convergence_bonus(
    sphere_key: str,
    activation_families: set[str],
    scoring_v2: dict,
) -> float:
    """Compute convergence bonus for a sphere based on unique technique families."""
    n = len(activation_families)
    if n <= 1:
        return 0.0
    curve = _required_mapping(scoring_v2, "convergence_curve")
    capped_n = min(n, 5)
    if capped_n not in curve:
        raise KeyError(f"Missing convergence_curve entry for {capped_n}")
    bonus_factor = float(curve[capped_n])
    conv_weight = _required_mapping(scoring_v2, "sphere_convergence_weight")
    default_w = _required_float(conv_weight, "default")
    return round(bonus_factor * default_w, 4)


# END_BLOCK: CONVERGENCE

# START_BLOCK: ANTI_DOMINANCE


def _apply_dominance_cap(
    sphere_scores: dict[str, SphereScoreV2],
    scoring_v2: dict,
) -> dict[str, SphereScoreV2]:
    """Apply anti-dominance cap to sphere scores."""
    cap_config = _required_mapping(scoring_v2, "dominance_cap")
    enabled = cap_config.get("enabled")
    if enabled is None or not enabled:
        return sphere_scores

    threshold = _required_float(cap_config, "threshold")
    sum_all = sum(s.raw_score for s in sphere_scores.values() if s.raw_score > 0)

    for key, ss in sphere_scores.items():
        if ss.raw_score <= 0:
            continue
        cap_value = threshold * sum_all
        if ss.raw_score > cap_value:
            cap_amount = round(cap_value - ss.raw_score, 4)
            ss.final_score = round(cap_value, 4)
            ss.dominance_capped = True
            ss.contributions.append(SphereContribution(
                sphere=key,
                source="cap",
                source_id=f"cap:{key}",
                amount=cap_amount,
                before=ss.raw_score,
                after=ss.final_score,
                evidence=f"Dominance cap applied: sphere exceeded {int(threshold*100)}% of total salience",
            ))

    return sphere_scores


# END_BLOCK: ANTI_DOMINANCE

# START_BLOCK: DAY_STATUS


def _compute_day_status_v2(
    signals: list[AstroSignal],
    activations: list[ActivationEvidence],
    scoring_v2: dict,
) -> tuple[str, dict]:
    """Compute V2 day status with transparent breakdown and V1 aspect thresholds."""
    thresholds = _required_mapping(scoring_v2, "status_thresholds")
    positive_ratio = _required_float(thresholds, "positive_ratio")
    positive_min = _required_float(thresholds, "positive_min_score")
    negative_ratio = _required_float(thresholds, "negative_ratio")
    negative_min = _required_float(thresholds, "negative_min_score")

    polarity_mod = _required_mapping(scoring_v2, "activation_polarity")
    support_mod = _required_mapping(polarity_mod, "status_support_modifier")
    tension_mod = _required_mapping(polarity_mod, "status_tension_modifier")

    # Aspect-based scores with V1 threshold (same as ScoringService._calculate_day_status)
    aspects = [s for s in signals if s.type == "aspect"]
    positive_aspect_score = 0.0
    negative_aspect_score = 0.0

    for s in aspects:
        aw = _aspect_weight(s.aspect_type or "")
        threshold = _aspect_threshold(_is_major(s.aspect_type or ""))
        base = aw * s.strength
        if base < threshold:
            continue
        atype = s.aspect_type or ""
        if atype in _POSITIVE:
            positive_aspect_score += base
        elif atype in _NEGATIVE:
            negative_aspect_score += base
        else:
            positive_aspect_score += base * 0.5
            negative_aspect_score += base * 0.5

    # Activation-based scores (only active activations)
    activation_support_score = 0.0
    activation_tension_score = 0.0

    for a in activations:
        if a.active is not None and not a.active:
            continue
        family = a.technique_family or _family_for_technique(a.technique)
        fw = _get_family_independence_weight(family)
        amount = a.strength * fw
        pol = a.polarity or "neutral"
        if pol not in support_mod:
            raise KeyError(f"Missing activation_polarity.status_support_modifier.{pol}")
        if pol not in tension_mod:
            raise KeyError(f"Missing activation_polarity.status_tension_modifier.{pol}")
        activation_support_score += amount * float(support_mod[pol])
        activation_tension_score += amount * float(tension_mod[pol])

    support_score = round(positive_aspect_score + activation_support_score, 4)
    tension_score = round(negative_aspect_score + activation_tension_score, 4)

    # Status determination
    ratio: float | None = round(support_score / tension_score, 4) if tension_score > 0 else None

    if support_score > tension_score * positive_ratio and support_score >= positive_min:
        status = "supportive"
        rule = f"supportive_if_support_score_gt_tension_{positive_ratio}"
    elif tension_score > support_score * negative_ratio and tension_score >= negative_min:
        status = "tense"
        rule = f"tense_if_tension_score_gt_support_{negative_ratio}"
    else:
        status = "steady"
        rule = "steady_otherwise"

    breakdown = {
        "positive_aspect_score": round(positive_aspect_score, 4),
        "negative_aspect_score": round(negative_aspect_score, 4),
        "activation_support_score": round(activation_support_score, 4),
        "activation_tension_score": round(activation_tension_score, 4),
        "support_score": support_score,
        "tension_score": tension_score,
        "ratio": ratio,
        "rule": rule,
    }

    return status, breakdown


# END_BLOCK: DAY_STATUS


class ScoringV2Service:
    """V2 scoring service. Pure computation, no side effects."""

    def score_day(
        self,
        day_signals: list[AstroSignal],
        activation_layer: ActivationLayer | dict | None = None,
    ) -> ScoringV2Result:
        # START_FUNCTION_CONTRACT: F-M-API-SCORING-V2-SERVICE.score_day
        # purpose: Compute V2 scoring result from day signals and optional activation layer.
        # inputs: day_signals — filtered day-scored signals;
        #         activation_layer — ActivationLayer, dict, or None.
        # returns: ScoringV2Result with full breakdown.
        # side_effects: none
        # error_behavior: KeyError on missing canon keys; ValueError on invalid activation layer.
        # END_FUNCTION_CONTRACT: F-M-API-SCORING-V2-SERVICE.score_day
        # Validate activation layer
        if activation_layer is not None:
            if isinstance(activation_layer, dict):
                activation_layer = ActivationLayer.model_validate(activation_layer)
        else:
            activation_layer = ActivationLayer(
                calculation_version=CALCULATION_VERSION,
                target_date="",
                target_time="",
                target_tz="",
                house_system="",
                activations=[],
                by_planet={},
                by_house={},
                by_lot={},
                by_angle={},
            )

        if not isinstance(activation_layer, ActivationLayer):
            raise ValueError("activation_layer must be ActivationLayer, dict, or None")

        scoring_v2 = _get_scoring_v2()
        spheres_data = _get_spheres().get("spheres", {})

        # ── 1. Base scores (V1 pre-cap formula via ScoringService) ──────
        base_scores = ScoringService()._calculate_sphere_scores(day_signals)

        # ── 2. Activation contributions (only active activations) ────────
        sphere_data: dict[str, dict] = {}
        for key in spheres_data:
            title = spheres_data[key].get("title", key)
            sphere_data[key] = {
                "key": key,
                "title": title,
                "base_score": base_scores[key],
                "activation_score": 0.0,
                "convergence_bonus": 0.0,
                "raw_score": 0.0,
                "final_score": 0.0,
                "dominance_capped": False,
                "contributions": [],
                "activated_families": set(),
            }

        unmapped_activations: list[str] = []

        for act in activation_layer.activations:
            if act.active is not None and not act.active:
                continue  # skip inactive activations

            mappings = _map_activation_to_spheres(act, spheres_data, scoring_v2)
            if not mappings:
                unmapped_activations.append(act.id)
                continue

            family = act.technique_family or _family_for_technique(act.technique)
            fw = _get_family_independence_weight(family)
            polarity_mod = _required_mapping(scoring_v2, "activation_polarity", "sphere_amount_modifier")
            pol = act.polarity or "neutral"
            if pol not in polarity_mod:
                raise KeyError(f"Missing activation_polarity.sphere_amount_modifier.{pol}")
            pol_mod = float(polarity_mod[pol])

            for skey, tweight in mappings:
                amount = round(act.strength * fw * tweight * pol_mod, 4)
                before = sphere_data[skey]["base_score"] + sphere_data[skey]["activation_score"]
                after = round(before + amount, 4)

                sphere_data[skey]["activation_score"] = round(
                    sphere_data[skey]["activation_score"] + amount, 4
                )
                sphere_data[skey]["activated_families"].add(family)
                sphere_data[skey]["contributions"].append(SphereContribution(
                    sphere=skey,
                    source="activation",
                    source_id=act.id,
                    amount=amount,
                    before=before,
                    after=after,
                    evidence=act.evidence or "",
                ))

        # ── 3. Convergence ──────────────────────────────────────────────
        convergence_by_sphere: dict[str, dict] = {}
        for key, sd in sphere_data.items():
            families = sd["activated_families"]
            bonus = _compute_convergence_bonus(key, families, scoring_v2)
            if bonus > 0:
                before = sd["base_score"] + sd["activation_score"]
                after = round(before + bonus, 4)
                sd["convergence_bonus"] = bonus
                sd["contributions"].append(SphereContribution(
                    sphere=key,
                    source="convergence",
                    source_id=f"convergence:{key}",
                    amount=bonus,
                    before=before,
                    after=after,
                    evidence=f"Convergence bonus: {len(families)} independent technique families ({', '.join(sorted(families))})",
                ))
                convergence_by_sphere[key] = {
                    "families": sorted(families),
                    "family_count": len(families),
                }

        # ── 4. Raw score ────────────────────────────────────────────────
        for key, sd in sphere_data.items():
            sd["raw_score"] = round(
                sd["base_score"] + sd["activation_score"] + sd["convergence_bonus"], 4
            )
            sd["final_score"] = sd["raw_score"]

        # ── 5. Build SphereScoreV2 objects ──────────────────────────────
        sphere_scores: dict[str, SphereScoreV2] = {}
        for key, sd in sphere_data.items():
            ss = SphereScoreV2(
                key=sd["key"],
                title=sd["title"],
                base_score=sd["base_score"],
                activation_score=sd["activation_score"],
                convergence_bonus=sd["convergence_bonus"],
                raw_score=sd["raw_score"],
                final_score=sd["raw_score"],
                normalized_score=None,
                dominance_capped=False,
                contributions=sd["contributions"],
            )
            sphere_scores[key] = ss

        # Base contributions
        for key, ss in sphere_scores.items():
            if ss.base_score != 0:
                ss.contributions.insert(0, SphereContribution(
                    sphere=key,
                    source="base_signal",
                    source_id=f"base_signal:{key}",
                    amount=ss.base_score,
                    before=0.0,
                    after=ss.base_score,
                    evidence=f"Base day signal score for {ss.title}",
                ))

        sphere_scores = _apply_dominance_cap(sphere_scores, scoring_v2)

        # ── 6. Day status (only active activations) ─────────────────────
        active_acts = [a for a in activation_layer.activations
                       if a.active is not None and a.active is not False]
        status, status_breakdown = _compute_day_status_v2(
            day_signals, active_acts, scoring_v2,
        )

        # ── 7. Top activations (only active) ────────────────────────────
        sorted_acts = sorted(
            active_acts,
            key=lambda a: (-a.strength, a.id),
        )[:10]

        # ── 8. Top signals (V1) ─────────────────────────────────────────
        v1_service = ScoringService()
        v1_result = v1_service.score_day(day_signals)
        top_signals = [s.model_dump(by_alias=True) if hasattr(s, 'model_dump') else s
                       for s in v1_result.get("top_signals", [])]

        # ── 9. Debug ────────────────────────────────────────────────────
        dc = _required_mapping(scoring_v2, "dominance_cap")
        if "enabled" not in dc:
            raise KeyError("Missing dominance_cap.enabled")
        debug: dict[str, Any] = {
            "unmapped_activations": unmapped_activations,
            "convergence_by_sphere": convergence_by_sphere,
            "dominance_cap": {
                "enabled": bool(dc["enabled"]),
                "threshold": _required_float(scoring_v2, "dominance_cap", "threshold"),
                "sum_all_positive_scores": round(
                    sum(s.raw_score for s in sphere_scores.values() if s.raw_score > 0), 4
                ),
            },
        }

        return ScoringV2Result(
            scoring_version=SCORING_V2_VERSION,
            canon_versions=get_canon_versions(),
            day_status=status,
            status_breakdown=status_breakdown,
            sphere_scores=sphere_scores,
            top_signals=top_signals,
            top_activations=sorted_acts,
            debug=debug,
        )
