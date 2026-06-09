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
