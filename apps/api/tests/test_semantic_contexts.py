import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.semantic import SemanticLayer
from app.services.semantic_service import SemanticService

def test_manifestation_zones_do_not_use_static_natal_houses_as_day_evidence():
    service = SemanticService()

    # We pass both a transit planet-in-house and a static natal planet-in-house signal
    all_signals = [
        AstroSignal(
            type="planet_in_house",
            planet="Transit_Sun",
            house=1,
            strength=1.0,
        ),
        AstroSignal(
            type="planet_in_house",
            planet="Moon",  # natal Moon
            house=5,
            strength=1.0,
        ),
        AstroSignal(
            type="aspect",
            planet="Transit_Moon",
            target_planet="Pluto",
            aspect_type="opposition",
            orb=1.0,
            strength=0.9,
        )
    ]

    semantic_layer = SemanticLayer(
        day_status="supportive",
        day_theme="День возможностей",
        sphere_themes=[],
        top_keywords=[],
    )

    contexts = service.build_why_contexts(
        day_status="supportive",
        sphere_scores={},
        top_signals=all_signals,
        natal={"planets": [], "houses": []},
        transits={"planets": []},
        semantic_layer=semantic_layer,
        all_signals=all_signals,
        day_scored_signals=[all_signals[0], all_signals[2]],
        natal_background_signals=[all_signals[1]],
    )

    period_context = contexts[3]["context"]
    zones_context = contexts[6]["context"]

    # Check that they mention "1 дом" (from Transit_Sun)
    assert "1" in period_context or "1 дом" in period_context

    # In the main part of the period context (before the natal background label), there should be no "5"
    main_period_part = period_context.split("Натальный фон")[0]
    assert "5" not in main_period_part

    # But it can be present in the natal background part
    assert "Натальный фон" in period_context
    assert "5" in period_context.split("Натальный фон")[1]

    assert "1 дом" in zones_context
    assert "5 дом" not in zones_context

def test_day_contexts_do_not_use_natal_aspects_as_day_evidence():
    service = SemanticService()

    # We pass both a transit aspect and a static natal aspect
    all_signals = [
        AstroSignal(
            type="aspect",
            planet="Transit_Moon",
            target_planet="Pluto",
            aspect_type="opposition",
            orb=1.0,
            strength=0.9,
        ),
        AstroSignal(
            type="aspect",
            planet="Sun",  # natal Sun
            target_planet="Saturn",  # natal Saturn
            aspect_type="square",
            orb=2.0,
            strength=0.8,
        )
    ]

    semantic_layer = SemanticLayer(
        day_status="supportive",
        day_theme="День возможностей",
        sphere_themes=[],
        top_keywords=[],
    )

    contexts = service.build_why_contexts(
        day_status="supportive",
        sphere_scores={},
        top_signals=all_signals,
        natal={"planets": [], "houses": []},
        transits={"planets": []},
        semantic_layer=semantic_layer,
        all_signals=all_signals,
        day_scored_signals=[all_signals[0]],
        natal_background_signals=[all_signals[1]],
    )

    main_theme = contexts[0]["context"]
    amplifiers = contexts[4]["context"]

    # Check that they mention Transit Moon opposition natal Pluto but NOT natal Sun square natal Saturn
    assert "Transit Moon opposition natal Pluto" in main_theme
    assert "natal Sun square natal Saturn" not in main_theme

    assert "Transit Moon opposition natal Pluto" in amplifiers
    assert "natal Sun square natal Saturn" not in amplifiers

def test_relationships_bullet_avoided_when_score_is_low():
    """Supportive day with relationships_partnership below avoid threshold must not
    emit the relationship outreach practical bullet."""
    service = SemanticService()

    semantic_layer = SemanticLayer(
        day_status="supportive",
        day_theme="День возможностей",
        sphere_themes=[],
        top_keywords=[],
    )

    # relationships_partnership=1.0 is below the 2.0 avoid threshold
    contexts = service.build_why_contexts(
        day_status="supportive",
        sphere_scores={"relationships_partnership": 1.0, "work_status_achievement": 3.0},
        top_signals=[],
        natal={"planets": [], "houses": []},
        transits={"planets": []},
        semantic_layer=semantic_layer,
    )

    practical_context = contexts[8]["context"]
    # Must NOT contain the relationship outreach bullet
    assert "Общайся с близкими" not in practical_context
    assert "близкими" not in practical_context
    # Must contain the two generic supportive bullets
    assert "Действуй" in practical_context
    assert "Заверши отложенные задачи" in practical_context
