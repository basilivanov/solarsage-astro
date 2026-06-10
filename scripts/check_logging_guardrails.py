#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: TOOL_OBSERVABILITY_GUARDRAILS
# ROLE: Static gate to ensure logging spine integrity and prevent drift.
# DEPENDENCIES: stdlib only (pathlib, re, sys, xml.etree.ElementTree)
# ############################################################################
"""
Logging and observability guardrails.
Enforces:
1. Event registry drift check (XML vs Python vs TS).
2. No raw/legacy backend logger imports or stdlib getLogger in feature services.
3. No production console.log/warn/error usage outside logging layer.
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
        ROOT / "__tests__",
        ROOT / "legacy",
        ROOT / "apps" / "api",
        ROOT / "apps" / "solarsage",
    }
    
    exclude_files = {
        "index.ts", "shipper.ts", "redactor.ts", "logger.ts", "fetch-interceptor.js", "chat-reducer.test.ts"
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
            # Exclude specific logging files
            if path.name in exclude_files:
                continue
            # Exclude test files
            if ".test." in path.name or ".spec." in path.name:
                continue
            # Exclude allow-listed paths
            rel = path.relative_to(ROOT).as_posix()
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


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    success = True
    
    print("=== Running Logging and Observability Guardrails ===")
    if not check_registry_drift():
        success = False
    if not check_backend_logger():
        success = False
    if not check_frontend_console():
        success = False

    if not success:
        print("\nGuardrails FAILED.")
        sys.exit(1)
    
    print("\nAll guardrails PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
