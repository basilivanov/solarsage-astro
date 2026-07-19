# ############################################################################
# AI_HEADER: CORE_EPHEMERIS_RUNTIME — pinned artifact identity + engine proof
# ROLE: Verifies the pinned Swiss Ephemeris artifact (manifest + sha256 +
#       inventory) and proves the calculation engine really uses Swiss files
#       (returned flags) on startup AND on every calculation, fail-closed in
#       production.
# DEPENDENCIES: swisseph, hashlib, json, pathlib, solarsage.core.config
# ############################################################################

# START_MODULE_CONTRACT: M-EPHEMERIS-RUNTIME
# purpose: Single owner of ephemeris configuration and proof for the sidecar.
#   Resolves the pinned artifact (per docs/work/.../80 ephemeris gate),
#   validates manifest bytes/hash and the exact file inventory (no extra
#   files, no symlinks, exact size+sha256 per entry), configures the engine
#   path once, and proves via returned calc flags that SWIEPH (not Moshier)
#   is used — at startup (fixed + boundary probes) and on every calculation
#   via calc_ut_checked. Production is fail-closed: missing/invalid artifact
#   or any fallback is fatal. Moshier is allowed only in explicit
#   non-production test mode and is always marked fallback=true.
# owns:
#   - apps/solarsage/solarsage/core/ephemeris_runtime.py
# inputs: filesystem artifact tree at settings.ephemeris_root.
# outputs: EphemerisIdentity for health/reporting; checked calc results.
# dependencies: solarsage.core.config settings; swisseph.
# side_effects: reads artifact files; calls swe.set_ephe_path once per verify.
# emitted_logs: none.
# invariants:
#   - Unknown/extra/missing files, symlinks (checked before resolve), wrong
#     size/hash, empty manifest.sha256, missing ephe dir all fail closed.
#   - Production (app_env == "production") never accepts Moshier.
#   - Every real calculation passes through calc_ut_checked.
# failure_policy: raises EphemerisError on any verification failure.
# END_MODULE_CONTRACT: M-EPHEMERIS-RUNTIME

# START_MODULE_MAP: M-EPHEMERIS-RUNTIME
# public_entrypoints:
#   - EphemerisError
#   - EphemerisIdentity
#   - verify_and_configure
#   - get_identity
#   - get_ephe_path
#   - calc_ut_checked
# semantic_blocks:
#   - MANIFEST_VERIFY: manifest + inventory + hash validation
#   - ENGINE_PROBE: startup fixed + boundary returned-flag proof
#   - CHECKED_CALC: per-calculation returned-flag proof
#   - IDENTITY_CACHE: one-time verified identity
# owned_tests:
#   - apps/solarsage/tests/test_ephemeris_runtime.py
# END_MODULE_MAP: M-EPHEMERIS-RUNTIME

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import swisseph as swe

from .config import settings

# START_BLOCK: CONSTANTS
PROBE_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
PROBE_JD = swe.julday(2026, 7, 8, 12.0)  # fixed deterministic probe date
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RANGE_RE = re.compile(r"^(\d{4})\s*[-–]\s*(\d{4})$")
ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class EphemerisError(RuntimeError):
    """Raised on any artifact or engine verification failure."""


@dataclass(frozen=True)
class EphemerisIdentity:
    artifact_id: str
    manifest_sha256: str
    engine: str  # "swieph" | "moshier"
    pyswisseph_version: str
    swiss_data_version: str
    ephemeris_path: str
    fallback: bool


_identity: EphemerisIdentity | None = None
# END_BLOCK: CONSTANTS


# START_BLOCK: MANIFEST_VERIFY
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_and_verify_manifest(root: Path) -> tuple[dict, str, Path]:
    # START_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME._load_and_verify_manifest
    # purpose: Validate the artifact tree at root: manifest presence and hash,
    #   exact inventory (regular non-symlink files, required size+sha256 per
    #   entry), no extra unlisted files, real ephe/ directory inside root.
    # inputs: root — artifact directory (contains ephe/, manifest.json,
    #   manifest.sha256).
    # returns: (manifest dict, manifest sha256 hex, resolved ephe dir).
    # side_effects: filesystem reads.
    # error_behavior: EphemerisError on any structural violation.
    # END_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME._load_and_verify_manifest
    if root.is_symlink():
        raise EphemerisError(f"ephemeris root must not be a symlink: {root}")
    if not root.is_dir():
        raise EphemerisError(f"ephemeris root is missing or not a directory: {root}")

    manifest_path = root / "manifest.json"
    hash_path = root / "manifest.sha256"
    for candidate in (manifest_path, hash_path):
        if candidate.is_symlink() or not candidate.is_file():
            raise EphemerisError(f"artifact file missing or not a regular file: {candidate}")

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    recorded = hash_path.read_text(encoding="utf-8").strip()
    if not recorded:
        raise EphemerisError("manifest.sha256 is empty")
    recorded = recorded.split()[0]
    if recorded != manifest_sha:
        raise EphemerisError("manifest.sha256 does not match manifest.json bytes")

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise EphemerisError(f"manifest.json is not valid JSON: {exc}") from exc

    if manifest.get("schema_version") != "solarsage-ephemeris/v1":
        raise EphemerisError("manifest schema_version must be solarsage-ephemeris/v1")
    artifact_id = manifest.get("artifact_id")
    if not isinstance(artifact_id, str) or not ARTIFACT_ID_RE.match(artifact_id):
        raise EphemerisError("manifest artifact_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    data_version = manifest.get("swiss_data_version")
    if not isinstance(data_version, str) or not data_version.strip():
        raise EphemerisError("manifest swiss_data_version must be a non-empty string")
    date_range = manifest.get("supported_date_range")
    if not isinstance(date_range, str):
        raise EphemerisError("manifest supported_date_range must be a string like '1800-2399'")
    _range_match = _RANGE_RE.match(date_range.strip())
    if not _range_match or int(_range_match.group(1)) > int(_range_match.group(2)):
        raise EphemerisError("manifest supported_date_range must be 'start-end' with start <= end")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise EphemerisError("manifest files inventory must be a non-empty list")

    ephe_raw = root / "ephe"
    if ephe_raw.is_symlink() or not ephe_raw.is_dir():
        raise EphemerisError("artifact ephe/ is missing, not a real directory, or a symlink")

    listed: set[str] = set()
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise EphemerisError("manifest inventory entries must be objects")
        rel = entry.get("path")
        size = entry.get("size")
        sha = entry.get("sha256")
        if not isinstance(rel, str) or not rel.startswith("ephe/") or ".." in Path(rel).parts:
            raise EphemerisError(f"manifest inventory path must stay inside ephe/: {rel!r}")
        if rel in seen:
            raise EphemerisError(f"manifest inventory path is duplicated: {rel}")
        if not isinstance(size, int) or size < 0:
            raise EphemerisError(f"manifest inventory size must be a non-negative int: {rel}")
        if not isinstance(sha, str) or not SHA256_RE.match(sha):
            raise EphemerisError(f"manifest inventory sha256 must be 64 lowercase hex: {rel}")
        raw = root / rel
        if raw.is_symlink():
            raise EphemerisError(f"artifact inventory file must not be a symlink: {rel}")
        if not raw.is_file():
            raise EphemerisError(f"artifact inventory file missing: {rel}")
        if raw.stat().st_size != size:
            raise EphemerisError(f"artifact inventory size mismatch: {rel}")
        if _sha256_file(raw) != sha:
            raise EphemerisError(f"artifact inventory sha256 mismatch: {rel}")
        seen.add(rel)
        listed.add(rel)

    # Reject any extra/unlisted file or symlink anywhere in the tree.
    allowed = listed | {"manifest.json", "manifest.sha256"}
    for found in sorted(root.rglob("*")):
        if found.is_symlink():
            raise EphemerisError(f"unexpected symlink inside artifact root: {found.relative_to(root)}")
        if found.is_file():
            rel_found = found.relative_to(root).as_posix()
            if rel_found not in allowed:
                raise EphemerisError(f"extra unlisted file inside artifact root: {rel_found}")

    return manifest, manifest_sha, ephe_raw.resolve()
# END_BLOCK: MANIFEST_VERIFY


# START_BLOCK: ENGINE_PROBE
def _retflag(result) -> int:
    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], int):
        return result[1]
    raise EphemerisError("calc_ut returned an unexpected shape (no retflag)")


def _probe_one(jd: float, body: int, name: str) -> None:
    retflag = _retflag(swe.calc_ut(jd, body, PROBE_FLAGS))
    if not (retflag & swe.FLG_SWIEPH):
        raise EphemerisError(
            f"engine probe for {name} did not return FLG_SWIEPH (retflag={retflag}) — "
            "Moshier/fallback is not acceptable"
        )


def _probe_engine(ephe_dir: Path, date_range: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME._probe_engine
    # purpose: Configure the engine path once and prove via returned flags
    #   that SWIEPH serves fixed-date Sun/Moon plus boundary dates of the
    #   declared supported range.
    # inputs: ephe_dir — verified data directory; date_range — '1800-2399'.
    # returns: None on proven SWIEPH.
    # side_effects: swe.set_ephe_path + probe calc_ut calls.
    # error_behavior: EphemerisError when any returned flag lacks FLG_SWIEPH.
    # END_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME._probe_engine
    swe.set_ephe_path(str(ephe_dir))
    _probe_one(PROBE_JD, swe.SUN, "Sun")
    _probe_one(PROBE_JD, swe.MOON, "Moon")
    match = _RANGE_RE.match(date_range.strip())
    year_start, year_end = int(match.group(1)), int(match.group(2))
    _probe_one(swe.julday(year_start, 1, 1, 12.0), swe.SUN, f"Sun@range-start {year_start}")
    _probe_one(swe.julday(year_end, 12, 31, 12.0), swe.SUN, f"Sun@range-end {year_end}")


def _moshier_allowed() -> bool:
    return settings.ephemeris_allow_moshier and settings.app_env != "production"
# END_BLOCK: ENGINE_PROBE


# START_BLOCK: IDENTITY_CACHE
def verify_and_configure() -> EphemerisIdentity:
    # START_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.verify_and_configure
    # purpose: One-shot verification + configuration used by the startup gate
    #   and lazily by calculations. Production is fail-closed on any
    #   artifact/engine problem; Moshier is returned (marked) only in
    #   explicit non-production test mode.
    # inputs: none (settings + filesystem).
    # returns: verified EphemerisIdentity (cached after first success).
    # side_effects: artifact reads; swe.set_ephe_path via probe.
    # error_behavior: EphemerisError on any failure in production mode;
    #   in explicit moshier test mode returns engine="moshier" identity.
    # END_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.verify_and_configure
    global _identity
    if _identity is not None:
        return _identity

    root = Path(settings.ephemeris_root)
    try:
        manifest, manifest_sha, ephe_dir = _load_and_verify_manifest(root)
        _probe_engine(ephe_dir, manifest["supported_date_range"])
    except EphemerisError:
        if _moshier_allowed():
            swe.set_ephe_path(str(Path(settings.ephemeris_path)))
            _identity = EphemerisIdentity(
                artifact_id="moshier-only",
                manifest_sha256="",
                engine="moshier",
                pyswisseph_version=str(getattr(swe, "__version__", "unknown")),
                swiss_data_version="none",
                ephemeris_path=str(Path(settings.ephemeris_path)),
                fallback=True,
            )
            return _identity
        raise

    _identity = EphemerisIdentity(
        artifact_id=manifest["artifact_id"],
        manifest_sha256=manifest_sha,
        engine="swieph",
        pyswisseph_version=str(getattr(swe, "__version__", "unknown")),
        swiss_data_version=str(manifest["swiss_data_version"]),
        ephemeris_path=str(ephe_dir),
        fallback=False,
    )
    return _identity


def get_identity() -> EphemerisIdentity:
    return verify_and_configure()


def get_ephe_path() -> str:
    # START_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.get_ephe_path
    # purpose: Single accessor for the configured ephemeris data directory so
    #   no module hardcodes its own path.
    # inputs: none.
    # returns: verified ephemeris directory string.
    # side_effects: triggers verification on first call.
    # error_behavior: EphemerisError on verification failure.
    # END_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.get_ephe_path
    return verify_and_configure().ephemeris_path
# END_BLOCK: IDENTITY_CACHE


# START_BLOCK: CHECKED_CALC
def calc_ut_checked(jd: float, body: int, flags: int):
    # START_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.calc_ut_checked
    # purpose: The ONLY allowed way for sidecar code to run a real ephemeris
    #   calculation: ensures the verified configuration, then checks the
    #   returned flag of every call. Production requires FLG_SWIEPH on every
    #   calculation; explicit moshier test mode passes and stays marked
    #   (identity.fallback is true).
    # inputs: jd — Julian day; body — swe body id; flags — swe iflag.
    # returns: raw swe.calc_ut result (positions, retflag).
    # side_effects: one swe.calc_ut call after verification.
    # error_behavior: EphemerisError when the returned flag lacks FLG_SWIEPH
    #   in production mode.
    # END_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.calc_ut_checked
    identity = verify_and_configure()
    result = swe.calc_ut(jd, body, flags)
    if identity.engine != "moshier" and not (_retflag(result) & swe.FLG_SWIEPH):
        raise EphemerisError(
            f"calc_ut returned retflag={_retflag(result)} without FLG_SWIEPH — "
            "fallback during calculation is fatal in production"
        )
    return result


def cross_ut_checked(fn, *args):
    # START_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.cross_ut_checked
    # purpose: Runtime-mediated path for swe crossing finders
    #   (solcross_ut/mooncross_ut). These functions return only jdcross and
    #   expose NO retflag, so per-call flag proof is impossible; the engine
    #   guarantee comes from the verified artifact + startup probes, which
    #   this wrapper enforces before every crossing call.
    # inputs: fn — swe crossing function; *args — its arguments.
    # returns: raw crossing result (jdcross float).
    # side_effects: verification on first call, then one crossing call.
    # error_behavior: EphemerisError when verification fails (production).
    # END_FUNCTION_CONTRACT: F-M-EPHEMERIS-RUNTIME.cross_ut_checked
    verify_and_configure()
    return fn(*args)


def _reset_identity_for_tests() -> None:
    global _identity
    _identity = None
# END_BLOCK: CHECKED_CALC
