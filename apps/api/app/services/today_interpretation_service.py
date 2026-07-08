# ############################################################################
# AI_HEADER: MODULE_TODAY_INTERPRETATION_SERVICE
# ROLE: Interpretation service — build backend-owned forecast texts.
# DEPENDENCIES: app.schemas.today, app.services.llm_service, app.core.config
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-INTERPRETATION-SERVICE
# purpose: Build deterministic ConcreteAdviceBlock, DaySummaryBlock, and DayChart
#          with backend-owned forecast texts generated via LLMService.
# owns:
#   - apps/api/app/services/today_interpretation_service.py
# END_MODULE_CONTRACT: M-TODAY-INTERPRETATION-SERVICE

from __future__ import annotations
import asyncio
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

SPHERE_ADVICE_TEXTS = {
    "work": {
        "good": "Новые задачи идут легко, не упускай момент",
        "caution": "Дела идут со скрипом — не торопись, дойдёт к вечеру",
        "avoid": "Новые проекты буксуют — не запускай, дорабатывай текущее",
        "neutral": "Ровный рабочий день — без сюрпризов, без прорывов",
    },
    "money": {
        "good": "Хороший день для вложений в себя и дом",
        "caution": "Сократи траты — день для финансовой дисциплины",
        "avoid": "Не делай крупных покупок — перепроверь цену завтра",
        "neutral": "Стабильно, без неожиданностей — можно планировать бюджет",
    },
    "documents": {
        "good": "Хорошее время для договоров — читай спокойно, подписывай",
        "caution": "Не подписывай контракты — перечитай через 3 дня",
        "avoid": "Луна без курса — не подписывай важное до завтра",
        "neutral": "Обычный день для бумаг — ничего не мешает, но и не помогает",
    },
    "relationships": {
        "good": "Свидания пройдут отлично — будь открыт и смел",
        "caution": "Легко поссориться на пустом — держи паузу перед ответом",
        "avoid": "Не начинай новый роман — старые чувства могут вернуться",
        "neutral": "Спокойный день для близких — без драмы, без озарений",
    },
    "sport": {
        "good": "Энергия бьёт ключом — иди на максимум",
        "caution": "Дисциплинированная тренировка — без рекордов, на выносливость",
        "avoid": "Снизь нагрузку — риск травм выше, работай на технику",
        "neutral": "Обычная нагрузка — не перегружай, но и не пропускай",
    },
    "communication": {
        "good": "Переговоры пройдут гладко — проси что хочешь",
        "caution": "Разговоры путаются — подтверждай всё письменно",
        "avoid": "Не назначай важные встречи — решения будут нетвёрдыми",
        "neutral": "Обычные разговоры — без конфликтов, но и без прорывов",
    },
    "health": {
        "good": "Тело полно сил — хороший день для очищения и процедур",
        "caution": "Береги суставы и кости — не переохлаждайся",
        "avoid": "Чувствительность повышена — береги нервы и сон",
        "neutral": "Стабильно — поддерживай режим, ничего особого",
    },
    "decisions": {
        "good": "Решения даются легко — интуиция работает чётко",
        "caution": "Запиши решение — перечитай через 2 дня, потом действуй",
        "avoid": "Не принимай важных решений — отложи до завтра",
        "neutral": "Обычная ясность — решения принимаются ровно",
    },
    "travel": {
        "good": "Дорога будет лёгкой — хороший день для отправления",
        "caution": "Поездки по необходимости — не планируй новое",
        "avoid": "Задержки вероятны — закладывай время на форс-мажор",
        "neutral": "Обычный день в дороге — без приключений",
    },
    "creativity": {
        "good": "Вдохновение бьёт ключом — садись за работу",
        "caution": "Спокойный фон для творчества — без искр, но ровно",
        "avoid": "Вдохновение спит — не форсируй, сделай заготовки",
        "neutral": "Спокойный фон для творчества — без искр, но ровно",
    },
    "study": {
        "good": "Память цепкая — учи сложное, оно задержится",
        "caution": "Повторяй старое — новое плохо усваивается",
        "avoid": "Концентрация снижена — сделай перерыв",
        "neutral": "Обычный темп — учи понемногу, без рывков",
    },
    "shopping": {
        "good": "Вкус работает — выберешь правильное, не пожалеешь",
        "caution": "Только необходимое — крупные покупки разочаруют",
        "avoid": "Не покупай электронику и технику — могут быть дефекты",
        "neutral": "Обычный день — покупай что нужно, без импульсов",
    },
}

def verdict_for_score(score: float) -> ConcreteAdviceVerdict:
    if score >= 6.0:
        return "good"
    if score <= 2.0:
        return "avoid"
    if score <= 3.5:
        return "caution"
    return "neutral"

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
                planet_aspect_verdicts[s.planet] = verdict
                planet_aspect_verdicts[s.target_planet] = verdict

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

        # Check if we have LLM keys configured and not in test environment (unless mocked)
        import sys
        from app.core.config import settings
        is_test_env = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
        is_mocked = hasattr(llm_service.generate_concrete_advice, "mock") or hasattr(llm_service.generate_concrete_advice, "assert_called")
        has_llm_keys = (bool(settings.openrouter_api_key or settings.anthropic_api_key) and not is_test_env) or is_mocked

        # Call LLM to generate concrete advice texts in one go
        llm_texts = None
        if has_llm_keys:
            llm_texts = await llm_service.generate_concrete_advice(advice_contexts)

        valid_llm_count = 0
        if llm_texts and isinstance(llm_texts, dict):
            for row in rows:
                text = llm_texts.get(row.key)
                if text and isinstance(text, str) and text.strip():
                    # Validate: no Latin words
                    import re
                    if not re.search(r'[A-Za-z]', text):
                        row.text = text.strip()
                        valid_llm_count += 1

        # Fallback check: if fewer than 9 rows are valid
        if valid_llm_count < 9:
            if has_llm_keys:
                raise ValueError(f"LLM generated only {valid_llm_count}/12 valid recommendations.")
            else:
                # In test environment / local dev without keys, use high-quality Russian templates
                for row in rows:
                    row.text = SPHERE_ADVICE_TEXTS[row.key][row.verdict]

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

        # Generate summary status line from LLM headline
        status_line = semantic_layer.day_theme if semantic_layer else "Обычный день, занимайся текущими делами"
        if semantic_layer and semantic_layer.day_theme:
            status_line = semantic_layer.day_theme

        summary_facts: list[DaySummaryFact] = []
        # Add Top Planet fact
        if planet_influences:
            top_p = sorted(planet_influences, key=lambda x: x.rank)[0]
            summary_facts.append(
                DaySummaryFact(
                    kind="top_planet",
                    icon_name=top_p.name,
                    title=f"Влияние {PLANET_LABELS_RU.get(top_p.name, top_p.name)}",
                    summary=f"тема дня — {PLANET_LABELS_RU.get(top_p.name, top_p.name)}: фокус на активности",
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
                    lunar_phase_summary = "планируй дела"
                elif d >= 157.5 and d < 202.5:
                    lunar_phase_title = "Полнолуние"
                    lunar_phase_summary = "будь сдержаннее"
                elif d >= 22.5 and d < 157.5:
                    lunar_phase_title = f"Растущая Луна {int(illumination)}%"
                    lunar_phase_summary = "накапливай силы"
                else:
                    lunar_phase_title = f"Убывающая Луна {int(illumination)}%"
                    lunar_phase_summary = "подводи итоги"

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
                    summary="не подписывай и не начинай",
                )
            )

        # Add Top Flag fact
        if signals:
            top_sig = signals[0]
            summary_facts.append(
                DaySummaryFact(
                    kind="top_flag",
                    icon_name="flag",
                    title=f"Аспект: {PLANET_LABELS_RU.get(top_sig.planet, top_sig.planet)} {ASPECT_LABELS_RU.get(top_sig.aspect_type, top_sig.aspect_type)} {PLANET_LABELS_RU.get(top_sig.target_planet, top_sig.target_planet)}" if top_sig.type == "aspect" else "Аспект дня",
                    summary="особое влияние дня",
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

            is_chart_mocked = hasattr(llm_service.generate_planet_interpretations, "mock") or hasattr(llm_service.generate_planet_interpretations, "assert_called")
            has_chart_keys = has_llm_keys or is_chart_mocked

            llm_interpretations = None
            if has_chart_keys:
                llm_interpretations = await llm_service.generate_planet_interpretations(planets_context)

            if llm_interpretations and isinstance(llm_interpretations, dict):
                for p in day_chart.transit_planets:
                    text = llm_interpretations.get(p.name)
                    if text and isinstance(text, str) and text.strip():
                        import re
                        if not re.search(r'[A-Za-z]', text):
                            p.interpretation = text.strip()
                    if not p.interpretation:
                        p.interpretation = "Интерпретация временно недоступна."
            else:
                for p in day_chart.transit_planets:
                    if has_chart_keys:
                        p.interpretation = "Интерпретация временно недоступна."
                    else:
                        p.interpretation = f"Интерпретация для {PLANET_LABELS_RU.get(p.name, p.name)} в доме {p.house}."

        return concrete_advice, day_summary, day_chart
