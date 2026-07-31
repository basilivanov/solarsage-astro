// ############################################################################
// AI_HEADER: FRONTEND_API_CALENDAR — calendar/v2 and day-state fetch facade.
// ROLE: Owns the generated calendar wire boundary used by the active calendar screen.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CALENDAR
// purpose: Fetch and validate calendar/v2 payloads and expose small compatibility helpers for day-state consumers.
// owns:
//   - lib/api/calendar.ts
// inputs: Date; zero-based year/month pair.
// outputs: generated CalendarPayload, hero|ordinary|not-computed state helpers, and Async aliases.
// dependencies: packages/contracts runtime schemas; lib/log/instrumented-fetch.
// side_effects: credentialed GET /api/day/{date} and /api/calendar?month=YYYY-MM via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_response_invalid.
// invariants:
//   - calendar/v2 is the only monthly response contract accepted by this facade.
//   - dayState never falls back to valence/status vocabulary.
//   - The month argument remains zero-based and is converted with +1.
//   - Async aliases remain reference-equal to canonical functions.
// failure_policy: HTTP failures propagate as API errors; malformed generated payloads propagate as schema errors.
// END_MODULE_CONTRACT: M-FRONTEND-API-CALENDAR

// START_MODULE_MAP: M-FRONTEND-API-CALENDAR
// public_entrypoints:
//   - DayState
//   - DayStatus
//   - DayStatusMap
//   - CalendarPayload
//   - CalendarPayloadReadModel
//   - normalizeDayState
//   - getDayStatus
//   - getMonthStatuses
//   - getMonthCalendar
//   - getDayStatusAsync
//   - getMonthStatusesAsync
//   - getMonthCalendarAsync
// semantic_blocks:
//   - STATE_NORMALIZATION: normalize generated day-state vocabulary.
//   - DAY_FETCH: fetch one Today Convergence envelope and project its state.
//   - MONTH_STATUS_DERIVATION: derive a keyed dayState map from a month payload.
//   - MONTH_FETCH: fetch and validate a zero-based requested month via instrumentedFetch.
//   - COMPATIBILITY_ALIASES: retain reference-equal Async exports.
// owned_tests:
//   - __tests__/api/calendar.test.ts
//   - __tests__/components/CalendarScreen.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-CALENDAR

import type { CalendarPayload } from "@/packages/contracts"
import { TodayConvergencePayloadWireSchema } from "@/packages/contracts/today-convergence"
import { CalendarPayloadWireSchema } from "@/packages/contracts/runtime"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export type { CalendarPayload }
export type CalendarPayloadReadModel = CalendarPayload
export type DayState = CalendarPayload["days"][number]["dayState"]

// Kept as additive aliases for callers that still use the old facade names.
// The values are intentionally the generated calendar/v2 enum, never valence labels.
export type DayStatus = DayState
export type DayStatusMap = Record<string, DayState>

// START_BLOCK: STATE_NORMALIZATION
export function normalizeDayState(raw: unknown): DayState | null {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.normalizeDayState
  // purpose: Accept only the canonical calendar/v2 dayState enum.
  // inputs: raw — untrusted API or compatibility value.
  // returns: hero, ordinary, not-computed, or null when no canonical state exists.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns null for unknown values.
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.normalizeDayState
  if (raw === "hero" || raw === "ordinary" || raw === "not-computed") return raw
  return null
}

function stateFromTodayPayload(raw: unknown): DayState | null {
  const parsed = TodayConvergencePayloadWireSchema.safeParse(raw)
  if (!parsed.success) return null
  if (parsed.data.state === "convergence_today") return "hero"
  if (parsed.data.state === "quiet_day") return "ordinary"
  return "not-computed"
}
// END_BLOCK: STATE_NORMALIZATION

// START_BLOCK: DAY_FETCH
export async function getDayStatus(date: Date): Promise<DayState | null> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getDayStatus
  // purpose: Fetch one generated Today envelope and project it onto calendar/v2 dayState.
  // inputs: date — Date object.
  // returns: Promise<DayState | null>.
  // side_effects: GET /api/day/{date} via instrumentedFetch.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: throws on HTTP failure; returns null for a malformed day response.
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getDayStatus
  const dateStr = date.toISOString().split("T")[0]
  const res = await instrumentedFetch({
    operation: "calendar.day_state",
    routeTemplate: "GET /api/day/{date}",
    url: `/api/day/${dateStr}`,
    init: {
      credentials: "include",
      headers: { Accept: "application/json" },
    },
    responseContract: {
      contractName: "TodayConvergencePayload",
      contractVersion: "v2",
      validate: (json) => {
        const parsed = TodayConvergencePayloadWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((issue) => String(issue.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return stateFromTodayPayload(await res.json())
}
// END_BLOCK: DAY_FETCH

// START_BLOCK: MONTH_STATUS_DERIVATION
export async function getMonthStatuses(year: number, month: number): Promise<DayStatusMap> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthStatuses
  // purpose: Derive a keyed calendar/v2 dayState map from getMonthCalendar.
  // inputs: year — YYYY; month — zero-indexed month (0..11).
  // returns: Promise<Record<date, DayState>>.
  // side_effects: calls getMonthCalendar.
  // emitted_logs: none.
  // error_behavior: propagates monthly fetch/schema failures.
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthStatuses
  const body = await getMonthCalendar(year, month)
  const map: DayStatusMap = {}
  for (const day of body.days) {
    const state = normalizeDayState(day.dayState)
    if (state !== null) map[day.date] = state
  }
  return map
}
// END_BLOCK: MONTH_STATUS_DERIVATION

// START_BLOCK: MONTH_FETCH
export async function getMonthCalendar(year: number, month: number): Promise<CalendarPayload> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthCalendar
  // purpose: Fetch and validate the generated calendar/v2 payload for a zero-based requested month.
  // inputs: year — YYYY; month — zero-indexed month (0..11).
  // returns: Promise<CalendarPayload>.
  // side_effects: GET /api/calendar?month=YYYY-MM via instrumentedFetch.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_response_invalid.
  // error_behavior: throws on HTTP failure or generated-schema validation failure.
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-CALENDAR.getMonthCalendar
  const monthStr = `${year}-${String(month + 1).padStart(2, "0")}`
  const res = await instrumentedFetch({
    operation: "calendar.month",
    routeTemplate: "GET /api/calendar",
    url: `/api/calendar?month=${monthStr}`,
    init: {
      credentials: "include",
      headers: { Accept: "application/json" },
    },
    responseContract: {
      contractName: "CalendarPayload",
      contractVersion: "v2",
      validate: (json) => {
        const parsed = CalendarPayloadWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((issue) => String(issue.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return CalendarPayloadWireSchema.parse(await res.json())
}
// END_BLOCK: MONTH_FETCH

// START_BLOCK: COMPATIBILITY_ALIASES
export const getDayStatusAsync = getDayStatus
export const getMonthStatusesAsync = getMonthStatuses
export const getMonthCalendarAsync = getMonthCalendar
// END_BLOCK: COMPATIBILITY_ALIASES
