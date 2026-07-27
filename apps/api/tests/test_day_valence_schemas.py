# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_SCHEMAS
# ROLE: Unit tests for day_valence Pydantic schemas, canon loading, and value equivalence.
# DEPENDENCIES: pytest, app.schemas.day_valence, app.services.canon_service
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-SCHEMAS
# purpose: Verify DayValence Pydantic schemas, day_valence.v1.yml loading, and value equivalence with spheres.v1.yml.
# owns:
#   - apps/api/tests/test_day_valence_schemas.py
# inputs: test cases
# outputs: assertions
# dependencies: app.schemas.day_valence, app.services.canon_service
# side_effects: loads canon YAML from disk
# failure_policy: fails test on schema or value mismatch
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-SCHEMAS

# START_MODULE_MAP: M-TEST-DAY-VALENCE-SCHEMAS
# public_entrypoints:
#   - test_day_valence_canon_loader
#   - test_day_valence_schemas_pydantic
#   - test_day_valence_canon_equivalence_with_spheres
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_schemas.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-SCHEMAS

import pytest
from app.schemas.day_valence import (
    DayStatusBreakdown,
    DayValenceFactor,
    ProductSphereAssessment,
    SphereValenceRead,
)
from app.services.canon_service import (
    load_day_valence_canon,
    validate_canon_bundle,
)


def test_day_valence_canon_loader():
    """Verify load_day_valence_canon loads and validates day_valence.v1.yml fail-closed."""
    canon = load_day_valence_canon()
    assert canon["schema_version"] == "day_valence.v1"
    assert "aspect_weights" in canon
    assert "planet_weights" in canon
    assert "family_independence_weights" in canon
    assert "technical_to_product_spheres" in canon
    assert "verdict_thresholds" in canon

    bundle = validate_canon_bundle()
    assert "day_valence.v1.yml" in bundle


def test_day_valence_schemas_pydantic():
    """Verify Pydantic models instantiate correctly with required fields."""
    factor = DayValenceFactor(
        factor_id="act:101",
        semantic_key="aspect:VENUS:sextile:natal_planet:URANUS",
        source="activation",
        technique="transit_to_natal",
        technique_family="transit",
        polarity="supportive",
        strength=0.85,
        technical_spheres=["relationships_partnership"],
        source_planet="Venus",
        target_type="natal_planet",
        target_key="Uranus",
        aspect_type="sextile",
    )
    assert factor.factor_id == "act:101"
    assert factor.polarity == "supportive"

    assessment = ProductSphereAssessment(
        key="work",
        salience_score=8.5,
        support_score=2.1,
        tension_score=0.4,
        balance=0.68,
        verdict="good",
        confidence="high",
        verdict_rule="good_support_1_3x",
        factor_count=5,
        effective_factor_count=3,
        independent_family_count=2,
        primary_factor_id="act:101",
    )
    assert assessment.verdict == "good"
    assert assessment.balance == 0.68

    read_model = SphereValenceRead(sphere="work", assessment=assessment, primary_factor=factor)
    assert read_model.sphere == "work"
    assert read_model.primary_factor.factor_id == "act:101"

    breakdown = DayStatusBreakdown(
        support_score=3.5,
        tension_score=1.2,
        ratio=2.91,
        rule="supportive",
        factor_count=12,
        effective_factor_count=8,
        family_counts={"transit": 6, "profection": 2},
        duplicate_factor_count=1,
    )
    assert breakdown.support_score == 3.5


def test_horizon_selection_no_drift_baseline():
    """Verify golden baseline file exists and contains deterministic selection triples."""
    import json
    from pathlib import Path

    baseline_path = Path(__file__).parent / "fixtures" / "day_valence" / "horizon_selection_baseline.json"
    assert baseline_path.exists()

    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert "structure_boundaries_control" in data
    assert "communication_learning_documents" in data
    assert "relationships_values_closeness" in data

    s_items = data["structure_boundaries_control"]["selection"]["items"]
    assert len(s_items) == 3
    selected_ids = tuple(item["activation_id"] for item in s_items)
    assert selected_ids == ("long-structure", "medium-structure", "fast-structure")
