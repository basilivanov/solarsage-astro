#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_PATH_TRANSACTION — Test suite for path transaction library
# ROLE: Verifies correctness of state capture, rollback, and cleanup.
# DEPENDENCIES: bash, mktemp, stat, cmp, rm, mv, ln, chown, chmod
# ############################################################################

set -euo pipefail
umask 027

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Source the library (verifying library as regular non-symlink)
LIB_PATH="$REPO_ROOT/scripts/deploy/lib/prod-path-transaction.sh"
if [ ! -f "$LIB_PATH" ] || [ -L "$LIB_PATH" ]; then
  echo "Error: Library not found at $LIB_PATH or is a symlink" >&2
  exit 1
fi
source "$LIB_PATH"

# Create a safe temp base directory for testing (no sudo required)
TEST_BASE=$(mktemp -d "/tmp/solarsage-tx-test-XXXXXX")
chmod 0700 "$TEST_BASE"

# Clean up test base on exit
trap 'rm -rf "$TEST_BASE"' EXIT

# Sandbox paths
FILE_A="$TEST_BASE/file_a.conf"
SYMLINK_B="$TEST_BASE/symlink_b.conf"
DANGLING_C="$TEST_BASE/dangling_c.conf"
MISSING_D="$TEST_BASE/missing_d.conf"
DIR_E="$TEST_BASE/dir_e"

# Initialize sandbox files
echo "content-a" > "$FILE_A"
chmod 0640 "$FILE_A"

# Ordinary symlink must have relative raw target
ln -sf "file_a.conf" "$SYMLINK_B"
ln -sf "nonexistent-target" "$DANGLING_C"

# Register paths in library
PROD_TX_PATHS["file_a"]="$FILE_A"
PROD_TX_PATHS["symlink_b"]="$SYMLINK_B"
PROD_TX_PATHS["dangling_c"]="$DANGLING_C"
PROD_TX_PATHS["missing_d"]="$MISSING_D"

# Test 1: Capture
echo "Test 1: Capturing sandbox state..."
if ! prod_tx_capture "$TEST_BASE"; then
  echo "FAIL: prod_tx_capture failed"
  exit 1
fi

# Test 2: Mutation
echo "Test 2: Mutating sandbox files..."
echo "mutated-content-a" > "$FILE_A"
chmod 0755 "$FILE_A"

rm -f "$SYMLINK_B"
echo "mutated-symlink-is-now-regular" > "$SYMLINK_B"

rm -f "$DANGLING_C"
echo "mutated-dangling-is-now-regular" > "$DANGLING_C"

echo "mutated-missing-file" > "$MISSING_D"

# Test 3: Rollback
echo "Test 3: Executing rollback..."
if ! prod_tx_rollback; then
  echo "FAIL: prod_tx_rollback failed"
  exit 1
fi

# Test 4: Verifying state restoration
echo "Test 4: Verifying correctness..."
# Check FILE_A
if [ "$(cat "$FILE_A")" != "content-a" ]; then
  echo "FAIL: FILE_A content mismatch"
  exit 1
fi
if [ "$(stat -c "%a" "$FILE_A")" != "640" ]; then
  echo "FAIL: FILE_A mode mismatch"
  exit 1
fi
# Check restored numeric uid/gid
EXPECTED_UID=$(id -u)
EXPECTED_GID=$(id -g)
if [ "$(stat -c "%u" "$FILE_A")" != "$EXPECTED_UID" ] || [ "$(stat -c "%g" "$FILE_A")" != "$EXPECTED_GID" ]; then
  echo "FAIL: FILE_A uid/gid mismatch"
  exit 1
fi

# Check SYMLINK_B (relative raw target)
if [ ! -L "$SYMLINK_B" ]; then
  echo "FAIL: SYMLINK_B is not a symlink"
  exit 1
fi
if [ "$(readlink "$SYMLINK_B")" != "file_a.conf" ]; then
  echo "FAIL: SYMLINK_B target mismatch (expected relative 'file_a.conf', got '$(readlink "$SYMLINK_B")')"
  exit 1
fi
if [ "$(stat -c "%u" "$SYMLINK_B")" != "$EXPECTED_UID" ] || [ "$(stat -c "%g" "$SYMLINK_B")" != "$EXPECTED_GID" ]; then
  echo "FAIL: SYMLINK_B uid/gid mismatch"
  exit 1
fi

# Check DANGLING_C
if [ ! -L "$DANGLING_C" ]; then
  echo "FAIL: DANGLING_C is not a symlink"
  exit 1
fi
if [ "$(readlink "$DANGLING_C")" != "nonexistent-target" ]; then
  echo "FAIL: DANGLING_C target mismatch"
  exit 1
fi

# Check MISSING_D is absent
if [ -e "$MISSING_D" ] || [ -L "$MISSING_D" ]; then
  echo "FAIL: MISSING_D was not deleted"
  exit 1
fi

# Test 5: Rejection of unexpected directory types
echo "Test 5: Testing unexpected directory capture/rollback rejection..."
# Reset transaction state
prod_tx_cleanup

mkdir -p "$DIR_E"
# Register E
PROD_TX_PATHS["dir_e"]="$DIR_E"

# Capture should fail because E is a directory (unsupported type)
if prod_tx_capture "$TEST_BASE"; then
  echo "FAIL: prod_tx_capture succeeded for directory (expected failure)"
  exit 1
fi

# Test 6: Two-phase rollback validation check (with directory candidate replacement)
echo "Test 6: Verifying two-phase rollback candidate verification..."
prod_tx_cleanup

# Reset sandbox
echo "content-a" > "$FILE_A"
chmod 0640 "$FILE_A"
PROD_TX_PATHS["file_a"]="$FILE_A"

# Capture valid state
if ! prod_tx_capture "$TEST_BASE"; then
  echo "FAIL: capture failed"
  exit 1
fi

# Mutate candidate to a directory
rm -f "$FILE_A"
mkdir -p "$FILE_A"

# Rollback should fail in Phase 1 (verification) and NOT delete or modify any other path
# We check that the snapshot directory is preserved on rollback failure
local_tx_dir="$PROD_TX_TEMP_DIR"
if prod_tx_rollback; then
  echo "FAIL: rollback succeeded despite directory candidate (expected failure)"
  exit 1
fi

# Verify snapshot directory is preserved
if [ -z "$local_tx_dir" ] || [ ! -d "$local_tx_dir" ]; then
  echo "FAIL: snapshot directory was cleaned up on rollback failure (must be preserved for manual recovery)"
  exit 1
fi

# Clean up FILE_A directory so trap cleanup can run cleanly
rm -rf "$FILE_A"

# Test 7: Cleanup test
echo "Test 7: Verifying cleanup..."
prod_tx_cleanup
# Verify no temp dirs are left in test base (except the base itself)
if ls "$TEST_BASE" | grep -q "solarsage-tx-"; then
  echo "FAIL: temp directories were not cleaned up"
  exit 1
fi

# Test 8: Double cleanup safety
echo "Test 8: Verifying double cleanup safety..."
prod_tx_cleanup
prod_tx_cleanup

echo "SUCCESS: All path transaction tests passed!"
exit 0
