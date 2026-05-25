// @deprecated since W-1.1B. Do NOT add or modify shapes here.
// Source of truth is apps/api/app/schemas/calendar.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type { CalendarPayload as _CalendarPayload } from "./index";

export type CalendarPayload = _CalendarPayload;
export type CalendarDay = _CalendarPayload["days"][number];
export type { ContentAccessState, DayStatus } from "./today";
