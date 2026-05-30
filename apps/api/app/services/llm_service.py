# ############################################################################
# AI_HEADER: MODULE_LLM_SERVICE
# ROLE: LLM integration for generating astrological interpretations.
# DEPENDENCIES: anthropic, app.core.config
# GRACE_ANCHORS: [HEADLINE_GENERATION, READING_GENERATION]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-SERVICE
# purpose: Generate headline and reading paragraphs from scoring results using
#   Anthropic Claude API.
# owns:
#   - apps/api/app/services/llm_service.py
# inputs:
#   - day_status: "supportive" | "steady" | "tense"
#   - top_signals: list[AstroSignal]
#   - sphere_scores: dict[str, int]
# outputs:
#   - headline: str (one sentence, max 10 words)
#   - reading: list[str] (2-3 paragraphs)
# dependencies:
#   - anthropic (Claude API client)
#   - M-CONFIG (settings.anthropic_api_key, settings.llm_model, settings.llm_max_tokens)
# invariants:
#   - ANTHROPIC_API_KEY must be set (raises ValueError if empty)
#   - headline is always a single sentence
#   - reading contains 2-3 paragraphs
# failure_policy:
#   - missing API key → ValueError at init
#   - API error → propagates to caller (500)
# non_goals:
#   - no caching (deferred)
#   - no prompt versioning (deferred)
#   - no streaming (deferred)
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-LLM-SERVICE
# public_entrypoints:
#   - LLMService.generate_headline
#   - LLMService.generate_reading
# semantic_blocks:
#   - HEADLINE_GENERATION: build prompt and call Claude API for headline
#   - READING_GENERATION: build prompt and call Claude API for reading
# owned_tests:
#   - apps/api/tests/test_llm_service.py
# END_MODULE_MAP

from __future__ import annotations

import anthropic

from app.core.config import settings


# START_BLOCK: HEADLINE_GENERATION
class LLMService:
    """LLM service for generating astrological interpretations."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def generate_headline(
        self,
        day_status: str,
        top_signals: list,
    ) -> str:
        """
        Generate headline from day_status and top signals.

        Args:
            day_status: "supportive" | "steady" | "tense"
            top_signals: List of top AstroSignal

        Returns:
            Headline string (one sentence)
        """
        # Build prompt from top 3 aspect signals
        signals_desc = "\n".join([
            f"- {s.planet} {s.aspect_type} {s.target_planet} (orb: {s.orb:.1f}°, strength: {s.strength:.2f})"
            for s in top_signals[:3] if s.type == "aspect"
        ])

        prompt = f"""Ты — астролог. Создай короткий заголовок (одно предложение) для дня со статусом "{day_status}".

Топ-3 аспекта:
{signals_desc}

Требования:
- Одно предложение, максимум 10 слов
- Разговорный стиль, без клише
- Отражает статус дня ({day_status})

Заголовок:"""

        response = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        headline = response.content[0].text.strip()
        return headline
# END_BLOCK: HEADLINE_GENERATION


# START_BLOCK: READING_GENERATION
    async def generate_reading(
        self,
        day_status: str,
        top_signals: list,
        sphere_scores: dict,
    ) -> list[str]:
        """
        Generate reading paragraphs from scoring results.

        Args:
            day_status: "supportive" | "steady" | "tense"
            top_signals: List of top AstroSignal
            sphere_scores: Dict of sphere scores

        Returns:
            List of 2-3 paragraphs
        """
        # Build prompt from top 5 aspect signals
        signals_desc = "\n".join([
            f"- {s.planet} {s.aspect_type} {s.target_planet} (orb: {s.orb:.1f}°, strength: {s.strength:.2f})"
            for s in top_signals[:5] if s.type == "aspect"
        ])

        spheres_desc = "\n".join([
            f"- {sphere}: {score}"
            for sphere, score in sphere_scores.items()
        ])

        prompt = f"""Ты — астролог. Создай интерпретацию дня для пользователя.

Статус дня: {day_status}

Топ-5 аспектов:
{signals_desc}

Оценки сфер:
{spheres_desc}

Требования:
- 2-3 параграфа
- Разговорный стиль, без клише
- Конкретные рекомендации
- Фокус на практическое применение

Интерпретация:"""

        response = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()

        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        return paragraphs[:3]  # Max 3 paragraphs
# END_BLOCK: READING_GENERATION
