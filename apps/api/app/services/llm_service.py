# ############################################################################
# AI_HEADER: MODULE_LLM_SERVICE
# ROLE: LLM integration for generating astrological interpretations.
# DEPENDENCIES: anthropic, httpx, app.core.config
# GRACE_ANCHORS: [HEADLINE_GENERATION, READING_GENERATION, LLM_CLIENT]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-SERVICE
# purpose: Generate headline and reading paragraphs from scoring results using
#   LLM API (Anthropic Claude or OpenRouter).
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
#   - httpx (for OpenRouter API)
#   - M-CONFIG (settings.llm_provider, settings.llm_model, settings.llm_max_tokens)
# invariants:
#   - API key must be set for selected provider (raises ValueError if empty)
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
#   - LLM_CLIENT: unified client for Anthropic and OpenRouter
#   - HEADLINE_GENERATION: build prompt and call LLM API for headline
#   - READING_GENERATION: build prompt and call LLM API for reading
# owned_tests:
#   - apps/api/tests/test_llm_service.py
# END_MODULE_MAP

from __future__ import annotations

import logging

import anthropic
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# START_BLOCK: LLM_CLIENT
class LLMService:
    """LLM service for generating astrological interpretations."""

    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.llm_model

        if self.provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.anthropic_client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key
            )
            logger.info(f"[LLM] Initialized Anthropic client with model {self.model}")

        elif self.provider == "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY not set")
            self.openrouter_base_url = settings.openrouter_base_url
            self.openrouter_api_key = settings.openrouter_api_key
            logger.info(f"[LLM] Initialized OpenRouter client with model {self.model}")

        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _generate_text(self, prompt: str, max_tokens: int) -> str:
        """
        Generate text using configured LLM provider.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if self.provider == "anthropic":
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()

        elif self.provider == "openrouter":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.openrouter_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": settings.openrouter_site_url or "",
                        "X-Title": settings.openrouter_app_name,
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()

                return data["choices"][0]["message"]["content"].strip()

        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
# END_BLOCK: LLM_CLIENT


# START_BLOCK: HEADLINE_GENERATION

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

        headline = await self._generate_text(prompt, max_tokens=100)
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

        text = await self._generate_text(prompt, max_tokens=settings.llm_max_tokens)

        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        return paragraphs[:3]  # Max 3 paragraphs
# END_BLOCK: READING_GENERATION
