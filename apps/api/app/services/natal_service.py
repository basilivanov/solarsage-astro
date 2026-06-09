# ############################################################################
# AI_HEADER: MODULE_NATAL_SERVICE
# ROLE: Natal reading service — generates structured natal reading payload.
# DEPENDENCIES: sqlalchemy, app.schemas.natal
# GRACE_ANCHORS: [NATAL_READING_GENERATION]
# WAVE: W-7.1, W-7.2
# ############################################################################

# START_MODULE_CONTRACT: M-NATAL-SERVICE
# purpose: Generate natal reading payload with sections and blocks.
#   W-7.1: Returns structured sections × blocks.
#   W-7.2: Simplified MVP version (hardcoded content).
# owns:
#   - apps/api/app/services/natal_service.py
# inputs:
#   - user_id: UUID
# outputs:
#   - NatalPayload: structured natal reading
# dependencies:
#   - M-CONTRACTS.natal
# side_effects:
#   - none (read-only)
# invariants:
#   - sections are ordered by order field
#   - blocks within sections are ordered by order field
# failure_policy:
#   - returns hardcoded content for MVP
# non_goals:
#   - no LLM integration (future wave)
#   - no database persistence (future wave)
# END_MODULE_CONTRACT: M-NATAL-SERVICE

from __future__ import annotations

from datetime import datetime, timezone
import logging
import uuid

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.solarsage_client import get_solarsage_client
from app.db.models import UserProfile
from app.schemas.natal import (
    BulletsBlock,
    HighlightsBlock,
    HighlightItem,
    NatalCalculationStats,
    NatalChapterPreview,
    NatalHighlight,
    NatalMeta,
    NatalPayload,
    NatalPlanetPreview,
    NatalPreviewMeta,
    NatalPreviewRead,
    NatalSection,
    NatalSpherePreview,
    ParagraphBlock,
    Person,
    PersonBirth,
    QuoteBlock,
)
from app.services.astro_utils import find_house
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)

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
        highlights.append(
            NatalHighlight(
                id="asc",
                title="Асцендент",
                value=asc.get("sign") or "—",
                description="Первое впечатление и способ входить в контакт.",
            )
        )
    if sun:
        highlights.append(
            NatalHighlight(
                id="sun-sign",
                title="Солнце",
                value=sun.get("sign") or "—",
                description=f"Базовый вектор личности: {_gender_forms(gender)['manifested']} через качества Солнца.",
            )
        )
    if moon:
        highlights.append(
            NatalHighlight(
                id="moon-sign",
                title="Луна",
                value=moon.get("sign") or "—",
                description=f"Эмоциональный отклик: как ты {_gender_forms(gender)['feels']} и восстанавливаешься.",
            )
        )
    return highlights[:3]


def _build_spheres(scores, gender: str) -> list[NatalSpherePreview]:
    ranked = sorted(scores.get("sphere_scores", {}).items(), key=lambda item: item[1], reverse=True)
    forms = _gender_forms(gender)
    result: list[NatalSpherePreview] = []
    for index, (sphere_id, score) in enumerate(ranked[:7], start=1):
        title = _sphere_label(sphere_id)
        result.append(
            NatalSpherePreview(
                id=sphere_id,
                title=title,
                score=round(float(score), 2),
                rank=index,
                description=f"Сфера «{title}» заметно выражена в карте: здесь {forms['assembled']} и легче считываешь свои приоритеты.",
            )
        )
    return result


def _build_planets(chart_data, scores, gender: str, signals=None) -> list[NatalPlanetPreview]:
    forms = _gender_forms(gender)
    houses = chart_data.get("houses", [])
    planet_scores = _extract_planet_scores(scores, chart_data, signals)
    planets: list[NatalPlanetPreview] = []

    for planet in chart_data.get("planets", [])[:5]:
        name = planet.get("name") or "Planet"
        house = planet.get("house") or find_house(planet.get("longitude", 0), houses)
        sign = planet.get("sign")
        sign_ru = _SIGN_RU.get(sign or "", sign or "знаке")
        house_text = f"в {house} доме" if house is not None else "без дома"
        planets.append(
            NatalPlanetPreview(
                id=name.lower(),
                name=_planet_label(name),
                sign=sign,
                house=house,
                score=planet_scores.get(name),
                description=f"{_planet_label(name)} в {sign_ru}, {house_text}: через эту планету особенно {forms['manifested']} личный паттерн карты.",
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

    async def get_natal_reading(self, user_id: uuid.UUID) -> NatalPayload:
        sections = [
            NatalSection(
                id="sun",
                title="Солнце",
                icon_name="sun",
                blocks=[
                    ParagraphBlock(
                        type="paragraph",
                        text="Ваше Солнце находится в знаке Овна, что наделяет вас энергией первопроходца. Вы прирожденный лидер, который не боится брать инициативу в свои руки.",
                    ),
                    HighlightsBlock(
                        type="highlights",
                        items=[
                            HighlightItem(
                                id="sun_strength",
                                title="Сильные стороны",
                                text="Смелость, решительность, энергичность",
                                tone="positive",
                            ),
                            HighlightItem(
                                id="sun_challenge",
                                title="Вызовы",
                                text="Импульсивность, нетерпеливость",
                                tone="neutral",
                            ),
                        ],
                    ),
                ],
            ),
            NatalSection(
                id="moon",
                title="Луна",
                icon_name="moon",
                blocks=[
                    ParagraphBlock(
                        type="paragraph",
                        text="Ваша Луна находится в знаке Рака, что делает вас глубоко эмоциональным и чувствительным человеком. Вы интуитивно понимаете эмоции других людей.",
                    ),
                    BulletsBlock(
                        type="bullets",
                        items=[
                            "Сильная связь с семьей и домом",
                            "Развитая интуиция и эмпатия",
                            "Потребность в эмоциональной безопасности",
                            "Склонность к заботе о других",
                        ],
                    ),
                    QuoteBlock(
                        type="quote",
                        text="Луна в Раке — это дар глубокого понимания человеческой природы.",
                        source="Классическая астрология",
                    ),
                ],
            ),
            NatalSection(
                id="ascendant",
                title="Асцендент",
                icon_name="arrow-up",
                blocks=[
                    ParagraphBlock(
                        type="paragraph",
                        text="Ваш Асцендент находится в знаке Льва, что придает вам харизму и естественное обаяние. Вы производите яркое впечатление на окружающих.",
                    ),
                    HighlightsBlock(
                        type="highlights",
                        items=[
                            HighlightItem(
                                id="asc_appearance",
                                title="Внешнее впечатление",
                                text="Уверенность, достоинство, магнетизм",
                                tone="positive",
                            ),
                        ],
                    ),
                ],
            ),
        ]

        meta = NatalMeta(
            schema_version="natal/v1",
            contract_version=1,
            title="Натальная карта",
            subtitle="Ваш астрологический портрет",
            generated_at=datetime.now(timezone.utc).isoformat(),
            calculation_version=1,
            interpretation_version=1,
            person=Person(
                name="Пользователь",
                birth=PersonBirth(
                    date="1990-01-01",
                    time="12:00",
                    place="Москва",
                ),
            ),
        )

        return NatalPayload(meta=meta, sections=sections)

    async def get_preview(self, user_id: uuid.UUID) -> NatalPreviewRead:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Profile is incomplete",
                    "missingFields": [
                        "birthday",
                        "birth_time",
                        "birth_lat",
                        "birth_lon",
                        "birth_tz",
                        "gender",
                    ],
                },
            )

        missing_fields = [
            field_name
            for field_name in ["birthday", "birth_time", "birth_lat", "birth_lon", "birth_tz", "gender"]
            if getattr(profile, field_name) is None
        ]
        if missing_fields:
            raise HTTPException(
                status_code=409,
                detail={"message": "Profile is incomplete", "missingFields": missing_fields},
            )

        gender = profile.gender
        if gender not in {"male", "female"}:
            raise HTTPException(
                status_code=409,
                detail={"message": "Profile is incomplete", "missingFields": ["gender"]},
            )

        client = get_solarsage_client()
        birth_date = profile.birthday.isoformat()
        birth_time = profile.birth_time.strftime("%H:%M")
        birth_lat = float(profile.birth_lat)
        birth_lon = float(profile.birth_lon)
        birth_tz = profile.birth_tz

        try:
            chart_data = await client.get_natal(
                birth_date=birth_date,
                birth_time=birth_time,
                birth_lat=birth_lat,
                birth_lon=birth_lon,
                birth_tz=birth_tz,
            )
            transits = await client.get_transits(
                target_date=birth_date,
                target_time=birth_time,
                target_tz=birth_tz,
            )
        except httpx.HTTPError as exc:
            logger.error(f"SolarSage sidecar error: {exc}")
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "SOLARSAGE_UNAVAILABLE",
                    "message": "Сервис расчёта временно недоступен. Попробуй позже.",
                },
            ) from exc

        normalization_service = NormalizationService()
        signals = normalization_service.normalize(chart_data, transits)
        scoring_service = ScoringService()
        scores = scoring_service.score(signals)

        asc = _find_special_point(chart_data, "ASC")
        meta = NatalPreviewMeta(
            name=profile.first_name,
            birth_date=birth_date,
            birth_time=birth_time,
            birth_city=profile.birth_city,
            house_system=chart_data.get("house_system"),
            asc_sign=asc.get("sign") if asc else None,
            asc_degree=float(asc["longitude"]) if asc and asc.get("longitude") is not None else None,
            gender=gender,
        )
        highlights = _build_highlights(chart_data, gender)
        spheres = _build_spheres(scores, gender)
        planets = _build_planets(chart_data, scores, gender, signals)
        chapters = _build_chapters(gender)
        personal_hook = _build_personal_hook(meta, highlights, spheres, gender)
        calculation_stats = _build_calculation_stats(chart_data, scores)
        sales_bullets = _build_sales_bullets(gender)

        return NatalPreviewRead(
            meta=meta,
            highlights=highlights,
            spheres=spheres,
            planets=planets,
            chapters=chapters,
            personal_hook=personal_hook,
            calculation_stats=calculation_stats,
            sales_bullets=sales_bullets,
            full_report_available=False,
            full_report_price_kopecks=99900,
        )
