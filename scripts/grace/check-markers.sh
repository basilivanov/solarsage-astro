#!/usr/bin/env bash

// ############################################################################
// AI_HEADER: MODULE_GRACE_CHECK_MARKERS
// ROLE: Tooling script
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-GUARDRAILS-TOOLING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Tooling script — scripts/grace/check-markers.sh
// owns:
//   - scripts/grace/check-markers.sh
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$ROOT/scripts/grace_front_lint.py"
