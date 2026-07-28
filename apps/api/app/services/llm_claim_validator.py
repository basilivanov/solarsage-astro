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
#   - LLMClaimValidator.check_focus_narrative_safety
# semantic_blocks: none
# owned_tests:
#   - tests/test_llm_claim_validator.py
# END_MODULE_MAP: M-LLM-CLAIM-VALIDATOR

from __future__ import annotations
from typing import Any
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
    def check_day_main_safety(self, text: str | None) -> tuple[str | None, str | None]:
        """Validate day_main synthesis string (S2).

        Returns:
            (sanitized_text, None) if valid.
            (None, reason_code) if rejected.
        """
        if not text or not isinstance(text, str) or not text.strip():
            return None, "empty"

        t = text.strip()
        if len(t) > 120:
            return None, "length"

        import re
        if re.search(r"[A-Za-z]", t):
            return None, "parse"

        if has_banned_jargon(t, "day_main"):
            return None, "banned_jargon"

        return t, None

    def validate_day_main(self, text: str | None) -> str | None:
        sanitized, _ = self.check_day_main_safety(text)
        return sanitized

    def check_focus_narrative_safety(
        self,
        narrative: dict[str, Any] | None,
        *,
        state: str,
        expected_event_ids: list[str],
        expected_sphere_keys: list[str],
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Validate LLM focus narrative output against schema, bounds, jargon, and expected keys.

        Returns:
            (sanitized_dict, None) on success.
            (None, reason_code) on rejection.
        """
        import re

        if not narrative or not isinstance(narrative, dict):
            return None, "parse"

        conv_summary = narrative.get("convergence_summary")
        if state == "convergence_today":
            if not isinstance(conv_summary, str) or not conv_summary.strip():
                return None, "empty"
            cs_clean = conv_summary.strip()
            if len(cs_clean) > 220:
                return None, "length"
            if re.search(r"[A-Za-z]", cs_clean):
                return None, "parse"
            if has_banned_jargon(cs_clean, "convergence_summary"):
                return None, "banned_jargon"
            conv_summary = cs_clean
        else:
            conv_summary = None

        event_meanings_raw = narrative.get("event_meanings")
        if not isinstance(event_meanings_raw, dict):
            return None, "parse"
        if set(event_meanings_raw.keys()) != set(expected_event_ids):
            return None, "parse"

        sanitized_event_meanings: dict[str, str] = {}
        for ev_id in expected_event_ids:
            meaning = event_meanings_raw.get(ev_id)
            if not isinstance(meaning, str) or not meaning.strip():
                return None, "empty"
            m_clean = meaning.strip()
            if len(m_clean) > 160:
                return None, "length"
            if re.search(r"[A-Za-z]", m_clean):
                return None, "parse"
            if has_banned_jargon(m_clean, f"event_meaning:{ev_id}"):
                return None, "banned_jargon"
            sanitized_event_meanings[ev_id] = m_clean

        featured_spheres_raw = narrative.get("featured_spheres")
        if not isinstance(featured_spheres_raw, dict):
            return None, "parse"
        if set(featured_spheres_raw.keys()) != set(expected_sphere_keys):
            return None, "parse"

        sanitized_featured: dict[str, dict[str, str]] = {}
        for s_key in expected_sphere_keys:
            s_obj = featured_spheres_raw.get(s_key)
            if not isinstance(s_obj, dict):
                return None, "parse"
            summary = s_obj.get("summary")
            action = s_obj.get("action")
            if not isinstance(summary, str) or not summary.strip():
                return None, "empty"
            if not isinstance(action, str) or not action.strip():
                return None, "empty"
            sum_clean = summary.strip()
            act_clean = action.strip()
            if len(sum_clean) > 140 or len(act_clean) > 100:
                return None, "length"
            if re.search(r"[A-Za-z]", sum_clean) or re.search(r"[A-Za-z]", act_clean):
                return None, "parse"
            if has_banned_jargon(sum_clean, s_key) or has_banned_jargon(act_clean, s_key):
                return None, "banned_jargon"
            sanitized_featured[s_key] = {"summary": sum_clean, "action": act_clean}

        return {
            "convergence_summary": conv_summary,
            "event_meanings": sanitized_event_meanings,
            "featured_spheres": sanitized_featured,
        }, None

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
