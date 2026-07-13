
// ############################################################################
// AI_HEADER: FRONTEND_API_HORARY — typed horary quota and question client.
// ROLE: Typed quota and question CRUD facade consumed by horary screens and pages.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-HORARY
// purpose: Fetch quota, list and detail data and create horary questions with schema validation.
// owns:
//   - lib/api/horary.ts
// inputs: pagination, question id or HoraryQuestionCreate.
// outputs: HoraryQuotaRead, question arrays, detail or null, created question and HoraryApiError failures.
// dependencies: packages/contracts; lib/contracts/horary Zod schemas; fetch; Response.
// side_effects: credentialed horary API GET and POST requests.
// emitted_logs: none.
// invariants:
//   - Detail 404 maps to null.
//   - 402/NO_HORARY_CREDITS and 409/IDEMPOTENCY_CONFLICT retain Russian messages.
//   - List, detail and create responses remain schema-validated.
//   - HoraryApiError preserves HTTP status and optional backend code.
// failure_policy: Quota throws the existing generic Error; other non-ok responses throw HoraryApiError; schema and network errors propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-HORARY

// START_MODULE_MAP: M-FRONTEND-API-HORARY
// public_entrypoints:
//   - HoraryApiError
//   - getHoraryQuota
//   - listHoraryQuestions
//   - getHoraryQuestion
//   - createHoraryQuestion
// semantic_blocks:
//   - ERROR_BODY: describe optional backend error detail.
//   - TYPED_ERROR: preserve status, code and message in HoraryApiError.
//   - ERROR_MESSAGE_PARSE: map known horary failures and fallbacks.
//   - ERROR_BUILD: reconstruct and return the typed API error.
//   - QUOTA_FETCH: fetch and validate quota.
//   - QUESTION_LIST: fetch and validate paginated questions.
//   - QUESTION_DETAIL: fetch one question with 404-to-null behavior.
//   - QUESTION_CREATE: submit and validate a new question.
// owned_tests:
//   - __tests__/horary/horary-screen-flow.test.tsx
//   - __tests__/horary/horary-error-state.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-HORARY
import type {
  HoraryQuestionCreate,
  HoraryQuestionRead,
  HoraryQuotaRead,
} from "@/packages/contracts"
import {
  HoraryQuestionSchema,
  HoraryQuotaSchema,
} from "@/lib/contracts/horary"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

type HoraryErrorBody = {
  detail?: {
    code?: string
    message?: string
    reason?: string
  }
}

export class HoraryApiError extends Error {
  status: number
  code?: string

  constructor({ status, code, message }: { status: number; code?: string; message: string }) {
    super(message)
    this.name = "HoraryApiError"
    this.status = status
    this.code = code
  }
}

async function parseHoraryError(res: Response) {
  const body = await res.json().catch(() => ({} as HoraryErrorBody))
  const detail = body?.detail

  if (res.status === 402 || detail?.code === "NO_HORARY_CREDITS") {
    return "Недостаточно хорарных вопросов"
  }
  if (res.status === 409 || detail?.code === "IDEMPOTENCY_CONFLICT") {
    return "Этот запрос уже был отправлен. Попробуй ещё раз."
  }
  if (res.status === 0 || !res.statusText) {
    return "Не удалось связаться с сервером. Попробуй ещё раз."
  }

  return detail?.message || detail?.reason || "Не удалось отправить вопрос."
}

async function buildHoraryApiError(res: Response): Promise<HoraryApiError> {
  const body = await res.json().catch(() => ({} as HoraryErrorBody))
  const detail = body?.detail
  const message = await parseHoraryError(
    new Response(JSON.stringify(body), {
      status: res.status,
      statusText: res.statusText,
      headers: res.headers,
    })
  )

  return new HoraryApiError({
    status: res.status,
    code: detail?.code,
    message,
  })
}

export async function getHoraryQuota(): Promise<HoraryQuotaRead> {
  const res = await fetch(`${API_BASE}/api/horary/quota`, { credentials: "include" })
  if (!res.ok) throw new Error("Failed to fetch horary quota")
  return HoraryQuotaSchema.parse(await res.json())
}

export async function listHoraryQuestions(
  limit = 20,
  offset = 0
): Promise<HoraryQuestionRead[]> {
  const res = await fetch(
    `${API_BASE}/api/horary/questions?limit=${limit}&offset=${offset}`,
    { credentials: "include" }
  )

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return HoraryQuestionSchema.array().parse(await res.json()) as HoraryQuestionRead[]
}

export async function getHoraryQuestion(id: string): Promise<HoraryQuestionRead | null> {
  const res = await fetch(`${API_BASE}/api/horary/questions/${id}`, {
    credentials: "include",
  })

  if (res.status === 404) {
    return null
  }

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return HoraryQuestionSchema.parse(await res.json()) as HoraryQuestionRead
}

export async function createHoraryQuestion(
  data: HoraryQuestionCreate
): Promise<HoraryQuestionRead> {
  const res = await fetch(`${API_BASE}/api/horary/questions`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return HoraryQuestionSchema.parse(await res.json()) as HoraryQuestionRead
}
