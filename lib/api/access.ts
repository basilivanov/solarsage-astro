// ############################################################################
// AI_HEADER: FRONTEND_API_ACCESS — authenticated access summary client and validated UI mapping.
// ROLE: Authenticated access client consumed by use-access and access UI types.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-ACCESS
// purpose: Fetch AccessSummary and map it into validated AccessInfo.
// owns:
//   - lib/api/access.ts
// inputs: no function arguments; NEXT_PUBLIC_API_URL; authenticated browser session.
// outputs: exported AccessInfo/AccessState types and Promise<AccessInfo> from getAccess.
// dependencies: packages/contracts AccessSummary; lib/contracts/access validator; browser fetch and Date.
// side_effects: credentialed GET /api/access.
// emitted_logs: none.
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
import {
  type AccessInfo,
  type AccessState,
  validateAccessInfo,
} from "@/lib/contracts/access"

export type { AccessInfo, AccessState }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null
  return new Date(`${value}T00:00:00`)
}

function toAccessInfo(summary: AccessSummary): AccessInfo {
  return validateAccessInfo({
    state: summary.user,
    hasAccess: summary.user === "trial" || summary.user === "subscription",
    accessStart: parseDate(summary.accessStart),
    accessEnd: parseDate(summary.accessUntil),
    daysLeft: summary.user === "trial" ? summary.referralDaysLeft : 0,
  })
}

export async function getAccess(): Promise<AccessInfo> {
  const res = await fetch(`${API_BASE}/api/access`, {
    credentials: "include",
    headers: { Accept: "application/json" },
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

  return toAccessInfo(await res.json())
}
