# ############################################################################
# AI_HEADER: MODULE_LLM_SERVICE
# ROLE: LLM integration — headline, reading, notes, why-sections
# DEPENDENCIES: anthropic, httpx, app.core.config
# GRACE_ANCHORS: [HEADLINE_GENERATION, READING_GENERATION, NOTES_GENERATION, WHY_GENERATION, LLM_CLIENT]
# ############################################################################

from __future__ import annotations

import json as json_lib
import logging

import anthropic
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

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

    async def _openrouter_generate(self, prompt: str, max_tokens: int) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": settings.openrouter_site_url or "",
                    "X-Title": settings.openrouter_app_name,
                },
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

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

    async def _generate_text(self, prompt: str, max_tokens: int) -> str | None:
        """Generate text with fallback: OpenRouter → DeepSeek → None."""
        # 1. Primary: OpenRouter
        try:
            return await self._openrouter_generate(prompt, max_tokens)
        except Exception as e:
            logger.warning(f"[LLM] OpenRouter failed: {e}")

        # 2. Fallback: DeepSeek
        try:
            return await self._deepseek_generate(prompt, max_tokens)
        except Exception as e:
            logger.warning(f"[LLM] DeepSeek fallback failed: {e}")

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

    async def generate_headline(self, day_status: str, top_signals: list) -> str | None:
        signals_desc = self._build_signal_descriptions(top_signals, limit=3)

        prompt = f"""Ты — астролог. Напиши короткий заголовок дня (одно предложение) для пользователя на «ты».

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

    async def generate_reading(
        self, day_status: str, top_signals: list, sphere_scores: dict
    ) -> list[str] | None:
        signals_desc = self._build_signal_descriptions(top_signals, limit=5)
        spheres_desc = self._build_sphere_descriptions(sphere_scores)

        prompt = f"""Ты — астролог. Напиши интерпретацию дня для пользователя на «ты».

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

    async def generate_notes(
        self,
        day_status: str,
        sphere_scores: dict,
        semantic_layer: dict,
    ) -> str | None:
        spheres_desc = self._build_sphere_descriptions(sphere_scores)
        sem_context = self._build_semantic_context(semantic_layer)

        prompt = f"""Ты — астролог. Напиши блок «Сегодня важно учесть» для пользователя на «ты».

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

    # ── Why sections generation ─────────────────────────────────────

    async def generate_why_sections(
        self,
        day_status: str,
        top_signals: list,
        sphere_scores: dict,
        semantic_layer,
        natal: dict | None = None,
    ) -> list[dict] | None:
        full_context = self._build_full_context(
            natal or {}, top_signals, sphere_scores, semantic_layer
        )

        prompt = f"""Ты — астролог. Объясни пользователю на «ты», почему сегодняшний день именно такой.

Статус дня: {day_status}

{full_context}

Верни ТОЛЬКО валидный JSON, без markdown-блоков и пояснений. Структура ЖЁСТКАЯ — ровно 9 секций:


{{
  "sections": [
    {{"id": "why-1", "layer": "main_theme", "title": "Главная тема дня", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-2", "layer": "daily_layer", "title": "Быстрый слой дня", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-3", "layer": "personal_activation", "title": "Почему это задевает именно тебя", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-4", "layer": "period_background", "title": "Фон периода", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-5", "layer": "amplifiers", "title": "Что усиливает этот день", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-6", "layer": "softeners", "title": "Что смягчает этот день", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-7", "layer": "manifestation_zones", "title": "Через какие сферы это проявляется", "blocks": [{{"kind": "bullets", "items": ["сфера 1", "сфера 2"]}}]}},
    {{"id": "why-8", "layer": "astrological_meaning", "title": "Астрологический смысл дня", "blocks": [{{"kind": "paragraph", "text": "..."}}]}},
    {{"id": "why-9", "layer": "practical_meaning", "title": "Что это значит практически", "blocks": [{{"kind": "bullets", "items": ["совет 1", "совет 2", "совет 3"]}}]}}
  ],
  "keyInsight": "Одно предложение — ключ дня"
}}

Требования к каждой секции:
- 01 main_theme: о чём день в целом, какая ось/конфликт/гармония задаёт тон. НАЗОВИ доминирующую планету и точный аспект из входных данных.
- 02 daily_layer: быстрые транзиты, Луна, смена знаков — что меняется в течение дня. УКАЖИ положения Луны и быстрых планет цифрами (градусы, время).
- 03 personal_activation: почему это задевает ИМЕННО этого пользователя. НАЗОВИ какие натальные планеты активированы какими транзитными аспектами. УКАЖИ дома и градусы.
- 04 period_background: профекции, соляр, дирекции — фон периода (год/месяц/неделя). Свяжи с конкретными домами и планетами из натала.
- 05 amplifiers: что усиливает день. ПЕРЕЧИСЛИ ретро-планеты поименно, лунные фазы, стеллиумы — с названиями.
- 06 softeners: что смягчает день. НАЗОВИ гармоничные аспекты — какие планеты в трине/секстиле, с какими орбисами.
- 07 manifestation_zones: через какие дома/сферы всё проявляется (bullets!). УКАЖИ номера домов и их значение.
- 08 astrological_meaning: астрологический смысл — это день пересборки или прорыва? Свяжи с конкретными конфигурациями из входных данных.
- 09 practical_meaning: что делать практически (bullets — 3-4 конкретных совета, привязанных к астрологическим фактам дня)

Правила:
- Разговорный стиль, на «ты»
- Без англицизмов — все названия планет, аспектов, домов на русском
- Каждая секция ОБЯЗАНА использовать конкретные названия планет, градусов, домов из входных данных
- Запрещены общие фразы без астрологических деталей
- Не выдумывай планеты, аспекты и градусы — используй ТОЛЬКО те что есть во входных данных
- Градусы всегда указывай в формате «19.9° Овна», а не «319.9°»
- keyInsight — короткое предложение, ключ дня
- В секции 09 ОБЯЗАТЕЛЬНО bullets, не paragraphs

JSON:"""

        text = await self._generate_text(prompt, max_tokens=2000)
        if not text:
            return None

        # Strip markdown code blocks (LLMs often wrap JSON in ```json ... ```)
        for marker in ['{\n', '{', '```json', '```']:
            text = text.strip()
        for marker in ['```json', '```']:
            if marker in text:
                text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                break

        try:
            data = json_lib.loads(text)
            return data.get("sections", [])
        except json_lib.JSONDecodeError as e:
            logger.warning(f"[LLM] Failed to parse why-sections JSON: {text[:300]}... error={e}")
            return None
