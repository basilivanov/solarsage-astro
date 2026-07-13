
// ############################################################################
// AI_HEADER: FRONTEND_API_NATAL — typed-result natal report lifecycle client.
// ROLE: Typed-result natal preview, generation, report and section client.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-NATAL
// purpose: Call natal endpoints, validate success payloads and normalize HTTP, contract and network failures into results.
// owns:
//   - lib/api/natal.ts
// inputs: optional forceRegenerate, reportId and sectionId.
// outputs: exported error interfaces and discriminated success or error result objects.
// dependencies: lib/contracts/natal types and Zod schemas; fetch.
// side_effects: credentialed natal GET and POST requests.
// emitted_logs: none.
// invariants:
//   - Public functions resolve typed results instead of throwing expected failures.
//   - 409, 501, 502, 401 and 404 mappings and existing wire-facing messages remain unchanged.
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// ---- Error types ----

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

// ---- Helpers ----

function parseErrorBody(res: Response): Promise<ErrorBody> {
  return res.json().catch(() => ({ message: "Request failed" }))
}

// ---- Preview ----

export async function fetchNatalPreview(): Promise<
  { ok: true; data: NatalPreviewRead } | { ok: false; error: NatalPreviewError }
> {
  try {
    const res = await fetch(`${API_BASE}/api/natal/preview`, {
      credentials: "include",
      headers: { Accept: "application/json" },
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

// ---- Generate ----

export async function fetchNatalGenerate(forceRegenerate = false): Promise<
  { ok: true; data: NatalGenerateResponse } | { ok: false; error: NatalGenerateError }
> {
  try {
    const res = await fetch(`${API_BASE}/api/natal/generate`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ forceRegenerate }),
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

// ---- Report ----

export async function fetchNatalReport(reportId?: string): Promise<
  { ok: true; data: NatalReportRead } | { ok: false; error: NatalReportError }
> {
  try {
    const url = reportId
      ? `${API_BASE}/api/natal/report/${reportId}`
      : `${API_BASE}/api/natal/report`

    const res = await fetch(url, {
      credentials: "include",
      headers: { Accept: "application/json" },
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
          message: body.detail?.message || body.message || "Failed to load report",
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

// ---- Section ----

export async function fetchNatalReportSection(
  reportId: string,
  sectionId: string
): Promise<
  { ok: true; data: NatalReportRead["sections"][number] } | { ok: false; error: NatalReportError }
> {
  try {
    const res = await fetch(
      `${API_BASE}/api/natal/report/${reportId}/section/${sectionId}`,
      {
        credentials: "include",
        headers: { Accept: "application/json" },
      }
    )

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
    // Zod validation error — surface as contract mismatch, not generic network error
    if (err instanceof Error && err.name === "ZodError") {
      return { ok: false, error: { type: "error", message: "Invalid response format from server" } }
    }
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
