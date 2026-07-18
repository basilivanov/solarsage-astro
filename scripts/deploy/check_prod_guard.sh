#!/usr/bin/env bash
# START_MODULE_CONTRACT
# purpose: Tooling script — scripts/deploy/check_prod_guard.sh
# owns:
#   - scripts/deploy/check_prod_guard.sh
# inputs: CLI arguments, environment variables
# outputs: exit codes, stdout, stderr
# dependencies: bash, standard CLI utils
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: exit 1 on error
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - export: default
#     contract: main export
# END_MODULE_MAP

# ############################################################################
# AI_HEADER: SCRIPT_CHECK_PROD_GUARD
# ROLE: Validate production environment config safety.
# DEPENDENCIES: bash, grep
# GRACE_ANCHORS: [PROD_GUARD]
# ############################################################################

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=== guardrails:prod ==="

# 1. Fail-closed: Verify that no .env.production path exists in the repository root
# (regular file, symlink, broken symlink, FIFO, directory, etc. are all strictly forbidden)
if [ -e "$ROOT/.env.production" ] || [ -L "$ROOT/.env.production" ]; then
  echo "ERROR: Unsafe path .env.production exists in repository root. Production configuration must live only under /etc/solarsage/env/"
  exit 1
fi

# 2. Verify that .env.example doesn't have NEXT_PUBLIC_DEMO_MODE=true
if grep -q "NEXT_PUBLIC_DEMO_MODE=true" "$ROOT/.env.example"; then
  echo "ERROR: Unsafe NEXT_PUBLIC_DEMO_MODE=true found in .env.example"
  exit 1
fi

# 3. Check for raw demo data usage in frontend app/ directory (should not import demo-data directly)
if [ -d "$ROOT/app" ]; then
  # Find any references to DEMO_ data in app/
  if grep -r "DEMO_TODAY_RESPONSE\|DEMO_CALENDAR_RESPONSE\|DEMO_PROFILE" "$ROOT/app/" --exclude-dir=node_modules 2>/dev/null; then
    echo "ERROR: Raw demo payload imported directly inside app/ page components."
    exit 1
  fi
fi

