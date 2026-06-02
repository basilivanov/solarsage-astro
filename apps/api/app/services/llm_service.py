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

    # ── Why sections generation (contexts pre-computed by SemanticService) ──

    async def generate_why_sections(
        self,
        contexts: list[dict],
        semantic_layer=None,
    ) -> list[dict] | None:
        """LLM writes narrative text for each pre-computed context.
        All numbers, planets, houses are pre-computed — LLM cannot hallucinate."""
        
        # Build prompt with all 9 pre-filled contexts
        context_text = "\n\n".join(
            f"СЕКЦИЯ #{i+1}: {c['title']}\nДАННЫЕ: {c['context']}"
            for i, c in enumerate(contexts)
        )

        prompt = f"""Ты — астролог. Напиши блок «Почему так у меня?».

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
- Писать Transit_ или Natal_ в тексте — только чистые названия: «Луна», «натальный Меркурий»
- Повторять основной разбор дня — это другой блок, не гороскоп
- Использовать именительный падеж после предлога «с»: правильно «с Юпитером», «с Сатурном», неправильно «с Юпитер», «с Сатурн»

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

ПИШИ ДЛЯ ЖИВОГО ЧЕЛОВЕКА — не энциклопедия, а разговор на кухне:
- Когда впервые упоминаешь планету в секции — одной фразой объясни за что она отвечает, без слова «отвечает». Пример: «Луна (твои эмоции и привычки) в квадратуре с Сатурном (дисциплина и границы) — поэтому сегодня внутреннее раздражение встречается с необходимостью держать себя в руках».
- Не перечисляй все планеты подряд — только те, что реально действуют в этой секции.
- Не используй слово «архетип» и «сигнификатор».
- Строй фразу как причину: планета А (за что) + аспект + планета Б (за что) → что это значит лично для человека.

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

        try:
            data = json_lib.loads(text)
            llm_sections = data.get("sections", [])

            # Merge pre-computed metadata with LLM text
            sections = []
            for i, ctx in enumerate(contexts):
                text = llm_sections[i].get("text", ctx["context"]) if i < len(llm_sections) else ctx["context"]
                blocks = []
                if ctx["blocks_kind"] == "bullets":
                    items = [line.strip("- ") for line in text.split("\n") if line.strip()]
                    if items:
                        blocks.append({"kind": "bullets", "items": items})
                    else:
                        blocks.append({"kind": "paragraph", "text": text})
                else:
                    blocks.append({"kind": "paragraph", "text": text})

                sections.append({
                    "id": f"why-{i+1}",
                    "layer": ctx["layer"],
                    "title": ctx["title"],
                    "blocks": blocks,
                })

            return sections
        except (json_lib.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning(f"[LLM] Failed to parse why-sections JSON: {text[:200]}... error={e}")
            return None

    # ── Important today details ─────────────────────────────────────

    async def generate_important_today_details(
        self,
        items: list[dict],
        context: dict,
    ) -> list[dict] | None:
        """LLM fills meaning/why_important/personal_context for each item.
        Events, times, planets, houses are already set by code — LLM only adds text."""

        items_json = json_lib.dumps(items, ensure_ascii=False, indent=2)
        context_json = json_lib.dumps(context, ensure_ascii=False, indent=2)

        prompt = f"""Ты пишешь раскрытие для блока «Сегодня важно учесть».

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
            logger.warning(f"[LLM] Failed to parse important-today details JSON: {text[:200]}... error={e}")
            return None
