#!/usr/bin/env python3
# START_MODULE_CONTRACT
# purpose: Tooling script — scripts/check_logging_guardrails.py
# owns:
#   - scripts/check_logging_guardrails.py
# inputs: Mocks, fixtures
# outputs: Assertions
# dependencies: local modules
# side_effects: Logging via v2 spine
# emitted_logs: v2: logEvent/logStart/logSuccess (frontend) or logger.* (backend)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# ############################################################################
# AI_HEADER: TOOL_OBSERVABILITY_GUARDRAILS
# ROLE: Static gate to ensure logging spine integrity and prevent drift.
# DEPENDENCIES: stdlib only (pathlib, re, sys, xml.etree.ElementTree, ast)
# ############################################################################
"""
Logging and observability guardrails.
Enforces:
1. Event registry drift check (XML vs Python vs TS).
2. No raw/legacy backend logger imports or stdlib getLogger in feature services.
3. No production console.log/warn/error usage outside logging layer.
4. Python AST checks to prevent raw identifiers and input fields leaking to log_event.
"""

from __future__ import annotations

import ast
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── AST Constants/Helpers ──────────────────────────────────────────────────
FORBIDDEN_RAW_NAMES = {
    "user_id", "tg_user_id", "telegram_id", "session_id", "token",
    "question_id", "credit_id", "thread_id", "message_id", "report_id",
    "natal_context_id", "profile_id",
}

FORBIDDEN_ID_BASES = {
    "user", "session", "question", "credit", "thread", "message",
    "report", "profile", "natal_context",
}

APPROVED_HASH_HELPERS = {"hash_log_identifier", "hash_user_id"}
INPUT_BEARING_ATTRS = {"text", "content", "question"}


def _dotted_name(node: ast.AST) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._dotted_name
    # purpose: Recursively build dotted attribute name from AST node.
    # inputs: node (ast.AST)
    # returns: str | None (dotted name representation or None)
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns None on unhandled types
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._dotted_name
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _check_dict_for_forbidden_keys(node: ast.Dict, forbidden_raw_keys: set[str]) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._check_dict_for_forbidden_keys
    # purpose: Check dictionary keys for forbidden raw keys.
    # inputs: node (ast.Dict), forbidden_raw_keys (set[str])
    # returns: list[str] of violations
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns empty list on failure
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._check_dict_for_forbidden_keys
    found = []
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            val_lower = key.value.lower().replace("_", "")
            for fk in forbidden_raw_keys:
                fk_clean = fk.lower().replace("_", "")
                if val_lower == fk_clean:
                    found.append(key.value)
    return found


def _collect_log_expr_violations(node: ast.AST) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._collect_log_expr_violations
    # purpose: Recursively collect violations in expressions, skipping approved helper calls.
    # inputs: node (ast.AST)
    # returns: list[str] of violations
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns empty list on failure
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._collect_log_expr_violations
    violations: list[str] = []

    def visit(current: ast.AST) -> None:
        if (
            isinstance(current, ast.Call)
            and isinstance(current.func, ast.Name)
            and current.func.id in APPROVED_HASH_HELPERS
        ):
            return  # raw argument is allowed inside approved hash helper

        if isinstance(current, ast.Name):
            if current.id.lower() in FORBIDDEN_RAW_NAMES:
                violations.append(f"raw identifier: {current.id}")

        elif isinstance(current, ast.Attribute):
            dotted = _dotted_name(current)
            parts = dotted.lower().split(".") if dotted else []

            if (
                len(parts) >= 2
                and parts[-1] == "id"
                and parts[-2] in FORBIDDEN_ID_BASES
            ):
                violations.append(f"raw attribute chain: {dotted}")

            if current.attr.lower() in FORBIDDEN_RAW_NAMES:
                violations.append(f"raw attribute: .{current.attr}")

            if current.attr.lower() in INPUT_BEARING_ATTRS:
                violations.append(f"forbidden input attribute: .{current.attr}")

        for child in ast.iter_child_nodes(current):
            visit(child)

    visit(node)
    return violations


def _collect_log_event_violations(call: ast.Call, file_info: str) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._collect_log_event_violations
    # purpose: Analyze a single log_event Call node for PII leak violations.
    # inputs: call (ast.Call), file_info (str)
    # returns: list[str] of violations
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns empty list on failure
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._collect_log_event_violations
    violations: list[str] = []

    # Check positional arguments (e.g. msg passed positionally)
    for arg in call.args:
        violations.extend(_collect_log_expr_violations(arg))

    # Check keyword arguments
    for kw in call.keywords:
        if kw.arg in ("payload", "error", "http"):
            # Check literal keys
            if isinstance(kw.value, ast.Dict):
                bad_keys = _check_dict_for_forbidden_keys(kw.value, FORBIDDEN_RAW_NAMES)
                if bad_keys:
                    violations.append(f"{file_info} - log_event keyword '{kw.arg}' contains forbidden raw keys: {bad_keys}")

                # Check key/value requirements for user_id_hash / *_id_hash
                for k, v in zip(kw.value.keys, kw.value.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        key_str = k.value
                        if key_str.endswith("_id_hash") or key_str == "user_id_hash":
                            valid = False
                            if isinstance(v, ast.Name) and v.id.endswith("_hash"):
                                valid = True
                            elif isinstance(v, ast.Call):
                                if isinstance(v.func, ast.Name) and v.func.id in APPROVED_HASH_HELPERS:
                                    valid = True
                            if not valid:
                                violations.append(f"{file_info} - log_event '{kw.arg}' key '{key_str}' value must be a hash helper call or a variable ending with '_hash'")

            # Recursively check the value expressions
            violations.extend(_collect_log_expr_violations(kw.value))

        elif kw.arg == "msg":
            violations.extend(_collect_log_expr_violations(kw.value))

    return violations


# ── 1. Event Registry Drift Check ──────────────────────────────────────────

def check_registry_drift() -> bool:
    xml_path = ROOT / "grace" / "canon" / "observability.xml"
    py_path = ROOT / "apps/api/app/core/logging_events.py"
    ts_path = ROOT / "lib/log/events.gen.ts"

    # A. Parse XML
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        xml_events = {el.get("name") for el in root.findall(".//event") if el.get("name")}
    except Exception as e:
        print(f"Error parsing observability.xml: {e}")
        return False

    # B. Parse Python registry
    try:
        content = py_path.read_text(encoding="utf-8")
        match = re.search(r"LogEventName = Literal\[(.*?)\]", content, re.DOTALL)
        if not match:
            print("Could not find LogEventName = Literal[...] block in logging_events.py")
            return False
        py_events = {s.strip().strip('"').strip("'") for s in re.findall(r'"([^"]+)"', match.group(1))}
    except Exception as e:
        print(f"Error reading logging_events.py: {e}")
        return False

    # C. Parse TS registry
    try:
        content = ts_path.read_text(encoding="utf-8")
        match = re.search(r"export type LogEventName =(.*?);", content, re.DOTALL)
        if not match:
            print("Could not find export type LogEventName = ... block in events.gen.ts")
            return False
        ts_events = {s.strip().strip('"').strip("'").strip("|").strip() for s in re.findall(r'"([^"]+)"', match.group(1))}
    except Exception as e:
        print(f"Error reading events.gen.ts: {e}")
        return False

    # D. Compare
    has_drift = False
    if xml_events != py_events:
        print("\n[DRIFT] XML events and Python generated registry differ:")
        print(f"  Only in XML: {xml_events - py_events}")
        print(f"  Only in Python: {py_events - xml_events}")
        has_drift = True

    if xml_events != ts_events:
        print("\n[DRIFT] XML events and TS generated registry differ:")
        print(f"  Only in XML: {xml_events - ts_events}")
        print(f"  Only in TS: {ts_events - xml_events}")
        has_drift = True

    if not has_drift:
        print("drift gate: OK")
        return True
    return False


# ── 2. No Raw Backend Logger Gate ──────────────────────────────────────────

def check_backend_logger() -> bool:
    api_dir = ROOT / "apps" / "api" / "app"
    exclude_files = {"logging.py", "logging_events.py", "redactor.py"}
    
    legacy_import_re = re.compile(r"from app\.core\.logging import logger")
    stdlib_logger_re = re.compile(r"logging\.getLogger\(")

    violations = []

    for path in api_dir.rglob("*.py"):
        if path.name in exclude_files:
            continue
        
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        if legacy_import_re.search(content):
            violations.append(f"Legacy logger import found in {path.relative_to(ROOT)}")
        
        if stdlib_logger_re.search(content):
            violations.append(f"Raw logging.getLogger() found in {path.relative_to(ROOT)}")

    if violations:
        print("\n[LEAK] Raw/legacy backend logging found:")
        for v in violations:
            print(f"  {v}")
        return False

    print("backend logger gate: OK")
    return True


# ── 3. No Production Console Usage Gate ────────────────────────────────────

def check_frontend_console() -> bool:
    exclude_dirs = {
        ROOT / "node_modules",
        ROOT / ".next",
        ROOT / ".next-prod",
        ROOT / ".next-v2-real-preview",
        ROOT / ".next-v2-preview",
        ROOT / ".grace",
        ROOT / "__tests__",
        ROOT / "legacy",
        ROOT / "apps" / "api",
        ROOT / "apps" / "solarsage",
    }
    
    # Exclude only the logging-layer files by path (not any file named index.ts)
    exclude_paths = {
        "lib/log/index.ts",
        "lib/log/shipper.ts",
        "lib/log/redactor.ts",
        "lib/log/logger.ts",
        "public/telemetry/fetch-interceptor.js",
    }

    # Allow-listed paths where console.log/warn/error is intentional
    allow_listed_prefixes = {
        "e2e/",
        "app/debug-auth/",
        "app/(grace)/debug/",
    }

    console_re = re.compile(r"\bconsole\.(log|warn|error)\b")
    violations = []

    for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
        for path in ROOT.rglob(ext):
            # Exclude directories
            if any(path.is_relative_to(d) for d in exclude_dirs):
                continue
            # Exclude only logging-layer files by path
            rel = path.relative_to(ROOT).as_posix()
            if rel in exclude_paths:
                continue
            # Exclude test files
            if ".test." in path.name or ".spec." in path.name:
                continue
            # Exclude allow-listed paths
            if any(rel.startswith(p) for p in allow_listed_prefixes):
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue

            # Strip comments to avoid checking comment notes/todo comments
            content_no_comments = re.sub(r"//.*|/\*[\s\S]*?\*/", "", content)

            if console_re.search(content_no_comments):
                violations.append(f"Console log usage found in {path.relative_to(ROOT)}")

    if violations:
        print("\n[LEAK] Raw console logging found in production code:")
        for v in violations:
            print(f"  {v}")
        return False

    print("frontend console gate: OK")
    return True


# ── 4. Python AST Security Guardrail Gate ───────────────────────────────────

def check_python_ast_guardrails() -> bool:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS.check_python_ast_guardrails
    # purpose: Scan python files for print statements and logging violations.
    # inputs: none
    # returns: bool
    # side_effects: prints to stdout
    # emitted_logs: none
    # error_behavior: returns False on violations
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS.check_python_ast_guardrails
    api_dir = ROOT / "apps" / "api" / "app"

    # Allowed prints in documented startup canon diagnostics
    allowed_prints = {
        "apps/api/app/services/canon_service.py",
    }

    violations = []

    for path in api_dir.rglob("*.py"):
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
        except Exception as e:
            print(f"Error parsing AST for {path}: {e}")
            continue

        rel_path = path.relative_to(ROOT).as_posix()
        file_info = f"{rel_path}"

        for node in ast.walk(tree):
            # Check for print() calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                if rel_path not in allowed_prints:
                    violations.append(f"{file_info}:{node.lineno} - Raw print() statement found")

            # Check for log_event(...) calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "log_event":
                violations.extend(_collect_log_event_violations(node, f"{file_info}:{node.lineno}"))

    if violations:
        print("\n[SECURITY] Logging security violations found:")
        for v in violations:
            print(f"  {v}")
        return False

    print("python AST security gate: OK")
    return True


# ── Self-Tests / Fixtures ──────────────────────────────────────────────────

def _violations_for_snippet(code: str) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._violations_for_snippet
    # purpose: Parse a code snippet and collect log_event violations.
    # inputs: code (str)
    # returns: list[str] of violations
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns empty list on syntax error
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS._violations_for_snippet
    tree = ast.parse(code)
    result: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "log_event"
        ):
            result.extend(_collect_log_event_violations(node, "<self-test>"))
    return result


def run_self_tests() -> bool:
    # START_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS.run_self_tests
    # purpose: Verify the correctness of AST check rules on safe and unsafe snippets.
    # inputs: none
    # returns: bool
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on test failure
    # END_FUNCTION_CONTRACT: F-M-TOOL-OBSERVABILITY-GUARDRAILS.run_self_tests
    print("Running AST guardrail self-tests...")

    # Positive case: safe log_event usage
    safe_code = """
log_event("system.info", msg="Hello world")
log_event("user.login", payload={"user_id_hash": hash_user_id(uid)})
log_event("some.event", payload={"thread_id_hash": thread_hash})
"""
    # Negative cases
    unsafe_code_1 = """
log_event("system.error", payload={"actor": user_id})
"""
    unsafe_code_2 = """
log_event("system.error", error={"detail": question.text})
"""
    unsafe_code_3 = """
log_event("system.error", payload={"user_id_hash": "123e4567-e89b-12d3-a456-426614174000"})
"""
    unsafe_code_4 = """
log_event("system.error", msg=f"Error in question {question_id}")
"""
    unsafe_code_5 = """
log_event("system.error", payload={"actor": credit.id})
"""
    unsafe_code_6 = """
log_event("system.error", msg=f"question {question.id}")
"""
    unsafe_code_7 = """
log_event("system.error", error={"context": {"actor": report.id}})
"""
    safe_code_2 = """
log_event("system.error", payload={"credit_id_hash": hash_log_identifier("credit", credit.id)})
"""

    # Safe test
    v_safe = _violations_for_snippet(safe_code)
    assert not v_safe, f"Safe code triggered violations: {v_safe}"

    v_safe_2 = _violations_for_snippet(safe_code_2)
    assert not v_safe_2, f"Safe code 2 triggered violations: {v_safe_2}"

    # Unsafe 1 test
    v_unsafe_1 = _violations_for_snippet(unsafe_code_1)
    assert any("raw identifier: user_id" in x for x in v_unsafe_1), f"Unsafe code 1 did not trigger user_id violation: {v_unsafe_1}"

    # Unsafe 2 test
    v_unsafe_2 = _violations_for_snippet(unsafe_code_2)
    assert any("forbidden input attribute: .text" in x for x in v_unsafe_2), f"Unsafe code 2 did not trigger .text violation: {v_unsafe_2}"

    # Unsafe 3 test
    v_unsafe_3 = _violations_for_snippet(unsafe_code_3)
    assert any("must be a hash helper call or a variable ending with" in x for x in v_unsafe_3), f"Unsafe code 3 did not trigger hash value violation: {v_unsafe_3}"

    # Unsafe 4 test
    v_unsafe_4 = _violations_for_snippet(unsafe_code_4)
    assert any("raw identifier: question_id" in x for x in v_unsafe_4), f"Unsafe code 4 did not trigger f-string violation: {v_unsafe_4}"

    # Unsafe 5 test (credit.id)
    v_unsafe_5 = _violations_for_snippet(unsafe_code_5)
    assert any("raw attribute chain: credit.id" in x for x in v_unsafe_5), f"Unsafe code 5 did not trigger credit.id violation: {v_unsafe_5}"

    # Unsafe 6 test (question.id)
    v_unsafe_6 = _violations_for_snippet(unsafe_code_6)
    assert any("raw attribute chain: question.id" in x for x in v_unsafe_6), f"Unsafe code 6 did not trigger question.id violation: {v_unsafe_6}"
    # Verify that we do not double count the violation in JoinedStr (f-string msg)
    assert v_unsafe_6.count("raw attribute chain: question.id") == 1

    # Unsafe 7 test (report.id)
    v_unsafe_7 = _violations_for_snippet(unsafe_code_7)
    assert any("raw attribute chain: report.id" in x for x in v_unsafe_7), f"Unsafe code 7 did not trigger report.id violation: {v_unsafe_7}"

    print("AST guardrail self-tests PASSED.")
    return True


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    success = True

    print("=== Running Logging and Observability Guardrails ===")
    if not run_self_tests():
        success = False
    if not check_registry_drift():
        success = False
    if not check_backend_logger():
        success = False
    if not check_frontend_console():
        success = False
    if not check_python_ast_guardrails():
        success = False

    if not success:
        print("\nGuardrails FAILED.")
        sys.exit(1)

    print("\nAll guardrails PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
