// START_MODULE_CONTRACT
// purpose: Library module — lib/env/production-guard.ts
// owns:
//   - lib/env/production-guard.ts
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

// ############################################################################
// AI_HEADER: MODULE_PRODUCTION_GUARD_TS
// ROLE: TypeScript wrapper for production environment safety guard.
// DEPENDENCIES: ./production-guard.mjs
// GRACE_ANCHORS: [SAFETY_CHECK_TS]
// ############################################################################

import { assertProductionSafety as _assertProductionSafety } from "./production-guard.mjs";

/* START_BLOCK: SAFETY_CHECK_TS */
export function assertProductionSafety(): void {
  _assertProductionSafety();
}
/* END_BLOCK: SAFETY_CHECK_TS */
