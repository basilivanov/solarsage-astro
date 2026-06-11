
// ############################################################################
// AI_HEADER: MODULE_GRACE_INDEX
// ROLE: Lib — index.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-LOGGING-SPINE
// #########################################// START_MODULE_CONTRACT
// purpose: Library: index
// owns:
//   - lib/grace/index.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-GRACE-INDEX
// wave: W-2.1
// purpose: Barrel export for GRACE frontend modules

export { fetchDay, fetchCalendar, ApiError } from './api/client';
export { useDay } from './hooks/useDay';
export { useCalendar } from './hooks/useCalendar';
export type { UseDayResult } from './hooks/useDay';
export type { UseCalendarResult } from './hooks/useCalendar';
