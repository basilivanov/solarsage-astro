// ############################################################################
// AI_HEADER: FRONTEND_API_HORARY — typed horary quota and question client.
// ROLE: Typed quota and question CRUD facade consumed by horary screens and pages.
// DEPENDENCIES: lib/log/instrumented-fetch, lib/contracts/horary, packages/contracts
// GRACE_ANCHORS: [FRONTEND_API_HORARY]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-HORARY
// purpose: Fetch quota, list and detail data and create horary questions with schema validation and diagnostic contracts via instrumentedFetch.
// owns:
//   - lib/api/horary.ts
// inputs: pagination, question id or HoraryQuestionCreate.
// outputs: HoraryQuotaRead, question arrays, detail or null, created question and HoraryApiError failures.
// dependencies: packages/contracts; lib/contracts/horary Zod schemas; lib/log/instrumented-fetch.
// side_effects: credentialed horary API GET and POST requests via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid
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
//   - __tests__/api/horary-instrumentation.test.ts
//   - __tests__/contracts/horary.test.ts
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
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

type HoraryErrorBody = {
  detail?: {
    code?: string
    message?: string
    reason?: string
  }
}

// START_BLOCK: TYPED_ERROR
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
// END_BLOCK: TYPED_ERROR

// START_BLOCK: ERROR_MESSAGE_PARSE
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
// END_BLOCK: ERROR_MESSAGE_PARSE

// START_BLOCK: ERROR_BUILD
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
// END_BLOCK: ERROR_BUILD

// START_BLOCK: QUOTA_FETCH
export async function getHoraryQuota(): Promise<HoraryQuotaRead> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.getHoraryQuota
  // purpose: Fetch horary quota balance via instrumentedFetch with HoraryQuota responseContract.
  // inputs: none
  // returns: Promise<HoraryQuotaRead>
  // side_effects: GET request to /api/horary/quota
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.getHoraryQuota
  const res = await instrumentedFetch({
    operation: "horary.quota",
    routeTemplate: "GET /api/horary/quota",
    url: `${API_BASE}/api/horary/quota`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "HoraryQuota",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = HoraryQuotaSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) throw new Error("Failed to fetch horary quota")
  return HoraryQuotaSchema.parse(await res.json())
}
// END_BLOCK: QUOTA_FETCH

// START_BLOCK: QUESTION_LIST
export async function listHoraryQuestions(
  limit = 20,
  offset = 0
): Promise<HoraryQuestionRead[]> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.listHoraryQuestions
  // purpose: Fetch paginated horary question list via instrumentedFetch with HoraryQuestionList responseContract.
  // inputs: limit — max items, offset — pagination offset
  // returns: Promise<HoraryQuestionRead[]>
  // side_effects: GET request to /api/horary/questions
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.listHoraryQuestions
  const res = await instrumentedFetch({
    operation: "horary.list_questions",
    routeTemplate: "GET /api/horary/questions",
    url: `${API_BASE}/api/horary/questions?limit=${limit}&offset=${offset}`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "HoraryQuestionList",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = HoraryQuestionSchema.array().safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return HoraryQuestionSchema.array().parse(await res.json()) as HoraryQuestionRead[]
}
// END_BLOCK: QUESTION_LIST

// START_BLOCK: QUESTION_DETAIL
export async function getHoraryQuestion(id: string): Promise<HoraryQuestionRead | null> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.getHoraryQuestion
  // purpose: Fetch horary question detail via instrumentedFetch with 404-to-null behavior and HoraryQuestionDetail responseContract.
  // inputs: id — question string ID
  // returns: Promise<HoraryQuestionRead | null>
  // side_effects: GET request to /api/horary/questions/{id}
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.getHoraryQuestion
  const res = await instrumentedFetch({
    operation: "horary.get_question",
    routeTemplate: "GET /api/horary/questions/{id}",
    url: `${API_BASE}/api/horary/questions/${id}`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "HoraryQuestionDetail",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = HoraryQuestionSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (res.status === 404) {
    return null
  }

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return HoraryQuestionSchema.parse(await res.json()) as HoraryQuestionRead
}
// END_BLOCK: QUESTION_DETAIL

// START_BLOCK: QUESTION_CREATE
export async function createHoraryQuestion(
  data: HoraryQuestionCreate
): Promise<HoraryQuestionRead> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.createHoraryQuestion
  // purpose: Create a horary question via instrumentedFetch with POST init, body payload, and HoraryQuestionCreate responseContract.
  // inputs: data — HoraryQuestionCreate object
  // returns: Promise<HoraryQuestionRead>
  // side_effects: POST request to /api/horary/questions
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-HORARY.createHoraryQuestion
  const res = await instrumentedFetch({
    operation: "horary.create_question",
    routeTemplate: "POST /api/horary/questions",
    url: `${API_BASE}/api/horary/questions`,
    init: {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    },
    responseContract: {
      contractName: "HoraryQuestionCreate",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = HoraryQuestionSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (!res.ok) {
    throw await buildHoraryApiError(res)
  }

  return HoraryQuestionSchema.parse(await res.json()) as HoraryQuestionRead
}
// END_BLOCK: QUESTION_CREATE
