# ############################################################################
# AI_HEADER: MODULE_NARRATIVE_SANITIZER — fail-closed guard for public narrative text.
# ROLE: Rejects provider text that exposes machine signal identifiers or
#       enumeration artifacts before it can enter a public API response.
# ############################################################################

# START_MODULE_CONTRACT: M-NARRATIVE-SANITIZER
# purpose: Validate public narrative text against known machine-token leaks.
# owns:
#   - apps/api/app/services/narrative_sanitizer.py
# inputs: provider-generated narrative text.
# outputs: stripped safe text or None when the text must not be published.
# dependencies: Python standard library only.
# side_effects: none; pure validation.
# emitted_logs: none.
# invariants: rejected text is never returned as a sanitized value.
# failure_policy: fail closed with None for blank or forbidden text.
# END_MODULE_CONTRACT: M-NARRATIVE-SANITIZER

# START_MODULE_MAP: M-NARRATIVE-SANITIZER
# public_entrypoints:
#   - has_forbidden_narrative_tokens
#   - sanitize_narrative_text
# semantic_blocks:
#   - FORBIDDEN_TOKENS: machine prefixes, generic Planet labels, and list artifacts.
#   - SANITIZE: deterministic trim-and-reject boundary.
# owned_tests:
#   - apps/api/tests/test_narrative_sanitizer.py
# END_MODULE_MAP: M-NARRATIVE-SANITIZER

from __future__ import annotations

import re


_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-zА-Яа-я0-9_])(?:Transit_|Natal_)[A-Za-z0-9_]*", re.IGNORECASE),
    re.compile(r"\bPlanet\b", re.IGNORECASE),
    re.compile(r"(?<![A-Za-zА-Яа-я0-9_])M\s*,\s*[A-Za-zА-Яа-я][A-Za-zА-Яа-я0-9_-]*", re.IGNORECASE),
)


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


__all__ = ["has_forbidden_narrative_tokens", "sanitize_narrative_text"]
