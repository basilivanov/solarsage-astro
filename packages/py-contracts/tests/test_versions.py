# ############################################################################
# AI_HEADER: TEST_SOLARSAGE_CONTRACTS_VERSIONS — shared version source tests.
# ROLE: Proves activation-layer wire versions are shared and app facades only re-export them.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SOLARSAGE-CONTRACTS-VERSIONS
# purpose: Validate shared wire version constants, app re-exports, and package metadata.
# owns:
#   - packages/py-contracts/tests/test_versions.py
# inputs: shared package, app version files, app pyproject metadata.
# outputs: pytest assertions.
# dependencies: ast, importlib.metadata, tomllib, solarsage_contracts.
# side_effects: sys.path bootstrap for test-only app imports.
# emitted_logs: none.
# invariants:
#   - Wire literals exist in shared versions only for product code.
#   - App pyprojects depend on solarsage-contracts exactly once.
#   - Package version is distinct from wire versions.
# failure_policy: pytest failure.
# END_MODULE_CONTRACT: M-TEST-SOLARSAGE-CONTRACTS-VERSIONS

# START_MODULE_MAP: M-TEST-SOLARSAGE-CONTRACTS-VERSIONS
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - VERSION_ASSERTIONS: shared/app version and metadata checks
# owned_tests:
#   - packages/py-contracts/tests/test_versions.py
# END_MODULE_MAP: M-TEST-SOLARSAGE-CONTRACTS-VERSIONS

from __future__ import annotations

import ast
import sys
import tomllib
from importlib import metadata
from pathlib import Path

from solarsage_contracts import (
    ACTIVATION_LAYER_VERSION,
    ACTIVATION_SCHEMA_VERSION,
    CALCULATION_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "apps" / "api"
SIDECAR_ROOT = REPO_ROOT / "apps" / "solarsage"
for root in (API_ROOT, SIDECAR_ROOT):
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


# START_BLOCK: VERSION_ASSERTIONS
def _module_imports_shared_versions(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "solarsage_contracts.versions":
            imported = {alias.name for alias in node.names}
            if {"ACTIVATION_LAYER_VERSION", "CALCULATION_VERSION"}.issubset(imported):
                return True
    return False


def _module_has_duplicated_version_assignment(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        target_names = {target.id for target in targets if isinstance(target, ast.Name)}
        if not target_names.intersection({"ACTIVATION_LAYER_VERSION", "CALCULATION_VERSION"}):
            continue
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return True
    return False


def _dependencies(path: Path) -> list[str]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return list(data["project"]["dependencies"])


def test_exact_shared_wire_constants():
    assert ACTIVATION_SCHEMA_VERSION == "activation-layer.v1"
    assert ACTIVATION_LAYER_VERSION == "al-1.1"
    assert CALCULATION_VERSION == "ss-calc-1.2.0"


def test_app_core_values_equal_shared_values():
    from app.core.versions import ACTIVATION_LAYER_VERSION as API_AL
    from app.core.versions import CALCULATION_VERSION as API_CALC
    from solarsage.core.versions import ACTIVATION_LAYER_VERSION as SIDECAR_AL
    from solarsage.core.versions import CALCULATION_VERSION as SIDECAR_CALC

    assert API_AL == ACTIVATION_LAYER_VERSION
    assert API_CALC == CALCULATION_VERSION
    assert SIDECAR_AL == ACTIVATION_LAYER_VERSION
    assert SIDECAR_CALC == CALCULATION_VERSION


def test_app_core_files_reexport_without_duplicated_literals():
    api_versions = REPO_ROOT / "apps/api/app/core/versions.py"
    sidecar_versions = REPO_ROOT / "apps/solarsage/solarsage/core/versions.py"
    for path in (api_versions, sidecar_versions):
        assert _module_imports_shared_versions(path)
        assert not _module_has_duplicated_version_assignment(path)


def test_app_pyprojects_contain_exact_dependency_once():
    for path in (REPO_ROOT / "apps/api/pyproject.toml", REPO_ROOT / "apps/solarsage/pyproject.toml"):
        deps = _dependencies(path)
        assert deps.count("solarsage-contracts==0.1.0") == 1


def test_package_distribution_metadata_is_distinct_from_wire_versions():
    distribution_version = metadata.version("solarsage-contracts")
    assert distribution_version == "0.1.0"
    assert distribution_version not in {
        ACTIVATION_SCHEMA_VERSION,
        ACTIVATION_LAYER_VERSION,
        CALCULATION_VERSION,
    }
# END_BLOCK: VERSION_ASSERTIONS
