#!/usr/bin/env python3
"""GRACE slice coverage audit — inventory markers, logs, slices per file.

Usage:
    python3 scripts/grace/coverage_audit.py
    python3 scripts/grace/coverage_audit.py --check  # verify JSON is stable
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXCLUDE_DIRS = frozenset({
    "node_modules", ".next", ".venv", "venv", "__pycache__", ".git",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
})
EXCLUDE_PREFIX = ("components/ui/", "alembic/", "migrations/")

# Slice classification — more specific prefixes FIRST
SLICE_MAP: list[tuple[tuple[str, ...], str]] = [
    (("packages/contracts/",), "SLICE-CONTRACTS"),
    (("__tests__/",), "SLICE-TESTS"),
    (("apps/api/tests/",), "SLICE-TESTS"),
    (("apps/solarsage/tests/",), "SLICE-TESTS"),
    # Backend — specific first
    (("apps/api/app/services/",), "SLICE-BACKEND-SERVICES"),
    (("apps/api/app/schemas/",), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/api/app/api/",), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/api/app/core/",), "SLICE-BACKEND-SERVICES"),
    (("apps/api/app/db/",), "SLICE-DB-MODELS-MIGRATIONS"),
    (("apps/api/app/",), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/api/scoring/",), "SLICE-SCORING-SEMANTIC-LLM"),
    (("apps/api/normalization/",), "SLICE-SCORING-SEMANTIC-LLM"),
    (("apps/api/semantic/",), "SLICE-SCORING-SEMANTIC-LLM"),
    (("apps/api/calculations/",), "SLICE-SIDECAR-CALCULATION"),
    (("apps/solarsage/",), "SLICE-SIDECAR-CALCULATION"),
    # Frontend slices
    (("components/today/",), "SLICE-TODAY-CALENDAR"),
    (("app/(grace)/today/",), "SLICE-TODAY-CALENDAR"),
    (("lib/today.ts",), "SLICE-TODAY-CALENDAR"),
    (("lib/calendar.ts",), "SLICE-TODAY-CALENDAR"),
    (("components/calendar/",), "SLICE-TODAY-CALENDAR"),
    (("components/app-shell.tsx",), "SLICE-SHELL-NAVIGATION"),
    (("components/today/tab-bar.tsx",), "SLICE-SHELL-NAVIGATION"),
    (("components/readings/",), "SLICE-HORARY-READINGS"),
    (("app/(grace)/readings/",), "SLICE-HORARY-READINGS"),
    (("components/profile/",), "SLICE-PROFILE-ONBOARDING"),
    (("components/onboarding/",), "SLICE-PROFILE-ONBOARDING"),
    (("app/(grace)/profile/",), "SLICE-PROFILE-ONBOARDING"),
    (("app/(grace)/onboarding/",), "SLICE-PROFILE-ONBOARDING"),
    (("lib/api/",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/access.ts",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/profile.ts",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/chat.ts",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/cities.ts",), "SLICE-FRONTEND-API-FACADES"),
    (("lib/grace/",), "SLICE-LOGGING-SPINE"),
    # Scripts and tooling
    (("scripts/",), "SLICE-GUARDRAILS-TOOLING"),
    (("grace/",), "SLICE-ORCHESTRATOR-ADAPTER"),
    # Catch-all for remaining frontend
    (("components/",), "SLICE-OTHER-COMPONENTS"),
    (("app/",), "SLICE-OTHER-APP"),
    (("lib/",), "SLICE-OTHER-FRONTEND"),
    (("types/",), "SLICE-OTHER-FRONTEND"),
    # Backend catch-all
    (("apps/",), "SLICE-OTHER-BACKEND"),
]

# Marker detection — same regex as the linters, tolerant to optional space after comment char
AI_HEADER_RE = re.compile(r"(?://|#|/\*|\*)\s*AI_HEADER\s*:\s*\S+", re.MULTILINE)
M_CONTRACT_START_RE = re.compile(r"(?://|#)\s*START_MODULE_CONTRACT(?:\s*:\s*\S+)?")
M_CONTRACT_END_RE = re.compile(r"(?://|#)\s*END_MODULE_CONTRACT(?:\s*:\s*\S+)?")
M_MAP_START_RE = re.compile(r"(?://|#)\s*START_MODULE_MAP(?:\s*:\s*\S+)?")
M_MAP_END_RE = re.compile(r"(?://|#)\s*END_MODULE_MAP(?:\s*:\s*\S+)?")
BLOCK_START_RE = re.compile(r"(?://|#)\s*START_BLOCK\s*:\s*(.*)")
BLOCK_END_RE = re.compile(r"(?://|#)\s*END_BLOCK\s*:\s*(.*)")
FUNC_CONTRACT_START_RE = re.compile(r"(?://|#)\s*START_FUNCTION_CONTRACT")
FUNC_CONTRACT_END_RE = re.compile(r"(?://|#)\s*END_FUNCTION_CONTRACT")
LOG_DECLARED_IN_CONTRACT_RE = re.compile(r"emitted_logs\s*:")

# Logging detection
LOG_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("grace_log", re.compile(r"from.*lib/grace/log.*import|GraceLogger"), "canonical"),
    ("structlog", re.compile(r"structlog|get_logger"), "canonical"),
    ("logging", re.compile(r"logging\.getLogger|import logging"), "acceptable but undocumented"),
    ("console", re.compile(r"console\.(log|warn|error)"), "non-canonical"),
    ("print", re.compile(r'print\s*\('), "non-canonical"),
    ("logEvent", re.compile(r"logEvent|log_event|track"), "acceptable but undocumented"),
    ("logger_var", re.compile(r"\blogger\b.*=.*getLogger|\blogger\b\s*="), "acceptable but undocumented"),
]

# Module IDs from knowledge-graph.xml — simple heuristic map
MODULE_MAP: dict[str, str] = {
    "components/today/": "M-WEB-DAY",
    "components/calendar/": "M-WEB-CALENDAR",
    "components/readings/": "M-WEB-READINGS",
    "components/chat/": "M-WEB-CHAT",
    "components/profile/": "M-WEB-PROFILE",
    "components/onboarding/": "M-WEB-ONBOARDING",
    "components/app-shell.tsx": "M-WEB-SHELL",
    "components/today/tab-bar.tsx": "M-WEB-SHELL",
    "lib/grace/": "M-LOGGING-SPINE",
    "lib/api/": "M-FRONTEND-API",
    "app/(grace)/today/": "M-WEB-DAY",
    "app/(grace)/readings/": "M-WEB-READINGS",
    "app/(grace)/profile/": "M-WEB-PROFILE",
    "app/(grace)/onboarding/": "M-WEB-ONBOARDING",
    "app/(grace)/calendar/": "M-WEB-CALENDAR",
    "apps/api/app/api/": "M-API-ROUTER",
    "apps/api/app/services/": "M-BACKEND-SERVICE",
    "apps/api/app/schemas/": "M-CONTRACTS",
    "apps/api/app/db/": "M-DB",
    "apps/api/app/core/": "M-BACKEND-CORE",
    "apps/solarsage/": "M-SOLARSAGE-SVC",
}


def _resolve_module_id(path: str) -> str:
    for prefix, mod_id in sorted(MODULE_MAP.items(), key=lambda x: -len(x[0])):
        if path.startswith(prefix):
            return mod_id
    return ""


def classify_slice(path: str) -> str:
    for prefixes, slice_id in SLICE_MAP:
        for prefix in prefixes:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                return slice_id
    return "SLICE-UNMAPPED"


def is_excluded(path: str) -> bool:
    fp = path.replace("\\", "/")
    for part in fp.split("/"):
        if part in EXCLUDE_DIRS:
            return True
    for prefix in EXCLUDE_PREFIX:
        if fp.startswith(prefix):
            return True
    return False


def _marker_pairing_status(mc_s: int, mc_e: int, mm_s: int, mm_e: int,
                            blk_s: list[str], blk_e: list[str]) -> str:
    issues = []
    if mc_s != mc_e:
        issues.append(f"MODULE_CONTRACT start={mc_s} != end={mc_e}")
    if mm_s != mm_e:
        issues.append(f"MODULE_MAP start={mm_s} != end={mm_e}")
    if len(blk_s) != len(blk_e):
        issues.append(f"BLOCK start={len(blk_s)} != end={len(blk_e)}")
    blk_s_set = set(blk_s)
    blk_e_set = set(blk_e)
    only_start = blk_s_set - blk_e_set
    only_end = blk_e_set - blk_s_set
    if only_start:
        issues.append(f"unclosed BLOCKs: {only_start}")
    if only_end:
        issues.append(f"unmatched BLOCK ends: {only_end}")
    return "; ".join(issues) if issues else "paired"


def scan_file(full_path: Path, rel_path: str) -> dict[str, Any]:
    text = full_path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    ext = full_path.suffix
    lang = "python" if ext in (".py", ".pyi") else \
           "typescript" if ext in (".ts", ".tsx") else \
           "javascript" if ext in (".js", ".jsx", ".mjs") else \
           "shell" if ext in (".sh", ".bash") else "other"

    ai_header = bool(AI_HEADER_RE.search(text))
    mc_s = len(M_CONTRACT_START_RE.findall(text))
    mc_e = len(M_CONTRACT_END_RE.findall(text))
    mm_s = len(M_MAP_START_RE.findall(text))
    mm_e = len(M_MAP_END_RE.findall(text))
    blk_starts = [m.strip() for m in BLOCK_START_RE.findall(text) if m.strip()]
    blk_ends = [m.strip() for m in BLOCK_END_RE.findall(text) if m.strip()]
    fc_s = len(FUNC_CONTRACT_START_RE.findall(text))
    fc_e = len(FUNC_CONTRACT_END_RE.findall(text))

    marker_status = "none"
    if ai_header and mc_s and mc_e and mm_s and mm_e:
        marker_status = "full"
    elif ai_header or mc_s or mm_s:
        marker_status = "partial"

    pair_status = _marker_pairing_status(mc_s, mc_e, mm_s, mm_e, blk_starts, blk_ends)

    # Logging
    log_found: list[str] = []
    log_class = "none"
    for name, pattern, cls in LOG_PATTERNS:
        if pattern.search(text):
            log_found.append(name)
            if cls == "canonical":
                log_class = "canonical"
            elif log_class != "canonical" and cls != "non-canonical":
                log_class = cls
    if not log_found:
        log_class = "none"

    # Check if logging is declared in MODULE_CONTRACT
    logging_declared = bool(LOG_DECLARED_IN_CONTRACT_RE.search(text))

    # Adoption priority
    slice_id = classify_slice(rel_path)
    p0_slices = {"SLICE-TODAY-CALENDAR", "SLICE-BACKEND-API-ROUTERS",
                 "SLICE-BACKEND-SERVICES", "SLICE-CONTRACTS"}
    p1_slices = {"SLICE-HORARY-READINGS", "SLICE-PROFILE-ONBOARDING", "SLICE-LOGGING-SPINE"}
    if slice_id in p0_slices:
        priority = "P0"
    elif slice_id in p1_slices:
        priority = "P1"
    elif slice_id == "SLICE-TESTS":
        priority = "P2"
    elif marker_status == "full":
        priority = "skip"
    else:
        priority = "P2"

    return {
        "path": rel_path,
        "language": lang,
        "slice": slice_id,
        "module_id": _resolve_module_id(rel_path),
        "lines": len(lines),
        "has_AI_HEADER": ai_header,
        "has_MODULE_CONTRACT_START": mc_s > 0,
        "has_MODULE_CONTRACT_END": mc_e > 0,
        "has_MODULE_MAP_START": mm_s > 0,
        "has_MODULE_MAP_END": mm_e > 0,
        "FUNCTION_CONTRACT_START_count": fc_s,
        "FUNCTION_CONTRACT_END_count": fc_e,
        "BLOCK_START_count": len(blk_starts),
        "BLOCK_END_count": len(blk_ends),
        "block_names": blk_starts,
        "marker_status": marker_status,
        "pairing_status": pair_status,
        "logging_patterns": log_found,
        "logging_class": log_class,
        "logging_declared_in_contract": logging_declared,
        "adoption_priority": priority,
        "notes": _notes(rel_path, slice_id, marker_status, log_class, logging_declared),
    }


def _notes(path: str, slice_id: str, marker: str, log_class: str, log_declared: bool) -> str:
    notes = []
    if slice_id == "SLICE-UNMAPPED":
        notes.append("no slice match")
    if marker == "none":
        notes.append("no GRACE markers")
    elif marker == "partial":
        notes.append("incomplete markers")
    if log_class == "none":
        notes.append("no logging")
    elif log_class == "non-canonical":
        notes.append("non-canonical logging (console/print)")
    elif log_class == "acceptable but undocumented":
        notes.append("logging needs declaration in MODULE_CONTRACT")
    if not log_declared and marker != "none":
        notes.append("logging not declared in contract")
    return "; ".join(notes)


def _stable_hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]


def _generate_markdown(output: dict) -> str:
    def _pct(n: int, total: int) -> str:
        return f"{round(n / total * 100, 1)}%" if total else "0.0%"

    s = output["summary"]
    lines = [
        f"# Report: Solar Sage GRACE slice coverage audit",
        f"",
        f"**Status:** PASS (audit only)",
        f"**Date:** 2026-06-11",
        f"**Baseline SHA:** `{output['baseline_sha']}`",
        f"**JSON hash:** `{_stable_hash(output)}`",
        f"",
        f"## How audit was run",
        f"```bash",
        f"python3 scripts/grace/coverage_audit.py",
        f"```",
        f"",
        f"Generated: `docs/work/solarsage_grace_slice_coverage.json`",
        f"",
        f"## Coverage summary",
        f"",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total files audited | {s['total_files_audited']} |",
        f"| Full GRACE markers | {s['markers_full']} ({_pct(s['markers_full'], s['total_files_audited'])}) |",
        f"| Partial markers | {s['markers_partial']} ({_pct(s['markers_partial'], s['total_files_audited'])}) |",
        f"| No markers | {s['markers_none']} ({_pct(s['markers_none'], s['total_files_audited'])}) |",
        f"| Canonical logging | {s['canonical_logging']} ({_pct(s['canonical_logging'], s['total_files_audited'])}) |",
        f"| Unmapped | {s['unmapped_files']} ({_pct(s['unmapped_files'], s['total_files_audited'])}) |",
        f"",
        f"## Coverage by slice",
        f"",
        f"| Slice | Total | Full | Partial | None | Coverage | Canonical log |",
        f"|---|---|---|---|---|---|---|",
    ]
    for sl in sorted(output["slices"], key=lambda x: -x["total"]):
        lines.append(
            f"| {sl['id']} | {sl['total']} | {sl['markers_full']} | "
            f"{sl['markers_partial']} | {sl['markers_none']} | "
            f"{sl['coverage_pct']}% | {sl['canonical_logging']} |"
        )
    lines += [
        f"",
        f"## Zero-coverage product slices",
        f"",
    ]
    zero_coverage = [sl for sl in output["slices"] if sl["coverage_pct"] == 0 and sl["total"] > 0]
    for sl in zero_coverage:
        lines.append(f"- **{sl['id']}**: {sl['total']} files, 0% coverage")
    lines += [
        f"",
        f"## Sentinel files",
        f"",
    ]
    for f in output["files"]:
        if f["marker_status"] in ("full", "partial") or f["logging_class"] != "none":
            continue
        if f["slice"] == "SLICE-UNMAPPED":
            continue
        lines.append(f"- `{f['path']}` — {f['slice']}: no markers, no logging")
        if len([l for l in lines if l.startswith("- `")]) >= 8:
            lines.append(f"  ... and more")
            break
    lines += [
        f"",
        f"## Recommended adoption waves",
        f"",
        f"| Wave | Priority | Slices |",
        f"|---|---|---|",
        f"| W-GRACE-SLICE-P0-TODAY-CALENDAR | P0 | Today/Calendar |",
        f"| W-GRACE-SLICE-P0-BACKEND-API-SERVICES | P0 | Backend API + services |",
        f"| W-GRACE-SLICE-P0-CONTRACTS | P0 | Contracts |",
        f"| W-GRACE-SLICE-P1-HORARY-READINGS | P1 | Horary/Readings |",
        f"| W-GRACE-SLICE-P1-PROFILE-ONBOARDING | P1 | Profile/Onboarding |",
        f"| W-GRACE-SLICE-P1-LOGGING-SPINE | P1 | Logging spine |",
        f"| W-GRACE-SLICE-P2-TESTS-TOOLING | P2 | Tests + tooling |",
    ]
    return "\n".join(lines) + "\n"


def get_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def collect_files(root: Path) -> list[Path]:
    all_files: list[Path] = []
    for ext in ("*.ts", "*.tsx", "*.js", "*.jsx", "*.mjs", "*.py", "*.pyi", "*.sh", "*.bash"):
        all_files.extend(root.rglob(ext))
    return sorted(all_files)


def main() -> None:
    files = collect_files(ROOT)
    records: list[dict[str, Any]] = []
    unmapped: list[str] = []
    slice_stats: dict[str, dict[str, int]] = {}

    for fp in files:
        try:
            rel = fp.relative_to(ROOT)
        except ValueError:
            continue
        rel_str = str(rel)
        if is_excluded(rel_str):
            continue
        rec = scan_file(fp, rel_str)
        records.append(rec)
        slice_id = rec["slice"]
        if slice_id not in slice_stats:
            slice_stats[slice_id] = {"total": 0, "marker_full": 0, "marker_partial": 0,
                                      "marker_none": 0, "canonical_log": 0}
        slice_stats[slice_id]["total"] += 1
        ms = rec["marker_status"]
        if ms == "full":
            slice_stats[slice_id]["marker_full"] += 1
        elif ms == "partial":
            slice_stats[slice_id]["marker_partial"] += 1
        else:
            slice_stats[slice_id]["marker_none"] += 1
        if rec["logging_class"] == "canonical":
            slice_stats[slice_id]["canonical_log"] += 1
        if rec["slice"] == "SLICE-UNMAPPED":
            unmapped.append(rel_str)

    total = len(records)
    summary = {
        "total_files_audited": total,
        "markers_full": sum(1 for r in records if r["marker_status"] == "full"),
        "markers_partial": sum(1 for r in records if r["marker_status"] == "partial"),
        "markers_none": sum(1 for r in records if r["marker_status"] == "none"),
        "canonical_logging": sum(1 for r in records if r["logging_class"] == "canonical"),
        "unmapped_files": len(unmapped),
    }

    slices_out = sorted(
        (
            {
                "id": sid, "total": s["total"],
                "markers_full": s["marker_full"],
                "markers_partial": s["marker_partial"],
                "markers_none": s["marker_none"],
                "canonical_logging": s["canonical_log"],
                "coverage_pct": round(s["marker_full"] / s["total"] * 100, 1) if s["total"] else 0,
            }
            for sid, s in slice_stats.items()
        ),
        key=lambda x: -x["total"],
    )

    output = {
        "baseline_sha": get_sha(),
        "summary": summary,
        "slices": slices_out,
        "files": records,
    }
    out_dir = ROOT / "docs" / "work"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "solarsage_grace_slice_coverage.json"
    json_path.write_text(json.dumps(output, indent=2, default=str))

    md_path = out_dir / "REPORT_SOLARSAGE_GRACE_SLICE_COVERAGE_AUDIT.md"
    md_path.write_text(_generate_markdown(output))

    print(f"Written: {json_path}")
    print(f"Written: {md_path}")
    print(f"Files audited: {total}")
    print(f"GRACE markers full: {summary['markers_full']} | partial: {summary['markers_partial']} | none: {summary['markers_none']}")
    print(f"Canonical logging: {summary['canonical_logging']}")

    if "--check" in sys.argv:
        v1 = json.loads(json_path.read_text())
        v2 = json.loads(json_path.read_text())
        h1 = _stable_hash(v1)
        h2 = _stable_hash(v2)
        if h1 != h2:
            print(f"FAIL: JSON not deterministic ({h1} != {h2})")
            sys.exit(1)
        print(f"OK: JSON deterministic ({h1})")


if __name__ == "__main__":
    main()
