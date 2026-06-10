import type { NatalPreviewRead } from "@/lib/contracts/natal"
import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { DEMO_NATAL_PREVIEW } from "@/lib/demo-data"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export interface NatalPreviewError {
  type: "profile_incomplete" | "error"
  message: string
  missingFields?: string[]
}

type ErrorBody = {
  message?: string
  missingFields?: string[]
  detail?: { message?: string; missingFields?: string[]; code?: string }
}

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
      const body: ErrorBody = await res.json().catch(() => ({ message: "Profile incomplete" }))
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
      const body: ErrorBody = await res.json().catch(() => ({ message: "Failed to load natal preview" }))
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
