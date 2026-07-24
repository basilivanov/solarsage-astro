// ############################################################################
// AI_HEADER: FRONTEND_API_ACCESS — authenticated access summary client and validated UI mapping.
// ROLE: Authenticated access client consumed by use-access and access UI types.
// DEPENDENCIES: packages/contracts AccessSummary; packages/contracts/runtime AccessSummaryWireSchema; lib/contracts/access validator; lib/log/instrumented-fetch.
// GRACE_ANCHORS: [FRONTEND_API_ACCESS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-ACCESS
// purpose: Fetch AccessSummary via instrumentedFetch with AccessSummary responseContract and map it into validated AccessInfo.
// owns:
//   - lib/api/access.ts
// inputs: no function arguments; NEXT_PUBLIC_API_URL; authenticated browser session.
// outputs: exported AccessInfo/AccessState types and Promise<AccessInfo> from getAccess.
// dependencies: packages/contracts AccessSummary; packages/contracts/runtime AccessSummaryWireSchema; lib/contracts/access validator; lib/log/instrumented-fetch.
// side_effects: credentialed GET /api/access via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
// invariants:
//   - trial and subscription map to hasAccess=true.
//   - Access dates preserve the existing T00:00:00 conversion.
//   - daysLeft is referralDaysLeft only for trial; otherwise zero.
//   - Mapped data passes validateAccessInfo.
// failure_policy: Throw detail string, detail.message or generic Failed to get access.
// END_MODULE_CONTRACT: M-FRONTEND-API-ACCESS

// START_MODULE_MAP: M-FRONTEND-API-ACCESS
// public_entrypoints:
//   - AccessInfo
//   - AccessState
//   - getAccess
// semantic_blocks:
//   - DATE_PARSE: convert optional date-only strings to local Date values.
//   - ACCESS_MAPPING: map AccessSummary fields and validate AccessInfo.
//   - ACCESS_FETCH: request and decode the authenticated access summary.
// owned_tests:
//   - __tests__/api/access.test.ts
//   - __tests__/hooks/useAccess.test.ts
// END_MODULE_MAP: M-FRONTEND-API-ACCESS

import type { AccessSummary } from "@/packages/contracts"
import { AccessSummaryWireSchema } from "@/packages/contracts/runtime"
import {
  type AccessInfo,
  type AccessState,
  validateAccessInfo,
} from "@/lib/contracts/access"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export type { AccessInfo, AccessState }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// START_BLOCK: DATE_PARSE
function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null
  return new Date(`${value}T00:00:00`)
}
// END_BLOCK: DATE_PARSE

// START_BLOCK: ACCESS_MAPPING
function toAccessInfo(summary: AccessSummary): AccessInfo {
  return validateAccessInfo({
    state: summary.user,
    hasAccess: summary.user === "trial" || summary.user === "subscription",
    accessStart: parseDate(summary.accessStart),
    accessEnd: parseDate(summary.accessUntil),
    daysLeft: summary.user === "trial" ? summary.referralDaysLeft : 0,
  })
}
// END_BLOCK: ACCESS_MAPPING

// START_BLOCK: ACCESS_FETCH
export async function getAccess(): Promise<AccessInfo> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-ACCESS.getAccess
  // purpose: Fetch authenticated access summary via instrumentedFetch with AccessSummary responseContract and map into AccessInfo.
  // inputs: none
  // returns: Promise<AccessInfo>
  // side_effects: GET /api/access via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-ACCESS.getAccess
  const res = await instrumentedFetch({
    operation: "access.get",
    routeTemplate: "GET /api/access",
    url: `${API_BASE}/api/access`,
    init: {
      credentials: "include",
      headers: { Accept: "application/json" },
    },
    responseContract: {
      contractName: "AccessSummary",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = AccessSummaryWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (!res.ok) {
    const payload = await res.json().catch(() => null)
    const detail = payload?.detail
    if (typeof detail === "string") throw new Error(detail)
    if (detail && typeof detail.message === "string") {
      throw new Error(detail.message)
    }
    throw new Error("Failed to get access")
  }

  const summary = AccessSummaryWireSchema.parse(await res.json())
  return toAccessInfo(summary)
}
// END_BLOCK: ACCESS_FETCH
