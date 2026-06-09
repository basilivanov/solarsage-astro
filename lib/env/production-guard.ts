// ############################################################################
// AI_HEADER: MODULE_PRODUCTION_GUARD_TS
// ROLE: TypeScript wrapper for production environment safety guard.
// DEPENDENCIES: ./production-guard.mjs
// GRACE_ANCHORS: [SAFETY_CHECK_TS]
// ############################################################################

// @ts-expect-error - importing mjs file
import { assertProductionSafety as _assertProductionSafety } from "./production-guard.mjs";

/* START_BLOCK: SAFETY_CHECK_TS */
export function assertProductionSafety(): void {
  _assertProductionSafety();
}
/* END_BLOCK: SAFETY_CHECK_TS */
