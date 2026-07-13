# ############################################################################
# AI_HEADER: TEST_SOLARSAGE_CONTRACTS_ACTIVATION — shared activation contract tests.
# ROLE: Proves shared activation fields, defaults, literals, constraints, and validator behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SOLARSAGE-CONTRACTS-ACTIVATION
# purpose: Validate shared-only activation contract semantics before boundary wrappers apply casing.
# owns:
#   - packages/py-contracts/tests/test_activation_contract.py
# inputs: solarsage_contracts activation models.
# outputs: pytest assertions.
# dependencies: pytest, pydantic, solarsage_contracts.activation.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Shared field order, defaults, constraints, literals, and validator message remain stable.
# failure_policy: pytest failure.
# END_MODULE_CONTRACT: M-TEST-SOLARSAGE-CONTRACTS-ACTIVATION

# START_MODULE_MAP: M-TEST-SOLARSAGE-CONTRACTS-ACTIVATION
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - SHARED_CONTRACT_ASSERTIONS: validates shared model behavior
# owned_tests:
#   - packages/py-contracts/tests/test_activation_contract.py
# END_MODULE_MAP: M-TEST-SOLARSAGE-CONTRACTS-ACTIVATION

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from solarsage_contracts.activation import (
    ActivationEvidenceContract,
    ActivationLayerContract,
)


EVIDENCE_FIELDS = [
    "id",
    "technique",
    "technique_family",
    "target_type",
    "target_key",
    "kind",
    "active",
    "source_planet",
    "source_frame",
    "target_planet",
    "target_frame",
    "aspect",
    "orb",
    "applying",
    "active_from",
    "exact_at",
    "active_until",
    "phase",
    "house",
    "lot",
    "angle",
    "strength",
    "polarity",
    "weight_hint",
    "evidence",
    "debug",
]

LAYER_FIELDS = [
    "schema_version",
    "activation_layer_version",
    "calculation_version",
    "target_date",
    "target_time",
    "target_tz",
    "house_system",
    "activations",
    "by_planet",
    "by_house",
    "by_lot",
    "by_angle",
    "warnings",
]


# START_BLOCK: SHARED_CONTRACT_ASSERTIONS
def _evidence_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": "act-001",
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "target_type": "planet",
        "target_key": "PLUTO",
        "kind": "opposition",
        "strength": 0.72,
        "evidence": "Transit Moon opposition natal Pluto, orb 1.05°",
    }
    payload.update(overrides)
    return payload


def _layer_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "calculation_version": "ss-calc-1.2.0",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "WHOLE_SIGN",
        "activations": [_evidence_payload()],
        "by_planet": {"PLUTO": ["act-001"]},
        "by_house": {},
        "by_lot": {},
        "by_angle": {},
    }
    payload.update(overrides)
    return payload


def _constraint_values(field_name: str) -> tuple[float | None, float | None]:
    field = ActivationEvidenceContract.model_fields[field_name]
    ge_value = None
    le_value = None
    for metadata in field.metadata:
        if hasattr(metadata, "ge"):
            ge_value = metadata.ge
        if hasattr(metadata, "le"):
            le_value = metadata.le
    return ge_value, le_value


def test_exact_field_order():
    assert list(ActivationEvidenceContract.model_fields) == EVIDENCE_FIELDS
    assert list(ActivationLayerContract.model_fields) == LAYER_FIELDS


def test_required_default_and_default_factory_matrix():
    evidence_required = {
        "id",
        "technique",
        "technique_family",
        "target_type",
        "target_key",
        "kind",
        "strength",
        "evidence",
    }
    layer_required = {
        "calculation_version",
        "target_date",
        "target_time",
        "target_tz",
        "house_system",
        "activations",
        "by_planet",
        "by_house",
        "by_lot",
        "by_angle",
    }

    assert {
        name for name, field in ActivationEvidenceContract.model_fields.items() if field.is_required()
    } == evidence_required
    assert {
        name for name, field in ActivationLayerContract.model_fields.items() if field.is_required()
    } == layer_required

    assert ActivationEvidenceContract.model_fields["active"].default is True
    for name in (
        "source_planet",
        "source_frame",
        "target_planet",
        "target_frame",
        "aspect",
        "orb",
        "applying",
        "active_from",
        "exact_at",
        "active_until",
        "house",
        "lot",
        "angle",
        "weight_hint",
    ):
        assert ActivationEvidenceContract.model_fields[name].default is None
    assert ActivationEvidenceContract.model_fields["phase"].default == "background"
    assert ActivationEvidenceContract.model_fields["polarity"].default == "neutral"
    assert ActivationEvidenceContract.model_fields["debug"].default_factory is dict

    assert ActivationLayerContract.model_fields["schema_version"].default == "activation-layer.v1"
    assert ActivationLayerContract.model_fields["activation_layer_version"].default == "al-1.1"
    assert ActivationLayerContract.model_fields["warnings"].default_factory is list


@pytest.mark.parametrize("bad_strength", [-0.01, 1.01])
def test_strength_rejects_out_of_range_values(bad_strength: float):
    with pytest.raises(ValidationError):
        ActivationEvidenceContract.model_validate(_evidence_payload(strength=bad_strength))

    assert _constraint_values("strength") == (0.0, 1.0)


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        ActivationEvidenceContract.model_validate(_evidence_payload(unexpected="nope"))


@pytest.mark.parametrize("target_type", ["planet", "house", "lot", "angle", "sphere"])
def test_all_target_type_literal_values_accepted(target_type: str):
    ev = ActivationEvidenceContract.model_validate(_evidence_payload(target_type=target_type))
    assert ev.target_type == target_type


@pytest.mark.parametrize("phase", ["applying", "exact", "separating", "background", "period"])
def test_all_phase_literal_values_accepted(phase: str):
    ev = ActivationEvidenceContract.model_validate(_evidence_payload(phase=phase))
    assert ev.phase == phase


@pytest.mark.parametrize("polarity", ["supportive", "tense", "mixed", "neutral"])
def test_all_polarity_literal_values_accepted(polarity: str):
    ev = ActivationEvidenceContract.model_validate(_evidence_payload(polarity=polarity))
    assert ev.polarity == polarity


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [("target_type", "asteroid"), ("phase", "future"), ("polarity", "chaotic")],
)
def test_unknown_literal_values_rejected(field_name: str, bad_value: str):
    with pytest.raises(ValidationError):
        ActivationEvidenceContract.model_validate(_evidence_payload(**{field_name: bad_value}))


def test_index_validator_accepts_valid_references():
    layer = ActivationLayerContract[ActivationEvidenceContract].model_validate(_layer_payload())
    assert layer.by_planet == {"PLUTO": ["act-001"]}


@pytest.mark.parametrize(
    ("map_name", "bad_map"),
    [
        ("by_planet", {"PLUTO": ["missing-id"]}),
        ("by_house", {"10": ["missing-id"]}),
        ("by_lot", {"FORTUNE": ["missing-id"]}),
        ("by_angle", {"ASC": ["missing-id"]}),
    ],
)
def test_index_validator_rejects_each_invalid_map(map_name: str, bad_map: dict[str, list[str]]):
    with pytest.raises(
        ValidationError,
        match=f"{map_name}\\[.*\\] references 'missing-id' which is not present in activations",
    ):
        ActivationLayerContract[ActivationEvidenceContract].model_validate(
            _layer_payload(**{map_name: bad_map})
        )


def test_generic_layer_materializes_activation_evidence_contract():
    layer = ActivationLayerContract[ActivationEvidenceContract].model_validate(_layer_payload())
    assert type(layer.activations[0]) is ActivationEvidenceContract


def test_default_lists_and_dicts_are_not_shared_between_instances():
    first_ev = ActivationEvidenceContract.model_validate(_evidence_payload(id="first"))
    second_ev = ActivationEvidenceContract.model_validate(_evidence_payload(id="second"))
    first_ev.debug["mutated"] = True
    assert second_ev.debug == {}

    first_layer = ActivationLayerContract[ActivationEvidenceContract].model_validate(_layer_payload())
    second_layer = ActivationLayerContract[ActivationEvidenceContract].model_validate(_layer_payload())
    first_layer.warnings.append("mutated")
    assert second_layer.warnings == []
# END_BLOCK: SHARED_CONTRACT_ASSERTIONS
