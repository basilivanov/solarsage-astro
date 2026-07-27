# ############################################################################
# AI_HEADER: MODULE_TEST_SPHERE_WHY_BUILDER
# ROLE: Unit tests for deterministic sphere why builder.
# DEPENDENCIES: pytest, app.services.sphere_why_builder, app.schemas.today.ConcreteAdviceEvidence
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SPHERE-WHY-BUILDER
# purpose: Test build_sphere_why function for planet mapping, direction, scale, dedup, and bounds.
# owns:
#   - apps/api/tests/test_sphere_why_builder.py
# inputs: evidence test cases
# outputs: assertions
# dependencies: app.services.sphere_why_builder
# side_effects: none
# failure_policy: fails on miscalculated why lines
# END_MODULE_CONTRACT: M-TEST-SPHERE-WHY-BUILDER

# START_MODULE_MAP: M-TEST-SPHERE-WHY-BUILDER
# public_entrypoints:
#   - test_build_sphere_why_supportive_transit
#   - test_build_sphere_why_challenging_firdar
#   - test_build_sphere_why_dedup_and_max_two
#   - test_build_sphere_why_empty_fallback
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_sphere_why_builder.py
# END_MODULE_MAP: M-TEST-SPHERE-WHY-BUILDER

import pytest
from app.schemas.today import ConcreteAdviceEvidence
from app.services.sphere_why_builder import build_sphere_why


def test_build_sphere_why_supportive_transit():
    """Supportive aspect transit generates 'поддерживают' + 'работает сегодня'."""
    ev = ConcreteAdviceEvidence(
        kind="aspect",
        title="Transit Venus sextile natal Uranus",
        planet="Transit_Venus",
        target_planet="Uranus",
        aspect_type="sextile",
        strength=0.85,
        technique_family="transit",
    )

    why = build_sphere_why([ev])
    assert len(why) == 1
    assert why[0] == "Чувства и симпатии поддерживают перемены и свободу — работает сегодня"


def test_build_sphere_why_challenging_firdar():
    """Challenging aspect firdar generates 'сталкиваются с' (instrumental) + 'долгий фон'."""
    ev = ConcreteAdviceEvidence(
        kind="aspect",
        title="Transit Sun square natal Saturn",
        planet="Transit_Sun",
        target_planet="Saturn",
        aspect_type="square",
        strength=0.90,
        technique_family="firdar",
    )

    why = build_sphere_why([ev])
    assert len(why) == 1
    assert why[0] == "Самовыражение и цели сталкиваются с правилами и сроками — долгий фон"


def test_build_sphere_why_dedup_and_max_two():
    """Returns at most 2 top-strength unique planet pairs."""
    ev1 = ConcreteAdviceEvidence(
        kind="aspect",
        title="Venus sextile Uranus",
        planet="Venus",
        target_planet="Uranus",
        aspect_type="sextile",
        strength=0.95,
    )
    ev2 = ConcreteAdviceEvidence(
        kind="aspect",
        title="Mars square Saturn",
        planet="Mars",
        target_planet="Saturn",
        aspect_type="square",
        strength=0.80,
    )
    ev3 = ConcreteAdviceEvidence(
        kind="aspect",
        title="Duplicate Venus Uranus",
        planet="Venus",
        target_planet="Uranus",
        aspect_type="trine",
        strength=0.70,
    )

    why = build_sphere_why([ev1, ev2, ev3])
    assert len(why) == 2
    assert "Чувства и симпатии" in why[0]
    assert "Действия и темп" in why[1]


def test_build_sphere_why_empty_fallback():
    """Evidence without planets/aspects returns empty list."""
    ev = ConcreteAdviceEvidence(
        kind="sphere_score",
        title="Показатель work",
        weight=1.5,
    )
    why = build_sphere_why([ev])
    assert why == []
