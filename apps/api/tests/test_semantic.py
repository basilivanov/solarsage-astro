# AI_HEADER
# module: M-TEST-SEMANTIC
# wave: W-4.3
# purpose: Semantic layer tests

import pytest

from app.services.semantic_service import SemanticService


def test_semantic_layer_supportive():
    """Supportive day has positive theme."""
    service = SemanticService()

    semantic = service.build_semantic_layer(
        day_status="supportive",
        sphere_scores={"career": 3, "relationships": 2},
    )

    assert semantic.day_status == "supportive"
    assert semantic.day_theme == "День возможностей"
    assert len(semantic.sphere_themes) == 2
    assert len(semantic.top_keywords) > 0


def test_semantic_layer_tense():
    """Tense day has challenging theme."""
    service = SemanticService()

    semantic = service.build_semantic_layer(
        day_status="tense",
        sphere_scores={"career": 1, "health": 0},
    )

    assert semantic.day_status == "tense"
    assert semantic.day_theme == "День вызовов"


def test_sphere_theme_high_score():
    """High score sphere has positive theme."""
    service = SemanticService()

    semantic = service.build_semantic_layer(
        day_status="steady",
        sphere_scores={"career": 4},
    )

    career_theme = next(t for t in semantic.sphere_themes if t.sphere == "career")
    assert career_theme.theme == "Активный рост"
    assert "продвижение" in career_theme.keywords
