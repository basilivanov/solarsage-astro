#!/usr/bin/env python3
# START_MODULE_CONTRACT
# purpose: Tooling script — scripts/check_docs_manifest.py
# owns:
#   - scripts/check_docs_manifest.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
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
# AI_HEADER: TOOL_DOCS_MANIFEST_CHECK
# ROLE: Static gate — verifies docs/MANIFEST.md mirrors the actual contents
#       of docs/ and grace/packets/.
# DEPENDENCIES: stdlib only (pathlib, re, sys)
# GRACE_ANCHORS: [DISCOVERY, PARSE_MANIFEST, COMPARE, REPORT]
# ############################################################################
"""
docs/MANIFEST.md sync gate.

Goal: stop docs from drifting away from the manifest. Every *.md file under
docs/ (except MANIFEST.md itself) MUST be listed in docs/MANIFEST.md. Every
W-*.md file under grace/packets/ MUST be listed in grace/MANIFEST.md (or the
root MANIFEST.md packets section).

Exit code 0 on success, 1 on any drift.

Usage:
  python scripts/check_docs_manifest.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
PACKETS_DIR = ROOT / "grace" / "packets"
DOCS_MANIFEST = DOCS_DIR / "MANIFEST.md"
GRACE_README = ROOT / "grace" / "README.md"

# ---------------------------------------------------------------------------
# START_BLOCK: DISCOVERY
# ---------------------------------------------------------------------------


def discover_docs() -> set[str]:
    """Return every *.md file in docs/ except MANIFEST.md, by basename."""
    return {
        p.name
        for p in DOCS_DIR.glob("*.md")
        if p.name != "MANIFEST.md"
    }


def discover_packets() -> set[str]:
    return {p.name for p in PACKETS_DIR.glob("*.md")}


# END_BLOCK: DISCOVERY


# ---------------------------------------------------------------------------
# START_BLOCK: PARSE_MANIFEST
# ---------------------------------------------------------------------------

# Matches "- `<name>.md`" or "- <name>.md" inside a markdown bullet list.
LIST_ITEM_RE = re.compile(r"^\s*[-*]\s*`?([^`\s]+\.md)`?")


def listed_in(manifest_path: Path, allow_paths: bool = False) -> set[str]:
    """Parse markdown bullets that look like file references.

    By default returns only basenames of bullets that have NO path separator
    (so cross-references like `- grace/README.md` are ignored — they are
    pointers, not declarations).

    With allow_paths=True, also accepts bullets like `packets/W-1.1.md` and
    returns the basename — used for grace/README.md which lists packets via
    a relative `packets/` prefix.
    """
    if not manifest_path.exists():
        return set()
    out: set[str] = set()
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        m = LIST_ITEM_RE.match(raw)
        if not m:
            continue
        entry = m.group(1)
        if "/" in entry and not allow_paths:
            continue
        out.add(entry.split("/")[-1])
    return out


# END_BLOCK: PARSE_MANIFEST


# ---------------------------------------------------------------------------
# START_BLOCK: COMPARE / REPORT
# ---------------------------------------------------------------------------


def main() -> int:
    docs_actual = discover_docs()
    docs_listed = listed_in(DOCS_MANIFEST)
    packets_actual = discover_packets()
    packets_listed = listed_in(GRACE_README, allow_paths=True) | listed_in(
        ROOT / "MANIFEST.md", allow_paths=True
    )

    failed = False

    missing_from_manifest = sorted(docs_actual - docs_listed)
    extra_in_manifest = sorted(docs_listed - docs_actual)
    if missing_from_manifest:
        failed = True
        print(
            "FAIL docs/MANIFEST.md is missing entries for:\n  - "
            + "\n  - ".join(missing_from_manifest)
        )
    if extra_in_manifest:
        failed = True
        print(
            "FAIL docs/MANIFEST.md lists files that no longer exist:\n  - "
            + "\n  - ".join(extra_in_manifest)
        )

    # Packets: warn-only on missing manifest entries (grace/README.md is the
    # human index, not a strict mirror). Promote to FAIL once that file
    # adopts the same flat-list convention.
    missing_packets = sorted(packets_actual - packets_listed)
    if missing_packets:
        print(
            "WARN grace packets not referenced from grace/README.md or "
            "MANIFEST.md:\n  - " + "\n  - ".join(missing_packets)
        )

    if failed:
        return 1
    print(
        f"OK docs manifest in sync ({len(docs_actual)} docs, "
        f"{len(packets_actual)} packets)"
    )
    return 0


# END_BLOCK: COMPARE / REPORT


if __name__ == "__main__":
    sys.exit(main())
