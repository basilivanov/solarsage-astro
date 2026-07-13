
// ############################################################################
// AI_HEADER: FRONTEND_API_CONFIG — canonical public API base URL constant.
// ROLE: Canonical frontend API base constant with no fixture or mock transport.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CONFIG
// purpose: Resolve API_BASE_URL from NEXT_PUBLIC_API_BASE_URL with /api fallback.
// owns:
//   - lib/api/config.ts
// inputs: build and runtime public environment.
// outputs: API_BASE_URL string constant.
// dependencies: process.env only.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Fallback remains exactly /api.
//   - The module contains no fixture, mock or stub selection.
// failure_policy: Missing environment configuration uses the fallback and does not throw.
// END_MODULE_CONTRACT: M-FRONTEND-API-CONFIG

// START_MODULE_MAP: M-FRONTEND-API-CONFIG
// public_entrypoints:
//   - API_BASE_URL
// semantic_blocks:
//   - API_BASE_RESOLUTION: select the public environment value or /api fallback.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-FRONTEND-API-CONFIG
/**
 * API layer configuration — canonical Telegram auth path only.
 * No fixtures, no mocks, no stubs.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "/api"
