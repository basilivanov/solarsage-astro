// ############################################################################
// AI_HEADER: MODULE_API_ACCESS
// ROLE: Authenticated access API client and UI mapping
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################
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
