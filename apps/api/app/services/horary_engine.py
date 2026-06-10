# ############################################################################
# AI_HEADER: MODULE_HORARY_ENGINE
# ROLE: Computational engine for horary questions.
# DEPENDENCIES: stdlib only
# GRACE_ANCHORS: [SIGNIFICATORS, COMPUTATION]
# ############################################################################

# START_MODULE_CONTRACT: M-HORARY-ENGINE
# purpose: Computational logic for determining significators, evidence and
#          producing a structured horary analysis.
# owns:
#   - apps/api/app/services/horary_engine.py
# inputs:
#   - horary_chart: dict, signals: list[AstroSignal], category: str,
#     question_text: str | None
# outputs:
#   - HoraryAnalysis (verdict, confidence, testimonies, timing, warnings)
# invariants:
#   - significators must align to category mapping.
#   - verdict logic is deterministic, not LLM-driven.
#   - LLM never invents evidence: every EvidenceItem.source == "computed".
# END_MODULE_CONTRACT: M-HORARY-ENGINE

# START_MODULE_MAP: M-HORARY-ENGINE
# public_entrypoints:
#   - get_significator
#   - compute_verdict
#   - analyze
# END_MODULE_MAP: M-HORARY-ENGINE

from __future__ import annotations

import logging
import re
from typing import Any

from app.schemas.horary_analysis import (
    ConfidenceLabel,
    EvidenceItem,
    HoraryAnalysis,
    TimingInfo,
)
from app.schemas.normalization import AstroSignal


SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_RULERS = {
    "Aries": "MARS",
    "Taurus": "VENUS",
    "Gemini": "MERCURY",
    "Cancer": "MOON",
    "Leo": "SUN",
    "Virgo": "MERCURY",
    "Libra": "VENUS",
    "Scorpio": "MARS",
    "Sagittarius": "JUPITER",
    "Capricorn": "SATURN",
    "Aquarius": "SATURN",
    "Pisces": "JUPITER",
}

CATEGORY_SIGNIFICATORS = {
    "love": "Venus",
    "career": "Saturn",
    "money": "Jupiter",
    "health": "Mars",
    "travel": "Mercury",
    "other": "Moon",
}

# START_BLOCK: TIMEFRAME_PATTERNS
_TIMEFRAME_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"сегодня|сейчас|в\s+(этот\s+)?(день|момент)", re.IGNORECASE), "hours", "сегодня"),
    (re.compile(r"завтра|на\s+завтра", re.IGNORECASE), "days", "завтра"),
    (re.compile(r"на\s+(этой|текущей)\s+неделе|до\s+конца\s+недели", re.IGNORECASE), "week", "на этой неделе"),
    (re.compile(r"в\s+течение\s+недели|за\s+неделю", re.IGNORECASE), "week", "в течение недели"),
    (re.compile(r"в\s+этом\s+месяце|до\s+конца\s+месяца|за\s+месяц", re.IGNORECASE), "month", "в этом месяце"),
    (re.compile(r"в\s+течение\s+месяца|за\s+месяц", re.IGNORECASE), "month", "в течение месяца"),
    (re.compile(r"в\s+этом\s+квартале|за\s+квартал", re.IGNORECASE), "quarter", "в этом квартале"),
    (re.compile(r"до\s+конца\s+года|в\s+этом\s+году|за\s+год", re.IGNORECASE), "year", "в этом году"),
    (re.compile(r"в\s+течение\s+года|за\s+год", re.IGNORECASE), "year", "в течение года"),
    (re.compile(r"через\s+(\d+)\s*(день|дня|дней|недел[юи]|месяц[аев]?|лет|года)", re.IGNORECASE), "explicit", "явный срок"),
]
# END_BLOCK: TIMEFRAME_PATTERNS

# START_BLOCK: CATEGORY_TIMING_HINTS
_CATEGORY_TIMING_HINTS: dict[str, tuple[str, str]] = {
    "love": ("weeks", "несколько недель — типичный горизонт для вопросов об отношениях"),
    "career": ("weeks-months", "несколько недель — несколько месяцев, в зависимости от темы"),
    "money": ("months", "несколько месяцев — обычный горизонт для финансовых вопросов"),
    "health": ("days-weeks", "дни или недели — для вопросов о самочувствии"),
    "travel": ("weeks", "несколько недель — типично для вопросов о поездках"),
    "other": ("weeks", "несколько недель — нейтральная оценка по умолчанию"),
}
# END_BLOCK: CATEGORY_TIMING_HINTS

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "тригон",
    "square": "квадратура",
    "sextile": "секстиль",
}


def _clean_planet(name: str | None) -> str:
    if not name:
        return ""
    return name.replace("Transit_", "").replace("Natal_", "")


def _planet_ru(name: str) -> str:
    table = {
        "Sun": "Солнце", "Moon": "Луна",
        "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
        "Jupiter": "Юпитер", "Saturn": "Сатурн",
        "Uranus": "Уран", "Neptune": "Нептун", "Pluto": "Плутон",
    }
    return table.get(name, name)


def _aspect_phrase(a: str) -> str:
    return _ASPECT_RU.get(a, a)


def _find_main_aspect(
    signals: list[AstroSignal], asc_ruler: str, significator: str
) -> tuple[AstroSignal | None, float]:
    """Return (signal, score) for the main aspect between ASC ruler and significator."""
    for sig in signals:
        if sig.type != "aspect":
            continue
        p1 = _clean_planet(sig.planet)
        p2 = _clean_planet(sig.target_planet)
        if {p1, p2} == {asc_ruler, significator}:
            if sig.aspect_type in ("trine", "sextile"):
                return sig, 1.0
            if sig.aspect_type == "conjunction":
                return sig, 0.8
            if sig.aspect_type == "square":
                return sig, -0.5
            if sig.aspect_type == "opposition":
                return sig, -0.8
    return None, 0.5  # neutral default


def _find_moon_testimony(signals: list[AstroSignal]) -> EvidenceItem | None:
    for sig in signals:
        if sig.type != "aspect":
            continue
        p1 = _clean_planet(sig.planet)
        p2 = _clean_planet(sig.target_planet)
        if "Moon" in (p1, p2) and sig.aspect_type in ("trine", "sextile", "conjunction"):
            other = p2 if p1 == "Moon" else p1
            aspect = _aspect_phrase(sig.aspect_type)
            return EvidenceItem(
                type="moon_testimony",
                title=f"Луна в {aspect}е с {_planet_ru(other)}",
                explanation=(
                    f"Луна делает {aspect} к {_planet_ru(other)} — это поддерживает "
                    "движение ситуации в благоприятную сторону."
                ),
                weight=0.3,
                planets_involved=["Moon", other],
                aspect_type=sig.aspect_type,
                orb=sig.orb,
                applying=getattr(sig, "phase", None) in ("applying", "entering"),
            )
    return None


def _find_moon_blocking_testimony(signals: list[AstroSignal]) -> EvidenceItem | None:
    for sig in signals:
        if sig.type != "aspect":
            continue
        p1 = _clean_planet(sig.planet)
        p2 = _clean_planet(sig.target_planet)
        if "Moon" in (p1, p2) and sig.aspect_type in ("square", "opposition"):
            other = p2 if p1 == "Moon" else p1
            aspect = _aspect_phrase(sig.aspect_type)
            return EvidenceItem(
                type="moon_testimony",
                title=f"Луна в {aspect}е с {_planet_ru(other)}",
                explanation=(
                    f"Луна в {aspect}е с {_planet_ru(other)} — это создаёт трение "
                    "и тормозит развитие ситуации."
                ),
                weight=-0.3,
                planets_involved=["Moon", other],
                aspect_type=sig.aspect_type,
                orb=sig.orb,
                applying=getattr(sig, "phase", None) in ("applying", "entering"),
            )
    return None


def _find_combustion(signals: list[AstroSignal], asc_ruler: str) -> EvidenceItem | None:
    for sig in signals:
        if sig.type != "aspect":
            continue
        p1 = _clean_planet(sig.planet)
        p2 = _clean_planet(sig.target_planet)
        if {p1, p2} == {asc_ruler, "Sun"} and sig.aspect_type == "conjunction":
            return EvidenceItem(
                type="combustion",
                title=f"Сожжение {_planet_ru(asc_ruler)}",
                explanation=(
                    f"{_planet_ru(asc_ruler)} слишком близко к Солнцу — это ослабляет "
                    "сигнификатор вопроса."
                ),
                weight=-0.2,
                planets_involved=[asc_ruler, "Sun"],
                aspect_type="conjunction",
                orb=sig.orb,
            )
    return None


def _category_modifier(category: str | None, asc_sign: str) -> EvidenceItem | None:
    if category == "love" and asc_sign in ("Libra", "Taurus"):
        return EvidenceItem(
            type="category_modifier",
            title="ASC в обители Венеры",
            explanation=(
                "Знак ASC хорошо согласуется с темой вопроса — это даёт небольшой "
                "дополнительный «плюс»."
            ),
            weight=0.1,
            planets_involved=["Venus"],
        )
    return None


def _derive_confidence_label(
    main_aspect_found: bool,
    moon_testimony: EvidenceItem | None,
    moon_blocking: EvidenceItem | None,
    combustion: EvidenceItem | None,
) -> tuple[ConfidenceLabel, int, str]:
    """Map evidence mix to (label, score 0..100, explanation)."""
    if main_aspect_found and moon_testimony and not moon_blocking and not combustion:
        return (
            "high",
            80,
            "Главный аспект читается ясно, и Луна его поддерживает — это сильные "
            "свидетельства.",
        )
    if main_aspect_found and (moon_testimony or not moon_blocking) and not combustion:
        return (
            "medium",
            55,
            "Главный аспект есть, но подтверждение от Луны или контекста недостаточно "
            "уверенное.",
        )
    if not main_aspect_found and not moon_testimony and not moon_blocking:
        return (
            "low",
            25,
            "Ни главного аспекта, ни показаний Луны не нашлось — карта даёт слабые "
            "свидетельства.",
        )
    if combustion and not moon_testimony:
        return (
            "low",
            30,
            "Главный сигнификатор ослаблен сожжением, и Луна не компенсирует — "
            "свидетельства слабые.",
        )
    if main_aspect_found and moon_blocking:
        return (
            "low",
            35,
            "Главный аспект есть, но Луна ему противоречит — это разнонаправленные "
            "свидетельства.",
        )
    return (
        "medium",
        50,
        "Карта даёт умеренные свидетельства: часть указаний подтверждает, часть — нет.",
    )


def _detect_timeframe_in_question(question_text: str | None) -> str | None:
    if not question_text:
        return None
    for pattern, _bucket, label in _TIMEFRAME_PATTERNS:
        if pattern.search(question_text):
            return label
    return None


def _derive_timing_from_orb(main_signal: AstroSignal | None) -> tuple[str | None, str | None]:
    if not main_signal or main_signal.orb is None:
        return None, None
    orb = main_signal.orb
    if orb <= 1.0:
        return "несколько дней", f"орб {orb:.1f}° — аспект точный, реализуется быстро"
    if orb <= 3.0:
        return "1–2 недели", f"орб {orb:.1f}° — аспект близок к точному"
    if orb <= 6.0:
        return "несколько недель", f"орб {orb:.1f}° — умеренный орб"
    return "месяц и более", f"орб {orb:.1f}° — широкий орб, события растянуты во времени"


def _build_timing(
    question_text: str | None,
    category: str | None,
    main_signal: AstroSignal | None,
    moon_testimony: EvidenceItem | None,
    calculation_warnings: list[str],
) -> TimingInfo:
    explicit = _detect_timeframe_in_question(question_text)
    if explicit:
        return TimingInfo(
            status="known",
            time_range=explicit,
            text="Вопрос задан с временной рамкой — ориентируемся на неё.",
            basis="явная временная рамка из текста вопроса",
        )

    orb_range, orb_basis = _derive_timing_from_orb(main_signal)
    if orb_range:
        return TimingInfo(
            status="known",
            time_range=orb_range,
            text="Срок выведен из орба главного аспекта.",
            basis=orb_basis,
        )

    if moon_testimony and moon_testimony.orb is not None and moon_testimony.orb <= 3.0:
        return TimingInfo(
            status="unclear",
            time_range=None,
            text=(
                "Точный срок назвать сложно, но движение Луны указывает на ближайшие недели."
            ),
            basis="Луна близка к точному аспекту",
        )

    if category and category in _CATEGORY_TIMING_HINTS:
        hint_range, hint_text = _CATEGORY_TIMING_HINTS[category]
        calculation_warnings.append(
            "Точный срок по карте не выражен — показана только типовая оценка по категории."
        )
        return TimingInfo(
            status="unclear",
            time_range=hint_range,
            text=(
                "Срок по карте не выражен достаточно ясно. "
                + hint_text[0].upper() + hint_text[1:] + "."
            ),
            basis="типовая оценка по категории вопроса (низкая уверенность)",
        )

    calculation_warnings.append("Срок по карте определить не удалось.")
    return TimingInfo(
        status="not_enough_evidence",
        time_range=None,
        text=(
            "Вопрос задан без временной рамки, а карта не даёт уверенного срока."
        ),
        basis=None,
    )


class HoraryEngine:
    @staticmethod
    def get_significator(category: str | None) -> str:
        # START_FUNCTION_CONTRACT: M-HORARY-ENGINE.get_significator
        # purpose: Resolve the significator planet name for a given question category.
        # inputs: category (str or None)
        # returns: str (planet name)
        # side_effects: none
        # emitted_logs: none
        # error_behavior: returns Moon as fallback
        # END_FUNCTION_CONTRACT: M-HORARY-ENGINE.get_significator

        if not category:
            return "Moon"
        return CATEGORY_SIGNIFICATORS.get(category, "Moon")

    @staticmethod
    def compute_verdict(
        horary_chart: dict[str, Any], signals: list[AstroSignal], category: str | None
    ) -> tuple[str, float, list[str]]:
        # START_FUNCTION_CONTRACT: M-HORARY-ENGINE.compute_verdict
        # purpose: Backward-compatible verdict helper. Use analyze() for full output.
        # inputs: horary_chart (dict), signals (list[AstroSignal]), category (str or None)
        # returns: tuple[str, float, list[str]] — (verdict, confidence 0..1, planets)
        # side_effects: none
        # emitted_logs: none
        # error_behavior: propagates
        # END_FUNCTION_CONTRACT: M-HORARY-ENGINE.compute_verdict

        analysis = HoraryEngine.analyze(horary_chart, signals, category, None)
        return analysis.verdict, analysis.confidence_score / 100.0, analysis.involved_planets

    @staticmethod
    def analyze(
        horary_chart: dict[str, Any],
        signals: list[AstroSignal],
        category: str | None,
        question_text: str | None,
    ) -> HoraryAnalysis:
        # START_FUNCTION_CONTRACT: M-HORARY-ENGINE.analyze
        # purpose: Build a structured horary analysis: verdict, confidence
        #          (label+score+explanation), testimonies for/against/neutral,
        #          timing and warnings.
        # inputs: horary_chart (dict), signals (list[AstroSignal]),
        #         category (str or None), question_text (str or None)
        # returns: HoraryAnalysis
        # side_effects: none
        # emitted_logs: none
        # error_behavior: propagates
        # END_FUNCTION_CONTRACT: M-HORARY-ENGINE.analyze

        special_points = horary_chart.get("special_points", [])
        asc_point = next((sp for sp in special_points if sp["name"] == "ASC"), None)
        if asc_point:
            asc_lon = asc_point["longitude"]
            asc_sign = SIGNS[int(asc_lon / 30) % 12]
        else:
            asc_sign = "Aries"

        asc_ruler = SIGN_RULERS.get(asc_sign, "MARS").title()
        significator = HoraryEngine.get_significator(category)

        main_signal, main_score = _find_main_aspect(signals, asc_ruler, significator)
        main_aspect_found = main_signal is not None
        moon_testimony = _find_moon_testimony(signals)
        moon_blocking = _find_moon_blocking_testimony(signals)
        combustion = _find_combustion(signals, asc_ruler)
        category_mod = _category_modifier(category, asc_sign)

        testimonies_for: list[EvidenceItem] = []
        testimonies_against: list[EvidenceItem] = []
        neutral_factors: list[EvidenceItem] = []

        if main_signal is not None and main_score > 0:
            aspect = _aspect_phrase(main_signal.aspect_type or "")
            testimonies_for.append(
                EvidenceItem(
                    type="main_aspect",
                    title=(
                        f"{_planet_ru(asc_ruler)} в {aspect}е с {_planet_ru(significator)}"
                    ),
                    explanation=(
                        f"Главный сигнификатор {_planet_ru(asc_ruler)} и управитель темы "
                        f"{_planet_ru(significator)} образуют {aspect} — это основное "
                        "свидетельство в пользу положительного ответа."
                    ),
                    weight=main_score,
                    planets_involved=[asc_ruler, significator],
                    aspect_type=main_signal.aspect_type,
                    orb=main_signal.orb,
                    applying=getattr(main_signal, "phase", None) in ("applying", "entering"),
                )
            )
        elif main_signal is not None and main_score < 0:
            aspect = _aspect_phrase(main_signal.aspect_type or "")
            testimonies_against.append(
                EvidenceItem(
                    type="main_aspect",
                    title=(
                        f"{_planet_ru(asc_ruler)} в {aspect}е с {_planet_ru(significator)}"
                    ),
                    explanation=(
                        f"Главный сигнификатор {_planet_ru(asc_ruler)} и управитель темы "
                        f"{_planet_ru(significator)} образуют {aspect} — это основное "
                        "свидетельство против."
                    ),
                    weight=main_score,
                    planets_involved=[asc_ruler, significator],
                    aspect_type=main_signal.aspect_type,
                    orb=main_signal.orb,
                    applying=getattr(main_signal, "phase", None) in ("applying", "entering"),
                )
            )
        else:
            neutral_factors.append(
                EvidenceItem(
                    type="chart_weakness",
                    title="Главный аспект не найден",
                    explanation=(
                        "Между управителем ASC и управителем темы нет явного аспекта в "
                        "рассчитанной карте — это серьёзно ослабляет аргументацию."
                    ),
                    weight=-0.2,
                    planets_involved=[asc_ruler, significator],
                )
            )

        if moon_testimony:
            testimonies_for.append(moon_testimony)
        if moon_blocking:
            testimonies_against.append(moon_blocking)
        if combustion:
            testimonies_against.append(combustion)
        if category_mod:
            testimonies_for.append(category_mod)

        if not testimonies_for and not testimonies_against:
            neutral_factors.append(
                EvidenceItem(
                    type="neutral",
                    title="Карта без явных указаний",
                    explanation=(
                        "Ни «за», ни «против» явно не читается — это честный нейтральный "
                        "фон."
                    ),
                    weight=0.0,
                    planets_involved=[],
                )
            )

        label, score, explanation = _derive_confidence_label(
            main_aspect_found, moon_testimony, moon_blocking, combustion
        )

        verdict = "yes" if testimonies_for and not testimonies_against else "no" if testimonies_against and not testimonies_for else "maybe"
        if testimonies_for and testimonies_against:
            verdict = "maybe"

        warnings: list[str] = []
        timing = _build_timing(
            question_text, category, main_signal, moon_testimony, warnings
        )

        involved = list(
            {p for p in (asc_ruler, significator, "Moon") if p}
        )

        return HoraryAnalysis(
            verdict=verdict,
            confidence_score=score,
            confidence_label=label,
            confidence_explanation=explanation,
            involved_planets=involved,
            testimonies_for=testimonies_for,
            testimonies_against=testimonies_against,
            neutral_factors=neutral_factors,
            timing=timing,
            calculation_warnings=warnings,
        )
