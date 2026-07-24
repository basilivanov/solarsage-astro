// ############################################################################
// AI_HEADER: FRONTEND_API_CALENDAR — calendar and day-status fetch facade.
// ROLE: Calendar/day-status facade used by day, calendar and week-strip consumers.
// DEPENDENCIES: lib/contracts/calendar; packages/contracts/runtime TodayPayloadWireSchema; lib/log/instrumented-fetch.
// GRACE_ANCHORS: [FRONTEND_API_CALENDAR]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CALENDAR
// purpose: Fetch one-day status or validated monthly calendar and derive status maps via instrumentedFetch.
// owns:
//   - lib/api/calendar.ts
// inputs: Date; zero-based year/month pair.
// outputs: exported calendar/status types, day status, month status map, CalendarPayloadReadModel and Async aliases.
// dependencies: lib/contracts/calendar; packages/contracts/runtime TodayPayloadWireSchema; lib/log/instrumented-fetch.
// side_effects: credentialed GET /api/day/{date} and /api/calendar?month=YYYY-MM via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
// invariants:
//   - supportive and tense pass through; steady maps to even; other values map null.
//   - The month argument remains zero-based and is converted with +1.
//   - Monthly payload remains validated by validateCalendarPayloadReadModel.
//   - Async aliases remain reference-equal to canonical functions.
// failure_policy: Throw API error with the HTTP status for non-ok responses.
// END_MODULE_CONTRACT: M-FRONTEND-API-CALENDAR

// START_MODULE_MAP: M-FRONTEND-API-CALENDAR
// public_entrypoints:
//   - DayStatus
//   - DayStatusMap
//   - CalendarPayload
//   - getDayStatus
//   - getMonthStatuses
//   - getMonthCalendar
//   - getDayStatusAsync
//   - getMonthStatusesAsync
//   - getMonthCalendarAsync
// semantic_blocks:
//   - STATUS_NORMALIZATION: normalize backend status vocabulary.
//   - DAY_FETCH: fetch and normalize one day status via instrumentedFetch.
//   - MONTH_STATUS_DERIVATION: derive a keyed status map from a month payload.
//   - MONTH_FETCH: fetch and validate a zero-based requested month via instrumentedFetch.
//   - COMPATIBILITY_ALIASES: retain reference-equal Async exports.
// owned_tests:
//   - __tests__/api/calendar.test.ts
//   - __tests__/components/CalendarScreen.test.tsx
//   - __tests__/components/WeekStrip.test.tsx
//   - __tests__/app/day-page.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-CALENDAR

import {
  type DayStatus,
  type DayStatusMap,
  type CalendarPayloadReadModel,
  CalendarPayloadReadModelSchema,
  validateCalendarPayloadReadModel,
} from "@/lib/contracts/calendar"
import type { CalendarPayload } from "@/packages/contracts"
import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export type { DayStatus, DayStatusMap }
export type { CalendarPayload }

// START_BLOCK: STATUS_NORMALIZATION
function normalizeDayStatus(raw: string | null | undefined): DayStatus | null {
  if (raw === "supportive" || raw === "tense") return raw
  if (raw === "steady") return "even"
  return null
}
// END_BLOCK: STATUS_NORMALIZATION

// START_BLOCK: DAY_FETCH
export async function getDayStatus(date: Date): Promise<DayStatus | null> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getDayStatus
  // purpose: Fetch single day status via instrumentedFetch with TodayPayload responseContract and normalize status vocabulary.
  // inputs: date — Date object
  // returns: Promise<DayStatus | null>
  // side_effects: GET /api/day/{date} via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getDayStatus
  const dateStr = date.toISOString().split("T")[0]
  const res = await instrumentedFetch({
    operation: "calendar.day_status",
    routeTemplate: "GET /api/day/{date}",
    url: `/api/day/${dateStr}`,
    init: {
      credentials: "include",
      headers: { "Accept": "application/json" },
    },
    responseContract: {
      contractName: "TodayPayload",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = TodayPayloadWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  const raw = await res.json()
  const payload = TodayPayloadWireSchema.parse(raw)
  return normalizeDayStatus(payload.dayStatus)
}
// END_BLOCK: DAY_FETCH

// START_BLOCK: MONTH_STATUS_DERIVATION
export async function getMonthStatuses(year: number, month: number): Promise<DayStatusMap> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthStatuses
  // purpose: Derive a keyed status map from getMonthCalendar.
  // inputs: year — YYYY, month — 0-indexed month (0..11)
  // returns: Promise<DayStatusMap>
  // side_effects: calls getMonthCalendar
  // emitted_logs: none
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthStatuses
  const body = await getMonthCalendar(year, month)
  const map: DayStatusMap = {}
  for (const day of body.days ?? []) {
    const status = normalizeDayStatus(day.dayStatus)
    if (status !== null) {
      map[day.date] = status
    }
  }
  return map
}
// END_BLOCK: MONTH_STATUS_DERIVATION

// START_BLOCK: MONTH_FETCH
export async function getMonthCalendar(year: number, month: number): Promise<CalendarPayloadReadModel> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthCalendar
  // purpose: Fetch zero-based monthly calendar via instrumentedFetch with CalendarPayloadReadModel responseContract.
  // inputs: year — YYYY, month — 0-indexed month (0..11)
  // returns: Promise<CalendarPayloadReadModel>
  // side_effects: GET /api/calendar?month=YYYY-MM via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthCalendar
  const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`
  const res = await instrumentedFetch({
    operation: "calendar.month",
    routeTemplate: "GET /api/calendar",
    url: `/api/calendar?month=${monthStr}`,
    init: {
      credentials: "include",
      headers: { "Accept": "application/json" },
    },
    responseContract: {
      contractName: "CalendarPayloadReadModel",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = CalendarPayloadReadModelSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  return validateCalendarPayloadReadModel(await res.json())
}
// END_BLOCK: MONTH_FETCH

// START_BLOCK: COMPATIBILITY_ALIASES
export const getDayStatusAsync = getDayStatus
export const getMonthStatusesAsync = getMonthStatuses
export const getMonthCalendarAsync = getMonthCalendar
// END_BLOCK: COMPATIBILITY_ALIASES
