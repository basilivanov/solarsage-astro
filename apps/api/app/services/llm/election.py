# ############################################################################
# AI_HEADER: MODULE_SERVICES_LLM_ELECTION
# ROLE: LLM narrative generator for election date search
# DEPENDENCIES: app.services.llm.client, app.schemas.election
# GRACE_ANCHORS: [LLM_ELECTION]
# ############################################################################

# START_MODULE_CONTRACT: M-SERVICES-LLM-ELECTION
# purpose: Generate structured RU narrative for election search results using LLM client.
# owns:
#   - apps/api/app/services/llm/election.py
# inputs: event_label (str), best_days (list[dict]), avoid_days (list[dict]), personal_facts (dict)
# outputs: dict representation of ElectionNarrative
# dependencies:
#   - M-LLM-CLIENT (LLMClient)
#   - M-SCHEMAS-ELECTION (validate_election_narrative)
# side_effects: calls OpenRouter via LLMClient (up to 2 attempts)
# emitted_logs: llm.requested, llm.response_validated, llm.response_rejected
# failure_policy: raises RuntimeError if LLM fails 2 attempts
# END_MODULE_CONTRACT: M-SERVICES-LLM-ELECTION

# START_MODULE_MAP: M-SERVICES-LLM-ELECTION
# public_entrypoints:
#   - generate_election_narrative
# semantic_blocks:
#   - LLM_ELECTION: Structured prompt assembly & retry logic
# END_MODULE_MAP: M-SERVICES-LLM-ELECTION

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.logging import log_event, log_block
from app.schemas.election import validate_election_narrative
from app.services.llm_service import LLMService

ELECTION_NARRATIVE_JSON_SCHEMA: dict[str, Any] = {
    "name": "election_narrative",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "hero_reason": {
                "type": "string",
                "description": "1-2 предложения: почему лучший день подходит под событие (только по фактам)"
            },
            "hero_personal": {
                "type": "string",
                "description": "1-2 предложения: связка дня с натальной Луной юзера"
            },
            "hero_plain": {
                "type": "string",
                "description": "1-2 предложения простыми словами про знак Луны и жизненный смысл"
            },
            "hero_hours": {
                "type": "string",
                "description": "1 предложение про лучшие часы (из voc_intervals или чистый день)"
            },
            "day_notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "note": {"type": "string"}
                    },
                    "required": ["date", "note"],
                    "additionalProperties": False
                },
                "description": "Ровно по одному элементу на каждый лучший день в том же порядке"
            },
            "avoid_notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "note": {"type": "string"}
                    },
                    "required": ["date", "note"],
                    "additionalProperties": False
                },
                "description": "Ровно по одному элементу на каждый нерекомендуемый день в том же порядке"
            }
        },
        "required": [
            "hero_reason",
            "hero_personal",
            "hero_plain",
            "hero_hours",
            "day_notes",
            "avoid_notes"
        ],
        "additionalProperties": False
    }
}


_SIGN_PREPOSITIONAL = {
    "aries": "в Овне", "taurus": "в Тельце", "gemini": "в Близнецах",
    "cancer": "в Раке", "leo": "во Льве", "virgo": "в Деве",
    "libra": "в Весах", "scorpio": "в Скорпионе", "sagittarius": "в Стрельце",
    "capricorn": "в Козероге", "aquarius": "в Водолее", "pisces": "в Рыбах",
}


def _build_prompt(
    event_label: str,
    best_days: list[dict[str, Any]],
    avoid_days: list[dict[str, Any]],
    personal_facts: dict[str, Any],
) -> str:
    lines = [
        "Ты — опытный астролог-элективщик. Твоя задача — составить понятное, тёплое описание подбора дат для пользователя.",
        "Аудитория — люди без глубокого астрологического бэкграунда. Пиши простым, уверенным и доброжелательным языком.",
        "СТРОГИЕ ПРАВИЛА:",
        "1. Запрещено использовать термины 'хорар', 'элекция', 'элективная астрология'.",
        "2. Запрещено выдумывать любые астрологические факты (знаки, фазы, аспекты). Используй ТОЛЬКО переданные факты.",
        "3. В day_notes должны быть записи строго для дат из списков best_days в том же порядке.",
        "4. В avoid_notes должны быть записи строго для дат из списков avoid_days в том же порядке.",
        "5. VOC интервалы — это периоды ХОЛОСТОГО КУРСА Луны: в это время начинать дела НЕ стоит. "
        "hero_hours называет удачное время ВНЕ этих интервалов (или что весь день чист, если интервалов нет). "
        "НИКОГДА не называй VOC-часы удачными.",
        "6. hero_reason обязан называть знак Луны и фазу лучшего дня (из фактов), без общих фраз «астрологические принципы».",
        "7. Знаки зодиака в текстах — в предложном падеже («в Раке», «в Тельце», «в Весах»...), формы даны в фактах.",
        "",
        f"СОБЫТИЕ: {event_label}",
        f"НАТАЛЬНАЯ ЛУНА ПОЛЬЗОВАТЕЛЯ: {personal_facts.get('natal_moon_sign_ru') or 'Не указана'} (Резонанс с лучшим днём: {personal_facts.get('resonates', False)})",
        "",
        "ЛУЧШИЕ ДНИ (best_days):",
    ]

    def _day_line(d: dict[str, Any]) -> str:
        sign = (d.get("moon_sign") or "").lower()
        sign_prep = _SIGN_PREPOSITIONAL.get(sign, sign)
        phase = d.get("phase_pct")
        phase_txt = f"{phase}%" if phase is not None else ("растущая" if d.get("waxing") else "убывающая")
        return (
            f"- Дата: {d['date']}, Луна {sign_prep} ({d.get('moon_sign_ru')}), фаза: {phase_txt}, "
            f"VOC интервалы (холостой курс, плохое время) UTC: {d.get('voc_intervals')}, "
            f"Причины: {'; '.join(d.get('reasons', []))}"
        )

    for d in best_days:
        lines.append(_day_line(d))

    lines.append("")
    lines.append("НЕ РЕКОМЕНДУЕМЫЕ ДНИ (avoid_days):")
    for d in avoid_days:
        lines.append(_day_line(d))

    return "\n".join(lines)


async def generate_election_narrative(
    event_label: str,
    best_days: list[dict[str, Any]],
    avoid_days: list[dict[str, Any]],
    personal_facts: dict[str, Any],
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-SERVICES-LLM-ELECTION.generate_election_narrative
    # purpose: Call LLM to generate structured RU narrative for election search.
    # inputs: event_label, best_days, avoid_days, personal_facts
    # returns: dict matching ElectionNarrative
    # error_behavior: raises RuntimeError on 2 failed attempts
    # END_FUNCTION_CONTRACT: F-M-SERVICES-LLM-ELECTION.generate_election_narrative
    prompt = _build_prompt(event_label, best_days, avoid_days, personal_facts)
    expected_best_dates = [d["date"] for d in best_days]
    expected_avoid_dates = [d["date"] for d in avoid_days]

    llm_service = LLMService()
    last_error: Exception | None = None

    for attempt in range(1, 3):
        with log_block(slice="W-ELECTION", module="M-SERVICES-LLM-ELECTION", block="LLM_ELECTION"):
            log_event("llm.requested", payload={"attempt": attempt, "service": "election"})
            try:
                raw_json = await llm_service._generate_text(
                    prompt, 1000, json_schema=ELECTION_NARRATIVE_JSON_SCHEMA
                )
                if not raw_json:
                    raise RuntimeError("Empty response from LLM")

                narrative_dict = json.loads(raw_json)
                fallback_notes = {
                    d["date"]: "; ".join(d.get("reasons", []))
                    for d in [*best_days, *avoid_days]
                }
                validated = validate_election_narrative(
                    narrative_dict,
                    expected_best_dates=expected_best_dates,
                    expected_avoid_dates=expected_avoid_dates,
                    fallback_notes=fallback_notes,
                )
                log_event("llm.response_validated", payload={"service": "election"})
                return validated.model_dump()
            except Exception as exc:
                last_error = exc
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"Election narrative attempt {attempt} failed: {exc}",
                    payload={"attempt": attempt, "error": str(exc)},
                )

    raise RuntimeError(f"Election narrative generation failed after 2 attempts: {last_error}")
