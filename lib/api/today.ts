// ############################################################################
// AI_HEADER: FRONTEND_API_TODAY — minimal date-to-day-payload fetch facade.
// ROLE: Minimal date-to-TodayPayload fetch facade and compatibility alias.
// DEPENDENCIES: packages/contracts TodayPayload; packages/contracts/runtime TodayPayloadWireSchema; lib/log/instrumented-fetch.
// GRACE_ANCHORS: [FRONTEND_API_TODAY]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-TODAY
// purpose: Fetch the canonical day payload for one Date via instrumentedFetch with TodayPayload responseContract.
// owns:
//   - lib/api/today.ts
// inputs: Date.
// outputs: Promise<TodayPayload> and getTodayPayloadAsync alias.
// dependencies: packages/contracts TodayPayload; packages/contracts/runtime TodayPayloadWireSchema; lib/log/instrumented-fetch.
// side_effects: credentialed GET /api/day/YYYY-MM-DD via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
// invariants:
//   - Date path remains UTC ISO YYYY-MM-DD derived by toISOString.
//   - Success payload is validated via TodayPayloadWireSchema.parse.
//   - The Async alias remains reference-equal.
// failure_policy: Non-ok throws detail.message when available, otherwise API error with status; network and JSON failures propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-TODAY

// START_MODULE_MAP: M-FRONTEND-API-TODAY
// public_entrypoints:
//   - getTodayPayload
//   - getTodayPayloadAsync
// semantic_blocks:
//   - DAY_FETCH: request, validate and return the canonical day payload via instrumentedFetch.
//   - COMPATIBILITY_ALIAS: retain the reference-equal Async export.
// owned_tests:
//   - __tests__/api/today-instrumentation.test.ts
// END_MODULE_MAP: M-FRONTEND-API-TODAY

import type { TodayPayload } from "@/packages/contracts"
import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

// START_BLOCK: DAY_FETCH
export async function getTodayPayload(date: Date): Promise<TodayPayload> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-TODAY.getTodayPayload
  // purpose: Fetch and validate canonical TodayPayload for a given Date using instrumentedFetch.
  // inputs: date — Date object
  // returns: Promise<TodayPayload>
  // side_effects: GET /api/day/{date} via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-TODAY.getTodayPayload
  const dateStr = date.toISOString().split("T")[0]
  const res = await instrumentedFetch({
    operation: "today.load",
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
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail?.message || `API error ${res.status}`)
  }
  const raw = await res.json()
  return TodayPayloadWireSchema.parse(raw)
}
// END_BLOCK: DAY_FETCH

// START_BLOCK: COMPATIBILITY_ALIAS
export const getTodayPayloadAsync = getTodayPayload
// END_BLOCK: COMPATIBILITY_ALIAS
