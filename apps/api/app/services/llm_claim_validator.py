# ############################################################################
# AI_HEADER: MODULE_LLM_CLAIM_VALIDATOR — validates and sanitizes LLM texts.
# ROLE: LLMClaimValidator — enforces doc-15 hard guards for advice rows.
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-CLAIM-VALIDATOR
# purpose: Validate generated advice texts against hard guards and banned jargon (S1 no-fallback policy).
# owns:
#   - apps/api/app/services/llm_claim_validator.py
# inputs: row_key, verdict, text, evidence
# outputs: sanitized text or None (no replacement texts)
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants: unsafe texts are rejected (return None), replacement text is disabled
# failure_policy: returns None for texts that violate hard guards or contain banned jargon
# END_MODULE_CONTRACT: M-LLM-CLAIM-VALIDATOR

# START_MODULE_MAP: M-LLM-CLAIM-VALIDATOR
# public_entrypoints:
#   - LLMClaimValidator.validate_concrete_advice_text
#   - LLMClaimValidator.check_concrete_advice_text_safety
#   - LLMClaimValidator.validate_concrete_advice_details
#   - LLMClaimValidator.check_concrete_advice_details_safety
# semantic_blocks: none
# owned_tests:
#   - tests/test_llm_claim_validator.py
# END_MODULE_MAP: M-LLM-CLAIM-VALIDATOR

from __future__ import annotations
from app.schemas.today import ConcreteAdviceEvidence

BANNED_ASTRO_STEMS: list[str] = [
    "транзит", "аспект", "орб", "натал", "планет",
    "поддержк", "влияни", "гармони",
]


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
    def check_concrete_advice_text_safety(
        self,
        *,
        row_key: str,
        verdict: str,
        text: str,
        evidence: list[ConcreteAdviceEvidence],
    ) -> tuple[str | None, str | None]:
        """Validate text safety against hard guards and jargon.

        Returns:
            (sanitized_text, None) if safe.
            (None, reason_code) if rejected by a hard guard or banned jargon.
        """
        if not text or not text.strip():
            return None, "empty"

        if has_banned_jargon(text, row_key):
            return None, "banned_jargon"

        text_lower = text.lower()

        # Hard guard 1: relationships + avoid -> direct relationship improvement / conflict-opening advice
        if row_key == "relationships" and verdict == "avoid":
            unsafe_keywords = [
                "выяснять отношения", "выясняй", "разбирай", "обсуди", "поговори",
                "улучши", "улучшать", "выяснения", "конфликт", "спор"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return None, "guard_relationships_avoid"

        # Hard guard 2: money + avoid -> invest/spend/buy recommendation
        if row_key == "money" and verdict == "avoid":
            unsafe_keywords = [
                "инвестируй", "инвестиции", "покупай", "покупка", "тратить", "потрать",
                "купи", "вкладывай", "вложения"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return None, "guard_money_avoid"

        # Hard guard 3: sport/health + avoid -> intense sport recommendation
        if row_key in ("sport", "health") and verdict == "avoid":
            unsafe_keywords = [
                "интенсивный", "тяжелый", "нагрузки", "кардио", "силовые", "тренировка",
                "активный", "спорт"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return None, "guard_body_avoid"

        # Hard guard 4: communication + avoid -> hard negotiation recommendation
        if row_key == "communication" and verdict == "avoid":
            unsafe_keywords = [
                "переговоры", "договаривайся", "убеждай", "спор", "дискуссия", "доказывай",
                "обсуждение", "совещание"
            ]
            if any(kw in text_lower for kw in unsafe_keywords):
                return None, "guard_communication_avoid"

        return text, None

    def validate_concrete_advice_text(
        self,
        *,
        row_key: str,
        verdict: str,
        text: str,
        evidence: list[ConcreteAdviceEvidence],
    ) -> str | None:
        """Validate generated text for a row domain against its verdict. S1 No-Fallback Policy.

        Returns:
            Original text if safe.
            None if unsafe (rejected by hard guard or banned jargon). Replacement text is disabled.
        """
        sanitized_text, _ = self.check_concrete_advice_text_safety(
            row_key=row_key, verdict=verdict, text=text, evidence=evidence
        )
        return sanitized_text

    def check_concrete_advice_details_safety(
        self,
        *,
        row_key: str,
        verdict: str,
        details: dict,
        evidence: list[ConcreteAdviceEvidence],
    ) -> tuple[dict | None, str | None]:
        """Validate story, why, and advice fields in details object.

        Returns:
            (sanitized_details_dict, None) if safe.
            (None, reason_code) if rejected.
        """
        if not isinstance(details, dict):
            return None, "parse"
        story = details.get("story")
        why = details.get("why")
        advice = details.get("advice")

        if not isinstance(story, str) or not story.strip():
            return None, "empty"
        if not isinstance(advice, str) or not advice.strip():
            return None, "empty"
        if not isinstance(why, list):
            why = []

        story_str = story.strip()
        advice_str = advice.strip()
        why_clean = [w.strip() for w in why if isinstance(w, str) and w.strip()]

        # Hard guard against astrology terms and abstractions in any part of details
        if has_banned_jargon(story_str, row_key) or has_banned_jargon(advice_str, row_key):
            return None, "banned_jargon"
        if any(has_banned_jargon(item, row_key) for item in why_clean):
            return None, "banned_jargon"

        sanitized_advice, reason = self.check_concrete_advice_text_safety(
            row_key=row_key,
            verdict=verdict,
            text=advice_str,
            evidence=evidence,
        )
        if not sanitized_advice:
            return None, reason or "validation_failed"

        return {
            "story": story_str,
            "why": why_clean,
            "advice": sanitized_advice,
        }, None

    def validate_concrete_advice_details(
        self,
        *,
        row_key: str,
        verdict: str,
        details: dict,
        evidence: list[ConcreteAdviceEvidence],
    ) -> dict | None:
        """Validate and sanitize story, why, and advice fields in details object."""
        sanitized_details, _ = self.check_concrete_advice_details_safety(
            row_key=row_key, verdict=verdict, details=details, evidence=evidence
        )
        return sanitized_details
