
// ############################################################################
// AI_HEADER: MODULE_API_TODAY
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/api/today.ts
// owns:
//   - lib/api/today.ts
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
// module: M-API-TODAY
// wave: W-2.7
// purpose: Today API facade

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
