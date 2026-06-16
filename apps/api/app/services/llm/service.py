# ############################################################################
# AI_HEADER: LLM_SERVICE — main LLMService class composing mixins
# ROLE: Provides headline, reading, notes, why-sections, important-today
#       generation methods. Inherits HTTP client, prompt-building, and
#       horary methods from mixins.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Main LLMService class for astrological text generation.
# inputs: day_status, top_signals, sphere_scores, semantic_layer, natal context
# returns: str | None (headline, notes), list[str] | None (reading),
#          list[dict] | None (why-sections, important-today), dict (horary)
# side_effects: calls external LLM provider
# emitted_logs: llm.response_rejected on provider failure
# error_behavior: returns None if all providers fail;
#   raises HoraryGenerationError if horary fails after 2 attempts
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - class: LLMService
#     methods:
#       - __init__
#       - generate_headline
#       - generate_reading
#       - generate_notes
#       - generate_why_sections
#       - generate_important_today_details
# END_MODULE_MAP

from __future__ import annotations

import json as json_lib

import anthropic

from app.core.config import settings
from app.core.logging import log_event, log_block

from .client import LLMClientMixin
from .prompts import LLMPromptMixin
from .horary import LLMHoraryMixin
from .russian import _planet, _ASPECT_RU, _HOUSE_RU, _SPHERE_RU


class LLMService(LLMClientMixin, LLMPromptMixin, LLMHoraryMixin):

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
    # END_BLOCK: NOTES_GENERATION

    # ── Why sections generation (contexts pre-computed by SemanticService) ──

    # START_BLOCK: WHY_GENERATION
    async def generate_why_sections(
        self,
        contexts: list[dict],
        semantic_layer=None,
    ) -> list[dict] | None:
        # START_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_why_sections
        # purpose: LLM writes narrative text for each pre-computed WhyThisHappens context.
        # inputs: contexts (list[dict]), semantic_layer (optional)
        # returns: list[dict] | None — sections with LLM text or None on failure
        # side_effects: calls external LLM provider
        # emitted_logs: llm.response_rejected on JSON parse failure
        # error_behavior: returns None if LLM fails or JSON parse fails
        # END_FUNCTION_CONTRACT: F-M-LLM-SERVICE.generate_why_sections
        """LLM writes narrative text for each pre-computed context.
        All numbers, planets, houses are pre-computed — LLM cannot hallucinate."""

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

        for marker in ['```json', '```']:
            if marker in text:
                text = text.split(marker, 1)[1].rsplit('```', 1)[0].strip()
                break

        try:
            data = json_lib.loads(text)
            llm_sections = data.get("sections", [])

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
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="WHY_GENERATION"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] Failed to parse why-sections JSON: {type(e).__name__}",
                    payload={"reason": "schema_invalid"},
                )
            return None
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
