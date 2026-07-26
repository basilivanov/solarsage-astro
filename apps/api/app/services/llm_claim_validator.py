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
