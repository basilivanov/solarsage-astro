# ############################################################################
# AI_HEADER: MODULE_DAY_VALENCE_SERVICE
# ROLE: Pure service calculating signed valence, 12 product sphere assessments, and global day status.
# DEPENDENCIES: app.schemas.day_valence, app.services.canon_service
# GRACE_ANCHORS: [DAY_VALENCE_ENGINE]
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-VALENCE
# purpose: Compute 12 ProductSphereAssessments and global DayStatusBreakdown from factor ledger and canon (§6-7).
# owns:
#   - apps/api/app/services/day_valence_service.py
# inputs: ledger (FactorLedger), sphere_scores_v2 (optional dict/list of SphereScoreV2 or dicts)
# outputs: tuple[dict[str, ProductSphereAssessment], DayStatusBreakdown, str] (assessments dict, breakdown, day_status string)
# dependencies: app.schemas.day_valence, app.services.canon_service
# side_effects: none (pure calculation)
# emitted_logs: none
# failure_policy: fail-closed on missing canon
# END_MODULE_CONTRACT: M-DAY-VALENCE

# START_MODULE_MAP: M-DAY-VALENCE
# public_entrypoints:
#   - DayValenceService.compute
# semantic_blocks:
#   - VALENCE_ENGINE: factor magnitude, family volume reducer, polarity split, sphere projection, verdict rules, and day status
# owned_tests:
#   - apps/api/tests/test_day_valence_engine.py
# END_MODULE_MAP: M-DAY-VALENCE

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.schemas.day_valence import (
    DayStatusBreakdown,
    DayValenceFactor,
    FactorLedger,
    ProductSphereAssessment,
)
from app.services.canon_service import load_day_valence_canon

CANONICAL_PRODUCT_SPHERES = [
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


class DayValenceService:
    """Pure API-owned signed valence calculation engine (§6)."""

    def __init__(self, canon_dir: Path | None = None) -> None:
        self.canon = load_day_valence_canon(canon_dir)
        self.aspect_weights: dict[str, float] = self.canon.get("aspect_weights", {})
        self.planet_weights: dict[str, float] = self.canon.get("planet_weights", {})
        self.family_ind_weights: dict[str, float] = self.canon.get("family_independence_weights", {})
        self.decay_multipliers: list[float] = self.canon.get("family_decay_multipliers", [1.00, 0.50, 0.25])
        self.tech_to_product: dict[str, list[str]] = self.canon.get("technical_to_product_spheres", {})
        self.verdict_thresholds: dict[str, Any] = self.canon.get("verdict_thresholds", {})
        self.confidence_thresholds: dict[str, Any] = self.canon.get("confidence_thresholds", {})
        self.day_status_thresholds: dict[str, Any] = self.canon.get("day_status_thresholds", {})

    def _get_planet_weight(self, key: str | None) -> float:
        if not key:
            return 1.0
        k_cap = key.strip().capitalize()
        if k_cap in self.planet_weights:
            return float(self.planet_weights[k_cap])
        if key in self.planet_weights:
            return float(self.planet_weights[key])
        if key.upper() in self.planet_weights:
            return float(self.planet_weights[key.upper()])
        return 1.0

    # START_BLOCK: VALENCE_ENGINE
    def _calculate_factor_raw_magnitude(self, factor: DayValenceFactor) -> float:
        """Calculate un-reduced factor magnitude per §6.1 and §6.2."""
        if factor.source == "day_signal":
            # Target planet weight, fallback to source planet
            target_p = factor.target_key if factor.target_type == "natal_planet" else (factor.source_planet or "")
            tech_weight = self._get_planet_weight(target_p)
            asp_weight = float(self.aspect_weights.get(factor.aspect_type or "", 1.0))
            return asp_weight * factor.strength * tech_weight
        else:
            # Activation magnitude §6.2
            fam_ind_weight = float(self.family_ind_weights.get(factor.technique_family, 1.0))
            target_p = factor.target_key or factor.source_planet
            target_weight = self._get_planet_weight(target_p)
            return factor.strength * fam_ind_weight * target_weight

    def _reduce_and_sum_valence(
        self, factors: list[tuple[DayValenceFactor, float]]
    ) -> tuple[float, float, int, int, set[str], DayValenceFactor | None, DayValenceFactor | None]:
        """Apply family volume reducer (§6.4) and polarity split (§6.3).

        Returns: (support_score, tension_score, total_factor_count, effective_factor_count, family_set, best_supportive, best_tense)
        """
        if not factors:
            return 0.0, 0.0, 0, 0, set(), None, None

        # Group valenced factors by family
        family_groups: dict[str, list[tuple[DayValenceFactor, float]]] = {}
        total_count = len(factors)

        for factor, mag in factors:
            if factor.polarity in ("supportive", "tense", "mixed"):
                family_groups.setdefault(factor.technique_family, []).append((factor, mag))

        support = 0.0
        tension = 0.0
        effective_count = 0
        family_set = set(family_groups.keys())

        best_support_factor: tuple[DayValenceFactor, float] | None = None
        best_tense_factor: tuple[DayValenceFactor, float] | None = None

        for fam, group in family_groups.items():
            # Sort group by (-magnitude, factor_id)
            group.sort(key=lambda item: (-item[1], item[0].factor_id))

            for rank, (factor, mag) in enumerate(group):
                if rank >= len(self.decay_multipliers):
                    mult = 0.0
                else:
                    mult = self.decay_multipliers[rank]

                if mult <= 0.0:
                    continue

                effective_mag = mag * mult
                effective_count += 1

                if factor.polarity == "supportive":
                    support += effective_mag
                    if best_support_factor is None or effective_mag > best_support_factor[1]:
                        best_support_factor = (factor, effective_mag)
                elif factor.polarity == "tense":
                    tension += effective_mag
                    if best_tense_factor is None or effective_mag > best_tense_factor[1]:
                        best_tense_factor = (factor, effective_mag)
                elif factor.polarity == "mixed":
                    half_mag = effective_mag * 0.5
                    support += half_mag
                    tension += half_mag
                    if best_support_factor is None or half_mag > best_support_factor[1]:
                        best_support_factor = (factor, half_mag)
                    if best_tense_factor is None or half_mag > best_tense_factor[1]:
                        best_tense_factor = (factor, half_mag)

        best_supp = best_support_factor[0] if best_support_factor else None
        best_tens = best_tense_factor[0] if best_tense_factor else None

        return (
            round(support, 4),
            round(tension, 4),
            total_count,
            effective_count,
            family_set,
            best_supp,
            best_tens,
        )

    def _compute_sphere_assessment(
        self,
        key: str,
        factors: list[tuple[DayValenceFactor, float]],
        salience_score: float,
    ) -> ProductSphereAssessment:
        """Compute ProductSphereAssessment for a single sphere (§6.6)."""
        support, tension, total_cnt, eff_cnt, family_set, best_supp, best_tens = (
            self._reduce_and_sum_valence(factors)
        )

        total = round(support + tension, 4)
        if total == 0:
            balance = 0.0
        else:
            balance = round((support - tension) / total, 4)

        # Verdict rules evaluation order §6.6
        # avoid: tension >= 1.50 and (support == 0 or tension >= support * 2.00)
        # caution: tension >= 0.75 and (support == 0 or tension > support * 1.30)
        # good: support >= 0.75 and (tension == 0 or support > tension * 1.30)
        # neutral: otherwise
        verdict: Literal["good", "neutral", "caution", "avoid"]
        verdict_rule: Literal[
            "avoid_tension_2x",
            "caution_tension_1_3x",
            "good_support_1_3x",
            "neutral_low_evidence",
            "neutral_balanced",
        ]

        if tension >= 1.50 and (support == 0.0 or tension >= round(support * 2.00, 4)):
            verdict = "avoid"
            verdict_rule = "avoid_tension_2x"
        elif tension >= 0.75 and (support == 0.0 or tension > round(support * 1.30, 4)):
            verdict = "caution"
            verdict_rule = "caution_tension_1_3x"
        elif support >= 0.75 and (tension == 0.0 or support > round(tension * 1.30, 4)):
            verdict = "good"
            verdict_rule = "good_support_1_3x"
        else:
            verdict = "neutral"
            verdict_rule = "neutral_low_evidence" if total < 0.75 else "neutral_balanced"

        # Confidence §6.6
        ind_families = len(family_set)
        if total >= 2.00 and ind_families >= 2:
            confidence: Literal["low", "medium", "high"] = "high"
        elif total >= 0.75:
            confidence = "medium"
        else:
            confidence = "low"

        # Primary driving factor §7.1
        primary_factor: DayValenceFactor | None = None
        if verdict == "good":
            primary_factor = best_supp or best_tens
        elif verdict in ("caution", "avoid"):
            primary_factor = best_tens or best_supp
        else:
            # neutral: highest effective valenced factor, tie factor_id asc
            primary_factor = best_supp if (best_supp and (not best_tens or get_strength(best_supp) >= get_strength(best_tens))) else best_tens

        primary_id = primary_factor.factor_id if primary_factor else None

        return ProductSphereAssessment(
            key=key,
            salience_score=round(salience_score, 4),
            support_score=support,
            tension_score=tension,
            balance=balance,
            verdict=verdict,
            confidence=confidence,
            verdict_rule=verdict_rule,
            factor_count=total_cnt,
            effective_factor_count=eff_cnt,
            independent_family_count=ind_families,
            primary_factor_id=primary_id,
        )

    def compute(
        self,
        ledger: FactorLedger,
        sphere_scores_v2: dict[str, Any] | list[Any] | None = None,
    ) -> tuple[dict[str, ProductSphereAssessment], DayStatusBreakdown, str]:
        """Compute signed valence for 12 product spheres and global day status.

        Returns: (assessments_dict, status_breakdown, day_status_str)
        """
        # Parse salience scores per technical sphere from sphere_scores_v2
        tech_salience: dict[str, float] = {}
        if sphere_scores_v2:
            if isinstance(sphere_scores_v2, dict):
                for k, v in sphere_scores_v2.items():
                    sc = getattr(v, "final_score", None) if not isinstance(v, dict) else v.get("final_score", v.get("score"))
                    if sc is not None:
                        tech_salience[k] = float(sc)
            elif isinstance(sphere_scores_v2, list):
                for item in sphere_scores_v2:
                    k = getattr(item, "key", None) or (item.get("key") if isinstance(item, dict) else None)
                    sc = getattr(item, "final_score", None) or getattr(item, "score", None) or (item.get("final_score") if isinstance(item, dict) else item.get("score") if isinstance(item, dict) else None)
                    if k and sc is not None:
                        tech_salience[k] = float(sc)

        # 1. Product Sphere Projection (§6.5)
        # Build mapping: product_sphere -> list of (factor, raw_magnitude)
        sphere_factor_maps: dict[str, dict[str, tuple[DayValenceFactor, float]]] = {
            pkey: {} for pkey in CANONICAL_PRODUCT_SPHERES
        }

        for factor in ledger.factors:
            raw_mag = self._calculate_factor_raw_magnitude(factor)

            # Find mapped product spheres
            mapped_product_spheres: set[str] = set()
            for tech_sphere in factor.technical_spheres:
                ps_list = self.tech_to_product.get(tech_sphere, [])
                mapped_product_spheres.update(ps_list)

            # If factor has no technical_spheres (e.g. AstroSignal aspect), deduce from technique / target
            if not mapped_product_spheres and factor.source == "day_signal":
                # AstroSignal aspect: map to product spheres via default fallback mapping or all
                mapped_product_spheres.update(CANONICAL_PRODUCT_SPHERES)

            # Deduplicate per product sphere if factor hits multiple technical spheres (§6.5)
            for pkey in mapped_product_spheres:
                if pkey not in sphere_factor_maps:
                    continue
                existing = sphere_factor_maps[pkey].get(factor.semantic_key)
                if existing is None or raw_mag > existing[1]:
                    sphere_factor_maps[pkey][factor.semantic_key] = (factor, raw_mag)

        # 2. Assess 12 Product Spheres (§6.6)
        assessments: dict[str, ProductSphereAssessment] = {}

        for pkey in CANONICAL_PRODUCT_SPHERES:
            cand_factors = list(sphere_factor_maps[pkey].values())

            # salience_score: max final_score across mapped technical spheres (§6.6)
            mapped_techs = [tk for tk, ps in self.tech_to_product.items() if pkey in ps]
            salience = max([tech_salience.get(tk, 0.0) for tk in mapped_techs], default=0.0)

            assessment = self._compute_sphere_assessment(pkey, cand_factors, salience)
            assessments[pkey] = assessment

        # 3. Global Day Status Calculation (§6.7)
        # Use canonical factor ledger once globally (no sphere projection multiplication)
        global_candidates = [
            (factor, self._calculate_factor_raw_magnitude(factor))
            for factor in ledger.factors
        ]
        g_support, g_tension, g_total_cnt, g_eff_cnt, g_families, _, _ = (
            self._reduce_and_sum_valence(global_candidates)
        )

        g_family_counts: dict[str, int] = {}
        for factor in ledger.factors:
            g_family_counts[factor.technique_family] = g_family_counts.get(factor.technique_family, 0) + 1

        # Global Day Status decision §6.7:
        # supportive if support >= 1.00 and support > tension * 1.30
        # tense if tension >= 1.00 and tension > support * 1.30
        # steady otherwise
        if g_support >= 1.00 and g_support > round(g_tension * 1.30, 4):
            day_status = "supportive"
            rule = "supportive_if_support_score_gt_tension_1.3"
            ratio: float | None = round(g_support / g_tension, 4) if g_tension > 0 else None
        elif g_tension >= 1.00 and g_tension > round(g_support * 1.30, 4):
            day_status = "tense"
            rule = "tense_if_tension_score_gt_support_1.3"
            ratio = round(g_tension / g_support, 4) if g_support > 0 else None
        else:
            day_status = "steady"
            rule = "steady_otherwise"
            ratio = round(g_support / g_tension, 4) if g_tension > 0 else None

        breakdown = DayStatusBreakdown(
            support_score=g_support,
            tension_score=g_tension,
            ratio=ratio,
            rule=rule,
            factor_count=g_total_cnt,
            effective_factor_count=g_eff_cnt,
            family_counts=g_family_counts,
            duplicate_factor_count=ledger.duplicate_count,
        )

        return assessments, breakdown, day_status
    # END_BLOCK: VALENCE_ENGINE


def get_strength(factor: DayValenceFactor) -> float:
    return factor.strength
