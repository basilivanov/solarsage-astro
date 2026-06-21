// ############################################################################
// AI_HEADER: MODULE_API_CHECKIN
// ROLE: Lib — checkin.ts (API фасад для checkin endpoints)
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// WAVE: W-8.1
// ############################################################################

// START_MODULE_CONTRACT
// purpose: API client for evening checkin endpoints.
//          Wraps fetch calls to /api/checkin/* with proper error handling.
// owns:
//   - lib/api/checkin.ts
// inputs: Function args (targetDate, mood, accuracy, energy, tags, note)
// outputs: Typed responses (CheckinResponse, metrics)
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (pure)
// invariants:
//   - All requests include credentials: "include" for session cookie
// failure_policy: throw Error on non-2xx
// END_MODULE_CONTRACT

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export interface CheckinResult {
  id: number
  targetDate: string
  mood: number
  accuracy: string | null
  energy: number | null
  tags: string[]
  note: string | null
  streak: number
  filledAt: string | null
  createdAt: string
}

export async function createCheckin(data: {
  targetDate: string
  mood: number
  accuracy?: string | null
  energy?: number | null
  tags?: string[] | null
  note?: string | null
}): Promise<CheckinResult> {
  const res = await fetch(`${API_BASE}/api/checkin`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || "Failed to create checkin")
  }
  return res.json()
}

export async function getCheckin(targetDate: string): Promise<CheckinResult | null> {
  const res = await fetch(`${API_BASE}/api/checkin/${targetDate}`, {
    credentials: "include",
  })
  if (res.status === 404) return null
  if (!res.ok) throw new Error("Failed to get checkin")
  return res.json()
}

export async function getYesterdayCheckin(): Promise<{ hadCheckin: boolean; checkin: CheckinResult | null }> {
  const res = await fetch(`${API_BASE}/api/checkin/yesterday`, {
    credentials: "include",
  })
  if (!res.ok) throw new Error("Failed to get yesterday checkin")
  return res.json()
}

export async function getCheckinMetrics(from: string, to: string) {
  const res = await fetch(`${API_BASE}/api/checkin/metrics?from=${from}&to=${to}`, {
    credentials: "include",
  })
  if (!res.ok) throw new Error("Failed to get metrics")
  return res.json()
}
