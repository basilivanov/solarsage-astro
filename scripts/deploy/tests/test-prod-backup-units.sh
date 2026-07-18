#!/usr/bin/env bash
# ############################################################################
# AI_HEADER: TEST_PROD_BACKUP_UNITS — Unit-template regression test for systemd units
# ROLE: Verifies that exact timeout properties are present in systemd service configurations.
# DEPENDENCIES: bash, grep, systemd-analyze
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROD-BACKUP-UNITS
# purpose: Verify that systemd units contain correct TimeoutStartSec and TimeoutStopSec values.
# owns:
#   - scripts/deploy/tests/test-prod-backup-units.sh
# inputs: none
# outputs:
#   - exit 0 on success, non-zero on failure
# dependencies: none
# invariants: none
# failure_policy: fails non-zero on test failures.
# END_MODULE_CONTRACT: M-TEST-PROD-BACKUP-UNITS

# START_MODULE_MAP: M-TEST-PROD-BACKUP-UNITS
# public_entrypoints:
#   - main
# semantic_blocks:
#   - UNITS_TEST: test implementation
# END_MODULE_MAP: M-TEST-PROD-BACKUP-UNITS

# START_BLOCK: UNITS_TEST
set -euo pipefail
umask 027

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

check_timeout() {
  local file="$1"
  local start_timeout="$2"
  local stop_timeout="$3"

  if [ ! -f "$file" ]; then
    echo "Error: Service unit file '$file' is missing." >&2
    exit 1
  fi

  if ! grep -q "^TimeoutStartSec=$start_timeout" "$file"; then
    echo "FAIL: '$file' does not contain exact 'TimeoutStartSec=$start_timeout'" >&2
    exit 1
  fi

  if ! grep -q "^TimeoutStopSec=$stop_timeout" "$file"; then
    echo "FAIL: '$file' does not contain exact 'TimeoutStopSec=$stop_timeout'" >&2
    exit 1
  fi
}

echo "Verifying service unit timeouts (canonical backup pair only)..."
check_timeout "$REPO_ROOT/infra/systemd/solarsage-backup.service" "3h" "2min"

echo "Running systemd-analyze verify on the canonical backup pair..."
# The canonical backup service references the installed orchestrator (a
# host-prepare install prerequisite); verify a sandbox copy with a staged
# ExecStart and the sibling DB unit for dependency resolution.
STAGED_DIR=$(mktemp -d "/tmp/solarsage-backup-units.XXXXXX")
trap 'rm -rf "$STAGED_DIR"' EXIT
mkdir -p "$STAGED_DIR/libexec"
cp "$REPO_ROOT/scripts/deploy/prod-orchestrator.sh" "$STAGED_DIR/libexec/prod-orchestrator"
chmod 0755 "$STAGED_DIR/libexec/prod-orchestrator"
cp "$REPO_ROOT/infra/systemd/solarsage-db.service" "$STAGED_DIR/solarsage-db.service"
cp "$REPO_ROOT/infra/systemd/solarsage-backup.timer" "$STAGED_DIR/solarsage-backup.timer"
sed "s|/usr/local/libexec/solarsage/prod-orchestrator|$STAGED_DIR/libexec/prod-orchestrator|g" \
  "$REPO_ROOT/infra/systemd/solarsage-backup.service" > "$STAGED_DIR/solarsage-backup.service"
if ! systemd-analyze verify \
  "$STAGED_DIR/solarsage-backup.service" \
  "$STAGED_DIR/solarsage-backup.timer" >/dev/null 2>&1; then
  echo "FAIL: systemd-analyze verify failed for canonical backup units (staged)" >&2
  exit 1
fi

echo "SUCCESS: test-prod-backup-units.sh passed!"
exit 0
# END_BLOCK: UNITS_TEST
