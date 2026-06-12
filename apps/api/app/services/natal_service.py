# ############################################################################
# AI_HEADER: MODULE_NATAL_SERVICE
# ROLE: Natal preview service — builds NatalPreviewRead from cached NatalContext.
# DEPENDENCIES: sqlalchemy, app.schemas.natal, app.services.natal_context_service
# GRACE_ANCHORS: [NATAL_PREVIEW]
# WAVE: W-NATAL-FULL
# ############################################################################

# START_MODULE_CONTRACT: M-NATAL-SERVICE
# purpose: Build natal preview from cached NatalContext via NatalContextService.
#   W-NATAL-FULL: Uses NatalContextService as single source of truth.
# owns:
#   - apps/api/app/services/natal_service.py
# inputs:
#   - user_id: UUID
# outputs:
#   - NatalPreviewRead: structured preview for the natal screen
# dependencies:
#   - M-NATAL-CONTEXT-SERVICE
# side_effects:
#   - may trigger sidecar call on cache miss (via NatalContextService)
# invariants:
#   - never calls sidecar directly; delegates to NatalContextService
#   - never calls transits for preview
# failure_policy:
#   - 409 if profile incomplete
#   - 502 if sidecar unavailable
# non_goals:
#   - no LLM integration (see NatalReportService)
#   - no legacy hardcoded content (removed in W-NATAL-FULL cleanup)
# END_MODULE_CONTRACT: M-NATAL-SERVICE

# START_MODULE_MAP: M-NATAL-SERVICE
# public_entrypoints:
#   - NatalService.get_preview
# semantic_blocks:
#   - NATAL_PREVIEW: build natal preview from cached context
# END_MODULE_MAP: M-NATAL-SERVICE

from __future__ import annotations

import json
import uuid
from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserProfile
from app.schemas.natal import (
    NatalCalculationStats,
    NatalChapterPreview,
    NatalContextData,
    NatalHighlight,
    NatalPlanetPreview,
    NatalPreviewMeta,
    NatalPreviewRead,
    NatalSpherePreview,
)
from app.services.astro_utils import find_house
from app.services.normalization_service import NormalizationService

_SPHERE_TITLES = {
    "love": "Отношения",
    "money": "Деньги",
    "career": "Карьера",
    "health": "Ресурс",
    "family": "Семья",
    "self": "Личность",
}

_SPHERE_TITLES_CAP = {
    "thinking_speech_learning": "Мысли · речь · учёба",
    "work_status_achievement": "Работа · статус · достижения",
    "relationships_partnership": "Отношения · партнёрство",
    "body_energy_health": "Тело · энергия · здоровье",
    "money_security_resources": "Деньги · ресурсы",
    "emotions_inner_world": "Эмоции · внутренний мир",
    "family_roots_ancestors": "Семья · корни · предки",
    "creativity_self_expression": "Творчество · самовыражение",
    "spirit_meaning_transformation": "Дух · смысл · трансформация",
}

_PLANET_TITLES = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
}

_SIGN_RU = {
    "Aries": "Овне",
    "Taurus": "Тельце",
    "Gemini": "Близнецах",
    "Cancer": "Раке",
    "Leo": "Льве",
    "Virgo": "Деве",
    "Libra": "Весах",
    "Scorpio": "Скорпионе",
    "Sagittarius": "Стрельце",
    "Capricorn": "Козероге",
    "Aquarius": "Водолее",
    "Pisces": "Рыбах",
}

_SIGN_NOM = {
    "Aries": "Овен",
    "Taurus": "Телец",
    "Gemini": "Близнецы",
    "Cancer": "Рак",
    "Leo": "Лев",
    "Virgo": "Дева",
    "Libra": "Весы",
    "Scorpio": "Скорпион",
    "Sagittarius": "Стрелец",
    "Capricorn": "Козерог",
    "Aquarius": "Водолей",
    "Pisces": "Рыбы",
}


def _gender_forms(gender: str) -> dict[str, str]:
    return {
        "assembled": "ты собран" if gender == "male" else "ты собрана",
        "feels": "чувствуешь",
        "manifested": "проявлен" if gender == "male" else "проявлена",
    }


def _planet_label(name: str | None) -> str:
    if not name:
        return "Планета"
    return _PLANET_TITLES.get(name, name)


def _sphere_label(sphere_id: str) -> str:
    return _SPHERE_TITLES_CAP.get(sphere_id) or _SPHERE_TITLES.get(sphere_id) or sphere_id.replace("_", " ").title()


def _find_special_point(chart_data: dict, name: str) -> dict | None:
    return next((p for p in chart_data.get("special_points", []) if p.get("name") == name), None)


def _aspect_count(chart_data: dict) -> int:
    planets = chart_data.get("planets", [])
    normalization = NormalizationService()
    count = 0
    for i, p1 in enumerate(planets):
        for p2 in planets[i + 1 :]:
            if normalization._calculate_aspect(p1.get("longitude", 0), p2.get("longitude", 0)):
                count += 1
    return count


def _extract_planet_scores(scores: dict, chart_data: dict, signals=None) -> dict[str, float]:
    planet_scores: dict[str, float] = {}
    for planet in chart_data.get("planets", []):
        name = planet.get("name")
        if not name:
            continue
        total = 0.0
        if signals:
            for s in signals:
                if s.planet == name or s.target_planet == name:
                    total += float(s.strength)
        planet_scores[name] = round(total, 2)
    return planet_scores


def _build_highlights(chart_data, gender: str) -> list[NatalHighlight]:
    asc = _find_special_point(chart_data, "ASC")
    sun = next((p for p in chart_data.get("planets", []) if p.get("name") == "Sun"), None)
    moon = next((p for p in chart_data.get("planets", []) if p.get("name") == "Moon"), None)
    highlights: list[NatalHighlight] = []

    if asc:
        sign = _SIGN_RU.get(asc.get("sign") or "", asc.get("sign") or "—")
        highlights.append(
            NatalHighlight(
                id="asc",
                title="Асцендент",
                value=sign,
                description="Как ты входишь в контакт и проявляешься внешне.",
            )
        )
    if sun:
        sign = _SIGN_RU.get(sun.get("sign") or "", sun.get("sign") or "—")
        highlights.append(
            NatalHighlight(
                id="sun-sign",
                title="Солнце",
                value=sign,
                description=f"Твой базовый вектор личности: через что {_gender_forms(gender)['manifested']} сильнее всего.",
            )
        )
    if moon:
        sign = _SIGN_RU.get(moon.get("sign") or "", moon.get("sign") or "—")
        highlights.append(
            NatalHighlight(
                id="moon-sign",
                title="Луна",
                value=sign,
                description=f"Эмоциональный отклик: как ты {_gender_forms(gender)['feels']} мир и восстанавливаешься.",
            )
        )
    return highlights[:3]


def _build_spheres(scores, gender: str) -> list[NatalSpherePreview]:
    ranked = sorted(scores.get("sphere_scores", {}).items(), key=lambda item: item[1], reverse=True)
    _sphere_hints = {
        "thinking_speech_learning": "Твой ум активно ищет информацию, обмен и новые знания.",
        "work_status_achievement": "Здесь заложен твой потенциал роста, статуса и профессионального признания.",
        "relationships_partnership": "Отношения — твоя важная опора и зеркало внутренних сценариев.",
        "body_energy_health": "Телесный тонус, энергия и базовый ресурс — твоя фундаментальная опора.",
        "money_security_resources": "Материальная стабильность и чувство безопасности тесно связаны в карте.",
        "emotions_inner_world": "Внутренний мир, эмоции и интуиция — твоя глубинная навигация.",
        "family_roots_ancestors": "Семья, род и корни формируют базовые сценарии опоры и близости.",
        "creativity_self_expression": "Творчество и самовыражение — твой естественный способ проявить себя.",
        "spirit_meaning_transformation": "Духовный рост, поиск смысла и глубокая трансформация — твой путь.",
    }
    result: list[NatalSpherePreview] = []
    for index, (sphere_id, score) in enumerate(ranked[:7], start=1):
        title = _sphere_label(sphere_id)
        hint = _sphere_hints.get(sphere_id, f"Сфера «{title}» заметно выражена в карте.")
        result.append(
            NatalSpherePreview(
                id=sphere_id,
                title=title,
                score=round(float(score), 2),
                rank=index,
                description=hint,
            )
        )
    return result


def _build_planets(chart_data, scores, gender: str, signals=None) -> list[NatalPlanetPreview]:
    _planet_hints = {
        "Sun": "Твоё Солнце показывает базовый вектор личности и главный источник жизненной силы.",
        "Moon": "Луна раскрывает эмоциональные потребности, интуицию и способ восстановления.",
        "Mercury": "Меркурий определяет стиль мышления, речи и обработки информации.",
        "Venus": "Венера показывает твой стиль любви, красоты, ценностей и привязанностей.",
        "Mars": "Марс — это твоя воля, активность, инициатива и способ действия.",
        "Jupiter": "Юпитер указывает на зоны роста, удачи и естественного расширения.",
        "Saturn": "Сатурн показывает твои опоры, границы, ответственность и зоны дисциплины.",
        "Uranus": "Уран отвечает за оригинальность, свободу и нестандартные решения.",
        "Neptune": "Нептун связан с интуицией, мечтами, вдохновением и размытием границ.",
        "Pluto": "Плутон — зона глубинной трансформации, силы и перерождения.",
    }
    houses = chart_data.get("houses", [])
    planet_scores = _extract_planet_scores(scores, chart_data, signals)
    planets: list[NatalPlanetPreview] = []

    for planet in chart_data.get("planets", [])[:5]:
        name = planet.get("name") or "Planet"
        house = planet.get("house") or find_house(planet.get("longitude", 0), houses)
        sign_en = planet.get("sign")
        sign_nom = _SIGN_NOM.get(sign_en or "", sign_en or "")
        sign_prep = _SIGN_RU.get(sign_en or "", sign_en or "знаке")
        house_text = f"{house} дом" if house is not None else ""
        hint = _planet_hints.get(name, f"{_planet_label(name)} — важный элемент твоей карты.")
        planets.append(
            NatalPlanetPreview(
                id=name.lower(),
                name=_planet_label(name),
                sign=sign_nom,
                house=house,
                score=planet_scores.get(name),
                description=f"{_planet_label(name)} в {sign_prep}, {house_text}. {hint}" if house_text else f"{_planet_label(name)} в {sign_prep}. {hint}",
            )
        )
    return planets


def _build_chapters(gender: str) -> list[NatalChapterPreview]:
    forms = _gender_forms(gender)
    return [
        NatalChapterPreview(
            id="relationships",
            eyebrow="Полный разбор",
            title="Отношения и близость",
            description=f"Покажем, как в отношениях {forms['manifested']} твой стиль привязанности и контакта.",
        ),
        NatalChapterPreview(
            id="purpose",
            eyebrow="Полный разбор",
            title="Предназначение и реализация",
            description="Соберём сильные стороны карты в понятный вектор реализации.",
        ),
        NatalChapterPreview(
            id="money",
            eyebrow="Полный разбор",
            title="Деньги и стратегия роста",
            description="Разложим по карте, где легче монетизировать способности и что мешает стабильно расти.",
        ),
        NatalChapterPreview(
            id="career",
            eyebrow="Полный разбор",
            title="Карьера и публичная позиция",
            description=f"Покажем, в какой роли ты ярче всего {forms['manifested']} в работе, статусе и публичной реализации.",
        ),
        NatalChapterPreview(
            id="health",
            eyebrow="Полный разбор",
            title="Здоровье и энергия тела",
            description=f"Разберём, как у тебя {forms['manifested']} ритм восстановления, запас энергии и телесная устойчивость.",
        ),
        NatalChapterPreview(
            id="family",
            eyebrow="Полный разбор",
            title="Семья и род",
            description=f"Покажем, как в теме семьи и корней {forms['manifested']} твои базовые сценарии опоры и близости.",
        ),
        NatalChapterPreview(
            id="creativity",
            eyebrow="Полный разбор",
            title="Творчество и самовыражение",
            description=f"Подсветим, через что ты естественнее всего {forms['manifested']} в творчестве, удовольствии и самоподаче.",
        ),
        NatalChapterPreview(
            id="spiritual_path",
            eyebrow="Полный разбор",
            title="Духовный путь и трансформация",
            description=f"Разберём, где глубже всего {forms['manifested']} твой внутренний рост, смысл и точки личной трансформации.",
        ),
    ]


def _build_personal_hook(meta, highlights, spheres, gender: str) -> str:
    forms = _gender_forms(gender)
    asc = highlights[0].value if highlights else "—"
    sun = highlights[1].value if len(highlights) > 1 else "—"
    top_sphere = spheres[0].title if spheres else "ключевая сфера"
    return f"{forms['assembled']}: с ASC в {asc} и Солнцем в {sun} у тебя особенно заметна тема «{top_sphere}», через неё ярче всего читается твой личный стиль."


def _build_calculation_stats(chart_data, scores) -> NatalCalculationStats:
    planets_count = len(chart_data.get("planets", []))
    houses_count = len(chart_data.get("houses", []))
    aspects_count = _aspect_count(chart_data)
    spheres_count = len(scores.get("sphere_scores", {}))
    special_points_count = len(chart_data.get("special_points", []))
    scoring_factors_count = len(scores.get("top_signals", []))
    dignity_factors_count = 0
    total_factors_count = (
        planets_count
        + houses_count
        + aspects_count
        + spheres_count
        + special_points_count
        + scoring_factors_count
        + dignity_factors_count
    )
    if total_factors_count >= 350:
        display_label = "350+ факторов карты"
    elif total_factors_count >= 300:
        display_label = "300+ факторов карты"
    elif total_factors_count >= 200:
        display_label = "200+ факторов карты"
    else:
        display_label = f"{total_factors_count} факторов карты"
    return NatalCalculationStats(
        planets_count=planets_count,
        houses_count=houses_count,
        aspects_count=aspects_count,
        spheres_count=spheres_count,
        special_points_count=special_points_count,
        scoring_factors_count=scoring_factors_count,
        dignity_factors_count=dignity_factors_count,
        total_factors_count=total_factors_count,
        display_label=display_label,
    )


def _build_sales_bullets(gender: str) -> list[str]:
    forms = _gender_forms(gender)
    return [
        f"Поймёшь, где в карте ты уже {forms['manifested']} сильнее всего.",
        "Увидишь приоритетные сферы, а не разрозненные факты.",
        "Получишь полный разбор планет, домов и жизненных тем.",
    ]


class NatalService:
    """Natal reading service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_preview(self, user_id: uuid.UUID) -> NatalPreviewRead:
        # START_FUNCTION_CONTRACT: F-M-NATAL-SERVICE.get_preview
        # purpose: Build natal preview from cached NatalContext.
        # inputs: user_id (UUID)
        # returns: NatalPreviewRead with highlights, spheres, planets, chapters
        # side_effects: reads/writes NatalChartCache, calls sidecar on cache miss
        # emitted_logs: none (events emitted by API route handler in natal.py)
        # error_behavior: HTTPException 409 on incomplete profile, 502 on sidecar failure
        # END_FUNCTION_CONTRACT: F-M-NATAL-SERVICE.get_preview
        """Build preview from cached/buildable NatalContext.

        W-NATAL-FULL: Uses NatalContextService as single source of truth.
        No direct SolarSage calls. No transit calls for preview.
        """
        from app.services.natal_context_service import NatalContextService
        from app.db.models import NatalChartCache

        context_service = NatalContextService(self.db)

        # get_or_build_natal_context handles profile validation and sidecar calls
        natal_context = await context_service.get_or_build_natal_context(user_id)

        # Load profile for name/city (already validated by context service)
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        gender = profile.gender if profile else "female"
        birth_date = profile.birthday.isoformat() if profile and profile.birthday else ""
        birth_time = profile.birth_time.strftime("%H:%M") if profile and profile.birth_time else ""
        birth_city = profile.birth_city if profile else None

        # Find the cache entry for raw_chart_json (needed for highlights/stats)
        profile_hash = NatalContextService.compute_profile_hash(profile) if profile else ""
        cache_result = await self.db.execute(
            select(NatalChartCache).where(
                NatalChartCache.user_id == user_id,
                NatalChartCache.profile_hash == profile_hash,
                NatalChartCache.invalidated_at.is_(None),
            )
        )
        cache_entry = cache_result.scalar_one_or_none()
        chart_data = json.loads(cache_entry.raw_chart_json) if cache_entry else {}

        # Build preview components from natal context
        asc = next((a for a in natal_context.angles if a.name == "ASC"), None)
        meta = NatalPreviewMeta(
            name=profile.first_name if profile else None,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_city=birth_city,
            house_system=natal_context.house_system,
            asc_sign=asc.sign if asc else None,
            asc_degree=asc.degree if asc else None,
            gender=gender,
        )

        # Build scores dict from context for helper functions
        scores = {
            "sphere_scores": natal_context.sphere_scores,
            "top_signals": natal_context.top_signals,
        }

        highlights = self._build_highlights_from_context(natal_context, gender)
        spheres = _build_spheres(scores, gender)
        planets = self._build_planets_from_context(natal_context, gender)
        chapters = _build_chapters(gender)
        personal_hook = _build_personal_hook(meta, highlights, spheres, gender)
        calculation_stats = self._build_calculation_stats_from_context(natal_context)
        sales_bullets = _build_sales_bullets(gender)

        # W-NATAL-FULL Wave 4: Check if user has a READY report tied to
        # the CURRENT active natal context (not any old context).
        # This prevents an old READY report from a previous birth-data
        # configuration from appearing as available for the current preview.
        full_report_available = False
        if cache_entry is not None:
            from app.db.models import NatalReport
            from app.services.natal_report_service import PROMPT_VERSION, REPORT_SCHEMA_VERSION
            report_result = await self.db.execute(
                select(NatalReport).where(
                    and_(
                        NatalReport.user_id == user_id,
                        NatalReport.natal_context_id == cache_entry.id,
                        NatalReport.status == "READY",
                        NatalReport.prompt_version == PROMPT_VERSION,
                        NatalReport.report_schema_version == REPORT_SCHEMA_VERSION,
                    )
                )
            )
            if report_result.scalar_one_or_none() is not None:
                full_report_available = True

        return NatalPreviewRead(
            meta=meta,
            highlights=highlights,
            spheres=spheres,
            planets=planets,
            chapters=chapters,
            personal_hook=personal_hook,
            calculation_stats=calculation_stats,
            sales_bullets=sales_bullets,
            full_report_available=full_report_available,
            full_report_price_kopecks=99900,
        )

    @staticmethod
    def _build_highlights_from_context(context: NatalContextData, gender: str) -> list[NatalHighlight]:
        """Build highlights from NatalContextData instead of raw chart_data."""
        asc = next((a for a in context.angles if a.name == "ASC"), None)
        sun = next((p for p in context.planets if p.name == "Sun"), None)
        moon = next((p for p in context.planets if p.name == "Moon"), None)
        highlights: list[NatalHighlight] = []

        if asc:
            sign = _SIGN_RU.get(asc.sign, asc.sign)
            highlights.append(NatalHighlight(
                id="asc", title="Асцендент", value=sign,
                description="Как ты входишь в контакт и проявляешься внешне.",
            ))
        if sun:
            sign = _SIGN_RU.get(sun.sign, sun.sign)
            highlights.append(NatalHighlight(
                id="sun-sign", title="Солнце", value=sign,
                description=f"Твой базовый вектор личности: через что {_gender_forms(gender)['manifested']} сильнее всего.",
            ))
        if moon:
            sign = _SIGN_RU.get(moon.sign, moon.sign)
            highlights.append(NatalHighlight(
                id="moon-sign", title="Луна", value=sign,
                description=f"Эмоциональный отклик: как ты {_gender_forms(gender)['feels']} мир и восстанавливаешься.",
            ))
        return highlights[:3]

    @staticmethod
    def _build_planets_from_context(context: NatalContextData, gender: str) -> list[NatalPlanetPreview]:
        """Build planet previews from NatalContextData."""
        _planet_hints = {
            "Sun": "Твоё Солнце показывает базовый вектор личности и главный источник жизненной силы.",
            "Moon": "Луна раскрывает эмоциональные потребности, интуицию и способ восстановления.",
            "Mercury": "Меркурий определяет стиль мышления, речи и обработки информации.",
            "Venus": "Венера показывает твой стиль любви, красоты, ценностей и привязанностей.",
            "Mars": "Марс — это твоя воля, активность, инициатива и способ действия.",
            "Jupiter": "Юпитер указывает на зоны роста, удачи и естественного расширения.",
            "Saturn": "Сатурн показывает твои опоры, границы, ответственность и зоны дисциплины.",
            "Uranus": "Уран отвечает за оригинальность, свободу и нестандартные решения.",
            "Neptune": "Нептун связан с интуицией, мечтами, вдохновением и размытием границ.",
            "Pluto": "Плутон — зона глубинной трансформации, силы и перерождения.",
        }
        planets: list[NatalPlanetPreview] = []
        for planet in context.planets[:5]:
            name = planet.name
            sign_en = planet.sign
            sign_nom = _SIGN_NOM.get(sign_en, sign_en)
            sign_prep = _SIGN_RU.get(sign_en, sign_en)
            house_text = f"{planet.house} дом" if planet.house is not None else ""
            hint = _planet_hints.get(name, f"{_planet_label(name)} — важный элемент твоей карты.")
            planets.append(NatalPlanetPreview(
                id=name.lower(),
                name=_planet_label(name),
                sign=sign_nom,
                house=planet.house,
                score=None,
                description=f"{_planet_label(name)} в {sign_prep}, {house_text}. {hint}" if house_text else f"{_planet_label(name)} в {sign_prep}. {hint}",
            ))
        return planets

    @staticmethod
    def _build_calculation_stats_from_context(context: NatalContextData) -> NatalCalculationStats:
        """Build calculation stats from NatalContextData."""
        planets_count = len(context.planets)
        houses_count = len(context.houses)
        aspects_count = len(context.aspects)
        spheres_count = len(context.sphere_scores)
        special_points_count = len(context.special_points)
        scoring_factors_count = len(context.top_signals)
        total_factors_count = (
            planets_count + houses_count + aspects_count +
            spheres_count + special_points_count + scoring_factors_count
        )
        if total_factors_count >= 350:
            display_label = "350+ факторов карты"
        elif total_factors_count >= 300:
            display_label = "300+ факторов карты"
        elif total_factors_count >= 200:
            display_label = "200+ факторов карты"
        else:
            display_label = f"{total_factors_count} факторов карты"
        return NatalCalculationStats(
            planets_count=planets_count,
            houses_count=houses_count,
            aspects_count=aspects_count,
            spheres_count=spheres_count,
            special_points_count=special_points_count,
            scoring_factors_count=scoring_factors_count,
            dignity_factors_count=0,
            total_factors_count=total_factors_count,
            display_label=display_label,
        )
