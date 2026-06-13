#!/usr/bin/env python3
# START_MODULE_CONTRACT
# purpose: Tooling script — scripts/check_frontmatter.py
# owns:
#   - scripts/check_frontmatter.py
# inputs: Mocks, fixtures
# outputs: Assertions
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
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
# AI_HEADER: TOOL_DOCS_FRONTMATTER_CHECK
# ROLE: Static gate — every doc/packet must declare YAML front-matter with
#       id / status / wave / last_review. Stops silent doc drift.
# DEPENDENCIES: stdlib only (pathlib, re, sys, datetime)
# GRACE_ANCHORS: [CONFIG, PARSE, VALIDATE, REPORT]
# ############################################################################
"""
Front-matter validator for docs/ and grace/packets/.

Required YAML keys (between leading `---` fences):

  id            non-empty kebab/word identifier (unique per scope)
  status        one of: active | superseded | planned | stale | archived
  wave          W-<x.y> (or "none" if not bound to a wave)
  last_review   YYYY-MM-DD

Optional:
  supersedes    id of the document this one replaces (required if
                status == superseded)
  source_of_truth  path or url pointing to the canonical artifact

Stale policy:
  status == active AND last_review older than STALE_DAYS  →  FAIL
  status == planned                                       →  warning only

Exit 0 on success, 1 on any violation.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES: tuple[Path, ...] = (
    ROOT / "docs",
    ROOT / "grace" / "packets",
)
EXCLUDE_NAMES: frozenset[str] = frozenset({"MANIFEST.md"})

ALLOWED_STATUS: frozenset[str] = frozenset(
    {"active", "superseded", "planned", "stale", "archived"}
)
REQUIRED_KEYS: tuple[str, ...] = ("id", "status", "wave", "last_review")
WAVE_RE = re.compile(r"^(W-[A-Z0-9.\-]+|none)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STALE_DAYS = 120


# ---------------------------------------------------------------------------
# START_BLOCK: PARSE
# ---------------------------------------------------------------------------


@dataclass
class FrontMatter:
    path: Path
    data: dict[str, str]


def extract_frontmatter(path: Path) -> FrontMatter | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    body: list[str] = []
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        body.append(raw)
    else:
        return None
    data: dict[str, str] = {}
    for raw in body:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return FrontMatter(path=path, data=data)


# END_BLOCK: PARSE


# ---------------------------------------------------------------------------
# START_BLOCK: VALIDATE
# ---------------------------------------------------------------------------


def validate(fm: FrontMatter, today: date) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in fm.data or not fm.data[key]:
            errors.append(f"missing required key: {key}")
    if errors:
        return errors

    status = fm.data["status"]
    if status not in ALLOWED_STATUS:
        errors.append(
            f"status '{status}' not in {sorted(ALLOWED_STATUS)}"
        )

    wave = fm.data["wave"]
    if not WAVE_RE.match(wave):
        errors.append(
            f"wave '{wave}' must match W-<x.y> (e.g. W-1.1B) or be 'none'"
        )

    last_review = fm.data["last_review"]
    if not DATE_RE.match(last_review):
        errors.append(f"last_review '{last_review}' must be YYYY-MM-DD")
        return errors
    parsed = datetime.strptime(last_review, "%Y-%m-%d").date()
    age_days = (today - parsed).days
    if status == "active" and age_days > STALE_DAYS:
        errors.append(
            f"status=active but last_review is {age_days}d old "
            f"(> {STALE_DAYS}d). Re-review or move to status=stale."
        )

    if status == "superseded" and not fm.data.get("supersedes"):
        errors.append(
            "status=superseded requires a 'supersedes: <id>' field"
        )

    return errors


# END_BLOCK: VALIDATE


# ---------------------------------------------------------------------------
# START_BLOCK: REPORT
# ---------------------------------------------------------------------------


def main() -> int:
    today = date.today()
    failed = 0
    checked = 0
    for scope in SCOPES:
        if not scope.exists():
            continue
        for path in sorted(scope.glob("*.md")):
            if path.name in EXCLUDE_NAMES:
                continue
            checked += 1
            fm = extract_frontmatter(path)
            if fm is None:
                failed += 1
                rel = path.relative_to(ROOT)
                print(f"FAIL {rel}: missing YAML front-matter block")
                continue
            errs = validate(fm, today)
            if errs:
                failed += 1
                rel = path.relative_to(ROOT)
                for e in errs:
                    print(f"FAIL {rel}: {e}")

    if failed:
        print(f"\nfront-matter gate: FAIL ({failed}/{checked} files)")
        return 1
    print(f"front-matter gate: PASS ({checked} files)")
    return 0


# END_BLOCK: REPORT

if __name__ == "__main__":
    sys.exit(main())
EXCLUDE_NAMES: frozenset[str] = frozenset({"MANIFEST.md"})

ALLOWED_STATUS: frozenset[str] = frozenset(
    {"active", "superseded", "planned", "stale", "archived"}
)
REQUIRED_KEYS: tuple[str, ...] = ("id", "status", "wave", "last_review")
WAVE_RE = re.compile(r"^(W-[A-Z0-9.\-]+|none)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STALE_DAYS = 120


# ---------------------------------------------------------------------------
# START_BLOCK: PARSE
# ---------------------------------------------------------------------------


@dataclass
class FrontMatter:
    path: Path
    data: dict[str, str]


def extract_frontmatter(path: Path) -> FrontMatter | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    body: list[str] = []
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        body.append(raw)
    else:
        return None
    data: dict[str, str] = {}
    for raw in body:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return FrontMatter(path=path, data=data)


# END_BLOCK: PARSE


# ---------------------------------------------------------------------------
# START_BLOCK: VALIDATE
# ---------------------------------------------------------------------------


def validate(fm: FrontMatter, today: date) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in fm.data or not fm.data[key]:
            errors.append(f"missing required key: {key}")
    if errors:
        return errors

    status = fm.data["status"]
    if status not in ALLOWED_STATUS:
        errors.append(
            f"status '{status}' not in {sorted(ALLOWED_STATUS)}"
        )

    wave = fm.data["wave"]
    if not WAVE_RE.match(wave):
        errors.append(
            f"wave '{wave}' must match W-<x.y> (e.g. W-1.1B) or be 'none'"
        )

    last_review = fm.data["last_review"]
    if not DATE_RE.match(last_review):
        errors.append(f"last_review '{last_review}' must be YYYY-MM-DD")
        return errors
    parsed = datetime.strptime(last_review, "%Y-%m-%d").date()
    age_days = (today - parsed).days
    if status == "active" and age_days > STALE_DAYS:
        errors.append(
            f"status=active but last_review is {age_days}d old "
            f"(> {STALE_DAYS}d). Re-review or move to status=stale."
        )

    if status == "superseded" and not fm.data.get("supersedes"):
        errors.append(
            "status=superseded requires a 'supersedes: <id>' field"
        )

    return errors


# END_BLOCK: VALIDATE


# ---------------------------------------------------------------------------
# START_BLOCK: REPORT
# ---------------------------------------------------------------------------


def main() -> int:
    today = date.today()
    failed = 0
    checked = 0
    for scope in SCOPES:
        if not scope.exists():
            continue
        for path in sorted(scope.glob("*.md")):
            if path.name in EXCLUDE_NAMES:
                continue
            checked += 1
            fm = extract_frontmatter(path)
            if fm is None:
                failed += 1
                rel = path.relative_to(ROOT)
                print(f"FAIL {rel}: missing YAML front-matter block")
                continue
            errs = validate(fm, today)
            if errs:
                failed += 1
                rel = path.relative_to(ROOT)
                for e in errs:
                    print(f"FAIL {rel}: {e}")

    if failed:
        print(f"\nfront-matter gate: FAIL ({failed}/{checked} files)")
        return 1
    print(f"front-matter gate: PASS ({checked} files)")
    return 0


# END_BLOCK: REPORT


if __name__ == "__main__":
    sys.exit(main())
