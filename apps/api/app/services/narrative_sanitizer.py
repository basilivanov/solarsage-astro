# ############################################################################
# AI_HEADER: MODULE_NARRATIVE_SANITIZER — fail-closed guard for public narrative text.
# ROLE: Rejects provider text that exposes machine signal identifiers or
#       enumeration artifacts before it can enter a public API response.
# ############################################################################

# START_MODULE_CONTRACT: M-NARRATIVE-SANITIZER
# purpose: Validate public narrative text against known machine-token leaks and
#   deterministic sphere/polarity grounding rules.
# owns:
#   - apps/api/app/services/narrative_sanitizer.py
# inputs: provider-generated narrative text and, for grounding, its selected
#   product spheres plus polarity.
# outputs: stripped safe text or None when the text must not be published;
#   grounding violations are reported as booleans without exposing raw text.
# dependencies: Python standard library only.
# side_effects: none; pure validation.
# emitted_logs: none.
# invariants: rejected text is never returned as a sanitized value; an unknown
#   sphere or polarity fails closed.
# failure_policy: fail closed with None for blank or forbidden text.
# END_MODULE_CONTRACT: M-NARRATIVE-SANITIZER

# START_MODULE_MAP: M-NARRATIVE-SANITIZER
# public_entrypoints:
#   - has_forbidden_narrative_tokens
#   - sanitize_narrative_text
#   - has_narrative_grounding_violation
# semantic_blocks:
#   - FORBIDDEN_TOKENS: machine prefixes, generic Planet labels, and list artifacts.
#   - GROUNDING: canonical sphere vocabulary, related-sphere allowances, and
#     explicit polarity-antonym checks.
#   - SANITIZE: deterministic trim-and-reject boundary.
# owned_tests:
#   - apps/api/tests/test_narrative_sanitizer.py
# END_MODULE_MAP: M-NARRATIVE-SANITIZER

from __future__ import annotations

import re
from collections.abc import Collection


_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-zА-Яа-я0-9_])(?:Transit_|Natal_)[A-Za-z0-9_]*", re.IGNORECASE),
    re.compile(r"\bPlanet\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-zА-Яа-я0-9_])M\s*,\s*[A-Za-zА-Яа-я][A-Za-zА-Яа-я0-9_-]*", re.IGNORECASE),
)


# These stems are deliberately conservative: they cover the twelve public
# labels and their obvious Russian forms without turning ordinary action copy
# ("шаг", "фокус", "результат") into a sphere claim.
_SPHERE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "work": (re.compile(r"(?<!\w)(?:работ\w*|статус\w*)", re.IGNORECASE),),
    "money": (re.compile(r"(?<!\w)(?:деньг\w*|ресурс\w*)", re.IGNORECASE),),
    "documents": (
        re.compile(r"(?<!\w)(?:документ\w*|формальност\w*|бумаг\w*|договор\w*)", re.IGNORECASE),
    ),
    "relationships": (
        re.compile(r"(?<!\w)(?:отношени\w*|близост\w*|партн[её]р\w*)", re.IGNORECASE),
    ),
    "sport": (
        re.compile(r"(?<!\w)(?:движен\w*|трениров\w*|спорт\w*)", re.IGNORECASE),
    ),
    "communication": (
        re.compile(r"(?<!\w)(?:общен\w*|разговор\w*|переписк\w*|контакт\w*)", re.IGNORECASE),
    ),
    "health": (
        re.compile(r"(?<!\w)(?:самочув\w*|здоров\w*|режим\w*|восстанов\w*)", re.IGNORECASE),
    ),
    "decisions": (re.compile(r"(?<!\w)(?:решен\w*)", re.IGNORECASE),),
    "travel": (
        re.compile(r"(?<!\w)(?:поезд\w*|маршрут\w*|дорог\w*)", re.IGNORECASE),
    ),
    "creativity": (re.compile(r"(?<!\w)(?:творч\w*|креатив\w*)", re.IGNORECASE),),
    "study": (
        re.compile(r"(?<!\w)(?:обуч\w*|уч[её]б\w*)", re.IGNORECASE),
    ),
    "shopping": (
        re.compile(r"(?<!\w)(?:покуп\w*|магазин\w*|заказ\w*)", re.IGNORECASE),
    ),
}

_RELATED_SPHERES: dict[str, frozenset[str]] = {
    "documents": frozenset({"communication", "study"}),
    "communication": frozenset({"documents"}),
    "study": frozenset({"documents"}),
    "money": frozenset({"shopping"}),
    "shopping": frozenset({"money"}),
    "health": frozenset({"sport"}),
    "sport": frozenset({"health"}),
    "relationships": frozenset({"decisions"}),
    "decisions": frozenset({"relationships"}),
}

_POLARITY_CONFLICT_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "supportive": (
        re.compile(r"напряж\w*", re.IGNORECASE),
        re.compile(r"конфликт\w*", re.IGNORECASE),
        re.compile(r"обостр\w*", re.IGNORECASE),
    ),
    "tense": (
        re.compile(r"(?:легк|лёгк)\w*", re.IGNORECASE),
        re.compile(r"гармонич\w*", re.IGNORECASE),
    ),
}


# START_BLOCK: FORBIDDEN_TOKENS
def has_forbidden_narrative_tokens(text: str) -> bool:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_forbidden_narrative_tokens
    # purpose: Detect technical identifiers and enumeration artifacts in narrative text.
    # inputs: text — candidate provider-generated text.
    # returns: True when the text must not be published.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: non-string input is treated as forbidden.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_forbidden_narrative_tokens
    if not isinstance(text, str):
        return True
    return any(pattern.search(text) is not None for pattern in _FORBIDDEN_PATTERNS)
# END_BLOCK: FORBIDDEN_TOKENS


# START_BLOCK: SANITIZE
def sanitize_narrative_text(text: str) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.sanitize_narrative_text
    # purpose: Return publishable narrative text or fail closed on a forbidden token.
    # inputs: text — candidate provider-generated text.
    # returns: trimmed text, or None when blank/unsafe.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: non-string, blank, or forbidden text returns None.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.sanitize_narrative_text
    if not isinstance(text, str):
        return None
    clean = text.strip()
    if not clean or has_forbidden_narrative_tokens(clean):
        return None
    return clean
# END_BLOCK: SANITIZE


# START_BLOCK: GROUNDING
def has_narrative_grounding_violation(
    text: str,
    *,
    allowed_spheres: Collection[str],
    polarity: str,
) -> bool:
    # START_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_narrative_grounding_violation
    # purpose: Reject a narrative claim that names an unrelated product sphere
    #   or uses an explicit polarity antonym.
    # inputs: text — sanitized candidate; allowed_spheres — primary plus any
    #   evidence/secondary spheres for the block; polarity — canonical block
    #   polarity.
    # returns: True when the claim must be withheld.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed text, unknown spheres, or unknown polarity fail closed.
    # END_FUNCTION_CONTRACT: F-M-NARRATIVE-SANITIZER.has_narrative_grounding_violation
    if not isinstance(text, str) or not isinstance(polarity, str):
        return True
    normalized_spheres = {sphere for sphere in allowed_spheres if isinstance(sphere, str)}
    if not normalized_spheres or not normalized_spheres.issubset(_SPHERE_PATTERNS):
        return True
    if polarity not in {"supportive", "tense", "mixed"}:
        return True

    for detected_sphere, patterns in _SPHERE_PATTERNS.items():
        if not any(pattern.search(text) is not None for pattern in patterns):
            continue
        if detected_sphere in normalized_spheres:
            continue
        if any(
            detected_sphere in _RELATED_SPHERES.get(allowed_sphere, frozenset())
            for allowed_sphere in normalized_spheres
        ):
            continue
        return True

    return any(
        pattern.search(text) is not None
        for pattern in _POLARITY_CONFLICT_PATTERNS.get(polarity, ())
    )
# END_BLOCK: GROUNDING


__all__ = [
    "has_forbidden_narrative_tokens",
    "has_narrative_grounding_violation",
    "sanitize_narrative_text",
]
