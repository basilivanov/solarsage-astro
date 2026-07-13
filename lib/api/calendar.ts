
// ############################################################################
// AI_HEADER: FRONTEND_API_CALENDAR — calendar and day-status fetch facade.
// ROLE: Calendar/day-status facade used by day, calendar and week-strip consumers.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CALENDAR
// purpose: Fetch one-day status or validated monthly calendar and derive status maps.
// owns:
//   - lib/api/calendar.ts
// inputs: Date; zero-based year/month pair.
// outputs: exported calendar/status types, day status, month status map, CalendarPayloadReadModel and Async aliases.
// dependencies: lib/contracts/calendar; packages/contracts CalendarPayload; fetch.
// side_effects: credentialed GET /api/day/:date and /api/calendar?month=YYYY-MM.
// emitted_logs: none.
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
//   - DAY_FETCH: fetch and normalize one day status.
//   - MONTH_STATUS_DERIVATION: derive a keyed status map from a month payload.
//   - MONTH_FETCH: fetch and validate a zero-based requested month.
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
  validateCalendarPayloadReadModel,
} from "@/lib/contracts/calendar"
import type { CalendarPayload } from "@/packages/contracts"

export type { DayStatus, DayStatusMap }
export type { CalendarPayload }

function normalizeDayStatus(raw: string | null | undefined): DayStatus | null {
  if (raw === "supportive" || raw === "tense") return raw
  if (raw === "steady") return "even"
  return null
}

export async function getDayStatus(date: Date): Promise<DayStatus | null> {
  const dateStr = date.toISOString().split("T")[0]
  const res = await fetch(`/api/day/${dateStr}`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  const body = await res.json() as { dayStatus?: string; day_status?: string }
  return normalizeDayStatus(body.dayStatus ?? body.day_status)
}

export async function getMonthStatuses(year: number, month: number): Promise<DayStatusMap> {
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

export async function getMonthCalendar(year: number, month: number): Promise<CalendarPayloadReadModel> {
  const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`
  const res = await fetch(`/api/calendar?month=${monthStr}`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  return validateCalendarPayloadReadModel(await res.json())
}

export const getDayStatusAsync = getDayStatus
export const getMonthStatusesAsync = getMonthStatuses
export const getMonthCalendarAsync = getMonthCalendar
