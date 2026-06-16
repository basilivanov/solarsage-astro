# ############################################################################
# AI_HEADER: LLM_CLIENT — HTTP client mixin for LLM providers
# ROLE: Provides _openrouter_generate, _deepseek_generate, _anthropic_generate,
#       and _generate_text (with OpenRouter → DeepSeek → None fallback).
#       Used via multiple inheritance by LLMService.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Low-level HTTP generation against OpenRouter, DeepSeek, Anthropic.
# inputs: self.provider, self.anthropic_client (set by LLMService.__init__)
# returns: generated text strings or None on total failure
# side_effects: HTTP calls to external LLM APIs
# emitted_logs: llm.response_rejected on provider failure
# error_behavior: returns None if all providers fail; raises ValueError on
#   missing API keys
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - class: LLMClientMixin
#     methods:
#       - _openrouter_generate
#       - _deepseek_generate
#       - _anthropic_generate
#       - _generate_text
# END_MODULE_MAP

from __future__ import annotations

import anthropic
import httpx

from app.core.config import settings
from app.core.logging import log_event, log_block


class LLMClientMixin:

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
