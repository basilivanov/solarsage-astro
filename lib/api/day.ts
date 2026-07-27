// ############################################################################
// AI_HEADER: MODULE_FRONTEND_API_DAY
// ROLE: Types and re-exports for relative day status models on the frontend.
// DEPENDENCIES: packages/contracts RelativeDayStatusRead, RelativeStatusBaseline
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-DAY
// purpose: Relative day status type definitions for frontend components.
// owns:
//   - lib/api/day.ts
// inputs: none
// outputs: RelativeDayStatus type alias, RelativeStatusBaseline
// dependencies: packages/contracts
// side_effects: none (pure types)
// failure_policy: none
// END_MODULE_CONTRACT: M-FRONTEND-API-DAY

// START_MODULE_MAP: M-FRONTEND-API-DAY
// public_entrypoints:
//   - RelativeDayStatus
//   - RelativeStatusBaseline
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-FRONTEND-API-DAY

import type { RelativeDayStatusRead, RelativeStatusBaseline } from "@/packages/contracts"

export type RelativeDayStatus = RelativeDayStatusRead
export type { RelativeStatusBaseline }
