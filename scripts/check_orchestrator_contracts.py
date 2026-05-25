#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH_DIR = ROOT / "grace" / "orchestrator"
PROJECT_YML = ORCH_DIR / "project.yml"
PROFILES_YML = ORCH_DIR / "verification_profiles.yml"
PACKET_SCHEMA = ORCH_DIR / "packet.schema.json"
ROLES_DIR = ORCH_DIR / "roles"
PACKETS_DIR = ROOT / "grace" / "packets"

REQUIRED_PROJECT_KEYS = (
    "version",
    "project_id",
    "repo_root",
    "default_branch",
    "packet_dir",
    "roles_dir",
    "packet_schema",
    "verification_profiles",
    "runtime_state_dir",
    "artifact_dir",
    "worktree_dir",
    "workflow_runtime",
    "agent_executor",
    "agent_command_default",
    "agent_model_default",
    "packet_policy",
    "allowed_scope_guard",
    "verification_evidence",
    "reviewer_verdict",
)
REQUIRED_PROFILES = (
    "profile.docs",
    "profile.secrets",
    "profile.orchestrator",
    "profile.contracts",
    "profile.backend",
    "profile.backend_grace",
    "profile.frontend",
    "profile.vercel",
    "profile.full",
    "profile.strict",
)
REQUIRED_ROLES = (
    "architect",
    "planner",
    "coder",
    "verifier",
    "reviewer",
    "orchestrator",
)
ROLE_REQUIRED_HEADINGS = (
    "## Role",
    "## Inputs",
    "## Outputs",
    "## Hard Constraints",
    "## Final Marker",
)
REQUIRED_PACKET_SCHEMA_FIELDS = (
    "id",
    "status",
    "wave",
    "phase",
    "modules",
    "allowed_write_scope",
    "frozen_scope",
    "verification",
    "expected_evidence",
    "escalation_triggers",
)
PACKET_FRONTMATTER_KEYS = ("id", "status", "wave", "last_review")


@dataclass
class Result:
    errors: list[str]
    warnings: list[str]

    def fail(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def parse_flat_yml(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            raise ValueError(
                f"{path.relative_to(ROOT)}:{lineno}: nested YAML is not supported here"
            )
        if ":" not in raw:
            raise ValueError(f"{path.relative_to(ROOT)}:{lineno}: expected key: value")
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            raise ValueError(f"{path.relative_to(ROOT)}:{lineno}: empty key")
        if key in out:
            raise ValueError(f"{path.relative_to(ROOT)}:{lineno}: duplicate key {key}")
        out[key] = value
    return out


def extract_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    data: dict[str, str] = {}
    for raw in text.splitlines()[1:]:
        if raw.strip() == "---":
            return data
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return {}


def require_path(result: Result, label: str, raw_path: str) -> None:
    if not (ROOT / raw_path).exists():
        result.fail(f"{label}: path does not exist: {raw_path}")


def check_project(result: Result) -> None:
    try:
        cfg = parse_flat_yml(PROJECT_YML)
    except (FileNotFoundError, ValueError) as exc:
        result.fail(str(exc))
        return
    for key in REQUIRED_PROJECT_KEYS:
        if not cfg.get(key):
            result.fail(f"project.yml missing required key: {key}")
    if cfg.get("project_id") != "solarsage-astro":
        result.fail("project.yml project_id must be solarsage-astro")
    if cfg.get("workflow_runtime") != "prefect":
        result.fail("project.yml workflow_runtime must be prefect")
    if cfg.get("agent_executor") != "codex-cli":
        result.fail("project.yml agent_executor must be codex-cli")
    for label, key in (
        ("packet_dir", "packet_dir"),
        ("roles_dir", "roles_dir"),
        ("packet_schema", "packet_schema"),
        ("verification_profiles", "verification_profiles"),
    ):
        if cfg.get(key):
            require_path(result, label, cfg[key])


def check_profiles(result: Result) -> None:
    try:
        profiles = parse_flat_yml(PROFILES_YML)
    except (FileNotFoundError, ValueError) as exc:
        result.fail(str(exc))
        return
    for key in REQUIRED_PROFILES:
        value = profiles.get(key)
        if not value:
            result.fail(f"verification_profiles.yml missing {key}")
            continue
        if not (
            value.startswith("pnpm guardrails:")
            or value.startswith("bash scripts/guardrails.sh ")
        ):
            result.fail(f"{key} uses non-portable command: {value}")
    for key, value in profiles.items():
        if key.startswith("default.") and value not in profiles:
            result.fail(f"{key} references missing profile: {value}")


def check_packet_schema(result: Result) -> None:
    try:
        schema = json.loads(PACKET_SCHEMA.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        result.fail(f"packet.schema.json invalid: {exc}")
        return
    required = schema.get("required")
    if not isinstance(required, list):
        result.fail("packet.schema.json must define required list")
        return
    missing = sorted(set(REQUIRED_PACKET_SCHEMA_FIELDS) - set(required))
    if missing:
        result.fail("packet.schema.json missing required fields: " + ", ".join(missing))
    if not isinstance(schema.get("properties"), dict):
        result.fail("packet.schema.json must define properties")


def check_roles(result: Result) -> None:
    for role in REQUIRED_ROLES:
        path = ROLES_DIR / f"{role}.md"
        if not path.exists():
            result.fail(f"missing role contract: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in ROLE_REQUIRED_HEADINGS:
            if heading not in text:
                result.fail(f"{path.relative_to(ROOT)} missing heading: {heading}")
        if not re.search(r"FINAL_GRACE_[A-Z0-9_]+_JSON", text):
            result.fail(f"{path.relative_to(ROOT)} missing FINAL_GRACE_*_JSON marker")


def check_packets(result: Result) -> None:
    packet_paths = sorted(PACKETS_DIR.glob("*.md"))
    if not packet_paths:
        result.fail("no packets found under grace/packets")
        return
    strict_sections = (
        "## Allowed",
        "## Frozen",
        "## Verification",
        "## Expected Evidence",
        "## Escalation",
    )
    strict_ready = 0
    legacy_warn = 0
    for path in packet_paths:
        text = path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(path)
        for key in PACKET_FRONTMATTER_KEYS:
            if not frontmatter.get(key):
                result.fail(f"{path.relative_to(ROOT)} missing frontmatter key: {key}")
        if all(section in text for section in strict_sections):
            strict_ready += 1
        else:
            legacy_warn += 1
    if strict_ready == 0:
        result.warn("no existing packet fully matches the strict orchestrator section set")
    if legacy_warn:
        result.warn(
            f"{legacy_warn} legacy packet(s) are warning-only until migrated to packet.schema.json"
        )


def main() -> int:
    result = Result(errors=[], warnings=[])
    check_project(result)
    check_profiles(result)
    check_packet_schema(result)
    check_roles(result)
    check_packets(result)
    for warning in result.warnings:
        print(f"WARN {warning}")
    for error in result.errors:
        print(f"FAIL {error}")
    if result.errors:
        print(f"orchestrator contract gate: FAIL ({len(result.errors)} error(s))")
        return 1
    print(
        "orchestrator contract gate: PASS "
        f"({len(result.warnings)} warning(s), legacy packet warnings allowed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
