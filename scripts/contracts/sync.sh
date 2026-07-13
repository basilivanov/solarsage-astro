#!/usr/bin/env bash

# ############################################################################
# AI_HEADER: MODULE_CONTRACTS_SYNC — intentional contract sync pipeline.
# ROLE: Runs focused contract guards, generation, compatibility, Vitest contracts, typecheck, and diff summary.
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS-SYNC
# purpose: Provide one developer command for intentional contract regeneration
#   with compatibility classification and frontend contract validation.
# owns:
#   - scripts/contracts/sync.sh
# inputs: CONTRACT_BASE_REF/PYTHON environment variables and repository files.
# outputs: stdout/stderr status and optional generated file modifications from generation.
# dependencies: pytest, scripts/contracts/generate.sh, check_compat.py, vitest, tsc, git diff.
# side_effects:
#   - runs generate.sh which rewrites generated contract artifacts deterministically.
#   - writes and removes a temporary compatibility JSON report.
# emitted_logs: none.
# invariants:
#   - does not stage, commit, restore, or require clean generated diff.
#   - removes temp report via trap.
# failure_policy: propagates first failed command.
# END_MODULE_CONTRACT: M-CONTRACTS-SYNC

# START_MODULE_MAP: M-CONTRACTS-SYNC
# public_entrypoints:
#   - sync.sh
# semantic_blocks:
#   - SYNC_PIPELINE: focused tests, generation, compatibility, Vitest, typecheck, generated diff stat.
# owned_tests:
#   - scripts/contracts/test_check_compat.py
#   - apps/api/tests/test_contract_registry.py
# END_MODULE_MAP: M-CONTRACTS-SYNC

# START_BLOCK: SYNC_PIPELINE
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ -x "apps/api/.venv/bin/python" ]]; then
  PYTHON_BIN="apps/api/.venv/bin/python"
else
  PYTHON_BIN="${PYTHON:-python3}"
fi

compat_report="$(mktemp)"
trap 'rm -f "$compat_report"' EXIT

echo "sync.sh: 1. running focused contract tests..."
"$PYTHON_BIN" -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  scripts/contracts/test_check_compat.py \
  -q

echo "sync.sh: 2. regenerating contracts..."
bash scripts/contracts/generate.sh

echo "sync.sh: 3. checking real compatibility..."
"$PYTHON_BIN" scripts/contracts/check_compat.py --json-output "$compat_report"

echo "sync.sh: 4. running contract Vitest suites..."
npx vitest run __tests__/contracts

echo "sync.sh: 5. running TypeScript typecheck..."
npx tsc --noEmit

echo "sync.sh: 6. generated contract diff stat..."
git diff --stat -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts

echo "sync.sh: compatibility report: $compat_report"
echo "sync.sh: completed successfully."
# END_BLOCK: SYNC_PIPELINE
