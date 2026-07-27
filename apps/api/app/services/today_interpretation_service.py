# ############################################################################
# AI_HEADER: MODULE_TODAY_INTERPRETATION_SERVICE
# ROLE: Z-INTERPRETATION — build backend-owned forecast texts.
# DEPENDENCIES: app.schemas.today, app.services.llm_service, app.core.config
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-INTERPRETATION-SERVICE
# purpose: Build deterministic ConcreteAdviceBlock, DaySummaryBlock, and DayChart
#          with backend-owned forecast texts generated via LLMService.
# owns:
#   - apps/api/app/services/today_interpretation_service.py
# invariants:
#   - concrete advice remains one 12-sphere batch call; the concrete-advice
#     and planet-interpretation batch calls run concurrently inside the
#     bounded LLM phase (10s request-local deadline) via asyncio.gather
#     once both deterministic contexts are built; result application order is
#     unchanged.
#   - concrete advice single-call semantics: exactly ONE external batch
#     call per cold day (inside the concurrent gather). When the result is
#     None, malformed, has a wrong exact key set, or yields fewer than 9
#     valid rows after the claim/row validators, the batch is rejected
#     atomically and every row keeps the honest fallback — no second paid
#     attempt is ever made.
#   - degraded semantics: when the single batch attempt is unacceptable the
#     build NEVER raises and NEVER shows invalid LLM text — all 12 rows keep
#     CONCRETE_ADVICE_FALLBACK_TEXT and the Today endpoint returns 200.
#     A degraded batch is not cacheable (TodayService checks >= 9 non-fallback
#     rows before writing the payload cache).
# END_MODULE_CONTRACT: M-TODAY-INTERPRETATION-SERVICE

# START_MODULE_MAP: M-TODAY-INTERPRETATION-SERVICE
# public_entrypoints:
#   - TodayInterpretationService
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-TODAY-INTERPRETATION-SERVICE

from __future__ import annotations
import asyncio
import re
from datetime import date as Date
from typing import Any

from app.schemas.normalization import AstroSignal
from app.schemas.semantic import SemanticLayer
from app.schemas.today import (
    ConcreteAdviceBlock,
    ConcreteAdviceCounts,
    ConcreteAdviceRow,
    ConcreteAdviceEvidence,
    ConcreteAdviceVerdict,
    ConcreteAdviceConfidence,
    SphereValenceRead,
    DaySummaryBlock,
    DaySummaryFact,
    DayChart,
    PlanetInfluence,
    SphereScore,
    TodayImportantEvent,
)
from app.services.llm_service import LLMService
from app.services.astro_utils import strip_prefix


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

BACKEND_TO_PRODUCT_KEY_MAP = {
    "work_status_achievement": "work",
    "career": "work",
    "career_social_status": "work",
    "public_image": "work",
    "technology_innovation": "work",
    "finance_money": "money",
    "money_security_resources": "money",
    "legal_affairs": "documents",
    "partnerships_contracts": "documents",
    "relationships_partnership": "relationships",
    "relationships": "relationships",
    "home_family_roots": "relationships",
    "home_family": "relationships",
    "inheritance": "relationships",
    "body_energy_health": "sport",
    "daily_routine": "sport",
    "service_routine": "sport",
    "communication_learning": "communication",
    "thinking_speech_learning": "communication",
    "friendship_social": "communication",
    "spirituality_inner_growth": "health",
    "inner_background_unconscious": "health",
    "healing": "health",
    "hidden_matters": "health",
    "career_ambition": "decisions",
    "crisis_transformation": "decisions",
    "crisis_transformation_control": "decisions",
    "philosophy": "decisions",
    "travel_adventure": "travel",
    "long_distance": "travel",
    "meaning_expansion_vector": "travel",
    "creativity_self_expression": "creativity",
    "education": "study",
    "higher_education": "study",
    "joint_finance": "shopping",
    "debts": "shopping",
    "investment": "shopping",
}

CANONICAL_PRODUCT_SPHERES = [
    {"key": "work", "label": "Работа", "icon_name": "briefcase"},
    {"key": "money", "label": "Деньги", "icon_name": "building"},
    {"key": "documents", "label": "Документы", "icon_name": "list-checks"},
    {"key": "relationships", "label": "Отношения", "icon_name": "sparkle"},
    {"key": "sport", "label": "Спорт", "icon_name": "leaf"},
    {"key": "communication", "label": "Общение", "icon_name": "telescope"},
    {"key": "health", "label": "Здоровье", "icon_name": "compass"},
    {"key": "decisions", "label": "Решения", "icon_name": "target"},
    {"key": "travel", "label": "Поездки", "icon_name": "hourglass"},
    {"key": "creativity", "label": "Творчество", "icon_name": "grid"},
    {"key": "study", "label": "Учёба", "icon_name": "layers"},
    {"key": "shopping", "label": "Покупки", "icon_name": "zap"},
]

# Shared honest fallback for concrete advice rows. A payload whose concrete
# advice has fewer than CONCRETE_ADVICE_CACHEABLE_MIN_ROWS non-fallback rows
# is degraded and must never be written to the Today payload cache.
CONCRETE_ADVICE_FALLBACK_TEXT = "Рекомендация временно недоступна."
CONCRETE_ADVICE_CACHEABLE_MIN_ROWS = 9

PLANET_TO_SPHERES_MAP = {
    "Sun": ["work", "creativity", "health"],
    "Moon": ["relationships", "health"],
    "Mercury": ["communication", "study", "documents"],
    "Venus": ["relationships", "creativity", "shopping", "money"],
    "Mars": ["sport", "work"],
    "Jupiter": ["travel", "money", "study"],
    "Saturn": ["decisions", "work", "documents"],
    "Uranus": ["decisions", "creativity"],
    "Neptune": ["health", "creativity"],
    "Pluto": ["decisions"],
}

PLANET_LABELS_RU = {
    "Sun": "Солнце", "Moon": "Луна", "Mercury": "Меркурий", "Venus": "Венера",
    "Mars": "Марс", "Jupiter": "Юпитер", "Saturn": "Сатурн",
    "Uranus": "Уран", "Neptune": "Нептун", "Pluto": "Плутон",
}

ASPECT_LABELS_RU = {
    "conjunction": "соединение", "opposition": "оппозиция",
    "trine": "трин", "square": "квадратура", "sextile": "секстиль",
}

PLANET_STEMS = {
    "Sun": ["солнц", "солнеч"],
    "Moon": ["лун"],
    "Mercury": ["меркур"],
    "Venus": ["венер"],
    "Mars": ["марс"],
    "Jupiter": ["юпитер"],
    "Saturn": ["сатурн"],
    "Uranus": ["уран"],
    "Neptune": ["нептун"],
    "Pluto": ["плутон"],
}

ASPECT_STEMS = {
    "conjunction": ["соедин"],
    "opposition": ["оппозиц"],
    "trine": ["трин", "тригон"],
    "square": ["квадрат", "квадратур"],
    "sextile": ["секстил"],
}

SOFT_ASPECTS = {"trine", "sextile"}
TENSE_ASPECTS = {"square", "opposition"}

def verdict_for_score(score: float) -> ConcreteAdviceVerdict:
    if score >= 6.0:
        return "good"
    if score <= 2.0:
        return "avoid"
    if score <= 3.5:
        return "caution"
    return "neutral"


def aspect_verdict(aspect_type: str | None) -> ConcreteAdviceVerdict:
    aspect = (aspect_type or "").lower()
    if aspect in SOFT_ASPECTS:
        return "good"
    if aspect in TENSE_ASPECTS:
        return "caution"
    return "neutral"


def aspect_supports_verdict(signal: AstroSignal, verdict: ConcreteAdviceVerdict) -> bool:
    aspect = (signal.aspect_type or "").lower()
    if verdict == "good":
        return aspect in SOFT_ASPECTS
    if verdict in ("caution", "avoid"):
        return aspect in TENSE_ASPECTS
    return verdict == "neutral" and aspect not in SOFT_ASPECTS and aspect not in TENSE_ASPECTS


def signal_matches_product_sphere(signal: AstroSignal, key: str) -> bool:
    planet = strip_prefix(signal.planet)
    target = strip_prefix(signal.target_planet) if signal.target_planet else ""
    return (
        key in PLANET_TO_SPHERES_MAP.get(planet, [])
        or bool(target and key in PLANET_TO_SPHERES_MAP.get(target, []))
    )


def signal_rank(signal: AstroSignal) -> tuple[float, float]:
    return (float(signal.daily_salience or signal.strength or 0.0), float(signal.strength or 0.0))


def aspect_evidence(signal: AstroSignal) -> ConcreteAdviceEvidence:
    planet = strip_prefix(signal.planet)
    target = strip_prefix(signal.target_planet) if signal.target_planet else ""

    p_frame = "Transit" if signal.planet.startswith("Transit_") else "natal"
    t_frame = "Transit" if (signal.target_planet and signal.target_planet.startswith("Transit_")) else "natal"
    title = f"{p_frame} {planet} {signal.aspect_type} {t_frame} {target}"

    return ConcreteAdviceEvidence(
        kind="aspect",
        title=title,
        planet=signal.planet,
        target_planet=signal.target_planet,
        aspect_type=signal.aspect_type,
        orb=signal.orb,
        strength=signal.strength,
    )


def planet_in_house_evidence(signal: AstroSignal) -> ConcreteAdviceEvidence:
    planet = strip_prefix(signal.planet)
    return ConcreteAdviceEvidence(
        kind="planet_in_house",
        title=f"{PLANET_LABELS_RU.get(planet, planet)} в {signal.house} доме",
        planet=signal.planet,
        house=signal.house,
        strength=signal.strength,
        sign=signal.sign,
    )


def select_top_sphere_for_day_synthesis(
    rows: list[ConcreteAdviceRow],
    day_status: str,
    valence_assessments: dict[str, Any] | None,
) -> tuple[ConcreteAdviceRow, str]:
    """Select top sphere for day mainAdvice synthesis according to S2 rules:
    - tense-day -> max tension_score (negative_volume);
    - supportive-day -> max support_score (positive_volume);
    - steady-day -> max total score / raw_score;
    - tie -> canonical key ascending order.
    Returns (top_row, top_why_str).
    """
    from app.services.sphere_why_builder import build_sphere_why

    if not rows:
        raise ValueError("rows list cannot be empty")

    canonical_order = {
        "work": 1, "money": 2, "documents": 3, "relationships": 4,
        "sport": 5, "communication": 6, "health": 7, "decisions": 8,
        "travel": 9, "creativity": 10, "study": 11, "shopping": 12,
    }

    def sort_key(row: ConcreteAdviceRow) -> tuple[float, int]:
        ass = valence_assessments.get(row.key) if valence_assessments else None
        if ass:
            if day_status == "tense":
                val = float(getattr(ass, "tension_score", 0.0))
            elif day_status == "supportive":
                val = float(getattr(ass, "support_score", 0.0))
            else:
                val = float(getattr(ass, "support_score", 0.0)) + float(getattr(ass, "tension_score", 0.0))
        else:
            val = float(-row.rank)
        return (-val, canonical_order.get(row.key, 99))

    sorted_rows = sorted(rows, key=sort_key)
    top_row = sorted_rows[0]
    why_facts = build_sphere_why(top_row.evidence)
    why_str = "; ".join(why_facts) if why_facts else ""
    return top_row, why_str


def sphere_score_evidence(score: SphereScore) -> ConcreteAdviceEvidence:
    return ConcreteAdviceEvidence(
        kind="sphere_score",
        title=f"Показатель {score.key}",
        weight=score.score,
        sphere_key=score.key,
    )


def influence_evidence(planet_name: str, influence: PlanetInfluence) -> ConcreteAdviceEvidence:
    return ConcreteAdviceEvidence(
        kind="planet_in_house",
        title=f"Влияние планеты {PLANET_LABELS_RU.get(planet_name, planet_name)}: {influence.score:.2f}",
        planet=planet_name,
        weight=influence.score,
    )


def associated_planets_for_product_sphere(key: str) -> list[str]:
    return [planet for planet, spheres in PLANET_TO_SPHERES_MAP.items() if key in spheres]

def validate_row_text(row: ConcreteAdviceRow, text: str) -> bool:
    t = text.lower()

    # 1. No Latin words
    if re.search(r'[A-Za-z]', text):
        return False

    # 2. No Transit_ or Natal_
    if "transit_" in t or "natal_" in t:
        return False

    # 3. Build allowed sets from evidence only
    allowed_planets = set()
    allowed_aspects = set()
    allowed_houses = set()

    for ev in row.evidence:
        if ev.planet:
            p_clean = strip_prefix(ev.planet)
            allowed_planets.add(p_clean)
        if ev.target_planet:
            tp_clean = strip_prefix(ev.target_planet)
            allowed_planets.add(tp_clean)
        if ev.aspect_type:
            allowed_aspects.add(ev.aspect_type.lower())
        if ev.title:
            # Also check the title for planet names
            for p_en, p_ru in PLANET_LABELS_RU.items():
                if p_ru.lower() in ev.title.lower():
                    allowed_planets.add(p_en)
            match = re.search(r'\b(\d+)\s+дом', ev.title.lower())
            if match:
                allowed_houses.add(int(match.group(1)))

    # Check for unauthorized planets
    for p_name, stems in PLANET_STEMS.items():
        if any(stem in t for stem in stems):
            if p_name not in allowed_planets:
                return False

    # Check for unauthorized aspects
    for a_name, stems in ASPECT_STEMS.items():
        if any(stem in t for stem in stems):
            if a_name not in allowed_aspects:
                return False

    # Check for unauthorized houses
    if "дом" in t:
        house_matches = re.findall(r'\b(\d+)\s+дом', t)
        if not house_matches:
            if not allowed_houses:
                return False
        else:
            for h_str in house_matches:
                h_num = int(h_str)
                if h_num not in allowed_houses:
                    return False

    # 4. Advice consistency guard (prevents active advice contradicting avoid)
    if row.verdict == "avoid":
        mitigation_markers = ["если нужно", "только", "короткий формат", "короткий, спокойный", "избегай", "не ", "не стоит", "отложи", "огранич"]
        if any(marker in t for marker in mitigation_markers):
            pass
        else:
            prohibited = [
                "начни", "начинать", "начинай",
                "покупай", "покупать", "покупка",
                "инвестировать", "инвестируй", "инвестиции",
                "договариваться", "договаривайся", "договор",
                "общаться", "общайся", "общение",
                "активно", "активность",
                "инициировать", "инициируй",
            ]
            for stem in prohibited:
                if stem in t:
                    return False

    return True

class TodayInterpretationService:
    async def build(
        self,
        *,
        target_date: Date,
        day_status: str,
        scoring_result: dict,
        signals: list[AstroSignal],
        semantic_layer: SemanticLayer,
        day_chart: DayChart | None,
        planet_influences: list[PlanetInfluence],
        sphere_scores: list[SphereScore],
        important_items: list[TodayImportantEvent],
        lunar: dict | None = None,
        activation_layer: Any | None = None,
        scoring_v2_result: Any | None = None,
        valence_assessments: dict[str, Any] | None = None,
        selected_horizons: dict | None = None,
        force_no_llm: bool = False,
    ) -> tuple[ConcreteAdviceBlock, DaySummaryBlock, DayChart | None]:
        # force_no_llm: the deadline fallback path — the same deterministic
        # computation with every LLM call disabled (advice fallback rows,
        # planet interpretation fallback). Never makes external calls.
        llm_service = LLMService()

        # 1. Deterministic Concrete Advice builder
        rows: list[ConcreteAdviceRow] = []
        advice_contexts: list[dict] = []

        for rank, canon in enumerate(CANONICAL_PRODUCT_SPHERES, 1):
            key = canon["key"]
            label = canon["label"]
            icon_name = canon["icon_name"]

            matching_scores = [s for s in sphere_scores if BACKEND_TO_PRODUCT_KEY_MAP.get(s.key) == key]
            evidence_list: list[ConcreteAdviceEvidence] = []
            verdict: ConcreteAdviceVerdict = "neutral"
            confidence: ConcreteAdviceConfidence = "low"
            best_score: SphereScore | None = None

            if matching_scores:
                def sort_key(s: SphereScore):
                    v = verdict_for_score(s.score)
                    avoid_caution_val = 0 if v in ("avoid", "caution") else 1
                    good_val = 0 if v == "good" else 1
                    return (avoid_caution_val, good_val, s.rank)

                matching_scores.sort(key=sort_key)
                best_score = matching_scores[0]
                verdict = verdict_for_score(best_score.score)
                confidence = "high" if verdict in ("good", "avoid", "caution") else "medium"

            planets_for_sphere = associated_planets_for_product_sphere(key)
            aspects = sorted(
                [s for s in signals if s.type == "aspect" and signal_matches_product_sphere(s, key)],
                key=signal_rank,
                reverse=True,
            )
            houses = sorted(
                [s for s in signals if s.type == "planet_in_house" and signal_matches_product_sphere(s, key)],
                key=signal_rank,
                reverse=True,
            )

            if best_score is not None:
                if verdict in ("good", "caution", "avoid"):
                    compatible_aspects = [s for s in aspects if aspect_supports_verdict(s, verdict)]
                    if compatible_aspects:
                        evidence_list.append(aspect_evidence(compatible_aspects[0]))
                    elif houses:
                        evidence_list.append(planet_in_house_evidence(houses[0]))
                    else:
                        evidence_list.append(sphere_score_evidence(best_score))
                else:
                    neutral_aspects = [s for s in aspects if aspect_verdict(s.aspect_type) == "neutral"]
                    if neutral_aspects:
                        evidence_list.append(aspect_evidence(neutral_aspects[0]))
                    elif houses:
                        evidence_list.append(planet_in_house_evidence(houses[0]))
                    else:
                        evidence_list.append(sphere_score_evidence(best_score))
            else:
                if aspects:
                    selected_aspect = aspects[0]
                    verdict = aspect_verdict(selected_aspect.aspect_type)
                    confidence = "medium" if verdict in ("good", "caution", "avoid") else "low"
                    evidence_list.append(aspect_evidence(selected_aspect))
                elif houses:
                    verdict = "neutral"
                    confidence = "low"
                    evidence_list.append(planet_in_house_evidence(houses[0]))
                else:
                    for planet_name in planets_for_sphere:
                        influence = next(
                            (
                                pi for pi in planet_influences
                                if pi.name == planet_name or PLANET_LABELS_RU.get(pi.name) == planet_name
                            ),
                            None,
                        )
                        if influence:
                            verdict = "neutral"
                            confidence = "low"
                            evidence_list.append(influence_evidence(planet_name, influence))
                            break

            if not evidence_list:
                if best_score is not None:
                    evidence_list.append(sphere_score_evidence(best_score))
                else:
                    verdict = "neutral"
                    confidence = "low"
                    evidence_list.append(
                        ConcreteAdviceEvidence(
                            kind="day_status",
                            title=f"Общий статус дня: {day_status}",
                        )
                    )

            if activation_layer:
                from app.services.semantic_v2_service import SemanticV2Service
                sem_service = SemanticV2Service()
                backend_keys = [bk for bk, pk in BACKEND_TO_PRODUCT_KEY_MAP.items() if pk == key]
                for bk in backend_keys:
                    v2_evidences = sem_service.get_evidence_for_sphere(
                        backend_sphere_key=bk,
                        activation_layer=activation_layer,
                        scoring_result=scoring_v2_result,
                    )
                    evidence_list.extend(v2_evidences)

            # LLM projection ONLY: at most 3 unique (kind, title) evidence
            # entries per product sphere, deterministic first-in-relevance
            # order. The full row.evidence above stays untouched — claim/row
            # validators and the wire payload keep the complete set.
            projected_evidence = []
            seen_evidence_keys = set()
            for ev in evidence_list:
                ev_key = (ev.kind, ev.title)
                if ev_key in seen_evidence_keys:
                    continue
                seen_evidence_keys.add(ev_key)
                projected_evidence.append(ev.model_dump())
                if len(projected_evidence) >= 3:
                    break

            assessment_read: SphereValenceRead | None = None
            if valence_assessments and key in valence_assessments:
                ass = valence_assessments[key]
                verdict = ass.verdict
                confidence = ass.confidence
                assessment_read = SphereValenceRead(sphere=key, assessment=ass)

            # Context for LLM wording
            advice_contexts.append({
                "key": key,
                "label": label,
                "verdict": verdict,
                "evidence": projected_evidence,
            })

            rows.append(
                ConcreteAdviceRow(
                    key=key,
                    label=label,
                    icon_name=icon_name,
                    rank=rank,
                    verdict=verdict,
                    confidence=confidence,
                    text=CONCRETE_ADVICE_FALLBACK_TEXT,
                    evidence=evidence_list,
                    assessment=assessment_read,
                )
            )

        # Check if we have LLM keys configured
        llm_texts = None
        from app.core.config import settings
        has_llm_keys = (not force_no_llm) and any(
            bool((key or "").strip())
            for key in (
                settings.openrouter_api_key,
                settings.anthropic_api_key,
                getattr(settings, "deepseek_api_key", ""),
            )
        )

        # Deterministic planet-interpretation context (built once, before the
        # concurrent LLM calls; application of results stays below unchanged).
        planets_context: list[dict] = []
        has_planet_context = bool(day_chart and day_chart.transit_planets)
        if day_chart and day_chart.transit_planets:
            for p in day_chart.transit_planets:
                p_aspects = []
                for a in day_chart.aspects:
                    if a.planet == p.name or a.target_planet == p.name:
                        asp_lbl = ASPECT_LABELS_RU.get(a.aspect_type, a.aspect_type)
                        other_p = a.target_planet if a.planet == p.name else a.planet
                        other_lbl = PLANET_LABELS_RU.get(other_p, other_p)
                        p_aspects.append(f"{asp_lbl} с {other_lbl}")
                planets_context.append({
                    "name": p.name,
                    "sign": p.sign,
                    "house": p.house,
                    "aspects": p_aspects,
                })

        applied_main_advice: str | None = None

        # Concurrent independent batch calls: one 12-sphere concrete advice
        # batch and one planet interpretations batch (never split per-row).
        llm_texts = None
        evidence_packet = None
        if has_llm_keys:
            if activation_layer:
                from app.services.semantic_v2_service import SemanticV2Service
                evidence_packet = SemanticV2Service().build_llm_evidence_packet(
                    day_status=day_status,
                    activation_layer=activation_layer,
                    scoring_result=scoring_v2_result,
                    contexts=advice_contexts,
                )

            top_row, top_why = select_top_sphere_for_day_synthesis(rows, day_status, valence_assessments)
            fast_horizon_title = ""
            if selected_horizons and "fast" in selected_horizons:
                fast_h = selected_horizons["fast"]
                fast_horizon_title = getattr(fast_h, "title", "") or (fast_h.get("title") if isinstance(fast_h, dict) else "")

            day_facts = {
                "status": day_status,
                "top_sphere_key": top_row.key,
                "top_sphere_label": top_row.label,
                "top_sphere_why": top_why,
                "fast_horizon_title": fast_horizon_title,
            }

            llm_texts, llm_interpretations = await asyncio.gather(
                llm_service.generate_concrete_advice(advice_contexts, evidence_packet=evidence_packet, day_facts=day_facts),
                llm_service.generate_planet_interpretations(planets_context) if has_planet_context else asyncio.sleep(0, result=None),
            )
        else:
            llm_interpretations = None

        expected_sphere_keys = {c["key"] for c in CANONICAL_PRODUCT_SPHERES}
        allowed_candidate_keys = expected_sphere_keys | {"day_main"}

        def _apply_advice_attempt(candidate: dict | None) -> int:
            nonlocal applied_main_advice
            from app.core.logging import log_event
            if not candidate or not isinstance(candidate, dict):
                log_event("llm.response_rejected", level="warning", payload={"reason": "attempt_rejected"})
                return 0
            candidate_keys = set(candidate.keys())
            if not (expected_sphere_keys <= candidate_keys <= allowed_candidate_keys):
                log_event("llm.response_rejected", level="warning", payload={"reason": "attempt_rejected"})
                return 0

            from app.schemas.today import ConcreteAdviceDetails
            from app.services.llm_claim_validator import LLMClaimValidator
            validator = LLMClaimValidator()

            # Parse and validate day_main synthesis
            day_main_raw = candidate.get("day_main")
            sanitized_main, main_reason = validator.check_day_main_safety(
                day_main_raw if isinstance(day_main_raw, str) else None
            )
            if sanitized_main:
                applied_main_advice = sanitized_main
            else:
                log_event(
                    "llm.response_rejected",
                    level="warning",
                    payload={"row_key": "day_main", "reason": main_reason or "validation_failed"},
                )
                applied_main_advice = None

            staged: list[tuple[ConcreteAdviceRow, str, ConcreteAdviceDetails | None]] = []

            for row in rows:
                entry = candidate.get(row.key)
                if not entry:
                    log_event(
                        "llm.response_rejected",
                        level="warning",
                        payload={"row_key": row.key, "reason": "empty"},
                    )
                    continue

                if isinstance(entry, str) and entry.strip():
                    text = entry.strip()
                    sanitized_text, reason = validator.check_concrete_advice_text_safety(
                        row_key=row.key,
                        verdict=row.verdict,
                        text=text,
                        evidence=row.evidence,
                    )
                    if sanitized_text and validate_row_text(row, sanitized_text):
                        staged.append((row, sanitized_text.strip(), None))
                    else:
                        reject_reason = reason or "validation_failed"
                        log_event(
                            "llm.response_rejected",
                            level="warning",
                            payload={"row_key": row.key, "reason": reject_reason},
                        )
                elif isinstance(entry, dict):
                    sanitized, reason = validator.check_concrete_advice_details_safety(
                        row_key=row.key,
                        verdict=row.verdict,
                        details=entry,
                        evidence=row.evidence,
                    )
                    if sanitized:
                        advice_text = sanitized["advice"]
                        if validate_row_text(row, advice_text):
                            from app.services.sphere_why_builder import build_sphere_why
                            deterministic_why = build_sphere_why(row.evidence)
                            details_obj = ConcreteAdviceDetails(
                                story=sanitized["story"],
                                why=deterministic_why,
                                advice=advice_text,
                            )
                            staged.append((row, advice_text, details_obj))
                        else:
                            log_event(
                                "llm.response_rejected",
                                level="warning",
                                payload={"row_key": row.key, "reason": "validation_failed"},
                            )
                    else:
                        reject_reason = reason or "validation_failed"
                        log_event(
                            "llm.response_rejected",
                            level="warning",
                            payload={"row_key": row.key, "reason": reject_reason},
                        )
                else:
                    log_event(
                        "llm.response_rejected",
                        level="warning",
                        payload={"row_key": row.key, "reason": "parse"},
                    )

            if len(staged) < 9:
                log_event("llm.response_rejected", level="warning", payload={"reason": "attempt_rejected"})
                return 0

            from app.services.sphere_why_builder import build_sphere_why_items

            staged_keys = {row.key for row, _, _ in staged}
            for row in rows:
                if row.key not in staged_keys:
                    row.text = CONCRETE_ADVICE_FALLBACK_TEXT
                    row.details = None

            for row, text, details_obj in staged:
                row.text = text
                row.details = details_obj

            # Global cross-sphere deduplication of why lines (highest strength wins)
            candidates_by_sphere = {
                row.key: build_sphere_why_items(row.evidence)
                for row, _, d in staged if d is not None
            }
            max_strength_by_pair: dict[tuple[str, str], tuple[str, float]] = {}
            for sphere_key, items in candidates_by_sphere.items():
                for item in items:
                    pair = item.pair_key
                    if pair not in max_strength_by_pair or item.strength > max_strength_by_pair[pair][1]:
                        max_strength_by_pair[pair] = (sphere_key, item.strength)

            for row, _, d in staged:
                if d is None:
                    continue
                sphere_items = candidates_by_sphere.get(row.key, [])
                assigned_lines: list[str] = []
                for item in sphere_items:
                    if len(assigned_lines) >= 2:
                        break
                    winning_sphere, _ = max_strength_by_pair.get(item.pair_key, (row.key, 0.0))
                    if winning_sphere == row.key:
                        assigned_lines.append(item.line)
                d.why = assigned_lines

            return len(staged)

        if has_llm_keys:
            from app.core.logging import log_block, log_event
            # Exactly ONE external advice call per cold day (already made in
            # the concurrent gather above — no second paid attempt). A
            # rejected batch keeps the honest fallback on all 12 rows, and
            # the degraded payload is never cached (TodayService requires
            # >= 9 non-fallback rows before writing the payload cache).
            valid_llm_count = _apply_advice_attempt(llm_texts)
            if valid_llm_count < 9:
                with log_block(slice="W-5.1", module="M-TODAY-INTERPRETATION-SERVICE", block="CONCRETE_ADVICE_FALLBACK"):
                    log_event(
                        "llm.response_rejected",
                        level="warn",
                        msg="[LLM] concrete advice degraded: all rows keep fallback text",
                        payload={"reason": "schema_invalid"},
                    )
        # No LLM keys: rows keep the honest fallback by construction.

        # Compute row counts
        good_count = sum(1 for r in rows if r.verdict == "good")
        caution_count = sum(1 for r in rows if r.verdict == "caution")
        avoid_count = sum(1 for r in rows if r.verdict == "avoid")
        neutral_count = sum(1 for r in rows if r.verdict == "neutral")

        counts = ConcreteAdviceCounts(
            good=good_count,
            caution=caution_count,
            avoid=avoid_count,
            neutral=neutral_count,
        )
        concrete_advice = ConcreteAdviceBlock(rows=rows, counts=counts)

        # 2. Day Summary Block builder
        status_label_map = {
            "steady": "Ровный день",
            "supportive": "Поддерживающий день",
            "tense": "Напряжённый день",
        }
        status_label = status_label_map.get(day_status, "Ровный день")

        status_line = semantic_layer.day_theme if semantic_layer else "Сводка временно недоступна."
        if semantic_layer and semantic_layer.day_theme:
            status_line = semantic_layer.day_theme

        summary_facts: list[DaySummaryFact] = []
        # Add Top Planet fact
        if planet_influences:
            top_p = sorted(planet_influences, key=lambda x: x.rank)[0]
            p_clean = strip_prefix(top_p.name)
            summary_facts.append(
                DaySummaryFact(
                    kind="top_planet",
                    icon_name=p_clean,
                    title=f"Влияние {PLANET_LABELS_RU.get(p_clean, p_clean)}",
                    summary=None,
                )
            )

        # Compute lunar phase dynamically from Sun/Moon longitudes in day_chart
        lunar_phase_title = None
        lunar_phase_summary = None
        if day_chart:
            sun = next((p for p in day_chart.transit_planets if p.name == "Sun"), None)
            moon = next((p for p in day_chart.transit_planets if p.name == "Moon"), None)
            if sun and moon:
                from math import radians, cos
                d = (moon.longitude - sun.longitude) % 360
                illumination = (1 - cos(radians(d))) / 2 * 100

                if d < 22.5 or d > 337.5:
                    lunar_phase_title = "Новолуние"
                    lunar_phase_summary = "новолуние"
                elif d >= 157.5 and d < 202.5:
                    lunar_phase_title = "Полнолуние"
                    lunar_phase_summary = "полнолуние"
                elif d >= 22.5 and d < 157.5:
                    lunar_phase_title = f"Растущая Луна {int(round(illumination))}%"
                    lunar_phase_summary = "растущая фаза"
                else:
                    lunar_phase_title = f"Убывающая Луна {int(round(illumination))}%"
                    lunar_phase_summary = "убывающая фаза"

        if lunar_phase_title:
            summary_facts.append(
                DaySummaryFact(
                    kind="lunar_phase",
                    icon_name="moon",
                    title=lunar_phase_title,
                    summary=lunar_phase_summary,
                )
            )

        # Check Void Moon from important_items
        is_void_moon = any(item.kind == "void_moon" for item in important_items)
        if is_void_moon:
            summary_facts.append(
                DaySummaryFact(
                    kind="void_moon",
                    icon_name="void_moon",
                    title="Луна без курса",
                    summary="период затишья",
                )
            )

        # Add Top Flag fact (Top daily aspect)
        top_aspect = next((s for s in scoring_result.get("top_signals", []) if _get_field(s, "type") == "aspect"), None)
        if top_aspect:
            p_clean = strip_prefix(_get_field(top_aspect, "planet") or "")
            tp_raw = _get_field(top_aspect, "target_planet") or ""
            tp_clean = strip_prefix(tp_raw) if tp_raw else ""
            asp_type = _get_field(top_aspect, "aspect_type") or ""
            summary_fact_title = f"{PLANET_LABELS_RU.get(p_clean, p_clean)} {ASPECT_LABELS_RU.get(asp_type, asp_type)} {PLANET_LABELS_RU.get(tp_clean, tp_clean)}"

            aspect_type_lower = asp_type.lower()
            if aspect_type_lower in TENSE_ASPECTS:
                summary_fact_desc = "напряжённый аспект"
            elif aspect_type_lower in SOFT_ASPECTS:
                summary_fact_desc = "поддерживающий аспект"
            else:
                summary_fact_desc = "транзитный аспект"

            summary_facts.append(
                DaySummaryFact(
                    kind="top_flag",
                    icon_name="flag",
                    title=summary_fact_title,
                    summary=summary_fact_desc,
                )
            )

        day_summary = DaySummaryBlock(
            status_label=status_label,
            status_line=status_line,
            facts=summary_facts,
            main_advice=applied_main_advice,
        )

        # 3. Planet Interpretations (apply the concurrently gathered result;
        # context was built above before the batch call)
        if day_chart and day_chart.transit_planets:
            if llm_interpretations and isinstance(llm_interpretations, dict):
                for p in day_chart.transit_planets:
                    text = llm_interpretations.get(p.name)
                    if text and isinstance(text, str) and text.strip():
                        if not re.search(r'[A-Za-z]', text):
                            p.interpretation = text.strip()
                    if not p.interpretation:
                        p.interpretation = "Интерпретация временно недоступна."
            else:
                for p in day_chart.transit_planets:
                    p.interpretation = "Интерпретация временно недоступна."

        return concrete_advice, day_summary, day_chart
