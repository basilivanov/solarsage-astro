# ############################################################################
# AI_HEADER: TEST_SOLARSAGE_CONTRACTS_BOUNDARY_CONFIGS — API/sidecar facade parity tests.
# ROLE: Proves thin wrappers preserve shared fields while applying only boundary casing config.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SOLARSAGE-CONTRACTS-BOUNDARY-CONFIGS
# purpose: Validate API camelCase and sidecar snake_case wrapper behavior against shared contracts.
# owns:
#   - packages/py-contracts/tests/test_boundary_configs.py
# inputs: Shared, API, and sidecar activation models plus canonical fixtures.
# outputs: pytest assertions.
# dependencies: pytest, pydantic, app schemas, solarsage schemas.
# side_effects: sys.path bootstrap for test-only app imports.
# emitted_logs: none.
# invariants:
#   - Wrappers contain no local fields, validators, literal aliases, or version literals.
#   - API public wire remains camelCase; sidecar wire remains snake_case.
# failure_policy: pytest failure.
# END_MODULE_CONTRACT: M-TEST-SOLARSAGE-CONTRACTS-BOUNDARY-CONFIGS

# START_MODULE_MAP: M-TEST-SOLARSAGE-CONTRACTS-BOUNDARY-CONFIGS
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - TEST_BOOTSTRAP: adds app roots to sys.path for boundary import checks
#   - FIXTURE_HELPERS: canonical fixture loading and dumping
#   - BOUNDARY_ASSERTIONS: wrapper config and AST guard assertions
# owned_tests:
#   - packages/py-contracts/tests/test_boundary_configs.py
# END_MODULE_MAP: M-TEST-SOLARSAGE-CONTRACTS-BOUNDARY-CONFIGS

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from solarsage_contracts.activation import (
    ActivationEvidenceContract,
    ActivationLayerContract,
)


# START_BLOCK: TEST_BOOTSTRAP
REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "apps" / "api"
SIDECAR_ROOT = REPO_ROOT / "apps" / "solarsage"
for root in (API_ROOT, SIDECAR_ROOT):
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
# END_BLOCK: TEST_BOOTSTRAP

from app.schemas._base import CamelModel  # noqa: E402
from app.schemas.activation import ActivationEvidence as ApiActivationEvidence  # noqa: E402
from app.schemas.activation import ActivationLayer as ApiActivationLayer  # noqa: E402
from solarsage.schemas.activation import ActivationEvidence as SidecarActivationEvidence  # noqa: E402
from solarsage.schemas.activation import ActivationLayer as SidecarActivationLayer  # noqa: E402


SNAKE_FIXTURE = REPO_ROOT / "packages/py-contracts/tests/fixtures/activation-layer-snake.json"
CAMEL_FIXTURE = REPO_ROOT / "apps/api/tests/fixtures/contracts/activation-layer-public-camel.json"
API_WRAPPER = REPO_ROOT / "apps/api/app/schemas/activation.py"
SIDECAR_WRAPPER = REPO_ROOT / "apps/solarsage/solarsage/schemas/activation.py"
SHARED_PACKAGE = REPO_ROOT / "packages/py-contracts/solarsage_contracts"

EXPECTED_ALIAS_MAP = {
    "technique_family": "techniqueFamily",
    "target_type": "targetType",
    "target_key": "targetKey",
    "source_planet": "sourcePlanet",
    "source_frame": "sourceFrame",
    "target_planet": "targetPlanet",
    "target_frame": "targetFrame",
    "active_from": "activeFrom",
    "exact_at": "exactAt",
    "active_until": "activeUntil",
    "weight_hint": "weightHint",
    "schema_version": "schemaVersion",
    "activation_layer_version": "activationLayerVersion",
    "calculation_version": "calculationVersion",
    "target_date": "targetDate",
    "target_time": "targetTime",
    "target_tz": "targetTz",
    "house_system": "houseSystem",
    "by_planet": "byPlanet",
    "by_house": "byHouse",
    "by_lot": "byLot",
    "by_angle": "byAngle",
}


# START_BLOCK: FIXTURE_HELPERS
def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def _canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _field_default_signature(model: type[Any]) -> dict[str, tuple[bool, Any, bool]]:
    return {
        name: (field.is_required(), field.default, field.default_factory is not None)
        for name, field in model.model_fields.items()
    }


def _strength_constraints(model: type[Any]) -> tuple[float | None, float | None]:
    ge_value = None
    le_value = None
    for metadata in model.model_fields["strength"].metadata:
        if hasattr(metadata, "ge"):
            ge_value = metadata.ge
        if hasattr(metadata, "le"):
            le_value = metadata.le
    return ge_value, le_value


def _validation_error_message(callable_obj: Any) -> str:
    with pytest.raises(ValidationError) as exc_info:
        callable_obj()
    return str(exc_info.value)
# END_BLOCK: FIXTURE_HELPERS


# START_BLOCK: BOUNDARY_ASSERTIONS
def test_api_mro_and_issubclass_requirements():
    assert issubclass(ApiActivationEvidence, CamelModel)
    assert issubclass(ApiActivationLayer, CamelModel)
    assert issubclass(ApiActivationEvidence, ActivationEvidenceContract)
    assert issubclass(ApiActivationLayer, ActivationLayerContract)

    layer = ApiActivationLayer.model_validate(_load_json(SNAKE_FIXTURE))
    assert type(layer.activations[0]) is ApiActivationEvidence


def test_api_alias_map_exact_and_single_word_fields_unchanged():
    for model in (ApiActivationEvidence, ApiActivationLayer):
        for name, field in model.model_fields.items():
            alias = field.alias or name
            if name in EXPECTED_ALIAS_MAP:
                assert alias == EXPECTED_ALIAS_MAP[name]
            elif "_" not in name:
                assert alias == name


def test_api_accepts_snake_and_camel_fixtures_and_dumps_public_camel():
    snake = _load_json(SNAKE_FIXTURE)
    camel = _load_json(CAMEL_FIXTURE)

    from_snake = ApiActivationLayer.model_validate(snake)
    from_camel = ApiActivationLayer.model_validate(camel)
    assert len(from_snake.activations) == 2
    assert len(from_camel.activations) == 2

    dumped = from_snake.model_dump(mode="json", by_alias=True)
    assert _canonical_json(dumped) == CAMEL_FIXTURE.read_text(encoding="utf-8")


def test_sidecar_validates_snake_and_dumps_byte_matching_snake():
    snake = _load_json(SNAKE_FIXTURE)
    layer = SidecarActivationLayer.model_validate(snake)
    dumped = layer.model_dump(mode="json")
    assert _canonical_json(dumped) == SNAKE_FIXTURE.read_text(encoding="utf-8")


def test_sidecar_rejects_camel_only_root_and_evidence_aliases():
    camel = _load_json(CAMEL_FIXTURE)
    with pytest.raises(ValidationError):
        SidecarActivationLayer.model_validate(camel)

    snake = _load_json(SNAKE_FIXTURE)
    evidence = dict(snake["activations"][0])
    evidence["techniqueFamily"] = evidence.pop("technique_family")
    snake["activations"] = [evidence]
    with pytest.raises(ValidationError):
        SidecarActivationLayer.model_validate(snake)


def test_wrapper_fields_required_defaults_and_constraints_match_shared():
    assert list(ApiActivationEvidence.model_fields) == list(ActivationEvidenceContract.model_fields)
    assert list(SidecarActivationEvidence.model_fields) == list(ActivationEvidenceContract.model_fields)
    assert list(ApiActivationLayer.model_fields) == list(ActivationLayerContract.model_fields)
    assert list(SidecarActivationLayer.model_fields) == list(ActivationLayerContract.model_fields)

    assert _field_default_signature(ApiActivationEvidence) == _field_default_signature(
        ActivationEvidenceContract
    )
    assert _field_default_signature(SidecarActivationEvidence) == _field_default_signature(
        ActivationEvidenceContract
    )
    assert _field_default_signature(ApiActivationLayer) == _field_default_signature(
        ActivationLayerContract
    )
    assert _field_default_signature(SidecarActivationLayer) == _field_default_signature(
        ActivationLayerContract
    )
    assert _strength_constraints(ApiActivationEvidence) == (0.0, 1.0)
    assert _strength_constraints(SidecarActivationEvidence) == (0.0, 1.0)


def test_wrappers_execute_identical_shared_index_validator_behavior_and_message():
    snake = _load_json(SNAKE_FIXTURE)
    snake["by_planet"] = {"PLUTO": ["missing-id"]}

    api_message = _validation_error_message(lambda: ApiActivationLayer.model_validate(snake))
    sidecar_message = _validation_error_message(lambda: SidecarActivationLayer.model_validate(snake))
    expected = "by_planet[PLUTO] references 'missing-id' which is not present in activations"
    assert expected in api_message
    assert expected in sidecar_message


def test_nested_activation_runtime_type_is_boundary_wrapper():
    snake = _load_json(SNAKE_FIXTURE)
    api_layer = ApiActivationLayer.model_validate(snake)
    sidecar_layer = SidecarActivationLayer.model_validate(snake)
    assert type(api_layer.activations[0]) is ApiActivationEvidence
    assert type(api_layer.activations[0]) is not ActivationEvidenceContract
    assert type(sidecar_layer.activations[0]) is SidecarActivationEvidence
    assert type(sidecar_layer.activations[0]) is not ActivationEvidenceContract


def test_wrapper_ast_contains_no_local_contract_implementation():
    forbidden_literals = {"activation-layer.v1", "al-1.1", "ss-calc-1.2.0"}
    for path in (API_WRAPPER, SIDECAR_WRAPPER):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in {"ActivationEvidence", "ActivationLayer"}:
                for child in node.body:
                    assert not isinstance(child, ast.AnnAssign)
                    if isinstance(child, ast.FunctionDef):
                        decorator_names = [ast.unparse(decorator) for decorator in child.decorator_list]
                        assert "model_validator" not in decorator_names
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        assert target.id not in {
                            "ActivationTargetType",
                            "ActivationPolarity",
                            "ActivationPhase",
                        }
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value not in forbidden_literals


def test_shared_package_import_scan_contains_no_app_imports():
    forbidden_roots = {"app", "apps", "solarsage"}
    for path in sorted(SHARED_PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str | None] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module)
            for module in modules:
                if not module:
                    continue
                assert module.split(".", 1)[0] not in forbidden_roots
# END_BLOCK: BOUNDARY_ASSERTIONS
