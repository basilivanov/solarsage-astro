#!/usr/bin/env bash

# ############################################################################
# AI_HEADER: MODULE_GRACE_CHECK_MARKERS
# ROLE: Shell script for operations automation
# DEPENDENCIES: bash, standard utils
# GRACE_ANCHORS: [SCRIPT]
# SLICE: SLICE-GUARDRAILS-TOOLING
# ############################################################################
# START_MODULE_CONTRACT
# purpose: Tool: check-markers
# owns:
#   - scripts/grace/check-markers.sh
# inputs: CLI arguments, environment variables
# outputs: exit codes, stdout, stderr
# dependencies: bash, standard CLI utils
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: exit 1 on error
# END_MODULE_CONTRACT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/scripts/grace_front_lint.py"
