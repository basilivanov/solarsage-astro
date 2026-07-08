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
    )
    
    # 04 period_background context is contexts[3]
    # 07 manifestation_zones context is contexts[6]
    period_context = contexts[3]["context"]
    zones_context = contexts[6]["context"]
    
    # Check that they mention "1 дом" (from Transit_Sun) but NOT "5 дом" (from natal Moon)
    assert "1" in period_context or "1 дом" in period_context
    assert "5" not in period_context
    
    assert "1 дом" in zones_context
    assert "5 дом" not in zones_context
