// ############################################################################
// AI_HEADER: FRONTEND_API_PROFILE — credentialed canonical profile read and update client.
// ROLE: Credentialed profile read and update facade used by profile and onboarding hooks.
// DEPENDENCIES: packages/contracts profile types; packages/contracts/runtime ProfileReadWireSchema; lib/log/instrumented-fetch.
// GRACE_ANCHORS: [FRONTEND_API_PROFILE]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PROFILE
// purpose: GET or PUT the canonical profile via instrumentedFetch with ProfileRead responseContract and preserve backend error detail.
// owns:
//   - lib/api/profile.ts
// inputs: no arguments for get; ProfileWrite for update; NEXT_PUBLIC_API_URL.
// outputs: exported profile types and Promise<ProfileRead>.
// dependencies: packages/contracts profile types; packages/contracts/runtime ProfileReadWireSchema; lib/log/instrumented-fetch.
// side_effects: credentialed GET and PUT /api/profile via instrumentedFetch.
// emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_request_failed, frontend.api_response_invalid.
// invariants:
//   - Update remains PUT with a JSON body.
//   - Successful response data is validated against ProfileReadWireSchema.
//   - Error priority remains detail string, detail.message, validation message array, then endpoint fallback.
// failure_policy: Throw the decoded Error on non-ok responses; network and JSON errors propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-PROFILE

// START_MODULE_MAP: M-FRONTEND-API-PROFILE
// public_entrypoints:
//   - BirthData
//   - ProfileRead
//   - ProfileWrite
//   - getProfile
//   - updateProfile
// semantic_blocks:
//   - ERROR_DECODE: preserve backend detail and validation-message priority.
//   - PROFILE_READ: fetch and return the canonical profile via instrumentedFetch.
//   - PROFILE_UPDATE: PUT profile data and return the canonical result via instrumentedFetch.
// owned_tests:
//   - __tests__/api/profile-client.test.ts
//   - __tests__/api/onboarding-payload.test.ts
//   - __tests__/hooks/useProfile.test.ts
// END_MODULE_MAP: M-FRONTEND-API-PROFILE

import type { BirthData, ProfileRead, ProfileWrite } from "@/packages/contracts"
import { ProfileReadWireSchema } from "@/packages/contracts/runtime"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export type { BirthData, ProfileRead, ProfileWrite }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

// START_BLOCK: ERROR_DECODE
async function responseError(res: Response, fallback: string): Promise<Error> {
  const payload = await res.json().catch(() => null)
  const detail = payload?.detail
  if (typeof detail === "string") return new Error(detail)
  if (detail && typeof detail.message === "string") return new Error(detail.message)
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((message): message is string => typeof message === "string")
    if (messages.length > 0) return new Error(messages.join(". "))
  }
  return new Error(fallback)
}
// END_BLOCK: ERROR_DECODE

// START_BLOCK: PROFILE_READ
/**
 * Get user profile
 * @returns ProfileRead
 * @throws Error on HTTP errors
 */
export async function getProfile(): Promise<ProfileRead> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROFILE.getProfile
  // purpose: Fetch canonical profile via instrumentedFetch with ProfileRead responseContract.
  // inputs: none
  // returns: Promise<ProfileRead>
  // side_effects: GET /api/profile via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROFILE.getProfile
  const res = await instrumentedFetch({
    operation: "profile.get",
    routeTemplate: "GET /api/profile",
    url: `${API_BASE}/api/profile`,
    init: {
      credentials: "include",
      headers: {
        "Accept": "application/json",
      },
    },
    responseContract: {
      contractName: "ProfileRead",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = ProfileReadWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (!res.ok) {
    throw await responseError(res, "Failed to get profile")
  }

  const raw = await res.json()
  return ProfileReadWireSchema.parse(raw)
}
// END_BLOCK: PROFILE_READ

// START_BLOCK: PROFILE_UPDATE
/**
 * Update user profile (partial update)
 * @param data - ProfileWrite with fields to update
 * @returns ProfileRead with updated profile
 * @throws Error on HTTP errors
 */
export async function updateProfile(data: ProfileWrite): Promise<ProfileRead> {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROFILE.updateProfile
  // purpose: Update user profile via instrumentedFetch PUT request with ProfileRead responseContract.
  // inputs: data — ProfileWrite payload
  // returns: Promise<ProfileRead>
  // side_effects: PUT /api/profile via instrumentedFetch
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-API-PROFILE.updateProfile
  const res = await instrumentedFetch({
    operation: "profile.update",
    routeTemplate: "PUT /api/profile",
    url: `${API_BASE}/api/profile`,
    init: {
      method: "PUT",
      credentials: "include",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    },
    responseContract: {
      contractName: "ProfileRead",
      contractVersion: "v1",
      validate: (json) => {
        const parsed = ProfileReadWireSchema.safeParse(json)
        if (parsed.success) return { valid: true }
        const fields = parsed.error.issues.map((i) => String(i.path[0] || "unknown"))
        return { valid: false, missingFields: fields, invalidFieldTypes: fields }
      },
    },
  })

  if (!res.ok) {
    throw await responseError(res, "Failed to update profile")
  }

  const raw = await res.json()
  return ProfileReadWireSchema.parse(raw)
}
// END_BLOCK: PROFILE_UPDATE
