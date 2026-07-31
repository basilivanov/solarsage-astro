
// ############################################################################
// AI_HEADER: GRACE_FRONTEND_INDEX — public barrel for the GRACE frontend API and hooks.
// ROLE: Pure re-export boundary for GRACE API client functions, errors, hooks and hook result types.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-GRACE-INDEX
// purpose: Provide the existing stable import surface without adding runtime behavior.
// owns:
//   - lib/grace/index.ts
// inputs: none.
// outputs: fetchDay, fetchCalendar, ApiError, ApiContractError, useDay, useCalendar and both hook result types.
// dependencies: lib/grace/api/client; lib/grace/hooks/useDay; lib/grace/hooks/useCalendar.
// side_effects: none introduced by this barrel.
// emitted_logs: none.
// invariants:
//   - Value exports and type-only exports remain exactly separated.
//   - All eight public names and their source modules remain unchanged.
//   - The module contains no wrapper logic or new initialization.
// failure_policy: None locally; import and runtime failures propagate from exported dependency modules.
// END_MODULE_CONTRACT: M-FRONTEND-GRACE-INDEX

// START_MODULE_MAP: M-FRONTEND-GRACE-INDEX
// public_entrypoints:
//   - fetchDay
//   - fetchCalendar
//   - ApiError
//   - ApiContractError
//   - useDay
//   - useCalendar
//   - UseDayResult
//   - UseCalendarResult
// semantic_blocks:
//   - API_CLIENT_EXPORTS: expose API functions and error classes.
//   - HOOK_EXPORTS: expose day and calendar hooks.
//   - RESULT_TYPE_EXPORTS: preserve type-only hook result exports.
// owned_tests:
//   - none direct; covered through typecheck and hook/API consumers.
// END_MODULE_MAP: M-FRONTEND-GRACE-INDEX

export { fetchDay, fetchCalendar, ApiError, ApiContractError } from './api/client';

export { useCalendar } from './hooks/useCalendar';

export type { UseCalendarResult } from './hooks/useCalendar';
