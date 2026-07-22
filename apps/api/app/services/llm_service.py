# ############################################################################
# AI_HEADER: MODULE_LLM_SERVICE
# ROLE: LLM integration — headline, reading, notes, why-sections, horary
# DEPENDENCIES: anthropic, httpx, app.core.config
# GRACE_ANCHORS: [HEADLINE_GENERATION, READING_GENERATION, NOTES_GENERATION, WHY_GENERATION, LLM_CLIENT]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-SERVICE
# purpose: Generate astrological text via LLM (headline, reading, notes, why-sections, horary).
# owns:
#   - apps/api/app/services/llm_service.py
# inputs:
#   - day_status, top_signals, sphere_scores, semantic_layer, natal context
# outputs:
#   - str | None (headline, notes)
#   - list[str] | None (reading paragraphs)
#   - list[dict] | None (why-sections, important-today details)
#   - dict (horary answer blocks)
# dependencies:
#   - M-CONFIG (settings)
#   - anthropic, httpx
# side_effects:
#   - HTTP requests to OpenRouter / DeepSeek / Anthropic
# invariants:
#   - falls back through providers: OpenRouter → DeepSeek → None
#   - horary generation has 2 retry attempts
#   - horary: the LLM writes ONLY five narrative strings through
#     provider-enforced Structured Outputs (OpenRouter response_format
#     json_schema strict + provider.require_parameters=true, Horary and
#     Natal sections only);
#     the backend assembles the public 8 blocks with engine-owned
#     verdict/confidence/testimonies/timing verbatim from the HoraryAnalysis
#     (no LLM-substituted engine fields; unclear timing never exposes the
#     internal hint)
#   - assembled horary blocks are re-validated against the shared public
#     HoraryBlock contract (validate_horary_llm_blocks); malformed output is
#     rejected, never persisted as an unreadable "answered" report
# failure_policy:
#   - returns None if all providers fail
#   - raises HoraryGenerationError if horary fails after 2 attempts
# non_goals:
#   - no streaming (MVP uses synchronous generation)
# END_MODULE_CONTRACT: M-LLM-SERVICE

# START_MODULE_MAP: M-LLM-SERVICE
# public_entrypoints:
#   - LLMService.generate_headline
#   - LLMService.generate_reading
#   - LLMService.generate_notes
#   - LLMService.generate_why_sections
#   - LLMService.generate_important_today_details
#   - LLMService.generate_horary_answer
# semantic_blocks:
#   - HEADLINE_GENERATION: generate day headline
#   - READING_GENERATION: generate day reading
#   - NOTES_GENERATION: generate day notes
#   - WHY_GENERATION: generate why-sections
#   - LLM_CLIENT: HTTP client for LLM providers
# END_MODULE_MAP: M-LLM-SERVICE

from __future__ import annotations

import json as json_lib
import logging

import anthropic
import httpx

from app.core.config import settings
from app.core.logging import log_event, log_block
from app.schemas.horary import validate_horary_llm_blocks
from pydantic import ValidationError

# ── Astrological boundary rules ─────────────────────────────────────
# LLM must NOT compute astrology — only interpret pre-computed backend data.

_ASTRO_BOUNDARY_RULES = """
КРИТИЧЕСКИЕ ПРАВИЛА:
- ТЫ НЕ ВЫЧИСЛЯЕШЬ астрологические данные. Ты ТОЛЬКО интерпретируешь готовые расчёты, которые тебе переданы.
- НЕ рассчитывай положения планет, дома, аспекты, орбы, даты и время.
- НЕ придумывай астрологические факты — используй ТОЛЬКО переданные данные.
- Если факта нет во входных данных — не добавляй его.
- Твоя роль — интерпретировать, а не вычислять.
"""

# ── Russian name mappings (no anglicisms) ─────────────────────────────

_PLANET_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна",
    "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
    "Jupiter": "Юпитер", "Saturn": "Сатурн",
    "Uranus": "Уран", "Neptune": "Нептун", "Pluto": "Плутон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение", "opposition": "оппозиция",
    "trine": "трин", "square": "квадратура", "sextile": "секстиль",
}

_SPHERE_RU: dict[str, str] = {
    "personal": "личная жизнь", "relationships": "отношения",
    "career": "карьера", "finance": "финансы",
    "health": "здоровье", "creativity": "творчество",
    "spirituality": "духовное развитие",
}

_HOUSE_RU: dict[int, str] = {
    1: "1 дом (личность)", 2: "2 дом (финансы)", 3: "3 дом (общение)",
    4: "4 дом (семья)", 5: "5 дом (творчество)", 6: "6 дом (здоровье)",
    7: "7 дом (партнёрство)", 8: "8 дом (трансформация)", 9: "9 дом (путешествия)",
    10: "10 дом (карьера)", 11: "11 дом (друзья)", 12: "12 дом (подсознание)",
}


def _planet(s: str) -> str:
    """Translate planet name to Russian, or pass through if unknown."""
    return _PLANET_RU.get(s, s)


# ── LLM Client ──────────────────────────────────────────────────────


class HoraryGenerationError(RuntimeError):
    """Raised when structured horary answer generation fails.

    Per docs/FAILURE_HANDLING_CANON.md and W-HORARY-ANSWER-QUALITY-V1,
    the service must mark the question failed and refund the credit
    instead of returning a generic fallback answer.
    """


# START_BLOCK: HORARY_NARRATIVE_CONTRACT
# The LLM writes ONLY the five narrative strings; every engine-owned
# field (verdict/confidence/testimonies/timing) is assembled by the
# backend verbatim from the HoraryAnalysis. Provider-enforced Structured
# Outputs (OpenRouter response_format json_schema, strict=true,
# provider.require_parameters=true) pin the wire shape AND the per-field
# minimum length (regex pattern derived from _HORARY_NARRATIVE_MIN_LENGTH
# — the single source of numbers); the local validator re-checks the
# same floors fail-closed regardless of provider.
_HORARY_NARRATIVE_FIELDS = (
    "lead",
    "significator_paragraph",
    "change_paragraph",
    "advice_callout",
    "final_summary",
)
_HORARY_NARRATIVE_MIN_LENGTH = {
    "lead": 60,
    "significator_paragraph": 60,
    "change_paragraph": 60,
    "advice_callout": 80,
    "final_summary": 60,
}
_HORARY_NARRATIVE_DESCRIPTIONS = {
    "lead": "Одно предложение — главный вывод по вопросу.",
    "significator_paragraph": "Что представляет пользователя и что — тему вопроса.",
    "change_paragraph": "Что может изменить исход.",
    "advice_callout": "Практический совет.",
    "final_summary": "Итоговое резюме.",
}


def _horary_narrative_pattern(field: str) -> str:
    """Newline-safe length pattern derived from the single floor map."""
    return rf"^[\s\S]{{{_HORARY_NARRATIVE_MIN_LENGTH[field]},}}$"


def _build_horary_narrative_json_schema() -> dict:
    """Build the strict schema from the floor map so the provider-enforced
    per-field minimums can never drift from the local validator."""
    return {
        "name": "horary_narrative",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                field: {
                    "type": "string",
                    "pattern": _horary_narrative_pattern(field),
                    "description": (
                        f"{_HORARY_NARRATIVE_DESCRIPTIONS[field]} "
                        f"Минимум {_HORARY_NARRATIVE_MIN_LENGTH[field]} символов."
                    ),
                }
                for field in _HORARY_NARRATIVE_FIELDS
            },
            "required": list(_HORARY_NARRATIVE_FIELDS),
            "additionalProperties": False,
        },
    }


_HORARY_NARRATIVE_JSON_SCHEMA = _build_horary_narrative_json_schema()


def _horary_narrative_requirements_prompt() -> str:
    """Russian length requirements line, derived from the same floor map."""
    parts = ", ".join(
        f"{field} — не короче {_HORARY_NARRATIVE_MIN_LENGTH[field]} символов"
        for field in _HORARY_NARRATIVE_FIELDS
    )
    return f"Требования к длине (строго): {parts}."


# END_BLOCK: HORARY_NARRATIVE_CONTRACT

class LLMService:

    def __init__(self):
        self.provider = settings.llm_provider

        if self.provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.anthropic_client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key
            )
        elif self.provider != "openrouter":
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _openrouter_generate(
        self, prompt: str, max_tokens: int, *, json_schema: dict | None = None
    ) -> str:
        body: dict = {
            "model": settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if json_schema is not None:
            # Provider-enforced Structured Outputs (Horary narrative and
            # natal report sections only;
            # ordinary calls keep the byte-identical body).
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}
            body["provider"] = {"require_parameters": True}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": settings.openrouter_site_url or "",
                    "X-Title": settings.openrouter_app_name,
                },
                json=body,
                timeout=60.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Structured-output refusal/empty shapes must not crash on
            # .strip() of a non-string; ordinary string content keeps the
            # byte-identical .strip() behavior.
            return content.strip() if isinstance(content, str) else ""

    async def _deepseek_generate(self, prompt: str, max_tokens: int) -> str:
        key = getattr(settings, "deepseek_api_key", None)
        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    async def _anthropic_generate(self, prompt: str, max_tokens: int) -> str:
        resp = self.anthropic_client.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    async def _generate_text(
        self, prompt: str, max_tokens: int, *, json_schema: dict | None = None
    ) -> str | None:
        """Generate text with fallback: OpenRouter → DeepSeek → None.

        json_schema (Horary narrative and natal report sections only) is
        enforced provider-side via
        OpenRouter Structured Outputs; the DeepSeek fallback always runs the
        plain prompt (no strict declaration without provider proof) — final
        local validation runs regardless of provider.
        """
        # 1. Primary: OpenRouter
        try:
            return await self._openrouter_generate(prompt, max_tokens, json_schema=json_schema)
        except Exception as e:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="LLM_CLIENT"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] OpenRouter failed: {type(e).__name__}",
                    payload={"reason": "timeout"},
                )

        # 2. Fallback: DeepSeek
        try:
            return await self._deepseek_generate(prompt, max_tokens)
        except Exception as e:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="LLM_CLIENT"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] DeepSeek fallback failed: {type(e).__name__}",
                    payload={"reason": "timeout"},
                )

        return None

    # ── Prompt helpers ──────────────────────────────────────────────

    def _build_signal_descriptions(self, signals: list, limit: int = 5) -> str:
        lines = []
        for s in signals[:limit]:
            p = _planet(s.planet)
            if s.type == "planet_in_house":
                h = _HOUSE_RU.get(s.house or 0, f"{s.house} дом")
                lines.append(
                    f"- {p} в {h} (сила {s.strength:.2f})"
                )
            elif s.type == "aspect" and s.aspect_type and s.target_planet:
                a = _ASPECT_RU.get(s.aspect_type, s.aspect_type)
                t = _planet(s.target_planet)
                lines.append(
                    f"- {p} в {a}е с {t} (орб {s.orb:.1f}°, сила {s.strength:.2f})"
                )
        return "\n".join(lines) if lines else "— нет ярко выраженных сигналов"

    def _build_sphere_descriptions(self, sphere_scores: dict) -> str:
        lines = []
        for s, v in sorted(sphere_scores.items(), key=lambda x: -x[1]):
            name = _SPHERE_RU.get(s, s)
            level = "сильное" if v >= 3 else ("среднее" if v >= 1 else "слабое")
            lines.append(f"- {name}: {level} влияние (балл: {v})")
        return "\n".join(lines) or "— нет данных по сферам"

    def _build_semantic_context(self, semantic_layer) -> str:
        # Handle both dict and Pydantic model
        if hasattr(semantic_layer, 'model_dump'):
            sl = semantic_layer.model_dump()
        elif isinstance(semantic_layer, dict):
            sl = semantic_layer
        else:
            return ""

        day_theme = sl.get("day_theme", "")
        sphere_themes = sl.get("sphere_themes", [])
        keywords = sl.get("top_keywords", sl.get("keywords", []))

        parts = []
        if day_theme:
            parts.append(f"Тема дня: {day_theme}")
        if sphere_themes:
            themes_text = ", ".join(
                f"{t.get('sphere', '')}: {t.get('theme', '')}"
                for t in sphere_themes[:4]
            )
            if themes_text.strip():
                parts.append(f"Темы сфер: {themes_text}")
        if keywords:
            parts.append(f"Ключевые слова: {', '.join(keywords[:6])}")
        return "\n".join(parts) if parts else ""

    # ── Generation methods ──────────────────────────────────────────

    # START_BLOCK: HEADLINE_GENERATION
    async def generate_headline(self, day_status: str, top_signals: list) -> str | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_headline
        # purpose: Generate a short headline for the day.
        # inputs: day_status (str), top_signals (list)
        # returns: str | None — headline text or None on failure
        # side_effects: calls external LLM provider
        # emitted_logs: llm.response_rejected on provider failure
        # error_behavior: returns None if all providers fail
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_headline
        signals_desc = self._build_signal_descriptions(top_signals, limit=3)

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты — астролог. Напиши короткий заголовок дня (одно предложение) для пользователя на «ты».

Статус дня: {day_status}

Топ-3 сигнала:
{signals_desc}

Правила:
- Одно предложение, до 12 слов
- Разговорный стиль, без клише и штампов
- Без англицизмов — все названия планет и аспектов на русском
- Конкретно, а не «сегодня хороший день»

Заголовок:"""

        return await self._generate_text(prompt, max_tokens=120)

    # END_BLOCK: HEADLINE_GENERATION

    # START_BLOCK: READING_GENERATION
    async def generate_reading(
        self, day_status: str, top_signals: list, sphere_scores: dict
    ) -> list[str] | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_reading
        # purpose: Generate full day reading paragraphs.
        # inputs: day_status (str), top_signals (list), sphere_scores (dict)
        # returns: list[str] | None — paragraph texts or None on failure
        # side_effects: calls external LLM provider
        # emitted_logs: llm.response_rejected on provider failure
        # error_behavior: returns None if all providers fail
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_reading
        signals_desc = self._build_signal_descriptions(top_signals, limit=5)
        spheres_desc = self._build_sphere_descriptions(sphere_scores)

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты — астролог. Напиши интерпретацию дня для пользователя на «ты».

Статус дня: {day_status}

Топ-5 сигналов:
{signals_desc}

Оценки сфер жизни:
{spheres_desc}

Правила:
- 2-3 параграфа
- Разговорный стиль, на «ты», без клише
- Конкретные рекомендации — что делать, как использовать энергии дня
- Без англицизмов — все названия на русском
- Фокус на практическое применение

Интерпретация:"""

        text = await self._generate_text(prompt, max_tokens=settings.llm_max_tokens)
        if not text:
            return None
        return [p.strip() for p in text.split("\n\n") if p.strip()][:3]

    # END_BLOCK: READING_GENERATION

    # START_BLOCK: NOTES_GENERATION
    async def generate_notes(
        self,
        day_status: str,
        sphere_scores: dict,
        semantic_layer: dict,
    ) -> str | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_notes
        # purpose: Generate notes block for "что сегодня важно учесть".
        # inputs: day_status (str), sphere_scores (dict), semantic_layer (dict)
        # returns: str | None — notes text or None on failure
        # side_effects: calls external LLM provider
        # emitted_logs: llm.response_rejected on provider failure
        # error_behavior: returns None if all providers fail
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_notes
        spheres_desc = self._build_sphere_descriptions(sphere_scores)
        sem_context = self._build_semantic_context(semantic_layer)

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты — астролог. Напиши блок «Сегодня важно учесть» для пользователя на «ты».

Статус дня: {day_status}

Оценки сфер:
{spheres_desc}

{sem_context}

Правила:
- 2-3 предложения, объединённых в один абзац
- Разговорный стиль, на «ты»
- Конкретные советы на сегодня
- Без англицизмов — всё на русском
- Никаких общих фраз вроде «прислушайся к себе»

Что сегодня важно учесть:"""

        return await self._generate_text(prompt, max_tokens=300)

    # ── Full context builder ────────────────────────────────────────

    def _build_full_context(
        self,
        natal: dict,
        top_signals: list,
        sphere_scores: dict,
        semantic_layer,
    ) -> str:
        """Build rich context for LLM — natal chart, ranked signals, grouping."""
        parts = []

        # 1. Natal chart
        parts.append("=== НАТАЛЬНАЯ КАРТА ===")
        natal_planets = natal.get("planets", [])
        for p in natal_planets:
            name = _planet(p.get("name", ""))
            sign = p.get("sign", "?")
            lon = p.get("longitude", 0)
            # Convert absolute longitude (0-360°) to zodiac degree (0-30° within sign)
            sign_deg = lon % 30
            parts.append(
                f"- {name}: {sign_deg:.1f}° {sign}"
            )

        # 2. Top transits (ranked by strength)
        parts.append("\n=== ТОП-ТРАНЗИТЫ (по силе) ===")
        for i, s in enumerate(top_signals[:5]):
            p = _planet(s.planet)
            if s.type == "planet_in_house":
                parts.append(
                    f"{i+1}. [сила {s.strength:.2f}] {p} в {s.house} доме"
                )
            elif s.type == "aspect" and s.aspect_type and s.target_planet:
                a = _ASPECT_RU.get(s.aspect_type, s.aspect_type)
                t = _planet(s.target_planet)
                parts.append(
                    f"{i+1}. [сила {s.strength:.2f}] {p} {a} {t} (орб {s.orb:.1f}°)"
                )

        # 3. Grouping
        parts.append("\n=== ГРУППИРОВКА ===")
        houses = [s for s in top_signals if s.type == "planet_in_house"]
        aspects = [s for s in top_signals if s.type == "aspect"]
        if houses:
            house_list = ", ".join(
                f"{_planet(s.planet)}({s.house} дом)" for s in houses
            )
            parts.append(f"Планеты в домах: {house_list}")
        if aspects:
            aspect_list = ", ".join(
                f"{_planet(s.planet)}-{_planet(s.target_planet or '?')} ({_ASPECT_RU.get(s.aspect_type or '', s.aspect_type or '')})"
                for s in aspects
            )
            parts.append(f"Аспекты: {aspect_list}")

        # 4. Sphere scores
        parts.append("\n=== СФЕРЫ ПО ВЛИЯНИЮ ===")
        for sphere, score in sorted(sphere_scores.items(), key=lambda x: -x[1]):
            name = _SPHERE_RU.get(sphere, sphere)
            level = "сильное" if score >= 3 else ("среднее" if score >= 1 else "слабое")
            parts.append(f"- {name}: {level} (балл {score})")

        # 5. Semantic layer
        sem = self._build_semantic_context(semantic_layer)
        if sem:
            parts.append(f"\n=== СЕМАНТИКА ===\n{sem}")

        return "\n".join(parts)

    # END_BLOCK: NOTES_GENERATION

    # ── Why sections generation (contexts pre-computed by SemanticService) ──

    # START_BLOCK: WHY_GENERATION
    async def generate_why_sections(
        self,
        contexts: list[dict],
        semantic_layer=None,
        evidence_packet: dict | None = None,
    ) -> list[dict] | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_why_sections
        # purpose: LLM writes narrative text for each pre-computed WhyThisHappens context.
        # inputs: contexts (list[dict]), semantic_layer (optional), evidence_packet (optional)
        # returns: list[dict] | None — sections with LLM text or None on failure
        # side_effects: calls external LLM provider
        # emitted_logs: llm.response_rejected on JSON parse failure or any
        #   schema violation (payload only reason=schema_invalid, never the
        #   raw model response)
        # error_behavior: returns None (never raises) when the LLM call fails,
        #   the JSON is malformed, the top level is not an object, sections is
        #   not a list, a consumed section is not an object, or an explicitly
        #   provided text value is not a non-blank string. Absent trailing
        #   sections and absent text fields keep the deterministic ctx
        #   fallback; a non-usable internal fallback also rejects the batch.
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_why_sections
        """LLM writes narrative text for each pre-computed context.
        All numbers, planets, houses are pre-computed — LLM cannot hallucinate."""

        # Build prompt with all 9 pre-filled contexts
        context_text = "\n\n".join(
            f"СЕКЦИЯ #{i+1}: {c['title']}\nДАННЫЕ: {c['context']}"
            for i, c in enumerate(contexts)
        )

        evidence_packet_str = ""
        if evidence_packet:
            evidence_packet_str = f"\nEVIDENCE PACKET:\n{json_lib.dumps(evidence_packet, ensure_ascii=False, indent=2)}\n"

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты — астролог. Напиши блок «Почему так у меня?».
{evidence_packet_str}
Это НЕ второй прогноз. Это ТЕХНИЧЕСКАЯ расшифровка: транзит → натальная точка → дом → орб → сила → смысл.

{context_text}

Для каждой секции напиши narrative текст на основе ДАННЫХ выше.
Верни ТОЛЬКО валидный JSON (без markdown):

{{
  "sections": [
    {{"id": "why-1", "text": "Главная тема дня — ..."}},
    {{"id": "why-2", "text": "Луна 18° Козерога проходит твой 8 дом и делает..."}},
    ...
    {{"id": "why-9", "text": "- Не принимай резких решений\\n- Зафиксируй договорённости\\n- Разгрузи тело"}}
  ]
}}

РОЛИ СЕКЦИЙ (строго соблюдай):
- 01: КОРОТКИЙ вывод — что за тон дня. Не перечисляй аспекты. 1-2 предложения.
- 02: ТОЛЬКО быстрые дневные факторы (Луна, быстрые транзиты). ОБЯЗАТЕЛЬНО градус, дом, орб.
- 03: ТОЛЬКО персональная натальная точка. Какая планета, в каком знаке/доме. Почему это НЕ общий прогноз.
- 04: ТОЛЬКО долгие/фоновые сигналы. Если их нет — честно напиши что фон построен по длительным транзитам.
- 05: ТОЛЬКО усиливающие факторы (напряжённые аспекты, повтор темы). Указывай орб/силу.
- 06: ТОЛЬКО смягчающие факторы (трины, секстили, поддержка). Указывай орб/силу.
- 07: ТОЛЬКО дома и сферы. НЕ повторяй аспекты. Объясни дома: что значит 8 дом, что значит 7 дом.
- 08: СИНТЕЗ, но НЕ повтор. Сведи воедино быстрый триггер + натальную точку + фон.
- 09: ТОЛЬКО действия. Без аспектов. 3-4 конкретных практических совета (bullets).

ЗАПРЕЩЕНО:
- Писать общие фразы без астрологических данных: «сегодня важны отношения», «планеты поддерживают»
- Использовать один и тот же аспект как главный аргумент в нескольких секциях
- Выдумывать планеты, градусы, аспекты — используй ТОЛЬКО данные выше
- Писать Transit_ или Natal_ в тексте
- Писать слово «Транзитный» или «натальный» в скобках при объяснении планеты — просто имя планеты
- Повторять основной разбор дня — это другой блок, не гороскоп
- Использовать именительный падеж после предлога «с»: правильно «с Юпитером», неправильно «с Юпитер»
- Писать сухо и энциклопедично — пользователь открыл бота в Telegram, он не астролог

ГРАММАТИКА (творительный падеж после «с»):
- Солнце → с Солнцем, Луна → с Луной
- Меркурий → с Меркурием, Венера → с Венерой
- Марс → с Марсом, Юпитер → с Юпитером
- Сатурн → с Сатурном, Уран → с Ураном
- Нептун → с Нептуном, Плутон → с Плутоном

ПЛАНЕТЫ — ЗА ЧТО ОТВЕЧАЮТ (для новичков, вплетай в текст ЕСТЕСТВЕННО, а не справочником):
- Солнце: жизненная сила, самооценка, воля, «я»
- Луна: эмоции, привычки, внутренний комфорт, бытовые реакции
- Меркурий: мышление, речь, коммуникации, документы, поездки
- Венера: любовь, красота, удовольствия, деньги, симпатии
- Марс: действие, энергия, конфликт, инициатива, желание
- Юпитер: рост, удача, смыслы, расширение горизонтов, оптимизм
- Сатурн: дисциплина, ограничения, зрелость, ответственность, структура
- Уран: неожиданность, свобода, прорыв, оригинальность, технологии
- Нептун: интуиция, иллюзии, вдохновение, размытость, духовность
- Плутон: трансформация, власть, кризис, глубина, перерождение

ДОМА — ЗА ЧТО ОТВЕЧАЮТ (вплетай в текст когда объясняешь активацию дома):
- 1 дом: личность, внешность, самоподача
- 2 дом: деньги, ресурсы, самооценка через материальное
- 3 дом: общение, учёба, братья/сёстры, ближние поездки
- 4 дом: дом, семья, корни, эмоциональная база
- 5 дом: творчество, радость, дети, романтика, игра
- 6 дом: работа, здоровье, порядок, обязанности
- 7 дом: партнёрство, брак, договорённости, открытые враги
- 8 дом: кризисы, чужие ресурсы, трансформация, секс, долги
- 9 дом: путешествия, высшее знание, убеждения, расширение
- 10 дом: карьера, статус, репутация, цели, отец
- 11 дом: друзья, сообщества, планы на будущее, единомышленники
- 12 дом: уединение, подсознание, тайное, завершение, отдых

ПИШИ ДЛЯ ЖИВОГО ЧЕЛОВЕКА — не энциклопедия, а разговор.
Пользователь НЕ знает астрологию. Он открыл бота из Telegram. Твоя задача —
объяснить почему день ощущается так, а не иначе, простым языком.

СТИЛЬ — ВОТ ТАК (это хороший пример, пиши похоже):
«Сегодня твоя Венера — а это планета любви, удовольствий и денег — соединяется
с твоим Юпитером. Юпитер отвечает за рост, удачу и расширение горизонтов.
Соединение двух таких планет в твоём третьем доме общения означает, что
деньги и симпатии могут прийти через разговор, сообщение или переговоры.
Поскольку Юпитер стоит в Весах, тема касается отношений и поиска баланса —
особенно в том, что касается твоих личных ценностей и удовольствий.»

ЧТО ДЕЛАТЬ В КАЖДОМ БЛОКЕ:
- Планету называешь → тут же объясняешь простыми словами: «Венера — планета любви и денег», «Сатурн — планета дисциплины и ответственности»
- Дом называешь → тут же расшифровываешь: «в твоём седьмом доме, который отвечает за партнёрство и брак»
- Аспект называешь → тут же поясняешь эффект: «квадратура — это напряжённый аспект, он создаёт трение и требует усилий»
- Строй фразу как причину: планета А (что это) + аспект (эффект) + планета Б (что это) + в доме (сфера жизни) → что это значит лично для человека сегодня
- Никаких скобок, никаких «Транзитный»/«натальный» — только живой текст
- Одно астрологическое понятие — одно предложение с объяснением

ДЛЯ НОВИЧКОВ — объясняй аспекты по-человечески при первом упоминании в секции:
- квадратура → «квадратура (трение, требует усилий)»
- оппозиция → «оппозиция (противостояние, нужен баланс)»
- трин → «трин (гармония, всё идёт легче)»
- секстиль → «секстиль (возможность, нужно приложить усилие)»
- соединение → «соединение (слияние энергий, усиление темы)»
Во второй раз в той же секции — без скобок.

ОБЯЗАТЕЛЬНО:
- В каждой секции 02-08 минимум ОДНА конкретная астрологическая деталь (планета, дом, градус, орб)
- Писать на «ты», без англицизмов
- Строить причинную цепочку: транзит → натальная точка → дом → орб → сила → смысл

JSON:"""

        text = await self._generate_text(prompt, max_tokens=2000)
        if not text:
            return None

        # Strip markdown
        for marker in ['```json', '```']:
            if marker in text:
                text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                break

        def _reject(exc_type: str) -> list[dict] | None:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="WHY_GENERATION"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] Rejected why-sections payload: {exc_type}",
                    # Never the raw model response — the rejection reason only.
                    payload={"reason": "schema_invalid"},
                )
            return None

        try:
            data = json_lib.loads(text)
        except json_lib.JSONDecodeError as e:
            return _reject(type(e).__name__)

        # Fail-closed schema boundary: the model may return valid JSON with
        # wrong TYPES (observed in release E2E 29894386844: sections[i].text
        # was a JSON array and text.split raised AttributeError -> /api/day
        # 500). Any explicitly provided wrong type or blank text rejects the
        # whole batch; absent trailing sections and absent text fields keep
        # the deterministic ctx fallback below.
        if not isinstance(data, dict):
            return _reject("top_level_not_object")
        llm_sections = data.get("sections", [])
        if not isinstance(llm_sections, list):
            return _reject("sections_not_list")
        for section in llm_sections[: len(contexts)]:
            if not isinstance(section, dict):
                return _reject("section_not_object")
            if "text" in section:
                value = section["text"]
                if not isinstance(value, str) or not value.strip():
                    return _reject("text_not_nonblank_string")

        # Merge pre-computed metadata with LLM text
        sections = []
        for i, ctx in enumerate(contexts):
            if i < len(llm_sections):
                candidate = llm_sections[i].get("text")
                chosen = candidate if isinstance(candidate, str) and candidate.strip() else ctx["context"]
            else:
                # Missing trailing section: deterministic fallback (unchanged).
                chosen = ctx["context"]
            if not isinstance(chosen, str) or not chosen.strip():
                # Internal deterministic fallback must itself be usable;
                # otherwise fail closed instead of emitting empty text.
                return _reject("empty_fallback_context")
            blocks = []
            if ctx["blocks_kind"] == "bullets":
                items = [line.strip("- ") for line in chosen.split("\n") if line.strip()]
                if items:
                    blocks.append({"kind": "bullets", "items": items})
                else:
                    blocks.append({"kind": "paragraph", "text": chosen})
            else:
                blocks.append({"kind": "paragraph", "text": chosen})

            sections.append({
                "id": f"why-{i+1}",
                "layer": ctx["layer"],
                "title": ctx["title"],
                "blocks": blocks,
            })

        return sections
    # END_BLOCK: WHY_GENERATION

    # ── Important today details ─────────────────────────────────────

    # START_BLOCK: IMPORTANT_TODAY_GENERATION
    async def generate_important_today_details(
        self,
        items: list[dict],
        context: dict,
    ) -> list[dict] | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_important_today_details
        # purpose: LLM fills meaning/why_important/personal_context for each pre-computed item.
        # inputs: items (list[dict]), context (dict)
        # returns: list[dict] | None — items with LLM text or None on failure
        # side_effects: calls external LLM provider
        # emitted_logs: llm.response_rejected on JSON parse failure
        # error_behavior: returns None if LLM fails or JSON parse fails
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_important_today_details
        """LLM fills meaning/why_important/personal_context for each item.
        Events, times, planets, houses are already set by code — LLM only adds text."""

        items_json = json_lib.dumps(items, ensure_ascii=False, indent=2)
        context_json = json_lib.dumps(context, ensure_ascii=False, indent=2)

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты пишешь раскрытие для блока «Сегодня важно учесть».

События уже рассчитаны кодом. Нельзя добавлять новые события, менять время, планеты, дома, орбы или количество дней.

Для каждого item заполни:
- meaning: что это значит астрологически;
- why_important: почему это важно для действий сегодня;
- personal_context: как это проявляется у пользователя через дом/сферу/главные сигналы.

Пиши коротко: 1–2 предложения на каждое поле.
Не используй англицизмы.
Не используй служебные имена Transit_ / Natal_.
Верни ТОЛЬКО валидный JSON (без markdown):

{{
  "items": [
    {{
      "id": "retro_mercury",
      "details": {{
        "meaning": "...",
        "why_important": "...",
        "personal_context": "..."
      }}
    }}
  ]
}}

События:
{items_json}

Контекст дня:
{context_json}

JSON:"""

        text = await self._generate_text(prompt, max_tokens=800)
        if not text:
            return None

        # Strip markdown code blocks
        for marker in ['```json', '```']:
            if marker in text:
                parts = text.split(marker, 1)
                if len(parts) > 1:
                    text = parts[1].rsplit('```', 1)[0].strip()
                break

        try:
            data = json_lib.loads(text)
            return data.get("items", [])
        except json_lib.JSONDecodeError as e:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="IMPORTANT_TODAY"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] Failed to parse important-today details JSON: {type(e).__name__}",
                    payload={"reason": "schema_invalid"},
                )
            return None
    # END_BLOCK: IMPORTANT_TODAY_GENERATION

    # ── Horary generation ──────────────────────────────────────────


    async def generate_horary_answer(
        self,
        question_text: str,
        category: str | None,
        analysis,
    ) -> dict:
        # START_FUNCTION_CONTRACT: LLMService.generate_horary_answer
        # purpose: Produce the public 8-block horary answer. The LLM writes
        #          ONLY five narrative strings (lead / significator paragraph /
        #          change paragraph / advice callout / final summary) through
        #          provider-enforced Structured Outputs (OpenRouter
        #          response_format json_schema strict + require_parameters);
        #          the backend assembles the 8 blocks in fixed order with ALL
        #          engine-owned fields (verdict, confidence, testimonies,
        #          timing) taken verbatim from the HoraryAnalysis — no
        #          LLM-substituted verdict/evidence/timing ever.
        # inputs:
        #   - question_text (str)
        #   - category (str | None)
        #   - analysis (HoraryAnalysis with verdict, confidence, testimonies,
        #     timing, warnings)
        # returns:
        #   - dict with key "blocks" -> list of 8 block dicts (fixed order)
        # side_effects:
        #   - calls external LLM provider (OpenRouter / DeepSeek fallback)
        # emitted_logs:
        #   - llm.response_rejected per rejected attempt with a sanitized
        #     reject code (empty/parse/type/missing/quality/provider); payload
        #     carries only reason=schema_invalid (never raw model/user text)
        # error_behavior:
        #   - raises HoraryGenerationError on 2 failed attempts (no fallback
        #     answer; the service keeps the honest failed/refund path)
        # END_FUNCTION_CONTRACT: LLMService.generate_horary_answer
        from app.schemas.horary_analysis import HoraryAnalysis

        if not isinstance(analysis, HoraryAnalysis):
            raise TypeError("analysis must be a HoraryAnalysis instance")

        verdict = analysis.verdict
        verdict_ru = {"yes": "да", "no": "нет", "maybe": "возможно"}.get(verdict, "возможно")

        evidences_for = [
            self._format_evidence(e) for e in analysis.testimonies_for
        ]
        evidences_against = [
            self._format_evidence(e) for e in analysis.testimonies_against
        ]
        neutrals = [self._format_evidence(e) for e in analysis.neutral_factors]
        warnings = list(analysis.calculation_warnings)

        system_prompt = (
            f"{_ASTRO_BOUNDARY_RULES}\n\n"
            "Ты — астролог, отвечающий на хорарный вопрос. Стиль: разговорный, "
            "на «ты», без англицизмов. Планеты и дома называй по-русски.\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Используй ТОЛЬКО астрологические факты из раздела «СВИДЕТЕЛЬСТВА».\n"
            "- НЕ выдумывай аспекты, дома, орбы, фазы или причины.\n"
            "- Если в свидетельствах чего-то нет — не упоминай это.\n"
            "- Вердикт, уверенность, свидетельства и срок УЖЕ вычислены движком.\n"
            "- Твоя задача — ТОЛЬКО живой русский narrative для пяти полей JSON.\n"
            "- Все имена планет — на русском, в творительном падеже после «с».\n"
            "- Верни ТОЛЬКО валидный JSON без markdown-обёрток.\n"
        )

        timing_block = self._format_timing(analysis.timing)

        user_prompt = (
            f"Вопрос: {question_text}\n"
            f"Категория: {category or 'не указана'}\n"
            f"Вердикт движка: {verdict_ru} ({verdict})\n"
            f"Уровень уверенности движка (low|medium|high): {analysis.confidence_label} "
            f"({analysis.confidence_score}/100)\n"
            f"Пояснение движка: {analysis.confidence_explanation}\n"
            f"Задействованные планеты: "
            f"{', '.join(_PLANET_RU.get(p, p) for p in analysis.involved_planets)}\n\n"
            "СВИДЕТЕЛЬСТВА «ЗА»:\n"
            f"{evidences_for or '— нет'}\n\n"
            "СВИДЕТЕЛЬСТВА «ПРОТИВ»:\n"
            f"{evidences_against or '— нет'}\n\n"
            "НЕЙТРАЛЬНЫЕ ФАКТОРЫ:\n"
            f"{neutrals or '— нет'}\n\n"
            f"СРОК ПО КАРТЕ:\n{timing_block}\n\n"
            f"ПРЕДУПРЕЖДЕНИЯ ДВИЖКА:\n"
            f"{chr(10).join(warnings) if warnings else '— нет'}\n\n"
            "Верни ТОЛЬКО валидный JSON РОВНО с пятью строковыми полями:\n"
            "{\n"
            '  "lead": "одно предложение — главный вывод по вопросу",\n'
            '  "significator_paragraph": "что представляет пользователя и что — тему вопроса",\n'
            '  "change_paragraph": "что может изменить исход",\n'
            '  "advice_callout": "практический совет",\n'
            '  "final_summary": "итоговое резюме"\n'
            "}\n\n"
            f"{_horary_narrative_requirements_prompt()}\n"
            "Не переопределяй и не пересчитывай вердикт, уверенность и срок "
            "движка: narrative только поясняет их, без других чисел, процентов "
            "и иных выводов."
        )

        prompt = f"{system_prompt}\n\n{user_prompt}"

        last_reject_code = "unknown"
        for attempt in range(2):
            try:
                text = await self._generate_text(
                    prompt,
                    max_tokens=1800,
                    json_schema=_HORARY_NARRATIVE_JSON_SCHEMA,
                )
            except Exception as e:
                last_reject_code = "provider"
                self._log_horary_reject(attempt, "provider", type(e).__name__)
                continue
            if not text:
                last_reject_code = "empty"
                self._log_horary_reject(attempt, "empty")
                continue
            for marker in ['```json', '```']:
                if marker in text:
                    text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                    break
            try:
                data = json_lib.loads(text)
            except json_lib.JSONDecodeError:
                last_reject_code = "parse"
                self._log_horary_reject(attempt, "parse")
                continue
            narrative, reject_code = self._validate_horary_narrative(data)
            if narrative is None:
                last_reject_code = reject_code
                self._log_horary_reject(attempt, reject_code)
                continue
            return {"blocks": self._assemble_horary_blocks(analysis, narrative)}

        raise HoraryGenerationError(
            f"horary answer generation failed after 2 attempts: {last_reject_code}"
        )

    @staticmethod
    def _log_horary_reject(attempt: int, code: str, detail: str | None = None) -> None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE._log_horary_reject
        # purpose: Emit the canonical per-attempt rejection with a sanitized
        #   reject code (empty/parse/type/missing/quality/provider). The msg
        #   distinguishes reject classes without raw model/user content; the
        #   payload stays reason=schema_invalid only.
        # inputs: attempt (0-based), code (sanitized), detail (exception type
        #   name only, never a message).
        # returns: None.
        # side_effects: structured log event.
        # emitted_logs: llm.response_rejected.
        # error_behavior: never raises.
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE._log_horary_reject
        suffix = f" ({detail})" if detail else ""
        with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="HORARY_GENERATION"):
            log_event(
                "llm.response_rejected",
                level="warn",
                msg=f"[Horary LLM] Attempt {attempt + 1} rejected: {code}{suffix}",
                payload={"reason": "schema_invalid"},
            )

    @staticmethod
    def _validate_horary_narrative(data) -> tuple[dict | None, str]:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE._validate_horary_narrative
        # purpose: Validate the raw parsed narrative object: it must be a dict
        #   with EXACTLY the five narrative fields, every value a non-blank
        #   string meeting the narrative quality floor. Returns the sanitized
        #   narrative dict plus an empty code, or (None, reject_code) with
        #   code in {type, missing, quality}.
        # inputs: data — parsed JSON value from the LLM response.
        # returns: (narrative | None, reject_code).
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: never raises.
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE._validate_horary_narrative
        if not isinstance(data, dict):
            return None, "type"
        if set(data.keys()) != set(_HORARY_NARRATIVE_FIELDS):
            return None, "missing"
        narrative: dict = {}
        for field_name in _HORARY_NARRATIVE_FIELDS:
            value = data[field_name]
            if not isinstance(value, str):
                return None, "type"
            value = value.strip()
            if len(value) < _HORARY_NARRATIVE_MIN_LENGTH[field_name]:
                return None, "quality"
            narrative[field_name] = value
        return narrative, ""

    @staticmethod
    def _assemble_horary_blocks(analysis, narrative: dict) -> list[dict]:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE._assemble_horary_blocks
        # purpose: Assemble the public 8 horary blocks in fixed order. ALL
        #   engine-owned fields are taken verbatim from the HoraryAnalysis:
        #   verdict/confidence/labels/explanation; testimony
        #   title/explanation/weight/planets/aspectType/orb; timing status.
        #   timeRange is exposed ONLY for status=known so the internal
        #   category hint (e.g. "weeks-months") never leaks when unclear.
        #   timing text is honestly augmented with the computed basis when
        #   the basis is not already part of the text. Assembled blocks are
        #   re-validated against the shared public contract as
        #   defense-in-depth.
        # inputs: analysis (HoraryAnalysis), narrative (validated 5 fields).
        # returns: ordered list of 8 public block dicts.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HoraryGenerationError (no raw leak) if the
        #   assembled blocks violate the public contract — an internal bug,
        #   never model input.
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE._assemble_horary_blocks
        timing = analysis.timing
        timing_text = timing.text.strip()
        basis = (timing.basis or "").strip()
        if basis and basis.lower() not in timing_text.lower():
            timing_text = f"{timing_text} Основание: {basis}."

        def _testimony(item) -> dict:
            return {
                "title": item.title,
                "explanation": item.explanation,
                "weight": item.weight,
                "planets": list(item.planets_involved),
                "aspectType": item.aspect_type,
                "orb": item.orb,
            }

        blocks = [
            {
                "type": "verdict_card",
                "verdict": analysis.verdict,
                "confidence": analysis.confidence_score / 100.0,
                "label": None,
                "confidenceLabel": analysis.confidence_label,
                "confidenceExplanation": analysis.confidence_explanation,
            },
            {"type": "lead", "text": narrative["lead"]},
            {"type": "paragraph", "text": narrative["significator_paragraph"]},
            {
                "type": "testimonies",
                "prosLabel": "Свидетельства «за»",
                "consLabel": "Свидетельства «против»",
                "neutralLabel": "Нейтральные факторы",
                "pros": [_testimony(e) for e in analysis.testimonies_for],
                "cons": [_testimony(e) for e in analysis.testimonies_against],
                "neutral": [_testimony(e) for e in analysis.neutral_factors],
            },
            {"type": "paragraph", "text": narrative["change_paragraph"]},
            {
                "type": "timing",
                "status": timing.status,
                "timeRange": timing.time_range if timing.status == "known" else None,
                "text": timing_text,
            },
            {
                "type": "callout",
                "tone": "insight",
                "title": "Совет",
                "text": narrative["advice_callout"],
            },
            {"type": "paragraph", "text": narrative["final_summary"]},
        ]
        LLMService._validate_horary_blocks(blocks)
        return blocks

    @staticmethod
    def _format_evidence(item) -> str:
        planets = ", ".join(_PLANET_RU.get(p, p) for p in item.planets_involved)
        aspect = f", аспект {item.aspect_type}" if item.aspect_type else ""
        orb = f", орб {item.orb:.1f}°" if item.orb is not None else ""
        return (
            f"- {item.title}\n"
            f"  {item.explanation}\n"
            f"  (планеты: {planets}{aspect}{orb}, вес: {item.weight:+.2f})"
        )

    @staticmethod
    def _format_timing(timing) -> str:
        range_str = f", диапазон: {timing.time_range}" if timing.time_range else ""
        basis = f"\n  Основание: {timing.basis}" if timing.basis else ""
        return (
            f"Статус: {timing.status}{range_str}\n"
            f"Текст для пользователя: {timing.text}{basis}"
        )

    @staticmethod
    def _validate_horary_blocks(blocks: list) -> bool:
        """Defense-in-depth: validate the ASSEMBLED blocks against the shared
        public HoraryBlock contract (e.g. every testimony item requires
        weight). A violation means an internal assembly bug, never model
        input — the pydantic error text (which embeds input fragments) is
        converted to the domain error WITHOUT chaining, so no raw content
        leaks."""
        if not isinstance(blocks, list):
            raise HoraryGenerationError("assembled blocks must be a list")
        try:
            validate_horary_llm_blocks(blocks)
        except ValidationError:
            raise HoraryGenerationError("assembled blocks failed public schema validation") from None
        return True

    # START_BLOCK: CONCRETE_ADVICE_GENERATION
    async def generate_concrete_advice(
        self,
        contexts: list[dict],
        evidence_packet: dict | None = None,
    ) -> dict[str, str] | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_concrete_advice
        # purpose: Generate Russian text recommendations for 12 canonical spheres.
        # inputs: contexts (list[dict]), evidence_packet (dict | None)
        # returns: dict[str, str] | None — map of product key -> recommendation text
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_concrete_advice
        context_lines = []
        for ctx in contexts:
            key = ctx.get("key")
            label = ctx.get("label")
            verdict = ctx.get("verdict")
            evidence_desc = []
            for ev in ctx.get("evidence", []):
                evidence_desc.append(f"{ev.get('kind')}: {ev.get('title')}")
            evidence_str = "; ".join(evidence_desc) if evidence_desc else "нет"
            context_lines.append(
                f"- Сфера: {label} (ключ: {key}), Вердикт: {verdict}, Доказательства: {evidence_str}"
            )

        evidence_packet_str = ""
        if evidence_packet:
            evidence_packet_str = f"\nEVIDENCE PACKET:\n{json_lib.dumps(evidence_packet, ensure_ascii=False, indent=2)}\n"

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты — профессиональный астрологический копирайтер. Напиши краткие практичные рекомендации на русском языке на «ты» для пользователя на основе переданных астрологических данных.
{evidence_packet_str}
Данные по 12 сферам жизни:
{"\n".join(context_lines)}

Правила:
1. Твой ответ должен быть строго валидным JSON-объектом, содержащим ровно те же 12 ключей сфер, которые переданы во входных данных.
2. Значение для каждого ключа должно быть одной емкой строкой-рекомендацией на русском языке.
3. Каждое предложение должно содержать от 7 до 18 слов.
4. Используй обращение на «ты» (например, «действуй», «сократи», «перепроверь»).
5. Не используй латиницу (английские слова) в рекомендациях.
6. Не выдумывай планеты, аспекты или дома, которых нет в доказательствах для конкретной сферы.
7. Если вердикт для сферы равен "avoid", рекомендация должна советовать отложить дела, ограничить активность или соблюдать осторожность. Избегай призывов к активным действиям или инициативам (например, не пиши "активно общайся" или "начинай"). Разрешены смягчающие формулировки вроде "если нужно..., то только в коротком/спокойном формате".
8. Не добавляй никаких других символов или текста вокруг JSON.

Верни JSON-объект ровно такого вида:
{{
  "work": "<русский текст>",
  "money": "<русский текст>",
  "documents": "<русский текст>",
  "relationships": "<русский текст>",
  "sport": "<русский текст>",
  "communication": "<русский текст>",
  "health": "<русский текст>",
  "decisions": "<русский текст>",
  "travel": "<русский текст>",
  "creativity": "<русский текст>",
  "study": "<русский текст>",
  "shopping": "<русский текст>"
}}

Твой JSON-ответ:"""

        # 12 short recommendations need more than the old 1500 budget: a
        # truncated response loses the closing brace and is unparseable
        # (observed in release E2E run 29890349759: 1083 chars, no final "}").
        # Only THIS output budget is raised; every other LLM budget is untouched.
        response_text = await self._generate_text(prompt, max_tokens=2400)
        if not response_text:
            return None

        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json_lib.loads(cleaned)
        except Exception as e:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="CONCRETE_ADVICE"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] Failed to parse concrete advice JSON: {type(e).__name__}",
                    # Never log the raw model response (may carry unvalidated
                    # user-facing text); the rejection reason only.
                    payload={"reason": "schema_invalid"},
                )
            return None
    # END_BLOCK: CONCRETE_ADVICE_GENERATION

    # START_BLOCK: PLANET_INTERPRETATION_GENERATION
    async def generate_planet_interpretations(
        self,
        planets_context: list[dict],
    ) -> dict[str, str] | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_planet_interpretations
        # purpose: Generate Russian text interpretations for transit planets.
        # inputs: planets_context (list[dict])
        # returns: dict[str, str] | None — map of planet name -> interpretation text
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_planet_interpretations
        context_lines = []
        for ctx in planets_context:
            name = ctx.get("name")
            sign = ctx.get("sign")
            house = ctx.get("house")
            aspects = ", ".join(ctx.get("aspects", [])) or "нет"
            context_lines.append(
                f"- Планета: {name}, Положение: в знаке {sign}, в {house} доме, Аспекты: {aspects}"
            )

        prompt = f"""{_ASTRO_BOUNDARY_RULES}

Ты — профессиональный астролог. Напиши краткие емкие интерпретации положения планет на сегодня на русском языке на «ты» для пользователя.

Положения планет и их аспекты:
{"\n".join(context_lines)}

Правила:
1. Твой ответ должен быть строго валидным JSON-объектом, содержащим ключи — названия планет на английском (например, "Sun", "Moon", "Mercury", и т.д.), которые переданы во входных данных.
2. Значение для каждого ключа должно быть короткой интерпретацией на русском языке (1-2 предложения, до 25 слов).
3. Не используй латиницу (английские слова) в текстах описаний. Все названия знаков, планет и аспектов переводи на русский.
4. Опиши характер влияния планеты в этом доме/знаке и её аспектов на сегодняшний день.
5. Не добавляй никаких других символов или текста вокруг JSON.

Пример ответа:
{{
  "Sun": "Солнце в первом доме усиливает твою личность и витальность. Квадратура к Марсу предупреждает об излишней импульсивности — направь энергию в спорт.",
  "Moon": "Луна в четвертом доме обращает твое внимание на дом и семью. Гармоничные аспекты помогают наладить уют и душевный контакт с близкими."
}}

Твой JSON-ответ:"""

        response_text = await self._generate_text(prompt, max_tokens=2000)
        if not response_text:
            return None

        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json_lib.loads(cleaned)
        except Exception as e:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="PLANET_INTERPRETATION"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] Failed to parse planet interpretations JSON: {type(e).__name__}",
                    payload={"response": response_text},
                )
            return None
    # END_BLOCK: PLANET_INTERPRETATION_GENERATION
