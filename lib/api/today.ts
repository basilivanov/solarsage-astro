
// ############################################################################
// AI_HEADER: FRONTEND_API_TODAY — minimal date-to-day-payload fetch facade.
// ROLE: Minimal date-to-TodayPayload fetch facade and compatibility alias.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-TODAY
// purpose: Fetch the canonical day payload for one Date.
// owns:
//   - lib/api/today.ts
// inputs: Date.
// outputs: Promise<TodayPayload> and getTodayPayloadAsync alias.
// dependencies: packages/contracts TodayPayload; fetch.
// side_effects: credentialed GET /api/day/YYYY-MM-DD.
// emitted_logs: none.
// invariants:
//   - Date path remains UTC ISO YYYY-MM-DD derived by toISOString.
//   - Success payload is returned unchanged.
//   - The Async alias remains reference-equal.
// failure_policy: Non-ok throws detail.message when available, otherwise API error with status; network and JSON failures propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-TODAY

// START_MODULE_MAP: M-FRONTEND-API-TODAY
// public_entrypoints:
//   - getTodayPayload
//   - getTodayPayloadAsync
// semantic_blocks:
//   - DATE_PATH: derive the UTC ISO date path.
//   - DAY_FETCH: request and return the canonical day payload.
//   - COMPATIBILITY_ALIAS: retain the reference-equal Async export.
// owned_tests:
//   - none direct; canonical day behavior is covered by contract and library tests.
// END_MODULE_MAP: M-FRONTEND-API-TODAY

import type { TodayPayload } from "@/packages/contracts"

export async function getTodayPayload(date: Date): Promise<TodayPayload> {
  const dateStr = date.toISOString().split("T")[0]
  const res = await fetch(`/api/day/${dateStr}`, {
    credentials: "include",
    headers: { "Accept": "application/json" },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail?.message || `API error ${res.status}`)
  }
  return res.json()
}

export const getTodayPayloadAsync = getTodayPayload
