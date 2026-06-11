# ############################################################################
# AI_HEADER: MODULE_SEMANTIC_SCHEMA
# ROLE: Semantic layer schemas
# DEPENDENCIES: pydantic, typing
# GRACE_ANCHORS: [SEMANTIC_LAYER, SPHERE_THEME]
# WAVE: W-4.3
# ############################################################################

# START_MODULE_CONTRACT: M-SEMANTIC-SCHEMA
# purpose: Define SemanticLayer and SphereTheme Pydantic schemas.
# owns:
#   - apps/api/app/schemas/semantic.py
# inputs:
#   - none (type definitions)
# outputs:
#   - SemanticLayer, SphereTheme
# dependencies:
#   - pydantic.BaseModel
#   - typing
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-SEMANTIC-SCHEMA

# START_MODULE_MAP: M-SEMANTIC-SCHEMA
# public_entrypoints:
#   - SemanticLayer
#   - SphereTheme
# semantic_blocks:
#   - SEMANTIC_LAYER: semantic layer data model
#   - SPHERE_THEME: sphere theme data model
# END_MODULE_MAP: M-SEMANTIC-SCHEMA

from pydantic import BaseModel


class SphereTheme(BaseModel):
    """Theme for a life sphere."""
    sphere: str  # "career", "relationships", etc
    score: float  # 0.0-1.0
    theme: str  # "Активный рост", "Стабильность", etc
    keywords: list[str]  # ["продвижение", "успех"]


class SemanticLayer(BaseModel):
    """Semantic layer for a day."""
    day_status: str  # "supportive", "steady", "tense"
    day_theme: str  # "День возможностей", "Спокойный день", etc
    sphere_themes: list[SphereTheme]
    top_keywords: list[str]  # Top 5 keywords across all spheres
