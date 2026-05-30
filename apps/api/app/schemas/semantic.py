# AI_HEADER
# module: M-SEMANTIC-SCHEMA
# wave: W-4.3
# purpose: Semantic layer schemas

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
