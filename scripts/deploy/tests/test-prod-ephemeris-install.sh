#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_EPHEMERIS_INSTALL — installer acceptance matrix
# ROLE: Proves the fail-closed ephemeris installer: reject missing/tampered/
#       extra/symlinked artifacts, accept a valid bundle atomically with
#       pointer flip and preserved previous, immutable releases, unchanged
#       current on failure.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROD-EPHEMERIS-INSTALL
# purpose: Contract tests for scripts/deploy/prod-ephemeris-install.sh using
#   fake staged bundles (no licensed bytes, oracle stubbed).
# owns:
#   - scripts/deploy/tests/test-prod-ephemeris-install.sh
# inputs: none
# outputs: exit 0 when all checks pass
# side_effects: temp sandbox dirs only
# emitted_logs: none
# invariants:
#   - no real artifact bytes; oracle always stubbed via EPHE_ORACLE_CMD
# failure_policy: assertion failures with exact case names
# END_MODULE_CONTRACT: M-TEST-PROD-EPHEMERIS-INSTALL

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
INSTALLER="$REPO_ROOT/scripts/deploy/prod-ephemeris-install.sh"
TEST_DIR=$(mktemp -d /tmp/ephe-install-test.XXXXXX)
trap 'rm -rf "$TEST_DIR"' EXIT

EPHE_ROOT="$TEST_DIR/root"
export EPHE_ROOT EPHE_INSTALL_ALLOW_NONROOT=1
FAILURES=0

stage_bundle() {
  # $1 = dir, $2 = artifact id
  local dir="$1" id="$2"
  mkdir -p "$dir/ephe"
  printf 'fake-se-bytes' > "$dir/ephe/sepl_18.se1"
  printf 'fake-se-bytes' > "$dir/ephe/semo_18.se1"
  local size sha
  size=$(stat -c %s "$dir/ephe/sepl_18.se1")
  sha=$(sha256sum "$dir/ephe/sepl_18.se1" | cut -d' ' -f1)
  cat > "$dir/manifest.json" <<EOF
{"schema_version":"solarsage-ephemeris/v1","artifact_id":"$id","created_at_utc":"2026-07-19T00:00:00Z","supported_date_range":"1800-2399","swiss_data_version":"2.10.03","files":[{"path":"ephe/sepl_18.se1","size":$size,"sha256":"$sha"},{"path":"ephe/semo_18.se1","size":$size,"sha256":"$sha"}]}
EOF
  sha256sum "$dir/manifest.json" | cut -d' ' -f1 > "$dir/manifest.sha256"
}

# Oracle stub: passes when the staged ephe dir contains sepl_18.se1.
cat > "$TEST_DIR/oracle-ok" <<'MOCK'
#!/usr/bin/env bash
[ -f "$EPHE_ORACLE_EPHE_DIR/sepl_18.se1" ] && exit 0
exit 1
MOCK
chmod +x "$TEST_DIR/oracle-ok"
export EPHE_ORACLE_CMD="$TEST_DIR/oracle-ok"

expect_fail() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "FAIL($name): expected non-zero, got 0" >&2; FAILURES=$((FAILURES+1))
  else
    echo "ok: $name"
  fi
}

expect_ok() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "ok: $name"
  else
    echo "FAIL($name): expected 0" >&2; FAILURES=$((FAILURES+1))
  fi
}

# 1. Missing staged path rejected.
expect_fail "apply missing staged path" bash "$INSTALLER" --apply "$TEST_DIR/nope"

# 2. Extra unlisted file rejected.
stage_bundle "$TEST_DIR/bad-extra" "se-bad-extra"
printf x > "$TEST_DIR/bad-extra/ephe/extra.se1"
expect_fail "apply extra file" bash "$INSTALLER" --apply "$TEST_DIR/bad-extra"

# 3. Symlink inside staged tree rejected.
stage_bundle "$TEST_DIR/bad-link" "se-bad-link"
rm "$TEST_DIR/bad-link/ephe/semo_18.se1"
ln -s "$TEST_DIR/bad-link/ephe/sepl_18.se1" "$TEST_DIR/bad-link/ephe/semo_18.se1"
expect_fail "apply symlinked inventory" bash "$INSTALLER" --apply "$TEST_DIR/bad-link"

# 4. Missing manifest.sha256 rejected.
stage_bundle "$TEST_DIR/bad-hash" "se-bad-hash"
rm "$TEST_DIR/bad-hash/manifest.sha256"
expect_fail "apply missing manifest.sha256" bash "$INSTALLER" --apply "$TEST_DIR/bad-hash"

# 5. Tampered inventory rejected.
stage_bundle "$TEST_DIR/bad-tamper" "se-bad-tamper"
printf 'tampered-longer-content' > "$TEST_DIR/bad-tamper/ephe/sepl_18.se1"
expect_fail "apply tampered inventory" bash "$INSTALLER" --apply "$TEST_DIR/bad-tamper"

# 6. Accepted apply: layout, pointer, check.
stage_bundle "$TEST_DIR/good" "se-test-2026a"
expect_ok "apply valid bundle" bash "$INSTALLER" --apply "$TEST_DIR/good"
[ -d "$EPHE_ROOT/releases/se-test-2026a/ephe" ] || { echo "FAIL: release dir missing" >&2; FAILURES=$((FAILURES+1)); }
[ "$(readlink "$EPHE_ROOT/current")" = "$EPHE_ROOT/releases/se-test-2026a" ] || { echo "FAIL: current pointer wrong" >&2; FAILURES=$((FAILURES+1)); }
cmp -s "$TEST_DIR/good/manifest.json" "$EPHE_ROOT/releases/se-test-2026a/manifest.json" || { echo "FAIL: installed manifest differs" >&2; FAILURES=$((FAILURES+1)); }
expect_ok "check after apply" bash "$INSTALLER" --check

# 7. Immutable release: re-apply same id rejected, current unchanged.
before=$(readlink "$EPHE_ROOT/current")
expect_fail "re-apply same artifact id" bash "$INSTALLER" --apply "$TEST_DIR/good"
[ "$(readlink "$EPHE_ROOT/current")" = "$before" ] || { echo "FAIL: current changed after failed re-apply" >&2; FAILURES=$((FAILURES+1)); }

# 8. Second artifact: pointer flips, previous recorded.
stage_bundle "$TEST_DIR/good2" "se-test-2026b"
expect_ok "apply second artifact" bash "$INSTALLER" --apply "$TEST_DIR/good2"
[ "$(readlink "$EPHE_ROOT/current")" = "$EPHE_ROOT/releases/se-test-2026b" ] || { echo "FAIL: current did not flip" >&2; FAILURES=$((FAILURES+1)); }
[ "$(cat "$EPHE_ROOT/previous")" = "$EPHE_ROOT/releases/se-test-2026a" ] || { echo "FAIL: previous not preserved" >&2; FAILURES=$((FAILURES+1)); }

# 9. Post-install oracle failure on a VALID bundle: new release removed,
#    current AND previous unchanged. The stub fails only for /releases/ paths
#    (i.e. exactly the post-install target), passing the staged probe.
cat > "$TEST_DIR/oracle-fail-final" <<'MOCK'
#!/usr/bin/env bash
case "$EPHE_ORACLE_EPHE_DIR" in
  *"/releases/"*) exit 1 ;;
  *) exit 0 ;;
esac
MOCK
chmod +x "$TEST_DIR/oracle-fail-final"
stage_bundle "$TEST_DIR/good3" "se-test-2026c"
prev_before=""
[ -f "$EPHE_ROOT/previous" ] && prev_before=$(cat "$EPHE_ROOT/previous")
cur_before=$(readlink "$EPHE_ROOT/current")
EPHE_ORACLE_CMD="$TEST_DIR/oracle-fail-final" expect_fail "apply valid bundle with failing post-install oracle" bash "$INSTALLER" --apply "$TEST_DIR/good3"
[ "$(readlink "$EPHE_ROOT/current")" = "$cur_before" ] || { echo "FAIL: current changed after post-install oracle failure" >&2; FAILURES=$((FAILURES+1)); }
[ ! -e "$EPHE_ROOT/releases/se-test-2026c" ] || { echo "FAIL: failed release left installed" >&2; FAILURES=$((FAILURES+1)); }
if [ -n "$prev_before" ]; then
  [ "$(cat "$EPHE_ROOT/previous")" = "$prev_before" ] || { echo "FAIL: previous changed after post-install oracle failure" >&2; FAILURES=$((FAILURES+1)); }
fi

# 10. --check fails when current missing.
rm -f "$EPHE_ROOT/current"
expect_fail "check with missing current" bash "$INSTALLER" --check

if [ "$FAILURES" -gt 0 ]; then
  echo "FAILED: $FAILURES checks" >&2
  exit 1
fi
echo "All test-prod-ephemeris-install checks passed!"
