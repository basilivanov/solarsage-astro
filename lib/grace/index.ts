
// ############################################################################
// AI_HEADER: MODULE_GRACE_INDEX
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-LOGGING-SPINE
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/grace/index.ts
// owns:
//   - lib/grace/index.ts
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

// AI_HEADER
// module: M-WEB-GRACE-INDEX
// wave: W-2.1
// purpose: Barrel export for GRACE frontend modules

export { fetchDay, fetchCalendar, ApiError } from './api/client';
export { useDay } from './hooks/useDay';
export { useCalendar } from './hooks/useCalendar';
export type { UseDayResult } from './hooks/useDay';
export type { UseCalendarResult } from './hooks/useCalendar';
