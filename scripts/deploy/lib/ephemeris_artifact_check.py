#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: LIB_EPHEMERIS_ARTIFACT_CHECK — deploy-side artifact acceptance
# ROLE: Standalone manifest/inventory verification for the ephemeris
#       installer (independent acceptance layer; no sidecar package import).
# DEPENDENCIES: python3.12 stdlib only
# ############################################################################

# START_MODULE_CONTRACT: M-LIB-EPHEMERIS-ARTIFACT-CHECK
# purpose: Verify a staged ephemeris artifact tree: manifest presence and
#   hash, exact inventory (regular non-symlink files, required size + 64-hex
#   sha256 per entry), no extra unlisted files, real ephe/ directory, safe
#   relative paths. Mirrors the runtime rules intentionally (two-layer
#   verification), exits non-zero with a precise reason on any violation.
# owns:
#   - scripts/deploy/lib/ephemeris_artifact_check.py
# inputs: argv[1] — artifact root path.
# outputs: stdout "OK <artifact_id>" on success; stderr reason + exit 78.
# dependencies: none.
# side_effects: filesystem reads only.
# emitted_logs: none.
# invariants:
#   - no writes, no downloads, no fabrication of artifact bytes.
# failure_policy: exit 78 on any structural/hash violation.
# END_MODULE_CONTRACT: M-LIB-EPHEMERIS-ARTIFACT-CHECK

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RANGE_RE = re.compile(r"^(\d{4})\s*[-–]\s*(\d{4})$")
ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def fail(reason: str) -> None:
    sys.stderr.write(f"Error: {reason}\n")
    sys.exit(78)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: ephemeris_artifact_check.py <artifact-root>")
    root = Path(sys.argv[1])
    if root.is_symlink():
        fail(f"artifact root must not be a symlink: {root}")
    if not root.is_dir():
        fail(f"artifact root is missing or not a directory: {root}")

    manifest_path = root / "manifest.json"
    hash_path = root / "manifest.sha256"
    for candidate in (manifest_path, hash_path):
        if candidate.is_symlink() or not candidate.is_file():
            fail(f"artifact file missing or not a regular file: {candidate}")

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    recorded = hash_path.read_text(encoding="utf-8").strip()
    if not recorded:
        fail("manifest.sha256 is empty")
    recorded = recorded.split()[0]
    if recorded != manifest_sha:
        fail("manifest.sha256 does not match manifest.json bytes")

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"manifest.json is not valid JSON: {exc}")

    if manifest.get("schema_version") != "solarsage-ephemeris/v1":
        fail("manifest schema_version must be solarsage-ephemeris/v1")
    artifact_id = manifest.get("artifact_id")
    if not isinstance(artifact_id, str) or not ARTIFACT_ID_RE.match(artifact_id):
        fail("manifest artifact_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    data_version = manifest.get("swiss_data_version")
    if not isinstance(data_version, str) or not data_version.strip():
        fail("manifest swiss_data_version must be a non-empty string")
    date_range = manifest.get("supported_date_range")
    if not isinstance(date_range, str):
        fail("manifest supported_date_range must be a string like '1800-2399'")
    range_match = RANGE_RE.match(date_range.strip())
    if not range_match or int(range_match.group(1)) > int(range_match.group(2)):
        fail("manifest supported_date_range must be 'start-end' with start <= end")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        fail("manifest files inventory must be a non-empty list")

    ephe_raw = root / "ephe"
    if ephe_raw.is_symlink() or not ephe_raw.is_dir():
        fail("artifact ephe/ is missing, not a real directory, or a symlink")

    listed: set[str] = set()
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            fail("manifest inventory entries must be objects")
        rel = entry.get("path")
        size = entry.get("size")
        sha = entry.get("sha256")
        if not isinstance(rel, str) or not rel.startswith("ephe/") or ".." in Path(rel).parts:
            fail(f"manifest inventory path must stay inside ephe/: {rel!r}")
        if rel in seen:
            fail(f"manifest inventory path is duplicated: {rel}")
        if not isinstance(size, int) or size < 0:
            fail(f"manifest inventory size must be a non-negative int: {rel}")
        if not isinstance(sha, str) or not SHA256_RE.match(sha):
            fail(f"manifest inventory sha256 must be 64 lowercase hex: {rel}")
        raw = root / rel
        if raw.is_symlink():
            fail(f"artifact inventory file must not be a symlink: {rel}")
        if not raw.is_file():
            fail(f"artifact inventory file missing: {rel}")
        if raw.stat().st_size != size:
            fail(f"artifact inventory size mismatch: {rel}")
        if sha256_file(raw) != sha:
            fail(f"artifact inventory sha256 mismatch: {rel}")
        seen.add(rel)
        listed.add(rel)

    allowed = listed | {"manifest.json", "manifest.sha256"}
    for found in sorted(root.rglob("*")):
        if found.is_symlink():
            fail(f"unexpected symlink inside artifact root: {found.relative_to(root)}")
        if found.is_file():
            rel_found = found.relative_to(root).as_posix()
            if rel_found not in allowed:
                fail(f"extra unlisted file inside artifact root: {rel_found}")

    print(f"OK {artifact_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
