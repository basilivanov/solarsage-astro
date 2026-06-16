# ############################################################################
# AI_HEADER: LLM_HORARY — horary answer generation mixin
# ROLE: Provides HoraryGenerationError and the async generate_horary_answer
#       method with validation helpers. Used via multiple inheritance by LLMService.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Structured horary answer generation via LLM with retry and validation.
# inputs: question_text, category, HoraryAnalysis instance
# returns: dict with "blocks" key containing validated block list
# side_effects: calls external LLM provider (up to 2 attempts)
# emitted_logs: llm.response_rejected on each failed attempt
# error_behavior: raises HoraryGenerationError after 2 failed attempts
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - class: HoraryGenerationError
#   - class: LLMHoraryMixin
#     methods:
#       - generate_horary_answer
#       - _format_evidence (static)
#       - _format_timing (static)
#       - _validate_horary_blocks (static)
# END_MODULE_MAP

from __future__ import annotations

import json as json_lib

from app.core.logging import log_event, log_block

from .russian import _PLANET_RU


class HoraryGenerationError(RuntimeError):
    """Raised when structured horary answer generation fails.

    Per docs/FAILURE_HANDLING_CANON.md and W-HORARY-ANSWER-QUALITY-V1,
    the service must mark the question failed and refund the credit
    instead of returning a generic fallback answer.
    """


class LLMHoraryMixin:

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
                with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="HORARY_GENERATION"):
                    log_event(
                        "llm.response_rejected",
                        level="warn",
                        msg=f"[Horary LLM] Attempt {attempt+1} failed: {type(e).__name__}",
                        payload={"reason": "schema_invalid"},
                    )
                continue
            except Exception as e:
                last_error = e
                with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="HORARY_GENERATION"):
                    log_event(
                        "llm.response_rejected",
                        level="warn",
                        msg=f"[Horary LLM] Attempt {attempt+1} error: {type(e).__name__}",
                        payload={"reason": "timeout"},
                    )
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
