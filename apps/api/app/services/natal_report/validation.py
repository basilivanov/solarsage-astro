# ############################################################################
# AI_HEADER: NATAL_REPORT_VALIDATION — hallucination detection and block text extraction
# ROLE: Provides _check_hallucinated_planets() and _iter_block_texts() helpers used
#       by NatalReportService._validate_sections() to guard against LLM fabrications.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Validate natal report LLM output for hallucinated planets and extract
#          all text fragments from block structures for scanning.
# inputs: text (str), known_planet_names (set), allowed_special_point_names (set),
#         section_id (str) — for _check_hallucinated_planets;
#         block (NatalBlock) — for _iter_block_texts
# returns: None (raises on hallucination); generator of strings
# side_effects: none
# emitted_logs: none
# error_behavior: raises ValueError if hallucinated planet or disallowed special
#                 point is found in text
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: _check_hallucinated_planets
#   - function: _iter_block_texts
# END_MODULE_MAP

from __future__ import annotations

from .constants import _FORBIDDEN_PLANET_PATTERNS_ALWAYS, _SPECIAL_POINT_PATTERNS
from app.schemas.natal import (
    NatalBlock,
    ParagraphBlock,
    LeadBlock,
    HeadingBlock,
    ListBlock,
    CalloutBlock,
    ProsConsBlock,
    HighlightsBlock,
    BulletsBlock,
    QuoteBlock,
    DividerBlock,
)


# START_BLOCK: HALLUCINATION_DETECTION

# START_FUNCTION_CONTRACT
# name: _check_hallucinated_planets
# purpose: Scan text for fabricated planet names and disallowed special points.
# inputs:
#   text — str, the text fragment to scan
#   known_planet_names — set[str], allowed planet names from chart context
#   allowed_special_point_names — set[str], special points present in chart context
#   section_id — str, section identifier for error messages
# returns: None
# side_effects: none
# emitted_logs: none
# error_behavior: raises ValueError if a forbidden pattern or disallowed
#                 special point is found in the text
# END_FUNCTION_CONTRACT
def _check_hallucinated_planets(
    text: str,
    known_planet_names: set[str],
    allowed_special_point_names: set[str],
    section_id: str,
) -> None:
    text_lower = text.lower()

    for forbidden in _FORBIDDEN_PLANET_PATTERNS_ALWAYS:
        if forbidden in text_lower:
            raise ValueError(
                f"Hallucinated planet name '{forbidden}' found in section {section_id}. "
                f"LLM must only reference planets from the provided chart context."
            )

    for ru_pattern, en_name in _SPECIAL_POINT_PATTERNS:
        if ru_pattern in text_lower and en_name not in allowed_special_point_names:
            raise ValueError(
                f"Hallucinated special point '{ru_pattern}' found in section {section_id}. "
                f"This point is not in the chart's deterministic special_points."
            )

# END_BLOCK: HALLUCINATION_DETECTION


# START_BLOCK: BLOCK_TEXT_EXTRACTION

# START_FUNCTION_CONTRACT
# name: _iter_block_texts
# purpose: Yield all human-readable text strings from a block recursively.
# inputs:
#   block — NatalBlock, the structured block to extract text from
# returns: Generator[str, None, None] — text fragments from the block
# side_effects: none
# emitted_logs: none
# error_behavior: none (silently skips blocks with no text fields)
# END_FUNCTION_CONTRACT
def _iter_block_texts(block: NatalBlock):
    if isinstance(block, ParagraphBlock | LeadBlock | HeadingBlock | QuoteBlock):
        if block.text:
            yield block.text
    elif isinstance(block, ListBlock):
        yield from (item for item in block.items if item)
    elif isinstance(block, CalloutBlock):
        if block.title:
            yield block.title
        if block.text:
            yield block.text
    elif isinstance(block, ProsConsBlock):
        for item in block.pros:
            if item.title:
                yield item.title
            if item.text:
                yield item.text
        for item in block.cons:
            if item.title:
                yield item.title
            if item.text:
                yield item.text
    elif isinstance(block, HighlightsBlock):
        for item in block.items:
            if item.title:
                yield item.title
            if item.text:
                yield item.text
    elif isinstance(block, BulletsBlock):
        yield from (item for item in block.items if item)

# END_BLOCK: BLOCK_TEXT_EXTRACTION
