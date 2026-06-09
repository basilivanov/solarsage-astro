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
