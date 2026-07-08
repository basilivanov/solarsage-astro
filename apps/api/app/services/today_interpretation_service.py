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
# END_MODULE_CONTRACT: M-TODAY-INTERPRETATION-SERVICE

from __future__ import annotations
import re
from datetime import date as Date

from app.schemas.normalization import AstroSignal
from app.schemas.semantic import SemanticLayer
from app.schemas.today import (
    ConcreteAdviceBlock,
    ConcreteAdviceCounts,
    ConcreteAdviceRow,
    ConcreteAdviceEvidence,
    ConcreteAdviceVerdict,
    ConcreteAdviceConfidence,
    ConcreteAdviceEvidenceKind,
    DaySummaryBlock,
    DaySummaryFact,
    DaySummaryFactKind,
    DayChart,
    DayChartTransitPlanet,
    PlanetInfluence,
    SphereScore,
    TodayImportantEvent,
)
from app.services.llm_service import LLMService
from app.services.astro_utils import strip_prefix

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

def verdict_for_score(score: float) -> ConcreteAdviceVerdict:
    if score >= 6.0:
        return "good"
    if score <= 2.0:
        return "avoid"
    if score <= 3.5:
        return "caution"
    return "neutral"

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
            allowed_planets.add(strip_prefix(ev.planet))
        if ev.target_planet:
            allowed_planets.add(strip_prefix(ev.target_planet))
        if ev.aspect_type:
            allowed_aspects.add(ev.aspect_type.lower())
        if ev.title:
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
            # Word "дом" is mentioned but no specific house number was parsed.
            # If allowed_houses is empty, this general mention is not allowed.
            if not allowed_houses:
                return False
        else:
            for h_str in house_matches:
                h_num = int(h_str)
                if h_num not in allowed_houses:
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
    ) -> tuple[ConcreteAdviceBlock, DaySummaryBlock, DayChart | None]:
        llm_service = LLMService()

        # 1. Deterministic Concrete Advice builder
        rows: list[ConcreteAdviceRow] = []
        advice_contexts: list[dict] = []

        # Find aspect and planet verdicts from signals
        planet_aspect_verdicts: dict[str, str] = {}
        for s in signals:
            if s.type == "aspect" and s.aspect_type and s.target_planet:
                t = s.aspect_type.lower()
                is_good = t in ("trine", "sextile")
                is_bad = t in ("square", "opposition")
                verdict = "good" if is_good else ("caution" if is_bad else "neutral")
                planet_aspect_verdicts[strip_prefix(s.planet)] = verdict
                planet_aspect_verdicts[strip_prefix(s.target_planet)] = verdict

        for rank, canon in enumerate(CANONICAL_PRODUCT_SPHERES, 1):
            key = canon["key"]
            label = canon["label"]
            icon_name = canon["icon_name"]

            matching_scores = [s for s in sphere_scores if BACKEND_TO_PRODUCT_KEY_MAP.get(s.key) == key]
            evidence_list: list[ConcreteAdviceEvidence] = []
            verdict: ConcreteAdviceVerdict = "neutral"
            confidence: ConcreteAdviceConfidence = "low"

            if matching_scores:
                # Deterministic selection: caution/avoid first, then good, then best rank
                def sort_key(s: SphereScore):
                    v = verdict_for_score(s.score)
                    avoid_caution_val = 0 if v in ("avoid", "caution") else 1
                    good_val = 0 if v == "good" else 1
                    return (avoid_caution_val, good_val, s.rank)

                matching_scores.sort(key=sort_key)
                best_score = matching_scores[0]
                verdict = verdict_for_score(best_score.score)
                confidence = "high" if verdict in ("good", "avoid", "caution") else "medium"
                evidence_list.append(
                    ConcreteAdviceEvidence(
                        kind="sphere_score",
                        title=f"Скор сферы {best_score.key}: {best_score.score:.2f}",
                        weight=best_score.score,
                        sphere_key=best_score.key,
                    )
                )
            else:
                # Top signals & influences check
                found_signal = False
                for planet_name, spheres in PLANET_TO_SPHERES_MAP.items():
                    if key in spheres:
                        # TopFlags aspect check
                        if planet_name in planet_aspect_verdicts:
                            verdict = planet_aspect_verdicts[planet_name]
                            confidence = "medium"
                            evidence_list.append(
                                ConcreteAdviceEvidence(
                                    kind="aspect",
                                    title=f"Аспект планеты {PLANET_LABELS_RU.get(planet_name, planet_name)}",
                                    planet=planet_name,
                                )
                            )
                            found_signal = True
                            break

                        # PlanetInfluence check
                        influence = next((pi for pi in planet_influences if pi.name == planet_name or PLANET_LABELS_RU.get(pi.name) == planet_name), None)
                        if influence:
                            if influence.score >= 6.0:
                                verdict = "good"
                                confidence = "medium"
                            elif influence.score <= 3.0:
                                verdict = "caution"
                                confidence = "medium"
                            else:
                                verdict = "neutral"
                                confidence = "low"
                            evidence_list.append(
                                ConcreteAdviceEvidence(
                                    kind="planet_in_house",
                                    title=f"Влияние планеты {PLANET_LABELS_RU.get(planet_name, planet_name)}: {influence.score:.2f}",
                                    planet=planet_name,
                                    weight=influence.score,
                                )
                            )
                            found_signal = True
                            break

                if not found_signal:
                    # Fallback to day_status
                    if day_status == "supportive":
                        verdict = "good"
                    elif day_status == "tense":
                        verdict = "caution"
                    else:
                        verdict = "neutral"
                    confidence = "low"
                    evidence_list.append(
                        ConcreteAdviceEvidence(
                            kind="day_status",
                            title=f"Общий статус дня: {day_status}",
                        )
                    )

            # Context for LLM wording
            advice_contexts.append({
                "key": key,
                "label": label,
                "verdict": verdict,
                "evidence": [ev.model_dump() for ev in evidence_list]
            })

            rows.append(
                ConcreteAdviceRow(
                    key=key,
                    label=label,
                    icon_name=icon_name,
                    rank=rank,
                    verdict=verdict,
                    confidence=confidence,
                    text="Рекомендация временно недоступна.",
                    evidence=evidence_list,
                )
            )

        # Check if we have LLM keys configured (no test branching)
        llm_texts = None
        from app.core.config import settings

        def is_real_key(key: str | None) -> bool:
            if not key:
                return False
            k = key.strip().lower()
            return len(k) > 0 and "mock" not in k and "test" not in k

        has_llm_keys = (
            is_real_key(settings.openrouter_api_key)
            or is_real_key(settings.anthropic_api_key)
            or is_real_key(getattr(settings, "deepseek_api_key", None))
        )

        if has_llm_keys:
            llm_texts = await llm_service.generate_concrete_advice(advice_contexts)

        valid_llm_count = 0
        if llm_texts and isinstance(llm_texts, dict):
            # Check exactly canonical 12 keys
            expected_keys = {c["key"] for c in CANONICAL_PRODUCT_SPHERES}
            actual_keys = set(llm_texts.keys())

            if expected_keys == actual_keys:
                for row in rows:
                    text = llm_texts.get(row.key)
                    if text and isinstance(text, str) and text.strip():
                        if validate_row_text(row, text):
                            row.text = text.strip()
                            valid_llm_count += 1

        # Fallback check: if fewer than 9 rows are valid, raise in prod/dev with keys
        if valid_llm_count < 9:
            if has_llm_keys:
                raise ValueError(f"LLM generated only {valid_llm_count}/12 valid recommendations.")
            else:
                # Fallback on LLM failure / missing keys
                for row in rows:
                    row.text = "Рекомендация временно недоступна."

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
                    summary="особая тема дня",
                )
            )

        # Compute lunar phase dynamically from Sun/Moon longitudes in day_chart
        lunar_phase_title = None
        lunar_phase_summary = None
        if day_chart:
            sun = next((p for p in day_chart.transit_planets if p.name == "Sun"), None)
            moon = next((p for p in day_chart.transit_planets if p.name == "Moon"), None)
            if sun and moon:
                d = (moon.longitude - sun.longitude) % 360
                illumination = abs(180 - abs(180 - d)) / 180.0 * 100.0

                if d < 22.5 or d > 337.5:
                    lunar_phase_title = "Новолуние"
                    lunar_phase_summary = "новолуние"
                elif d >= 157.5 and d < 202.5:
                    lunar_phase_title = "Полнолуние"
                    lunar_phase_summary = "полнолуние"
                elif d >= 22.5 and d < 157.5:
                    lunar_phase_title = f"Растущая Луна {int(illumination)}%"
                    lunar_phase_summary = "растущая фаза"
                else:
                    lunar_phase_title = f"Убывающая Луна {int(illumination)}%"
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

        # Add Top Flag fact
        if signals:
            top_sig = signals[0]
            p_clean = strip_prefix(top_sig.planet)
            tp_clean = strip_prefix(top_sig.target_planet) if top_sig.target_planet else ""
            summary_facts.append(
                DaySummaryFact(
                    kind="top_flag",
                    icon_name="flag",
                    title=f"Аспект: {PLANET_LABELS_RU.get(p_clean, p_clean)} {ASPECT_LABELS_RU.get(top_sig.aspect_type, top_sig.aspect_type)} {PLANET_LABELS_RU.get(tp_clean, tp_clean)}" if top_sig.type == "aspect" else "Аспект дня",
                    summary="транзитный аспект",
                )
            )

        day_summary = DaySummaryBlock(
            status_label=status_label,
            status_line=status_line,
            facts=summary_facts,
        )

        # 3. Planet Interpretations
        if day_chart and day_chart.transit_planets:
            planets_context = []
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

            llm_interpretations = None
            if has_llm_keys:
                llm_interpretations = await llm_service.generate_planet_interpretations(planets_context)

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
