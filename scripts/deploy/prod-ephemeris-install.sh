#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: PROD_EPHEMERIS_INSTALL — fail-closed ephemeris artifact installer
# ROLE: Root-only check/apply installer for the pinned Swiss Ephemeris
#       artifact per docs/work/.../80 (offline installer design).
# DEPENDENCIES: bash, python3.12, scripts/deploy/lib/ephemeris_artifact_check.py
# ############################################################################

# START_MODULE_CONTRACT: M-PROD-EPHEMERIS-INSTALL
# purpose: Install an operator-staged ephemeris artifact bundle into the
#   canonical immutable layout /opt/solarsage-ephemeris/releases/<id> with an
#   atomic `current` pointer, preserving the previous release for rollback.
#   Never downloads, never fabricates artifact bytes, never overwrites an
#   existing release, and a failed apply leaves `current` byte-unchanged.
# owns:
#   - scripts/deploy/prod-ephemeris-install.sh
# inputs:
#   - --check : verify the current installation (layout + manifest + oracle)
#   - --apply <staged-path> : validate, prove, then atomically install
# outputs: exit 0 on proven success, non-zero otherwise.
# dependencies:
#   - scripts/deploy/lib/ephemeris_artifact_check.py (manifest verification)
#   - offline engine oracle via EPHE_ORACLE_CMD (default python3.12 probe)
# side_effects:
#   - --apply: creates root-owned release dir + flips `current` symlink
# emitted_logs: none.
# invariants:
#   - no implicit downloads, no fabricated artifact files
#   - immutable releases: an existing release id is never overwritten
#   - `current` flips only after full proof; previous pointer preserved
# failure_policy: fail closed (78) on any validation, oracle or IO error.
# END_MODULE_CONTRACT: M-PROD-EPHEMERIS-INSTALL

# START_MODULE_MAP: M-PROD-EPHEMERIS-INSTALL
# public_entrypoints:
#   - main
# semantic_blocks:
#   - EPHE_CHECK: verify current installation state
#   - EPHE_APPLY: staged validation, oracle proof, atomic install
# owned_tests:
#   - scripts/deploy/tests/test-prod-ephemeris-install.sh
# END_MODULE_MAP: M-PROD-EPHEMERIS-INSTALL

set -euo pipefail
umask 022

EPHE_ROOT="${EPHE_ROOT:-/opt/solarsage-ephemeris}"
RELEASES_DIR="$EPHE_ROOT/releases"
CURRENT_LINK="$EPHE_ROOT/current"
PREVIOUS_FILE="$EPHE_ROOT/previous"
CHECK_PY="${EPHE_CHECK_PY:-/usr/bin/python3.12}"
CHECK_SCRIPT="$(cd "$(dirname "$0")" && pwd)/lib/ephemeris_artifact_check.py"
ORACLE_CMD="${EPHE_ORACLE_CMD:-}"
ORACLE_PYTHON="${EPHE_ORACLE_PYTHON:-/opt/solarsage-astro/apps/solarsage/venv/bin/python}"

fail() {
  echo "Error: $*" >&2
  exit 78
}

usage() {
  echo "Usage: $0 --check" >&2
  echo "       $0 --apply <staged-artifact-path>" >&2
  exit 78
}

# START_BLOCK: EPHE_ORACLE
run_oracle() {
  # START_FUNCTION_CONTRACT: F-M-PROD-EPHEMERIS-INSTALL.run_oracle
  # purpose: Offline engine oracle against a staged/installed ephe dir.
  #   Default probe uses pyswisseph with FLG_SWIEPH|FLG_SPEED and requires
  #   the returned flag to contain FLG_SWIEPH (MOSEPH/JPL fallback rejected).
  # inputs: $1 — ephe data directory.
  # returns: 0 on proven SWIEPH; non-zero otherwise.
  # side_effects: one python probe process (no network).
  # error_behavior: returns non-zero on fallback or probe failure.
  # END_FUNCTION_CONTRACT: F-M-PROD-EPHEMERIS-INSTALL.run_oracle
  local ephe_dir="$1"
  if [ -n "$ORACLE_CMD" ]; then
    EPHE_ORACLE_EPHE_DIR="$ephe_dir" "$ORACLE_CMD"
    return $?
  fi
  [ -x "$ORACLE_PYTHON" ] || fail "oracle python is missing or not executable: $ORACLE_PYTHON (set EPHE_ORACLE_PYTHON)"
  EPHE_ORACLE_EPHE_DIR="$ephe_dir" "$ORACLE_PYTHON" - <<'PYEOF'
import os, sys
try:
    import swisseph as swe
except ImportError:
    sys.stderr.write("Error: pyswisseph not available for the oracle probe\n")
    sys.exit(78)
swe.set_ephe_path(os.environ["EPHE_ORACLE_EPHE_DIR"])
flags = swe.FLG_SWIEPH | swe.FLG_SPEED
jd = swe.julday(2026, 7, 8, 12.0)
for body, name in ((swe.SUN, "Sun"), (swe.MOON, "Moon")):
    result = swe.calc_ut(jd, body, flags)
    retflag = result[1] if isinstance(result, tuple) and len(result) > 1 else None
    if retflag is None or not (retflag & swe.FLG_SWIEPH):
        sys.stderr.write(f"Error: oracle probe for {name} returned retflag={retflag} (fallback)\n")
        sys.exit(78)
sys.exit(0)
PYEOF
}
# END_BLOCK: EPHE_ORACLE

# START_BLOCK: EPHE_CHECK
check_cmd() {
  [ -d "$RELEASES_DIR" ] || fail "releases directory is missing: $RELEASES_DIR"
  [ -L "$CURRENT_LINK" ] || fail "current pointer is missing or not a symlink: $CURRENT_LINK"
  local target resolved releases_resolved
  target=$(readlink "$CURRENT_LINK")
  [ -n "$target" ] || fail "current pointer target is empty"
  # Canonicalize: the resolved target must really live inside releases/.
  resolved=$(realpath -m -- "$CURRENT_LINK")
  releases_resolved=$(realpath -m -- "$RELEASES_DIR")
  case "$resolved" in
    "$releases_resolved"/*) ;;
    *) fail "current pointer resolves outside the releases directory: $resolved" ;;
  esac
  [ "$resolved" != "$releases_resolved" ] || fail "current points at the releases root itself"
  [ -d "$resolved" ] || fail "current target is not a directory: $resolved"
  "$CHECK_PY" "$CHECK_SCRIPT" "$resolved" >/dev/null
  run_oracle "$resolved/ephe" || fail "engine oracle failed for the current installation"
  echo "Ephemeris installation check OK: $(basename "$resolved")"
}
# END_BLOCK: EPHE_CHECK

# START_BLOCK: EPHE_APPLY
apply_cmd() {
  local staged="$1"
  [ -n "$staged" ] || usage
  if [ "$(id -u)" != "0" ] && [ "${EPHE_INSTALL_ALLOW_NONROOT:-0}" != "1" ]; then
    fail "--apply must run as root"
  fi
  [ -d "$staged" ] || fail "staged artifact path is missing or not a directory: $staged"

  # 1. Manifest + inventory verification (acceptance layer).
  local out artifact_id
  out=$("$CHECK_PY" "$CHECK_SCRIPT" "$staged") || exit 78
  artifact_id=${out#OK }
  [ -n "$artifact_id" ] || fail "artifact id not reported by the verifier"

  # 2. Offline engine oracle against the STAGED path (proof before install).
  run_oracle "$staged/ephe" || fail "engine oracle failed for the staged artifact"

  # 3. Atomic install: stage-copy, normalize modes, re-verify, rename.
  local final="$RELEASES_DIR/$artifact_id"
  [ ! -e "$final" ] || fail "release already exists (immutable, no overwrite): $artifact_id"
  mkdir -p "$RELEASES_DIR"
  local tmp="$RELEASES_DIR/.staging-$artifact_id.$$"
  rm -rf "$tmp"
  cp -a "$staged" "$tmp" || { rm -rf "$tmp"; fail "copy to staging failed"; }
  # Normalize modes: dirs 0755, files 0644 — staged modes never preserved.
  find "$tmp" -type d -exec chmod 0755 {} + || { rm -rf "$tmp"; fail "mode normalization failed"; }
  find "$tmp" -type f -exec chmod 0644 {} + || { rm -rf "$tmp"; fail "mode normalization failed"; }
  "$CHECK_PY" "$CHECK_SCRIPT" "$tmp" >/dev/null || { rm -rf "$tmp"; fail "staged copy verification failed"; }
  if [ "$(id -u)" = "0" ]; then
    chown -R root:root "$tmp" || { rm -rf "$tmp"; fail "ownership apply failed"; }
  fi
  mv -T "$tmp" "$final" || { rm -rf "$tmp"; fail "atomic rename failed"; }

  # 4. Post-install proof BEFORE the pointer flip. On failure only the new
  #    unreferenced release is removed; current/previous stay untouched.
  if ! "$CHECK_PY" "$CHECK_SCRIPT" "$final" >/dev/null; then
    rm -rf "$final"
    fail "post-install manifest verification failed; new release removed, current unchanged"
  fi
  if ! run_oracle "$final/ephe"; then
    rm -rf "$final"
    fail "post-install oracle failed; new release removed, current unchanged"
  fi

  # 5. Atomic pointer flip preserving previous (only after full proof).
  local prev_tmp="$EPHE_ROOT/.previous.$$" cur_tmp="$EPHE_ROOT/.current.$$"
  if [ -L "$CURRENT_LINK" ]; then
    readlink "$CURRENT_LINK" > "$prev_tmp"
  fi
  ln -sfn "$final" "$cur_tmp"
  mv -T "$cur_tmp" "$CURRENT_LINK"
  if [ -f "$prev_tmp" ]; then
    mv -fT "$prev_tmp" "$PREVIOUS_FILE"
  fi
  echo "Ephemeris artifact installed: $artifact_id (current -> $final)"
}
# END_BLOCK: EPHE_APPLY

main() {
  [ $# -ge 1 ] || usage
  case "$1" in
    --check) [ $# -eq 1 ] || usage; check_cmd ;;
    --apply) [ $# -eq 2 ] || usage; apply_cmd "$2" ;;
    *) usage ;;
  esac
}

main "$@"
# END_BLOCK: M-PROD-EPHEMERIS-INSTALL
