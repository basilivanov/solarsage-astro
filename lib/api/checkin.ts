import type {
  CheckinCreate,
  CheckinMetrics,
  CheckinResponse,
  YesterdayCheckinResponse,
} from "@/packages/contracts"

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

export async function createCheckin(
  payload: CheckinCreate,
): Promise<CheckinResponse> {
  const response = await fetch("/api/checkin", {
    method: "POST",
    credentials: "include",
    headers: {
      ...JSON_HEADERS,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })
  return readJson<CheckinResponse>(response, "Failed to save check-in")
}

export async function getCheckin(
  targetDate: string,
): Promise<CheckinResponse | null> {
  const response = await fetch(`/api/checkin/${targetDate}`, {
    credentials: "include",
    headers: JSON_HEADERS,
  })
  const body = await readJson<CheckinResponse | { checkin: null }>(
    response,
    "Failed to load check-in",
  )
  return "checkin" in body ? null : body
}

export async function getYesterdayCheckin(): Promise<YesterdayCheckinResponse> {
  const response = await fetch("/api/checkin/yesterday", {
    credentials: "include",
    headers: JSON_HEADERS,
  })
  return readJson<YesterdayCheckinResponse>(
    response,
    "Failed to load yesterday's check-in",
  )
}

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
  const response = await fetch(`/api/checkin/metrics${suffix}`, {
    credentials: "include",
    headers: JSON_HEADERS,
  })
  return readJson<CheckinMetrics>(response, "Failed to load check-in metrics")
}
