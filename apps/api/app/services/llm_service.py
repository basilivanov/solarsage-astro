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


class HoraryGenerationError(RuntimeError):
    """Raised when structured horary answer generation fails.

    Per docs/FAILURE_HANDLING_CANON.md and W-HORARY-ANSWER-QUALITY-V1,
    the service must mark the question failed and refund the credit
    instead of returning a generic fallback answer.
    """


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

    # ── Horary generation ──────────────────────────────────────────

    async def generate_horary_answer(
        self,
        question_text: str,
        category: str | None,
        analysis,
    ) -> dict:
        # START_FUNCTION_CONTRACT: LLMService.generate_horary_answer
        # purpose: Build a horary LLM prompt from a structured analysis and
        #          parse the response. Returns the validated blocks dict.
        # inputs:
        #   - question_text (str)
        #   - category (str | None)
        #   - analysis (HoraryAnalysis with verdict, confidence, testimonies,
        #     timing, warnings)
        # returns:
        #   - dict with key "blocks" -> list of block dicts
        # side_effects:
        #   - calls external LLM provider (OpenRouter / DeepSeek / Anthropic)
        # emitted_logs:
        #   - warnings on each failed parse attempt
        # error_behavior:
        #   - raises HoraryGenerationError on 2 failed attempts (no fallback)
        # END_FUNCTION_CONTRACT: LLMService.generate_horary_answer
        from app.schemas.horary_analysis import (
            EvidenceItem,
            HoraryAnalysis,
            TimingInfo,
        )

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
            "Ты — астролог, отвечающий на хорарный вопрос. Стиль: разговорный, "
            "на «ты», без англицизмов. Планеты и дома называй по-русски.\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Используй ТОЛЬКО астрологические факты из раздела «СВИДЕТЕЛЬСТВА».\n"
            "- НЕ выдумывай аспекты, дома, орбы, фазы или причины.\n"
            "- Если в свидетельствах чего-то нет — не упоминай это.\n"
            "- Срок реализации (timing) бери ТОЛЬКО из раздела «СРОК ПО КАРТЕ».\n"
            "- Не выдумывай временной диапазон. Если статус timing "
            "«not_enough_evidence», timeRange НЕ указывай.\n"
            "- Все имена планет — на русском, в творительном падеже после «с».\n"
            "- Верни ТОЛЬКО валидный JSON без markdown-обёрток.\n\n"
            "Обязательная структура blocks (порядок важен):\n"
            "1. verdict_card — verdict, confidence 0..1, label (короткая подпись),\n"
            "   confidenceLabel (low|medium|high), confidenceExplanation (1-2 предложения).\n"
            "2. lead — одно предложение, главный вывод.\n"
            "3. paragraph — что представляет пользователя и что — тему вопроса.\n"
            "4. testimonies — prosLabel='Свидетельства «за»',\n"
            "   consLabel='Свидетельства «против»', neutralLabel='Нейтральные факторы'.\n"
            "   В pros/cons/neutral клади [{title, explanation, weight, planets, aspectType, orb}].\n"
            "   Не повторяй pros в cons.\n"
            "5. paragraph — что может изменить исход.\n"
            "6. timing — status: 'known'|'unclear'|'not_enough_evidence'.\n"
            "   timeRange: только если status='known'. text — всегда.\n"
            "7. callout (tone='insight', title='Совет') — практический совет.\n"
            "8. paragraph — итоговое резюме."
        )

        timing_block = self._format_timing(analysis.timing)

        user_prompt = (
            f"Вопрос: {question_text}\n"
            f"Категория: {category or 'не указана'}\n"
            f"Вердикт движка: {verdict_ru} ({verdict})\n"
            f"Уровень уверенности движка: {analysis.confidence_label} "
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
            "Верни ТОЛЬКО валидный JSON со схемой:\n"
            "{\n"
            "  \"blocks\": [\n"
            "    {\"type\": \"verdict_card\", \"verdict\": \"yes|no|maybe\",\n"
            "     \"confidence\": 0.0-1.0, \"label\": \"...\",\n"
            "     \"confidenceLabel\": \"low|medium|high\",\n"
            "     \"confidenceExplanation\": \"...\"},\n"
            "    {\"type\": \"lead\", \"text\": \"...\"},\n"
            "    {\"type\": \"paragraph\", \"text\": \"...\"},\n"
            "    {\"type\": \"testimonies\",\n"
            "     \"prosLabel\": \"...\", \"consLabel\": \"...\", \"neutralLabel\": \"...\",\n"
            "     \"pros\": [{\"title\": \"...\", \"explanation\": \"...\",\n"
            "                \"weight\": 0.0, \"planets\": [\"...\"], \"aspectType\": \"...\", \"orb\": 0.0}],\n"
            "     \"cons\": [{\"title\": \"...\", \"explanation\": \"...\",\n"
            "                \"weight\": 0.0, \"planets\": [\"...\"], \"aspectType\": \"...\", \"orb\": 0.0}],\n"
            "     \"neutral\": [{\"title\": \"...\", \"explanation\": \"...\",\n"
            "                   \"weight\": 0.0, \"planets\": [], \"aspectType\": null, \"orb\": null}]},\n"
            "    {\"type\": \"paragraph\", \"text\": \"...\"},\n"
            "    {\"type\": \"timing\", \"status\": \"known|unclear|not_enough_evidence\",\n"
            "     \"timeRange\": \"...\" | null, \"text\": \"...\"},\n"
            "    {\"type\": \"callout\", \"tone\": \"insight\", \"title\": \"Совет\", \"text\": \"...\"},\n"
            "    {\"type\": \"paragraph\", \"text\": \"...\"}\n"
            "  ]\n"
            "}"
        )

        prompt = f"{system_prompt}\n\n{user_prompt}"

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                text = await self._generate_text(prompt, max_tokens=1800)
                if not text:
                    last_error = HoraryGenerationError("LLM returned empty response")
                    continue
                for marker in ['```json', '```']:
                    if marker in text:
                        text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                        break
                data = json_lib.loads(text)
                if not isinstance(data, dict) or "blocks" not in data:
                    raise HoraryGenerationError("LLM response missing 'blocks'")
                if not isinstance(data["blocks"], list):
                    raise HoraryGenerationError("LLM response 'blocks' is not a list")
                if not self._validate_horary_blocks(data["blocks"]):
                    raise HoraryGenerationError("LLM response failed block schema validation")
                return data
            except (json_lib.JSONDecodeError, HoraryGenerationError) as e:
                last_error = e
                logger.warning(f"[Horary LLM] Attempt {attempt+1} failed: {e}")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"[Horary LLM] Attempt {attempt+1} error: {e}")
                continue

        raise HoraryGenerationError(
            f"horary answer generation failed after 2 attempts: {last_error}"
        )

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
        """Validate that LLM-produced blocks contain the required types and
        the required fields per type. Does not invent missing data — simply
        fails the request so the service marks it failed."""
        if not isinstance(blocks, list):
            raise HoraryGenerationError("LLM response 'blocks' is not a list")
        if len(blocks) < 7:
            raise HoraryGenerationError("LLM response must contain at least 7 blocks")

        types_seen: set[str] = set()
        paragraph_count = 0

        for b in blocks:
            if not isinstance(b, dict) or "type" not in b:
                raise HoraryGenerationError("LLM block must be an object with a type")
            t = b["type"]
            types_seen.add(t)

            if t == "verdict_card":
                if b.get("verdict") not in ("yes", "no", "maybe"):
                    raise HoraryGenerationError("verdict_card.verdict is invalid")
                if not isinstance(b.get("confidence"), (int, float)):
                    raise HoraryGenerationError("verdict_card.confidence must be numeric")
                if not (0.0 <= float(b["confidence"]) <= 1.0):
                    raise HoraryGenerationError("verdict_card.confidence must be between 0 and 1")
                if b.get("confidenceLabel") not in ("low", "medium", "high"):
                    raise HoraryGenerationError("verdict_card.confidenceLabel is invalid")
                if not isinstance(b.get("confidenceExplanation"), str):
                    raise HoraryGenerationError("verdict_card.confidenceExplanation must be a string")
                if len(b["confidenceExplanation"].strip()) < 60:
                    raise HoraryGenerationError("verdict_card.confidenceExplanation is too short")
            elif t == "lead":
                if not isinstance(b.get("text"), str):
                    raise HoraryGenerationError("lead.text must be a string")
                if len(b["text"].strip()) < 60:
                    raise HoraryGenerationError("lead.text is too short")
            elif t == "paragraph":
                if not isinstance(b.get("text"), str):
                    raise HoraryGenerationError("paragraph.text must be a string")
                if b["text"].strip():
                    paragraph_count += 1
            elif t == "timing":
                if b.get("status") not in ("known", "unclear", "not_enough_evidence"):
                    raise HoraryGenerationError("timing.status is invalid")
                if not isinstance(b.get("text"), str):
                    raise HoraryGenerationError("timing.text must be a string")
                if len(b["text"].strip()) < 60:
                    raise HoraryGenerationError("timing.text is too short")
                if b["status"] == "known" and not b.get("timeRange"):
                    raise HoraryGenerationError("timing.timeRange is required for known status")
            elif t == "callout":
                if not isinstance(b.get("text"), str):
                    raise HoraryGenerationError("callout.text must be a string")
                if len(b["text"].strip()) < 80:
                    raise HoraryGenerationError("callout.text is too short")
            elif t == "testimonies":
                for bucket in ("pros", "cons", "neutral"):
                    items = b.get(bucket) or []
                    if not isinstance(items, list):
                        raise HoraryGenerationError(f"testimonies.{bucket} must be a list")
                    for it in items:
                        if not isinstance(it, dict):
                            raise HoraryGenerationError(f"testimonies.{bucket} item must be an object")
                        if not isinstance(it.get("title"), str):
                            raise HoraryGenerationError(f"testimonies.{bucket} item title must be a string")
                        if not isinstance(it.get("explanation"), str):
                            raise HoraryGenerationError(f"testimonies.{bucket} item explanation must be a string")
                        if not it["explanation"].strip():
                            raise HoraryGenerationError(f"testimonies.{bucket} item explanation must not be empty")

        required = {"verdict_card", "lead", "testimonies", "timing", "callout"}
        if not required.issubset(types_seen):
            raise HoraryGenerationError("LLM response is missing required horary blocks")
        if paragraph_count < 2:
            raise HoraryGenerationError("LLM response must contain at least 2 paragraph blocks")
        return True
