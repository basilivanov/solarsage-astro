# ############################################################################
# AI_HEADER: MODULE_LLM_CLAIM_VALIDATOR — validates and sanitizes LLM texts.
# ROLE: LLMClaimValidator — enforces doc-15 hard guards for advice rows.
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-CLAIM-VALIDATOR
# purpose: Validate and sanitize LLM-generated advice texts against hard guards.
# owns:
#   - apps/api/app/services/llm_claim_validator.py
# inputs: row_key, verdict, text, evidence
# outputs: sanitized text or None
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants: unsafe texts are rejected or replaced, never passed through
# failure_policy: returns None for texts that must be rejected completely
# END_MODULE_CONTRACT: M-LLM-CLAIM-VALIDATOR

# START_MODULE_MAP: M-LLM-CLAIM-VALIDATOR
# public_entrypoints:
#   - LLMClaimValidator.validate_concrete_advice_text
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-LLM-CLAIM-VALIDATOR

from __future__ import annotations
from app.schemas.today import ConcreteAdviceEvidence

BANNED_ASTRO_STEMS: list[str] = ["транзит", "аспект", "орб", "натал", "планет"]


def has_banned_jargon(text: str, row_key: str = "") -> bool:
    """Check text for banned astrology terms or abstract filler phrases."""
    t = text.lower()
    for stem in BANNED_ASTRO_STEMS:
        if stem in t:
            return True
    if "день складывается" in t:
        return True
    if "энерги" in t and row_key not in ("sport", "health"):
        return True
    if "важные аспекты" in t or "активные аспекты" in t:
        return True
    return False


class LLMClaimValidator:
    def validate_concrete_advice_text(
        self,
        *,
        row_key: str,
        verdict: str,
        text: str,
        evidence: list[ConcreteAdviceEvidence],
    ) -> str | None:
        """Validate generated text for a row domain against its verdict. W-6.

        Returns:
            Sanitized or replacement text if unsafe, or the original text if safe.
            None only if the text should be rejected completely.
        """
        text_lower = text.lower()

        # Hard guard 1: relationships + avoid -> direct relationship improvement / conflict-opening advice
        if row_key == "relationships" and verdict == "avoid":
            unsafe_keywords = [
                "выяснять отношения", "выясняй", "разбирай", "обсуди", "поговори",
                "улучши", "улучшать", "выяснения", "конфликт", "спор"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return "Если контакт неизбежен, выбирай короткий спокойный формат и не разбирай острые темы."

        # Hard guard 2: money + avoid -> invest/spend/buy recommendation
        if row_key == "money" and verdict == "avoid":
            unsafe_keywords = [
                "инвестируй", "инвестиции", "покупай", "покупка", "тратить", "потрать",
                "купи", "вкладывай", "вложения"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return "Для финансовых решений день не подходит, отложи крупные покупки и инвестиции."

        # Hard guard 3: sport/health + avoid -> intense sport recommendation
        if row_key in ("sport", "health") and verdict == "avoid":
            unsafe_keywords = [
                "интенсивный", "тяжелый", "нагрузки", "кардио", "силовые", "тренировка",
                "активный", "спорт"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return "Избегай чрезмерных нагрузок и интенсивного спорта, отдай предпочтение легкому движению."

        # Hard guard 4: communication + avoid -> hard negotiation recommendation
        if row_key == "communication" and verdict == "avoid":
            unsafe_keywords = [
                "переговоры", "договаривайся", "убеждай", "спор", "дискуссия", "доказывай",
                "обсуждение", "совещание"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return "Отложи важные переговоры и споры, перенеси обсуждение на более благоприятный период."

        return text

    def validate_concrete_advice_details(
        self,
        *,
        row_key: str,
        verdict: str,
        details: dict,
        evidence: list[ConcreteAdviceEvidence],
    ) -> dict | None:
        """Validate and sanitize story, why, and advice fields in details object."""
        if not isinstance(details, dict):
            return None
        story = details.get("story")
        why = details.get("why")
        advice = details.get("advice")

        if not isinstance(story, str) or not story.strip():
            return None
        if not isinstance(advice, str) or not advice.strip():
            return None
        if not isinstance(why, list):
            why = []

        story_str = story.strip()
        advice_str = advice.strip()
        why_clean = [w.strip() for w in why if isinstance(w, str) and w.strip()]

        # Hard guard against astrology terms and abstractions in any part of details
        if has_banned_jargon(story_str, row_key) or has_banned_jargon(advice_str, row_key):
            return None
        if any(has_banned_jargon(item, row_key) for item in why_clean):
            return None

        sanitized_advice = self.validate_concrete_advice_text(
            row_key=row_key,
            verdict=verdict,
            text=advice_str,
            evidence=evidence,
        )
        if not sanitized_advice:
            return None

        return {
            "story": story_str,
            "why": why_clean,
            "advice": sanitized_advice,
        }
