
// ############################################################################
// AI_HEADER: MODULE_API_CALENDAR
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/api/calendar.ts
// owns:
//   - lib/api/calendar.ts
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
// module: M-API-CALENDAR
// wave: W-2.7
// purpose: Calendar API facade

import {
  type DayStatus,
  type DayStatusMap,
} from "@/lib/contracts/calendar"

export type { DayStatus, DayStatusMap }

interface BackendCalendarDay {
  date: string
  dayStatus?: string
  day_status?: string
}

interface BackendCalendarPayload {
  days?: BackendCalendarDay[]
}

function normalizeDayStatus(raw: string | undefined): DayStatus {
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
  const body = await res.json()
  return normalizeDayStatus(body.dayStatus ?? body.day_status)
}

export async function getMonthStatuses(year: number, month: number): Promise<DayStatusMap> {
  const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`
  const res = await fetch(`/api/calendar?month=${monthStr}`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  const body: BackendCalendarPayload = await res.json()
  const days = body.days ?? []
  const map: DayStatusMap = {}
  for (const day of days) {
    map[day.date] = normalizeDayStatus(day.dayStatus ?? day.day_status)
  }
  return map
}

export const getDayStatusAsync = getDayStatus
export const getMonthStatusesAsync = getMonthStatuses
