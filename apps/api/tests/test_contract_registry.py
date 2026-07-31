# ############################################################################
# AI_HEADER: TEST_CONTRACT_REGISTRY — explicit public contract registry tests.
# ROLE: Guards OpenAPI root registration against string lookup and shared contract leaks.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CONTRACT-REGISTRY
# purpose: Validate the API public contract root registry and exporter integration.
# owns:
#   - apps/api/tests/test_contract_registry.py
# inputs: contract_registry module, export_openapi source, generated OpenAPI artifact.
# outputs: pytest assertions.
# dependencies: pytest, ast/json stdlib, app.schemas.contract_registry.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Public roots are exactly the accepted class objects in stable order.
#   - Exporter does not use string-name getattr registry lookup.
#   - Generated OpenAPI root dummy paths and component names stay unchanged.
# failure_policy: pytest failure.
# END_MODULE_CONTRACT: M-TEST-CONTRACT-REGISTRY

# START_MODULE_MAP: M-TEST-CONTRACT-REGISTRY
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - REGISTRY_ASSERTIONS: tuple/order/class validation behavior.
#   - EXPORTER_ASSERTIONS: AST guard and generated artifact checks.
# owned_tests:
#   - apps/api/tests/test_contract_registry.py
# END_MODULE_MAP: M-TEST-CONTRACT-REGISTRY

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import ConfigDict

from app.schemas._base import CamelModel
from app.schemas.access import AccessSummary
from app.schemas.contract_registry import PUBLIC_CONTRACT_ROOTS, validate_public_contract_roots
from app.schemas.promo import PromoCodeRequest


# START_BLOCK: REGISTRY_ASSERTIONS
REPO_ROOT = Path(__file__).resolve().parents[3]
EXPORTER = REPO_ROOT / "scripts/contracts/export_openapi.py"
OPENAPI = REPO_ROOT / "packages/contracts/openapi.json"

EXPECTED_ROOT_NAMES = [
    "AccessSummary",
    "ActivationLayer",
    "AuthError",
    "AuthSession",
    "BirthData",
    "CalendarPayload",
    "CheckinCreate",
    "CheckinMetrics",
    "CheckinResponse",
    "ConvergenceEvidence",
    "DayHistoryPayload",
    "FocusEventDrilldown",
    "HoraryAnswerRead",
    "HoraryQuestionCreate",
    "HoraryQuestionRead",
    "HoraryQuotaRead",
    "LocationData",
    "NatalPayload",
    "ProductsListResponse",
    "ProfileRead",
    "ProfileWrite",
    "PromoCodeRequest",
    "PromoErrorDetail",
    "PromoGrantSummary",
    "PromoOffer",
    "PromoPreviewResponse",
    "PromoRedeemResponse",
    "PurchaseStartResponse",
    "PurchaseStatusResponse",
    "ScoringV2Result",
    "SubscriptionStartResponse",
    "SubscriptionStatusResponse",
    "TelegramAuthRequest",
    "TodayConvergencePayload",
    "TodayPayload",
    "YesterdayCheckinResponse",
]


def test_public_contract_roots_have_exact_names_and_order() -> None:
    assert [root.__name__ for root in PUBLIC_CONTRACT_ROOTS] == EXPECTED_ROOT_NAMES


def test_public_contract_roots_are_unique_camelmodel_subclasses() -> None:
    expected_len = len(EXPECTED_ROOT_NAMES)
    assert len(PUBLIC_CONTRACT_ROOTS) == expected_len
    assert len({id(root) for root in PUBLIC_CONTRACT_ROOTS}) == expected_len
    assert len({root.__name__ for root in PUBLIC_CONTRACT_ROOTS}) == expected_len
    assert all(issubclass(root, CamelModel) for root in PUBLIC_CONTRACT_ROOTS)


def test_canonical_validation_returns_same_tuple() -> None:
    assert validate_public_contract_roots() is PUBLIC_CONTRACT_ROOTS
    assert validate_public_contract_roots(PUBLIC_CONTRACT_ROOTS) is PUBLIC_CONTRACT_ROOTS


def test_duplicate_object_is_rejected() -> None:
    roots = (AccessSummary, AccessSummary)
    with pytest.raises(ValueError, match="duplicate-object"):
        validate_public_contract_roots(roots)


def test_unsorted_roots_are_rejected() -> None:
    roots = (PUBLIC_CONTRACT_ROOTS[1], PUBLIC_CONTRACT_ROOTS[0])
    with pytest.raises(ValueError, match="unsorted"):
        validate_public_contract_roots(roots)


def test_non_class_is_rejected() -> None:
    with pytest.raises(TypeError, match="non-class"):
        validate_public_contract_roots(("AccessSummary",))  # type: ignore[arg-type]


def test_non_camelmodel_class_is_rejected() -> None:
    class Plain:
        pass

    with pytest.raises(TypeError, match="non-camelmodel-subclass"):
        validate_public_contract_roots((Plain,))  # type: ignore[arg-type]


def test_shared_contract_suffix_is_rejected() -> None:
    class LocalContract(CamelModel):
        value: str

    with pytest.raises(TypeError, match="shared-contract-suffix"):
        validate_public_contract_roots((LocalContract,))


def test_duplicate_schema_title_is_rejected() -> None:
    class Alpha(CamelModel):
        model_config = ConfigDict(**CamelModel.model_config, title="DuplicateTitle")
        value: str

    class Beta(CamelModel):
        model_config = ConfigDict(**CamelModel.model_config, title="DuplicateTitle")
        value: str

    with pytest.raises(ValueError, match="duplicate-schema-title"):
        validate_public_contract_roots((Alpha, Beta))


def test_promo_code_request_json_schema_has_no_raw_token_or_validators() -> None:
    schema = PromoCodeRequest.model_json_schema()
    token_prop = schema["properties"]["token"]

    assert token_prop.get("writeOnly") is True
    assert token_prop.get("format") == "password"
    assert "default" not in token_prop
    assert "example" not in token_prop
    assert "minLength" not in token_prop
    assert "maxLength" not in token_prop
    assert "pattern" not in token_prop
# END_BLOCK: REGISTRY_ASSERTIONS


# START_BLOCK: EXPORTER_ASSERTIONS
def test_exporter_ast_contains_no_string_registry_or_getattr_lookup() -> None:
    tree = ast.parse(EXPORTER.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "_TOP_LEVEL_NAMES" not in names
    assert "schemas_pkg" not in names
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "getattr"


def test_exporter_imports_contract_registry() -> None:
    tree = ast.parse(EXPORTER.read_text(encoding="utf-8"))
    imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert any(node.module == "app.schemas.contract_registry" for node in imports)


def test_generated_openapi_has_previous_dummy_root_paths() -> None:
    data = json.loads(OPENAPI.read_text(encoding="utf-8"))
    paths = sorted(data["paths"])
    assert paths == sorted(f"/__contracts__/{name.lower()}" for name in EXPECTED_ROOT_NAMES)


def test_generated_openapi_keeps_public_activation_names_without_shared_contract_components() -> None:
    data = json.loads(OPENAPI.read_text(encoding="utf-8"))
    schema_names = set(data["components"]["schemas"])
    assert "ActivationEvidence" in schema_names
    assert "ActivationLayer" in schema_names
    assert "TodayV2Provenance" in schema_names
    assert "TodayV2HorizonTiming" in schema_names
    assert "TodayV2Horizon" in schema_names
    assert "TodayV2HorizonsBlock" in schema_names
    assert "PromoCodeRequest" in schema_names
    assert "PromoOffer" in schema_names
    assert "PromoPreviewResponse" in schema_names
    assert "PromoGrantSummary" in schema_names
    assert "PromoRedeemResponse" in schema_names
    assert "PromoErrorDetail" in schema_names
    assert "/__contracts__/todayv2horizonsblock" not in data["paths"]
    assert not any("Contract" in name for name in schema_names)
# END_BLOCK: EXPORTER_ASSERTIONS
