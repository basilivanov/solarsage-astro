#!/usr/bin/env python3
"""GRACE slice coverage audit — inventory markers, logs, slices per file.

Usage:
    python3 scripts/grace/coverage_audit.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXCLUDE_DIRS = frozenset({
    "node_modules", ".next", ".venv", "venv", "__pycache__", ".git",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".pytest_cache",
})
EXCLUDE_PREFIX = ("components/ui/", "alembic/", "migrations/")

# Slice classification by path prefix
SLICE_MAP: list[tuple[tuple[str, ...], str]] = [
    (("app/(grace)/", "components/today/", "lib/today.ts", "lib/calendar.ts"), "SLICE-TODAY-CALENDAR"),
    (("components/today/tab-bar.tsx", "components/app-shell.tsx"), "SLICE-SHELL-NAVIGATION"),
    (("components/readings/", "app/(grace)/readings/"), "SLICE-HORARY-READINGS"),
    (("components/profile/", "components/onboarding/", "app/(grace)/profile/", "app/(grace)/onboarding/"), "SLICE-PROFILE-ONBOARDING"),
    (("lib/api/", "lib/access.ts", "lib/profile.ts", "lib/chat.ts", "lib/cities.ts"), "SLICE-FRONTEND-API-FACADES"),
    (("packages/contracts/",), "SLICE-CONTRACTS"),
    (("apps/api/app/", "apps/api/schemas/"), "SLICE-BACKEND-API-ROUTERS"),
    (("apps/api/core/", "apps/api/services/"), "SLICE-BACKEND-SERVICES"),
    (("apps/api/db/",), "SLICE-DB-MODELS-MIGRATIONS"),
    (("apps/solarsage/",), "SLICE-SIDECAR-CALCULATION"),
    (("apps/api/scoring/", "apps/api/normalization/", "apps/api/semantic/"), "SLICE-SCORING-SEMANTIC-LLM"),
    (("lib/grace/",), "SLICE-LOGGING-SPINE"),
    (("__tests__/", "apps/api/tests/", "apps/solarsage/tests/"), "SLICE-TESTS"),
    (("scripts/",), "SLICE-GUARDRAILS-TOOLING"),
    (("grace/orchestrator/", "grace/"), "SLICE-ORCHESTRATOR-ADAPTER"),
    (("components/calendar/", "components/chat/"), "SLICE-OTHER-COMPONENTS"),
    (("components/monetization/", "components/locked-", "components/debug-", "components/correlation-"), "SLICE-OTHER-COMPONENTS"),
    (("app/api/", "app/debug-", "app/reset/", "app/test-"), "SLICE-OTHER-APP"),
]

# Marker detection
AI_HEADER_RE = re.compile(r"(?://|#|/\*|\*)\s*AI_HEADER\s*:\s*\S+", re.MULTILINE)
MODULE_CONTRACT_START_RE = re.compile(r"(?://|#)\s*START_MODULE_CONTRACT(?:\s*:\s*\S+)?")
MODULE_CONTRACT_END_RE = re.compile(r"(?://|#)\s*END_MODULE_CONTRACT(?:\s*:\s*\S+)?")
MODULE_MAP_START_RE = re.compile(r"(?://|#)\s*START_MODULE_MAP(?:\s*:\s*\S+)?")
MODULE_MAP_END_RE = re.compile(r"(?://|#)\s*END_MODULE_MAP(?:\s*:\s*\S+)?")
BLOCK_START_RE = re.compile(r"(?://|#)\s*START_BLOCK:(.*)")
BLOCK_END_RE = re.compile(r"(?://|#)\s*END_BLOCK:(.*)")

# Logging detection
LOG_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("grace_log", re.compile(r"from.*lib/grace/log.*import|GraceLogger"), "canonical"),
    ("structlog", re.compile(r"structlog|get_logger"), "canonical"),
    ("logging", re.compile(r"logging\.getLogger|import logging"), "acceptable but undocumented"),
    ("console", re.compile(r"console\.(log|warn|error)"), "non-canonical"),
    ("print", re.compile(r'print\s*\('), "non-canonical"),
    ("logEvent", re.compile(r"logEvent|log_event|log_event\b"), "acceptable but undocumented"),
    ("logger_var", re.compile(r"\blogger\b.*=.*getLogger|\blogger\b\s*="), "acceptable but undocumented"),
    ("track", re.compile(r"\btrack\b|emitEvent"), "acceptable but undocumented"),
]


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


def scan_file(full_path: Path, rel_path: str) -> dict[str, Any]:
    text = full_path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    ext = full_path.suffix
    lang = "python" if ext in (".py", ".pyi") else \
           "typescript" if ext in (".ts", ".tsx") else \
           "javascript" if ext in (".js", ".jsx", ".mjs") else \
           "shell" if ext in (".sh", ".bash") else \
           "other"

    ai_header = bool(AI_HEADER_RE.search(text))
    mc_start = len(MODULE_CONTRACT_START_RE.findall(text))
    mc_end = len(MODULE_CONTRACT_END_RE.findall(text))
    mm_start = len(MODULE_MAP_START_RE.findall(text))
    mm_end = len(MODULE_MAP_END_RE.findall(text))
    blk_start = len(BLOCK_START_RE.findall(text))
    blk_end = len(BLOCK_END_RE.findall(text))

    marker_status = "none"
    if ai_header and mc_start and mc_end:
        marker_status = "full"
    elif ai_header or mc_start:
        marker_status = "partial"

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

    slice_id = classify_slice(rel_path)
    lines_count = len(lines)

    return {
        "path": rel_path,
        "language": lang,
        "slice": slice_id,
        "lines": lines_count,
        "has_AI_HEADER": ai_header,
        "has_MODULE_CONTRACT_START": mc_start > 0,
        "has_MODULE_CONTRACT_END": mc_end > 0,
        "has_MODULE_MAP_START": mm_start > 0,
        "has_MODULE_MAP_END": mm_end > 0,
        "BLOCK_START_count": blk_start,
        "BLOCK_END_count": blk_end,
        "START_BLOCK_names": [m.strip() for m in BLOCK_START_RE.findall(text) if m.strip()],
        "marker_status": marker_status,
        "logging_patterns": log_found,
        "logging_class": log_class,
    }


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
        s = rec["marker_status"]
        if s == "full":
            slice_stats[slice_id]["marker_full"] += 1
        elif s == "partial":
            slice_stats[slice_id]["marker_partial"] += 1
        else:
            slice_stats[slice_id]["marker_none"] += 1

        if rec["logging_class"] == "canonical":
            slice_stats[slice_id]["canonical_log"] += 1

        if rec["slice"] == "SLICE-UNMAPPED":
            unmapped.append(rel_str)

    total = len(records)
    marker_full = sum(1 for r in records if r["marker_status"] == "full")
    marker_partial = sum(1 for r in records if r["marker_status"] == "partial")
    marker_none = total - marker_full - marker_partial
    canonical_log = sum(1 for r in records if r["logging_class"] == "canonical")

    output = {
        "baseline_sha": _get_sha(),
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_files_audited": total,
            "markers_full": marker_full,
            "markers_partial": marker_partial,
            "markers_none": marker_none,
            "canonical_logging": canonical_log,
            "unmapped_files": len(unmapped),
        },
        "slices": [
            {
                "id": sid,
                "total": s["total"],
                "markers_full": s["marker_full"],
                "markers_partial": s["marker_partial"],
                "markers_none": s["marker_none"],
                "canonical_logging": s["canonical_log"],
                "coverage_pct": round(s["marker_full"] / s["total"] * 100, 1) if s["total"] else 0,
            }
            for sid, s in sorted(slice_stats.items())
        ],
        "files": records,
    }

    out_dir = ROOT / "docs" / "work"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "solarsage_grace_slice_coverage.json"
    json_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"Written: {json_path}")
    print(f"Files audited: {total}")
    print(f"GRACE markers full: {marker_full} | partial: {marker_partial} | none: {marker_none}")
    print(f"Canonical logging: {canonical_log}")
    print(f"Unmapped files: {len(unmapped)}")
    if unmapped:
        print("\nTop unmapped directories:")
        dirs = {}
        for p in unmapped:
            d = "/".join(p.split("/")[:2])
            dirs[d] = dirs.get(d, 0) + 1
        for d, c in sorted(dirs.items(), key=lambda x: -x[1])[:10]:
            print(f"  {d}: {c} files")


def _get_sha() -> str:
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
