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
// invariants:
//   - All API endpoints send credentialed cookies and preserve error messages.
// failure_policy: Throws Error on non-2xx responses.
// END_MODULE_CONTRACT: M-FRONTEND-API-SYNASTRY

// START_MODULE_MAP: M-FRONTEND-API-SYNASTRY
// public_entrypoints:
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

export type SynastryCapabilities = {
  canCalculate: boolean
  activePartnerCount: number
  maxPartners: number
  hasUnlockedAccess: boolean
  creditBalance: number
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

export type AspectDrilldownData = {
  aspectId: string
  title: string
  tone: "good" | "mid" | "bad" | "supportive" | "mixed" | "tense"
  techSignature: string | null
  explanation: string
  scenario: string | null
  advice: string | null
}

export type SynastrySphereItem = {
  id: string
  title: string
  score: number
  description: string | null
}

export type SynastryReportData = {
  id: string
  ownerId: string
  partnerId: string
  partnerName: string
  partnerBirthDate: string | null
  partnerBirthTime: string | null
  partnerBirthCity: string | null
  relationType: string
  precision: "exact" | "approximate"
  score: number
  status: "good" | "mid" | "bad"
  verdict: string
  summary: string
  heroTitle: string | null
  heroDescription: string | null
  counters: { good: number; mid: number; bad: number }
  ownerPlanets?: SynastryPlanetPoint[]
  partnerPlanets?: SynastryPlanetPoint[]
  aspects: SynastryAspectItem[]
  houseOverlays: Array<{ tech?: string; text?: string }>
  spheres: SynastrySphereItem[]
  translations: Array<{ tone?: string; title?: string; aspectId?: string | null; tech?: string; text?: string; scene?: string }>
  userFeedback: string | null
  createdAt: string
}

export async function getSynastryCapabilities(): Promise<SynastryCapabilities> {
  const res = await instrumentedFetch({
    operation: "getSynastryCapabilities",
    routeTemplate: "/api/synastry/capabilities",
    url: "/api/synastry/capabilities",
    init: { credentials: "include" },
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch synastry capabilities: ${res.status}`)
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
    throw new Error(`Failed to fetch synastry partners: ${res.status}`)
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
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || errorData.message || `Failed to add partner: ${res.status}`)
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
    throw new Error(`Failed to fetch synastry report: ${res.status}`)
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
    throw new Error(`Failed to fetch synastry status: ${res.status}`)
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
    throw new Error(`Failed to fetch aspect drilldown: ${res.status}`)
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
    throw new Error(`Failed to submit feedback: ${res.status}`)
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
    throw new Error(`Failed to delete partner: ${res.status}`)
  }
}
