#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: SCRIPT_CONTRACTS_CHECK_COMPAT — deterministic OpenAPI compatibility checker.
# ROLE: Compares current generated OpenAPI against a Git base artifact without external deps.
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS-CHECK-COMPAT
# purpose: Classify OpenAPI contract drift between the current generated artifact
#   and a base artifact stored in Git as no-change, additive, or breaking.
# owns:
#   - scripts/contracts/check_compat.py
# inputs: CLI flags, current OpenAPI JSON file, Git base ref.
# outputs: deterministic human and/or JSON compatibility report.
# dependencies: Python stdlib, git CLI.
# side_effects:
#   - Optional --json-output writes a report file.
# emitted_logs: none.
# invariants:
#   - Base artifact is read only through git show <commit>:packages/contracts/openapi.json.
#   - subprocess calls never use shell=True.
#   - Documentation-only OpenAPI annotations do not affect classification.
#   - Report arrays are sorted by (path, kind, reason) and contain no schema payloads.
# failure_policy:
#   - exit 0 for no-change/additive, exit 1 for breaking without approved override,
#     exit 2 for ref/input/JSON/config errors.
# END_MODULE_CONTRACT: M-CONTRACTS-CHECK-COMPAT

# START_MODULE_MAP: M-CONTRACTS-CHECK-COMPAT
# public_entrypoints:
#   - main
#   - compare_openapi_documents
#   - build_report
# semantic_blocks:
#   - CONSTANTS: compatibility settings and ignored annotations.
#   - JSON_IO: deterministic JSON parsing and report serialization.
#   - NORMALIZATION: schema annotation stripping and union/nullability signatures.
#   - VERSION_DISCIPLINE: known wire version parsing and comparison.
#   - COMPARISON: OpenAPI paths/components comparison.
#   - GIT_BASE: safe Git ref resolution and base artifact loading.
#   - CLI: argparse entrypoint and exit-code policy.
# owned_tests:
#   - scripts/contracts/test_check_compat.py
# END_MODULE_MAP: M-CONTRACTS-CHECK-COMPAT

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


# START_BLOCK: CONSTANTS
REPORT_VERSION = "solarsage.contract-compat.v1"
DEFAULT_CURRENT_ARTIFACT = "packages/contracts/openapi.json"
BASE_ARTIFACT = "packages/contracts/openapi.json"
IGNORED_KEYS = {"title", "description", "example", "examples"}
HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}
KNOWN_VERSION_PROPERTIES = {
    "schemaVersion",
    "activationLayerVersion",
    "calculationVersion",
    "scoringVersion",
    "payloadVersion",
}
LOWER_BOUND_CONSTRAINTS = {"minimum", "exclusiveMinimum", "minLength", "minItems"}
UPPER_BOUND_CONSTRAINTS = {"maximum", "exclusiveMaximum", "maxLength", "maxItems"}
CONSTRAINT_KEYS = LOWER_BOUND_CONSTRAINTS | UPPER_BOUND_CONSTRAINTS | {"pattern"}
HANDLED_SCHEMA_KEYS = {
    "$ref",
    "additionalProperties",
    "allOf",
    "anyOf",
    "const",
    "default",
    "discriminator",
    "enum",
    "format",
    "items",
    "nullable",
    "oneOf",
    "properties",
    "required",
    "type",
    "uniqueItems",
} | CONSTRAINT_KEYS
NULL_SIGNATURE = "__type:null__"
ERROR_FETCH_HINT = "Run git fetch origin main and retry."
# END_BLOCK: CONSTANTS


ChangeItem = dict[str, str]
Report = dict[str, Any]


# START_BLOCK: JSON_IO
def load_json_file(path: Path) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.load_json_file
    # purpose: Read and parse a JSON object from disk.
    # inputs: path — JSON file path.
    # returns: Parsed JSON object.
    # side_effects: file read.
    # emitted_logs: none.
    # error_behavior: Raises ValueError with path-only context for invalid input.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.load_json_file
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"current input error: {path}: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"current JSON error: {path}: line={exc.lineno} column={exc.colno}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"current JSON error: {path}: root must be object")
    return data


def load_json_text(payload: str, label: str) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.load_json_text
    # purpose: Parse a JSON object from a Git-provided text payload.
    # inputs: payload — JSON text; label — safe input label for errors.
    # returns: Parsed JSON object.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Raises ValueError with label-only context for invalid input.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.load_json_text
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"base JSON error: {label}: line={exc.lineno} column={exc.colno}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"base JSON error: {label}: root must be object")
    return data


def dump_report_json(report: Report) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.dump_report_json
    # purpose: Serialize compatibility report deterministically.
    # inputs: report — report dictionary.
    # returns: sorted-key, indented JSON string with trailing newline.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: json serialization errors propagate.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.dump_report_json
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def human_summary(report: Report) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.human_summary
    # purpose: Build concise human-readable compatibility summary.
    # inputs: report — compatibility report.
    # returns: Multi-line summary string.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.human_summary
    return "\n".join(
        [
            f"classification: {report['classification']}",
            f"baseRef: {report['baseRef']}",
            f"currentArtifact: {report['currentArtifact']}",
            f"changedSchemas: {len(report['changedSchemas'])}",
            f"additiveChanges: {len(report['additiveChanges'])}",
            f"breakingChanges: {len(report['breakingChanges'])}",
            f"informationalChanges: {len(report['informationalChanges'])}",
            f"overrideUsed: {str(report['overrideUsed']).lower()}",
        ]
    )
# END_BLOCK: JSON_IO


# START_BLOCK: NORMALIZATION
def is_ignored_key(key: str) -> bool:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.is_ignored_key
    # purpose: Decide whether an OpenAPI key is documentation-only for compatibility.
    # inputs: key — object key.
    # returns: True for title/description/example/examples/x-* annotations.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.is_ignored_key
    return key in IGNORED_KEYS or key.startswith("x-")


def strip_ignored_annotations(value: Any) -> Any:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.strip_ignored_annotations
    # purpose: Remove documentation-only keys recursively before structural comparison.
    # inputs: value — JSON-compatible value.
    # returns: Value with ignored annotations removed.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.strip_ignored_annotations
    if isinstance(value, dict):
        return {
            key: strip_ignored_annotations(child)
            for key, child in value.items()
            if not is_ignored_key(key)
        }
    if isinstance(value, list):
        return [strip_ignored_annotations(child) for child in value]
    return value


def canonical_json(value: Any) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.canonical_json
    # purpose: Produce a deterministic signature string for normalized schema fragments.
    # inputs: value — JSON-compatible value.
    # returns: Compact sorted-key JSON string.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: json serialization errors propagate.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.canonical_json
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_for_signature(value: Any) -> Any:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalize_for_signature
    # purpose: Canonicalize schemas so order-only differences do not become drift.
    # inputs: value — JSON-compatible schema fragment.
    # returns: Recursively normalized value.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalize_for_signature
    value = strip_ignored_annotations(value)
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            normalized[key] = normalize_for_signature(child)
        for union_key in ("allOf", "anyOf", "oneOf"):
            if isinstance(normalized.get(union_key), list):
                variants = normalized[union_key]
                normalized[union_key] = sorted(variants, key=canonical_json)
        if isinstance(normalized.get("enum"), list):
            normalized["enum"] = sorted(normalized["enum"], key=canonical_json)
        if isinstance(normalized.get("required"), list):
            normalized["required"] = sorted(normalized["required"])
        schema_type = normalized.get("type")
        if isinstance(schema_type, list):
            normalized["type"] = sorted(schema_type, key=str)
        return normalized
    if isinstance(value, list):
        return [normalize_for_signature(child) for child in value]
    return value


def is_null_schema(schema: Any) -> bool:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.is_null_schema
    # purpose: Detect JSON schema variants that represent null.
    # inputs: schema — schema fragment.
    # returns: True when fragment is a null type schema.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.is_null_schema
    return isinstance(schema, dict) and schema.get("type") == "null"


def is_union_like(schema: dict[str, Any]) -> bool:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.is_union_like
    # purpose: Identify schemas where variant-set comparison controls shape compatibility.
    # inputs: schema — schema object.
    # returns: True for anyOf/oneOf, nullable:true, or multi-type schemas.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.is_union_like
    schema_type = schema.get("type")
    return (
        isinstance(schema.get("anyOf"), list)
        or isinstance(schema.get("oneOf"), list)
        or schema.get("nullable") is True
        or isinstance(schema_type, list)
    )


def variant_signatures(schema: dict[str, Any]) -> set[str]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.variant_signatures
    # purpose: Normalize nullable and union representations into a deterministic variant set.
    # inputs: schema — schema object.
    # returns: Set of canonical variant signatures, including NULL_SIGNATURE for null.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.variant_signatures
    signatures: set[str] = set()
    union_variants: list[Any] = []
    for union_key in ("anyOf", "oneOf"):
        variants = schema.get(union_key)
        if isinstance(variants, list):
            union_variants.extend(variants)

    if union_variants:
        for variant in union_variants:
            if is_null_schema(variant):
                signatures.add(NULL_SIGNATURE)
            else:
                signatures.add(canonical_json(normalize_for_signature(variant)))
        if schema.get("nullable") is True:
            signatures.add(NULL_SIGNATURE)
        return signatures

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        for type_name in schema_type:
            if type_name == "null":
                signatures.add(NULL_SIGNATURE)
                continue
            variant = dict(schema)
            variant["type"] = type_name
            variant.pop("nullable", None)
            signatures.add(canonical_json(normalize_for_signature(variant)))
        return signatures

    variant = dict(schema)
    if variant.pop("nullable", False) is True:
        signatures.add(NULL_SIGNATURE)
    signatures.add(canonical_json(normalize_for_signature(variant)))
    return signatures


def normalized_type_set(schema: dict[str, Any]) -> set[str]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_type_set
    # purpose: Return a schema's non-null type set for primitive/container change detection.
    # inputs: schema — schema object.
    # returns: Set of type names, excluding null.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_type_set
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return {str(item) for item in schema_type if item != "null"}
    if isinstance(schema_type, str) and schema_type != "null":
        return {schema_type}
    if "$ref" in schema:
        return {"$ref"}
    return set()
# END_BLOCK: NORMALIZATION


# START_BLOCK: VERSION_DISCIPLINE
def extract_version_value(schema: dict[str, Any]) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.extract_version_value
    # purpose: Extract a known version value from default/const/single-enum schema metadata.
    # inputs: schema — property schema.
    # returns: Version string or None when no single value is declared.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.extract_version_value
    for key in ("default", "const"):
        value = schema.get(key)
        if isinstance(value, str):
            return value
    enum_value = schema.get("enum")
    if isinstance(enum_value, list) and len(enum_value) == 1 and isinstance(enum_value[0], str):
        return enum_value[0]
    return None


def parse_known_version(value: str) -> tuple[str, tuple[int, ...]] | None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.parse_known_version
    # purpose: Parse approved public wire version formats into comparable tuples.
    # inputs: value — version string.
    # returns: (family, numeric tuple) or None for malformed values.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.parse_known_version
    patterns = (
        ("activation-layer", r"^activation-layer\.v(\d+)$"),
        ("al", r"^al-(\d+)\.(\d+)$"),
        ("ss-calc", r"^ss-calc-(\d+)\.(\d+)\.(\d+)$"),
        ("ss-scoring", r"^ss-scoring-(\d+)\.(\d+)$"),
        ("today", r"^today\.v(\d+)$"),
    )
    for family, pattern in patterns:
        match = re.match(pattern, value)
        if match:
            return family, tuple(int(part) for part in match.groups())
    slash_match = re.match(r"^([a-z][a-z0-9-]*)/v(\d+)$", value)
    if slash_match:
        return f"slash:{slash_match.group(1)}", (int(slash_match.group(2)),)
    return None


def compare_version_values(
    base_value: str,
    current_value: str,
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_version_values
    # purpose: Classify known wire version changes as informational or breaking.
    # inputs: base/current strings, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_version_values
    if base_value == current_value:
        return
    base_parsed = parse_known_version(base_value)
    current_parsed = parse_known_version(current_value)
    if base_parsed is None or current_parsed is None:
        add_change(changes, "breaking", "version-malformed", path, "known version malformed")
        return
    base_family, base_parts = base_parsed
    current_family, current_parts = current_parsed
    if base_family != current_family:
        add_change(changes, "breaking", "version-family-changed", path, "known version family changed")
        return
    if current_parts > base_parts:
        add_change(
            changes,
            "informational",
            "version-monotonic-increase",
            path,
            f"known version increased {base_value} -> {current_value}",
        )
        return
    add_change(changes, "breaking", "version-downgrade", path, "known version decreased")
# END_BLOCK: VERSION_DISCIPLINE


# START_BLOCK: COMPARISON
def add_change(
    changes: dict[str, list[ChangeItem]],
    bucket: str,
    kind: str,
    path: str,
    reason: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.add_change
    # purpose: Append a sanitized change item to one report bucket.
    # inputs: changes accumulator, bucket name, kind/path/reason strings.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.add_change
    changes[bucket].append({"kind": kind, "path": path, "reason": reason})


def sorted_unique_changes(items: Iterable[ChangeItem]) -> list[ChangeItem]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.sorted_unique_changes
    # purpose: Deduplicate and sort report change arrays deterministically.
    # inputs: items — change item iterable.
    # returns: Sorted list by (path, kind, reason).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.sorted_unique_changes
    seen: set[tuple[str, str, str]] = set()
    unique: list[ChangeItem] = []
    for item in items:
        key = (item["path"], item["kind"], item["reason"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return sorted(unique, key=lambda item: (item["path"], item["kind"], item["reason"]))


def compare_enum(
    property_name: str,
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_enum
    # purpose: Classify enum widening/narrowing.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_enum
    if "enum" not in base_schema and "enum" not in current_schema:
        return
    base_enum = base_schema.get("enum")
    current_enum = current_schema.get("enum")
    if (
        property_name in KNOWN_VERSION_PROPERTIES
        and isinstance(base_enum, list)
        and isinstance(current_enum, list)
        and len(base_enum) == 1
        and len(current_enum) == 1
        and isinstance(base_enum[0], str)
        and isinstance(current_enum[0], str)
        and extract_version_value(base_schema) == base_enum[0]
        and extract_version_value(current_schema) == current_enum[0]
    ):
        return
    if not isinstance(base_enum, list) or not isinstance(current_enum, list):
        if base_enum != current_enum:
            add_change(changes, "breaking", "enum-shape-changed", path, "enum declaration changed")
        return
    base_set = {canonical_json(item) for item in base_enum}
    current_set = {canonical_json(item) for item in current_enum}
    if base_set == current_set:
        return
    if base_set.issubset(current_set):
        add_change(changes, "additive", "enum-widened", path, "enum widened")
    elif current_set.issubset(base_set):
        add_change(changes, "breaking", "enum-narrowed", path, "enum narrowed")
    else:
        add_change(changes, "breaking", "enum-changed", path, "enum changed")


def compare_const(
    property_name: str,
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_const
    # purpose: Classify non-version const narrowing/widening and value changes.
    # inputs: property name, base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_const
    base_has = "const" in base_schema
    current_has = "const" in current_schema
    if property_name in KNOWN_VERSION_PROPERTIES:
        if not base_has and not current_has:
            return
        if (
            base_has
            and current_has
            and extract_version_value(base_schema) == base_schema.get("const")
            and extract_version_value(current_schema) == current_schema.get("const")
        ):
            return
    child_path = f"{path}.const"
    if not base_has and not current_has:
        return
    if not base_has and current_has:
        add_change(changes, "breaking", "const-added", child_path, "const added")
        return
    if base_has and not current_has:
        add_change(changes, "additive", "const-removed", child_path, "const removed")
        return
    if base_schema.get("const") != current_schema.get("const"):
        add_change(changes, "breaking", "const-changed", child_path, "const changed")


def compare_format(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_format
    # purpose: Classify JSON schema format additions/removals/value changes.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_format
    base_has = "format" in base_schema
    current_has = "format" in current_schema
    child_path = f"{path}.format"
    if not base_has and not current_has:
        return
    if not base_has and current_has:
        add_change(changes, "breaking", "format-added", child_path, "format added")
        return
    if base_has and not current_has:
        add_change(changes, "additive", "format-removed", child_path, "format removed")
        return
    if base_schema.get("format") != current_schema.get("format"):
        add_change(changes, "breaking", "format-changed", child_path, "format changed")


def normalized_unique_items(schema: dict[str, Any]) -> Any:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_unique_items
    # purpose: Return uniqueItems with JSON schema's absent-as-false default.
    # inputs: schema — schema object.
    # returns: uniqueItems value, using False when absent.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_unique_items
    return schema.get("uniqueItems", False)


def compare_unique_items(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_unique_items
    # purpose: Classify array uniqueItems tightening/loosening.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_unique_items
    base_value = normalized_unique_items(base_schema)
    current_value = normalized_unique_items(current_schema)
    child_path = f"{path}.uniqueItems"
    if base_value == current_value:
        return
    if base_value is False and current_value is True:
        add_change(changes, "breaking", "unique-items-tightened", child_path, "uniqueItems false -> true")
    elif base_value is True and current_value is False:
        add_change(changes, "additive", "unique-items-loosened", child_path, "uniqueItems true -> false")
    else:
        add_change(changes, "breaking", "unique-items-changed", child_path, "uniqueItems changed")


def normalized_all_of(schema: dict[str, Any]) -> Any:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_all_of
    # purpose: Normalize allOf order and annotations for exact equality checks.
    # inputs: schema — schema object.
    # returns: normalized allOf value or None when absent.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_all_of
    if "allOf" not in schema:
        return None
    normalized = normalize_for_signature({"allOf": schema["allOf"]})
    if isinstance(normalized, dict):
        return normalized.get("allOf")
    return normalized


def compare_all_of(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_all_of
    # purpose: Classify any semantic allOf drift as conservative breaking.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_all_of
    base_value = normalized_all_of(base_schema)
    current_value = normalized_all_of(current_schema)
    if base_value == current_value:
        return
    add_change(changes, "breaking", "allof-changed", f"{path}.allOf", "allOf changed")


def compare_constraints(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_constraints
    # purpose: Classify JSON schema constraint tightening/loosening.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_constraints
    for key in sorted(CONSTRAINT_KEYS):
        base_has = key in base_schema
        current_has = key in current_schema
        if not base_has and not current_has:
            continue
        child_path = f"{path}.{key}"
        if key == "pattern":
            if base_has and not current_has:
                add_change(changes, "additive", "constraint-loosened", child_path, "pattern removed")
            elif not base_has and current_has:
                add_change(changes, "breaking", "constraint-tightened", child_path, "pattern added")
            elif base_schema.get(key) != current_schema.get(key):
                add_change(changes, "breaking", "constraint-tightened", child_path, "pattern changed")
            continue

        if base_has and not current_has:
            add_change(changes, "additive", "constraint-loosened", child_path, f"{key} removed")
            continue
        if not base_has and current_has:
            add_change(changes, "breaking", "constraint-tightened", child_path, f"{key} added")
            continue

        base_value = base_schema.get(key)
        current_value = current_schema.get(key)
        if base_value == current_value:
            continue
        if not isinstance(base_value, (int, float)) or not isinstance(current_value, (int, float)):
            add_change(changes, "breaking", "constraint-tightened", child_path, f"{key} changed")
            continue
        if key in LOWER_BOUND_CONSTRAINTS:
            if current_value > base_value:
                add_change(changes, "breaking", "constraint-tightened", child_path, f"{key} increased")
            else:
                add_change(changes, "additive", "constraint-loosened", child_path, f"{key} decreased")
        elif current_value < base_value:
            add_change(changes, "breaking", "constraint-tightened", child_path, f"{key} decreased")
        else:
            add_change(changes, "additive", "constraint-loosened", child_path, f"{key} increased")


def normalized_additional_properties(schema: dict[str, Any]) -> bool | dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_additional_properties
    # purpose: Treat absent additionalProperties as true per JSON schema defaults.
    # inputs: schema — schema object.
    # returns: bool or schema-valued additionalProperties.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.normalized_additional_properties
    value = schema.get("additionalProperties", True)
    if isinstance(value, dict):
        return value
    return bool(value)


def compare_additional_properties(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_additional_properties
    # purpose: Classify additionalProperties tightening/loosening.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_additional_properties
    base_value = normalized_additional_properties(base_schema)
    current_value = normalized_additional_properties(current_schema)
    child_path = f"{path}.additionalProperties"
    if base_value == current_value:
        return
    if base_value is True and current_value is False:
        add_change(changes, "breaking", "additional-properties-tightened", child_path, "additionalProperties true -> false")
    elif base_value is False and current_value is True:
        add_change(changes, "additive", "additional-properties-loosened", child_path, "additionalProperties false -> true")
    elif base_value is True and isinstance(current_value, dict):
        add_change(changes, "breaking", "additional-properties-tightened", child_path, "additionalProperties true -> schema")
    elif isinstance(base_value, dict) and current_value is True:
        add_change(changes, "additive", "additional-properties-loosened", child_path, "additionalProperties schema -> true")
    elif isinstance(base_value, dict) and current_value is False:
        add_change(changes, "breaking", "additional-properties-tightened", child_path, "additionalProperties schema -> false")
    elif base_value is False and isinstance(current_value, dict):
        add_change(changes, "additive", "additional-properties-loosened", child_path, "additionalProperties false -> schema")
    elif isinstance(base_value, dict) and isinstance(current_value, dict):
        compare_schema(base_value, current_value, child_path, changes)


def compare_union_variants(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_union_variants
    # purpose: Classify nullability and anyOf/oneOf variant additions/removals.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_union_variants
    base_variants = variant_signatures(base_schema)
    current_variants = variant_signatures(current_schema)
    added = current_variants - base_variants
    removed = base_variants - current_variants
    for signature in sorted(added):
        if signature == NULL_SIGNATURE:
            add_change(changes, "additive", "nullability-widened", path, "nullability widened")
        else:
            add_change(changes, "additive", "union-variant-added", path, "anyOf/oneOf variant added")
    for signature in sorted(removed):
        if signature == NULL_SIGNATURE:
            add_change(changes, "breaking", "nullability-narrowed", path, "nullability narrowed")
        else:
            add_change(changes, "breaking", "union-variant-removed", path, "anyOf/oneOf variant removed")


def compare_default(
    property_name: str,
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_default
    # purpose: Classify default changes, delegating known wire versions to version discipline.
    # inputs: property name, base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_default
    base_version = extract_version_value(base_schema) if property_name in KNOWN_VERSION_PROPERTIES else None
    current_version = extract_version_value(current_schema) if property_name in KNOWN_VERSION_PROPERTIES else None
    if base_version is not None or current_version is not None:
        if base_version is None or current_version is None:
            add_change(changes, "breaking", "version-value-missing", path, "known version value missing")
        else:
            compare_version_values(base_version, current_version, path, changes)
        return
    sentinel = object()
    base_default = base_schema.get("default", sentinel)
    current_default = current_schema.get("default", sentinel)
    if base_default != current_default:
        add_change(changes, "breaking", "default-changed", path, "non-version default changed")


def compare_object_properties(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_object_properties
    # purpose: Compare object properties and requiredness changes.
    # inputs: base/current object schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_object_properties
    base_properties = base_schema.get("properties")
    current_properties = current_schema.get("properties")
    if not isinstance(base_properties, dict) and not isinstance(current_properties, dict):
        return
    if not isinstance(base_properties, dict):
        base_properties = {}
    if not isinstance(current_properties, dict):
        current_properties = {}
    base_required = set(base_schema.get("required") or [])
    current_required = set(current_schema.get("required") or [])

    for name in sorted(set(base_properties) - set(current_properties)):
        add_change(changes, "breaking", "property-removed", f"{path}.properties.{name}", "property removed")
    for name in sorted(set(current_properties) - set(base_properties)):
        child_path = f"{path}.properties.{name}"
        if name in current_required:
            add_change(changes, "breaking", "required-property-added", child_path, "required property added")
        else:
            add_change(changes, "additive", "optional-property-added", child_path, "optional property added")

    for name in sorted(set(base_properties) & set(current_properties)):
        child_path = f"{path}.properties.{name}"
        if name not in base_required and name in current_required:
            add_change(changes, "breaking", "optional-to-required", child_path, "optional property became required")
        elif name in base_required and name not in current_required:
            add_change(changes, "additive", "required-to-optional", child_path, "required property became optional")
        base_child = base_properties[name]
        current_child = current_properties[name]
        if isinstance(base_child, dict) and isinstance(current_child, dict):
            compare_schema(base_child, current_child, child_path, changes)
        elif base_child != current_child:
            add_change(changes, "breaking", "property-schema-changed", child_path, "property schema changed")


def compare_residual_schema_keys(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_residual_schema_keys
    # purpose: Fail closed on structural JSON schema keywords not handled explicitly.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_residual_schema_keys
    sentinel = object()
    candidate_keys = (set(base_schema) | set(current_schema)) - HANDLED_SCHEMA_KEYS
    for key in sorted(candidate_keys):
        if is_ignored_key(key):
            continue
        if base_schema.get(key, sentinel) != current_schema.get(key, sentinel):
            add_change(changes, "breaking", "schema-key-changed", f"{path}.{key}", "unknown structural schema key changed")


def compare_schema(
    base_schema: dict[str, Any],
    current_schema: dict[str, Any],
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_schema
    # purpose: Compare two JSON schema objects under compatibility rules.
    # inputs: base/current schemas, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_schema
    base_schema = strip_ignored_annotations(base_schema)
    current_schema = strip_ignored_annotations(current_schema)
    if not isinstance(base_schema, dict) or not isinstance(current_schema, dict):
        if base_schema != current_schema:
            add_change(changes, "breaking", "schema-fragment-changed", path, "schema fragment changed")
        return

    base_ref = base_schema.get("$ref")
    current_ref = current_schema.get("$ref")
    if base_ref != current_ref:
        add_change(changes, "breaking", "ref-changed", f"{path}.$ref", "$ref changed")

    if base_schema.get("discriminator") != current_schema.get("discriminator"):
        add_change(changes, "breaking", "discriminator-changed", f"{path}.discriminator", "discriminator changed")

    property_name = path.rsplit(".", 1)[-1]
    compare_default(property_name, base_schema, current_schema, path, changes)
    compare_const(property_name, base_schema, current_schema, path, changes)
    compare_enum(property_name, base_schema, current_schema, path, changes)
    compare_format(base_schema, current_schema, path, changes)
    compare_constraints(base_schema, current_schema, path, changes)
    compare_unique_items(base_schema, current_schema, path, changes)
    compare_all_of(base_schema, current_schema, path, changes)
    compare_additional_properties(base_schema, current_schema, path, changes)
    compare_object_properties(base_schema, current_schema, path, changes)
    compare_residual_schema_keys(base_schema, current_schema, path, changes)

    if is_union_like(base_schema) or is_union_like(current_schema):
        compare_union_variants(base_schema, current_schema, path, changes)
        return

    base_types = normalized_type_set(base_schema)
    current_types = normalized_type_set(current_schema)
    if base_types != current_types:
        add_change(changes, "breaking", "type-changed", f"{path}.type", "primitive/container type changed")

    if base_schema.get("type") == "array" or current_schema.get("type") == "array":
        base_items = base_schema.get("items")
        current_items = current_schema.get("items")
        if isinstance(base_items, dict) and isinstance(current_items, dict):
            compare_schema(base_items, current_items, f"{path}.items", changes)
        elif base_items != current_items:
            add_change(changes, "breaking", "array-items-changed", f"{path}.items", "array items changed")


def compare_paths(
    base_paths: Any,
    current_paths: Any,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_paths
    # purpose: Compare OpenAPI paths and method additions/removals.
    # inputs: base/current paths objects, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_paths
    if not isinstance(base_paths, dict) or not isinstance(current_paths, dict):
        if base_paths != current_paths:
            add_change(changes, "breaking", "paths-shape-changed", "paths", "paths object changed")
        return
    for path_name in sorted(set(base_paths) - set(current_paths)):
        add_change(changes, "breaking", "endpoint-removed", f"paths.{path_name}", "endpoint removed")
    for path_name in sorted(set(current_paths) - set(base_paths)):
        add_change(changes, "additive", "endpoint-added", f"paths.{path_name}", "endpoint added")
    for path_name in sorted(set(base_paths) & set(current_paths)):
        base_path = base_paths[path_name]
        current_path = current_paths[path_name]
        if not isinstance(base_path, dict) or not isinstance(current_path, dict):
            if strip_ignored_annotations(base_path) != strip_ignored_annotations(current_path):
                add_change(changes, "breaking", "endpoint-shape-changed", f"paths.{path_name}", "endpoint shape changed")
            continue
        base_methods = {key for key in base_path if key.lower() in HTTP_METHODS}
        current_methods = {key for key in current_path if key.lower() in HTTP_METHODS}
        for method in sorted(base_methods - current_methods):
            add_change(changes, "breaking", "method-removed", f"paths.{path_name}.{method}", "method removed")
        for method in sorted(current_methods - base_methods):
            add_change(changes, "additive", "method-added", f"paths.{path_name}.{method}", "method added")
        for method in sorted(base_methods & current_methods):
            base_operation = normalize_for_signature(base_path[method])
            current_operation = normalize_for_signature(current_path[method])
            if base_operation != current_operation:
                compare_generic_json(
                    base_operation,
                    current_operation,
                    f"paths.{path_name}.{method}",
                    changes,
                )


def compare_generic_json(
    base_value: Any,
    current_value: Any,
    path: str,
    changes: dict[str, list[ChangeItem]],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_generic_json
    # purpose: Conservatively compare non-schema OpenAPI operation fragments.
    # inputs: base/current JSON values, report path, change accumulator.
    # returns: None.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_generic_json
    if isinstance(base_value, dict) and isinstance(current_value, dict):
        for key in sorted(set(base_value) - set(current_value)):
            add_change(changes, "breaking", "operation-field-removed", f"{path}.{key}", "operation field removed")
        for key in sorted(set(current_value) - set(base_value)):
            add_change(changes, "additive", "operation-field-added", f"{path}.{key}", "operation field added")
        for key in sorted(set(base_value) & set(current_value)):
            compare_generic_json(base_value[key], current_value[key], f"{path}.{key}", changes)
        return
    if isinstance(base_value, list) and isinstance(current_value, list):
        if canonical_json(base_value) != canonical_json(current_value):
            add_change(changes, "breaking", "operation-list-changed", path, "operation list changed")
        return
    if base_value != current_value:
        add_change(changes, "breaking", "operation-value-changed", path, "operation value changed")


def compare_components_schemas(
    base_schemas: Any,
    current_schemas: Any,
    changes: dict[str, list[ChangeItem]],
) -> list[ChangeItem]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_components_schemas
    # purpose: Compare components.schemas and return changed schema summary items.
    # inputs: base/current schema maps, change accumulator.
    # returns: changedSchemas report items.
    # side_effects: Mutates changes accumulator.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_components_schemas
    changed_schemas: list[ChangeItem] = []
    if not isinstance(base_schemas, dict) or not isinstance(current_schemas, dict):
        if base_schemas != current_schemas:
            add_change(changes, "breaking", "schemas-shape-changed", "components.schemas", "schemas object changed")
            changed_schemas.append(
                {"kind": "schemas-changed", "path": "components.schemas", "reason": "schemas object changed"}
            )
        return changed_schemas

    for name in sorted(set(base_schemas) - set(current_schemas)):
        schema_path = f"components.schemas.{name}"
        add_change(changes, "breaking", "schema-removed", schema_path, "schema component removed")
        changed_schemas.append({"kind": "schema-removed", "path": schema_path, "reason": "schema component removed"})
    for name in sorted(set(current_schemas) - set(base_schemas)):
        schema_path = f"components.schemas.{name}"
        add_change(changes, "additive", "schema-added", schema_path, "schema component added")
        changed_schemas.append({"kind": "schema-added", "path": schema_path, "reason": "schema component added"})
    for name in sorted(set(base_schemas) & set(current_schemas)):
        before_counts = tuple(len(changes[bucket]) for bucket in ("additive", "breaking", "informational"))
        compare_schema(base_schemas[name], current_schemas[name], f"components.schemas.{name}", changes)
        after_counts = tuple(len(changes[bucket]) for bucket in ("additive", "breaking", "informational"))
        if after_counts != before_counts:
            changed_schemas.append(
                {"kind": "schema-changed", "path": f"components.schemas.{name}", "reason": "schema changed"}
            )
    return changed_schemas


def compare_openapi_documents(base_doc: dict[str, Any], current_doc: dict[str, Any]) -> dict[str, list[ChangeItem]]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_openapi_documents
    # purpose: Compare OpenAPI paths and components.schemas under compatibility rules.
    # inputs: base/current OpenAPI objects.
    # returns: Dict containing changedSchemas/additive/breaking/informational arrays.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.compare_openapi_documents
    changes: dict[str, list[ChangeItem]] = {
        "changedSchemas": [],
        "additive": [],
        "breaking": [],
        "informational": [],
    }
    compare_paths(base_doc.get("paths", {}), current_doc.get("paths", {}), changes)
    base_schemas = (base_doc.get("components") or {}).get("schemas", {}) if isinstance(base_doc.get("components"), dict) else {}
    current_schemas = (
        (current_doc.get("components") or {}).get("schemas", {})
        if isinstance(current_doc.get("components"), dict)
        else {}
    )
    changes["changedSchemas"] = compare_components_schemas(base_schemas, current_schemas, changes)
    return changes


def build_report(
    base_doc: dict[str, Any],
    current_doc: dict[str, Any],
    base_ref: str,
    current_artifact: str,
    override_used: bool = False,
) -> Report:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.build_report
    # purpose: Build the deterministic compatibility report object.
    # inputs: base/current docs, base ref, current artifact label, override flag.
    # returns: Report dictionary matching solarsage.contract-compat.v1.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.build_report
    changes = compare_openapi_documents(base_doc, current_doc)
    additive_changes = sorted_unique_changes(changes["additive"])
    breaking_changes = sorted_unique_changes(changes["breaking"])
    informational_changes = sorted_unique_changes(changes["informational"])
    changed_schemas = sorted_unique_changes(changes["changedSchemas"])
    if breaking_changes:
        classification = "breaking"
    elif additive_changes or informational_changes:
        classification = "additive"
    else:
        classification = "no-change"
    return {
        "reportVersion": REPORT_VERSION,
        "baseRef": base_ref,
        "currentArtifact": current_artifact,
        "classification": classification,
        "changedSchemas": changed_schemas,
        "additiveChanges": additive_changes,
        "breakingChanges": breaking_changes,
        "informationalChanges": informational_changes,
        "overrideUsed": override_used,
    }
# END_BLOCK: COMPARISON


# START_BLOCK: GIT_BASE
def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.run_git
    # purpose: Execute Git with list arguments and no shell.
    # inputs: args — git arguments excluding the git executable.
    # returns: CompletedProcess with captured text streams.
    # side_effects: subprocess execution.
    # emitted_logs: none.
    # error_behavior: non-zero return is preserved, not raised.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.run_git
    return subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def verify_commit_ref(ref: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.verify_commit_ref
    # purpose: Resolve a user/environment Git ref to an exact commit SHA.
    # inputs: ref — Git ref text.
    # returns: Verified commit SHA.
    # side_effects: git subprocess execution.
    # emitted_logs: none.
    # error_behavior: Raises RuntimeError with actionable fetch hint.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.verify_commit_ref
    if not ref.strip():
        raise RuntimeError(f"empty base ref. {ERROR_FETCH_HINT}")
    result = run_git(["rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"])
    if result.returncode != 0:
        raise RuntimeError(f"could not resolve base ref {ref!r}. {ERROR_FETCH_HINT}")
    return result.stdout.strip()


def resolve_default_base_ref() -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.resolve_default_base_ref
    # purpose: Resolve default base to git merge-base HEAD origin/main.
    # inputs: none.
    # returns: merge-base commit SHA.
    # side_effects: git subprocess execution.
    # emitted_logs: none.
    # error_behavior: Raises RuntimeError with actionable fetch hint when origin/main is missing.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.resolve_default_base_ref
    result = run_git(["merge-base", "HEAD", "origin/main"])
    if result.returncode != 0:
        raise RuntimeError(f"could not resolve merge-base HEAD origin/main. {ERROR_FETCH_HINT}")
    return verify_commit_ref(result.stdout.strip())


def resolve_base_commit(explicit_ref: str | None) -> str:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.resolve_base_commit
    # purpose: Apply base priority: CLI ref, CONTRACT_BASE_REF, merge-base.
    # inputs: explicit_ref — optional --base-ref value.
    # returns: Verified base commit SHA.
    # side_effects: git subprocess execution.
    # emitted_logs: none.
    # error_behavior: Raises RuntimeError with actionable fetch hint on failure.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.resolve_base_commit
    if explicit_ref is not None:
        return verify_commit_ref(explicit_ref)
    env_ref = os.environ.get("CONTRACT_BASE_REF")
    if env_ref:
        return verify_commit_ref(env_ref)
    return resolve_default_base_ref()


def load_base_openapi_from_git(commit: str) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.load_base_openapi_from_git
    # purpose: Read base OpenAPI only through git show <commit>:packages/contracts/openapi.json.
    # inputs: commit — verified commit SHA.
    # returns: Parsed base OpenAPI JSON object.
    # side_effects: git subprocess execution.
    # emitted_logs: none.
    # error_behavior: Raises RuntimeError/ValueError with safe labels.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.load_base_openapi_from_git
    result = run_git(["show", f"{commit}:{BASE_ARTIFACT}"])
    if result.returncode != 0:
        raise RuntimeError(f"could not read {BASE_ARTIFACT} at {commit}. {ERROR_FETCH_HINT}")
    return load_json_text(result.stdout, f"{commit}:{BASE_ARTIFACT}")
# END_BLOCK: GIT_BASE


# START_BLOCK: CLI
def parse_args(argv: list[str]) -> argparse.Namespace:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.parse_args
    # purpose: Parse check_compat CLI flags.
    # inputs: argv — argument list excluding program name.
    # returns: argparse namespace.
    # side_effects: argparse may write usage on invalid args.
    # emitted_logs: none.
    # error_behavior: argparse SystemExit on invalid CLI syntax.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.parse_args
    parser = argparse.ArgumentParser(description="Check OpenAPI contract compatibility.")
    parser.add_argument("--base-ref", dest="base_ref", default=None)
    parser.add_argument("--current", default=DEFAULT_CURRENT_ARTIFACT)
    parser.add_argument("--json-output", dest="json_output", default=None)
    parser.add_argument("--json", action="store_true", dest="json_stdout")
    parser.add_argument("--allow-breaking", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # START_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.main
    # purpose: CLI entrypoint that emits report and enforces compatibility exit codes.
    # inputs: argv — optional CLI args excluding program name.
    # returns: Process exit code 0/1/2 per contract.
    # side_effects: Reads current file, invokes git, may write --json-output, writes stdout/stderr.
    # emitted_logs: none.
    # error_behavior: Handles expected input/ref/config errors with exit 2.
    # END_FUNCTION_CONTRACT: F-M-CONTRACTS-CHECK-COMPAT.main
    args = parse_args(sys.argv[1:] if argv is None else argv)
    breaking_reason = os.environ.get("CONTRACT_BREAKING_REASON", "")
    if args.allow_breaking and not breaking_reason.strip():
        print("--allow-breaking requires non-empty CONTRACT_BREAKING_REASON", file=sys.stderr)
        return 2

    try:
        base_commit = resolve_base_commit(args.base_ref)
        current_doc = load_json_file(Path(args.current))
        base_doc = load_base_openapi_from_git(base_commit)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    initial_report = build_report(
        base_doc,
        current_doc,
        base_ref=base_commit,
        current_artifact=args.current,
        override_used=False,
    )
    override_used = bool(
        args.allow_breaking and initial_report["classification"] == "breaking" and breaking_reason.strip()
    )
    report = (
        build_report(
            base_doc,
            current_doc,
            base_ref=base_commit,
            current_artifact=args.current,
            override_used=True,
        )
        if override_used
        else initial_report
    )

    payload = dump_report_json(report)
    if args.json_output:
        try:
            Path(args.json_output).write_text(payload, encoding="utf-8")
        except OSError as exc:
            print(f"json-output error: {args.json_output}: {exc.strerror}", file=sys.stderr)
            return 2

    if args.json_stdout:
        print(payload, end="")
    else:
        print(human_summary(report))

    if report["classification"] == "breaking" and not override_used:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK: CLI
