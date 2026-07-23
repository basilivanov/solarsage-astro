// ############################################################################
// AI_HEADER: FRONTEND_API_ELECTION — typed election quota and search client.
// ROLE: Typed facade for /api/election endpoints consumed by election UI.
// ############################################################################

import type { HoraryQuotaRead } from "@/packages/contracts"
import { HoraryQuotaSchema } from "@/lib/contracts/horary"
import {
  ElectionSearch,
  ElectionSearchSchema,
} from "@/lib/contracts/election"
import { z } from "zod"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export class ElectionApiError extends Error {
  status: number
  code?: string

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.name = "ElectionApiError"
    this.status = status
    this.code = code
  }
}

type ErrorBody = {
  detail?: string | { code?: string; message?: string }
}

async function parseError(res: Response): Promise<ElectionApiError> {
  const status = res.status
  let code: string | undefined
  let message = `Request failed (${status})`

  try {
    const body: ErrorBody = await res.json()
    if (typeof body.detail === "string") {
      message = body.detail
    } else if (body.detail) {
      code = body.detail.code
      message = body.detail.message || message
    }
  } catch {
    // Ignore JSON parse error
  }

  if (code === "NO_HORARY_CREDITS" || code === "NO_CREDITS") {
    message = "У вас нет доступных кредитов. Пополните баланс."
  } else if (code === "IDEMPOTENCY_CONFLICT") {
    message = "Запрос с таким ключом уже был отправлен с другими параметрами."
  }

  return new ElectionApiError(status, message, code)
}

export async function getElectionQuota(): Promise<HoraryQuotaRead> {
  const res = await fetch(`${API_BASE}/api/election/quota`, {
    credentials: "include",
  })
  if (!res.ok) {
    throw await parseError(res)
  }
  const data = await res.json()
  return HoraryQuotaSchema.parse(data)
}

export async function listElectionSearches(
  limit = 20,
  offset = 0
): Promise<ElectionSearch[]> {
  const res = await fetch(
    `${API_BASE}/api/election/searches?limit=${limit}&offset=${offset}`,
    { credentials: "include" }
  )
  if (!res.ok) {
    throw await parseError(res)
  }
  const data = await res.json()
  return z.array(ElectionSearchSchema).parse(data)
}

export async function getElectionSearch(id: string): Promise<ElectionSearch | null> {
  const res = await fetch(`${API_BASE}/api/election/searches/${id}`, {
    credentials: "include",
  })
  if (res.status === 404) {
    return null
  }
  if (!res.ok) {
    throw await parseError(res)
  }
  const data = await res.json()
  return ElectionSearchSchema.parse(data)
}

export async function createElectionSearch(params: {
  eventType: string
  windowFrom: string
  windowTo: string
  idempotencyKey?: string
  clientTimezone?: string
}): Promise<ElectionSearch> {
  const idempotencyKey = params.idempotencyKey || crypto.randomUUID()
  const body = {
    eventType: params.eventType,
    windowFrom: params.windowFrom,
    windowTo: params.windowTo,
    idempotencyKey,
    clientTimezone: params.clientTimezone,
  }

  const res = await fetch(`${API_BASE}/api/election/searches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    throw await parseError(res)
  }

  const data = await res.json()
  return ElectionSearchSchema.parse(data)
}
