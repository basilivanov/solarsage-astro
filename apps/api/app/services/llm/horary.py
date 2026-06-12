# ############################################################################
# AI_HEADER: MODULE_LLM_HORARY
# ROLE: Horary validation helpers — block validation, evidence formatting
# DEPENDENCIES: app.services.llm.russian
# GRACE_ANCHORS: [VALIDATE_HORARY_BLOCKS, FORMAT_EVIDENCE, FORMAT_TIMING]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-HORARY
# purpose: Validate and format horary LLM response blocks.
# owns:
#   - apps/api/app/services/llm/horary.py
# inputs:
#   - blocks list, EvidenceItem, TimingInfo
# outputs:
#   - bool (validation result), str (formatted text)
# dependencies:
#   - M-LLM-RUSSIAN (_PLANET_RU)
# invariants:
#   - validation is schema-only (no semantic checking)
# failure_policy:
#   - raises HoraryGenerationError on invalid blocks
# END_MODULE_CONTRACT: M-LLM-HORARY

from __future__ import annotations

from app.services.llm.client import HoraryGenerationError
from app.services.llm.russian import _PLANET_RU


def _format_evidence(item) -> str:
    planets = ", ".join(_PLANET_RU.get(p, p) for p in item.planets_involved)
    aspect = f", аспект {item.aspect_type}" if item.aspect_type else ""
    orb = f", орб {item.orb:.1f}°" if item.orb is not None else ""
    return (
        f"- {item.title}\n"
        f"  {item.explanation}\n"
        f"  (планеты: {planets}{aspect}{orb}, вес: {item.weight:+.2f})"
    )


def _format_timing(timing) -> str:
    range_str = f", диапазон: {timing.time_range}" if timing.time_range else ""
    basis = f"\n  Основание: {timing.basis}" if timing.basis else ""
    return (
        f"Статус: {timing.status}{range_str}\n"
        f"Текст для пользователя: {timing.text}{basis}"
    )


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
