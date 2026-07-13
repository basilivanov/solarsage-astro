# ############################################################################
# AI_HEADER: HORIZON_SELECTION_TESTKIT — shared synthetic builders for B2A selection tests.
# ROLE: Supplies deterministic, non-user-data fixtures to core and ordering selection test modules.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-SELECTION-TESTKIT
# purpose: Build synthetic ActivationLayer, ScoringV2Result, candidate, and golden-story inputs for B2A tests.
# owns:
#   - apps/api/tests/_horizon_selection_testkit.py
# inputs: Explicit test-only overrides, stable story ids, and typed candidate anchor data.
# outputs: Deterministic Pydantic test inputs without production fixture/demo imports.
# dependencies: app.schemas activation/scoring/horizon selection models and HorizonSelectionService.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No real user data, network, database, clock, or production fixture imports are used.
#   - Every builder preserves stable ids and deterministic ordering needed by B2A proofs.
# failure_policy: raises Pydantic validation errors for invalid synthetic test payloads.
# END_MODULE_CONTRACT: M-HORIZON-SELECTION-TESTKIT

# START_MODULE_MAP: M-HORIZON-SELECTION-TESTKIT
# public_entrypoints:
#   - build_activation
#   - build_layer
#   - build_scoring
#   - build_story
#   - build_control_selection
#   - build_candidate_from_anchor
#   - build_equal_score_triple_population
# semantic_blocks:
#   - SYNTHETIC_INPUT_BUILDERS: activation, layer, scoring, and golden-story builders.
#   - TYPED_SELECTION_BUILDERS: selected-triple and candidate builders for ordering assertions.
# owned_tests:
#   - apps/api/tests/test_horizon_selection_service.py
#   - apps/api/tests/test_horizon_selection_ordering.py
# END_MODULE_MAP: M-HORIZON-SELECTION-TESTKIT

# START_BLOCK: SYNTHETIC_INPUT_BUILDERS
from __future__ import annotations

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.horizon_selection import HorizonCandidate, SelectedHorizonAnchor, SelectedHorizonTriple
from app.schemas.scoring_v2 import ScoringV2Result, SphereContribution, SphereScoreV2
from app.services.horizon_selection_service import HorizonSelectionService


def build_activation(**overrides: object) -> ActivationEvidence:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_activation
    # purpose: Build one deterministic synthetic activation evidence item.
    # inputs: overrides - explicit test-only ActivationEvidence field replacements.
    # returns: validated ActivationEvidence.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError for an invalid synthetic payload.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_activation
    payload = {
        "id": "act",
        "technique": "annual_profection",
        "technique_family": "profection",
        "target_type": "planet",
        "target_key": "SATURN",
        "kind": "story",
        "strength": 0.8,
        "evidence": "Synthetic selection evidence",
        "active_from": "2026-01-01",
        "exact_at": None,
        "active_until": "2026-12-31",
        "polarity": "neutral",
        "source_planet": None,
        "target_planet": "SATURN",
    }
    payload.update(overrides)
    return ActivationEvidence(**payload)


_MEDIUM_WINDOW = ("2026-03-01T00:00:00Z", "2026-09-30T00:00:00Z")
_FAST_WINDOW = ("2026-07-12T00:00:00Z", "2026-07-12T23:00:00Z")


def _build_transit(
    identifier: str,
    source_planet: str,
    target_planet: str,
    strength: float,
    *,
    medium: bool = False,
    exact_at: str = "2026-07-12T12:00:00Z",
) -> ActivationEvidence:
    active_from, active_until = _MEDIUM_WINDOW if medium else _FAST_WINDOW
    return build_activation(
        id=identifier,
        technique="transit_to_natal",
        technique_family="transit",
        source_planet=source_planet,
        target_key=target_planet,
        target_planet=target_planet,
        strength=strength,
        active_from=active_from,
        exact_at=exact_at,
        active_until=active_until,
    )


def build_layer(
    activations: list[ActivationEvidence],
    *,
    target_time: str = "12:00",
) -> ActivationLayer:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_layer
    # purpose: Build a deterministic request activation layer for selector tests.
    # inputs: activations - ordered synthetic evidence; target_time - explicit UTC request time.
    # returns: validated ActivationLayer.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError for invalid test data.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_layer
    return ActivationLayer(
        calculation_version="calc",
        target_date="2026-07-12",
        target_time=target_time,
        target_tz="UTC",
        house_system="WHOLE_SIGN",
        activations=activations,
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )


def build_scoring(
    activations: list[ActivationEvidence],
    sphere_by_activation: dict[str, tuple[str, float]],
) -> ScoringV2Result:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_scoring
    # purpose: Build activation-linked synthetic scoring with only specified contribution mappings.
    # inputs: activations - ordered synthetic evidence; sphere_by_activation - id to technical sphere/amount mapping.
    # returns: validated ScoringV2Result.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError for invalid scoring test payloads.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_scoring
    grouped: dict[str, list[SphereContribution]] = {}
    for activation in activations:
        mapping = sphere_by_activation.get(activation.id)
        if mapping is None:
            continue
        sphere_key, amount = mapping
        grouped.setdefault(sphere_key, []).append(
            SphereContribution(
                sphere=sphere_key,
                source="activation",
                source_id=activation.id,
                amount=amount,
                evidence=f"synthetic:{activation.id}:{sphere_key}",
            )
        )
    sphere_scores = {
        sphere_key: SphereScoreV2(
            key=sphere_key,
            title=sphere_key,
            base_score=0.0,
            activation_score=sum(item.amount for item in contributions),
            convergence_bonus=0.0,
            raw_score=sum(item.amount for item in contributions),
            final_score=sum(item.amount for item in contributions),
            contributions=contributions,
        )
        for sphere_key, contributions in grouped.items()
    }
    return ScoringV2Result(
        canon_versions={"spheres": "v1"},
        day_status="supportive",
        status_breakdown={},
        sphere_scores=sphere_scores,
        top_signals=[],
        top_activations=activations,
        debug={"synthetic": "selection"},
    )


def build_story(
    story: str,
) -> tuple[list[ActivationEvidence], dict[str, tuple[str, float]], tuple[str, str, str], str]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_story
    # purpose: Build one of three deterministic coherent B2A story corpora plus stronger unrelated alternatives.
    # inputs: story - stable internal golden story id.
    # returns: activations, scoring mapping, expected ordered selected ids, and story theme id.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for an unknown story id.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_story
    if story == "structure_boundaries_control":
        activations = [
            build_activation(id="long-structure", target_key="SATURN", target_planet="SATURN", strength=0.72),
            _build_transit("medium-structure", "PLUTO", "SATURN", 0.63, medium=True),
            _build_transit("fast-structure", "MOON", "PLUTO", 0.66),
            _build_transit("venus-strong", "VENUS", "JUPITER", 0.99, exact_at="2026-07-12T11:00:00Z"),
        ]
        return (
            activations,
            {
                "long-structure": ("work_status_achievement", 2.0),
                "medium-structure": ("crisis_transformation_control", 1.8),
                "fast-structure": ("crisis_transformation_control", 1.7),
                "venus-strong": ("meaning_expansion_vector", 3.5),
            },
            ("long-structure", "medium-structure", "fast-structure"),
            story,
        )
    if story == "communication_learning_documents":
        activations = [
            build_activation(id="long-comm", target_key="MERCURY", target_planet="MERCURY", strength=0.75),
            _build_transit("medium-comm", "PLUTO", "MERCURY", 0.64, medium=True),
            _build_transit("fast-comm", "MOON", "MERCURY", 0.69),
            _build_transit("jupiter-strong", "JUPITER", "VENUS", 0.98, exact_at="2026-07-12T11:00:00Z"),
        ]
        return (
            activations,
            {
                "long-comm": ("thinking_speech_learning", 2.1),
                "medium-comm": ("thinking_speech_learning", 1.9),
                "fast-comm": ("thinking_speech_learning", 1.8),
                "jupiter-strong": ("meaning_expansion_vector", 3.8),
            },
            ("long-comm", "medium-comm", "fast-comm"),
            story,
        )
    if story == "relationships_values_closeness":
        activations = [
            build_activation(id="long-rel", target_key="VENUS", target_planet="VENUS", strength=0.78),
            _build_transit("medium-rel", "PLUTO", "VENUS", 0.65, medium=True),
            _build_transit("fast-rel", "MOON", "VENUS", 0.68),
            _build_transit("mars-strong", "MARS", "SATURN", 0.97, exact_at="2026-07-12T11:00:00Z"),
        ]
        return (
            activations,
            {
                "long-rel": ("relationships_partnership", 2.1),
                "medium-rel": ("relationships_partnership", 1.9),
                "fast-rel": ("relationships_partnership", 1.8),
                "mars-strong": ("body_energy_health", 3.9),
            },
            ("long-rel", "medium-rel", "fast-rel"),
            story,
        )
    raise ValueError(f"unknown synthetic story: {story}")


# END_BLOCK: SYNTHETIC_INPUT_BUILDERS


# START_BLOCK: TYPED_SELECTION_BUILDERS
def build_control_selection() -> SelectedHorizonTriple:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_control_selection
    # purpose: Select the structure golden and return its typed selected triple for direct internal tests.
    # inputs: none.
    # returns: SelectedHorizonTriple.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises AssertionError if the control corpus stops selecting a triple.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_control_selection
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    result = HorizonSelectionService().select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    assert result.selection is not None
    return result.selection


def build_candidate_from_anchor(
    anchor: SelectedHorizonAnchor,
    *,
    activation_id: str | None = None,
    updates: dict[str, object] | None = None,
) -> HorizonCandidate:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_candidate_from_anchor
    # purpose: Convert a selected anchor into a valid candidate while applying explicit test-only identity/field overrides.
    # inputs: anchor - valid selected anchor; activation_id - optional synchronized candidate/timing id; updates - candidate field changes.
    # returns: validated HorizonCandidate.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError for inconsistent overrides.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_candidate_from_anchor
    data = anchor.model_dump()
    if activation_id is not None:
        data["activation_id"] = activation_id
        data["timing"] = {**data["timing"], "activation_id": activation_id}
    if updates:
        data.update(updates)
    return HorizonCandidate.model_validate(data)


def build_equal_score_triple_population() -> tuple[list[ActivationEvidence], dict[str, tuple[str, float]]]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_equal_score_triple_population
    # purpose: Build two equal-score candidates per horizon for triple lexicographic ordering and diagnostics tests.
    # inputs: none.
    # returns: ordered activations and activation-to-sphere mapping.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError for invalid synthetic evidence.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-SELECTION-TESTKIT.build_equal_score_triple_population
    activations = [
        build_activation(id="long-a", target_key="SATURN", target_planet="SATURN", strength=0.8),
        build_activation(id="long-b", target_key="SATURN", target_planet="SATURN", strength=0.8),
        _build_transit("medium-a", "SATURN", "SATURN", 0.8, medium=True),
        _build_transit("medium-b", "SATURN", "SATURN", 0.8, medium=True),
        _build_transit("fast-a", "MOON", "SATURN", 0.8),
        _build_transit("fast-b", "MOON", "SATURN", 0.8),
    ]
    return activations, {activation.id: ("work_status_achievement", 1.0) for activation in activations}


# END_BLOCK: TYPED_SELECTION_BUILDERS
