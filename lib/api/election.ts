// ############################################################################
// AI_HEADER: FRONTEND_API_ELECTION — typed election quota and search client.
// ROLE: Typed facade for /api/election endpoints consumed by election UI.
// DEPENDENCIES: lib/log/instrumented-fetch, lib/contracts/election, lib/contracts/horary, packages/contracts
// GRACE_ANCHORS: [FRONTEND_API_ELECTION]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-ELECTION
// purpose: Fetch quota, list searches, get search detail and create election searches with schema validation and diagnostic contracts via instrumentedFetch.
// owns:
//   - lib/api/election.ts
// inputs: pagination, search id or election search creation parameters.
// outputs: HoraryQuotaRead, ElectionSearch arrays, detail or null, created search and ElectionApiError failures.
// dependencies: packages/contracts; lib/contracts/election Zod schemas; lib/contracts/horary Zod schemas; lib/log/instrumented-fetch.
// side_effects: credentialed election API GET and POST requests via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid
// invariants:
//   - Detail 404 maps to null.
//   - 402/NO_HORARY_CREDITS and 409/IDEMPOTENCY_CONFLICT retain localized Russian messages.
//   - Search list, detail and create responses remain schema-validated.
//   - ElectionApiError preserves HTTP status and optional backend code.
// failure_policy: Throws ElectionApiError on non-ok responses; schema and transport errors propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-ELECTION

// START_MODULE_MAP: M-FRONTEND-API-ELECTION
// public_entrypoints:
//   - ElectionApiError
//   - getElectionQuota
//   - listElectionSearches
//   - getElectionSearch
//   - createElectionSearch
// semantic_blocks:
//   - TYPED_ERROR: preserve status, code and message in ElectionApiError.
//   - ERROR_MESSAGE_PARSE: parse backend error detail and map localized messages.
//   - QUOTA_FETCH: fetch and validate horary quota balance for election.
//   - SEARCH_LIST: fetch paginated list of election searches.
//   - SEARCH_DETAIL: fetch single election search by id with 404-to-null behavior.
//   - SEARCH_CREATE: submit parameters and create new election search.
// owned_tests:
//   - __tests__/lib/election-api.test.ts
// END_MODULE_MAP: M-FRONTEND-API-ELECTION

import type { HoraryQuotaRead } from "@/packages/contracts"
import { HoraryQuotaSchema } from "@/lib/contracts/horary"
import {
  ElectionSearch,
  ElectionSearchSchema,
} from "@/lib/contracts/election"
import { z } from "zod"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// START_BLOCK: TYPED_ERROR
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
// END_BLOCK: TYPED_ERROR

type ErrorBody = {
  detail?: string | { code?: string; message?: string }
}

// START_BLOCK: ERROR_MESSAGE_PARSE
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
// END_BLOCK: ERROR_MESSAGE_PARSE

// START_BLOCK: QUOTA_FETCH
export async function getElectionQuota(): Promise<HoraryQuotaRead> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.getElectionQuota
  // purpose: Fetch horary quota balance for election via instrumentedFetch with HoraryQuota responseContract.
  // inputs: none
  // returns: Promise<HoraryQuotaRead>
  // side_effects: GET request to /api/election/quota
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.getElectionQuota
  const res = await instrumentedFetch({
    operation: "election.quota",
    routeTemplate: "GET /api/election/quota",
    url: `${API_BASE}/api/election/quota`,
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
  if (!res.ok) {
    throw await parseError(res)
  }
  const data = await res.json()
  return HoraryQuotaSchema.parse(data)
}
// END_BLOCK: QUOTA_FETCH

// START_BLOCK: SEARCH_LIST
export async function listElectionSearches(
  limit = 20,
  offset = 0
): Promise<ElectionSearch[]> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.listElectionSearches
  // purpose: Fetch paginated election searches via instrumentedFetch with ElectionSearchList responseContract.
  // inputs: limit — max items, offset — pagination offset
  // returns: Promise<ElectionSearch[]>
  // side_effects: GET request to /api/election/searches
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.listElectionSearches
  const res = await instrumentedFetch({
    operation: "election.list_searches",
    routeTemplate: "GET /api/election/searches",
    url: `${API_BASE}/api/election/searches?limit=${limit}&offset=${offset}`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "ElectionSearchList",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = z.array(ElectionSearchSchema).safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })
  if (!res.ok) {
    throw await parseError(res)
  }
  const data = await res.json()
  return z.array(ElectionSearchSchema).parse(data)
}
// END_BLOCK: SEARCH_LIST

// START_BLOCK: SEARCH_DETAIL
export async function getElectionSearch(id: string): Promise<ElectionSearch | null> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.getElectionSearch
  // purpose: Fetch election search detail via instrumentedFetch with 404-to-null behavior and ElectionSearchDetail responseContract.
  // inputs: id — search string ID
  // returns: Promise<ElectionSearch | null>
  // side_effects: GET request to /api/election/searches/{id}
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.getElectionSearch
  const res = await instrumentedFetch({
    operation: "election.get_search",
    routeTemplate: "GET /api/election/searches/{id}",
    url: `${API_BASE}/api/election/searches/${id}`,
    init: { credentials: "include" },
    responseContract: {
      contractName: "ElectionSearchDetail",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = ElectionSearchSchema.safeParse(json)
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
    throw await parseError(res)
  }
  const data = await res.json()
  return ElectionSearchSchema.parse(data)
}
// END_BLOCK: SEARCH_DETAIL

// START_BLOCK: SEARCH_CREATE
export async function createElectionSearch(params: {
  eventType: string
  windowFrom: string
  windowTo: string
  idempotencyKey?: string
  clientTimezone?: string
}): Promise<ElectionSearch> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.createElectionSearch
  // purpose: Create an election search via instrumentedFetch with POST init, body payload, and ElectionSearchCreate responseContract.
  // inputs: params — election search creation parameters
  // returns: Promise<ElectionSearch>
  // side_effects: POST request to /api/election/searches
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-ELECTION.createElectionSearch
  const idempotencyKey = params.idempotencyKey || crypto.randomUUID()
  const body = {
    eventType: params.eventType,
    windowFrom: params.windowFrom,
    windowTo: params.windowTo,
    idempotencyKey,
    clientTimezone: params.clientTimezone,
  }

  const res = await instrumentedFetch({
    operation: "election.create_search",
    routeTemplate: "POST /api/election/searches",
    url: `${API_BASE}/api/election/searches`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    },
    responseContract: {
      contractName: "ElectionSearchCreate",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = ElectionSearchSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (!res.ok) {
    throw await parseError(res)
  }

  const data = await res.json()
  return ElectionSearchSchema.parse(data)
}
// END_BLOCK: SEARCH_CREATE
