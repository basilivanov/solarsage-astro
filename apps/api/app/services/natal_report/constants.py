# ############################################################################
# AI_HEADER: NATAL_REPORT_CONSTANTS — module-level constants for natal report generation
# ROLE: Provides all configurable constants used by natal report generation and
#       hallucination detection. Imported by validation.py and natal_report_service.py.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Centralize all magic strings and numeric constants for natal reports.
# inputs: (none — module-level constants)
# returns: REQUIRED_SECTIONS, _SECTION_TITLES, PROMPT_VERSION, REPORT_SCHEMA_VERSION,
#          MAX_RETRY_ATTEMPTS, _FORBIDDEN_PLANET_PATTERNS_ALWAYS, _SPECIAL_POINT_PATTERNS
# side_effects: none
# emitted_logs: none
# error_behavior: none
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - const: REQUIRED_SECTIONS
#   - const: _SECTION_TITLES
#   - const: PROMPT_VERSION
#   - const: REPORT_SCHEMA_VERSION
#   - const: MAX_RETRY_ATTEMPTS
#   - const: _FORBIDDEN_PLANET_PATTERNS_ALWAYS
#   - const: _SPECIAL_POINT_PATTERNS
# END_MODULE_MAP

from __future__ import annotations

# ── Required section IDs for this wave ────────────────────────────
REQUIRED_SECTIONS = [
    "portrait",
    "ascendant",
    "rulers",
    "aspects",
    "spheres",
    "planets",
    "shadow",
    "synthesis",
]

_SECTION_TITLES = {
    "portrait": "Психологический портрет",
    "ascendant": "Асцендент и внешняя маска",
    "rulers": "Управители и ключевые темы",
    "aspects": "Аспекты и внутренние диалоги",
    "spheres": "Сферы жизни",
    "planets": "Планеты в деталях",
    "shadow": "Теневая сторона и зоны роста",
    "synthesis": "Синтез и практические выводы",
}

PROMPT_VERSION = "1"
REPORT_SCHEMA_VERSION = "natal/v1"
MAX_RETRY_ATTEMPTS = 3

# ── Known astrological proper nouns (for hallucination detection) ──
_FORBIDDEN_PLANET_PATTERNS_ALWAYS = [
    "зевс", "гера", "афина", "аполлон", "артемида",
    "кронос", "немезида", "вулкан", "изида",
    "xenu", "nibiru", "pholus", "ceres", "pallas", "juno", "vesta",
    "прозерпина",
]

_SPECIAL_POINT_PATTERNS = [
    ("хирон", "chiron"),
    ("селена", "selena"),
    ("лилит", "lilith"),
]
