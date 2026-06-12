# ############################################################################
# AI_HEADER: MODULE_LLM_CLIENT
# ROLE: LLM HTTP client — OpenRouter, DeepSeek, Anthropic providers
# DEPENDENCIES: anthropic, httpx, app.core.config
# GRACE_ANCHORS: [OPENROUTER_CLIENT, DEEPSEEK_CLIENT, ANTHROPIC_CLIENT, LLM_CLIENT_FALLBACK]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-CLIENT
# purpose: Provide HTTP/SDK client for LLM providers with fallback chain.
# owns:
#   - apps/api/app/services/llm/client.py
# inputs:
#   - prompt (str), max_tokens (int)
# outputs:
#   - str | None (generated text)
# dependencies:
#   - M-CONFIG (settings)
#   - anthropic, httpx
# side_effects:
#   - HTTP requests to OpenRouter / DeepSeek / Anthropic
# invariants:
#   - falls back through providers: OpenRouter → DeepSeek → None
# failure_policy:
#   - returns None if all providers fail
#   - raises HoraryGenerationError if horary fails after 2 attempts
# non_goals:
#   - no streaming (MVP uses synchronous generation)
# END_MODULE_CONTRACT: M-LLM-CLIENT

# START_MODULE_MAP: M-LLM-CLIENT
# public_entrypoints:
#   - LLMClient._generate_text
# semantic_blocks:
#   - OPENROUTER_CLIENT: primary provider
#   - DEEPSEEK_CLIENT: first fallback
#   - ANTHROPIC_CLIENT: second fallback
#   - LLM_CLIENT_FALLBACK: fallback chain logic
# END_MODULE_MAP: M-LLM-CLIENT

from __future__ import annotations

import anthropic
import httpx

from app.core.config import settings
from app.core.logging import log_event, log_block


class HoraryGenerationError(RuntimeError):
    """Raised when structured horary answer generation fails.

    Per docs/FAILURE_HANDLING_CANON.md and W-HORARY-ANSWER-QUALITY-V1,
    the service must mark the question failed and refund the credit
    instead of returning a generic fallback answer.
    """


class LLMClient:

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
        try:
            return await self._openrouter_generate(prompt, max_tokens)
        except Exception as e:
            with log_block(slice="W-5.1", module="M-LLM-SERVICE", block="LLM_CLIENT"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=f"[LLM] OpenRouter failed: {type(e).__name__}",
                    payload={"reason": "timeout"},
                )

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
