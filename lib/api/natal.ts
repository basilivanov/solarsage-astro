import type { NatalPreviewRead } from "@/lib/contracts/natal"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export interface NatalPreviewError {
  type: "profile_incomplete" | "error"
  message: string
  missingFields?: string[]
}

type ErrorBody = { message?: string; missingFields?: string[] }

export async function fetchNatalPreview(): Promise<
  { ok: true; data: NatalPreviewRead } | { ok: false; error: NatalPreviewError }
> {
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
          message: body.message || "Profile incomplete",
          missingFields: body.missingFields || [],
        },
      }
    }
    if (!res.ok) {
      const body: ErrorBody = await res.json().catch(() => ({ message: "Failed to load natal preview" }))
      return {
        ok: false,
        error: { type: "error", message: body.message || "Failed to load natal preview" },
      }
    }
    const data: NatalPreviewRead = await res.json()
    return { ok: true, data }
  } catch {
    return { ok: false, error: { type: "error", message: "Network error" } }
  }
}
