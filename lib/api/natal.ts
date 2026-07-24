// ############################################################################
// AI_HEADER: FRONTEND_API_NATAL — typed-result natal report lifecycle client.
// ROLE: Typed-result natal preview, generation, report and section client.
// DEPENDENCIES: lib/contracts/natal types and Zod schemas; lib/log/instrumented-fetch
// GRACE_ANCHORS: [FRONTEND_API_NATAL]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-NATAL
// purpose: Call natal endpoints via instrumentedFetch with diagnostic contracts, validate success payloads and normalize HTTP, contract and network failures into results.
// owns:
//   - lib/api/natal.ts
// inputs: optional forceRegenerate, reportId and sectionId.
// outputs: exported error interfaces and discriminated success or error result objects.
// dependencies: lib/contracts/natal types and Zod schemas; lib/log/instrumented-fetch.
// side_effects: credentialed natal GET and POST requests via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid
// invariants:
//   - Public functions resolve typed results instead of throwing expected failures.
//   - 409, 501, 502, 401 and 404 status-to-error mappings remain unchanged.
//   - The generic fetchNatalReport HTTP-error fallback message is localized:
//     "Не удалось загрузить отчёт" (other wire-facing messages unchanged).
//   - Successful payloads remain Zod-validated.
//   - Zod failures remain Invalid response format; other caught failures remain Network error.
//   - No payment client or access grant is introduced.
// failure_policy: Catch request and schema failures and return the current typed error without logging or exposing raw response bodies.
// END_MODULE_CONTRACT: M-FRONTEND-API-NATAL

// START_MODULE_MAP: M-FRONTEND-API-NATAL
// public_entrypoints:
//   - NatalPreviewError
//   - NatalReportError
//   - NatalGenerateError
//   - fetchNatalPreview
//   - fetchNatalGenerate
//   - fetchNatalReport
//   - fetchNatalReportSection
// semantic_blocks:
//   - ERROR_MODELS: define discriminated public failure shapes.
//   - ERROR_BODY_PARSE: decode backend detail with a safe fallback.
//   - PREVIEW: fetch and validate natal preview.
//   - GENERATE: request report generation and normalize backend states.
//   - REPORT: fetch and validate the current or identified report.
//   - SECTION: fetch and validate one report section.
// owned_tests:
//   - __tests__/api/natal-instrumentation.test.ts
//   - __tests__/api/natal-report.test.ts
//   - __tests__/natal/natal-component-states.test.tsx
//   - __tests__/natal/natal-no-english.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-NATAL

/**
 * API client for natal endpoints.
 *
 * Wave 5: added generate, report, and section fetch functions
 * aligned with backend routes in apps/api/app/api/natal.py.
 *
 * Payment clients intentionally do not live here. Full-report payment remains
 * disabled until the backend has a real catalog, provider confirmation,
 * verified webhook, idempotent fulfillment, and access grant.
 */

import type {
  NatalPreviewRead,
  NatalReportRead,
  NatalGenerateResponse,
} from "@/lib/contracts/natal"
import {
  NatalPreviewReadSchema,
  NatalReportReadSchema,
  NatalGenerateResponseSchema,
  NatalReportSectionReadSchema,
} from "@/lib/contracts/natal"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// START_BLOCK: ERROR_MODELS
export interface NatalPreviewError {
  type: "profile_incomplete" | "error"
  message: string
  missingFields?: string[]
}

export interface NatalReportError {
  type: "not_found" | "feature_disabled" | "context_missing" | "generation_failed" | "error"
  message: string
  errorCode?: string | null
}

export interface NatalGenerateError {
  type: "profile_incomplete" | "feature_disabled" | "generation_failed" | "context_missing" | "error"
  message: string
  errorCode?: string | null
  status?: string | null
}

type ErrorBody = {
  message?: string
  missingFields?: string[]
  detail?: { message?: string; missingFields?: string[]; code?: string }
}
// END_BLOCK: ERROR_MODELS

// START_BLOCK: ERROR_BODY_PARSE
function parseErrorBody(res: Response): Promise<ErrorBody> {
  return res.json().catch(() => ({ message: "Request failed" }))
}
// END_BLOCK: ERROR_BODY_PARSE

// START_BLOCK: PREVIEW
export async function fetchNatalPreview(): Promise<
  { ok: true; data: NatalPreviewRead } | { ok: false; error: NatalPreviewError }
> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalPreview
  // purpose: Fetch natal preview payload via instrumentedFetch with NatalPreview responseContract.
  // inputs: none
  // returns: Promise<{ ok: true; data: NatalPreviewRead } | { ok: false; error: NatalPreviewError }>
  // side_effects: GET /api/natal/preview via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalPreview
  try {
    const res = await instrumentedFetch({
      operation: "natal.preview",
      routeTemplate: "GET /api/natal/preview",
      url: `${API_BASE}/api/natal/preview`,
      init: {
        credentials: "include",
        headers: { Accept: "application/json" },
      },
      responseContract: {
        contractName: "NatalPreview",
        contractVersion: "v1",
        validate: (json) => {
          const parsed = NatalPreviewReadSchema.safeParse(json)
          if (parsed.success) return { valid: true }
          const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
          return { valid: false, missingFields: fields, invalidFieldTypes: fields }
        },
      },
    })
    if (res.status === 409) {
      const body = await parseErrorBody(res)
      return {
        ok: false,
        error: {
          type: "profile_incomplete",
          message: body.detail?.message || body.message || "Profile incomplete",
          missingFields: body.detail?.missingFields || body.missingFields || [],
        },
      }
    }
    if (!res.ok) {
      const body = await parseErrorBody(res)
      return {
        ok: false,
        error: { type: "error", message: body.detail?.message || body.message || "Failed to load natal preview" },
      }
    }
    const raw = await res.json()
    const data = NatalPreviewReadSchema.parse(raw)
    return { ok: true, data }
  } catch (err) {
    if (err instanceof Error && err.name === "ZodError") {
      return { ok: false, error: { type: "error", message: "Invalid response format from server" } }
    }
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
// END_BLOCK: PREVIEW

// START_BLOCK: GENERATE
export async function fetchNatalGenerate(forceRegenerate = false): Promise<
  { ok: true; data: NatalGenerateResponse } | { ok: false; error: NatalGenerateError }
> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalGenerate
  // purpose: Request natal report generation via instrumentedFetch with NatalGenerate responseContract.
  // inputs: forceRegenerate — boolean flag
  // returns: Promise<{ ok: true; data: NatalGenerateResponse } | { ok: false; error: NatalGenerateError }>
  // side_effects: POST /api/natal/generate via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalGenerate
  try {
    const res = await instrumentedFetch({
      operation: "natal.generate",
      routeTemplate: "POST /api/natal/generate",
      url: `${API_BASE}/api/natal/generate`,
      init: {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ forceRegenerate }),
      },
      responseContract: {
        contractName: "NatalGenerate",
        contractVersion: "v1",
        validate: (json) => {
          const parsed = NatalGenerateResponseSchema.safeParse(json)
          if (parsed.success) return { valid: true }
          const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
          return { valid: false, missingFields: fields, invalidFieldTypes: fields }
        },
      },
    })

    if (res.status === 409) {
      const body = await parseErrorBody(res)
      return {
        ok: false,
        error: {
          type: "profile_incomplete",
          message: body.detail?.message || body.message || "Profile incomplete",
        },
      }
    }

    if (res.status === 501) {
      return {
        ok: false,
        error: {
          type: "feature_disabled",
          message: "Full report generation is not available yet",
        },
      }
    }

    if (res.status === 502) {
      return {
        ok: false,
        error: {
          type: "context_missing",
          message: "Natal context is not available. Please try again later.",
        },
      }
    }

    if (!res.ok) {
      const body = await parseErrorBody(res)
      return {
        ok: false,
        error: {
          type: "generation_failed",
          message: body.detail?.message || body.message || "Failed to generate report",
          errorCode: body.detail?.code,
        },
      }
    }

    const raw = await res.json()
    const data = NatalGenerateResponseSchema.parse(raw)
    return { ok: true, data }
  } catch (err) {
    if (err instanceof Error && err.name === "ZodError") {
      return { ok: false, error: { type: "error", message: "Invalid response format from server" } }
    }
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
// END_BLOCK: GENERATE

// START_BLOCK: REPORT
export async function fetchNatalReport(reportId?: string): Promise<
  { ok: true; data: NatalReportRead } | { ok: false; error: NatalReportError }
> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalReport
  // purpose: Fetch current or identified natal report via instrumentedFetch with NatalReport responseContract.
  // inputs: reportId — optional string ID
  // returns: Promise<{ ok: true; data: NatalReportRead } | { ok: false; error: NatalReportError }>
  // side_effects: GET /api/natal/report or /api/natal/report/{id} via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalReport
  try {
    const url = reportId
      ? `${API_BASE}/api/natal/report/${reportId}`
      : `${API_BASE}/api/natal/report`

    const res = await instrumentedFetch({
      operation: "natal.report",
      routeTemplate: reportId ? "GET /api/natal/report/{id}" : "GET /api/natal/report",
      url,
      init: {
        credentials: "include",
        headers: { Accept: "application/json" },
      },
      responseContract: {
        contractName: "NatalReport",
        contractVersion: "v1",
        validate: (json) => {
          const parsed = NatalReportReadSchema.safeParse(json)
          if (parsed.success) return { valid: true }
          const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
          return { valid: false, missingFields: fields, invalidFieldTypes: fields }
        },
      },
    })

    if (res.status === 401) {
      return { ok: false, error: { type: "error", message: "Not authenticated" } }
    }

    if (res.status === 404) {
      return { ok: false, error: { type: "not_found", message: "Report not found" } }
    }

    if (res.status === 501) {
      return { ok: false, error: { type: "feature_disabled", message: "Full report feature is not available" } }
    }

    if (res.status === 502) {
      return { ok: false, error: { type: "context_missing", message: "Natal context unavailable" } }
    }

    if (!res.ok) {
      const body = await parseErrorBody(res)
      return {
        ok: false,
        error: {
          type: "error",
          message: body.detail?.message || body.message || "Не удалось загрузить отчёт",
          errorCode: body.detail?.code,
        },
      }
    }

    const raw = await res.json()
    const data = NatalReportReadSchema.parse(raw)
    return { ok: true, data }
  } catch (err) {
    if (err instanceof Error && err.name === "ZodError") {
      return { ok: false, error: { type: "error", message: "Invalid response format from server" } }
    }
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
// END_BLOCK: REPORT

// START_BLOCK: SECTION
export async function fetchNatalReportSection(
  reportId: string,
  sectionId: string
): Promise<
  { ok: true; data: NatalReportRead["sections"][number] } | { ok: false; error: NatalReportError }
> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalReportSection
  // purpose: Fetch single natal report section via instrumentedFetch with NatalReportSection responseContract.
  // inputs: reportId — report string ID, sectionId — section string ID
  // returns: Promise<{ ok: true; data: NatalReportRead["sections"][number] } | { ok: false; error: NatalReportError }>
  // side_effects: GET /api/natal/report/{id}/section/{sectionId} via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-NATAL.fetchNatalReportSection
  try {
    const res = await instrumentedFetch({
      operation: "natal.section",
      routeTemplate: "GET /api/natal/report/{id}/section/{sectionId}",
      url: `${API_BASE}/api/natal/report/${reportId}/section/${sectionId}`,
      init: {
        credentials: "include",
        headers: { Accept: "application/json" },
      },
      responseContract: {
        contractName: "NatalReportSection",
        contractVersion: "v1",
        validate: (json) => {
          const parsed = NatalReportSectionReadSchema.safeParse(json)
          if (parsed.success) return { valid: true }
          const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
          return { valid: false, missingFields: fields, invalidFieldTypes: fields }
        },
      },
    })

    if (res.status === 404) {
      return { ok: false, error: { type: "not_found", message: "Section not found" } }
    }

    if (!res.ok) {
      const body = await parseErrorBody(res)
      return {
        ok: false,
        error: { type: "error", message: body.detail?.message || body.message || "Failed to load section" },
      }
    }

    const raw = await res.json()
    const data = NatalReportSectionReadSchema.parse(raw)
    return { ok: true, data }
  } catch (err) {
    if (err instanceof Error && err.name === "ZodError") {
      return { ok: false, error: { type: "error", message: "Invalid response format from server" } }
    }
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
// END_BLOCK: SECTION
