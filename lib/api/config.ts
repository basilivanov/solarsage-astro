
// ############################################################################
// AI_HEADER: MODULE_API_CONFIG
// ROLE: UI — config
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: UI config — component
// owns:
//   - lib/api/config.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * API layer configuration — canonical Telegram auth path only.
 * No fixtures, no mocks, no stubs.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "/api"
