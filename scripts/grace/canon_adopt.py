#!/usr/bin/env python3
"""GRACE canon adoption — add missing AI_HEADER, MODULE_CONTRACT, MODULE_MAP, blocks.

Usage:
    python3 scripts/grace/canon_adopt.py --wave frontend     # app/ components/ hooks/ lib/
    python3 scripts/grace/canon_adopt.py --wave backend      # apps/api/app/
    python3 scripts/grace/canon_adopt.py --wave sidecar      # apps/solarsage/
    python3 scripts/grace/canon_adopt.py --wave contracts    # packages/contracts/ lib/api/ lib/log/
    python3 scripts/grace/canon_adopt.py --wave tests        # __tests__/ apps/api/tests/
    python3 scripts/grace/canon_adopt.py --wave tooling      # scripts/ grace/
    python3 scripts/grace/canon_adopt.py --all               # everything

Safety: only adds comment lines, never modifies code logic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXCLUDE_DIRS = frozenset({
    "node_modules", ".next", ".venv", "venv", "__pycache__", ".git",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
})
EXCLUDE_PREFIX = ("components/ui/", "alembic/", "migrations/", "packages/contracts/_generated.ts")

WAVE_PATHS = {
    "frontend": ["app/", "components/", "hooks/", "lib/"],
    "backend": ["apps/api/app/", "apps/api/tests/"],
    "sidecar": ["apps/solarsage/"],
    "contracts": ["packages/contracts/", "lib/api/", "lib/log/"],
    "tests": ["__tests__/"],
    "tooling": ["scripts/", "grace/"],
}


def _is_excluded(path_str: str) -> bool:
    """Check if a file path should be excluded from canon adoption."""
    fp = path_str.replace("\\", "/")
    for part in fp.split("/"):
        if part in EXCLUDE_DIRS:
            return True
    for prefix in EXCLUDE_PREFIX:
        if fp.startswith(prefix):
            return True
    return False

_ARG = ""  # set by parse_args

HEADER_TS = """// ############################################################################
// AI_HEADER: MODULE_{module_id}
// ROLE: {role}
// DEPENDENCIES: local modules
// GRACE_ANCHORS: {anchors}
// SLICE: {slice_id}
// ############################################################################"""

HEADER_PY = """# ############################################################################
# AI_HEADER: MODULE_{module_id}
# ROLE: {role}
# DEPENDENCIES: local modules
# GRACE_ANCHORS: {anchors}
# SLICE: {slice_id}
# ##################################################################### START_MODULE_CONTRACT
# purpose: Tests for canon_adopt.py behavior
# owns:
#   - scripts/grace/canon_adopt.py
# inputs: HTTP request, path/query params
# outputs: HTTP response / JSON body
# dependencies: local modules
# side_effects: Database reads/writes; Network calls to API; Logging via v2 logging spine; React state management; Processes HTTP requests
# emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
MODULE_MAP_PY = """# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP"""

BLOCK_TS = "// START_BLOCK: MAIN\n// END_BLOCK: MAIN"
BLOCK_PY = "# START_BLOCK: MAIN\n# END_BLOCK: MAIN"


PLACEHOLDER_PATTERNS = (
    "varies", "Library module", "Varies", "library module",
    "n/a (pure)", "n/a (pure)",
)

# ── Slice classification (exact paths before prefixes) ─────────────────
SLICE_MAP: list[tuple[tuple[str, ...], str]] = [
    (("__tests__/",), "SLICE-TESTS"),
    (("apps/api/tests/",), "SLICE-TESTS"),
    (("components/today/tab-bar.tsx",), "SLICE-SHELL-NAVIGATION"),
    (("components/app-shell.tsx",), "SLICE-SHELL-NAVIGATION"),
    (("lib/today.ts",), "SLICE-TODAY-CALENDAR"),
    (("lib/calendar.ts",), "SLICE-TODAY-CALENDAR"),
    (("components/today/",), "SLICE-TODAY-CALENDAR"),
    (("components/calendar/",), "SLICE-TODAY-CALENDAR"),
    (("app/(grace)/today/",), "SLICE-TODAY-CALENDAR"),
    (("components/readings/",), "SLICE-HORARY-READINGS"),
    (("components/profile/",), "SLICE-PROFILE-ONBOARDING"),
    (("components/onboarding/",), "SLICE-PROFILE-ONBOARDING"),
    (("lib/api/",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/access.ts",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/grace/",), "SLICE-LOGGING-SPINE"),
    (("packages/contracts/",), "SLICE-CONTRACTS"),
    (("apps/api/app/api/",), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/api/app/services/",), "SLICE-BACKEND-SERVICES"),
    (("apps/api/app/schemas/",), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/api/app/db/",), "SLICE-DB-MODELS-MIGRATIONS"),
    (("apps/api/app/core/",), "SLICE-BACKEND-SERVICES"),
    (("apps/api/app/",), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/solarsage/",), "SLICE-SIDECAR-CALCULATION"),
    (("scripts/",), "SLICE-GUARDRAILS-TOOLING"),
    (("grace/",), "SLICE-ORCHESTRATOR-ADAPTER"),
]

def _has_placeholder(text: str) -> bool:
    """Check if existing markers contain placeholder values that need replacement."""
    return any(p in text for p in PLACEHOLDER_PATTERNS)


# ── Slice / module ID helpers ─────────────────────────────────────────


def _slice(path: str) -> str:
    for prefixes, sid in SLICE_MAP:
        for prefix in prefixes:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                return sid
    return "SLICE-UNMAPPED"


def _module_id(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    name = Path(path).stem.upper().replace("-", "_").replace(".", "_")
    if name.startswith("_"):
        name = name[1:]
    parent = parts[-2].upper() if len(parts) >= 2 else ""
    return f"{parent}_{name}" if parent else name


# ── File content analysis ──────────────────────────────────────────────


def _analyze_file(text: str) -> dict[str, bool]:
    info: dict[str, bool] = {}
    info["has_react"] = "from \"react\"" in text or "from 'react'" in text
    info["has_next"] = "next/" in text
    info["has_log"] = any(p in text for p in ["lib/grace/log", "GraceLogger", "logEvent", "log_event", "logger."])
    info["has_api"] = any(p in text for p in ["fetch(", "axios", "get_api", "post_api", "httpx", "requests"])
    info["has_db"] = any(p in text for p in ["db.", "session.", "query(", "execute(", "SQL", "models."])
    info["has_http_routes"] = any(p in text for p in ["@router.", "@app.", "def get(", "def post(", "def put("])
    info["is_test"] = "describe(" in text or "test(" in text or "def test_" in text or "it(" in text
    info["has_hooks"] = any(p in text for p in ["useEffect", "useState", "useCallback", "useMemo"])
    info["has_components"] = any(p in text for p in ["export default function", "export const", "React.FC", "extends Component"])
    return info


def _purpose(rel_path: str, info: dict) -> str:
    if info["is_test"]: return f"Tests for {rel_path.split('/')[-1]} behavior"
    if info["has_http_routes"]: return f"HTTP routes for {rel_path.split('/')[-1].replace('.py','')}"
    if info["has_db"] and info["has_api"]: return f"Data access and service for {rel_path.split('/')[-1].replace('.py','')}"
    if info["has_db"]: return f"DB access for {rel_path.split('/')[-1].replace('.py','')}"
    if info["has_api"]: return f"API client for {rel_path.split('/')[-1].replace('.ts','').replace('.tsx','')}"
    if info["has_components"] or info["has_hooks"]: return f"UI {rel_path.split('/')[-1].replace('.tsx','').replace('.ts','')}"
    if info["has_next"]: return f"Page: {rel_path.split('/')[-1].replace('.tsx','').replace('.ts','')}"
    if rel_path.startswith("packages/contracts/"): return f"Contract: {rel_path.split('/')[-1].replace('.ts','')}"
    if rel_path.startswith("scripts/"): return f"Tool: {rel_path.split('/')[-1].replace('.py','').replace('.sh','')}"
    if rel_path.startswith("lib/"): return f"Library: {rel_path.split('/')[-1].replace('.ts','')}"
    return f"Module: {rel_path.split('/')[-1]}"


def _side_effects(rel_path: str, info: dict) -> str:
    parts = []
    if info["has_db"]: parts.append("Database reads/writes")
    if info["has_api"]: parts.append("Network calls to API")
    if info["has_log"]: parts.append("Logging via v2 spine")
    if info["has_hooks"]: parts.append("React state management")
    if info["has_http_routes"]: parts.append("Processes HTTP requests")
    return "; ".join(parts) if parts else ("n/a (pure)" if not info["is_test"] else "n/a (tests)")


def _emitted_logs(rel_path: str, info: dict) -> str:
    if info["has_log"]: return "v2: logEvent/logStart/logSuccess (frontend) or logger.* (backend)"
    return "n/a (pure)" if not info["is_test"] else "n/a (tests)"


def _inputs_outputs(rel_path: str, info: dict) -> tuple[str, str]:
    if info["has_http_routes"]: return "HTTP request, path/query", "HTTP response / JSON"
    if info["has_components"] or info["has_hooks"]: return "Props / hook params", "TSX / return values"
    if info["has_db"]: return "Query params, models", "Records"
    if info["has_api"]: return "Endpoint params, body", "Parsed response"
    if info["is_test"]: return "Mocks, fixtures", "Assertions"
    if rel_path.startswith("packages/contracts/"): return "n/a (types)", "n/a (types)"
    return "Function args", "Return values"


def _role(rel_path: str, info: dict) -> str:
    if info["is_test"]: return f"Tests — {rel_path.split('/')[-1]}"
    if info["has_http_routes"]: return f"API — {rel_path.split('/')[-1].replace('.py','')}"
    if info["has_db"] and info["has_api"]: return f"Service — {rel_path.split('/')[-1].replace('.py','')}"
    if info["has_db"]: return f"DB — {rel_path.split('/')[-1].replace('.py','')}"
    if info["has_components"] or info["has_hooks"]: return f"UI — {rel_path.split('/')[-1].replace('.tsx','').replace('.ts','')}"
    if info["has_next"]: return f"Page — {rel_path.split('/')[-1]}"
    if rel_path.startswith("packages/contracts/"): return f"Contract — {rel_path.split('/')[-1]}"
    if rel_path.startswith("lib/"): return f"Lib — {rel_path.split('/')[-1]}"
    if rel_path.startswith("scripts/"): return f"Tool — {rel_path.split('/')[-1]}"
    return "Module"


AI_HEADER_RE = re.compile(r"(?://|#|/\*|\*)\s*AI_HEADER\s*:\s*\S+", re.MULTILINE)
MC_RE = re.compile(r"(?://|#)\s*START_MODULE_CONTRACT")
MM_RE = re.compile(r"(?://|#)\s*START_MODULE_MAP")
BLOCK_RE = re.compile(r"(?://|#)\s*START_BLOCK\s*:")


def _needs_update(text: str, rel_path: str) -> bool:
    """Check if file needs any marker changes."""
    has_ai = bool(AI_HEADER_RE.search(text))
    has_mc = bool(MC_RE.search(text))
    has_mm = bool(MM_RE.search(text))
    missing = not (has_ai and has_mc and has_mm)
    placeholders = _has_placeholder(text)
    return missing or placeholders


def _replace_marker_block(text: str, marker_start: str, marker_end: str,
                           new_content: str, is_py: bool) -> str:
    """Replace content between two markers, inclusive. If markers don't exist, append."""
    start_idx = text.find(marker_start)
    end_idx = text.find(marker_end, start_idx + 1) if start_idx != -1 else -1
    if start_idx != -1 and end_idx != -1:
        # Find end of the end marker line
        eol = text.find("\n", end_idx)
        if eol == -1:
            eol = len(text)
        return text[:start_idx] + new_content + "\n" + text[eol + 1:]
    # Marker not found — append before imports/first code
    lines = text.split("\n")
    insert_at = 0
    while insert_at < len(lines):
        line = lines[insert_at]
        if line.startswith("#!") or line.startswith("# -*-") or line.strip() == "":
            insert_at += 1
        else:
            break
    return "\n".join(lines[:insert_at] + [new_content] + lines[insert_at:])


def _generate_header(is_py: bool, mod_id: str, role: str, anchors: str, slice_id: str) -> str:
    tpl = HEADER_PY if is_py else HEADER_TS
    return tpl.format(module_id=mod_id, role=role, anchors=anchors, slice_id=slice_id)


def _generate_contract(is_py: bool, purpose: str, path: str, inputs_str: str,
                       outputs_str: str, side_effects: str, emitted: str) -> str:
    tpl = MODULE_CONTRACT_PY if is_py else MODULE_CONTRACT_TS
    return tpl.format(purpose=purpose, path=path, inputs=inputs_str,
                      outputs=outputs_str, side_effects=side_effects,
                      emitted_logs=emitted)


def _generate_mm(is_py: bool) -> str:
    tpl = MODULE_MAP_PY if is_py else MODULE_MAP_TS
    return tpl if "{" not in tpl else tpl.format()


def _add_markers(text: str, rel_path: str, ext: str) -> str:
    """Surgically replace placeholder lines within existing contract blocks.

    Only replaces lines containing placeholder values like 'varies' or
    'Library module'. Does NOT overwrite hand-written contracts.
    """
    if not _needs_update(text, rel_path):
        return text

    is_py = ext in (".py", ".pyi")
    info = _analyze_file(text)
    slice_id = _slice(rel_path)
    mod_id = _module_id(rel_path)
    role = _role(rel_path, info)
    purpose = _purpose(rel_path, info)
    side_effects = _side_effects(rel_path, info)
    emitted = _emitted_logs(rel_path, info)
    inputs_str, outputs_str = _inputs_outputs(rel_path, info)
    anchors = "[]"

    # Build replacement values keyed by field name
    replacements = {
        "purpose:": purpose,
        "ROLE:": role,
        "inputs:": inputs_str if inputs_str != "varies" else "Function arguments",
        "outputs:": outputs_str if outputs_str != "varies" else "Return values",
        "side_effects:": side_effects,
        "emitted_logs:": emitted,
    }

    lines = text.split("\n")
    modified = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Only touch comment lines inside contract or AI_HEADER blocks
        if not stripped.startswith("#") and not stripped.startswith("//"):
            continue

        for field, new_value in replacements.items():
            if field in stripped and any(p in stripped for p in ("varies", "n/a", "Library module", "library module",
                                                                   "Varies", "n/a (pure)", )):
                # Replace the value after the field label
                marker_char = "#" if stripped.startswith("#") else "//"
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = f"{indent}{marker_char} {field} {new_value}"
                modified = True

    if not modified:
        return text
    return "\n".join(lines)
    mm_block = mm_tpl.format()
    block_block = block_tpl

    lines = text.split("\n")
    insert_at = 0

    # Find insertion point after existing shebang/encoding lines
    while insert_at < len(lines):
        line = lines[insert_at]
        if line.startswith("#!") or line.startswith("# -*-") or line.startswith("<?xml"):
            insert_at += 1
        elif line.strip() == "":
            insert_at += 1
        else:
            break

    # Build preamble
    preamble = []
    if needs_ai:
        preamble.append("")
        preamble.append(header)
        preamble.append("")
    # Add module contract before imports
    if needs_mc:
        preamble.append(contract)
        preamble.append("")
    # Add module map before code
    if needs_mm:
        preamble.append(mm_block)
        preamble.append("")

    if not preamble:
        return text

    # Insert preamble
    new_lines = lines[:insert_at] + preamble + lines[insert_at:]
    return "\n".join(new_lines)


def _collect_files(paths: list[str], exclude_existing: bool) -> list[Path]:
    """Collect files in given paths, optionally excluding those with full markers."""
    files: list[Path] = []
    valid_exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".pyi", ".sh", ".bash")
    for p in paths:
        target = ROOT / p
        if not target.exists():
            continue
        if target.is_file():
            if target.suffix in valid_exts and not _is_excluded(str(target.relative_to(ROOT))):
                files.append(target)
        else:
            for ext in valid_exts:
                files.extend(target.rglob(f"*{ext}"))
    # Filter
    result = []
    for f in sorted(set(files)):
        try:
            rel = str(f.relative_to(ROOT))
        except ValueError:
            continue
        if _is_excluded(rel):
            continue
        if exclude_existing:
            text = f.read_text(encoding="utf-8", errors="replace")
            if not _needs_update(text, str(f.relative_to(ROOT))):
                continue  # already has full markers without placeholders
        result.append(f)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="GRACE canon adoption")
    ap.add_argument("--wave", choices=list(WAVE_PATHS) + ["all", "check"])
    ap.add_argument("--exclude-existing", action="store_true", help="Skip files that already have AI_HEADER")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be changed without writing")
    args = ap.parse_args()

    if args.wave == "check":
        # Run coverage audit check
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "grace" / "coverage_audit.py"), "--check"],
                           cwd=ROOT, capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr)
            sys.exit(r.returncode)
        return

    if args.wave == "all":
        paths = []
        for p in WAVE_PATHS.values():
            paths.extend(p)
    else:
        paths = WAVE_PATHS[args.wave]

    files = _collect_files(paths, exclude_existing=args.exclude_existing)
    changed = 0
    for fp in files:
        try:
            rel = str(fp.relative_to(ROOT))
        except ValueError:
            continue
        text = fp.read_text(encoding="utf-8", errors="replace")
        original = text
        text = _add_markers(text, rel, fp.suffix)
        if text != original:
            changed += 1
            if not args.dry_run:
                fp.write_text(text)
            else:
                print(f"[dry-run] would modify: {rel}")

    if args.dry_run:
        print(f"\nDry-run: {changed} files would be modified")
    else:
        print(f"Modified: {changed} files in {args.wave}")

    # Re-run audit
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "grace" / "coverage_audit.py")],
                       cwd=ROOT, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)


if __name__ == "__main__":
    main()
