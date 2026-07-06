
// ############################################################################
// AI_HEADER: MODULE_API_CALENDAR
// ROLE: Tests — calendar.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: Tests for calendar.ts behavior
// owns:
//   - lib/api/calendar.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT// AI_HEADER
// module: M-API-CALENDAR
// wave: W-2.7
// purpose: Calendar API facade

import {
  type DayStatus,
  type DayStatusMap,
} from "@/lib/contracts/calendar"
import type { CalendarPayload } from "@/packages/contracts"

export type { DayStatus, DayStatusMap }
export type { CalendarPayload }

function normalizeDayStatus(raw: string | null | undefined): DayStatus {
  if (raw === "supportive" || raw === "tense") return raw
  return "even"
}

export async function getDayStatus(date: Date): Promise<DayStatus> {
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
    map[day.date] = normalizeDayStatus(day.dayStatus)
  }
  return map
}

export async function getMonthCalendar(year: number, month: number): Promise<CalendarPayload> {
  const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`
  const res = await fetch(`/api/calendar?month=${monthStr}`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  return res.json() as Promise<CalendarPayload>
}

export const getDayStatusAsync = getDayStatus
export const getMonthStatusesAsync = getMonthStatuses
export const getMonthCalendarAsync = getMonthCalendar
