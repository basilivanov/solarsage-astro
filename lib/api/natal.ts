/**
 * API client for natal endpoints.
 *
 * Wave 5: added generate, report, and section fetch functions
 * aligned with backend routes in apps/api/app/api/natal.py.
 */

import type {
  NatalPreviewRead,
  NatalReportRead,
  NatalGenerateResponse,
} from "@/lib/contracts/natal"
import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { DEMO_NATAL_PREVIEW } from "@/lib/demo-data"
import { MOCK_NATAL_REPORT_READ } from "@/lib/mocks/natal"

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
  if (IS_DEMO_MODE) {
    return { ok: true, data: DEMO_NATAL_PREVIEW as unknown as NatalPreviewRead }
  }

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
    const data: NatalPreviewRead = await res.json()
    return { ok: true, data }
  } catch {
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}

// ---- Generate ----

export async function fetchNatalGenerate(forceRegenerate = false): Promise<
  { ok: true; data: NatalGenerateResponse } | { ok: false; error: NatalGenerateError }
> {
  if (IS_DEMO_MODE) {
    // In demo mode, simulate a successful generation with mock data
    return {
      ok: true,
      data: {
        reportId: "demo",
        status: "READY",
        sectionsAvailable: true,
      },
    }
  }

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

    const data: NatalGenerateResponse = await res.json()
    return { ok: true, data }
  } catch {
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}

// ---- Report ----

export async function fetchNatalReport(reportId?: string): Promise<
  { ok: true; data: NatalReportRead } | { ok: false; error: NatalReportError }
> {
  if (IS_DEMO_MODE || reportId === "demo") {
    return { ok: true, data: MOCK_NATAL_REPORT_READ }
  }

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

    const data: NatalReportRead = await res.json()
    return { ok: true, data }
  } catch {
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

    const data = await res.json()
    return { ok: true, data }
  } catch {
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
