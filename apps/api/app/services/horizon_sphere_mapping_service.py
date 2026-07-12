# ############################################################################
# AI_HEADER: MODULE_HORIZON_SPHERE_MAPPING_SERVICE — pure activation-to-product sphere mapping.
# ROLE: Convert activation-linked technical sphere scoring into ordered product spheres and stable theme keys.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-SPHERE-MAPPING-SERVICE
# purpose: Read scoring contributions for one activation and map them through the typed B2A canon.
# owns:
#   - apps/api/app/services/horizon_sphere_mapping_service.py
# inputs: activation id, scoring result, optional source and target planet identifiers.
# outputs: HorizonSphereMapping without evidence/debug/raw text.
# dependencies: collections/re stdlib, app.schemas.horizon_selection, app.schemas.scoring_v2, app.services.horizon_canon_service.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - only activation-linked SphereContribution entries are inspected.
#   - product spheres and theme keys are stable-deduped in canonical order.
#   - empty linkage returns an empty mapping without guessing.
# failure_policy: invalid canon raises; ordinary no-link cases return empty mapping.
# END_MODULE_CONTRACT: M-HORIZON-SPHERE-MAPPING-SERVICE

# START_MODULE_MAP: M-HORIZON-SPHERE-MAPPING-SERVICE
# public_entrypoints:
#   - HorizonSphereMappingService.map_activation
# semantic_blocks:
#   - HORIZON_SPHERE_MAPPING_HELPERS: normalization and stable dedupe helpers.
#   - HORIZON_SPHERE_MAPPING_SERVICE: contribution aggregation and canon mapping.
# owned_tests:
#   - apps/api/tests/test_horizon_sphere_mapping_service.py
# END_MODULE_MAP: M-HORIZON-SPHERE-MAPPING-SERVICE

# START_BLOCK: HORIZON_SPHERE_MAPPING_HELPERS
from __future__ import annotations

from collections import defaultdict
import math
import re

from app.schemas.horizon_selection import HorizonSphereMapping
from app.schemas.scoring_v2 import ScoringV2Result
from app.services.horizon_canon_service import load_horizon_selection_canon

PREFIX_RE = re.compile(r"^(?:TRANSIT_|NATAL_)+")


def _normalize_planet(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = PREFIX_RE.sub("", value.strip().upper())
    return normalized or None


def _stable_dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
# END_BLOCK: HORIZON_SPHERE_MAPPING_HELPERS


# START_BLOCK: HORIZON_SPHERE_MAPPING_SERVICE
class HorizonSphereMappingService:
    def map_activation(
        self,
        activation_id: str,
        scoring_result: ScoringV2Result,
        *,
        source_planet: str | None,
        target_planet_or_key: str | None,
    ) -> HorizonSphereMapping:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-SPHERE-MAPPING-SERVICE.HorizonSphereMappingService.map_activation
        # purpose: Map one activation's linked technical score contributions into ordered product spheres and themes.
        # inputs: activation_id, scoring_result, source_planet, target_planet_or_key.
        # returns: HorizonSphereMapping.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: invalid canon raises; empty linkage returns empty mapping.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-SPHERE-MAPPING-SERVICE.HorizonSphereMappingService.map_activation
        canon = load_horizon_selection_canon()
        sums: dict[str, float] = defaultdict(float)
        for sphere_key, sphere_score in scoring_result.sphere_scores.items():
            if sphere_score.key != sphere_key:
                raise AssertionError("scoring sphere key does not match outer score identity")
            if not math.isfinite(sphere_score.final_score):
                raise AssertionError("scoring sphere final score must be finite")
            for contribution in sphere_score.contributions:
                if contribution.source == "activation" and contribution.source_id == activation_id:
                    if contribution.sphere != sphere_key:
                        raise AssertionError("activation contribution sphere does not match outer score identity")
                    if not math.isfinite(contribution.amount):
                        raise AssertionError("activation contribution amount must be finite")
                    sums[sphere_key] += abs(contribution.amount)
        if not sums:
            return HorizonSphereMapping()
        if not all(math.isfinite(amount) for amount in sums.values()):
            raise AssertionError("linked activation amount must be finite")

        ranked_technical = sorted(
            sums,
            key=lambda key: (
                -sums[key],
                -scoring_result.sphere_scores[key].final_score,
                key,
            ),
        )
        global_rank = {
            key: index + 1
            for index, key in enumerate(
                sorted(scoring_result.sphere_scores, key=lambda key: (-scoring_result.sphere_scores[key].final_score, key))
            )
        }
        product_spheres: list[str] = []
        theme_keys: list[str] = []
        for technical_key in ranked_technical:
            product_spheres.extend(canon.technical_to_product_spheres[technical_key])
            theme_keys.extend(canon.technical_sphere_themes[technical_key])
        normalized_target = _normalize_planet(target_planet_or_key)
        normalized_source = _normalize_planet(source_planet)
        if normalized_target is not None and normalized_target in canon.target_planet_themes:
            theme_keys.extend(canon.target_planet_themes[normalized_target])
        if normalized_source is not None and normalized_source in canon.target_planet_themes:
            theme_keys.extend(canon.target_planet_themes[normalized_source])

        deduped_products = _stable_dedupe(product_spheres)[: canon.limits.max_product_spheres_per_candidate]
        deduped_themes = _stable_dedupe(theme_keys)[: canon.limits.max_theme_keys_per_candidate]
        linked_abs_amount = sum(sums.values())
        if not math.isfinite(linked_abs_amount):
            raise AssertionError("linked activation amount must be finite")
        return HorizonSphereMapping(
            technical_spheres=ranked_technical,
            product_spheres=deduped_products,
            theme_keys=deduped_themes,
            linked_abs_amount=linked_abs_amount,
            best_technical_rank=min(global_rank[key] for key in ranked_technical) if ranked_technical else None,
        )
# END_BLOCK: HORIZON_SPHERE_MAPPING_SERVICE


__all__ = ["HorizonSphereMappingService"]
