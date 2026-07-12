#!/usr/bin/env bash

# ############################################################################
# AI_HEADER: MODULE_CONTRACTS_CHECK — unified contracts drift check script.
# ROLE: Verifies shared/registry/compat guards, generation, fixture normalization, and generated diff.
# DEPENDENCIES: bash, git, standard utils
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS-CHECK
# purpose: Check shared Python contract guards, registry/compat unit tests,
#   deterministic generation, JSON fixture normalization, and generated artifact drift.
# owns:
#   - scripts/contracts/check.sh
# inputs: none.
# outputs: exit codes, stdout, stderr
# dependencies: pytest, generate.sh, today_fixture.sh, git diff
# side_effects:
#   - check.sh runs generate.sh which can write generated contract files.
#   - check.sh does not normalize the visual JSON fixture automatically.
# emitted_logs: none.
# invariants:
#   - uses set -euo pipefail
#   - drift detection exits non-zero on subprocess failures
# failure_policy: propagates the first non-zero focused test, generator, fixture-check, or diff status.
# END_MODULE_CONTRACT: M-CONTRACTS-CHECK

# START_MODULE_MAP: M-CONTRACTS-CHECK
# public_entrypoints:
#   - check.sh
# semantic_blocks:
#   - CHECK_PIPELINE: run focused tests, generate, check fixture, diff generated files.
# END_MODULE_MAP: M-CONTRACTS-CHECK

# START_BLOCK: CHECK_PIPELINE
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ -x "apps/api/.venv/bin/python" ]]; then
  PYTHON="apps/api/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

echo "check.sh: 1. running focused contract tests..."
"$PYTHON" -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  scripts/contracts/test_check_compat.py \
  -q

echo "check.sh: 2. running generate.sh..."
bash scripts/contracts/generate.sh

echo "check.sh: 3. checking JSON fixture normalization..."
bash scripts/contracts/today_fixture.sh --check

echo "check.sh: 4. checking git diff for generated contract files..."
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts

echo "check.sh: all checks passed successfully."
# END_BLOCK: CHECK_PIPELINE
