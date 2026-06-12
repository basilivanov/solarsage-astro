
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CALENDAR
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Contract: calendar
// owns:
//   - packages/contracts/calendar.ts
// inputs: n/a (types)
// outputs: n/a (types)
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// @deprecated since W-1.1B. Do NOT add or modify shapes here.
// Source of truth is apps/api/app/schemas/calendar.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type { CalendarPayload as _CalendarPayload } from "./index";

export type CalendarPayload = _CalendarPayload;
export type CalendarDay = _CalendarPayload["days"][number];
export type { ContentAccessState, DayStatus } from "./today";
