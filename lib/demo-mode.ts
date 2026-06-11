// START_MODULE_CONTRACT
// purpose: UI demo-mode
// owns:
//   - lib/demo-mode.ts
// inputs: Props / hook params
// outputs: TSX / return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
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
// AI_HEADER: MODULE_DEMO_MODE
// ROLE: Resolve and gate demo/mock mode flag for local development.
// DEPENDENCIES: ./env/production-guard
// GRACE_ANCHORS: [DEMO_MODE_RESOLVE]
// ############################################################################

import { assertProductionSafety } from "./env/production-guard";

/* START_BLOCK: DEMO_MODE_RESOLVE */
export function resolveDemoMode(): boolean {
  assertProductionSafety();
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
}

// Retained for backward compatibility
export const IS_DEMO_MODE = resolveDemoMode()// START_MODULE_CONTRACT
// purpose: UI demo-mode — component
// owns:
//   - lib/demo-mode.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// ############################################################################
// AI_HEADER: MODULE_DEMO_MODE
// ROLE: Resolve and gate demo/mock mode flag for local development.
// DEPENDENCIES: ./env/production-guard
// GRACE_ANCHORS: [DEMO_MODE_RESOLVE]
// ############################################################################

import { assertProductionSafety } from "./env/production-guard";

/* START_BLOCK: DEMO_MODE_RESOLVE */
export function resolveDemoMode(): boolean {
  assertProductionSafety();
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true";
}

// Retained for backward compatibility
export const IS_DEMO_MODE = resolveDemoMode();
/* END_BLOCK: DEMO_MODE_RESOLVE */
