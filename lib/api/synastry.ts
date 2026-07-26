// ############################################################################
// AI_HEADER: FRONTEND_API_SYNASTRY — typed synastry API client.
// ROLE: Typed facade for /api/synastry endpoints consumed by synastry UI.
// DEPENDENCIES: lib/log/instrumented-fetch
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-SYNASTRY
// purpose: Fetch capabilities, list partners, report details, aspect drilldowns, and submit feedback.
// owns:
//   - lib/api/synastry.ts
// inputs: Partner creation parameters, partner_id, aspect_id, feedback value.
// outputs: Synastry capabilities, partners list, generation status, report detail, aspect drilldown.
// dependencies: lib/log/instrumented-fetch.
// side_effects: credentialed synastry API HTTP requests.
// emitted_logs: none
// failure_policy: Throws SynastryApiError on non-2xx responses.
// END_MODULE_CONTRACT: M-FRONTEND-API-SYNASTRY

// START_MODULE_MAP: M-FRONTEND-API-SYNASTRY
// public_entrypoints:
//   - SynastryApiError
//   - getSynastryCapabilities
//   - getSynastryPartners
//   - createSynastryPartner
//   - getSynastryReport
//   - getSynastryStatus
//   - getAspectDrilldown
//   - submitSynastryFeedback
//   - deleteSynastryPartner
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-FRONTEND-API-SYNASTRY

import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export class SynastryApiError extends Error {
  status: number
  code: string | null

  constructor({ status, code, message }: { status: number; code?: string | null; message: string }) {
    super(message)
    this.name = "SynastryApiError"
    this.status = status
    this.code = code ?? null
  }
}

async function buildSynastryApiError(res: Response): Promise<SynastryApiError> {
  const status = res.status
  let code: string | null = null
  let message = `Request failed with status ${status}`

  try {
    const data = await res.clone().json()
    const detail = data?.detail
    if (detail) {
      if (typeof detail === "string") {
        message = detail
        code = detail
      } else if (typeof detail === "object" && detail !== null) {
        if (typeof detail.message === "string") message = detail.message
        if (typeof detail.code === "string") code = detail.code
      }
    } else if (data?.message && typeof data.message === "string") {
      message = data.message
      if (typeof data.code === "string") code = data.code
    }
  } catch {
    // Ignore JSON parse errors
  }

  return new SynastryApiError({ status, code, message })
}

export type SynastryCapabilities = {
  canCalculate: boolean
  canPurchase?: boolean
  activePartnerCount: number
  maxPartners: number
  hasUnlockedAccess: boolean
  creditBalance: number
  blockedReason?: "no_credits" | "partner_limit" | null
}

export type PartnerCreatePayload = {
  name: string
  relation?: string
  birthDate: string
  birthTime?: string | null
  birthCity?: string | null
  birthLat?: number | null
  birthLon?: number | null
  birthTz?: string | null
  birthTimePrecision?: "exact" | "approximate"
  idempotencyKey?: string | null
}

export type SynastryPartnerListItem = {
  id: string
  name: string
  relationType: string
  birthDate: string
  precision: "exact" | "approximate"
  score: number | null
  status: "good" | "mid" | "bad" | null
  summary: string | null
  counters?: { good: number; mid: number; bad: number } | null
  reportState?: string | null
  createdAt: string
}

export type SynastryGenerationStatus = {
  reportId: string
  partnerId: string
  state: "pending" | "calculating" | "narrative_generating" | "ready" | "failed" | "invalidated"
  stage: string | null
  attemptCount: number
  errorCode: string | null
  errorMessage: string | null
}

export type SynastryPlanetPoint = {
  id: string
  owner: "user" | "partner"
  planet: string
  longitude: number
  sign?: string | null
  retrograde?: boolean
  house?: number | null
  houseReliable?: boolean
}

export type SynastryAspectItem = {
  id: string
  title: string
  tone: "good" | "mid" | "bad" | "supportive" | "mixed" | "tense"
  score: number | null
  description: string | null
  techSignature: string | null
  ownerPlanetKey?: string | null
  partnerPlanetKey?: string | null
  aspectSymbol?: string | null
  orbDegrees?: number | null
  orbLabel?: string | null
}

export type SynastrySphereItem = {
  id: string
  title: string
  score: number
  description: string
}

export type SynastryTranslation = {
  aspectId?: string
  title: string
  tone: string
  tech?: string
  text?: string
  scene?: string
}

export type SynastryReportData = {
  partnerId: string
  partnerName: string
  relationType: string
  partnerBirthDate: string
  partnerBirthTime: string | null
  partnerBirthCity: string | null
  precision: "exact" | "approximate"
  score: number
  status: "good" | "mid" | "bad"
  verdict: string
  summary: string
  heroTitle: string | null
  heroDescription: string | null
  counters: { good: number; mid: number; bad: number }
  ownerPlanets: SynastryPlanetPoint[]
  partnerPlanets: SynastryPlanetPoint[]
  aspects: SynastryAspectItem[]
  houseOverlays: Array<{ tech?: string; text?: string }>
  houseSystem?: string
  translations: SynastryTranslation[]
  spheres: SynastrySphereItem[]
  userFeedback: string | null
  createdAt: string
}

export type AspectDrilldownData = {
  aspectId: string
  title: string
  tone: "good" | "mid" | "bad" | "supportive" | "mixed" | "tense"
  techSignature?: string
  aspectSymbol?: string
  aspectKindLabel?: string
  orbText?: string
  headline?: string
  ownerPlanet?: { key: string; label: string; glyph: string; meaning: string }
  partnerPlanet?: { key: string; label: string; glyph: string; meaning: string }
  aspectMechanics?: string
  explanation?: string
  scenes?: Array<{ title: string; text: string }>
  repairs?: string[]
  notMeans?: string[]
  scenario?: string
  advice?: string
}

export async function getSynastryCapabilities(): Promise<SynastryCapabilities> {
  const res = await instrumentedFetch({
    operation: "getSynastryCapabilities",
    routeTemplate: "/api/synastry/capabilities",
    url: "/api/synastry/capabilities",
    init: { credentials: "include" },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  return res.json()
}

export async function getSynastryPartners(): Promise<SynastryPartnerListItem[]> {
  const res = await instrumentedFetch({
    operation: "getSynastryPartners",
    routeTemplate: "/api/synastry",
    url: "/api/synastry",
    init: { credentials: "include" },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  const data = await res.json()
  return data.partners || []
}

export async function createSynastryPartner(
  payload: PartnerCreatePayload
): Promise<SynastryGenerationStatus> {
  const res = await instrumentedFetch({
    operation: "createSynastryPartner",
    routeTemplate: "/api/synastry/partners",
    url: "/api/synastry/partners",
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  return res.json()
}

export async function getSynastryReport(partnerId: string): Promise<SynastryReportData> {
  const res = await instrumentedFetch({
    operation: "getSynastryReport",
    routeTemplate: "/api/synastry/{partner_id}",
    url: `/api/synastry/${partnerId}`,
    init: { credentials: "include" },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  return res.json()
}

export async function getSynastryStatus(partnerId: string): Promise<SynastryGenerationStatus> {
  const res = await instrumentedFetch({
    operation: "getSynastryStatus",
    routeTemplate: "/api/synastry/{partner_id}/status",
    url: `/api/synastry/${partnerId}/status`,
    init: { credentials: "include" },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  return res.json()
}

export async function getAspectDrilldown(
  partnerId: string,
  aspectId: string
): Promise<AspectDrilldownData> {
  const res = await instrumentedFetch({
    operation: "getAspectDrilldown",
    routeTemplate: "/api/synastry/{partner_id}/aspect/{aspect_id}",
    url: `/api/synastry/${partnerId}/aspect/${aspectId}`,
    init: { credentials: "include" },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  return res.json()
}

export async function submitSynastryFeedback(
  partnerId: string,
  value: string
): Promise<{ reportId: string; value: string; updatedAt: string }> {
  const res = await instrumentedFetch({
    operation: "submitSynastryFeedback",
    routeTemplate: "/api/synastry/{partner_id}/feedback",
    url: `/api/synastry/${partnerId}/feedback`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ value }),
    },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
  return res.json()
}

export async function deleteSynastryPartner(partnerId: string): Promise<void> {
  const res = await instrumentedFetch({
    operation: "deleteSynastryPartner",
    routeTemplate: "/api/synastry/{partner_id}",
    url: `/api/synastry/${partnerId}`,
    init: {
      method: "DELETE",
      credentials: "include",
    },
  })
  if (!res.ok) {
    throw await buildSynastryApiError(res)
  }
}
