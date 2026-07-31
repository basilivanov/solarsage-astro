// ############################################################################
// AI_HEADER: FRONTEND_API_CHECKIN — date helpers and authenticated check-in endpoints.
// ROLE: Check-in date helpers and credentialed CRUD/metrics facade.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CHECKIN
// purpose: Resolve local check-in dates and call create, read, yesterday and metrics endpoints.
// owns:
//   - lib/api/checkin.ts
// inputs: Date, timezone and target; CheckinCreate; date key; optional metric range.
// outputs: date keys and typed check-in response models.
// dependencies: packages/contracts check-in types; Intl; URLSearchParams; fetch.
// side_effects: credentialed GET and POST check-in API calls.
// emitted_logs: none.
// invariants:
//   - No-timezone formatting uses local Date getters.
//   - Timezone formatting uses Intl parts.
//   - An explicit YYYY-MM-DD target wins; yesterday shifts the local key by one UTC-safe day.
//   - A { checkin: null } response maps to null.
//   - Metrics query includes only provided from and to values.
// failure_policy: Throw detail string, detail.message, detail.reason or endpoint fallback.
// END_MODULE_CONTRACT: M-FRONTEND-API-CHECKIN

// START_MODULE_MAP: M-FRONTEND-API-CHECKIN
// public_entrypoints:
//   - formatDateInTimeZone
//   - resolveCheckinTargetDate
//   - createCheckin
//   - getCheckin
//   - getYesterdayCheckin
//   - fetchYesterdayCheckin
//   - getCheckinMetrics
// semantic_blocks:
//   - ERROR_DECODE: preserve backend detail priority and endpoint fallback.
//   - JSON_RESPONSE: enforce ok responses before typed JSON decoding.
//   - DATE_FORMAT: derive local or timezone-specific date keys.
//   - DATE_SHIFT: move date keys with UTC-safe noon arithmetic.
//   - TARGET_RESOLUTION: resolve explicit, yesterday or current local target.
//   - CHECKIN_ENDPOINTS: create and read check-in resources.
//   - METRICS_QUERY: include only supplied range parameters.
// owned_tests:
//   - __tests__/api/checkin.test.ts
//   - __tests__/components/CheckinScreen.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-CHECKIN

import type {
  CheckinCreate,
  CheckinMetrics,
  CheckinResponse,
  YesterdayCheckinResponse,
} from "@/packages/contracts"
// The generated Yesterday schema is not re-exported by the frozen runtime barrel yet.
// eslint-disable-next-line grace/contracts-only-import
import { YesterdayCheckinResponse as YesterdayCheckinResponseWireSchema } from "@/packages/contracts/_generated.zod"

const JSON_HEADERS = { Accept: "application/json" }

async function readError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null) as
    | { detail?: string | { message?: string; reason?: string } }
    | null
  const detail = body?.detail
  if (typeof detail === "string") return new Error(detail)
  if (detail && typeof detail === "object") {
    return new Error(detail.message || detail.reason || fallback)
  }
  return new Error(fallback)
}

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw await readError(response, fallback)
  }
  return response.json() as Promise<T>
}

export function formatDateInTimeZone(
  value: Date,
  timeZone?: string | null,
): string {
  if (!timeZone) {
    const year = value.getFullYear()
    const month = String(value.getMonth() + 1).padStart(2, "0")
    const day = String(value.getDate()).padStart(2, "0")
    return `${year}-${month}-${day}`
  }

  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(value)
  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${byType.year}-${byType.month}-${byType.day}`
}

function shiftDateKey(dateKey: string, days: number): string {
  const [year, month, day] = dateKey.split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day + days, 12))
  const shiftedYear = date.getUTCFullYear()
  const shiftedMonth = String(date.getUTCMonth() + 1).padStart(2, "0")
  const shiftedDay = String(date.getUTCDate()).padStart(2, "0")
  return `${shiftedYear}-${shiftedMonth}-${shiftedDay}`
}

export function resolveCheckinTargetDate(
  now: Date,
  timeZone?: string | null,
  target?: string | null,
): string {
  if (target && /^\d{4}-\d{2}-\d{2}$/.test(target)) {
    return target
  }
  const localToday = formatDateInTimeZone(now, timeZone)
  if (target === "yesterday") {
    return shiftDateKey(localToday, -1)
  }
  return localToday
}

import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export async function createCheckin(
  payload: CheckinCreate,
): Promise<CheckinResponse> {
  const response = await instrumentedFetch({
    operation: "checkin.create",
    routeTemplate: "POST /api/checkin",
    url: "/api/checkin",
    init: {
      method: "POST",
      credentials: "include",
      headers: {
        ...JSON_HEADERS,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  })
  return readJson<CheckinResponse>(response, "Failed to save check-in")
}

export async function getCheckin(
  targetDate: string,
): Promise<CheckinResponse | null> {
  const response = await instrumentedFetch({
    operation: "checkin.get",
    routeTemplate: "GET /api/checkin/{date}",
    url: `/api/checkin/${targetDate}`,
    init: {
      credentials: "include",
      headers: JSON_HEADERS,
    },
  })
  const body = await readJson<CheckinResponse | { checkin: null }>(
    response,
    "Failed to load check-in",
  )
  return "checkin" in body ? null : body
}

export async function getYesterdayCheckin(): Promise<YesterdayCheckinResponse> {
  const response = await instrumentedFetch({
    operation: "checkin.get_yesterday",
    routeTemplate: "GET /api/checkin/yesterday",
    url: "/api/checkin/yesterday",
    init: {
      credentials: "include",
      headers: JSON_HEADERS,
    },
  })
  const body = await readJson<unknown>(response, "Failed to load yesterday's check-in")
  const parsed = YesterdayCheckinResponseWireSchema.safeParse(body)
  if (!parsed.success) {
    throw new Error("Ответ вчерашнего check-in имеет неверный формат")
  }
  return parsed.data
}

// START_BLOCK: YESTERDAY_ALIAS
// The existing check-in client owns this endpoint; keep the packet's fetch-oriented
// name as an additive alias without creating a second HTTP implementation.
export const fetchYesterdayCheckin = getYesterdayCheckin
// END_BLOCK: YESTERDAY_ALIAS

export async function getCheckinMetrics({
  from,
  to,
}: {
  from?: string
  to?: string
} = {}): Promise<CheckinMetrics> {
  const params = new URLSearchParams()
  if (from) params.set("from", from)
  if (to) params.set("to", to)
  const suffix = params.size ? `?${params.toString()}` : ""
  const response = await instrumentedFetch({
    operation: "checkin.get_metrics",
    routeTemplate: "GET /api/checkin/metrics",
    url: `/api/checkin/metrics${suffix}`,
    init: {
      credentials: "include",
      headers: JSON_HEADERS,
    },
  })
  return readJson<CheckinMetrics>(response, "Failed to load check-in metrics")
}
