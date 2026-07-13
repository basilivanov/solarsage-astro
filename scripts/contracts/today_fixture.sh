#!/usr/bin/env bash

# ############################################################################
# AI_HEADER: MODULE_TODAY_FIXTURE_WRAPPER — shell wrapper for today fixture normalization.
# ROLE: Provides a repo-portable wrapper to execute normalize_today_fixture.py.
# DEPENDENCIES: bash, python
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-FIXTURE-WRAPPER
# purpose: Portable shell entrypoint for fixture normalization.
# owns:
#   - scripts/contracts/today_fixture.sh
# inputs: CLI arguments (accepts no args or exactly --check)
# outputs: exit codes, stdout, stderr
# dependencies: bash, standard CLI utilities, normalize_today_fixture.py
# side_effects:
#   - today_fixture.sh in normal mode can atomically write/overwrite the canonical JSON fixture file.
#   - today_fixture.sh --check does not write files.
# emitted_logs: none.
# invariants:
#   - uses set -euo pipefail
#   - resolves repository root and python executable correctly
# failure_policy: usage error -> exit 2; otherwise propagates normalizer non-zero status
# END_MODULE_CONTRACT: M-TODAY-FIXTURE-WRAPPER

# START_MODULE_MAP: M-TODAY-FIXTURE-WRAPPER
# public_entrypoints:
#   - today_fixture.sh
# semantic_blocks:
#   - EXECUTION: python execution mapping.
# END_MODULE_MAP: M-TODAY-FIXTURE-WRAPPER

# START_BLOCK: EXECUTION
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if [[ -x "apps/api/.venv/bin/python" ]]; then
  PYTHON="apps/api/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

# Always target the canonical JSON path by default if no path is given
if [ "$#" -eq 0 ]; then
  "$PYTHON" scripts/contracts/normalize_today_fixture.py e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
elif [ "$#" -eq 1 ] && [ "$1" = "--check" ]; then
  "$PYTHON" scripts/contracts/normalize_today_fixture.py e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json --check
else
  echo "Usage: $0 [--check]" >&2
  exit 2
fi
# END_BLOCK: EXECUTION
