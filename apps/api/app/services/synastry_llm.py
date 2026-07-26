# ############################################################################
# AI_HEADER: MODULE_LLM_SYNASTRY
# ROLE: Pure LLM prompt builder, static dictionaries, and local validator for synastry reports.
# DEPENDENCIES: typing, json, re
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-SYNASTRY
# purpose: Pure LLM prompts, JSON schema definitions, static dictionaries, and local validation rules for synastry.
# owns:
#   - apps/api/app/services/synastry_llm.py
# inputs: Scoring output, aspect parameters, precision flags
# outputs: LLM prompts (dict with system and user messages), static dictionaries, validation results
# dependencies: none (pure Python)
# side_effects: none (no network calls, no DB calls)
# emitted_logs: none
# invariants:
#   - PII (partner name, exact birth date) is NEVER included in LLM prompts
#   - Local validator enforces length limits, blocklist, and approximate-mode house/ASC constraints
# failure_policy: validate_llm_output returns (False, reason) on any constraint violation
# END_MODULE_CONTRACT: M-LLM-SYNASTRY

# START_MODULE_MAP: M-LLM-SYNASTRY
# public_entrypoints:
#   - PLANET_MEANINGS
#   - ASPECT_MEANINGS
#   - BANNED_PHRASES
#   - build_report_prompt
#   - build_drilldown_prompt
#   - validate_llm_output
#   - validate_drilldown_output
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_synastry_llm.py
# END_MODULE_MAP: M-LLM-SYNASTRY

from __future__ import annotations

from typing import Any


PLANET_MEANINGS: dict[str, str] = {
    "Sun": "Ядро личности, самовыражение и сознательные жизненные цели.",
    "Moon": "Подсознание, эмоции, базовая безопасность и повседневные привычки.",
    "Mercury": "Мышление, стиль общения, обработка информации и логика.",
    "Venus": "Отношения, привязанность, романтические ценности и понятие о красоте.",
    "Mars": "Энергия, воля, запуск действий и отстаивание своих границ.",
    "Jupiter": "Расширение возможностей, мировоззрение, щедрость и оптимизм.",
    "Saturn": "Дисциплина, границы, ответственность и уроки на прочность.",
    "Uranus": "Свобода, озарения, нестандартность и внезапные перемены.",
    "Neptune": "Вдохновение, эмпатия, мечты и тонкая чувствительность.",
    "Pluto": "Глубокая трансформация, сила притяжения и эмоциональная интенсивность.",
    "Ascendant": "Первое впечатление, стиль проявления в мире и личные границы.",
    "ASC": "Первое впечатление, стиль проявления в мире и личные границы.",
}

ASPECT_MEANINGS: dict[str, dict[str, str]] = {
    "conjunction": {
        "name": "Соединение",
        "explanation": "Слияние двух энергий в одной точке, задающее сильный общий вектор.",
    },
    "sextile": {
        "name": "Секстиль",
        "explanation": "Гармоничный шанс и лёгкое взаимопонимание при проявлении инициативы.",
    },
    "trine": {
        "name": "Трин",
        "explanation": "Естественный поток поддержки и гармонии, работающий без усилий.",
    },
    "square": {
        "name": "Квадрат",
        "explanation": "Динамический вызов и трение, требующие роста и выработки компромиссов.",
    },
    "opposition": {
        "name": "Оппозиция",
        "explanation": "Полярность и поиск баланса между противоположными точками зрения.",
    },
    "quincunx": {
        "name": "Квиконс",
        "explanation": "Тонкая настройка и адаптация к разным внутренним ритмам.",
    },
}

BANNED_PHRASES: list[str] = [
    "обречены",
    "обречен",
    "обречена",
    "всегда",
    "никогда",
    "идеальная пара",
    "точно изменит",
    "гарантированно",
    "развод неминуем",
]

APPROXIMATE_FORBIDDEN_TERMS: list[str] = [
    "1-м доме",
    "2-м доме",
    "3-м доме",
    "4-м доме",
    "5-м доме",
    "6-м доме",
    "7-м доме",
    "8-м доме",
    "9-м доме",
    "10-м доме",
    "11-м доме",
    "12-м доме",
    "в доме партнера",
    "асцендент партнера",
]


SYNASTRY_SYSTEM_PROMPT = """Ты — опытный психологический астролог-консультант. Твоя задача — дать глубокий, уважительный и конструктивный разбор взаимодействия двух людей на основе астрологических факторов.

ПРАВИЛА И ОГРАНИЧЕНИЯ:
1. Используй калиброванный язык: «может», «чаще», «похоже».
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать слова-фатализмы: «обречены», «всегда», «никогда», «идеальная пара», «точно изменит», «гарантированно».
3. Обращайся к пользователю на «ты», а второго человека называй «партнёр» (без имён и PII).
4. Описывай наблюдаемое поведение пары, а не личность. У каждого напряжения показывай конкретный конструктивный путь (repair).
5. Не приписывай измену, ложь или манипуляцию на основе астрологических аспектов.
6. Выдавай строго валидный JSON в соответствии со структурой.
"""


def build_report_prompt(
    score: int,
    status: str,
    counters: dict[str, int],
    aspects: list[dict[str, Any]],
    partner_precision: str = "exact",
) -> dict[str, str]:
    """Build system and user prompts for full synastry report generation without PII."""
    aspect_lines = []
    for a in aspects[:8]:
        op = a.get("owner_planet", "")
        pp = a.get("partner_planet", "")
        asp = a.get("aspect", "")
        tone = a.get("tone", "")
        orb = a.get("orb_degrees", 0.0)
        aspect_lines.append(f"- {op} {asp} {pp} (орбис {orb:.1f}°, тон: {tone})")

    aspects_str = "\n".join(aspect_lines)
    approx_note = ""
    if partner_precision in ("approximate", "unknown"):
        approx_note = "\nВНИМАНИЕ: Время рождения партнёра НЕИЗВЕСТНО. НЕ используй дома партнёра и его Асцендент в текстах."

    user_prompt = f"""Сформируй нарратив синастрии для пары:
- Общий балл совместимости: {score}/100 (статус: {status})
- Счётчики контактов: {counters.get('good', 0)} поддерживающих, {counters.get('mid', 0)} неоднозначных, {counters.get('bad', 0)} напряжённых
- Ключевые аспекты:
{aspects_str}
{approx_note}

Сформируй JSON-ответ со следующими полями:
- verdict: краткая фраза-вердикт (до 120 символов)
- hero_title: заголовок героя (до 60 символов)
- hero_description: подзаголовок героя (до 220 символов)
- summary: краткий общий вердикт (2-3 предложения, до 300 символов)
- aspect_shorts: список кратких заголовков (до 7 слов) для каждого аспектов в том же порядке
- translations: 3-5 карточек перевода, КАЖДАЯ привязана к одному из ключевых аспектов выше. Обязательные ключи объекта:
  - "title": заголовок до 42 символов
  - "tone": "good" | "mid" | "bad" — тон соответствующего аспекта
  - "tech": техническая подпись аспекта ИЗ СПИСКА ВЫШЕ в том же виде (например "Солнце trine Луна" — копируй формат из списка)
  - "text": текст до 220 символов
  - "scene": жизненная сцена до 120 символов
- spheres: тексты для 4 сфер ("intimacy", "communication", "daily_life", "finance") до 220 символов каждый
"""
    return {
        "system": SYNASTRY_SYSTEM_PROMPT,
        "user": user_prompt,
    }


def build_drilldown_prompt(aspect: dict[str, Any]) -> dict[str, str]:
    """Build system and user prompts for aspect drill-down detail generation."""
    op = aspect.get("owner_planet", "")
    pp = aspect.get("partner_planet", "")
    asp = aspect.get("aspect", "")
    tone = aspect.get("tone", "")

    user_prompt = f"""Разбери подробный drill-down для аспекта: {op} {asp} {pp} (тон: {tone}).
Сформируй JSON со следующими полями:
- intro: вводное объяснение взаимодействия (до 250 символов)
- scenes: список из 3-4 жизненных сцен ("title", "text")
- repairs: список из 3-5 конкретных действий для гармонизации (нумерованные рекомендации)
- not_means: ровно 3 пункта защиты от фатализма ("Не означает, что...")
"""
    return {
        "system": SYNASTRY_SYSTEM_PROMPT,
        "user": user_prompt,
    }


def validate_llm_output(
    data: dict[str, Any],
    report_precision: str = "exact",
) -> tuple[bool, str | None]:
    """Validate generated LLM output against length limits, blocklist, and precision rules."""
    if not isinstance(data, dict):
        return False, "Output is not a dict"

    # 1. Banned phrases check across all string fields
    text_content = _extract_all_text(data).lower()

    for phrase in BANNED_PHRASES:
        if phrase in text_content:
            return False, f"Banned phrase detected: '{phrase}'"

    # 2. Approximate mode restriction check
    if report_precision in ("approximate", "unknown"):
        for term in APPROXIMATE_FORBIDDEN_TERMS:
            if term in text_content:
                return False, f"Forbidden house/ASC term in approximate mode: '{term}'"

    # 3. Check summary & verdict length limits if present
    verdict = data.get("verdict")
    if isinstance(verdict, str) and len(verdict) > 150:
        return False, f"Verdict exceeds length limit ({len(verdict)} > 150)"

    hero_title = data.get("hero_title")
    if isinstance(hero_title, str) and len(hero_title) > 80:
        return False, f"Hero title exceeds length limit ({len(hero_title)} > 80)"

    hero_desc = data.get("hero_description")
    if isinstance(hero_desc, str) and len(hero_desc) > 250:
        return False, f"Hero description exceeds length limit ({len(hero_desc)} > 250)"

    summary = data.get("summary")
    if isinstance(summary, str) and len(summary) > 350:
        return False, f"Summary exceeds length limit ({len(summary)} > 350)"

    # 4. Check translations length if present
    translations = data.get("translations")
    if isinstance(translations, list):
        for idx, t in enumerate(translations):
            if isinstance(t, dict):
                text = t.get("text", "")
                if isinstance(text, str) and len(text) > 260:
                    return False, f"Translation {idx} text exceeds limit ({len(text)} > 260)"

    return True, None


def validate_drilldown_output(data: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate generated aspect drilldown LLM payload."""
    if not isinstance(data, dict):
        return False, "Output is not a dict"

    # Banned phrases are checked WITHOUT not_means: that block denies fatalism by
    # construction, so it legitimately contains phrases like "не значит, что ... всегда ...".
    not_means = data.get("not_means")
    content_for_ban = {k: v for k, v in data.items() if k != "not_means"}
    text_content = _extract_all_text(content_for_ban).lower()
    for phrase in BANNED_PHRASES:
        if phrase in text_content:
            return False, f"Banned phrase detected: '{phrase}'"

    if isinstance(not_means, list) and len(not_means) != 3:
        return False, f"not_means must contain exactly 3 items, got {len(not_means)}"

    scenes = data.get("scenes")
    if isinstance(scenes, list) and not (3 <= len(scenes) <= 5):
        return False, f"scenes count must be between 3 and 5, got {len(scenes)}"

    return True, None


def _extract_all_text(obj: Any) -> str:
    """Recursively collect all string values from dict/list structure."""
    if isinstance(obj, str):
        return obj + " "
    elif isinstance(obj, dict):
        return "".join(_extract_all_text(v) for v in obj.values())
    elif isinstance(obj, list):
        return "".join(_extract_all_text(item) for item in obj)
    return ""
