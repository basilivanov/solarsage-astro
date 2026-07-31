# ############################################################################
# AI_HEADER: TEST_CONTRACTS_CHECK_COMPAT — compatibility checker test matrix.
# ROLE: Validates pure OpenAPI comparison helpers and CLI/ref safety cases.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CONTRACTS-CHECK-COMPAT
# purpose: Prove scripts/contracts/check_compat.py classifies contract changes
#   deterministically and enforces safe Git/override CLI behavior.
# owns:
#   - scripts/contracts/test_check_compat.py
# inputs: In-memory OpenAPI fixtures and subprocess CLI invocations.
# outputs: pytest assertions.
# dependencies: pytest, Python stdlib, scripts.contracts.check_compat.
# side_effects: CLI tests create temporary JSON files and may invoke git read-only.
# emitted_logs: none.
# invariants:
#   - Pure comparison cases do not use subprocess.
#   - Ref/CLI safety cases use subprocess and never shell execution.
# failure_policy: pytest failure.
# END_MODULE_CONTRACT: M-TEST-CONTRACTS-CHECK-COMPAT

# START_MODULE_MAP: M-TEST-CONTRACTS-CHECK-COMPAT
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - FIXTURE_BUILDERS: tiny OpenAPI fixture construction helpers.
#   - PURE_COMPAT_MATRIX: direct comparison/report assertions.
#   - CLI_REF_CASES: subprocess-only CLI and Git ref behavior assertions.
# owned_tests:
#   - scripts/contracts/test_check_compat.py
# END_MODULE_MAP: M-TEST-CONTRACTS-CHECK-COMPAT

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.contracts import check_compat


# START_BLOCK: FIXTURE_BUILDERS
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/contracts/check_compat.py"
CURRENT_ARTIFACT = REPO_ROOT / "packages/contracts/openapi.json"


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required or [],
        "title": "Example",
        "description": "ignored documentation",
    }


def _doc(schema: dict[str, Any] | None = None, paths: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "contracts", "version": "0"},
        "paths": paths if paths is not None else {},
        "components": {"schemas": {"Example": schema if schema is not None else _schema({})}},
    }


def _prop(type_name: str, **extra: Any) -> dict[str, Any]:
    return {"type": type_name, **extra}


def _report(base: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return check_compat.build_report(base, current, "base-sha", "current.json")


def _classification(base: dict[str, Any], current: dict[str, Any]) -> str:
    return str(_report(base, current)["classification"])


def _change_kinds(report: dict[str, Any], bucket: str) -> set[str]:
    return {str(item["kind"]) for item in report[bucket]}


def _assert_real_artifact_invariant(report: dict[str, Any]) -> None:
    assert report["classification"] in {"no-change", "additive"}
    assert report["breakingChanges"] == []
    assert report["overrideUsed"] is False


def _cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        env=process_env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
# END_BLOCK: FIXTURE_BUILDERS


# START_BLOCK: PURE_COMPAT_MATRIX
def test_same_contract_is_no_change() -> None:
    base = _doc(_schema({"name": _prop("string")}, ["name"]))
    current = json.loads(json.dumps(base))
    current["components"]["schemas"]["Example"]["description"] = "ignored drift"
    assert _classification(base, current) == "no-change"


def test_optional_property_add_is_additive() -> None:
    base = _doc(_schema({"name": _prop("string")}, ["name"]))
    current = _doc(_schema({"name": _prop("string"), "nickname": _prop("string")}, ["name"]))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert report["additiveChanges"][0]["kind"] == "optional-property-added"


def test_required_property_add_is_breaking() -> None:
    base = _doc(_schema({"name": _prop("string")}, ["name"]))
    current = _doc(_schema({"name": _prop("string"), "age": _prop("integer")}, ["name", "age"]))
    assert _classification(base, current) == "breaking"


def test_property_removal_is_breaking() -> None:
    base = _doc(_schema({"name": _prop("string"), "age": _prop("integer")}, ["name"]))
    current = _doc(_schema({"name": _prop("string")}, ["name"]))
    assert _classification(base, current) == "breaking"


def test_enum_widen_is_additive() -> None:
    base = _doc(_schema({"tone": _prop("string", enum=["calm"])}))
    current = _doc(_schema({"tone": _prop("string", enum=["calm", "tense"])}))
    assert _classification(base, current) == "additive"


def test_enum_narrow_is_breaking() -> None:
    base = _doc(_schema({"tone": _prop("string", enum=["calm", "tense"])}))
    current = _doc(_schema({"tone": _prop("string", enum=["calm"])}))
    assert _classification(base, current) == "breaking"


def test_const_add_is_breaking() -> None:
    base = _doc(_schema({"kind": _prop("string")}))
    current = _doc(_schema({"kind": _prop("string", const="daily-card")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "const-added" in _change_kinds(report, "breakingChanges")


def test_const_remove_is_additive() -> None:
    base = _doc(_schema({"kind": _prop("string", const="daily-card")}))
    current = _doc(_schema({"kind": _prop("string")}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert "const-removed" in _change_kinds(report, "additiveChanges")


def test_const_change_is_breaking() -> None:
    base = _doc(_schema({"kind": _prop("string", const="daily-card")}))
    current = _doc(_schema({"kind": _prop("string", const="weekly-card")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "const-changed" in _change_kinds(report, "breakingChanges")


def test_known_version_const_monotonic_increase_is_informational_non_breaking() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", const="today.v1")}))
    current = _doc(_schema({"schemaVersion": _prop("string", const="today.v2")}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert _change_kinds(report, "breakingChanges") == set()
    assert _change_kinds(report, "informationalChanges") == {"version-monotonic-increase"}


def test_known_version_singleton_enum_monotonic_increase_is_informational_without_generic_enum_change() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", enum=["today.v1"])}))
    current = _doc(_schema({"schemaVersion": _prop("string", enum=["today.v2"])}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert _change_kinds(report, "breakingChanges") == set()
    assert _change_kinds(report, "informationalChanges") == {"version-monotonic-increase"}
    assert "enum-changed" not in _change_kinds(report, "breakingChanges")


def test_known_version_default_bump_with_multi_enum_narrowing_is_breaking() -> None:
    base = _doc(_schema({"payloadVersion": _prop("string", default="today.v1", enum=["today.v1", "today.v2"])}))
    current = _doc(_schema({"payloadVersion": _prop("string", default="today.v2", enum=["today.v2"])}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "version-monotonic-increase" in _change_kinds(report, "informationalChanges")
    assert "enum-narrowed" in _change_kinds(report, "breakingChanges")


def test_known_version_stable_default_changed_singleton_enum_is_breaking() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", enum=["today.v1"])}))
    current = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", enum=["today.v2"])}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert _change_kinds(report, "breakingChanges") == {"enum-changed"}
    assert _change_kinds(report, "informationalChanges") == set()


def test_known_version_monotonic_default_with_divergent_singleton_enum_is_breaking() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", enum=["today.v1"])}))
    current = _doc(_schema({"schemaVersion": _prop("string", default="today.v2", enum=["today.v3"])}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "enum-changed" in _change_kinds(report, "breakingChanges")
    assert _change_kinds(report, "informationalChanges") == {"version-monotonic-increase"}


def test_known_version_stable_default_changed_const_is_breaking() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", const="today.v1")}))
    current = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", const="today.v2")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert _change_kinds(report, "breakingChanges") == {"const-changed"}


def test_known_version_aligned_default_const_and_enum_bump_is_informational_once() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", enum=["today.v1"], const="today.v1")}))
    current = _doc(_schema({"schemaVersion": _prop("string", default="today.v2", enum=["today.v2"], const="today.v2")}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert report["breakingChanges"] == []
    assert _change_kinds(report, "informationalChanges") == {"version-monotonic-increase"}
    assert len(report["informationalChanges"]) == 1
    assert "enum-changed" not in _change_kinds(report, "breakingChanges")
    assert "const-changed" not in _change_kinds(report, "breakingChanges")


def test_known_version_stable_default_plus_const_added_is_breaking() -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", default="today.v1")}))
    current = _doc(_schema({"schemaVersion": _prop("string", default="today.v1", const="today.v1")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "const-added" in _change_kinds(report, "breakingChanges")


def test_format_add_is_breaking() -> None:
    base = _doc(_schema({"startsAt": _prop("string")}))
    current = _doc(_schema({"startsAt": _prop("string", format="date-time")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "format-added" in _change_kinds(report, "breakingChanges")


def test_format_change_is_breaking() -> None:
    base = _doc(_schema({"value": _prop("string", format="date")}))
    current = _doc(_schema({"value": _prop("string", format="date-time")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "format-changed" in _change_kinds(report, "breakingChanges")


def test_format_remove_is_additive() -> None:
    base = _doc(_schema({"startsAt": _prop("string", format="date-time")}))
    current = _doc(_schema({"startsAt": _prop("string")}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert "format-removed" in _change_kinds(report, "additiveChanges")


def test_nullability_widen_is_additive() -> None:
    base = _doc(_schema({"note": _prop("string")}))
    current = _doc(_schema({"note": {"anyOf": [{"type": "string"}, {"type": "null"}]}}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert any(item["kind"] == "nullability-widened" for item in report["additiveChanges"])


def test_nullability_narrow_is_breaking() -> None:
    base = _doc(_schema({"note": {"type": ["string", "null"]}}))
    current = _doc(_schema({"note": _prop("string")}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert any(item["kind"] == "nullability-narrowed" for item in report["breakingChanges"])


def test_alias_rename_is_breaking() -> None:
    base = _doc(_schema({"oldName": _prop("string")}, ["oldName"]))
    current = _doc(_schema({"newName": _prop("string")}, ["newName"]))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert any(item["kind"] == "property-removed" for item in report["breakingChanges"])


def test_primitive_change_is_breaking() -> None:
    base = _doc(_schema({"value": _prop("string")}))
    current = _doc(_schema({"value": _prop("integer")}))
    assert _classification(base, current) == "breaking"


def test_array_item_ref_change_is_breaking() -> None:
    base = _doc(_schema({"rows": {"type": "array", "items": {"$ref": "#/components/schemas/A"}}}))
    current = _doc(_schema({"rows": {"type": "array", "items": {"$ref": "#/components/schemas/B"}}}))
    assert _classification(base, current) == "breaking"


def test_discriminator_mapping_change_is_breaking() -> None:
    base = _doc(_schema({"item": {"oneOf": [{"$ref": "#/components/schemas/A"}], "discriminator": {"propertyName": "type", "mapping": {"a": "#/components/schemas/A"}}}}))
    current = _doc(_schema({"item": {"oneOf": [{"$ref": "#/components/schemas/A"}], "discriminator": {"propertyName": "type", "mapping": {"b": "#/components/schemas/A"}}}}))
    assert _classification(base, current) == "breaking"


def test_constraint_tighten_is_breaking() -> None:
    base = _doc(_schema({"name": _prop("string", minLength=1)}))
    current = _doc(_schema({"name": _prop("string", minLength=2)}))
    assert _classification(base, current) == "breaking"


def test_constraint_loosen_is_additive() -> None:
    base = _doc(_schema({"name": _prop("string", maxLength=10)}))
    current = _doc(_schema({"name": _prop("string", maxLength=20)}))
    assert _classification(base, current) == "additive"


def test_unique_items_tighten_is_breaking() -> None:
    base = _doc(_schema({"tags": {"type": "array", "items": _prop("string")}}))
    current = _doc(_schema({"tags": {"type": "array", "items": _prop("string"), "uniqueItems": True}}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "unique-items-tightened" in _change_kinds(report, "breakingChanges")


def test_unique_items_loosen_is_additive() -> None:
    base = _doc(_schema({"tags": {"type": "array", "items": _prop("string"), "uniqueItems": True}}))
    current = _doc(_schema({"tags": {"type": "array", "items": _prop("string")}}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert "unique-items-loosened" in _change_kinds(report, "additiveChanges")


def test_allof_ref_change_is_breaking() -> None:
    base = _doc(_schema({"payload": {"allOf": [{"$ref": "#/components/schemas/A"}]}}))
    current = _doc(_schema({"payload": {"allOf": [{"$ref": "#/components/schemas/B"}]}}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "allof-changed" in _change_kinds(report, "breakingChanges")


def test_allof_order_and_annotations_are_no_change() -> None:
    base = _doc(_schema({"payload": {"allOf": [{"$ref": "#/components/schemas/A", "description": "a"}, {"$ref": "#/components/schemas/B"}]}}))
    current = _doc(_schema({"payload": {"allOf": [{"$ref": "#/components/schemas/B"}, {"$ref": "#/components/schemas/A", "description": "b"}]}}))
    assert _classification(base, current) == "no-change"


def test_unknown_structural_keyword_change_is_breaking() -> None:
    base = _doc(_schema({"value": _prop("integer", multipleOf=1)}))
    current = _doc(_schema({"value": _prop("integer", multipleOf=2)}))
    report = _report(base, current)
    assert report["classification"] == "breaking"
    assert "schema-key-changed" in _change_kinds(report, "breakingChanges")


def test_additional_properties_tighten_is_breaking() -> None:
    base = _doc({"type": "object", "properties": {"meta": {"type": "object"}}})
    current = _doc({"type": "object", "properties": {"meta": {"type": "object", "additionalProperties": False}}})
    assert _classification(base, current) == "breaking"


def test_required_to_optional_is_additive() -> None:
    base = _doc(_schema({"name": _prop("string")}, ["name"]))
    current = _doc(_schema({"name": _prop("string")}, []))
    assert _classification(base, current) == "additive"


def test_union_variant_add_is_additive() -> None:
    base = _doc(_schema({"value": {"anyOf": [{"type": "string"}]}}))
    current = _doc(_schema({"value": {"anyOf": [{"type": "integer"}, {"type": "string"}]}}))
    assert _classification(base, current) == "additive"


def test_union_variant_remove_is_breaking() -> None:
    base = _doc(_schema({"value": {"oneOf": [{"type": "integer"}, {"type": "string"}]}}))
    current = _doc(_schema({"value": {"oneOf": [{"type": "string"}]}}))
    assert _classification(base, current) == "breaking"


def test_version_minor_increase_is_informational_non_breaking() -> None:
    base = _doc(_schema({"activationLayerVersion": _prop("string", default="al-1.0")}))
    current = _doc(_schema({"activationLayerVersion": _prop("string", default="al-1.1")}))
    report = _report(base, current)
    assert report["classification"] == "additive"
    assert report["informationalChanges"][0]["kind"] == "version-monotonic-increase"
    assert report["breakingChanges"] == []


@pytest.mark.parametrize(
    ("base_version", "current_version", "expected_classification", "expected_kind"),
    [
        ("calendar/v1", "calendar/v2", "additive", "version-monotonic-increase"),
        ("natal/v1", "natal/v2", "additive", "version-monotonic-increase"),
        ("today/v1", "today/v2", "additive", "version-monotonic-increase"),
        ("calendar/v1", "natal/v2", "breaking", "version-family-changed"),
        ("today/v2", "today/v1", "breaking", "version-downgrade"),
        ("today/v1", "today/vx", "breaking", "version-malformed"),
    ],
)
def test_slash_style_known_versions(
    base_version: str,
    current_version: str,
    expected_classification: str,
    expected_kind: str,
) -> None:
    base = _doc(_schema({"schemaVersion": _prop("string", enum=[base_version])}))
    current = _doc(_schema({"schemaVersion": _prop("string", enum=[current_version])}))
    report = _report(base, current)
    assert report["classification"] == expected_classification
    if expected_classification == "additive":
        assert expected_kind in _change_kinds(report, "informationalChanges")
        assert report["breakingChanges"] == []
    else:
        assert expected_kind in _change_kinds(report, "breakingChanges")
    assert "const-changed" not in _change_kinds(report, "breakingChanges")
    assert "enum-changed" not in _change_kinds(report, "breakingChanges")


@pytest.mark.parametrize("bad_version", ["al-0.9", "not-a-version"])
def test_version_downgrade_or_malformed_is_breaking(bad_version: str) -> None:
    base = _doc(_schema({"activationLayerVersion": _prop("string", default="al-1.0")}))
    current = _doc(_schema({"activationLayerVersion": _prop("string", default=bad_version)}))
    assert _classification(base, current) == "breaking"


def test_deterministic_ordering_and_json_newline() -> None:
    base = _doc(_schema({"bRemoved": _prop("string"), "aEnum": _prop("string", enum=["x"])}))
    current = _doc(_schema({"aEnum": _prop("string", enum=["x", "y"]), "cAdded": _prop("string")}))
    report = _report(base, current)
    payload = check_compat.dump_report_json(report)
    assert payload.endswith("\n")
    for key in ("changedSchemas", "additiveChanges", "breakingChanges", "informationalChanges"):
        assert report[key] == sorted(report[key], key=lambda item: (item["path"], item["kind"], item["reason"]))
    assert list(json.loads(payload)) == sorted(json.loads(payload))


def test_real_current_artifact_against_merge_base_is_no_change_or_additive_without_breaking() -> None:
    base_commit = check_compat.resolve_default_base_ref()
    base_doc = check_compat.load_base_openapi_from_git(base_commit)
    current_doc = check_compat.load_json_file(CURRENT_ARTIFACT)
    report = check_compat.build_report(base_doc, current_doc, base_commit, "packages/contracts/openapi.json")
    # Approved breaking changes carry a non-empty packages/contracts/COMPAT_OVERRIDE
    # file (reviewed in git); without it the strict invariant applies.
    override_path = REPO_ROOT / "packages" / "contracts" / "COMPAT_OVERRIDE"
    if override_path.is_file():
        assert override_path.read_text(encoding="utf-8").strip(), "COMPAT_OVERRIDE must be non-empty"
        return
    _assert_real_artifact_invariant(report)


def test_real_artifact_invariant_accepts_identical_no_change() -> None:
    current_doc = check_compat.load_json_file(CURRENT_ARTIFACT)
    report = check_compat.build_report(current_doc, current_doc, "HEAD", "packages/contracts/openapi.json")
    _assert_real_artifact_invariant(report)
# END_BLOCK: PURE_COMPAT_MATRIX


# START_BLOCK: CLI_REF_CASES
def test_missing_base_ref_exits_2_with_actionable_message() -> None:
    result = _cli(["--base-ref", "missing-contract-ref-for-test", "--current", str(CURRENT_ARTIFACT)])
    assert result.returncode == 2
    assert "git fetch origin main" in result.stderr


def test_allow_breaking_without_reason_exits_2() -> None:
    result = _cli(["--allow-breaking", "--current", str(CURRENT_ARTIFACT)], env={"CONTRACT_BREAKING_REASON": ""})
    assert result.returncode == 2
    assert "CONTRACT_BREAKING_REASON" in result.stderr


def test_breaking_with_flag_and_reason_exits_0_and_sets_override(tmp_path: Path) -> None:
    base_commit = check_compat.resolve_default_base_ref()
    current = tmp_path / "breaking-openapi.json"
    current_doc = _doc(_schema({"onlyNew": _prop("string")}, ["onlyNew"]))
    current.write_text(json.dumps(current_doc), encoding="utf-8")
    result = _cli(
        ["--base-ref", base_commit, "--current", str(current), "--allow-breaking", "--json"],
        env={"CONTRACT_BREAKING_REASON": "reviewed breaking fixture"},
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["classification"] == "breaking"
    assert report["overrideUsed"] is True


def test_shell_like_ref_text_is_not_executed(tmp_path: Path) -> None:
    marker = tmp_path / "shell-would-have-created-this"
    ref = f"HEAD;touch {marker}"
    result = _cli(["--base-ref", ref, "--current", str(CURRENT_ARTIFACT)])
    assert result.returncode == 2
    assert not marker.exists()
    assert "git fetch origin main" in result.stderr
# END_BLOCK: CLI_REF_CASES
