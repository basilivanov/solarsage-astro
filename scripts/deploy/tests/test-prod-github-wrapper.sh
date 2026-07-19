#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_GITHUB_WRAPPER — forced-command wrapper contract matrix
# ROLE: Verifies SSH_ORIGINAL_COMMAND validation, dispatch, propagation,
#       fail-closed path substitution, and self-test against false positives.
# ############################################################################

set -euo pipefail

# START_MODULE_CONTRACT: M-TEST-PROD-GITHUB-WRAPPER
# purpose: Verify solarsage-github-deploy forced-command wrapper contract matrix.
# owns:
#   - scripts/deploy/tests/test-prod-github-wrapper.sh
# inputs: none
# outputs: exits 0 on success, non-zero on test failure.
# invariants:
#   - No execution of real deploy/access scripts.
#   - No network, SSH, git, or systemd operations.
#   - Fail-closed path substitution; sandbox mock targets only.
#   - Primary audit uses append-mode invocation records with BEGIN/END/target=.
#   - Exactly one invocation per case enforced via byte-exact cmp -s.
#   - stderr must be empty for valid cases, generic message for rejects.
#   - No raw SSH_ORIGINAL_COMMAND, SHA, or sentinel string in outputs.
#   - Self-tests verify harness assertion integrity, not counted in product cases.
# END_MODULE_CONTRACT: M-TEST-PROD-GITHUB-WRAPPER

# START_MODULE_MAP: M-TEST-PROD-GITHUB-WRAPPER
# public_entrypoints:
#   - test-prod-github-wrapper.sh (standalone execution)
# semantic_blocks:
#   - FAIL_CLOSED_PATH_SUBSTITUTION: pre/post exec-line assertions, canonical→sandbox
#   - PRIMARY_AUDIT_BUILDERS: build_expected_deploy_audit, build_expected_access_audit
#   - ASSERT_AUDIT_INVOCATION: verifies correct target, single invocation, exact argv
#   - RUN_CASE: single-case runner with rc, target, stderr-class, and audit validation
#   - SELF_TEST_BLOCK: 10 self-test mutations verifying harness assertion integrity
#   - NEGATIVE_MATRIX: 21 deploy + 21 source-check + 5 migrate hostile input cases
#   - POSITIVE_MATRIX: 5 deploy + 5 source-check + 2 migrate valid+propagation cases
#   - MANIFEST_VERIFICATION: sorted cmp -s of declared vs executed case IDs
#   - OUTPUT_SAFETY_SCAN: sentinel injection check, stderr generic-only audit
# owned_tests:
#   - scripts/deploy/tests/test-prod-github-wrapper.sh
# END_MODULE_MAP: M-TEST-PROD-GITHUB-WRAPPER

# START_BLOCK: FAIL_CLOSED_PATH_SUBSTITUTION

TEST_DIR=$(mktemp -d "/tmp/solarsage-r13-wrapper-test.XXXXXX")
trap 'rm -rf "$TEST_DIR"' EXIT INT TERM HUP

MOCK_BIN="$TEST_DIR/bin"
SENTINEL_PATH="$TEST_DIR/hostile_sentinel"
mkdir -p "$MOCK_BIN"

# ----------------------------------------------------------------------
# 1. Copy wrapper to sandbox (from the current checkout, never a foreign path)
# ----------------------------------------------------------------------
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
WRAPPER_COPY="$TEST_DIR/wrapper.sh"
cp "$REPO_ROOT/infra/production/solarsage-github-deploy" "$WRAPPER_COPY"
chmod +x "$WRAPPER_COPY"

# ----------------------------------------------------------------------
# 2. Fail-closed path substitution — executable dispatch only
# ----------------------------------------------------------------------
DEPLOY_CANON="/usr/local/libexec/solarsage/prod-orchestrator"
ACCESS_CANON="/opt/solarsage-astro/scripts/deploy/prod-github-access.sh"
SUDO_CANON="/usr/bin/sudo"
DEPLOY_EXEC_PATTERN="exec $SUDO_CANON -n -H $DEPLOY_CANON"
ACCESS_EXEC_PATTERN="exec /bin/bash $ACCESS_CANON"

# Pre-check: exactly three exec dispatch lines (two sudo orchestrator, one bash access)
EXEC_LINE_COUNT=$(grep -cE "^[[:space:]]*exec " "$WRAPPER_COPY" || true)
if [ "$EXEC_LINE_COUNT" -ne 3 ]; then
  echo "FAIL: Expected exactly 3 exec dispatch lines, got $EXEC_LINE_COUNT" >&2
  exit 1
fi

# Each canonical target appears in executable dispatch lines: the orchestrator
# twice (deploy + migrate), the access script exactly once.
DEPLOY_EXEC_COUNT_BEFORE=$(grep -cF "$DEPLOY_EXEC_PATTERN" "$WRAPPER_COPY" || true)
ACCESS_EXEC_COUNT_BEFORE=$(grep -cF "$ACCESS_EXEC_PATTERN" "$WRAPPER_COPY" || true)

if [ "$DEPLOY_EXEC_COUNT_BEFORE" -ne 2 ]; then
  echo "FAIL: Deploy orchestrator exec target count $DEPLOY_EXEC_COUNT_BEFORE != 2" >&2
  exit 1
fi
if [ "$ACCESS_EXEC_COUNT_BEFORE" -ne 1 ]; then
  echo "FAIL: Access exec target count $ACCESS_EXEC_COUNT_BEFORE != 1" >&2
  exit 1
fi

# Reusable exec dispatch validator: returns 0 if every exec dispatch targets
# exactly one of the expected paths (bash form or sudo -n -H form).
LAST_EXEC_ERROR=""
check_exec_targets() {
  local wrapper="$1"
  local exp1="$2"
  local exp2="$3"
  LAST_EXEC_ERROR=""
  while IFS= read -r line; do
    local tgt=""
    if [[ "$line" =~ ^[[:space:]]*exec[[:space:]]+/bin/bash[[:space:]]+([^[:space:]]+) ]]; then
      tgt="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]*exec[[:space:]]+/usr/bin/sudo[[:space:]]+-n[[:space:]]+-H[[:space:]]+([^[:space:]]+) ]]; then
      tgt="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]*exec[[:space:]] ]]; then
      LAST_EXEC_ERROR="Malformed exec dispatch line: $line"
      return 1
    fi
    if [ -n "$tgt" ] && [ "$tgt" != "$exp1" ] && [ "$tgt" != "$exp2" ]; then
      LAST_EXEC_ERROR="Unknown executable target: $tgt"
      return 1
    fi
  done < <(grep -E "^[[:space:]]*exec " "$wrapper" || true)
  return 0
}

# Check there is no third / unknown absolute executable target
check_exec_targets "$WRAPPER_COPY" "$DEPLOY_CANON" "$ACCESS_CANON"
if [ $? -ne 0 ]; then
  echo "FAIL: $LAST_EXEC_ERROR" >&2
  exit 1
fi

MOCK_DEPLOY="$MOCK_BIN/prod-orchestrator"
MOCK_ACCESS="$MOCK_BIN/prod-github-access.sh"
MOCK_SUDO="$MOCK_BIN/sudo"

# Mock sudo: validates exact -n -H flags, then execs the remaining argv.
cat > "$MOCK_SUDO" << 'MOCKEOF'
#!/usr/bin/env bash
if [ "${1:-}" != "-n" ] || [ "${2:-}" != "-H" ]; then
  exit 126
fi
shift 2
exec "$@"
MOCKEOF
chmod +x "$MOCK_SUDO"

# Perform substitution on executable dispatch lines and the sudo path only
sed -i "s|$DEPLOY_CANON|$MOCK_DEPLOY|g" "$WRAPPER_COPY"
sed -i "s|$ACCESS_CANON|$MOCK_ACCESS|g" "$WRAPPER_COPY"
sed -i "s|$SUDO_CANON|$MOCK_SUDO|g" "$WRAPPER_COPY"

# Post-check: canonical paths absent from executable dispatch lines
DEPLOY_EXEC_AFTER=$(grep -cF "exec $SUDO_CANON -n -H $DEPLOY_CANON" "$WRAPPER_COPY" || true)
ACCESS_EXEC_AFTER=$(grep -cF "exec /bin/bash $ACCESS_CANON" "$WRAPPER_COPY" || true)
if [ "$DEPLOY_EXEC_AFTER" -ne 0 ]; then
  echo "FAIL: Deploy exec canonical path still present after substitution" >&2
  exit 1
fi
if [ "$ACCESS_EXEC_AFTER" -ne 0 ]; then
  echo "FAIL: Access exec canonical path still present after substitution" >&2
  exit 1
fi

# Sandbox target paths present in executable dispatch lines: the orchestrator
# twice (deploy + migrate), the access script exactly once.
MOCK_DEPLOY_EXEC_COUNT=$(grep -cF "exec $MOCK_SUDO -n -H $MOCK_DEPLOY" "$WRAPPER_COPY" || true)
MOCK_ACCESS_EXEC_COUNT=$(grep -cF "exec /bin/bash $MOCK_ACCESS" "$WRAPPER_COPY" || true)
if [ "$MOCK_DEPLOY_EXEC_COUNT" -ne 2 ]; then
  echo "FAIL: Mock deploy orchestrator exec count $MOCK_DEPLOY_EXEC_COUNT != 2" >&2
  exit 1
fi
if [ "$MOCK_ACCESS_EXEC_COUNT" -ne 1 ]; then
  echo "FAIL: Mock access exec count $MOCK_ACCESS_EXEC_COUNT != 1" >&2
  exit 1
fi

# All executable target paths are inside TEST_DIR
for tgt in $(grep -E "^[[:space:]]*exec " "$WRAPPER_COPY" | sed -E 's|^[[:space:]]*exec[[:space:]]+(/bin/bash)[[:space:]]+([^[:space:]]+).*|\2|; s|^[[:space:]]*exec[[:space:]]+([^[:space:]]+)[[:space:]]+-n[[:space:]]+-H[[:space:]]+([^[:space:]]+).*|\2|' | awk '{print $1}'); do
  case "$tgt" in
    "$MOCK_DEPLOY"|"$MOCK_ACCESS") ;;
    *)
      echo "FAIL: Executable target $tgt is outside TEST_DIR sandbox" >&2
      exit 1
      ;;
  esac
done

# Mutation self-proof: canonical string in comment, executable path differs.
# The check_exec_targets function must reject the unknown target.
MUTATION_SELF_PROOF_FILE="$TEST_DIR/wrapper_mutation_self_proof.sh"
cp "$WRAPPER_COPY" "$MUTATION_SELF_PROOF_FILE"
# Add comment decoy with canonical deploy path (must not affect exec validation)
sed -i "1i# Canonical deploy: $DEPLOY_CANON" "$MUTATION_SELF_PROOF_FILE"
# Replace exec $MOCK_SUDO -n -H $MOCK_DEPLOY with a different absolute path
sed -i "s|exec $MOCK_SUDO -n -H $MOCK_DEPLOY|exec $MOCK_SUDO -n -H $MOCK_BIN/prod-deploy-other.sh|" "$MUTATION_SELF_PROOF_FILE"
set +e
check_exec_targets "$MUTATION_SELF_PROOF_FILE" "$MOCK_DEPLOY" "$MOCK_ACCESS"
MUT_CHECK_RC=$?
set -e
if [ "$MUT_CHECK_RC" -eq 0 ]; then
  echo "FAIL: Mutation self-proof — check_exec_targets did not detect unknown target" >&2
  exit 1
fi
rm -f "$MUTATION_SELF_PROOF_FILE"
echo "PASS: Mutation self-proof — unknown executable target detected (comment decoy ignored)"

echo "PASS: Executable-only path substitution verified"

# END_BLOCK: FAIL_CLOSED_PATH_SUBSTITUTION

# START_BLOCK: PRIMARY_AUDIT_BUILDERS

# ----------------------------------------------------------------------
# 3. Create mock targets with append-mode invocation records
# ----------------------------------------------------------------------
DEPLOY_AUDIT="$TEST_DIR/deploy_audit.txt"
ACCESS_AUDIT="$TEST_DIR/access_audit.txt"

# Invocation record format:
#   BEGIN
#   target=deploy
#   /bin/bash
#   <%q of $0>
#   <%q of arg1>
#   ...
#   END

cat > "$MOCK_DEPLOY" << MOCKEOF
#!/usr/bin/env bash
{
  printf '%s\n' "BEGIN"
  printf '%s\n' "target=deploy"
  printf '%s\n' "/bin/bash"
  printf '%q\n' "\$0"
  for arg in "\$@"; do
    printf '%q\n' "\$arg"
  done
  printf '%s\n' "END"
} >> "$DEPLOY_AUDIT"
exit \${MOCK_TARGET_RC:-0}
MOCKEOF
chmod +x "$MOCK_DEPLOY"

cat > "$MOCK_ACCESS" << MOCKEOF
#!/usr/bin/env bash
{
  printf '%s\n' "BEGIN"
  printf '%s\n' "target=source-check"
  printf '%s\n' "/bin/bash"
  printf '%q\n' "\$0"
  for arg in "\$@"; do
    printf '%q\n' "\$arg"
  done
  printf '%s\n' "END"
} >> "$ACCESS_AUDIT"
exit \${MOCK_TARGET_RC:-0}
MOCKEOF
chmod +x "$MOCK_ACCESS"

# ----------------------------------------------------------------------
# 4. Standard SHAs for positive tests
# ----------------------------------------------------------------------
SHA1="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
SHA2="f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2"

# DEP_SHA used in validate_case_output SHA-leak check and negative matrix
DEP_SHA="$SHA1"

# 40-char non-hex SHA: replace last char with 'g' (40 chars total)
NONHEX_SHA="${DEP_SHA%?}g"
if [ "${#NONHEX_SHA}" -ne 40 ]; then
  echo "FAIL: NONHEX_SHA length ${#NONHEX_SHA} != 40" >&2; exit 1
fi
if [[ "$NONHEX_SHA" != *g ]]; then
  echo "FAIL: NONHEX_SHA does not contain 'g'" >&2; exit 1
fi
if [[ "$NONHEX_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "FAIL: NONHEX_SHA unexpectedly matches lowercase hex regex" >&2; exit 1
fi

# END_BLOCK: PRIMARY_AUDIT_BUILDERS

# ----------------------------------------------------------------------
# 5. Helper functions
# ----------------------------------------------------------------------

CASE_COUNT=0
LAST_CASE_ID="setup"

# START_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.build_expected_deploy_audit
# purpose: Build expected single-invocation audit file for deploy target.
# inputs: sha (40-char hex), out (output file path).
# outputs: Writes invocation record to out for cmp -s comparison.
# side_effects: Creates out file.
# END_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.build_expected_deploy_audit
build_expected_deploy_audit() {
  local sha="$1"
  local out="$2"
  {
    printf '%s\n' "BEGIN"
    printf '%s\n' "target=deploy"
    printf '%s\n' "/bin/bash"
    printf '%q\n' "$MOCK_DEPLOY"
    printf '%q\n' "deploy"
    printf '%q\n' "$sha"
    printf '%q\n' "--manual-confirm"
    printf '%s\n' "END"
  } > "$out"
}

# START_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.build_expected_access_audit
# purpose: Build expected single-invocation audit file for source-check target.
# END_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.build_expected_access_audit
build_expected_access_audit() {
  local sha="$1"
  local out="$2"
  {
    printf '%s\n' "BEGIN"
    printf '%s\n' "target=source-check"
    printf '%s\n' "/bin/bash"
    printf '%q\n' "$MOCK_ACCESS"
    printf '%q\n' "--check"
    printf '%q\n' "--expected-sha"
    printf '%q\n' "$sha"
    printf '%s\n' "END"
  } > "$out"
}

# START_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.build_expected_migrate_audit
# purpose: Build expected single-invocation audit file for the migrate target
#   (orchestrator mock invoked with migrate argv).
# END_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.build_expected_migrate_audit
build_expected_migrate_audit() {
  local sha="$1"
  local out="$2"
  {
    printf '%s\n' "BEGIN"
    printf '%s\n' "target=deploy"
    printf '%s\n' "/bin/bash"
    printf '%q\n' "$MOCK_DEPLOY"
    printf '%q\n' "migrate"
    printf '%q\n' "$sha"
    printf '%q\n' "--manual-confirm"
    printf '%s\n' "END"
  } > "$out"
}

# START_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.assert_audit_invocation
# purpose: Verify correct target was invoked exactly once with exact argv.
# inputs: audit_file, expected_file, target_label (deploy/access for diagnostics).
# failure_policy: Exits 1 if audit missing, wrong target, or argv mismatch.
# END_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.assert_audit_invocation
assert_audit_invocation() {
  local audit_file="$1"
  local expected_file="$2"
  local target_label="$3"
  if [ ! -f "$audit_file" ]; then
    echo "FAIL: $LAST_CASE_ID audit file missing: $audit_file (expected $target_label)" >&2
    exit 1
  fi
  if ! cmp -s "$audit_file" "$expected_file"; then
    echo "FAIL: $LAST_CASE_ID $target_label audit mismatch — expected single invocation" >&2
    echo "  audit: $audit_file" >&2
    echo "  expected: $expected_file" >&2
    exit 1
  fi
}

# Expected stderr files for generic messages
REMOTE_ERR_FILE="$TEST_DIR/remote_err.txt"
printf 'Remote commands are not permitted for this deploy key.\n' > "$REMOTE_ERR_FILE"
ARGS_ERR_FILE="$TEST_DIR/args_err.txt"
printf 'Arguments are not permitted for this deploy key.\n' > "$ARGS_ERR_FILE"
FORBIDDEN_ERR_FILE="$TEST_DIR/forbidden_err.txt"
printf 'Forbidden command format.\n' > "$FORBIDDEN_ERR_FILE"

# START_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.validate_case_output
# purpose: Validate per-case stdout/stderr contract. Returns 0 on pass,
#   1 on violation with VIOLATION_REASON set. Does not exit.
# inputs: stdout_file, stderr_file, expected_stderr_class, case_id
# side_effects: Sets VIOLATION_REASON on violation.
# END_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.validate_case_output
VIOLATION_REASON=""
validate_case_output() {
  local stdout_file="$1"
  local stderr_file="$2"
  local expected_stderr_class="$3"
  local case_id="$4"
  VIOLATION_REASON=""

  # stdout must be empty
  if [ -s "$stdout_file" ]; then
    VIOLATION_REASON="$case_id: stdout not empty"
    return 1
  fi

  # Check for SHA leak in stderr (before class check, so leak is caught first)
  if grep -Fq "$DEP_SHA" "$stderr_file" 2>/dev/null; then
    VIOLATION_REASON="$case_id: SHA leaked to stderr"
    return 1
  fi
  if grep -Fq "$DEP_SHA" "$stdout_file" 2>/dev/null; then
    VIOLATION_REASON="$case_id: SHA leaked to stdout"
    return 1
  fi

  # Check stderr class
  local expected_err_file=""
  case "$expected_stderr_class" in
    "empty")   expected_err_file="/dev/null" ;;
    "remote")  expected_err_file="$REMOTE_ERR_FILE" ;;
    "args")    expected_err_file="$ARGS_ERR_FILE" ;;
    "forbidden") expected_err_file="$FORBIDDEN_ERR_FILE" ;;
    *)
      VIOLATION_REASON="$case_id: unknown stderr class: $expected_stderr_class"
      return 1
      ;;
  esac
  if ! cmp -s "$stderr_file" "$expected_err_file"; then
    VIOLATION_REASON="$case_id: stderr mismatch (expected class: $expected_stderr_class)"
    return 1
  fi
  return 0
}

# START_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.run_case
# purpose: Run a single test case against the sandbox wrapper and verify result.
# inputs:
#   expected_rc — expected exit code from wrapper
#   expect_target — "deploy", "access", or "none" (which target should be called)
#   case_id — unique uppercase ID for manifest tracking
#   label — human-readable label for diagnostics
#   ssh_cmd — SSH_ORIGINAL_COMMAND value
#   expected_stderr_class — "empty", "remote", "args", or "forbidden"
#   remaining args — positional args passed to wrapper (for testing positional rejection)
# side_effects: Creates output files in TEST_DIR/outputs/; updates CASE_COUNT and
#   case_ids manifest.
# error_behavior: Exits 1 on rc mismatch, audit mismatch, wrong target called,
#   or stderr class mismatch.
# END_FUNCTION_CONTRACT: F-M-TEST-PROD-GITHUB-WRAPPER.run_case
run_case() {
  local expected_rc="$1"
  local expect_target="$2"
  local case_id="$3"
  local label="$4"
  local ssh_cmd="$5"
  local expected_stderr_class="$6"
  shift 6

  if [[ ! "$case_id" =~ ^[A-Z0-9_]+$ ]]; then
    echo "FAIL: Invalid Case ID format: $case_id" >&2
    exit 1
  fi
  if grep -Fxq "$case_id" "$TEST_DIR/case_ids" 2>/dev/null; then
    echo "FAIL: Duplicate Case ID: $case_id" >&2
    exit 1
  fi
  echo "$case_id" >> "$TEST_DIR/case_ids"

  CASE_COUNT=$((CASE_COUNT + 1))
  LAST_CASE_ID="$case_id"
  mkdir -p "$TEST_DIR/outputs"

  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"

  set +e
  SSH_ORIGINAL_COMMAND="$ssh_cmd" "$WRAPPER_COPY" "$@" \
    > "$TEST_DIR/outputs/$case_id.stdout" 2> "$TEST_DIR/outputs/$case_id.stderr"
  local rc=$?
  set -e

  if [ "$rc" -ne "$expected_rc" ]; then
    echo "FAIL: $case_id $label (expected RC $expected_rc, got $rc)" >&2
    echo "  stdout: $TEST_DIR/outputs/$case_id.stdout" >&2
    echo "  stderr: $TEST_DIR/outputs/$case_id.stderr" >&2
    exit 1
  fi

  # Validate stdout/stderr contract via reusable validator
  if ! validate_case_output "$TEST_DIR/outputs/$case_id.stdout" \
       "$TEST_DIR/outputs/$case_id.stderr" "$expected_stderr_class" "$case_id"; then
    echo "FAIL: $case_id $label ($VIOLATION_REASON)" >&2
    echo "  stderr: $TEST_DIR/outputs/$case_id.stderr" >&2
    exit 1
  fi

  # Target audit validation
  if [ "$expect_target" = "deploy" ]; then
    if [ ! -f "$DEPLOY_AUDIT" ]; then
      echo "FAIL: $case_id $label (deploy audit missing)" >&2
      exit 1
    fi
    if [ -f "$ACCESS_AUDIT" ]; then
      echo "FAIL: $case_id $label (unexpected access audit)" >&2
      exit 1
    fi
  elif [ "$expect_target" = "access" ]; then
    if [ ! -f "$ACCESS_AUDIT" ]; then
      echo "FAIL: $case_id $label (access audit missing)" >&2
      exit 1
    fi
    if [ -f "$DEPLOY_AUDIT" ]; then
      echo "FAIL: $case_id $label (unexpected deploy audit)" >&2
      exit 1
    fi
  elif [ "$expect_target" = "none" ]; then
    if [ -f "$DEPLOY_AUDIT" ]; then
      echo "FAIL: $case_id $label (unexpected deploy audit)" >&2
      exit 1
    fi
    if [ -f "$ACCESS_AUDIT" ]; then
      echo "FAIL: $case_id $label (unexpected access audit)" >&2
      exit 1
    fi
  fi

  echo "PASS: $case_id $label"
}

# ----------------------------------------------------------------------
# 6. Self-test block (separate manifest, not counted in CASE_COUNT)
# ----------------------------------------------------------------------
SELF_TEST_MANIFEST="$TEST_DIR/self_test_ids"
: > "$SELF_TEST_MANIFEST"

run_self_test() {
  local test_id="$1"
  if [[ ! "$test_id" =~ ^[A-Z0-9_]+$ ]]; then
    echo "FAIL: Invalid self-test ID format: $test_id" >&2
    exit 1
  fi
  if grep -Fxq "$test_id" "$SELF_TEST_MANIFEST" 2>/dev/null; then
    echo "FAIL: Duplicate self-test ID: $test_id" >&2
    exit 1
  fi
  echo "$test_id" >> "$SELF_TEST_MANIFEST"
}

echo "--- Self-test block ---"

# Helper: build expected deploy audit file (shared with product tests)
# Already defined as build_expected_deploy_audit / build_expected_access_audit

# Self-test 1: mock deploy adds extra argv
run_self_test "SELF01_EXTRA_ARGV"
self_test_1() {
  local mut_deploy="$MOCK_BIN/deploy_self1.sh"
  cat > "$mut_deploy" << MUTEOF
#!/usr/bin/env bash
{
  printf '%s\n' "BEGIN"
  printf '%s\n' "target=deploy"
  printf '%s\n' "/bin/bash"
  printf '%q\n' "\$0"
  for arg in "\$@"; do
    printf '%q\n' "\$arg"
  done
  printf '%q\n' "--extra"
  printf '%s\n' "END"
} >> "$DEPLOY_AUDIT"
exit 0
MUTEOF
  chmod +x "$mut_deploy"
  local tmp_wrapper="$TEST_DIR/wrapper_self1.sh"
  cp "$WRAPPER_COPY" "$tmp_wrapper"
  sed -i "s|$MOCK_DEPLOY|$mut_deploy|g" "$tmp_wrapper"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1" "$tmp_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then echo "FAIL: Self-test 1 wrapper failed" >&2; exit 1; fi
  local exp_aud="$TEST_DIR/self1_exp.txt"
  build_expected_deploy_audit "$SHA1" "$exp_aud"
  # Expected has 1 record, actual has extra argv — cmp should fail
  if cmp -s "$DEPLOY_AUDIT" "$exp_aud" 2>/dev/null; then
    echo "FAIL: Self-test 1 did not detect extra argv" >&2; exit 1
  fi
  rm -f "$mut_deploy" "$tmp_wrapper" "$exp_aud"
  echo "PASS: Self-test 1 caught: mock deploy adds extra argv"
}

# Self-test 2: mock source-check changes argv order
run_self_test "SELF02_ARGV_REORDER"
self_test_2() {
  local mut_access="$MOCK_BIN/access_self2.sh"
  cat > "$mut_access" << MUTEOF
#!/usr/bin/env bash
{
  printf '%s\n' "BEGIN"
  printf '%s\n' "target=source-check"
  printf '%s\n' "/bin/bash"
  printf '%q\n' "\$0"
  printf '%q\n' "\$3"
  printf '%q\n' "\$1"
  printf '%q\n' "\$2"
  printf '%s\n' "END"
} >> "$ACCESS_AUDIT"
exit 0
MUTEOF
  chmod +x "$mut_access"
  local tmp_wrapper="$TEST_DIR/wrapper_self2.sh"
  cp "$WRAPPER_COPY" "$tmp_wrapper"
  sed -i "s|$MOCK_ACCESS|$mut_access|g" "$tmp_wrapper"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="source-check $SHA1" "$tmp_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then echo "FAIL: Self-test 2 wrapper failed" >&2; exit 1; fi
  local exp_aud="$TEST_DIR/self2_exp.txt"
  build_expected_access_audit "$SHA1" "$exp_aud"
  if cmp -s "$ACCESS_AUDIT" "$exp_aud" 2>/dev/null; then
    echo "FAIL: Self-test 2 did not detect reordered argv" >&2; exit 1
  fi
  rm -f "$mut_access" "$tmp_wrapper" "$exp_aud"
  echo "PASS: Self-test 2 caught: source-check argv reordered"
}

# Self-test 3: deploy/access targets swapped in wrapper-copy
run_self_test "SELF03_TARGETS_SWAPPED"
self_test_3() {
  local swapped="$TEST_DIR/wrapper_self3.sh"
  cp "$WRAPPER_COPY" "$swapped"
  sed -i "s|$MOCK_DEPLOY|__DEP_PH__|g" "$swapped"
  sed -i "s|$MOCK_ACCESS|$MOCK_DEPLOY|g" "$swapped"
  sed -i "s|__DEP_PH__|$MOCK_ACCESS|g" "$swapped"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1" "$swapped" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then echo "FAIL: Self-test 3 wrapper failed" >&2; exit 1; fi
  # Should have called ACCESS mock instead of DEPLOY mock
  if [ -f "$DEPLOY_AUDIT" ]; then
    echo "FAIL: Self-test 3 called deploy target unexpectedly" >&2; exit 1
  fi
  if [ ! -f "$ACCESS_AUDIT" ]; then
    echo "FAIL: Self-test 3 did not detect swapped targets" >&2; exit 1
  fi
  rm -f "$swapped"
  echo "PASS: Self-test 3 caught: deploy/access targets swapped"
}

# Self-test 4: propagation branch returns rc without calling target
run_self_test "SELF04_NO_TARGET"
self_test_4() {
  local noexec="$TEST_DIR/wrapper_self4.sh"
  cp "$WRAPPER_COPY" "$noexec"
  sed -i "s|exec $MOCK_SUDO -n -H $MOCK_DEPLOY deploy \"\\\$sha\" --manual-confirm|exit 0|" "$noexec"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1" "$noexec" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then echo "FAIL: Self-test 4 wrapper failed" >&2; exit 1; fi
  if [ -f "$DEPLOY_AUDIT" ]; then
    echo "FAIL: Self-test 4 wrapper called target despite noexec" >&2; exit 1
  fi
  rm -f "$noexec"
  echo "PASS: Self-test 4 caught: exit without calling target"
}

# Self-test 5: two argv concatenated into one
run_self_test "SELF05_CONCAT_ARGV"
self_test_5() {
  local mut_deploy="$MOCK_BIN/deploy_self5.sh"
  cat > "$mut_deploy" << MUTEOF
#!/usr/bin/env bash
{
  printf '%s\n' "BEGIN"
  printf '%s\n' "target=deploy"
  printf '%s\n' "/bin/bash"
  printf '%q\n' "\$0"
  printf '%q\n' "\$1 \$2"
  printf '%s\n' "END"
} >> "$DEPLOY_AUDIT"
exit 0
MUTEOF
  chmod +x "$mut_deploy"
  local tmp_wrapper="$TEST_DIR/wrapper_self5.sh"
  cp "$WRAPPER_COPY" "$tmp_wrapper"
  sed -i "s|$MOCK_DEPLOY|$mut_deploy|g" "$tmp_wrapper"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1" "$tmp_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then echo "FAIL: Self-test 5 wrapper failed" >&2; exit 1; fi
  local exp_aud="$TEST_DIR/self5_exp.txt"
  build_expected_deploy_audit "$SHA1" "$exp_aud"
  if cmp -s "$DEPLOY_AUDIT" "$exp_aud" 2>/dev/null; then
    echo "FAIL: Self-test 5 did not detect concatenated argv" >&2; exit 1
  fi
  rm -f "$mut_deploy" "$tmp_wrapper" "$exp_aud"
  echo "PASS: Self-test 5 caught: two argv concatenated into one"
}

# Self-test 6: target called twice — detected via append record
# Uses the primary audit builder: expected has 1 record, actual has 2 records.
# run_self_test: must use same build_expected_*_audit for cmp validation.
run_self_test "SELF06_DOUBLE_CALL"
self_test_6() {
  local twice_wrapper="$TEST_DIR/wrapper_self6.sh"

  # Use primary append mocks (already exist at $MOCK_DEPLOY/$MOCK_ACCESS)

  # Build a wrapper that calls deploy target twice (no exec, so both run)
  cp "$WRAPPER_COPY" "$twice_wrapper"
  # Remove exec prefix and duplicate the command
  sed -i "s|exec $MOCK_SUDO -n -H $MOCK_DEPLOY deploy \"\\\$sha\" --manual-confirm|$MOCK_SUDO -n -H $MOCK_DEPLOY deploy \"\$sha\" --manual-confirm; $MOCK_SUDO -n -H $MOCK_DEPLOY deploy \"\$sha\" --manual-confirm|" "$twice_wrapper"

  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1" "$twice_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then echo "FAIL: Self-test 6 wrapper failed" >&2; exit 1; fi

  # Build expected with ONE record — actual has TWO records
  local exp_aud="$TEST_DIR/self6_exp.txt"
  build_expected_deploy_audit "$SHA1" "$exp_aud"

  # cmp should fail because audit has 2 records (12 lines) vs expected 1 (7 lines)
  if cmp -s "$DEPLOY_AUDIT" "$exp_aud" 2>/dev/null; then
    echo "FAIL: Self-test 6 did not detect double invocation" >&2; exit 1
  fi
  rm -f "$twice_wrapper" "$exp_aud"
  echo "PASS: Self-test 6 caught: target called twice (primary audit validator)"
}

# Self-test 7: literal-space check bypassed — tab-separated command is accepted
run_self_test "SELF07_TAB_AFTER_BYPASS"
self_test_7() {
  local mut_wrapper="$TEST_DIR/wrapper_self7.sh"
  cp "$WRAPPER_COPY" "$mut_wrapper"
  sed -i '67s|if \[\[[^]]*\]\]; then|if false; then|' "$mut_wrapper"
  sed -i '75s|if \[\[[^]]*\]\]; then|if false; then|' "$mut_wrapper"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  local tab_cmd
  tab_cmd=$(printf "deploy\t%s" "$SHA1")
  set +e
  SSH_ORIGINAL_COMMAND="$tab_cmd" "$mut_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -f "$DEPLOY_AUDIT" ]; then
    echo "FAIL: Self-test 7 mutation ineffective — literal-space bypass did not allow tab" >&2
    exit 1
  fi
  rm -f "$mut_wrapper"
  echo "PASS: Self-test 7 caught: literal-space check bypassed allowed tab-separated command"
}

# Self-test 8: regex widened to accept uppercase hex
run_self_test "SELF08_UPPER_REGEX"
self_test_8() {
  local up_wrapper="$TEST_DIR/wrapper_self8.sh"
  cp "$WRAPPER_COPY" "$up_wrapper"
  sed -i 's|\[0-9a-f\]|[0-9a-fA-F]|g' "$up_wrapper"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4E5F6A1B2" "$up_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -f "$DEPLOY_AUDIT" ]; then
    echo "FAIL: Self-test 8 mutation ineffective — uppercase SHA was rejected" >&2
    exit 1
  fi
  rm -f "$up_wrapper"
  echo "PASS: Self-test 8 caught: regex widened to accept uppercase SHA"
}

# Self-test 9: $ end-anchor removed — trailing content accepted
run_self_test "SELF09_NO_ANCHOR"
self_test_9() {
  local trail_wrapper="$TEST_DIR/wrapper_self9.sh"
  cp "$WRAPPER_COPY" "$trail_wrapper"
  sed -i 's/\$  */ /' "$trail_wrapper"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1 extra" "$trail_wrapper" > /dev/null 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ] || [ ! -f "$DEPLOY_AUDIT" ]; then
    echo "FAIL: Self-test 9 mutation ineffective — trailing content was rejected" >&2
    exit 1
  fi
  rm -f "$trail_wrapper"
  echo "PASS: Self-test 9 caught: \$ anchor removed allowed trailing content"
}

# Self-test 10: output validator rejects raw SSH_ORIGINAL_COMMAND in stderr
# Mutation: wrapper echoes the raw command before the generic reject message.
# The reusable validate_case_output must return non-zero (SHA leak).
# Output is stored outside $TEST_DIR/outputs/ so global scan doesn't see it.
run_self_test "SELF10_RAW_COMMAND_IN_STDERR"
self_test_10() {
  local raw_wrapper="$TEST_DIR/wrapper_self10.sh"
  cp "$WRAPPER_COPY" "$raw_wrapper"
  # Before the reject, add echo of raw SSH_ORIGINAL_COMMAND
  sed -i 's|echo "Forbidden command format." >&2|echo "$SSH_ORIGINAL_COMMAND" >\&2; echo "Forbidden command format." >\&2|' "$raw_wrapper"
  local self10_dir="$TEST_DIR/self_outputs"
  mkdir -p "$self10_dir"
  rm -f "$DEPLOY_AUDIT" "$ACCESS_AUDIT"
  set +e
  SSH_ORIGINAL_COMMAND="deploy $SHA1 extra" "$raw_wrapper" \
    > "$self10_dir/stdout" 2> "$self10_dir/stderr"
  local rc=$?
  set -e
  if [ "$rc" -ne 126 ]; then
    echo "FAIL: Self-test 10 wrapper returned $rc, expected 126" >&2; exit 1
  fi
  # Call the same reusable output validator — must return non-zero
  if validate_case_output "$self10_dir/stdout" "$self10_dir/stderr" "forbidden" "self10"; then
    echo "FAIL: Self-test 10 — validate_case_output did not reject leaked command" >&2
    exit 1
  fi
  # Clean up intentional output before global scan
  rm -rf "$self10_dir" "$raw_wrapper"
  echo "PASS: Self-test 10 caught: raw SSH_ORIGINAL_COMMAND leaked to stderr (reusable validator)"
}

self_test_1
self_test_2
self_test_3
self_test_4
self_test_5
self_test_6
self_test_7
self_test_8
self_test_9
self_test_10

echo "--- Self-test block complete ---"
echo ""

# ----------------------------------------------------------------------
# 7. Negative cases — deploy (21 cases)
# ----------------------------------------------------------------------
# DEP_SHA and NONHEX_SHA defined earlier after SHA1/SHA2

run_case 126 "none" "DEP_N01" "empty command" "" "remote"
run_case 126 "none" "DEP_N02" "positional arg on wrapper" "deploy $DEP_SHA" "args" extra_arg
run_case 126 "none" "DEP_N03" "uppercase SHA" "deploy A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4E5F6A1B2" "forbidden"
run_case 126 "none" "DEP_N04" "non-hex SHA (40 chars, g)" "deploy $NONHEX_SHA" "forbidden"
run_case 126 "none" "DEP_N05" "short SHA" "deploy a1b2" "forbidden"
run_case 126 "none" "DEP_N06" "long SHA (41 chars)" "deploy a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c" "forbidden"
run_case 126 "none" "DEP_N07" "missing SHA" "deploy" "forbidden"
run_case 126 "none" "DEP_N08" "two spaces after verb" "deploy  $DEP_SHA" "forbidden"
run_case 126 "none" "DEP_N09" "leading space" " deploy $DEP_SHA" "forbidden"
run_case 126 "none" "DEP_N10" "trailing space" "deploy $DEP_SHA " "forbidden"
run_case 126 "none" "DEP_N11" "tab instead of space" $'deploy\t'$DEP_SHA "forbidden"
run_case 126 "none" "DEP_N12" "trailing LF" $'deploy '"$DEP_SHA"$'\n' "forbidden"
run_case 126 "none" "DEP_N13" "trailing CR" $'deploy '"$DEP_SHA"$'\r' "forbidden"
run_case 126 "none" "DEP_N14" "extra token after SHA" "deploy $DEP_SHA extra" "forbidden"
run_case 126 "none" "DEP_N15" "semicolon injection" "deploy $DEP_SHA; id" "forbidden"
run_case 126 "none" "DEP_N16" "command substitution (dollar)" 'deploy '"$DEP_SHA"'; $(id)' "forbidden"
run_case 126 "none" "DEP_N17" "backtick command substitution" 'deploy '"$DEP_SHA"' `id`' "forbidden"
run_case 126 "none" "DEP_N18" "pipe" "deploy $DEP_SHA | true" "forbidden"
run_case 126 "none" "DEP_N19" "double-ampersand" "deploy $DEP_SHA && true" "forbidden"
run_case 126 "none" "DEP_N20" "other verb with valid SHA" "status $DEP_SHA" "forbidden"
run_case 126 "none" "DEP_N21" "arbitrary command" "id" "forbidden"

# ----------------------------------------------------------------------
# 8. Negative cases — source-check (21 cases, symmetric with deploy)
# ----------------------------------------------------------------------

run_case 126 "none" "SRC_N01" "empty command" "" "remote"
run_case 126 "none" "SRC_N02" "positional arg on wrapper" "source-check $DEP_SHA" "args" extra_arg
run_case 126 "none" "SRC_N03" "uppercase SHA" "source-check A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4E5F6A1B2" "forbidden"
run_case 126 "none" "SRC_N04" "non-hex SHA (40 chars, g)" "source-check $NONHEX_SHA" "forbidden"
run_case 126 "none" "SRC_N05" "short SHA" "source-check a1b2" "forbidden"
run_case 126 "none" "SRC_N06" "long SHA (41 chars)" "source-check a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c" "forbidden"
run_case 126 "none" "SRC_N07" "missing SHA" "source-check" "forbidden"
run_case 126 "none" "SRC_N08" "two spaces after verb" "source-check  $DEP_SHA" "forbidden"
run_case 126 "none" "SRC_N09" "leading space" " source-check $DEP_SHA" "forbidden"
run_case 126 "none" "SRC_N10" "trailing space" "source-check $DEP_SHA " "forbidden"
run_case 126 "none" "SRC_N11" "tab instead of space" $'source-check\t'$DEP_SHA "forbidden"
run_case 126 "none" "SRC_N12" "trailing LF" $'source-check '"$DEP_SHA"$'\n' "forbidden"
run_case 126 "none" "SRC_N13" "trailing CR" $'source-check '"$DEP_SHA"$'\r' "forbidden"
run_case 126 "none" "SRC_N14" "extra token after SHA" "source-check $DEP_SHA extra" "forbidden"
run_case 126 "none" "SRC_N15" "semicolon injection" "source-check $DEP_SHA; id" "forbidden"
run_case 126 "none" "SRC_N16" "command substitution (dollar)" 'source-check '"$DEP_SHA"'; $(id)' "forbidden"
run_case 126 "none" "SRC_N17" "backtick command substitution" 'source-check '"$DEP_SHA"' `id`' "forbidden"
run_case 126 "none" "SRC_N18" "pipe" "source-check $DEP_SHA | true" "forbidden"
run_case 126 "none" "SRC_N19" "double-ampersand" "source-check $DEP_SHA && true" "forbidden"
run_case 126 "none" "SRC_N20" "other verb with valid SHA" "status $DEP_SHA" "forbidden"
run_case 126 "none" "SRC_N21" "arbitrary command" "env" "forbidden"

# ----------------------------------------------------------------------
# 9. Positive cases + propagation
# ----------------------------------------------------------------------

# Helper: build expected audit files and run + verify
run_positive_deploy() {
  local case_id="$1"
  local sha="$2"
  local expected_rc="$3"
  local label="$4"
  export MOCK_TARGET_RC="$expected_rc"
  run_case "$expected_rc" "deploy" "$case_id" "deploy $label" "deploy $sha" "empty"
  local exp_aud="$TEST_DIR/${case_id}_exp.txt"
  build_expected_deploy_audit "$sha" "$exp_aud"
  assert_audit_invocation "$DEPLOY_AUDIT" "$exp_aud" "deploy"
  rm -f "$exp_aud"
}

run_positive_access() {
  local case_id="$1"
  local sha="$2"
  local expected_rc="$3"
  local label="$4"
  export MOCK_TARGET_RC="$expected_rc"
  run_case "$expected_rc" "access" "$case_id" "access $label" "source-check $sha" "empty"
  local exp_aud="$TEST_DIR/${case_id}_exp.txt"
  build_expected_access_audit "$sha" "$exp_aud"
  assert_audit_invocation "$ACCESS_AUDIT" "$exp_aud" "access"
  rm -f "$exp_aud"
}

# Deploy: valid with SHA1
export MOCK_TARGET_RC=0
run_positive_deploy "DEP_V01" "$SHA1" 0 "valid SHA1"
# Deploy: valid with SHA2 (prove not SHA-specific)
run_positive_deploy "DEP_V02" "$SHA2" 0 "valid SHA2"
# Deploy: propagation rc 1
run_positive_deploy "DEP_P01" "$SHA1" 1 "propagation rc 1"
# Deploy: propagation rc 42
run_positive_deploy "DEP_P02" "$SHA1" 42 "propagation rc 42"
# Deploy: propagation rc 126 (target returns 126, not wrapper)
run_positive_deploy "DEP_P03" "$SHA1" 126 "propagation rc 126"

# Source-check: valid with SHA1
export MOCK_TARGET_RC=0
run_positive_access "SRC_V01" "$SHA1" 0 "valid SHA1"
# Source-check: valid with SHA2
run_positive_access "SRC_V02" "$SHA2" 0 "valid SHA2"
# Source-check: propagation rc 1
run_positive_access "SRC_P01" "$SHA1" 1 "propagation rc 1"
# Source-check: propagation rc 42
run_positive_access "SRC_P02" "$SHA1" 42 "propagation rc 42"
# Source-check: propagation rc 126
run_positive_access "SRC_P03" "$SHA1" 126 "propagation rc 126"

unset MOCK_TARGET_RC

# ----------------------------------------------------------------------
# 9b. Migrate: exact success + rc propagation + representative rejects
# ----------------------------------------------------------------------

run_positive_migrate() {
  local case_id="$1"
  local sha="$2"
  local expected_rc="$3"
  local label="$4"
  export MOCK_TARGET_RC="$expected_rc"
  run_case "$expected_rc" "deploy" "$case_id" "migrate $label" "migrate $sha" "empty"
  local exp_aud="$TEST_DIR/${case_id}_exp.txt"
  build_expected_migrate_audit "$sha" "$exp_aud"
  assert_audit_invocation "$DEPLOY_AUDIT" "$exp_aud" "deploy"
  rm -f "$exp_aud"
}

# Migrate: valid with SHA1
export MOCK_TARGET_RC=0
run_positive_migrate "MIG_V01" "$SHA1" 0 "valid SHA1"
# Migrate: rc propagation (orchestrator fail code)
run_positive_migrate "MIG_P01" "$SHA1" 78 "propagation rc 78"

unset MOCK_TARGET_RC

# Representative malformed/injection rejects (no full matrix)
run_case 126 "none" "MIG_N01" "missing SHA" "migrate" "forbidden"
run_case 126 "none" "MIG_N02" "non-hex SHA (40 chars, g)" "migrate $NONHEX_SHA" "forbidden"
run_case 126 "none" "MIG_N03" "tab instead of space" $'migrate\t'$DEP_SHA "forbidden"
run_case 126 "none" "MIG_N04" "extra token after SHA" "migrate $DEP_SHA extra" "forbidden"
run_case 126 "none" "MIG_N05" "semicolon injection" "migrate $DEP_SHA; id" "forbidden"

# ----------------------------------------------------------------------
# 10. Hostile sentinel cases — verify shell injection is prevented
# ----------------------------------------------------------------------

# These send literal $() and backtick touches to SSH_ORIGINAL_COMMAND.
# The wrapper must NEVER execute them. Verify sentinel file does not exist.
# Also the sentinel path must not appear in any output.

run_case 126 "none" "DEP_N22" "dollar injection sentinel" \
  'deploy '"$DEP_SHA"' $(touch '"$SENTINEL_PATH"')' "forbidden"

run_case 126 "none" "DEP_N23" "backtick injection sentinel" \
  'deploy '"$DEP_SHA"' `touch '"$SENTINEL_PATH"'`' "forbidden"

run_case 126 "none" "SRC_N22" "dollar injection sentinel" \
  'source-check '"$DEP_SHA"' $(touch '"$SENTINEL_PATH"')' "forbidden"

run_case 126 "none" "SRC_N23" "backtick injection sentinel" \
  'source-check '"$DEP_SHA"' `touch '"$SENTINEL_PATH"'`' "forbidden"

# Verify sentinel file was NOT created by any case
if [ -f "$SENTINEL_PATH" ]; then
  echo "FAIL: Hostile sentinel file was created — shell injection occurred!" >&2
  exit 1
fi

# ----------------------------------------------------------------------
# 11. Case manifest verification
# ----------------------------------------------------------------------

# Build expected product manifest sorted
EXPECTED_MANIFEST="$TEST_DIR/expected_manifest.txt"
cat > "$EXPECTED_MANIFEST" << 'MANIFEST_EOF'
DEP_N01
DEP_N02
DEP_N03
DEP_N04
DEP_N05
DEP_N06
DEP_N07
DEP_N08
DEP_N09
DEP_N10
DEP_N11
DEP_N12
DEP_N13
DEP_N14
DEP_N15
DEP_N16
DEP_N17
DEP_N18
DEP_N19
DEP_N20
DEP_N21
DEP_N22
DEP_N23
DEP_P01
DEP_P02
DEP_P03
DEP_V01
DEP_V02
MIG_N01
MIG_N02
MIG_N03
MIG_N04
MIG_N05
MIG_P01
MIG_V01
SRC_N01
SRC_N02
SRC_N03
SRC_N04
SRC_N05
SRC_N06
SRC_N07
SRC_N08
SRC_N09
SRC_N10
SRC_N11
SRC_N12
SRC_N13
SRC_N14
SRC_N15
SRC_N16
SRC_N17
SRC_N18
SRC_N19
SRC_N20
SRC_N21
SRC_N22
SRC_N23
SRC_P01
SRC_P02
SRC_P03
SRC_V01
SRC_V02
MANIFEST_EOF

sort "$EXPECTED_MANIFEST" > "$TEST_DIR/expected_sorted"
sort "$TEST_DIR/case_ids" > "$TEST_DIR/actual_sorted"

EXPECTED_LINES=$(wc -l < "$TEST_DIR/expected_sorted")
ACTUAL_LINES=$(wc -l < "$TEST_DIR/actual_sorted")

PRODUCT_CASE_COUNT="$ACTUAL_LINES"

if [ "$EXPECTED_LINES" -ne 63 ]; then
  echo "FAIL: Manifest expected line count is $EXPECTED_LINES, expected 63" >&2
  exit 1
fi
if [ "$ACTUAL_LINES" -ne "$EXPECTED_LINES" ]; then
  echo "FAIL: Case count mismatch. Expected $EXPECTED_LINES, got $ACTUAL_LINES" >&2
  echo "Missing:" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^<' || true
  echo "Extra:" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^>' || true
  exit 1
fi
if ! cmp -s "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted"; then
  echo "FAIL: Case ID manifest mismatch" >&2
  echo "Missing:" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^<' || true
  echo "Extra:" >&2
  diff "$TEST_DIR/expected_sorted" "$TEST_DIR/actual_sorted" | grep '^>' || true
  exit 1
fi

# Self-test manifest verification
EXPECTED_SELF_MANIFEST="$TEST_DIR/expected_self_manifest.txt"
cat > "$EXPECTED_SELF_MANIFEST" << 'SELF_MANIFEST_EOF'
SELF01_EXTRA_ARGV
SELF02_ARGV_REORDER
SELF03_TARGETS_SWAPPED
SELF04_NO_TARGET
SELF05_CONCAT_ARGV
SELF06_DOUBLE_CALL
SELF07_TAB_AFTER_BYPASS
SELF08_UPPER_REGEX
SELF09_NO_ANCHOR
SELF10_RAW_COMMAND_IN_STDERR
SELF_MANIFEST_EOF

sort "$EXPECTED_SELF_MANIFEST" > "$TEST_DIR/expected_self_sorted"
sort "$SELF_TEST_MANIFEST" > "$TEST_DIR/actual_self_sorted"

SELF_EXPECTED_LINES=$(wc -l < "$TEST_DIR/expected_self_sorted")
SELF_ACTUAL_LINES=$(wc -l < "$TEST_DIR/actual_self_sorted")

if [ "$SELF_EXPECTED_LINES" -ne 10 ]; then
  echo "FAIL: Self-test manifest expected $SELF_EXPECTED_LINES, expected 10" >&2
  exit 1
fi
if [ "$SELF_ACTUAL_LINES" -ne "$SELF_EXPECTED_LINES" ]; then
  echo "FAIL: Self-test count mismatch. Expected $SELF_EXPECTED_LINES, got $SELF_ACTUAL_LINES" >&2
  exit 1
fi
if ! cmp -s "$TEST_DIR/expected_self_sorted" "$TEST_DIR/actual_self_sorted"; then
  echo "FAIL: Self-test ID manifest mismatch" >&2
  exit 1
fi

# ----------------------------------------------------------------------
# 12. Output safety scan
# ----------------------------------------------------------------------

# Check no output file contains raw SHA, sentinel path, or other hostile strings
for f in "$TEST_DIR"/outputs/*.stdout "$TEST_DIR"/outputs/*.stderr; do
  [ -f "$f" ] || continue
  # Reject any SHA content in outputs (self10 output stored outside this dir)
  if grep -Fq "$DEP_SHA" "$f" 2>/dev/null; then
    echo "FAIL: SHA found in output: $f" >&2
    exit 1
  fi
  # Reject sentinel path in any output
  if grep -Fq "$SENTINEL_PATH" "$f" 2>/dev/null; then
    echo "FAIL: Sentinel path found in output: $f" >&2
    exit 1
  fi
done

# Final sentinel check (belt-and-suspenders)
if [ -f "$SENTINEL_PATH" ]; then
  echo "FAIL: Sentinel file present after output scan — shell injection" >&2
  exit 1
fi

echo "PASS: Output safety scan — no hostile content detected"

# ----------------------------------------------------------------------
# 13. Cleanup and exit
# ----------------------------------------------------------------------
echo ""
echo "All $PRODUCT_CASE_COUNT test-prod-github-wrapper product cases passed!"
echo "All $(wc -l < "$TEST_DIR/actual_self_sorted") self-tests passed!"
exit 0
# END_BLOCK: WRAPPER_TESTS
