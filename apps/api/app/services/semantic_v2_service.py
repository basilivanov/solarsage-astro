# ############################################################################
# AI_HEADER: MODULE_SEMANTIC_V2_SERVICE — build V2 semantic layer block.
# ROLE: SemanticV2Service — builds the TodayV2Block schema for the frontend.
# ############################################################################

from __future__ import annotations
import sys
from typing import Any, Literal
from app.core.versions import SCORING_V2_VERSION, TODAY_V2_PAYLOAD_VERSION
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.schemas.scoring_v2 import ScoringV2Result, SphereScoreV2
from app.schemas.today import (
    TodayV2Block,
    TodayV2ActivationSummary,
    TodayV2ActivatedTarget,
    TodayV2WhyTodayItem,
    TodayV2Audit,
    ConcreteAdviceEvidence,
)
from app.services.canon_service import load_canon_bundle

PLANET_LABELS = {
    "SUN": "Солнце",
    "MOON": "Луна",
    "MERCURY": "Меркурий",
    "VENUS": "Венера",
    "MARS": "Марс",
    "JUPITER": "Юпитер",
    "SATURN": "Сатурн",
    "URANUS": "Уран",
    "NEPTUNE": "Нептун",
    "PLUTO": "Плутон",
    "NORTH_NODE": "Северный узел",
    "SOUTH_NODE": "Южный узел",
    "CHIRON": "Хирон",
}

ANGLE_LABELS = {
    "ASC": "Асцендент",
    "DSC": "Десцендент",
    "MC": "Меридиан (MC)",
    "IC": "Надир (IC)",
}

LOT_LABELS = {
    "FORTUNE": "Жребий Фортуны",
    "SPIRIT": "Жребий Духа",
    "EROS": "Жребий Эроса",
    "MARRIAGE": "Жребий Брака",
    "NECESSITY": "Жребий Необходимости",
    "VICTORY": "Жребий Победы",
    "NEMESIS": "Жребий Немезиды",
}

TECHNIQUE_FAMILY_LABELS = {
    "transit": "Транзиты",
    "profection": "Профекции",
    "firdar": "Фирдары",
    "return": "Возвращения",
    "progression": "Прогрессии",
    "eclipse": "Затмения",
}


def get_target_label(target_type: str, target_key: str) -> str:
    key_upper = target_key.upper()
    if target_type == "planet":
        return PLANET_LABELS.get(key_upper, target_key)
    elif target_type == "angle":
        return ANGLE_LABELS.get(key_upper, target_key)
    elif target_type == "lot":
        return LOT_LABELS.get(key_upper, target_key)
    elif target_type == "house":
        return f"{target_key} дом"
    elif target_type == "sphere":
        return target_key
    return target_key


def get_target_spheres(target_type: str, target_key: str, spheres_data: dict) -> list[str]:
    mapped_spheres = []
    for sphere_key, sphere_val in spheres_data.get("spheres", {}).items():
        if target_type == "house":
            try:
                house_num = int(target_key)
                if house_num in sphere_val.get("houses", []):
                    mapped_spheres.append(sphere_key)
            except ValueError:
                pass
        elif target_type == "planet":
            if target_key.upper() in [k.upper() for k in sphere_val.get("planets", {}).keys()]:
                mapped_spheres.append(sphere_key)
        elif target_type == "lot":
            if target_key.upper() in [l.upper() for l in sphere_val.get("lots", [])]:
                mapped_spheres.append(sphere_key)
        elif target_type == "angle":
            angle_map = {"ASC": 1, "DSC": 7, "MC": 10, "IC": 4}
            mapped_house = angle_map.get(target_key.upper())
            if mapped_house and mapped_house in sphere_val.get("houses", []):
                mapped_spheres.append(sphere_key)
    return mapped_spheres


class SemanticV2Service:
    def __init__(self):
        self._canon = load_canon_bundle()
        self._spheres_data = self._canon.get("spheres.v1.yml", {})

    def build_v2_block(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result | None = None,
        v1_v2_diff: dict | None = None,
        trace_id: str | None = None,
    ) -> TodayV2Block:
        if scoring_result is None:
            raise ValueError("scoring_result is required for V2 block")
        # Group activations by target
        grouped: dict[tuple[str, str], list[ActivationEvidence]] = {}
        for act in activation_layer.activations:
            key = (act.target_type, act.target_key)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(act)

        # Build activated targets list
        activated_targets = []
        for (target_type, target_key), acts in grouped.items():
            families = {act.technique_family for act in acts}
            techniques = sorted(list({act.technique for act in acts}))
            spheres = get_target_spheres(target_type, target_key, self._spheres_data)
            act_ids = [act.id for act in acts]
            total_strength = sum(act.strength for act in acts)

            activated_targets.append({
                "target_type": target_type,
                "target_key": target_key,
                "label": get_target_label(target_type, target_key),
                "family_count": len(families),
                "techniques": techniques,
                "spheres": spheres,
                "activation_ids": act_ids,
                "total_strength": total_strength,
            })

        # Sort activated targets deterministically
        # 1. descending family_count
        # 2. descending total_strength
        # 3. target_type
        # 4. target_key
        def sort_key(t):
            return (-t["family_count"], -t["total_strength"], t["target_type"], t["target_key"])

        activated_targets.sort(key=sort_key)

        # Convert to schema model
        top_activated_targets = [
            TodayV2ActivatedTarget(
                target_type=t["target_type"],
                target_key=t["target_key"],
                label=t["label"],
                family_count=t["family_count"],
                techniques=t["techniques"],
                spheres=t["spheres"],
                activation_ids=t["activation_ids"],
            )
            for t in activated_targets
        ]

        # Determine convergence & summary headline
        has_convergence = len(top_activated_targets) > 0 and top_activated_targets[0].family_count >= 2
        if has_convergence:
            top_target = top_activated_targets[0]
            headline = f"Сегодня сходятся {top_target.family_count} независимые техники на теме: {top_target.label}"
        else:
            headline = "День в основном определяется текущими транзитами, без сильной сходимости долгих техник."

        activation_summary = TodayV2ActivationSummary(
            headline=headline,
            top_activated_targets=top_activated_targets[:5],  # Top 5 targets
        )

        # Build why_today
        why_today = []
        if not has_convergence:
            why_today.append(
                TodayV2WhyTodayItem(
                    id="fallback-no-convergence",
                    title="Влияние транзитов",
                    body="День в основном определяется текущими транзитами, без сильной сходимости долгих техник.",
                    activation_ids=[],
                    techniques=[],
                )
            )
        else:
            # Generate items for targets with family_count >= 2
            for target in top_activated_targets:
                if target.family_count < 2:
                    continue

                # Group activations for this target by technique family
                target_acts = grouped[(target.target_type, target.target_key)]
                family_groups: dict[str, list[ActivationEvidence]] = {}
                for act in target_acts:
                    if act.technique_family not in family_groups:
                        family_groups[act.technique_family] = []
                    family_groups[act.technique_family].append(act)

                for family, acts_in_family in family_groups.items():
                    # Sort by strength to find strongest
                    acts_in_family.sort(key=lambda x: x.strength, reverse=True)
                    strongest = acts_in_family[0]
                    family_label = TECHNIQUE_FAMILY_LABELS.get(family, family)

                    why_today.append(
                        TodayV2WhyTodayItem(
                            id=f"why-{target.target_type}-{target.target_key}-{family}",
                            title=f"{family_label} активируют {target.label}",
                            body=f"Влияние на {target.label}: {strongest.evidence}.",
                            activation_ids=[act.id for act in acts_in_family],
                            techniques=sorted(list({act.technique for act in acts_in_family})),
                        )
                    )

        # Populate scoreBreakdown
        score_breakdown = {}
        if scoring_result and scoring_result.sphere_scores:
            score_breakdown = scoring_result.sphere_scores

        # Build audit
        from app.services.canon_service import get_canon_versions
        canon_versions = {}
        if scoring_result and hasattr(scoring_result, "canon_versions") and scoring_result.canon_versions:
            if isinstance(scoring_result, dict):
                canon_versions = scoring_result.get("canon_versions") or {}
            else:
                canon_versions = getattr(scoring_result, "canon_versions", {}) or {}
        else:
            canon_versions = get_canon_versions()

        audit = TodayV2Audit(
            trace_id=trace_id,
            available=True,
            payload_version=TODAY_V2_PAYLOAD_VERSION,
            calculation_version=activation_layer.calculation_version,
            scoring_version=scoring_result.scoring_version if scoring_result and hasattr(scoring_result, "scoring_version") else SCORING_V2_VERSION,
            activation_layer_version=activation_layer.activation_layer_version,
            canon_versions={str(k): str(v) for k, v in canon_versions.items()},
            v1_v2_diff=v1_v2_diff,
        )

        return TodayV2Block(
            activation_summary=activation_summary,
            activation_evidence=activation_layer.activations,
            score_breakdown=score_breakdown,
            why_today=why_today,
            audit=audit,
        )

    def get_evidence_for_sphere(
        self,
        *,
        backend_sphere_key: str,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result | None = None,
    ) -> list[ConcreteAdviceEvidence]:
        evidence_list = []

        # 1. Collect activation evidence
        for act in activation_layer.activations:
            if backend_sphere_key in get_target_spheres(act.target_type, act.target_key, self._spheres_data):
                evidence_list.append(
                    ConcreteAdviceEvidence(
                        kind="activation",
                        title=act.evidence,
                        strength=act.strength,
                        planet=act.source_planet,
                        target_planet=act.target_planet,
                        aspect_type=act.aspect,
                        orb=act.orb,
                        house=act.house,
                        activation_id=act.id,
                        technique=act.technique,
                        technique_family=act.technique_family,
                        source_frame=act.source_frame,
                        target_frame=act.target_frame,
                    )
                )

        # 2. Collect score contribution evidence
        if scoring_result and scoring_result.sphere_scores:
            sphere_score = scoring_result.sphere_scores.get(backend_sphere_key)
            if sphere_score:
                for contrib in sphere_score.contributions:
                    evidence_list.append(
                        ConcreteAdviceEvidence(
                            kind="score_contribution",
                            title=contrib.evidence,
                            weight=contrib.amount,
                            strength=contrib.amount,
                            contribution_source_id=contrib.source_id,
                        )
                    )

        return evidence_list

    def build_llm_evidence_packet(
        self,
        *,
        day_status: str,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result | None = None,
        contexts: list[dict],
    ) -> dict[str, Any]:
        top_activations = [
            {
                "id": act.id,
                "technique": act.technique,
                "technique_family": act.technique_family,
                "target_type": act.target_type,
                "target_key": act.target_key,
                "strength": act.strength,
                "evidence": act.evidence,
            }
            for act in activation_layer.activations
        ]

        sphere_scores = {}
        if scoring_result and scoring_result.sphere_scores:
            sphere_scores = {k: v.final_score for k, v in scoring_result.sphere_scores.items()}

        concrete_rows = []
        forbidden_claims = []
        for ctx in contexts:
            key = ctx.get("key")
            verdict = ctx.get("verdict")
            concrete_rows.append({
                "key": key,
                "verdict": verdict,
                "evidence": [ev.get("title") for ev in ctx.get("evidence", [])]
            })
            if verdict == "avoid":
                if key == "relationships":
                    forbidden_claims.append("no direct relationship improvement or conflict-opening advice for relationships")
                elif key == "money":
                    forbidden_claims.append("no invest/spend/buy recommendation for money")
                elif key in ("sport", "health"):
                    forbidden_claims.append("no intense sport recommendation for sport/health")
                elif key == "communication":
                    forbidden_claims.append("no hard negotiation recommendation for communication")

        return {
            "day_status": day_status,
            "status_breakdown": scoring_result.status_breakdown if scoring_result else {},
            "top_activations": top_activations,
            "sphere_scores": sphere_scores,
            "concrete_rows": concrete_rows,
            "forbidden_claims": forbidden_claims,
            "required_distinctions": [
                "distinguish transit-to-natal from transit-to-transit"
            ]
        }
